# Brief 17 — H10b resume + H5 observe mode on the Schwab preclose lane (rev 2)

**Date:** 2026-08-17 (rev 2: 2026-08-18)
**Author:** orchestrating Claude session (Fable), 2026-08-16/17 owner-directed batch
**Executor:** Codex (high reasoning)
**Status:** DRAFT — rev 1 FAILED independent adversarial review 2026-08-18
(3 blockers, 6 fixes — all applied in this rev 2); pending re-review before
hand-off. The amendment precondition is MET: H10B_AMENDMENT_V1_1 (seq 28)
and H5_AMENDMENT_V1 (seq 29) were appended 2026-08-19T01:05:33Z (=
2026-08-18 ~21:05 ET) via the typed API after confirmation-round review +
Fable sign-off (`reports/2026-08-17-reopen-drafts-adversarial-review-receipt.md`).
**Provenance:** Repo-verified against branch
`claude/reopen-directives-2026-08-16` @`5b544d6` (which contains
`origin/main` @`3d6f88e`) unless labeled otherwise.

## Why this exists (plain language)

The owner directed (2026-08-16/17, confirmations recorded in
`reports/2026-08-16-owner-directives.md`): H10b's forward-paper observation
resumes on the Schwab 15:45 ET preclose chain captures, and H5 becomes a
daily observer on the same lane with its old entry trigger retired. The
amendments carry review-mandated safety obligations this brief closes
(BL-B closed-trial guard, BL-C no-backfill floor), and this rev 2 folds in
the brief-review blockers (BL-1 IV units, BL-2 floor semantics, BL-3
receipt-schema types) and fixes FX-1..FX-6.

## KNOWN AMENDMENT-TEXT DEFECT (read first)

Seq 28 clause 2 and seq 29 clause 2 both instruct a "percent→decimal (÷100)
normalization" of Schwab IV, citing `schwab_chain_view.py:223`. That claim is
**INVERTED**: the store's `iv` is ALREADY a decimal fraction —
`data/schwab_adapter.py:148-154` (`_iv_decimal`) divides Schwab's
percentage-point `volatility` by 100 at capture time, `schwab_chain_view.py:221-225`
documents that a second division "would render every implied vol ~100x too
small", and guard tests pin it
(`tests/test_schwab_chain_view.py:222,233`). An append-only correction entry
(seq 30, `H10B_H5_AMENDMENT_CORRECTION_V1`) records this; the amendments'
normalization clauses are void and replaced by the no-double-division
obligation in WP-D. Do NOT implement a ÷100. Do NOT touch
`data/schwab_adapter.py` or the two guard tests.

## Scope

**IN:**
- Re-point H10b's daily entry evaluation to verified Schwab preclose captures.
- H10a CLOSED guard in the H10 watcher, red-green test-enforced.
- Namespaced H10b observation store + receipt-schema handling + union reader.
- Floor constants + refusal paths bound to the EVALUATION session.
- New H5 observer output (prices, data availability, Schwab-IV accumulation
  count), fail-visible, labeled non-verdict-bearing.
- Retire the H5 fire path in code AND in the ritual's prose (trigger retired
  per seq 29).

