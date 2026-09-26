import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import git, make_repo


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = make_repo(self.temp.name)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'openharness', '--repo', str(self.root), *args], capture_output=True, text=True, encoding='utf-8')

    def test_help_and_bootstrap_from_fresh_process(self):
        self.assertEqual(0, self.run_cli('--help').returncode)
        result = self.run_cli('bootstrap')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('GENESIS', json.loads(result.stdout)['lifecycle'])
        again = self.run_cli('bootstrap')
        self.assertEqual([], json.loads(again.stdout)['changed'])

    def test_no_user_acceptance_commands_means_verification_is_blocked(self):
        self.run_cli('bootstrap')
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'install')
        result = self.run_cli('verify', '--head', 'HEAD', '--base', 'main')
        self.assertEqual(1, result.returncode)
        self.assertIn('acceptance commands', json.loads(result.stderr)['error'])

    def test_cli_verifies_and_discovers_evidence_in_new_session(self):
        self.run_cli('bootstrap')
        config_path = self.root / '.harness/config.json'
        config = json.loads(config_path.read_text(encoding='utf-8'))
        config['verification']['commands'] = [[sys.executable, '-c', 'print("passed")']]
        config_path.write_text(json.dumps(config), encoding='utf-8')
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'install')
        verified = self.run_cli('verify', '--head', 'HEAD', '--base', 'main')
        self.assertEqual(0, verified.returncode, verified.stderr)
        self.assertFalse(json.loads(verified.stdout)['authorizes_integration'])
        evidence = self.run_cli('evidence', '--head', 'HEAD', '--base', 'main')
        self.assertTrue(json.loads(evidence.stdout)['fresh'])

    def test_failing_candidate_check_has_blocking_exit(self):
        self.run_cli('bootstrap')
        config_path = self.root / '.harness/config.json'
        config = json.loads(config_path.read_text(encoding='utf-8'))
        config['verification']['commands'] = [[sys.executable, '-c', 'raise SystemExit(7)']]
        config_path.write_text(json.dumps(config), encoding='utf-8')
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'install')
        verified = self.run_cli('verify', '--head', 'HEAD', '--base', 'main')
        self.assertEqual(2, verified.returncode)
        self.assertFalse(json.loads(verified.stdout)['passed'])

    def test_setup_plan_does_not_mutate_remote_or_activate(self):
        self.run_cli('bootstrap')
        plan = self.run_cli('setup-plan')
        self.assertEqual(0, plan.returncode)
        data = json.loads(plan.stdout)
        self.assertEqual('proposal-only', data['mode'])
        self.assertFalse(data['activation_possible_in_this_version'])
        self.assertTrue(data['unresolved'])


if __name__ == '__main__':
    unittest.main()
