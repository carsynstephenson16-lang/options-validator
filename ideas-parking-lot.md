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



### Event-edge signal (implied move vs realized event move) — **PROMOTED 2026-07-15**

- **What:** compare the option-implied move into an earnings/event to the
*historical realized* move over the last N like events.
- **Status:** pulled from the lot by explicit owner decision 2026-07-15
(ledger fact EVENT_EDGE_UNPARKED; plan
`docs/superpowers/plans/2026-07-15-event-edge-phase-plan.md`). Phase E1 =
descriptive study only (grades nothing). The original gate still stands for
anything that grades or ranks: **pre-register** the event window, the
"N like events" definition, the implied-move source, and thresholds — all
owner-typed — before it influences any entry (that is Phase E2, not open).



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
  - **pre-register** the threshold and grading rule in the ledger before it
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
- **Measured a second time 2026-07-16 (IBEX, 72 contracts, median OI 0, median
spread 114.1%, 0/72 pass the gate — worse than HYLN).** Two of two microcaps
measured return unusable chains; this is no longer an inference from one
name. See the IBEX section below.

**Review date:** at the first H5/H6 verdict, or the 2026-10-06 quarterly
audit, whichever comes first.

## AVGO entry for the closes SPLITS registry (parked 2026-07-12 — **DONE 2026-07-15**)

Resolved: the SPLITS entry was registered and closes/OHLCV re-fetched raw on
2026-07-15 (commit 7c9bab7; ledger fact SPLITS_REGISTRY_AVGO). Kept below as
the historical record of why it was needed.

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
UNVERIFIED against real chain data **except UNH — measured 2026-07-16, see the
UNH/CRWD/ZS/NBIS section below**): UNH, LMT, XOM, V, PGR (8/10); JPM, BAC,
AXP, LLY, VRTX, COST, NEM (7/10). Equally important: the crossover
traps that must NOT be treated as diversification — FCX, CAT, PWR,
uranium/nuclear plays, ISRG, BX/APO/KKR, ICE, BLK (all now AI-capex stories
in costume).

