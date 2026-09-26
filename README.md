# OpenHarness

OpenHarness turns a frozen repository guarantee contract into executable evaluation,
native Git workspaces, candidate-bound local verification and explicit recovery.
Project truth stays in the target repository. GitHub remains the authority for
Issues, PRs, canonical refs, integration rules and accepted checks.

**Version 0.1 is a runnable Genesis toolchain. Full Harness activation is blocked.**
The trusted external verifier/provenance and end-to-end deployment coverage adapters
are still OPEN GAP. The CLI deliberately refuses activation even when provider rules
look correct. This release does not deliver an activated Agent-ready repository.
The [frozen contract](docs/contracts/repository-agent-harness-v1.0.md) remains normative.

## Install

Requires Python 3.11+, Git 2.38+ (`merge-tree --write-tree`), and authenticated
[GitHub CLI](https://cli.github.com/manual/gh_auth_login) with read access to repository
metadata, Issues, workflows, contents and enforcement configuration. Permission errors
are unresolved observations. This version supports `github.com` and the
`github-pr-v1` profile. Windows and POSIX native process locks are supported.

```sh
python -m venv .venv
# Activate the environment using your shell's activation command.
python -m pip install -e .
openharness --help
```

Use `python -m openharness` directly from this source directory without installation.
All commands emit JSON. Exit `0` means that command succeeded, `2` means an open gap,
stale proof or failing candidate check, and `1` means invalid input/tool failure.
A successful local verification never authorizes remote integration.

## Bootstrap a target

```sh
openharness --repo /path/to/project bootstrap --target main
openharness --repo /path/to/project setup-plan
openharness --repo /path/to/project doctor
openharness --repo /path/to/project entry
```

Bootstrap stages `.harness/config.json`, `.harness/AGENT.md` and a review-only CI
template. It appends one discoverability entry to `AGENTS.md`, preserving project
instructions. Repeated installation preserves valid custom configuration. Conflicting
generated files stop the entire installation before it changes files. Control and
material input paths reject symlinks, junctions and traversal.

`setup-plan` emits a proposed GitHub ruleset plus unresolved wiring steps. It never
updates GitHub. Its unresolved App id is a placeholder; applying null would permit
any-source checks and must not be done. The merge queue and trusted verifier require
separate setup; the proposal is intentionally not an activation-ready API request.
The staged CI template fails until a trusted verifier has been installed.

The project must explicitly configure acceptance commands as argument arrays:

```json
{
  "commands": [["python", "-m", "unittest", "discover", "-s", "tests", "-v"]],
  "material_inputs": ["tests/fixtures/example.json"],
  "environment": {"PROJECT_TEST_MODE": "stable"},
  "required_check": "openharness / candidate",
  "expected_app_id": null
}
```

These are the fields of `config.verification`, not a standalone configuration.
No acceptance command is invented for an unknown project. Material inputs must be
files within the repository and match the tested result checkout. Set each declared
material environment value in the invoking process. Verification configuration and
acceptance semantics are trusted project inputs; review them before running commands.
Local execution uses the executor's existing permissions/sandbox. OpenHarness does
not supply an additional process sandbox.

## Supported execution envelope

The default topology trusts one executor writer per workspace. Administrators and
CI maintainers are trusted substrate operators. Arbitrary local writes and privileged
policy reconfiguration are outside the protected transition envelope. Reconfiguration
still invalidates observed closure. These are explicit scope assumptions, not detected
OS access restrictions. Set `workspace_writers` to `multiple` or `unknown` whenever
the single-writer assumption is untrue or unproven; ownership/fencing then remain gaps.
This version has no effective exclusive ownership adapter or distributed claim service.

Each work Issue can have multiple Changes. Changes receive distinct native worktrees
and branches. This does not prove arbitrary path scopes independent. Conflicting
canonical integration is delegated to provider-native gates and candidate verification.

For explicit authorized Genesis installer work:

```sh
openharness --repo /path/to/project workspace --issue 123 --change fix-parser --genesis
```

The Issue must be open and the base must be observable from GitHub. A Change binding
records the Issue, branch, base and workspace. The optional fetch goes through the
configured `origin`; no canonical ref is changed. Bindings and lifecycle observations
live in the Git common directory, so a fresh process and sibling worktree can locate
them. They are local operational projections, never GitHub ownership claims.

Managed `workspace` and `preflight` require current activation, a valid binding and
legal live work. These commands are intentionally blocked in v0.1. Bootstrap authority
is unavailable after exceptional/managed operation. Direct filesystem mutation is not
restricted by a local hook and cannot be represented as a protected transition.

## Integration candidate and evidence

```sh
openharness --repo /path/to/project candidate --head HEAD --base origin/main
openharness --repo /path/to/project verify --head HEAD --base origin/main
openharness --repo /path/to/project evidence --head HEAD --base origin/main
```

Resolve/fetch the intended base before invoking these commands. Explicit base refs
must represent the actual intended target; local diagnostic commands do not assert
that `origin/main` is currently GitHub's head.

Verification requires a clean source checkout. Git computes the merged result tree,
then commands run on that result in a temporary detached worktree. Conflicts are
rejected. Head, base, result tree, verification configuration, material inputs,
declared material environment and verifier code/runtime identity bind the evidence.
The source is checked again after execution. Test mutation of the candidate checkout,
nonzero exit and timeout fail verification. Diagnostics are stored under
`<git-common-dir>/openharness/evidence`, with bounded stdout/stderr. The records are
trusted-local diagnostic observations; modifying them can never produce accepted
GitHub integration proof.

GitHub's real merge-group candidate must be verified through trusted provider wiring.
A stale local diagnostic record or a candidate-editable workflow cannot satisfy that
requirement. A sourced check alone also leaves provenance unproven.

## Doctor and lifecycle

Doctor always evaluates all 16 candidate guarantees from the fixed profile. Unknown
applicability, omitted observations, unsupported inherited rules, truncated API lists,
unavailable check provenance and missing mechanisms block closure. No repository field
can shrink the catalogue or self-attest a guarantee.

Doctor reads effective branch rules, ruleset details including inherited organization
rules, bypass actors, legacy protection, target identity, workflow metadata and target
workflow blob identities. This version requires ruleset enforcement plus a merge queue;
legacy protection alone is reported without asserting equivalence. Rules from unrelated
active rulesets can conservatively produce a gap if their applicability/bypass cannot
be narrowed. Workflow content or policy changes alter the observed fingerprint. Target
commit movement alone changes candidate freshness rather than policy identity.

Genesis reports contain **readiness assessments**, not established repository
guarantees. Break-glass invalidates every advertised guarantee. Even a complete readiness
assessment would require an explicit live Activation transition. v0.1 leaves provenance
and enforcement coverage unresolved in every assessment.

```sh
openharness --repo /path/to/project activate
openharness --repo /path/to/project preflight
openharness --repo /path/to/project reconcile
openharness --repo /path/to/project break-glass --reason "repair damaged control files"
openharness --repo /path/to/project upgrade
```

Reconcile observes current authority, invalidates stale managed state and removes dead
workspace bindings. It preserves user worktrees and never reacquires authority or
reactivates automatically. Native process locks serialize local lifecycle updates;
OS process exit releases locks without a lease coordinator. Break-glass works with
broken project configuration, preserves corrupt local runtime data, records its reason
and grants no GitHub bypass. Repair files explicitly, rerun verification and Doctor;
return to Managed Operation requires complete closure and activation. Upgrade runs
the non-destructive installer under applicable governance and invalidates affected
activation. In v0.1 it can restage missing current-version artifacts; incompatible
artifact migrations require a reviewed implementation delta.

## Verification and remaining delta

```sh
python -m unittest discover -s tests -v
python -m compileall -q openharness
```

The suite uses real temporary Git repositories/worktrees and deterministic GitHub API
responses. It covers invalid/valid local paths, omitted guarantees, competing writers,
unknown applicability, source checks, bypass policy, base changes, workflow drift,
merged-result verification, failed checks, interruption and fresh processes. CI runs
this suite on Windows and Linux. Fixture success is separate from live deployment proof.

Remaining implementation delta: trusted external verification adapter, provider-bound
candidate proof/provenance and authoritative-path/bypass deployment tests; effective
ownership/fencing if competing writers enter scope; provider integration/release/handoff
commands once their enforcement can be established. No merge command is offered before
those guarantees are proven. See [design](docs/plans/2026-09-26-github-harness-design.md),
[plan](docs/plans/2026-09-26-github-harness.md) and `docs/verification.md` for current evidence.

GitHub source semantics: [rules and sourced checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets),
[merge-group checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks),
[rules REST API](https://docs.github.com/en/rest/repos/rules).
