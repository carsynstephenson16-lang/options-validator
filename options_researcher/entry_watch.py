"""options_researcher/entry_watch.py -- pre-registered LEAPS entry-trigger watch.

Prints one WAIT/FIRE line per name in config.H5_ENTRY_TRIGGERS. FIRE means
"evaluate a 0.70-delta LEAPS per H5 CORE rules now" -- never "buy". The rule
is pre-registered in ledger/facts.log (H5_ENTRY_TRIGGER_PREREG 2026-07-07).
Read-only: never writes positions, never trades. NaN IV-rank counts as
UNMET (unknown never passes a gate).
"""
from __future__ import annotations

import glob
import os
from datetime import date

import pandas as pd

import config
from data.thetadata_adapter import passes_liquidity


def trigger_status(symbol: str, *, close: float, iv_rank: float,
                   leaps_row) -> dict:
    """Grade one name against the frozen entry trigger. `leaps_row` is the
    0.70-delta LEAPS candidate row from the latest cached chain, or None
    when no candidate exists in the DTE band."""
    level = config.H5_ENTRY_TRIGGERS[symbol]
    price_ok = close <= level
    iv_ok = iv_rank <= config.H5_ENTRY_IVR_MAX  # NaN compares False
    liq_ok = bool(leaps_row is not None and passes_liquidity(
        leaps_row["open_interest"], leaps_row["bid"], leaps_row["ask"]))
    unmet = []
    if not price_ok:
        unmet.append(f"close ${close:,.2f} > trigger ${level:,.2f}")
    if not iv_ok:
        unmet.append(f"IV-rank {iv_rank:.2f} > {config.H5_ENTRY_IVR_MAX}")
    if not liq_ok:
        unmet.append("LEAPS fails liquidity gates" if leaps_row is not None
                     else "no LEAPS candidate in DTE band")
    return {"symbol": symbol, "close": close, "trigger": level,
            "iv_rank": iv_rank, "price_ok": price_ok, "iv_ok": iv_ok,
            "liq_ok": liq_ok, "unmet": unmet,
            "verdict": "WAIT" if unmet else "FIRE"}


def _gather() -> list[dict]:
    """Real project state: free underlying closes, cached features, latest
    cached chain per name. Read-only; no network beyond the closes cache."""
    from data.underlying_closes import load_closes
    from options_researcher.features import load_features
    from options_researcher.studies.long_call_carry import _leaps_candidate

    out = []
    today = date.today().isoformat()
    for symbol in config.H5_ENTRY_TRIGGERS:
        closes = load_closes(symbol, "2018-01-01", today, allow_oos=True)
        close = float(closes.iloc[-1])
        close_asof = str(closes.index[-1])[:10]
        ivr = load_features(symbol)["iv_rank"].iloc[-1]
        iv_rank = float(ivr) if pd.notna(ivr) else float("nan")
        files = sorted(glob.glob(os.path.join(".cache", "chains",
                                              f"{symbol}_*.parquet")))
        leaps_row, chain_asof = None, None
        if files:
            chain_asof = (os.path.basename(files[-1]).split("_")[1]
                          .replace(".parquet", ""))
            chain = pd.read_parquet(files[-1])
            leaps_row = _leaps_candidate(chain, date.fromisoformat(chain_asof),
                                         config.H4_THESIS_DELTA)
        row = trigger_status(symbol, close=close, iv_rank=iv_rank,
                             leaps_row=leaps_row)
        row["close_asof"] = close_asof
        row["chain_asof"] = chain_asof
        out.append(row)
    return out


def main(rows: list[dict] | None = None) -> None:
    if rows is None:
        rows = _gather()
    print("H5 LEAPS ENTRY TRIGGER WATCH (pre-registered "
          "H5_ENTRY_TRIGGER_PREREG; this tool alerts, it never auto-enters)")
    for r in rows:
        line = (f"{r['symbol']}: {r['verdict']}  close ${r['close']:,.2f} "
                f"(as of {r['close_asof']}) vs trigger ${r['trigger']:,.2f}; "
                f"IV-rank {r['iv_rank']:.2f} (max "
                f"{config.H5_ENTRY_IVR_MAX})")
        if r["unmet"]:
            line += " -- waiting on: " + "; ".join(r["unmet"])
        else:
            line += (" -- ALL conditions met: evaluate the 0.70-delta LEAPS "
                     "per H5 CORE rules with FRESH data before any entry "
                     "(re-subscribe/audit first if the chain cache is old)")
        print(line)
        if r["chain_asof"] and r["chain_asof"] < r["close_asof"]:
            print(f"  note: chain cache is stale ({r['chain_asof']} < close "
                  f"{r['close_asof']}) -- liquidity check may be outdated")


if __name__ == "__main__":
    main()
