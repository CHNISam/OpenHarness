"""Issue #34: generic assent must not authorize disabling installed controls."""
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from openharness.ci import control_authorized
from openharness.control import impact_statement, local_changes, require_approval, review_marker
from openharness.model import default_config
from openharness.repository import Repository
from tests.helpers import make_repo, git


class ControlScopeTests(unittest.TestCase):
    def setUp(self):
        self.config = default_config('owner/repo', 'main')
        self.context = {'pr': 7, 'issue': 3, 'head': 'a' * 40, 'base': 'b' * 40}
        self.rows = [{'path': '.harness/config.json', 'operation': 'remove', 'patch': '-controller'}]
        self.pull = {'head': {'sha': self.context['head']}, 'base': {'sha': self.context['base']},
                     'user': {'login': 'executor-bot'}}
        self.review = {'id': 11, 'state': 'APPROVED', 'commit_id': self.context['head'],
                       'user': {'login': 'owner', 'type': 'User'}, 'body': ''}
        self.viewer = {'login': 'executor-bot'}

    def api(self, path):
        if isinstance(path, dict):
            row = self.review
            node = {'id': str(row['id']), 'state': row['state'], 'body': row['body'],
                    'submittedAt': '2026-10-26T00:00:00Z', 'lastEditedAt': row.get('lastEditedAt'),
                    'isMinimized': False, 'viewerDidAuthor': self.viewer['login'] == 'owner',
                    'author': {'login': row['user']['login'], '__typename': row['user']['type']},
                    'commit': {'oid': row['commit_id']}}
            return {'data': {'viewer': self.viewer, 'repository': {'pullRequest': {
                'headRefOid': self.pull['head']['sha'], 'baseRefOid': self.pull['base']['sha'],
                'author': self.pull['user'], 'reviews': {
                    'pageInfo': {'hasNextPage': False}, 'nodes': [node]}}}}}
        if path == 'user':
            return self.viewer
        if path.endswith('/pulls/7'):
            return self.pull
        if path.endswith('/pulls/7/reviews?per_page=100'):
            return [self.review]
        raise AssertionError(path)

    def test_generic_old_owner_comment_cannot_authorize_harness_removal(self):
        impact = impact_statement(self.config, self.context, self.rows)
        old = {'user': {'login': 'owner'}, 'body': 'OpenHarness-Control-Approval: ' +
               self.context['head'] + ' ' + self.context['base']}
        self.assertFalse(control_authorized(self.config, self.context,
            lambda path: [old] if '/comments' in path else self.api(path), impact=impact))
        self.assertFalse(control_authorized(self.config, self.context, lambda path: [old]))

    def test_exact_native_review_and_independent_executor_are_required(self):
        impact = impact_statement(self.config, self.context, self.rows)
        self.review['body'] = review_marker(impact)
        self.assertTrue(control_authorized(self.config, self.context, self.api, impact=impact))
        self.assertTrue(control_authorized(self.config, self.context, self.api, impact=impact, mutating=True))
        self.viewer = {'login': 'owner'}
        with self.assertRaisesRegex(ValueError, 'identity'):
            control_authorized(self.config, self.context, self.api, impact=impact, mutating=True)

    def test_self_authored_pr_stale_dismissed_edited_and_forged_review_fail(self):
        impact = impact_statement(self.config, self.context, self.rows)
        self.review['body'] = review_marker(impact)
        original = copy.deepcopy(self.review)
        for change in ({'state': 'DISMISSED'}, {'commit_id': 'f' * 40},
                       {'lastEditedAt': '2026-10-26T01:00:00Z'},
                       {'body': 'yes'}, {'body': review_marker(impact) + ' extra'},
                       {'user': {'login': 'imposter', 'type': 'User'}},
                       {'user': {'login': 'owner', 'type': 'Bot'}}):
            with self.subTest(change=change):
                self.review = {**original, **change}
                self.assertFalse(control_authorized(self.config, self.context, self.api, impact=impact))
        self.review = original
        self.pull['user']['login'] = 'owner'
        self.assertFalse(control_authorized(self.config, self.context, self.api, impact=impact))

    def test_changed_base_pr_repository_and_operation_invalidate_approval(self):
        impact = impact_statement(self.config, self.context, self.rows)
        self.review['body'] = review_marker(impact)
        for key, value in (('base', 'f' * 40), ('pr', 8), ('repository', 'other/repo'),
                           ('changes', [{'path': 'AGENTS.md', 'operation': 'remove'}])):
            altered = copy.deepcopy(impact)
            altered[key] = value
            self.assertNotEqual(review_marker(impact), review_marker(altered))

    def test_archive_rename_semantic_unbinding_and_policy_changes_are_reported(self):
        for row in (
            {'path': '.harness/config.json', 'operation': 'remove'},
            {'path': '.harness/config.json', 'operation': 'modify', 'patch': '-controller'},
            {'path': 'AGENTS.md', 'operation': 'modify', 'patch': '-Read .harness/AGENT.md'},
            {'path': 'requirements.txt', 'operation': 'remove', 'patch': '-openharness @ git+https://example.invalid/tool'},
            {'path': 'pyproject.toml', 'operation': 'modify', 'patch': '-openharness = "openharness.cli:main"'},
            {'path': '.github/workflows/ci.yml', 'operation': 'modify', 'patch': '-required_check'},
        ):
            with self.subTest(row=row):
                impact = impact_statement(self.config, self.context, [row])
                self.assertIsNotNone(impact)
                self.assertEqual(row['path'], impact['changes'][0]['path'])
        self.config['verification']['controller'] = {'repository': 'owner/repo', 'revision': 'c' * 40}
        self.assertIsNotNone(impact_statement(self.config, self.context,
            [{'path': 'openharness/ci.py', 'operation': 'modify'}]))

    def test_unrelated_product_change_needs_no_approval_or_identity_lookup(self):
        self.assertIsNone(impact_statement(self.config, self.context,
            [{'path': 'src/product.py', 'operation': 'modify'}]))
        self.assertIsNone(impact_statement(self.config, self.context,
            [{'path': 'requirements.txt', 'operation': 'modify', 'patch': '+unrelated==1.0'}]))

    def test_real_git_archive_preserves_original_removed_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_repo(temp)
            source = root / '.harness/config.json'
            source.parent.mkdir()
            source.write_text('{"controller":"pinned"}')
            git(root, 'add', '.')
            git(root, 'commit', '-m', 'synthetic installed control')
            base = git(root, 'rev-parse', 'HEAD')
            archive = root / 'history/config.json'
            archive.parent.mkdir()
            source.rename(archive)
            git(root, 'add', '.')
            git(root, 'commit', '-m', 'synthetic archive removal')
            context = {**self.context, 'base': base, 'head': git(root, 'rev-parse', 'HEAD')}
            changes = local_changes(Repository(root), base, context['head'])
            impact = impact_statement(self.config, context, changes)
            self.assertIn({'path': '.harness/config.json', 'operation': 'remove'}, impact['changes'])
            with patch('openharness.ci.control_authorized', return_value=False), self.assertRaisesRegex(ValueError, 'impact'):
                require_approval(Repository(root), self.config, context, self.api)

    def test_unavailable_edited_deleted_and_paginated_native_observations_stop(self):
        impact = impact_statement(self.config, self.context, self.rows)
        self.review['body'] = review_marker(impact)
        for failure in ('deleted', 'paginated', 'missing-edit-state', 'errors'):
            def observe(query):
                response = self.api(query)
                if failure == 'errors':
                    return {'errors': [{'message': 'unavailable'}], 'data': response['data']}
                reviews = response['data']['repository']['pullRequest']['reviews']
                if failure == 'deleted':
                    reviews['nodes'] = []
                elif failure == 'paginated':
                    reviews['pageInfo']['hasNextPage'] = True
                else:
                    del reviews['nodes'][0]['lastEditedAt']
                return response
            with self.subTest(failure=failure):
                if failure in ('errors', 'missing-edit-state'):
                    with self.assertRaises(ValueError):
                        control_authorized(self.config, self.context, observe, impact=impact)
                else:
                    self.assertFalse(control_authorized(self.config, self.context, observe, impact=impact))

    def test_cooperative_removal_is_rejected_before_native_merge(self):
        from tests.test_cooperative import CooperativeTests
        fixture = CooperativeTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        runtime, data, merge = fixture.merge_fixture()
        path = runtime.repo.root / 'AGENTS.md'
        path.unlink()
        git(runtime.repo.root, 'add', '.')
        git(runtime.repo.root, 'commit', '-m', 'synthetic unapproved instruction removal')
        head = runtime.repo.revision('HEAD')
        data['pull']['head']['sha'] = head
        data['check']['head_sha'] = data['run']['head_sha'] = head
        with patch('openharness.ci.control_authorized', return_value=False), \
                patch('openharness.provider.gh_write') as write, \
                self.assertRaisesRegex(ValueError, 'control impact'):
            runtime.integrate(7)
        write.assert_not_called()

    def test_publisher_reobserves_native_review_instead_of_reusing_success(self):
        from openharness.ci import publish, candidate_context
        from openharness.model import digest
        from tests.test_ci import ControllerTests
        fixture = ControllerTests()
        fixture.setUp()
        context = candidate_context(fixture.config, fixture.pull, {'state': 'open', 'number': 3})
        identity = digest({'context': context, 'tree': 'd' * 40, 'verification': fixture.config['verification']})
        original_api = fixture.publisher_api([fixture.pull] * 2)
        def api(path):
            if isinstance(path, str) and '/compare/' in path:
                return {'base_commit': {'sha': context['base']}, 'files': [
                    {'filename': '.harness/config.json', 'status': 'removed', 'patch': '-controller'}]}
            return original_api(path)
        writes = []
        with patch.dict('os.environ', {'GITHUB_RUN_ID': '123'}), \
                patch('openharness.ci.control_authorized', return_value=False) as approval:
            result = publish(fixture.config, {'pull_request': {'number': 7}}, 'success',
                context['head'], context['base'], 'd' * 40, identity, api, lambda *args: writes.append(args))
        approval.assert_called_once()
        self.assertEqual('failure', result['state'])
        self.assertTrue(all(row[2]['state'] == 'failure' for row in writes))

    def test_graphql_transport_rejects_mutation_and_partial_observation(self):
        from openharness.provider import gh_api
        for request in ({'query': 'mutation { deleteRepository }'}, {'query': 'query { viewer { login } }', 'other': 1}):
            with patch('openharness.provider.gh_write') as write, self.assertRaises(ValueError):
                gh_api(request)
            write.assert_not_called()
        with patch('openharness.provider.gh_write', return_value={'errors': [{'message': 'no access'}]}), self.assertRaises(ValueError):
            gh_api({'query': 'query { viewer { login } }'})

    def test_readonly_cli_uses_trusted_base_after_candidate_removes_detector_and_config(self):
        from openharness.cli import main
        from openharness.repository import bootstrap, json_text
        with tempfile.TemporaryDirectory() as temporary:
            root = make_repo(temporary)
            repo = Repository(root)
            bootstrap(repo)
            config = repo.config()
            config['verification']['controller'] = {'repository': config['repository'], 'revision': 'a' * 40}
            (root / '.harness/config.json').write_text(json_text(config))
            detector = root / 'openharness/ci.py'
            detector.parent.mkdir()
            detector.write_text('# synthetic trusted detector')
            git(root, 'add', '.')
            git(root, 'commit', '-m', 'synthetic trusted baseline')
            base = repo.revision('HEAD')
            detector.unlink()
            (root / '.harness/config.json').unlink()
            git(root, 'add', '.')
            git(root, 'commit', '-m', 'synthetic removal cannot disable base detector')
            output = io.StringIO()
            with redirect_stdout(output), patch('openharness.provider.gh_api', side_effect=AssertionError('must stay offline')):
                code = main(['--repo', str(root), 'control-impact', '--pr', '7', '--base', base, '--head', 'HEAD'])
            self.assertEqual(0, code, output.getvalue())
            result = json.loads(output.getvalue())
            self.assertFalse(result['authorized'])
            self.assertIn({'path': 'openharness/ci.py', 'operation': 'remove'}, result['impact']['changes'])
