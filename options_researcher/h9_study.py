"""H9 written study — trigger, lifecycle, adjudication (spec §3, §7).

Mark convention mirrors h6_watch.evaluate_exit exactly: proceeds =
adverse_sell(bid)*100*contracts - COMMISSION_PER_CONTRACT*contracts, compared
to entry_cost*(1+TP). Decisions at session close; fills at the NEXT session's
close (T->T+1). Exit priority (spec §3): pre_next_report > dte_close >
take_profit. One contract per event. NO trading path exists here.

Protective exits (pre_next_report, dte_close) are pure CALENDAR decisions,
resolved before any quote scanning -- they cannot be starved by missing or
invalid chain data (adversarial review of 202899e). The take-profit scan
only ever looks at sessions strictly before the protective session. During
the FILL loop that follows the decision, a chain row that is PRESENT with
bid<=0 (a worthless losing call) books a max-loss exit
(`worthless_quote_exit=True`) rather than being treated as missing data and
dropped into `unresolved_data_gap` -- losers hit a 0 bid far more often than
winners, and silently excluding them from the scoreboard biases the verdict
away from REJECTED. A row that is genuinely ABSENT, or present but crossed/
non-finite (bid>0 but not `quote_valid`), still counts as a gap.
"""
from __future__ import annotations

from datetime import date

import numpy as np
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
    """Match by right/strike/expiration only -- NO quote_valid filter here.

    Callers decide what an absent-vs-present-but-bad quote means for their
    own purposes (fill loop books a worthless-quote max loss for a present
    row with bid<=0; TP scan just skips a present-but-invalid row).
    """
    strike_mask = np.isclose(ch["strike"].astype(float), strike, rtol=0.0, atol=1e-6)
    m: pd.DataFrame = ch.loc[(ch["right"] == "C") & strike_mask
                              & (ch["expiration"].map(_exp_date) == expiration)]
    return None if m.empty else m.iloc[0]


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
    sessions = trading_days(t_entry, config.H9_WINDOW[1])[1:]

    # 1. Protective exits are calendar-only decisions -- resolved BEFORE any
    #    quote scanning, so they cannot be starved by missing/invalid data.
    cutoff_session = None
    if next_report_iso:
        pre = trading_days(t_entry, next_report_iso)
        k = config.H9_NEXT_REPORT_EXIT_SESSIONS
        cutoff_session = pre[-(k + 1)] if len(pre) > k else t_entry
        if cutoff_session <= t_entry:
            raise ValueError(
                f"next report {next_report_iso} within "
                "H9_NEXT_REPORT_EXIT_SESSIONS+1 sessions of entry "
                f"{t_entry}; contaminated geometry must fail loud")

    dte_session = next(
        (s for s in sessions if _dte(s, expiration) <= config.H6_CLOSE_AT_DTE),
        None)

    if cutoff_session is not None and dte_session is not None:
        if cutoff_session <= dte_session:
            protective = (cutoff_session, "pre_next_report")
        else:
            protective = (dte_session, "dte_close")
    elif cutoff_session is not None:
        protective = (cutoff_session, "pre_next_report")
    elif dte_session is not None:
        protective = (dte_session, "dte_close")
    else:
        raise ValueError(
            f"no dte_close session found for {event.symbol} entry {t_entry} "
            f"expiration {expiration.isoformat()} within H9_WINDOW")
    protective_session, protective_reason = protective

    # 2. TP scan: strictly before the protective session. Missing chain or
    #    an invalid quote here is just skipped -- nothing was owed on those
    #    sessions, so they are not gaps (gaps are a fill-loop concept).
    decision = protective
    for s in sessions:
        if s >= protective_session:
            break
        try:
            ch = chain_provider(event.symbol, s)
        except FileNotFoundError:
            continue
        found = _find_row(ch, strike, expiration)
        if found is None:
            continue
        bid, ask = float(found["bid"]), float(found["ask"])
        if not quote_valid(bid, ask):
            continue
        if _proceeds(bid) >= cost * (1.0 + config.H6_TAKE_PROFIT_PCT):
            decision = (s, "take_profit")
            break

    dec_session, reason = decision
    base = {"symbol": event.symbol, "entry_date": event.t_entry,
            "capital_at_risk": cost}

    # 4. Fill loop: sessions strictly after the decision session.
    gaps: list[str] = []
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
        bid, ask = float(found["bid"]), float(found["ask"])
        if bid > 0 and quote_valid(bid, ask):
            proceeds = _proceeds(bid)
            return {**base, "pnl": round(proceeds - cost, 2), "exit_reason": reason,
                    "exit_fill_session": s, "gaps": gaps,
                    "worthless_quote_exit": False}
        if bid <= 0:
            return {**base, "pnl": round(-cost, 2), "exit_reason": reason,
                    "exit_fill_session": s, "gaps": gaps,
                    "worthless_quote_exit": True}
        # bid > 0 but crossed/non-finite -> data artifact, not a fill.
        gaps.append(s)
    return {**base, "pnl": None, "exit_reason": "unresolved_data_gap",
            "exit_fill_session": None, "gaps": gaps,
            "worthless_quote_exit": False}


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
    n_gap = len(trades) - len(complete)
    board["unresolved_data_gap_trades"] = n_gap
    board["worthless_quote_exits"] = sum(
        1 for t in trades if t.get("worthless_quote_exit"))
    board["unresolved_gap_capital"] = round(
        sum(t["capital_at_risk"] for t in trades if t["pnl"] is None), 2)
    # C6: mass-dropping unresolved-gap trades biases the CI toward NOT_REJECTED
    # (losers hit absent/crossed quotes more often). When the gap rate over all
    # triggered trades exceeds the disclosed ceiling, the sample is not
    # adjudicable -> force INSUFFICIENT_SAMPLE (never a REJECTED/NOT_REJECTED).
    gap_fraction = n_gap / len(trades) if trades else 0.0
    board["unresolved_gap_fraction"] = round(gap_fraction, 4)
    board["gap_gate_forced_insufficient"] = bool(
        trades and gap_fraction > config.H9_MAX_UNRESOLVED_GAP_FRACTION)
    if board["gap_gate_forced_insufficient"]:
        board["h9_outcome"] = "INSUFFICIENT_SAMPLE"
    return board
