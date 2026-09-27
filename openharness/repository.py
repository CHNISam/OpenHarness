"""Native Git isolation and non-destructive project-local installation."""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from .model import default_config, digest, validate_config

ENTRY = '''# OpenHarness entry

Canonical project configuration: `.harness/config.json`.
Run `openharness --repo . entry` for current authoritative state and legal work.
Run `openharness --repo . doctor`; exit 2 means incomplete closure, never PASS.
GitHub Issues own work state; PRs contain Changes; GitHub refs/rules/checks own
revision/integration/evidence. Local reports are observations, never provider authority.
Create isolated Changes with `workspace --issue N --change NAME` only after activation.
Use `reconcile` after interruption and `break-glass --reason TEXT` for explicit local
recovery. This command grants no remote bypass rights. Never label local verification
as authoritative integration evidence. v0.1 lacks deployment proof/provenance adapters
and therefore intentionally refuses full activation. See the installed config and
tool README for exact boundaries. The execution envelope trusts one local writer per
workspace; multiple/unknown writers require a real authority/fencing adapter.
'''
LEGACY_ENTRY = ENTRY
ENTRY = '''# OpenHarness entry

Read `.harness/config.json`; run `openharness --repo . entry` and `doctor` to observe
current authority, work and closure. Exit 2 means OPEN GAP, never success.
Work authority is GitHub Issues; one Issue has multiple Changes. Use `workspace
--issue N --change NAME` for a bound isolated worktree. Work PRs must use that branch
and exactly one `Work-Item: #N` line. Native strict merge-only PR gates protect the
target. Trusted baseline controllers run candidate acceptance in a credential-free
Docker sandbox; a separate publisher binds current head/base/tree before authorizing
integration. Native Actions event policy blocks candidate-controlled workflow sources.
Use `integrate --pr N`, then `release`, or `handoff --reason TEXT` to preserve continuity.
Control changes require native owner approval bound to the exact head/base, then the
same enforced integration path. `reconcile` invalidates drift and stale projections.
`break-glass --reason TEXT` records exceptional local recovery and grants no provider
bypass. Doctor re-observes deployment proof, code pins, policy and applicability.
Physical local writes are outside the declared authoritative mutation envelope.
One trusted writer per workspace is a scope assumption; competing writers need an
effective authority/fencing adapter. No conversational history is required.
'''
MARKER = '<!-- OpenHarness entry -->'
INSTRUCTION = f'\n{MARKER}\nRead `.harness/AGENT.md` and run `openharness --repo . entry` before managed work.\n'
BACKLOG_ENTRY = '''# OpenHarness entry

Read `.harness/config.json`; run `openharness --repo . entry` and `doctor` for live
authority, legal work and current closure. Exit 2 means OPEN GAP, never success.
Canonical Backlog task files at the GitHub target ref are the sole work authority.
Use `workspace --task TASK_ID --change NAME` for a task-bound isolated Change;
PRs require exactly one `Work-Item: TASK_ID` line and the bound backlog branch.
Explicit configured assignee mapping authorizes the native executor/PR author.
Unassigned/ambiguous work, incomplete dependencies and stale corpus bindings reject.
Task metadata is not exclusive ownership or fencing; only the declared trusted
single-writer envelope is supported. Competing/unknown writers remain OPEN GAP.
Task corpus/control changes require exact native owner approval on the PR.
Trusted immutable baseline verification and independent publication preserve native
strict candidate/ref/check enforcement. Local verification never authorizes merge.
Use `integrate --pr N`, then `release`, or `handoff --reason TEXT` for continuity.
Reconcile invalidates drift without acquiring authority or automatically activating.
Break-glass invalidates guarantees and grants no remote bypass. Unsupported task
syntax and unavailable native proof remain OPEN GAP. Run current Doctor/activation;
saved reports and conversations are not activation authority.
'''


def entry_text(config):
    return BACKLOG_ENTRY if config['profile'] == 'github-backlog-v1' else ENTRY
