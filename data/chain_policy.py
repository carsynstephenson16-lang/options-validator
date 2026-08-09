from __future__ import annotations

import pandas as pd

import config


def _pick_col(frame: pd.DataFrame, candidates, ctx: str) -> str:
    for name in candidates:
        if name in frame.columns:
            return name
    raise ValueError(
        f"{ctx}: none of {list(candidates)} present; got columns {sorted(frame.columns)}"
    )


_KEY_COLS = ["expiration", "strike", "right"]


def _normalize_contract_keys(frame: pd.DataFrame, ctx: str) -> pd.DataFrame:
    """Lowercase columns; normalize right to P/C; one row per contract (last
    report of the day wins when a timestamp column is present)."""
    out = frame.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    missing = [k for k in _KEY_COLS if k not in out.columns]
    if missing:
        raise ValueError(
            f"{ctx}: missing contract key column(s) {missing}; got {sorted(out.columns)}"
        )
    right = out["right"].astype(str).str.strip().str.upper().str[0]
    if not set(right.unique()) <= {"P", "C"}:
        raise ValueError(
            f"{ctx}: unexpected right values {sorted(out['right'].astype(str).unique())}"
        )
    out["right"] = right
    out["expiration"] = out["expiration"].astype(str)
    out["strike"] = pd.to_numeric(out["strike"], errors="coerce")
    if "timestamp" in out.columns:
        out = out.sort_values("timestamp", kind="stable")
    return out.drop_duplicates(subset=_KEY_COLS, keep="last")


def mid_price(bid: float, ask: float) -> float:
    """Quote mid. Fills must be at this OR WORSE -- never the favorable side."""
    return (bid + ask) / 2.0


def passes_liquidity(open_interest: float, bid: float, ask: float) -> bool:
    """A contract must pass before it is tradeable. Check BOTH legs."""
    if open_interest < config.MIN_OPEN_INTEREST:
        return False
    if bid < 0 or ask <= 0 or ask < bid:
        return False
    mid = mid_price(bid, ask)
    if mid <= 0:
        return False
    return ((ask - bid) / mid) <= config.MAX_SPREAD_PCT
