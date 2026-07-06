"""Study E: monthly short puts and bull put credit spreads, hold to expiry.

Owner's priority structures. DESCRIPTIVE, not a verdict. Cycle: at each
monthly-expiration chain day r, sell the put nearest `target_delta`
(band +/- 0.15, else cycle skipped fail-closed) on the nearest monthly e;
optionally buy the put exactly `width` lower (bull put credit spread --
missing long strike skips the cycle, fail-closed). Conservative entry per
the frozen model: naked = short bid x (1 - haircut); spread = the existing
entry_credit_conservative helper. Commissions charged on opening legs only
(expiring legs cost nothing to not-close). Held to expiration, NO stop --
the loss engine H1 measured was the stop; this measures the raw structure.

At expiry (level-exact Yahoo closes): short put pays -max(0, K - close)x100;
the spread's long wing pays +max(0, K - width - close)x100. Naked puts here
are CASH-SECURED economics (loss to zero possible); the report states both
worst-cycle and the $600-cap feasibility view.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

import config
from options_researcher.chains import atm_row, nearest_monthly
from strategies.base import entry_credit_conservative

DELTA_BAND = 0.15


def _long_wing(chain: pd.DataFrame, expiration: date, strike: float):
    exp_dates = pd.to_datetime(chain["expiration"]).dt.date
    rows = chain[(chain["right"] == "P") & (exp_dates == expiration)
                 & (chain["strike"] == strike)
                 & (chain["bid"] > 0) & (chain["ask"] >= chain["bid"])]
    return None if rows.empty else rows.iloc[0]


def compute_put_cycles(symbol: str, closes: pd.Series,
                       chains: dict[str, pd.DataFrame], *,
                       target_delta: float = 0.30,
                       width: float | None = None) -> pd.DataFrame:
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
        short = atm_row(chains[r], exp, right="P", target_delta=target_delta)
        if short is not None and abs(abs(float(short["delta"])) - target_delta) <= DELTA_BAND:
            k = float(short["strike"])
            close_e = float(closes[e_iso])
            legs = 1
            if width is None:
                credit = (float(short["bid"]) * (1 - config.SLIPPAGE_HAIRCUT)
                          * 100.0)
                payoff = -max(0.0, k - close_e) * 100.0
                wing_k = None
            else:
                wing = _long_wing(chains[r], exp, k - width)
                if wing is None:
                    rows.append({"roll_date": r, "expiry": e_iso, "strike": k,
                                 "skipped": "no_long_wing"})
                    r = _advance(days, e_iso, r)
                    if r is None:
                        break
                    continue
                legs = 2
                credit = entry_credit_conservative(
                    float(short["bid"]), float(short["ask"]),
                    float(wing["bid"]), float(wing["ask"]),
                    config.SLIPPAGE_HAIRCUT) * 100.0
                payoff = (-max(0.0, k - close_e)
                          + max(0.0, k - width - close_e)) * 100.0
                wing_k = k - width
            commissions = config.COMMISSION_PER_CONTRACT * legs
            if credit <= 0:
                rows.append({"roll_date": r, "expiry": e_iso, "strike": k,
                             "skipped": "non_positive_credit"})
            else:
                rows.append({
                    "roll_date": r, "expiry": e_iso, "strike": k,
                    "wing": wing_k, "delta": float(short["delta"]),
                    "credit": credit - commissions,
                    "expired_worthless": close_e >= k,
                    "pnl": credit - commissions + payoff,
                    "skipped": None,
                })
        r = _advance(days, e_iso, r)
        if r is None:
            break
    return pd.DataFrame(rows)


def _advance(days, e_iso, current):
    nxt = [d for d in days if d >= e_iso]
    if not nxt or nxt[0] == current:
        return None
    return nxt[0]


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
    lines = [f"# Study E — monthly short puts & bull put spreads, hold to expiry ({today})",
             "", "Descriptive economics of the owner's priority structures; "
             "NOT a verdict. No stops (H1 measured the stop as the loss "
             "engine); conservative fills; level-exact closes. Naked-put "
             "rows are cash-secured economics. Post-2022 data disclosed "
             "(facts.log PIVOT_4NAME_SCOPE).", ""]
    for symbol, start in eras.items():
        closes = load_closes(symbol, start, config.BACKTEST_END, allow_oos=True)
        chains = load_range(symbol, start, config.BACKTEST_END, allow_oos=True)
        lines.append(f"## {symbol} (from {start})\n")
        for delta in (0.20, 0.30):
            for width in (None, 5.0):
                t = compute_put_cycles(symbol, closes, chains,
                                       target_delta=delta, width=width)
                label = f"{delta:.2f}Δ {'naked' if width is None else f'${width:.0f}-wide spread'}"
                if t.empty or t["skipped"].notna().all():
                    lines.append(f"- {label}: no scoreable cycles\n")
                    continue
                g = t[t["skipped"].isna()]
                skips = int(t["skipped"].notna().sum())
                wins = int(g["expired_worthless"].sum())
                lines += [f"### {label} — {len(g)} cycles ({skips} skipped), "
                          f"{wins} expired worthless ({wins / len(g):.0%})",
                          f"- total P&L: ${g['pnl'].sum():,.0f}; credit "
                          f"collected: ${g['credit'].sum():,.0f}; worst "
                          f"cycle: ${g['pnl'].min():,.0f}; mean/cycle: "
                          f"${g['pnl'].mean():,.0f}", ""]
                append_fact(f"STUDY_E {symbol} d={delta:.2f} "
                            f"{'naked' if width is None else 'w5'}: "
                            f"cycles={len(g)} win={wins / len(g):.0%} "
                            f"pnl={g['pnl'].sum():,.0f} "
                            f"worst={g['pnl'].min():,.0f}")
    path = f"reports/{today}-study-e-short-puts-verticals.md"
    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
