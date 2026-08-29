# Options Validator Repository Audit - Baseline Verification

**Captured:** 2026-08-25 America/New_York
**Frozen start SHA:** `c9e74ccd05e4ecdd0de8de6f35bef714bc6f1771`
**Worktree:** `/Users/carsynstephenson/options-validator/.tmp/worktrees/2026-08-25-1403-options-validator-audit`
**Environment:** existing locked `.venv`, Python 3.12.13, uv 0.11.29, `UV_OFFLINE=1`, `LIVE_MARKET_DATA_PROVIDER=schwab`; no dependency install and no provider call.

## Verdict

The static baseline is healthy enough for a read-only audit, but the full test baseline is **environment-blocked**, not clean. Compilation, lint, types, the canonical cache manifest, and both append-only ledger checks passed. The suite executed all 3,229 tests twice; after correcting two worktree/macOS setup conditions, the second run encountered 11 process-creation failures because the host was above its per-user process limit. All 11 affected tests passed in isolated reruns. This does not justify a blanket `tests pass` claim.

## Static and test checks

| Check | Result | Evidence |
|---|---:|---|
| `python -m compileall` | PASS | Exit 0, about 1 second. |
| `ruff check .` | PASS | Exit 0. |
| `ruff format --check .` | FAIL (baseline debt) | Exit 1: 281 files would be reformatted; 148 already formatted. No mass-formatting was attempted. |
| `pyright` | PASS | Exit 0: 0 errors, 0 warnings. |
| First coverage suite | ENV FAIL | 3,229 tests, 2 failures, 5 skipped, 228.368 seconds. Both failures were setup/path conditions described below. |
| Coverage report | PASS | Exit 0; total statement coverage 81%. |
| Corrected full-suite rerun | ENV BLOCKED | 3,229 tests, 7 failures, 4 errors, 5 skipped, 186.206 seconds. Every failure contained `fork: Resource temporarily unavailable`, `BlockingIOError: [Errno 35]`, or a downstream assertion caused by that inability to fork. |
| Isolated rerun of initial two failures | PASS | 2 tests in 0.073 seconds. |
| Isolated rerun of all 11 process-pressure failures | PASS | 4 intraday wrapper tests in 0.053 seconds; 5 irreplaceable-data root-anchoring tests in 0.632 seconds; 2 job-health CLI tests in 0.864 seconds. |

## Root-cause evidence

1. `tests.test_daily_ritual_provenance.DailyRitualProvenanceTests.test_status_preserves_log_tree_and_lockfile_bytes` initially failed because a fresh linked worktree had no `.venv/bin/python`, which `tools/daily_ritual.sh` requires. An ignored `.venv` symlink to the canonical locked environment corrected the setup, and the targeted test passed.
2. `tests.test_h7_backup.H7ForwardBackupTests.test_backup_prints_expected_payload_size_before_restic` initially compared a `/var/...` temporary path with macOS's canonical `/private/var/...` resolution. Setting `TMPDIR` to the canonical `/private/var/...` path corrected the setup, and the targeted test passed.
3. Before the corrected full rerun, the host had 1,513 processes against a per-user limit of 1,333. Of those, 797 were zombies with parent PID 2842, an unrelated long-running Pioneer `FwUpdateManagerd`. The audit did not terminate or alter that external process. The affected tests all passed when rerun in small groups, supporting resource exhaustion rather than eleven independent code regressions.

## Integrity and research-context checks

| Check | Result | Interpretation |
|---|---:|---|
| `python -m research.cli verify` | PASS | `ledger OK`. |
| `python -m options_researcher.h7_event_ledger verify` | PASS | `VALID records=1 head=a1ea228c2abb`. |
| `python -m options_researcher.h7_event_ledger verify --base-dir ledger/h7_forward_schwab` | PASS | `VALID EMPTY`. |
| `python tools/irreplaceable_data_guard.py verify` | PASS | Canonical checkout reported `irreplaceable data: OK`. |
| `python tools/cache_manifest.py verify` from canonical checkout | PASS | `verify: OK`. A prior cacheless-worktree invocation reported 31,366 missing files; that result was a location/coverage limitation, not canonical loss. |
| `python tools/h7_data_audit.py --verify` from canonical checkout | FAIL CLOSED | Current receipt rejected because multiple inputs/hashes changed. No receipt was regenerated. |
| `RESEARCH_RITUAL_ROOT=/Users/carsynstephenson/options-validator-ops python -m tools.research_context_assemble --verify` | FAIL CLOSED | Missing canonical `reports/attractiveness_research/2026-08-19/manifest.json`. No artifact was rebuilt. |
| `git diff --check c9e74ccd05e4ecdd0de8de6f35bef714bc6f1771 --` | PASS | No whitespace errors in audit changes at capture time. |

## Quant and provider boundary

No new backtest, strategy verdict, provider refresh, live/paper decision, ledger append, cache mutation, or research receipt regeneration was run. The repository's ledger-discipline and data-audit gates require a declared hypothesis, frozen parameters, admissible point-in-time data, and explicit run authority before such work. The audit therefore evaluates strategy validity from existing canonical evidence, code, and tests only.

## Unsupported assumptions and limitations

- Passing isolated tests shows the observed 11 failures were not reproducible under lower process pressure; it does not prove the entire suite would pass on a healthy host.
- The 81% figure is aggregate coverage, not evidence that decision-critical paths are sufficiently covered.
- The stale/missing research receipts are fail-closed operational evidence, not proof that underlying cached data are invalid.
- Formatting debt is repository-wide and pre-existing; changing it would violate the narrow-change and protected-WIP rules.
