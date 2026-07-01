"""
harness/run_backtest.py -- thin Lumibot wrapper. STATUS: PHASE 0.

Ties config + a Strategy class + the ThetaData datasource + metrics together.
Keep this THIN: do not reimplement the engine -- call Lumibot's run_backtest.
"""
from __future__ import annotations
from datetime import datetime

import config


def run(strategy_cls, start: str = None, end: str = None):
    """PHASE 0 VERIFY: confirm the ThetaDataBacktesting import and the
    run_backtest signature against the installed lumibot, then map Lumibot's
    per-trade output into the list-of-dicts that metrics.scoreboard expects:
    [{"pnl": float, "capital_at_risk": float}, ...].
    """
    start_dt = datetime.strptime(start or config.BACKTEST_START, "%Y-%m-%d")
    end_dt = datetime.strptime(end or config.BACKTEST_END, "%Y-%m-%d")

    # VERIFY and uncomment:
    #
    # from lumibot.backtesting import ThetaDataBacktesting
    # from lumibot.entities import TradingFee
    # fee = TradingFee(flat_fee=config.COMMISSION_PER_CONTRACT)   # per contract
    # result, strat = strategy_cls.run_backtest(
    #     ThetaDataBacktesting, start_dt, end_dt,
    #     budget=config.STARTING_CAPITAL, benchmark_asset="SPY",
    #     buy_trading_fees=[fee], sell_trading_fees=[fee],
    # )
    # trades = extract_closed_trades(strat)   # -> [{pnl, capital_at_risk}, ...]
    # return trades

    raise NotImplementedError(
        f"Phase 0: wire Lumibot run_backtest ({start_dt:%Y-%m-%d}..{end_dt:%Y-%m-%d}) "
        "+ trade extraction, then feed metrics.scoreboard().")


def _oos_backtest_trades():
    """PHASE 0 SEAM: this is where the wired Lumibot/ThetaData OOS backtest will
    produce the post-IN_SAMPLE_END trades. Until then it raises -- but the OOS
    gate (research.experiments.reveal_oos) enforces pre-registration, frozen
    params, look budget, and a committed ledger BEFORE this is ever called."""
    raise NotImplementedError(
        "Phase 0: wire the OOS ThetaData backtest, then this feeds reveal_oos().")


def reveal_out_of_sample(hypothesis_id, *, base_dir="ledger", git_clean_tracked=None):
    """Thin seam: delegate the write-once OOS reveal to the integrity substrate,
    injecting the (still-unwired) backtest as the run function."""
    from research import experiments
    return experiments.reveal_oos(
        hypothesis_id, run_fn=_oos_backtest_trades, base_dir=base_dir,
        git_clean_tracked=git_clean_tracked)
