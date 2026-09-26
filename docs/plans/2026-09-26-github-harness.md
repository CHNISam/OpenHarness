# GitHub Harness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a runnable conservative GitHub harness without claiming unsupported closure.

**Architecture:** A standard-library Python CLI installs target-local mechanisms and observes GitHub via `gh`. A fixed guarantee catalogue and fail-closed lifecycle prevent omitted, stale or unsupported guarantees from authorizing execution.

**Tech Stack:** Python 3.11+, Git, GitHub CLI, unittest, GitHub Actions.

Execution stays sequential in this task, as authorized by the user and required by repository instructions.

### Task 1: Fixed evaluation and candidate identity
Create `openharness/model.py`, `tests/test_model.py`, `pyproject.toml`.
Write tests for complete evaluation, ambiguous authority, freshness, unsupported exclusive ownership and unknown provider observations. Run `python -m unittest discover -s tests -v` (initially fails importing model). Implement immutable catalogue and hashes, then rerun to PASS.

### Task 2: Native adapters and installer
Create `openharness/provider.py`, `openharness/repository.py`, `tests/test_repository.py`, `tests/test_provider.py`.
Test provider errors, ruleset provenance, target drift, installation collisions and actual worktree isolation using temporary repositories. Implement read-only `gh api` transport, Git adapter and staged non-destructive install. Rerun full suite.

### Task 3: Runtime and lifecycle
Create `openharness/runtime.py`, `openharness/cli.py`, `openharness/__main__.py`, `tests/test_runtime.py`.
Test activation refusing gaps, preflight refusing stale candidate/workspace, reconciliation, explicit break-glass and recovery without memory. Implement bootstrap/doctor/preflight/activate/workspace/candidate/verify/reconcile/upgrade/break-glass/setup-plan/entry commands. Rerun suite and CLI help.

### Task 4: End-to-end proof and documentation
Create `README.md`, `AGENTS.md`, `.github/workflows/tests.yml`, `tests/test_cli.py`, provider fixtures and usage examples.
Run CLI in fresh temporary repositories; verify emitted CI/setup proposals, candidate invalidation and nonzero blocking exits. Run `python -m unittest discover -s tests -v`, `python -m compileall openharness`, CLI smoke checks and real read-only GitHub Doctor. Record actual remote gaps independently of local tests.
