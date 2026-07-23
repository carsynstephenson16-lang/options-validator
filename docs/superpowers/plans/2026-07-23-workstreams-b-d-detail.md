# Workstream detail: B (aggressive-vol opportunity cards) and D (earnings variance decomposition)

**Date:** 2026-07-23. Companion to
`docs/superpowers/plans/2026-07-23-twelve-month-scanner-research-program.md`.
Drafted by a design subagent against the live repo, then corrected by the
orchestrator (block below). Descriptive-first: cards and measurements, never
orders; every registered test goes through the ledger.

## Orchestrator corrections (2026-07-23, supersede matching lines below)

1. **Rates are no longer blocked.** `data/rates/treasury_cmt.csv` was sourced
   this session (Treasury.gov capture, forward-serving provenance:
   known_as_of = capture time). Bid/ask IV inversion for FORWARD events can use
   real `r` immediately; it still needs `q` per name, which arrives with
   `data/rates/expected_dividends.csv` (pending owner spot-check). HISTORICAL
   events can never get point-in-time rates (capture-time provenance is
   deliberate), so historical bands run under a labeled Assumption (flat
   current-level rate, `band_status="assumption_flat_rate"`), never silently.
2. **SPY/QQQ closes+OHLCV are now cached** (2017-01-03→2026-07-22, sanctioned
   Yahoo path). Card #17's realized-vol ratio line and D §2's beta-adjusted
   residual upgrade are buildable now. Index IV remains blocked (chains end
   2026-06-30) pending an owner decision on index-chain top-up.
3. **Owner-forwarded exit convention (2026-07-23, ratify at registration):**
   income-card labels use 50% max-profit / 21-DTE time-stop / breach → hold to
   21 DTE then close. "Roll" is studied only as a separate comparison arm
   (roll = close + new trade), never inside the base label.
4. **Expected-move wording:** where a card quotes a priced move, the primary
   quantity is the ATM straddle mid (model-free); `0.8·S·IV·√τ` is the labeled
   fallback ("expected absolute move"); `S·IV·√τ` stays a separate 1-SD band
   line. Per the 2026-07-23 math verification.

---

## Workstream B — 19 opportunity-card designs

Platform-wide defaults (not repeated per card): `MIN_OPEN_INTEREST=100`,
`MAX_SPREAD_PCT=0.10` both legs; commissions $0.65/contract/leg/way +
`SLIPPAGE_HAIRCUT=0.01` beyond mid + half-spread both legs; `RISK_SLEEVE=$14k`;
`MAX_LOSS_PER_TRADE=$600` economic cap; `DTE_MIN=10`. Feature fields from
`options_researcher/features.py` (`atm_iv`, `iv_rank`, `iv_minus_rv`) and
`options_researcher/h7_signals.py` (`rv_percentile`, `drawdown_pct`,
`atm_iv_90d`). **`term_slope` is not a materialized field anywhere in the repo
(repo-verified absence)** — cards needing it construct
`atm_iv − atm_iv_90d`-style slope as NEW build work. Earnings gating reuses
`options_researcher/h7_earnings.py` (`earnings_gate`, v3 store) exclusively;
session timing (bmo/amc) exists on both earnings stores. Multi-leg cards apply
the stricter H7 admission gate (`H7_ADMIT_MIN_CONTRACTS=5`,
`H7_ADMIT_MAX_SPREAD_PCT=0.05`) to EVERY leg.

**Eligibility rulings (platform-binding):** short straddles, short strangles,
naked risk-reversals, and ratio front-spreads are undefined-risk and NOT
ELIGIBLE as cards, ever. Cash-secured puts and covered calls are eligible but
do NOT fit the $600 defined-risk badge — their cards must say so explicitly
(collateral-sized / equity-sized risk, H4/H5 position-count caps instead).

