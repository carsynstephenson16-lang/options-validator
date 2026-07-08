# Monthly-vs-weekly open-interest concentration check (roadmap step 2).
# Question: the ~37-DTE-nearest profile often sampled thin WEEKLY expirations;
# do the power names' puts carry their open interest in standard MONTHLY
# expirations instead? Descriptive only -- no P&L. Reads all cached years
# (disclosed research look; see facts.log PIVOT_4NAME_SCOPE).
#
# Monthly definition: the standard listed monthly expires the 3rd Friday of
# its month; when that Friday is an exchange holiday (e.g. Good Friday) the
# listed expiration is the Thursday before, so a Thursday immediately
# preceding a 3rd Friday also counts as monthly.

import glob
import os
import sys
from datetime import date

import pandas as pd

import config
from options_researcher.chains import is_monthly, third_friday  # noqa: F401

CACHE_DIR = os.path.join(".cache", "chains")
SYMBOLS = list(config.UNIVERSE)
DTE_LO, DTE_HI = 15, 60          # window wide enough to always contain a monthly
SAMPLE_EVERY = 5
OI_FLOOR, SPREAD_MAX = config.MIN_OPEN_INTEREST, config.MAX_SPREAD_PCT


def day_stats(df: pd.DataFrame, file_date: date):
    """Per-day put-side stats over expirations in the DTE window."""
    puts = df[(df["right"] == "P") & (df["bid"] > 0) & (df["ask"] >= df["bid"])].copy()
    if puts.empty:
        return None
    puts["exp_date"] = pd.to_datetime(puts["expiration"]).dt.date
    puts["dte"] = puts["exp_date"].map(lambda e: (e - file_date).days)
    win = puts[(puts["dte"] >= DTE_LO) & (puts["dte"] <= DTE_HI)].copy()
    if win.empty:
        return None

    win["monthly"] = win["exp_date"].map(is_monthly)
    oi_total = float(win["open_interest"].sum())
    oi_monthly = float(win.loc[win["monthly"], "open_interest"].sum())
    share = oi_monthly / oi_total if oi_total > 0 else float("nan")

    monthlies = sorted(win.loc[win["monthly"], "exp_date"].unique())
    if not monthlies:
        return {"share": share, "m_spread": float("nan"), "m_oi": float("nan"),
                "m_liquid": float("nan"), "m_dte": float("nan")}

    m = win[win["exp_date"] == monthlies[0]]
    atm = m.loc[(m["delta"].abs() - 0.50).abs().idxmin()]
    mid = (atm["bid"] + atm["ask"]) / 2.0
    spread = (atm["ask"] - atm["bid"]) / mid if mid > 0 else float("nan")
    mids = (m["bid"] + m["ask"]) / 2.0
    liquid = int(((m["open_interest"] >= OI_FLOOR)
                  & (mids > 0)
                  & ((m["ask"] - m["bid"]) / mids <= SPREAD_MAX)).sum())
    return {"share": share, "m_spread": spread * 100.0,
            "m_oi": float(atm["open_interest"]), "m_liquid": liquid,
            "m_dte": float((monthlies[0] - file_date).days)}


def profile_symbol(symbol: str) -> None:
    files = sorted(glob.glob(os.path.join(CACHE_DIR, f"{symbol}_*.parquet")))
    if not files:
        print(f"{symbol}: NO CACHED DATA\n")
        return
    rows = []
    for f in files[::SAMPLE_EVERY]:
        iso = os.path.basename(f).split("_")[1].replace(".parquet", "")
        try:
            df = pd.read_parquet(f)
        except Exception as e:
            print(f"WARN unreadable cache file skipped: {f}: {e}", file=sys.stderr)
            continue
        s = day_stats(df, date.fromisoformat(iso))
        if s is not None:
            s["year"] = int(iso[:4])
            rows.append(s)
    if not rows:
        print(f"{symbol}: no usable sampled days\n")
        return
    frame = pd.DataFrame(rows)
    print(symbol)
    print("-" * 100)
    print(f"{'Year':<6}{'Days':<7}{'OI% in monthlies':<18}{'Mo-ATM spread%':<16}"
          f"{'Mo-ATM OI':<11}{'Mo liquid strikes':<19}{'Mo DTE':<7}")
    print("-" * 100)
    for year, g in frame.groupby("year"):
        print(f"{year:<6}{len(g):<7}{100 * g['share'].median():<18.1f}"
              f"{g['m_spread'].median():<16.2f}{g['m_oi'].median():<11.0f}"
              f"{g['m_liquid'].median():<19.1f}{g['m_dte'].median():<7.0f}")
    recent = frame[frame["year"] >= 2024]
    if len(recent):
        ok = (recent["m_oi"].median() >= OI_FLOOR
              and recent["m_spread"].median() <= SPREAD_MAX * 100)
        print(f"2024-26 medians: monthly-ATM OI {recent['m_oi'].median():.0f}, "
              f"spread {recent['m_spread'].median():.2f}% -> "
              f"{'PASSES frozen gates via monthlies' if ok else 'still FAILS frozen gates'}")
    print()


if __name__ == "__main__":
    for sym in SYMBOLS:
        profile_symbol(sym)
