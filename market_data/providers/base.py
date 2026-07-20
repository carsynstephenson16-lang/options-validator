"""Shared adapter helpers; no provider-specific business logic belongs here."""
from __future__ import annotations

import math
import os
from datetime import date, datetime, timezone
from typing import Mapping

from market_data.models import (
    DataQualityStatus,
    DataTiming,
    OptionQuote,
    ProviderHealth,
    compute_midpoint,
)
from market_data.transport import JsonTransport, ProviderError


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def env_value(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def as_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        converted = float(str(value))
    except (TypeError, ValueError):
        return None
    return converted if math.isfinite(converted) else None


def as_int(value: object) -> int | None:
    converted = as_float(value)
    if converted is None or not converted.is_integer():
        return None
    return int(converted)


def as_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def as_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if not math.isfinite(number):
            return None
        # Provider timestamps are commonly milliseconds; infer only by scale.
        divisor = 1.0 if abs(number) < 10_000_000_000 else 1000.0
        parsed = datetime.fromtimestamp(number / divisor, tz=timezone.utc)
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def payload_dict(payload: object, *, provider: str) -> Mapping[str, object]:
    if not isinstance(payload, dict):
        raise ProviderError(f"{provider} returned a non-object JSON payload")
    return payload


def quote_from_fields(
    *,
    provider: str,
    symbol: str,
    underlying_symbol: str,
    option_type: str,
    strike: float,
    expiration: date,
    bid: object = None,
    ask: object = None,
    last_price: object = None,
    volume: object = None,
    open_interest: object = None,
    implied_volatility: object = None,
    delta: object = None,
    gamma: object = None,
    theta: object = None,
    vega: object = None,
    underlying_price: object = None,
    quote_timestamp: object = None,
    timing: DataTiming = DataTiming.UNKNOWN,
    retrieved_at: datetime | None = None,
    unavailable_reasons: Mapping[str, str] | None = None,
) -> OptionQuote:
    values = {
        "bid": as_float(bid),
        "ask": as_float(ask),
        "last_price": as_float(last_price),
        "volume": as_int(volume),
        "open_interest": as_int(open_interest),
        "implied_volatility": as_float(implied_volatility),
        "delta": as_float(delta),
        "gamma": as_float(gamma),
        "theta": as_float(theta),
        "vega": as_float(vega),
        "underlying_price": as_float(underlying_price),
        "quote_timestamp": as_datetime(quote_timestamp),
    }
    reasons = dict(unavailable_reasons or {})
    for field_name, value in values.items():
        if value is None:
            reasons.setdefault(field_name, "provider did not return a usable value")
    midpoint = compute_midpoint(values["bid"], values["ask"])
    if midpoint is None:
        reasons.setdefault("midpoint", "bid and ask are missing, invalid, or crossed")
    quality = DataQualityStatus.OK if not reasons else DataQualityStatus.DEGRADED
    if values["bid"] is not None and values["ask"] is not None and midpoint is None:
        quality = DataQualityStatus.INVALID
    if values["bid"] is None and values["ask"] is None and values["last_price"] is None:
        quality = DataQualityStatus.UNAVAILABLE
    return OptionQuote(
        provider=provider,
        symbol=symbol,
        underlying_symbol=underlying_symbol,
        option_type=option_type,
        strike=float(strike),
        expiration=expiration,
        bid=values["bid"],
        ask=values["ask"],
        last_price=values["last_price"],
        midpoint=midpoint,
        volume=values["volume"],
        open_interest=values["open_interest"],
        implied_volatility=values["implied_volatility"],
        delta=values["delta"],
        gamma=values["gamma"],
        theta=values["theta"],
        vega=values["vega"],
        underlying_price=values["underlying_price"],
        quote_timestamp=values["quote_timestamp"],
        retrieved_at=retrieved_at or utc_now(),
        timing=timing,
        data_quality_status=quality,
        missing_field_reasons=reasons,
    )


class ProviderBase:
    name = "provider"

    def __init__(self, transport: JsonTransport) -> None:
        self.transport = transport

    def missing_credentials(self, *, detail: str) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name,
            connection_status="not_checked",
            authentication_status="missing",
            subscription_status="unknown",
            detail=detail,
        )
