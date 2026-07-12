# H7 Forward Roadmap Stage 1 — Source Health Implementation Plan

**Status: BUILT 2026-07-11; independently reviewed and HARDENED 2026-07-12.**
The hardening closes dry-run validation, concurrent-writer, cross-symbol
supersession, evidence-backed retraction, and exact watcher-replay gaps. Stage
1 is not operationally complete until the 12-name live health command exits 0.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Per-symbol source-health reporting over the v3 gating store (exit non-zero when any watched name's earnings provenance is unhealthy) plus an owner-in-the-loop, append-only refresher that adds raw evidence rows and promotes them into the gating store under the 7b-2R.2 citation contract.

**Architecture:** A read-only research-layer module (`options_researcher/h7_source_health.py`) computes health from the existing typed gate primitives (`assertions_view`, `earnings_gate`, `next_report`) — it adds NO new gate semantics, only observability. `options_researcher/h7_scope.py` is the one shared universe definition consumed by the watcher and health tooling (and reserved for later roadmap gates). A separate owner-driven tool (`tools/h7_refresh_earnings.py`) is the ONLY mutator; it appends one record per invocation to v2 (raw evidence) or v3 (gating, with `promoted_from` citation). Interprocess store locks cover id allocation, full-store temp-copy validation, and the flushed append; dry runs validate the same candidate without writing. No network anywhere; no crawler (recurring automation stays deferred by owner decision).

**Tech Stack:** Python 3.12, stdlib csv/datetime/argparse, existing `options_researcher.h7_earnings` loaders, `data.cache_runner.trading_days`/`session_close_utc`, unittest (offline).

**Authorization:** Owner authorized "continue with the plan" 2026-07-11 after the 7b-2R.2 merge; Stage 1 is the next dependency-ordered arc in `docs/superpowers/plans/2026-07-11-h7-forward-roadmap.md`. Stages 2–8 remain unauthorized; Stage 8 belongs to owner + independent review.

**Owner-owned number:** `H7_SOURCE_HEALTH_WARN_SESSIONS = 5` is LLM-proposed (reasoning: one trading week of runway to refresh a schedule by hand before grace lapses into UNKNOWN and the watcher fails closed). It is an OPERATIONAL alerting threshold — it never changes what the gate returns or what any verdict does — so it is not a registered strategy parameter and gets no freeze test. Flag it to the owner for ratification or retyping in the session summary.

**Health semantics (documented here, tested below):**

- Universe: exactly the names the watcher evaluates — `H7_WATCHLIST + H7_CORE_LONG_ONLY` minus `H7_EXCLUDED` (12 names today).
- Per symbol, over the in-view (`known_as_of`-filtered) gating-class assertions:
  - `coverage = "schedule"` — a live future assertion exists (status estimated/confirmed, expected_date ≥ on);
  - `coverage = "grace"` — no live future assertion, but an occurred report within `H7_EARNINGS_POST_REPORT_GRACE_D` calendar days;
  - `coverage = "none"` — neither.
- Flags: `MISSING` when coverage ≠ schedule (the owner's refresh work-list); `STALE` when coverage == grace AND the grace window lapses within `H7_SOURCE_HEALTH_WARN_SESSIONS` XNYS sessions (urgent: the gate is about to start failing closed).
- `healthy` = gate ≠ UNKNOWN and not STALE. (BANNED is healthy — an informed pre-report ban. MISSING alone with long grace runway is the normal post-report state and stays healthy; it escalates to STALE, then to gate-UNKNOWN.)
- Exit codes: 0 all healthy, 1 any unhealthy, 2 store unreadable / bad invocation (fail closed, mirroring the watcher).
- Point-in-time: live runs use now-UTC as `known_as_of`; `--as-of D` uses the last completed session before D as both the gate date and its close cutoff (exact watcher replay semantics; no lookahead).

**Refresher rules (mechanically enforced):**

- `append-raw`: one assertion or evidence-backed retraction row into v2. A retraction names the earlier raw A id it invalidates. `aggregator` source ⇒ status MUST be `estimated` AND notes required (disclosed limitation). `occurred` from a non-`sec_filing` source ⇒ notes required (why no SEC acceptance time). Everything else the store loader already enforces (https URL, tz-aware timestamps, monotone checked_at, status/date coherence) via validate-on-temp-copy-then-append.
- `promote`: one gating row into v3 citing `--raw-id` via `promoted_from`, copying `_PROMOTION_FIELDS` (including `record_type`) verbatim from the raw record. Refuses: foreign raw id; `actual_quarterly_earnings` when the raw row carries no fiscal_period (fiscal identity must live IN the evidence — append a raw row carrying identity first); double-promotion of the same raw id (corrections append a NEW raw row and supersede the old G id); `--supersedes` naming a nonexistent or different-symbol/event gating record; a retraction whose raw target is not the raw evidence promoted into its gating target. After building the row, the FULL `load_assertions()` contract check runs on a temp copy before the real append.
- Both subcommands support `--dry-run` (validate and print the row, write nothing), serialize writers with store locks, and never rewrite/reorder existing rows.

**Files:**
- Modify: `config.py` (one operational constant, after the v1.3 block)
- Create: `options_researcher/h7_source_health.py`
- Create: `options_researcher/h7_scope.py` (independent-review hardening)
- Create: `tools/h7_refresh_earnings.py`
- Create: `tests/test_h7_source_health.py`
- Create: `tests/test_h7_refresh_earnings.py`
- Modify: `docs/superpowers/plans/2026-07-11-h7-forward-roadmap.md` (Stage 1 status note only)
- Modify: `README.md` + `CLAUDE.md` (command lines), `ledger/facts.log` (dated fact, append-only)

---

### Task 1: Config constant

**Files:**
- Modify: `config.py` (immediately after the `H7_HISTORICAL_WITHDRAWAL_HASH` block)

- [x] **Step 1: Add the operational constant**

```python
# ---------------------------------------------------------------------------
# Forward-roadmap Stage 1 (source health) -- OPERATIONAL alerting threshold,
# NOT a registered strategy parameter: it changes when a human is warned,
# never what the earnings gate returns or what any backtest/verdict does.
# LLM-proposed 2026-07-11 (one trading week of runway to refresh a schedule
# by hand before grace lapses into UNKNOWN); owner may retype.
H7_SOURCE_HEALTH_WARN_SESSIONS = 5
```

- [x] **Step 2: Verify the freeze tests still pass (they pin values, not the key set)**

Run: `uv run python -m unittest tests.test_config_h7 -v` → expect all pass.

- [x] **Step 3: Commit** — `feat(stage1): H7_SOURCE_HEALTH_WARN_SESSIONS operational threshold (LLM-proposed, owner may retype)`

### Task 2: Health module (TDD)

**Files:**
- Create: `tests/test_h7_source_health.py`
- Create: `options_researcher/h7_source_health.py`

- [x] **Step 1: Write failing tests** — fixture helper mirrors `tests/test_h7_earnings.A()` plus `record_id`/`source_type`/`occurred_date` params; cover: schedule-coverage healthy (days_to_report exact); grace-with-runway → MISSING only, healthy; grace lapsing within N sessions → MISSING+STALE, unhealthy (on=2026-07-08, occurred=2026-05-27 ⇒ grace_end Sat 2026-07-11, 2 sessions left); grace expired → gate UNKNOWN, coverage none, unhealthy; no assertions → UNKNOWN+MISSING; same-fiscal-period conflict → gate UNKNOWN with empty flags, unhealthy; point-in-time invisibility (known_as_of after cutoff ⇒ MISSING); newest-assertion fields; `watch_universe()` = 12 names, no HYLN; `_sessions_between` weekend math; deterministic CLI replay fixture proving requested Saturday evaluates Friday with Friday's close cutoff; malformed/future `--as-of` refused with exit 2. The test no longer pins an incomplete committed-store count that an honest historical backfill must change.
- [x] **Step 2: Run tests, verify they fail** (`ModuleNotFoundError: options_researcher.h7_source_health`).
- [x] **Step 3: Implement `options_researcher/h7_source_health.py`** — module docstring states read-only + Stage 1 provenance; `watch_universe()`; `_sessions_between(start, end)` via `data.cache_runner.trading_days` (sessions strictly after start, ≤ end); shared `h7_earnings.report_date`; `symbol_health(symbol, on, assertions, *, known_as_of, warn_sessions) -> dict` with keys symbol/gate/gate_reason/newest_record_id/newest_known_as_of/event_class/status/source_type/next_report/days_to_report/coverage/grace_end/grace_sessions_left/flags/healthy per the semantics block above; `main(argv) -> int` per the CLI contract (argparse, `--as-of`, fail-closed 2 on unreadable store or bad/future date, one line per symbol, summary line, exit 1 when any unhealthy).
- [x] **Step 4: Run the new tests → pass; run the FULL suite → pass (exit code, not grep).**
- [x] **Step 5: Commit** — `feat(stage1): per-symbol source-health report over the v3 gating store`

### Task 3: Refresher tool (TDD)

**Files:**
- Create: `tests/test_h7_refresh_earnings.py`
- Create: `tools/h7_refresh_earnings.py`

- [x] **Step 1: Write failing tests** — tempfile v2+v3 fixture stores (valid per loader: https URLs, tz-aware stamps, monotone checked_at, A0001 MSFT occurred sec_filing WITH fiscal identity, A0002 VST confirmed schedule company_pr with fiscal, G0001 promoting A0001); cores called with explicit paths + fixed `now_utc`. Cover: append_raw happy path (next A-id, file gains exactly one line, prior bytes untouched — append-only proof, store revalidates); aggregator+confirmed refused; aggregator+estimated+empty-notes refused; occurred+company_pr+empty-notes refused; occurred+sec_filing+empty-notes accepted; dry-run validates while leaving bytes unchanged; naive timestamp and regressive checked_at refuse; notes containing commas round-trip; competing writer waits for the store lock. Promote covers citation/verbatim copy, missing fiscal, foreign/double promotion, unknown and cross-symbol supersession refusal, valid correction, and validation-grade dry-run.
- [x] **Step 2: Run tests, verify they fail.**
- [x] **Step 3: Implement `tools/h7_refresh_earnings.py`** — sys.path shim like the collector; import `_GATING_COLUMNS`, `_RAW_COLUMNS`, `_PROMOTION_FIELDS`, loaders, `EVENT_CLASSES`, `GATING_EVENT_CLASS`, paths from `h7_earnings` (private-constant imports are deliberate: single source of truth for the contract); `_next_id(rows, prefix)`; locked `_validated_append(path, row, columns, loader)` (copy store to a system-temp file, append row, run loader on the copy, only then flush+fsync the real append; dry-run stops after validation; always unlink the temp); `append_raw(...)` and `promote(...)` cores enforcing exactly the refresher rules above, `raise SystemExit(msg)` on refusal, returning the appended row dict; `main(argv) -> int` with `append-raw`/`promote` subparsers, `--dry-run` on both, `checked_at = datetime.now(timezone.utc).isoformat()`, printed confirmation of the exact row appended.
- [x] **Step 4: Run the new tests → pass; FULL suite → pass (exit code).**
- [x] **Step 5: Commit** — `feat(stage1): owner-in-the-loop append-only earnings refresher (append-raw + promote under the citation contract)`

### Task 4: Docs, roadmap status, ledger fact

- [x] **Step 1:** README + CLAUDE.md: add the two command lines next to the existing h7_watch entry. Roadmap doc: annotate Stage 1 heading `(BUILT 2026-07-11 — h7_source_health + h7_refresh_earnings; stages 2-8 still not implemented)` and adjust the top status line to match. `ledger/facts.log`: append one dated fact (mirror tail format) recording merge `2d04b47` + Stage 1 tooling with test counts.
- [x] **Step 2:** `uv run ruff check .`, `uv run pyright`, full unittest — all exit 0 (true exit codes).
- [x] **Step 3: Commit** — `docs+ledger(stage1): roadmap Stage 1 BUILT; commands documented; dated fact appended`

## Self-review

Spec coverage: newest assertion + class/status/source (symbol_health newest_* fields) ✓; days to expected report ✓; STALE/MISSING flags with N-session grace warning ✓; exact watcher replay session/cutoff ✓; exit non-zero when unhealthy ✓; owner-in-the-loop append-only refresher with SEC-first hierarchy and disclosed aggregator estimates ✓; dry-run validation + serialized id allocation/append ✓; promotion and retraction cite raw evidence, with same-event supersession and cross-store retraction-target identity enforced ✓; no crawler/no recurring automation ✓; offline tests ✓. Type consistency: `symbol_health` field names used identically in module, CLI, and tests; `_PROMOTION_FIELDS` imported, never re-declared. No placeholders remain.
