"""options_researcher/technicals.py -- offline MA/breakout/momentum snapshot.

Pure, deterministic technical context for the attractiveness dashboard
(spec: docs/superpowers/specs/2026-07-16-attractiveness-v2-technicals-
context-design.md). Presentation layer ONLY -- these numbers are never
strategy gates and never touch frozen H5/H6/H7 parameters. No network,
no file access: input is a pandas Series of closes (index = dates
ascending, values = float closes), output is a plain dict.

No look-ahead: `breakout_20d` compares the LAST close against the high of
the PRIOR `TECH_BREAKOUT_LOOKBACK` closes, excluding the last close itself.
"""
from __future__ import annotations

import math

import pandas as pd

import config

_NAN = float("nan")


def _sma(values: pd.Series, window: int) -> float:
    """Simple moving average of the trailing `window` closes; NaN if short."""
    if len(values) < window:
        return _NAN
    return float(values.iloc[-window:].mean())


def _pct_vs(price: float, level: float) -> float:
    """Pct distance of price above (+) / below (-) level; NaN when undefined."""
    if math.isnan(level) or level == 0.0:
        return _NAN
    return price / level - 1.0


def _momentum(values: pd.Series, sessions: int) -> float:
    """Pct change over `sessions` sessions; NaN if history is too short."""
    if len(values) < sessions + 1:
        return _NAN
    past = float(values.iloc[-1 - sessions])
    if past == 0.0:
        return _NAN
    return float(values.iloc[-1]) / past - 1.0


def technical_snapshot(closes: pd.Series) -> dict:
    """Deterministic technical snapshot of a close series (dates ascending).

    Returns floats (NaN when history is insufficient), booleans, and posture
    strings; never raises on short or empty input.
    """
    n = len(closes)
    win_short, win_mid, win_long = config.TECH_SMA_WINDOWS
    snap: dict = {}

    px = float(closes.iloc[-1]) if n > 0 else _NAN

    smas: dict[int, float] = {w: _sma(closes, w) for w in config.TECH_SMA_WINDOWS}
    for w, sma in smas.items():
        snap[f"sma{w}"] = sma
        snap[f"px_vs_sma{w}"] = _pct_vs(px, sma) if not math.isnan(px) else _NAN

    if any(math.isnan(s) for s in smas.values()) or math.isnan(px):
        snap["ma_posture"] = "insufficient_history"
    elif all(px > s for s in smas.values()):
        snap["ma_posture"] = "above_all"
    elif all(px < s for s in smas.values()):
        snap["ma_posture"] = "below_all"
    else:
        snap["ma_posture"] = "mixed"

    # Breakout vs the PRIOR `lookback` closes, EXCLUDING the last close (no
    # look-ahead: the bar being judged never contributes to its own hurdle).
    lookback = config.TECH_BREAKOUT_LOOKBACK
    if n >= lookback + 1:
        hh = float(closes.iloc[-1 - lookback:-1].max())
        snap["hh_20d"] = hh
        snap["breakout_20d"] = bool(px >= hh)
    else:
        snap["hh_20d"] = _NAN
        snap["breakout_20d"] = False

    if n > 0:
        high_52w = float(closes.iloc[-config.TECH_52W_LOOKBACK:].max())
        snap["high_52w"] = high_52w
        snap["dist_52w_high"] = _pct_vs(px, high_52w)
    else:
        snap["high_52w"] = _NAN
        snap["dist_52w_high"] = _NAN

    snap["mom_1m"] = _momentum(closes, config.TECH_MOM_1M)
    snap["mom_3m"] = _momentum(closes, config.TECH_MOM_3M)

    sma_s, sma_m, sma_l = smas[win_short], smas[win_mid], smas[win_long]
    if math.isnan(sma_l) or math.isnan(sma_m) or math.isnan(sma_s):
        snap["trend"] = "insufficient_history"
    elif sma_s > sma_m > sma_l:
        snap["trend"] = "up"
    elif sma_s < sma_m < sma_l:
        snap["trend"] = "down"
    else:
        snap["trend"] = "sideways"

    return snap


def technical_summary_line(snap: dict) -> str:
    """Short human strip, e.g.
    "above all MAs · 20d breakout · +4.2% 1M · 2.1% off 52w high".
    Skips NaN/insufficient pieces instead of printing them.
    """
    parts: list[str] = []

    posture_text = {
        "above_all": "above all MAs",
        "below_all": "below all MAs",
        "mixed": "mixed vs MAs",
    }.get(snap.get("ma_posture", ""))
    if posture_text is not None:
        parts.append(posture_text)

    if snap.get("breakout_20d"):
        parts.append("20d breakout")

    mom_1m = snap.get("mom_1m", _NAN)
    if isinstance(mom_1m, float) and not math.isnan(mom_1m):
        parts.append(f"{mom_1m:+.1%} 1M")

    dist = snap.get("dist_52w_high", _NAN)
    if isinstance(dist, float) and not math.isnan(dist):
        if dist >= 0.0:
            parts.append("at 52w high")
        else:
            parts.append(f"{abs(dist):.1%} off 52w high")

    if not parts:
        return "insufficient history"
    return " · ".join(parts)
