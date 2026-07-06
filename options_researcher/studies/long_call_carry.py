"""Study D: what long calls and LEAPS actually cost on these names.

DESCRIPTIVE. Two lenses, conservative fills throughout (buy at ask x (1 +
haircut) + commission; sell at bid x (1 - haircut) - commission; level-exact
closes):

1. LEAPS carry: buy the call nearest 0.70 delta with DTE nearest 365 (band
   270-500), hold ~1 year, sell; compare against the stock's move over the
   same window and report capital-at-risk ratio (premium / 100 shares).
2. Short-dated long calls: monthly cadence, buy the 0.40-delta call on the
   nearest monthly, hold to EXPIRY (payoff = intrinsic - cost). The
   expected result is bleed; measuring the size is the point.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

import config
from options_researcher.chains import atm_row, nearest_monthly

DELTA_BAND = 0.15
LEAPS_BAND = (270, 500)


def _row_at(chains: dict, day_iso: str, expiration, strike: float,
            lookback: int = 10):
    """The (expiration, strike) call row on the last chain day <= day_iso
    within `lookback` days; None if absent (fail closed)."""
    days = [d for d in sorted(chains) if d <= day_iso][-lookback:]
    for d in reversed(days):
        ch = chains[d]
        exp_dates = pd.to_datetime(ch["expiration"]).dt.date
        rows = ch[(ch["right"] == "C") & (exp_dates == expiration)
                  & (ch["strike"] == strike)
                  & (ch["bid"] > 0) & (ch["ask"] >= ch["bid"])]
        if not rows.empty:
            return d, rows.iloc[0]
    return None, None


def _leaps_candidate(chain: pd.DataFrame, today: date, target_delta: float):
    calls = chain[(chain["right"] == "C") & (chain["bid"] > 0)
                  & (chain["ask"] >= chain["bid"])].copy()
    if calls.empty:
        return None
    calls["exp_date"] = pd.to_datetime(calls["expiration"]).dt.date
    calls["dte"] = calls["exp_date"].map(lambda e: (e - today).days)
    band = calls[(calls["dte"] >= LEAPS_BAND[0]) & (calls["dte"] <= LEAPS_BAND[1])]
    if band.empty:
        return None
    exp = band.loc[(band["dte"] - 365).abs().idxmin(), "exp_date"]
    on_exp = band[band["exp_date"] == exp]
    row = on_exp.loc[(on_exp["delta"].abs() - target_delta).abs().idxmin()]
    if abs(abs(float(row["delta"])) - target_delta) > DELTA_BAND:
        return None
    return row


def compute_leaps_cycles(symbol: str, closes: pd.Series,
                         chains: dict[str, pd.DataFrame], *,
                         target_delta: float = 0.70) -> pd.DataFrame:
    h, comm = config.SLIPPAGE_HAIRCUT, config.COMMISSION_PER_CONTRACT
    rows = []
    days = sorted(chains)
    r = days[0]
    while r is not None:
        cand = _leaps_candidate(chains[r], date.fromisoformat(r), target_delta)
        if cand is None:
            nxt = [d for d in days if d > r]
            r = nxt[0] if nxt else None
            continue
        exit_target = (date.fromisoformat(r) + timedelta(days=365)).isoformat()
        exit_day, exit_row = _row_at(chains, exit_target,
                                     cand["exp_date"], float(cand["strike"]))
        if exit_row is None or exit_day <= r or r not in closes.index \
                or exit_day not in closes.index:
            nxt = [d for d in days if d > r]
            r = nxt[0] if nxt else None
            continue
        cost = float(cand["ask"]) * (1 + h) * 100.0 + comm
        proceeds = float(exit_row["bid"]) * (1 - h) * 100.0 - comm
        rows.append({
            "entry": r, "exit": exit_day, "strike": float(cand["strike"]),
            "entry_delta": float(cand["delta"]), "cost": cost,
            "pnl": proceeds - cost,
            "stock_pnl_100sh": (float(closes[exit_day]) - float(closes[r])) * 100.0,
            "capital_ratio": cost / (float(closes[r]) * 100.0),
        })
        nxt = [d for d in days if d > exit_day]
        r = nxt[0] if nxt else None
    return pd.DataFrame(rows)


def compute_long_call_cycles(symbol: str, closes: pd.Series,
                             chains: dict[str, pd.DataFrame], *,
                             target_delta: float = 0.40) -> pd.DataFrame:
    h, comm = config.SLIPPAGE_HAIRCUT, config.COMMISSION_PER_CONTRACT
    rows = []
    days = sorted(chains)
    r = days[0]
    while True:
        today = date.fromisoformat(r)
        exp = nearest_monthly(chains[r], today) if r in chains else None
        if exp is None:
            break
        e_iso = exp.isoformat()
        if e_iso not in closes.index or r not in closes.index:
            break
        call = atm_row(chains[r], exp, right="C", target_delta=target_delta)
        if call is not None and abs(abs(float(call["delta"])) - target_delta) <= DELTA_BAND:
            k = float(call["strike"])
            cost = float(call["ask"]) * (1 + h) * 100.0 + comm
            payoff = max(0.0, float(closes[e_iso]) - k) * 100.0
            rows.append({"roll_date": r, "expiry": e_iso, "strike": k,
                         "cost": cost, "pnl": payoff - cost,
                         "won": payoff > cost})
        nxt = [d for d in days if d >= e_iso]
        if not nxt or nxt[0] == r:
            break
        r = nxt[0]
    return pd.DataFrame(rows)


def main():
    import os
    from datetime import date as _date

    from data.underlying_closes import load_closes
    from options_researcher.chains import load_range
    from research.facts import append_fact

    os.makedirs("reports", exist_ok=True)
    today = _date.today().isoformat()
    eras = {"MSFT": "2018-01-02", "AMZN": "2022-07-01",
            "VST": "2023-01-01", "CEG": "2023-01-01"}
    lines = [f"# Study D — long calls & LEAPS carry ({today})", "",
             "Descriptive; conservative fills; level-exact closes. "
             "Post-2022 data disclosed (facts.log PIVOT_4NAME_SCOPE).", ""]
    for symbol, start in eras.items():
        closes = load_closes(symbol, start, config.BACKTEST_END, allow_oos=True)
        chains = load_range(symbol, start, config.BACKTEST_END, allow_oos=True)
        lines.append(f"## {symbol} (from {start})\n")
        lp = compute_leaps_cycles(symbol, closes, chains)
        if len(lp):
            lines += [f"### LEAPS ~0.70Δ ~365d — {len(lp)} sequential cycles",
                      f"- option P&L total: ${lp['pnl'].sum():,.0f} vs same-"
                      f"window stock move (per 100sh): ${lp['stock_pnl_100sh'].sum():,.0f}",
                      f"- median capital at risk: {100 * lp['capital_ratio'].median():.1f}% "
                      f"of 100 shares; worst cycle: ${lp['pnl'].min():,.0f}", ""]
            append_fact(f"STUDY_D {symbol} LEAPS: cycles={len(lp)} "
                        f"pnl={lp['pnl'].sum():,.0f} "
                        f"stock={lp['stock_pnl_100sh'].sum():,.0f} "
                        f"cap_ratio_med={lp['capital_ratio'].median():.2f}")
        else:
            lines.append("### LEAPS: no scoreable cycles\n")
        sc = compute_long_call_cycles(symbol, closes, chains)
        if len(sc):
            wins = int(sc["won"].sum())
            lines += [f"### Monthly 0.40Δ long calls held to expiry — "
                      f"{len(sc)} cycles, {wins} profitable ({wins / len(sc):.0%})",
                      f"- total P&L: ${sc['pnl'].sum():,.0f}; total premium "
                      f"paid: ${sc['cost'].sum():,.0f}; mean/cycle: "
                      f"${sc['pnl'].mean():,.0f}", ""]
            append_fact(f"STUDY_D {symbol} calls40d: cycles={len(sc)} "
                        f"win={wins / len(sc):.0%} pnl={sc['pnl'].sum():,.0f}")
        else:
            lines.append("### Monthly long calls: no scoreable cycles\n")
    path = f"reports/{today}-study-d-long-calls-leaps.md"
    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
