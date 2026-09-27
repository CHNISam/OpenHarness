"""Observe actual native provenance and deployment proof, never self-attested flags."""

import json
import re
import subprocess

from .ci import WORKFLOW_PATH, CHECKOUT, PYTHON, controller_blobs, workflow_text
from .model import digest
from .provider import ProviderError, file_bytes


def producer_blobs():
    # Only code executed by `python -m openharness.ci` produces accepted evidence.
    # Observer/CLI/recovery upgrades do not replace that immutable producer.
    paths = {'openharness/__init__.py', 'openharness/ci.py', 'openharness/model.py',
             'openharness/provider.py', 'openharness/repository.py',
             'openharness/backlog.py', 'openharness/updates.py', 'openharness/adoption.py'}
    return {path: sha for path, sha in controller_blobs().items() if path in paths}


def job_log(path):
    try:
        result = subprocess.run(['gh', 'api', path], capture_output=True, text=True, encoding='utf-8', timeout=45)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProviderError('Native publisher log unavailable') from exc
    if result.returncode or len(result.stdout) > 2_000_000:
        raise ProviderError('Native publisher log unavailable, expired or too large')
    return result.stdout


def executed_baseline(config, prefix, run, api, logs):
    jobs = api(f'{prefix}/actions/runs/{int(run["id"])}/jobs?per_page=100')
    if jobs.get('total_count') != len(jobs.get('jobs', [])):
        raise ProviderError('Native job observation incomplete')
    publishers = [job for job in jobs['jobs'] if job.get('name') == 'publish' and job.get('status') == 'completed' and job.get('conclusion') == 'success']
    if len(publishers) != 1:
        raise ProviderError('Completed trusted publisher job missing')
    text = logs(f'{prefix}/actions/jobs/{int(publishers[0]["id"])}/logs')
    refs = re.findall(r'^\S+[ \t]+ref: ([0-9a-f]{40})[ \t]*\r?$', text, re.MULTILINE)
    if len(refs) != 2 or refs[1] != config['verification']['controller']['revision']:
        raise ProviderError('Executed publisher baseline/source identity unavailable')
    return refs[0]


def actions_available(permissions):
    if not isinstance(permissions, dict) or permissions.get('enabled') is not True:
        return False
    if permissions.get('allowed_actions') == 'all':
        return True
    if permissions.get('allowed_actions') != 'selected':
        return False
    selected = permissions.get('selected_actions')
    if (not isinstance(selected, dict) or type(selected.get('github_owned_allowed')) is not bool
            or type(selected.get('verified_allowed')) is not bool
            or not isinstance(selected.get('patterns_allowed'), list)
            or not all(isinstance(p, str) for p in selected['patterns_allowed'])):
        return False
    # Only the two public, GitHub-owned Actions in the fixed compiler need access.
    # Avoid interpreting provider wildcard or Marketplace verification semantics.
    return selected['github_owned_allowed'] or {f'actions/checkout@{CHECKOUT}',
        f'actions/setup-python@{PYTHON}'} <= set(selected['patterns_allowed'])


def trusted(config, raw):
    controller = config['verification'].get('controller')
    if not controller or not config['verification'].get('sandbox_image'):
        return False
    if raw.get('controller_workflow') != workflow_text():
        return False
    if raw.get('controller_blobs') != producer_blobs():
        return False
    if not any(w.get('path') == WORKFLOW_PATH and w.get('state') == 'active' for w in raw.get('workflows', {}).get('workflows', [])):
        return False
    permissions = raw.get('workflows', {}).get('permissions', {})
    if not actions_available(permissions):
        return False
    policies = raw.get('actions_policies', [])
    def all_workflows(policy):
        conditions = policy.get('conditions')
        return not conditions or conditions == {'workflow_path': {'include': ['~ALL'], 'exclude': []}} or conditions == {'workflow_path': {'include': [], 'exclude': []}}
    policy = any(p.get('enforcement') == 'active' and all_workflows(p) and any(
        r.get('type') == 'restrict_action_events' and r.get('parameters', {}).get('allowed_events') == ['pull_request_target']
        for r in p.get('rules', [])) for p in policies)
    return policy and raw.get('other_target_workflows') == [] and raw.get('canonical_config') == config


