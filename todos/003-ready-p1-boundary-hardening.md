---
status: ready
priority: p1
issue_id: "003"
tags: [security, git, provenance, recovery]
dependencies: []
---

# Repair authority boundaries and proof operations

## Problem Statement

Issue #36 owns the user-authorized review remediation. Git text path quoting bypasses protected-change classification; publication can validate one snapshot and write success to another.

## Findings

Both reproduced at 05f83dd. Baseline suite: 147 cases, one OS permission skip. Similar tree parsing exists in upgrades. Strict native proof depends on retrievable historical logs. Cooperative compatibility already exists and does not establish strict closure.

## Proposed Solutions

1. Recommended: small standard-library repairs, adversarial tests, observation-local immutable reuse and explicit proof renewal. Retains native authority and predictable cost.
2. Rebuild around new coordination/storage services. Rejected: unnecessary complexity, unsupported fencing promises and larger trust envelope.

## Recommended Action

Execute docs/plans/2026-09-27-boundary-hardening.md sequentially. Preserve frozen contract and strict gates. No new runtime dependencies.

## Acceptance Criteria

- [x] Lossless machine path parsing and real Git approval regressions.
- [x] Context-bound publication and merge subject/race regressions.
- [x] Observation reuse, mutable freshness and structured renewal diagnostics.
- [x] Compatibility and deployment acceptance/runbook documentation.
- [x] Full unittest and compileall validation.
- [ ] Native PR checks; changed producer deployment and fresh proof recorded separately.

## Work Log

2026-09-27: User approved full remediation and requested lightweight implementation. Opened Issue #36. Independent live Doctor observed existing old-producer closure; created normal managed workspace after a transient observation rejection.

2026-09-27: 161 tests, 160 passed, one Windows permission skip; compileall and diff checks passed. Added 14 regression tests with no runtime dependency. Native acceptance and producer deployment remain separate next steps. An old-run cancellation could reject a new head; added a failing regression and repaired that adjacent false-negative.

## Resources

https://github.com/CHNISam/OpenHarness/issues/36
