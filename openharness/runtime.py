"""Local lifecycle projections, isolated candidate checks and fail-closed preflight."""

import copy
import hashlib
import json
import os
import platform
import subprocess
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from . import __version__
from .model import CATALOGUE, candidate_id, digest, evaluate
from .provider import GitHub, ProviderError
from .repository import Repository, bootstrap, json_text, safe_path


def now():
    return datetime.now(timezone.utc).isoformat()


def execution_identity():
    from pathlib import Path
    code = {p.name: hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in Path(__file__).parent.glob('*.py')}
    return {'tool': __version__, 'code': digest(code), 'python': sys.version, 'platform': platform.platform()}


class Runtime:
    def __init__(self, repo, provider=None):
        self.repo = repo
        self.provider = provider or GitHub()
        self.storage = safe_path(repo.common_dir, 'openharness')

    @contextmanager
    def locked(self):
        self.storage.mkdir(parents=True, exist_ok=True)
        path = safe_path(self.storage, 'operation.lock')
        with path.open('a+b') as stream:
            stream.seek(0)
            if stream.read(1) == b'':
                stream.write(b'0')
                stream.flush()
            stream.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise ValueError('Another local lifecycle operation holds the native process lock; retry after it exits') from exc
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def read(self, name, default):
        path = safe_path(self.storage, name)
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

    def write(self, name, value):
        path = safe_path(self.storage, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            with temporary.open('x', encoding='utf-8', newline='\n') as stream:
                stream.write(json_text(value))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def state(self):
        state = self.read('runtime.json', {'lifecycle': 'GENESIS', 'substrate': None, 'events': [], 'workspaces': {}})
        if not isinstance(state, dict) or state.get('lifecycle') not in ('GENESIS', 'MANAGED', 'UNPROVEN', 'BREAK_GLASS'):
            raise ValueError('Invalid lifecycle projection; repair explicitly with break-glass')
        if not isinstance(state.get('events', []), list) or not isinstance(state.get('workspaces', {}), dict):
            raise ValueError('Invalid runtime events/workspaces; repair explicitly with break-glass')
        return state

    def save_state(self, state):
        self.write('runtime.json', state)

    def doctor(self, revalidate=False):
        config = self.repo.config()
        provider = self.provider.observe(config)
        local = self.repo.local()
        local['verifier'] = execution_identity()
        try:
            local['authority_matches_origin'] = self.repo.identity().lower() == config['repository'].lower()
        except ValueError:
            local['authority_matches_origin'] = False
        report = evaluate(config, local, provider)
        report['observed_at'] = now()
        state = self.state()
        report['lifecycle'] = state['lifecycle']
        report['readiness'] = {'closure': report['closure'], 'guarantees': copy.deepcopy(report['guarantees']), 'authority': 'assessment-only; not activation'}
        if not revalidate and (state['lifecycle'] != 'MANAGED' or state.get('substrate') != report['substrate']):
            report['closure'] = False
            for row in report['guarantees']:
                if state['lifecycle'] == 'BREAK_GLASS' or row['status'] == 'ESTABLISHED':
                    row.update(status='OPEN GAP', proof=None, reason=f'{state["lifecycle"]}: no current activation / proof invalidated. Readiness: {row["reason"]}')
        return report

    def activate(self):
        with self.locked():
            report = self.doctor(revalidate=True)
            if report['provider'].get('source') != 'live-github-api' or not report['closure']:
                gaps = ', '.join(g['id'] for g in report['guarantees'] if g['status'] == 'OPEN GAP')
                raise ValueError(f'Activation blocked: live complete closure required; gaps: {gaps}')
            state = self.state()
            state.update(lifecycle='MANAGED', substrate=report['substrate'])
            state.setdefault('events', []).append({'time': now(), 'transition': 'ACTIVATE', 'substrate': report['substrate']})
            self.save_state(state)
            return state

    def preflight(self):
        report = self.doctor()
        state = self.state()
        if state['lifecycle'] != 'MANAGED' or not report['closure'] or state.get('substrate') != report['substrate']:
            raise ValueError('Protected transition rejected: no current managed closure; run doctor/reconcile')
        config = self.repo.config()
        if self.repo.identity().lower() != config['repository'].lower():
            raise ValueError('Origin authority does not match installed configuration')
        branch = self.repo.git('branch', '--show-current')
        binding = state.get('workspaces', {}).get(str(self.repo.root))
        if not binding or binding['branch'] != branch or branch == config['target']:
            raise ValueError('Protected transition requires a bound isolated Change workspace')
        self.provider.work(config, binding['work_item'])
        if binding.get('config') != digest(config):
            raise ValueError('Workspace authority binding invalidated by configuration change')
        return {'allowed': True, 'workspace': binding, 'substrate': report['substrate']}

    def workspace(self, issue, change, genesis=False):
        with self.locked():
            config = self.repo.config()
            state = self.state()
            if genesis:
                if state['lifecycle'] != 'GENESIS':
                    raise ValueError('Genesis installer authority is unavailable after managed/exceptional operation')
            else:
                report = self.doctor()
                if state['lifecycle'] != 'MANAGED' or not report['closure'] or state.get('substrate') != report['substrate']:
                    raise ValueError('Workspace creation requires current managed closure; use explicit --genesis only during bootstrap')
            self.provider.work(config, issue)
            observation = self.provider.observe(config)
            if observation.get('errors') or not observation.get('target_sha'):
                raise ValueError('Cannot bind workspace without observable live target revision')
            sha = observation['target_sha']
            # Fetch only the configured authority, without silently moving project refs.
            try:
                self.repo.revision(sha)
            except ValueError:
                self.repo.git('fetch', '--no-tags', 'origin', config['target'])
                self.repo.revision(sha)
            binding = self.repo.workspace(issue, change, sha)
            binding.update(authority=state['lifecycle'], config=digest(config), created_at=now())
            state.setdefault('workspaces', {})[binding['path']] = binding
            self.save_state(state)
            return binding

    def reconcile(self):
        with self.locked():
            report = self.doctor()
            state = self.state()
            if state['lifecycle'] == 'MANAGED' and (not report['closure'] or state.get('substrate') != report['substrate']):
                state.update(lifecycle='UNPROVEN', substrate=None)
                state.setdefault('events', []).append({'time': now(), 'transition': 'INVALIDATE', 'reason': 'Guarantee/applicability/substrate no longer proven'})
            from pathlib import Path
            existing = {str(Path(record['path']).resolve()) for record in self._worktrees()}
            orphaned = [p for p in state.get('workspaces', {}) if p not in existing]
            for path in orphaned:
                del state['workspaces'][path]
            state.setdefault('events', []).append({'time': now(), 'transition': 'RECONCILE', 'orphaned_bindings': orphaned})
            self.save_state(state)
            return {**state, 'doctor': report, 'orphaned_bindings': orphaned, 'recovery': 'No automatic reactivation or acquisition of stale authority'}

    def _worktrees(self):
        records = []
        for section in self.repo.git('worktree', 'list', '--porcelain').split('\n\n'):
            lines = section.splitlines()
            if lines and lines[0].startswith('worktree '):
                records.append({'path': lines[0][9:]})
        return records

    def break_glass(self, reason):
        if not reason.strip():
            raise ValueError('Explicit nonempty break-glass reason required')
        with self.locked():
            try:
                state = self.state()
            except (ValueError, json.JSONDecodeError):
                corrupt = self.read_bytes('runtime.json')
                backup_name = 'corrupt-runtime-' + uuid.uuid4().hex + '.txt'
                self.write(backup_name, {'original': corrupt.decode('utf-8', errors='replace')})
                state = {'lifecycle': 'UNPROVEN', 'events': [], 'workspaces': {}}
            state.update(lifecycle='BREAK_GLASS', substrate=None)
            state.setdefault('events', []).append({'time': now(), 'transition': 'BREAK_GLASS', 'reason': reason, 'invalidated': list(CATALOGUE), 'authority': 'trusted-local-operator; grants no provider bypass'})
            self.save_state(state)
            return state

    def read_bytes(self, name):
        return safe_path(self.storage, name).read_bytes()

    def entry(self):
        config = self.repo.config()
        state = self.state()
        try:
            work = self.provider.list_work(config)
            work_error = None
        except (ProviderError, ValueError) as exc:
            work, work_error = [], str(exc)
        return {
            'config': str(self.repo.root / '.harness/config.json'), 'authorities': config['authorities'],
            'work_url': f'https://github.com/{config["repository"]}/issues', 'legal_work': work,
            'work_discovery_error': work_error, 'lifecycle': state['lifecycle'],
            'workspace': state.get('workspaces', {}).get(str(self.repo.root)),
            'doctor': self.doctor(), 'next': 'Resolve OPEN GAPs before activation; Genesis supports explicit installer workspaces and local candidate diagnostics',
        }

    def verify(self, head, base, timeout=300):
        with self.locked():
            if self.repo.git('status', '--porcelain'):
                raise ValueError('Candidate verification requires a clean source workspace')
            config = self.repo.config()
            commands = config['verification']['commands']
            if not commands:
                raise ValueError('Project acceptance commands are unresolved; configure argv commands explicitly')
            candidate = self.repo.candidate(head, base)
            # Include verifier identity/environment so evidence cannot outlive a tool/runtime change.
            execution = execution_identity()
            candidate['environment'] = digest({'material': candidate['environment'], 'execution': execution})
            cid = candidate_id(candidate)
            path = safe_path(self.storage, f'candidates/{uuid.uuid4().hex}')
            path.parent.mkdir(parents=True, exist_ok=True)
            env = dict(os.environ)
            env.update(GIT_AUTHOR_NAME='OpenHarness', GIT_AUTHOR_EMAIL='harness@example.invalid', GIT_COMMITTER_NAME='OpenHarness', GIT_COMMITTER_EMAIL='harness@example.invalid')
            commit = self.repo.git('commit-tree', candidate['tree'], '-p', candidate['base'], '-p', candidate['head'], input_text='OpenHarness diagnostic integration candidate\n', env=env)
            checks, created = [], False
            try:
                self.repo.git('worktree', 'add', '--detach', str(path), commit)
                created = True
                isolated = Repository(path)
                # External material input bytes must match the actual tested checkout.
                for relative in config['verification']['material_inputs']:
                    original = safe_path(self.repo.root, relative)
                    tested = safe_path(path, relative)
                    if not tested.is_file() or original.read_bytes() != tested.read_bytes():
                        raise ValueError(f'Material input is not bound to candidate result: {relative}')
                for argv in commands:
                    try:
                        process = subprocess.run(argv, cwd=path, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
                        check = {'argv': argv, 'returncode': process.returncode, 'stdout': process.stdout[-8192:], 'stderr': process.stderr[-8192:]}
                    except (OSError, subprocess.TimeoutExpired) as exc:
                        check = {'argv': argv, 'returncode': -1, 'error': type(exc).__name__}
                    checks.append(check)
                    if check['returncode'] != 0:
                        break
                unchanged = not isolated.git('status', '--porcelain') and isolated.revision('HEAD') == commit
                fresh = self._verification_candidate(head, base) == candidate
                record = {'candidate': candidate, 'candidate_id': cid, 'checks': checks, 'passed': all(c['returncode'] == 0 for c in checks) and unchanged and fresh, 'subject_unchanged': unchanged, 'fresh': fresh, 'observed_at': now(), 'authority': 'local-diagnostic-only', 'authorizes_integration': False, 'execution': execution}
                self.write(f'evidence/{cid}.json', record)
                return record
            finally:
                if created:
                    # This path is a freshly generated, contained diagnostic worktree only.
                    self.repo.git('worktree', 'remove', '--force', str(path))

    def _verification_candidate(self, head, base):
        candidate = self.repo.candidate(head, base)
        execution = execution_identity()
        candidate['environment'] = digest({'material': candidate['environment'], 'execution': execution})
        return candidate

    def evidence(self, head, base):
        candidate = self._verification_candidate(head, base)
        cid = candidate_id(candidate)
        record = self.read(f'evidence/{cid}.json', None)
        valid = isinstance(record, dict) and record.get('candidate') == candidate and record.get('candidate_id') == cid and record.get('passed') is True
        return {'candidate_id': cid, 'fresh': valid, 'record': record, 'authorizes_integration': False}

    def upgrade(self):
        with self.locked():
            state = self.state()
            if state['lifecycle'] in ('MANAGED', 'UNPROVEN'):
                self.preflight()
            config = self.repo.config()
            # Installer refuses uncontrolled changes to any installed artifact.
            result = bootstrap(self.repo, config['repository'], config['target'], governed_upgrade=True)
            state.update(substrate=None, lifecycle='UNPROVEN' if state['lifecycle'] == 'MANAGED' else state['lifecycle'])
            state.setdefault('events', []).append({'time': now(), 'transition': 'UPGRADE_STAGE', 'version': __version__})
            self.save_state(state)
            return {**result, 'lifecycle': state['lifecycle'], 'activated': False}

    def setup_plan(self):
        config = self.repo.config()
        app = config['verification']['expected_app_id']
        from .ci import event_policy, workflow_text, WORKFLOW_PATH
        return {
            'mode': 'proposal-only', 'repository': config['repository'], 'target': config['target'],
            'ruleset': {
                'name': 'OpenHarness integration', 'target': 'branch', 'enforcement': 'active',
                'conditions': {'ref_name': {'include': [f'refs/heads/{config["target"]}'], 'exclude': []}},
                'bypass_actors': [],
                'rules': [{'type': 'pull_request', 'parameters': {'required_approving_review_count': 0, 'dismiss_stale_reviews_on_push': True, 'require_code_owner_review': False, 'require_last_push_approval': False, 'required_review_thread_resolution': True, 'allowed_merge_methods': ['merge']}}, {'type': 'non_fast_forward'}, {'type': 'deletion'}, {'type': 'required_status_checks', 'parameters': {'strict_required_status_checks_policy': True, 'required_status_checks': [{'context': config['verification']['required_check'], 'integration_id': app}]}}],
            },
            'actions_policy': event_policy(),
            'workflow': {'path': WORKFLOW_PATH, 'contents': workflow_text()},
            'unresolved': [
                *(['Discover and configure trusted check App id; null must never be applied as any-source acceptance'] if app is None else []),
                *(['Pin immutable controller source and sandbox image'] if not config['verification'].get('controller') or not config['verification'].get('sandbox_image') else []),
                'Apply native policy, install canonical workflow, run and record current live deployment proof',
            ],
            'activation_possible_in_this_version': True,
        }

    def setup_apply(self):
        """Explicit installer command; collision-safe and never activates."""
        from .provider import gh_write
        with self.locked():
            if self.state()['lifecycle'] != 'GENESIS':
                raise ValueError('Native installer authority is available only in Genesis; managed policy upgrades require operator governance')
            plan = self.setup_plan()
            config = self.repo.config()
            if config['verification']['expected_app_id'] is None or not config['verification'].get('controller') or not config['verification'].get('sandbox_image'):
                raise ValueError('Native setup requires resolved provenance pins and App identity')
            prefix = f'repos/{config["repository"]}'
            applied = []
            for endpoint, field in (('actions/policies', 'actions_policy'), ('rulesets', 'ruleset')):
                listed = self.provider.api(f'{prefix}/{endpoint}?per_page=100')
                items = listed.get('policies', []) if isinstance(listed, dict) else listed
                if not isinstance(items, list) or len(items) >= 100:
                    raise ValueError('Native policy inventory incomplete')
                same = [item for item in items if item.get('name') == plan[field]['name']]
                if same:
                    raise ValueError(f'Existing policy name requires explicit operator review: {plan[field]["name"]}')
                self.write(f'setup/{field}.json', plan[field])
                result = gh_write(f'{prefix}/{endpoint}', 'POST', plan[field])
                applied.append({'kind': field, 'id': result.get('id')})
            return {'applied': applied, 'activated': False, 'next': 'Observe live enforcement and complete deployment proof before activation'}

    def integrate(self, pr):
        from .ci import candidate_context
        from .provider import gh_write
        with self.locked():
            preflight = self.preflight()
            config = self.repo.config()
            prefix = f'repos/{config["repository"]}'
            pull = self.provider.api(f'{prefix}/pulls/{int(pr)}')
            issue = self.provider.api(f'{prefix}/issues/{preflight["workspace"]["work_item"]}')
            context = candidate_context(config, pull, issue)
            if pull['head']['ref'] != preflight['workspace']['branch'] or context['head'] != self.repo.revision('HEAD') or self.repo.git('status', '--porcelain'):
                raise ValueError('Integration requires the exact clean bound local PR candidate')
            base = self.provider.api(f'{prefix}/branches/{config["target"]}')['commit']['sha']
            if context['base'] != base:
                raise ValueError('Integration candidate base is stale')
            self.repo.git('merge-base', '--is-ancestor', base, context['head'])
            expected = self.repo.git('rev-parse', 'HEAD^{tree}')
            result = gh_write(f'{prefix}/pulls/{pr}/merge', 'PUT', {'sha': context['head'], 'merge_method': 'merge'})
            if not result.get('merged'):
                raise ValueError('Native integration rejected: ' + str(result.get('message')))
            integrated = self.provider.api(f'{prefix}/git/commits/{result["sha"]}')
            if integrated['tree']['sha'] != expected:
                self.break_glass_after_integration(result['sha'])
                raise ValueError('Native integrated tree differs from tested candidate; managed authority invalidated')
            state = self.state()
            state['workspaces'][str(self.repo.root)]['integrated'] = {'pr': pr, 'head': context['head'], 'commit': result['sha'], 'tree': expected}
            state['events'].append({'time': now(), 'transition': 'INTEGRATE', **state['workspaces'][str(self.repo.root)]['integrated']})
            self.save_state(state)
            return result

    def break_glass_after_integration(self, sha):
        state = self.state()
        state.update(lifecycle='UNPROVEN', substrate=None)
        state['events'].append({'time': now(), 'transition': 'INVALIDATE', 'reason': 'Integration tree mismatch', 'commit': sha})
        self.save_state(state)

    def release(self):
        with self.locked():
            state = self.state()
            binding = state.get('workspaces', {}).get(str(self.repo.root))
            if not binding or not binding.get('integrated'):
                raise ValueError('Release requires a recorded native integration; use handoff for unfinished work')
            config = self.repo.config()
            pull = self.provider.api(f'repos/{config["repository"]}/pulls/{binding["integrated"]["pr"]}')
            if not pull.get('merged') or pull.get('merge_commit_sha') != binding['integrated']['commit']:
                raise ValueError('Native integration record no longer matches release subject')
            del state['workspaces'][str(self.repo.root)]
            state['events'].append({'time': now(), 'transition': 'RELEASE', 'binding': binding})
            self.save_state(state)
            return {'released': binding, 'worktree_preserved': True, 'issue_closed': False}

    def handoff(self, reason):
        if not reason.strip():
            raise ValueError('Handoff requires a continuity note')
        with self.locked():
            state = self.state()
            binding = state.get('workspaces', {}).get(str(self.repo.root))
            if not binding:
                raise ValueError('Handoff requires a bound workspace')
            record = {'time': now(), 'transition': 'HANDOFF', 'binding': binding, 'head': self.repo.revision('HEAD'), 'dirty': bool(self.repo.git('status', '--porcelain')), 'reason': reason}
            state['events'].append(record)
            self.save_state(state)
            return {**record, 'worktree_preserved': True, 'next': 'Successor reads entry/reconcile and resumes this same binding; single-writer envelope remains required'}
