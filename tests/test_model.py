import copy
import unittest

from openharness.model import CATALOGUE, candidate_id, evaluate, default_config, validate_config


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.config = default_config('owner/repo', 'main')
        self.local = {'installed': True, 'git': True, 'clean': True}

    def test_omitting_guarantees_cannot_produce_pass(self):
        self.config['guarantees'] = []
        with self.assertRaises(ValueError):
            validate_config(self.config)
        result = evaluate(default_config('owner/repo', 'main'), self.local, {})
        self.assertEqual(set(CATALOGUE), {g['id'] for g in result['guarantees']})
        self.assertFalse(result['closure'])

    def test_multiple_authorities_rejected(self):
        self.config['authorities']['work'] = ['github-issues', 'local-backlog']
        with self.assertRaises(ValueError):
            validate_config(self.config)

    def test_unknown_topology_is_not_na(self):
        self.config['envelope']['workspace_writers'] = 'unknown'
        report = evaluate(self.config, self.local, {})
        row = next(g for g in report['guarantees'] if g['id'] == 'fencing')
        self.assertEqual(row['status'], 'OPEN GAP')
        self.assertFalse(row['applicability_resolved'])

    def test_competing_writers_require_real_adapter(self):
        self.config['envelope']['workspace_writers'] = 'multiple'
        report = evaluate(self.config, self.local, {'gate': True})
        for name in ('concurrency', 'fencing'):
            row = next(g for g in report['guarantees'] if g['id'] == name)
            self.assertEqual(row['status'], 'OPEN GAP')

    def test_na_is_scoped_to_declared_trusted_single_writer_envelope(self):
        report = evaluate(self.config, self.local, {})
        row = next(g for g in report['guarantees'] if g['id'] == 'fencing')
        self.assertEqual(row['status'], 'NOT APPLICABLE')
        self.assertIn('single', row['reason'])
        self.assertIn('workspace_writers', row['invalidation_triggers'])

    def test_unknown_provider_is_not_proven(self):
        report = evaluate(self.config, self.local, {'errors': ['403 forbidden']})
        for name in ('integration', 'provenance', 'coverage'):
            row = next(g for g in report['guarantees'] if g['id'] == name)
            self.assertEqual(row['status'], 'OPEN GAP')

    def test_every_material_candidate_component_changes_identity(self):
        candidate = dict(head='a', base='b', tree='c', config='d', inputs='e', environment='f')
        original = candidate_id(candidate)
        for field in candidate:
            changed = copy.deepcopy(candidate)
            changed[field] += '-changed'
            self.assertNotEqual(original, candidate_id(changed), field)

    def test_candidate_identity_cannot_omit_base(self):
        with self.assertRaises(ValueError):
            candidate_id({'head': 'a'})


if __name__ == '__main__':
    unittest.main()