**UNH measured 2026-07-16 (the shortlist's first real chain vetting):** deep
book — 2,201 contracts, 18 expirations out to 2028-12-15, near-the-money OI
1,000-6,700 — but only **1** contract clears the H7 admission bar (>=5 needed),
because EOD-snapshot spreads run 6-10% vs the 5% bar. Read that as an EOD
artifact pending intraday quotes, NOT as illiquidity. The wider lesson for this
section: the remaining shortlist's liquidity claims are still web-asserted, and
UNH shows the H7 admission bar can fail even a hyper-liquid mega-cap on EOD
data — so vet each name against real chains before trusting any 8/10 fit score.

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

## Options × equity-research bridge (parked 2026-07-15)

Owner-requested investigation done; full proposal in
`reports/2026-07-15-options-equity-research-bridge-proposal.md`. Three plugs,
all flowing options → equity-research, file-based, no code coupling:
(1) options-implied anchor row (implied forward / risk-neutral P(price≤X)) in
equity-research's §6F method table as an Independent-confirmation anchor;
(2) a Brier comparator — log market-implied P alongside the analyst's
P(beat SPY, 180d) and score both at T+180, testing whether the verdict engine
beats the options market, not just the 0.25 coin-flip baseline;
(3) sharing the Phase E1 event-vol tables as descriptive context. Micro-cap
options are ruled out by measured liquidity (HYLN ~128 rows/day, gates fail;
IBEX 0/72 pass the gate as of 2026-07-15 — see the IBEX section below, which
scopes this proposal to the ~10 liquid overlap names); micro-caps stay
equity-side in the existing kill-screen. Prerequisite for
(1)+(2) is the still-parked market-implied probability readout (owner nod +
one-page spec). The reverse flow — narratives into options gates — is
explicitly declined as discretionary contamination.

**Review date:** first H5/H6 verdict, ThetaData renewal decision (2026-07-25),
or 2026-10-06 quarterly audit, whichever comes first.

**Scope clarification 2026-07-22 (owner decision):** the *opposite* direction —
a read-only reader of equity-research's append-only market-updates store, into
this repo — was built and **stays** (`options_researcher.market_context`,
commit `4082141`, doc `docs/market-intelligence-bridge.md`). It is a
descriptive research-layer utility with zero callers on any strategy, trigger,
watcher, or receipt path; it does not move a live hypothesis toward its verdict
and is retained by owner decision, not by the scope gate. The three plugs
described above (options → equity-research) remain PARKED with the review date
unchanged, and narratives-into-options-gates remains declined.

## IBEX options expression of the equity-research LONG (REJECTED on measured data 2026-07-16)

Context: owner asked 2026-07-16 whether the equity-research book's IBEX pick
could be expressed through options. Owner authorized one paid ThetaData pull to
settle it. This is the first *measured* test of the microcap-options claim that
the two sections above (Microcaps / combining projects; the bridge proposal)
had been asserting from HYLN alone.

**Measured, IBEX EOD chain @ 2026-07-15** (one ThetaData call; cached at
`.cache/chains/IBEX_2026-07-15.parquet`; `allow_oos=True` disclosed look — IBEX
sits in no hypothesis and no sealed holdout, so no OOS reveal budget was spent):


| Symbol                                   | Contracts | Expirations | Median OI | Median spread | Pass `passes_liquidity` |
| ---------------------------------------- | --------- | ----------- | --------- | ------------- | ----------------------- |
| **IBEX**                                 | **72**    | **4**       | **0**     | **114.1%**    | **0 (0%)**              |
| HYLN (already H7_EXCLUDED, "dead chain") | 128       | 4           | 115.5     | 35.8%         | 2 (1.6%)                |
| PLTR                                     | 2,383     | 19          | 307       | 4.88%         | 1,054 (44%)             |
| NVDA                                     | 3,847     | 25          | 554       | 4.82%         | 1,755 (46%)             |
| AMZN                                     | 2,384     | 23          | 293.5     | 4.55%         | 1,132 (47%)             |


IBEX is materially **worse than the name this repo already excludes as dead**:
half HYLN's contract count, median OI of zero, spreads ~3x HYLN's and ~23x the
live names'. Exactly one contract in the whole chain clears
`MIN_OPEN_INTEREST` (Sep $45C, OI 419) and it has a **zero bid**. 29 of 72
contracts are zero-bid. Zero contracts clear `MAX_SPREAD_PCT` (10%) — or even
43%. (Reference rows for HYLN/PLTR/NVDA/AMZN computed offline from the existing
cache, dates 2026-07-15 except HYLN 2026-07-07.)

Two independent reasons this is rejected, either sufficient on its own:

- **The chain does not reach the thesis horizon.** Longest IBEX expiration is
2026-12-18 (~5 months). The equity-research thesis is a *12-month* re-rating
to $45.61 base. No instrument survives to the horizon being traded.
- **The spread exceeds the thesis.** Best available expression (Dec $35C,
bid 3.10 / ask 6.70, OI 12) fills at ~37% above mid, breakeven $41.70 by Dec
= **+19.7% required in 5 months** against a 12-month base-case target, with
the $20.88 bear case a **-100%** option outcome. Round-tripping the Sep $35C
(buy 3.80 / sell 1.80) loses **53% to the spread alone** on a correct thesis
with no stock move.

Note the shape of the finding: **the thesis was never the blocker.** A
P(beat SPY, 180d) = 0.58 view with a slow, catalyst-free 12-month horizon and
no scored calibration record yet (first T+180 outcomes resolve ~2026-11-05) is
the kind of thesis options carry worst — and this chain would fail for a thesis
we liked far more. The illiquidity that forced equity-research to cut IBEX from
Kelly-implied 8.0% to a final 1.5% *propagates into the derivative*; it does not
disappear there. The honest expression of an IBEX view is shares, at the size
the other book already set.

**Generalization (this is the reusable part):** any microcap graduating from
equity-research's EDGAR kill-screen (~$20M-$500M) should be expected to fail
this repo's liquidity gate the same way. Two of two microcaps measured (HYLN,
IBEX) return unusable chains. The bridge proposal above should therefore scope
itself to the ~10 liquid overlap names (VST, CEG, AVGO, NVDA, TEM, CRWV, IREN,
NOW) and treat kill-screen microcaps as equity-side only — which is what its
own §"Micro-cap options are ruled out" already says, now on measured rather
than inferred grounds.

Un-parking gate (should not be needed): a re-measured IBEX chain clearing
`MIN_OPEN_INTEREST` and `MAX_SPREAD_PCT` on both legs at a tenor that reaches
the thesis horizon. Absent that, do not re-ask this question per-ticker — the
gate is mechanical, run it before any analysis. Note the ThetaData subscription
lapses ~2026-07-29; per-pull owner approval required.

