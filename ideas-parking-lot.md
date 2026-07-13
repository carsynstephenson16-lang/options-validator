# Ideas parking lot

Not-now, not-rejected. Per the scope guard: an idea lands here when it does not
move the current phase to a verdict. Pull one out only with an explicit owner
decision (and, where noted, a pre-registration first).

## Attractiveness-scanner enrichment (parked 2026-07-06)

Context: the seller lanes now carry a `vrp_for_seller` VRP-*proxy* badge
(front-month IV vs trailing 21d realized -- descriptive, horizon-mismatched,
never a forecast; see `H5_VRP_SELL_GREEN` in config.py). The two ideas below
were proposed alongside it in an external deep-research report. They are
valuable but bigger and easier to overfit, so they wait.

### Term-structure signal (front vs back-month IV)
- **What:** an IV30/IV90 (contango/backwardation) badge or ranking input.
- **Why parked:** needs a second ATM-IV tenor added to the feature layer
  first; and once it *ranks* candidates it becomes fittable logic.
- **Gate before building:** owner decision + **pre-register** the exact tenors,
  threshold, and grading rule in the ledger before it influences any ranking.
  Descriptive-only display could ship earlier, but must not order candidates
  until pre-registered.

### Event-edge signal (implied move vs realized event move)
- **What:** compare the option-implied move into an earnings/event to the
  *historical realized* move over the last N like events.
- **Why parked:** needs an event-move history dataset and a validation design;
  highest overfit risk of the three (small event samples, look-ahead traps).
- **Gate before building:** owner decision + **pre-register** the event window,
  the "N like events" definition, the implied-move source, and the accept/reject
  thresholds *before* it grades or ranks anything. This is a hypothesis, not a
  display tweak.

## Cross-sectional richness signals (parked 2026-07-07)

Context: an external framework proposed a 10-point weighted score
(regime + stock-IV-edge + IV-rank + liquidity + chart-quality, summed, bucketed
Attractive/Watchlist/Skip). The **composite score and the Attractive/Skip
suggestor are rejected**, not parked -- same reason as the TAOV scalar below
(unfitted weights destroy per-dimension honesty; a bucketed action call is a
suggestor, out of scope per `.cursorrules`). IV-rank and liquidity already ship
as honest per-dimension badges/gates (`H5_IVR_*`, `MIN_OPEN_INTEREST`,
`MAX_SPREAD_PCT`). Chart-quality is discretionary narrative -> belongs in the
equity-research repo (see rejected list below). The two ideas here are the only
salvageable, genuinely-new pieces: descriptive richness badges, display-only,
never a ranking.

### Market-regime badge (VIXEQ minus VIX)
- **What:** average single-stock implied vol (VIXEQ) minus index implied vol
  (VIX). A high spread means single-stock options are rich vs index options
  (a low-implied-correlation regime). Economically ~ Cboe implied-correlation.
- **Why parked:** (1) **No data** -- the repo has no VIX or VIXEQ feed; the
  universe is four ThetaData single-name chains. (2) It is a **market-wide**
  reading, not a per-name screen -- it gates all four names together, it cannot
  rank them against each other. (3) The "spread above 25" threshold is
  asserted/unfitted.
- **Assumption to pin down first:** that "VIXEQ" maps to a *published,
  fetchable* average-single-stock-vol index. Source must be identified before
  anything is built; this repo cannot compute an S&P-500 average from four names.
- **Gate before building:** owner decision + a verified VIX/VIXEQ data source
  + **pre-register** the threshold and grading rule in the ledger before it
  grades anything. Descriptive display may ship earlier; must not order
  candidates until pre-registered.

### Per-name richness badge (stock IV30 minus VIXEQ)
- **What:** a name's 30-day ATM IV minus VIXEQ -- positive means this name is
  richer than the average S&P 500 stock.
