# OpenHarness entry

Canonical project configuration: `.harness/config.json`.
Run `openharness --repo . entry` for current authoritative state and legal work.
Run `openharness --repo . doctor`; exit 2 means incomplete closure, never PASS.
GitHub Issues own work state; PRs contain Changes; GitHub refs/rules/checks own
revision/integration/evidence. Local reports are observations, never provider authority.
Create isolated Changes with `workspace --issue N --change NAME` only after activation.
Use `reconcile` after interruption and `break-glass --reason TEXT` for explicit local
recovery. This command grants no remote bypass rights. Never label local verification
as authoritative integration evidence. v0.1 lacks deployment proof/provenance adapters
and therefore intentionally refuses full activation. See the installed config and
tool README for exact boundaries. The execution envelope trusts one local writer per
workspace; multiple/unknown writers require a real authority/fencing adapter.