**Review date:** do not review per-ticker. Revisit only if the bridge proposal
is un-parked, or at the 2026-10-06 quarterly audit.

## UNH / CRWD / ZS / NBIS — measured chains + H7 story scan (parked 2026-07-16)

Context: owner authorized 4 paid ThetaData pulls (UNH, CRWD, ZS, NBIS) on
2026-07-16; IREN and the reference names came free from the existing cache.
Two questions were asked of the data: (a) do these chains clear the H7
admission bar, and (b) does the H7 story scan fire on any of them today.
**Nothing was added to any universe; no config or ledger write.** OOS reveal
budget untouched (0/3) — none of these names sits in a sealed holdout.

**Measured @ 2026-07-15** (`allow_oos=True` disclosed look; chains cached in
`.cache/chains/`). ADMIT column = the real H7 bar: `H7_ADMIT_MIN_CONTRACTS`
(>=5) near-the-money (+/-10% spot) monthly contracts at 30-120 DTE with
spread <= `H7_ADMIT_MAX_SPREAD_PCT` (5%) and OI >= `MIN_OPEN_INTEREST` (100):


| Symbol     | Contracts | Exps | Longest    | Median OI | Median spread | Pass 10% gate | ADMIT (>=5 @5%)      |
| ---------- | --------- | ---- | ---------- | --------- | ------------- | ------------- | -------------------- |
| NBIS       | 2,232     | 19   | 2028-12-15 | 112       | 5.29%         | 634 (28%)     | **7 — admits**       |
| CRWD       | 3,618     | 18   | 2028-12-15 | 97        | 10.50%        | 797 (22%)     | **8 — admits**       |
| IREN       | 1,588     | 18   | 2028-09-15 | 176.5     | 15.11%        | 258 (16%)     | **5 — bare minimum** |
| ZS         | 1,662     | 17   | 2028-06-16 | 25        | 12.68%        | 135 (8%)      | **4 — fails by one** |
| UNH        | 2,201     | 18   | 2028-12-15 | 40        | 12.23%        | 305 (14%)     | **1 — fails**        |
| PLTR (ref) | 2,383     | 19   | —          | 307       | 4.88%         | 1,054 (44%)   | 31                   |
| NVDA (ref) | 3,847     | 25   | —          | 554       | 4.82%         | 1,755 (46%)   | 69                   |
| AMZN (ref) | 2,384     | 23   | —          | 293.5     | 4.55%         | 1,132 (47%)   | 71                   |
| IBEX (ref) | 72        | 4    | 2026-12-18 | 0         | 114%          | 0 (0%)        | 0                    |


All five are real, deep chains with LEAPS to 2027-28 — categorically unlike
IBEX above. But all sit *marginally* over the bar (5-8 admitted contracts) vs
the incumbents' 31-71. Note **IREN — already a live H7 watchlist name — admits
at exactly 5, one contract from failing.** That fragility is worth knowing.

**The UNH failure is an EOD-snapshot artifact, not illiquidity — do not cite
it as "UNH options are untradable."** UNH's near-the-money OI runs 1,000-6,700
contracts (Aug $400C: OI 6,776); what fails is only the 5% *spread* bar, with
NTM quotes at 6-10%. **Inference (unverified):** ThetaData EOD chains come from
the 17:15 ET report and market makers widen at the close, so EOD spread%
systematically overstates the true intraday tradable spread. This repo is
EOD-only (README known limitation) and **cannot settle it** without an intraday
feed = new spend. The caveat applies to every row but only changes the marginal
calls (UNH, ZS); it cannot rescue IBEX (median OI 0, 114% spreads, 5-month max
expiry are not snapshot artifacts). Relative ranking stays valid — one basis.

**H7 story scan @ 2026-07-15 — all three route** `none`**. Nothing fires.**
Computed via `options_researcher/h7_signals.py` (the single decision
authority), registered measure: RV = `H7_RV_LOOKBACK_D` 21d annualized
close-to-close on *adjusted* closes; IV = ATM call at expiration nearest 90 DTE
(`H7_IV_TENOR_DTE_BAND` 72-108).


