import unittest
from unittest.mock import patch

from openharness.ci import candidate_context, docker_arguments, workflow_text, event_policy, publish
from openharness.model import default_config, digest


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

    def test_publisher_rejects_old_head_and_accepts_only_matching_identity(self):
        event = {'pull_request': {'number': 7}}
        def api(path):
            if '/pulls/' in path:
                return self.pull
            if '/issues/' in path:
                return {'state': 'open', 'number': 3}
            if '/branches/' in path:
                return {'commit': {'sha': 'b' * 40}}
            return {'tree': {'sha': 'd' * 40}}
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
