# Native deployment proof, 2026-09-26

These are native observations, not activation authority. Run `openharness entry`
and `doctor` for current lifecycle and all 16 guarantees.

- Canonical controller: immutable source `a2c316748cd89ac1f57f6e4faec35edbf4c2736b`.
- Native Actions event policy: 5742; branch ruleset: 24036561; no bypass actors.
- Windows local suite: 68 tests passed without skips. Trusted Linux Docker suite passed.
- Legal candidate [PR 8](https://github.com/CHNISam/OpenHarness/pull/8) passed trusted
  [run 36231981559](https://github.com/CHNISam/OpenHarness/actions/runs/36231981559)
  and merged. Native integrated tree equals the tested head tree.
- Invalid [PR 4](https://github.com/CHNISam/OpenHarness/pull/4) failed candidate acceptance;
  native merge returned HTTP 405, required status failing. Failed rule suite 4239052127.
- Source-spoof [PR 6](https://github.com/CHNISam/OpenHarness/pull/6) lacked exact control
  approval and failed. Candidate push and PR event workflows were rejected before any
  job executed; [blocked run](https://github.com/CHNISam/OpenHarness/actions/runs/36231969711).
  Native merge returned HTTP 405; failed rule suite 4239052547.
- The successful legal head also failed a direct main-ref push: native rules require
  a merge commit when squash/rebase are forbidden. Failed rule suite 4239052746.

`.harness/deployment-proof.json` stores only provider references and the policy
fingerprint. Doctor re-fetches PR subjects, sourced statuses, historical baseline,
native runs/job counts, integrated trees and failed rule suites. Changed policy,
config/tool pins, workflow state or incomplete observation invalidates proof.

Deployment found and fixed real API normalization, candidate-inclusive workflow
registry and Windows CRLF continuity issues. Canonical Git source determines baseline
authority; registry display names/timestamps and unmerged candidates do not.

The bounded envelope trusts a single local writer, repository policy operators and
CI maintainers. Physical local writes and privileged policy reconfiguration remain
explicit exclusions. Competing/unknown writers need effective ownership/fencing;
the profile does not substitute a claim file for enforcement.

Managed control upgrades retain native protection and exact owner approval. Staging
changed controls can invalidate local Managed readiness; finish through the same
native protected PR protocol and refresh proof before reactivation. No bypass is granted.
