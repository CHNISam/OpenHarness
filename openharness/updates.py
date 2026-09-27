"""Declarative release upgrades; Renovate proposes, native governance authorizes."""

import argparse
import copy
import hashlib
import json
import re
import subprocess
import tomllib
from pathlib import Path
from urllib.parse import quote

from . import __version__
from .provider import gh_api
from .repository import Repository, ENTRY, BACKLOG_ENTRY, json_text, safe_path

INSTALLATION = '.harness/installation.json'
REQUEST = '.harness/upgrade-request.json'
RUNTIME_ENTRY = '.harness/runtime-entry.md'
ADOPTION = '.harness/adoption.json'
MIGRATION = 'legacy-backlog-adoption-v1'
ARTIFACTS = {'.harness/AGENT.md', '.harness/github-workflow.yml.template',
             '.github/workflows/openharness.yml'}
SHA = re.compile(r'[0-9a-f]{40}')
SEMVER = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)')
SOURCE = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+')


def version(value):
    if not isinstance(value, str) or not SEMVER.fullmatch(value):
        raise ValueError('Stable exact SemVer required; mutable refs and prereleases are rejected')
    return tuple(int(part) for part in value.split('.'))


def content_hash(text):
    return hashlib.sha256(text.replace('\r\n', '\n').encode('utf-8')).hexdigest()


def manifest(compatible_from):
    from .ci import workflow_text
    for previous in compatible_from:
        version(previous)
    return {'schema': 2, 'version': __version__, 'profile': 'github-pr-v1',
            'profiles': {'github-pr-v1': ENTRY, 'github-backlog-v1': BACKLOG_ENTRY},
            'migrations': [MIGRATION],
            'compatible_from': sorted(set(compatible_from)),
            'artifacts': {'.harness/AGENT.md': ENTRY,
                          '.harness/github-workflow.yml.template': workflow_text(),
                          '.github/workflows/openharness.yml': workflow_text()}}


def validate_manifest(data, selected):
    fields = {'schema', 'version', 'profile', 'compatible_from', 'artifacts'}
    if isinstance(data, dict) and data.get('schema') == 2:
        fields |= {'profiles', 'migrations'}
    if not isinstance(data, dict) or set(data) != fields:
        raise ValueError('Invalid release manifest')
    if data['schema'] not in (1, 2) or data['profile'] != 'github-pr-v1' or data['version'] != selected:
        raise ValueError('Unsupported release schema/profile or mismatched version')
    version(selected)
    if not isinstance(data['compatible_from'], list):
        raise ValueError('Explicit compatible source versions required')
    for previous in data['compatible_from']:
        version(previous)
    if not isinstance(data['artifacts'], dict) or set(data['artifacts']) != ARTIFACTS:
        raise ValueError('Release must contain exactly the supported generated artifacts')
    texts = list(data['artifacts'].values())
    if data['schema'] == 2:
        profiles = data['profiles']
        if not isinstance(profiles, dict) or set(profiles) != {'github-pr-v1', 'github-backlog-v1'} or profiles['github-pr-v1'] != data['artifacts']['.harness/AGENT.md'] or data['migrations'] != [MIGRATION]:
            raise ValueError('Unsupported release profiles or migration protocol')
        texts += list(profiles.values())
    if not all(isinstance(text, str) and text and len(text.encode()) <= 100_000 for text in texts):
        raise ValueError('Invalid generated artifact content')
    return data


def release_artifacts(release, profile, preserved=False):
    data = validate_manifest(release['manifest'], release['version'])
    result = dict(data['artifacts'])
    if profile != 'github-pr-v1':
        if data['schema'] != 2 or profile not in data['profiles']:
            raise ValueError('Release does not support installed profile')
        result['.harness/AGENT.md'] = data['profiles'][profile]
    if preserved:
        result[RUNTIME_ENTRY] = result.pop('.harness/AGENT.md')
    return result


