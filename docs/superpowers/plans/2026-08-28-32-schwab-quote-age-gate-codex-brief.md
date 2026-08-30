# Codex brief 32 — daily quote-age REPORT for Schwab captures (DATA-02, rev 3 — regated)

**Date:** 2026-08-28 (rev 3 — owner rerouted after two review FAILs)
**Author:** Claude orchestrating session (Fable), deferred-closeout session
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** HANDED OFF TO CODEX (rev 4) — round-3 fresh independent
review (Opus, 2026-08-28) verdict PASS WITH FIXES (F1–F12; F1–F3
blocking); ALL applied in this rev; Fable sign-off recorded. The round-3
reviewer reproduced every quantitative claim byte-for-byte and confirmed
the seam, the sidecar's consumer-safety, and both named tests. Owner
directive to proceed: 2026-08-28 in-session.
**Owner ruling (2026-08-28 in-session, decision prompt):** "Report now,
gate later" — a descriptive daily quote-age report ships now; the
BLOCKING gate + owner-typed threshold are a **binding requirement of the
H7 Schwab window registration arc** (recorded below). Rationale: round-2
finding N1 proved the gate has no production surface today — the daily
gate reads only the frozen v1 cache (no timestamp columns) and
**`h7_schwab_data_gate.evaluate()`** has zero production callers
(round-3 F1 precision: the MODULE is imported for
`EVIDENCE_MODE`/scope-closure at `h7_data_gate.py:522,:601` and in
`h7_schwab_window_registration.py`; nothing in production calls
`evaluate()` — sole caller is a test).
**Provenance:** Repo-verified against origin/main @`704a138`; round-2
review measurements (Opus, 2026-08-28) labeled Reviewer-measured.

## What ships now (plain language)

Every day at 15:45 the Schwab capture writes option-chain files plus a
manifest and receipt. This brief adds one SIDECAR report per capture —
`reports/schwab_chains/<session>/<tag>.quote_age.json` — describing how old the
quotes inside that day's package are. Display-only, no gate, no
threshold, no effect on any verdict, receipt, or GO/NO_GO.

## Design constraints carried from the two failed rounds (all binding)

1. **Surface (round-2 N1; round-3 F4/F5):** the report reads the
   session's chain parquet bound to its manifest — the only production
   data that has timestamps. Implement as a small standalone module
   (e.g. `options_researcher/schwab_quote_age_report.py`) invoked from
   `capture()` at the EXACT seam: inside the `if complete:` block, after
   `append_fact` (`schwab_chain_capture.py:353`), before the success
   print (`:354`) — NEVER on the partial-failure path (the receipt is
   written on both paths at `:331-334` but the manifest exists only when
   complete). Wrapped fail-soft (try/except + logged note): a report
   failure must be INCAPABLE of failing or altering the capture,
   manifest, or receipt. The report takes `chain_dir`, `reports_dir`,
   and the session from `capture()`'s PARAMETERS (`:230-231`) — never
   module constants; every existing test drives capture with tmp dirs
   and a hardcoded path would be silently wrong under test and in ops.
2. **No receipt/verifier coupling (rounds 1-2 B3/N2):** `verify_session`'s
   return, the capture receipt, and the data-gate receipt are untouched.
   The report is its own file. Do not add any key to any existing
   dict/receipt/artifact.
3. **Both timestamp columns (round-2 N6), both row populations
   (round-3 F11):** the frames carry `timestamp` AND `trade_timestamp`
   (nullable). Report stats for BOTH columns, per symbol and
   package-wide: null counts, min/max, and the age distribution
   (p50/p90/max minutes) relative to the per-symbol MAX of that column —
   computed for ALL ROWS and separately for the SELECTABLE SUBSET.
   Reviewer-measured: all-rows worst ages run 375–1,787 minutes
   (dominated by illiquid contracts) vs 0.61–10.38 for selectable; a
   single blended stat would read as a false alarm. The `"semantics"`
   field says so. For the selectable subset, pass a mask into
   `data.recent_topup.audit_chain`'s existing `selectable_mask=`
   parameter path or compute per its documented default — round-3 F12:
   the gap is a public accessor for the DEFAULT mask, not injection
   ability; if a one-line public accessor in `data/recent_topup.py` is
   needed, coordinate with brief 33 (which owns that file) by landing
   AFTER it.
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
6. **Overwrite guard + lane-safe filename (round-3 F6/F10):** the
   sidecar filename derives from the capture's `receipt_filename` stem
   (pre-close → `preclose.quote_age.json`; a future midday lane writes
   `midday.quote_age.json` — PR #100's parameterization tests already
   drive a second lane into the SAME session dir, so a fixed name would
   collide and the fail-soft would silently swallow the refusal). Write
   via `data.atomic_io.atomic_text_write` (no partial JSON in a
   git-committed data-tier dir), with a pre-write `path.exists()` check
   raising `FileExistsError` unless byte-identical (brief 33 M1
   pattern).
6b. **Fail-soft note prefix (round-3 F7):** the logged note uses a
   distinct stable anchored prefix, `schwab_quote_age_report skipped:`,
   which must NOT match the four pinned
   `^schwab_chain_capture <label>:` classifications
   (`tests/test_shell_banner_guard.py:398-402`) — a chronically failing
   report stays greppable in the ops log instead of invisible.
6c. **Machine-checked authority labels (round-3 F8):** the report emits
   `"display_only": true` and `"verdict_eligible": false` (the enforced
   repo pair — `options_researcher/ownership_context.py:164-166`
   precedent), NOT an invented authority string. Test 1 asserts both
   keys.
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

The trigger is the OWNER REGISTRATION EVENT ALONE (round-3 F2: the
earlier conjunctive wording — "registers AND gains a production caller" —
could be half-satisfied by merely merging open PR #71
`codex/h7-schwab-recovery`, whose `tools/h7_schwab_manual_activate.py`
calls `h7_schwab_data_gate.evaluate`; a merge is not a registration).
When the H7 Schwab window REGISTERS, the BLOCKING per-quote age gate
becomes a REQUIRED work package of that arc, with: an owner-typed threshold (evidence
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
2. Capture-flow integration (round-3 F9 — within-run A/B, since the
   receipt embeds the landing's own `code_sha` and can never match a
   pre-change artifact): under the existing `_isolated_capture()`
   harness (`tests/test_schwab_chain_parameterization.py:64-88`),
   capture into dir A with the working writer and into dir B with the
   writer mocked to raise; assert manifest bytes, receipt bytes,
   `exit_code == 0`, and the returned receipt dict are all EQUAL, and
   the failure note (with the 6b prefix) was logged.
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
