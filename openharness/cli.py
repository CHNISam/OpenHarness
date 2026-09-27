"""JSON CLI; exit 2 is an explicit open gap/failed proof, never success."""

import argparse
import json
import subprocess
import sys

from . import __version__
from .repository import Repository, bootstrap, json_text, safe_path
from .runtime import Runtime


def parser():
    command = argparse.ArgumentParser(description='OpenHarness native GitHub profile')
    command.add_argument('--repo', default='.', help='Target repository path')
    command.add_argument('--version', action='version', version=__version__)
    commands = command.add_subparsers(dest='command', required=True)
    install = commands.add_parser('bootstrap', help='Stage missing project-local mechanisms without activation')
    install.add_argument('--repository', help='owner/repository; defaults to origin')
    install.add_argument('--target', default='main')
    install.add_argument('--profile', choices=['github-pr-v1', 'github-backlog-v1'])
    install.add_argument('--work-config', help='Repository-relative JSON Backlog adapter configuration for Genesis')
    for name, help_text in (
        ('doctor', 'Observe live GitHub substrate and evaluate every candidate guarantee'),
        ('entry', 'Discover instructions, authority, work and current closure'),
        ('activate', 'Require complete live closure before entering managed operation'),
        ('preflight', 'Reject invalid protected transition'),
        ('reconcile', 'Observe authoritative state and invalidate stale local projections'),
        ('setup-plan', 'Emit reviewable remote setup proposal without applying it'),
        ('setup-apply', 'Install resolved native policy in Genesis without activating'),
        ('release', 'Release an integrated binding while preserving worktree and Issue'),
    ):
        commands.add_parser(name, help=help_text)
    upgrade = commands.add_parser('upgrade', help='Stage governed artifacts or an immutable release migration')
    upgrade.add_argument('--release', help='Exact stable SemVer; never a runtime ref')
    upgrade.add_argument('--enroll', action='store_true', help='Record the already pinned immutable release')
    integrate = commands.add_parser('integrate', help='Integrate exact bound candidate through native protected PR merge')
    integrate.add_argument('--pr', type=int, required=True)
    handoff = commands.add_parser('handoff', help='Record continuity in the existing isolated workspace')
    handoff.add_argument('--reason', required=True)
    exceptional = commands.add_parser('break-glass', help='Record local exceptional recovery; grants no remote bypass')
    exceptional.add_argument('--reason', required=True)
    workspace = commands.add_parser('workspace', help='Bind an open Issue/Change to a native isolated worktree')
    work_item = workspace.add_mutually_exclusive_group(required=True)
    work_item.add_argument('--issue', type=int)
    work_item.add_argument('--task', help='Exact canonical Backlog task ID')
    workspace.add_argument('--change', required=True)
    workspace.add_argument('--genesis', action='store_true', help='Explicit bootstrap installer authority, only before activation')
    for name in ('candidate', 'verify', 'evidence'):
        candidate = commands.add_parser(name, help='Candidate-bound local diagnostics (not remote integration authority)')
        candidate.add_argument('--head', required=True)
        candidate.add_argument('--base', required=True, help='Explicit intended target revision/ref; no implicit moving base')
        if name == 'verify':
            candidate.add_argument('--timeout', type=int, default=300, help='Per-command timeout in seconds')
    return command


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        repo = Repository(args.repo)
        runtime = Runtime(repo)
        exit_code = 0
        if args.command == 'bootstrap':
            work = json.loads(safe_path(repo.root, args.work_config).read_text(encoding='utf-8')) if args.work_config else None
            result = bootstrap(repo, args.repository, args.target, profile=args.profile, work=work)
        elif args.command == 'break-glass':
            result = runtime.break_glass(args.reason)
        elif args.command == 'upgrade':
            if args.enroll and not args.release:
                raise ValueError('--enroll requires --release')
            result = runtime.upgrade(args.release, args.enroll)
        elif args.command == 'integrate':
            result = runtime.integrate(args.pr)
        elif args.command == 'handoff':
            result = runtime.handoff(args.reason)
        elif args.command == 'workspace':
            result = runtime.workspace(args.task if args.task is not None else args.issue, args.change, args.genesis)
        elif args.command == 'candidate':
            from .model import candidate_id
            candidate = runtime._verification_candidate(args.head, args.base)
            result = {'candidate': candidate, 'candidate_id': candidate_id(candidate), 'authority': 'local-diagnostic-only'}
        elif args.command == 'verify':
            if args.timeout <= 0:
                raise ValueError('Timeout must be positive')
            result = runtime.verify(args.head, args.base, args.timeout)
            exit_code = 0 if result['passed'] else 2
        elif args.command == 'evidence':
            result = runtime.evidence(args.head, args.base)
            exit_code = 0 if result['fresh'] else 2
        else:
            action = getattr(runtime, args.command.replace('-', '_'))
            result = action()
            if args.command == 'doctor':
                exit_code = 0 if result['closure'] else 2
            elif args.command in ('entry', 'reconcile'):
                exit_code = 0 if result['doctor']['closure'] else 2
        print(json_text(result), end='')
        return exit_code
    except (ValueError, OSError, subprocess.SubprocessError, KeyError, TypeError) as exc:
        result = {'error': str(exc), 'command': args.command, 'closure': False}
        if hasattr(exc, 'diagnostics'):
            result['diagnostics'] = exc.diagnostics
        print(json_text(result), file=sys.stderr, end='')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
