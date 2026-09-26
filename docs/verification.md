# v0.1 verification record

Date: 2026-09-26. Scope: executable Genesis tooling, not full repository Harness closure.

`python -m unittest discover -s tests -v`: 49 tests, 48 passed, one skipped because the
Windows environment does not permit symlink creation. No failures. The symlink scenario
remains present for environments supporting creation. Linux CI is configured but has
not run remotely. `python -m compileall -q openharness` passed.

Editable packaging was installed into the workspace `.venv` using
`python -m pip install --no-build-isolation --no-deps --no-index -e .` with bundled
setuptools. The installed `openharness --version` prints `0.1.0`. CLI subprocess tests
verify entry-point help, repeatable installation, passing/failing diagnostic checks,
fresh-process evidence discovery and review-only remote setup output.

The suite uses actual temporary Git repositories for isolated Changes, merged-tree
verification, head/base freshness, dirty checkout rejection, failed/mutating checks,
environment changes, configuration/origin/verifier drift, recovery and lifecycle
protection. Deterministic GitHub responses exercise API failures, inherited policy,
sourced checks, merge queue, bypass actors, malformed observations and workflow drift.
These tests are implementation evidence, not proof of deployed GitHub enforcement.

Read-only GitHub Doctor observed `CHNISam/OpenHarness`, target `main`, without API
errors: no effective rules, no rulesets, no branch protection and no workflows.
Lifecycle is GENESIS and closure is false. [Doctor JSON](github-doctor.json) is a
dated snapshot; its hashes and assumptions must be revalidated after material changes.
[Setup proposal](github-setup-proposal.json) is not applied and contains unresolved
trusted App, merge queue, verifier and deployment proof requirements.

The runtime always keeps unimplemented external provenance/coverage as OPEN GAP.
Activation and protected managed transitions are blocked. Genesis single-writer
applicability is a declared trusted envelope assumption, not an OS writer-count proof.
Outside that envelope, exclusive authority/fencing requires an effective adapter.

Candidate end-to-end verification is run separately after committing this implementation;
the resulting diagnostic evidence resides in the Git common directory and cannot
authorize GitHub integration. Remote integration remains unverified and unconfigured.
