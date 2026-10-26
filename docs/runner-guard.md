# Optional self-hosted command guard

This additive toolkit does not install, activate, remove or reconfigure Core or any
consumer. It does not claim task ownership. Continue the project's task/session,
claim, worktree, acceptance, CI security and integration protocols unchanged.

On Windows, the wrapper holds an OS file lock throughout the command and child
cleanup. It checks free disk space **after acquiring the lock, before starting the
command**. It creates the child suspended, assigns it to a native Job Object with
kill-on-close, then resumes it. Assignment failure prevents execution. Normal exit,
failure and timeout terminate any remaining descendants before releasing the lock.
Abrupt wrapper death closes the Job handle and Windows terminates contained children.
This is cooperative resource protection for trusted commands, not a security sandbox.
Administrator bypass, deliberately detached services and nonparticipating commands
are outside its envelope. POSIX supports ordinary process-group cleanup but does not
provide the Windows abrupt-wrapper-death guarantee.

## Explicit adoption and rollback

After review, use `CHNISam/OpenHarness/actions/runner-guard@<FULL_REVIEWED_COMMIT_SHA>`.
The placeholder must be replaced; never use main, latest or a moving version tag.
Do not use this unreleased candidate as a claim of deployed protection.

```yaml
- uses: CHNISam/OpenHarness/actions/runner-guard@<FULL_REVIEWED_COMMIT_SHA>
  with:
    command-json: '["python", "tools/project_validation.py"]'
    lock-path: 'C:\ci-guard\physical-host.lock'
    disk-path: '${{ github.workspace }}'
    min-free-bytes: '4294967296'
    wait-seconds: '120'
    timeout-seconds: '2400'
```

The project supplies its **existing** exact command and budgets. The example command
is illustrative, never a replacement test suite. Put related high-cost commands in
one project-owned script to keep one continuous lock across them. Use the same
canonical local lock path across repositories, services, local agents and worktrees
on the physical host; repository concurrency groups alone cannot achieve this.
An operator creates the parent directory once, grants only participating trusted
accounts access and excludes untrusted writers. The guard never creates or changes
ACLs, services or global configuration. Do not use a network share or separate lock
file per project. Never delete/recreate a live lock file. Lock-file existence is not
a stale-lock condition: the OS releases the lock on process exit.

Windows commands must resolve to `.exe`. Use explicit `powershell.exe`/`python.exe`
for scripts, and a project-owned script for npm `.cmd`. No implicit shell parsing.
Arguments are passed as JSON through environment variables, not interpolated into
PowerShell source. No retry loop is added. The child exit status is preserved;
preflight/input errors exit 2 and lock/command timeout exits 124. The configured
job timeout must leave room for waiting and cleanup; existing required checks and
timeouts must not be silently relaxed.

Consumer installation and rollback are independent PRs: replace just the reviewed
guard pin/wrapper, retain the original exact commands/check identities/triggers and
permissions, run equivalent validation, then test on the actual runner. Reverting
that PR restores the original path. Producer changes cannot alter a pinned consumer.
No project files, caches, worktrees or uncommitted work are cleaned by this tool.
This component does not repair cache contents or manage Git object retention.

## Download and cache boundaries

Wrap fetch/install **before** they run if protecting them with this lock. Set project
download count, request retries, per-request timeout and expected size budgets in the
project command using native tool options. Check expected headroom before fetching;
keep exact SHA verification and a reachable advancing Git ref. Reuse installed tools
and local caches isolated by repository, lockfile hash and toolchain version. Never
clear Godot imports or unrelated work to recover a dependency-cache error.

Free disk is a point-in-time preflight, not a reservation. This guard does not measure
egress or enforce a network quota. New Git pack bytes are post-download filesystem
evidence, not total network traffic. No hard network circuit breaker is claimed.

## Optional native Runner Job Hooks (operator procedure only)

[GitHub's hooks](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/run-scripts)
run synchronously as the runner service account. The started hook runs before the
job, the completed hook after its steps. A nonzero started-hook exit fails the job;
hooks have no built-in timeout. A hook that exits cannot hold a lock over later steps.
Use hooks for bounded preflight, never as a substitute for the command wrapper.

Nothing here installs hooks. For a separately authorized operator installation:

1. Inventory existing `ACTIONS_RUNNER_HOOK_JOB_STARTED` and
   `ACTIONS_RUNNER_HOOK_JOB_COMPLETED` settings and scripts; preserve them. Compose
   with existing hooks explicitly or stop on conflict.
2. Review a local `.ps1` preflight outside the runner application directory. Give it
   an explicit time bound, disk/tool checks and no cleanup/download/proxy changes.
   Pin its source and restrict write ACLs to the trusted operator.
3. After receiving a runner maintenance window, back up `.env`, add the absolute
   started-hook path and restart only the authorized runner service.
4. Check `Set up runner` logs for a disposable trusted job, including deliberate
   low-disk rejection. Verify existing hooks still run and normal jobs still pass.
5. Uninstall in another approved window: restore only the changed `.env` entries,
   preserving intervening operator changes, restart, verify hook absence in logs.
   Keep scripts/history until no setting references them.

Native process containment source:
[Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
No runner service or system network setting is changed by executing the guard tests.

## Verification and known gaps

`python -m unittest tests.test_runner_guard -v` uses synthetic subprocesses and
temporary directories. It is not actual self-hosted Actions execution evidence.
Run the complete existing Core suite before integration. Consumer baselines,
equivalent guarded suites, real runner interruption/retry and independent rollback
must be measured per consumer before declaring adoption complete.

Issue #34 remains open: green CI, Infrastructure labels, task assignment and an
agent-authored approval are not exact human removal authorization. This addition
does not solve approval identity separation or alter existing control policy.
No auto-enrollment, updater propagation or published release is implied.
