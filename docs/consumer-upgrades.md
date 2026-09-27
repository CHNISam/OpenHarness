# Release and consumer upgrade propagation

Runtime execution uses `verification.controller.revision`, a full immutable commit
SHA. SemVer is a discovery label; `.harness/upgrade-request.json` is a proposal input.
Neither a version label nor the request is ever passed to runtime checkout.

## Publish a producer release

The release protocol began at 0.2.1. Version 0.3.0 adds schema 2 profile and explicit legacy ownership adoption. Older updaters reject this new protocol; the release declares no automatic compatible source versions. Generate the declarative manifest
from the release compiler before committing, reviewing, and integrating:

```sh
python -m openharness.updates manifest > openharness-release.json
python -m unittest discover -s tests -v
python -m compileall -q openharness
```

The committed manifest must equal this compiler output. Version in `pyproject.toml`,
`openharness/__init__.py`, manifest and `vMAJOR.MINOR.PATCH` release tag must agree.
Create the tag on the exact governed integrated commit. Enable GitHub immutable
releases in the producer's release settings before publishing the stable release.
A draft, prerelease, non-immutable release, mismatched tag/tool version, unresolved
tag or unavailable observation is rejected. `target_commitish` and GitHub's mutable
`latest` endpoint are not used. Do not republish or move an existing version.

The manifest contains data, never arbitrary migration commands. Only the existing
entry, review template and (when installed) canonical controller workflow are
compiler-owned. Consumer configuration remains project-owned.

## Enroll an existing consumer

An enrollment has to name a published immutable release whose resolved SHA already
matches the consumer's reviewed controller pin. Legacy/unreleased installations
are not assigned an invented version. Install the operator's CLI from that exact
reviewed source SHA; Python packaging build dependencies must follow the project's
normal reviewed dependency policy.

Use an open GitHub upgrade Issue and the existing managed workspace:

```sh
openharness --repo /consumer workspace --issue 123 --change enroll-release
# In the returned workspace, using the already reviewed immutable CLI:
openharness --repo . upgrade --release 0.2.1 --enroll
```

Enrollment stages `.harness/installation.json` (source, version, SHA, generated
artifact hashes) and the dependency request. It invalidates local activation.
Finish normal candidate verification, owner control approval, native merge,
deployment re-proof, Doctor and explicit activation. Genesis enrollment remains
staged and cannot activate itself. Custom generated files stop enrollment.

## Configure the established updater

Use **self-hosted Renovate**, with an existing open GitHub Issue for recurring
upgrade work. The hosted Renovate App cannot run arbitrary post-upgrade commands.
The runner is an existing trusted local executor inside the declared single-writer
envelope; run it sequentially. It is not a new authority service.

Generate the OpenHarness preset, then review and combine it with the consumer's
existing Renovate configuration (do not overwrite project settings):

```sh
python -m openharness.updates renovate --source CHNISam/OpenHarness --issue 123
```

Renovate uses `github-releases`, exact SemVer, an Issue-bound `codex/123-...` branch,
`Work-Item: #123`, no dependency dashboard and no automerge. It updates only the
request's version. Its post-upgrade task invokes `openharness-upgrade-prepare`,
installed by the operator from the consumer's **old reviewed immutable SHA**.
Never install/execute the proposed source with the bot's credentials. Configure the
runner's `allowedCommands` to exactly `^openharness-upgrade-prepare$` and
`binarySource: "global"`. Limit the runner to the reviewed consumer configuration
and OpenHarness manager; grant only the normal Issue-read/PR/branch permissions.
Use the supported runtime and pinned Renovate distribution from your normal
runner installation. Do not add a scheduled workflow to the consumer: the existing
native event policy deliberately forbids candidate-controlled scheduled execution.

The post-upgrade task reads the baseline installation/configuration from Git HEAD,
resolves the immutable release independently, validates compatibility and artifact
ownership, and stages a deterministic delta. It rejects unrelated edits, preserves
project acceptance commands/environment/authority, restores previous file bytes on
write failure, and can repeat the exact operation after interruption. It does not
edit lifecycle projections, merge, mutate the target ref or activate.

Native `pull_request_target` checks validate the release migration independently
from the trusted baseline, require exact owner head/base approval, and execute both
old and proposed consumer acceptance configurations in the existing credential-free
sandbox. Bot assertions never substitute for the accepted check. A request without
its complete installation delta cannot pass installation validation.

## Compatibility, verification and rollback

Patch upgrades within a minor and minor upgrades within a stable major require the
new release's explicit `compatible_from` entry for the installed source version.
Major changes and minor changes before 1.0 always stop and require a separately
reviewed migration. Unknown manifest/profile/schema, downgrades, custom artifacts,
mutable/untrusted revisions and same-version SHA replacement stop before writes.
Missing generated files are conflicts, not permission to recreate project files.

Inspect discovery without changing files:

```sh
python -m openharness.updates discover --repo /consumer
```

An incompatible highest release is not guessed around. Renovate may propose it,
but preparation and the native installation check reject an incomplete migration.
For manual staging, `upgrade --release VERSION` retains existing lifecycle preflight
and invalidates activation **before** writes. A failed apply can therefore leave
local state UNPROVEN even after bytes are restored; this is conservative.

After the bot PR's native checks pass, review and merge through the normal governed
path. A local executor continuing that proposal must acquire an ordinary managed
workspace/binding; a Renovate branch is not a claim on local lifecycle authority.
Doctor also rejects a CLI version that differs from the enrolled release.
Installation/pin/artifact changes alter Doctor's substrate and make old activation
and deployment proof stale. Use the **new reviewed pinned CLI**, produce fresh native
valid/invalid/source-spoof/direct-update deployment proof for the new substrate,
then run Doctor and explicit `activate`. No automatic reactivation is provided.

