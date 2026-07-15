"""tools/qm_pooled_readings.py -- read-only reducer that reproduces the
pooled decision statistics recorded in the QM_STUDY_RESULT 2026-07-14 ledger
fact (per-fire forward return minus the SAME NAME's unconditional baseline
MEDIAN at the same horizon, pooled median across h7_scope.watch_universe(),
plus pooled tradability). It writes nothing, appends no facts, and is NOT a
study re-run -- the one-run-per-vintage contract (QM_STUDY_PREREG) belongs to
`options_researcher.qm_study`, not to this file. It exists only so the fact's
headline numbers are reproducible from committed code instead of a session
scratchpad script.

Reuses qm_study's own loaders and metric functions (forward_returns,
baseline_stats, _aggregate_tradability, _default_load_adjusted,
_default_load_raw, _default_load_chain) and qm_signals' fire detectors and
config gate (qm_params, qm_prereg_gate, breakout_fires, parabolic_fires) --
no metric or gate logic is duplicated here.

CAVEAT: the universe is evaluated AT RUN TIME via h7_scope.watch_universe().
The QM_STUDY_RESULT fact was recorded against the 2026-07-14 data vintage and
watchlist; H7_AMENDMENT_V1_5 (same day) later staged IREN onto the watchlist
*after* that study ran. Any watchlist or cache change since 2026-07-14 means
these pooled numbers reproduce the fact only for the SAME active universe and
data vintage as the original run -- a different universe or later cache is a
disclosed non-reproduction, not a bug.

Run:
    uv run python tools/qm_pooled_readings.py
"""

from __future__ import annotations

import os
import sys
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from options_researcher import h7_scope, qm_signals  # noqa: E402
from options_researcher.qm_study import (  # noqa: E402
    START_ISO,
    _aggregate_tradability,
    _default_load_adjusted,
    _default_load_chain,
    _default_load_raw,
    _now_ny_iso,
    baseline_stats,
    forward_returns,
)

SETUPS = ("breakout", "parabolic")


# --------------------------------------------------------------------------
# Pure pooling core -- no I/O, no config; testable against tiny synthetic
# frames with hand-computed excess values.
# --------------------------------------------------------------------------


def pool_excess_across_universe(
    name_fires: Sequence[tuple[pd.DataFrame, Sequence[str]]],
    horizons: Sequence[int],
) -> dict[int, list[float]]:
    """Pool per-fire excess returns across every (frame, fires_iso) pair.

    Excess at horizon h = that fire's forward return at h minus the SAME
    frame's unconditional baseline MEDIAN return at h (QM_STUDY_PREREG
    definition). A fire truncated at h (forward_returns -> None) or a
    baseline with no observations at h (bmed -> None) is excluded from that
    horizon's pool, never imputed.
    """
    pooled: dict[int, list[float]] = {int(h): [] for h in horizons}
    for frame, fires_iso in name_fires:
        baseline = baseline_stats(frame, horizons)
        for iso in fires_iso:
            fr = forward_returns(frame, iso, horizons)
            for h in horizons:
                h = int(h)
                v = fr[h]
                bmed = baseline["returns"][h]["median"]
                if v is not None and bmed is not None:
                    pooled[h].append(v - bmed)
    return pooled


def pooled_median(values: Sequence[float]) -> float | None:
    """Median of a pooled excess-return list, or None when empty."""
    return float(np.median(values)) if values else None


def sum_tradability(readings: Sequence[Mapping[str, int]]) -> dict[str, int]:
    """Sum per-name tradability tuples into one pooled tuple."""
    return {
        "tradable": sum(int(r["tradable"]) for r in readings),
        "untradable": sum(int(r["untradable"]) for r in readings),
        "no_chain": sum(int(r["no_chain"]) for r in readings),
    }


def tradability_rate(pooled: Mapping[str, int]) -> float | None:
    """tradable / (tradable + untradable); no-chain fires excluded from the
    denominator and disclosed separately, matching qm_study's convention."""
    denom = pooled["tradable"] + pooled["untradable"]
    return (pooled["tradable"] / denom) if denom else None