def observe_controller(config, raw, api, errors):
    controller = config['verification'].get('controller')
    if not controller:
        return
    prefix = f'repos/{config["repository"]}'
    ref = raw.get('branch', {}).get('commit', {}).get('sha')
    try:
        raw.setdefault('workflows', {})['permissions'] = api(f'{prefix}/actions/permissions')
        if not isinstance(raw['workflows']['permissions'], dict):
            raise ProviderError('Actions permissions observation malformed')
        if raw['workflows']['permissions'].get('allowed_actions') == 'selected':
            raw['workflows']['permissions']['selected_actions'] = api(f'{prefix}/actions/permissions/selected-actions')
        raw['canonical_config'] = json.loads(file_bytes(api, prefix, '.harness/config.json', ref))
        raw['controller_workflow'] = file_bytes(api, prefix, WORKFLOW_PATH, ref).decode('utf-8').replace('\r\n', '\n')
        source = f'repos/{controller["repository"]}'
        tree = api(f'{source}/git/trees/{controller["revision"]}?recursive=1')
        if tree.get('truncated'):
            raise ProviderError('Immutable source tree is truncated')
        expected = producer_blobs()
        raw['controller_blobs'] = {item['path']: item['sha'] for item in tree.get('tree', []) if item.get('path') in expected and item.get('mode') == '100644'}
        listing = api(f'{prefix}/actions/policies?per_page=100')
        if listing.get('total_count', 0) > len(listing.get('policies', [])):
            raise ProviderError('Actions policy observation is truncated')
        policies = []
        for policy in listing.get('policies', []):
            link = policy.get('_links', {}).get('self', {}).get('href')
            path = link if link and link.startswith('https://api.github.com/') else f'{prefix}/actions/policies/{int(policy["id"])}'
            policies.append(api(path))
        raw['actions_policies'] = policies
        raw['other_target_workflows'] = []
        raw['other_target_workflows'] = [path for path in raw.get('workflow_blobs', {}) if path != WORKFLOW_PATH]
    except (ProviderError, ValueError, KeyError, TypeError) as exc:
        errors.append(f'trusted controller: {exc}')


def proof_gap(reason, phase):
    return {'valid': False, 'reason': reason, 'phase': phase,
            'recovery': {'guide': 'docs/proof-recovery.md', 'automatic_activation': False,
                         'steps': ['Resolve unavailable observations and retry Doctor',
                                   'If evidence expired or substrate changed, collect fresh native deployment cases',
                                   'Commit reviewed proof, rerun Doctor and explicitly activate']}}