| # | Setup | Class | Eligible? | Entry condition core | Vehicle & max loss | Hold | Key refusal |
|---|-------|-------|-----------|---------------------|--------------------|------|-------------|
| 1 | Long calls | Directional | YES | `iv_route=="call"` (IV/RV ≤ 1.00) + drawdown-reclaim or coil | premium ≤ $600 | ≤30 sess / +100% TP | route≠call; earnings-UNKNOWN; leg liquidity |
| 2 | Long puts | Directional | YES (new — no repo precedent routes puts) | IV cheap vs RV + breakdown trigger | premium ≤ $600 | ≤30 sess | put-side liquidity often worse — check separately |
| 3 | Call debit spreads | Directional | YES | `iv_route=="spread"` (IV/RV 1.00–1.15) | net debit; width-based | ≤30 sess / 75% of max value | either leg fails strict gate |
| 4 | Put debit spreads | Directional | YES (new) | same, put side | net debit | ≤30 sess | same |
| 5 | Straddles (LONG only) | Vol-expansion | YES; SHORT excluded | low-to-mid `iv_rank` or catalyst; per-name realized/implied context printed (E1: NVDA median 0.60 — caution) | both premiums; $600 squeeze on rich names — per-name feasibility check required | 10–15 sess or event-bounded | leg liquidity; iv_rank NaN |
| 6 | Strangles (LONG only) | Vol-expansion | YES; SHORT excluded | as #5 + strike density | both premiums (cheaper) | as #5 | OTM legs re-gated, not inherited |
| 7 | Calendars | Vol-expansion (long back vega) | YES | front IV rich vs constructed ~90d slope; low `rv_percentile` | net debit | through front expiry, never naked into back | slope not computable (build first); earnings in front leg unless #14 variant |
| 8 | Diagonals | Directional + term | YES | #7 condition + directional trigger | net debit | through front expiry | ITM-leg premium itself > $600 |
| 9 | Backspreads (long-heavy ratio ONLY) | Vol-expansion | YES (1×2 long-heavy); front-spreads OUT | cheap wing IV / catalyst | max loss AT the long strike — check THAT vs $600, not the debit | catalyst-bounded, exit before max-loss zone | 3-leg cost drag; any leg fails strict gate |
| 10 | Cash-secured puts | Vol-collapse | YES, NOT $600-badged | H5 gates (IVR ≥ 0.5, cushion, VRP proxy ≥ 0) | collateral-sized (strike×100 − credit); H4_CSP_MAX_POSITIONS=1 | 21-DTE/50% owner convention | H5 amber fails; earnings-UNKNOWN |
| 11 | Covered calls | Vol-collapse | YES, NOT $600-badged; requires held shares | H5 CC gates + upside room | stock-side risk; premium is small offset | 21-DTE/50% | no 100-share lot declared |
| 12 | Defined-risk credit spreads | Vol-collapse | YES — best cap fit (H7c precedent) | `iv_route=="h7c"` (IV/RV ≥ 1.25); credit ≥ 30% width | width − credit | 30–45 DTE, hard close 7 DTE; TP 50%; stop 2× | NEVER through earnings (registered rule); H7C_MAX_CONCURRENT=1 |
| 13 | Pre-earnings long-vol | Vol-expansion | YES | gate CLEAR + confirmed date; entry T-15..T-8; IVR ≤ 0.50; name's measured run-up ≠ ~0 (NVDA structurally refused per E1) | premium ≤ $600 | hard close T-2, never through print | estimated/aggregator date (fail closed) |
| 14 | Post-earnings crush (defined-risk ONLY) | Vol-collapse | YES as credit spread; naked short excluded | event `occurred`; IV still rich post-print; short tenor per E1 2–4× crush asymmetry | width − credit | days, not weeks | still pre-report (that's #13); no crush premium left |
| 15 | Term-structure trades | Relative-value | YES (calendar vehicle) | meaningfully positive constructed slope | net debit | through front leg | back-tenor liquidity unproven on thin names |
| 16 | Skew trades (two-vertical construction ONLY) | Relative-value | YES; naked RR excluded | 25Δ skew large net of costs + direction consistent | each vertical defined-risk | ≤30–45 sess | 4 legs — expect frequent refusals (wings fail on ~half the universe) |
| 17 | Single-stock vs index vol | Relative-value | DESCRIPTIVE-ONLY | RV-ratio line now buildable (SPY/QQQ closes cached); IV comparison blocked until index chains resume | n/a — no structure | n/a | must render as "descriptive only", never silently vanish |
| 18 | Stock-vs-cluster relative vol | Relative-value | YES (two independent verticals) | name's `iv_rank`/`iv_minus_rv` an outlier vs same-day cross-section (z-score field = new build) | each vertical ≤ $600 alone | 30–45 sess | either name's liquidity; z-score not built |
| 19 | Related-pair RV (VST/CEG, NVDA/AMD) | Relative-value | YES (two verticals) | pair gap large vs measured co-movement baseline (new build; do not assume pair correlation — measure first) | each vertical ≤ $600 | DTE-matched | idiosyncratic-catalyst decoupling check on exit |

Per-card prose fields (edge hypothesis, profit/failure paths, exit
alternatives, sizing arithmetic) are retained in the design subagent's full
text, archived in the session transcript and reproducible from this table +
the constraints above; the table is the binding surface for Codex briefs.

**Cross-cutting refusal rules:** any leg failing OI/spread; `earnings_gate ==
UNKNOWN` (fail closed); features NaN (warmup); undefined-risk structure
requested (never rendered); combined premium/max-loss over the applicable cap
without the card saying which cap applies.

---

## Workstream D — earnings variance decomposition (EOD-implementable)

Reuses `h7_earnings` gating (point-in-time, `GATE_CLEAR`/`occurred`,
`source_type != aggregator`), `features.py` conventions, and the BS layer.
Descriptive-first: measurement records, never a verdict; claim-discipline
labels on every interpretive output.

### 1. Option-market event variance

`E` = confirmed report date; `T1` = last expiration strictly before the report
session; `T2` = first on/after; `τᵢ` in years (calendar/365); `ivᵢ` = ATM IV
computed for the SPECIFIC bracketing expirations (new extraction, not the
feature-frame column).

```
TV1 = iv1²·τ1        TV2 = iv2²·τ2
diffusive_rate (a, primary):  (TV3 − TV2)/(τ3 − τ2)   with T3 = next clean
                              (no-event) expiration after T2, gate-checked
diffusive_rate (b, fallback): rv21² over an earnings-week-EXCLUDED trailing
                              window (features.py earnings_week flag);
                              labeled "ex_earnings_trailing_rv", Inference
σ²_evt = (TV2 − TV1) − diffusive_rate·(τ2 − τ1)
implied_1day_event_move = sqrt(σ²_evt)      # single-session injection —
                                            # a modeling Assumption, labeled
```

**Bid/ask bands:** invert bid-IV and ask-IV per leg via the BS layer; band
σ²_evt with the minimizing and maximizing combinations →
`event_variance_low/high`. Forward events: real `r` (sourced curve), `q` once
the dividends CSV lands. Historical events: `band_status =
"assumption_flat_rate"` (labeled) or point-only — never a silent unbanded
point estimate.

### 2. Physical event-jump estimate

E1 conventions exactly (`analysis/earnings_event_vol_study.py`): `T-1`/`T+1`
around the report using `session_timing` (bmo/amc) from the v3 gating store
(authoritative), `realized_move_1d = close(T+1)/close(T-1) − 1`.
Cluster-move removal: subtract same-day mean return of the other 14 names —
labeled approximation; upgrade path = beta-adjusted residual vs QQQ (closes
now cached). Shrinkage for thin names:
`w = n/(n+k)`, k = 4 (owner-typed draft), `shrunk = w·name_mean_abs + (1−w)·cluster_mean_abs`;
AMD/AVGO currently have n=0 local occurred events → full cluster estimate,
which is the honest behavior.

### 3. Study windows and measurements

| Window | Record |
|---|---|
| T-10, T-5 | iv1, iv2, slope, rv_percentile, running σ²_evt (its drift = run-up diagnostic) |
| T-1 | frozen pre-event snapshot: σ²_evt point + band, implied 1-day move, slope |
| T+1 | realized/residual move; crush on the surviving tenor; T2-straddle conservative EOD mark |
| T+3/5/10 | continued straddle marks; slope renormalization; cumulative move (drift check) |

### 4. Refusal conditions

No bracketing pair; gate not CLEAR/occurred from a non-aggregator source;
crossed/zero-bid ATM on T1/T2/T3; τ1 < 2 trading sessions (real calendar via
`trading_days()`); standard liquidity gate on both ATM legs.

### 5. Per-event record schema

As drafted by the design agent: identity + gate provenance (record ids),
per-tenor IV/bid/ask/liquidity, diffusive method, variance point + band +
`band_status`, tenor gap + `listing_density_flag`, realized/residual moves,
shrinkage fields, window snapshots, refusal reason, chain-manifest provenance.

### 6. Expiration-density pre-check (required, per name)

Never assume weeklies. Measure trailing ~90-day mean gap between consecutive
listed expirations per name BEFORE running; record `listing_density_flag`.
TEM/CRWV/USAR are the expected LOW_PRECISION names (large tenor gaps dilute
event variance into diffusive noise and may kill the clean-T3 method).
