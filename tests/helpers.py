import subprocess
from pathlib import Path


def git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


def make_repo(root):
    root = Path(root)
    git(root, 'init', '-b', 'main')
    git(root, 'config', 'user.name', 'Harness Test')
    git(root, 'config', 'user.email', 'test@example.invalid')
    git(root, 'config', 'core.autocrlf', 'false')
    (root / 'file.txt').write_text('base\n', encoding='utf-8')
    git(root, 'add', '.')
    git(root, 'commit', '-m', 'base')
    git(root, 'remote', 'add', 'origin', 'https://github.com/owner/repo.git')
    return root
