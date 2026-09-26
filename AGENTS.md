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

Run `python -m unittest discover -s tests -v` and
`python -m compileall -q openharness` before reporting implementation changes verified.
Keep work sequential in the main task. Follow the configured `codex/` branch convention.

<!-- OpenHarness entry -->
Read `.harness/AGENT.md` and run `openharness --repo . entry` before managed work.
