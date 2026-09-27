# Backlog native validation, 2026-09-27

This record concerns the bounded `github-backlog-v1` profile and synthetic data in
[the disposable validation repository](https://github.com/CHNISam/OpenHarness-backlog-native-proof).
It is historical evidence, not activation authority. Run live `doctor` before use.
The OpenHarness production repository retains its Issue authority and native gates.

## Scope and immutable subjects

The installed controller is OpenHarness revision
`d49bdc98a793346017bb078cede19715764a2563`. Observer-only upgrades preserve the
immutable producer blobs; candidate acceptance still executes that pinned producer.
The verification command runs the synthetic product's unittest in the pinned Python
container. Native ruleset `24061631` has no bypass actors; Actions policy `5787`
restricts all workflows to `pull_request_target`.

Canonical work consists of explicitly configured `backlog/tasks` and
`backlog/completed`, flat Backlog.md 1.53-compatible metadata, explicit status mapping,
and `@owner`/`@other` mapped to native logins. No Issue mirrors were created.
This does not establish arbitrary YAML compatibility or fencing of competing writers.

## Reobserved native cases

| Case | Native PR | Trusted run | Rejected rule suite |
| --- | --- | --- | --- |
| Legal integration | [1](https://github.com/CHNISam/OpenHarness-backlog-native-proof/pull/1) | 36290981947 | native merged |
| Failing candidate test | [4](https://github.com/CHNISam/OpenHarness-backlog-native-proof/pull/4) | 36291096430 | 4244567228 |
| Candidate workflow source | [5](https://github.com/CHNISam/OpenHarness-backlog-native-proof/pull/5) | 36291104741 | 4244567462 |
| Wrong executor | [2](https://github.com/CHNISam/OpenHarness-backlog-native-proof/pull/2) | 36291255768 | 4244573784 |
| Incomplete prerequisite | [3](https://github.com/CHNISam/OpenHarness-backlog-native-proof/pull/3) | 36291258310 | 4244574013 |
| Self-authorizing task edit | [6](https://github.com/CHNISam/OpenHarness-backlog-native-proof/pull/6) | 36291112642 | 4244567656 |
| Done with incomplete prerequisite | [7](https://github.com/CHNISam/OpenHarness-backlog-native-proof/pull/7) | 36291163096 | 4244567955 |
| Revoked executor, unchanged HEAD | [8](https://github.com/CHNISam/OpenHarness-backlog-native-proof/pull/8) | 36291777441 | 4244620770 |

The candidate-source run `36291100631` was rejected before any job executed.
Direct authoritative update of the invalid candidate produced failed suite
`4244554235`. Native PR merge attempts for the invalid cases also failed.

PR 8's exact HEAD first passed run `36291130204`. Owner-approved
[PR 9](https://github.com/CHNISam/OpenHarness-backlog-native-proof/pull/9) changed its
canonical assignee; the same HEAD then failed with the trusted verifier exception
`Backlog executor is not currently assigned`. Its proposed native merge was rejected.
The rejection suite's merge has exactly the canonical baseline and candidate HEAD
as its two parents. The observer checks these identities; unrelated merge commits,
wrong bases/heads and extra parents cannot substitute for candidate rejection.

An additional direct push of the stale HEAD stopped at Git's non-fast-forward check.
That result is not used as native rule-suite proof. No force-push was performed.

[PR 10](https://github.com/CHNISam/OpenHarness-backlog-native-proof/pull/10) installs
the reobservable proof declaration through the native gate. All four generic and
five work-specific cases passed live API reobservation before this declaration was
integrated. Its policy fingerprint is
`19f0725ef36ead9187fc79e6e01cc1b2cdf75fa6e621f9dc5f1c94fc39706bf3`.

## Managed completion and recovery

Standard live `activate` succeeded at `2026-09-27T03:57:58.754047+00:00`, recording
Managed substrate `b64c020c5ead93aaff7f4a94ddf9cb52e618faf51d6b55438390ad22a1faa673`.
The first subsequent workspace attempt correctly failed closed when a GitHub blob
read became unavailable. Same-observation diagnostics retained the matching activation,
current policy and exact missing proof read; no Genesis fallback was used.

The fresh Managed binding for `task-1` was created at
`2026-09-27T04:10:04.900923+00:00` from canonical revision
`9f2d950f35648fc323665d469a3c438f6185378b`, branch
`codex/backlog-task-1-managed-completion`. Positive completion to Done is
[PR 11](https://github.com/CHNISam/OpenHarness-backlog-native-proof/pull/11), exact
HEAD `f44c1642eeec86368a0d88790562ef5049fa8995`. Handoff preserved its clean worktree
and binding at `2026-09-27T04:10:24.795492+00:00`.

Trusted completion run `36293541103` passed. A fresh process used standard Managed
`integrate --pr 11`, merging commit `6bd9be089e6b0d6d8abacfd77b32513204f7d182`.
The native integrated tree exactly matched candidate tree
`a499d1fdb53764750822109aa1495a3e5543bc5d`. Standard `release` removed the binding
and preserved its worktree. Completion was only the reviewed Git task change;
there was no separate Issue or mirrored task-state write.

Fresh-process standard `reconcile` completed at
`2026-09-27T04:17:28.165540+00:00`, with `closure: true`, `MANAGED`, the same
activation substrate and all nine native cases valid. All 16 catalogue entries
were evaluated: 14 ESTABLISHED and 2 NOT APPLICABLE within the declared trusted
single-writer envelope. This does not establish competing-writer fencing.

Live canonical work discovery returned only `task-4`, `task-5` and `task-6` for
the authenticated owner. Completed task-1 and reassigned task-7 were absent.
Reconcile invalidated the retained old Genesis task-1 binding, preserved its
worktree, reported no orphaned bindings and did not acquire stale authority.

The formal OpenHarness repository was checked read-only during these tests and
retained `closure: true`, `MANAGED`, substrate
`96e71246ff36be526477b3b6efd1ca6c19161fae6fb39ad133f4319259e5daf3`.
Its history and native policy were not changed by the synthetic negative tests.

Implementation regression validation: 101 tests passed without skips using Python
3.13 on Windows; `compileall` and `git diff --check` passed. These tests do not replace
the native deployment cases above.
