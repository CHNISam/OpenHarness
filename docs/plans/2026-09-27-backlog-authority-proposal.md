# Repository-native work authority proposal

Status: **DRAFT — owner review required; not an approved design or supported profile.**
Work authority for this repository remains GitHub Issues. This proposal addresses
[Issue #24](https://github.com/CHNISam/OpenHarness/issues/24); it grants no activation
or implementation authority by itself and changes no frozen contract.

## Observed requirement and options

An adopter already uses Backlog.md task files on its canonical Git ref. Duplicating
writable work state in GitHub Issues would create competing semantic authorities.
The current fixed GitHub profile correctly rejects an unsupported authority.

1. **Recommended: separate `github-backlog-v1` profile.** Reuse native GitHub PR,
   ref, check and integration adapters; replace work observation and binding with
   one canonical repository-native adapter. Explicit profile separation preserves
   the installed GitHub profile and exposes new proof obligations.
2. General pluggable work providers in `github-pr-v1`. More flexible, but makes
   the established fixed profile depend on arbitrary combinations without proven
   coverage. Defer a general extension interface until a second concrete adapter
   demonstrates the need.
3. GitHub Issue mirror. Rejected: writable mirrored status/ownership/dependencies
   conflict with the requested sole authority. A read-only viewer is optional and
   cannot authorize transitions.

## Proposed authority and execution boundary

Work, assignee, dependency and completion state come exclusively from Backlog files
at the live canonical target SHA. Local files, a candidate's task changes and saved
exports are not current work authorization. GitHub continues to own PRs, canonical
refs, native gates and accepted checks. Bindings remain local operational projections.

Start with the existing trusted single-writer-per-workspace envelope. Task assignee
metadata is an authorization predicate, not an exclusive filesystem lock. Competing
or unknown writers keep concurrency/fencing OPEN GAP; no task file or branch claims
remote fencing. Privileged policy operators remain explicit trusted exclusions.

The owner must approve the mapping from canonical task assignee identifiers to native
GitHub executor identities, legal task statuses and completion rules. Unassigned,
ambiguous or unknown executor identities fail closed. Shared assignees must not imply
exclusive ownership. Supporting teams/service identities requires a proven resolver,
not username guessing.

## Minimal adapter delta

- Immutable-revision discovery and read: resolve the configured GitHub target, read
  regular files from its tree/blobs and check completeness. Reject symlinks, traversal,
  duplicate task IDs, ambiguous filenames and truncated/unavailable observations.
- Pin the supported Backlog version and task field schema. Inspect its public parser
  before choosing reuse versus a strict standard-library reader. A reader must reject
  unsupported syntax rather than silently lose assignee/status/dependency semantics.
  Runtime mutation commands are never the authority reader.
- Validate the selected task and transitive prerequisites from the same target SHA.
  Missing/cyclic dependencies, malformed state, revoked assignment and completed or
  cancelled selected work reject the transition. Task edits cannot authorize their
  own execution retroactively.
- Bind string task ID, Change, branch, canonical work revision and material task
  identities to a workspace; keep the existing Issue-bound API for `github-pr-v1`.
  A separate task CLI/branch namespace avoids confusing `task-24` with Issue #24.
- Make the trusted controller and independent publisher use the exact same pinned
  adapter and canonical work revision. Re-observe assignment/status/dependencies
  immediately before publication and integration. Include work identity in candidate
  evidence. Target advancement makes the strict candidate stale and requires rerun.
- Separate authority-changing Backlog edits (assignment, status, dependencies,
  adapter config) from ordinary execution results. Require exact head/base owner
  authority for those edits. Approve completion only after acceptance and validate
  the resulting task graph; a task must not mark its own prerequisites complete to
  bypass authorization. Owner intent and mutation scope must be specified first.
- Reconciliation invalidates changed work bindings and evidence while preserving
  user worktrees. It cannot acquire a new owner or activate automatically.

Do not cache a task corpus as a second tracker or add a lease service. Reuse native
strict merge-only enforcement to serialize canonical updates. Publication and merge
must prove that the canonical work revision matches the candidate's live base; a
stale-owner PR cannot retain acceptance after reassignment advances the target.

## Verification and deployment requirements

Retain all 16 catalogue guarantees; this profile cannot activate by omitting one.
Fixtures must cover immutable parsing, unknown formats, multiple assignees, missing
and cyclic dependencies, source spoofing, invalid completion, interruption and fresh
process recovery. Existing Issue behavior must remain unchanged.

Before claiming support, deploy a representative adopter repository and prove:

1. Legal assigned task with completed prerequisites creates an isolated Change,
   passes the trusted candidate path, integrates and releases.
2. Missing/cancelled/completed work, wrong executor and incomplete dependencies fail.
3. Reassignment/status/dependency edits on the target invalidate an old workspace,
   published check and integration attempt; refreshed legal work can succeed.
4. Candidate-controlled task edits cannot self-authorize; unauthorized control edits,
   candidate source spoof and direct target update are rejected natively.
5. Base/input/parser/image drift invalidate proof; unavailable observations remain
   OPEN GAP. Recovery preserves work and requires current owner/closure validation.
6. Competing-writer applicability remains explicit; no metadata-only ownership proof
   is accepted. Fresh agents discover canonical work without inherited context.

This needs a new immutable producer revision, profile-aware Doctor/proof evaluation
and real valid/invalid/spoof/direct-update records. Existing deployment proof is not
reusable evidence that this proposed adapter works.

## Owner decisions before implementation

Approve the separate-profile approach and its bounded single-writer scope. Specify
the Backlog version, supported task schema/statuses, assignee-to-executor authority
and who may change assignment/dependencies/completion. Then write an approved design
and staged implementation plan; only after fixture and native deployment proof may
the new profile be advertised as supported. Keep #24 open until that exit proof exists.

Reference: [Backlog.md upstream](https://github.com/MrLesk/Backlog.md) stores work as
repository Markdown. The actual pinned schema/parser must be inspected during design
finalization; current upstream documentation alone does not prove version 1.53.0
compatibility.
