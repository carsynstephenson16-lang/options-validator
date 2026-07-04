# Options Research Platform — VST · CEG · MSFT · AMZN

**Mission (owner decision 2026-07-03):** research how the options of four
AI-infrastructure names — Vistra (VST) and Constellation (CEG) on the
nuclear/data-center power side, Microsoft (MSFT) and Amazon (AMZN) on the
Mag-7 cloud side — actually behave, and only then build and validate option
strategies on them. **Research only. This is NOT a live bot and places no
orders.** "No edge after costs" is a successful finding — the point is to
learn that cheaply, before risking money.

The platform has two layers, and the separation is deliberate:

1. **The discipline layer** (kept from the project's first phase, fully
   tested): conservative fill model (quote mid **or worse**, commissions both
   legs both ways, adverse haircut), liquidity gates on every leg, a
   scoreboard whose verdict gates on the number of **losses** (not trades),
   dependence-aware confidence intervals, an append-only research ledger, and
   a sealed-holdout protocol. This layer exists because it already caught
   three tempting strategies (H1, H2, H3-draft) that would have lost money.
2. **The research layer** (`options_researcher/`, new): descriptive and
   predictive studies of the four names' options — liquidity, strike grids,
   implied-vol behavior, how option prices react around big moves — that
   produce *facts first*, and only later feed pre-registered strategy tests.

## Current status

| Piece | State |
|---|---|
| Universe | `config.UNIVERSE = ["MSFT", "AMZN", "VST", "CEG"]` |
| Chain data | Daily EOD chains cached for the full universe: MSFT/AMZN/VST 2018-01-02..2026-06-30 (~2,134 days each), CEG 2022-02-09..2026-06-30 (1,100 days, zero empty files; the 2018–2022-02 gap is pre-listing) |
| Tradability profile | `options_researcher/profile_tradability.py` — first findings below |
| Backtest path | Offline Lumibot/PandasData harness + `tools/score_backtest.py` scoreboard CLI, wired against the real cache |
| Feasibility | `analysis/feasibility.py` — credits measured from cached chains, not assumed |
| Discipline layer | 256 tests green (`uv run python -m unittest discover -s tests`) |
| Strategy history | H1 ($2-wide SPY/QQQ put spread), H2 ($5-wide): registered, honest in-sample **FAILs**. H3R (SPY conditional-VRP): archived un-run at scope pivot. Ledger records are permanent; OOS budget 0/3 spent |

### What the first profile says (sampled days, ~37-DTE puts)

- **MSFT**: tradable under our gates since 2019; spreads ~3–9%; $5 strike
  grid since 2021. Best-behaved name of the four.
- **AMZN**: thin before its 2022 split, good after — spreads ~2–4%, growing
  open interest, 6–12 strikes passing gates recently.
- **VST**: rich implied vol (50%+ in 2024–25) but **ATM open interest failed
  our ≥100 floor in every sampled year, including 2024–26**. Caveat: weekly
  expirations may fragment OI; checking monthly expiries is a roadmap item.
  Until then, VST structures must assume poor fills.
- **CEG**: fetched 2026-07-04, and it rhymes with VST — rich implied vol
  (45–53% in 2024–26) but thin ATM open interest at the sampled ~37-DTE
  expiries: passed our gates in 2023 (7.7% spread, OI 134), just missed in
  2024 (OI 87), collapsed at sampled expiries in 2025–26. Only ~4.5 years of
  option history exist at all. The monthly-expiry check decides CEG too.

## Quickstart

Python 3.12 managed by uv; the lockfile is the source of truth.

```bash
uv sync
uv run python -m unittest discover -s tests                 # discipline layer
uv run python options_researcher/profile_tradability.py     # 4-name liquidity profile
uv run python analysis/feasibility.py                       # sizing vs the sleeve
uv run python tools/score_backtest.py --symbols MSFT,AMZN --json   # in-sample scoreboard
```

`smoke_test.py` probes a single in-sample chain (cached parquet, or the
official ThetaData client on a cache miss). Post-`IN_SAMPLE_END` values stay
sealed for the legacy holdout machinery unless the reveal gate opens them.

## Capital & risk

`RISK_SLEEVE` ($14k) and `MAX_LOSS_PER_TRADE` ($600 economic max loss, owner
decision 2026-07-02) live in `config.py`. Four concurrent positions ≈ $2,400
≈ 17.1% of the sleeve at simultaneous risk — and these four names are **one
AI-infrastructure cluster, not four independent bets**; in an AI or
power-sector drawdown they can lose together. Never size against net worth,
and never raise the cap to make a structure "fit".

## Research rules (non-negotiable, inherited)

See `.cursorrules` and `AGENTS.md`. No look-ahead; fills at quote mid or
worse; commission plus half-spread on both legs; liquidity filters on both
legs; verdicts gate on losses; every strategy number lives in `config.py`;
data gaps are skipped and logged, never papered over. New strategy ideas are
**pre-registered in the ledger before results exist** — parameters frozen
first, run once, result recorded whatever it shows. The 2023+ window is no
longer a credible blind holdout for these four names (they were picked
knowing the 2023+ AI boom, and profiling has opened their recent
microstructure — disclosed in `ledger/facts.log`); future hypotheses
therefore pre-declare their own validation design, e.g. a forward
paper-trading window.

## Roadmap (one scoped step per prompt)

1. ~~**CEG data**~~ — DONE 2026-07-04: 1,100 chains cached, profiler re-run
   (see findings above; `ledger/facts.log` CEG_CACHE_COMPLETE).
2. **VST + CEG monthly-expiry check**: does open interest concentrate in
   monthlies? (Decides whether the power names are tradable at all under
   honest gates — currently the single most important open question.)
3. **Behavior studies** (facts, not verdicts): per name — implied vol vs
   later realized moves, behavior around earnings, reaction to large
   sector/market moves. Produces the feature set for any predictive idea.
4. **Structure menu per name from measured liquidity**: which defined-risk
   structures (spreads, covered calls / LEAPS-based, condors) clear friction
   arithmetic on each name's real grids and spreads.
5. **First 4-name hypothesis**: pre-registered like H1/H2 were, with its own
   validation design declared before any P&L is computed.

## Known limitations

- **EOD data** is an upper bound on realism — real fills happen intraday.
- **Assignment/early exercise** are not simulated (American-style, physically
  settled); defined-risk caps bound the damage.
- **Earnings gaps**: single names gap through levels at EOD cadence; any
  strategy test must handle earnings explicitly (blackouts or measured
  exposure).
- **History asymmetry**: CEG effectively starts 2022; VST's tradable era is
  recent. Sample sizes will be small; the loss-gated verdict machinery exists
  precisely so thin samples read as INSUFFICIENT SAMPLE, not fake passes.
