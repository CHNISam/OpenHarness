import base64
import hashlib
import unittest
from unittest.mock import patch

from openharness.backlog import corpus
from openharness.ci import current_context, control_authorized, control_change, publish
from openharness.model import digest
from tests.test_backlog import configuration, task


class BacklogControllerTests(unittest.TestCase):
    def setUp(self):
        self.config = configuration()
        self.data = task()
        self.pull = {'number': 7, 'state': 'open', 'draft': False, 'body': 'Work-Item: task-1',
                     'user': {'login': 'alice'}, 'head': {'sha': 'a' * 40, 'ref': 'codex/backlog-task-1-fix'},
                     'base': {'sha': 'b' * 40, 'ref': 'main'}, 'merge_commit_sha': 'c' * 40}
        self.calls = []

    def api(self, path):
        self.calls.append(path)
        if '/pulls/' in path:
            return self.pull
        if '/branches/' in path:
            return {'commit': {'sha': 'b' * 40}}
        sha = hashlib.sha1(b'blob ' + str(len(self.data)).encode() + b'\0' + self.data).hexdigest()
        if '/git/trees/' in path:
            return {'truncated': False, 'tree': [{'path': 'backlog/tasks/task-1 - Example.md',
                                                'sha': sha, 'mode': '100644', 'type': 'blob'}]}
        if '/git/blobs/' in path:
            return {'sha': sha, 'encoding': 'base64', 'content': base64.b64encode(self.data).decode()}
        if '/git/commits/' in path:
            return {'sha': path.rsplit('/', 1)[1], 'tree': {'sha': 'd' * 40},
                    'parents': [{'sha': 'b' * 40}, {'sha': 'a' * 40}]}
        raise AssertionError(path)

    def test_context_uses_canonical_task_not_issue_or_candidate_task(self):
        context = current_context(self.config, {'pull_request': {'number': 7}}, self.api)
        self.assertEqual('task-1', context['task'])
        self.assertEqual('alice', context['actor'])
        self.assertEqual('b' * 40, context['work_revision'])
        self.assertFalse(any('/issues/' in path for path in self.calls))
        self.assertFalse(any('/git/trees/' + 'a' * 40 in path for path in self.calls))

    def test_wrong_author_missing_work_and_mixed_authorities_fail(self):
        for mutation in ('author', 'missing', 'mixed', 'branch', 'base'):
            with self.subTest(mutation=mutation):
                self.setUp()
                if mutation == 'author':
                    self.pull['user']['login'] = 'bob'
                elif mutation == 'missing':
                    self.pull['body'] = 'Work-Item: task-2'
                elif mutation == 'mixed':
                    self.pull['body'] += '\nWork-Item: #3'
                elif mutation == 'branch':
                    self.pull['head']['ref'] = 'codex/1-fix'
                else:
                    self.pull['base']['sha'] = 'e' * 40
                with self.assertRaises(ValueError):
                    current_context(self.config, {'pull_request': {'number': 7}}, self.api)

    def test_task_control_approval_is_native_pr_change_authority(self):
        context = current_context(self.config, {'pull_request': {'number': 7}}, self.api)
        calls = []
        approval = {'user': {'login': 'owner'}, 'body': 'OpenHarness-Control-Approval: ' + 'a' * 40 + ' ' + 'b' * 40}
        self.assertTrue(control_authorized(self.config, context, lambda path: calls.append(path) or [approval]))
        self.assertEqual(['repos/owner/repo/issues/7/comments?per_page=100'], calls)
        self.assertTrue(control_change(self.config, ['backlog/tasks/task-1 - Example.md']))
        self.assertTrue(control_change(self.config, ['backlog']))
        self.assertFalse(control_change(self.config, ['src/project.py']))

    def test_independent_publisher_rejects_canonical_reassignment_drift(self):
        event = {'pull_request': {'number': 7}}
        context = current_context(self.config, event, self.api)
        identity = digest({'context': context, 'tree': 'd' * 40, 'verification': self.config['verification']})
        writes = []
        with patch.dict('os.environ', {'GITHUB_RUN_ID': '123'}):
            result = publish(self.config, event, 'success', 'a' * 40, 'b' * 40, 'd' * 40,
                             identity, self.api, lambda *args: writes.append(args))
            self.assertEqual('success', result['state'])
            self.data = task(assignee='["@bob"]')
            with self.assertRaisesRegex(ValueError, 'assigned'):
                publish(self.config, event, 'success', 'a' * 40, 'b' * 40, 'd' * 40,
                        identity, self.api, lambda *args: writes.append(args))
        self.assertEqual(2, len(writes))


if __name__ == '__main__':
    unittest.main()
