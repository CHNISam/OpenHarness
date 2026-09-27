import base64
import copy
import json
import unittest

from openharness.ci import WORKFLOW_PATH, workflow_text
from openharness.model import default_config
from openharness.native import observe_proof


class ProofTests(unittest.TestCase):
    def setUp(self):
        self.config = default_config('owner/repo', 'main')
        self.config['verification']['controller'] = {'repository': 'owner/repo', 'revision': 'a' * 40}
        self.observation = {'gate': True, 'trusted_controller': True, 'fingerprint': 'policy', 'target_sha': 'b' * 40}
        self.proof = {'schema': 1, 'repository': 'owner/repo', 'policy': 'policy', 'cases': {
            'valid': {'pr': 1, 'head': '1' * 40},
            'invalid': {'pr': 2, 'head': '2' * 40, 'rule_suite_id': 2},
            'source-spoof': {'pr': 3, 'head': '3' * 40, 'rule_suite_id': 3, 'blocked_run': 9},
            'direct-update': {'head': '4' * 40, 'rule_suite_id': 4}}}
        self.run_event = 'pull_request_target'
        self.merged_tree = 'tree'
        self.denial = 'fail'

    def api(self, path):
        if '/actions/runs/9/jobs' in path:
            return {'total_count': 0, 'jobs': []}
        if '/actions/runs/' in path and '/jobs?' in path:
            return {'total_count': 1, 'jobs': [{'id': 8, 'name': 'publish', 'status': 'completed', 'conclusion': 'success'}]}
        if path.endswith('/actions/runs/9'):
            return {'id': 9, 'head_sha': '3' * 40, 'event': 'push', 'conclusion': 'startup_failure'}
        if '/contents/' in path:
            value = self.proof if 'deployment-proof' in path else self.config
            content = workflow_text() if WORKFLOW_PATH in path else json.dumps(value)
            return {'type': 'file', 'encoding': 'base64', 'content': base64.b64encode(content.encode()).decode()}
        if '/pulls/' in path:
            number = int(path.rsplit('/', 1)[1])
            return {'number': number, 'head': {'sha': str(number) * 40}, 'base': {'ref': 'main'}, 'merged': number == 1, 'merge_commit_sha': 'a' * 40}
        if '/statuses?' in path:
            number = int(path.split('/commits/')[1][0])
            return [{'context': self.config['verification']['required_check'], 'state': 'success' if number == 1 else 'failure', 'creator': {'login': 'github-actions[bot]'}, 'target_url': f'https://github.com/owner/repo/actions/runs/{number}'}]
        if '/actions/runs/' in path:
            number = int(path.rsplit('/', 1)[1])
            return {'id': number, 'event': self.run_event, 'path': WORKFLOW_PATH, 'status': 'completed', 'head_sha': str(number) * 40, 'pull_requests': []}
        if '/git/commits/' in path:
            return {'tree': {'sha': self.merged_tree if path.endswith('a' * 40) else 'tree'}}
        if '/rule-suites/' in path:
            number = int(path.rsplit('/', 1)[1])
            return {'id': number, 'result': self.denial, 'ref': 'refs/heads/main', 'after_sha': str(number) * 40}
        raise AssertionError(path)

    def test_complete_native_proof_is_observed(self):
        self.assertTrue(observe_proof(self.config, self.observation, self.api, self.logs)['valid'])

    def test_candidate_workflow_cannot_supply_provenance(self):
        self.run_event = 'pull_request'
        self.assertFalse(observe_proof(self.config, self.observation, self.api, self.logs)['valid'])

    def test_drift_missing_case_different_tree_or_unenforced_denial_blocks(self):
        for alteration in ('drift', 'missing', 'tree', 'denial'):
            with self.subTest(alteration=alteration):
                saved = copy.deepcopy(self.proof)
                if alteration == 'drift':
                    self.proof['policy'] = 'old'
                elif alteration == 'missing':
                    del self.proof['cases']['source-spoof']
                elif alteration == 'tree':
                    self.merged_tree = 'different'
                else:
                    self.denial = 'pass'
                self.assertFalse(observe_proof(self.config, self.observation, self.api, self.logs)['valid'])
                self.proof = saved
                self.merged_tree, self.denial = 'tree', 'fail'

    def logs(self, path):
        return '2026-09-26T09:11:22Z   ref: ' + 'b' * 40 + '\n2026-09-26T09:11:23Z   ref: ' + 'a' * 40 + '\n'

    def test_wrong_executed_source_or_expired_native_log_blocks(self):
        result = observe_proof(self.config, self.observation, self.api, lambda _: '')
        self.assertFalse(result['valid'])
        self.assertEqual('valid', result['phase'])
        self.assertEqual('docs/proof-recovery.md', result['recovery']['guide'])
        self.assertFalse(result['recovery']['automatic_activation'])
        self.assertFalse(observe_proof(self.config, self.observation, self.api, lambda _: self.logs('').replace('a' * 40, 'f' * 40))['valid'])

    def test_backlog_profile_cannot_reuse_issue_only_deployment_proof(self):
        from tests.test_backlog import settings
        self.config['profile'] = 'github-backlog-v1'
        self.config['work'] = settings()
        self.config['authorities']['work'] = 'repository-backlog'
        result = observe_proof(self.config, self.observation, self.api, self.logs)
        self.assertFalse(result['valid'])
        self.assertIn('Backlog work proof cases', result['reason'])
