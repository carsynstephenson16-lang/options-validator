"""Card 3 -- "near-the-bottom long call" EXPLORATORY IN-SAMPLE historical study.

Owner-frozen "freeze as is" 2026-07-18; pre-registered as ledger trial_intent
CARD3-near-bottom-long-call-v1 BEFORE any result existed. This produces
EXPLORATORY IN-SAMPLE evidence, NEVER a verdict.

Seal discipline: every close and every chain is read IN-SAMPLE ONLY, over
[config.CARD3_START, config.IN_SAMPLE_END], through the audited cached-only
paths WITHOUT allow_oos. The chain provider is existence-gated (never fetches)
and the adapter's OOS guard is a belt-and-suspenders backstop -- a single
post-IN_SAMPLE_END read raises rather than silently leaking the holdout.

Cost model is the frozen repo surface (data.pandas_feed.adverse_buy /
adverse_sell): a long call is BOUGHT at ask + SLIPPAGE_HAIRCUT rounded up
(mid-or-worse + half-spread on the single leg) plus COMMISSION_PER_CONTRACT,
and SOLD at bid - haircut rounded down minus commission (commission both ways).
Nothing here reinvents a fill.

Frozen operationalizations of the card's prose (all windows END at the decision
close t, so they use only information available at t -- no look-ahead):
  * cond 1 "close >= 30% below trailing 252-session high":
        close_t <= (1 - CARD3_DD_MIN) * max(close over trailing 252 sessions)
  * cond 2 "close within 10% of trailing 60-session low":
        close_t <= (1 + CARD3_NEAR_LOW_PCT) * min(close over trailing 60 sessions)
  * cond 3 "close is NOT a new 20-session low":
        close_t >= min(close over the PRIOR 20 sessions, t-20..t-1). A close that
        breaks strictly below the prior-20 minimum IS a new low (excluded); a tie
        is not a new low (kept). Ties are immaterial in practice because cond 4
        already restricts to up-days.
  * cond 4 "close > previous close": close_t > close_{t-1}.
Signals require a full trailing 252-session history (min_periods), so a name
with fewer than 252 in-sample closes produces zero signals (recorded as such,
never an error).

Exit fills use the SAME session's conservative sell, symmetric with the card's
same-close entry fill and never optimistic (adverse_sell is below the mid that
triggered a take-profit). Exit priority, checked daily at close, first trigger
wins, with take-profit ahead of the time-exit on a shared day:
  1. take-profit  -- contract mid >= CARD3_TP_MULT * entry mid
  2. time-exit    -- DTE <= CARD3_CLOSE_AT_DTE (calendar-only backstop)
  3. worthless    -- a present bid <= 0 at the exit session books the max loss
No stop-loss; positions HOLD THROUGH earnings. An entry whose exit can only be
observed after IN_SAMPLE_END (expiration in the sealed window) is recorded
pnl=None / open_at_in_sample_end and excluded from the scoreboard rather than
peeking past the seal. EOD gaps on an exit-check session are skipped and logged.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

import config
import metrics
from data.cache_runner import trading_days
from data.pandas_feed import adverse_buy, adverse_sell, quote_valid
from data.thetadata_adapter import _cache_path, get_eod_chain, passes_liquidity
from data.underlying_closes import load_closes_adjusted
from options_researcher.chains import is_monthly

VERDICT_REJECTED = "REJECTED"
VERDICT_GRADUATE = "GRADUATE TO FORWARD-PAPER DESIGN"
VERDICT_INCONCLUSIVE = "INSUFFICIENT SAMPLE / INCONCLUSIVE"


# --------------------------------------------------------------------------
# Entry signal
# --------------------------------------------------------------------------
def entry_signal_frame(closes: pd.Series) -> pd.DataFrame:
    """Per-session boolean frame for the four frozen entry conditions.

    `closes` is an ascending, date-(ISO-string)-indexed float Series of
    SPLIT-ADJUSTED closes (the only series trailing price signals may consume).
    """
    c = closes.sort_index().astype(float)
    high_252 = c.rolling(config.CARD3_DD_LOOKBACK_D,
                         min_periods=config.CARD3_DD_LOOKBACK_D).max()
    low_60 = c.rolling(config.CARD3_NEAR_LOW_LOOKBACK_D,
                       min_periods=config.CARD3_NEAR_LOW_LOOKBACK_D).min()
    prior_low_20 = c.shift(1).rolling(config.CARD3_NEW_LOW_LOOKBACK_D,
                                      min_periods=config.CARD3_NEW_LOW_LOOKBACK_D).min()
    prev = c.shift(1)

    cond1 = c <= (1.0 - config.CARD3_DD_MIN) * high_252
    cond2 = c <= (1.0 + config.CARD3_NEAR_LOW_PCT) * low_60
    cond3 = c >= prior_low_20
    cond4 = c > prev
    signal = cond1 & cond2 & cond3 & cond4
    return pd.DataFrame(
        {"close": c, "cond1": cond1, "cond2": cond2, "cond3": cond3,
         "cond4": cond4, "signal": signal.fillna(False)})


def entry_signals(closes: pd.Series) -> list[str]:
    """ISO dates (ascending) where all four entry conditions hold."""
    frame = entry_signal_frame(closes)
    return [str(d) for d in frame.index[frame["signal"].to_numpy()]]


# --------------------------------------------------------------------------
# Contract selection + costs (frozen repo cost model)
# --------------------------------------------------------------------------
def _exp_date(e) -> date:
    return e if isinstance(e, date) else date.fromisoformat(str(e)[:10])


def _dte(iso: str, expiration) -> int:
    return (_exp_date(expiration) - date.fromisoformat(iso)).days


def select_contract(chain: pd.DataFrame, entry_iso: str) -> pd.Series | None:
    """Highest-delta CALL in the frozen delta/DTE bands on a standard monthly
    expiration, passing both quote sanity and the liquidity gates. None if no
    contract qualifies."""
    calls: pd.DataFrame = chain.loc[chain["right"] == "C"].copy()
    lo_d, hi_d = config.CARD3_DELTA_BAND
    lo_t, hi_t = config.CARD3_DTE_BAND
    if calls.empty:
        return None
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
    """Conservative total entry cost (premium + entry costs) for one contract,
    or None if it exceeds the $600 per-trade cap. adverse_buy already encodes
    mid-or-worse + half-spread + slippage on the single leg."""
    if row is None:
        return None
    cost = round(adverse_buy(row["ask"]) * 100.0 + config.COMMISSION_PER_CONTRACT, 2)
    return cost if cost <= config.MAX_LOSS_PER_TRADE else None


def entry_mid(row: pd.Series) -> float:
    """Raw quote mid at entry -- the take-profit reference (card: 'mid >= 2x
    entry mid'). The FILL is still the conservative adverse price; only the
    trigger is measured on the mid."""
    return (float(row["bid"]) + float(row["ask"])) / 2.0


def _proceeds(bid: float) -> float:
    """Conservative sell proceeds for one contract (commission on the way out)."""
    return round(adverse_sell(bid) * 100.0 - config.COMMISSION_PER_CONTRACT, 2)


def _find_row(chain: pd.DataFrame, strike: float, expiration: date) -> pd.Series | None:
    """The call row matching strike/expiration, or None if absent. No quote
    filter here -- callers decide what an absent vs present-but-bad quote means."""
    import numpy as np
    strike_mask = np.isclose(chain["strike"].astype(float), strike, rtol=0.0, atol=1e-6)
    m: pd.DataFrame = chain.loc[(chain["right"] == "C") & strike_mask
                                & (chain["expiration"].map(_exp_date) == expiration)]
    return None if m.empty else m.iloc[0]


# --------------------------------------------------------------------------
# One trade: entry -> exit
# --------------------------------------------------------------------------
def simulate_trade(symbol: str, entry_iso: str, chain_provider,
                   sessions_after: list[str]) -> dict | None:
    """One signal -> one trade dict, or None when no tradable contract exists
    or the entry cost exceeds the cap (no position is opened). `chain_provider`
    (symbol, iso) -> chain DataFrame, raising FileNotFoundError on a gap.
    `sessions_after` = in-sample trading sessions strictly after entry."""
    entry_chain = chain_provider(symbol, entry_iso)  # FileNotFoundError -> caller skips
    row = select_contract(entry_chain, entry_iso)
    cost = entry_cost_if_within_cap(row)
    if row is None or cost is None:
        return None
    expiration = _exp_date(row["expiration"])
    strike = float(row["strike"])
    e_mid = entry_mid(row)
    base = {
        "symbol": symbol, "entry_date": entry_iso,
        "capital_at_risk": cost, "economic_max_loss": cost,
        "strike": strike, "expiration": expiration.isoformat(),
        "delta": float(row["delta"]), "entry_mid": e_mid,
    }

    # time-exit is a pure calendar backstop: first session with DTE <= threshold.
    protective = next(
        (s for s in sessions_after if _dte(s, expiration) <= config.CARD3_CLOSE_AT_DTE),
        None)

    # take-profit scan: sessions up to AND INCLUDING the protective session
    # (TP wins a shared day). A missing/invalid quote is simply skipped -- the
    # scan owes nothing on those sessions, so they are not gaps.
    tp_session = None
    for s in sessions_after:
        if protective is not None and s > protective:
            break
        try:
            ch = chain_provider(symbol, s)
        except FileNotFoundError:
            continue
        found = _find_row(ch, strike, expiration)
        if found is None:
            continue
        bid, ask = float(found["bid"]), float(found["ask"])
        if not quote_valid(bid, ask):
            continue
        if (bid + ask) / 2.0 >= config.CARD3_TP_MULT * e_mid:
            tp_session = s
            break

    if tp_session is not None:
        decision_session, reason = tp_session, "take_profit"
    elif protective is not None:
        decision_session, reason = protective, "time_exit"
    else:
        # exit can only be observed past the seal -> do not peek.
        return {**base, "pnl": None, "exit_reason": "open_at_in_sample_end",
                "exit_fill_session": None, "gaps": []}

    # Fill loop from the decision session forward (same-close conservative fill).
    # For take-profit the decision session already carries a valid bid>0 quote,
    # so it fills immediately. For a time-exit an EOD gap or crossed quote is
    # skipped-and-logged; a present bid<=0 books the worthless max loss.
    gaps: list[str] = []
    start_idx = sessions_after.index(decision_session)
    for s in sessions_after[start_idx:]:
        try:
            ch = chain_provider(symbol, s)
        except FileNotFoundError:
            gaps.append(s)
            continue
        found = _find_row(ch, strike, expiration)
        if found is None:
            gaps.append(s)
            continue
        bid, ask = float(found["bid"]), float(found["ask"])
        if bid > 0 and quote_valid(bid, ask):
            return {**base, "pnl": round(_proceeds(bid) - cost, 2),
                    "exit_reason": reason, "exit_fill_session": s, "gaps": gaps,
                    "worthless_quote_exit": False}
        if bid <= 0:
            return {**base, "pnl": round(-cost, 2), "exit_reason": reason,
                    "exit_fill_session": s, "gaps": gaps,
                    "worthless_quote_exit": True}
        gaps.append(s)  # crossed / non-finite -> data artifact, not a fill
    return {**base, "pnl": None, "exit_reason": "open_at_in_sample_end",
            "exit_fill_session": None, "gaps": gaps}


# --------------------------------------------------------------------------
# Book loop over one name, then the whole universe
# --------------------------------------------------------------------------
def run_symbol(symbol: str, chain_provider, closes: pd.Series,
               sessions: list[str]) -> dict:
    """All Card-3 trades for one name under the book rules: max 1 open
    position, no new entry while open, re-entry allowed on any later signal."""
    sig_dates = entry_signals(closes)
    trades: list[dict] = []
    skips: list[dict] = []
    open_until: str | None = None  # exit session that blocks new entries (inclusive)
    for d in sig_dates:
        if open_until is not None and d <= open_until:
            skips.append({"date": d, "reason": "position_open"})
            continue
        after = [s for s in sessions if s > d]
        try:
            trade = simulate_trade(symbol, d, chain_provider, after)
        except FileNotFoundError:
            skips.append({"date": d, "reason": "entry_chain_gap"})
            continue
        if trade is None:
            skips.append({"date": d, "reason": "no_tradable_contract_or_over_cap"})
            continue
        trades.append(trade)
        if trade["pnl"] is None:
            open_until = config.IN_SAMPLE_END  # unresolved -> blocks the rest
        else:
            open_until = trade["exit_fill_session"]
    return {"symbol": symbol, "n_signals": len(sig_dates),
            "trades": trades, "skips": skips}


def _cached_chain_provider(symbol: str):
    """Existence-gated, cached-only, in-sample chain reader (never fetches).

    Single-day equivalent of data.pandas_feed.load_cached_chains: a day is only
    read when its parquet already exists, and get_eod_chain's OOS guard refuses
    any date past IN_SAMPLE_END even from cache. All requested dates are
    in-sample, so the guard never fires -- it is a seal backstop, not a path."""
    def provider(sym: str, iso: str) -> pd.DataFrame:
        if not _cache_path(sym, iso).exists():
            raise FileNotFoundError(f"no cached chain for {sym} {iso}")
        return get_eod_chain(sym, iso, allow_oos=False)
    return provider


def card3_verdict(board: dict) -> str:
    """The frozen verdict lines, applied to the scoreboard."""
    n_loss = board["n_losses"]
    lo, hi = board["expectancy_CI90"]
    if n_loss < config.MIN_LOSSES_FOR_VERDICT:
        return VERDICT_INCONCLUSIVE
    if hi < 0:
        return VERDICT_REJECTED
    if lo > 0:
        return VERDICT_GRADUATE
    return VERDICT_INCONCLUSIVE


def run_study(symbols: list[str] | None = None, *,
              sessions: list[str] | None = None) -> dict:
    """Run the frozen card once over the real in-sample cache and adjudicate."""
    symbols = list(symbols if symbols is not None else config.H7_BACKTEST_SYMBOLS)
    if sessions is None:
        sessions = trading_days(config.CARD3_START, config.IN_SAMPLE_END)

    per_symbol: list[dict] = []
    all_trades: list[dict] = []
    skipped_names: list[dict] = []
    for sym in symbols:
        try:
            closes = load_closes_adjusted(sym, config.CARD3_START, config.IN_SAMPLE_END)
        except Exception as exc:  # noqa: BLE001 -- closes unavailable -> skip-and-log the name
            skipped_names.append({"symbol": sym, "reason": f"closes_unavailable: {exc}"})
            continue
        provider = _cached_chain_provider(sym)
        res = run_symbol(sym, provider, closes, sessions)
        per_symbol.append(res)
        all_trades.extend(res["trades"])

    complete = [t for t in all_trades if t["pnl"] is not None]
    board = metrics.scoreboard(
        complete, label="CARD3 near-bottom long call (in-sample, exploratory)")
    board["card3_verdict"] = card3_verdict(board)
    unresolved = [t for t in all_trades if t["pnl"] is None]
    return {
        "symbols": symbols,
        "n_signals": sum(r["n_signals"] for r in per_symbol),
        "n_fills": len(all_trades),
        "n_complete": len(complete),
        "n_unresolved_open_at_in_sample_end": len(unresolved),
        "skipped_names": skipped_names,
        "per_symbol": per_symbol,
        "trades": all_trades,
        "scoreboard": board,
    }


def _per_symbol_summary(res: dict) -> list[dict]:
    rows = []
    for r in res["per_symbol"]:
        complete = [t for t in r["trades"] if t["pnl"] is not None]
        rows.append({
            "symbol": r["symbol"],
            "signals": r["n_signals"],
            "fills": len(r["trades"]),
            "complete": len(complete),
            "unresolved": sum(1 for t in r["trades"] if t["pnl"] is None),
            "wins": sum(1 for t in complete if t["pnl"] > 0),
            "losses": sum(1 for t in complete if t["pnl"] < 0),
            "total_pnl": round(sum(t["pnl"] for t in complete), 2),
        })
    return rows


def main() -> None:  # pragma: no cover -- CLI convenience
    import json

    res = run_study()
    board = res["scoreboard"]
    print("=" * 72)
    print("CARD 3 -- near-the-bottom long call (EXPLORATORY IN-SAMPLE; NOT a verdict)")
    print("=" * 72)
    print(f"signals={res['n_signals']}  fills={res['n_fills']}  "
          f"complete={res['n_complete']}  "
          f"unresolved(open@IS_END)={res['n_unresolved_open_at_in_sample_end']}")
    if res["skipped_names"]:
        print("skipped names:", res["skipped_names"])
    print("per-symbol:")
    for row in _per_symbol_summary(res):
        print("  ", row)
    print("-" * 72)
    metrics.print_scoreboard(board)
    print("CARD3 frozen verdict line:", board["card3_verdict"])
    print(json.dumps({"expectancy_CI90": board["expectancy_CI90"],
                      "n_losses": board["n_losses"]}, default=str))


if __name__ == "__main__":
    main()
