import copy
import unittest

from openharness.ci import WORKFLOW_PATH, CHECKOUT, PYTHON, controller_blobs, event_policy, workflow_text
from openharness.model import default_config
from openharness.native import trusted, producer_blobs
from openharness.provider import summarize
from tests.test_provider import substrate


class NativeTests(unittest.TestCase):
    def setUp(self):
        self.config = default_config('owner/repo', 'main')
        self.config['verification'].update(expected_app_id=42, controller={'repository': 'owner/tool', 'revision': 'a' * 40}, sandbox_image='python@sha256:' + 'a' * 64)
        self.raw = substrate()
        self.raw.update(controller_workflow=workflow_text(), controller_blobs=producer_blobs(), actions_policies=[event_policy()], other_target_workflows=[], canonical_config=copy.deepcopy(self.config))
        self.raw['workflows'] = {'workflows': [{'path': WORKFLOW_PATH, 'state': 'active'}], 'permissions': {'enabled': True, 'allowed_actions': 'all'}}

    def test_provenance_requires_real_native_inputs(self):
        self.assertTrue(trusted(self.config, self.raw))
        for key, changed in [('controller_workflow', 'forged'), ('controller_blobs', {}), ('actions_policies', []), ('other_target_workflows', ['forge.yml']), ('canonical_config', {})]:
            raw = copy.deepcopy(self.raw)
            raw[key] = changed
            self.assertFalse(trusted(self.config, raw), key)

    def test_evaluate_policy_is_not_enforcement(self):
        self.raw['actions_policies'][0]['enforcement'] = 'evaluate'
        self.assertFalse(trusted(self.config, self.raw))

    def test_disabled_controller_cannot_claim_provenance(self):
        self.raw['workflows']['workflows'][0]['state'] = 'disabled_manually'
        self.assertFalse(trusted(self.config, self.raw))

    def test_repository_level_actions_disable_or_unknown_allowlist_blocks(self):
        self.raw['workflows']['permissions']['enabled'] = False
        self.assertFalse(trusted(self.config, self.raw))
        self.raw['workflows']['permissions'].update(enabled=True, allowed_actions='selected')
        self.assertFalse(trusted(self.config, self.raw))

    def test_selected_actions_supports_explicit_native_permission(self):
        permissions = self.raw['workflows']['permissions']
        permissions.update(allowed_actions='selected', selected_actions={
            'github_owned_allowed': True, 'verified_allowed': False, 'patterns_allowed': []})
        self.assertTrue(trusted(self.config, self.raw))
        permissions['selected_actions'].update(github_owned_allowed=False, patterns_allowed=[
            f'actions/checkout@{CHECKOUT}', f'actions/setup-python@{PYTHON}'])
        self.assertTrue(trusted(self.config, self.raw))
        permissions['selected_actions']['patterns_allowed'].pop()
        self.assertFalse(trusted(self.config, self.raw))
        permissions['selected_actions'].update(verified_allowed=True, patterns_allowed=['actions/*'])
        self.assertFalse(trusted(self.config, self.raw))
        permissions['selected_actions']['github_owned_allowed'] = 'true'
        self.assertFalse(trusted(self.config, self.raw))

    def test_native_all_workflows_normalization_is_equivalent(self):
        self.raw['actions_policies'][0]['conditions'] = {'workflow_path': {'include': ['~ALL'], 'exclude': []}}
        self.assertTrue(trusted(self.config, self.raw))

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
