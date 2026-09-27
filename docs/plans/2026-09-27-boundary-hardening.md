# Boundary hardening implementation plan

> Execute sequentially with the executing-plans skill. User approved the complete phased design, with lightweight mechanisms, on 2026-09-27. Work authority: GitHub Issue #36.

**Goal:** Repair demonstrated authority/evidence defects, reduce observation cost without stale authority, and make deployment and recovery independently inspectable.

**Architecture:** Preserve the frozen contract, native Git/GitHub authorities and existing strict/cooperative profiles. Add lossless Git path records and context-bound status publication; reuse only immutable reads within one observation. No new dependency, tracker, coordinator, persistent proof cache or automatic downgrade.

**Tech stack:** Python standard library, Git, GitHub REST through gh.

## 1. Paths and controls

- Add real Git regressions in tests/test_ci.py and tests/test_repository.py: Unicode, quotes, CR/LF, whitespace, rename/deletion and directory-to-file replacement. Use Git index objects for names unsupported by Windows filesystems.
- Run the regressions before repair and record the failures.
- Add Repository.git_paths using binary NUL records (no stripping or newline translation). Replace CI diff and upgrade tree path readers; preserve raw status records in upgrade preparation.
- Protect control directory roots as well as descendants. Test approval rejection before sandbox execution.

## 2. Publication

- Extend tests/test_ci.py and tests/test_backlog_ci.py with independent PR snapshots, base/Issue/task drift, malformed merge objects, wrong parents/tree and failed verification.
- Remove the separate pre-validation PR snapshot. Derive status subjects from the validated context. Require merge object SHA, parents and tree to match head/base/tree before success.
- Reobserve context after object reads. Reject drift without transferring success to a new subject. Document that the provider has no atomic PR-read/status-write transaction; immutable subjects and native strict integration gates remain necessary.
- Run CI and Backlog tests, then commit the bounded repair.

## 3. Observation cost and recovery

- Add tests for immutable read reuse, mutable rereads, failures not cached, observation isolation, target drift and expired proof.
- Use an observation-local immutable reader for exact commit-addressed contents/trees/blobs/commits. Report request counts, reuse and elapsed time. Never cache rules, branch refs, PRs, statuses, runs or logs across observations.
- Add structured proof failure stage and recovery guidance, preserving valid=false for missing/expired evidence. Recheck canonical target at audit completion.
- Document a renewal runbook and actual compatibility boundaries. Reuse cooperative operation checks; do not weaken strict policy or claim competing-writer fencing.

## 4. Verification and governed deployment

- Run python -m unittest discover -s tests -v and python -m compileall -q openharness. Record skipped cases separately. Baseline: 147 cases, 146 passed, 1 Windows symlink permission skip.
- Inspect the diff for new dependencies, persistent ownership claims, weakened gates and unused abstractions.
- Publish an Issue-bound PR through native gates with exact owner control approval. Executed producer upgrades require a separate reviewed immutable pin transition and fresh live valid/invalid/source-spoof/direct-update proof before activation.
- Record implementation, CI and live deployment separately. Native enforcement remains OPEN GAP until the changed producer is deployed and re-proven; no fixture or historical snapshot substitutes for this.

## Acceptance matrix

| Review finding | Completion evidence |
| --- | --- |
| Escaped paths bypass control classification | Real Git denial regressions and all machine path readers audited |
| Validated B publishes success to A | Snapshot/merge-object race regressions; only verified subjects receive success |
| Existing CI compatibility | Cooperative tests + documented strict envelope, no silent downgrade |
| Proof availability/cost | Immutable per-observation reuse, counters, fail-closed recovery runbook |
| Concurrency/fencing | Explicit unsupported topology; no local claim advertised as authority |
| Production maturity | Exact implementation/CI/deployment evidence and declared remaining live gaps |
