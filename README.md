# Options Strategy Validation Harness

**One question:** does an options strategy have *positive expectancy after
realistic costs*, across multiple market regimes (2018 / 2020 / 2022)?

This is a **research / validation tool. It is NOT a live bot and places no
orders.** A result of "no edge after costs" is a **successful** outcome -- the
whole point is to find that out cheaply, before risking money.

## Status

| Piece | File | State |
|---|---|---|
| Parameters | `config.py` | complete |
| Feasibility check | `analysis/feasibility.py` | measured from cached in-sample chains |
| Scoreboard | `metrics.py`, `tools/score_backtest.py` | real-cache in-sample scoreboard available |
| Sizing / cost helpers | `strategies/base.py` | complete |
| Liquidity / caching helpers | `data/thetadata_adapter.py` | official ThetaData client + parquet cache wired |
| Strategy A (put credit spread) | `strategies/put_credit_spread.py` | offline Lumibot/PandasData path wired |
| Backtest wrapper | `harness/run_backtest.py` | chunked real-cache backtest wired |
| Smoke test | `smoke_test.py` | wired in-sample ThetaData/cache probe |
| Tests | `tests/` | passing (`unittest`) |

## Quickstart (the parts that work now)

The reproducible environment target is **Python 3.12 managed by uv**. The
lockfile is the source of truth once generated; avoid running this research code
against an arbitrary system Python.

```bash
uv sync
uv run python analysis/feasibility.py     # can a spread even fit your risk sleeve?
uv run python tools/score_backtest.py --symbols SPY,QQQ --json
uv run python -m unittest discover -s tests   # run the test suite
```

`smoke_test.py` is wired for a single in-sample chain probe. It will use a
cached parquet file when present, or the official ThetaData Python client on a
cache miss. Post-`IN_SAMPLE_END` values remain sealed unless the OOS reveal gate
explicitly opens them.

## Capital & risk

Set `RISK_SLEEVE` in `config.py` to the dollars you're genuinely willing to lose
to this strategy, and cap each trade's **economic max loss** (margin plus
round-trip commissions) at an explicit dollar figure decided against that
sleeve (`MAX_LOSS_PER_TRADE`; owner decision 2026-07-02: $600 ≈ 4.3% of the
$14k sleeve). Do **not** size against your whole net worth (that silently puts
your stock portfolio behind every options trade) or an arbitrary account
number, and never raise the cap to make a width "fit". The feasibility script
shows what fits the cap **and** the portfolio view the per-trade cap hides:
nine concurrent positions ≈ $5,400 at simultaneous risk (~38.6% of the sleeve)
in a universe that is far fewer than nine independent bets -- in a growth/AI or
tech drawdown, many of them can lose together.

## Current research state

- ThetaData's official Python client fetches EOD greeks/NBBO/IV plus open
  interest into local parquet cache files.
- Lumibot remains the engine, but backtests run fully offline through
  per-contract PandasData objects built from the cache.
- H1 (`SPY,QQQ`, $2-wide) and H2 (`SPY,QQQ`, $5-wide) both failed in-sample
  after conservative fills and fees. The owner declined OOS reveal, so the
  holdout remains sealed and `OOS_LOOK_BUDGET` is still unspent.
- Any new strategy, symbol scope, width, stop, signal, or fill-model change is a
  new hypothesis and must preserve the OOS gate.

A live "scanner / suggestor" is a **separate project** that only makes sense
*after* a strategy survives this validation process. Building it first is
premature.

## Known limitations (don't paper over these)

- **Factor concentration:** SPY/QQQ overlap heavily with AAPL/MSFT/NVDA/AMZN,
  and PLTR/NOW/VST add high-beta thematic exposure. This is not nine clean
  independent bets. A positive result here may not generalize.
- **EOD data** is an upper bound on realism -- real fills happen intraday.
- **VRP compression:** the historical volatility risk premium has thinned; a
  2018-2024 backtest may overstate what's available now.
- **Assignment risk:** single names and SPY/QQQ are American-style, physically
  settled. `A_CLOSE_AT_DTE` mitigates pin/assignment risk -- keep it.

## Guardrails

See `.cursorrules`. The non-negotiables: no look-ahead; fills at the quote mid
**or worse**, never the favorable side; commission + half-spread on **both**
legs; liquidity filters on both legs; don't build a custom engine (use Lumibot);
verify every Lumibot API call against the installed library; the verdict gates
on the number of **losses**, not trades.
