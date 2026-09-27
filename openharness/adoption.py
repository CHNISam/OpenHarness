"""Explicit reviewed adoption of legacy Backlog installations; no authority inference."""

import copy
import json

from .backlog import local_corpus, validate_work
from .model import digest, validate_config
from .repository import json_text
from .updates import (ADOPTION, ARTIFACTS, INSTALLATION, MIGRATION, REQUEST,
                      RUNTIME_ENTRY, Releases, content_hash, git_text,
                      installed, read_files, release_artifacts, validate_installation, validate_manifest)

PROJECT = {'.harness/AGENT.md', 'AGENTS.md'}


def declaration(config, work, read):
    """Produce review input only; hashes never imply ownership without owner review."""
    validate_config(config)
    validate_work(work)
    if config['profile'] != 'github-pr-v1' or not config['verification'].get('controller'):
        raise ValueError('Legacy staged Issue-profile configuration with immutable controller required')
    if read(INSTALLATION) is not None or read(REQUEST) is not None or read(RUNTIME_ENTRY) is not None:
        raise ValueError('Legacy adoption conflicts with existing release/runtime metadata')
    from .ci import workflow_text
    for path in ARTIFACTS - {'.harness/AGENT.md'}:
        if read(path) is not None and content_hash(read(path)) != content_hash(workflow_text()):
            raise ValueError(f'Custom compiler artifact requires separate ownership migration: {path}')
    generated = {path: content_hash(read(path)) for path in sorted(ARTIFACTS - {'.harness/AGENT.md'}) if read(path) is not None}
    if '.harness/github-workflow.yml.template' not in generated or any(read(path) is None for path in PROJECT) or '.harness/AGENT.md' not in (read('AGENTS.md') or ''):
        raise ValueError('Complete explicit legacy ownership required')
    return {'schema': 1, 'migration': MIGRATION, 'config': digest(config),
            'work': copy.deepcopy(work),
            'project_artifacts': {path: content_hash(read(path)) for path in sorted(PROJECT)},
            'generated_artifacts': generated}


def plan(config, release, read):
    raw = read(ADOPTION)
    if raw is None:
        raise ValueError('Commit and review explicit adoption declaration before migration')
    reviewed = json.loads(raw)
    if not isinstance(reviewed, dict) or set(reviewed) != {'schema', 'migration', 'config', 'work', 'project_artifacts', 'generated_artifacts'}:
        raise ValueError('Invalid adoption declaration')
    if reviewed != declaration(config, reviewed['work'], read):
        raise ValueError('Legacy configuration/ownership conflicts with reviewed adoption')
    if raw != json_text(reviewed):
        raise ValueError('Adoption declaration must use canonical compiler serialization')
    data = validate_manifest(release['manifest'], release['version'])
    if data.get('schema') != 2 or MIGRATION not in data.get('migrations', []):
        raise ValueError('Release does not explicitly support legacy Backlog adoption')
    controller = config['verification']['controller']
    if release['repository'] != controller['repository']:
        raise ValueError('Adoption must retain the explicitly trusted producer repository')
    proposed = copy.deepcopy(config)
    proposed['profile'] = 'github-backlog-v1'
    proposed['authorities']['work'] = 'repository-backlog'
    proposed['work'] = copy.deepcopy(reviewed['work'])
    proposed['verification']['controller']['revision'] = release['revision']
    validate_config(proposed)
    artifacts = release_artifacts(release, proposed['profile'], preserved=True)
    paths = set(reviewed['generated_artifacts']) | {RUNTIME_ENTRY}
    changes = {path: artifacts[path] for path in sorted(paths)}
    hashes = {path: content_hash(changes[path]) for path in sorted(paths)}
    identity = {'schema': 2, 'repository': release['repository'], 'version': release['version'],
                'revision': release['revision'], 'profile': proposed['profile'], 'artifacts': hashes,
                'project_artifacts': reviewed['project_artifacts'], 'adoption': content_hash(raw)}
    validate_installation(identity, proposed)
    changes.update({'.harness/config.json': json_text(proposed), INSTALLATION: json_text(identity),
                    REQUEST: json_text({'version': release['version']})})
    return {'kind': MIGRATION, 'installation': identity, 'changes': changes,
            'activated': False, 'next': 'Governed review/integration, native deployment re-proof, Doctor and explicit activation required'}


