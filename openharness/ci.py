"""Trusted baseline controller; candidate code executes only inside native Docker."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from .model import digest, validate_config
from .provider import gh_api, gh_write
from .repository import Repository, safe_path

WORKFLOW_PATH = '.github/workflows/openharness.yml'
CHECKOUT = '11d5960a326750d5838078e36cf38b85af677262'
PYTHON = 'a26af69be951a213d495a4c3e4e4022e16d87065'


def event_policy():
    return {'name': 'OpenHarness trusted baseline events', 'enforcement': 'active',
            'conditions': {}, 'rules': [{'type': 'restrict_action_events',
            'parameters': {'allowed_events': ['pull_request_target']}}]}


def workflow_text():
    # Fixed compiler output, not parsed from candidate-controlled YAML. Publisher
    # has its own hosted runner and never downloads/executes candidate artifacts.
    common = f'''      - uses: actions/checkout@{CHECKOUT}
        with:
          ref: ${{{{ github.sha }}}}
          path: baseline
          persist-credentials: false
      - uses: actions/setup-python@{PYTHON}
        with:
          python-version: '3.13'
      - id: source
        name: Read trusted immutable tool source
        run: |
          python -c 'import json,os; c=json.load(open("baseline/.harness/config.json")); s=c["verification"]["controller"]; f=open(os.environ["GITHUB_OUTPUT"],"a"); print("repository="+s["repository"],file=f); print("revision="+s["revision"],file=f)'
      - uses: actions/checkout@{CHECKOUT}
        with:
          repository: ${{{{ steps.source.outputs.repository }}}}
          ref: ${{{{ steps.source.outputs.revision }}}}
          path: tool
          persist-credentials: false
'''
    return '''name: OpenHarness trusted controller
on:
  pull_request_target:
    types: [opened, synchronize, reopened, edited, ready_for_review]
permissions: {}
concurrency:
  group: openharness-${{ github.event.pull_request.number }}
  cancel-in-progress: true
jobs:
  verify:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: read
      issues: read
    outputs:
      head: ${{ steps.check.outputs.head }}
      base: ${{ steps.check.outputs.base }}
      tree: ${{ steps.check.outputs.tree }}
      identity: ${{ steps.check.outputs.identity }}
    steps:
''' + common + f'''      - uses: actions/checkout@{CHECKOUT}
        with:
          ref: ${{{{ github.event.pull_request.head.sha }}}}
          path: candidate
          fetch-depth: 0
          persist-credentials: false
      - id: check
        name: Verify actual candidate inside credential-free sandbox
        env:
          GH_TOKEN: ${{{{ github.token }}}}
          PYTHONPATH: ${{{{ github.workspace }}}}/tool
        run: python -m openharness.ci verify --baseline baseline --candidate candidate
  publish:
    needs: verify
    if: always()
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: read
      issues: read
      statuses: write
    steps:
''' + common + '''      - name: Publish only fresh trusted result
        env:
          GH_TOKEN: ${{ github.token }}
          PYTHONPATH: ${{ github.workspace }}/tool
          CANDIDATE_RESULT: ${{ needs.verify.result }}
          CANDIDATE_HEAD: ${{ needs.verify.outputs.head }}
          CANDIDATE_BASE: ${{ needs.verify.outputs.base }}
          CANDIDATE_TREE: ${{ needs.verify.outputs.tree }}
          CANDIDATE_IDENTITY: ${{ needs.verify.outputs.identity }}
        run: python -m openharness.ci publish --baseline baseline
'''


def candidate_context(config, pull, issue):
    refs = re.findall(r'^Work-Item: #(\d+)\s*$', pull.get('body') or '', flags=re.MULTILINE)
    if len(refs) != 1:
        raise ValueError('PR must bind exactly one canonical Work-Item: #N')
    number = int(refs[0])
    if pull.get('state') != 'open' or pull.get('draft') or pull.get('base', {}).get('ref') != config['target']:
        raise ValueError('Only open ready PRs targeting the configured authority are legal')
    if issue.get('state') != 'open' or issue.get('number') != number or 'pull_request' in issue:
        raise ValueError('Canonical work Issue must still be open')
    if not re.fullmatch(rf'codex/{number}-[a-z][a-z0-9-]{{0,47}}', pull.get('head', {}).get('ref', '')):
        raise ValueError('Change branch must bind the Issue and isolated Change namespace')
    head, base = pull['head']['sha'], pull['base']['sha']
    if not all(re.fullmatch(r'[0-9a-f]{40}', sha) for sha in (head, base)):
        raise ValueError('Candidate must contain exact authoritative revisions')
    return {'head': head, 'base': base, 'issue': number, 'pr': pull['number'], 'merge': pull.get('merge_commit_sha')}


def docker_arguments(root, image, argv, environment=None):
    root = str(Path(root).resolve())
    if any(character in root for character in (',', '\n', '\r')):
        raise ValueError('Ambiguous native sandbox mount path')
    if not re.fullmatch(r'[a-z0-9./_-]+@sha256:[0-9a-f]{64}', image or ''):
        raise ValueError('Sandbox image must be immutable and explicitly pinned')
    if not isinstance(argv, list) or not argv or not all(isinstance(v, str) and v for v in argv):
        raise ValueError('Acceptance must be an argv command')
    command = ['docker', 'run', '--rm', '--network', 'none', '--read-only', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges', '--user', '65534:65534', '--pids-limit', '256',
               '--memory', '4g', '--cpus', '2', '--tmpfs', '/tmp:rw,mode=1777,size=1g',
               '--mount', f'type=bind,src={root},dst=/candidate,readonly', '--workdir', '/candidate',
               '--env', 'PYTHONDONTWRITEBYTECODE=1', '--env', 'HOME=/tmp']
    for key, value in (environment or {}).items():
        if not re.fullmatch(r'[A-Z][A-Z0-9_]*', key) or any(part in key for part in ('TOKEN', 'SECRET', 'PASSWORD', 'GITHUB', 'GH_')):
            raise ValueError('Material environment cannot inject credential or runner control variables')
        command.extend(['--env', f'{key}={value}'])
    return [*command, image, *argv]


def git_blob(data):
    return hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()


def controller_blobs():
    return {f'openharness/{path.name}': git_blob(path.read_bytes().replace(b'\r\n', b'\n'))
            for path in Path(__file__).parent.glob('*.py')}


def baseline_config(path):
    config = validate_config(json.loads((Path(path) / '.harness/config.json').read_text(encoding='utf-8')))
    if not config['verification'].get('controller') or not config['verification'].get('sandbox_image'):
        raise ValueError('Trusted controller source and immutable sandbox are unresolved')
    return config


def current_context(config, event, api=gh_api):
    prefix = f'repos/{config["repository"]}'
    pull = api(f'{prefix}/pulls/{int(event["pull_request"]["number"])}')
    refs = re.findall(r'^Work-Item: #(\d+)\s*$', pull.get('body') or '', flags=re.MULTILINE)
    if len(refs) != 1:
        raise ValueError('Exactly one work authority required')
    issue = api(f'{prefix}/issues/{int(refs[0])}')
    context = candidate_context(config, pull, issue)
    live = api(f'{prefix}/branches/{config["target"]}')['commit']['sha']
    if context['base'] != live:
        raise ValueError('PR base has not converged to current authoritative target')
    return context


def control_authorized(config, context, api=gh_api):
    prefix = f'repos/{config["repository"]}'
    comments = api(f'{prefix}/issues/{context["issue"]}/comments?per_page=100')
    if len(comments) >= 100:
        raise ValueError('Approval observation incomplete')
    expected = f'OpenHarness-Control-Approval: {context["head"]} {context["base"]}'
    owner = config['repository'].split('/')[0]
    return any(comment.get('user', {}).get('login', '').lower() == owner.lower()
               and expected in comment.get('body', '').splitlines() for comment in comments)


def check_candidate(config, baseline, root, event, api=gh_api):
    context = current_context(config, event, api)
    if Repository(baseline).revision('HEAD') != context['base']:
        raise ValueError('Trusted baseline is stale; refresh the provider event')
    repo = Repository(root)
    if repo.revision('HEAD') != context['head']:
        raise ValueError('Checked-out subject differs from the current PR head')
    repo.git('merge-base', '--is-ancestor', context['base'], context['head'])
    tree = repo.git('rev-parse', 'HEAD^{tree}')
    merged = repo.git('merge-tree', '--write-tree', context['base'], context['head']).splitlines()[0]
    if tree != merged:
        raise ValueError('Strict candidate head must equal intended integration result tree')
    changed = repo.git('diff', '--name-only', '--no-renames', context['base'], context['head']).splitlines()
    protected = any(p.startswith(('.github/', '.harness/')) or p == 'AGENTS.md' for p in changed)
    authorized = control_authorized(config, context, api) if protected else False
    if protected and not authorized:
        raise ValueError('Protected control change requires native owner approval bound to head and base')
    # If controls change, both old and proposed acceptance configurations are tested.
    configurations = [config]
    if '.harness/config.json' in changed:
        proposed = validate_config(json.loads(repo.git('show', 'HEAD:.harness/config.json')))
        if proposed['repository'] != config['repository'] or proposed['target'] != config['target']:
            raise ValueError('Control upgrade cannot silently move semantic authority')
        configurations.append(proposed)
    checks = []
    for selected in configurations:
        verification = selected['verification']
        commands = verification['commands']
        if not commands:
            raise ValueError('Project acceptance commands are unresolved')
        for relative in verification['material_inputs']:
            if not safe_path(repo.root, relative).is_file():
                raise ValueError(f'Material input missing from candidate: {relative}')
        for argv in commands:
            command = docker_arguments(repo.root, verification['sandbox_image'], argv, verification['environment'])
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
            checks.append({'argv': argv, 'returncode': result.returncode, 'stdout': result.stdout[-4096:], 'stderr': result.stderr[-4096:]})
            if result.returncode:
                raise ValueError('Candidate acceptance failed: ' + json.dumps(checks[-1]))
    if current_context(config, event, api) != context or repo.git('status', '--porcelain'):
        raise ValueError('Candidate/work authority changed during verification')
    identity = digest({'context': context, 'tree': tree, 'verification': config['verification']})
    return {**context, 'tree': tree, 'identity': identity, 'checks': checks, 'control_authorized': authorized}


def publish(config, event, result, head, base, tree, identity, api=gh_api, write=gh_write):
    prefix = f'repos/{config["repository"]}'
    pull = api(f'{prefix}/pulls/{int(event["pull_request"]["number"])}')
    state = 'failure'
    if result == 'success':
        context = current_context(config, event, api)
        actual_tree = api(f'{prefix}/git/commits/{context["head"]}')['tree']['sha']
        expected_identity = digest({'context': context, 'tree': actual_tree, 'verification': config['verification']})
        if head == context['head'] and base == context['base'] and tree == actual_tree and identity == expected_identity:
            state = 'success'
    url = f'https://github.com/{config["repository"]}/actions/runs/{os.environ["GITHUB_RUN_ID"]}'
    payload = {'state': state, 'context': config['verification']['required_check'], 'description': f'candidate {identity[:32] if identity else "rejected"}', 'target_url': url}
    subjects = {pull['head']['sha']}
    if pull.get('merge_commit_sha'):
        subjects.add(pull['merge_commit_sha'])
    for sha in subjects:
        write(f'{prefix}/statuses/{sha}', 'POST', payload)
    return {'state': state, 'subjects': sorted(subjects), 'target_url': url}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['verify', 'publish'])
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--candidate')
    args = parser.parse_args()
    config = baseline_config(args.baseline)
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
    if os.environ.get('GITHUB_EVENT_NAME') != 'pull_request_target' or os.environ.get('GITHUB_REPOSITORY', '').lower() != config['repository'].lower():
        raise ValueError('Only trusted baseline provider events are accepted')
    if args.action == 'verify':
        result = check_candidate(config, args.baseline, args.candidate, event)
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as stream:
            for key in ('head', 'base', 'tree', 'identity'):
                print(f'{key}={result[key]}', file=stream)
    else:
        result = publish(config, event, os.environ.get('CANDIDATE_RESULT'), os.environ.get('CANDIDATE_HEAD'), os.environ.get('CANDIDATE_BASE'), os.environ.get('CANDIDATE_TREE'), os.environ.get('CANDIDATE_IDENTITY'))
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
