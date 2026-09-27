# Locked dependencies in isolated candidates

Ignored `node_modules` in the source checkout is not a candidate input. Local
`verify` creates a clean merged-result worktree and rejects changes to it. Trusted
CI mounts that result at `/candidate` read-only, disables network access and uses
a new container for each acceptance command. Installing into the candidate or
sharing scratch between commands is not a supported preparation path.

Use a reviewed project image with dependencies installed before candidate execution.
This is a project acceptance recipe, not a new preparation API. This example targets
Linux Node projects; mixed toolchains can use the same layout.

## Prepare the immutable image

Use a digest-pinned base with the project's exact Node/npm versions, Python, Git
and an independently installed OpenHarness. In a separate trusted image build:

```dockerfile
ARG PROJECT_BASE
FROM ${PROJECT_BASE}
WORKDIR /opt/project-deps
COPY package.json package-lock.json ./
# COPY .npmrc ./  # only reviewed credential-free project configuration
RUN npm ci --ignore-scripts --no-audit --no-fund
WORKDIR /candidate
```

Resolve `PROJECT_BASE` to a real immutable digest. Review dependencies requiring
install scripts separately; do not silently enable them. Preserve the input files
next to the prepared `node_modules`. Publish the image and set its actual registry
digest in `verification.sandbox_image`; a tag is insufficient. Archive the recipe,
base identity, tool versions and dependency inputs. Keep candidate source, host
caches and registry credentials out of the final image. Candidate execution remains
credential-free and offline even when trusted preparation needs registry access.

## One offline acceptance command

Commit a Linux project script such as `scripts/offline-test.sh`:

```sh
#!/bin/sh
set -eu
deps=/opt/project-deps
cmp package.json "$deps/package.json"
cmp package-lock.json "$deps/package-lock.json"
# Compare .npmrc too if it is material to installation.
scratch=$(mktemp -d /tmp/project-acceptance.XXXXXX)
trap 'rm -rf "$scratch"' EXIT HUP INT TERM
tar --exclude=.git --exclude=node_modules -cf "$scratch/source.tar" .
tar -xf "$scratch/source.tar" -C "$scratch"
rm "$scratch/source.tar"
cp -R "$deps/node_modules" "$scratch/node_modules"
cd "$scratch"
npm test --ignore-scripts
```

Configure a single command `[["sh", "scripts/offline-test.sh"]]`, so preparation
and tests share one `/tmp` mount. Project imports resolve the copied dependencies
next to the copied source. All output and caches must stay in scratch. Adjust the
test command to reviewed project semantics. The explicit npm test script still runs
with `--ignore-scripts`; its pre/post scripts do not
([npm documentation](https://docs.npmjs.com/cli/v10/commands/npm-ci/)).
Tests needing Git metadata must prepare it explicitly in scratch; this example
excludes `.git`. The existing 1 GiB scratch and resource limits still apply.

Declare `package.json`, `package-lock.json` and material install configuration in
`verification.material_inputs`. Tracked source is already bound by the candidate
tree; these inputs make the dependency boundary explicit. The image digest is part
of verification configuration identity. Comparing image inputs with candidate
inputs rejects an outdated image when the lock changes.

A lock change requires rebuilding the image and reviewing the configuration change
under existing exact control approval and old/proposed acceptance checks. If the
old recipe cannot accept the new lock, plan a compatible staged migration; do not
bypass its failure. A dependency image change alone cannot establish native closure.

## Local diagnostics

On Linux, provision `/opt/project-deps` from the same reviewed build and use matching
toolchain versions before invoking `verify`. On Windows use the Linux image for
parity. Native host dependencies are not hashed by the configured image digest:
local evidence records verifier runtime/configuration, not arbitrary host package
contents, and cannot authorize integration.

For closer parity, run local verification in the exact project image. Mount a clean
disposable source clone read-only at `/source`, without personal Git configuration
or credentials. Inside the container, clone into writable `/tmp` and run the
independently installed tool:

```sh
git clone --no-hardlinks /source /tmp/project
cd /tmp/project
openharness --repo . verify --head HEAD --base HEAD
```

`HEAD/HEAD` is only a dependency smoke test. For integration diagnostics resolve the
real head/base commits before going offline and ensure both exist in the disposable
clone. Apply the same non-root, no-network, read-only-root and writable `/tmp` limits
as `ci.docker_arguments`. The clone must be readable by that user; a narrowly scoped
Git safe-directory setting may be necessary for `/source`. Do not mount Docker's
socket or publisher credentials. Git creates local diagnostic candidates under the
writable clone; the original source stays read-only.

## Adoption proof

Exercise the actual pinned image through the normal trusted check:

1. A clean candidate with matching lock passes without source `node_modules`.
2. Changed package/lock inputs fail before tests run.
3. Imports resolve prepared dependencies; output stays in scratch; candidate tree
   and material files remain unchanged.
4. Network fetches and writes to `/candidate` fail; secrets are unavailable; a second
   command cannot inherit the first command's scratch files.
5. Head/base, material input, image and configuration drift invalidate old evidence.

Documentation and fixtures are not proof of a live adopter image. Until native cases
have run, retain the corresponding OPEN GAP. This recipe does not add a writable
candidate, privileged preparation job or unbound host-cache adapter.