def observe_proof(config, observation, api, logs=job_log):
    if not observation.get('gate') or not observation.get('trusted_controller'):
        return proof_gap('Native enforcement/provenance not currently established', 'substrate')
    prefix = f'repos/{config["repository"]}'
    phase = 'manifest'
    try:
        proof = json.loads(file_bytes(api, prefix, '.harness/deployment-proof.json', observation['target_sha']))
        if proof.get('schema') != 1 or proof.get('policy') != observation['fingerprint'] or proof.get('repository') != config['repository']:
            raise ProviderError('Deployment proof scope/substrate changed')
        cases = proof.get('cases', {})
        if set(cases) != {'valid', 'invalid', 'source-spoof', 'direct-update'}:
            raise ProviderError('Complete deployment proof cases required')
        result = {}
        for name in ('valid', 'invalid', 'source-spoof'):
            phase = name
            case = cases[name]
            sha = case['head']
            if not re.fullmatch(r'[0-9a-f]{40}', sha):
                raise ProviderError('Proof subject identity malformed')
            pull = api(f'{prefix}/pulls/{int(case["pr"])}')
            if pull['head']['sha'] != sha or pull['base']['ref'] != config['target']:
                raise ProviderError('Proof PR subject/target changed')
            statuses = api(f'{prefix}/commits/{sha}/statuses?per_page=100')
            matching = [s for s in statuses if s.get('context') == config['verification']['required_check']]
            if not matching or len(statuses) >= 100:
                raise ProviderError('Proof status missing or observation truncated')
            status = matching[0]
            expected = 'success' if name == 'valid' else 'failure'
            if status.get('state') != expected or status.get('creator', {}).get('login') != 'github-actions[bot]':
                raise ProviderError('Proof result/producer invalid')
            url = status.get('target_url', '')
            match = re.fullmatch(rf'https://github.com/{re.escape(config["repository"])}/actions/runs/(\d+)', url)
            if not match:
                raise ProviderError('Proof run provenance absent')
            run = api(f'{prefix}/actions/runs/{match[1]}')
            if run.get('event') != 'pull_request_target' or run.get('path') != WORKFLOW_PATH or run.get('status') != 'completed':
                raise ProviderError('Proof did not use the trusted authoritative path')
            if run.get('head_sha') != sha:
                raise ProviderError('Native run subject differs from proof candidate')
            baseline = executed_baseline(config, prefix, run, api, logs)
            if not baseline or file_bytes(api, prefix, WORKFLOW_PATH, baseline).decode('utf-8').replace('\r\n', '\n') != workflow_text() or json.loads(file_bytes(api, prefix, '.harness/config.json', baseline)) != config:
                raise ProviderError('Historical proof controller/config differs from current trusted substrate')
            if name == 'valid':
                if not pull.get('merged') or not pull.get('merge_commit_sha'):
                    raise ProviderError('Representative legal integration not observed')
                head_tree = api(f'{prefix}/git/commits/{sha}')['tree']['sha']
                merge_tree = api(f'{prefix}/git/commits/{pull["merge_commit_sha"]}')['tree']['sha']
                if head_tree != merge_tree:
                    raise ProviderError('Integrated tree differs from verified strict candidate')
            elif pull.get('merged'):
                raise ProviderError('Invalid candidate became authoritative')
            if name != 'valid':
                denied = api(f'{prefix}/rulesets/rule-suites/{int(case["rule_suite_id"])}')
                if denied.get('result') != 'fail' or denied.get('after_sha') != sha or denied.get('ref') != f'refs/heads/{config["target"]}':
                    raise ProviderError('Invalid integration rejection not observed natively')
            result[name] = {'pr': pull['number'], 'head': sha, 'state': expected, 'run_id': int(match[1])}
            if name == 'source-spoof':
                blocked = api(f'{prefix}/actions/runs/{int(case["blocked_run"])}')
                jobs = api(f'{prefix}/actions/runs/{int(case["blocked_run"])}/jobs?per_page=100')
                if blocked.get('head_sha') != sha or blocked.get('event') not in ('push', 'pull_request') or blocked.get('conclusion') != 'startup_failure' or jobs.get('total_count') != 0:
                    raise ProviderError('Candidate-source workflow rejection before execution not observed')
                result[name]['blocked_run'] = blocked['id']
        phase = 'direct-update'
        suite = api(f'{prefix}/rulesets/rule-suites/{int(cases["direct-update"]["rule_suite_id"])}')
        if suite.get('result') != 'fail' or suite.get('ref') != f'refs/heads/{config["target"]}' or suite.get('after_sha') != cases['direct-update']['head']:
            raise ProviderError('Direct authoritative bypass rejection not observed')
        result['direct-update'] = {'rule_suite_id': suite['id'], 'result': 'fail'}
        work_result = None
        if config['profile'] == 'github-backlog-v1':
            phase = 'work-cases'
            work_result = observe_work_proof(config, proof, api, logs)
        return {'valid': True, 'cases': result, 'proof_subject': digest(proof),
                **({'work_cases': work_result} if work_result is not None else {})}
    except (ProviderError, ValueError, KeyError, TypeError) as exc:
        return proof_gap(str(exc), phase)


