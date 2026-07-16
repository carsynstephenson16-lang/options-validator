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

## TradingView plugin — read-only chart/alert layer (parked 2026-07-13)

Idea: surface the H5/H6/H7 forward-paper watcher signals on TradingView
charts (read-only visualization + alerts), not a new data or execution path.

Triage: PARKED, weakly in-scope-adjacent at best.
- Does it move a live hypothesis to its verdict? No. The repo already renders
  this surface offline: `entry_watch`, `h7_watch`, `dashboard`, and
  `attractiveness_dashboard`. A TradingView chart layer duplicates existing
  output rather than advancing H5/H6/H7.
- Boundary risk (the reason to keep it parked, not just deferred):
  TradingView's differentiating features are webhook alerts and order
  routing. The moment the integration is useful beyond a static chart it
  points at the live-order boundary the repo's hook exists to forbid. A
  strictly read-only build is possible but is the redundant, low-value half.
- Standing rule: it is new tooling/account/spend before the first H5/H6 verdict
  exists — the same milestone the operating manual calls the "Phase-0 verdict"
  — which the one standing rule forbids. (Un-parking uses that identical
  milestone below, so it cannot license spend any earlier.)

If ever un-parked, constrain to: read-only pull FROM the repo's existing
signal outputs INTO a chart annotation; no webhooks, no broker connection, no
alert-to-execution path; and only after the Phase-0 verdict (the first H5/H6
verdict) frees the "nothing new" gate — the same milestone named above.

**Review date:** at the first H5/H6 verdict, or the 2026-10-06 quarterly
audit, whichever comes first.

## Qullamaggie momentum swing strategy (EP / Breakout / Parabolic short) (parked 2026-07-13)

Context: owner proposal 2026-07-13 — port Kristjan "Qullamaggie" Qullamägi's
momentum swing method: three setups (Episodic Pivot = gap-up >10% on news with
first-15-min volume, buy the opening-range high; Breakout = 2–8wk base surfing
the 10/20-day SMA, buy the breakout to new highs; Parabolic Short = fade a
100%+ vertical move after 3–5 green days), ADR-based stops, partial exits at
2R–3R + trail on the 10/20-day MA, universe from an external screener
(Finviz/TC2000/Deepvue: vol>500k, price>$5, 30–100% move / 3mo), backtested
"candle-by-candle, be brutally honest," paper-traded 3–6mo before capital.

Triage: PARKED, and blocked on two independent gates.
- **Standing rule:** it is new strategy/tooling/spend before the first H5/H6
  verdict — the Phase-0 milestone the operating manual forbids building past.
  Scope-guard answer: does it move H5/H6/H7 to a verdict? No.
- **Hard data mismatch (blocks it even under an override):**
  - EP entry is *intraday* (opening-range high, first-15-min volume). Repo is
    **EOD-only** (README known-limitation, Repo-verified). Untestable as
    specified without an intraday equity feed = new spend.
  - ADR stops need daily high/low; the repo stores daily *closes*, not OHLCV
    for arbitrary tickers (Inference — verify before building).
  - Open screener universe vs the fixed 12 names (`config.UNIVERSE` +
    `H7_WATCHLIST`) = new tickers, new data.
  - Parabolic **short** is out-of-mandate: repo is long-lanes-only,
    defined-risk options; the live-order boundary is hook-enforced.
  - "Candle-by-candle, be brutally honest" manual backtesting is precisely the
    look-ahead-prone, non-reproducible method the pre-registration + hash-chained
    ledger exist to replace. Any port must be mechanical and frozen-first.
- Relation to the 2026-07-09 drawdown-reversal park: that idea is
  mean-reversion (catch the bottom); this is momentum-continuation (ride the
  breakout) — opposite direction, identical gate (verdict-first + mechanical
  EOD signals + pre-registration).

Salvageable core if ever un-parked: the **Breakout** base/SMA/breakout signal
and the **Parabolic** consecutive-green-days signal are EOD-computable *if*
daily OHLCV is added; entries would be EOD approximations (next-day open/close),
never the intraday opening range. EP and ADR-intraday stops are unreachable on
EOD data.

Gate before building: first H5/H6 verdict lands (or an explicit owner scope
override logged in the ledger, as H7 was on 2026-07-09) + a verified daily
OHLCV data source for the chosen universe + **pre-registration** with a
mechanical universe rule, frozen setup thresholds (gap %, base length, ADR
multiple, R-multiple exits, MA trail), earnings handling, and the numeric
result that rejects it — owner types the frozen numbers herself (any threshold
an LLM proposes is LLM-asserted until tested).

**Review date:** at the first H5/H6 verdict, or the 2026-10-06 quarterly audit,
whichever comes first.

## Non-AI sector diversification watch-names (parked 2026-07-15)

Context: owner request 2026-07-15 following the deep-research report (7)
reconciliation (`reports/2026-07-15-deep-research-7-reconciliation.md` §3.4):
the whole current book — core VST/CEG/MSFT/AMZN plus the H7 story watchlist —
is ONE AI/semis/power factor, and adding more AI-adjacent names raises
concentration rather than lowering it. Three research subagents screened
healthcare, financials, and consumer/industrials/energy/materials lanes for
names with (1) non-AI primary revenue drivers, (2) liquid monthly options,
(3) low fundamental overlap with the AI cluster.

Full memo: `reports/2026-07-15-non-ai-diversification-candidates.md`.
Headline shortlist (fit-scored, all liquidity claims web-asserted and
UNVERIFIED against real chain data): UNH, LMT, XOM, V, PGR (8/10); JPM, BAC,
AXP, LLY, VRTX, COST, NEM (7/10). Equally important: the confirmed crossover
traps that must NOT be treated as diversification — FCX, CAT, PWR,
uranium/nuclear plays, ISRG, BX/APO/KKR, ICE, BLK (all now AI-capex stories
in costume).

Why parked and not built: adds tickers/scope; moves no live hypothesis (H5/H6/
H7) toward its declared verdict. Ticker selection is an owner decision.

Gate before un-parking: owner shortlist → liquidity vetting against real
chain data at the H7 admission bar (near-the-money OI + spread at monthlies)
→ measured return correlation vs the four-name core (free OHLCV suffices) →
a NEW pre-registered hypothesis (or owner-logged scope override) with
owner-typed frozen numbers. Note the ThetaData subscription lapses
~2026-07-29; chain-liquidity vetting is cheap only before then, per-pull
owner approval required.

**Review date:** at the first H5/H6 verdict, or the 2026-10-06 quarterly
audit, whichever comes first.

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