**OUT (hard):**
- No ledger writes (the orchestrating session owns those).
- No H10a-v2 work (separate owner-gated registration).
- No new entry rule for H5.
- `config.py` additions limited to EXACTLY two constants
  (`H10B_RESUME_FLOOR_SESSION`, `H5_RESUME_FLOOR_SESSION`); the H10a
  adjudication marker lives at module scope in the watcher, NOT in config
  (review FX-3). No other config changes; in particular
  `config.py:321-322` (`H5_ENTRY_TRIGGERS`, `H5_ENTRY_IVR_MAX`) are frozen
  HISTORY and must NOT be deleted or renamed — only their evaluation/output
  is disabled (seq 29 clause 1: retired triggers "remain on the append-only
  record as history"; review FX-5).
- No changes to `data/schwab_adapter.py`, `schwab_chain_capture.py`
  (read-only consumer), `tests/test_schwab_chain_view.py:222,233` (guard
  tests), `hypothesis_evidence.py`'s `_HYPOTHESIS_ORDER`
  (`hypothesis_evidence.py:93` — it feeds H5–H8 rollups outside this scope),
  or `h7_scope.watch_universe` (review BL-1/BL-3/scope-gap items).
- No live-order paths; no authority flips; no paper-book writes; no network
  in tests.

## Work packages

- **WP-A — H10a CLOSED guard (closes amendment BL-B; test per seq 28 clause
  3(a) VERBATIM, review FX-1).** In `options_researcher/h10_watch.py`
  (signals computed for both hypotheses at `h10_watch.py:145-146`; only
  suppression today is window-end at `h10_watch.py:83-92`; note
  `config.py:613` `H10A_WINDOW_END = "2026-10-06"` is still in the future,
  so this is a LIVE path): add a module-scope ADJUDICATED marker for H10a
  (comment cites the `H10A_RESULT` fact, ratified 2026-08-15 / appended
  2026-08-16) such that the watcher never evaluates or records H10a in any
  mode. Test obligation, red-green, through the REAL watcher path (not an
  isolated helper): run the watcher for a session inside H10a's old window
  and assert BOTH zero H10a evaluation AND zero write to any H10a record.
- **WP-B — namespaced H10b store, receipt schema, union reader (closes
  BL-B/NEW-1; review BL-3 + FX-6).**
  - Post-resumption H10b observations go to
    `reports/h10/h10b_observations.jsonl` with a per-row `hypothesis`
    field. CAUTION: `h10_observe.py:28-34` `_OBSERVATION_FIELDS` is
    enforced as an EXACT field set by `_validate_existing`
    (`h10_observe.py:171-175`) — the legacy store's validation must keep
    accepting legacy rows; give the new store its own schema/validator
    rather than widening the legacy one.
  - `reports/h10/observations.jsonl` becomes read-only history. The ritual
    currently invokes the appender unconditionally
    (`tools/daily_ritual.sh:390`) — re-point that invocation; the
    no-append test must drive the real recording path (not a grep), e.g.
    run a post-floor session end-to-end and assert the legacy file's bytes
    are unchanged.
  - RECEIPT schema (review BL-3): receipts carry
    `"signals": {"H10a": ..., "H10b": ...}`;
    `hypothesis_evidence.py:787-791` asserts the exact key set AND that
    every value is `None` or `bool` — a string marker like `"ADJUDICATED"`
    makes the whole receipt malformed and collapses H10b's evidence row to
    UNKNOWN (`hypothesis_evidence.py:815-833`, consumed per family at
    `:1311-1323`). Post-resumption receipts therefore emit
    `"H10a": None` (type-legal "not evaluated") plus a separate
    discriminator field (e.g. `"h10a_status": "ADJUDICATED"`), with a test
    that the evidence layer still renders H10b correctly.
  - UNION READER + hole disclosure (seq 28 clause 3, review FX-6): H10b's
    record is the union of the pre-starvation receipts (4 rows in the
    legacy store, sessions 2026-07-23/24/27/28, receipts
    `reports/h10/receipts/h10_watch_*.json`) and the new store; any
    consumer/rollup reads both and stamps the permanent
    2026-07-29→first-capture hole; nothing interpolated. Test: union view
    returns 4 legacy + N new rows with the hole disclosed.
  - COVERAGE assertion (seq 28 clause 2): test that
    `config.py:391-392` H7_WATCHLIST (11 names, consumed at
    `h10_watch.py:485`) is a subset of
    `schwab_chain_capture.watch_universe()` (15 names) so drift can't
    silently starve names.
- **WP-C — no-backfill floors bound to the EVALUATION session (closes BL-C;
  review BL-2 + FX-4).** `h10_watch.py:428-449` refuses only FUTURE
  `--as-of` dates, and `as_of` is a RUN date whose evaluated session is the
  prior completed one (`h10_watch.py:451` → `evaluation_session()` at
  `h7_watch.py:236`; receipt stamps `"as_of": run_date` at
  `h10_watch.py:531`). The floor MUST bind `eval_iso` (the session actually
  evaluated/recorded), not the CLI argument — otherwise a run at exactly
  the floor records the pre-floor session. Add `H10B_RESUME_FLOOR_SESSION`
  / `H5_RESUME_FLOOR_SESSION` to `config.py`. Resolution procedure (review
  FX-4 — Codex cannot know the merge date): set both to the first NYSE
  session ON OR AFTER the day this brief's PR is opened (ET basis), with a
  provenance comment "mechanical floor per seq 28/29 clause 5; append date
  2026-08-18 ET; updated at merge by the orchestrating session if the merge
  lands later"; the orchestrating session verifies/updates the value at
  merge BEFORE the lane is enabled. Enforcement pattern: the brief-14
  `dryrun/` quarantine pattern — refusal in the real path plus tests on
  both sides of the boundary ASSERTING ON THE EVALUATED SESSION, not the
  CLI date.
- **WP-D — Schwab source adapter (timing per seq 28 clause 2; IV units per
  the correction, seq 30).** Three legs stated explicitly (review FX-2):
  (1) SIGNAL on completed-session OHLCV — `_load_adjusted`
  (`h10_watch.py:99-103`) → `_signals_at_session`; unchanged. (2) SPOT =
  `_load_raw`'s official close (`h10_watch.py:105-109`, consumed at
  `h10_watch.py:321`); do NOT substitute
  `schwab_chain_view.load_preclose_spot` (`schwab_chain_view.py:270`) —
  that would silently move the strike band at `h10_watch.py:167-171`.
  (3) ADMISSION (>=5 NTM monthly contracts, spread<=5 pct, OI>=100 — seq
  16, unchanged), contract selection (delta 0.40–0.60 within ±10% of the
  official-close spot), and FILL pricing from the newest VERIFIED 15:45
  preclose capture; missing/partial/failed-verification capture ⇒ session
  skipped + logged (fail-closed). IV units: the store's `iv` is ALREADY
  decimal — consume as-is, NO division; named test: a fixture capture with
  known IV proves the H10b/H5 path consumes it unscaled and contains no
  second ÷100. Every output row stamps the mixed-timing convention
  (close-based spot vs 15:45 chain) per seq 28 clause 2.
