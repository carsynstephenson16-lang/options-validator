"""options_researcher/h4_backtest.py -- H4 composite EVIDENCE backtest.

Replays the SEEDED book's frozen rules over the tradable era as one
portfolio: MSFT LEAPS (0.70d, ~365d, annual roll), VST cash-secured put
(0.20d monthly, hold to expiry), VST tactical long call (0.40d monthly,
hold to expiry). Reuses the golden-tested cycle engines from Studies D/E.

EVIDENCE ONLY (H4 prereg, frozen): these four names were selected knowing
the 2023+ boom, so this replay is hindsight-contaminated by construction
and is NEVER the verdict -- the forward paper window is. Banner appears in
every output.
"""
from __future__ import annotations

import pandas as pd

import config
from options_researcher.studies.covered_call_income import compute_cc_cycles  # noqa: F401 (menu parity)
from options_researcher.studies.long_call_carry import (compute_leaps_cycles,
                                                        compute_long_call_cycles)
from options_researcher.studies.short_put_vertical import compute_put_cycles

ERA_START = "2023-01-01"          # VST tradable era bounds the composite
BANNER = ("EVIDENCE ONLY -- hindsight-contaminated by name selection; "
          "the forward paper window is the verdict (H4 prereg).")


def _quarter(iso: str) -> str:
    y, m = int(iso[:4]), int(iso[5:7])
    return f"{y}Q{(m - 1) // 3 + 1}"


def quarterly(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Per-quarter P&L per leg + total. Each frame needs an exit-ish date
    column ('exit' or 'expiry') and 'pnl'."""
    cols = {}
    for name, f in frames.items():
        if f.empty:
            continue
        datecol = "exit" if "exit" in f.columns else "expiry"
        g = f.dropna(subset=["pnl"]).groupby(f[datecol].map(_quarter))["pnl"].sum()
        cols[name] = g
    out = pd.DataFrame(cols).fillna(0.0).sort_index()
    out["total"] = out.sum(axis=1)
    return out


def run_composite(era_start: str = ERA_START):
    from data.underlying_closes import load_closes
    from options_researcher.chains import load_range

    end = config.BACKTEST_END
    msft_closes = load_closes("MSFT", era_start, end, allow_oos=True)
    msft_chains = load_range("MSFT", era_start, end, allow_oos=True)
    vst_closes = load_closes("VST", era_start, end, allow_oos=True)
    vst_chains = load_range("VST", era_start, end, allow_oos=True)

    legs = {
        "leaps_MSFT": compute_leaps_cycles(
            "MSFT", msft_closes, msft_chains,
            target_delta=config.H4_THESIS_DELTA),
        "csp_VST": (lambda f: f[f["skipped"].isna()].copy() if len(f) else f)(
            compute_put_cycles("VST", vst_closes, vst_chains,
                               target_delta=config.H4_CSP_DELTA, width=None)),
        "tactical_VST": compute_long_call_cycles(
            "VST", vst_closes, vst_chains,
            target_delta=config.H4_TACTICAL_DELTA),
    }
    q = quarterly(legs)
    summary = {
        name: {"cycles": int(len(f)), "pnl": float(f["pnl"].sum()),
               "worst": float(f["pnl"].min()) if len(f) else 0.0}
        for name, f in legs.items()
    }
    summary["combined"] = {
        "pnl": float(q["total"].sum()),
        "quarters": int(len(q)),
        "positive_quarters": int((q["total"] > 0).sum()),
        "worst_quarter": float(q["total"].min()) if len(q) else 0.0,
    }
    return legs, q, summary


def main():
    import os
    from datetime import date as _date

    from research.facts import append_fact

    os.makedirs("reports", exist_ok=True)
    today = _date.today().isoformat()
    legs, q, s = run_composite()
    lines = [f"# H4 composite evidence backtest ({today})", "",
             f"**{BANNER}**", "",
             f"Era {ERA_START}..{config.BACKTEST_END}; frozen rules; "
             "conservative fills; hold-to-expiry; no stops; CSP collateral "
             "return basis = $14,500/contract (equity-side).", ""]
    for name, v in s.items():
        if name == "combined":
            continue
        lines.append(f"- **{name}**: {v['cycles']} cycles, total "
                     f"${v['pnl']:,.0f}, worst cycle ${v['worst']:,.0f}")
    c = s["combined"]
    lines += ["", f"**Combined: ${c['pnl']:,.0f} over {c['quarters']} "
              f"quarters; {c['positive_quarters']}/{c['quarters']} quarters "
              f"positive; worst quarter ${c['worst_quarter']:,.0f}.**", "",
              "## Per-quarter P&L", "", q.round(0).to_markdown()]
    path = f"reports/{today}-h4-composite-evidence.md"
    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    append_fact(f"H4_EVIDENCE_BACKTEST {ERA_START}..{config.BACKTEST_END}: "
                f"combined={c['pnl']:,.0f} "
                f"posQ={c['positive_quarters']}/{c['quarters']} "
                f"worstQ={c['worst_quarter']:,.0f} | "
                + " | ".join(f"{k}={v['pnl']:,.0f}/{v['cycles']}cyc"
                             for k, v in s.items() if k != "combined")
                + " | EVIDENCE ONLY, verdict=forward window")
    print(f"wrote {path}")
    print(BANNER)


if __name__ == "__main__":
    main()
