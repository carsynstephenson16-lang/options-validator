# Single-name diagnostics — UNREGISTERED, NON-VERDICT-FEEDING (2026-07-03)

Per the pre-registration decision doc §6: per-symbol in-sample runs of the
registered configuration ($2-wide, 30-delta, 30–45 DTE, EOD) on the 7
unregistered names. These characterize concentration and robustness. **They
feed no verdict, change no scope, and tune no parameter.** The verdict-bearing
result remains H1's registered SPY/QQQ record (FAIL).

## Results (in-sample 2018-01-01..2022-12-31, $2-wide)

| Symbol | Trades | Win rate | Expectancy/trade | CI90 | Outcome |
|---|---|---|---|---|---|
| MSFT | 33 | 63.6% | −$85.16 | [−149.54, −29.42] | FAIL |
| AAPL | 34 | 41.2% | −$152.06 | [−214.45, −90.03] | FAIL |
| NVDA | 4 | 75.0% | +$3.45 | [−58.80, +65.70] | INSUFFICIENT SAMPLE (1 loss) |
| VST | 0 | — | — | — | zero trades |
| PLTR | 25 | 60.0% | −$79.94 | [−137.23, −24.30] | FAIL |
| AMZN | 14 | 14.3% | −$240.09 | [−298.81, −181.36] | FAIL |
| NOW | 0 | — | — | — | zero trades |

## Finding 1: the FAIL is universal, not an index artifact

Every name with a scoreable sample fails individually, same as SPY/QQQ. The
negative expectancy under the frozen conservative cost model is a property of
the strategy's cost structure, not of the registered scope choice.

## Finding 2: the 9-name universe was never operationally real at $2 width

Trade dates expose a strike-grid/liquidity mirage:

- **MSFT stops trading entirely after 2019-11-20** — once the price crossed
  ~$200, near-the-money spacing became $2.50/$5, and the exact $2-lower long
  strike stopped existing. 0 trades in 2020–2022.
- **AMZN's 14 trades all sit after the June 2022 20:1 split** (pre-split
  ~$2,000–3,700 stock: no $2 grid, OI spread across strikes).
- **NVDA managed 4 trades in 5 years**; **VST and NOW zero** (OI below the 100
  floor and/or >10% quote spreads and/or no $2 grid at their prices).
- Only PLTR (cheap, $1 strikes, listed 2020-10) traded densely inside its
  listing window.

So a hypothetical 9-name registration would in practice have been SPY/QQQ
plus sparse, regime-biased single-name fragments — reinforcing (after the
fact, changing nothing) the a priori decision to register SPY/QQQ only.

## Finding 3 (data quality, descriptive): fail-closed gates did their job

Zero-trade symbols produced no synthetic fills, no fallback quotes, no errors —
entries were skipped by the liquidity/strike gates exactly as designed.

## What these numbers must never do

Per the frozen protocols: no pooling into any verdict, no scope amendment to
any registered hypothesis, no width/parameter selection ("learn facts, not
parameters"). NVDA's +$3.45 point estimate on 4 trades is noise and is
recorded only to be explicit that it was seen and does not constitute
evidence.
