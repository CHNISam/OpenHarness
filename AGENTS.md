# OpenHarness contributor entry

Read `docs/contracts/repository-agent-harness-v1.0.md` and `README.md` before changing mechanisms.
The contract is frozen; use implementation evidence to drive applicable deltas.
Current lifecycle is Genesis. This repository has not activated Harness guarantees.

Project product/engineering truth is in the frozen contract and approved design under
`docs/plans/`. GitHub Issues/PRs are the intended work/change authorities once installed.
`todos/` tracks the authorized implementation work; it is a bootstrap artifact rather
than a competing runtime tracker.

Use Python standard-library mechanisms, native Git and read-only `gh api` observation.
Do not turn configuration declarations or fixture test success into proof of live
provider enforcement. Missing/unknown/stale observations remain explicit OPEN GAP.
Do not create local ownership claims that pretend to fence remote writers.

Run `python -m unittest discover -s tests -v` and
`python -m compileall -q openharness` before reporting implementation changes verified.
Keep work sequential in the main task. Follow the configured `codex/` branch convention.

<!-- OpenHarness entry -->
Read `.harness/AGENT.md` and run `openharness --repo . entry` before managed work.
