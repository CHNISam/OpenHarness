"""Read-only native GitHub observation. Unobservable is never equivalent to absent."""

import base64
import json
import subprocess
from urllib.parse import quote

from .model import digest


class ProviderError(ValueError):
    pass


def gh_write(path, method, payload):
    result = subprocess.run(['gh', 'api', path, '--method', method, '--input', '-'], input=json.dumps(payload), capture_output=True, text=True, encoding='utf-8', timeout=45)
    if result.returncode:
        raise ProviderError(result.stderr.strip()[:1000])
    return json.loads(result.stdout) if result.stdout.strip() else {}


def gh_api(path):
    try:
        result = subprocess.run(['gh', 'api', path], capture_output=True, text=True, encoding='utf-8', timeout=45)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProviderError(f'GitHub API unavailable: {type(exc).__name__}') from exc
    if result.returncode:
        # A genuine unprotected-branch response is distinct from hidden/forbidden state.
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        if path.endswith('/protection') and payload.get('message') == 'Branch not protected':
            return None
        fallback = 'Network access unavailable' if any(term in result.stderr.lower() for term in ('connectex', 'dial tcp', 'connection refused', 'timeout', 'no such host')) else 'GitHub CLI failed; check gh auth status'
        raise ProviderError(f'{path}: {payload.get("message", fallback)}')
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ProviderError(f'{path}: invalid JSON response') from exc


def file_bytes(api, prefix, path, ref):
    data = api(f'{prefix}/contents/{path}?ref={ref}')
    if not isinstance(data, dict) or data.get('type') != 'file' or data.get('encoding') != 'base64':
        raise ProviderError(f'Authoritative file unavailable: {path}')
    return base64.b64decode(data['content'])