| Symbol     | Spot   | RV21   | IV90   | IV/RV      | Route    | Why                                                      |
| ---------- | ------ | ------ | ------ | ---------- | -------- | -------------------------------------------------------- |
| CRWD       | 206.77 | 57.3%  | 66.1%  | **1.1523** | `none`   | misses lane_b by **0.0023** (`H7_IV_PAR_K`=1.15)         |
| NBIS       | 199.51 | 110.9% | 130.2% | **1.1734** | `none`   | dead zone between 1.15 and 1.25                          |
| ZS         | 148.19 | 52.0%  | —      | —          | `none`   | **no expiry in the 72-108 DTE band** -> `atm_iv_90d`=0.0 |
| IREN (ref) | 38.28  | 85.7%  | 118.6% | 1.38       | `h7c`    |                                                          |
| PLTR (ref) | 133.76 | 57.5%  | 58.8%  | 1.02       | `spread` |                                                          |
| NVDA (ref) | 212.50 | 39.4%  | 43.0%  | 1.09       | `spread` |                                                          |


- **CRWD is a MISS at 1.152272, not a "basically par."** Recording the exact
figure precisely so it is never rounded into a pass later. A threshold that
gets rounded toward when inconvenient is not a threshold. Single-day
snapshot — the ratio moves daily and could route `spread` tomorrow; that is
an argument to watch, never to fudge.
- **NBIS** at 1.17 is *too rich to buy premium, not rich enough to sell it* —
the 1.15-1.25 dead zone doing its job. Its 111% RV / 130% IV is the market
pricing NBIS as the same high-vol AI story IREN gets.
- **ZS** is out twice: no IV at the registered tenor AND admission fails (4<5).

**Factor overlap (checked per the standing correction that the book is ONE
AI/semis/power factor):** 4 of these 5 deepen that factor — NBIS is an AI
neocloud (the CRWV/IREN trade in costume), IREN is already H7, CRWD/ZS are
high-beta growth tech that co-moves with it. **UNH is the only genuine non-AI
diversifier** — and it is the one that fails the bar (artifactually). Owner
clarified 2026-07-16 that NBIS/CRWD/ZS were scanned as **H7 story candidates,
not as diversification**, so the overlap is context here rather than a defect —
but it stands as a caution: adding NBIS would raise factor risk while feeling
like progress.

**Nothing here is actionable without a registration.** None of the three is in
`H7_WATCHLIST`; admission requires an **owner-typed ledger amendment** (the
`H7_AMENDMENT_V1_5` / `V1_6` pattern that admitted IREN and USAR). NBIS and ZS
carry **no earnings data** in `data/earnings/calendar.csv`, so source health
would read UNHEALTHY -> per-name entry ban under amendment v1.4 (the CRWV
precedent). **CRWD is the only one of the three with earnings provenance on
file**, which — with 8-contract admission and a ratio 0.0023 off a lane — makes
it the only real candidate of the batch. It is also new scope before the
Phase-0 verdict, which the standing rule forbids.

Verified rather than assumed while doing this (both corrected a stale prior):

