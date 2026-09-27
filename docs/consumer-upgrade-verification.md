# Issue #30 verification record

Date: 2026-09-27. Work is sequential in the managed `codex/30-consumer-upgrades`
workspace bound to GitHub Issue #30 and base
`8a088a700b52fb1187badd5578b8000c1b49191a`.

## Implementation verification

- `python -m unittest discover -s tests -v`: **91 tests passed**. Fourteen consumer-upgrade tests cover real temporary Git
  consumers, deterministic immutable-release discovery, proposed SHA/config delta,
  enrollment, mutable/untrusted/re-published version rejection, compatible artifact
  migration, repeat preparation, transactional rollback, canonical governed revert,
  failed consumer acceptance, stale activation, incomplete requests, annotated tags,
  observation races and independent trusted candidate migration validation.
- `python -m compileall -q openharness`: exit 0.
- `git diff --check`: exit 0.
- Real Renovate **44.115.10**, supported Node **24.11.0**: custom regex manager
  extracted the request as one `github-releases` dependency for
  `CHNISam/OpenHarness`, current value `0.2.1`, SemVer and `^v` extraction.
  Strict repository config validation (`--strict --no-global`) exited 0. The
  optional native RE2 module was unavailable on Windows; Renovate used its RegExp
  fallback. This is config/extraction evidence, not a live scheduled bot delivery.

## Governance and live evidence boundary

Entry with the established independently installed 0.2.0 verifier observed live
managed closure before workspace creation. The workspace was created through the
normal Issue-bound CLI and current target observation. The proposed implementation
changes the producer dependency identity. Doctor using proposed 0.2.1 code observes
live API responses without provider errors, but reports **closure/readiness false**:
the configured source still pins the old producer, and deployment proof does not
cover the new source. This is an expected OPEN GAP; no new activation is claimed.

The existing controller and native owner head/base control approval remain the
integration authorities. The PR must obtain their checks before governed merge.
Fixture PASS, updater config and local candidate diagnostics do not replace those
checks. No native policy has been changed, no consumer has been silently updated,
and no activation or canonical integration is requested by the bot.

The producer release API returned no published releases when implementation began.
A reviewed, integrated immutable release, enrolled consumer and configured trusted
self-hosted Renovate runner remain deployment prerequisites. The committed
`openharness-release.json` is version 0.2.1 compiler output, not a claim that the
release is already published. See `docs/consumer-upgrades.md` for the executable
release, enrollment, updater, verification and explicit re-proof procedure.
