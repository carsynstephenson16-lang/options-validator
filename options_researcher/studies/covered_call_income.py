"""Study C: monthly covered calls on the owner's share names (VST, AMZN)
vs buy-and-hold. DESCRIPTIVE INCOME TABLE, not a verdict.

Cycle definition: roll day r = a monthly expiration present in the cache
(or the first cached day for the opening cycle); at r, sell 1 call per 100
shares at the strike whose delta is nearest `target_delta` (accepted band
target +/- 0.15, else the cycle is SKIPPED -- fail closed) on the nearest
monthly expiration e; credit = bid*(1-haircut)*100 - commission (one leg,
one way; expiring options aren't closed). At e: assigned iff close(e) > K
(shares notionally sold at K and re-bought at close(e) frictionlessly --
stated simplification); cc_pnl = (min(close(e),K) - close(r))*100 + credit;
bh_pnl = (close(e) - close(r))*100. Dividends ignored on BOTH sides
(stated; slightly flatters neither leg's comparison).

The benchmark is buy-and-hold on the same shares: premium income's cost is
capped upside, and every report says so.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

import config
from options_researcher.chains import atm_row, nearest_monthly

DELTA_BAND = 0.15


def compute_cc_cycles(symbol: str, closes: pd.Series,
                      chains: dict[str, pd.DataFrame], *,
                      target_delta: float = 0.30) -> pd.DataFrame:
    rows = []
    days = sorted(chains)
    r = days[0]
    while True:
        today = date.fromisoformat(r)
        exp = nearest_monthly(chains[r], today) if r in chains else None
        if exp is None:
            break
        call = atm_row(chains[r], exp, right="C", target_delta=target_delta)
        e_iso = exp.isoformat()
        if e_iso not in closes.index or r not in closes.index:
            break
        if call is not None and abs(abs(float(call["delta"])) - target_delta) <= DELTA_BAND:
            k = float(call["strike"])
            credit = (float(call["bid"]) * (1 - config.SLIPPAGE_HAIRCUT) * 100
                      - config.COMMISSION_PER_CONTRACT)
            c_r, c_e = float(closes[r]), float(closes[e_iso])
            assigned = c_e > k
            rows.append({
                "roll_date": r, "expiry": e_iso, "strike": k,
                "delta": float(call["delta"]), "credit": credit,
                "assigned": assigned,
                "cc_pnl": (min(c_e, k) - c_r) * 100 + credit,
                "bh_pnl": (c_e - c_r) * 100,
            })
        nxt = [d for d in days if d >= e_iso]
        if not nxt or nxt[0] == r:
            break
        r = nxt[0]
    return pd.DataFrame(rows, columns=["roll_date", "expiry", "strike",
                                       "delta", "credit", "assigned",
                                       "cc_pnl", "bh_pnl"])


def main():
    import os
    from datetime import date as _date

    from data.underlying_closes import load_closes
    from options_researcher.chains import load_range
    from research.facts import append_fact

    os.makedirs("reports", exist_ok=True)
    today = _date.today().isoformat()
    eras = {"VST": "2023-01-01", "AMZN": "2018-01-02"}
    lines = [f"# Study C — monthly covered-call income vs buy-and-hold ({today})",
             "", "Descriptive income table, NOT a verdict. Benchmark is "
             "buy-and-hold on the same shares: premium's cost is capped "
             "upside. Frictionless share re-buy after assignment and no "
             "dividends on either side are stated simplifications. "
             "Post-2022 data disclosed (facts.log PIVOT_4NAME_SCOPE).", ""]
    for symbol, start in eras.items():
        closes = load_closes(symbol, start, config.BACKTEST_END,
                             allow_oos=True)
        chains = load_range(symbol, start, config.BACKTEST_END,
                            allow_oos=True)
        lines.append(f"## {symbol} (from {start})\n")
        for delta in (0.20, 0.30, 0.40):
            t = compute_cc_cycles(symbol, closes, chains, target_delta=delta)
            if t.empty:
                lines.append(f"- {delta:.2f}Δ: no scoreable cycles\n")
                continue
            cc, bh = t["cc_pnl"].sum(), t["bh_pnl"].sum()
            lines += [f"### target delta {delta:.2f} — {len(t)} cycles, "
                      f"{int(t['assigned'].sum())} assigned",
                      f"- premium collected: ${t['credit'].sum():,.0f}; "
                      f"CC total: ${cc:,.0f}; buy-and-hold: ${bh:,.0f}; "
                      f"difference: ${cc - bh:,.0f}",
                      f"- worst cycle (CC): ${t['cc_pnl'].min():,.0f}", ""]
            append_fact(f"STUDY_C {symbol} d={delta:.2f}: cycles={len(t)} "
                        f"assigned={int(t['assigned'].sum())} "
                        f"cc_total={cc:,.0f} bh_total={bh:,.0f}")
    path = f"reports/{today}-study-c-covered-calls.md"
    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
