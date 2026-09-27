import json
import subprocess
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

    def test_native_checkout_line_endings_do_not_invalidate_same_controls(self):
        bootstrap(self.repo, 'owner/repo', 'main')
        original = self.repo.local()['controls']
        for relative in ('.harness/config.json', '.harness/AGENT.md', 'AGENTS.md'):
            path = self.root / relative
            path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
        self.assertEqual(original, self.repo.local()['controls'])
        self.assertTrue(self.repo.local()['installed'])
        (self.root / 'AGENTS.md').write_text('Different controls\n', encoding='utf-8')
        self.assertNotEqual(original, self.repo.local()['controls'])

    def test_machine_paths_preserve_git_names_without_filesystem_checkout(self):
        # Git permits names Windows cannot materialize. Populate objects directly
        # so CR/LF, quotes and undecodable bytes are exercised on both platforms.
        paths = [b' leading ', b'quote".yml', b'line\r\nbreak',
                 '测试.py'.encode('utf-8'), b'odd-\xff', b'trailing\n']
        blob = git(self.root, 'rev-parse', 'HEAD:file.txt')
        records = b''.join(b'100644 blob ' + blob.encode() + b'\t' + path + b'\0' for path in paths + [b'file.txt'])
        result = subprocess.run(['git', '-C', str(self.root), 'mktree', '-z'],
                                input=records, capture_output=True)
        self.assertEqual(0, result.returncode, result.stderr)
        tree = result.stdout.decode().strip()
        commit = git(self.root, 'commit-tree', tree, '-p', 'HEAD', '-m', 'unusual Git paths')
        git(self.root, 'update-ref', 'HEAD', commit)
        actual = self.repo.git_paths('ls-tree', '-r', '--name-only', '-z', 'HEAD')
        self.assertEqual(set(paths + [b'file.txt']), {path.encode('utf-8', 'surrogateescape') for path in actual})
        changed = self.repo.git_paths('diff', '--name-only', '--no-renames', '-z', 'HEAD^', 'HEAD')
        self.assertEqual(set(paths), {path.encode('utf-8', 'surrogateescape') for path in changed})
        self.assertEqual([], self.repo.git_paths('diff', '--name-only', '-z', 'HEAD', 'HEAD'))

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
