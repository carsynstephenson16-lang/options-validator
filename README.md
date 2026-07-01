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
| Feasibility check | `analysis/feasibility.py` | runs today |
| Scoreboard | `metrics.py` | runs today (synthetic demo) |
| Sizing / cost helpers | `strategies/base.py` | complete |
| Liquidity / caching helpers | `data/thetadata_adapter.py` | helpers done; fetch is Phase 0 |
| Strategy A (put credit spread) | `strategies/put_credit_spread.py` | logic done; Lumibot calls Phase 0 |
| Backtest wrapper | `harness/run_backtest.py` | Phase 0 |
| Smoke test | `smoke_test.py` | Phase 0 (needs ThetaData) |
| Tests | `tests/test_core.py` | passing (`unittest`) |

## Quickstart (the parts that work now)

The reproducible environment target is **Python 3.12 managed by uv**. The
lockfile is the source of truth once generated; avoid running this research code
against an arbitrary system Python.

```bash
uv sync
uv run python analysis/feasibility.py     # can a spread even fit your risk sleeve?
uv run python metrics.py                  # see the scoreboard on synthetic trades
uv run python -m unittest discover -s tests   # run the test suite
```

`smoke_test.py` is intentionally blocked until ThetaData chain fetching is
wired and verified.

## Capital & risk

Set `RISK_SLEEVE` in `config.py` to the dollars you're genuinely willing to lose
to this strategy, and size 1% of *that*. Do **not** size against your whole net
worth (that silently puts your stock portfolio behind every options trade) or an
arbitrary account number. The feasibility script shows the trade-off across
several sleeve sizes -- and confirms that a $5-wide spread does not fit a small
sleeve at 1% risk, which is a real finding, not a bug.

## Phase plan

- **Phase 0** -- make the environment reproducible, then verify the
  load-bearing assumptions from the *installed*
  Lumibot/ThetaData (chain access, multi-leg orders, quote-based fills,
  per-contract fees). Wire the ThetaData fetch and run the smoke test.
  **Stop and confirm before building further.**
- **Phase 1** -- finish the ThetaData adapter + smoke test.
- **Phase 2** -- finish Strategy A + the backtest wrapper; produce a scoreboard.
- **Phase 3** -- width sweep ($1 / $2 / $5) reporting expectancy *and* feasibility.
- **Phase 4** -- (optional, later) Strategy B + an apples-to-apples comparison.

A live "scanner / suggestor" is a **separate project** that only makes sense
*after* a strategy survives Phases 0-4. Building it first is premature.

## Known limitations (don't paper over these)

- **Factor concentration:** SPY/QQQ overlap heavily with AAPL/MSFT/NVDA, so this
  universe is ~one tech-beta bet. A positive result here may not generalize.
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
