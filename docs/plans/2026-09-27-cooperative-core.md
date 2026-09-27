# Minimal cooperative core implementation plan

User-approved design: make independent operations usable without native rules or activation. Keep daily Agent use small; no second tracker, lifecycle, registry or automatic authority migration.

1. Add an explicit cooperative execution mode. Missing mode remains strict for existing callers/installations; new CLI installs default cooperative. Keep strict checks and full Doctor intact.
2. Reuse canonical Backlog/Issue reads, Git worktrees, candidate verification and native PR merge. Check only an operation's prerequisites. Allow binding existing registered worktrees and delegating merge to an existing reviewed project command.
3. Default entry is a compact local orientation, with no API calls, task enumeration or claimed fresh closure. Explicit entry --full and Doctor retain complete observations.
4. Cooperative bootstrap preserves project-owned instructions and CI; no generated workflow or activation ceremony. Existing authority/configuration changes require review, never implicit migration.
5. Prove exact-head CI/source checks, stale work/head/base rejection, merge parent/tree observation, preserved project artifacts and strict regressions. Report bypass and base-race limits; never label optional unproven guarantees N/A.

Verification: python -m unittest discover -s tests -v; python -m compileall -q openharness. Publish an Issue #33 PR through the existing strict producer governance; exact control approval remains required before integration. No Nameless Reach writes or consumer activation.
