"""QM mechanical signals: Breakout (momentum continuation) and Parabolic
(overextension, fade -- signal-only).

Spec: docs/superpowers/specs/2026-07-14-qm-signal-research-design.md §3.
Pure functions over a split-adjusted OHLCV frame (index = ISO date strings,
sorted ascending; columns open/high/low/close/volume as float, e.g. from
data.underlying_ohlcv.load_ohlcv_adjusted). No look-ahead by construction:
the signal at session t uses only rows dated <= t.

Every threshold comes from the injected ``params`` mapping (config QM_* names).
``qm_params()`` is the only config reader and refuses loudly while any QM_*
value is still the None scaffold -- the owner types the frozen numbers herself
(spec §7.1); nothing here may default or invent a value.
"""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd

import config

QM_PARAM_NAMES = (
    "QM_RUN_LOOKBACK",
    "QM_RUN_MIN_PCT",
    "QM_BASE_MIN_DAYS",
    "QM_BASE_MAX_DAYS",
    "QM_BASE_MAX_DEPTH",
    "QM_BASE_SMA",
    "QM_VOL_DRYUP_RATIO",
    "QM_PARA_LOOKBACK",
    "QM_PARA_MIN_PCT",
    "QM_PARA_GREEN_DAYS",
    "QM_PARA_EXT_PCT",
    "QM_PARA_SMA",
    "QM_HORIZONS",
    "QM_TRADABILITY_DTE",
    "QM_NTM_BAND",
)


def qm_params() -> dict[str, Any]:
    """Read the owner-typed QM_* block; refuse while any value is None."""
    missing = [n for n in QM_PARAM_NAMES if getattr(config, n) is None]
    if missing:
        raise RuntimeError(
            "QM pre-registration incomplete: the owner has not typed "
            f"{', '.join(missing)} into config.py (spec §7); refusing to run"
        )
    return {n: getattr(config, n) for n in QM_PARAM_NAMES}


QM_REQUIRED_FACTS = ("QM_SCOPE_OVERRIDE", "QM_STUDY_PREREG")


def qm_prereg_gate(base_dir: str = "ledger") -> str | None:
    """The one gate qm_study and qm_watch call before ANY output.

    Returns a refusal reason (spec §7: owner-typed values plus both
    pre-registration facts) or None when the arc is cleared to run.
    """
    try:
        qm_params()
    except RuntimeError as exc:
        return str(exc)
    from research.facts import read_facts

    lines = read_facts(base_dir=base_dir)
    for tag in QM_REQUIRED_FACTS:
        if not any(line.split("\t", 1)[-1].startswith(tag) for line in lines):
            return (
                f"QM pre-registration incomplete: no {tag} fact in "
                "ledger/facts.log (spec §7); refusing to run"
            )
    return None


def _position(frame: pd.DataFrame, t: str) -> int:
    try:
        return int(frame.index.get_loc(t))
    except KeyError as exc:
        raise ValueError(f"session {t} not in OHLCV index") from exc


def _sma(closes: np.ndarray, window: int) -> np.ndarray:
    """Trailing SMA; NaN until a full window exists (fail-closed)."""
    return (
        pd.Series(closes).rolling(int(window), min_periods=int(window)).mean().to_numpy()
    )