- **Why parked:** (1) needs the same VIXEQ feed (same blocker). (2) **Overlaps
  existing signals** -- `vrp_for_seller` (IV vs trailing realized) and
  `H5_IVR_*` (IV vs the name's own 1yr history) already answer "is this rich";
  a third richness axis risks double-counting. (3) The "IV30 above VIXEQ by 5+"
  threshold is asserted/unfitted.
- **Gate before building:** owner decision + VIXEQ source + **pre-register** the
  threshold + a demonstration that it adds signal *beyond* the existing VRP
  proxy and IV-rank badges (don't add a redundant axis).

## Volatile-name drawdown-reversal scanner + probability layer (parked 2026-07-09)

Context: owner proposal 2026-07-09 — a daily watcher over high-beta AI names
(CRWV, TEM, PLTR, NOW, VST, CEG; possibly microcaps) that catches names at the
bottom of a drawdown and buys calls/LEAPS into the recovery, short- and
long-horizon variants; plus a TradingView/Pine chart layer, recovery-probability
forecasts, and Kelly/Sharpe-based identification. Standing rule (Operating
Manual 2026-07-06): nothing new gets built until the first verdict lands.
Related, already-recorded facts: the 2026-07-08 H6 liquidity screen
(facts `H6_DATA_PULL`; H6 registration in `experiments.jsonl`) tested most of
this universe on real chains — **SMCI/NOW/CRWV/TEM/HYLN failed the liquidity
gates; CEG's 45–90DTE call legs failed MAX_SPREAD_PCT; NVDA/PLTR/AMZN passed
and are live in H6** (post-earnings tactical long calls).

### Mechanical drawdown-reversal entry signal (H7 candidate)
- **What:** a pre-registerable entry trigger of the form
  drawdown-from-52w-high ≥ X% AND mechanical reversal confirmation (e.g. close
  above the N-day high) AND IVR ≤ Y AND both-leg liquidity gates; instrument =
  defined-risk long calls / LEAPS; exits and kill criteria frozen at
  registration; verdict gates on losses. The systematic version of "catch the
  bottom, ride the recovery."
- **Why parked:** does not move H5/H6 to a verdict. Chart-reading as
  discretion was already rejected 2026-07-07 (belongs in the equity-research
  repo) — this survives only as coded, testable signals. Most of the proposed
  universe fails today's liquidity gates (above). CRWV/TEM listing history
  (Assumption: 2025 / 2024 IPOs — verify) is too short to backtest drawdown
  "cycles"; names with real history (MSFT/AMZN 2018+, PLTR in the legacy
  cache) could support a base-rate study, but the window design must respect
  the sealed legacy holdout (reveal budget 0/3).
- **Gate before building:** first H5/H6 verdict lands (or an explicit owner
  override logged in the ledger) + owner decision + pre-registration with a
  mechanical universe rule (e.g. "optionable, passes OI/spread gates on both
  legs"), frozen X/Y/N, exits, and the numeric result that rejects it. Any
  threshold an LLM proposes is LLM-asserted until tested; owner enters the
  frozen numbers herself.

### Market-implied probability readout (small; display-only)
- **What:** risk-neutral P(close ≤ level by expiry) for the four names, read
  from the cached chains — e.g. "P(VST ≤ $140 by Dec)" next to `entry_watch`.
  The honest substitute for asking an LLM to predict recoveries with
  probabilities. Labeled risk-neutral ≠ real-world on the display.
- **Why parked (lightly):** display-only and cheap (no new data), but it must
  never grade or rank without pre-registration; needs a one-page spec first.
- **Gate:** owner nod + short spec.

### TradingView / Pine chart layer
- No TradingView MCP is connected to this environment (checked 2026-07-09),
  and Pine cannot join ThetaData chains. The 2026-07-07 decision already
  routed discretionary chart reading to the equity-research repo. If a chart
  signal matters here, it gets coded (pandas on cached closes) and
  pre-registered like any other rule — see H7 above.

### Kelly / Sharpe layer
- Kelly and Sharpe size and evaluate a *measured* edge; they cannot identify
  mispricings. Kelly becomes relevant only after a hypothesis survives its
  window with a positive expectancy CI after costs — then it's a `config.py`
  sizing decision with its own registration. Until then
  MAX_LOSS_PER_TRADE / RISK_SLEEVE govern.

### Microcaps / combining projects
- HYLN's entire chain was ~128 rows/day in the 2026-07-08 pull; microcap
  options broadly cannot pass MIN_OPEN_INTEREST / MAX_SPREAD_PCT, so a
  microcap options scanner has no tradable output under this repo's cost
  model. Microcap *equity* ideas belong in the equity-research book; the
  cross-book review covers the portfolio view.

**Review date:** at the first H5/H6 verdict, or the 2026-10-06 quarterly
audit, whichever comes first.

## AVGO entry for the closes SPLITS registry (parked 2026-07-12)

`data/underlying_closes.SPLITS` has no AVGO entry, so the Yahoo-sourced
closes store carries split-ADJUSTED pre-2024-07-15 closes for AVGO (10-for-1,
Official-source: company 8-K) instead of raw ones aligned with raw strikes.
Verified 2026-07-12 via a no-reveal discontinuity check; the store state is
reproducible, not corrupted. Nothing live consumes pre-split AVGO closes —
H7 is forward-only and the historical diagnostic is permanently retired — so
this gates nothing today. If any future authorized work reads AVGO closes
before 2024-07-15, add the SPLITS entry (first split-adjusted trade
2024-07-15, ratio 10.0) test-first and re-pull before trusting that span.

**Review date:** before any arc that consumes pre-2024 AVGO history.

## Explicitly rejected (not parked)

From the 2026-07-06 deep-research report (and the 2026-07-07 10-point
framework, whose composite score + Attractive/Skip suggestor + chart-quality
axis are rejected for the same reasons):
- Composite weighted `TAOV` scalar -- unfitted weights; destroys per-dimension
  honesty. Do not build.
- Ranked trade-suggestor with named structures (iron fly, short straddle) --
  that is a suggestor, out of scope per `.cursorrules`.
- Ticker-specific narrative scores (regulatory/weather/segment) -- discretionary
  contamination; belongs in the equity-research repo, not a systematic screen.