Rollback is a governed Git revert of the complete upgrade commit (installation,
request, config and generated artifacts together), tested through the same gates
and followed by fresh proof/activation. A downgrade request is not a rollback.
Project-owned acceptance/configuration is never restored from a producer default.

## Verification evidence and deployment prerequisites

Tests create real Git consumers and exercise discovery, proposal, migration,
acceptance, rollback and stale activation. GitHub responses are deterministic test
fixtures. Fixture PASS is not live deployment proof. This producer had no published
releases when Issue #30 began. Publishing the first immutable release, enrolling a
consumer, and configuring its trusted Renovate runner are explicit operator setup
steps; configuration output alone does not prove ongoing automatic delivery.

Sources: [regex custom manager](https://docs.renovatebot.com/modules/manager/regex/),
[GitHub releases datasource](https://docs.renovatebot.com/modules/datasource/github-releases/),
[post-upgrade tasks](https://docs.renovatebot.com/configuration-options/#postupgradetasks).

## Adopt a staged legacy Backlog installation (0.3.0)

This is explicit Genesis installer work, not automatic enrollment of a mutable or
unreleased pin. It supports the Nameless Reach shape: inactive `github-pr-v1`
configuration, Backlog authority declared in project instructions on `develop`,
an immutable legacy producer pin, project acceptance argv, a canonical review-only
workflow template, and a custom `.harness/AGENT.md` Genesis boundary. The migration
never assumes GitHub Issues were the project's active work authority.

Use the existing owner-governed project review path for the adoption declaration
and migration PR. **Do not create an Issue mirror or bypass native gates.** If the
project remains Genesis because its GitHub plan lacks enforcement, stage/review only;
activation and native managed integration remain blocked until enforcement exists.
No consumer is enrolled or configured by this OpenHarness implementation task.

1. Independently resolve the published immutable 0.3.0 release, inspect its exact
   source SHA and install the reviewed CLI from that SHA. The legacy updater does
   not execute proposed producer code. This is an operator-installed new protocol.
2. In the project's ordinary review workspace, supply a reviewed work mapping JSON
   using actual directories/statuses and explicit session-assignee to GitHub-login
   mappings. For example `codex:session-20` is a literal assignee mapped to one login,
   never an inferred lease. Unknown/multiple assignees reject authorization. Changes
   to this mapping remain protected configuration changes. Do not normalize task files.
3. Produce an ownership review input, inspect it and commit it through the existing
   project review path before staging the migration:

   ```sh
   python -m openharness.updates adoption-plan --repo . --work-config backlog-work.json > .harness/adoption.json
   ```

   `legacy-backlog-adoption-v1` binds the complete semantic legacy configuration,
   selected work mapping, exact normalized hashes of project-owned `AGENTS.md` and
   `.harness/AGENT.md`, and compiler-owned template/controller files. These hashes
   are a review subject, not ownership inferred from a filename. The generator
   rejects any custom compiler workflow; migrating such a workflow requires a
   separate explicit reviewed mechanism. Unknown ownership or existing installation,
   request, companion entry, malformed/conflicting corpus or discovery instructions
   stop without writes. The custom project instruction files are preserved byte-for-byte.
4. From a clean Change based on that reviewed commit, stage the exact release:

   ```sh
   openharness --repo . upgrade --release 0.3.0 --adopt-backlog
   ```

   The proposal selects `github-backlog-v1` and `repository-backlog`, copies only the
   explicitly reviewed work mapping and updates the existing trusted producer pin to
   the resolved full SHA. All other authority, envelope, target, acceptance argv,
   environment, material inputs, App/check and sandbox settings remain project-owned.
   It creates compiler-owned `.harness/runtime-entry.md` with current Backlog
   instructions; the existing Genesis boundary and project instructions are untouched.
   `entry`/Doctor use pinned installation ownership to recognize this companion.
   Consult it alongside preserved project instructions; a preserved statement of
   Genesis remains truthful until the operator separately re-proves and activates.
5. Review the entire delta. The new pinned verifier independently recomputes it from
   the immutable baseline, reviewed declaration and published release; candidate
   edits to config, ownership, project instructions or generated bytes reject.
   A legacy verifier cannot validate the new protocol: deploy the reviewed new
   controller through the project's normal operator process and obtain fresh native
   proof before claiming managed closure. No missing gate is simulated or waived.

Staging accepts an exact interrupted proposal, repeats deterministically before
commit, and is a verified no-op after the same adoption is committed. Every write
is transactional with exact prior-byte restoration on failure. Staging clears any
substrate projection and remains Genesis; it cannot activate. Subsequent compatible
0.3.x releases use the normal upgrade planner, keep Backlog and project ownership,
and preserve the declaration. Project ownership hashes record the initial reviewed adoption snapshot, not a perpetual lock: subsequent project instruction edits use normal protected control review, alter Doctor controls and invalidate stale activation. An upgrade preserves the project bytes from its own baseline. Minor/major transitions still require explicit migration.
Rollback is the existing governed complete Git revert, followed by fresh proof; it
is never a mutable pin or downgrade request. Reverting initial adoption restores the
staged legacy installation and its explicit Genesis boundary, without claiming closure.

For later Backlog upgrade proposals, generate the existing self-hosted Renovate
preset with `--task TASK-ID` instead of `--issue`. It emits the native task branch
namespace and `Work-Item: task-id`, with no automerge or second tracker. Configure
only after the consumer's own native enforcement prerequisites are satisfied.
