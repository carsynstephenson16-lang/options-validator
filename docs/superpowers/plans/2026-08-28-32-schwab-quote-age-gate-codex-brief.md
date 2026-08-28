# Codex brief 32 — daily quote-age REPORT for Schwab captures (DATA-02, rev 3 — regated)

**Date:** 2026-08-28 (rev 3 — owner rerouted after two review FAILs)
**Author:** Claude orchestrating session (Fable), deferred-closeout session
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** DRAFT rev 3 — pending FRESH independent adversarial review
(rounds 1 and 2 FAILED earlier gate designs; this rev is a different,
smaller deliverable per owner ruling).
**Owner ruling (2026-08-28 in-session, decision prompt):** "Report now,
gate later" — a descriptive daily quote-age report ships now; the
BLOCKING gate + owner-typed threshold are a **binding requirement of the
H7 Schwab window registration arc** (recorded below). Rationale: round-2
finding N1 proved the gate has no production surface today — the daily
gate reads only the frozen v1 cache (no timestamp columns) and
`h7_schwab_data_gate` has zero production callers.
**Provenance:** Repo-verified against origin/main @`704a138`; round-2
review measurements (Opus, 2026-08-28) labeled Reviewer-measured.

## What ships now (plain language)

Every day at 15:45 the Schwab capture writes option-chain files plus a
manifest and receipt. This brief adds one SIDECAR report per capture —
`reports/schwab_chains/<session>/quote_age.json` — describing how old the
quotes inside that day's package are. Display-only, no gate, no
threshold, no effect on any verdict, receipt, or GO/NO_GO.

## Design constraints carried from the two failed rounds (all binding)

1. **Surface (round-2 N1):** the report reads `.cache/schwab_chains/*_<session>.parquet`
   bound to `reports/schwab_chains/<session>/manifest.json` — the only
   production data that has timestamps. Implement as a small standalone
   module (e.g. `options_researcher/schwab_quote_age_report.py`) invoked
   from the capture flow AFTER the manifest/receipt are written, wrapped
   fail-soft (try/except + logged note): a report failure must be
   INCAPABLE of failing or altering the capture, manifest, or receipt.
2. **No receipt/verifier coupling (rounds 1-2 B3/N2):** `verify_session`'s
   return, the capture receipt, and the data-gate receipt are untouched.
   The report is its own file. Do not add any key to any existing
   dict/receipt/artifact.
3. **Both timestamp columns (round-2 N6):** the frames carry `timestamp`
   AND `trade_timestamp` (nullable). Report stats for BOTH, per symbol
   and package-wide: null counts, min/max, and the age distribution
   (p50/p90/max minutes) relative to the per-symbol MAX of that column.
4. **Honest vocabulary (round-2 N10 note):** the per-symbol-max reference
   is a WITHIN-PACKAGE DISPERSION measure, not absolute wall-clock age —
   a wholly-late package reads as fresh. Say exactly that in the report's
   own `"semantics"` field. Absolute cross-day staleness IS covered:
   prior-session detection compares `tz_convert("America/New_York")` of
   each timestamp to the session date (round-2 N9 — pin the tz step; the
   stored dtype is `datetime64[ns, UTC]`).
5. **Durability is already free:** `reports/schwab_chains` is in the
   ritual's `DATA_TIER_PATHS` (PR #76) — the sidecar rides the existing
   entry. NO edit to `tools/daily_ritual.sh`, none, at all.
6. **Overwrite guard:** same pattern as brief 33 M1 — pre-write
   `path.exists()` check, `FileExistsError` unless byte-identical.
7. **Hash disclosure (round-2 M6 class):** `options_researcher/` is
   inside `DIAGNOSTIC_SOURCE_PATHS_V3`; this landing moves
   `diagnostic_source_hash()`. Measured harmless today (all existing
   data-gate receipts already mismatch live hashes); one PR-body
   sentence, and any receipt intended for a future Schwab registration
   is generated after the last code landing.
8. **No config constants.** A report needs no threshold — so no
   `FROZEN_CONFIG_UPPERCASE_NAMES` pin update and no `config_hash()`
   move from this brief.

## Recorded for the H7 registration arc (binding hand-forward)

When the H7 Schwab window registers and `h7_schwab_data_gate` gains a
production caller, the BLOCKING per-quote age gate becomes a REQUIRED
work package of that arc, with: an owner-typed threshold (evidence
already gathered, Reviewer-measured 2026-08-28 across all seven
timestamped sessions — worst SELECTABLE age 0.61–10.38 min; a 10-min
block would have NO_GO'd 1 of 7 sessions, 15/20 min none; n=7), a
public selectable-mask accessor in `data/recent_topup.py` (round-2 N4 —
the mask is private at `:489`; brief 33 owns that file, so ordering is
33 → gate), and reason-code semantics designed against
`h7_data_gate.py:417` and `build_receipt` `:645` (rounds 1-2 B1/N2).
This paragraph is the DATA-02 disposition of record; do not re-propose a
standalone gate outside that arc.

## Scope

**IN:** the report module, its fail-soft invocation from the capture
flow, tests.
**OUT (hard stops):** no gate, no threshold, no config changes; no edits
to `tools/schwab_chain_manifest.py` `verify_session` return, any receipt,
`options_researcher/h7_data_gate.py`, `data/recent_topup.py`, `config.py`,
or `tools/daily_ritual.sh`; no provider calls; report failures never
propagate; nothing verdict-bearing — the report file carries
`"authority": "descriptive-only"` and its max as-of session.

## Tests (unittest, offline, synthetic parquet fixtures)

1. Synthetic package (both timestamp columns, some nulls, one
   prior-session row) → report written with correct per-symbol stats,
   prior-session count, semantics field, as-of stamp.
2. Capture-flow integration: report writer raising → capture result,
   manifest, receipt byte-identical to pre-change; failure note logged
   (fail-soft proof, RED/GREEN).
3. Overwrite guard: differing same-session rewrite refuses; identical
   no-op.
4. No-coupling regression: `verify_session` output on existing fixtures
   byte-identical to pre-change.

## Acceptance

```
uv run python -m unittest discover -s tests
uv run ruff check . && uv run pyright
```
Born-draft PR; owner un-drafts. Independent of briefs 33/34/35 (no shared
files); no landing-order constraint.
