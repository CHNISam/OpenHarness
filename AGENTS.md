# OpenHarness contributor entry

Read `docs/contracts/repository-agent-harness-v1.0.md` and `README.md` before changing mechanisms.
The contract is frozen; use implementation evidence to drive applicable deltas.
Run `openharness --repo . entry` for current lifecycle and guarantees; saved documents
are historical observations, never activation authority.

Project product/engineering truth is in the frozen contract and approved design under
`docs/plans/`. GitHub Issues/PRs are the intended work/change authorities once installed.
`todos/` tracks the authorized implementation work; it is a bootstrap artifact rather
than a competing runtime tracker.

Use Python standard-library mechanisms, native Git and `gh api` observation.
Explicit `setup-apply` installs reviewed native policies in Genesis. Managed changes
use Issue-bound workspaces, trusted checks and `integrate`; policy reconfiguration
requires the declared trusted repository operator. User-authorized deployment and
closure proof are part of installer work.
Do not turn configuration declarations or fixture test success into proof of live
provider enforcement. Missing/unknown/stale observations remain explicit OPEN GAP.
Do not create local ownership claims that pretend to fence remote writers.


## Agent feedback and contribution

Treat friction observed during real Agent use as product evidence, not something to silently
work around. If OpenHarness is confusing, unnecessarily costly, missing a reusable capability,
produces a false positive/negative, or makes a legal workflow difficult to discover, open a
GitHub Issue with the observed context, expected vs. actual behavior and the smallest useful
evidence. Use the Agent feedback template when applicable.

When the problem and proof are sufficiently understood, an Agent may propose an Issue-bound PR
through the normal managed path. Do not weaken a Guarantee, widen the Trust Envelope, or bypass
native enforcement merely to make the current task easier. Prefer provider/runtime-native
capabilities and build only the missing OpenHarness delta.

Run `python -m unittest discover -s tests -v` and
`python -m compileall -q openharness` before reporting implementation changes verified.
Keep work sequential in the main task. Follow the configured `codex/` branch convention.

<!-- OpenHarness entry -->
Read `.harness/AGENT.md` and run `openharness --repo . entry` before managed work.