- **WP-E — H5 observer (seq 29 clauses 1–2; review FX-5/FX-6).** Universe =
  exactly the keys of `config.py:321` `H5_ENTRY_TRIGGERS` ({VST, AMZN}) —
  no expansion. Per name, record price, capture availability, and the count
  of finite single-source Schwab IV observations toward the 126 needed for
  a computable IV rank (`features.py:25` `PCT_MIN_OBS = 126`). NO fire
  path: trigger evaluation is hard-disabled with a test proving no FIRE
  output can be produced — while `config.py:321-322` themselves REMAIN
  (frozen history; see OUT). Note the real rework surface: the IV-rank
  input today is `_exact_iv_rank` (`entry_watch.py:115-133`) reading the
  attractiveness feature store, and `entry_watch.py:136-137` `_chain_edge`
  provides only a context line from hardcoded `.cache/chains/` paths — the
  observer replaces both reads with the Schwab capture, no
  ThetaData/Schwab IV splicing anywhere. Every observer output is labeled
  **observational / non-verdict-bearing** (seq 29 clause 2 wording) and
  stamps its max as-of session.
- **WP-F — ritual wiring incl. prose retirement (seq 29 clause 1; review
  FX-5).** In `tools/daily_ritual.sh`: route H10b + the H5 observer
  through the Schwab-lane branch per the owner-confirmed D-1=F1 override
  (H10b and H5 watch ONLY; H6/H8 stay paused — the `h10_watch`/`h10_observe`
  invocations at `:388-395` and the H5 step-4b block). The step-4b banner
  and messages (`tools/daily_ritual.sh:351,364-373`) currently print
  trigger prose ("H5 ENTRY TRIGGER FIRE …", "WAIT (no trigger fired)") —
  replace with observe-mode wording; the ledger says the trigger is
  retired and the ritual must not contradict it. Fail-closed: no verified
  capture ⇒ skip + visible log line.

## Acceptance / verification

- `uv run python -m unittest discover -s tests` exit 0 (offline; no network).
- `uv run ruff check . && uv run pyright` exit 0.
- Proof tests, each through the REAL execution path (no isolated-helper
  vacuity): WP-A red-green closed-trial run; WP-B no-legacy-append
  end-to-end + receipt-type + union-with-hole + coverage-subset; WP-C floor
  boundary both sides asserting the evaluated session; WP-D IV-unscaled
  fixture + spot-source; WP-E no-FIRE-possible + label presence; WP-F
  observe-mode prose.
- `uv run python tools/irreplaceable_data_guard.py verify` exit 0 before any
  branch cleanup.
