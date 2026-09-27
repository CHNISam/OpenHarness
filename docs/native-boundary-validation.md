# Repaired producer deployment, 2026-09-27

Issue: https://github.com/CHNISam/OpenHarness/issues/36
Implementation: https://github.com/CHNISam/OpenHarness/pull/37
Reviewed candidate: `8accc20754f71891e523427c764f644c22f59d7b`.
Native integrated tree: `432d172668651f88d262dd51222a5cd19deca005`.
Repaired producer pin: `1cf6ad4662f1df171989ad9fa022f832628b8c7f`.

The final implementation passed 161 Windows cases (160 passed, one symlink
permission skip), compileall and the native Linux sandbox in run `36310484039`.
The native PR was merged with the installed trusted tool's `integrate`, with no
bypass and an independently observed matching integrated tree.

The pin transition is separately reviewed. Existing proof references concern the
old producer and must not activate the changed substrate. During proof renewal,
operator-authorized exceptional staging and native protected PR integration grant
no managed closure, provider bypass or exclusive ownership.

Fresh native acceptance must record: legal integration under the repaired producer,
failing candidate rejection, Unicode candidate workflow rejection plus blocked
source execution, direct canonical update denial, and a new complete live Doctor.
The canonical proof file and current Doctor remain authority; this saved record is
historical evidence. Selected-actions and arbitrary consumer production deployments
are not claimed by this repository's `allowed_actions: all` proof.

## Legal native acceptance probe

This documentation-only candidate exercises the complete acceptance suite and
independent publisher under the repaired canonical pin. PR #39 passed run
`36311097690`. A non-force refs update to its checked, PR-associated head was
accepted (rule suite `4246480721`); GitHub marked the PR merged. The resulting
head is `dd2dd6f6e38a35d1fceb0500d9c98f4e67e6430d`, with the exact verified tree
`93930ae61a92a9b76c699f85932089c64c9c52db`.

This is an allowed native integration route, not evidence that every refs update
is denied. GitHub's pull-request rule requires changes to be associated with a PR;
it does not require exclusive use of the merge API. See the
[native rule semantics](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).
The security boundary is authorized work and exact trusted evidence, not transport.

## Native rejection probes

No policy, bypass actor or enforcement strength was changed for these probes.
Ruleset `24036561` remains active with no bypass actors and strict, App-sourced
required status. Actions event policy `5742` still permits only the trusted event.

| Case | Real observation | Canonical reference |
| --- | --- | --- |
| Unbound update | No PR and no statuses; non-force refs update rejected HTTP 422 for missing PR and required check; main unchanged | head `5c24f9b29e6ef02b03c9b00e804dd59ea0d0bd0e`, failed suite `4246500490` |
| Failing candidate | PR #40 intentionally fails its disposable test in trusted run `36311530371`; merge HTTP 405 and refs HTTP 422 rejected; main unchanged | head `11c32f213b4c3ca525e436e67bf041630d987bdd`, failed HEAD-bound suite `4246520814` |
| Unicode workflow | PR #41 adds `.github/workflows/测试.yml` without exact control approval; trusted run `36311531748` rejects protected change; merge and refs rejected; main unchanged | head `4582eab94c305e04af1a1d12711900e7ef04a2bc`, failed HEAD-bound suite `4246522335` |
| Untrusted source | The harmless echo workflow is blocked before executing any job; no status-spoofing payload was run | run `36311479797`, `startup_failure`, zero jobs |

The proof references immutable heads, native rule suites and trusted publisher
logs. It is scoped to this deployment and remains subject to live re-observation.
Log expiry requires proof renewal; it is not hidden by a local receipt. Competing
writers and arbitrary existing workflows are not established by these cases.
After this manifest is integrated, an independently installed tool must re-audit
and explicitly activate before managed closure is claimed.
