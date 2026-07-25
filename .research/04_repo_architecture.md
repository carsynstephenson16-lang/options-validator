# Repository architecture map — for adding ONE new scanner signal

- **Research cutoff / run date:** 2026-07-24
- **Scope:** read-and-map only. No refactor proposals. RAG layer, agent
  configuration, and UI visual hierarchy are explicitly out of scope per the
  task brief.
- **Evidence standard:** every claim below is Repo-verified with a file path
  and symbol/line. Where I could not verify something, it is listed under
  "Not found" at the end of the relevant section.

---

## 1. Market-data ingestion (equity/underlying prices)

- **ThetaData terminal/API access lives in `data/thetadata_adapter.py`.**
  `_client()` (`data/thetadata_adapter.py:136`) resolves the API key via
  `_resolve_api_key()` (`data/thetadata_adapter.py:118`, env vars
  `THETADATA_API_KEY` / `THETA_DATA_API_KEY`, `data/thetadata_adapter.py:112`)
  and builds a client — this repo's ThetaData path is a direct keyed HTTP
  call to the remote MDDS, not a local `ThetaTerminal` process (confirmed by
  `tools/daily_ritual.sh:50-54`, comment: "PATH C ... uses a direct API key
  over HTTP ... NO local ThetaTerminal process").
- **EOD option-chain fetch:** `_fetch_raw` (`data/thetadata_adapter.py:177`),
  `_fetch_merged_chain` (`data/thetadata_adapter.py:294`),
  `get_eod_chain(symbol, date, *, allow_oos=False)`
  (`data/thetadata_adapter.py:319`). Chain schema is validated by
  `validate_chain_schema` (`data/thetadata_adapter.py:88`) against
  `CHAIN_COLUMNS` / `NUMERIC_CHAIN_COLUMNS` (`data/thetadata_adapter.py:49,54`).
- **Underlying (equity) closes are NOT fetched from ThetaData** in the
  researched path — `data/underlying_closes.py` fetches from AlphaVantage
  (`fetch_underlying_eod_av`, `data/underlying_closes.py:163`, using
  `AV_QUERY_URL`, `data/underlying_closes.py:146`) and from Yahoo
  (`fetch_underlying_eod_yahoo`, `data/underlying_closes.py:260`, using
  `YAHOO_CHART_URL`, `data/underlying_closes.py:190`), plus a manual
  unsplit/adjustment table `SPLITS` (`data/underlying_closes.py:203`).
  `load_closes` / `load_closes_adjusted` (`data/underlying_closes.py:44,86`)
  read the local cache (`CACHE_DIR = ".cache/underlying"`,
  `data/underlying_closes.py:21`); `adjustment_factor` /
  `adjusted_from_raw` (`data/underlying_closes.py:62,73`) apply splits.
- **Parity-derived spot** (used when the live stock feed is not entitled):
  `parity_spot_from_chain(chain, today_iso, ...)`
  (`data/underlying_closes.py:289`) and `build_parity_closes`
  (`data/underlying_closes.py:321`) derive an underlying price from
  put-call parity on the option chain itself rather than a stock quote.
  `options_researcher/live_quotes.py` imports and calls this at
  `_symbol_preview_live` (`options_researcher/live_quotes.py:501-526`): when
  `stock_entitled` is False, it fetches the nearest-monthly option snapshot
  (`client.option_snapshot_quote`) and calls
  `parity_spot_from_chain(chain_like, ny_iso)`
  (`options_researcher/live_quotes.py:519-522`) instead of a stock quote.
- **Stock endpoints the code assumes are NOT entitled on the current tier:**
  `options_researcher/live_quotes.py` treats `client.stock_snapshot_quote`
  as possibly-denied. `run_probe` (`options_researcher/live_quotes.py:276`)
  records `probe["stock_entitled"] = bool(stock_res["ok"])`
  (`options_researcher/live_quotes.py:324`) from calling
  `client.stock_snapshot_quote(list(config.UNIVERSE))`
  (`options_researcher/live_quotes.py:294-296`). `probe_ok`
  (`options_researcher/live_quotes.py:346`) explicitly does **not** fail the
  probe on a stock-entitlement denial (comment at
  `options_researcher/live_quotes.py:349`: "A stock entitlement denial does
  NOT fail the probe (parity-fallback mode)"), returning
  `(True, "ok (no stock entitlement -- parity-fallback spot for trigger
  names only)")` (`options_researcher/live_quotes.py:372-374`). `refresh`
  (`options_researcher/live_quotes.py:565`) branches on `stock_entitled`
  (line 597): if entitled it calls `_stock_spots` (batched
  `client.stock_snapshot_quote`, `options_researcher/live_quotes.py:467-498`);
  if not, spot comes from parity per symbol
  (`options_researcher/live_quotes.py:610-620`). Memory
  (`~/.claude/.../session-2026-07-24-big-day.md`, referenced in the system
  context) states this was confirmed live: "greeks/stock NOT entitled ->
  parity spot + IV gap" — consistent with the code's fallback branch, though
  I did not independently re-run the probe.
- **Parquet cache layout under `data/`:**
  - Option chains: `.cache/chains/<SYMBOL>_<YYYY-MM-DD>.parquet`
    (`CACHE_DIR = Path(os.environ.get("OPTIONS_CACHE_DIR", ".cache/chains"))`,
    `data/thetadata_adapter.py:45`; path builder `_cache_path`,
    `data/thetadata_adapter.py:84`).
  - Underlying closes: `.cache/underlying/<SYMBOL>.parquet`
    (`data/underlying_closes.py:21,24`).
  - Underlying OHLCV (QM/technicals inputs): `.cache/underlying_ohlcv/`
    (`CACHE_DIR = os.path.join(".cache", "underlying_ohlcv")`,
    `data/underlying_ohlcv.py:33`), columns `OHLCV_COLUMNS`
    (`data/underlying_ohlcv.py:35`).
  - A manifest of the whole chain cache is tracked at
    `data/chain_cache_manifest.txt` (top-level `ls`, 2.9 MB file) and built by
    `tools/cache_manifest.py`.
- **`recent_topup` flow** (`data/recent_topup.py`): keeps forward-paper chain
  caches current after the one-time paid backfill
  (`data/cache_runner.py`). Key functions: `scope_symbols(scope)`
  (`data/recent_topup.py:43`, `"core"` = `config.UNIVERSE`, `"h7"` =
  `options_researcher.h7_scope.watch_universe()`), `topup_days(last_cached,
  today, ...)` (`data/recent_topup.py:81`, strictly between last-cached and
  today, today excluded because "its EOD report is not finalized until the
  next session"), `latest_cached_date(symbols, ...)`
  (`data/recent_topup.py:90`, min over symbols' own max cached date — a
  never-cached name is never silently skipped), `audit_chain` /
  `audit_day` (`data/recent_topup.py:122,164`, structural/sanity audit with
  BLOCK/PASS-WITH-WARNINGS/PASS verdicts), and the orchestrator
  `run_topup(...)` (`data/recent_topup.py:179`) which calls
  `data.thetadata_adapter.blind_cache_chain` per missing day — a blind cache
  (writes parquet, "surfaces no values", logs a `BLIND_CACHE` fact,
  `data/thetadata_adapter.py:401`) so config boundaries (`BACKTEST_END`,
  `IN_SAMPLE_END`) are never moved. CLI entry `main()`
  (`data/recent_topup.py:242`) supports `--scope {core,h7}`, `--dry-run`,
  `--no-audit`, `--refresh-closes`. Invoked in production by
  `tools/daily_ritual.sh:65` as `data/recent_topup.py --scope h7
  --refresh-closes`.
- **`live_quotes` flow (5-snaps/day live scanner path):**
  `options_researcher/live_quotes.py`. Session gate `in_regular_session(now_ny)`
  (`options_researcher/live_quotes.py:89`, `SESSION_OPEN=9:30`,
  `SESSION_CLOSE=16:00`, `NY_TZ="America/New_York"`, lines 46-54). One-shot
  schema probe `run_probe` (line 276) writes
  `reports/live_probe/<ny_date>.json` (`PROBE_DIR = "reports/live_probe"`,
  line 46) recording every live endpoint's observed columns
  (`REQUIRED_PROBE_ENDPOINTS`, line 76) — this file is required before the
  live lane turns on (per `CLAUDE.md`'s `live_quotes --probe` command and
  `probe_ok`'s age/version checks, `options_researcher/live_quotes.py:346`).
  `refresh(client=None, now_ny=None, probe=None)`
  (`options_researcher/live_quotes.py:565`) is the per-call entry point that
  assembles the live payload; it is gated by `probe_ok` and
  `in_regular_session` and marks every symbol `"off"` outside those
  conditions (lines 576-589). Per-symbol option endpoints (greeks, open
  interest) are touched only when the name is "armed" (spot at/through its
  entry trigger) — see `_symbol_preview_live` (line 501), comment
  "Option endpoints (greeks_all + OI) are touched ONLY while the live spot
  is at-or-through the trigger (armed)" (line 504-505). The literal
  "5 snaps/day" cadence itself (cron schedule / count) was **not found**
  inside `live_quotes.py`; it is referenced only in owner memory notes, not
  in a repo constant I located — see "Not found" below.

**Not found:** an explicit "5 snapshots per day" schedule constant in code
(the cadence appears to live in an external scheduler/cron, not in
`config.py` or `live_quotes.py`); a local `ThetaTerminal` process launcher
(the repo's only ThetaData path found is the direct-HTTP adapter).

---

## 2. Options-data ingestion

- **Chain snapshot fetch + cache:** covered above —
  `data/thetadata_adapter.get_eod_chain` /
  `blind_cache_chain` (`data/thetadata_adapter.py:319,401`), cached at
  `.cache/chains/<SYMBOL>_<DATE>.parquet`.
- **Cache schema:** `CHAIN_COLUMNS` and `NUMERIC_CHAIN_COLUMNS`
  (`data/thetadata_adapter.py:49-57`); enforced by `validate_chain_schema`
  (`data/thetadata_adapter.py:88`). Reading back a range of cached days is
  done via `data/pandas_feed.py::load_cached_chains`, wrapped by
  `options_researcher/chains.py::load_range(symbol, start_iso, end_iso, *,
  allow_oos=False)` (`options_researcher/chains.py:37`) — the single
  call site researcher code uses to read multi-day chain caches.
- **Monthly-expiration selection is centralized in
  `options_researcher/chains.py`:** `third_friday`, `is_monthly`
  (`options_researcher/chains.py:19,26`), `nearest_monthly(chain, today, *,
  min_dte=15, max_dte=60)` (`options_researcher/chains.py:63`),
  `ladder_expirations(chain, today, buckets=None)`
  (`options_researcher/chains.py:76`, iterates
  `config.A_LADDER_BUCKETS`, `config.py:153`), `atm_row(chain, expiration, *,
  right="P", target_delta=0.50)` (`options_researcher/chains.py:104`),
  `liquid_strikes` (`options_researcher/chains.py:117`). Module docstring:
  "Every researcher module selects expirations through THIS module."
- **Liquidity gate (used on every chain read for scanner purposes):**
  `data/thetadata_adapter.py::passes_liquidity(open_interest, bid, ask)`
  (`data/thetadata_adapter.py:456`), against `config.MIN_OPEN_INTEREST=100`
  and `config.MAX_SPREAD_PCT=0.10` (`config.py:125-126`). `mid_price`
  (`data/thetadata_adapter.py:451`).
- **Live 5-snaps/day scanner path:** `options_researcher/live_quotes.py`
  `refresh()` (line 565) — see section 1 for the probe gate, session gate,
  and armed-only option-endpoint touches. Live per-symbol output is built by
  `build_symbol_preview` (`options_researcher/live_quotes.py:157`), which
  returns spot/trigger/IV/leaps-candidate/OI fields; it does not write a
  parquet cache — it is a live-preview payload consumed by
  `options_researcher/live_dashboard.py` (see section 11), not by
  `.cache/chains/`.
- **Recent-day top-up of the EOD chain cache** (distinct from the live
  5-snap path): `data/recent_topup.py::run_topup` — see section 1.

**Not found:** a distinct "options-data-only" ingestion module separate from
`thetadata_adapter.py` — chains and their integrity checks are consolidated
there and in `data/recent_topup.py`'s offline audit subset
(`data/recent_topup.py:105-112` notes it is "a single EOD chain" subset of
the full checks in `tools/h7_data_audit.py`, which was not read in full for
this map since it is H7-forward-book specific, not scanner-signal specific).

---

## 3. Feature generation

Two separate, deliberately non-shared feature stores exist:

- **Attractiveness/presentation feature store:**
  `options_researcher/features.py`. `build_daily_features(symbol, start_iso,
  end_iso, *, closes, chains, earnings)` (`options_researcher/features.py:44`)
  computes, per cached chain day: `close`, `rv21` (21-day annualized realized
  vol, `RV_WINDOW=21`), `atm_iv` (0.50-delta put on the nearest monthly,
  15-60 DTE via `chains.atm_row`/`chains.nearest_monthly`), `iv_minus_rv`,
  `iv_rank` (inclusive-rank percentile over a trailing ≤252-obs window,
  `PCT_WINDOW=252`, `PCT_MIN_OBS=126`, NaN until 126 obs — computed
  causally in a running loop at lines 76-84), `monthly_dte`, and
  `earnings_week` (`_earnings_flags`, `options_researcher/features.py:28`,
  business-day window `EARN_BD_BEFORE=5` / `EARN_BD_AFTER=1`). Persistence:
  `FEATURES_DIR = ".tmp/research/attractiveness"`
  (`options_researcher/features.py:88`, deliberately separate from H6's
  store — comment: "a `build_all()` run on 2026-07-16 overwrote the
  manifested AMZN artifact when both builders shared one path"),
  `save_features`/`load_features` (`options_researcher/features.py:91,98`).
  Builder entry point: `build_all(end_iso=None, symbols=None)`
  (`options_researcher/features.py:102`), default universe
  `config.ATTRACTIVENESS_UNIVERSE`.
- **H6 feature store (separate, manifest/hash-bound):**
  `options_researcher/h6_features.py`. `FEATURE_DIR = Path(".tmp/research")`
  (`options_researcher/h6_features.py:41`), `FEATURE_MANIFEST_SCHEMA =
  "h6_feature_manifest_v1"` (line 42). `build_symbol_features(...)`
  (line 329), `_build_manifest` / `verify_feature_manifest`
  (lines 158, 216) hash-verify provenance (`FEATURE_SOURCE_PATHS`, line 44).
  This is a separate concern from the attractiveness scanner and is not
  read by `attractiveness.py`/`attractiveness_dashboard.py`.
- **Rebuild triggers (attractiveness store):** `tools/daily_ritual.sh`
  (lines ~264-272) calls
  `python -c "from options_researcher.features import build_all;
  build_all('$AS_OF')"` after the source-health/data-gate/h7_watch steps,
  pinned to the day's `evaluation_session` (see section 8), specifically so
  "the dashboard's IV-ranks are never silently stale at BACKTEST_END"
  (comment, `tools/daily_ritual.sh:266`). There is no automatic
  file-watcher/rebuild-on-chain-write hook found; the rebuild is an explicit
  ritual step run once per day after the chain top-up.
- **Feature freshness is checked at read time, not just at build time:**
  `options_researcher/attractiveness_dashboard.py::_gather_symbol`
  (line 941) computes `features_as_of` as the newest feature row
  at-or-before the chain day (never a future row — comment at lines
  953-956) and sets `section["features_stale"] = (features_as_of != day)`
  (line 1085), which downstream feeds `top3_snapshot.integrity_status`
  (section 4) and the `DATA_BLOCKED` display tier.

---

## 4. Signal definitions — existing signals/badges/gates

All grades below are produced by `grade(value, green, amber, *,
higher_is_better=True)` (`options_researcher/attractiveness.py:26`) which
returns `"GREEN"|"AMBER"|"RED"` from two frozen thresholds in `config.py`.

**Card-level grades, by builder function (`options_researcher/attractiveness.py`):**

| Badge key | Where computed | Threshold source |
|---|---|---|
| `yield` | `put_card_rows` L164-166, `cc_card_rows` L221-223 | `config.H5_PUT_YIELD_GREEN/AMBER` (0.010/0.006), `config.H5_CC_YIELD_GREEN/AMBER` (0.008/0.004) |
| `cushion` | `put_card_rows` L166-168 | `config.H5_CUSHION_GREEN/AMBER` (0.8/0.5) |
| `upside_room` | `cc_card_rows` L224 | `config.H5_CC_UPSIDE_GREEN` (0.03) |
| `iv_for_seller` | `put_card_rows` L169-170, `cc_card_rows` L226-227, `pmcc_card_rows` L286-287 | `config.H5_IVR_SELL_GREEN` (0.5) |
| `vrp_for_seller` | `_vrp_seller_grade(iv_minus_rv)`, `attractiveness.py:132` | `config.H5_VRP_SELL_GREEN` (0.0) — GREEN iff front-month IV ≥ trailing 21d realized |
| `earnings` | all seller builders, e.g. `put_card_rows` L172-173 | AMBER if in-cycle, GREEN if clear, `UNKNOWN` if `earnings_unknown` (coverage-horizon gap, `config.EARNINGS_COVERAGE_DAYS=98`) |
| `fomc` | all seller builders, e.g. L174 | `fomc_in_cycle` boolean from `options_researcher/fomc.py::load_fomc` |
| `liquidity` | every builder, e.g. L175-176 | `data.thetadata_adapter.passes_liquidity` |
| `safety` | `pmcc_card_rows` L285 | structural (only strikes ≥ `leaps_strike+leaps_premium` reach the builder) |
| `fits_bucket` | `leaps_card_rows` L330 | `bucket_room` derived from `config.H4_THESIS_MAX_PREMIUM_TOTAL` |
| `iv_for_buyer` | `leaps_card_rows` L331-333, `long_call_card_rows` L373-374 | `config.H5_IVR_BUY_GREEN` (0.3) / `H5_IVR_BUY_RED` (0.7), lower-is-better |
| `fits_cap` | `long_call_card_rows` L372 | `config.MAX_LOSS_PER_TRADE` (600) |
| `portfolio` (post-hoc, dashboard layer) | `attractiveness_dashboard.assemble` L789-798 | mirrors `top3_snapshot` lane policy (`ELIGIBLE→GREEN`, `WATCH→AMBER`, `PLAN_ONLY/other→RED`) |

**Card "roles"/lanes (each a distinct scanner section, `attractiveness.py`
functions and `attractiveness_dashboard.py::_gather_symbol` groups):**
`put_card_rows` (sell-a-put, L142), `cc_card_rows` (sell-a-covered-call,
L194), `pmcc_card_rows` (poor-man's covered call, L252), `leaps_card_rows`
(buy-a-LEAPS, L312), `long_call_card_rows` (tactical short-dated call,
L349). All but `leaps_card_rows` are laddered across `config.A_LADDER_BUCKETS`
DTE buckets via `ladder_cards` (`attractiveness.py:69`), which also
recomputes `earnings_in_cycle`/`fomc_in_cycle` per bucket and sets
`earnings_unknown` per the coverage-horizon rule (L86-107).

**Earnings-cycle re-grading (v3 point-in-time store):**
`options_researcher/earnings_cycle.py::cycle_badge` (line 34) and
`apply_cycle_badges` (line 76) re-grade the `earnings` badge in place from
`options_researcher.h7_earnings` assertions for watchlist names lacking a
curated CSV, returning tri-state `AMBER`/`GREEN`/`UNKNOWN` (never a falsely
reassuring GREEN — module docstring).

**Portfolio/session-integrity gate (a policy "badge", not a market signal):**
`options_researcher/top3_snapshot.py`:
`integrity_status(section)` (line 83, `DATA_BLOCKED` vs `ELIGIBLE` based on
`as_of`/`features_as_of` alignment and `features_stale`), `lane_policy_status`
(line 119, per-lane: `long_call` max-loss cap, `put` CSP slot/authorization,
`pmcc` LEAPS-held requirement, covered-call 100-share requirement),
`snapshot_candidate` (line 217, combines both into `selection_status` and
`rank_eligible`). Statuses: `ELIGIBLE`/`WATCH`/`PLAN_ONLY`/`DATA_BLOCKED`
(lines 24-27).

**Technicals snapshot (dashboard-only, not a strategy gate):**
`options_researcher/technicals.py::technical_snapshot(closes)` (line 48)
returns SMA20/50/200-based `trend`, `ma_posture`, `breakout_20d`
(`config.TECH_BREAKOUT_LOOKBACK=20`), `mom_1m`/`mom_3m`
(`config.TECH_MOM_1M=21`, `TECH_MOM_3M=63`), `dist_52w_high`
(`config.TECH_52W_LOOKBACK=252`). `technical_summary_line` (line 109)
renders it to prose. Consumed only for display-score tech-confluence bonus
(`attractiveness_dashboard._display_score`, line 528) — never a grade/gate.

**Planned, not implemented (from
`docs/superpowers/plans/2026-07-22-rq2-scanner-enrichment-briefs.md`):**
- **Badge B — term-structure "corner"** (`ts_slope`, `ts_pctl`,
  `earnings_tag`, `corner`): Brief B1, planned columns in
  `options_researcher/features.py` + `config.py` `TS_*` constants + new
  `tests/test_ts_corner_badge.py`. Not present in the current
  `features.py` (verified: no `ts_slope`/`ts_pctl`/`TS_` symbols found).
- **Badge A — bounce lens** (`bounce_armed`): Brief A1, planned in
  `options_researcher/technicals.py` or a new `bounce_lens.py` + `config.py`
  `BOUNCE_*` constants. Not present (no `bounce_armed`/`BOUNCE_` symbols
  found).
- **Panel C — board concentration & clustering** (ρ̄/n_eff, earnings
  clustering, combined-max-loss bracket, worst-observed-day replay): Brief
  C1, planned new `options_researcher/board_risk.py` + `config.py`
  `BOARD_CORR_WINDOW` etc. Not present (no `board_risk.py` file exists).
- **N3-1 — market-implied expectations lines** (expected move,
  assignment-touch odds): planned additive prose in
  `options_researcher/attractiveness.py` + `portfolio.py`
  `ASSIGNMENT_WATCH` extension. Not present in current `attractiveness.py`
  card verdicts (no "not a forecast"/"risk-neutral" strings found there).
- **V1 — VRP-done-properly calibration pair** (tenor-matched VRP history,
  earnings-crush history): planned batch walk-forward builder in
  `options_researcher/features.py` + `config.py` `VRP_CAL_*` constants. Not
  present.
- **H1 — cost/annualization honesty bundle**: wording-only, "ship anytime,"
  not yet applied per my read of `attractiveness.py` (verdict strings
  already include "(simple, not compounded)" in several places, e.g.
  `attractiveness.py:182,238,301` — but the RQ2 doc's specific asks, e.g.
  round-trip cost line and 252-vs-365 footer disclosure, were not found).
- **§ Delegated values (2026-07-24) table** in the same doc records
  LLM-proposed frozen numbers for B1/A1/C1/N3-1/V1 (e.g. B1 long-tenor band
  = `config.H7_IV_TENOR_DTE_BAND` (72,108); A1 `dist_52w_high` ≤ −20%,
  `mom_1m` ≥ +5%, `rv21` percentile ≥ 0.60) — these are pre-registration
  proposals only, not yet in `config.py` (verified: no `BOUNCE_DIST_52W`,
  `BOUNCE_MOM_1M`, etc. constants exist).

---

## 5. Scoring and ranking

All scoring/ranking below is explicitly documented as **presentation-layer
display ordering only, never a strategy gate** (module docstring,
`attractiveness_dashboard.py:1-25`; also `config.py:550-552`: "dashboard
display only, NOT strategy gates; frozen H5/H6/H7 numbers untouched").

- **Per-card GREEN-fraction ranking (the core cross-lane ordering key):**
  `_display_quality_key(card, kind, tech)`
  (`options_researcher/attractiveness_dashboard.py:552`) returns
  `(-frac, -leader, -tech_conf)` where `frac = greens / len(grades)` —
  fraction, not raw count, "because seller lanes carry 7 gradeable badges
  vs 3 on buyer lanes" (docstring, line ~562). This is the literal
  "GREEN-fraction lexicographic ranking" named in the task.
- **Legacy additive display score (kept for an audit line, no longer
  orders the shortlist):** `_display_score(card, kind, tech)`
  (`attractiveness_dashboard.py:528`) sums `config.PICK_GREEN_POINT` (1) per
  GREEN badge, `config.PICK_RANK_LEADER_BONUS` (2) if `rank_leader`, and
  `config.PICK_TECH_BONUS` (2) for technical confluence
  (`config.py:554-556`).
  Confirmed no-longer-primary by `select_top_picks`'s docstring (line 353):
  "Ordering is the lexicographic `_display_quality_key` ... The legacy
  integer `pick_score` ... is kept on each pick for the audit line but no
  longer orders the shortlist."
- **Hero/Top-3 selection:** `select_top_picks(data, n=3, *,
  policy_veto=None, include_csp_watch=False)`
  (`attractiveness_dashboard.py:330`) builds an admissible pool via
  `_admissible_pick_pool` (line 242, hard vetoes: `liquidity=="RED"`, and
  `top3_snapshot.rank_eligible is not True` unless `include_csp_watch`
  admits a specific CSP-authorization-only WATCH case), sorts by
  `(quality_key, tie, symbol, lane, strike)`, and keeps at most one pick per
  symbol (line 369-375, "the hero is a cross-name shortlist, and each
  symbol surfaces only its best card"). A QM-aware variant
  `select_qm_top_picks` (line 379) re-tiers the same admissible pool using
  current QM/moving-average context, fail-closed unless the context is
  `"CURRENT"` for the exact dashboard date (`_qm_context_block_reason`,
  line 294).
- **Pinned symbols:** `pinned_picks(data)` (`attractiveness_dashboard.py:499`)
  reads `config.PICK_PINNED_SYMBOLS = ["VST", "AMZN"]` (`config.py:563`) and
  runs `select_top_picks` scoped to just that symbol's section — "Separate
  from — and never reordering — the deterministic Top-3" (docstring).
- **Within-symbol strategy-section ordering** (which lane/group renders
  first on a symbol's panel): `_rank_groups_for_display(groups, *,
  tech=None)` (`attractiveness_dashboard.py:630`), keyed by
  `_group_candidate_sort_key` (line 606), which layers a liquidity-RED tier
  (3) and `_display_policy_tier(card)` (line 574, 0=ELIGIBLE .. 3=DATA_BLOCKED,
  via `_DISPLAY_POLICY_TIER` dict line 520) on top of the same
  `_display_quality_key`.
- **Rank/policy status precedence:** a card's `top3_snapshot` (built by
  `options_researcher/top3_snapshot.py::snapshot_candidate`) is the
  authoritative merged status; `_display_policy_tier` explicitly treats a
  missing/malformed snapshot as `DATA_BLOCKED` (worst tier), never as an
  accidental pass (`attractiveness_dashboard.py:574-597`).

---

## 6. Volatility handling (IV, IVR, term structure)

- **Per-contract IV / greeks** come straight from the cached chain columns
  (`iv`, `delta`, `vega`, `gamma` in `NUMERIC_CHAIN_COLUMNS`,
  `data/thetadata_adapter.py:54`) — no separate IV solve is run by the
  scanner itself for cached-chain paths (the chain already carries
  ThetaData's own greeks/IV).
- **ATM IV (front-month, "atm_iv"):** computed once per day in
  `options_researcher/features.py::build_daily_features` (line 55-63) via
  `chains.nearest_monthly` (15-60 DTE band) + `chains.atm_row` (0.50-delta
  put). Long-tenor ATM IV (≈90d): `options_researcher/h7_signals.py`
  (referenced by name in the RQ2 doc as `atm_iv_90d()`; I located
  `options_researcher/h7_signals.py` in the repo listing but did not open it
  in full for this map — see "Not found" note). `config.H7_IV_TENOR_DTE_BAND
  = (72, 108)` (`config.py:430`) is the registered ~90d ± 18d tenor band
  used by the H7 (not the attractiveness) signal path, and the RQ2 brief's
  delegated decision reuses this exact constant for the planned
  term-structure badge (section 4 above).
- **IV rank (IVR):** `iv_rank` in `options_researcher/features.py`
  (lines 76-84) — a causal, inclusive-rank percentile of `atm_iv` over a
  trailing ≤252-day window, `PCT_MIN_OBS=126` (NaN before that many finite
  observations). This is the only "IV-rank" definition found; it feeds
  `H5_IVR_SELL_GREEN`/`H5_IVR_BUY_GREEN`/`H5_IVR_BUY_RED` badge grades
  (section 4) and the live preview's own rank approximation
  `iv_rank_preview(history_atm_iv, live_iv)`
  (`options_researcher/live_quotes.py:111`).
- **VRP proxy (`iv_minus_rv`):** `atm_iv - rv21`, computed in
  `features.py` (line 68); graded by
  `attractiveness.py::_vrp_seller_grade(iv_minus_rv)` (line 132) against
  `config.H5_VRP_SELL_GREEN=0.0`. The docstring is explicit that this is
  "NOT a true variance risk premium" — tenor and realization window only
  roughly match (`attractiveness.py:132-139`).
- **Realized vol (`rv21`):** 21-day annualized log-return stdev (ddof=1),
  computed in both `features.py::build_daily_features` (line 47-48) and
  independently in `attractiveness.py::put_card_rows`'s local
  `monthly_move = rv21/sqrt(12)` cushion math (line 156).
- **Term structure:** no current computed "term structure" column exists in
  `features.py` today (only single-tenor `atm_iv`). The RQ2 plan's Brief B1
  (`ts_slope = atm_iv_near - atm_iv_long`) is the planned addition (section
  4, "planned, not implemented").
- **IV history for the live-preview IVR:** `_load_iv_history(symbol)`
  (`options_researcher/live_quotes.py:458`) reads the cached EOD feature
  frame's `atm_iv` column via `options_researcher.features.load_features`.

**Not found:** a full read of `options_researcher/h7_signals.py`'s
`atm_iv_90d()` internals (file exists per `ls`, referenced by name in the
RQ2 doc; not opened line-by-line for this map since it is an H7-forward
signal, not an attractiveness-scanner one — flagging so the next agent
knows to verify the exact tenor-selection logic before reusing it).

---

## 7. Market-regime logic

- **No computed market-regime/breadth/trend-filter signal exists in the
  scanner code itself.** The only "regime" string in the rendered
  dashboard, `_market_html(context)` (`attractiveness_dashboard.py:2335`),
  is pass-through display of `context["market"]["regime"]` — free text read
  from an externally-authored JSON file via `load_context(as_of, base_dir=
  "reports/attractiveness_context")` (`attractiveness_dashboard.py:653`).
  There is no code in this repo that classifies breadth/trend into that
  `"regime"` string; it is presentation of whatever a research-context file
  contains (test fixture example: `{"regime": "mixed", "notes": [...]}"`,
  `tests/test_attractiveness_dashboard.py:1045`).
- **Per-name trend/momentum ("technicals"), not board-wide regime:**
  `options_researcher/technicals.py::technical_snapshot` (line 48) — SMA
  20/50/200 trend classification, `ma_posture`, `breakout_20d`, `mom_1m`,
  `mom_3m`, `dist_52w_high`. This is per-symbol, used only for the display
  score's tech-confluence bonus (section 5) — not a board-wide regime
  filter.
- **"Regime" as a backtest-robustness slicing dimension (a different,
  unrelated concept)** exists in `options_researcher/robustness/` — e.g.
  `PanelObservation.regime` (`options_researcher/robustness/screening.py:24`),
  `_regime_contributions` (`options_researcher/robustness/runner.py:256`),
  `regime_concentration` diagnostic
  (`options_researcher/robustness/stability.py:31,105`). This is a
  registered-experiment (RQ1) walk-forward/stability-slicing label (e.g.
  bull/bear historical windows) for the backtest-robustness layer, not a
  live scanner signal, and not wired to `attractiveness.py` at all.
- **Correlation/concentration precedent** cited by the RQ2 plan's Brief C1
  (planned, not implemented): `analysis/power_check.py` computes pairwise
  simulated dependence (`measure_dependence(n_pairs=200_000, seed=99)`,
  `analysis/power_check.py:109`) — a Monte-Carlo power-analysis helper, not
  a live board-correlation computation; C1 proposes reusing its "formula
  precedent," not its code.

**Not found:** any board-wide breadth indicator (advance/decline, % above
moving average, etc.) computed anywhere in `options_researcher/` or
`analysis/`.

---

## 8. Freshness and timestamp handling

- **NY-date basis is the repo-wide convention.** `options_researcher.h7_watch`
  uses `ZoneInfo("America/New_York")` for the CLI's default run date
  (`options_researcher/h7_watch.py:359`); `options_researcher.live_quotes`
  defines `NY_TZ = "America/New_York"` (line 49) and session bounds
  `SESSION_OPEN=time(9,30)`/`SESSION_CLOSE=time(16,0)` (lines 53-54),
  checked by `in_regular_session(now_ny)` (line 89). Memory context notes
  `data/recent_topup.py` moved to "NY-date basis" (commit `82ac003`,
  referenced in the user's memory file, not independently re-verified line
  by line here beyond the module's own use of XNYS trading-day calendars).
- **Session alignment (the exact-session data-integrity contract):**
  `options_researcher/h7_watch.py::evaluation_session(run_date)` (line 155)
  returns "the latest COMPLETED XNYS session strictly before `run_date`" —
  never the run date itself, because "its EOD is not final" (docstring,
  matching `recent_topup`'s "today excluded" rule). `check_alignment(closes,
  chain_day, eval_iso)` (`options_researcher/h7_watch.py:168`) refuses
  (returns a gap reason, never silently proceeds) unless `closes` end
  *exactly* at the evaluation session and `chain_day == eval_iso` — "No
  fallback, no mixing: every decide_lane_* input shares one completed
  session or nothing runs" (docstring).
- **Attractiveness-scanner freshness (per-symbol, per-card):**
  `attractiveness_dashboard.py::_gather_symbol` (line 941) computes
  `features_as_of` as the newest feature row at-or-before the chain day
  (never future), and `features_stale = (features_as_of != day)`
  (line 1085). This flows into
  `top3_snapshot.integrity_status(section)` (`top3_snapshot.py:83`), which
  sets `DATA_BLOCKED` reason codes `SECTION_AS_OF_INVALID`,
  `FEATURES_AS_OF_INVALID`, `FEATURES_SESSION_MISMATCH`, `FEATURES_STALE`,
  `FEATURES_STALENESS_UNKNOWN` (lines 86-99) — any of these forces
  `selection_status = DATA_BLOCKED` regardless of lane policy
  (`top3_snapshot.py:265-266`), which in turn forces the worst display tier
  (`_display_policy_tier`, section 5).
- **Page-level "data as-of" banner:** `_page_data_as_of(sections)`
  (`attractiveness_dashboard.py:734`) takes the **earliest** per-symbol
  `as_of` date across all sections (not the freshest), specifically "so a
  stale chain cache can never hide behind a fresher one" (docstring).
- **Live-quote freshness:** `quote_is_fresh(quote_ts, now, max_age_seconds)`
  (`options_researcher/live_quotes.py:126`) against
  `config.LIVE_QUOTE_MAX_AGE_SECONDS = 120` (`config.py:592`); the schema
  probe itself expires via `probe_ok`'s age check against
  `config.LIVE_PROBE_MAX_AGE_DAYS = 7` (`config.py:593`,
  `options_researcher/live_quotes.py:364-366`).
- **Per-day chain/parquet staleness for the offline scanner CLI**
  (`attractiveness.py::main`, section 4): reads the *latest* cached parquet
  file per symbol via `glob` + filename date parsing
  (`attractiveness.py:443-448`) — no explicit staleness check beyond "file
  exists"; freshness enforcement is concentrated in the dashboard path
  (`_gather_symbol`/`top3_snapshot`), not the plain-text CLI path.

---

## 9. Backtesting flow

- **Harness:** `harness/run_backtest.py` — generic Lumibot-based runner.
  `_year_chunks` (line 36), `_run_chunk` (line 52, builds a Lumibot
  `ThetaDataBacktesting`/`BacktestingBroker` per the project's engineering
  rule of never hand-rolling a fill simulator), `run(strategy_cls, start=
  None, end=None, ...)` (line 104), plus the sealed-holdout reveal path
  `reveal_out_of_sample` (line 154, gated on
  `config.IN_SAMPLE_END = "2022-12-31"`, `config.py:78`).
  `harness/run_h7_backtest.py` is the H7-specific variant:
  `_require_h7_history_not_retired` (line 59, refuses to run the retired
  historical diagnostic), `run_lane(lane, start=None, end=None, ...)`
  (line 216).
- **Strategies:** `strategies/put_credit_spread.py::PutCreditSpread` (line
  141, the H1/H2 registered credit-spread strategy) and
  `strategies/h7_backtest.py::H7LaneBacktest` (line 140, the H7 lane
  backtest engine) both subclass Lumibot's `Strategy`
  (`strategies/base.py`). `strategies/h7_lanes.py` holds the lane-decision
  functions (`decide_lane_a/b/c`) that both the backtest and the live
  `h7_watch.py` import (confirmed shared-source-of-truth by
  `h7_watch.py::_decide`, line 208: "Dispatch to the SINGLE decision
  authority (strategies.h7_lanes)").
- **CLI scoreboard:** `tools/score_backtest.py::main()` (line 47) runs
  `harness.run_backtest.run(PutCreditSpread, ...)` restricted to
  `start<=end<=config.IN_SAMPLE_END` (`_validate_in_sample`, line 36,
  raises `OOSDataTouchError` past that boundary) and prints/JSON-dumps
  `metrics.scoreboard(trades, label=...)`.
- **Do scanner signals (attractiveness badges) connect to the backtest
  path? No — confirmed by absence.** Neither `strategies/put_credit_spread.py`
  nor `strategies/h7_backtest.py` imports
  `options_researcher.attractiveness`, `attractiveness_dashboard`,
  `features` (the attractiveness store), or `top3_snapshot` (verified: I
  grepped the strategies/harness/tools files read above and found no such
  import; the strategies instead read `data.pandas_feed`/chains directly
  and apply their own registered entry/exit rules from `config.py`,
  independent of the badge/grade vocabulary in `attractiveness.py`). The
  attractiveness scanner is a **read-only, presentation-layer research
  tool**; the backtest strategies are a **separate, registered,
  frozen-parameter code path**. This matches the module docstrings'
  repeated "READ-ONLY: never trades, never writes" language throughout
  `attractiveness.py`/`attractiveness_dashboard.py`.
- **`H7LaneBacktest` does reuse some of the same low-level building
  blocks** as the scanner (e.g. `options_researcher.chains` for expiration
  selection, `data.thetadata_adapter.passes_liquidity` for the liquidity
  gate) — but it does not consume the scanner's *badges*, *grades*, or
  *ranking* at all; it re-derives its own entry/exit decisions from
  `config.H7_*` constants and `strategies/h7_lanes.py`.

---

## 10. Configuration (`config.py`)

- **Structure:** one flat module, organized into commented sections
  (`# ---...` banner comments throughout, e.g. `config.py:12-14, 48-50,
  87-89, ...`) covering: universe/date ranges (`UNIVERSE`, `BACKTEST_START`,
  `BACKTEST_END`, `IN_SAMPLE_END`, lines 60-78), cost model
  (`COMMISSION_PER_CONTRACT`, `SLIPPAGE_HAIRCUT`, lines 91-92), liquidity
  gates (`MIN_OPEN_INTEREST`, `MAX_SPREAD_PCT`, lines 125-126), verdict
  rule (`MIN_LOSSES_FOR_VERDICT = 10`, line 174), H5 income-lane thresholds
  (`H5_*`, lines 226-265), H6 (`H6_*`, lines 272-288), H7 (`H7_*`, lines
  326+, the largest single block — universe lists, lane deltas/DTE bands,
  risk sleeve, admission gates), presentation-layer `PICK_*` weights and
  `PICK_PINNED_SYMBOLS` (lines 554-563), `EARNINGS_COVERAGE_DAYS` (line
  569), the derived `ATTRACTIVENESS_UNIVERSE` (lines 577-579), live
  mission-control constants (`LIVE_*`, lines 589-593), and H9 study
  parameters (lines 605+).
- **"Every number from config.py" rule is enforced in practice** — every
  badge threshold traced in section 4 above (`H5_PUT_YIELD_GREEN`,
  `H5_CUSHION_GREEN`, `H5_IVR_SELL_GREEN`, `MAX_LOSS_PER_TRADE`, etc.) is a
  named `config.py` constant referenced by symbol in `attractiveness.py`
  and `top3_snapshot.py` — no bare numeric literals were found inline in
  the threshold comparisons I read (each `grade(...)` call passes
  `config.H5_*`/`config.MAX_LOSS_PER_TRADE`, never a literal).
- **`ATTRACTIVENESS_UNIVERSE` is explicitly DERIVED, never independent:**
  `config.py:577-579`, `[s for s in H7_WATCHLIST + H7_CORE_LONG_ONLY if s
  not in H7_EXCLUDED]` — comment states "adding a ticker here requires
  adding it to the H7 scope first," and this equality is unit-tested
  (`tests/test_attractiveness_universe.py::test_equals_canonical_h7_scope`,
  comparing to `options_researcher.h7_scope.watch_universe()`). Current
  composition: `H7_WATCHLIST` = 11 names (`config.py:327-328`, includes
  IREN/USAR/ET added by later amendments), `H7_CORE_LONG_ONLY` = 4 names
  (`VST`, `CEG`, `MSFT`, `AMZN`, line 334), `H7_EXCLUDED = ["HYLN"]` (line
  335, currently a no-op since `HYLN` is not present in either source
  list) — giving 15 names in `ATTRACTIVENESS_UNIVERSE`.
- **How a new signal's parameters would be added (fact, not proposal):**
  the RQ2 brief itself states the convention explicitly — "every new
  constant lives in `config.py`" (`docs/superpowers/plans/2026-07-22-rq2-
  scanner-enrichment-briefs.md` standing constraint #5) and each individual
  brief names its own prefix (`TS_*` for Badge B, `BOUNCE_*` for Badge A,
  `BOARD_CORR_WINDOW` etc. for Panel C, `VRP_CAL_*` for Badge V1) — matching
  the existing `PICK_*`/`H5_*`/`H7_*` prefixing convention already used
  throughout `config.py`.

---

## 11. User-facing output

- **`options_researcher/dashboard.py`** (`OUTPUT_PATH =
  ".tmp/dashboard/index.html"`, line 35): the H5 paper-book/"game-styled"
  static dashboard. `assemble(*, book=None, facts=None, ...)` (line 146),
  `render(data)` (line 426), `main(**assemble_kwargs)` (line 682, writes the
  HTML file). Shows the paper book, facts ledger excerpts, achievements,
  and an H7 window panel (`_h7_window_panel`, line 397) — separate from the
  attractiveness scanner.
- **`options_researcher/attractiveness_dashboard.py`** (`OUTPUT_PATH =
  ".tmp/dashboard/attractiveness.html"`, line 37): the scanner's primary
  surface. `assemble(...)` (line 743) → `render(...)` (line 2471) →
  `_build_and_write`/`main()` (lines 2565, 2592). CLI: `python -m
  options_researcher.attractiveness_dashboard`
  (`CLAUDE.md` command list) and `--json` prints `sections_json()`
  (line 1092). Renders: per-symbol card grids (`_card_html`, line 1794),
  hero/Top-3 (`_hero_pick_html`/`_original_hero_html`/`_qm_hero_html`,
  lines 2034/2175/2248), pinned-symbol strip (`_pinned_html`, line 2404),
  blocked-symbol banner (`_blocked_html`, line 2445), market-context strip
  (`_market_html`, line 2335), and a nonzero-exit-on-unexpected-failure
  contract (`_run_exit_code`, line 2464).
- **`options_researcher/live_dashboard.py`**: a **serving**, not a
  file-writing, dashboard (`_USAGE` string, line 459: "live_dashboard
  serves; it does not write files"). `LiveDashboardServer` (line 421),
  `_Handler`/`_HTTPServer` (lines 395, 385) serve on `127.0.0.1` only
  (`config.LIVE_DASH_PORT = 8642`, `config.py:589`). `build_payload(live,
  official_rows=None)` (line 147) assembles a two-lane payload: "OFFICIAL"
  (from `_gather_official`, line 118, sourced from `entry_watch` — the only
  lane allowed to FIRE) and "LIVE PREVIEW" (`PREVIEW_LANE` constant in
  `live_quotes.py:66`, cannot fire — test-enforced per memory notes).
  `inject_live_panel(html)` (line 366) injects a live-refresh panel into
  the static `attractiveness_dashboard.py` HTML for local viewing.
- **CLI text outputs:** `attractiveness.py::main()` (line 403, plain-text
  scanner printout, `python -m options_researcher.attractiveness`),
  `entry_watch.py::main()` (line 90, WAIT/FIRE trigger lines), and
  `h7_watch.py`'s own CLI (`main`, line 341) for the H7 lane watcher.
- **Orchestration order (owner-frozen ritual):** `tools/daily_ritual.sh`
  comment (lines 2-4): "topup -> source health -> data gate (HARD) ->
  h7_watch -> h6_features -> h6_watch [-> h8_watch if built] ->
  dashboards." Dashboards rebuild unconditionally at the end regardless of
  gate state (comment, `tools/daily_ritual.sh:275-276`: "they display
  cached truth and carry their own honest data-as-of banner").

---

## 12. Existing tests (scanner/attractiveness path)

All tests are `unittest` (not `pytest`), run via `uv run python -m unittest
discover -s tests` (`CLAUDE.md` command list), and are offline against the
local parquet cache per `.cursorrules`/`CLAUDE.md` ("no network, no paid API
calls" in the suite; tests inject fake dependencies rather than hitting
ThetaData/AlphaVantage/Yahoo).

- **`tests/test_attractiveness.py`** (29 tests, e.g. `test_grade_directions`,
  `test_golden_numbers`, `test_verdict_states_annualized_not_percent_per_month`,
  `test_fomc_in_cycle_grades_amber`, `test_positive_vrp_grades_green_on_put`,
  `test_picks_tactical_delta_and_grades`, `test_rank_cards_marks_single_
  leader_higher_better`, `test_ladder_cards_recomputes_earnings_per_bucket`)
  — asserts the exact numeric grading thresholds, verdict-string formatting,
  and ladder/rank mechanics of `attractiveness.py`'s card builders.
- **`tests/test_attractiveness_dashboard.py`** (93 tests) — the largest
  scanner test file; covers `_price_ladder`, `_put_pnl`/`_cc_pnl`/`_pmcc_pnl`,
  `scenario_rows`, `bbb_rows`, `assemble`, `render` (HTML escaping, label
  presence, no external assets), `select_top_picks`/`select_qm_top_picks`
  scoring and hard-veto behavior (`test_liquidity_red_is_a_hard_veto`,
  `test_at_most_one_pick_per_symbol`,
  `test_green_fraction_not_raw_count_orders_cross_lane`,
  `test_sell_lane_tiebreak_prefers_higher_annualized_yield`,
  `test_qm_cannot_admit_a_policy_rejected_card`,
  `test_missing_one_symbol_context_blocks_the_whole_qm_list`), and section
  ordering (`test_sections_sort_by_best_card_then_policy_and_liquidity`,
  `test_selection_status_outranks_policy_status`).
- **`tests/test_attractiveness_universe.py`** (4 tests) — pins
  `config.ATTRACTIVENESS_UNIVERSE` to equal
  `options_researcher.h7_scope.watch_universe()` exactly, plus core-names-
  present / excluded-names-absent / no-duplicates checks.
- **`tests/test_attractiveness_v3.py`** (23 tests) — v3 earnings-badge
  ladder behavior (`test_ladder_marks_unknown_beyond_coverage_horizon`,
  `test_in_cycle_beats_unknown`), worst-case economics per lane
  (`test_put_worst_case_is_strike_minus_credit`,
  `test_pmcc_full_structure_economics`), the policy-veto removal/no-op
  compatibility (`test_universal_policy_veto_no_longer_excludes_cash_
  secured_puts`, `test_legacy_policy_veto_argument_is_a_noop`), and render-
  level assertions (`test_partial_top3_keeps_three_visible_slots_in_each_
  list`, `test_status_badges_pair_semantic_color_with_text_and_symbol`).
- **`tests/test_top3_snapshot.py`** (12 tests) — `integrity_status`,
  `lane_policy_status` per lane, `snapshot_candidate`'s merged
  `selection_status`/`rank_eligible`.
- **`tests/test_top3_context.py`** (research-annotation normalization —
  `normalize_research_annotations`, validation error paths).
- **`tests/test_features.py`** (7 tests) — `test_constant_closes_give_
  zero_rv`, `test_iv_rank_high_on_spike_day_only_with_min_obs`,
  `test_earnings_week_window`, `test_missing_chain_day_gives_nan_iv_not_
  crash`, `test_stores_are_different_directories`, `test_save_features_
  cannot_clobber_h6_artifact`, `test_save_and_load_roundtrip`.
- **`tests/test_technicals.py`** (12 tests) — trend/breakout/momentum math
  including `test_breakout_no_look_ahead` (a causality property test).
- **`tests/test_live_quotes.py`** (large file, 29KB) — probe schema
  recording, `probe_ok` gating, parity-vs-stock-entitled branching, armed-
  only option-endpoint touches (not individually enumerated here for
  length; file exists and is substantial).
- **`tests/test_live_dashboard.py`** — two-lane OFFICIAL/LIVE-PREVIEW
  payload assembly and the "LIVE PREVIEW can't fire" enforcement referenced
  in owner memory.
- **`tests/test_recent_topup.py`** (6 tests) — `topup_days`,
  `latest_cached_date`, audit verdict logic.
- **`tests/test_dashboard.py`** — the H5 book dashboard (`dashboard.py`),
  separate from the attractiveness scanner.
- **`tests/test_qm_dashboard.py`** — QM sidecar context loading/blocking.

---

## 13. Missing tests (gaps relevant to adding a new signal)

Based on the test inventory above and the planned-badge briefs in section 4:

- **No test file exists yet for any of the RQ2-planned badges**
  (`tests/test_ts_corner_badge.py` is *named* in Brief B1 but does not exist
  in `tests/` — verified by directory listing). No tests exist for
  `bounce_lens`/`board_risk`/VRP-calibration/N3-1 prose either, consistent
  with "not implemented" from section 4.
- **No generic/reusable "add a new badge" test harness or fixture exists.**
  Each existing badge's tests are hand-written per-builder
  (`test_attractiveness.py`) — there is no parametrized "every badge must
  render X" test I could find that a new signal would automatically be
  checked against (e.g. no test iterating `grades.keys()` generically to
  assert every badge value is one of `GREEN/AMBER/RED/UNKNOWN` — this is
  asserted implicitly per-badge, not via a shared contract test).
- **No dedicated causal/no-look-ahead property test for `features.py`'s
  planned percentile-style additions.** `iv_rank`'s causal-window
  correctness is implicitly exercised by
  `test_iv_rank_high_on_spike_day_only_with_min_obs`, but there is no
  reusable "shifting later data never changes an earlier value" helper in
  `tests/` — each RQ2 brief (B1, V1) asks for its *own* causal-percentile
  property test to be written from scratch, implying no shared utility
  exists yet.
- **No test pinning "frozen recipe untouched" (byte-identical Top-3 with a
  new badge column present vs. absent)** currently exists for any signal,
  because no additive badge has shipped yet; every RQ2 brief's acceptance
  criteria independently re-states this requirement (e.g. B1: "board
  ordering byte-identical with badges hidden"), which suggests this is a
  pattern to be introduced per-signal rather than a shared fixture.
- **No test asserts the specific string-label discipline** ("not a
  forecast", "risk-neutral", "(simple, not compounded)") as a cross-cutting
  contract; `test_attractiveness.py::test_verdict_states_annualized_not_
  percent_per_month` checks one instance of the phrasing on the existing
  put-card verdict, but there is no repo-wide grep-based test enforcing it
  on every future badge (Brief N3-1 explicitly proposes adding one:
  "label text is test-pinned").

---

## 14. Reusable abstractions

- **No typed "Signal" class/dataclass abstraction exists.** Every badge is
  a plain `dict` entry (`card["grades"][key] = "GREEN"/"AMBER"/"RED"/
  "UNKNOWN"`), and every card is a plain `dict` built ad hoc by each
  builder function (`put_card_rows`, `cc_card_rows`, etc. in
  `attractiveness.py`) — there is no `@dataclass class Badge`/`class
  Signal`/`class Card` anywhere in `options_researcher/attractiveness.py`
  or `attractiveness_dashboard.py` (verified: grep for `@dataclass` and
  `^class ` in both files found no such definitions; the only
  `@dataclass` in the researched area is
  `options_researcher/market_context.py::StoredMarketContext`, an unrelated
  equity-research bridge type). A new signal would follow the existing
  convention of adding a key to the `grades` dict and/or a new top-level
  card field, not instantiate a typed class.
- **`grade()` helper is the reusable threshold-classification primitive:**
  `attractiveness.py:26`, `grade(value, green, amber, *,
  higher_is_better=True) -> "GREEN"|"AMBER"|"RED"`. Any new numeric badge
  with a simple two-threshold rule should call this rather than
  reimplementing comparison logic.
- **`rank_cards`/`ladder_cards`** (`attractiveness.py:50,69`) are the
  reusable per-bucket ranking and DTE-laddering primitives; any new
  *card-shaped* signal that needs per-expiration-bucket selection should
  reuse `ladder_cards`, not re-derive its own bucket loop.
- **`top3_snapshot.snapshot_candidate`/`integrity_status`/
  `lane_policy_status`** (`options_researcher/top3_snapshot.py`) is the
  reusable "is this candidate safe to rank" pattern — freshness/session
  integrity is fully separated from lane policy is fully separated from
  qualitative research annotation (module docstring: "three independent
  questions"). A new signal that should participate in ranking eligibility
  would need to flow through this snapshot, not invent a parallel
  eligibility check.
- **`DATA_BLOCKED` fail-visible pattern** is used consistently at multiple
  layers, each with the same intent (never hide a gap as a false pass):
  - Plain-text CLI (`attractiveness.py:446,456`): prints
    `f"{symbol}: DATA BLOCKED -- ..."` and `continue`s past the symbol.
  - Dashboard gather loop (`attractiveness_dashboard.py::_gather_all`, line
    896-938): `_block(symbol, code, detail, day, unexpected=False)` appends
    a machine-readable record to `blocked`, rendered by `_blocked_html`
    (line 2445), with `unexpected=True` cases forcing a nonzero CLI exit
    (`_run_exit_code`, line 2464) so an unexpected programming failure is
    never mistaken for a clean rebuild.
  - Candidate-level (`top3_snapshot.py::DATA_BLOCKED = "DATA_BLOCKED"`,
    line 27; `integrity_status`, line 83): a stale/misaligned candidate is
    tagged `DATA_BLOCKED` regardless of its lane policy.
  - Display tiering (`attractiveness_dashboard.py::_DISPLAY_POLICY_TIER`,
    line 520; `_display_policy_tier`, line 574): `DATA_BLOCKED` is always
    the worst (last) display tier, and a missing/malformed snapshot
    defaults to `DATA_BLOCKED`, never to a passing tier.
  A new signal that can fail to compute (e.g. missing rates CSV, missing
  QQQ closes per the RQ2 doc's "Data-unlock actions") should follow this
  same pattern: an honest per-symbol/per-badge gap, never a silently
  fabricated value.
- **Feature-store pattern** (`options_researcher/features.py::
  save_features`/`load_features`/`build_all`, and separately
  `h6_features.py`'s manifest-hash-verified variant) is the reusable
  "compute once per day, cache to parquet, read back in the dashboard"
  pattern. A new per-day numeric signal (e.g. the planned `ts_slope`)
  is explicitly slated to be added as a **new column** in this same
  `features.py` store (RQ2 Brief B1's "Files" line), not a separate store.
- **Config-constant naming convention** (`H5_*`, `H6_*`, `H7_*`, `PICK_*`,
  `TECH_*`) is the reusable naming pattern any new signal's frozen
  parameters should follow (see section 10).

---

## 15. Integration-point recommendation (facts about the code, not a
proposal)

These are the places in the code where the RQ2 briefs and the existing
badge/card architecture already point a new additive signal, stated as
facts about what the code currently does or names, not a suggested design:

- **A new per-day numeric column belongs in
  `options_researcher/features.py::build_daily_features`** (and its
  persisted frame via `save_features`/`load_features`,
  `FEATURES_DIR = ".tmp/research/attractiveness"`) — this is where every
  existing per-day scalar (`rv21`, `atm_iv`, `iv_minus_rv`, `iv_rank`,
  `earnings_week`) already lives, it is rebuilt once per ritual run via
  `build_all(AS_OF)` (`tools/daily_ritual.sh` ~line 268), and RQ2's own
  Brief B1 names this exact file as its "Files" target for `ts_slope`/
  `ts_pctl`.
- **A new per-card badge belongs as an additional key in a card's
  `grades` dict**, computed inside the relevant builder function in
  `options_researcher/attractiveness.py` (`put_card_rows`, `cc_card_rows`,
  `pmcc_card_rows`, `leaps_card_rows`, `long_call_card_rows`) using the
  existing `grade()` helper (`attractiveness.py:26`) and a new
  `config.py` constant, following the `H5_*`/`config.PICK_*` naming
  convention.
- **A new frozen threshold or window constant belongs in `config.py`**,
  named with a signal-specific prefix (the RQ2 briefs already reserve
  `TS_*`, `BOUNCE_*`, `BOARD_CORR_WINDOW`, `VRP_CAL_*` for exactly this).
- **If the new signal must participate in ranking/rank-eligibility** (not
  just display), it must flow through `options_researcher/top3_snapshot.py`
  (`lane_policy_status`/`integrity_status`/`snapshot_candidate`) so that
  `_display_quality_key`/`_admissible_pick_pool`/`select_top_picks` in
  `attractiveness_dashboard.py` see it consistently — but every RQ2 brief
  explicitly states new badges must NOT change rank/grade/trigger (only
  display), which the current architecture supports because `grades` dict
  keys used only for *display* never touch `_admissible_pick_pool`'s hard
  vetoes (which check specifically `grades.get("liquidity")` and the
  `top3_snapshot` fields — not "every grade").
- **Any new signal's HTML rendering belongs in
  `options_researcher/attractiveness_dashboard.py`**, most likely as an
  addition to `_card_html`/`_badges` (lines 1794, 1629) for a per-card
  badge, or as a new panel function analogous to `_market_html`
  (line 2335) / a new `_board_risk_html`-shaped function called from
  `render()` (line 2471) for a board-wide panel (Brief C1's shape).
- **Any new signal needing per-name entitlement/session freshness must
  reuse the existing freshness fields** (`features_as_of`,
  `features_stale`, `top3_snapshot.integrity_status`) rather than invent a
  new staleness check — these are the only staleness signals the rest of
  the pipeline (display tiering, hero admission) already understands.
- **Tests for a new signal belong in a new `tests/test_<signal>.py`**,
  following the existing per-module test-file convention (one test file
  per production module: `test_attractiveness.py` ↔ `attractiveness.py`,
  `test_features.py` ↔ `features.py`, `test_top3_snapshot.py` ↔
  `top3_snapshot.py`), run offline via `unittest` with injected
  closes/chains/assertions exactly as the existing tests do (no network,
  per `.cursorrules`).

---

## Files inspected (paths only)

```
config.py
options_researcher/attractiveness.py
options_researcher/attractiveness_dashboard.py
options_researcher/chains.py
options_researcher/dashboard.py
options_researcher/earnings_cycle.py
options_researcher/entry_watch.py
options_researcher/features.py
options_researcher/h6_features.py
options_researcher/h7_watch.py
options_researcher/live_dashboard.py
options_researcher/live_quotes.py
options_researcher/market_context.py
options_researcher/qm_dashboard.py
options_researcher/technicals.py
options_researcher/top3_context.py
options_researcher/top3_snapshot.py
data/recent_topup.py
data/thetadata_adapter.py
data/underlying_closes.py
data/underlying_ohlcv.py
data/rates.py
harness/run_backtest.py
harness/run_h7_backtest.py
strategies/h7_backtest.py
strategies/put_credit_spread.py
tools/score_backtest.py
tools/daily_ritual.sh
analysis/power_check.py
options_researcher/robustness/screening.py
options_researcher/robustness/runner.py
options_researcher/robustness/stability.py
docs/superpowers/plans/2026-07-22-rq2-scanner-enrichment-briefs.md
tests/test_attractiveness.py
tests/test_attractiveness_dashboard.py
tests/test_attractiveness_universe.py
tests/test_attractiveness_v3.py
tests/test_top3_snapshot.py
tests/test_features.py
tests/test_technicals.py
tests/test_recent_topup.py
```

## Not found (repo-wide, consolidated)

- An explicit "5 snapshots/day" cadence constant in code (lives outside
  the repo, e.g. an external scheduler).
- A local `ThetaTerminal` process/port launcher (this repo's ThetaData path
  is direct keyed HTTP, per `tools/daily_ritual.sh` comment).
- Full internal read of `options_researcher/h7_signals.py::atm_iv_90d()`
  (file exists, referenced by name in the RQ2 doc; not opened in full since
  it is an H7-forward-book signal, not an attractiveness-scanner one).
- Any board-wide breadth/advance-decline computation.
- Any typed `Signal`/`Badge`/`Card` class or dataclass in the scanner path.
- Any test file for the RQ2-planned badges (none exist yet; several are
  explicitly *named* in the plan doc but not present in `tests/`).
