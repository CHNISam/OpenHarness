# Cooperative workflow

Cooperative execution reuses the project's existing work authority, acceptance, CI
and PR path. It needs no activation, policy installation, separate task system or
deployment proof. Use an immutable OpenHarness release SHA for installation/runtime;
never execute a moving main/latest ref. This change is not in published v0.3.0 yet.

## One reviewed configuration

New CLI bootstrap defaults to cooperative. Existing installations keep their mode;
`mode` absent means strict, including the legacy Python bootstrap API. Mode changes
are explicit project control changes, reviewed and merged through the existing
governed path. Local edits cannot downgrade the canonical configuration.

Set `mode` to `cooperative`. Preserve existing acceptance argv/material inputs/env.
Point verification at the existing CI, for example:

```json
{"required_check": "Control and verification", "expected_app_id": 15368,
 "workflow": ".github/workflows/agent-gate.yml"}
```

These are verification fields, alongside the existing commands/inputs/environment.
The selected Actions check must uniquely bind a successful pull_request run to the
same PR/head, App and workflow. No synthetic green check or OpenHarness workflow is
installed. Existing CI and its maintainers are trusted project mechanisms; native
candidate-independent producer enforcement is not claimed. CI source changes need
independent project review, not approval from their own candidate run.

For Backlog select `github-backlog-v1` and its existing explicit `work` reader
settings (directories, legal statuses, completion status, assignee mapping). This
describes the existing authority; no task, status, Backlog config or project
instruction is rewritten. Unsupported/ambiguous corpus or assignment still stops.
An inactive legacy Issue-profile config must explicitly describe the real Backlog
authority before use; bootstrap never silently reinterprets or migrates it.

If the project already integrates PRs, reuse its command via one optional argv:

```json
{"integration_command": ["python", "tools/integrate_pr.py", "--pr", "{pr}",
                         "--item", "{work_item}"]}
```

Only literal pr/work_item substitution is supported; no shell or workflow DSL.
The task spelling supplied when binding is preserved for the project command.
The command's exit code never substitutes for independent GitHub merge observation.

## Daily use

Read project instructions once. `entry` gives a small local orientation with zero
API calls and no claimed fresh activation. Continue the existing project task flow.
For a registered project worktree, `workspace --task TASK-1 --change fix --bind`
binds it without renaming its branch. No task claim/lease is written. New worktrees
can still use the usual workspace command.

Run project acceptance or `verify --head HEAD --base EXACT_BASE_SHA`, retain existing
CI, then `integrate --pr N`. Integration checks canonical work/config, exact clean
head, current base, unchanged CI workflow source and current CI; merges the specified
head through native PRs or the configured project command; then independently checks
the merged commit's parents, tree and current target. Configuration changes must be
reviewed/merged first through project governance. No silent activation or auto-merge.

GitHub PR merge conditions fence head changes but do not atomically condition on base.
Pre-merge observed drift stops; races found after merging are reported with the actual
commit and invalidate the local operation projection. There is no automatic rollback
of a published merge. Administrators/writers may bypass all client checks. Cooperative
success explicitly reports server_enforced=false and closure=false.

`doctor` and `entry --full` are optional full audits; unproven native guarantees remain
OPEN GAP, never false N/A. `--verbose` exposes full successful verification evidence.
Published v0.3.0 artifact migrations describe strict installation only; cooperative
release migration stops explicitly instead of replacing project CI/instructions.
Upgrade the immutable tool installation through the project PR path.
Strict installation, policy setup, independent producer/deployment proof and activation
keep their existing requirements. Do not treat cooperative mode as recovery from an
explicit break-glass operation.
