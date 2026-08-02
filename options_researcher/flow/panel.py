"""Canonical, point-in-time assembly of options-flow analog panels.

This module is the only in-repository path from daily flow features and the
event, IV, and close histories to the regime columns consumed by
``match_historical_analogs``.  It deliberately does not infer missing context:
insufficient IV/skew/RV history or ambiguous event context yields an explicit
unknown regime state that the analog engine abstains on.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from options_researcher.flow.context import (
    EVENT_KNOWN,
    EVENT_NONE,
    EVENT_UNKNOWN,
    IV_READY,
    RV_READY,
    EventContext,
    event_context_for_session,
    iv_context_for_session,
    realized_volatility_context_for_session,
)

ANALOG_REGIME_READY = "ANALOG_REGIME_READY"
ANALOG_REGIME_UNKNOWN = "ANALOG_REGIME_UNKNOWN"
EVENT_TYPE_NONE = "NONE"
EVENT_TYPE_UNKNOWN = "EVENT_TYPE_UNKNOWN"
EVENT_TYPE_SINGLE_PREFIX = "SINGLE:"
EVENT_TYPE_MULTI_PREFIX = "MULTI:"


def collapse_event_type(context: EventContext) -> str:
    """Return the canonical scalar event signature used by the analog gate.

    No known event maps to ``NONE``.  A single type maps to
    ``SINGLE:<TYPE>``.  Multiple distinct types map to the sorted set as
    ``MULTI:<TYPE>|<TYPE>``; duplicate events of the same type remain one
    regime because the gate is by type composition, not event count.  A
    contradictory or malformed event context is unknown, never ``NONE``.
    """
    if context.state == EVENT_UNKNOWN:
        return EVENT_TYPE_UNKNOWN
    types = tuple(sorted({str(value).strip().upper() for value in context.event_types}))
    if any(not value or "|" in value for value in types):
        return EVENT_TYPE_UNKNOWN
    if context.state == EVENT_NONE:
        return EVENT_TYPE_NONE if not types else EVENT_TYPE_UNKNOWN
    if context.state != EVENT_KNOWN or not types:
        return EVENT_TYPE_UNKNOWN
    if len(types) == 1:
        return f"{EVENT_TYPE_SINGLE_PREFIX}{types[0]}"
    return f"{EVENT_TYPE_MULTI_PREFIX}{'|'.join(types)}"


def _identity_frame(frame: pd.DataFrame, *, name: str, required: set[str]) -> pd.DataFrame:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{name} missing columns: {missing}")
    out = frame.copy()
    out["symbol"] = out["symbol"].astype(str).str.upper()
    out["session"] = pd.to_datetime(out["session"], errors="coerce").dt.strftime("%Y-%m-%d")
    if bool(out[["symbol", "session"]].isna().to_numpy().any()) or bool(out["symbol"].eq("").any()):
        raise ValueError(f"{name} contains malformed identity fields")
    if out.duplicated(["symbol", "session"]).any():
        raise ValueError(f"{name} contains duplicate symbol/session rows")
    return out


def _coverage_frame(
    flow: pd.DataFrame,
    coverage_complete: bool | pd.DataFrame,
) -> pd.DataFrame:
    if isinstance(coverage_complete, bool):
        return pd.DataFrame(
            {
                "symbol": flow["symbol"].to_numpy(),
                "session": flow["session"].to_numpy(),
                "coverage_complete": coverage_complete,
            }
        )
    coverage = _identity_frame(
        coverage_complete,
        name="event coverage",
        required={"symbol", "session", "coverage_complete"},
    )
    merged = flow.loc[:, ["symbol", "session"]].merge(
        coverage.loc[:, ["symbol", "session", "coverage_complete"]],
        on=["symbol", "session"],
        how="left",
        validate="one_to_one",
    )
    if bool(merged["coverage_complete"].isna().any()):
        raise ValueError("event coverage is missing flow sessions")
    merged["coverage_complete"] = merged["coverage_complete"].astype(bool)
    return merged


def assemble_analog_panel(
    flow_features: pd.DataFrame,
    *,
    data_quality: pd.DataFrame,
    iv_history: pd.DataFrame,
    close_history: pd.DataFrame,
    events: pd.DataFrame,
    trading_sessions: Iterable[str],
    event_coverage_complete: bool | pd.DataFrame,
    iv_history_window: int = 252,
    rv_return_window: int = 21,
    rv_tercile_history: int = 252,
) -> pd.DataFrame:
    """Assemble all mandatory analog regime fields without same/future-session data.

    ``flow_features`` is the daily output of ``build_flow_features`` (or its
    persisted equivalent).  ``data_quality`` is an explicit per-session audit
    output with ``symbol``, ``session``, and ``data_quality``; it is required
    rather than defaulted to PASS.  The IV and close histories are sliced by
    symbol and each context function only consumes observations strictly before
    the candidate flow session.
    """
    flow = _identity_frame(flow_features, name="flow features", required={"symbol", "session"})
    quality = _identity_frame(
        data_quality,
        name="data quality",
        required={"symbol", "session", "data_quality"},
    )
    panel = flow.merge(
        quality.loc[:, ["symbol", "session", "data_quality"]],
        on=["symbol", "session"],
        how="left",
        validate="one_to_one",
    )
    if bool(panel["data_quality"].isna().any()):
        raise ValueError("data quality is missing flow sessions")
    iv = _identity_frame(
        iv_history,
        name="IV history",
        required={"symbol", "session", "atm30_iv", "atm60_iv", "put25_iv"},
    )
    closes = _identity_frame(
        close_history,
        name="close history",
        required={"symbol", "session", "close"},
    )
    coverage = _coverage_frame(panel, event_coverage_complete)
    calendar = tuple(sorted({str(value) for value in trading_sessions}))
    if not calendar:
        raise ValueError("trading_sessions must not be empty")
    absent = sorted(set(panel["session"]) - set(calendar))
    if absent:
        raise ValueError(f"trading_sessions missing flow sessions: {absent[:3]}")

    contexts: list[dict[str, object]] = []
    coverage_by_identity = coverage.set_index(["symbol", "session"])["coverage_complete"]
    for _, row in panel.iterrows():
        symbol = str(row["symbol"])
        session = str(row["session"])
        event_context = event_context_for_session(
            symbol=symbol,
            session=session,
            events=events,
            trading_sessions=calendar,
            coverage_complete=bool(coverage_by_identity.loc[(symbol, session)]),
        )
        iv_context = iv_context_for_session(
            session=session,
            history=iv.loc[iv["symbol"].eq(symbol)],
            minimum_history=iv_history_window,
        )
        rv_context = realized_volatility_context_for_session(
            session=session,
            history=closes.loc[closes["symbol"].eq(symbol)],
            return_window=rv_return_window,
            tercile_history=rv_tercile_history,
        )
        event_type = collapse_event_type(event_context)
        ready = (
            event_type != EVENT_TYPE_UNKNOWN
            and iv_context.state == IV_READY
            and rv_context.state == RV_READY
        )
        contexts.append(
            {
                "event_state": event_context.state,
                "event_type": event_type,
                "iv_state": iv_context.state,
                "iv_percentile_252": iv_context.iv_percentile_252,
                "term_slope": iv_context.term_slope,
                "put_skew": iv_context.put_skew,
                "skew_z": iv_context.skew_z,
                "realized_volatility_21": rv_context.realized_volatility_21,
                "rv_tercile": rv_context.rv_tercile,
                "rv_observations": rv_context.observations,
                "analog_regime_state": (ANALOG_REGIME_READY if ready else ANALOG_REGIME_UNKNOWN),
            }
        )
    return pd.concat([panel.reset_index(drop=True), pd.DataFrame(contexts)], axis=1)
