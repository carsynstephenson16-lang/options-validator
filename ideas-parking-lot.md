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