def validate_installation(data, config):
    fields = {'schema', 'repository', 'version', 'revision', 'artifacts'}
    if isinstance(data, dict) and data.get('schema') == 2:
        fields |= {'profile', 'project_artifacts', 'adoption'}
    if not isinstance(data, dict) or set(data) != fields or data['schema'] not in (1, 2):
        raise ValueError('Invalid installation identity')
    version(data['version'])
    if not isinstance(data['repository'], str) or not SOURCE.fullmatch(data['repository']):
        raise ValueError('Invalid installation source')
    if not isinstance(data['revision'], str) or not SHA.fullmatch(data['revision']):
        raise ValueError('Installation execution must pin an immutable SHA')
    expected = {'repository': data['repository'], 'revision': data['revision']}
    if config['verification'].get('controller') != expected:
        raise ValueError('Installed release and runtime controller pin differ')
    hashes = data['artifacts']
    preserved = data.get('project_artifacts', {})
    if data['schema'] == 2:
        if data['profile'] != config['profile'] or not isinstance(preserved, dict) or (preserved and set(preserved) != {'.harness/AGENT.md', 'AGENTS.md'}):
            raise ValueError('Invalid installed profile/project ownership')
        if (preserved and (config['profile'] != 'github-backlog-v1' or not isinstance(data['adoption'], str) or not re.fullmatch(r'[0-9a-f]{64}', data['adoption']))) or (not preserved and data['adoption'] is not None):
            raise ValueError('Explicit adoption provenance required')
    elif config['profile'] != 'github-pr-v1':
        raise ValueError('Legacy release identity does not support Backlog')
    entry = RUNTIME_ENTRY if preserved else '.harness/AGENT.md'
    supported = (ARTIFACTS - {'.harness/AGENT.md'} | {RUNTIME_ENTRY}) if preserved else ARTIFACTS
    if not isinstance(hashes, dict) or not {entry, '.harness/github-workflow.yml.template'} <= set(hashes) or set(hashes) - supported:
        raise ValueError('Invalid installed generated artifact set')
    if not all(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) for value in [*hashes.values(), *preserved.values()]):
        raise ValueError('Invalid generated artifact hashes')
    return data


class Releases:
    def __init__(self, repository, api=gh_api):
        if not isinstance(repository, str) or not SOURCE.fullmatch(repository):
            raise ValueError('Invalid release repository')
        self.repository, self.api = repository, api
        self.prefix = f'repos/{repository}'

    def resolve(self, selected):
        version(selected)
        tag = f'v{selected}'
        release = self.api(f'{self.prefix}/releases/tags/{tag}')
        if not isinstance(release, dict) or release.get('tag_name') != tag or release.get('draft') is not False or release.get('prerelease') is not False or release.get('immutable') is not True:
            raise ValueError('Trusted stable immutable GitHub release required')
        reference = self.api(f'{self.prefix}/git/ref/tags/{tag}')
        obj = reference['object']
        seen = set()
        while obj.get('type') == 'tag':
            sha = obj.get('sha')
            if not isinstance(sha, str) or not SHA.fullmatch(sha) or sha in seen or len(seen) >= 8:
                raise ValueError('Invalid annotated release tag')
            seen.add(sha)
            obj = self.api(f'{self.prefix}/git/tags/{sha}')['object']
        revision = obj.get('sha')
        if obj.get('type') != 'commit' or not isinstance(revision, str) or not SHA.fullmatch(revision):
            raise ValueError('Release tag must resolve to an immutable commit SHA')
        from .provider import file_bytes
        data = json.loads(file_bytes(self.api, self.prefix, 'openharness-release.json', revision))
        validate_manifest(data, selected)
        source_version = file_bytes(self.api, self.prefix, 'openharness/__init__.py', revision).decode('utf-8')
        if not re.search(r"^__version__ = ['\"]" + re.escape(selected) + r"['\"]\s*$", source_version, re.MULTILINE):
            raise ValueError('Release manifest and immutable tool version differ')
        package = tomllib.loads(file_bytes(self.api, self.prefix, 'pyproject.toml', revision).decode('utf-8'))
        if package.get('project', {}).get('name') != 'openharness' or package['project'].get('version') != selected:
            raise ValueError('Release package identity/version differs from immutable tool')
        # Re-observe the immutable release and ref rather than trusting a torn read.
        if self.api(f'{self.prefix}/releases/tags/{tag}') != release or self.api(f'{self.prefix}/git/ref/tags/{tag}') != reference:
            raise ValueError('Release identity changed during observation')
        return {'repository': self.repository, 'version': selected, 'revision': revision, 'manifest': data}

    def discover(self, installed):
        current = version(installed)
        candidates = set()
        # Explicit pagination: no truncated list can masquerade as complete discovery.
        for page in range(1, 101):
            rows = self.api(f'{self.prefix}/releases?per_page=100&page={page}')
            if not isinstance(rows, list):
                raise ValueError('Incomplete release observation')
            for row in rows:
                tag = row.get('tag_name', '')
                if row.get('draft') is False and row.get('prerelease') is False and row.get('immutable') is True and isinstance(tag, str) and tag.startswith('v') and SEMVER.fullmatch(tag[1:]) and version(tag[1:]) > current:
                    candidates.add(tag[1:])
            if len(rows) < 100:
                break
        else:
            raise ValueError('Release pagination limit reached')
        return [self.resolve(value) for value in sorted(candidates, key=version)]


