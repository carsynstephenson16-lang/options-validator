# Brief 12 (rev-2) — Schwab display freshness: scanner + QM unfreeze on verified pre-close captures

**Date:** 2026-08-14 (late; rev-2 same night). **Status:** implementation-ready.
rev-1 received an independent adversarial audit with verdict **FAIL** (11
blockers, 10 cautions) and an implementer stop-report (2 blockers, both
duplicated by the audit). Every finding is resolved below; the audit's
fact-check table stands as the measurement record.
**Authorization:** owner-directed in-session 2026-08-14, recorded in
`reports/2026-08-14-schwab-freshness-owner-directive.md` and (spot ruling,
option A) in-session by the orchestrator; owner menu answers in
`reports/2026-08-14-owner-answers-decision-menu.md`.
**Executor:** Opus implementation agent. **Review:** independent adversarial
review of the implementation before merge.
**Ground truth:** origin/main `175f9ca`; audit-verified line numbers.

## rev-1 → rev-2 change log (finding → disposition)

| Finding | Disposition |
| --- | --- |
| Audit B1 / impl-B1: iv already decimal | C4 inverted: PASS-THROUGH, no conversion; decimal-assertion test + mutation red for a spurious /100 (`data/schwab_adapter.py:148-154` is the provenance cite) |
| Audit B2 / impl-B2: stale close under fresh chains (drift to +25.7%) | NEW D2b: section `close` for schwab-sourced sections comes from the intraday preclose receipt `spot_mid`, with `close_as_of` + `close_kind="preclose_mid_1545"` threaded and labeled; own gate (receipt `status=="ok"`, `force is False`, `spot_source=="stock_snapshot"`, session match) else the section REFUSES to render fresh (falls to stale path with visible reason) |
| Audit B3: NaN→0.0 coercions turn nulls into GREEN | NEW D4a precondition: `attractiveness_dashboard.py:1119-1122` fail-closed — a NaN `iv_rank`/`iv_minus_rv`/`rv21` renders "unavailable (no closes past 2026-08-04)" and the affected badge shows UNKNOWN (never GREEN/default-0.0); scenario tables state why they are absent instead of vanishing |
| Audit B4: D4 wrote the store H5's `entry_watch` reads | D4 REDESIGNED: the on-disk feature store `.tmp/research/attractiveness` is NEVER written by this brief. Schwab-session feature values are computed IN-MEMORY at gather time into the section (source-tagged), satisfying the snapshot's date checks without a store row. `entry_watch`/`live_quotes`/`rq1_runner` inputs stay byte-identical; a test asserts `build_all` output dirs untouched by a schwab-session dashboard build |
| Audit B5+B6: data_as_of=08-14 re-freezes QM; same-day OHLCV impossible (`_drop_same_day_ohlcv`) | D5 REDESIGNED: QM panel DECOUPLES from the board chain session. QM targets its own session = newest OHLCV-complete session (chain session − 1 on capture days, structural), rendered with an explicit two-date label ("QM daily-bar context as of <S-1>; board chains 15:45 pre-close <S>"). `_qm_context_block_reason` compares against QM's own target, not `data_as_of`. rev-1's "refresh follows data_as_of" is DELETED as structurally impossible |
| Audit B7: "Market close" chip lie; mission-control divergence | D3 extended: header chip becomes source-aware ("Pre-close 15:45 (Schwab) 2026-08-14" vs "Market close <date>"); pinned tests at `tests/test_attractiveness_dashboard.py:387,396,424` amended (not weakened — they pin the NEW honest literals). Mission control (`dashboard.py:627`) is OUT OF SCOPE tonight and keeps its own honest closes-derived date; the attractiveness page footer notes the two artifacts date independently |
| Audit B8: five all-or-nothing QM gates, wrong file for one | D5 enumerates all five: `qm_dashboard.build_qm_context:268-287`, `qm_dashboard.refresh_qm_ohlcv:418-424`, `qm_dashboard.main:445`, `attractiveness_dashboard._qm_context_block_reason:324-359` (CORRECT FILE), `attractiveness_dashboard.select_qm_top_picks:420-432` |
| Audit B9: verify_session universe mismatch = silent total no-op | D1 states: verification uses the CAPTURED universe (read `manifest["symbols"]` first, verify with exactly that list); `DISPLAY_EXCLUDED_SYMBOLS` applies strictly AFTER verification. A universe-change session verifies against its own manifest |
| Audit B10: invisible verification failure; receipts ops-only | D1+D3: three distinguishable page-level states — "no Schwab receipts found" / "session <S> FAILED verification: <reason>" (loud, with the error) / verified-fresh. Never a silent fallback. The ops-only-receipts fact is recorded in D7 docs as an open ops follow-up (receipt tracking), not silently absorbed |
| Audit B11: gamma/theta/vega dropped | D1 schema keeps `gamma, theta, vega` (native in the store); parity with the ThetaData frame asserted in a test |
| Impl finding: D5 missed `build_qm_context` | folded into B8 disposition |
| Cautions 1,2,5,6,7,8,9,10 | see §5 dispositions |

