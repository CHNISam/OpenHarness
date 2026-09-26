---
status: complete
priority: p1
issue_id: "002"
tags: [harness, provenance, integration]
dependencies: ["001"]
---

## Problem Statement
The initial runnable Genesis implementation lacked trusted producer provenance and
native deployment proof, so it could not activate the frozen-contract profile.

## Resolution
Public personal GitHub repositories have no merge queue. Native strict up-to-date
checks plus enforced merge-only PRs provide the applicable path. An immutable baseline
producer runs acceptance in a credential-free Docker sandbox and publishes from a
separate runner. Native all-workflow event policy prevents candidate source spoofing.
Control/Harness/test/contract changes require exact native owner authority.

## Acceptance Criteria
- [x] Candidate cannot replace the trusted evidence producer
- [x] Native acceptance binds strict head/base/result/config/environment
- [x] Legal, invalid, source-spoof and direct-update paths have real provider records
- [x] Doctor reads native source, availability, job logs and proof, and detects drift
- [x] Complete current profile activates from an independent installed tool environment
- [x] Managed workspace, continuity, native integration and release preserve authority

## Work Log
2026-09-26: Original v0.1 gap recorded honestly; no activation was claimed.
2026-09-26: Native deployment completed. 72 Windows tests pass without skips; trusted
Linux Docker validation passes. The final native proof is canonical and live-observed.
Independent wheel installation in a neutral directory activated MANAGED at
10:06:40 UTC. Fresh entry reports 14 ESTABLISHED and 2 NOT APPLICABLE guarantees,
with zero OPEN GAP. This Issue-bound managed documentation Change completes the
normal integration/release path. Read current entry/Doctor rather than this snapshot.

## Evidence
See `docs/native-deployment-validation.md` and `.harness/deployment-proof.json`.
Canonical work: https://github.com/CHNISam/OpenHarness/issues/1.

## Scope
Trusted single writer per workspace; trusted provider policy operators/CI maintainers.
Competing or unknown writers require effective ownership/fencing. Selected Actions
allowlists require an applicable adapter. Unavailable/expired native logs or changed
substrate invalidate proof. These boundaries do not omit catalogue candidates.
