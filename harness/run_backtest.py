"""harness/run_backtest.py -- thin Lumibot wrapper over the OFFLINE cache.

Ties config + a Strategy class + the offline pandas feed + metrics together.
Keep this THIN: Lumibot stays the engine (fills, cash, fees); this module only
loads cached chains, builds the per-contract feed, runs the engine, and
collects the strategy's closed-trade dicts for metrics.scoreboard.

Chunking (memory, not statistics): one 5-year, 9-symbol feed would need
~10^5 per-contract Data objects, so run() executes per-symbol, per-calendar-
year chunks. Chunking must not change WHAT is traded:
  * interior chunks allow entries through Dec 31 and simulate MAX_HOLD_DAYS
    into the next year so every position exits inside its own chunk;
  * a position exiting inside the next chunk's calendar blocks that chunk's
    entries until after the exit day (one-spread-per-underlying holds across
    the seam);
  * the FINAL chunk stops entries MAX_HOLD_DAYS before `end`: no in-sample
    position ever needs post-IN_SAMPLE_END (holdout) quotes to exit.
Per-symbol runs equal one multi-symbol run for the scoreboard: positions are
per-underlying, sizing is a fixed per-trade cap, and the backtesting broker
imposes no cross-symbol buying-power coupling (verified 4.5.63).
"""
from __future__ import annotations

from datetime import date as Date
from datetime import datetime, timedelta

import config
from data import pandas_feed
from data.thetadata_adapter import OOSDataTouchError

# Longest possible hold: an entry at the top of the DTE band lives until at
# most its expiration (exits trigger at A_CLOSE_AT_DTE, expiry is the bound).
MAX_HOLD_DAYS = config.A_TARGET_DTE[1] + 1


def _year_chunks(start: Date, end: Date) -> list[tuple[str, str, str]]:
    """(sim_start, entry_cutoff, sim_end) per calendar year, ISO strings.
    entry_cutoff is INCLUSIVE; sim_end never passes `end`."""
    chunks = []
    for year in range(start.year, end.year + 1):
        sim_start = max(Date(year, 1, 1), start)
        year_end = Date(year, 12, 31)
        entry_cutoff = min(year_end, end - timedelta(days=MAX_HOLD_DAYS))
        sim_end = min(year_end + timedelta(days=MAX_HOLD_DAYS), end)
        if entry_cutoff < sim_start:
            continue  # window slice admits no entries
        chunks.append(
            (sim_start.isoformat(), entry_cutoff.isoformat(), sim_end.isoformat()))
    return chunks


def _run_chunk(strategy_cls, symbol: str, sim_start: str, entry_cutoff: str,
               sim_end: str, blocked_until: str | None, allow_oos: bool) -> list[dict]:
    """One symbol, one chunk, one Lumibot backtest -- fully offline."""
    from lumibot.backtesting import PandasDataBacktesting
    from lumibot.entities import TradingFee

    chains = pandas_feed.load_cached_chains(
        symbol, sim_start, sim_end, allow_oos=allow_oos)
    if not chains:
        return []
    feed = pandas_feed.build_option_data(chains, symbol, exp_max=sim_end)
    if not feed:
        return []

    fee = TradingFee(per_contract_fee=config.COMMISSION_PER_CONTRACT)
    end_dt = datetime.combine(
        Date.fromisoformat(sim_end) + timedelta(days=1), datetime.min.time())
    _result, strat = strategy_cls.run_backtest(
        PandasDataBacktesting,
        backtesting_start=datetime.combine(
            Date.fromisoformat(sim_start), datetime.min.time()),
        backtesting_end=end_dt,   # engine end is exclusive; include sim_end
        pandas_data=feed,
        budget=config.STARTING_CAPITAL,
        buy_trading_fees=[fee],
        sell_trading_fees=[fee],
        benchmark_asset=None,     # offline: never fetch benchmark returns
        risk_free_rate=0.0,       # offline: never fetch a rate
        analyze_backtest=False,
        show_plot=False,
        save_tearsheet=False,
        show_tearsheet=False,
        show_progress_bar=False,
        quiet_logs=True,
        save_logfile=False,
        save_stats_file=False,
        parameters={
            "symbols": [symbol],
            "chain_provider": lambda sym, iso_day: chains.get(iso_day),
            "tradeable_assets": set(feed.keys()),
            "entry_cutoff": entry_cutoff,
            "blocked_until": blocked_until,
        },
    )
    if strat._spreads:
        # fail LOUD: silently dropping an unresolved position would bias PnL
        raise RuntimeError(
            f"{symbol} chunk {sim_start}..{sim_end} ended with unresolved "
            f"spread state: { {s: p.state for s, p in strat._spreads.items()} }")
    return list(strat.closed_trades)


def run(strategy_cls, start: str | None = None, end: str | None = None, *,
        symbols: list[str] | None = None, allow_oos: bool = False) -> list[dict]:
    """Run the offline pre-registered backtest; return metrics.scoreboard
    trade dicts. Defaults to the FULL IN-SAMPLE window; any end past
    IN_SAMPLE_END is refused unless the OOS reveal path sets allow_oos."""
    start_d = Date.fromisoformat(start or config.BACKTEST_START)
    end_d = Date.fromisoformat(end or config.IN_SAMPLE_END)
    if end_d > Date.fromisoformat(config.IN_SAMPLE_END) and not allow_oos:
        raise OOSDataTouchError(
            f"backtest end {end_d} is past IN_SAMPLE_END={config.IN_SAMPLE_END}; "
            "the holdout is only reachable through the OOS reveal gate.")

    trades: list[dict] = []
    for symbol in symbols or config.UNIVERSE:
        blocked_until: str | None = None
        chunks = _year_chunks(start_d, end_d)
        for i, (sim_start, entry_cutoff, sim_end) in enumerate(chunks):
            chunk_trades = _run_chunk(
                strategy_cls, symbol, sim_start, entry_cutoff, sim_end,
                blocked_until, allow_oos)
            trades.extend(chunk_trades)
            if i + 1 < len(chunks):
                next_start = chunks[i + 1][0]
                tail_exits = [t["exit_date"] for t in chunk_trades
                              if t.get("exit_date") and t["exit_date"] >= next_start]
                blocked_until = max(tail_exits) if tail_exits else None
    return sorted(trades, key=lambda t: (t["entry_date"], t["symbol"]))


def _oos_backtest_trades():
    """OOS seam, still sealed ON PURPOSE: the charge-on-touch policy (every
    holdout data open logged as an auditable event) is not implemented yet,
    and memory records it as REQUIRED before any reveal. Wire it, then call
    run(strategy_cls, start=<IN_SAMPLE_END+1>, end=config.BACKTEST_END,
    allow_oos=True) from here."""
    raise NotImplementedError(
        "OOS backtest stays sealed: implement charge-on-touch logging before "
        "any reveal (see project memory / pre-registration decisions).")


def reveal_out_of_sample(hypothesis_id, *, base_dir="ledger", git_clean_tracked=None):
    """Thin seam: delegate the write-once OOS reveal to the integrity substrate,
    injecting the (still-sealed) backtest as the run function."""
    from research import experiments
    return experiments.reveal_oos(
        hypothesis_id, run_fn=_oos_backtest_trades, base_dir=base_dir,
        git_clean_tracked=git_clean_tracked)
