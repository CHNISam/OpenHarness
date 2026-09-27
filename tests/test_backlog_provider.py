import base64
import hashlib
import unittest

from openharness.backlog import read_corpus
from openharness.provider import GitHub
from tests.test_backlog import configuration, task


class BacklogProviderTests(unittest.TestCase):
    def setUp(self):
        self.config = configuration()
        self.data = task()
        self.sha = hashlib.sha1(b'blob ' + str(len(self.data)).encode() + b'\0' + self.data).hexdigest()
        self.entries = [{'path': 'backlog/tasks/task-1 - Example.md', 'mode': '100644', 'type': 'blob', 'sha': self.sha}]
        self.calls = []

    def api(self, path):
        self.calls.append(path)
        if path == 'user':
            return {'login': 'alice'}
        if '/branches/' in path:
            return {'commit': {'sha': 'a' * 40}}
        if '/git/trees/' in path:
            return {'tree': self.entries, 'truncated': False}
        if '/git/blobs/' in path:
            return {'sha': self.sha, 'encoding': 'base64', 'content': base64.b64encode(self.data).decode()}
        raise AssertionError(path)

    def test_task_authorization_reads_only_immutable_tree_and_blob(self):
        provider = GitHub(self.api)
        work = provider.work(self.config, 'task-1')
        self.assertEqual('alice', work['actor'])
        self.assertEqual('a' * 40, work['revision'])
        self.assertTrue(any('/git/trees/' + 'a' * 40 in call for call in self.calls))
        self.assertFalse(any('/issues/' in call for call in self.calls))
        self.assertEqual('task-1', provider.list_work(self.config)[0]['id'])

    def test_incomplete_nonregular_and_hash_mismatch_cannot_authorize(self):
        for mutation in ('truncated', 'link', 'ancestor_link', 'blob'):
            def api(path):
                result = self.api(path)
                if '/git/trees/' in path:
                    if mutation == 'truncated':
                        result['truncated'] = True
                    elif mutation == 'link':
                        result['tree'] = [{**self.entries[0], 'mode': '120000'}]
                    elif mutation == 'ancestor_link':
                        result['tree'] = [*self.entries, {'path': 'backlog', 'mode': '120000', 'type': 'blob'}]
                elif '/git/blobs/' in path and mutation == 'blob':
                    result['content'] = base64.b64encode(b'wrong').decode()
                return result
            with self.assertRaises(ValueError, msg=mutation):
                read_corpus(self.config, 'a' * 40, api)

    def test_mutable_revision_cannot_be_passed_as_immutable_work(self):
        with self.assertRaises(ValueError):
            read_corpus(self.config, 'main', self.api)


if __name__ == '__main__':
    unittest.main()