# --------------------------------------------------------------------------
# Per-name collection (I/O boundary; injectable for tests)
# --------------------------------------------------------------------------


def _collect_one_name(
    symbol: str,
    load_adjusted: Callable[[str, str, str], pd.DataFrame],
    load_raw: Callable[[str, str, str], pd.DataFrame],
    load_chain: Callable[[str, str], Any],
    params: Mapping[str, Any],
    end_iso: str,
) -> dict[str, Any] | None:
    """One name's fires plus tradability per setup, or None on a disclosed
    OHLCV cache gap (skipped, never a crash)."""
    try:
        frame = load_adjusted(symbol, START_ISO, end_iso)
        raw = load_raw(symbol, START_ISO, end_iso)
    except FileNotFoundError:
        print(f"{symbol}: no OHLCV cache (skipped, disclosed)")
        return None

    dte_band = tuple(int(x) for x in params["QM_TRADABILITY_DTE"])
    ntm_band = float(params["QM_NTM_BAND"])
    fires = {
        "breakout": [str(f["t"]) for f in qm_signals.breakout_fires(frame, params)],
        "parabolic": [str(f) for f in qm_signals.parabolic_fires(frame, params)],
    }
    trad = {
        setup: _aggregate_tradability(load_chain, symbol, raw, dates, dte_band, ntm_band)
        for setup, dates in fires.items()
    }
    return {"frame": frame, "fires": fires, "trad": trad}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(
    argv: Sequence[str] | None = None,
    *,
    universe: Sequence[str] | None = None,
    load_adjusted: Callable[[str, str, str], pd.DataFrame] | None = None,
    load_raw: Callable[[str, str, str], pd.DataFrame] | None = None,
    load_chain: Callable[[str, str], Any] | None = None,
    params: Mapping[str, Any] | None = None,
    gate: Callable[[], str | None] | None = None,
) -> int:
    del argv  # no flags -- this reducer takes no arguments

    # GATE FIRST -- same contract as qm_study/qm_watch (spec §7).
    gate_fn = gate if gate is not None else qm_signals.qm_prereg_gate
    reason = gate_fn()
    if reason:
        print(reason)
        return 2

    if params is None:
        params = qm_signals.qm_params()
    if universe is None:
        universe = h7_scope.watch_universe()
    load_adjusted = load_adjusted or _default_load_adjusted
    load_raw = load_raw or _default_load_raw
    load_chain = load_chain or _default_load_chain

    horizons = tuple(int(h) for h in params["QM_HORIZONS"])
    end_iso = _now_ny_iso()

    per_setup_fires: dict[str, list[tuple[pd.DataFrame, Sequence[str]]]] = {
        s: [] for s in SETUPS
    }
    per_setup_trad: dict[str, list[Mapping[str, int]]] = {s: [] for s in SETUPS}

    for symbol in universe:
        collected = _collect_one_name(symbol, load_adjusted, load_raw, load_chain, params, end_iso)
        if collected is None:
            continue
        for setup in SETUPS:
            per_setup_fires[setup].append((collected["frame"], collected["fires"][setup]))
            per_setup_trad[setup].append(collected["trad"][setup])

    for setup in SETUPS:
        fires_total = sum(len(dates) for _frame, dates in per_setup_fires[setup])
        pooled = pool_excess_across_universe(per_setup_fires[setup], horizons)
        trad = sum_tradability(per_setup_trad[setup])
        rate = tradability_rate(trad)

        print(f"\n== {setup} ==")
        print(f"deduped fires: {fires_total}")
        for h in horizons:
            h = int(h)
            vals = pooled[h]
            med = pooled_median(vals)
            if med is None:
                print(f"  +{h}d: no data")
            else:
                print(f"  +{h}d pooled median excess (n={len(vals)}): {med:+.4f}")
        if rate is None:
            print("  tradability: no denom")
        else:
            print(
                f"  tradability: {trad['tradable']} tradable / "
                f"{trad['untradable']} untradable / {trad['no_chain']} no-chain "
                f"-> rate {rate:.1%}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