## 1. Goal (unchanged) and honest meaning (sharpened)

Give the display layer a read path to the newest VERIFIED Schwab pre-close
session so staleness gates stand down by seeing fresh data. No gate deleted
or loosened. A pre-close snapshot is never presented as a close: every date
surface (banner, header chip, card meta, close field) carries the
`preclose_snapshot_v1` semantics explicitly. `h7_watch.py:236-246`'s
invariant ("an intraday snapshot must never masquerade as a close") is
honored by LABELING every surface, not by pretending the data is EOD.

## 2. Hard constraints (rev-2)

- **C1** zero `config.py` changes (weekend `config_hash` trap,
  `intraday_preview.py:81`; hash-containment test). Unchanged.
- **C2** never write `.cache/chains`; **and never write
  `.tmp/research/attractiveness`** (H5 registered input path — audit B4).
- **C3** consume only `verify_session`-verified sessions, verified with the
  manifest's own symbol list; verification failure is page-visible.
- **C4** Schwab `iv` is ALREADY DECIMAL (`data/schwab_adapter.py:148-154`
  converts at capture). Pass through unchanged; test asserts a
  real-magnitude fixture value survives untouched; mutation red for any
  conversion.
- **C5** drop `non_standard`/`mini` rows (cheap invariant; all-False today).
- **C6** `DISPLAY_EXCLUDED_SYMBOLS = frozenset({"ET","USAR"})`
  (owner-directed 2026-08-14): excluded from the FRESH path only; on the
  board they keep their existing stale-path rendering (visible, blocked) —
  never silently dropped. Reconciles rev-1's C6/D5 contradiction.
- **C7** no network at render. QM's OHLCV refresh remains an explicit CLI
  step targeting QM's OWN session (chain session − 1); no circular
  dependency on `assemble()`.
- **C8** unittest offline; suite+ruff+pyright green; mutation-style reds.
  The ~15 pinned assertions the audit enumerated
  (`tests/test_qm_dashboard.py:111,169,241-311,329-332,353,411,443,450-455`;
  `tests/test_attractiveness_dashboard.py:387,396,424,775-781,854-860,1601,
  1604-1610,1768-1803`) are REWRITTEN to pin the new honest literals — never
  deleted, never weakened to substring-less forms.
- **C9** hashed-surface landing rules unchanged (brief 11 §11 regime 1); do
  not touch `tools/daily_ritual.sh` (its `--as-of`/invocation lines are
  pinned by frozen-order tests; QM's ritual step is UNCHANGED tonight).

## 3. Measured facts

rev-1 §3 as corrected by the audit's fact-check table (which is authoritative
where they differ): iv decimal; `_qm_context_block_reason` lives in
`attractiveness_dashboard.py:324-359`; OHLCV ends 2026-08-13 for the 12
covered names and 2026-08-03 for ET/IREN/USAR; `top3_snapshot.integrity_status`
spans `:95-140` including `FEATURES_SESSION_MISMATCH:113-114`; closes store
ends 2026-08-04; intraday preclose receipt has `spot_mid`/`spot_source` for
all 15 names; `reports/schwab_chains` exists only in the ops checkout;
`ATTRACTIVENESS_UNIVERSE` = 18 names (15 H7 + NBIS/AMAT/CLSK display-only).

## 4. Deltas (complete)

