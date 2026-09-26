import copy
import unittest

from openharness.ci import controller_blobs, event_policy, workflow_text
from openharness.model import default_config
from openharness.native import trusted
from openharness.provider import summarize
from tests.test_provider import substrate


class NativeTests(unittest.TestCase):
    def setUp(self):
        self.config = default_config('owner/repo', 'main')
        self.config['verification'].update(expected_app_id=42, controller={'repository': 'owner/tool', 'revision': 'a' * 40}, sandbox_image='python@sha256:' + 'a' * 64)
        self.raw = substrate()
        self.raw.update(controller_workflow=workflow_text(), controller_blobs=controller_blobs(), actions_policies=[event_policy()], other_target_workflows=[], canonical_config=copy.deepcopy(self.config))

    def test_provenance_requires_real_native_inputs(self):
        self.assertTrue(trusted(self.config, self.raw))
        for key, changed in [('controller_workflow', 'forged'), ('controller_blobs', {}), ('actions_policies', []), ('other_target_workflows', ['forge.yml']), ('canonical_config', {})]:
            raw = copy.deepcopy(self.raw)
            raw[key] = changed
            self.assertFalse(trusted(self.config, raw), key)

    def test_evaluate_policy_is_not_enforcement(self):
        self.raw['actions_policies'][0]['enforcement'] = 'evaluate'
        self.assertFalse(trusted(self.config, self.raw))

    def test_policy_excluded_workflow_keeps_bypass_open(self):
        self.raw['actions_policies'][0]['conditions'] = {'workflow_path': {'exclude': ['forge.yml']}}
        self.assertFalse(trusted(self.config, self.raw))

    def test_personal_repo_strict_merge_only_is_native_alternative(self):
        self.raw['rules'] = [r for r in self.raw['rules'] if r['type'] != 'merge_queue']
        self.raw['rules'][0]['parameters'] = {'allowed_merge_methods': ['merge']}
        report = summarize(self.config, self.raw, [])
        self.assertTrue(report['gate'])
        self.assertEqual('strict-merge-only-pr', report['candidate_strategy'])
        self.raw['rules'][0]['parameters']['allowed_merge_methods'].append('squash')
        self.assertFalse(summarize(self.config, self.raw, [])['gate'])


if __name__ == '__main__':
    unittest.main()
