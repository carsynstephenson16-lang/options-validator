"""Bounded ThetaData trade-quote and prior-known OI retrieval.

The default client reuses the repository's authenticated remote ThetaClient
factory. Tests inject a fake client and never authenticate or make requests.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Protocol, cast

import pandas as pd

TRADE_QUOTE_ENDPOINT = "option_history_trade_quote"
OPEN_INTEREST_ENDPOINT = "option_history_open_interest"
SOURCE_VERSION = "thetadata-python-1.0.9"


class FlowClient(Protocol):
    """Subset of ThetaClient used by this adapter."""

    def option_history_trade_quote(
        self,
        *,
        symbol: str,
        expiration: str,
        date: date,
        start_time: str,
        end_time: str,
        exclusive: bool,
    ) -> pd.DataFrame: ...

    def option_history_open_interest(
        self,
        *,
        symbol: str,
        expiration: str,
        date: date,
    ) -> pd.DataFrame: ...


@dataclass(frozen=True, slots=True)
class FlowFetch:
    """One symbol-session fetch and its reproducibility metadata."""

    symbol: str
    session: str
    trade_quote: pd.DataFrame
    open_interest: pd.DataFrame
    acquired_at_utc: str
    source_version: str = SOURCE_VERSION

    @property
    def requests(self) -> tuple[str, ...]:
        return (TRADE_QUOTE_ENDPOINT, OPEN_INTEREST_ENDPOINT)


def _validate_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized or any(not (char.isalnum() or char in "._-") for char in normalized):
        raise ValueError(f"invalid flow symbol: {symbol!r}")
    return normalized


def _validate_session(session: str) -> date:
    try:
        return date.fromisoformat(session)
    except ValueError as exc:
        raise ValueError(f"session must be ISO date: {session!r}") from exc


def default_client() -> FlowClient:
    """Return the existing lazily-authenticated remote client.

    Importing this function is network-free. Authentication occurs only when
    a non-dry-run caller explicitly invokes it.
    """
    from data.thetadata_adapter import _client

    return cast(FlowClient, _client())


def fetch_session(
    symbol: str,
    session: str,
    *,
    client: FlowClient | None = None,
    acquired_at_utc: str | None = None,
) -> FlowFetch:
    """Fetch one regular-session trade-quote/OI pair.

    ``exclusive=True`` ensures the matched NBBO timestamp is strictly before
    the trade timestamp. The OI response queried for D is the prior-known OI
    observation available during D; no opening/closing inference is made.
    """
    normalized_symbol = _validate_symbol(symbol)
    session_date = _validate_session(session)
    fetch_client = default_client() if client is None else client
    acquired = acquired_at_utc or datetime.now(timezone.utc).isoformat()
    trade_quote = fetch_client.option_history_trade_quote(
        symbol=normalized_symbol,
        expiration="*",
        date=session_date,
        start_time=time(9, 30).isoformat(),
        end_time=time(16, 0).isoformat(),
        exclusive=True,
    )
    open_interest = fetch_client.option_history_open_interest(
        symbol=normalized_symbol,
        expiration="*",
        date=session_date,
    )
    if not isinstance(trade_quote, pd.DataFrame) or not isinstance(
        open_interest, pd.DataFrame
    ):
        raise TypeError("ThetaData flow endpoints must return pandas DataFrames")
    return FlowFetch(
        symbol=normalized_symbol,
        session=session_date.isoformat(),
        trade_quote=trade_quote.copy(deep=True),
        open_interest=open_interest.copy(deep=True),
        acquired_at_utc=acquired,
    )
