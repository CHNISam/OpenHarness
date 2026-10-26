# Opt-in runner guard implementation plan

Goal: protect trusted high-resource commands without changing Core, consumer
authority, test content, runner selection, workflow permissions or activation.

Architecture: additive standard-library command wrapper and Composite Action.
Use OS file locking and Windows Job Objects, not a scheduler or service. Consumers
adopt a reviewed full SHA separately. No private consumer material belongs here.

Work authority: Issue #45, isolated `codex/45-runner-guard` workspace. Genesis local
diagnostics grant no protected integration or deployment authority.

1. Add `tests/test_runner_guard.py`; show failure before the new module exists.
2. Add `openharness/runner_guard.py`: argv validation, shared native lock, disk
   preflight, finite budgets, suspended Windows launch, Job containment and cleanup.
3. Exercise real processes: contention, failure/retry, timeout with descendants,
   abrupt wrapper death, cache/work preservation. Use synthetic inputs only.
4. Add `actions/runner-guard/action.yml`; run its actual PowerShell body with literal
   shell-looking Unicode argv and compare the original acceptance result.
5. Document explicit SHA adoption/rollback, native optional hook procedure, trust
   prerequisites and network-accounting limitations in `docs/runner-guard.md`.
6. Run the existing full unittest suite and compileall when host resources permit;
   inspect the complete diff and unchanged Core/control paths. Preserve failures,
   distinguish synthetic verification from real consumer/runner evidence, submit
   the Issue-bound PR through existing gates, and do not self-author owner consent.

Alternative choices: job hooks alone cannot retain a lock after the pre-hook exits;
repository concurrency does not span repositories; a new scheduler/cache server
adds unnecessary operations. Retain project-native checkout, caching and validation
capabilities rather than replace them in this slice. Issue #34 needs independent
approval-mechanism work; do not imply that this additive toolkit resolves it.
