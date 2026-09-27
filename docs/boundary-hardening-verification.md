# Boundary hardening verification, 2026-09-27

Work authority: [Issue 36](https://github.com/CHNISam/OpenHarness/issues/36).
Approved design: [implementation plan](plans/2026-09-27-boundary-hardening.md).
Saved results are historical observations, never activation authority.

## Implementation evidence

At baseline `05f83dd`, real Git with `core.quotePath=true` produced a quoted escaped
path for `.github/workflows/测试.yml`; protection classified it false. Simulated
publication validated head `e*40` but wrote success to earlier head `a*40` and merge
`c*40`. Added regression tests failed before repair. Related directory replacement
and unverified merge-object cases also failed.

Repaired path readers use binary NUL records without stripping, escaping or newline
translation. Git object fixtures exercise names Windows cannot check out, including
quotes, CR/LF, whitespace and undecodable bytes. All path-list interpretation in CI
and upgrades uses the new reader. Remaining name-only reads in adoption/upgrades
only check whether any diff exists; they do not interpret or classify filenames.

Publication binds head, base, tree, work and merge from one validated context,
checks immutable merge identity/tree/ordered parents and reobserves after reads.
Base/work/merge drift rejects success. Ref movement between status writes does not
retarget the verified immutable subjects. There is no atomic provider transaction
covering all reads/writes; native strict up-to-date integration remains required.

One audit reuses only successful exact-commit Git object reads. Mutable observations
and final target freshness are re-read; separate audits never share a cache. API/log
attempt counts and elapsed time expose actual cost rather than assuming a fixed
request count or latency. Failures retain OPEN GAP with phase and renewal guidance.

Explicit selected-actions support observes GitHub-owned permission or the exact
two public compiler Action SHA entries. It does not infer wildcard/Marketplace-only
permission or relax event isolation. This adapter's fixture tests are not proof of
selected-actions deployment in an arbitrary consumer.

## Local validation

`python -m unittest discover -s tests -v`: 160 tests in 121.286 seconds, 159 passed,
one skipped because Windows does not permit creating symlinks. No failures.
`python -m compileall -q openharness` and `git diff --check`: passed.

No runtime dependency, persistence service, ownership claim or catalogue change
was added. Existing cooperative/strict compatibility and unsupported topology
behavior remain covered by the full suite.

## Native deployment acceptance

Independent installed old-tool Doctor observed current existing enforcement and
historical proof with closure=true before this change. That observation concerns
the old producer `d85c0df`, not deployment of these fixes.

The repaired producer requires an exact reviewed source pin and fresh native
valid/invalid/source-spoof/direct-update references for that substrate. Native PR
acceptance under the old producer proves candidate tests, not execution of the new
publisher. Record the new pin, native runs and fresh Doctor separately when deployed.

## Explicit limits

- Strict multiple-workflow integration remains outside the current native envelope;
  cooperative mode preserves existing project workflows with no closure claim.
- Multiple/unknown writers require real ownership/fencing; no local file emulates it.
- Native publisher logs remain required. Expiration requires fresh proof, not cached
  activation. Follow [proof recovery](proof-recovery.md).
- Neither fixtures nor a single successful deployment prove broad production maturity
  or long-term safety/availability. Consumer evidence must identify its actual profile,
  source pins, CI, deployment cases and support period.
