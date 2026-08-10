"""Display-only experiment for role-based option-spread stability.

Each session independently resolves the near-tenor, 0.50-delta put. The
reference can therefore change strikes or expirations across sessions; it is
not a fixed-contract time series. Earnings week means the Monday-Friday week
containing the operative assertion date in ``gating_v3.csv``.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

import config
from options_researcher.chains import atm_row, load_range, nearest_monthly

# LLM-proposed 2026-08-09; survey rank-12 convention; display-only; not owner-ratified.
EXP_SPREAD_BASELINE = getattr(config, "EXP_SPREAD_BASELINE", 20)
# LLM-proposed 2026-08-09; survey rank-12 convention; display-only; not owner-ratified.
EXP_SPREAD_MIN_BASELINE_OBS = getattr(config, "EXP_SPREAD_MIN_BASELINE_OBS", 10)
# LLM-proposed 2026-08-09; repo bounded-read convention; display-only; not owner-ratified.
EXP_SPREAD_LOOKBACK_SESSIONS = getattr(config, "EXP_SPREAD_LOOKBACK_SESSIONS", 25)
# LLM-proposed 2026-08-09; survey display label; display-only; not owner-ratified.
EXP_SPREAD_ELEVATED = getattr(config, "EXP_SPREAD_ELEVATED", 2.0)
# LLM-proposed 2026-08-09; composite near-tenor convention; display-only; not owner-ratified.
EXP_SPREAD_TENOR_DTE = getattr(config, "EXP_SPREAD_TENOR_DTE", (15, 60))
# LLM-proposed 2026-08-09; composite near-tenor convention; display-only; not owner-ratified.
EXP_SPREAD_TARGET_DELTA = getattr(config, "EXP_SPREAD_TARGET_DELTA", 0.50)

EXPERIMENT_ID = "EXP-SPREAD"
GATING_V3_PATH = Path("data/earnings/gating_v3.csv")
CAVEAT = (
    "Role-based reference contracts can change strikes across sessions; "
    "earnings week is the calendar Monday-Friday containing the asserted "
    "event. Descriptive at the frozen chain close; not a forecast."
)


def _blocked(reason: str, *, asof: str, max_asof: str | None = None) -> dict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "state": "DATA_BLOCKED",
        "data_blocked": True,
        "reason": reason,
        "asof": asof,
        "max_asof": max_asof or asof,
        "rel_spread_today": None,
        "baseline_median": None,
        "ratio": None,
        "baseline_sessions_used": 0,
        "today_is_earnings_week": False,
        "caveat": CAVEAT,
    }


def _week_sessions(day_iso: str) -> set[str]:
    event_day = date.fromisoformat(day_iso)
    monday = event_day - timedelta(days=event_day.weekday())
    return {(monday + timedelta(days=offset)).isoformat() for offset in range(5)}


def load_earnings_weeks(*, asof: str, path: str | Path = GATING_V3_PATH) -> dict[str, set[str]]:
    """Read causally-known, operative quarterly-earnings weeks by symbol.

    Business updates are ignored. Retractions remove the assertion named in
    ``supersedes``. An occurred assertion uses ``occurred_date``; all other
    statuses use ``expected_date``.
    """
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    required = {
        "record_id",
        "symbol",
        "record_type",
        "event_class",
        "status",
        "expected_date",
        "occurred_date",
        "known_as_of_utc",
        "supersedes",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"gating_v3 missing columns: {sorted(missing)}")

    known = frame[frame["known_as_of_utc"].str.slice(0, 10) <= asof].copy()
    retracted_ids = set(known.loc[known["record_type"] == "retraction", "supersedes"]) - {""}
    assertions = known[
        (known["record_type"] == "assertion")
        & (known["event_class"] == "actual_quarterly_earnings")
        & (~known["record_id"].isin(retracted_ids))
    ]

    result: dict[str, set[str]] = {}
    for row in assertions.itertuples(index=False):
        operative = row.occurred_date if row.status == "occurred" else row.expected_date
        if not operative:
            continue
        result.setdefault(str(row.symbol), set()).update(_week_sessions(operative))
    return result


def _reference_rel_spread(chain: pd.DataFrame, session: str) -> float | None:
    session_day = date.fromisoformat(session)
    expiration = nearest_monthly(
        chain,
        session_day,
        min_dte=EXP_SPREAD_TENOR_DTE[0],
        max_dte=EXP_SPREAD_TENOR_DTE[1],
    )
    if expiration is None:
        return None
    row = atm_row(
        chain,
        expiration,
        right="P",
        target_delta=EXP_SPREAD_TARGET_DELTA,
    )
    if row is None:
        return None
    bid = float(row["bid"])
    ask = float(row["ask"])
    mid = (bid + ask) / 2.0
    if not np.isfinite([bid, ask, mid]).all() or bid <= 0 or ask < bid or mid <= 0:
        return None
    return (ask - bid) / mid


def exp_spread_stability(
    chain_by_session: dict[str, pd.DataFrame],
    *,
    asof: str,
    earnings_weeks: set[str],
) -> dict:
    """Compare the latest role-based relative spread with its prior baseline."""
    sessions = sorted(day for day in chain_by_session if day <= asof)
    if not sessions:
        return _blocked("no cached chain sessions", asof=asof)

    max_asof = sessions[-1]
    current = _reference_rel_spread(chain_by_session[max_asof], max_asof)
    if current is None:
        return _blocked("no valid reference row", asof=asof, max_asof=max_asof)

    candidate_sessions = sessions[:-1][-EXP_SPREAD_BASELINE:]
    baseline = [
        spread
        for session in candidate_sessions
        if session not in earnings_weeks
        for spread in [_reference_rel_spread(chain_by_session[session], session)]
        if spread is not None
    ]
    if len(baseline) < EXP_SPREAD_MIN_BASELINE_OBS:
        return _blocked(
            f"fewer than {EXP_SPREAD_MIN_BASELINE_OBS} usable baseline sessions",
            asof=asof,
            max_asof=max_asof,
        )
    median = float(np.median(baseline))
    if not np.isfinite(median) or median <= 0:
        return _blocked("degenerate baseline median", asof=asof, max_asof=max_asof)
    ratio = current / median
    return {
        "experiment_id": EXPERIMENT_ID,
        "state": "ELEVATED" if ratio >= EXP_SPREAD_ELEVATED else "OK",
        "data_blocked": False,
        "reason": None,
        "asof": asof,
        "max_asof": max_asof,
        "rel_spread_today": float(current),
        "baseline_median": median,
        "ratio": float(ratio),
        "baseline_sessions_used": len(baseline),
        "today_is_earnings_week": max_asof in earnings_weeks,
        "caveat": CAVEAT,
    }


def _cached_sessions(symbol: str, asof: str) -> list[str]:
    cache_dir = Path(os.environ.get("OPTIONS_CACHE_DIR", ".cache/chains"))
    prefix = f"{symbol}_"
    sessions = sorted(
        path.stem[len(prefix) :]
        for path in cache_dir.glob(f"{symbol}_????-??-??.parquet")
        if path.stem[len(prefix) :] <= asof
    )
    return sessions[-EXP_SPREAD_LOOKBACK_SESSIONS:]


def _load_selected_sessions(symbol: str, sessions: Iterable[str]) -> dict[str, pd.DataFrame]:
    chains: dict[str, pd.DataFrame] = {}
    for session in sessions:
        loaded = load_range(symbol, session, session, allow_oos=True)
        if session in loaded:
            chains[session] = loaded[session]
    return chains


def build_exp_spread_board(symbols: list[str], *, asof: str) -> list[dict]:
    """Build fail-visible cards using at most 25 cached chain files per symbol."""
    try:
        weeks_by_symbol = load_earnings_weeks(asof=asof)
    except Exception as exc:
        reason = f"earnings gating failed ({exc.__class__.__name__}: {exc})"
        return [{"symbol": symbol, **_blocked(reason, asof=asof)} for symbol in symbols]

    cards: list[dict] = []
    for symbol in symbols:
        try:
            sessions = _cached_sessions(symbol, asof)
            chains = _load_selected_sessions(symbol, sessions)
            card = exp_spread_stability(
                chains,
                asof=asof,
                earnings_weeks=weeks_by_symbol.get(symbol, set()),
            )
            cards.append({"symbol": symbol, **card})
        except Exception as exc:
            cards.append(
                {
                    "symbol": symbol,
                    **_blocked(
                        f"chain load failed ({exc.__class__.__name__}: {exc})",
                        asof=asof,
                    ),
                }
            )
    return cards
