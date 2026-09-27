# Backlog Authority Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Preserve Backlog as the sole canonical work authority with a bounded native GitHub profile.

**Architecture:** Reuse native policy/controller/candidate enforcement. Add a strict immutable task reader and profile-specific work authorization shared by local commands, verifier and publisher. Retain all catalogue guarantees and explicit unsupported formats/concurrency gaps.

**Tech Stack:** Python standard library, native Git, gh API, upstream Backlog.md 1.53.0 flat task subset.

Execution is sequential in this task, per repository instructions and owner approval.

### Task 1: Finalize and integrate approved design

Files: this plan and `docs/plans/2026-09-27-backlog-authority-proposal.md`.
Record inspected upstream revision, bounded schema, actor mapping and rollout limits.
Commit, update PR #27, run trusted native checks and integrate/release the design.

### Task 2: Strict reader and explicit configuration

Create `openharness/backlog.py`, `tests/test_backlog.py`; update `model.py`.
First write tests for serializer-compatible scalar/block/flow lists, duplicate IDs,
fields, aliases, unsupported syntax, missing dependencies, cycles and wrong executor.
Run `python -m unittest tests.test_backlog -v` and observe failure before implementing.
Implement strict parsing and same-revision corpus authorization; test valid and invalid
cases. Add exact profile config validation without changing github-pr-v1. Commit.

### Task 3: Immutable provider and local lifecycle binding

Modify `provider.py`, `repository.py`, `runtime.py`, `cli.py`; extend provider/runtime
tests. Test immutable Git tree/blob identity and completeness, regular paths, native
actor identity, task workspace namespace, drift rejection and fresh process recovery.
Implement bounded API reads and shared graph checks; bind canonical revision/corpus.
Preflight/reconcile reject drift without acquiring new owner authority. Commit.

### Task 4: Trusted candidate and independent publication

Modify `ci.py`, `native.py`; extend `test_ci.py`, `test_native.py`, `test_proof.py`.
Test wrong author, self-authorizing candidate task edits, control approval on native PR,
baseline and result graph checks, stale target/work state and publisher mismatch.
Implement profile-aware context while preserving Issue API. Include backlog module in
immutable producer dependencies and bind new-profile work observation into accepted
identity. Test selected completion and unauthorized corpus edits. Commit.

### Task 5: Documentation and comprehensive candidate verification

Update README, profile instructions/installer wiring and skill discoverability.
Document exact unsupported syntax, explicit corpus configuration and single-writer
scope; do not advertise native support before proof. Run
`python -m unittest discover -s tests -v`, `python -m compileall -q openharness`,
`git diff --check`, then clean-candidate `verify`. Push Issue-bound implementation PR;
obtain exact owner control approval and require the existing trusted CI gate.

### Task 6: Native rollout and exit proof

Use immutable reviewed producer source in a dedicated adopter proof repository with
explicit Genesis installer authority. Install native strict merge-only, sourced check
and all-workflow event policy without bypass actors. Prove legal integration, invalid
work/actor/dependencies/completion, source spoof, direct update and canonical
reassignment/stale-owner rejection. Record rule-suite/run/tree references and current
profile policy fingerprint. Observe live Doctor, activate, exercise fresh managed
workspace/integrate/release and recovery. Fixture success is not deployment proof.
Integrate implementation through OpenHarness's existing native path and close #24 only
after the bounded adapter and its real native exit proof exist. Any blocked observation
or unsupported format remains explicit OPEN GAP.
