---
status: pending
priority: p1
issue_id: "002"
tags: [harness, provenance, integration]
dependencies: ["001"]
---

## Problem Statement
v0.1 local Genesis mechanisms run, but full Activation remains unavailable. App identity
alone does not prove candidate-independent trusted verification or authoritative bypass coverage.

## Findings
Actual GitHub repository has no integration rules or workflows. The installed CI template
is explicitly staged, and the source implementation CI is candidate-controlled. These cannot
establish remote provenance. `evaluate` therefore preserves provenance/coverage OPEN GAP.

## Proposed Solutions
1. Reuse organization-required immutable workflows where available; observe source pins,
   protected controls and current deployment proof. Fits native provider enforcement.
2. Integrate an existing trusted external GitHub App verifier with equivalent provenance
   and candidate binding. Requires a proven existing service, not a duplicate coordinator.

## Recommended Action
Source an applicable trusted verifier, implement its adapter and real deployment proof,
then review the concrete remote configuration before applying it. The frozen contract
does not need redesign. Do not replace missing proof with a configuration boolean.

## Acceptance Criteria
- [ ] Trusted verification implementation cannot be replaced by candidate input
- [ ] Provider acceptance binds actual merge-group candidate and verification configuration
- [ ] Live invalid, valid and authoritative bypass scenarios are evidenced
- [ ] Doctor observes relevant source/proof validity and invalidates drift
- [ ] Representative complete profile can activate and perform protected normal integration
- [ ] Remote release/handoff completes applicable authority semantics

## Work Log
2026-09-26: Gap recorded explicitly during first runnable release; never represented as closure.
