# Native proof recovery

Doctor is a live audit. Saved reports, successful local tests and a retry do not
activate a repository. `deployment_proof.valid=false` remains an OPEN GAP.

## Diagnose the exact rejected observation

Use the rejection's embedded diagnostics first. `deployment_proof.phase` identifies
the failing substrate, manifest, native case, work case or final target observation;
`reason` retains the provider error. A later Doctor is a distinct observation.

Run `openharness --repo . doctor` from the trusted installed tool with native read
permissions. `provider.observation_cost` reports API requests, immutable-object reuse,
publisher log requests and elapsed seconds. Counts include attempted reads; no failed
read is cached. The immutable reuse lasts only for this invocation. Branches, PRs,
rules, statuses, runs and logs are always freshly observed. The target is re-read at
completion; target drift rejects the audit and requires a complete retry.

For transient network/rate-limit/permission failures, resolve the specific cause
and retry the complete audit. A previous successful audit is not a fallback. Avoid
repeated full audits for daily orientation: default `entry` stays local. Cooperative
operations check their own prerequisites and never claim server enforcement.

## Renew missing, expired or changed proof

Publisher log expiration cannot be repaired by copying logs locally, changing a
timestamp or editing an applicability flag. Historical checks are not proof of a new
producer. Use the trusted repository operator and the normal Issue-bound PR path:

1. Confirm the canonical workflow, current rules, no bypass actors, immutable
   controller/image pins and native all-workflow event policy. Repair drift through
   the reviewed control-change path; never downgrade strict configuration to recover.
2. Collect fresh native cases for this exact substrate: a legal verified integration;
   rejected failing candidate; candidate-source workflow rejected before job execution;
   and rejected direct target update. Use disposable Changes and a declared test repo
   where applicable. Observe refusal before claiming it; an attempted mutation alone
   proves nothing. Include all five native work cases for the Backlog profile.
3. Record exact PR/head/run/rule-suite references and the current policy fingerprint
   in `.harness/deployment-proof.json`. Keep accepted and rejected subjects separate.
   Historical controller/config, source, job logs and integrated trees must remain
   observable through GitHub, not a copied report.
4. Submit the proof change for review under the existing control approval and native
   integration gates. If protected managed operations are unavailable, report the
   failed observation; explicitly authorized exceptional local staging grants no
   GitHub bypass, activation or server-enforced ownership.
5. Run the trusted new tool's complete Doctor. Only complete current closure permits
   explicit `activate`. Reconcile stale projections without reacquiring authority.

Retain publisher logs for the declared support period and renew cases before that
period expires. This implementation still depends on GitHub retaining those logs.
It supplies diagnostics and fewer repeated object reads; it does not make missing
native evidence valid. Durable signed receipts would require a separately reviewed
producer/proof protocol and are not approximated by local caches.

## Compatibility and execution limits

| Setting | Cooperative | Strict native profile |
| --- | --- | --- |
| Existing multiple CI/release/scheduled workflows | Preserve project CI and selected exact-head check | Unsupported under the current all-workflow event envelope |
| Rulesets unavailable (for example project plan restrictions) | Independent operations remain usable; no closure claim | OPEN GAP |
| Actions `allowed_actions=all` | Existing project policy | Supported with other complete native conditions |
| Actions `selected` with GitHub-owned actions enabled | Existing project policy | Supported after reading complete selected-actions settings |
| Actions `selected` with both exact compiler Action SHA entries | Existing project policy | Supported; wildcard/Marketplace-only inference remains unsupported |
| Competing or unknown writers in one workspace | Refuse unsupported topology | Ownership/fencing OPEN GAP |
| Expired native publisher logs | No native closure claim | OPEN GAP; fresh deployment cases required |

Selected-actions observation adds one API read only when needed. It checks the
two public GitHub-owned Actions used by the fixed compiler. Action selection never
replaces event restrictions, source pins or deployment proof. Supported configuration
is not evidence that an arbitrary consumer has deployed it. See the official
[GitHub Actions permissions API](https://docs.github.com/en/rest/actions/permissions).

Separate worktrees support independent single writers; they do not fence competing
writers. Do not advertise a distributed execution guarantee or mark applicable
ownership/fencing N/A to make an unsupported topology pass.
