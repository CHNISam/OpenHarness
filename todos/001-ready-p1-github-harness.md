---
status: ready
priority: p1
issue_id: "001"
tags: [harness, implementation]
dependencies: []
---

## Problem Statement
Empty repository must implement the approved frozen-contract GitHub profile.

## Findings
GitHub remote has no rulesets, protection or workflows. Python/Git/gh are available.

## Proposed Solutions
Reuse GitHub provider gates (chosen); a local coordinator would introduce unnecessary authority infrastructure.

## Recommended Action
Execute docs/plans/2026-09-26-github-harness.md sequentially.

## Acceptance Criteria
- [ ] Runnable installable CLI and non-destructive bootstrap
- [ ] Complete conservative guarantee evaluation and live Doctor
- [ ] Candidate-bound verification and fail-closed lifecycle
- [ ] Recovery, break-glass and fresh-agent continuity tests
- [ ] Documentation and actual provider gaps reported

## Work Log
2026-09-26: Contract, design and GitHub envelope approved. Initial live observation confirms Genesis.