def observe_work_proof(config, proof, api, logs):
    """Reobserve native task-adapter rejection and stale-owner proof, not flags."""
    from .backlog import authorize, read_corpus
    reasons = {
        'wrong-executor': 'Backlog executor is not currently assigned',
        'blocked-dependency': 'Backlog dependency is not complete',
        'self-authority': 'Protected control change requires native owner approval bound to head and base',
        'invalid-completion': 'Candidate completion requires completed prerequisites',
        'stale-work': 'Backlog executor is not currently assigned',
    }
    cases = proof.get('work_cases')
    if not isinstance(cases, dict) or set(cases) != set(reasons):
        raise ProviderError('Complete native Backlog work proof cases required')
    prefix = f'repos/{config["repository"]}'
    result = {}
    for name, reason in reasons.items():
        case = cases[name]
        sha = case['head']
        if not re.fullmatch(r'[0-9a-f]{40}', sha):
            raise ProviderError('Backlog proof subject malformed')
        pull = api(f'{prefix}/pulls/{int(case["pr"])}')
        if pull['head']['sha'] != sha or pull['base']['ref'] != config['target'] or pull.get('merged'):
            raise ProviderError('Backlog rejection proof PR scope changed')
        statuses = api(f'{prefix}/commits/{sha}/statuses?per_page=100')
        matching = [s for s in statuses if s.get('context') == config['verification']['required_check']]
        if not matching or len(statuses) >= 100:
            raise ProviderError('Backlog proof status unavailable/truncated')
        status = matching[0]
        match = re.fullmatch(rf'https://github.com/{re.escape(config["repository"])}/actions/runs/(\d+)', status.get('target_url', ''))
        if status.get('state') != 'failure' or status.get('creator', {}).get('login') != 'github-actions[bot]' or not match:
            raise ProviderError('Backlog rejection proof producer invalid')
        run = api(f'{prefix}/actions/runs/{match[1]}')
        if run.get('event') != 'pull_request_target' or run.get('path') != WORKFLOW_PATH or run.get('head_sha') != sha or run.get('status') != 'completed':
            raise ProviderError('Backlog proof did not use trusted native path')
        baseline = executed_baseline(config, prefix, run, api, logs)
        if (file_bytes(api, prefix, WORKFLOW_PATH, baseline).decode('utf-8').replace('\r\n', '\n') != workflow_text()
                or json.loads(file_bytes(api, prefix, '.harness/config.json', baseline)) != config):
            raise ProviderError('Historical Backlog proof substrate differs')
        jobs = api(f'{prefix}/actions/runs/{int(run["id"])}/jobs?per_page=100')
        if jobs.get('total_count') != len(jobs.get('jobs', [])):
            raise ProviderError('Backlog verifier job observation incomplete')
        failed = [job for job in jobs['jobs'] if job.get('name') == 'verify' and job.get('conclusion') == 'failure' and job.get('status') == 'completed']
        failure_log = logs(f'{prefix}/actions/jobs/{int(failed[0]["id"])}/logs') if len(failed) == 1 else ''
        if len(failed) != 1 or not re.search(r'^\S+[ \t]+ValueError: ' + re.escape(reason) + r'[ \t]*\r?$', failure_log, re.MULTILINE):
            raise ProviderError('Native Backlog rejection reason unavailable')
        denied = api(f'{prefix}/rulesets/rule-suites/{int(case["rule_suite_id"])}')
        subject_matches = denied.get('after_sha') == sha
        if not subject_matches and re.fullmatch(r'[0-9a-f]{40}', denied.get('after_sha', '')):
            # Native PR merge rejection records the proposed merge, not its HEAD.
            # Bind both parents to the trusted run's canonical base and candidate.
            proposed = api(f'{prefix}/git/commits/{denied["after_sha"]}')
            subject_matches = (denied.get('before_sha') == baseline
                               and proposed.get('sha') == denied['after_sha']
                               and [parent.get('sha') for parent in proposed.get('parents', [])] == [baseline, sha])
        if denied.get('result') != 'fail' or not subject_matches or denied.get('ref') != f'refs/heads/{config["target"]}':
            raise ProviderError('Backlog invalid integration denial unavailable')
        if name == 'stale-work':
            accepted = api(f'{prefix}/actions/runs/{int(case["accepted_run"])}')
            if (accepted.get('event') != 'pull_request_target' or accepted.get('path') != WORKFLOW_PATH
                    or accepted.get('head_sha') != sha or accepted.get('conclusion') != 'success'
                    or accepted.get('status') != 'completed'):
                raise ProviderError('Prior legal Backlog acceptance unavailable')
            previous = executed_baseline(config, prefix, accepted, api, logs)
            if (json.loads(file_bytes(api, prefix, '.harness/config.json', previous)) != config
                    or file_bytes(api, prefix, WORKFLOW_PATH, previous).decode('utf-8').replace('\r\n', '\n') != workflow_text()):
                raise ProviderError('Prior Backlog acceptance configuration differs')
            comparison = api(f'{prefix}/compare/{previous}...{baseline}')
            if comparison.get('status') != 'ahead':
                raise ProviderError('Canonical Backlog revocation ancestry unavailable')
            old = read_corpus(config, previous, api)
            new = read_corpus(config, baseline, api)
            authorize(old, config['work'], case['task'], pull.get('user', {}).get('login'))
            if previous == baseline or old['identity'] == new['identity']:
                raise ProviderError('Canonical Backlog revocation was not observed')
            try:
                authorize(new, config['work'], case['task'], pull.get('user', {}).get('login'))
            except ValueError:
                pass
            else:
                raise ProviderError('Stale Backlog executor remains authorized')
        result[name] = {'pr': pull['number'], 'head': sha, 'run_id': run['id'], 'baseline': baseline}
    return result