WORKFLOW = '''# REVIEW TEMPLATE ONLY: candidate-controlled workflow is not trusted provenance.
# Install a pinned verifier through provider-enforced candidate-independent wiring.
name: openharness
on:
  pull_request:
  merge_group:
permissions:
  contents: read
jobs:
  candidate:
    runs-on: ubuntu-latest
    steps:
      - name: Require trusted verifier installation
        run: |
          echo 'OPEN GAP: wire an independently trusted pinned verifier before activation'
          exit 1
'''
LEGACY_WORKFLOW = WORKFLOW


def json_text(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n'


def safe_path(root, relative):
    root = Path(root).resolve()
    path = Path(relative)
    if path.is_absolute() or not path.parts or '..' in path.parts:
        raise ValueError('Path must remain repository-relative')
    candidate = root / path
    for parent in [candidate, *candidate.parents]:
        if parent == root:
            break
        if parent.is_symlink() or (hasattr(parent, 'is_junction') and parent.is_junction()):
            raise ValueError('Symlink/junction control or material input path is unsupported')
    if not candidate.resolve().is_relative_to(root):
        raise ValueError('Resolved path escapes repository')
    return candidate


class Repository:
    def __init__(self, path):
        self.root = Path(path).resolve()
        self.root = Path(self.git('rev-parse', '--show-toplevel')).resolve()
        self.common_dir = Path(self.git('rev-parse', '--path-format=absolute', '--git-common-dir')).resolve()

    def git(self, *args, input_text=None, env=None):
        result = subprocess.run(['git', '-C', str(self.root), *args], input=input_text, capture_output=True, text=True, encoding='utf-8', timeout=60, env=env)
        if result.returncode:
            raise ValueError(f'Git {args[0]} failed: {result.stderr.strip() or result.stdout.strip()}')
        return result.stdout.strip()

    def config(self):
        path = safe_path(self.root, '.harness/config.json')
        if not path.is_file():
            raise ValueError('Harness not installed; run bootstrap')
        return validate_config(json.loads(path.read_text(encoding='utf-8')))

    def local(self):
        paths = ('.harness/config.json', '.harness/AGENT.md', 'AGENTS.md')
        controls = {p: hashlib.sha256(safe_path(self.root, p).read_bytes().replace(b'\r\n', b'\n')).hexdigest() if safe_path(self.root, p).is_file() else None for p in paths}
        entry = safe_path(self.root, '.harness/AGENT.md')
        agents = safe_path(self.root, 'AGENTS.md')
        installed = all(controls.values()) and entry.read_text(encoding='utf-8') == entry_text(self.config()) and MARKER in agents.read_text(encoding='utf-8')
        return {'installed': installed, 'git': True, 'clean': not bool(self.git('status', '--porcelain')), 'controls': digest(controls)}

    def identity(self):
        url = self.git('remote', 'get-url', 'origin')
        match = re.fullmatch(r'(?:https://github\.com/|git@github\.com:)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?', url)
        if not match:
            raise ValueError('Origin must be an unambiguous github.com repository URL')
        return match[1]

    def revision(self, ref):
        if not isinstance(ref, str) or not ref or ref.startswith('-'):
            raise ValueError('Invalid revision argument')
        return self.git('rev-parse', '--verify', f'{ref}^{{commit}}')

    def candidate(self, head, base):
        config = self.config()
        head_sha, base_sha = self.revision(head), self.revision(base)
        tree = self.git('merge-tree', '--write-tree', base_sha, head_sha).splitlines()[0]
        inputs = {}
        for relative in config['verification']['material_inputs']:
            path = safe_path(self.root, relative)
            if not path.is_file():
                raise ValueError(f'Missing material input: {relative}')
            inputs[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        env = {key: os.environ.get(key) for key in config['verification']['environment']}
        expected = config['verification']['environment']
        if env != expected:
            raise ValueError('Material environment does not match declared values')
        return {'head': head_sha, 'base': base_sha, 'tree': tree, 'config': digest(config), 'inputs': digest(inputs), 'environment': digest(env)}

    def workspace(self, issue, change, base):
        if self.config()['profile'] == 'github-backlog-v1':
            from .backlog import task_id
            issue = task_id(issue)
            prefix = f'backlog-{issue}'
        elif type(issue) is int and issue > 0:
            prefix = str(issue)
        else:
            raise ValueError('Positive Issue required for the GitHub Issue profile')
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,47}', change):
            raise ValueError('Positive Issue and lowercase change name required')
        sha = self.revision(base)
        name = f'{prefix}-{change}'
        path = safe_path(self.common_dir, f'openharness/workspaces/{name}')
        path.parent.mkdir(parents=True, exist_ok=True)
        branch = f'codex/{name}'
        if path.exists():
            raise ValueError('Workspace already exists; reconcile instead of reusing blindly')
        self.git('worktree', 'add', '-b', branch, str(path), sha)
        return {'work_item': issue, 'change': change, 'branch': branch, 'path': str(path), 'base': sha, 'protected_scope': f'change:{branch}'}


def bootstrap(repo, repository=None, target='main', governed_upgrade=False, profile=None, work=None):
    runtime = safe_path(repo.common_dir, 'openharness/runtime.json')
    if runtime.exists() and not governed_upgrade:
        try:
            lifecycle = json.loads(runtime.read_text(encoding='utf-8'))['lifecycle']
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError('Bootstrap cannot bypass damaged lifecycle state; use explicit break-glass recovery') from exc
        if lifecycle != 'GENESIS':
            raise ValueError('Bootstrap has no managed lifecycle exemption; use governed upgrade or explicit break-glass recovery')
    repository = repository or repo.identity()
    if repository.lower() != repo.identity().lower():
        raise ValueError('Requested repository does not match origin authority')
    config = default_config(repository, target)
    if safe_path(repo.root, '.harness/config.json').exists():
        config = repo.config()
        if (profile is not None and profile != config['profile']) or (work is not None and work != config.get('work')):
            raise ValueError('Bootstrap cannot reconfigure installed authority; use reviewed upgrade')
    elif profile is not None:
        config['profile'] = profile
        if profile == 'github-backlog-v1':
            config['authorities']['work'] = 'repository-backlog'
            config['work'] = work
        elif work is not None:
            raise ValueError('Work configuration is only supported by the Backlog profile')
    validate_config(config)
    from .ci import workflow_text
    plans = {
        '.harness/config.json': json_text(config), '.harness/AGENT.md': entry_text(config),
        '.harness/github-workflow.yml.template': workflow_text(),
    }
    agents_path = safe_path(repo.root, 'AGENTS.md')
    agents = agents_path.read_text(encoding='utf-8') if agents_path.exists() else ''
    if MARKER not in agents:
        plans['AGENTS.md'] = agents + INSTRUCTION
    changes = []
    for relative, content in plans.items():
        path = safe_path(repo.root, relative)
        if path.exists():
            if relative == '.harness/config.json':
                existing = repo.config()
                if existing['repository'] != repository or existing['target'] != target:
                    raise ValueError('Installed project identity differs; use reviewed upgrade')
                continue
            if relative != 'AGENTS.md' and path.read_text(encoding='utf-8') != content:
                legacy = {'.harness/AGENT.md': LEGACY_ENTRY, '.harness/github-workflow.yml.template': LEGACY_WORKFLOW}
                if not governed_upgrade or path.read_text(encoding='utf-8') != legacy.get(relative):
                    raise ValueError(f'Installation conflict: {relative}; no files changed')
            elif relative != 'AGENTS.md':
                continue
        changes.append((path, content))
    backups = []
    try:
        for path, content in changes:
            path.parent.mkdir(parents=True, exist_ok=True)
            previous = path.read_bytes() if path.exists() else None
            if previous is None:
                with path.open('x', encoding='utf-8', newline='\n') as stream:
                    backups.append((path, previous))
                    stream.write(content)
            else:
                backups.append((path, previous))
                path.write_text(content, encoding='utf-8', newline='\n')
    except (OSError, ValueError):
        for path, previous in reversed(backups):
            if previous is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(previous)
        raise
    return {'lifecycle': 'GENESIS', 'changed': [str(p.relative_to(repo.root)) for p, _ in changes], 'activation': 'Run live doctor; no automatic activation', 'ci': 'Staged .harness/github-workflow.yml.template; not yet wired or trusted'}
