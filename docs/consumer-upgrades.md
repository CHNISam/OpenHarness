# Release and consumer upgrade propagation

Runtime execution uses `verification.controller.revision`, a full immutable commit
SHA. SemVer is a discovery label; `.harness/upgrade-request.json` is a proposal input.
Neither a version label nor the request is ever passed to runtime checkout.

## Publish a producer release

This delta starts the release protocol at 0.2.1. Generate the declarative manifest
from the release compiler before committing, reviewing, and integrating:

```sh
python -m openharness.updates manifest --compatible-from 0.2.0 > openharness-release.json
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