def baseline_reader(repo, revision):
    paths = {}
    for row in repo.git('ls-tree', '-r', '-z', revision).split('\0'):
        if row:
            metadata, path = row.split('\t', 1)
            mode, kind, sha = metadata.split(' ')
            paths[path] = (mode, kind)
    def read(path):
        if path not in paths:
            return None
        if paths[path] not in (('100644', 'blob'), ('100755', 'blob')):
            raise ValueError(f'Adoption controls must be regular committed files: {path}')
        return git_text(repo, 'show', f'{revision}:{path}')
    return read


def proposal(repo, selected, api):
    baseline = baseline_reader(repo, 'HEAD')
    config = validate_config(json.loads(baseline('.harness/config.json')))
    if baseline(INSTALLATION) is not None:
        from .updates import installation_observation
        identity = installation_observation(repo)
        release = Releases(identity['repository'], api).resolve(selected)
        if identity.get('adoption') is None or identity['version'] != selected or identity['revision'] != release['revision']:
            raise ValueError('Already adopted installation requires normal governed release upgrade')
        expected = release_artifacts(release, config['profile'], preserved=True)
        if any(baseline(path) != expected[path] for path in identity['artifacts']):
            raise ValueError('Adopted compiler artifacts differ from published release')
        if repo.git('status', '--porcelain'):
            raise ValueError('Committed adoption repeat requires a clean worktree')
        local_corpus(repo, 'HEAD', config['work'])
        return {'kind': MIGRATION, 'installation': identity, 'changes': {}, 'activated': False,
                'next': 'Governed review/integration, native deployment re-proof, Doctor and explicit activation required'}
    release = Releases(config['verification']['controller']['repository'], api).resolve(selected)
    result = plan(config, release, baseline)
    local_corpus(repo, 'HEAD', json.loads(baseline(ADOPTION))['work'])
    read = read_files(repo)
    # Permit only an exact interrupted/repeated application of this same proposal.
    allowed = set(result['changes'])
    for row in git_text(repo, 'status', '--porcelain', '--untracked-files=all', '-z').split('\0'):
        if not row:
            continue
        if len(row) < 4 or row[:2] not in (' M', '??') or row[3:] not in allowed or read(row[3:]) != result['changes'][row[3:]]:
            raise ValueError('Adoption requires a clean baseline or this exact unstaged proposal')
    return result


def validate_candidate(repo, base, api):
    baseline = baseline_reader(repo, base)
    original = validate_config(json.loads(baseline('.harness/config.json')))
    current = installed(repo)
    if current is None or not current.get('adoption'):
        raise ValueError('Adoption candidate requires complete installation identity')
    release = Releases(original['verification']['controller']['repository'], api).resolve(current['version'])
    expected = plan(original, release, baseline)
    local_corpus(repo, base, json.loads(baseline(ADOPTION))['work'])
    read = read_files(repo)
    if repo.git('diff', '--name-only', '--no-renames', base, '--', *sorted(PROJECT), ADOPTION):
        raise ValueError('Adoption must preserve committed project instruction bytes/modes and declaration')
    for path in {*expected['changes'], *PROJECT, ADOPTION}:
        wanted = expected['changes'].get(path, baseline(path))
        if read(path) != wanted:
            raise ValueError(f'Candidate differs from independently verified adoption: {path}')
    # Pin/metadata agreement and compiler entry are validated from the published release,
    # independent of the CLI version executing this baseline verifier.
    if current != expected['installation']:
        raise ValueError('Adoption installation identity differs from reviewed plan')
