"""Study A: does a high IV rank actually precede larger realized moves?

Descriptive only. For days in each iv_rank bucket (>=0.70 vs <=0.30,
earnings weeks excluded to keep the comparison clean), measure the NEXT
`horizon_bd` business days: annualized realized vol and |total move|, and
compare with the move the option market implied (atm_iv * sqrt(h/252)).
An honest "no relationship" result is a fully successful outcome.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

HI, LO = 0.70, 0.30


def _forward_stats(close: pd.Series, horizon_bd: int):
    logret = np.log(close.astype(float)).diff()
    fwd_rv = (logret.rolling(horizon_bd).std(ddof=1) * np.sqrt(252.0)
              ).shift(-horizon_bd)
    fwd_move = (close.shift(-horizon_bd) / close - 1.0).abs()
    return fwd_rv, fwd_move


def compute_iv_vs_realized(features: pd.DataFrame, *,
                           horizon_bd: int = 21) -> pd.DataFrame:
    f = features[~features["earnings_week"].astype(bool)].copy()
    fwd_rv, fwd_move = _forward_stats(f["close"], horizon_bd)
    f["fwd_rv"], f["fwd_move"] = fwd_rv, fwd_move
    f = f.dropna(subset=["iv_rank", "atm_iv", "fwd_rv", "fwd_move"])

    rows = []
    for name, mask in (("iv_rank>=0.70", f["iv_rank"] >= HI),
                       ("iv_rank<=0.30", f["iv_rank"] <= LO)):
        g = f[mask]
        implied = g["atm_iv"] * np.sqrt(horizon_bd / 252.0)
        rows.append({
            "bucket": name,
            "n_days": int(len(g)),
            "iv_median": float(g["atm_iv"].median()),
            "fwd_rv_median": float(g["fwd_rv"].median()),
            "fwd_absmove_median_pct": float(100 * g["fwd_move"].median()),
            "implied_move_median_pct": float(100 * implied.median()),
        })
    return pd.DataFrame(rows)


def main():
    import os
    from datetime import date as _date

    import config
    from options_researcher.features import load_features
    from research.facts import append_fact

    os.makedirs("reports", exist_ok=True)
    today = _date.today().isoformat()
    lines = [f"# Study A — IV rank vs subsequent realized moves ({today})",
             "", "Descriptive; earnings weeks excluded; horizon 21 business "
             "days. Post-2022 data disclosed (facts.log PIVOT_4NAME_SCOPE).",
             ""]
    for symbol in config.UNIVERSE:
        table = compute_iv_vs_realized(load_features(symbol))
        lines += [f"## {symbol}", "", table.to_markdown(index=False), ""]
        hi = table.iloc[0]
        append_fact(
            f"STUDY_A {symbol}: iv_rank>=0.70 days n={hi['n_days']} "
            f"iv_med={hi['iv_median']:.3f} fwd_rv_med={hi['fwd_rv_median']:.3f}")
    path = f"reports/{today}-study-a-iv-vs-realized.md"
    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
