# OpenHarness

OpenHarness turns a frozen repository guarantee contract into executable evaluation,
native Git workspaces, candidate-bound local verification and explicit recovery.
Project truth stays in the target repository. The existing Backlog or Issues remain work authority; native PRs, canonical refs
and project CI remain their respective sources of truth.

**Version 0.3 adds explicit legacy Backlog adoption and release ownership metadata.** Run `entry` and `doctor`
for actual current lifecycle and guarantees; a saved report cannot activate a repository.
The [frozen contract](docs/contracts/repository-agent-harness-v1.0.md) remains normative.

## Install

Requires Python 3.11+, Git 2.38+ (`merge-tree --write-tree`), and authenticated
[GitHub CLI](https://cli.github.com/manual/gh_auth_login) with read access to repository
metadata and the work/PR/CI used by an operation. Enforcement configuration access
is additionally required for strict operation and full audits. Permission errors
are unresolved observations. This version supports `github.com` and the
`github-pr-v1` profile, plus the bounded [canonical Backlog profile](docs/backlog-profile.md)
with its separate producer and native deployment proof for strict operation. Windows and
POSIX native process locks are supported.

```sh
python -m venv .venv
# Activate the environment using your shell's activation command.
python -m pip install -e .
openharness --help
```

Use `python -m openharness` directly from this source directory without installation.
All commands emit JSON. A successful default `entry` means orientation succeeded,
not that closure was observed. Exit `0` means that command succeeded, `2` means an open gap,
stale proof or failing candidate check, and `1` means invalid input/tool failure.
A successful local verification never authorizes remote integration.


## Feedback from real Agent use

OpenHarness is intended to improve from actual use by different agents, runtimes and projects.
If an Agent or operator encounters confusing behavior, unnecessary ceremony, a missing reusable
capability, an enforcement false positive/negative, poor discoverability, or another recurring
friction point, report the observed problem rather than compensating with undocumented local
workarounds.

Open an Issue using the **Agent feedback** template and include the execution context, expected
and actual behavior, and the smallest evidence that makes the problem inspectable. If the
problem is already well understood and a bounded change can be verified, an Issue-bound PR is
welcome through the normal managed path.

Feedback is evidence, not automatic authority to relax guarantees. Improvements should preserve
or strengthen the declared execution/trust envelope, prefer native provider/runtime capabilities
where sufficient, and add only the OpenHarness-specific delta.

## Default: use the existing project workflow

The CLI defaults new installations to **cooperative** execution. Private GitHub Free
repositories can use workspaces, acceptance and exact-head PR integration without
rulesets, deployment proof or managed activation. Existing installations without a
`mode` field retain strict behavior; permission errors never auto-downgrade them.

```sh
openharness --repo /path/to/project bootstrap --target develop
openharness --repo /path/to/project entry
```

Keep project-owned instructions and CI. Review the config once: select the existing
work authority, acceptance argv, required check, its App id and workflow path. For
Backlog use the existing bounded reader; task files and Backlog configuration are
not migrated. Bind an existing worktree with `workspace --task TASK-1 --change fix
--bind`, preserving its branch, or create one with the existing workspace command.
See the [short cooperative recipe](docs/cooperative-workflow.md).

Daily `entry` is local orientation: no API calls, task enumeration or full Doctor.
Successful `verify` and `evidence` output concise summaries; `--verbose` includes
details. `entry --full` and `doctor` explicitly request live audits. Strict protected
transitions continue to revalidate complete closure.

Cooperative checks can be bypassed by administrators and repository writers.
They do not establish server enforcement or complete closure. Missing native
capabilities remain OPEN GAP in Doctor; they do not block independent core operations.
There is no requirement to change the repository's plan or visibility.

## Optional strict bootstrap

```sh
openharness --repo /path/to/project bootstrap --mode strict --target main
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
any-source checks and must not be done. Configure immutable controller repository/revision
and sandbox image pins. `setup-apply` explicitly installs resolved native policies in
Genesis, saves exact payloads and never activates. Existing policy names require operator
review. Commit the compiler template to `.github/workflows/openharness.yml` on the target.

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

Dependencies must also be available in the clean candidate environment. See the
[locked dependency recipe](docs/offline-dependencies.md) for reviewed immutable
project images, offline scratch execution, import resolution and local diagnostics.
Ignored source dependencies are not copied into candidates.

## Agent skill

The reusable [openharness skill](skills/openharness/SKILL.md) helps Codex enter an
installed repository, follow its live lifecycle, and recover without bypassing
authority. Copy `skills/openharness` into your Codex skills directory (normally
`~/.codex/skills/openharness`) to make it discoverable across projects. The skill
does not install or activate OpenHarness and is not a repository guarantee; use
the project-local instructions and current `entry`/`doctor` results for authority.

## Supported execution envelope

The separate `github-backlog-v1` adapter keeps canonical Backlog task files as the
sole work authority, with explicit executor mapping and immutable task/dependency
reads. It does not migrate this repository's Issue authority. Read its exact supported
format and deployment boundaries before adoption in the [profile guide](docs/backlog-profile.md).

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
legal live work. Bootstrap authority
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

The native profile requires strict up-to-date checks and merge-only PRs. The trusted
`pull_request_target` workflow loads baseline acceptance configuration and immutable
tool source, then tests the candidate in a read-only Docker sandbox with no network,
credentials, capabilities or host write mounts. A separate hosted publisher re-observes
head/base/tree/work authority. An all-workflow native Actions event policy permits only
baseline `pull_request_target`, blocking candidate push/PR/dispatch source spoofing.

PRs require exactly one `Work-Item: #N` line and their Issue-bound Change branch.
Changes to `.github/`, `.harness/` or `AGENTS.md` require a repository-owner Issue
comment with `OpenHarness-Control-Approval: HEAD_SHA BASE_SHA`. Both old and proposed
acceptance configurations run when config changes. Control changes use the same gate.

`integrate --pr N` merges the exact clean bound candidate through native enforcement
and confirms the integrated tree; no administrator bypass is requested. `release`
requires recorded native integration and preserves worktree and Issue. `handoff
--reason TEXT` preserves the binding, head and continuity note for the next single writer.

## Doctor and lifecycle

Doctor always evaluates all 16 candidate guarantees from the fixed profile. Unknown
applicability, omitted observations, unsupported inherited rules, truncated API lists,
unavailable check provenance and missing mechanisms block closure. No repository field
can shrink the catalogue or self-attest a guarantee.

Doctor reads effective branch rules, ruleset details including inherited organization
rules, bypass actors, legacy protection, target identity, workflow metadata and target
workflow blob identities, immutable tool code and native Actions policy. This version
requires ruleset enforcement plus strict merge-only integration or a native merge queue;
legacy protection alone is reported without asserting equivalence. Rules from unrelated
active rulesets can conservatively produce a gap if their applicability/bypass cannot
be narrowed. Workflow content or policy changes alter the observed fingerprint. Target
commit movement alone changes candidate freshness rather than policy identity.

Genesis reports contain **readiness assessments**, not established repository
guarantees. Break-glass invalidates every advertised guarantee. Even a complete readiness
assessment requires an explicit live Activation transition. Record native valid,
invalid, source-spoof and direct-update PR/head/rule-suite references in
`.harness/deployment-proof.json`, bound to the current Doctor policy fingerprint.
Doctor re-fetches results, historical controller/config and integrated trees;
missing, stale or incomplete native proof blocks coverage and activation.

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
activation. Exact generated v0.1 artifacts can migrate to the current compiler;
custom artifact conflicts are preserved and require an explicit implementation delta.

When `workspace` or `preflight` rejects current closure, its JSON error includes
`diagnostics` from that exact Doctor observation: observation time, provider errors,
native gate/controller state, deployment-proof result, guarantee gaps, readiness and
saved/current substrate identities. A later successful Doctor is a new observation,
not proof that the rejected transition was legal. Readiness with an activation mismatch
requires revalidation and explicit activation; unavailable observations or proof must
be resolved before retrying. The rejection does not create a binding or relax a gate.

## Verification and remaining delta

```sh
python -m unittest discover -s tests -v
python -m compileall -q openharness
```

The suite uses real temporary Git repositories/worktrees and deterministic GitHub API
responses. It covers invalid/valid local paths, omitted guarantees, competing writers,
unknown applicability, source checks, bypass policy, base changes, workflow drift,
merged-result verification, failed checks, interruption and fresh processes. Local
validation covers Windows; trusted candidate CI covers Linux. Fixture success is separate
from live deployment proof.

Current native closure requires live deployment proof, not fixture PASS. Effective
ownership/fencing remains required if competing writers enter scope. See
[native delta](docs/plans/2026-09-26-native-closure.md), [design](docs/plans/2026-09-26-github-harness-design.md),
[plan](docs/plans/2026-09-26-github-harness.md) and `docs/verification.md` for current evidence.

GitHub source semantics: [rules and sourced checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets),
[merge-group checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks),
[rules REST API](https://docs.github.com/en/rest/repos/rules).

## Current native validation

See the [repaired producer deployment record](docs/native-boundary-validation.md)
and canonical `.harness/deployment-proof.json`. The independently installed v0.3.0
tool from reviewed source has activated this repository's configured profile;
the post-activation live audit established 14 guarantees, with 2 not applicable
under the trusted single-writer scope. `entry`/`doctor` must still revalidate current
state. The [earlier deployment record](docs/native-deployment-validation.md) is historical.

The conservative adapter requires repository Actions enabled, one canonical trusted
workflow and the native all-workflow event policy. It supports `allowed_actions: all`
or fully observed `selected` settings allowing GitHub-owned Actions or both exact
compiler Action SHA entries. Other allowlist interpretations and competing/unknown
workspace writers remain explicit unsupported scope. Native publisher logs are part
of proof: expiration or unavailability invalidates closure and requires fresh proof.
The [proof recovery guide](docs/proof-recovery.md) explains failure phases, observation
costs, renewal and strict/cooperative compatibility. Immutable objects are reused only
within one live audit; mutable authority and final target freshness are re-observed.

Harness self-upgrades also protect tool code, acceptance tests and frozen contracts
when this repository hosts its producer. These changes retain exact owner authority
and native integration; observer-only code is distinguished from executed producer
dependencies. Local verifier code/runtime identity still invalidates stale activation.

## Release → consumer upgrades

[Consumer upgrades](docs/consumer-upgrades.md) use immutable stable releases and
self-hosted Renovate to discover, propose and verify upgrades. Execution stays
pinned to the existing controller SHA. Machine-readable installation metadata,
explicit compatibility and transactional generated-artifact migration preserve
project configuration. Normal Issue-bound PRs, exact owner control approval and
native checks still govern integration. Changed installations require fresh
native deployment proof, Doctor and explicit activation; no bot activates a
consumer. Start with explicit enrollment of an already pinned published release.
