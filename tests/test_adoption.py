import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openharness import __version__
from openharness import adoption, updates
from openharness.backlog import authorize, local_corpus
from openharness.model import default_config
from openharness.repository import ENTRY, BACKLOG_ENTRY, Repository, json_text
from openharness.runtime import Runtime
from tests.helpers import git, make_repo
from tests.test_updates import ReleaseAPI


class BacklogAdoptionTests(unittest.TestCase):
    """Observed Nameless Reach shape, synthetic task data; never its deployment proof."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = make_repo(self.temp.name)
        git(self.root, 'branch', '-m', 'develop')
        git(self.root, 'checkout', '-b', 'change/task-20')
        self.repo = Repository(self.root)
        self.config = default_config('owner/repo', 'develop')
        self.config['verification'].update(commands=[['python', '-m', 'unittest', 'discover', '-s', 'tools/tests', '-v']],
              environment={'PROJECT_MODE': 'preserved'}, expected_app_id=15368,
              controller={'repository': 'trusted/tool', 'revision': '2e8af8112fda085dae8c81ce80e31b7d1f4f46c3'},
              sandbox_image='python@sha256:' + 'c' * 64)
        self.work = {'format': 'backlog-md-1.53-subset-v1',
                     'directories': ['backlog/tasks', 'backlog/completed'],
                     'ready_statuses': ['Ready', 'In Progress'], 'done_status': 'Done',
                     'actors': {'codex:session-20': 'alice'}}
        self.agent = ('# GENESIS boundary for Nameless Reach\r\n\r\n'
                      'Installation is not activation. Current work authority is native Backlog tasks on remote develop; follow root AGENTS.md and the Backlog execution protocol. The upstream GitHub Issue workflow below is inactive. Future activation must preserve Backlog as the work authority and prove compatible integration.\r\n\r\n' + ENTRY.replace('\n', '\r\n'))
        self.agents = '# Project execution\r\nBacklog tasks on remote develop are the sole work authority. OpenHarness remains staged in GENESIS; read .harness/AGENT.md for that boundary.\r\n'
        (self.root / '.gitignore').write_text('__pycache__/\n')
        (self.root / '.harness').mkdir()
        (self.root / '.harness/config.json').write_text(json_text(self.config))
        (self.root / '.harness/AGENT.md').write_bytes(self.agent.encode())
        (self.root / 'AGENTS.md').write_bytes(self.agents.encode())
        from openharness.ci import workflow_text
        (self.root / '.harness/github-workflow.yml.template').write_text(workflow_text())
        for path, text in {
            'tools/tests/test_project.py': 'import unittest\nfrom pathlib import Path\nclass ProjectTests(unittest.TestCase):\n    def test_acceptance(self):\n        self.assertEqual("base\\n", Path("file.txt").read_text())\n',
            'backlog/tasks/task-20 - Support migration.md': "---\nid: task-20\ntitle: Support migration\nstatus: In Progress\nassignee: ['codex:session-20']\ndependencies: [task-19]\nlabels: [infrastructure]\n---\nProject acceptance remains project-owned.\n",
            'backlog/completed/task-19 - Prerequisite.md': "---\nid: task-19\ntitle: Prerequisite\nstatus: Done\nassignee: []\ndependencies: []\n---\nHistorical completion remains unchanged.\n",
        }.items():
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        reviewed = adoption.declaration(self.config, self.work, updates.read_files(self.repo))
        (self.root / updates.ADOPTION).write_text(json_text(reviewed))
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'review legacy ownership and Backlog adoption declaration')
        self.base = self.repo.revision('HEAD')
        self.api = ReleaseAPI()
        self.api.add(__version__, 'd' * 40, previous=())
        self.release = updates.Releases('trusted/tool', self.api).resolve(__version__)
        self.runtime = Runtime(self.repo)
        self.runtime.provider.api = self.api

    def stage(self):
        return self.runtime.adopt_backlog(__version__)

    def test_nameless_shape_preserved_and_independently_verified(self):
        project = {p: (self.root / p).read_bytes() for p in adoption.PROJECT}
        corpus = {str(p.relative_to(self.root)): p.read_bytes() for p in (self.root / 'backlog').rglob('*.md')}
        result = self.stage()
        expected = copy.deepcopy(self.config)
        expected.update(profile='github-backlog-v1', work=self.work)
        expected['authorities']['work'] = 'repository-backlog'
        expected['verification']['controller']['revision'] = 'd' * 40
        self.assertEqual(expected, self.repo.config())
        self.assertEqual(project, {p: (self.root / p).read_bytes() for p in project})
        self.assertEqual(corpus, {str(p.relative_to(self.root)): p.read_bytes() for p in (self.root / 'backlog').rglob('*.md')})
        self.assertEqual(BACKLOG_ENTRY, (self.root / updates.RUNTIME_ENTRY).read_text())
        self.assertNotIn('.harness/AGENT.md', result['changes'])
        self.assertEqual('GENESIS', self.runtime.state()['lifecycle'])
        self.assertIsNone(self.runtime.state()['substrate'])
        self.assertFalse(result['activated'])
        self.assertTrue(self.repo.local()['installed'])
        with patch.object(self.runtime.provider, 'list_work', return_value=[]), patch.object(self.runtime.provider, 'observe', return_value={'source': 'test-fixture', 'errors': ['private-plan gap']}):
            self.assertIn(updates.RUNTIME_ENTRY, self.runtime.entry()['instruction_paths'])
        updates.validate_candidate(self.repo, self.base, self.api)
        observed = local_corpus(self.repo, self.base, self.work)
        self.assertEqual('alice', authorize(observed, self.work, 'task-20', 'alice')['actor'])
        with patch.dict('os.environ', {'PROJECT_MODE': 'preserved'}):
            git(self.root, 'add', '.')
            git(self.root, 'commit', '-m', 'staged adoption candidate')
            self.assertTrue(self.runtime.verify('HEAD', self.base)['passed'])
        with patch.object(self.runtime.provider, 'observe', return_value={'source': 'test-fixture', 'errors': ['private plan cannot enforce'], 'fingerprint': 'gap'}):
            self.assertFalse(self.runtime.doctor()['closure'])
            with self.assertRaisesRegex(ValueError, 'live complete closure'):
                self.runtime.activate()

    def test_repeat_staging_and_committed_repeat_are_idempotent(self):
        first = self.stage()
        state = {p: (self.root / p).read_bytes() for p in first['changes']}
        self.assertEqual(first, self.stage())
        self.assertEqual(state, {p: (self.root / p).read_bytes() for p in state})
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'adopt')
        self.assertEqual({}, self.stage()['changes'])
        self.assertEqual(state, {p: (self.root / p).read_bytes() for p in state})

    def test_every_write_failure_restores_exact_bytes_and_stays_unactivated(self):
        proposal = adoption.proposal(self.repo, __version__, self.api)
        original = Path.write_text
        for fail_at in range(1, len(proposal['changes']) + 1):
            before = {p: (self.root / p).read_bytes() if (self.root / p).exists() else None for p in proposal['changes']}
            count = 0
            def failing(path, *args, **kwargs):
                nonlocal count
                count += 1
                if count == fail_at:
                    raise OSError('simulated write failure')
                return original(path, *args, **kwargs)
            with patch.object(Path, 'write_text', failing), self.assertRaises(OSError):
                self.stage()
            self.assertEqual(before, {p: (self.root / p).read_bytes() if (self.root / p).exists() else None for p in before})
            self.assertIsNone(self.runtime.state()['substrate'])

    def test_ownership_configuration_drift_and_unrelated_edits_stop(self):
        for path in ['AGENTS.md', '.harness/AGENT.md', '.harness/github-workflow.yml.template', '.harness/config.json', 'file.txt']:
            original = (self.root / path).read_bytes()
            (self.root / path).write_bytes(original + b'Unexpected change\n')
            with self.assertRaises(ValueError):
                self.stage()
            (self.root / path).write_bytes(original)
        self.assertFalse((self.root / updates.INSTALLATION).exists())

    def test_candidate_rejects_changed_preserved_bytes_config_and_ownership(self):
        self.stage()
        for path in ['AGENTS.md', '.harness/AGENT.md', updates.RUNTIME_ENTRY, updates.ADOPTION]:
            original = (self.root / path).read_bytes()
            (self.root / path).write_bytes(original + b'Changed\n')
            with self.assertRaises(ValueError):
                updates.validate_candidate(self.repo, self.base, self.api)
            (self.root / path).write_bytes(original)
        original = (self.root / '.harness/config.json').read_text()
        config = self.repo.config()
        for modify in (lambda c: c['verification'].update(commands=[['echo', 'forged']]),
                       lambda c: c['authorities'].update(work='github-issues'),
                       lambda c: c.update(target='main')):
            altered = copy.deepcopy(config)
            modify(altered)
            (self.root / '.harness/config.json').write_text(json_text(altered))
            with self.assertRaises(ValueError):
                updates.validate_candidate(self.repo, self.base, self.api)
        (self.root / '.harness/config.json').write_text(original)

    def test_ambiguous_declarations_existing_metadata_and_unknown_actors_reject(self):
        baseline = adoption.baseline_reader(self.repo, self.base)
        declaration = json.loads(baseline(updates.ADOPTION))
        for mutate in (lambda d: d.update(schema=99), lambda d: d['generated_artifacts'].clear(),
                       lambda d: d['project_artifacts'].pop('AGENTS.md'),
                       lambda d: d['work']['actors'].update({'CODEX:SESSION-20': 'bob'})):
            data = copy.deepcopy(declaration)
            mutate(data)
            def read(path):
                return json_text(data) if path == updates.ADOPTION else baseline(path)
            with self.assertRaises(ValueError):
                adoption.plan(self.config, self.release, read)
        for path in (updates.INSTALLATION, updates.REQUEST, updates.RUNTIME_ENTRY):
            with self.assertRaises(ValueError):
                adoption.declaration(self.config, self.work, lambda p: '{}' if p == path else baseline(p))
        wrong = copy.deepcopy(self.work)
        wrong['actors'] = {'codex:different-session': 'alice'}
        with self.assertRaises(ValueError):
            authorize(local_corpus(self.repo, self.base, wrong), wrong, 'task-20', 'alice')

    def test_unknown_release_protocol_mutable_revision_and_untrusted_source_reject(self):
        for modify in (lambda r: r['manifest'].update(schema=1), lambda r: r['manifest'].update(migrations=[]),
                       lambda r: r.update(repository='evil/tool'), lambda r: r.update(revision='main')):
            release = copy.deepcopy(self.release)
            modify(release)
            with self.assertRaises(ValueError):
                adoption.plan(self.config, release, adoption.baseline_reader(self.repo, self.base))
        self.runtime.save_state({'lifecycle': 'MANAGED', 'substrate': 'prior', 'events': [], 'workspaces': {}})
        with self.assertRaisesRegex(ValueError, 'Genesis'):
            self.stage()

    def test_missing_or_conflicting_corpus_stops_before_writes(self):
        task = self.root / 'backlog/tasks/task-20 - Support migration.md'
        task.write_text(task.read_text().replace('dependencies: [task-19]', 'dependencies: [task-99]'))
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'invalid corpus')
        with self.assertRaises(ValueError):
            self.stage()
        self.assertFalse((self.root / updates.INSTALLATION).exists())

    def test_followup_release_preserves_project_ownership_and_backlog_configuration(self):
        self.stage()
        config = self.repo.config()
        identity = updates.installed(self.repo)
        self.api.add('0.3.1', 'e' * 40, previous=(__version__,))
        next_release = updates.Releases('trusted/tool', self.api).resolve('0.3.1')
        result = updates.plan(config, identity, next_release, updates.read_files(self.repo))
        self.assertNotIn('.harness/AGENT.md', result['changes'])
        self.assertNotIn('AGENTS.md', result['changes'])
        updates.apply(self.repo, result['changes'])
        expected = copy.deepcopy(config)
        expected['verification']['controller']['revision'] = 'e' * 40
        self.assertEqual(expected, self.repo.config())
        self.assertEqual(identity['project_artifacts'], updates.installed(self.repo)['project_artifacts'])

    def test_independent_migration_check_rejects_line_ending_only_project_edit(self):
        self.stage()
        path = self.root / '.harness/AGENT.md'
        original = path.read_bytes()
        path.write_bytes(original.replace(b'\r\n', b'\n'))
        with self.assertRaisesRegex(ValueError, 'preserve'):
            updates.validate_candidate(self.repo, self.base, self.api)
        path.write_bytes(original)
        updates.validate_candidate(self.repo, self.base, self.api)

    def test_project_owned_instructions_remain_editable_through_normal_control_review(self):
        from openharness.ci import control_change
        self.stage()
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'adopted baseline')
        base = self.repo.revision('HEAD')
        old_controls = self.repo.local()['controls']
        path = self.root / '.harness/AGENT.md'
        path.write_bytes(path.read_bytes() + b'Project-owned reviewed customization.\n')
        self.assertNotEqual(old_controls, self.repo.local()['controls'])
        self.assertTrue(control_change(self.repo.config(), ['.harness/AGENT.md']))
        updates.validate_candidate(self.repo, base, self.api)
        updates.installation_observation(self.repo)
        self.api.add('0.3.1', 'e' * 40, previous=(__version__,))
        release = updates.Releases('trusted/tool', self.api).resolve('0.3.1')
        proposal = updates.plan(self.repo.config(), updates.installed(self.repo), release, updates.read_files(self.repo))
        self.assertNotIn('.harness/AGENT.md', proposal['changes'])

    def test_native_task_preset_and_real_cli_stage(self):
        import contextlib
        import io
        from types import SimpleNamespace
        from openharness.cli import main
        preset = updates.renovate_config('trusted/tool', task='TASK-20')
        rule = preset['packageRules'][0]
        self.assertEqual('codex/backlog-task-20-', rule['branchPrefix'])
        self.assertIn('Work-Item: task-20', rule['prBodyNotes'])
        self.assertFalse(rule['automerge'])
        output = io.StringIO()
        with patch('openharness.runtime.GitHub', return_value=SimpleNamespace(api=self.api)), contextlib.redirect_stdout(output):
            self.assertEqual(0, main(['--repo', str(self.root), 'upgrade', '--release', __version__, '--adopt-backlog']))
        self.assertFalse(json.loads(output.getvalue())['activated'])
        updates.validate_candidate(self.repo, self.base, self.api)

    def test_custom_compiler_artifact_is_not_adopted_as_overwrite_permission(self):
        baseline = adoption.baseline_reader(self.repo, self.base)
        with self.assertRaisesRegex(ValueError, 'Custom compiler artifact'):
            adoption.declaration(self.config, self.work, lambda path: '# custom workflow' if path == '.harness/github-workflow.yml.template' else baseline(path))

    def test_old_manifest_resolves_without_claiming_backlog_support(self):
        data = updates.manifest(['0.2.0'])
        data.update(schema=1, version='0.2.1')
        data.pop('profiles')
        data.pop('migrations')
        updates.validate_manifest(data, '0.2.1')
        release = {**self.release, 'version': '0.2.1', 'manifest': data}
        with self.assertRaisesRegex(ValueError, 'support'):
            updates.release_artifacts(release, 'github-backlog-v1')


if __name__ == '__main__':
    unittest.main()