def breakout_detail(
    frame: pd.DataFrame, t: str, params: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Spec §3 Breakout at session t; returns fire detail or None.

    Base search is deterministic: the LARGEST L in [QM_BASE_MIN_DAYS,
    QM_BASE_MAX_DAYS] ending at t-1 satisfying depth and every-close>=SMA
    is THE base; the run/volume/trigger gates then apply to that base only
    (a failed gate never retries a smaller window).
    """
    pos = _position(frame, t)
    closes = frame["close"].to_numpy(dtype=float)
    highs = frame["high"].to_numpy(dtype=float)
    lows = frame["low"].to_numpy(dtype=float)
    vols = frame["volume"].to_numpy(dtype=float)
    sma = _sma(closes, int(params["QM_BASE_SMA"]))

    base_start = None
    for length in range(int(params["QM_BASE_MAX_DAYS"]), int(params["QM_BASE_MIN_DAYS"]) - 1, -1):
        s = pos - length
        if s < 0:
            continue
        w_low = lows[s:pos].min()
        w_high = highs[s:pos].max()
        if w_low <= 0:
            continue
        if (w_high - w_low) / w_low > float(params["QM_BASE_MAX_DEPTH"]):
            continue
        seg_sma = sma[s:pos]
        if np.isnan(seg_sma).any():
            continue
        if not (closes[s:pos] >= seg_sma).all():
            continue
        base_start = s
        break
    if base_start is None:
        return None

    # Prior run: QM_RUN_LOOKBACK sessions ending at the base's first session.
    r0 = max(0, base_start - int(params["QM_RUN_LOOKBACK"]) + 1)
    run_closes = closes[r0 : base_start + 1]
    if len(run_closes) < 2:
        return None
    running_min = np.minimum.accumulate(run_closes)
    if running_min.min() <= 0:
        return None
    if (run_closes / running_min - 1.0).max() < float(params["QM_RUN_MIN_PCT"]):
        return None

    run_vol = vols[r0 : base_start + 1].mean()
    if run_vol <= 0:
        return None
    if vols[base_start:pos].mean() > float(params["QM_VOL_DRYUP_RATIO"]) * run_vol:
        return None

    base_high = float(highs[base_start:pos].max())
    if closes[pos] <= base_high:
        return None
    return {
        "t": t,
        "base_start": str(frame.index[base_start]),
        "base_end": str(frame.index[pos - 1]),
        "base_len": pos - base_start,
        "base_high": base_high,
    }


def breakout_fires(frame: pd.DataFrame, params: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Deduped chronological Breakout fires (spec §3 dedupe): a qualifying
    streak counts once at its first session, and a refire requires the new
    base window to start strictly after the prior fire's trigger session."""
    fires: list[dict[str, Any]] = []
    prev_qualified = False
    last_trigger: str | None = None
    for t in frame.index:
        detail = breakout_detail(frame, str(t), params)
        qualified = detail is not None
        if (
            detail is not None
            and not prev_qualified
            and (last_trigger is None or detail["base_start"] > last_trigger)
        ):
            fires.append(detail)
            last_trigger = detail["t"]
        prev_qualified = qualified
    return fires


def parabolic_qualifies(frame: pd.DataFrame, t: str, params: Mapping[str, Any]) -> bool:
    """Spec §3 Parabolic conditions at session t (raw, before dedupe)."""
    pos = _position(frame, t)
    closes = frame["close"].to_numpy(dtype=float)

    lookback = int(params["QM_PARA_LOOKBACK"])
    if pos - lookback < 0:
        return False
    ref = closes[pos - lookback]
    if ref <= 0:
        return False
    if closes[pos] / ref - 1.0 < float(params["QM_PARA_MIN_PCT"]):
        return False

    green = int(params["QM_PARA_GREEN_DAYS"])
    if pos - green < 0:
        return False
    for i in range(pos - green + 1, pos + 1):
        if closes[i] <= closes[i - 1]:
            return False

    sma = _sma(closes[: pos + 1], int(params["QM_PARA_SMA"]))[-1]
    if np.isnan(sma):
        return False
    return closes[pos] >= (1.0 + float(params["QM_PARA_EXT_PCT"])) * sma


def parabolic_fires(frame: pd.DataFrame, params: Mapping[str, Any]) -> list[str]:
    """Deduped Parabolic fires: a qualifying streak counts once at its first
    session; a refire requires at least one non-qualifying session (spec §3)."""
    fires: list[str] = []
    prev_qualified = False
    for t in frame.index:
        qualified = parabolic_qualifies(frame, str(t), params)
        if qualified and not prev_qualified:
            fires.append(str(t))
        prev_qualified = qualified
    return fires
