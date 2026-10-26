"""Synthetic projects only: no consumer data, tools, network or runner services."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import hashlib

from openharness.runner_guard import run, host_lock


class RunnerGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='openharness-guard-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.lock = self.root / 'host.lock'

    def command(self, code):
        return [sys.executable, '-c', code]

    def invoke(self, command, **options):
        return run(command, lock_path=self.lock, disk_path=self.root,
                   min_free_bytes=0, wait_seconds=0, timeout_seconds=3, **options)

    def test_disk_rejection_precedes_command(self):
        marker = self.root / 'started'
        with self.assertRaisesRegex(ValueError, 'disk'):
            run(self.command(f'open({str(marker)!r}, "w").close()'),
                lock_path=self.lock, disk_path=self.root, min_free_bytes=2**63,
                wait_seconds=0, timeout_seconds=3)
        self.assertFalse(marker.exists())

    def test_lock_from_other_project_blocks_before_launch(self):
        marker = self.root / 'started'
        with host_lock(self.lock, 0):
            result = subprocess.run([sys.executable, '-m', 'openharness.runner_guard',
                '--lock', str(self.lock), '--disk', str(self.root), '--min-free-bytes', '0',
                '--wait-seconds', '0', '--timeout-seconds', '3', '--argv-json',
                json.dumps(self.command(f'open({str(marker)!r}, "w").close()'))],
                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('lock', result.stderr)
        self.assertFalse(marker.exists())

    def test_exit_status_and_retry_after_failure(self):
        self.assertEqual(self.invoke(self.command('raise SystemExit(7)')), 7)
        self.assertEqual(self.invoke(self.command('pass')), 0)
        self.assertTrue(self.lock.exists(), 'lock inode must never be removed')

    def test_timeout_stops_process_tree_before_releasing_lock(self):
        marker = self.root / 'late-write'
        grandchild = f'import time; time.sleep(1); open({str(marker)!r}, "w").close()'
        child = ('import subprocess,sys,time; '
                 f'subprocess.Popen([sys.executable,"-c",{grandchild!r}]); time.sleep(10)')
        with self.assertRaises(TimeoutError):
            run(self.command(child), lock_path=self.lock, disk_path=self.root,
                min_free_bytes=0, wait_seconds=0, timeout_seconds=.2)
        self.assertEqual(self.invoke(self.command('pass')), 0)
        time.sleep(1.1)
        self.assertFalse(marker.exists())

    def test_invalid_inputs_do_not_start_command(self):
        for command in ([], 'echo hello', ['python', 12], ['python', 'bad\0arg']):
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.invoke(command)
        for value in (-1, float('inf'), float('nan')):
            with self.subTest(timeout=value), self.assertRaises(ValueError):
                run(self.command('pass'), lock_path=self.lock, disk_path=self.root,
                    min_free_bytes=0, wait_seconds=0, timeout_seconds=value)

    def test_preexisting_work_and_cache_are_preserved(self):
        cache = self.root / '.godot'
        cache.mkdir()
        (cache / 'imported').write_bytes(b'cache')
        source = self.root / 'uncommitted.txt'
        source.write_bytes(b'local work')
        self.invoke(self.command('pass'))
        self.assertEqual(source.read_bytes(), b'local work')
        self.assertEqual((cache / 'imported').read_bytes(), b'cache')

    @unittest.skipUnless(os.name == 'nt', 'Windows Job Object kill-on-close contract')
    def test_abrupt_wrapper_death_terminates_contained_children(self):
        ready, late = self.root / 'ready', self.root / 'late'
        command = self.command('import time; '
            f'open({str(ready)!r}, "w").close(); time.sleep(1); '
            f'open({str(late)!r}, "w").close()')
        wrapper = subprocess.Popen([sys.executable, '-m', 'openharness.runner_guard',
            '--lock', str(self.lock), '--disk', str(self.root), '--min-free-bytes', '0',
            '--wait-seconds', '0', '--timeout-seconds', '10', '--argv-json', json.dumps(command)])
        try:
            deadline = time.monotonic() + 5
            while not ready.exists() and time.monotonic() < deadline:
                self.assertIsNone(wrapper.poll())
                time.sleep(.02)
            self.assertTrue(ready.exists())
            wrapper.kill()
            wrapper.wait(timeout=5)
            time.sleep(1.1)
            self.assertFalse(late.exists())
            self.assertEqual(self.invoke(self.command('pass')), 0)
        finally:
            if wrapper.poll() is None:
                wrapper.kill()
            wrapper.wait(timeout=5)

    @unittest.skipUnless(os.name == 'nt', 'Windows composite action')
    def test_actual_composite_body_and_synthetic_consumer_equivalence(self):
        producer = Path(__file__).resolve().parents[1]
        action = producer / 'actions/runner-guard/action.yml'
        body = action.read_text().split('      run: |\n', 1)[1]
        script = self.root / 'action.ps1'
        script.write_text('\n'.join(line[8:] for line in body.splitlines()), encoding='utf-8')
        source = self.root / 'acceptance.py'
        # Argument includes shell syntax: must reach the child as literal bytes.
        output = self.root / 'output.json'
        source.write_text('import json,sys; from pathlib import Path; '
            'Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))')
        command = [sys.executable, str(source), str(output), 'hello $(exit 93); 雪']
        subprocess.run(command, check=True, timeout=5)
        baseline = output.read_bytes()
        original = hashlib.sha256(source.read_bytes()).hexdigest()
        environment = dict(os.environ, GITHUB_ACTION_PATH=str(action.parent),
            OPENHARNESS_COMMAND_JSON=json.dumps(command), OPENHARNESS_LOCK=str(self.lock),
            OPENHARNESS_DISK=str(self.root), OPENHARNESS_FREE='0', OPENHARNESS_WAIT='0',
            OPENHARNESS_TIMEOUT='3', OPENHARNESS_PYTHON=sys.executable)
        result = subprocess.run(['powershell.exe', '-NoProfile', '-File', str(script)],
                                env=environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_bytes(), baseline)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original)

    def test_missing_executable_releases_lock_and_keeps_work(self):
        with self.assertRaises((ValueError, OSError)):
            self.invoke(['openharness-definitely-missing-executable-9ae81'])
        self.assertEqual(self.invoke(self.command('pass')), 0)

    def test_full_sha_consumer_pin_survives_producer_upgrade_and_rollback(self):
        from tests.helpers import git, make_repo
        producer_path = self.root / 'synthetic-producer'
        producer_path.mkdir()
        producer = make_repo(producer_path)
        guard = producer / 'guard.py'
        guard.write_bytes((Path(__file__).resolve().parents[1] / 'openharness/runner_guard.py').read_bytes())
        git(producer, 'add', '.')
        git(producer, 'commit', '-m', 'synthetic reviewed guard')
        old_sha = git(producer, 'rev-parse', 'HEAD')
        consumer_a = self.root / 'consumer-a.json'
        consumer_b = self.root / 'consumer-b.json'
        for consumer in (consumer_a, consumer_b):
            consumer.write_text(json.dumps({'revision': old_sha}))
        before = {p: p.read_bytes() for p in (consumer_a, consumer_b)}

        def execute(consumer):
            pin = json.loads(consumer.read_text())['revision']
            installed = self.root / 'installed-guard.py'
            installed.write_text(git(producer, 'show', f'{pin}:guard.py'), encoding='utf-8')
            return subprocess.run([sys.executable, str(installed), '--lock', str(self.lock),
                '--disk', str(self.root), '--min-free-bytes', '0', '--wait-seconds', '0',
                '--timeout-seconds', '3', '--argv-json', json.dumps(self.command('pass'))],
                capture_output=True, text=True, timeout=10)

        self.assertEqual(execute(consumer_a).returncode, 0)
        guard.write_text('raise SystemExit(91)\n')  # deliberately broken producer release
        git(producer, 'add', '.')
        git(producer, 'commit', '-m', 'synthetic broken candidate')
        new_sha = git(producer, 'rev-parse', 'HEAD')
        self.assertNotEqual(old_sha, new_sha)
        self.assertEqual(execute(consumer_a).returncode, 0)
        self.assertEqual(execute(consumer_b).returncode, 0)
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        consumer_a.write_text(json.dumps({'revision': new_sha}))
        self.assertEqual(execute(consumer_a).returncode, 91)
        self.assertEqual(execute(consumer_b).returncode, 0)
        consumer_a.write_bytes(before[consumer_a])
        self.assertEqual(execute(consumer_a).returncode, 0)


if __name__ == '__main__':
    unittest.main()
