# Offline Pandas backtesting — spike evidence + wiring decisions (2026-07-03)

**Question (handoff Decision 2):** can the Lumibot backtest run FULLY OFFLINE
from `.cache/chains/` (no ThetaTerminal, no network), with the cache's REAL
exchange greeks and the frozen conservative fill model intact?

**Answer: YES — proven by a throwaway spike, then productized with TDD.**
Every claim below was verified against the installed lumibot 4.5.63 source
and/or observed in the spike run (SPY, 2022-06-01..2022-07-29, socket-level
network block + poisoned fetch path active the whole run).

## What the spike proved

| Claim | Evidence |
|---|---|
| PandasData accepts per-contract option `Data` (bid/ask quote columns) and fills market sells at bid / buys at ask | `data_sources/pandas_data.py` (`_DATA_QUOTE_COLS`), `backtesting_broker.py:2326-2349`; spike fills matched feed quotes exactly |
| Fills price at the DECISION day's EOD quotes | spike fill-day attribution: entry decided 06-01 filled at 06-01 quotes (logged at next session's stamp); exit decided 06-10 filled at 06-10 quotes |
| Bars must be stamped 16:00 America/New_York | option marks only ingested 09:30–16:00 sim time (`_strategy.py:1148-1151`) |
| Per-contract commissions | `TradingFee(per_contract_fee=0.65)` passed as buy+sell fees; engine final cash matched hand math to the cent |
| No greeks dependency in the engine | zero greeks references in broker/executor; selection uses the cache's REAL exchange greeks via the chain provider |
| ThetaDataBacktesting is NOT the offline path | it kills/launches a local ThetaTerminal and fetches on cache miss (`thetadata_helper.py`) |
| Feeding orders without Data never fills | `pandas_data.py:515-532` — route B without route A's data feeding is dead |
| Scale | 4,851 Data objects built in ~3 s; 2-month backtest in ~7 s; full in-sample estimated well under an hour with chunking |

## Wiring decisions (now production code, TDD'd)

1. **`data/pandas_feed.py`** — cache → per-contract `Data`. Quote columns are
   pre-widened by `SLIPPAGE_HAIRCUT` with **adverse penny rounding** (bid
   floored, ask ceiled): an engine fill can never be BETTER than
   `entry_credit_conservative`. `close` = raw mid (mark-to-market only).
   Contract inclusion by |delta| ever in [0.03, 0.65] — plumbing, not a
   tunable: the strategy fails LOUD if a selected leg lacks feed Data.
2. **`strategies/put_credit_spread.py`** — adapters implemented. Chains come
   from an injected `chain_provider` (offline cache, real greeks/OI);
   fill-state machine `pending_entry → open → pending_exit → closed`;
   closed trades extracted from ENGINE fills net of the frozen commission
   model, keyed by ENTRY DECISION date.
3. **`harness/run_backtest.py`** — per-symbol, per-calendar-year chunks
   (memory bound: one 5-year 9-symbol feed ≈ 10^5 Data objects). Equivalence
   argument: positions are per-underlying, sizing is a fixed per-trade cap,
   and the backtesting broker has no cross-symbol buying-power coupling.
   Carry-over: a tail exit blocks the next chunk's entries until after the
   exit day. **Final chunk stops entries `MAX_HOLD_DAYS` (=46) before `end`
   so no in-sample position ever needs post-IN_SAMPLE_END quotes to exit** —
   without this, Dec-2022 entries would touch the holdout to close.
4. **Offline hygiene in `run()`** — `benchmark_asset=None` (else Lumibot
   fetches Yahoo benchmark returns), explicit `risk_free_rate`, no tearsheet.

## Known, documented imperfections (do not silently "fix")

- **Penny rounding** of pre-widened quotes is adverse by construction
  (floor/ceil), so it can only understate credits/overstate debits — never
  flatter the strategy.
- **Worthless long leg at exit:** if the long leg's bid is 0 at close time,
  the quote path can't fill a market sell and Lumibot falls back to the OHLC
  close (= raw mid), overstating recovery by ≤ half the ask on a sub-$0.02
  contract (pennies per spread, conservative side dominates elsewhere).
- **Expiration settlement needs underlying stock Data** which the cache does
  not hold. The strategy's 7-DTE forced close makes expiry unreachable in
  normal operation; if a position ever DOES reach expiry the run fails loud
  (RuntimeError from the chunk-end open-spread check / settlement) rather
  than settling silently.
- **In-sample entry loss at the boundary:** the final ~46 days of the
  in-sample window admit no entries (holdout protection). This is part of
  the registered design and must be stated in the H1 registration notes.

## Integrity events logged (ledger/facts.log)

- `SPIKE_OFFLINE_BACKTEST` — the one spike trade's result WAS seen
  (engineering peek, recorded honestly).
- `HARNESS_SMOKE` — real-cache mechanics check (3 trades, SPY, Jun–Aug 2022);
  no aggregate PnL surfaced pre-registration.
