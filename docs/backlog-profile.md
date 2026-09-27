# Canonical Backlog work with native GitHub enforcement

`github-backlog-v1` is a separate bounded profile. Backlog task files on the live
canonical GitHub target ref are its sole work authority. GitHub continues to own
PRs, refs, rules and accepted checks. There is no writable Issue mirror or lease
registry. OpenHarness's own repository continues to use `github-pr-v1`.

Native support requires this profile's new immutable producer and complete live
deployment proof. Installing configuration or passing fixtures cannot activate it.
Read current `entry`/`doctor`; the native validation record describes actual proof.

## Configure an adopter

Create a reviewed repository-relative JSON file such as `backlog-work.json`:

```json
{
  "format": "backlog-md-1.53-subset-v1",
  "directories": ["backlog/tasks", "backlog/completed", "backlog/archive/tasks"],
  "ready_statuses": ["To Do", "In Progress"],
  "done_status": "Done",
  "actors": {"@your-assignee": "your-github-login"}
}
```

Use the project's actual assignee identifiers, native executor logins, task directories
and statuses; these values are examples, not automatic authority. Each selected task
must have exactly one explicitly mapped executor. Multiple/unassigned/unknown actors
reject authorization. Task assignee metadata does not fence other local writers.

```sh
openharness --repo . bootstrap --profile github-backlog-v1 --work-config backlog-work.json
openharness --repo . setup-plan
```

Bootstrap copies this reviewed mapping into `.harness/config.json`; the input JSON
is not a second runtime work authority. Configure acceptance argv commands, sourced
check App identity, immutable producer revision and image, then install/revalidate
native policy and this profile's deployment cases. Repeat bootstrap preserves valid
installed mapping and rejects reconfiguration; managed changes use exact control
approval and the normal gate. It cannot migrate an active Issue profile implicitly.

## Exact supported task subset

The adapter inspected Backlog.md v1.53.0 at immutable upstream revision
`fd20f71493fb4eda44b021aa89f257956f17fb71`
([upstream parser](https://github.com/MrLesk/Backlog.md/blob/fd20f71493fb4eda44b021aa89f257956f17fb71/src/markdown/parser.ts)).
Upstream supports full YAML. This standard-library reader deliberately accepts only
flat bare/quoted scalar strings and inline/block string lists. It is not a general
YAML parser and does not claim compatibility with every existing Backlog corpus.

```markdown
---
id: task-1
title: Example change
status: To Do
assignee:
  - '@your-assignee'
dependencies: []
labels: []
created_date: '2026-09-27'
---

## Description
Project acceptance semantics remain in the project.
```

Required fields: `id`, `title`, `status`, `assignee`, `dependencies`. Known optional
fields are `reporter`, dates, `labels`, `milestone`, `references`, `documentation`,
`modified_files`, `parent_task_id`, `subtasks`, `priority`, `type`, `project`,
`ordinal`, `onStatusChange`. Optional metadata does not authorize execution; the
Markdown body is opaque. No Backlog mutation command or status hook is executed.

IDs use a letter/alphanumeric prefix, hyphen and numeric components, for example
`task-1`, `back-23`, `back-23.1`; matching is case-insensitive. Files must be direct
children named `ID - Title.md` in configured directories. A regular `README.md` is
documentation and is excluded. The corpus is bounded to 1..500 task files, each at
most 1 MB. Task bytes come from exact immutable Git blobs and bind corpus identity.

Duplicate IDs/keys, unknown fields, quoted keys, ambiguous YAML types, anchors,
aliases, tags, nested objects, multiline scalars, nested task paths, symlinks,
submodules, missing/cyclic dependencies and truncated API observation reject.
Unsupported syntax remains OPEN GAP; do not rewrite private tasks silently or
weaken parsing to obtain activation. Extend the supported format only with reviewed
semantics and corresponding proof. Full upstream YAML reuse would require a separate
reviewed capability delta rather than unbound package execution in the observer.

## Managed task execution

```sh
openharness --repo . workspace --task task-1 --change fix-parser
openharness --repo RETURNED_WORKSPACE preflight
```

Workspaces use `codex/backlog-task-1-fix-parser`. PRs contain exactly one line:

```text
Work-Item: task-1
```

Workspace/preflight use the authenticated GitHub login. Trusted verifier, publisher
and integration use the native PR author login against the canonical mapping. Every
transitive prerequisite must be complete. Candidate-local task files cannot authorize
the current Change. Strict head/base/result checks bind the canonical work revision
and corpus digest to accepted evidence; target movement forces refreshed acceptance.

Task corpus changes, including descriptions, require owner control approval on the
native PR comment surface: `OpenHarness-Control-Approval: HEAD_SHA BASE_SHA`.
This approves a Change, not a mirrored work state. Assignment, status, dependency
and completion changes cannot grant their own baseline authorization. Resulting graph
must remain complete/acyclic; a Done task cannot retain an incomplete prerequisite.
The selected task must remain in the declared resulting corpus, including when moved
into a configured completion directory.

After accepted native integration use `release`; it preserves worktrees and does not
perform a separate task-state write. Completion is a reviewed Git change. `handoff`
preserves continuity. Canonical corpus/assignment drift rejects old bindings;
`reconcile` records invalidation and preserves work, without acquiring an executor.
An invalidated binding cannot become valid merely because task bytes later revert;
create a fresh legal Change. Local candidate evidence cannot authorize merge.

## Deployment and concurrency boundary

Retain all 16 catalogue guarantees. Competing/unknown workspace writers leave
concurrency/fencing OPEN GAP. No task file, branch or local binding claims to exclude
remote writers. Privileged policy operators remain declared trusted substrate actors.

Deployment proof retains native valid/invalid/source-spoof/direct-update cases and
requires `work_cases` for wrong executor, blocked dependency, self-authority,
invalid completion and stale work. Each is reobserved from sourced native status,
trusted historical controller/config, exact verifier rejection log and failed
integration rule suite. Stale-work proof includes a prior successful native run,
canonical descendant revision with revoked assignment and rejected renewed integration.
Candidate output cannot substitute for the trusted verifier's rejection exception.
Missing/unavailable/expired evidence blocks coverage and activation.

See [the native validation record](backlog-native-validation.md) for the bounded
synthetic rollout, immutable subjects, rejected cases and Managed exit proof.
It is historical evidence; live `doctor` remains the activation authority.
