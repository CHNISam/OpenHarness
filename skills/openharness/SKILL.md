---
name: openharness
description: Enter, operate, or recover a repository managed by OpenHarness using its live authority, Issue-bound workspace, verification, and protected integration lifecycle. Use when working in an OpenHarness repository or installing OpenHarness into a new project.
---

# OpenHarness

OpenHarness owns repository execution guarantees. The project owns product and engineering truth; the executor owns reasoning, tools, reviews, and task execution. This skill is a route into the installed mechanism, not an alternative authority or guarantee.

## Enter a repository

1. Read repository-local `AGENTS.md`, then `.harness/AGENT.md` if installed. Follow any more specific project instructions.
2. Run `openharness --repo . entry` and `openharness --repo . doctor`. Read their current lifecycle, work authority, workspace bindings, and guarantee gaps. Exit code `2` means an open gap, never success. Saved reports and prior conversation are not live authority.
3. Read only the project owners relevant to the requested work. Keep product decisions and acceptance semantics in that repository.

If OpenHarness is absent, use the canonical [OpenHarness install and bootstrap instructions](https://github.com/CHNISam/OpenHarness#install) for the applicable profile. Inspect existing capabilities before configuring a delta. Do not invent project acceptance commands, owner decisions, or a second work tracker. Installation and activation are distinct; `doctor` readiness does not activate a repository.

## Managed work

Use the repository's declared work authority. In the native GitHub profile, bind an open Issue to a distinct Change with `openharness --repo . workspace --issue N --change NAME`, then work in the returned worktree and branch. Respect the configured single-writer envelope; do not run competing lifecycle operations in that workspace. Run `preflight` before a protected transition.

Build the actual delta and run project checks. For a clean candidate, fetch the configured target and use `candidate --head HEAD --base origin/<target>` and `verify --head HEAD --base origin/<target>`; inspect the result and its exact head/base/tree. These local diagnostics never authorize integration. The PR must come from the bound branch and contain exactly one `Work-Item: #N` line. Wait for the trusted candidate check on the current head/base, then use `openharness --repo . integrate --pr N` and `openharness --repo . release`. Confirm the merged tree and current `doctor` closure before claiming completion.

For other profiles or changed CLI behavior, follow the installed `.harness/AGENT.md` and current OpenHarness documentation rather than these example commands.

## Recover without bypassing authority

Inspect the failed command, `entry`, and `doctor` for the exact gap. A temporary provider observation failure can make a fresh Doctor differ from an earlier one; re-observe before changing lifecycle state. If reconciliation is needed, use `reconcile` and preserve the worktree. It can invalidate activation and does not reactivate automatically. Return to managed operation only through a complete live readiness assessment and `activate`; resolve remaining gaps first.

An active lifecycle command may hold the native process lock. Wait for that command to exit before retrying; do not delete the lock file or edit Harness runtime state. If integration rejects a dirty candidate, inspect and preserve the unexpected changes, then form and verify a clean exact candidate. Never merge directly, forge accepted evidence, or use local verification as a substitute for the trusted provider gate. Use `handoff --reason TEXT` when work must continue in a later session.

The [frozen contract](https://github.com/CHNISam/OpenHarness/blob/main/docs/contracts/repository-agent-harness-v1.0.md) defines the boundary; the installed CLI and live provider observations determine what is currently established.
