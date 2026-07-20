"""Fail-closed cross-provider option-data validation results."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from itertools import groupby
from typing import Iterable, Sequence

from market_data.models import OptionQuote, ValidationStatus, contract_key, parse_option_symbol


@dataclass(frozen=True)
class ValidationResult:
    rule_name: str
    status: ValidationStatus
    severity: str
    explanation: str
    source: str
    data_timestamp: datetime | None
    recommended_next_action: str


def _result(
    quote: OptionQuote,
    rule_name: str,
    status: ValidationStatus,
    severity: str,
    explanation: str,
    action: str,
) -> ValidationResult:
    return ValidationResult(
        rule_name=rule_name,
        status=status,
        severity=severity,
        explanation=explanation,
        source=quote.provider,
        data_timestamp=quote.quote_timestamp,
        recommended_next_action=action,
    )


def _availability(
    quote: OptionQuote, rule: str, field: str, reason: str | None = None
) -> ValidationResult:
    return _result(
        quote,
        rule,
        ValidationStatus.UNAVAILABLE,
        "warning",
        reason or quote.missing_field_reasons.get(field, f"{field} is unavailable"),
        f"obtain {field} from an entitled provider before using this contract",
    )


def _finite(value: float | None) -> bool:
    return value is not None and math.isfinite(float(value))


def validate_quote(
    quote: OptionQuote,
    *,
    as_of: date | None = None,
    now: datetime | None = None,
    max_stale_seconds: float = 900.0,
    max_spread_fraction: float = 0.25,
    minimum_open_interest: int = 1,
    minimum_volume: int = 1,
    earnings_dates: Iterable[date] | None = None,
    dividend_dates: Iterable[date] | None = None,
    event_window_days: int = 14,
    provider_plan: str | None = None,
) -> list[ValidationResult]:
    """Evaluate one normalized quote without converting unavailable data to zero."""

    valuation_date = as_of or (now or datetime.now(timezone.utc)).date()
    current_time = now or datetime.now(timezone.utc)
    earnings_list = list(earnings_dates) if earnings_dates is not None else None
    dividend_list = list(dividend_dates) if dividend_dates is not None else None
    results: list[ValidationResult] = []

    try:
        parsed = parse_option_symbol(quote.symbol)
    except ValueError as exc:
        results.append(
            _result(
                quote, "invalid_option_symbol", ValidationStatus.FAIL, "error", str(exc),
                "discard the row and request a canonical OCC symbol",
            )
        )
    else:
        results.append(
            _result(
                quote, "invalid_option_symbol", ValidationStatus.PASS, "info",
                f"canonical symbol parses as {parsed.option_type} {parsed.strike:g}",
                "continue to the remaining quality checks",
            )
        )

    if quote.bid is None or quote.ask is None:
        results.append(_availability(quote, "bid_greater_than_ask", "bid/ask"))
        results.append(_availability(quote, "zero_or_missing_spread", "bid/ask"))
        results.append(_availability(quote, "excessive_bid_ask_spread", "bid/ask"))
    else:
        crossed = quote.bid > quote.ask
        results.append(
            _result(
                quote,
                "bid_greater_than_ask",
                ValidationStatus.FAIL if crossed else ValidationStatus.PASS,
                "error" if crossed else "info",
                f"bid={quote.bid:g}, ask={quote.ask:g}",
                "discard the crossed quote and fetch a synchronized NBBO" if crossed else "continue",
            )
        )
        spread = quote.ask - quote.bid
        results.append(
            _result(
                quote,
                "zero_or_missing_spread",
                ValidationStatus.FAIL if spread <= 0 else ValidationStatus.PASS,
                "error" if spread <= 0 else "info",
                f"spread={spread:g}",
                "discard zero-width or invalid quote" if spread <= 0 else "continue",
            )
        )
        mid = quote.midpoint
        excessive = mid is not None and mid > 0 and spread / mid > max_spread_fraction
        results.append(
            _result(
                quote,
                "excessive_bid_ask_spread",
                ValidationStatus.FAIL if excessive else ValidationStatus.PASS,
                "warning" if excessive else "info",
                f"spread/mid={spread / mid:.3f}" if mid else "midpoint is unavailable",
                "do not treat this contract as liquid" if excessive else "continue",
            )
        )

    negative_fields = [
        field for field in ("bid", "ask", "last_price")
        if getattr(quote, field) is not None and getattr(quote, field) < 0
    ]
    results.append(
        _result(
            quote,
            "negative_option_prices",
            ValidationStatus.FAIL if negative_fields else ValidationStatus.PASS,
            "error" if negative_fields else "info",
            f"negative fields: {negative_fields}" if negative_fields else "all supplied option prices are non-negative",
            "discard the provider row" if negative_fields else "continue",
        )
    )

    if quote.quote_timestamp is None:
        results.append(_availability(quote, "stale_quote", "quote_timestamp"))
    else:
        timestamp = quote.quote_timestamp
        if timestamp.tzinfo is None:
            stale = True
            age = "timezone-naive"
        else:
            age_seconds = (current_time - timestamp.astimezone(timezone.utc)).total_seconds()
            stale = age_seconds > max_stale_seconds or age_seconds < -60
            age = f"age_seconds={age_seconds:.1f}"
        results.append(
            _result(
                quote,
                "stale_quote",
                ValidationStatus.FAIL if stale else ValidationStatus.PASS,
                "warning" if stale else "info",
                str(age),
                "refresh the quote; do not mix it with current data" if stale else "continue",
            )
        )

    results.append(
        _result(
            quote,
            "missing_underlying_price",
            ValidationStatus.UNAVAILABLE if quote.underlying_price is None else ValidationStatus.PASS,
            "warning" if quote.underlying_price is None else "info",
            quote.missing_field_reasons.get("underlying_price", "underlying price supplied"),
            "obtain a synchronized underlying quote before model or parity checks" if quote.underlying_price is None else "continue",
        )
    )

    expiration_valid = isinstance(quote.expiration, date)
    results.append(
        _result(
            quote,
            "invalid_expiration_date",
            ValidationStatus.PASS if expiration_valid else ValidationStatus.FAIL,
            "info" if expiration_valid else "error",
            str(quote.expiration),
            "discard the row and repair the provider date mapping" if not expiration_valid else "continue",
        )
    )
    expired = expiration_valid and quote.expiration <= valuation_date
    results.append(
        _result(
            quote,
            "expired_contract",
            ValidationStatus.FAIL if expired else ValidationStatus.PASS,
            "warning" if expired else "info",
            f"expiration={quote.expiration.isoformat()}, as_of={valuation_date.isoformat()}",
            "exclude expired contracts from current-chain selection" if expired else "continue",
        )
    )

    for field, rule in (
        ("open_interest", "missing_open_interest"),
        ("volume", "missing_volume"),
        ("implied_volatility", "missing_implied_volatility"),
        ("delta", "missing_delta"),
        ("gamma", "missing_gamma"),
        ("theta", "missing_theta"),
        ("vega", "missing_vega"),
    ):
        value = getattr(quote, field)
        results.append(
            _result(
                quote,
                rule,
                ValidationStatus.UNAVAILABLE if value is None else ValidationStatus.PASS,
                "warning" if value is None else "info",
                quote.missing_field_reasons.get(field, f"{field} supplied"),
                f"obtain {field} before using this field" if value is None else "continue",
            )
        )

    low_liquidity = (
        quote.open_interest is not None
        and quote.volume is not None
        and (quote.open_interest < minimum_open_interest or quote.volume < minimum_volume)
    )
    results.append(
        _result(
            quote,
            "low_liquidity",
            ValidationStatus.UNAVAILABLE
            if quote.open_interest is None or quote.volume is None
            else (ValidationStatus.FAIL if low_liquidity else ValidationStatus.PASS),
            "warning" if low_liquidity or quote.open_interest is None or quote.volume is None else "info",
            f"open_interest={quote.open_interest}, volume={quote.volume}",
            "exclude until liquidity fields are present and meet the minimums" if low_liquidity or quote.open_interest is None or quote.volume is None else "continue",
        )
    )

    if provider_plan in {"massive_options_basic", "alpha_vantage_free"}:
        results.append(
            _result(
                quote,
                "free_tier_data_limitations",
                ValidationStatus.UNAVAILABLE,
                "warning",
                f"provider plan {provider_plan} does not guarantee all option fields",
                "use only fields explicitly present; obtain an entitled source for missing fields",
            )
        )
    else:
        results.append(
            _result(
                quote,
                "free_tier_data_limitations",
                ValidationStatus.UNAVAILABLE,
                "info",
                "provider plan entitlement was not supplied",
                "record the provider plan before treating absent fields as a capability limitation",
            )
        )

    event_window = timedelta(days=event_window_days)
    for label, events, rule in (
        ("earnings", earnings_list, "earnings_near_expiration"),
        ("dividend", dividend_list, "dividend_near_expiration"),
    ):
        event_list = list(events or [])
        near = [event for event in event_list if abs((event - quote.expiration).days) <= event_window.days]
        results.append(
            _result(
                quote,
                rule,
                ValidationStatus.UNAVAILABLE if events is None else (ValidationStatus.FAIL if near else ValidationStatus.PASS),
                "warning" if near else ("info" if events is not None else "warning"),
                f"nearby {label} dates={near}" if near else (f"no nearby {label} dates" if events is not None else f"{label} calendar not supplied"),
                "review event gap and assignment/volatility risk before use" if near else (f"load the {label} calendar" if events is None else "continue"),
            )
        )

    assignment_risk = bool(
        quote.option_type.lower() == "call"
        and quote.underlying_price is not None
        and quote.underlying_price > quote.strike
        and dividend_list is not None
        and any(0 <= (event - valuation_date).days <= event_window_days for event in dividend_list)
    )
    results.append(
        _result(
            quote,
            "early_assignment_risk",
            ValidationStatus.FAIL if assignment_risk else (ValidationStatus.PASS if dividend_list is not None else ValidationStatus.UNAVAILABLE),
            "warning" if assignment_risk else ("info" if dividend_list is not None else "warning"),
            "ITM call near a supplied dividend date" if assignment_risk else "assignment screen is not triggered by supplied inputs",
            "manual assignment review required" if assignment_risk else ("load dividend and spot data" if dividend_list is None else "continue"),
        )
    )
    return results


def validate_chain(
    quotes: Sequence[OptionQuote],
    *,
    max_timestamp_gap_seconds: float = 300.0,
    max_price_difference_fraction: float = 0.20,
    as_of: date | None = None,
    now: datetime | None = None,
    max_stale_seconds: float = 900.0,
    max_spread_fraction: float = 0.25,
    minimum_open_interest: int = 1,
    minimum_volume: int = 1,
    earnings_dates: Iterable[date] | None = None,
    dividend_dates: Iterable[date] | None = None,
    event_window_days: int = 14,
    provider_plan: str | None = None,
) -> list[ValidationResult]:
    """Run per-quote checks plus duplicate, timestamp, and price reconciliation."""

    results: list[ValidationResult] = []
    for quote in quotes:
        results.extend(
            validate_quote(
                quote,
                as_of=as_of,
                now=now,
                max_stale_seconds=max_stale_seconds,
                max_spread_fraction=max_spread_fraction,
                minimum_open_interest=minimum_open_interest,
                minimum_volume=minimum_volume,
                earnings_dates=earnings_dates,
                dividend_dates=dividend_dates,
                event_window_days=event_window_days,
                provider_plan=provider_plan,
            )
        )
    ordered = sorted(quotes, key=contract_key)
    for key, group_iter in groupby(ordered, key=contract_key):
        group = list(group_iter)
        if len(group) > 1:
            for quote in group[1:]:
                results.append(
                    _result(
                        quote,
                        "duplicate_contract",
                        ValidationStatus.FAIL,
                        "error",
                        f"duplicate normalized contract key {key}",
                        "keep one source row only after resolving provider identity",
                    )
                )
        timestamps = [quote.quote_timestamp for quote in group if quote.quote_timestamp is not None]
        if len(timestamps) >= 2:
            gap = (max(timestamps) - min(timestamps)).total_seconds()
            for quote in group:
                results.append(
                    _result(
                        quote,
                        "conflicting_provider_timestamps",
                        ValidationStatus.FAIL if gap > max_timestamp_gap_seconds else ValidationStatus.PASS,
                        "warning" if gap > max_timestamp_gap_seconds else "info",
                        f"provider timestamp gap={gap:.1f}s",
                        "reconcile to one observation time before comparing prices" if gap > max_timestamp_gap_seconds else "continue",
                    )
                )
        prices = [quote for quote in group if quote.midpoint is not None or quote.last_price is not None]
        numeric_prices = [quote.midpoint if quote.midpoint is not None else quote.last_price for quote in prices]
        numeric_prices = [float(price) for price in numeric_prices if price is not None and price > 0]
        if len(numeric_prices) >= 2:
            difference = (max(numeric_prices) - min(numeric_prices)) / min(numeric_prices)
            for quote in group:
                results.append(
                    _result(
                        quote,
                        "large_provider_price_difference",
                        ValidationStatus.FAIL if difference > max_price_difference_fraction else ValidationStatus.PASS,
                        "warning" if difference > max_price_difference_fraction else "info",
                        f"provider price difference={difference:.3f}",
                        "inspect raw responses, timestamps, and contract identity" if difference > max_price_difference_fraction else "continue",
                    )
                )
    return results
