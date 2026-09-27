import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from openharness.cli import main
from openharness.model import digest, validate_config
from openharness.provider import GitHub
from openharness.repository import Repository, bootstrap, json_text
from openharness.runtime import Runtime
from tests.helpers import git, make_repo
from tests.test_backlog import settings, task
from tests.test_backlog_runtime import CanonicalFixture


class CooperativeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = make_repo(self.temp.name)
        self.repo = Repository(self.root)

    def install(self, backlog=False):
        (self.root / 'AGENTS.md').write_text('Keep native Backlog, change/task-N and project CI.\n')
        (self.root / '.harness').mkdir()
        (self.root / '.harness/AGENT.md').write_text('Project-owned Backlog boundary.\n')
        workflow = self.root / '.github/workflows/ci.yml'
        workflow.parent.mkdir(parents=True)
        workflow.write_text('name: Existing CI\non: pull_request\n')
        bootstrap(self.repo, 'owner/repo', 'main', mode='cooperative',
                  profile='github-backlog-v1' if backlog else None,
                  work=settings() if backlog else None)
        config = self.repo.config()
        config['verification'].update(commands=[[sys.executable, '-c', 'print("acceptance")']],
                                      required_check='Existing acceptance', expected_app_id=15368,
                                      workflow='.github/workflows/ci.yml')
        (self.root / '.harness/config.json').write_text(json_text(config))
        if backlog:
            folder = self.root / 'backlog/tasks'
            folder.mkdir(parents=True)
            (folder / 'task-1 - Example.md').write_bytes(task())
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'reviewed project configuration')
        return config

    def test_cli_default_is_light_and_does_not_install_a_workflow(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(0, main(['--repo', str(self.root), 'bootstrap']))
        self.assertEqual('cooperative', self.repo.config()['mode'])
        self.assertFalse((self.root / '.harness/github-workflow.yml.template').exists())

    def test_repeat_preserves_project_owned_files_and_config(self):
        config = self.install(True)
        paths = ['AGENTS.md', '.harness/AGENT.md', '.github/workflows/ci.yml',
                 'backlog/tasks/task-1 - Example.md', '.harness/config.json']
        before = {p: (self.root / p).read_bytes() for p in paths}
        self.assertEqual([], bootstrap(self.repo, 'owner/repo', 'main', mode='cooperative')['changed'])
        self.assertEqual(before, {p: (self.root / p).read_bytes() for p in paths})
        self.assertEqual(config, self.repo.config())
        with self.assertRaisesRegex(ValueError, 'reconfigure'):
            bootstrap(self.repo, 'owner/repo', 'main', mode='strict')

    def test_entry_is_small_local_orientation_not_cached_authority(self):
        self.install(True)
        provider = GitHub(lambda path: self.fail('daily entry must make zero API calls'))
        entry = Runtime(self.repo, provider).entry()
        self.assertNotIn('doctor', entry)
        self.assertNotIn('legal_work', entry)
        self.assertEqual('not-observed', entry['assessment'])
        self.assertLess(len(json.dumps(entry)), 1800)

    def test_backlog_core_path_without_rules_or_activation(self):
        self.install(True)
        provider = CanonicalFixture(self.repo)
        runtime = Runtime(self.repo, provider)
        with patch.object(runtime, 'doctor', side_effect=AssertionError('no full Doctor')):
            provider.target = lambda config: self.repo.revision('main')
            binding = runtime.workspace('task-1', 'fix')
        work = Runtime(Repository(binding['path']), provider)
        provider.target = lambda config: self.repo.revision('main')
        self.assertTrue(work.verify('HEAD', binding['base'])['passed'])
        with patch.object(work, 'doctor', side_effect=AssertionError('no full Doctor')):
            self.assertTrue(work.preflight()['allowed'])
        path = self.root / 'backlog/tasks/task-1 - Example.md'
        path.write_bytes(task(assignee='["@bob"]'))
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'canonical assignment changed')
        with self.assertRaises(ValueError):
            work.preflight()

    def test_existing_project_branch_can_be_bound_without_renaming(self):
        self.install(True)
        path = Path(self.temp.name) / 'existing'
        git(self.root, 'worktree', 'add', '-b', 'change/task-1', str(path), 'main')
        repo = Repository(path)
        provider = CanonicalFixture(self.repo)
        provider.target = lambda config: self.repo.revision('main')
        binding = Runtime(repo, provider).workspace('TASK-1', 'existing', bind=True)
        self.assertEqual('change/task-1', binding['branch'])
        self.assertEqual('TASK-1', binding['project_work_item'])
        self.assertTrue(Runtime(repo, provider).preflight()['allowed'])

    def test_strict_does_not_fall_back_on_permissions_or_accept_bind(self):
        bootstrap(self.repo, 'owner/repo', 'main')
        self.assertNotIn('mode', self.repo.config())
        runtime = Runtime(self.repo, GitHub(lambda path: (_ for _ in ()).throw(ValueError('403'))))
        with self.assertRaises(ValueError):
            runtime.workspace(1, 'fix', bind=True)
        with self.assertRaises(ValueError):
            runtime.workspace(1, 'fix')

    def test_activation_remains_explicit_strict_only(self):
        self.install()
        runtime = Runtime(self.repo, GitHub(lambda path: self.fail('no activation probe')))
        with self.assertRaisesRegex(ValueError, 'strict'):
            runtime.activate()
        self.assertEqual('GENESIS', runtime.state()['lifecycle'])

    def merge_fixture(self):
        config = self.install()
        base = self.repo.revision('HEAD')
        provider = GitHub()
        provider.target = lambda config: base
        provider.work = lambda config, issue: {'number': 1, 'state': 'open'}
        binding = Runtime(self.repo, provider).workspace(1, 'fix')
        repo = Repository(binding['path'])
        (repo.root / 'file.txt').write_text('changed\n')
        git(repo.root, 'add', '.')
        git(repo.root, 'commit', '-m', 'candidate')
        head = repo.revision('HEAD')
        pull = {'number': 7, 'state': 'open', 'draft': False, 'body': 'Work-Item: #1',
                'head': {'ref': binding['branch'], 'sha': head, 'repo': {'full_name': 'owner/repo'}},
                'base': {'ref': 'main', 'sha': base}, 'user': {'login': 'alice'}}
        tree = repo.git('rev-parse', 'HEAD^{tree}')
        commit = repo.git('commit-tree', tree, '-p', base, '-p', head, input_text='merge\n')
        check = {'id': 11, 'name': 'Existing acceptance', 'head_sha': head,
                 'status': 'completed', 'conclusion': 'success', 'app': {'id': 15368},
                 'check_suite': {'id': 12}}
        run = {'id': 13, 'check_suite_id': 12, 'head_sha': head,
               'path': '.github/workflows/ci.yml', 'event': 'pull_request',
               'status': 'completed', 'conclusion': 'success', 'run_attempt': 1,
               'pull_requests': [{'number': 7}]}
        data = {'pull': pull, 'check': check, 'run': run, 'commit': commit, 'merged': False}

        def api(path):
            if path.endswith('/pulls/7'):
                row = copy.deepcopy(data['pull'])
                if data['merged']:
                    row.update(state='closed', merged=True, merge_commit_sha=data['commit'])
                return row
            if '/check-runs?' in path:
                return {'total_count': 1, 'check_runs': [data['check']]}
            if '/actions/runs?' in path:
                return {'total_count': 1, 'workflow_runs': [data['run']]}
            if '/git/commits/' in path:
                return {'tree': {'sha': tree}, 'parents': [{'sha': base}, {'sha': head}]}
            raise AssertionError(path)

        def merge(path, method, payload):
            self.assertEqual({'sha': head, 'merge_method': 'merge'}, payload)
            data['merged'] = True
            provider.target = lambda config: data['commit']
            return {'merged': True, 'sha': data['commit']}

        provider.api = api
        return Runtime(repo, provider), data, merge

    def test_exact_candidate_merge_reobserves_and_records_without_activation(self):
        runtime, data, merge = self.merge_fixture()
        with patch('openharness.provider.gh_write', side_effect=merge):
            result = runtime.integrate(7)
        self.assertEqual(data['commit'], result['sha'])
        self.assertFalse(result['closure'])
        self.assertFalse(result['server_enforced'])
        self.assertEqual('GENESIS', runtime.state()['lifecycle'])
        self.assertTrue(runtime.release()['worktree_preserved'])

    def test_wrong_stale_pending_ambiguous_and_untrusted_ci_never_merge(self):
        runtime, data, merge = self.merge_fixture()
        good = copy.deepcopy(data['check'])
        bad = [{'head_sha': 'a' * 40}, {'conclusion': 'failure'}, {'status': 'in_progress'},
               {'app': {'id': 999}}, {'check_suite': {'id': 999}}]
        for mutation in bad:
            with self.subTest(mutation=mutation):
                data['check'] = {**good, **mutation}
                with patch('openharness.provider.gh_write') as write, self.assertRaises(ValueError):
                    runtime.integrate(7)
                write.assert_not_called()
        data['check'] = good
        for mutation in [{'path': '.github/workflows/spoof.yml'}, {'head_sha': 'b' * 40},
                         {'pull_requests': [{'number': 8}]}, {'conclusion': 'cancelled'}]:
            original = copy.deepcopy(data['run'])
            data['run'].update(mutation)
            with patch('openharness.provider.gh_write') as write, self.assertRaises(ValueError):
                runtime.integrate(7)
            write.assert_not_called()
            data['run'] = original

    def test_changed_head_or_base_stops_before_merge(self):
        runtime, data, merge = self.merge_fixture()
        for field in ('head', 'base'):
            original = data['pull'][field]['sha']
            data['pull'][field]['sha'] = 'f' * 40
            with patch('openharness.provider.gh_write') as write, self.assertRaises(ValueError):
                runtime.integrate(7)
            write.assert_not_called()
            data['pull'][field]['sha'] = original

    def test_local_configuration_cannot_silently_downgrade_canonical_authority(self):
        runtime, data, merge = self.merge_fixture()
        config = runtime.repo.config()
        config['verification']['required_check'] = 'Spoof'
        (runtime.repo.root / '.harness/config.json').write_text(json_text(config))
        git(runtime.repo.root, 'add', '.')
        git(runtime.repo.root, 'commit', '-m', 'unreviewed configuration')
        with patch('openharness.provider.gh_write') as write, self.assertRaises(ValueError):
            runtime.integrate(7)
        write.assert_not_called()

    def test_existing_project_integrator_is_used_and_independently_observed(self):
        runtime, data, merge = self.merge_fixture()
        config = runtime.repo.config()
        config['integration_command'] = [sys.executable, 'tools/integrate_pr.py', '--pr', '{pr}', '--item', '{work_item}']
        # A reviewed project configuration at both canonical and candidate commits.
        for repo in (self.repo, runtime.repo):
            (repo.root / '.harness/config.json').write_text(json_text(config))
            git(repo.root, 'add', '.')
            git(repo.root, 'commit', '-m', 'project integration command')
        base = self.repo.revision('main')
        git(runtime.repo.root, 'merge', '--no-edit', 'main')
        head = runtime.repo.revision('HEAD')
        data['pull']['head']['sha'] = head
        data['pull']['base']['sha'] = base
        tree = runtime.repo.git('rev-parse', 'HEAD^{tree}')
        data['commit'] = runtime.repo.git('commit-tree', tree, '-p', base, '-p', head, input_text='merge\n')
        data['check']['head_sha'] = data['run']['head_sha'] = head
        original_api = runtime.provider.api
        runtime.provider.api = lambda path: ({'tree': {'sha': tree}, 'parents': [{'sha': base}, {'sha': head}]}
                                            if '/git/commits/' in path else original_api(path))
        runtime.provider.target = lambda config: base
        state = runtime.state()
        state['workspaces'][str(runtime.repo.root)]['config'] = digest(config)
        runtime.save_state(state)
        import subprocess
        real_run = subprocess.run
        def project(argv, **kwargs):
            if argv[0] == 'git':
                return real_run(argv, **kwargs)
            self.assertEqual([sys.executable, 'tools/integrate_pr.py', '--pr', '7', '--item', '1'], argv)
            self.assertEqual(runtime.repo.root, kwargs['cwd'])
            data['merged'] = True
            runtime.provider.target = lambda config: data['commit']
            from subprocess import CompletedProcess
            return CompletedProcess(argv, 0, 'project output', '')
        with patch('openharness.cooperative.subprocess.run', side_effect=project), patch('openharness.provider.gh_write') as write:
            result = runtime.integrate(7)
        write.assert_not_called()
        self.assertEqual(data['commit'], result['sha'])

    def test_strict_artifact_release_cannot_overwrite_cooperative_project_files(self):
        self.install(True)
        config = self.repo.config()
        config['verification']['controller'] = {'repository': 'owner/tool', 'revision': 'a' * 40}
        (self.root / '.harness/config.json').write_text(json_text(config))
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file() and '.git' not in p.parts}
        with self.assertRaisesRegex(ValueError, 'cooperative compatibility'):
            Runtime(self.repo).upgrade('0.3.0', enroll=True)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file() and '.git' not in p.parts})

    def test_backlog_reads_observed_git_commit_without_per_task_api_calls(self):
        self.install(True)
        calls = []
        def api(path):
            calls.append(path)
            if '/branches/main' in path:
                return {'commit': {'sha': self.repo.revision('main')}}
            if path == 'user':
                return {'login': 'alice'}
            self.fail('unexpected policy/task API request: ' + path)
        Runtime(self.repo, GitHub(api)).workspace('TASK-1', 'git-corpus')
        self.assertEqual(['repos/owner/repo/branches/main', 'user'], calls)

    def test_successful_verification_summary_keeps_full_evidence_out_of_daily_output(self):
        self.install()
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(0, main(['--repo', str(self.root), 'verify', '--head', 'HEAD', '--base', 'main']))
        result = json.loads(stream.getvalue())
        self.assertTrue(result['passed'])
        self.assertNotIn('stdout', result['checks'][0])
        full = Runtime(self.repo).evidence('HEAD', 'main')
        self.assertIn('acceptance', full['record']['checks'][0]['stdout'])

    def test_cooperative_doctor_retains_all_guarantees_and_open_gaps(self):
        from openharness.model import CATALOGUE
        self.install()
        provider = GitHub()
        provider.observe = lambda config: {'source': 'fixture', 'errors': ['rules: private capability unavailable']}
        report = Runtime(self.repo, provider).doctor()
        self.assertFalse(report['closure'])
        self.assertEqual(len(CATALOGUE), report['candidate_count'])
        self.assertEqual('OPEN GAP', next(g for g in report['guarantees'] if g['id'] == 'integration')['status'])

    def test_ci_pagination_and_duplicate_sources_fail_closed(self):
        runtime, data, merge = self.merge_fixture()
        original = runtime.provider.api
        for duplicate in (False, True):
            def incomplete(path):
                result = original(path)
                if '/check-runs?' in path:
                    if duplicate:
                        result['check_runs'].append(copy.deepcopy(data['check']))
                        result['total_count'] = 2
                    else:
                        result['total_count'] = 101
                return result
            runtime.provider.api = incomplete
            with patch('openharness.provider.gh_write') as write, self.assertRaises(ValueError):
                runtime.integrate(7)
            write.assert_not_called()

    def test_post_merge_base_race_is_an_incident_not_a_false_success(self):
        runtime, data, merge = self.merge_fixture()
        api = runtime.provider.api
        def raced(path):
            result = api(path)
            if '/git/commits/' in path:
                result['parents'][0]['sha'] = 'e' * 40
            return result
        runtime.provider.api = raced
        with patch('openharness.provider.gh_write', side_effect=merge), self.assertRaisesRegex(ValueError, 'already merged'):
            runtime.integrate(7)
        self.assertTrue(data['merged'])
        self.assertEqual('UNPROVEN', runtime.state()['lifecycle'])
        self.assertNotIn('integrated', runtime.state()['workspaces'][str(runtime.repo.root)])
        self.assertIn('invalidated', runtime.state()['workspaces'][str(runtime.repo.root)])
        with self.assertRaisesRegex(ValueError, 'current bound'):
            runtime.preflight()


if __name__ == '__main__':
    unittest.main()