class GitHub:
    def __init__(self, api=None):
        self.api = api or gh_api

    def target(self, config):
        """Only the canonical ref needed by this operation; no policy audit."""
        import re
        sha = self.api(f'repos/{config["repository"]}/branches/{quote(config["target"], safe="")}')['commit']['sha']
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{40}', sha):
            raise ProviderError('Canonical target must resolve to an exact commit')
        return sha

    def project_work(self, repo, config, item, sha):
        # Git objects fetched from the configured origin are bound to the observed
        # canonical commit. Reuse the reader, avoiding one API request per task.
        if config['profile'] != 'github-backlog-v1':
            return self.work(config, item)
        from .backlog import authorize, local_corpus
        try:
            repo.revision(sha)
        except ValueError:
            repo.git('fetch', '--no-tags', 'origin', config['target'])
            repo.revision(sha)
        observation = local_corpus(repo, sha, config['work'])
        actor = self.api('user').get('login')
        return {**authorize(observation, config['work'], item, actor), 'revision': sha}

    def acceptance(self, config, pull):
        """Observe the existing Actions check, bound to its actual run and PR head."""
        selected = config['verification']
        workflow, app = selected.get('workflow'), selected.get('expected_app_id')
        if not workflow or not app:
            raise ValueError('Configure the existing CI workflow path and expected check App before integration')
        prefix, head = f'repos/{config["repository"]}', pull['head']['sha']
        checks = self.api(f'{prefix}/commits/{head}/check-runs?filter=latest&per_page=100')
        runs = self.api(f'{prefix}/actions/runs?head_sha={head}&per_page=100')
        for data, field in ((checks, 'check_runs'), (runs, 'workflow_runs')):
            if (not isinstance(data, dict) or not isinstance(data.get(field), list) or
                    type(data.get('total_count')) is not int or data['total_count'] != len(data[field]) or len(data[field]) >= 100):
                raise ProviderError('CI observation malformed or incomplete')
        matching = [c for c in checks['check_runs'] if c.get('name') == selected['required_check']]
        if len(matching) != 1:
            raise ValueError('Existing required CI check missing or ambiguous')
        check = matching[0]
        if (check.get('head_sha') != head or check.get('app', {}).get('id') != app or
                check.get('status') != 'completed' or check.get('conclusion') != 'success'):
            raise ValueError('Existing required CI check is stale, untrusted or not successful')
        suite = check.get('check_suite', {}).get('id')
        matching = [r for r in runs['workflow_runs'] if r.get('check_suite_id') == suite]
        if type(suite) is not int or len(matching) != 1:
            raise ValueError('Existing CI run provenance missing or ambiguous')
        run = matching[0]
        if (run.get('head_sha') != head or run.get('path') != workflow or
                run.get('event') != 'pull_request' or run.get('status') != 'completed' or
                run.get('conclusion') != 'success' or
                not any(p.get('number') == pull['number'] for p in run.get('pull_requests', []))):
            raise ValueError('Existing CI run does not bind the selected workflow, PR and exact head')
        return {'check': check['id'], 'run': run['id'], 'attempt': run['run_attempt'], 'head': head}

    def observe(self, config):
        prefix = f'repos/{config["repository"]}'
        target = quote(config['target'], safe='')
        raw, errors = {}, []
        for key, path in (
            ('repository', prefix), ('branch', f'{prefix}/branches/{target}'),
            ('rules', f'{prefix}/rules/branches/{target}'),
            ('protection', f'{prefix}/branches/{target}/protection'),
            ('workflows', f'{prefix}/actions/workflows?per_page=100'),
        ):
            try:
                raw[key] = self.api(path)
            except (ProviderError, ValueError, TypeError) as exc:
                errors.append(f'{key}: {exc}')
        details = []
        try:
            path = f'{prefix}/rulesets?includes_parents=true&per_page=100'
            summaries = self.api(path)
            if not isinstance(summaries, list):
                raise ProviderError('Expected ruleset list')
            # Conservative limit: do not mistake a truncated topology for completeness.
            if len(summaries) >= 100:
                raise ProviderError('Ruleset pagination limit reached; complete observation unavailable')
            for summary in summaries:
                source_type = summary.get('source_type', 'Repository')
                if source_type == 'Repository':
                    detail_path = f'{prefix}/rulesets/{int(summary["id"])}'
                elif source_type == 'Organization':
                    source = quote(summary['source'], safe='')
                    detail_path = f'orgs/{source}/rulesets/{int(summary["id"])}'
                else:
                    raise ProviderError(f'Unsupported inherited ruleset source: {source_type}')
                detail = self.api(detail_path)
                if not isinstance(detail, dict) or 'bypass_actors' not in detail:
                    raise ProviderError('Ruleset bypass policy not observable')
                details.append(detail)
        except (ProviderError, ValueError, KeyError, TypeError) as exc:
            errors.append(f'rulesets: {exc}')
        raw['rulesets'] = details
        workflows = raw.get('workflows', {})
        if not isinstance(workflows, dict) or not isinstance(workflows.get('workflows', []), list) or type(workflows.get('total_count', 0)) is not int:
            errors.append('workflows: malformed API observation')
            workflows = {}
        if isinstance(workflows, dict) and workflows.get('total_count', 0) > len(workflows.get('workflows', [])):
            errors.append('workflows: pagination incomplete')
        raw['workflow_blobs'] = {}
        try:
            sha = raw.get('branch', {}).get('commit', {}).get('sha')
            if not sha:
                raise ProviderError('Missing workflow target revision')
            tree = self.api(f'{prefix}/git/trees/{sha}?recursive=1')
            if not isinstance(tree.get('tree'), list) or tree.get('truncated'):
                raise ProviderError('Canonical workflow tree incomplete')
            for item in tree['tree']:
                path = item['path']
                if path.startswith('.github/workflows/') and len(path.split('/')) == 3 and path.lower().endswith(('.yml', '.yaml')):
                    if item.get('type') != 'blob' or item.get('mode') not in ('100644', '100755'):
                        raise ProviderError('Canonical workflow must be a regular source file')
                    raw['workflow_blobs'][path] = item['sha']
            # Actions registry includes unmerged candidate workflows. Only canonical
            # source owns baseline authority; candidate registration is not policy drift.
            raw['workflows'] = {'workflows': [{'id': w.get('id'), 'path': w['path'], 'state': w.get('state')}
                for w in workflows.get('workflows', []) if w.get('path') in raw['workflow_blobs']]}
        except (ProviderError, ValueError, KeyError, TypeError) as exc:
            errors.append(f'canonical workflow tree: {exc}')
        from .native import observe_controller, observe_proof
        observe_controller(config, raw, self.api, errors)
        work_authority = None
        if config['profile'] == 'github-backlog-v1':
            from .backlog import read_corpus
            try:
                work = read_corpus(config, raw.get('branch', {}).get('commit', {}).get('sha'), self.api)
                work_authority = {'valid': True, 'revision': work['revision'], 'identity': work['identity']}
            except (ValueError, TypeError, KeyError) as exc:
                errors.append(f'backlog work authority: {exc}')
                work_authority = {'valid': False, 'reason': str(exc)}
        observation = summarize(config, raw, errors)
        if work_authority is not None:
            observation['work_authority'] = work_authority
        observation['deployment_proof'] = observe_proof(config, observation, self.api)
        observation['deployment_proven'] = observation['deployment_proof']['valid']
        return observation

    def work(self, config, issue):
        if config['profile'] == 'github-backlog-v1':
            from .backlog import authorize, read_corpus
            revision = self.api(f'repos/{config["repository"]}/branches/{quote(config["target"], safe="")}')['commit']['sha']
            observation = read_corpus(config, revision, self.api)
            actor = self.api('user').get('login')
            return {**authorize(observation, config['work'], issue, actor), 'revision': revision}
        if type(issue) is not int or issue <= 0:
            raise ValueError('Work item must be a positive GitHub Issue number')
        item = self.api(f'repos/{config["repository"]}/issues/{issue}')
        if not isinstance(item, dict) or item.get('state') != 'open' or 'pull_request' in item:
            raise ValueError('Legal work requires an open Issue, not a PR or closed item')
        return {'number': issue, 'title': item.get('title'), 'url': item.get('html_url'), 'state': item['state']}

    def list_work(self, config):
        if config['profile'] == 'github-backlog-v1':
            from .backlog import authorize, read_corpus
            revision = self.api(f'repos/{config["repository"]}/branches/{quote(config["target"], safe="")}')['commit']['sha']
            observation = read_corpus(config, revision, self.api)
            actor = self.api('user').get('login')
            if not isinstance(actor, str) or not actor:
                raise ProviderError('Native executor identity unavailable')
            result = []
            for identifier in sorted(observation['tasks']):
                try:
                    result.append({**authorize(observation, config['work'], identifier, actor), 'revision': revision})
                except ValueError:
                    continue
            return result
        items = self.api(f'repos/{config["repository"]}/issues?state=open&per_page=100')
        if not isinstance(items, list):
            raise ProviderError('Expected Issue list')
        return [{'number': i['number'], 'title': i['title'], 'url': i['html_url']} for i in items if 'pull_request' not in i]


