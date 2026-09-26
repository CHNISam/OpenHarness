import json
import tempfile
import unittest
from pathlib import Path

from openharness.repository import Repository, bootstrap
from tests.helpers import git, make_repo


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = make_repo(self.temp.name)
        self.repo = Repository(self.root)

    def test_install_is_repeatable_and_preserves_existing_instructions(self):
        (self.root / 'AGENTS.md').write_text('Project preferences.\n', encoding='utf-8')
        bootstrap(self.repo, 'owner/repo', 'main')
        first = (self.root / 'AGENTS.md').read_text(encoding='utf-8')
        bootstrap(self.repo, 'owner/repo', 'main')
        self.assertEqual(first, (self.root / 'AGENTS.md').read_text(encoding='utf-8'))
        self.assertTrue(first.startswith('Project preferences.'))
        config = self.repo.config()
        config['verification']['commands'] = [['python', '--version']]
        (self.root / '.harness/config.json').write_text(json.dumps(config), encoding='utf-8')
        bootstrap(self.repo, 'owner/repo', 'main')
        self.assertEqual(config, self.repo.config())

    def test_conflicting_install_never_leaves_partial_config(self):
        (self.root / '.harness').mkdir()
        (self.root / '.harness/AGENT.md').write_text('custom', encoding='utf-8')
        with self.assertRaises(ValueError):
            bootstrap(self.repo, 'owner/repo', 'main')
        self.assertFalse((self.root / '.harness/config.json').exists())

    def test_install_cannot_change_repository_identity(self):
        bootstrap(self.repo, 'owner/repo', 'main')
        with self.assertRaises(ValueError):
            bootstrap(self.repo, 'other/repo', 'main')

    def test_candidate_tracks_base_and_untracked_material_inputs(self):
        bootstrap(self.repo, 'owner/repo', 'main')
        config = self.repo.config()
        config['verification']['commands'] = [['python', '--version']]
        config['verification']['material_inputs'] = ['fixture.txt']
        (self.root / 'fixture.txt').write_text('one', encoding='utf-8')
        (self.root / '.harness/config.json').write_text(json.dumps(config), encoding='utf-8')
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'install')
        before = self.repo.candidate('HEAD', 'main')
        (self.root / 'fixture.txt').write_text('two', encoding='utf-8')
        after = self.repo.candidate('HEAD', 'main')
        self.assertNotEqual(before['inputs'], after['inputs'])

    def test_path_escape_material_input_rejected(self):
        bootstrap(self.repo, 'owner/repo', 'main')
        config = self.repo.config()
        config['verification']['material_inputs'] = ['../outside']
        (self.root / '.harness/config.json').write_text(json.dumps(config), encoding='utf-8')
        with self.assertRaises(ValueError):
            self.repo.candidate('HEAD', 'main')

    def test_control_directory_symlink_cannot_escape_install_root(self):
        with tempfile.TemporaryDirectory() as outside:
            try:
                (self.root / '.harness').symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest('OS does not permit creating symlinks')
            with self.assertRaises(ValueError):
                bootstrap(self.repo, 'owner/repo', 'main')
            self.assertEqual([], list(Path(outside).iterdir()))

    def test_native_worktrees_are_isolated(self):
        bootstrap(self.repo, 'owner/repo', 'main')
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'install')
        first = self.repo.workspace(1, 'first', 'main')
        second = self.repo.workspace(1, 'second', 'main')
        (Path(first['path']) / 'file.txt').write_text('first-only', encoding='utf-8')
        self.assertEqual('base\n', (Path(second['path']) / 'file.txt').read_text(encoding='utf-8'))
        self.assertNotEqual(first['branch'], second['branch'])
        self.assertEqual(1, first['work_item'])
        self.assertEqual(self.repo.common_dir, Repository(first['path']).common_dir)


if __name__ == '__main__':
    unittest.main()
