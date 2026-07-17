"""H9 written study — trigger, lifecycle, adjudication (spec §3, §7).

Mark convention mirrors h6_watch.evaluate_exit exactly: proceeds =
adverse_sell(bid)*100*contracts - COMMISSION_PER_CONTRACT*contracts, compared
to entry_cost*(1+TP). Decisions at session close; fills at the NEXT session's
close (T->T+1). Exit priority (spec §3): pre_next_report > dte_close >
take_profit. One contract per event. NO trading path exists here.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

import config
import metrics
from data.cache_runner import trading_days
from data.pandas_feed import adverse_buy, adverse_sell, quote_valid
from data.thetadata_adapter import passes_liquidity
from options_researcher.chains import is_monthly
from options_researcher.h9_events import H9Event

VOCAB = ("REJECTED", "INSUFFICIENT_SAMPLE",
         "NOT_REJECTED_FOR_THIS_NARROW_HISTORICAL_TEST")


def trigger(event: H9Event, closes: pd.Series) -> str:
    r = closes[event.t_dec] / closes[event.t_pre] - 1.0
    return "call" if r >= config.H9_REACTION_MIN else "reaction_below_min"


def _exp_date(e) -> date:
    return e if isinstance(e, date) else date.fromisoformat(str(e)[:10])


def _dte(iso: str, expiration) -> int:
    return (_exp_date(expiration) - date.fromisoformat(iso)).days


def select_contract(chain: pd.DataFrame, entry_iso: str) -> pd.Series | None:
    calls: pd.DataFrame = chain.loc[chain["right"] == "C"].copy()
    lo_d, hi_d = config.H6_DELTA_BAND
    lo_t, hi_t = config.H6_DTE_BAND
    mask = ((calls["delta"] >= lo_d) & (calls["delta"] <= hi_d)
            & calls["expiration"].map(lambda e: lo_t <= _dte(entry_iso, e) <= hi_t)
            & calls["expiration"].map(lambda e: is_monthly(_exp_date(e))))
    band: pd.DataFrame = calls.loc[mask].copy()
    if band.empty:
        return None
    band = band.loc[band.apply(
        lambda r: quote_valid(r["bid"], r["ask"])
        and passes_liquidity(r["open_interest"], r["bid"], r["ask"]), axis=1)]
    if band.empty:
        return None
    return band.sort_values("delta", ascending=False).iloc[0]


def entry_cost_if_within_cap(row: pd.Series | None) -> float | None:
    if row is None:
        return None
    cost = round(adverse_buy(row["ask"]) * 100.0 + config.COMMISSION_PER_CONTRACT, 2)
    return cost if cost <= config.H9_PREMIUM_CAP_DOLLARS else None


def _proceeds(bid: float) -> float:
    return round(adverse_sell(bid) * 100.0 - config.COMMISSION_PER_CONTRACT, 2)


def _find_row(ch: pd.DataFrame, strike: float, expiration: date) -> pd.Series | None:
    m: pd.DataFrame = ch.loc[(ch["right"] == "C") & (ch["strike"] == strike)
                              & (ch["expiration"].map(_exp_date) == expiration)]
    if m.empty:
        return None
    row = m.iloc[0]
    return row if quote_valid(row["bid"], row["ask"]) else None


def simulate_trade(event: H9Event, chain_provider, *,
                   next_report_iso: str | None) -> dict | None:
    """One event -> one trade dict, or None when entry is cancelled."""
    assert event.t_entry is not None, "simulate_trade requires a resolved t_entry"
    t_entry: str = event.t_entry
    entry_chain = chain_provider(event.symbol, t_entry)
    row = select_contract(entry_chain, t_entry)
    cost = entry_cost_if_within_cap(row)
    if cost is None or row is None:
        return None
    expiration, strike = _exp_date(row["expiration"]), float(row["strike"])
    pre_report_cutoff = None
    if next_report_iso:
        pre = trading_days(t_entry, next_report_iso)
        k = config.H9_NEXT_REPORT_EXIT_SESSIONS
        pre_report_cutoff = pre[-(k + 1)] if len(pre) > k else t_entry
    sessions = trading_days(t_entry, config.H9_WINDOW[1])[1:]
    decision = None
    gaps: list[str] = []
    for s in sessions:
        if _dte(s, expiration) < 0:
            break
        try:
            ch = chain_provider(event.symbol, s)
        except FileNotFoundError:
            gaps.append(s)
            continue
        found = _find_row(ch, strike, expiration)
        if found is None:
            gaps.append(s)
            continue
        if pre_report_cutoff and s >= pre_report_cutoff:
            decision = (s, "pre_next_report")
        elif _dte(s, expiration) <= config.H6_CLOSE_AT_DTE:
            decision = (s, "dte_close")
        elif _proceeds(float(found["bid"])) >= cost * (1.0 + config.H6_TAKE_PROFIT_PCT):
            decision = (s, "take_profit")
        if decision:
            break
    base = {"symbol": event.symbol, "entry_date": event.t_entry,
            "capital_at_risk": cost, "gaps": gaps}
    if decision is None:
        return {**base, "pnl": None, "exit_reason": "unresolved_data_gap",
                "exit_fill_session": None}
    dec_session, reason = decision
    for s in trading_days(dec_session, config.H9_WINDOW[1])[1:]:
        try:
            ch = chain_provider(event.symbol, s)
        except FileNotFoundError:
            gaps.append(s)
            continue
        found = _find_row(ch, strike, expiration)
        if found is None:
            gaps.append(s)
            continue
        proceeds = _proceeds(float(found["bid"]))
        return {**base, "pnl": round(proceeds - cost, 2), "exit_reason": reason,
                "exit_fill_session": s}
    return {**base, "pnl": None, "exit_reason": "unresolved_data_gap",
            "exit_fill_session": None}


def map_verdict(board: dict) -> str:
    v = board["verdict"]
    if v.startswith("FAIL"):
        return "REJECTED"
    if v.startswith("INSUFFICIENT"):
        return "INSUFFICIENT_SAMPLE"
    return "NOT_REJECTED_FOR_THIS_NARROW_HISTORICAL_TEST"


def adjudicate(trades: list[dict]) -> dict:
    complete = [t for t in trades if t["pnl"] is not None]
    board = metrics.scoreboard(complete, label="H9")
    board["h9_outcome"] = map_verdict(board)
    board["unresolved_data_gap_trades"] = len(trades) - len(complete)
    return board
