"""Fixed candidate catalogue and deliberately conservative proof resolution."""

import hashlib
import json
import re

CATALOGUE = (
    'applicability', 'authority', 'coverage', 'concurrency', 'fencing',
    'isolation', 'mutation', 'candidate-freshness', 'provenance',
    'integration', 'guarantee-freshness', 'na-freshness', 'recovery',
    'break-glass', 'closure', 'fresh-agent',
)
AUTHORITIES = {
    'product': 'repository-docs', 'work': 'github-issues',
    'change': 'github-pull-requests', 'revision': 'github-target-ref',
    'integration': 'github-rules', 'evidence': 'github-checks',
    'workspace': 'git-worktree',
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def default_config(repository, target):
    return {
        'schema': 1, 'profile': 'github-pr-v1', 'repository': repository,
        'target': target, 'authorities': dict(AUTHORITIES),
        'envelope': {
            'workspace_writers': 'single',
            'trusted_actors': ['repository-admins', 'ci-maintainers', 'local-executor'],
            'excluded_transitions': ['arbitrary-local-writes', 'administrator-policy-reconfiguration'],
        },
        'verification': {
            'commands': [], 'material_inputs': [], 'environment': {},
            'required_check': 'openharness / candidate',
            'expected_app_id': None,
        },
    }


def validate_config(config):
    expected = {'schema', 'profile', 'repository', 'target', 'authorities', 'envelope', 'verification'}
    if not isinstance(config, dict) or set(config) != expected:
        raise ValueError('Configuration must contain the exact supported fields; guarantee omission/overrides are forbidden')
    if config['schema'] != 1 or config['profile'] != 'github-pr-v1':
        raise ValueError('Unsupported schema or profile')
    if not isinstance(config['repository'], str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', config['repository']):
        raise ValueError('Expected GitHub owner/repository')
    if not isinstance(config['target'], str) or not re.fullmatch(r'[A-Za-z0-9_./-]+', config['target']) or config['target'].startswith('-') or '..' in config['target']:
        raise ValueError('Invalid target branch')
    if config['authorities'] != AUTHORITIES:
        raise ValueError('Each semantic state must have exactly the supported effective authority')
    envelope = config['envelope']
    if not isinstance(envelope, dict) or set(envelope) != {'workspace_writers', 'trusted_actors', 'excluded_transitions'}:
        raise ValueError('Envelope must explicitly declare topology, trusted actors and exclusions')
    if envelope['workspace_writers'] not in ('single', 'multiple', 'unknown'):
        raise ValueError('Unknown workspace topology')
    for field in ('trusted_actors', 'excluded_transitions'):
        if not isinstance(envelope[field], list) or not all(isinstance(v, str) for v in envelope[field]):
            raise ValueError('Envelope actors and exclusions must be string lists')
    verification = config['verification']
    if not isinstance(verification, dict) or set(verification) != {'commands', 'material_inputs', 'environment', 'required_check', 'expected_app_id'}:
        raise ValueError('Invalid verification configuration')
    if not isinstance(verification['commands'], list) or not all(isinstance(c, list) and c and all(isinstance(v, str) and v for v in c) for c in verification['commands']):
        raise ValueError('Verification commands must be nonempty argv lists, never shell text')
    if not isinstance(verification['material_inputs'], list) or not all(isinstance(v, str) for v in verification['material_inputs']):
        raise ValueError('Material inputs must be repository-relative paths')
    if not isinstance(verification['environment'], dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in verification['environment'].items()):
        raise ValueError('Material environment must be a string mapping')
    if not isinstance(verification['required_check'], str) or not verification['required_check']:
        raise ValueError('A required check name is mandatory')
    app = verification['expected_app_id']
    if app is not None and (type(app) is not int or app <= 0):
        raise ValueError('Check provenance app id must be a positive integer or unresolved null')
    return config


def candidate_id(candidate):
    required = {'head', 'base', 'tree', 'config', 'inputs', 'environment'}
    if not isinstance(candidate, dict) or set(candidate) != required or not all(isinstance(candidate[k], str) and candidate[k] for k in required):
        raise ValueError('Candidate requires head, base, resulting tree, config, inputs and material environment')
    return digest(candidate)


def evaluate(config, local, provider):
    validate_config(config)
    rows = {}

    def resolve(name, proven, reason, scope, triggers, applicable=True, resolved=True):
        rows[name] = {
            'id': name, 'status': ('NOT APPLICABLE' if not applicable else 'ESTABLISHED' if proven else 'OPEN GAP'),
            'applicability_resolved': resolved, 'reason': reason, 'scope': scope,
            'authority': 'fixed profile / live Git and GitHub',
            'proof': {'local': local, 'provider_observation': provider.get('fingerprint')} if proven else None,
            'validity_conditions': 'Only current observed substrate inside declared envelope',
            'invalidation_triggers': triggers,
        }

    installed = local.get('installed', False)
    git = local.get('git', False)
    observed = not provider.get('errors') and bool(provider.get('fingerprint'))
    gate = observed and provider.get('gate', False)
    resolve('applicability', True, 'Fixed profile evaluates all 16 candidates; unknown applicability blocks closure', 'catalogue completeness', ['profile', 'envelope'])
    resolve('authority', installed and observed and local.get('authority_matches_origin', False), 'Exact semantic authority map plus live repository and origin identity required', 'declared semantic mapping; privileged policy operators trusted', ['authorities', 'provider_identity', 'origin'])
    topology = config['envelope']['workspace_writers']
    single = topology == 'single' and 'local-executor' in config['envelope']['trusted_actors']
    for name in ('concurrency', 'fencing'):
        resolve(name, False, 'Trusted single writer per workspace; conflicting integration delegated to provider' if single else 'Exclusive/stale-writer enforcement adapter unavailable; no claim file is accepted as authority', 'local workspace writers; target integration evaluated separately', ['workspace_writers', 'trusted_actors'], applicable=not single, resolved=topology != 'unknown')
    resolve('isolation', installed and git, 'Workspace command binds separate Git worktrees; executor must enforce declared single writer', 'workspaces created through supported command', ['git_worktrees', 'envelope'])
    resolve('candidate-freshness', installed and bool(config['verification']['commands']), 'Verifier binds explicit head/base/result/config/inputs/environment and rejects changed subjects', 'local verification evidence; remote acceptance evaluated separately', ['candidate', 'verification'])
    for name in ('integration', 'mutation'):
        resolve(name, gate, 'Live required PR, merge queue, sourced check, non-fast-forward/deletion protection and no bypass required', 'GitHub target-ref updates', ['rulesets', 'protection', 'bypass_actors', 'required_checks'])
    # App identity does not prove the implementation producing that check. v0.1 has
    # no external verifier attestation adapter: refuse to manufacture such proof.
    resolve('provenance', False, 'Expected App is necessary but insufficient: trusted verifier implementation and candidate-independent wiring not yet attested by this version', 'accepted integration evidence producer', ['workflow', 'expected_app_id', 'verifier_source'])
    resolve('coverage', False, 'Provider rules observed; end-to-end trusted guard wiring and authoritative bypass rejection require deployment proof adapter', 'all in-scope authoritative transitions', ['rulesets', 'workflow', 'bypass_actors', 'authority'])
    for name in ('guarantee-freshness', 'na-freshness'):
        resolve(name, installed and observed, 'Doctor re-observes current provider/configuration; saved activation digest cannot survive drift', 'observed closure and applicability', ['provider_fingerprint', 'config', 'envelope'])
    for name, reason in (
        ('recovery', 'Reconcile re-observes provider and invalidates stale local projections without conversational memory'),
        ('break-glass', 'Explicit local exceptional lifecycle record invalidates managed authority; does not grant GitHub bypass permissions'),
        ('closure', 'Entry locates config, lifecycle and fresh complete Doctor report; saved reports are projections'),
        ('fresh-agent', 'Installed entry and CLI expose authority, Issue/PR discovery, workspace binding and recovery'),
    ):
        resolve(name, installed, reason, 'supported local lifecycle commands; remote enforcement separately evaluated', ['installation', 'config', 'runtime'])
    guarantees = [rows[name] for name in CATALOGUE]
    return {
        'profile': config['profile'], 'repository': config['repository'],
        'envelope': config['envelope'], 'candidate_count': len(CATALOGUE),
        'closure': all(g['status'] != 'OPEN GAP' and g['applicability_resolved'] for g in guarantees),
        'guarantees': guarantees, 'provider': provider,
        'substrate': digest({'config': config, 'local': {k: v for k, v in local.items() if k != 'clean'}, 'provider': provider.get('fingerprint')}),
        'limitations': ['v0.1 cannot establish full closure: external verifier provenance and deployment coverage proof adapters are not implemented'],
    }
