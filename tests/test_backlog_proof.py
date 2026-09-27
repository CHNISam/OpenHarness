import base64
import copy
import hashlib
import json
import unittest

from openharness.ci import WORKFLOW_PATH, workflow_text
from openharness.native import observe_work_proof
from tests.test_backlog import configuration, task


class BacklogProofTests(unittest.TestCase):
    def setUp(self):
        self.config = configuration()
        self.config['verification']['controller'] = {'repository': 'owner/tool', 'revision': 'a' * 40}
        names = ('wrong-executor', 'blocked-dependency', 'self-authority', 'invalid-completion', 'stale-work')
        self.reasons = ('Backlog executor is not currently assigned', 'Backlog dependency is not complete',
                        'Protected control change requires native owner approval bound to head and base',
                        'Candidate completion requires completed prerequisites', 'Backlog executor is not currently assigned')
        self.proof = {'work_cases': {name: {'pr': i, 'head': str(i) * 40, 'rule_suite_id': i}
                                     for i, name in enumerate(names, 1)}}
        self.proof['work_cases']['stale-work'].update(accepted_run=9, task='task-1')
        self.changed = True
        self.ancestry = 'ahead'
        self.denied = 'fail'
        self.untrusted_output = False

    def api(self, path):
        if '/contents/' in path:
            content = workflow_text() if WORKFLOW_PATH in path else json.dumps(self.config)
            return {'type': 'file', 'encoding': 'base64', 'content': base64.b64encode(content.encode()).decode()}
        if '/pulls/' in path:
            number = int(path.rsplit('/', 1)[1])
            return {'number': number, 'head': {'sha': str(number) * 40}, 'base': {'ref': 'main'}, 'merged': False, 'user': {'login': 'alice'}}
        if '/statuses?' in path:
            number = int(path.split('/commits/')[1][0])
            return [{'context': self.config['verification']['required_check'], 'state': 'failure',
                     'creator': {'login': 'github-actions[bot]'}, 'target_url': f'https://github.com/owner/repo/actions/runs/{number}'}]
        if '/actions/runs/' in path:
            number = int(path.split('/actions/runs/')[1].split('/')[0])
            if '/jobs?' in path:
                return {'total_count': 2, 'jobs': [
                    {'id': number * 10, 'name': 'publish', 'status': 'completed', 'conclusion': 'success'},
                    {'id': number * 10 + 1, 'name': 'verify', 'status': 'completed', 'conclusion': 'failure' if number != 9 else 'success'}]}
            return {'id': number, 'event': 'pull_request_target', 'path': WORKFLOW_PATH,
                    'head_sha': ('5' if number == 9 else str(number)) * 40, 'status': 'completed',
                    'conclusion': 'success' if number == 9 else 'failure'}
        if '/rule-suites/' in path:
            number = int(path.rsplit('/', 1)[1])
            return {'result': self.denied, 'after_sha': str(number) * 40, 'ref': 'refs/heads/main'}
        if '/compare/' in path:
            return {'status': self.ancestry}
        old = task()
        new = task(assignee='["@bob"]') if self.changed else old
        blob = lambda data: hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if '/git/trees/' in path:
            data = old if 'c' * 40 in path else new
            return {'truncated': False, 'tree': [{'path': 'backlog/tasks/task-1 - Example.md', 'mode': '100644', 'type': 'blob', 'sha': blob(data)}]}
        if '/git/blobs/' in path:
            data = old if path.endswith(blob(old)) else new
            return {'sha': blob(data), 'encoding': 'base64', 'content': base64.b64encode(data).decode()}
        raise AssertionError(path)

    def logs(self, path):
        number = int(path.split('/actions/jobs/')[1].split('/')[0])
        if number % 10 == 0:
            baseline = ('c' if number == 90 else 'b') * 40
            return f'2026-09-27T00:00:00Z ref: {baseline}\n2026-09-27T00:00:01Z ref: ' + 'a' * 40 + '\n'
        reason = self.reasons[number // 10 - 1]
        if self.untrusted_output:
            return '2026-09-27T00:00:02Z ValueError: Candidate acceptance failed: ' + json.dumps({'stdout': 'ValueError: ' + reason})
        return '2026-09-27T00:00:02Z ValueError: ' + reason + '\n'

    def test_all_native_cases_and_canonical_revocation_required(self):
        self.assertEqual(5, len(observe_work_proof(self.config, self.proof, self.api, self.logs)))
        for mutation in ('missing', 'unchanged', 'ancestry', 'denial', 'spoofed_output'):
            with self.subTest(mutation=mutation):
                self.setUp()
                if mutation == 'missing':
                    del self.proof['work_cases']['wrong-executor']
                elif mutation == 'unchanged':
                    self.changed = False
                elif mutation == 'ancestry':
                    self.ancestry = 'diverged'
                elif mutation == 'denial':
                    self.denied = 'pass'
                else:
                    self.untrusted_output = True
                with self.assertRaises(ValueError):
                    observe_work_proof(self.config, self.proof, self.api, self.logs)


if __name__ == '__main__':
    unittest.main()