| # | File | Change |
| --- | --- | --- |
| D1 | NEW `options_researcher/schwab_chain_view.py` | `verified_sessions()`: glob `reports/schwab_chains/*/preclose.json`; per session read `manifest.json`, call `verify_session(session, manifest["symbols"], …)`; memo keyed on (cwd, session) — never across a cwd change (audit caution 8). Returns `(sessions, failures)` where failures carry `(session, reason)` for page display. `load_chain(symbol, session)`: drop `non_standard`/`mini`; columns `expiration, strike, right, bid, ask, open_interest, iv, delta, gamma, theta, vega`; iv PASS-THROUGH; OI int. `newest_chain(symbol)`: newest verified session containing symbol; None for `DISPLAY_EXCLUDED_SYMBOLS`. `load_preclose_spot(symbol, session)`: minimal reader of `reports/intraday_capture/<session>/preclose.json` — requires per-name `status=="ok"`, top-level `force is False`, `spot_source=="stock_snapshot"`, finite `spot_mid`; returns `(spot_mid, spot_ts)` or None; does NOT validate `config_hash` (display-only reader; C1 trap) and says so in its docstring. Module literals with provenance comments. |
| D2 | `attractiveness_dashboard.py` `_gather_all`/`_gather_symbol` + `attractiveness.py` twin | Per symbol: newer of (ThetaData filename date, newest verified schwab session). Schwab-sourced sections REQUIRE `load_preclose_spot` success; on failure the symbol stays on the stale path with a visible per-card reason ("no verified 15:45 spot — fresh chain not rendered"). Section gains `chain_source`, `close_as_of`, `close_kind`. |
| D2b | same | For schwab sections: `close` = receipt `spot_mid`; every renderer of the close (stat line `:2945-2946`, risk_economics, scenario/bbb inputs) shows "spot 15:45 pre-close" wording via `close_kind`, and `close_as_of` equals the chain session (same instant — the one internally consistent pairing on the board). |
| D3 | same | Page banner: three-state (verified-fresh line with names count / stale line for stale-path names / verification-FAILURE notice with reason). Header chip source-aware ("Pre-close 15:45 (Schwab) <S>" vs "Market close <D>"). `data_as_of` = newest fresh session when ≥1 fresh section exists (else old min); consumers threaded: `_research_html` date-equality (07-24 annotations will show the honest stale notice — expected), `load_qm_context` DECOUPLED (D5), `load_context`, `tools/research_context_assemble.py:61-63,147` re-verified coherent and covered by a test. `display_data_as_of` (NBIS/AMAT/CLSK lane, `:964-966`) unchanged — two-dated board is honest and labeled (audit caution 9). |
| D4a | `attractiveness_dashboard.py:1119-1122` | PRECONDITION: NaN `rv21`/`iv_rank`/`iv_minus_rv` → explicit "unavailable" states; badges UNKNOWN (grey), never default-0.0/GREEN; scenario/bbb sections render an absence line naming the missing input and its edge date. Mutation red: restoring `else 0.0` fails a test. |
| D4b | same, gather path | Schwab sections compute IN-MEMORY per-section features: `atm_iv` from the fresh chain (0.50-delta convention matching `features.py`), `iv_minus_rv`/`rv21` = unavailable (closes end 08-04; D4a renders that honestly), `iv_rank` = receipt `iv_rank_preview` when present, labeled "preview (capture-lane calibration)", else unavailable. Snapshot date-integrity fields set so `FEATURES_SESSION_MISMATCH`/`FEATURES_STALE` reflect truth (feature values ARE from the session; the unavailable ones say why). The on-disk store is untouched — test asserts no write under `.tmp/research/attractiveness` during a schwab-session build. |
| D5 | `qm_dashboard.py` + `attractiveness_dashboard.py` | Per-name aggregation across ALL FIVE gates (files per change log). QM targets its own newest OHLCV-complete session; panel shows the two-date label; covered names render CURRENT at QM's session; ET/IREN/USAR per-name NOT_COVERED lines; board-level DATA_BLOCKED only when a covered displayed name fails at QM's own session. `qm_dashboard.main` exit semantics preserved for the ritual (its step/wording untouched — C9). |
| D6 | Tests | Everything in C8 plus: decimal-iv fixture; spurious-/100 mutation; verification-failure page notice; universe-from-manifest verification; ET/USAR fresh-path exclusion with stale-path presence; no-store-write assertion; `close_kind` labeling; NaN fail-closed reds; QM two-date decoupling; five-gate per-name behavior; `research_context_assemble` coherence. Hermetic git/receipt fixtures. |
| D7 | Docs | `docs/provider-transition.md` Phase-A/B/C paragraph + open follow-ups: `reports/schwab_chains` tracking question (ops-only today), `CHAIN_STALE_*` thresholds still LLM-asserted/owner-unconfirmed, 2-session freshness runway note (captures are daily; Monday extends it). |

## 5. Caution dispositions

(1) `iv_rank` cross-provider percentile: AVOIDED — D4b uses the receipt's
preview rank or shows unavailable; the store's ThetaData series is never
mixed with Schwab observations. (2) `BACKTEST_END` default: moot — `build_all`
is not invoked for schwab sessions. (5) test rewrites enumerated in C8.
(6) resolved in C6. (7) resolved by D5's decoupling. (8) memo keyed on cwd.
(9) two-dated board labeled. (10) thresholds disclosure in D7.

## 6. What this brief still does NOT do

rev-1 §5 unchanged (no config, no `.cache/chains` write, no watcher inputs,
no flag flips, no closes unfreeze) PLUS: no on-disk feature-store writes, no
`tools/daily_ritual.sh` edits, no mission-control (`dashboard.py`) changes.

## 7. Acceptance smoke (ops, after merge + R1)

`uv run python -m options_researcher.attractiveness_dashboard` only (no QM
refresh needed for the board; QM panel self-targets 08-13 which is already
complete). Expect: 13 names fresh at "Pre-close 15:45 (Schwab) 2026-08-14"
with receipt spots; ET/USAR on the stale path, visible; QM panel CURRENT for
12 covered names at its own 2026-08-13 label; NaN-derived badges UNKNOWN
with reasons; liquidity/policy gates unchanged (WATCH/PLAN_ONLY expected);
annotations stale-notice expected. In a non-ops checkout: the explicit
"no Schwab receipts found" page state, not silence.
