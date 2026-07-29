"""Point-in-time event and implied-volatility context for flow research."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, cast

import numpy as np
import pandas as pd

EVENT_UNKNOWN = "EVENT_CONTEXT_UNKNOWN"
EVENT_NONE = "NO_KNOWN_EVENT_WITHIN_T5"
EVENT_KNOWN = "KNOWN_EVENT_WITHIN_T5"
IV_UNKNOWN = "IV_CONTEXT_UNKNOWN"
IV_READY = "IV_CONTEXT_READY"
RV_UNKNOWN = "RV_CONTEXT_UNKNOWN"
RV_READY = "RV_CONTEXT_READY"

# The analog topology declares a 21-return annualized realized-volatility
# estimate and a trailing 252-observation tercile reference distribution.
RV_RETURN_WINDOW = 21
RV_TERCILE_HISTORY = 252


@dataclass(frozen=True, slots=True)
class EventContext:
    state: str
    event_types: tuple[str, ...]
    event_ids: tuple[str, ...]
    as_of: str


@dataclass(frozen=True, slots=True)
class IVContext:
    state: str
    source_session: str | None
    atm30_iv: float | None
    iv_percentile_252: float | None
    iv_change_1d: float | None
    term_slope: float | None
    put_skew: float | None
    skew_z: float | None
    observations: int


@dataclass(frozen=True, slots=True)
class RealizedVolatilityContext:
    """Strictly-prior realized-volatility regime inputs for analog matching."""

    state: str
    source_session: str | None
    realized_volatility_21: float | None
    rv_tercile: int | None
    observations: int


def event_context_for_session(
    *,
    symbol: str,
    session: str,
    events: pd.DataFrame,
    trading_sessions: Iterable[str],
    coverage_complete: bool,
    horizon: int = 5,
    cutoff_time: str = "16:00:00",
) -> EventContext:
    """Classify only events published by the historical query cutoff."""
    if not coverage_complete:
        return EventContext(EVENT_UNKNOWN, (), (), session)
    required = {
        "symbol",
        "event_id",
        "event_type",
        "published_at",
        "effective_at",
    }
    missing = sorted(required - set(events.columns))
    if missing:
        raise ValueError(f"event calendar missing columns: {missing}")
    calendar = sorted({str(value) for value in trading_sessions})
    if session not in calendar:
        raise ValueError(f"query session is absent from trading calendar: {session}")
    index = calendar.index(session)
    forward = {session, *calendar[index + 1 : index + horizon + 1]}
    query_cutoff = pd.Timestamp(
        f"{session}T{cutoff_time}",
        tz="America/New_York",
    ).tz_convert("UTC")
    published = pd.to_datetime(events["published_at"], errors="coerce", utc=True)
    effective = pd.to_datetime(events["effective_at"], errors="coerce", utc=True)
    malformed = published.isna() | effective.isna()
    if bool(malformed.any()):
        raise ValueError("event calendar contains malformed timestamps")
    effective_sessions = effective.dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")
    known = events.loc[
        events["symbol"].astype(str).str.upper().eq(symbol.upper())
        & published.le(query_cutoff)
        & effective.gt(query_cutoff)
        & effective_sessions.isin(forward)
    ].sort_values(["effective_at", "event_id"])
    if known.empty:
        return EventContext(EVENT_NONE, (), (), session)
    return EventContext(
        EVENT_KNOWN,
        tuple(known["event_type"].astype(str)),
        tuple(known["event_id"].astype(str)),
        session,
    )


def _valid_chain(chain: pd.DataFrame) -> pd.DataFrame:
    required = {"expiration", "dte", "right", "delta", "iv", "bid", "ask"}
    missing = sorted(required - set(chain.columns))
    if missing:
        raise ValueError(f"IV chain missing columns: {missing}")
    out = chain.copy()
    for column in ("dte", "delta", "iv", "bid", "ask"):
        out[column] = pd.to_numeric(out[column], errors="coerce")
    return out.loc[
        out["dte"].gt(0)
        & out["iv"].gt(0)
        & out["iv"].le(5)
        & out["ask"].ge(out["bid"])
        & out["bid"].ge(0)
        & out["delta"].abs().le(1)
    ].copy()


def _per_expiry_iv(
    chain: pd.DataFrame,
    *,
    delta_target: float,
    right: str | None,
    minimum_contracts: int,
) -> pd.DataFrame:
    rows: list[dict[str, float]] = []
    for dte, group in chain.groupby("dte", sort=True):
        eligible = group if right is None else group.loc[group["right"].eq(right)]
        if len(eligible) < minimum_contracts:
            continue
        selected = eligible.loc[(eligible["delta"] - delta_target).abs().idxmin()]
        rows.append(
            {
                "dte": float(cast(Any, dte)),
                "iv": float(cast(Any, selected["iv"])),
            }
        )
    return pd.DataFrame(rows)


def _interpolate_total_variance(points: pd.DataFrame, target_dte: int) -> float:
    if points.empty:
        return np.nan
    lower = points.loc[points["dte"].le(target_dte)].tail(1)
    upper = points.loc[points["dte"].ge(target_dte)].head(1)
    if lower.empty or upper.empty:
        return np.nan
    low_dte, low_iv = map(float, lower.iloc[0][["dte", "iv"]])
    high_dte, high_iv = map(float, upper.iloc[0][["dte", "iv"]])
    if low_dte == high_dte:
        return low_iv
    low_t, high_t, target_t = low_dte / 365.0, high_dte / 365.0, target_dte / 365.0
    low_var, high_var = low_iv**2 * low_t, high_iv**2 * high_t
    weight = (target_t - low_t) / (high_t - low_t)
    target_var = low_var + weight * (high_var - low_var)
    return float(np.sqrt(target_var / target_t)) if target_var > 0 else np.nan


def build_daily_iv_snapshot(
    chain: pd.DataFrame,
    *,
    session: str,
    minimum_contracts_per_expiry: int = 2,
) -> dict[str, object]:
    """Build constant-maturity ATM/put-skew fields without extrapolation."""
    valid = _valid_chain(chain)
    calls = _per_expiry_iv(
        valid,
        delta_target=0.5,
        right="C",
        minimum_contracts=minimum_contracts_per_expiry,
    )
    puts = _per_expiry_iv(
        valid,
        delta_target=-0.25,
        right="P",
        minimum_contracts=minimum_contracts_per_expiry,
    )
    atm30 = _interpolate_total_variance(calls, 30)
    atm60 = _interpolate_total_variance(calls, 60)
    put25 = _interpolate_total_variance(puts, 30)
    return {
        "session": session,
        "atm30_iv": atm30,
        "atm60_iv": atm60,
        "put25_iv": put25,
        "chain_rows": len(chain),
        "valid_chain_rows": len(valid),
    }


def iv_context_for_session(
    *,
    session: str,
    history: pd.DataFrame,
    minimum_history: int = 252,
) -> IVContext:
    """Use only completed sessions strictly before the query session.

    ``skew_z`` is the latest known 25-delta put skew standardized against the
    preceding observations in the same ``minimum_history`` IV window.  The
    latest observation is never included in its own mean or sample standard
    deviation.  A constant or too-short skew history is unknown rather than
    assigned a default z-score.
    """
    required = {"session", "atm30_iv", "atm60_iv", "put25_iv"}
    missing = sorted(required - set(history.columns))
    if missing:
        raise ValueError(f"IV history missing columns: {missing}")
    if minimum_history < 3:
        raise ValueError("minimum_history must be at least 3")
    ordered = history.copy()
    ordered["session"] = pd.to_datetime(ordered["session"], errors="coerce").dt.strftime(
        "%Y-%m-%d"
    )
    for column in ("atm30_iv", "atm60_iv", "put25_iv"):
        ordered[column] = pd.to_numeric(ordered[column], errors="coerce")
    prior = ordered.loc[
        ordered["session"].lt(session)
        & ordered["atm30_iv"].gt(0)
        & ordered["atm60_iv"].gt(0)
        & ordered["put25_iv"].gt(0)
    ].sort_values("session")
    if len(prior) < minimum_history:
        return IVContext(IV_UNKNOWN, None, None, None, None, None, None, None, len(prior))
    window = prior.tail(minimum_history)
    latest = window.iloc[-1]
    atm30 = float(latest["atm30_iv"])
    previous = float(window.iloc[-2]["atm30_iv"]) if len(window) >= 2 else np.nan
    percentile = float((window["atm30_iv"].iloc[:-1] <= atm30).mean())
    put_skew = window["put25_iv"].sub(window["atm30_iv"])
    skew_reference = put_skew.iloc[:-1].to_numpy(dtype=float)
    skew_scale = float(np.std(skew_reference, ddof=1))
    if not np.isfinite(skew_scale) or skew_scale <= 0:
        return IVContext(IV_UNKNOWN, None, None, None, None, None, None, None, len(window))
    skew_z = float((float(put_skew.iloc[-1]) - float(np.mean(skew_reference))) / skew_scale)
    return IVContext(
        IV_READY,
        str(latest["session"]),
        atm30,
        percentile,
        atm30 - previous if np.isfinite(previous) else None,
        float(latest["atm60_iv"] - atm30),
        float(put_skew.iloc[-1]),
        skew_z,
        len(window),
    )


def realized_volatility_context_for_session(
    *,
    session: str,
    history: pd.DataFrame,
    return_window: int = RV_RETURN_WINDOW,
    tercile_history: int = RV_TERCILE_HISTORY,
) -> RealizedVolatilityContext:
    """Return a prior-only annualized-RV tercile for one query session.

    The estimator is the sample standard deviation (``ddof=1``) of the most
    recent ``return_window`` daily log returns, annualized by ``sqrt(252)``.
    Its tercile reference contains the previous ``tercile_history`` values of
    that estimator and excludes the query value itself.  Therefore every close
    used by either the value or its cut points is strictly before ``session``.
    """
    required = {"session", "close"}
    missing = sorted(required - set(history.columns))
    if missing:
        raise ValueError(f"close history missing columns: {missing}")
    if return_window < 2:
        raise ValueError("return_window must be at least 2")
    if tercile_history < 1:
        raise ValueError("tercile_history must be positive")
    ordered = history.loc[:, ["session", "close"]].copy()
    ordered["session"] = pd.to_datetime(ordered["session"], errors="coerce").dt.strftime(
        "%Y-%m-%d"
    )
    ordered["close"] = pd.to_numeric(ordered["close"], errors="coerce")
    prior = ordered.loc[
        ordered["session"].lt(session) & ordered["close"].gt(0)
    ].sort_values("session")
    if prior["session"].duplicated().any():
        raise ValueError("close history contains duplicate sessions")

    required_closes = return_window + tercile_history + 2
    available_reference = max(len(prior) - return_window - 1, 0)
    if len(prior) < required_closes:
        return RealizedVolatilityContext(
            RV_UNKNOWN,
            None,
            None,
            None,
            min(available_reference, tercile_history),
        )

    log_returns = np.diff(np.log(prior["close"].to_numpy(dtype=float)))
    current_rv = float(np.std(log_returns[-return_window:], ddof=1) * np.sqrt(252.0))
    previous_rvs = np.asarray(
        [
            np.std(log_returns[end - return_window : end], ddof=1) * np.sqrt(252.0)
            for end in range(return_window, len(prior) - 1)
        ],
        dtype=float,
    )
    reference = previous_rvs[-tercile_history:]
    lower, upper = np.quantile(reference, (1.0 / 3.0, 2.0 / 3.0))
    tercile = 1 if current_rv <= lower else (2 if current_rv <= upper else 3)
    return RealizedVolatilityContext(
        RV_READY,
        str(prior.iloc[-1]["session"]),
        current_rv,
        tercile,
        len(reference),
    )


def context_dict(
    value: EventContext | IVContext | RealizedVolatilityContext,
) -> dict[str, object]:
    return asdict(value)
