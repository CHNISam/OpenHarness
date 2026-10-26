# Exact control scope and independent approval

Issue #34 demonstrated that task ownership and green tests do not authorize removing
an installed Harness. Declining an updater never implies removal, archival, disabling
an entry, unbinding a controller/dependency, or weakening its detector/approval policy.

This candidate extends the existing native control approval mechanism. It does not
install another tracker, mirror Issues, migrate work authority, activate a consumer,
change native policy, or publish a release. Existing pinned consumers are unchanged.

## Review the exact operation first

```sh
python -m openharness --repo /path/to/project control-impact \
  --pr 123 --base FULL_BASE_SHA --head FULL_HEAD_SHA
```

This read-only command uses configuration from the exact trusted **base**, reads Git
objects with replacements disabled, reports affected active control paths and their
add/modify/remove operations, and emits an exact review marker. Review the bound diff
for the before/after behavior, including semantic changes inside configuration files;
file existence alone does not establish preservation. Renames are read without rename
coalescing, so an archive move still reports removal of the original active path.

Existing `.harness`, `AGENTS.md`, native workflow and self-controller/verification
roots retain protection. Manifest edits mentioning OpenHarness are also protected,
including removing its dependency or console entry without deleting the file.
Missing/truncated binary manifest observations fail conservatively. Unknown ownership
or unavailable observations grant no approval.

The reviewer must be the native repository owner, a real User, and different from the
PR author. Submit an **APPROVED native PR review** whose whole body is the emitted
marker. It binds repository, PR, head, base and the digest of the exact control impact.
Historical Issue comments containing only head/base, generic assent, Infrastructure
labels, task assignment and agent-written "owner authorized" notes are rejected.

No OpenHarness command creates that approval. A same-account self-authored PR cannot
use self-review. At integration the authenticated executor is freshly observed and
must differ from the approval owner. If the executor can authenticate as that owner,
the tool reports an authorization **OPEN GAP**, rather than interpreting a matching
username as independent human consent. A real separately controlled reviewer identity
is a deployment prerequisite; fixtures cannot establish it.

## Re-observation and enforcement boundary

The trusted controller checks the exact impact before candidate execution. The
separate publisher recomputes native changed paths and observes review state again
before publishing success. Local cooperative and strict integration check it again
before their native/project merge operation. Edited, deleted, minimized, dismissed,
stale or ambiguous approval cannot authorize continuation. GraphQL supplies the native
edit metadata unavailable from the basic REST review list; partial data and pagination
stop explicitly. At most 100 reviews and fewer than 300 changed files are supported;
larger changes require splitting or a separately reviewed observation extension.

Ordinary product edits outside the control surface perform no review or identity API
lookup. Project acceptance commands, task/session/claim authority, CI identity and
strict deployment proof remain in place. Controlled updates and mechanical restoration
still require applicable control review; this is not an auto-removal/auto-restoration
exception. Both original and proposed acceptance configurations continue to be tested.

Consumers adopt the new tool/controller by a separate reviewed immutable SHA update
and their existing deployment proof procedure. Merely merging this source does not
upgrade an installed controller or prove current native enforcement. Administrator
bypass and direct writes outside the declared supported mutation path remain an
explicit limitation, particularly on private/free cooperative installations. Native
observation and merge cannot form one atomic transaction; protected transitions
re-observe immediately and report uncertainty rather than promise absolute fencing.

Source: [GitHub native PR review fields](https://docs.github.com/en/graphql/reference/pulls#pullrequestreview).

## Regression evidence

`tests/test_control_scope.py` uses real disposable Git repositories and synthetic
native responses. It covers archived control removal, configuration unbinding,
dependency/entry deletion, instruction changes, policy edits, legacy/forged/stale/edited/
dismissed/deleted approvals, missing observations, same-account credentials, a valid
independently approved operation, unaffected product edits, cooperative rejection and
publisher re-observation. These tests are separate from live native deployment proof.
