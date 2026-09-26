import unittest

from openharness.model import default_config
from openharness.provider import GitHub, summarize


def protected_rules():
    return [
        {'type': 'pull_request'}, {'type': 'merge_queue'},
        {'type': 'non_fast_forward'}, {'type': 'deletion'},
        {'type': 'required_status_checks', 'parameters': {'strict_required_status_checks_policy': True, 'required_status_checks': [{'context': 'openharness / candidate', 'integration_id': 42}]}},
    ]


def substrate():
    return {
        'repository': {'full_name': 'owner/repo', 'id': 1, 'default_branch': 'main'},
        'rules': protected_rules(),
        'rulesets': [{'id': 7, 'enforcement': 'active', 'bypass_actors': [], 'rules': protected_rules()}],
        'branch': {'name': 'main', 'commit': {'sha': 'a' * 40}},
        'protection': None, 'workflows': {'workflows': []},
    }


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.config = default_config('owner/repo', 'main')
        self.config['verification']['expected_app_id'] = 42

    def test_native_gate_requires_no_bypass(self):
        raw = substrate()
        self.assertTrue(summarize(self.config, raw, [])['gate'])
        raw['rulesets'][0]['bypass_actors'] = [{'actor_id': 5, 'bypass_mode': 'always'}]
        self.assertFalse(summarize(self.config, raw, [])['gate'])

    def test_unbound_check_source_is_not_sufficient(self):
        raw = substrate()
        raw['rules'][4]['parameters']['required_status_checks'][0]['integration_id'] = None
        self.assertFalse(summarize(self.config, raw, [])['gate'])

    def test_missing_queue_cannot_establish_candidate_gate(self):
        raw = substrate()
        raw['rules'] = [r for r in raw['rules'] if r['type'] != 'merge_queue']
        self.assertFalse(summarize(self.config, raw, [])['gate'])

    def test_permissions_failure_cannot_be_treated_as_absence(self):
        report = summarize(self.config, substrate(), ['ruleset detail: HTTP 403'])
        self.assertFalse(report['gate'])
        self.assertEqual(['ruleset detail: HTTP 403'], report['errors'])

    def test_malformed_check_policy_is_unobservable_not_pass(self):
        raw = substrate()
        raw['rules'][4]['parameters'] = {'required_status_checks': 'invalid'}
        report = summarize(self.config, raw, [])
        self.assertFalse(report['gate'])
        self.assertTrue(report['errors'])

    def test_target_movement_not_policy_drift(self):
        raw = substrate()
        before = summarize(self.config, raw, [])
        raw['branch']['commit']['sha'] = 'b' * 40
        after = summarize(self.config, raw, [])
        self.assertEqual(before['fingerprint'], after['fingerprint'])
        self.assertNotEqual(before['target_sha'], after['target_sha'])

    def test_workflow_content_drift_invalidates_fingerprint(self):
        raw = substrate()
        raw['workflow_blobs'] = {'ci.yml': 'first-blob'}
        before = summarize(self.config, raw, [])
        raw['workflow_blobs']['ci.yml'] = 'second-blob'
        self.assertNotEqual(before['fingerprint'], summarize(self.config, raw, [])['fingerprint'])

    def test_inherited_ruleset_details_are_read(self):
        calls = []

        def api(path):
            calls.append(path)
            if path.endswith('/rulesets?includes_parents=true&per_page=100'):
                return [{'id': 7, 'source_type': 'Organization', 'source': 'owner'}]
            if '/orgs/owner/rulesets/7' in path:
                return {'id': 7, 'enforcement': 'active', 'bypass_actors': []}
            if path.endswith('/protection'):
                return None
            if '/rules/branches/' in path:
                return protected_rules()
            if '/branches/' in path:
                return {'commit': {'sha': 'a' * 40}}
            if path.endswith('/actions/workflows?per_page=100'):
                return {'total_count': 0, 'workflows': []}
            return {'full_name': 'owner/repo', 'id': 1}

        GitHub(api).observe(self.config)
        self.assertIn('orgs/owner/rulesets/7', calls)


if __name__ == '__main__':
    unittest.main()
