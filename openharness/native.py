"""Observe actual native provenance and deployment proof, never self-attested flags."""

import base64
import json
import re

from .ci import WORKFLOW_PATH, controller_blobs, workflow_text
from .model import digest
from .provider import ProviderError


def file_bytes(api, prefix, path, ref):
    data = api(f'{prefix}/contents/{path}?ref={ref}')
    if not isinstance(data, dict) or data.get('type') != 'file' or data.get('encoding') != 'base64':
        raise ProviderError(f'Authoritative file unavailable: {path}')
    return base64.b64decode(data['content'])


def trusted(config, raw):
    controller = config['verification'].get('controller')
    if not controller or not config['verification'].get('sandbox_image'):
        return False
    if raw.get('controller_workflow') != workflow_text():
        return False
    if raw.get('controller_blobs') != controller_blobs():
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
        raw['canonical_config'] = json.loads(file_bytes(api, prefix, '.harness/config.json', ref))
        raw['controller_workflow'] = file_bytes(api, prefix, WORKFLOW_PATH, ref).decode('utf-8').replace('\r\n', '\n')
        source = f'repos/{controller["repository"]}'
        tree = api(f'{source}/git/trees/{controller["revision"]}?recursive=1')
        if tree.get('truncated'):
            raise ProviderError('Immutable source tree is truncated')
        expected = controller_blobs()
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
        for workflow in raw.get('workflows', {}).get('workflows', []):
            if workflow.get('path') != WORKFLOW_PATH:
                content = file_bytes(api, prefix, workflow['path'], ref).decode('utf-8')
                if 'pull_request_target' in content:
                    raw['other_target_workflows'].append(workflow['path'])
    except (ProviderError, ValueError, KeyError, TypeError) as exc:
        errors.append(f'trusted controller: {exc}')


def observe_proof(config, observation, api):
    if not observation.get('gate') or not observation.get('trusted_controller'):
        return {'valid': False, 'reason': 'Native enforcement/provenance not currently established'}
    prefix = f'repos/{config["repository"]}'
    try:
        proof = json.loads(file_bytes(api, prefix, '.harness/deployment-proof.json', observation['target_sha']))
        if proof.get('schema') != 1 or proof.get('policy') != observation['fingerprint'] or proof.get('repository') != config['repository']:
            raise ProviderError('Deployment proof scope/substrate changed')
        cases = proof.get('cases', {})
        if set(cases) != {'valid', 'invalid', 'source-spoof', 'direct-update'}:
            raise ProviderError('Complete deployment proof cases required')
        result = {}
        for name in ('valid', 'invalid', 'source-spoof'):
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
            baseline = run.get('head_sha')
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
        suite = api(f'{prefix}/rulesets/rule-suites/{int(cases["direct-update"]["rule_suite_id"])}')
        if suite.get('result') != 'fail' or suite.get('ref') != f'refs/heads/{config["target"]}' or suite.get('after_sha') != cases['direct-update']['head']:
            raise ProviderError('Direct authoritative bypass rejection not observed')
        result['direct-update'] = {'rule_suite_id': suite['id'], 'result': 'fail'}
        return {'valid': True, 'cases': result, 'proof_subject': digest(proof)}
    except (ProviderError, ValueError, KeyError, TypeError) as exc:
        return {'valid': False, 'reason': str(exc)}
