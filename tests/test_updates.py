import base64
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openharness import updates
from openharness.ci import candidate_context
from openharness.model import digest
from openharness.repository import Repository, bootstrap, json_text
from openharness.runtime import Runtime, ClosureError
from tests.helpers import git, make_repo


class ReleaseAPI:
    def __init__(self):
        self.values = {}
        self.manifests = {}
        self.add('0.2.1', 'a' * 40)
        self.add('0.2.2', 'b' * 40)

    def add(self, value, sha, previous=('0.2.1',)):
        data = updates.manifest(list(previous))
        data['version'] = value
        prefix = 'repos/trusted/tool'
        record = {'tag_name': 'v' + value, 'draft': False, 'prerelease': False, 'immutable': True}
        self.values[f'{prefix}/releases/tags/v{value}'] = record
        self.values[f'{prefix}/git/ref/tags/v{value}'] = {'object': {'type': 'commit', 'sha': sha}}
        for path, content in [('openharness-release.json', json_text(data)), ('openharness/__init__.py', f"__version__ = '{value}'\n"), ('pyproject.toml', f'[project]\nname = "openharness"\nversion = "{value}"\n')]:
            self.values[f'{prefix}/contents/{path}?ref={sha}'] = {'type': 'file', 'encoding': 'base64', 'content': base64.b64encode(content.encode()).decode()}
        self.manifests[value] = data

    def __call__(self, path):
        if '/releases?per_page=100&page=1' in path:
            return [value for key, value in self.values.items() if '/releases/tags/' in key]
        if path not in self.values:
            raise AssertionError('Unexpected provider request: ' + path)
        return copy.deepcopy(self.values[path])


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        # These historical propagation fixtures execute the old pinned 0.2.1 preparer.
        if self._testMethodName != 'test_committed_manifest_matches_compiler_and_package_version':
            pinned = patch('openharness.updates.__version__', '0.2.1')
            pinned.start()
            self.addCleanup(pinned.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = make_repo(self.temp.name)
        self.repo = Repository(self.root)
        bootstrap(self.repo, 'owner/repo', 'main')
        self.api = ReleaseAPI()
        self.source = updates.Releases('trusted/tool', self.api)
        config = self.repo.config()
        config['verification']['controller'] = {'repository': 'trusted/tool', 'revision': 'a' * 40}
        config['verification']['commands'] = [[sys.executable, '-c', 'from pathlib import Path; assert Path("file.txt").read_text() == "base\\n"']]
        config['verification']['environment'] = {'PROJECT_MODE': 'preserved'}
        config['verification']['sandbox_image'] = 'python@sha256:' + 'c' * 64
        (self.root / '.harness/config.json').write_text(json_text(config), encoding='utf-8')
        proposal = updates.plan(config, None, self.source.resolve('0.2.1'), updates.read_files(self.repo))
        updates.apply(self.repo, proposal['changes'])
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'enroll consumer')

    def request(self, value='0.2.2'):
        (self.root / updates.REQUEST).write_text(json_text({'version': value}), encoding='utf-8')

    def test_end_to_end_discovery_renovate_proposal_acceptance_and_reproof(self):
        before = self.repo.config()
        releases = self.source.discover('0.2.1')
        self.assertEqual(['0.2.2'], [r['version'] for r in releases])
        preset = updates.renovate_config('trusted/tool', 7)
        rule = preset['packageRules'][0]
        self.assertFalse(rule['automerge'])
        self.assertEqual('codex/7-', rule['branchPrefix'])
        self.assertIn('Work-Item: #7', rule['prBodyNotes'])
        git(self.root, 'checkout', '-b', 'codex/7-openharness-0-2-2')
        runtime = Runtime(self.repo)
        # A prior activation is a local projection; fixture success cannot activate.
        runtime.save_state({'lifecycle': 'MANAGED', 'substrate': 'prior', 'events': [], 'workspaces': {}})
        self.request()
        proposal = updates.prepare(self.repo, self.api)
        self.assertEqual('patch', proposal['kind'])
        self.assertFalse(proposal['activated'])
        expected = copy.deepcopy(before)
        expected['verification']['controller']['revision'] = 'b' * 40
        self.assertEqual(expected, self.repo.config())
        self.assertEqual('0.2.2', updates.installed(self.repo)['version'])
        updates.validate_candidate(self.repo, 'main', self.api)
        self.assertEqual(proposal, updates.prepare(self.repo, self.api))
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'propose upgrade')
        pull = {'number': 8, 'state': 'open', 'draft': False, 'body': 'Work-Item: #7',
                'head': {'sha': self.repo.revision('HEAD'), 'ref': 'codex/7-openharness-0-2-2'},
                'base': {'sha': self.repo.revision('main'), 'ref': 'main'}}
        self.assertEqual(7, candidate_context(expected, pull, {'number': 7, 'state': 'open'})['issue'])
        with patch.dict('os.environ', {'PROJECT_MODE': 'preserved'}):
            self.assertTrue(runtime.verify('HEAD', 'main')['passed'])
        # Doctor still re-observes the provider, not candidate-authored evidence.
        provider = {'source': 'test-fixture', 'fingerprint': 'changed', 'errors': [], 'gate': True}
        with patch.object(runtime.provider, 'observe', return_value=provider):
            report = runtime.doctor()
            self.assertFalse(report['closure'])
            with self.assertRaises(ClosureError):
                runtime.preflight()
            self.assertEqual('UNPROVEN', runtime.reconcile()['lifecycle'])
            with self.assertRaisesRegex(ValueError, 'live complete closure'):
                runtime.activate()
        self.assertFalse(runtime.state().get('substrate'))

    def test_upgrade_alone_invalidates_previously_current_activation_and_evidence(self):
        runtime = Runtime(self.repo)
        observation = {'source': 'test-fixture', 'fingerprint': 'unchanged-policy',
                       'errors': [], 'gate': True, 'trusted_controller': True,
                       'deployment_proven': True, 'target_sha': self.repo.revision('main')}
        with patch.object(runtime.provider, 'observe', return_value=observation):
            assessment = runtime.doctor(revalidate=True)
            self.assertTrue(assessment['closure'])
            # Simulate an already established projection, never activation from fixtures.
            runtime.save_state({'lifecycle': 'MANAGED', 'substrate': assessment['substrate'],
                                'events': [], 'workspaces': {}})
            self.assertTrue(runtime.doctor()['closure'])
            with patch.dict('os.environ', {'PROJECT_MODE': 'preserved'}):
                self.assertTrue(runtime.verify('HEAD', 'main')['passed'])
                self.assertTrue(runtime.evidence('HEAD', 'main')['fresh'])
                self.request()
                updates.prepare(self.repo, self.api)
                self.assertFalse(runtime.evidence('HEAD', 'main')['fresh'])
            self.assertFalse(runtime.doctor()['closure'])
            self.assertEqual('UNPROVEN', runtime.reconcile()['lifecycle'])
            with self.assertRaisesRegex(ValueError, 'live complete closure'):
                runtime.activate()

    def test_mutable_prerelease_untrusted_and_republished_revisions_rejected(self):
        for value in ('main', 'latest', 'v0.2.2', '0.2.2-rc.1', '01.2.3'):
            with self.assertRaises(ValueError):
                self.source.resolve(value)
        key = 'repos/trusted/tool/releases/tags/v0.2.2'
        self.api.values[key]['immutable'] = False
        with self.assertRaisesRegex(ValueError, 'immutable'):
            self.source.resolve('0.2.2')
        self.api.values[key]['immutable'] = True
        release = self.source.resolve('0.2.2')
        release['repository'] = 'attacker/tool'
        with self.assertRaisesRegex(ValueError, 'trusted controller'):
            updates.plan(self.repo.config(), updates.installed(self.repo), release, updates.read_files(self.repo))
        release = self.source.resolve('0.2.1')
        release['revision'] = 'c' * 40
        with self.assertRaisesRegex(ValueError, 'cannot change'):
            updates.plan(self.repo.config(), updates.installed(self.repo), release, updates.read_files(self.repo))

    def test_compatibility_is_explicit_and_major_or_zero_minor_stop(self):
        for value in ('0.3.0', '1.0.0'):
            self.api.add(value, 'c' * 40)
            with self.assertRaisesRegex(ValueError, 'dedicated migration'):
                updates.plan(self.repo.config(), updates.installed(self.repo), self.source.resolve(value), updates.read_files(self.repo))
        self.api.add('0.2.3', 'd' * 40, previous=())
        with self.assertRaisesRegex(ValueError, 'explicitly support'):
            updates.plan(self.repo.config(), updates.installed(self.repo), self.source.resolve('0.2.3'), updates.read_files(self.repo))
        release = self.source.resolve('0.2.2')
        release['version'] = '1.3.0'
        release['manifest']['compatible_from'] = ['1.2.0']
        self.assertEqual('minor', updates.compatible('1.2.0', release))

    def test_artifacts_migrate_preserving_project_configuration_and_instructions(self):
        path = self.root / '.harness/AGENT.md'
        old = updates.installed(self.repo)
        old_content = path.read_text() + '\nprevious compiler\n'
        path.write_text(old_content)
        old['artifacts']['.harness/AGENT.md'] = updates.content_hash(old_content)
        (self.root / updates.INSTALLATION).write_text(json_text(old))
        before = self.repo.config()
        instructions = (self.root / 'AGENTS.md').read_bytes()
        proposal = updates.plan(before, old, self.source.resolve('0.2.2'), updates.read_files(self.repo))
        self.assertIn('.harness/AGENT.md', proposal['changes'])
        updates.apply(self.repo, proposal['changes'])
        self.assertEqual(updates.manifest([])['artifacts']['.harness/AGENT.md'], path.read_text())
        self.assertEqual(instructions, (self.root / 'AGENTS.md').read_bytes())
        self.assertEqual(before['verification']['commands'], self.repo.config()['verification']['commands'])
        self.assertEqual({}, updates.plan(self.repo.config(), updates.installed(self.repo), self.source.resolve('0.2.2'), updates.read_files(self.repo))['changes'])

    def test_custom_artifact_and_unrelated_edit_stop_without_mutation(self):
        self.request()
        path = self.root / '.harness/AGENT.md'
        path.write_text('project custom instructions\n')
        before = (self.root / '.harness/config.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'Unexpected proposal checkout edit'):
            updates.prepare(self.repo, self.api)
        self.assertEqual(before, (self.root / '.harness/config.json').read_bytes())
        self.assertEqual('project custom instructions\n', path.read_text())
        self.assertFalse(self.repo.local()['installed'])

    def test_write_failure_rolls_back_all_bytes(self):
        proposal = updates.plan(self.repo.config(), updates.installed(self.repo), self.source.resolve('0.2.2'), updates.read_files(self.repo))
        before = {p: (self.root / p).read_bytes() for p in proposal['changes']}
        actual = Path.write_text
        count = 0
        def failing(path, *args, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('simulated full disk')
            return actual(path, *args, **kwargs)
        with patch.object(Path, 'write_text', failing):
            with self.assertRaises(OSError):
                updates.apply(self.repo, proposal['changes'])
        self.assertEqual(before, {p: (self.root / p).read_bytes() for p in proposal['changes']})

    def test_candidate_rejects_tampered_delta_and_failed_acceptance(self):
        self.request()
        updates.prepare(self.repo, self.api)
        config = self.repo.config()
        config['verification']['commands'] = [[sys.executable, '-c', 'raise SystemExit(1)']]
        (self.root / '.harness/config.json').write_text(json_text(config))
        with self.assertRaisesRegex(ValueError, 'differs from verified migration'):
            updates.validate_candidate(self.repo, 'main', self.api)
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'bad proposed acceptance')
        with patch.dict('os.environ', {'PROJECT_MODE': 'preserved'}):
            self.assertFalse(Runtime(self.repo).verify('HEAD', 'main')['passed'])

    def test_governed_revert_restores_exact_previous_canonical_release(self):
        before = self.repo.revision('main')
        self.request()
        updates.prepare(self.repo, self.api)
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'canonical upgrade')
        upgraded = self.repo.revision('HEAD')
        git(self.root, 'checkout', '-b', 'codex/7-rollback')
        git(self.root, 'revert', '--no-edit', upgraded)
        updates.validate_candidate(self.repo, 'main', self.api)
        self.assertEqual('0.2.1', updates.installed(self.repo)['version'])
        with self.assertRaisesRegex(ValueError, 'Downgrade'):
            updates.compatible('0.2.2', self.source.resolve('0.2.1'))
        self.assertEqual(self.repo.git('rev-parse', before + '^{tree}'),
                         self.repo.git('rev-parse', 'HEAD^{tree}'))

    def test_request_without_migration_cannot_pass_doctor_or_candidate(self):
        self.request()
        self.assertFalse(self.repo.local()['installed'])
        with self.assertRaisesRegex(ValueError, 'not materialized'):
            updates.validate_candidate(self.repo, 'main', self.api)

    def test_annotated_tag_and_torn_or_incomplete_observations(self):
        key = 'repos/trusted/tool/git/ref/tags/v0.2.2'
        self.api.values[key] = {'object': {'type': 'tag', 'sha': 'c' * 40}}
        self.api.values['repos/trusted/tool/git/tags/' + 'c' * 40] = {'object': {'type': 'commit', 'sha': 'b' * 40}}
        self.assertEqual('b' * 40, self.source.resolve('0.2.2')['revision'])
        counter = 0
        def torn(path):
            nonlocal counter
            result = self.api(path)
            if path == key:
                counter += 1
                if counter == 2:
                    result['object']['sha'] = 'd' * 40
            return result
        with self.assertRaisesRegex(ValueError, 'changed during observation'):
            updates.Releases('trusted/tool', torn).resolve('0.2.2')
        with self.assertRaisesRegex(ValueError, 'pagination limit'):
            updates.Releases('trusted/tool', lambda _: [{}] * 100).discover('0.2.1')

    def test_committed_manifest_matches_compiler_and_package_version(self):
        producer = Path(__file__).resolve().parents[1]
        data = json.loads((producer / 'openharness-release.json').read_bytes())
        self.assertEqual(updates.manifest([]), data)
        import tomllib
        package = tomllib.loads((producer / 'pyproject.toml').read_text())
        self.assertEqual(data['version'], package['project']['version'])

    def test_trusted_candidate_path_runs_both_configurations_after_migration_validation(self):
        from openharness.ci import check_candidate
        git(self.root, 'checkout', '-b', 'codex/7-openharness-0-2-2')
        baseline_path = self.root / 'baseline'
        git(self.root, 'worktree', 'add', '--detach', str(baseline_path), 'main')
        # Native worktree directory is ignored by this test consumer, not committed.
        (self.root / '.git/info/exclude').write_text('baseline/\n')
        self.request()
        updates.prepare(self.repo, self.api)
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'upgrade proposal')
        head, base = self.repo.revision('HEAD'), self.repo.revision('main')
        pull = {'number': 8, 'state': 'open', 'draft': False, 'body': 'Work-Item: #7',
                'head': {'sha': head, 'ref': 'codex/7-openharness-0-2-2'},
                'base': {'sha': base, 'ref': 'main'}}
        def provider(path):
            if path == 'repos/owner/repo/pulls/8':
                return pull
            if path == 'repos/owner/repo/issues/7':
                return {'number': 7, 'state': 'open'}
            if path == 'repos/owner/repo/branches/main':
                return {'commit': {'sha': base}}
            if path == 'repos/owner/repo/issues/7/comments?per_page=100':
                return [{'user': {'login': 'owner'}, 'body': f'OpenHarness-Control-Approval: {head} {base}'}]
            return self.api(path)
        from subprocess import CompletedProcess
        original_run = updates.subprocess.run
        docker_calls = []
        def run(command, **kwargs):
            if command[0] == 'docker':
                docker_calls.append(command)
                return CompletedProcess(command, 0, '', '')
            return original_run(command, **kwargs)
        with patch('openharness.ci.subprocess.run', side_effect=run):
            result = check_candidate(Repository(baseline_path).config(), baseline_path, self.root,
                                     {'pull_request': {'number': 8}}, provider)
        self.assertTrue(result['control_authorized'])
        self.assertEqual(2, len(docker_calls))
        self.assertEqual(head, result['head'])

    def test_governed_upgrade_requires_preflight_and_invalidates_before_apply(self):
        runtime = Runtime(self.repo)
        runtime.save_state({'lifecycle': 'MANAGED', 'substrate': 'old', 'events': [], 'workspaces': {}})
        with patch.object(runtime, 'preflight', side_effect=ValueError('no current authority')):
            with self.assertRaisesRegex(ValueError, 'no current authority'):
                runtime.upgrade('0.2.2')
        self.assertEqual('0.2.1', updates.installed(self.repo)['version'])
        with patch.object(runtime, 'preflight', return_value={'allowed': True}), patch('openharness.updates.gh_api', self.api):
            # Releases default api is supplied at construction, so patch its constructor.
            with patch('openharness.updates.Releases', return_value=self.source):
                result = runtime.upgrade('0.2.2')
        self.assertFalse(result['activated'])
        self.assertEqual('UNPROVEN', runtime.state()['lifecycle'])
        self.assertIsNone(runtime.state()['substrate'])


if __name__ == '__main__':
    unittest.main()
