# Legacy Backlog adoption implementation plan

Goal: support Nameless Reach's staged legacy installation without changing that repository.

Architecture: reuse the Backlog profile and immutable release protocol. A reviewed declarative adoption input binds the complete old configuration, project-owned instruction hashes and explicitly adopted compiler artifacts. Preserve custom instructions byte-for-byte and install a separate compiler runtime entry. Recompute the exact delta independently from the Git baseline; invalidate activation before transactional writes. Unknown ownership, drift, unsupported profiles, mappings and extra edits stop. No native enforcement exemption or automatic activation.

1. Reconcile/review PR #28, full suite, native approval/checks and integrate.
2. Version 0.3.0; extend release/installation metadata with supported profiles and bounded legacy adoption. Preserve v0.2.1 schema support.
3. Add pure adoption planner, explicit CLI staging and independent candidate validation; preserve all project configuration except reviewed work mapping/profile and immutable pin.
4. Cover Nameless Reach-shaped GENESIS boundary, develop target, session actors, acceptance argv, custom instructions, idempotence, full rollback, ambiguous ownership and altered candidate/config rejection.
5. Full verification, Issue #30 governed PR/native acceptance/integration, then publish exact integrated 0.3.0 commit with immutable release settings and live resolver evidence.

Ownership: custom .harness/AGENT.md and AGENTS.md remain project-owned. The review input explicitly adopts only fingerprinted template/controller artifacts. A compiler-owned runtime-entry.md supplies current profile instructions without normalizing project files. A hash is a reviewed ownership decision, not proof of live enforcement.

Deployment: existing private-plan protection gaps stay OPEN GAP. Installing a new producer and re-proof/activation are separate operator tasks; this implementation modifies only OpenHarness.
