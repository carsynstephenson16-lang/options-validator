"""options_researcher/entry_watch.py -- pre-registered LEAPS entry-trigger watch.

Prints one WAIT/FIRE line per name in config.H5_ENTRY_TRIGGERS. FIRE means
"evaluate a 0.70-delta LEAPS per H5 CORE rules now" -- never "buy". The rule
is pre-registered in ledger/facts.log (H5_ENTRY_TRIGGER_PREREG 2026-07-07).
Read-only: never writes positions, never trades. NaN IV-rank counts as
UNMET (unknown never passes a gate).
"""
from __future__ import annotations

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
