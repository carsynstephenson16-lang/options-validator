"""Study B: what earnings actually do to these names' options.

Per announcement e (using feature-frame rows, which are trading days):
  iv_runup  = atm_iv(last day <= e) - atm_iv(10 trading rows earlier)
  iv_crush  = atm_iv(first day > e) - atm_iv(last day <= e)
  abs_move_pct = |close(first day > e) / close(last day < e-window) - 1|
      measured close(day before announcement day) -> close(day after), so
      amc and bmo releases are both bracketed.
Events without a full bracket in the frame are SKIPPED (fail closed).
"""
from __future__ import annotations

from datetime import date

import pandas as pd


def compute_earnings_behavior(features: pd.DataFrame,
                              earnings: list[date]) -> pd.DataFrame:
    idx = list(features.index)
    rows = []
    for e in earnings:
        iso = e.isoformat()
        at_or_before = [i for i, d in enumerate(idx) if d <= iso]
        after = [i for i, d in enumerate(idx) if d > iso]
        if not at_or_before or not after or at_or_before[-1] < 10:
            continue
        i0, i1 = at_or_before[-1], after[0]
        iv = features["atm_iv"]
        close = features["close"]
        if pd.isna(iv.iloc[i0]) or pd.isna(iv.iloc[i1]) or pd.isna(iv.iloc[i0 - 10]):
            continue
        rows.append({
            "earnings_date": iso,
            "iv_runup": float(iv.iloc[i0] - iv.iloc[i0 - 10]),
            "iv_crush": float(iv.iloc[i1] - iv.iloc[i0]),
            "abs_move_pct": float(100 * abs(close.iloc[i1] / close.iloc[i0 - 1] - 1)),
        })
    return pd.DataFrame(rows,
                        columns=["earnings_date", "iv_runup", "iv_crush",
                                 "abs_move_pct"])


def main():
    import os
    from datetime import date as _date

    import config
    from options_researcher.earnings import load_earnings
    from options_researcher.features import load_features
    from research.facts import append_fact

    os.makedirs("reports", exist_ok=True)
    today = _date.today().isoformat()
    lines = [f"# Study B — earnings behavior ({today})", "",
             "Descriptive. Post-2022 data disclosed (facts.log "
             "PIVOT_4NAME_SCOPE).", ""]
    for symbol in config.UNIVERSE:
        table = compute_earnings_behavior(load_features(symbol),
                                          load_earnings(symbol))
        med = table[["iv_runup", "iv_crush", "abs_move_pct"]].median()
        lines += [f"## {symbol} — {len(table)} events", "",
                  f"Medians: run-up {med['iv_runup']:+.3f}, crush "
                  f"{med['iv_crush']:+.3f}, |move| {med['abs_move_pct']:.2f}%",
                  "", table.to_markdown(index=False), ""]
        append_fact(f"STUDY_B {symbol}: n={len(table)} "
                    f"runup_med={med['iv_runup']:+.3f} "
                    f"crush_med={med['iv_crush']:+.3f} "
                    f"absmove_med={med['abs_move_pct']:.2f}%")
    path = f"reports/{today}-study-b-earnings.md"
    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
