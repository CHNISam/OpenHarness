# Capability sourcing for v0.1

Source order follows frozen contract section 8. The initial repository contained only
LICENSE, so no existing project implementation could be revalidated. No prior internal
mechanism was supplied. Executor sandbox and approvals remain executor-owned.

| Capability | Source used | Applicable delta / limit |
| --- | --- | --- |
| Filesystem/process permission envelope | Existing Codex/executor sandbox | No new sandbox; CLI checks paths and declares trusted local execution |
| Change isolation and revision identity | Native Git worktree, merge-tree, object database | Bind Issue/Change/workspace, compute and verify actual merged tree |
| Work and Change authority | Native GitHub Issues and PRs | Read-only Issue discovery/legality; no local tracker mirror |
| Canonical integration | GitHub rulesets, required checks, merge queue | Observe actual effective rules and bypass policy; output setup proposal |
| Check subject/provenance | GitHub-native checks/workflow surfaces | App-source observation exists; independent trusted-verifier and deployment proof still missing |
| Exclusive ownership/fencing | Existing executor single-writer envelope where explicitly trusted | Multiple/unknown workspace writers produce OPEN GAP; no imitation lock service |
| Local lifecycle concurrency | Native Windows/POSIX process locks | Serialize local projections only; never claim remote fencing |
| Guarantee applicability and evaluation | Custom fixed profile catalogue | Needed contract-specific semantics; cannot be delegated to README or status presence |
| Candidate diagnostic evidence | Native Git plus standard-library subprocess | Bind all declared material identity and actual tested result; no remote-authority claim |
| Provider drift/recovery | Native Git/GitHub observation plus custom reconciliation | Keep only local bindings, lifecycle events and diagnostic evidence; provider remains authoritative |

No new agent, scheduler, review engine, distributed coordinator or provider-state
database is introduced. Saved Doctor reports are explicitly dated evidence artifacts,
not inputs to current closure evaluation.
