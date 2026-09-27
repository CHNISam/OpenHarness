import tempfile
import unittest
from unittest.mock import patch

from openharness.backlog import authorize, local_corpus
from openharness.repository import Repository, bootstrap
from openharness.runtime import Runtime
from tests.helpers import git, make_repo
from tests.test_backlog import settings, task


class CanonicalFixture:
    def __init__(self, repo):
        self.repo = repo

    def observe(self, config):
        return {'source': 'fixture', 'target_sha': self.repo.revision('main'), 'errors': []}

    def work(self, config, identifier):
        revision = self.repo.revision('main')
        observation = local_corpus(self.repo, revision, config['work'])
        return {**authorize(observation, config['work'], identifier, 'alice'), 'revision': revision}


class BacklogRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = make_repo(self.temp.name)
        self.repo = Repository(self.root)
        bootstrap(self.repo, 'owner/repo', 'main', profile='github-backlog-v1', work=settings())
        folder = self.root / 'backlog/tasks'
        folder.mkdir(parents=True)
        self.path = folder / 'task-1 - Example.md'
        self.path.write_bytes(task())
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'canonical Backlog')
        self.provider = CanonicalFixture(self.repo)
        self.runtime = Runtime(self.repo, self.provider)

    def test_installed_task_profile_and_genesis_binding_survive_fresh_process(self):
        self.assertTrue(self.repo.local()['installed'])
        binding = self.runtime.workspace('task-1', 'fix', genesis=True)
        self.assertEqual('codex/backlog-task-1-fix', binding['branch'])
        self.assertEqual('alice', binding['actor'])
        self.assertEqual(self.provider.work(self.repo.config(), 'task-1')['identity'], binding['work_identity'])
        fresh = Runtime(Repository(binding['path']), self.provider)
        self.assertEqual(binding, fresh.state()['workspaces'][binding['path']])

    def test_preflight_and_reconcile_reject_canonical_drift_without_deleting_work(self):
        binding = self.runtime.workspace('task-1', 'fix', genesis=True)
        work = Runtime(Repository(binding['path']), self.provider)
        state = work.state()
        state.update(lifecycle='MANAGED', substrate='fixture')
        work.save_state(state)
        report = {'closure': True, 'substrate': 'fixture'}
        with patch.object(work, 'doctor', return_value=report):
            self.assertTrue(work.preflight()['allowed'])
            self.path.write_bytes(task() + b'Canonical corpus changed\n')
            git(self.root, 'add', '.')
            git(self.root, 'commit', '-m', 'canonical drift')
            with self.assertRaisesRegex(ValueError, 'drift'):
                work.preflight()
            reconciled = work.reconcile()
            self.assertEqual([binding['path']], reconciled['invalid_work_bindings'])
            self.assertTrue(Repository(binding['path']).root.exists())
            self.path.write_bytes(task())
            git(self.root, 'add', '.')
            git(self.root, 'commit', '-m', 'restore bytes')
            with self.assertRaisesRegex(ValueError, 'invalidated'):
                work.preflight()

    def test_work_revision_race_rejects_before_binding(self):
        with patch.object(self.provider, 'observe', return_value={'target_sha': 'b' * 40, 'errors': []}):
            with self.assertRaisesRegex(ValueError, 'revision changed'):
                self.runtime.workspace('task-1', 'raced', genesis=True)
        self.assertEqual({}, self.runtime.state()['workspaces'])

    def test_working_tree_assignment_cannot_authorize_workspace(self):
        self.path.write_bytes(task(assignee='["@bob"]'))
        binding = self.runtime.workspace('task-1', 'committed', genesis=True)
        self.assertEqual('alice', binding['actor'])
        self.assertNotEqual(self.path.read_bytes(), (Repository(binding['path']).root / 'backlog/tasks/task-1 - Example.md').read_bytes())

    def test_task_bootstrap_repeat_preserves_authority_and_reconfiguration_rejects(self):
        again = bootstrap(self.repo, 'owner/repo', 'main')
        self.assertEqual([], again['changed'])
        with self.assertRaises(ValueError):
            bootstrap(self.repo, 'owner/repo', 'main', profile='github-pr-v1')


if __name__ == '__main__':
    unittest.main()
