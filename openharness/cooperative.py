"""Small cooperative PR path using existing work authority, project CI and GitHub."""

import subprocess

from .ci import work_reference


def integrate(runtime, pr):
    from .provider import gh_write
    repo, provider = runtime.repo, runtime.provider
    config = repo.config()
    preflight = runtime.preflight()
    binding = preflight['workspace']
    prefix = f'repos/{config["repository"]}'
    pull = provider.api(f'{prefix}/pulls/{int(pr)}')
    head, base = pull['head']['sha'], pull['base']['sha']
    if (pull.get('state') != 'open' or pull.get('draft') or
            pull['base']['ref'] != config['target'] or
            pull['head']['repo']['full_name'].lower() != config['repository'].lower() or
            pull['head']['ref'] != binding['branch'] or head != repo.revision('HEAD') or
            work_reference(config, pull) != binding['work_item'] or repo.git('status', '--porcelain')):
        raise ValueError('Integration requires the exact clean bound project PR and work item')
    if config['profile'] == 'github-backlog-v1' and (preflight['work']['actor'] != pull['user']['login'].lower() or preflight['work']['revision'] != base):
        raise ValueError('Canonical Backlog executor or work revision differs from PR')
    if preflight['target'] != base:
        raise ValueError('Integration candidate base is stale')
    runtime.canonical_config(config, base)
    repo.git('merge-base', '--is-ancestor', base, head)
    candidate = runtime._verification_candidate(head, base)
    if candidate['tree'] != repo.git('rev-parse', 'HEAD^{tree}'):
        raise ValueError('PR head differs from the intended integration result')
    workflow = config['verification'].get('workflow')
    if not workflow:
        raise ValueError('Configure the existing CI workflow before integration')
    if repo.git('rev-parse', f'{base}:{workflow}') != repo.git('rev-parse', f'{head}:{workflow}'):
        raise ValueError('CI workflow changes require independent project review; candidate cannot authorize its own producer')
    accepted = provider.acceptance(config, pull)
    # Re-observe exact subjects immediately before writing; the provider SHA condition
    # fences head drift. There is no atomic base condition in GitHub PR merge.
    current = provider.api(f'{prefix}/pulls/{int(pr)}')
    subject = lambda row: (row.get('state'), row.get('draft'), row.get('body'), row.get('head'), row.get('base'), row.get('user', {}).get('login'))
    if subject(current) != subject(pull) or provider.target(config) != base:
        raise ValueError('PR or canonical base changed before integration')
    command = config.get('integration_command')
    command_error = None
    if command:
        argv = [v.replace('{pr}', str(pr)).replace('{work_item}', str(binding.get('project_work_item', binding['work_item']))) for v in command]
        try:
            process = subprocess.run(argv, cwd=repo.root, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
            if process.returncode:
                command_error = f'project command exited {process.returncode}: {process.stderr[-1000:]}'
        except (OSError, subprocess.TimeoutExpired) as exc:
            command_error = f'project command outcome uncertain: {type(exc).__name__}'
        # A command exit code is not authority. Independently observe the native PR.
    else:
        try:
            result = gh_write(f'{prefix}/pulls/{pr}/merge', 'PUT', {'sha': head, 'merge_method': 'merge'})
            if not result.get('merged'):
                raise ValueError('Native integration rejected: ' + str(result.get('message')))
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            command_error = f'Native merge response uncertain: {exc}'
    try:
        merged = provider.api(f'{prefix}/pulls/{int(pr)}')
    except (ValueError, KeyError, TypeError) as exc:
        runtime.break_glass_after_integration(None, 'Native merge outcome unobservable; inspect remote before retrying')
        raise ValueError('Native merge outcome unobservable; inspect remote before retrying') from exc
    if not merged.get('merged') or not merged.get('merge_commit_sha'):
        raise ValueError(command_error or 'Native PR merge was not confirmed; inspect remote before retrying')
    sha = merged['merge_commit_sha']
    try:
        commit = provider.api(f'{prefix}/git/commits/{sha}')
        if (commit['tree']['sha'] != candidate['tree'] or
                [p['sha'] for p in commit['parents']] != [base, head] or
                provider.target(config) != sha or command_error):
            raise ValueError(command_error or 'merged parents/tree or current target differ from verified candidate')
    except (ValueError, KeyError, TypeError) as exc:
        runtime.break_glass_after_integration(sha, str(exc))
        raise ValueError(f'PR already merged as {sha}; inspection required: {exc}') from exc
    from .runtime import now
    record = {'pr': pr, 'head': head, 'base': base, 'commit': sha, 'tree': candidate['tree'], 'ci': accepted}
    state = runtime.state()
    state['workspaces'][str(repo.root)]['integrated'] = record
    state['events'].append({'time': now(), 'transition': 'INTEGRATE', **record})
    runtime.save_state(state)
    return {'merged': True, 'sha': sha, 'mode': 'cooperative', 'ci': accepted,
            'closure': False, 'server_enforced': False,
            'limitations': ['Administrators/writers can bypass client checks; base races are detected after merge, not atomically prevented']}