def summarize(config, raw, errors):
    errors = list(errors)
    repository = raw.get('repository') or {}
    branch = raw.get('branch') or {}
    rules = raw.get('rules') or []
    rulesets = raw.get('rulesets') or []
    protection = raw.get('protection')
    if not isinstance(repository, dict) or repository.get('full_name', '').lower() != config['repository'].lower():
        errors.append('repository: authoritative identity mismatch or missing')
        repository = {}
    if not isinstance(branch, dict) or not isinstance(branch.get('commit'), dict) or not branch['commit'].get('sha'):
        errors.append('branch: authoritative target identity missing')
        branch = {}
    if not isinstance(rules, list) or not all(isinstance(r, dict) and isinstance(r.get('type'), str) for r in rules):
        errors.append('rules: malformed effective rules')
        rules = []
    if not isinstance(rulesets, list) or not all(isinstance(r, dict) for r in rulesets):
        errors.append('rulesets: malformed policy')
        rulesets = []
    kinds = {r['type'] for r in rules}
    active = [r for r in rulesets if r.get('enforcement') == 'active']
    bypass = [actor for r in active for actor in r.get('bypass_actors', [])]
    if any('bypass_actors' not in r for r in active):
        errors.append('rulesets: active bypass policy unavailable')
    sourced_check = False
    strict = False
    verification = config['verification']
    for rule in rules:
        if rule['type'] == 'required_status_checks':
            parameters = rule.get('parameters', {})
            if not isinstance(parameters, dict):
                errors.append('required checks: malformed parameters')
                continue
            checks = parameters.get('required_status_checks', [])
            if not isinstance(checks, list) or not all(isinstance(c, dict) for c in checks):
                errors.append('required checks: malformed accepted sources')
                continue
            for check in checks:
                if check.get('context') == verification['required_check'] and verification['expected_app_id'] is not None and check.get('integration_id') == verification['expected_app_id']:
                    sourced_check = True
                    strict = strict or parameters.get('strict_required_status_checks_policy') is True
    # Legacy protection can add stricter constraints; not silently ignored in drift.
    # Initial profile requires effective ruleset enforcement rather than guessing
    # equivalent semantics from incomplete legacy branch-protection responses.
    merge_only = any(r.get('type') == 'pull_request' and r.get('parameters', {}).get('allowed_merge_methods') == ['merge'] for r in rules)
    fresh_candidate = 'merge_queue' in kinds or (strict and merge_only)
    native_gate = bool(active) and {'pull_request', 'non_fast_forward', 'deletion'} <= kinds and fresh_candidate and sourced_check and not bypass and not errors
    policy = {
        'repository': {'id': repository.get('id'), 'full_name': repository.get('full_name'), 'default_branch': repository.get('default_branch')},
        'rules': rules, 'rulesets': rulesets, 'protection': protection,
        'workflows': raw.get('workflows'), 'workflow_blobs': raw.get('workflow_blobs'),
        'actions_policies': raw.get('actions_policies'), 'controller_blobs': raw.get('controller_blobs'),
        'controller_workflow': raw.get('controller_workflow'), 'canonical_config': raw.get('canonical_config'),
    }
    from .native import trusted
    provenance = not errors and trusted(config, raw)
    return {
        'source': 'live-github-api', 'fingerprint': digest(policy) if not errors else None,
        'gate': native_gate, 'errors': errors, 'effective_rule_types': sorted(kinds),
        'bypass_actors': bypass, 'sourced_check': sourced_check,
        'target_sha': branch.get('commit', {}).get('sha'), 'policy': policy,
        'trusted_controller': provenance,
        'provenance': 'Native immutable controller and event policy observed' if provenance else 'UNPROVEN: trusted controller/event policy incomplete',
        'candidate_strategy': 'merge-queue' if 'merge_queue' in kinds else 'strict-merge-only-pr',
    }
