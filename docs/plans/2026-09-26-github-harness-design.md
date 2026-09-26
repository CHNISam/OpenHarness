# GitHub Harness v1 design

Approved on 2026-09-26. The frozen contract is normative; implementation gaps do not weaken it.

Python standard-library CLI delegates Git state/isolation to Git and remote integration to GitHub through `gh`. Target repositories retain their own `.harness/config.json` and authority mapping. GitHub Issues are work authority, PRs change containers, GitHub target refs revision authority, and provider checks integration evidence authority. Generated observations are projections, never a competing source of truth.

The initial profile supports trusted single-writer change workspaces and GitHub merge-queue integration. Arbitrary filesystem writes are outside the authority envelope. Repository administrators and trusted CI maintainers are trusted substrate operators; their configuration changes invalidate closure. Concurrent exclusive writers and revocation require an ownership adapter; absent one they remain OPEN GAP. No local claim file is represented as fencing.

The fixed candidate catalogue covers applicability, authority, enforcement coverage, concurrency, fencing, isolation, mutation, candidate freshness, check provenance, integration, guarantee freshness, N/A freshness, recovery, break-glass, closure and fresh-agent continuity. Missing observations never establish a guarantee. Local tests prove implementation behavior; only live authoritative observations can support provider closure. Bootstrap never auto-activates.

Installer stages configuration, instructions and CI template without overwriting existing project artifacts. Doctor reads live provider rules, bypass actors, branch protection and workflow configuration. Candidate evidence binds head, base, result tree, verification configuration and material inputs. Lifecycle records are durable local operational records, explicitly not provider authority; activation and recovery always re-observe substrate. Break-glass records cause and affected guarantees and blocks managed operations until revalidation.

Remote setup is emitted as a reviewable proposal, not silently applied. Provenance requires trusted verification configuration; candidate-editable workflows alone are insufficient. Unsupported or unobservable provider behavior blocks closure.

Verification uses temporary Git repositories, deterministic provider fixtures and CLI subprocesses. Includes valid/invalid paths, omitted guarantees, ambiguous authority, unsafe installs, stale candidates, configuration drift, recovery, break-glass and fresh-session discovery. Actual GitHub Doctor runs separately from fixture tests.
