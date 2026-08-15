# Brief 12 — Schwab display freshness: scanner + QM unfreeze on verified pre-close captures

**Date:** 2026-08-14 (late). **Status:** DRAFT SPEC for immediate implementation.
**Authorization:** owner-directed in-session 2026-08-14 (~22:15 ET), recorded in
`reports/2026-08-14-schwab-freshness-owner-directive.md`. Owner wording: "scope
and implement the charles schwab implementation path as well as fix the
dashboard for the newest data … and unfreeze all gates that can be unfrozen
for example the qm and other ideas. i dont care abt et and usar just all the
other tickers i cached for."
**Executor:** Opus implementation agent. **Review:** independent adversarial
review required before merge (house rule).
**Ground truth measured 2026-08-14 ~22:20 ET** by two read-only scouts against
`origin/main = 175f9ca` (worktree gracious-neumann-d938c9) and the ops data
root. All line numbers below are 175f9ca line numbers.

---

## 1. Goal and honest meaning

The attractiveness board and QM context currently block on staleness because
their only quote source is `.cache/chains` (ThetaData EOD, frozen at
2026-07-27, refill forbidden by OD-2/OD-4). A second, fresher, verified quote
namespace now exists: `.cache/schwab_chains/` (15:45 pre-close full-chain
captures, manifest-verified, write-once, currently one session: 2026-08-14).

"Unfreeze" means: give the display layer a READ path to the newest VERIFIED
Schwab session so the existing staleness gates see fresh data and stand down
on their own. **No gate is deleted, loosened, or re-thresholded.** Every
consumer of the new path labels its data "15:45 pre-close (Schwab)" — never
as an EOD close. Display-only: nothing here is verdict-bearing, FIRE-capable,
or a registered signal; no hypothesis watcher input changes.

## 2. Hard constraints (each traces to a measured fact)

- **C1 — ZERO `config.py` changes.** `intraday_preview.py:81-82` hard-fails on
  `config_hash` drift vs the receipts on disk; no new capture receipts arrive
  until Monday 09:31, so ANY config edit kills the live-dashboard intraday
  panel for the whole weekend. Additionally
  `tests/test_ritual_switch_on_hash_containment.py` freezes the config
  uppercase-name set. All new fixed values land as module-level literals with
  provenance comments (precedent: `schwab_chain_capture.py:42-44`).
- **C2 — never write `.cache/chains`** (OD-2/OD-4: no refill, ever). The new
  path is a read-time view, not a cache merge.
- **C3 — verified sessions only.** Chains are consumed ONLY for sessions where
  `tools.schwab_chain_manifest.verify_session(session, symbols, chain_dir,
  manifest_path, receipt_path)` succeeds (it already enforces
  `receipt["force"] is not False`, universe equality, sha256, row counts,
  preclose timing — `tools/schwab_chain_manifest.py:139-247`). Verify once per
  session per process, not per symbol.
- **C4 — IV unit conversion at the boundary.** Schwab-store `iv` is PERCENT
  POINTS (e.g. 59.57637); every display consumer expects decimals. Divide by
  100.0 in the view; assert it in a test with a real-magnitude fixture.
- **C5 — contract hygiene.** Drop rows with `non_standard == True` or
  `mini == True` in the view (the ThetaData cache is standard contracts only).
