import copy
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from openharness.ci import candidate_context, docker_arguments, workflow_text, event_policy, publish, control_change, control_authorized, check_candidate
from openharness.model import default_config, digest
from tests.helpers import git, make_repo


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.config = default_config('owner/repo', 'main')
        self.pull = {'number': 7, 'state': 'open', 'draft': False, 'body': 'Work-Item: #3', 'head': {'sha': 'a' * 40, 'ref': 'codex/3-fix'}, 'base': {'sha': 'b' * 40, 'ref': 'main'}, 'merge_commit_sha': 'c' * 40}

    def test_valid_issue_bound_candidate_accepted(self):
        result = candidate_context(self.config, self.pull, {'state': 'open', 'number': 3})
        self.assertEqual('a' * 40, result['head'])
        self.assertEqual(3, result['issue'])

    def test_no_legal_work_or_wrong_branch_rejected(self):
        with self.assertRaises(ValueError):
            candidate_context(self.config, self.pull, {'state': 'closed', 'number': 3})
        self.pull['head']['ref'] = 'codex/4-other'
        with self.assertRaises(ValueError):
            candidate_context(self.config, self.pull, {'state': 'open', 'number': 3})

    def test_candidate_must_have_exactly_one_work_authority(self):
        self.pull['body'] += '\nWork-Item: #4'
        with self.assertRaises(ValueError):
            candidate_context(self.config, self.pull, {'state': 'open', 'number': 3})

    def test_sandbox_has_no_host_write_network_or_token_environment(self):
        command = docker_arguments('/candidate-source', 'python@sha256:' + 'a' * 64, ['python', '--version'])
        self.assertIn('--read-only', command)
        self.assertIn('none', command)
        self.assertIn('no-new-privileges', command)
        self.assertTrue(any('readonly' in v for v in command))
        values = [command[i + 1] for i, value in enumerate(command) if value == '--env']
        self.assertFalse(any('TOKEN' in value or 'SECRET' in value or 'GITHUB' in value for value in values))
        self.assertNotIn('--privileged', command)

    def test_unpinned_image_and_host_mount_injection_rejected(self):
        with self.assertRaises(ValueError):
            docker_arguments('/candidate', 'python:latest', ['python'])
        with self.assertRaises(ValueError):
            docker_arguments('/candidate,src=/etc', 'python@sha256:' + 'a' * 64, ['python'])
        with self.assertRaises(ValueError):
            docker_arguments('/candidate', 'python@sha256:' + 'a' * 64, ['python'], {'GH_TOKEN': 'forged'})

    def test_policy_applies_all_workflows_and_blocks_candidate_events(self):
        policy = event_policy()
        self.assertEqual('active', policy['enforcement'])
        self.assertEqual({}, policy['conditions'])
        self.assertEqual(['pull_request_target'], policy['rules'][0]['parameters']['allowed_events'])

    def test_harness_self_upgrade_and_acceptance_sources_require_control_authority(self):
        self.config['verification']['controller'] = {'repository': 'owner/repo', 'revision': 'a' * 40}
        for path in ('openharness/native.py', 'openharness/ci.py', 'tests/test_ci.py', 'pyproject.toml', 'docs/contracts/frozen.md'):
            self.assertTrue(control_change(self.config, [path]))
        self.assertFalse(control_change(self.config, ['docs/results.md']))
        self.config['verification']['controller']['repository'] = 'external/tool'
        self.assertFalse(control_change(self.config, ['tests/test_product.py']))

    def test_control_approval_is_exact_native_owner_head_and_base(self):
        context = {'head': 'a' * 40, 'base': 'b' * 40, 'issue': 3}
        comment = {'user': {'login': 'other'}, 'body': 'OpenHarness-Control-Approval: ' + 'a' * 40 + ' ' + 'b' * 40}
        self.assertFalse(control_authorized(self.config, context, lambda _: [comment]))
        comment['user']['login'] = 'owner'
        self.assertTrue(control_authorized(self.config, context, lambda _: [comment]))
        context['base'] = 'c' * 40
        self.assertFalse(control_authorized(self.config, context, lambda _: [comment]))

    def test_control_directory_replacement_is_protected(self):
        self.config['verification']['controller'] = {'repository': 'owner/repo', 'revision': 'a' * 40}
        for path in ('.github', '.harness', 'openharness', 'tests', 'docs/contracts'):
            with self.subTest(path=path):
                self.assertTrue(control_change(self.config, [path]))

    def test_real_git_unicode_control_change_requires_approval_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = make_repo(directory)
            git(root, 'config', 'core.quotePath', 'true')
            base = git(root, 'rev-parse', 'HEAD')
            baseline = root / 'baseline'
            git(root, 'worktree', 'add', '--detach', str(baseline), base)
            path = root / '.github/workflows/测试.yml'
            path.parent.mkdir(parents=True)
            path.write_text('# comment\n', encoding='utf-8')
            git(root, 'add', '.github')
            git(root, 'commit', '-m', 'unicode protected path')
            context = {'head': git(root, 'rev-parse', 'HEAD'), 'base': base, 'pr': 7, 'issue': 3, 'merge': None}
            with patch('openharness.ci.current_context', return_value=context), \
                    patch('openharness.ci.control_authorized', return_value=False), \
                    patch('openharness.updates.validate_candidate'), \
                    patch('openharness.ci.subprocess.run', wraps=subprocess.run) as run:
                with self.assertRaisesRegex(ValueError, 'Protected control change'):
                    check_candidate(self.config, baseline, root, {'pull_request': {'number': 7}})
                self.assertFalse(any(call.args[0][0] == 'docker' for call in run.call_args_list))
            git(root, 'worktree', 'remove', '--force', str(baseline))

    def publisher_api(self, pulls, merge=None):
        snapshots = iter(pulls)
        def api(path):
            if '/pulls/' in path:
                return copy.deepcopy(next(snapshots))
            if '/branches/' in path:
                return {'commit': {'sha': 'b' * 40}}
            if '/issues/' in path:
                return {'state': 'open', 'number': 3}
            sha = path.rsplit('/', 1)[1]
            if sha == 'c' * 40:
                return merge or {'sha': sha, 'tree': {'sha': 'd' * 40}, 'parents': [{'sha': 'b' * 40}, {'sha': 'a' * 40}]}
            return {'sha': sha, 'tree': {'sha': 'd' * 40}}
        return api

    def test_publication_never_transfers_success_between_pr_snapshots(self):
        updated = copy.deepcopy(self.pull)
        updated['head']['sha'], updated['merge_commit_sha'] = 'e' * 40, 'f' * 40
        context = candidate_context(self.config, updated, {'state': 'open', 'number': 3})
        identity = digest({'context': context, 'tree': 'd' * 40, 'verification': self.config['verification']})
        writes = []
        with patch.dict('os.environ', {'GITHUB_RUN_ID': '123'}):
            result = publish(self.config, {'pull_request': {'number': 7}}, 'success', 'e' * 40, 'b' * 40,
                             'd' * 40, identity, self.publisher_api([self.pull, updated]), lambda *args: writes.append(args))
        self.assertEqual('failure', result['state'])
        self.assertTrue(all(call[2]['state'] == 'failure' for call in writes))

    def test_publication_rejects_drift_while_reading_git_objects(self):
        changed = copy.deepcopy(self.pull)
        changed['head']['sha'] = 'e' * 40
        context = candidate_context(self.config, self.pull, {'state': 'open', 'number': 3})
        identity = digest({'context': context, 'tree': 'd' * 40, 'verification': self.config['verification']})
        writes = []
        with patch.dict('os.environ', {'GITHUB_RUN_ID': '123'}):
            result = publish(self.config, {'pull_request': {'number': 7}}, 'success', 'a' * 40, 'b' * 40,
                             'd' * 40, identity, self.publisher_api([self.pull, changed]), lambda *args: writes.append(args))
        self.assertEqual('failure', result['state'])
        self.assertTrue(all(call[2]['state'] == 'failure' for call in writes))

    def test_base_work_and_merge_drift_cannot_publish_success(self):
        context = candidate_context(self.config, self.pull, {'state': 'open', 'number': 3})
        identity = digest({'context': context, 'tree': 'd' * 40, 'verification': self.config['verification']})
        for drift in ('base', 'work', 'merge'):
            with self.subTest(drift=drift), patch.dict('os.environ', {'GITHUB_RUN_ID': '123'}):
                updated = copy.deepcopy(self.pull)
                if drift == 'merge':
                    updated['merge_commit_sha'] = 'f' * 40
                reader = self.publisher_api([self.pull, updated])
                reads, writes = {}, []
                def api(path):
                    reads[path] = reads.get(path, 0) + 1
                    if drift == 'base' and '/branches/' in path and reads[path] == 2:
                        return {'commit': {'sha': 'e' * 40}}
                    if drift == 'work' and '/issues/' in path and reads[path] == 2:
                        return {'state': 'closed', 'number': 3}
                    return reader(path)
                if drift == 'merge':
                    result = publish(self.config, {'pull_request': {'number': 7}}, 'success', 'a' * 40, 'b' * 40,
                                     'd' * 40, identity, api, lambda *args: writes.append(args))
                    self.assertEqual('failure', result['state'])
                else:
                    with self.assertRaises(ValueError):
                        publish(self.config, {'pull_request': {'number': 7}}, 'success', 'a' * 40, 'b' * 40,
                                'd' * 40, identity, api, lambda *args: writes.append(args))
                self.assertFalse(any(call[2]['state'] == 'success' for call in writes))

    def test_ref_movement_between_writes_never_retargets_verified_objects(self):
        context = candidate_context(self.config, self.pull, {'state': 'open', 'number': 3})
        identity = digest({'context': context, 'tree': 'd' * 40, 'verification': self.config['verification']})
        writes = []
        def write(*args):
            self.pull['head']['sha'], self.pull['merge_commit_sha'] = 'e' * 40, 'f' * 40
            writes.append(args)
        with patch.dict('os.environ', {'GITHUB_RUN_ID': '123'}):
            result = publish(self.config, {'pull_request': {'number': 7}}, 'success', 'a' * 40, 'b' * 40,
                             'd' * 40, identity, self.publisher_api([self.pull] * 2), write)
        self.assertEqual('success', result['state'])
        self.assertEqual(['repos/owner/repo/statuses/' + sha for sha in ('a' * 40, 'c' * 40)],
                         [call[0] for call in writes])

    def test_no_merge_subject_and_missing_failed_outputs_are_supported(self):
        self.pull['merge_commit_sha'] = None
        context = candidate_context(self.config, self.pull, {'state': 'open', 'number': 3})
        identity = digest({'context': context, 'tree': 'd' * 40, 'verification': self.config['verification']})
        writes = []
        with patch.dict('os.environ', {'GITHUB_RUN_ID': '123'}):
            valid = publish(self.config, {'pull_request': {'number': 7}}, 'success', 'a' * 40, 'b' * 40,
                            'd' * 40, identity, self.publisher_api([self.pull] * 2), lambda *args: writes.append(args))
            failed = publish(self.config, {'pull_request': {'number': 7}}, 'failure', None, None, None, None,
                             self.publisher_api([self.pull]), lambda *args: writes.append(args))
        self.assertEqual('success', valid['state'])
        self.assertEqual(['a' * 40], valid['subjects'])
        self.assertEqual('failure', failed['state'])
        self.assertEqual(2, len(writes))

    def test_unverified_merge_objects_never_receive_success(self):
        context = candidate_context(self.config, self.pull, {'state': 'open', 'number': 3})
        identity = digest({'context': context, 'tree': 'd' * 40, 'verification': self.config['verification']})
        for merge in ({'sha': 'f' * 40, 'tree': {'sha': 'd' * 40}, 'parents': [{'sha': 'b' * 40}, {'sha': 'a' * 40}]},
                      {'sha': 'c' * 40, 'tree': {'sha': 'f' * 40}, 'parents': [{'sha': 'b' * 40}, {'sha': 'a' * 40}]},
                      {'sha': 'c' * 40, 'tree': {'sha': 'd' * 40}, 'parents': [{'sha': 'e' * 40}, {'sha': 'a' * 40}]}):
            with self.subTest(merge=merge), patch.dict('os.environ', {'GITHUB_RUN_ID': '123'}):
                writes = []
                result = publish(self.config, {'pull_request': {'number': 7}}, 'success', 'a' * 40, 'b' * 40,
                                 'd' * 40, identity, self.publisher_api([self.pull] * 3, merge=merge), lambda *args: writes.append(args))
                self.assertEqual('failure', result['state'])
                self.assertTrue(all(call[2]['state'] == 'failure' for call in writes))

    def test_publisher_rejects_old_head_and_accepts_only_matching_identity(self):
        event = {'pull_request': {'number': 7}}
        def api(path):
            if '/pulls/' in path:
                return self.pull
            if '/issues/' in path:
                return {'state': 'open', 'number': 3}
            if '/branches/' in path:
                return {'commit': {'sha': 'b' * 40}}
            sha = path.rsplit('/', 1)[1]
            return {'sha': sha, 'tree': {'sha': 'd' * 40}, 'parents': [{'sha': 'b' * 40}, {'sha': 'a' * 40}]}
        context = candidate_context(self.config, self.pull, {'state': 'open', 'number': 3})
        identity = digest({'context': context, 'tree': 'd' * 40, 'verification': self.config['verification']})
        writes = []
        with patch.dict('os.environ', {'GITHUB_RUN_ID': '123'}):
            valid = publish(self.config, event, 'success', 'a' * 40, 'b' * 40, 'd' * 40, identity, api, lambda *v: writes.append(v))
            self.assertEqual('success', valid['state'])
            stale = publish(self.config, event, 'success', 'f' * 40, 'b' * 40, 'd' * 40, identity, api, lambda *v: writes.append(v))
            self.assertEqual('failure', stale['state'])
            failed = publish(self.config, event, 'failure', 'a' * 40, 'b' * 40, 'd' * 40, identity, api, lambda *v: writes.append(v))
            self.assertEqual('failure', failed['state'])
        self.assertTrue(writes)


if __name__ == '__main__':
    unittest.main()
