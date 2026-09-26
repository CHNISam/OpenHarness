# Native deployment validation, 2026-09-26

Run `openharness entry` and `doctor` for current lifecycle and all 16 guarantees.
This document is a dated observation, never activation authority.

Immutable producer source: `d85c0df27f1c93d69aa40bc6c4401ae3258c90a5`. Native Actions event policy: 5742.
Main ruleset: 24036561, strict merge-only checks from GitHub Actions App 15368,
non-fast-forward/deletion protection and no bypass actors. Repository Actions is
enabled; this conservative adapter supports the observed `allowed_actions: all`.
Selection policies require an applicable adapter and remain OPEN GAP.

Windows local suite: 72 tests passed without skips. The trusted Linux Docker suite
passed for the legal candidate. Every controlled Harness code/test/contract change
requires exact native owner approval; config changes test old and proposed acceptance.

Native cases in `.harness/deployment-proof.json`:

| Case | Native subject | Result |
| --- | --- | --- |
| valid | [PR 11](https://github.com/CHNISam/OpenHarness/pull/11) | Trusted success, native integration, result tree equals tested head tree |
| invalid | [PR 12](https://github.com/CHNISam/OpenHarness/pull/12) | Authorized deliberately failing acceptance; merge HTTP 405; rule suite 4239309295 failed |
| source-spoof | [PR 13](https://github.com/CHNISam/OpenHarness/pull/13) | Control approval absent; merge HTTP 405; rule suite 4239309677 failed |
| direct-update | Legal verified head | Main push rejected: merge commit required; rule suite 4239309876 failed |

The source-spoof [native run](https://github.com/CHNISam/OpenHarness/actions/runs/36234408922)
was rejected at startup before any job ran. It could not mint the accepted App status.

Doctor re-fetches exact PR heads, sourced statuses, native runs, publisher job logs,
historical baseline/config, blocked job counts, result trees and failed rule suites.
Merged PRs disappear from run association lists: actual publisher checkout SHA comes
from the native job log instead. Missing/expired logs block proof. The immutable
producer's complete executed dependencies are checked; observer-only code is not
mistaken for evidence-producing code. Local verifier code/runtime still binds activation.

Policy/config/source pins, workflow state and repository Actions availability affect
the live fingerprint. Scope is one trusted local writer per workspace, trusted policy
operators and CI maintainers; physical local writes and privileged policy reconfiguration
are explicit exclusions. Competing/unknown writers require effective ownership/fencing.
No claim file, saved report or configuration boolean substitutes for native proof.

Earlier v0.1 reports and initial probe snapshots are historical. This record and the
canonical reference file supersede their deployment conclusions. Activation is a
separate complete live transition. Managed control staging can invalidate readiness;
finish through the same protected native PR protocol, refresh proof and reactivate.