def compatible(previous, release):
    old, new = version(previous), version(release['version'])
    if new < old:
        raise ValueError('Downgrade requires an explicit governed revert and re-proof')
    if new == old:
        return 'same'
    if new[0] != old[0] or (old[0] == 0 and new[1] != old[1]):
        raise ValueError('Major/pre-1.0 minor upgrade requires a dedicated migration')
    if previous not in release['manifest']['compatible_from']:
        raise ValueError('Release does not explicitly support this installed source version')
    return 'minor' if new[1] != old[1] else 'patch'


def plan(config, installed, release, read, *, rollback=False):
    """Pure deterministic migration; read is bound to the baseline checkout."""
    controller = config['verification'].get('controller')
    if not controller or release['repository'] != controller['repository']:
        raise ValueError('Upgrade source must remain the project trusted controller repository')
    validate_manifest(release['manifest'], release['version'])
    project = installed.get('project_artifacts', {}) if installed else {}
    if project and content_hash(read(ADOPTION) or '') != installed['adoption']:
        raise ValueError('Reviewed adoption declaration drift')
    artifacts = release_artifacts(release, config['profile'], bool(project))
    for path in project:
        if read(path) is None:
            raise ValueError(f'Project-owned instruction missing: {path}')
    if not SHA.fullmatch(release['revision']):
        raise ValueError('Upgrade revision must be an immutable SHA')
    if installed is None:
        if controller['revision'] != release['revision']:
            raise ValueError('Enrollment requires the already pinned release revision')
        kind = 'enrollment'
        paths = {path for path in ARTIFACTS if read(path) is not None}
        if not {'.harness/AGENT.md', '.harness/github-workflow.yml.template'} <= paths:
            raise ValueError('Enrollment requires installed compiler artifacts')
    else:
        validate_installation(installed, config)
        if rollback:
            if version(release['version']) >= version(installed['version']):
                raise ValueError('Rollback requires a previous installed release')
            kind = 'rollback'
        else:
            kind = compatible(installed['version'], release)
        if kind == 'same' and installed['revision'] != release['revision']:
            raise ValueError('Published version cannot change immutable revision')
        paths = set(installed['artifacts'])
    changes, hashes = {}, {}
    for path in sorted(paths):
        old = read(path)
        expected = (installed['artifacts'][path] if installed else content_hash(artifacts[path]))
        if old is None or content_hash(old) != expected:
            raise ValueError(f'Project-owned/generated artifact conflict: {path}; no files changed')
        new = artifacts[path]
        hashes[path] = content_hash(new)
        if old.replace('\r\n', '\n') != new.replace('\r\n', '\n'):
            changes[path] = new
    proposed = copy.deepcopy(config)
    proposed['verification']['controller']['revision'] = release['revision']
    if proposed != config:
        changes['.harness/config.json'] = json_text(proposed)
    identity = {'schema': 1, 'repository': release['repository'], 'version': release['version'],
                'revision': release['revision'], 'artifacts': hashes}
    if release['manifest']['schema'] == 2:
        identity.update(schema=2, profile=config['profile'], project_artifacts=project, adoption=installed.get('adoption') if installed else None)
    for path, text in ((INSTALLATION, json_text(identity)), (REQUEST, json_text({'version': release['version']}))):
        if read(path) != text:
            changes[path] = text
    return {'kind': kind, 'installation': identity, 'changes': changes, 'activated': False,
            'next': 'Governed merge, fresh deployment proof, Doctor and explicit activate required'}


def git_text(repo, *args):
    result = subprocess.run(['git', '-C', str(repo.root), *args], capture_output=True,
                            text=True, encoding='utf-8', timeout=60)
    if result.returncode:
        raise ValueError('Git baseline read failed: ' + result.stderr.strip())
    return result.stdout


def read_files(repo):
    def read(path):
        value = safe_path(repo.root, path)
        return value.read_text(encoding='utf-8') if value.is_file() else None
    return read


