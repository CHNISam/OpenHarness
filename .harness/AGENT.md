# OpenHarness entry

Read `.harness/config.json`; run `openharness --repo . entry` and `doctor` to observe
current authority, work and closure. Exit 2 means OPEN GAP, never success.
Work authority is GitHub Issues; one Issue has multiple Changes. Use `workspace
--issue N --change NAME` for a bound isolated worktree. Work PRs must use that branch
and exactly one `Work-Item: #N` line. Native strict merge-only PR gates protect the
target. Trusted baseline controllers run candidate acceptance in a credential-free
Docker sandbox; a separate publisher binds current head/base/tree before authorizing
integration. Native Actions event policy blocks candidate-controlled workflow sources.
Use `integrate --pr N`, then `release`, or `handoff --reason TEXT` to preserve continuity.
Control changes require native owner approval bound to the exact head/base, then the
same enforced integration path. `reconcile` invalidates drift and stale projections.
`break-glass --reason TEXT` records exceptional local recovery and grants no provider
bypass. Doctor re-observes deployment proof, code pins, policy and applicability.
Physical local writes are outside the declared authoritative mutation envelope.
One trusted writer per workspace is a scope assumption; competing writers need an
effective authority/fencing adapter. No conversational history is required.
