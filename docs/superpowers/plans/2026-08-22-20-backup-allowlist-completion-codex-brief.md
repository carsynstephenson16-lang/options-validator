# Backup allow-list completion — Codex brief

- **Date:** 2026-08-22
- **Author:** Claude Fable 5 orchestrating session
- **Executor:** Codex (default model, high reasoning)
- **Status:** DRAFT — pending independent adversarial review before hand-off
- **Provenance:** Repo-verified against origin/main @accd165bd2a7aeacf8ff6f1630d0b3b815b39703 unless labeled otherwise.

## Why this exists (plain language)

`tools/irreplaceable_data_guard.py` protects eight gitignored data namespaces because the cached options data can never be re-purchased (ThetaData acquisition is permanently disabled, OD-4). But the backup tool's allow-list covers only four of them (`.cache/chains`, `.cache/schwab_chains`, `.cache/underlying`, `reports/schwab_chains` — adversarial-review correction 2026-08-22: `reports/schwab_chains` is in both lists). The 2026-08-22 audit finding: `.cache/chains_v2` (~1.9 GB), `.cache/future_tickers` (~110 MB), `.cache/intraday`, and `.cache/underlying_ohlcv` are guard-protected yet have **no backup path at all** — if the disk dies, they are gone. This brief closes that gap in code. (Choosing an off-machine backup destination and running the backup remain owner actions — routing row #3 of plan 19.)

## Scope

**IN:**
- Extend `BACKUP_PATHS` in `tools/h7_forward_backup.py:60-75` (Repo-verified) so every namespace listed in `irreplaceable_data_guard.py`'s `DEFAULT_NAMESPACES` is covered.
- Tests proving the two lists cannot drift again.

**OUT (do not touch):**
- No ledger writes, no registration, no authority flips, no live-order paths, no frozen values.
- No changes to `irreplaceable_data_guard.py` semantics.
- No scheduling/LaunchAgent changes — the backup stays owner-run by design (Repo-verified: `tools/h7_forward_backup.py:8-10` docstring; `docs/h7-forward-operations.md:22-40`).
- No change to `EXCLUDE_PATTERNS` (`tools/h7_forward_backup.py:76-79`) beyond what WP-A strictly requires.
- Do not run a real restic backup in tests; tests stay offline.

## Work packages

**WP-A — Extend the allow-list.** Add to `BACKUP_PATHS` every guard namespace currently missing (`.cache/chains_v2`, `.cache/future_tickers`, `.cache/intraday`, `.cache/underlying_ohlcv`). Import the single source of truth: `from tools.irreplaceable_data_guard import DEFAULT_NAMESPACES` — Repo-verified side-effect-free (stdlib-only top-level imports, no module-level execution), and `tools.*` imports are already the pattern (`tools/h7_forward_backup.py:317` imports `tools.cache_manifest`). Hand-copied strings are not acceptable.

**WP-B — Drift-proof test.** Extend the existing precedent test `tests/test_h7_backup.py:18-25` (`test_allow_list_includes_new_schwab_evidence_and_ledger`, a subset assertion — WP-A cannot break it) with an assertion that every namespace in `DEFAULT_NAMESPACES` maps to a covered `BACKUP_PATHS` entry. The test must fail today before WP-A and pass after (prove both directions: commit the failing assertion first or demonstrate it in the PR notes).

**Consequence to state in the PR (adversarial-review M2; corrected per Codex PR-68 review):** every future backup receipt seals per-file hashes of everything in `BACKUP_PATHS` (`run_backup:165`), and `run_restore_check:417-420` demands exact inventory equality. Old sealed receipts stay valid (`backup_paths()` skips absent namespaces). But from this change on, any refresh of `.cache/intraday` / `.cache/underlying_ohlcv` bytes creates the same permanently-unverifiable receipt binding that caused the 2026-08-05 drill-red incident. **Code-verified gap — do NOT claim `record-invalidation` covers this:** `build_invalidation_fact()` expects flat `{exists, sha256, path}` input records, but backup receipts store directories as `{kind: "directory", files: {...}}`, so directory inventory entries are silently skipped and the command records nothing for them; `run_restore_check()` additionally enforces exact inventory equality before applying data-gate invalidations. The PR must state this gap plainly; adding tested backup-inventory invalidation semantics is a separate follow-up work package requiring its own review, not a footnote here.

**WP-C — Size/feasibility note.** The additions raise the backup payload by ~2.1 GB (Inference from `du`; verify with the guard's inventory figures). Print the total expected payload size in the `backup` subcommand's pre-flight output so the owner sees it before the first big run. No behavior change beyond the printed line.

## Acceptance / verification

```
uv run python -m unittest discover -s tests
uv run ruff check . && uv run pyright
```
Exit codes define done. Plus: the WP-B test demonstrably fails on the pre-change tree (both directions proven). No network, no restic invocation in the suite.
