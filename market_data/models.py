"""Provider-neutral market-data models and strict option-symbol helpers."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Mapping


class DataTiming(StrEnum):
    DELAYED = "delayed"
    REAL_TIME = "real_time"
    UNKNOWN = "unknown"


class DataQualityStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"


class ValidationStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ProviderHealth:
    """A non-secret provider readiness result."""

    provider: str
    connection_status: str
    authentication_status: str
    subscription_status: str
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    detail: str | None = None


@dataclass(frozen=True)
class ProviderResponse:
    """Raw provider payload with explicit provenance and retrieval time."""

    provider: str
    endpoint: str
    payload: Mapping[str, object]
    retrieved_at: datetime
    timing: DataTiming = DataTiming.UNKNOWN


@dataclass(frozen=True)
class OptionContract:
    """The identity portion of a listed option contract."""

    symbol: str
    underlying_symbol: str
    option_type: str
    strike: float
    expiration: date


@dataclass(frozen=True)
class OptionQuote:
    """Normalized option quote; absent vendor fields remain ``None``."""

    provider: str
    symbol: str
    underlying_symbol: str
    option_type: str
    strike: float
    expiration: date
    bid: float | None = None
    ask: float | None = None
    last_price: float | None = None
    midpoint: float | None = None
    volume: int | None = None
    open_interest: int | None = None
    implied_volatility: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    underlying_price: float | None = None
    quote_timestamp: datetime | None = None
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    timing: DataTiming = DataTiming.UNKNOWN
    data_quality_status: DataQualityStatus = DataQualityStatus.UNAVAILABLE
    missing_field_reasons: Mapping[str, str] = field(default_factory=dict)


_OCC_RE = re.compile(
    r"^(?:O:)?(?P<root>[A-Z0-9.]{1,6})(?P<date>\d{6})(?P<right>[CP])(?P<strike>\d{8})$"
)


def _finite_nonnegative(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        return None
    return number


def compute_midpoint(bid: object, ask: object) -> float | None:
    """Return a midpoint only for a finite, non-crossed quote.

    Missing or invalid premium fields stay missing; they are never represented
    as a fabricated zero.
    """

    bid_value = _finite_nonnegative(bid)
    ask_value = _finite_nonnegative(ask)
    if bid_value is None or ask_value is None or bid_value > ask_value:
        return None
    return (bid_value + ask_value) / 2.0


def parse_option_symbol(symbol: str) -> OptionContract:
    """Parse the OCC/Massive symbol form ``O:AAPL240119C00150000``."""

    if not isinstance(symbol, str):
        raise ValueError("option symbol must be a string")
    match = _OCC_RE.fullmatch(symbol.strip().upper())
    if match is None:
        raise ValueError(f"invalid OCC option symbol: {symbol!r}")
    date_text = match.group("date")
    expiration = date(2000 + int(date_text[:2]), int(date_text[2:4]), int(date_text[4:]))
    right = match.group("right")
    return OptionContract(
        symbol=normalize_option_symbol(
            match.group("root"), expiration, right, int(match.group("strike")) / 1000.0
        ),
        underlying_symbol=match.group("root"),
        option_type="call" if right == "C" else "put",
        strike=int(match.group("strike")) / 1000.0,
        expiration=expiration,
    )


def normalize_option_symbol(
    underlying_symbol: str, expiration: date, right: str, strike: float
) -> str:
    """Build the canonical Massive/OCC symbol without rounding surprises."""

    root = str(underlying_symbol).strip().upper()
    if not re.fullmatch(r"[A-Z0-9.]{1,6}", root):
        raise ValueError(f"invalid underlying symbol: {underlying_symbol!r}")
    if not isinstance(expiration, date):
        raise ValueError("expiration must be a date")
    normalized_right = str(right).strip().upper()
    if normalized_right not in {"C", "P"}:
        raise ValueError("option right must be C or P")
    strike_value = _finite_nonnegative(strike)
    if strike_value is None or strike_value <= 0 or strike_value > 9_999_999.999:
        raise ValueError("strike must be a finite positive value")
    scaled = round(strike_value * 1000)
    if not math.isclose(scaled / 1000.0, strike_value, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("strike must be representable to three decimal places")
    return f"O:{root}{expiration:%y%m%d}{normalized_right}{scaled:08d}"


def contract_key(quote: OptionQuote) -> tuple[str, date, str, float]:
    """Stable key used for duplicate and cross-provider checks."""

    return (
        quote.underlying_symbol.upper(),
        quote.expiration,
        quote.option_type.lower(),
        float(quote.strike),
    )
