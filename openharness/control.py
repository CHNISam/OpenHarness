"""Exact-impact extension of the existing native control approval mechanism."""
from pathlib import PurePosixPath
import json

from .model import digest


def local_changes(repo, base, head):
    records = repo.git_paths('--no-replace-objects', 'diff', '--name-status',
                             '--no-renames', '-z', base, head)
    if len(records) % 2:
        raise ValueError('Incomplete control change observation')
    changes = []
    for status, path in zip(records[::2], records[1::2]):
        operation = {'A': 'add', 'D': 'remove', 'M': 'modify', 'T': 'modify'}.get(status)
        if operation is None:
            raise ValueError('Unknown control change operation')
        row = {'path': path, 'operation': operation}
        if dependency_manifest(path):
            row['patch'] = repo.git('--no-replace-objects', 'diff', '--no-ext-diff',
                '--no-textconv', '--no-renames', base, head, '--', path)
            if 'Binary files ' in row['patch'] or 'GIT binary patch' in row['patch']:
                row['patch'] = None
        changes.append(row)
    return changes


def dependency_manifest(path):
    name = PurePosixPath(path).name.lower()
    return (name in ('pyproject.toml', 'package.json', 'package-lock.json', 'uv.lock', 'poetry.lock')
            or name.startswith('requirements') and name.endswith('.txt'))


def impact_statement(config, context, changes):
    from .ci import control_change
    affected = []
    for row in changes:
        path, operation = row['path'], row['operation']
        if operation not in ('add', 'remove', 'modify'):
            raise ValueError('Unknown control impact')
        patch = row.get('patch')
        # Missing/truncated manifest patches cannot establish preservation.
        dependency = dependency_manifest(path) and (patch is None or 'openharness' in patch.lower())
        if control_change(config, [path]) or dependency:
            affected.append({'path': path, 'operation': operation})
    if not affected:
        return None
    return {'schema': 1, 'repository': config['repository'], 'pr': int(context['pr']),
            'head': context['head'], 'base': context['base'],
            'changes': sorted(affected, key=lambda row: (row['path'], row['operation']))}


def review_marker(impact):
    return (f'OpenHarness-Control-Approval: {impact["repository"]} #{impact["pr"]} '
            f'{impact["head"]} {impact["base"]} {digest(impact)}')


def approved_review(config, context, impact, api, *, mutating=False):
    """Native review, including edit/dismissal state; never write an approval.

    A same-account PR cannot self-review. An executor authenticated as the approval
    owner remains an authorization OPEN GAP even if the username matches.
    """
    owner, name = config['repository'].split('/')
    query = ('query { viewer { login } repository(owner: ' + json.dumps(owner) +
             ', name: ' + json.dumps(name) + ') { pullRequest(number: ' + str(int(context['pr'])) +
             ') { headRefOid baseRefOid author { login } reviews(first: 100) { '
             'pageInfo { hasNextPage } nodes { id state body submittedAt lastEditedAt '
             'isMinimized viewerDidAuthor author { login __typename } commit { oid } } } } } }')
    response = api({'query': query})
    if response.get('errors'):
        raise ValueError('Native control review observation unavailable')
    try:
        data = response['data']
        pull = data['repository']['pullRequest']
        reviews = pull['reviews']
        author = pull['author']['login'].lower()
        if (pull['headRefOid'] != context['head'] or pull['baseRefOid'] != context['base'] or
                reviews['pageInfo']['hasNextPage'] is not False or not author or author == owner.lower()):
            return False
        if mutating and (not data['viewer']['login'] or data['viewer']['login'].lower() == owner.lower()):
            raise ValueError('Authorization identity OPEN GAP: executor can authenticate as approval owner')
        owned = [row for row in reviews['nodes'] if row.get('author') and
                 row['author'].get('login', '').lower() == owner.lower()]
        if not owned:
            return False
        last_time = max(row.get('submittedAt') or '' for row in owned)
        latest = [row for row in owned if row.get('submittedAt') == last_time]
        if len(latest) != 1:
            return False
        row = latest[0]
        return (row['author']['__typename'] == 'User' and row['state'] == 'APPROVED' and
                row['commit']['oid'] == context['head'] and row['lastEditedAt'] is None and
                row['isMinimized'] is False and row['viewerDidAuthor'] is False and
                row['body'] == review_marker(impact))
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('Incomplete native control review observation') from error


def require_approval(repo, config, context, api, *, mutating=True):
    from .ci import control_authorized
    impact = impact_statement(config, context, local_changes(repo, context['base'], context['head']))
    if impact and not control_authorized(config, context, api, impact=impact, mutating=mutating):
        raise ValueError('Authorization OPEN GAP: exact control impact requires independent native owner review: ' +
                         json.dumps(impact, ensure_ascii=False, sort_keys=True))
    return impact


def remote_changes(config, context, api):
    comparison = api(f'repos/{config["repository"]}/compare/{context["base"]}...{context["head"]}')
    files = comparison.get('files')
    # GitHub compare responses expose at most 300 changed files, even with commit pagination.
    if (not isinstance(files, list) or len(files) >= 300 or
            comparison.get('base_commit', {}).get('sha') != context['base']):
        raise ValueError('Incomplete native control diff observation')
    changes = []
    for row in files:
        status, path = row['status'], row['filename']
        if status == 'renamed':
            changes.append({'path': row['previous_filename'], 'operation': 'remove', 'patch': row.get('patch')})
            status = 'added'
        operation = {'added': 'add', 'removed': 'remove', 'modified': 'modify',
                     'changed': 'modify', 'copied': 'add'}.get(status)
        if operation is None:
            raise ValueError('Unknown native control diff operation')
        changes.append({'path': path, 'operation': operation, 'patch': row.get('patch')})
    return changes