- **C6 — owner name scope.** `DISPLAY_EXCLUDED_SYMBOLS = frozenset({"ET",
  "USAR"})` (module literal, provenance comment "owner-directed in-session
  2026-08-14"). Applies to the NEW read path and board rendering only; the
  registered H7 cohort and `watch_universe()` are untouched.
- **C7 — no network at render.** The dashboard build reads local parquet only.
  The one network step (QM OHLCV top-up via the already-ratified Yahoo lane)
  runs as its own explicit CLI invocation, never inside `assemble()`/render.
- **C8 — offline unittest**, fixtures for the Schwab store; suite + ruff +
  pyright green; every new guard gets a mutation-style red test.
- **C9 — landing regime.** All touched Python is inside
  `diagnostic_source_hash` (options_researcher/). Per brief 11 §11 regime 1
  this is safe now (the six refusal sites sit behind `require-full`, off);
  do not land while a ritual run is in flight.

## 3. Measured facts the implementation builds on

**Schwab store** (`options_researcher/schwab_chain_capture.py:42-63`):
`.cache/schwab_chains/{SYM}_{YYYY-MM-DD}.parquet`, columns `expiration(str),
strike(f64), right(C/P), contract_symbol, bid, ask, open_interest(i64),
iv(PERCENT), delta, gamma, theta, vega, multiplier, non_standard(bool),
mini(bool), timestamp, trade_timestamp`. Receipts
`reports/schwab_chains/<session>/preclose.json` + `manifest.json`;
`session_chain_convention = "preclose_snapshot_v1"`. One session exists
(2026-08-14, 15 symbols, e.g. NVDA 3794 rows / 23 expirations). No spot price
in this lane's receipt; spot for display comes from the intraday receipt
(`reports/intraday_capture/<date>/preclose.json`, per-name `spot_mid`,
`spot_source`, force-refusal precedent `intraday_preview.py:71-72`).

**Board data path:** `attractiveness_dashboard.py:1050-1057` `_gather_all()`
literal-globs `.cache/chains/{sym}_*.parquet`, session = newest filename date;
CLI twin `attractiveness.py:443-449`. Chain read `:1101`. Feature store
`.tmp/research/attractiveness` (`features.py:91`), newest row at-or-before
chain day (`attractiveness_dashboard.py:1106-1113`), `features_stale =
features_as_of != day` (`:1248-1249`). Page-level `data_as_of` = EARLIEST
section as_of across non-display-only symbols (`:725-731`, `:956-963`).
Staleness banner `_chain_age_html:752-790`; card-level gate
`top3_snapshot.py:121-135` (`CHAIN_STALE_VS_TODAY` at `age >=
config.CHAIN_STALE_BLOCK_SESSIONS`, plus `FEATURES_STALE` and friends);
liquidity via `data/chain_policy.py:48-57` (`MIN_OPEN_INTEREST=100`,
`MAX_SPREAD_PCT=0.10` — unchanged).

**QM path:** `qm_dashboard.py` — sidecar `reports/qm_context/2026-07-14.json`
(sha-sealed to the frozen study, `:32-85`); coverage check
`_frozen_symbol_or_block:125-135`; **all-or-nothing aggregation**:
`refresh_qm_ohlcv:418-424` sets board `DATA_BLOCKED` if ANY
`watch_universe()` symbol is not CURRENT; panel gate
`_qm_context_block_reason:324-359` requires `qm_context.as_of ==
data_as_of` and every displayed non-display-only symbol CURRENT. Sidecar
coverage today: ET absent; IREN and USAR `NOT_IN_FROZEN_STUDY`; other 12
CURRENT. OHLCV cache `.cache/underlying_ohlcv` ends 2026-08-13 (tonight's
ritual refreshed to its evaluation session).

## 4. Deltas (complete; nothing else changes)

| # | File | Change |
| --- | --- | --- |
| D1 | **NEW** `options_researcher/schwab_chain_view.py` | The one boundary module. `verified_sessions() -> list[str]`: glob `reports/schwab_chains/*/preclose.json`, canonical-date parents only, run `verify_session` per session (in-process memo), return ascending verified sessions; verification failure = session simply absent (log-line, fail-closed). `load_chain(symbol, session) -> pd.DataFrame`: read the store parquet, drop `non_standard`/`mini`, select+rename to the display schema (`expiration, strike, right, bid, ask, open_interest, iv, delta`), `iv = iv / 100.0`, `open_interest` as int. `newest_chain(symbol) -> (frame, session) | None`: newest verified session containing the symbol; returns None for `DISPLAY_EXCLUDED_SYMBOLS`. Module literals: `CHAIN_DIR`, `REPORTS_DIR` (mirror `schwab_chain_capture.py:42-43`), `DISPLAY_EXCLUDED_SYMBOLS`, `CONVENTION_LABEL = "15:45 pre-close (Schwab)"`. |
| D2 | `attractiveness_dashboard.py` `_gather_all` + `attractiveness.py` gather twin | Per symbol: newest ThetaData filename date vs `newest_chain()` session; consume the newer; record `chain_source` (`"thetadata_eod"` / `"schwab_preclose"`) on the section and thread it to card meta. As-of surfaces for schwab-sourced sections render the session WITH the convention label (C4 of brief 11's timing-semantics concern): "2026-08-14 · 15:45 pre-close (Schwab)". |
| D3 | `attractiveness_dashboard.py` page banner | `_page_data_as_of`/`_chain_age_html` become source-aware: the single-date model is replaced by a two-line freshness statement — fresh-source line ("option quotes: 15:45 pre-close (Schwab) session <S> for <N> names") and, when any rendered name still rides the frozen cache, the existing stale-warning line scoped to those names. The card-level `CHAIN_STALE_VS_TODAY` gate is UNCHANGED — stale-source cards keep blocking; the page banner stops letting the stalest name misdescribe the freshest. `data_as_of` (used by QM coupling and annotations) becomes the newest fresh-source session when one exists, else the old min. |
| D4 | `features.py` | `build_all` gains schwab-session awareness: for sessions newer than the ThetaData edge, build the per-session feature row from the D1 view frame (same feature computations; history series = ThetaData sessions + verified schwab sessions, gap tolerated and recorded). Feature rows carry a `source` value so nothing pretends the 07-28..08-13 hole doesn't exist. If a specific feature is honestly uncomputable across the gap, it is null — never interpolated. |
| D5 | `qm_dashboard.py` | (a) Aggregation goes per-name: `refresh_qm_ohlcv` and `_qm_context_block_reason` treat sidecar-uncovered symbols (`NOT_IN_FROZEN_STUDY` / absent) as per-name `NOT_COVERED` display states rather than board-level blockers; board `DATA_BLOCKED` only when a COVERED, displayed, non-excluded name fails. Precedent: H7 amendment v1.4 per-name source health. The frozen sidecar file and its sha bindings are UNTOUCHED. (b) The refresh/target session follows the board's fresh `data_as_of` so OHLCV-ends-exactly-on-session can hold. ET/IREN/USAR render as excluded/not-covered lines, never silently dropped. |
| D6 | Tests | New `tests/test_schwab_chain_view.py` (fixture store + receipts + manifest built by the test; real-magnitude iv fixture asserting /100; forced receipt refused; tampered sha refused; non_standard/mini dropped; ET/USAR return None). Extend attractiveness/QM tests: newer-source selection, convention label present on schwab cards, page banner two-line honesty, per-name QM aggregation (covered renders while IREN says NOT_COVERED), `FEATURES_STALE` clears when a schwab-session feature row exists. Mutation-style reds: remove the verify_session call → test fails; skip iv conversion → test fails; drop the convention label → test fails. |
| D7 | Docs | `docs/provider-transition.md`: record this display lane as Phase-A of the Schwab path; Phase-B (hypothesis-input amendments) and Phase-C (S1 flip ≥ 2026-08-19 + registration) listed as owner-gated future work. |

## 5. What this spec explicitly does NOT do

- No `config.py` line (C1). No `.cache/chains` write (C2). No change to
  `watch_universe()`, `ATTRACTIVENESS_UNIVERSE`, any registered universe, the
  frozen QM sidecar/study bindings, `h7_*` modules, ledger paths, or the
  ritual/authority modules landed earlier tonight.
- No hypothesis watcher reads Schwab data (that is Phase-B: per-hypothesis
  registered-input amendments under the 2026-07-25 delegation with their own
  adversarial review).
- No flip of `exact_session_source_active` (S1 bar: three consecutive
  verifying sessions; earliest ≈ 2026-08-19) or `h7_active`.
- No closes-store (`.cache/underlying`) unfreeze (drill disposition A/B is
  owner-open). No `SHORT_CONTEXT_ENABLED` change (config value ⇒ C1 trap).

## 6. Acceptance smoke (after merge + ops sync, manual)

Run in ops: `uv run python -m options_researcher.qm_dashboard --as-of
2026-08-14 --refresh-ohlcv` (ratified Yahoo lane, explicit invocation), then
`uv run python -m options_researcher.attractiveness_dashboard`. Expect:
13 names on Schwab pre-close 2026-08-14 with the convention label; no
14-session STALE banner for those names; ET/USAR absent from the fresh path;
QM context CURRENT for the 12 covered names with IREN/USAR/ET shown as
not-covered; liquidity gates still filtering (some cards will remain
WATCH/PLAN_ONLY — that is policy, not staleness); annotations notice may
remain (research context is 2026-07-24 — separate refresh lane).
