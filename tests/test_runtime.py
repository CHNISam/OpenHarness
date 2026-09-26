import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openharness.model import digest
from openharness.repository import Repository, bootstrap, json_text
from openharness.runtime import Runtime
from tests.helpers import git, make_repo


class FakeGitHub:
    def __init__(self):
        self.fingerprint = 'current-policy'
        self.sha = None

    def observe(self, config):
        return {'source': 'test-fixture', 'fingerprint': self.fingerprint, 'target_sha': self.sha, 'gate': True, 'errors': []}

    def work(self, config, issue):
        return {'number': issue, 'state': 'open'}

    def list_work(self, config):
        return [{'number': 1, 'title': 'Legal work', 'url': 'https://github.com/owner/repo/issues/1'}]


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = make_repo(self.temp.name)
        self.repo = Repository(self.root)
        bootstrap(self.repo, 'owner/repo', 'main')
        config = self.repo.config()
        config['verification']['commands'] = [['python', '-c', 'from pathlib import Path; assert Path("file.txt").read_text() == "base\\n"']]
        (self.root / '.harness/config.json').write_text(json_text(config), encoding='utf-8')
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'install')
        self.provider = FakeGitHub()
        self.provider.sha = self.repo.revision('main')
        self.runtime = Runtime(self.repo, self.provider)

    def test_native_lock_contention_reports_busy_and_recovers_after_holder_exits(self):
        child = (
            'import sys\n'
            'from openharness.repository import Repository\n'
            'from openharness.runtime import Runtime\n'
            'with Runtime(Repository(sys.argv[1])).locked():\n'
            '    print("locked", flush=True)\n'
            '    sys.stdin.read(1)\n'
        )
        process = subprocess.Popen(
            [sys.executable, '-c', child, str(self.root)],
            cwd=Path(__file__).resolve().parents[1],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual('locked\n', process.stdout.readline())
            with self.assertRaisesRegex(ValueError, 'Another local lifecycle operation holds the native process lock'):
                with self.runtime.locked():
                    pass
            process.stdin.write('x')
            process.stdin.flush()
            self.assertEqual(0, process.wait(timeout=5))
            with self.runtime.locked():
                pass
            self.assertEqual(b'0', (self.runtime.storage / 'operation.lock').read_bytes())
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            process.stdin.close()
            process.stdout.close()
            process.stderr.close()

    def test_lock_file_access_denial_remains_permission_error(self):
        with patch.object(Path, 'open', side_effect=PermissionError('ACL denied')):
            with self.assertRaisesRegex(PermissionError, 'ACL denied'):
                with self.runtime.locked():
                    pass

    def test_release_refuses_unintegrated_work_and_handoff_preserves_binding(self):
        binding = self.repo.workspace(1, 'fix', self.repo.revision('HEAD'))
        work = Runtime(Repository(binding['path']), self.provider)
        work.save_state({'lifecycle': 'GENESIS', 'events': [], 'workspaces': {binding['path']: binding}})
        with self.assertRaises(ValueError):
            work.release()
        record = work.handoff('Tests complete; native PR still needs integration')
        self.assertTrue(record['worktree_preserved'])
        self.assertEqual(binding, work.state()['workspaces'][binding['path']])
        self.assertEqual('HANDOFF', work.state()['events'][-1]['transition'])

    def test_activation_refuses_fixture_pass_without_provenance(self):
        with self.assertRaises(ValueError):
            self.runtime.activate()
        self.assertEqual('GENESIS', self.runtime.state()['lifecycle'])

    def test_break_glass_is_observable_and_cannot_silently_reactivate(self):
        before = self.runtime.break_glass('repair broken control surface')
        self.assertEqual('BREAK_GLASS', before['lifecycle'])
        self.assertEqual('repair broken control surface', before['events'][-1]['reason'])
        after = Runtime(self.repo, self.provider).reconcile()
        self.assertEqual('BREAK_GLASS', after['lifecycle'])
        self.assertFalse(after['doctor']['closure'])
        with self.assertRaises(ValueError):
            self.runtime.preflight()

    def test_empty_break_glass_reason_rejected(self):
        with self.assertRaises(ValueError):
            self.runtime.break_glass('  ')

    def test_break_glass_doctor_never_labels_invalidated_guarantees_established(self):
        self.runtime.break_glass('explicit recovery')
        report = self.runtime.doctor()
        self.assertFalse(report['closure'])
        self.assertTrue(all(g['status'] == 'OPEN GAP' for g in report['guarantees']))

    def test_genesis_cannot_claim_established_repository_guarantees(self):
        report = self.runtime.doctor()
        self.assertFalse(any(g['status'] == 'ESTABLISHED' for g in report['guarantees']))

    def test_corrupt_runtime_can_be_repaired_without_working_harness_config(self):
        self.runtime.storage.mkdir(parents=True, exist_ok=True)
        (self.runtime.storage / 'runtime.json').write_text('{corrupt', encoding='utf-8')
        (self.root / '.harness/config.json').write_text('{broken', encoding='utf-8')
        state = self.runtime.break_glass('repair malformed configuration')
        self.assertEqual('BREAK_GLASS', state['lifecycle'])
        self.assertTrue(list(self.runtime.storage.glob('corrupt-runtime-*')))

    def test_bootstrap_has_no_managed_lifecycle_exemption(self):
        self.runtime.save_state({'lifecycle': 'MANAGED', 'substrate': 'old', 'events': []})
        with self.assertRaises(ValueError):
            bootstrap(self.repo, 'owner/repo', 'main')

    def test_malformed_runtime_semantics_require_explicit_recovery(self):
        self.runtime.save_state({'lifecycle': 'MANAGED', 'events': 'not-an-event-list'})
        state = self.runtime.break_glass('recover invalid state schema')
        self.assertEqual('BREAK_GLASS', state['lifecycle'])
        self.assertIsInstance(state['events'], list)

    def test_reconcile_invalidates_old_activation_when_policy_changes(self):
        self.runtime.save_state({'lifecycle': 'MANAGED', 'substrate': 'old', 'events': []})
        recovered = Runtime(self.repo, self.provider).reconcile()
        self.assertEqual('UNPROVEN', recovered['lifecycle'])
        self.assertIsNone(recovered['substrate'])

    def test_verifier_code_identity_changes_invalidate_guarantee_substrate(self):
        from unittest.mock import patch
        before = self.runtime.doctor()['substrate']
        with patch('openharness.runtime.execution_identity', return_value={'code': 'changed-verifier'}):
            after = self.runtime.doctor()['substrate']
        self.assertNotEqual(before, after)

    def test_changed_origin_cannot_keep_authority_readiness(self):
        git(self.root, 'remote', 'set-url', 'origin', 'https://github.com/other/repo.git')
        report = self.runtime.doctor()
        row = next(g for g in report['readiness']['guarantees'] if g['id'] == 'authority')
        self.assertEqual('OPEN GAP', row['status'])

    def test_candidate_verification_is_local_and_bound_to_result_tree(self):
        result = self.runtime.verify('HEAD', 'main')
        self.assertTrue(result['passed'])
        self.assertEqual('local-diagnostic-only', result['authority'])
        self.assertFalse(result['authorizes_integration'])
        self.assertEqual(digest(result['candidate']), result['candidate_id'])
        self.assertTrue(self.runtime.evidence('HEAD', 'main')['fresh'])

    def test_changed_base_invalidates_existing_evidence(self):
        self.runtime.verify('HEAD', 'main')
        (self.root / 'extra.txt').write_text('new-base', encoding='utf-8')
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'base moved')
        self.assertFalse(self.runtime.evidence('HEAD', 'main')['fresh'])

    def test_tests_run_on_merged_candidate_not_head(self):
        git(self.root, 'checkout', '-b', 'change')
        (self.root / 'extra.txt').write_text('head', encoding='utf-8')
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'head')
        git(self.root, 'checkout', 'main')
        (self.root / 'file.txt').write_text('changed-base\n', encoding='utf-8')
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'base')
        git(self.root, 'checkout', 'change')
        result = self.runtime.verify('HEAD', 'main')
        self.assertFalse(result['passed'])
        self.assertEqual(1, result['checks'][0]['returncode'])

    def test_dirty_workspace_rejected_before_running_tests(self):
        (self.root / 'file.txt').write_text('dirty', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.runtime.verify('HEAD', 'main')

    def test_candidate_mutation_cannot_produce_passing_evidence(self):
        config = self.repo.config()
        config['verification']['commands'] = [['python', '-c', 'from pathlib import Path; Path("file.txt").write_text("mutated")']]
        (self.root / '.harness/config.json').write_text(json_text(config), encoding='utf-8')
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'mutating check')
        result = self.runtime.verify('HEAD', 'main')
        self.assertFalse(result['passed'])
        self.assertFalse(result['subject_unchanged'])
        self.assertEqual('base\n', (self.root / 'file.txt').read_text(encoding='utf-8'))

    def test_failed_check_removes_only_diagnostic_worktree(self):
        config = self.repo.config()
        config['verification']['commands'] = [['python', '-c', 'raise SystemExit(7)']]
        (self.root / '.harness/config.json').write_text(json_text(config), encoding='utf-8')
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'failing check')
        result = self.runtime.verify('HEAD', 'main')
        self.assertFalse(result['passed'])
        self.assertEqual(1, len(self.runtime._worktrees()))

    def test_material_environment_changes_reject_old_evidence(self):
        import os
        from unittest.mock import patch
        config = self.repo.config()
        config['verification']['environment'] = {'OPENHARNESS_TEST_MODE': 'one'}
        (self.root / '.harness/config.json').write_text(json_text(config), encoding='utf-8')
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'material environment')
        with patch.dict(os.environ, {'OPENHARNESS_TEST_MODE': 'one'}):
            self.assertTrue(self.runtime.verify('HEAD', 'main')['passed'])
        with patch.dict(os.environ, {'OPENHARNESS_TEST_MODE': 'two'}):
            with self.assertRaises(ValueError):
                self.runtime.evidence('HEAD', 'main')

    def test_orphaned_workspace_binding_is_reconciled(self):
        state = self.runtime.state()
        state['workspaces'] = {'missing-path': {'branch': 'codex/missing'}}
        self.runtime.save_state(state)
        result = self.runtime.reconcile()
        self.assertEqual(['missing-path'], result['orphaned_bindings'])
        self.assertEqual({}, result['workspaces'])

    def test_genesis_workspace_requires_explicit_flag(self):
        with self.assertRaises(ValueError):
            self.runtime.workspace(1, 'first')
        binding = self.runtime.workspace(1, 'first', genesis=True)
        self.assertEqual(1, binding['work_item'])
        self.assertEqual('GENESIS', binding['authority'])
        entry = Runtime(Repository(binding['path']), self.provider).entry()
        self.assertEqual(binding['branch'], entry['workspace']['branch'])

    def test_upgrade_in_genesis_is_staged_not_activated(self):
        result = self.runtime.upgrade()
        self.assertEqual('GENESIS', result['lifecycle'])
        self.assertFalse(result['activated'])


if __name__ == '__main__':
    unittest.main()