- **IREN source health is CLEAR** (14/14 healthy, next report 2026-08-27) — an
earlier note that IREN was entry-banned on UNHEALTHY source health is stale.
- **NBIS carries no Yandex/YNDX entity contamination.** Its free Yahoo history
starts 2024-10-21 at the re-listing, so **no** `H7_SIGNAL_CLOSES_START` **floor
is needed** (unlike USAR's pre-2025 IPXX SPAC shell). Checked because the
ticker was renamed from YNDX; the trap did not materialize.

Side effect: free Yahoo closes for CRWD/ZS/NBIS now sit in `.cache/underlying`
(gitignored, disposable, consumed by nothing — no config references them).

Gate before un-parking: first H5/H6 verdict (or an owner-logged scope override,
as H7 got 2026-07-09) + owner-typed `H7_AMENDMENT` naming the ticker + an
earnings source for NBIS/ZS + a re-measured admission at entry time (these
cleared by 5-8 contracts; that margin can vanish). ThetaData lapses ~2026-07-29
— re-measurement is cheap only before then, per-pull owner approval required.

**Review date:** at the first H5/H6 verdict, the ThetaData renewal decision
(2026-07-25), or the 2026-10-06 quarterly audit, whichever comes first.

## `config.UNIVERSE` is misleadingly named (parked 2026-07-16 — future cleanup)

Context: on 2026-07-16 the owner asked to "add all the tickers above to
universe" (IBEX/UNH/CRWD/ZS/NBIS). The request was declined on the evidence
(see `reports/2026-07-16-h7-amendment-v1_7-proposal.md`), but it surfaced a
real defect worth fixing later: **the name** `UNIVERSE` **invites exactly the wrong
mental model, and it sits on top of the risk math.**

The trap, precisely:

- `UNIVERSE` reads as "the names I am allowed to trade." **It is not.** Proof:
H6 trades NVDA/PLTR/AMZN and *neither NVDA nor PLTR is in* `UNIVERSE`. The
registered hypotheses freeze their own name-sets in the ledger (H6's record
reads `Names NVDA/PLTR/AMZN`); `config.py:56` says so explicitly. Adding a
ticker to `UNIVERSE` makes **nothing** tradable.
- What it actually is: (1) the research/display set — dashboard rows, H5's live
evaluator (`options_researcher/attractiveness.py:425` iterates it), tradability
profiling; (2) **a denominator in the risk math** — `config.py:36-38` sizes
simultaneous exposure as `MAX_LOSS_PER_TRADE x len(UNIVERSE)`.
- Consequence of the confusion, in dollars: adding 5 tickers would have moved
simultaneous at-risk from **$2,400 (17.1% of the $14,000 sleeve) to $5,400
(38.6%)** with **no risk setting touched and no warning** — and because the
added names were all one AI factor, the $5,400 would be closer to one bet
than nine. The risk math would report diversification; the book would have
concentrated. `config.py:38` already flags that the current four "are
emphatically not 4 independent bets."
- Second-order: `UNIVERSE` edits also silently widen **H5's** live evaluator
scope (H5 alone reads the list at runtime; H6/H7 do not). A concurrent
session's in-flight `options_researcher/{live_quotes,live_dashboard}.py` also
iterate `config.UNIVERSE`, adding a live-preview row per name — display
scope, nothing more.
- **CORRECTION 2026-07-17 (owner-flagged):** an earlier draft of this note
claimed that path "requests paid quotes" and that adding names would give
`UNIVERSE` a spend-per-run consumer. **That is wrong — there is NO spend
argument attached to** `UNIVERSE` **size.** Read the code: `live_quotes.py` makes
**ONE BATCHED** `stock_snapshot_quote` call for the entire list (docstring at
~line 475: *"from ONE batched stock_snapshot_quote call"*), so cost is flat in
`len(UNIVERSE)` — 4 names and 9 names cost the same one call. The other call
site is a **one-shot manual** `--probe` (`run_probe`, invoked via
`python -m options_researcher.live_quotes --probe`), not a per-run request;
and a stock-entitlement denial does not even fail that probe — it falls back
to a put-call-parity spot. The claim was asserted without reading the module.
**The dollar case against widening** `UNIVERSE` **rests entirely on the risk
denominator above ($2,400 -> $5,400), which is real and unaffected by this
correction.** Do not re-import a spend argument here.
- Re-grep the call sites before any refactor; the list below was taken
2026-07-16 and will drift.

Candidate fix (NOT today's work): rename to something that cannot be misread as
permission — e.g. `RESEARCH_DISPLAY_NAMES` — and **separate the risk
denominator from the display list** so a display change can never move
exposure. The two responsibilities are conflated today; that conflation is the
actual bug, and renaming alone would only hide it.

Why parked, not built: pure refactor, touches `config.py` plus ~10 call sites
as of 2026-07-16 (`metrics.py`, `analysis/feasibility.py`,
`analysis/power_check.py`, `options_researcher/{features,attractiveness, dashboard,refresh,profile_monthlies,profile_tradability}.py`) — plus whatever
the in-flight `live_*.py` work adds — and the tests that assert the universe
count. Moves no live hypothesis toward its verdict — the scope-guard
answer is no. It is also exactly the kind of wide mechanical change that should
not land while H5/H6/H7 forward windows are running and a concurrent session is
active in the same checkout.

Gate before building: first H5/H6 verdict (the Phase-0 milestone) + a
test-first refactor that proves `len()`-based risk math is unchanged (or
deliberately re-derived with owner-typed numbers) BEFORE any rename lands. If
the risk denominator is split out, the new value is owner-typed, not inherited.

**Review date:** at the first H5/H6 verdict, or the 2026-10-06 quarterly audit,
whichever comes first.

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



## Insider-cluster pre-earnings signal (parked 2026-07-16, owner decision)

- **What:** blackout-aware opportunistic insider-cluster signal (Form 4,
T-45..T-15 window) from `reports/2026-07-16-pre-earnings-signal-research.md`
candidate 1 — the survey's best-evidenced signal (Cohen–Malloy–Pomorski).
- **Why parked:** owner directive 2026-07-16: "Do not pursue insider clusters
... now." The TSMC read-through and IV-direction studies were selected
instead (written tests only, no trade permission).
- **Gate before building:** explicit owner un-park + its own pre-registration
with owner-typed cluster definition, window, and null. The rare-event
statistics constraint (years to significance on 14 names vs an
option-surface null) must be confronted in the registration, not after.
- **Review date:** 2026-10-16 (or at the first quarterly cross-book review
after the H9 verdict lands).



## Black–Scholes descriptive-arc parked items (parked 2026-07-18)

Context: owner directed a Black–Scholes + QM arc 2026-07-18. Scoped down to a  
descriptive/data-quality layer only (spec  
`docs/superpowers/specs/2026-07-17-black-scholes-attractiveness-design.md`;  
Phase-1 plan `docs/superpowers/plans/2026-07-18-bs-descriptive-infrastructure.md`).  
A skeptical research subagent's brief (the arc's §-notes) found every BS  
"mispricing" signal collapses to either the [[variance risk premium]] (short  
vol) or a normalization tool. The items below were cut from that arc's scope and  
parked here so the cut is on the record, not just in the spec.

### BS "fair value vs market price" richness ranking — park-leaning-REJECT

- **What:** rank contracts by (BS theoretical value − market price) using some
  vol input, treat the largest residuals as "opportunities."
- **Why parked (nearly rejected):** the research brief flagged this as the
  **most self-deceiving** candidate — the residual is IV-minus-your-vol-input
  restated, i.e. short vol dressed as a pricing error, which hides the risk
  being taken. Same failure family as the rejected `TAOV` composite (see
  "Explicitly rejected"). It is recorded here, not built.
- **Gate before building:** would need an explicit owner override AND a
  pre-registration proving the residual carries signal *beyond* the existing
  `vrp_for_seller` / `H5_IVR_*` axes after costs — the same non-redundancy bar
  the VIXEQ richness park failed. Default expectation: it does not.

### Generic (non-earnings-conditioned) term/skew richness score

- **What:** a bare IV term-structure slope or skew-richness ranking column with
no earnings tag.
- **Why parked:** the research brief judged a term-structure feature defensible
*only* when earnings-conditioned (the E1/H8 template); stripped of the event
tag it degrades to VRP-in-disguise. The earnings-conditioned version IS in the
arc's scope (spec §6). This is the un-conditioned version, which is not.
Overlaps the "Term-structure signal (front vs back-month IV)" park above and
the "Cross-sectional richness signals" section — same gate: pre-register exact
tenors/threshold/grading before it orders anything.



### QM study rerun / fresh QM historical recomputation

- **What:** re-running `qm_study` on the current data vintage, or recomputing QM
signals over history, to get "fresh" numbers.
- **Why parked:** the QM one-run-per-vintage study is **spent**; a rerun is
attempt-#2 p-hacking (ledger-discipline rule 8). The arc instead *publishes* a
labeled `retrospective_result` from the existing hash-bound readings — no
rerun. See [[QM]] study facts `QM_STUDY_PREREG` / `QM_STUDY_RESULT` (parabolic
fade REJECTED, no H8 from either setup).
- **Gate before building:** a genuinely NEW data vintage (not the spent one) or
a new owner-typed pre-registration on unseen forward data — which is what the
H10a/H10b forward registrations in the arc are for.



### P&L backtest of any strategy on the big 4 (sealed-holdout)

- **What:** running a P&L backtest of a new BS/QM strategy on VST/CEG/MSFT/AMZN
over 2023+.
- **Why parked (really a standing guardrail):** those four are outcome-selected
(picked knowing the AI boom; README "Scope status"), so 2023+ is not a
credible blind holdout; the sealed legacy holdout is SPY/QQQ index data
(reveal budget 0/3) and does not test a single-name signal. No honest
historical dataset exists — forward paper is the only verdict path.
- **Gate before building:** does not un-park as a big-4 backtest at all; a real
test is a forward-paper pre-registration (H10 pattern).

**Review date:** at the first H5/H6 verdict, or the 2026-10-06 quarterly audit,
whichever comes first.

## 2026-07-18 — ET long-term exposure (equity/LEAPS, not H7 options)

Owner thesis: ET (Energy Transfer) is an energy player in the AI buildout and a
possible long-term play. Its listed options FAIL the frozen H7 liquidity gates
(~$20 spot, ATM spread ~10.5% > 10% cap; 0 contracts pass the strict 5%
admission gate), and the owner accepted that (ET_TRADABILITY_ACCEPTED,
facts.log) rather than loosening gates. If long-term exposure is wanted, the
honest vehicles are shares (outside this validator's scope) or a deliberate,
separately-registered LEAPS design that respects costs. Review date: next
cross-book review.





## 2026-07-21 — PRYMY (Prysmian S.p.A.) — structurally out of scope, no options exist
Owner asked for an analysis on "pry" / PRYMY. **This validator cannot analyze it:
PRYMY is an *unsponsored* ADR quoted OTC (OTCMKTS/Pink), not listed on NYSE or
Nasdaq.** OCC clears standardized options listed on a national securities
exchange and the underlying must meet the selecting exchange's listing
standards, so an OTC unsponsored ADR has no listed US options chain. The
"option chain" tabs on Yahoo / Benzinga / Seeking Alpha are template pages
rendered for every symbol, not evidence that contracts exist.

Consequences: no ThetaData chain to cache, no spread/OI liquidity gates to
evaluate, nothing for H5/H6/H7/H8 to consume. It also does not move any live
hypothesis toward its verdict, so it fails the README "Scope status" scope gate
independently of the data problem.

Concentration note: Prysmian is power/grid cable — the *same* AI-infrastructure
power factor the existing book is already concentrated in. Adding it would
increase, not diversify, that exposure.

Un-park gate: only if Prysmian lists an exchange-traded US ADR with an OCC
options chain that passes the frozen liquidity gates, AND it is written into a
registered hypothesis. Milan-listed PRY options are a different market
(non-US clearing, EUR, different hours) and are out of this repo's scope
entirely. Review date: next cross-book review.

## Primary Model Separation & Corner Indicator

We isolate the unconditional baseline from the conditional interaction to prevent $\gamma_1$ from being misinterpreted.

### Model 1: Primary Unconditional Model

$$R = \alpha + \beta_1 TS_c + \text{controls} + \varepsilon$$

- **Primary Hypothesis:** $\beta_1 > 0$ (Term-structure cross-sectional rank positively predicts net returns across the entire universe).

### Model 2: Secondary Interaction Model

$$R = \gamma_0 + \gamma_1 TS_c + \gamma_2 VRP_c + \gamma_3 (TS_c \times VRP_c) + \text{controls} + \varepsilon$$

- **Secondary Hypothesis:** $\gamma_3 < 0$.
- **Reporting Mandate:** We report the marginal TS effect ($\frac{\partial R}{\partial TS_c}$) at the 20th ($v=0.20$), 50th ($v=0.50$), and 80th ($v=0.80$) VRP percentiles:
  $$\text{TS effect at VRP rank } v = \gamma_1 + \gamma_3(v - 0.50)$$

### Model 3: Explicit Corner Indicator

$$R = \alpha + \beta_1 TS\_rank + \beta_2 VRP\_rank + \beta_3 \text{High\_TS\_Low\_VRP} + \text{controls} + \varepsilon$$

- **Definition:** `High_TS_Low_VRP = ((ts_percentile >= 0.80) & (vrp_percentile <= 0.20)).astype(int)`
- **Hypothesis:** $\beta_3 > 0$ (The corner provides incremental alpha beyond the sum of the linear main effects).
- **Sparsity Gate:** The regression for date $T$ is skipped if $\sum \text{High\_TS\_Low\_VRP}_{i,T} < 15$.

## 2. Hardened Liquidity Gates & Contract Selection

All upstream metadata and relative-spread requirements are now explicitly enforced inside the contract-selection engine prior to strike matching.

Python

```
MAX_RELATIVE_SPREAD = 0.15

# 1. Metadata & Snapshot Verification
required_cols = ["data_available_at", "quote_timestamp", "snapshot_id", "quality_rule_version"]
if chain_df[required_cols].isna().any().any():
    return pd.Series({"rejection_reason": "invalid_snapshot_metadata"})

# 2. Strict Point-in-Time & Liquidity Filtering
mid = (chain_df["bid"] + chain_df["ask"]) / 2.0
valid_df = chain_df[
    chain_df['option_type'].isin(['C', 'P'])
    & chain_df['is_standard_contract']
    & ~chain_df['is_crossed']
    & ~chain_df['is_stale']
    & ~chain_df['is_zero_bid']
    & (chain_df['bid'] > 0)
    & (chain_df['ask'] >= chain_df['bid'])
    & ((chain_df["ask"] - chain_df["bid"]) / mid <= MAX_RELATIVE_SPREAD)
    & chain_df['dte'].between(25, 46)
    & (chain_df['data_available_at'] <= signal_cutoff)
    & (chain_df['has_unresolved_corp_action'] == False)
].copy()

```

## 3. Early Assignment & Dividend Treatment

To eliminate early assignment distortions on American options while keeping the pure factor research clean, we adopt **Option A**:

- **Rule:** Any ticker with a known ex-dividend date falling between $T$ (signal date) and $T+6$ (holding period exit) is strictly excluded from the daily cross-section.

## 4. Objective Robustness & Independence Diagnostics

We replace subjective "confirmation" with objective numerical hurdles to test whether the interaction is a mechanical artifact of the shared $IV_{30}$ variable.

- **Variance Inflation Factor (VIF):** Must remain $< 5.0$ for both main effects and the interaction term.
- **Condition Number:** Matrix condition number must remain $< 30$.
- **Model C (Residualization):** When regressing returns on the residual of $TS$ (after regressing $TS$ on VRP-proxy cross-sectionally), the residualized term-structure coefficient must retain a positive sign and two-sided $p < 0.05$.
- **Forward Volatility Validation:** The primary effect must remain positive and statistically significant when $IV_{90}$ is replaced by $\sigma_{30,90}$ (Forward Volatility).

## 5. Frozen OOS Promotion Gates & Holm Family

A return barely above zero is an academic curiosity, not a trading edge. The promotion criteria demand strict economic utility and monotonicity.

### A. Minimum Economic Thresholds (True OOS Sample)

1. **Net Return hurdle:** Mean annualized net portfolio return $> 8.0\%$ (after conservative midpoint + $25\%$ slippage and standard SEC/OCC/broker fees).
2. **Top-Minus-Bottom Hurdle:** Net long-straddle spread return $> 1.5\%$ per month.
3. **Monotonicity:** Mean net return must rank perfectly across quintiles: $Q5 > Q4 > Q3 > Q2 > Q1$.

### B. Statistical Inference & Multiple Testing

- **Bootstrap Parameters:** Stationary block-bootstrap; resampling unit = entire trading-date cross-sections; expected block length = 10 days; 5,000 replications; seed = 42; 95% basic percentile interval.
- **Holm Step-Down Family (Frozen Secondary Hypotheses):**
  1. Interaction coefficient ($\gamma_3$)
  2. High-TS-low-VRP indicator coefficient ($\beta_3$)
  3. Short-margin outcome (FINRA_4210_MINIMUM_MARGIN denominator)
  4. Lagged delta-hedged outcome
  5. Forward-volatility TS replacement
  6. Epsilon 0.005 state test
  7. Epsilon 0.010 state test
  8. Epsilon 0.020 state test
  9. Model B decomposed components ($IV_{30}$, $IV_{90}$, $RV_{21}$)
  10. Model C residualized TS

## 6. Immutable Freeze Manifest (July 22, 2026)

This JSON manifest serves as the cryptographic lock for the methodology. Any alteration to this file forces a new OOS start date.

JSON

```
{
  "freeze_timestamp": "2026-07-22T10:20:34-04:00",
  "git_commit_hash": "PENDING_EXECUTION_HASH",
  "config_hash": "PENDING_EXECUTION_HASH",
  "database_schema_version": "v1.4.2",
  "vendor_snapshot_id": "OptionMetrics_IvyDB_US_v8.1",
  "universe_definition": "standard_equity_min_price_10_min_adv_1m",
  "primary_regression_formula": "net_ret ~ ts_percentile_centered",
  "controls": ["log_mcap", "trailing_1m_ret", "sector_dummy"],
  "cost_model_version": "conservative_mid_plus_25_pct_spread",
  "margin_model": "FINRA_4210_MINIMUM_MARGIN",
  "bootstrap": {
    "method": "stationary_block",
    "block_length_days": 10,
    "replications": 5000,
    "seed": 42
  },
  "holm_family_count": 10,
  "promotion_thresholds": {
    "min_annualized_net_ret": 0.08,
    "min_monthly_tmb_spread": 0.015,
    "require_monotonic_quintiles": true
  }
}

```