def apply(repo, changes):
    """All-path validation before writes; restore bytes on any write failure."""
    backups = {path: (safe_path(repo.root, path).read_bytes() if safe_path(repo.root, path).exists() else None) for path in changes}
    written = []
    try:
        for path, content in changes.items():
            target = safe_path(repo.root, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            written.append(path)
            target.write_text(content, encoding='utf-8', newline='\n')
    except BaseException:
        for path in reversed(written):
            target = safe_path(repo.root, path)
            previous = backups[path]
            if previous is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(previous)
        raise


def installed(repo):
    data = read_files(repo)(INSTALLATION)
    return validate_installation(json.loads(data), repo.config()) if data is not None else None


def installation_observation(repo):
    data = installed(repo)
    if data is not None:
        if data['version'] != __version__:
            raise ValueError('Executing CLI version differs from installed release; use the reviewed pinned CLI')
        read = read_files(repo)
        request = json.loads(read(REQUEST) or '{}')
        if request != {'version': data['version']}:
            raise ValueError('Upgrade request is not materialized in the installed release')
        if data.get('project_artifacts'):
            if content_hash(read(ADOPTION) or '') != data['adoption']:
                raise ValueError('Reviewed adoption declaration changed')
        # Project ownership records the reviewed adoption snapshot, not a content lock.
        # Later project edits use normal control approval and invalidate Doctor controls.
        for path in data.get('project_artifacts', {}):
            if read(path) is None:
                raise ValueError(f'Project-owned instruction missing: {path}')
        for path, expected in data['artifacts'].items():
            text = read(path)
            if text is None or content_hash(text) != expected:
                raise ValueError(f'Installed generated artifact changed: {path}')
    return data


def renovate_config(repository, issue=None, task=None):
    if not SOURCE.fullmatch(repository) or (issue is None) == (task is None):
        raise ValueError('Trusted source and exactly one existing upgrade work item required')
    if task is not None:
        from .backlog import task_id
        reference = task_id(task)
        branch_prefix = f'codex/backlog-{reference}-'
        work_line = f'Work-Item: {reference}'
    else:
        if type(issue) is not int or issue <= 0:
            raise ValueError('Positive existing upgrade Issue required')
        branch_prefix = f'codex/{issue}-'
        work_line = f'Work-Item: #{issue}'
    return {'dependencyDashboard': False, 'customManagers': [{'customType': 'regex', 'managerFilePatterns': ['/\\.harness/upgrade-request\\.json$/'],
             'matchStrings': ['"version"\\s*:\\s*"(?<currentValue>[0-9]+\\.[0-9]+\\.[0-9]+)"'],
             'datasourceTemplate': 'github-releases', 'depNameTemplate': repository,
             'versioningTemplate': 'semver', 'extractVersionTemplate': '^v(?<version>.*)$'}],
            'packageRules': [{'matchManagers': ['custom.regex'], 'matchDepNames': [repository],
                'automerge': False, 'ignoreUnstable': True,
                'branchPrefix': branch_prefix, 'branchTopic': 'openharness-{{{newMajor}}}-{{{newMinor}}}-{{{newPatch}}}',
                'prBodyNotes': [work_line, 'Owner approval on exact head/base and fresh deployment proof are required.'],
                'postUpgradeTasks': {'commands': ['openharness-upgrade-prepare'], 'executionMode': 'branch',
                    'fileFilters': [INSTALLATION, REQUEST, '.harness/config.json', *sorted(ARTIFACTS), RUNTIME_ENTRY]}}]}


def prepare(repo, api=gh_api):
    """Renovate adapter: baseline owns input; proposed request is never authority.

    This stages a PR checkout only. It grants no lifecycle/merge/activation authority.
    The old pinned executable must be supplied by the self-hosted runner operator.
    """
    from .model import validate_config
    tracked = repo.git('ls-tree', '-r', '--name-only', 'HEAD').splitlines()
    def baseline(path):
        return git_text(repo, 'show', f'HEAD:{path}') if path in tracked else None
    config = validate_config(json.loads(baseline('.harness/config.json')))
    identity = json.loads(baseline(INSTALLATION))
    validate_installation(identity, config)
    if identity['version'] != __version__:
        raise ValueError('Renovate preparer must execute the old installed release version')
    request = json.loads(read_files(repo)(REQUEST))
    if set(request) != {'version'}:
        raise ValueError('Upgrade request must contain one exact version')
    selected = request['version']
    release = Releases(identity['repository'], api).resolve(selected)
    proposal = plan(config, identity, release, baseline)
    # Reject unrelated edits; permit repeat execution of this exact proposal.
    allowed = {**proposal['changes'], REQUEST: json_text(request)}
    for path in git_text(repo, 'status', '--porcelain', '--untracked-files=all', '-z').split('\0'):
        if not path:
            continue
        if len(path) < 4 or path[:2] not in (' M', '??'):
            raise ValueError('Renovate preparation requires unstaged dependency-only edits')
        relative = path[3:]
        if relative not in allowed or read_files(repo)(relative) != allowed[relative]:
            raise ValueError(f'Unexpected proposal checkout edit: {relative}')
    apply(repo, proposal['changes'])
    return proposal


def validate_candidate(repo, base, api=gh_api):
    paths = repo.git('ls-tree', '-r', '--name-only', base).splitlines()
    def baseline(path):
        return git_text(repo, 'show', f'{base}:{path}') if path in paths else None
    config = json.loads(baseline('.harness/config.json'))
    original_text = baseline(INSTALLATION)
    original = json.loads(original_text) if original_text is not None else None
    current = installed(repo)
    if original is None:
        if current is not None and current.get('adoption'):
            from .adoption import validate_candidate as validate_adoption
            validate_adoption(repo, base, api)
            return
        if current is None:
            return
        release = Releases(config['verification']['controller']['repository'], api).resolve(current['version'])
        expected = plan(config, None, release, baseline)
        for path, wanted in expected['changes'].items():
            if read_files(repo)(path) != wanted:
                raise ValueError(f'Enrollment candidate differs from pinned release: {path}')
        installation_observation(repo)
        return
    if current == original:
        installation_observation(repo)
        return
    if current is None:
        raise ValueError('Upgrade cannot remove installed immutable release identity')
    release = Releases(original['repository'], api).resolve(current['version'])
    rollback = version(current['version']) < version(original['version'])
    if rollback:
        # Only an exact previously canonical identity may use the native revert path.
        history = repo.git('log', '--first-parent', '--max-count=1000', '--format=%H', base, '--', INSTALLATION).splitlines()
        known = False
        for commit in history:
            recorded = git_text(repo, 'show', f'{commit}:{INSTALLATION}')
            if json.loads(recorded) == current:
                known = True
                break
        if not known:
            raise ValueError('Rollback identity must have been installed on canonical first-parent ancestry')
    expected = plan(config, original, release, baseline, rollback=rollback)
    if original.get('project_artifacts') and repo.git('diff', '--name-only', '--no-renames', base, '--', *sorted(original['project_artifacts'])):
        raise ValueError('Upgrade must preserve baseline project instruction bytes/modes')
    read = read_files(repo)
    for path in {INSTALLATION, REQUEST, '.harness/config.json', *original['artifacts'], *original.get('project_artifacts', {}), ADOPTION}:
        wanted = expected['changes'].get(path, baseline(path))
        if read(path) != wanted:
            raise ValueError(f'Upgrade candidate differs from verified migration: {path}')


def prepare_main():
    print(json_text(prepare(Repository('.'))), end='')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    release = sub.add_parser('manifest')
    release.add_argument('--compatible-from', action='append', default=[])
    preset = sub.add_parser('renovate')
    preset.add_argument('--source', required=True)
    work_item = preset.add_mutually_exclusive_group(required=True)
    work_item.add_argument('--issue', type=int)
    work_item.add_argument('--task')
    adoption = sub.add_parser('adoption-plan')
    adoption.add_argument('--repo', default='.')
    adoption.add_argument('--work-config', required=True)
    discovery = sub.add_parser('discover')
    discovery.add_argument('--repo', default='.')
    args = parser.parse_args()
    if args.action == 'manifest':
        output = manifest(args.compatible_from)
    elif args.action == 'renovate':
        output = renovate_config(args.source, args.issue, args.task)
    elif args.action == 'adoption-plan':
        from .adoption import declaration
        repo = Repository(args.repo)
        work = json.loads(safe_path(repo.root, args.work_config).read_text(encoding='utf-8'))
        output = declaration(repo.config(), work, read_files(repo))
    else:
        identity = installed(Repository(args.repo))
        if identity is None:
            raise ValueError('Enroll an immutable release before discovery')
        output = Releases(identity['repository']).discover(identity['version'])
    print(json_text(output), end='')


if __name__ == '__main__':
    main()
