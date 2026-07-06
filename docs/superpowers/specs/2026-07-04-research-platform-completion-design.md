# Research Platform Completion — design (2026-07-04)

**Decision record:** owner approved Approach A ("facts pipeline first,
strategies on top") on 2026-07-04. End state = a **repeatable research tool**:
refresh data on demand, re-score the four names, run behavior studies, track
registered strategy tests; the game-style dashboard ships **last**. Owner
holds (or will soon hold) 100+ shares of **VST and AMZN** → covered calls are
first-class research candidates on those two names; MSFT and CEG are
options-only (defined-risk spreads, LEAPS-based substitutes).

## 1. Ground truth this design builds on (measured, committed)

- **Universe:** VST, CEG, MSFT, AMZN (config.UNIVERSE; one AI-infrastructure
  cluster, not four independent bets).
- **Chain cache complete:** MSFT/AMZN/VST 2018-01-02..2026-06-30 (~2,134 days
  each), CEG 2022-02-09..2026-06-30 (1,100 days), zero empty files.
- **Monthlies finding (2026-07-04):** put open interest is 85–100%
  concentrated in standard monthly expirations for all four names. At the
  nearest monthly (~30 DTE), 2024–26 medians PASS the frozen gates
  (OI ≥ 100, spread ≤ 10%): VST OI 220 / 5.1% spread, CEG 212 / 5.5%,
  MSFT 3,213 / 2.6%, AMZN 6,462 / 2.1%. **Every structure researched here
  targets monthly expirations.**
- **Tradable eras:** MSFT — full history; AMZN — monthlies fine throughout,
  fine strike grids post-2022 split; VST — spreads ≤ ~5% only from ~2024;
  CEG — from ~2023. Small samples on the power names are a fact, not a bug.
- **Validation honesty (facts.log `PIVOT_4NAME_SCOPE`):** 2023+ cannot pose
  as unseen data for these names. Any strategy test declares its own
  validation design up front; the credible final test is a **forward paper
  window**. Legacy H1/H2 holdout machinery stays untouched.
- **Frozen cost model:** quote mid or worse, half-spread both legs,
  $0.65/contract/leg/way, 1% adverse haircut, liquidity gates both legs,
  verdicts gate on ≥ 10 losses. Not negotiable anywhere below.

## 2. Architecture — three layers plus reports

```
.cache/chains/*.parquet   .cache/underlying/*.parquet      [DATA]
        │                        │
        ▼                        ▼
options_researcher/       data/underlying_closes.py
  chains.py  ──────►  features.py  ──────►  studies/*     [RESEARCH CORE]
  (monthly selection)  (daily per-name       (income tables,
                        feature frame)        behavior facts)
        │                        │                │
        ▼                        ▼                ▼
reports/YYYY-MM-DD-*.md   ledger/facts.log   docs/…/structure-menu
        │                                          │
        ▼                                          ▼
metrics.py + research/ ledger  ◄────  strategies/* hypotheses  [DISCIPLINE]
(scoreboard, prereg, verdicts — existing, untouched)
```

Rules: research core **reads** the data layer and **writes** dated reports +
facts; only the discipline layer issues verdicts; every load-bearing number
lands in a committed report or facts.log, never only in a terminal scroll.
Post-2022 reads in researcher paths pass `allow_oos=True` explicitly with the
standing disclosure (pivot note); the flag and legacy gates are preserved.

## 3. Modules (each one prompt, each lands with tests + green suite + commit)

### M1 — Research core: `options_researcher/chains.py`
Purpose: one blessed way to select monthly expirations and ATM rows, shared
by everything (the two profilers currently duplicate this ad hoc).
Interface: `load_range(symbol, start, end, allow_oos)` (delegates to
`data.pandas_feed.load_cached_chains`); `third_friday(y, m)`;
`is_monthly(exp_date)` (3rd Friday, or Thursday before a holiday 3rd Friday);
`nearest_monthly(chain, today, min_dte=15, max_dte=60)`;
`atm_row(chain, expiration, right, target_delta=0.50)`;
`liquid_strikes(chain, expiration)` (reuses `passes_liquidity`).
Also: refactor `profile_tradability.py` and `profile_monthlies.py` to import
these helpers (same printed output, no behavior change).
Tests: fixture chains; Thursday-expiry (Good Friday) case; band edges.
Done when: profilers reproduce today's committed numbers via chains.py.

### M2 — Underlying closes + daily features
`data/underlying_closes.py` (adapted from the archived H3R plan, Task 4):
`store_closes`/`load_closes` with the OOS flag; one-shot ThetaData stock-EOD
pull (endpoint VERIFIED against the installed client first; STOP if absent)
for MSFT/AMZN/VST 2017-01-01.. and CEG 2022-01-01.., written blind.
`options_researcher/features.py`: `build_daily_features(symbol)` → frame
indexed by date: close, rv21 (annualized 21-day realized vol), atm_iv
(nearest-monthly 0.50Δ put IV), iv_minus_rv, iv_rank_252 (percentile of
atm_iv over trailing 252 obs, min 126), monthly_dte, earnings_week flag.
Cached to `.tmp/research/{SYM}_features.parquet` (regenerable).
**Earnings dates:** authoritative source = small curated CSVs
`data/earnings/{SYM}.csv` (date, confirmed_source_url), compiled once from
company IR/press pages (delegable to a cheaper model WITH citation URLs;
spot-audited); an IV-term-structure-kink inference study cross-checks them
later and is always labeled LOW-CONFIDENCE. No paid data.
Tests: synthetic closes/chains give known rv/iv/rank; earnings flag from a
fixture CSV; OOS-flag behavior.

### M3 — Behavior studies (three small CLIs; output = dated report + facts)
a. `studies/iv_vs_realized.py` — per name/year: does high iv_rank (≥ 70)
   actually precede larger 21-day realized moves than low iv_rank (≤ 30)?
   Table + honest "no relationship" reporting if that's what the data says.
b. `studies/earnings_behavior.py` — per name: pre-earnings IV run-up size,
   post-earnings IV crush, |earnings-week move| vs ordinary weeks.
c. `studies/covered_call_income.py` — **VST + AMZN**: for every monthly
   cycle in the tradable era (AMZN also 2018+ for context): sell the
   20/30/40Δ monthly call at conservative fill (bid minus haircut), hold to
   expiration; report premium collected, % of cycles assigned (assigned =
   underlying close above the strike at expiration), total return vs
   buy-and-hold on the same shares, worst months, earnings-cycle flag.
   Descriptive income table — explicitly NOT a verdict; the benchmark is
   buy-and-hold (premium's cost = capped upside, stated in the report).
Tests: golden numbers on synthetic fixtures per study.

### M4 — Structure menu (decision document)
Synthesize M1–M3 into `docs/superpowers/<date>-structure-menu.md`: per name,
which structures clear friction arithmetic (expected friction ÷ typical
credit), sleeve fit under the $600 cap, explicit rejects with numbers.
Candidates at minimum: covered calls (VST/AMZN vs held shares), put credit
spreads and call debit spreads (MSFT/AMZN), LEAPS-based covered-call
substitute (MSFT/CEG), earnings-aware variants of each. Ends with a
recommended first hypothesis. **Owner picks or approves; nothing registers
in M4.**

### M5 — First registered hypothesis
Whatever M4 selects (working expectation: monthly covered call on VST with
an earnings rule — but the menu decides, not this spec). Gets its own
pre-registration doc in the H1/H3R mold: frozen parameters, in-era backtest
window, PASS/FAIL/NO-EDGE/INSUFFICIENT-SAMPLE via the existing scoreboard,
**plus a declared forward paper window (≥ 2 earnings cycles) as the primary
validation** per the pivot note. Engineering carried in from the archived
H3R plan: strategy registry + `strategy_id` on records (un-hardcodes the
reveal path), per-trade P&L decomposition fields. New strategy class in
`strategies/`, one in-sample run, honest ledger record.

### M6 — One-command refresh
`options_researcher/refresh.py`: fetch missing chain days for all four names
(both cache_runner windows), update closes, rebuild feature frames, rerun
studies, regenerate reports; print a "what changed" summary. Idempotent
(skip-if-cached everywhere). Tests: stubbed fetchers, dry-run counts.

### M7 — Dashboard (deferred by owner decision; design session comes later)
Single static HTML "mission control" generated from reports/features/ledger —
game-style presentation (per-ticker character cards, quest-log roadmap,
achievements from facts.log). Scope intentionally undesigned here; it gets
its own brainstorm after M1–M6 ship.

## 4. Error handling & honesty rails
House pattern everywhere: fail closed, skip-and-log (facts.log for
load-bearing gaps), no silent excepts, no synthetic fills, no fallback
quotes. Earnings-CSV rows require a source URL; inferred earnings dates are
labeled LOW-CONFIDENCE and never silently merged. Covered-call studies state
the buy-and-hold benchmark in every report. Sample-size honesty: VST/CEG
short histories mean INSUFFICIENT SAMPLE is an expected, successful outcome;
the forward window is the real test. No parameter auto-tuning anywhere;
strategy variants are separate registered hypotheses (ledger discipline
unchanged). Delegation policy: mechanical fetch/format/tabulate tasks go to
cheaper models with tight specs and audited outputs; selection logic, cost
math, verdict interpretation, and anything touching the discipline layer
stay at full capability.

## 5. Testing strategy
`unittest`, fixtures under `tests/` alongside existing patterns; every module
lands with its tests in the same commit; the full suite (256 green today)
must stay green at every milestone; studies use golden-number fixtures so a
refactor that changes results fails loudly.

## 6. Out of scope (unchanged)
Live trading, order routing, alerts, auto-execution, tickers beyond the
four, intraday data, deep-learning models (sample sizes cannot support
them), any weakening of the cost model.

## 7. Prompt map
One milestone per prompt: **M1 → M2 → M3a → M3b → M3c → M4 (menu + owner
pick) → M5 (register + run) → M6 → M7 (dashboard design first, then build).**
Each prompt ends: tests green, work committed, README status row updated.
