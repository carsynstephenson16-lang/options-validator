"""Point-in-time risk-free rates and dividend yields for Black-Scholes.

The local inputs are strict, provenance-bearing CSV stores.  This module has
no fetch path: missing, malformed, stale, or not-yet-known inputs fail closed.
Treasury CMT values are par yields; treating the interpolated par curve as a
zero curve is an explicitly labeled approximation from the frozen design.
"""
from __future__ import annotations

import csv
import hashlib
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import config

TREASURY_FIELDS = (
    "observation_date",
    "tenor_days",
    "par_yield",
    "known_as_of_utc",
    "valid_through",
    "source_url",
    "captured_at_utc",
    "units",
)
DIVIDEND_FIELDS = (
    "symbol",
    "effective_date",
    "expected_annual_cash_dividend",
    "known_as_of_utc",
    "valid_through",
    "source_url",
    "captured_at_utc",
    "units",
)
_NEW_YORK = ZoneInfo("America/New_York")


class MissingRateError(ValueError):
    """No valid point-in-time Treasury curve can support the computation."""


class MissingDividendYieldError(ValueError):
    """No sourced point-in-time dividend expectation exists for a symbol."""


@dataclass(frozen=True)
class SourceProvenance:
    source_url: str
    source_date: date
    known_as_of_utc: datetime
    captured_at_utc: datetime
    valid_through: date
    units: str
    staleness_rule: str


@dataclass(frozen=True)
class RiskFreeRate:
    rate: float
    par_yield: float
    observation_date: date
    expiration_date: date
    source_date: date
    par_curve_as_zero_approximation: bool
    provenance: SourceProvenance


@dataclass(frozen=True)
class DividendYield:
    yield_rate: float
    expected_annual_cash_dividend: float
    symbol: str
    observation_date: date
    synchronized_spot: float
    provenance: SourceProvenance


@dataclass(frozen=True)
class _TreasuryRow:
    source_date: date
    tenor_days: int
    par_yield: float
    known_as_of_utc: datetime
    valid_through: date
    source_url: str
    captured_at_utc: datetime
    units: str


@dataclass(frozen=True)
class _DividendRow:
    symbol: str
    effective_date: date
    expected_annual_cash_dividend: float
    known_as_of_utc: datetime
    valid_through: date
    source_url: str
    captured_at_utc: datetime
    units: str


def _valuation_close_utc(on: date) -> datetime:
    if type(on) is not date:
        raise ValueError("observation_date must be a datetime.date")
    return datetime.combine(on, time(16, 0), tzinfo=_NEW_YORK).astimezone(timezone.utc)


def _parse_date(value: str, *, field: str, context: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context}: {field} must be an ISO date") from exc


def _parse_timestamp(value: str, *, field: str, context: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{context}: {field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{context}: {field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _parse_float(value: str, *, field: str, context: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context}: {field} must be numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{context}: {field} must be finite")
    return parsed


def _source_url(value: str, *, context: str) -> str:
    normalized = value.strip()
    if not normalized.startswith("https://"):
        raise ValueError(f"{context}: source_url must be an exact https:// URL")
    return normalized


def par_to_continuous(par_yield: float) -> float:
    """Approximate a continuous rate from an annually compounded par yield."""
    if (
        isinstance(par_yield, bool)
        or not isinstance(par_yield, (int, float))
        or not math.isfinite(par_yield)
        or par_yield <= -1.0
    ):
        raise ValueError("par_yield must be finite and greater than -1")
    return math.log1p(par_yield)


def interp_rate(curve: dict[int, float], days: float) -> float:
    """Interpolate linearly in time; clamp outside the supplied tenor range."""
    if not curve:
        raise ValueError("curve must contain at least one tenor")
    if (
        isinstance(days, bool)
        or not isinstance(days, (int, float))
        or not math.isfinite(days)
        or days < 0
    ):
        raise ValueError("days must be a finite non-negative number")
    if any(type(tenor) is not int or tenor <= 0 for tenor in curve):
        raise ValueError("curve tenors must be positive integer days")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= -1.0
        for value in curve.values()
    ):
        raise ValueError("curve rates must be finite and greater than -1")

    tenors = sorted(curve)
    if days <= tenors[0]:
        return float(curve[tenors[0]])
    if days >= tenors[-1]:
        return float(curve[tenors[-1]])
    for lower, upper in zip(tenors, tenors[1:]):
        if lower <= days <= upper:
            weight = (days - lower) / (upper - lower)
            return float(curve[lower] + weight * (curve[upper] - curve[lower]))
    raise AssertionError("unreachable")


def _load_treasury_rows(path: Path) -> list[_TreasuryRow]:
    rows: list[_TreasuryRow] = []
    seen: set[tuple[date, datetime, int]] = set()
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != TREASURY_FIELDS:
            raise ValueError(
                f"{path}: header must be {list(TREASURY_FIELDS)}, got {reader.fieldnames}"
            )
        for line_number, raw in enumerate(reader, start=2):
            context = f"{path}:{line_number}"
            source_date = _parse_date(
                raw["observation_date"], field="observation_date", context=context
            )
            valid_through = _parse_date(
                raw["valid_through"], field="valid_through", context=context
            )
            if valid_through < source_date:
                raise ValueError(f"{context}: valid_through precedes observation_date")
            try:
                tenor_days = int(raw["tenor_days"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{context}: tenor_days must be an integer") from exc
            if tenor_days <= 0:
                raise ValueError(f"{context}: tenor_days must be positive")
            par_yield = _parse_float(raw["par_yield"], field="par_yield", context=context)
            if par_yield < 0:
                raise ValueError(f"{context}: Treasury CMT par_yield must be non-negative")
            known = _parse_timestamp(
                raw["known_as_of_utc"], field="known_as_of_utc", context=context
            )
            captured = _parse_timestamp(
                raw["captured_at_utc"], field="captured_at_utc", context=context
            )
            if captured < known:
                raise ValueError(f"{context}: captured_at_utc precedes known_as_of_utc")
            units = raw["units"].strip()
            if units != config.BS_TREASURY_UNITS:
                raise ValueError(
                    f"{context}: units must be {config.BS_TREASURY_UNITS!r}"
                )
            key = (source_date, known, tenor_days)
            if key in seen:
                raise ValueError(f"{context}: duplicate curve tenor/version")
            seen.add(key)
            rows.append(
                _TreasuryRow(
                    source_date=source_date,
                    tenor_days=tenor_days,
                    par_yield=par_yield,
                    known_as_of_utc=known,
                    valid_through=valid_through,
                    source_url=_source_url(raw["source_url"], context=context),
                    captured_at_utc=captured,
                    units=units,
                )
            )
    return rows


@lru_cache(maxsize=32)
def _cached_treasury_rows(path: Path, content_sha256: str) -> tuple[_TreasuryRow, ...]:
    """Reuse a curve only while its complete local content is unchanged."""
    del content_sha256
    return tuple(_load_treasury_rows(path))


def _treasury_rows(path: Path) -> tuple[_TreasuryRow, ...]:
    return _cached_treasury_rows(path, hashlib.sha256(path.read_bytes()).hexdigest())


def risk_free_rate(
    observation_date: date,
    expiration_date: date,
    *,
    path: str | Path = config.BS_TREASURY_CURVE_PATH,
) -> RiskFreeRate:
    """Return a point-in-time continuous rate with explicit provenance."""
    if type(observation_date) is not date or type(expiration_date) is not date:
        raise ValueError("observation_date and expiration_date must be datetime.date values")
    if expiration_date < observation_date:
        raise ValueError("expiration_date must not precede observation_date")
    valuation_close = _valuation_close_utc(observation_date)
    eligible = [
        row
        for row in _treasury_rows(Path(path))
        if row.source_date <= observation_date <= row.valid_through
        and row.known_as_of_utc <= valuation_close
    ]
    if not eligible:
        raise MissingRateError(
            f"no Treasury curve known by valuation close for {observation_date.isoformat()}"
        )
    selected_version = max((row.source_date, row.known_as_of_utc) for row in eligible)
    selected = [
        row
        for row in eligible
        if (row.source_date, row.known_as_of_utc) == selected_version
    ]
    metadata = {
        (
            row.source_url,
            row.captured_at_utc,
            row.valid_through,
            row.units,
        )
        for row in selected
    }
    if len(metadata) != 1:
        raise ValueError("selected Treasury curve has inconsistent provenance")
    curve = {row.tenor_days: row.par_yield for row in selected}
    if len(curve) != len(selected):
        raise ValueError("selected Treasury curve has duplicate tenors")
    days = (expiration_date - observation_date).days
    par_yield = interp_rate(curve, days)
    source_url, captured, valid_through, units = metadata.pop()
    provenance = SourceProvenance(
        source_url=source_url,
        source_date=selected_version[0],
        known_as_of_utc=selected_version[1],
        captured_at_utc=captured,
        valid_through=valid_through,
        units=units,
        staleness_rule=config.BS_RATE_STALENESS_RULE,
    )
    return RiskFreeRate(
        rate=par_to_continuous(par_yield),
        par_yield=par_yield,
        observation_date=observation_date,
        expiration_date=expiration_date,
        source_date=selected_version[0],
        par_curve_as_zero_approximation=True,
        provenance=provenance,
    )


def _load_dividend_rows(path: Path) -> list[_DividendRow]:
    rows: list[_DividendRow] = []
    seen: set[tuple[str, date, datetime]] = set()
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != DIVIDEND_FIELDS:
            raise ValueError(
                f"{path}: header must be {list(DIVIDEND_FIELDS)}, got {reader.fieldnames}"
            )
        for line_number, raw in enumerate(reader, start=2):
            context = f"{path}:{line_number}"
            symbol = raw["symbol"].strip().upper()
            if not symbol:
                raise ValueError(f"{context}: symbol is required")
            effective_date = _parse_date(
                raw["effective_date"], field="effective_date", context=context
            )
            valid_through = _parse_date(
                raw["valid_through"], field="valid_through", context=context
            )
            if valid_through < effective_date:
                raise ValueError(f"{context}: valid_through precedes effective_date")
            expected = _parse_float(
                raw["expected_annual_cash_dividend"],
                field="expected_annual_cash_dividend",
                context=context,
            )
            if expected < 0:
                raise ValueError(
                    f"{context}: expected_annual_cash_dividend must be non-negative"
                )
            known = _parse_timestamp(
                raw["known_as_of_utc"], field="known_as_of_utc", context=context
            )
            captured = _parse_timestamp(
                raw["captured_at_utc"], field="captured_at_utc", context=context
            )
            if captured < known:
                raise ValueError(f"{context}: captured_at_utc precedes known_as_of_utc")
            units = raw["units"].strip()
            if units != config.BS_DIVIDEND_UNITS:
                raise ValueError(
                    f"{context}: units must be {config.BS_DIVIDEND_UNITS!r}"
                )
            key = (symbol, effective_date, known)
            if key in seen:
                raise ValueError(f"{context}: duplicate dividend expectation/version")
            seen.add(key)
            rows.append(
                _DividendRow(
                    symbol=symbol,
                    effective_date=effective_date,
                    expected_annual_cash_dividend=expected,
                    known_as_of_utc=known,
                    valid_through=valid_through,
                    source_url=_source_url(raw["source_url"], context=context),
                    captured_at_utc=captured,
                    units=units,
                )
            )
    return rows


def dividend_yield(
    symbol: str,
    observation_date: date,
    spot: float,
    *,
    path: str | Path = config.BS_DIVIDEND_INPUT_PATH,
) -> DividendYield:
    """Return expected annual cash dividend / synchronized raw spot."""
    normalized_symbol = symbol.strip().upper() if isinstance(symbol, str) else ""
    if not normalized_symbol:
        raise ValueError("symbol is required")
    if type(observation_date) is not date:
        raise ValueError("observation_date must be a datetime.date")
    if (
        isinstance(spot, bool)
        or not isinstance(spot, (int, float))
        or not math.isfinite(spot)
        or spot <= 0
    ):
        raise ValueError("synchronized spot must be a finite positive number")

    valuation_close = _valuation_close_utc(observation_date)
    eligible = [
        row
        for row in _load_dividend_rows(Path(path))
        if row.symbol == normalized_symbol
        and row.effective_date <= observation_date <= row.valid_through
        and row.known_as_of_utc <= valuation_close
    ]
    if not eligible:
        raise MissingDividendYieldError(
            f"no sourced dividend expectation for {normalized_symbol} known by "
            f"valuation close on {observation_date.isoformat()}"
        )
    selected = max(eligible, key=lambda row: (row.effective_date, row.known_as_of_utc))
    provenance = SourceProvenance(
        source_url=selected.source_url,
        source_date=selected.effective_date,
        known_as_of_utc=selected.known_as_of_utc,
        captured_at_utc=selected.captured_at_utc,
        valid_through=selected.valid_through,
        units=selected.units,
        staleness_rule=config.BS_DIVIDEND_STALENESS_RULE,
    )
    spot_value = float(spot)
    return DividendYield(
        yield_rate=selected.expected_annual_cash_dividend / spot_value,
        expected_annual_cash_dividend=selected.expected_annual_cash_dividend,
        symbol=normalized_symbol,
        observation_date=observation_date,
        synchronized_spot=spot_value,
        provenance=provenance,
    )


def require_dividend_coverage(
    symbols: Iterable[str],
    observation_date: date,
    synchronized_spots: Mapping[str, float],
    *,
    path: str | Path = config.BS_DIVIDEND_INPUT_PATH,
) -> dict[str, DividendYield]:
    """Resolve every requested symbol or raise; never silently default q to zero."""
    results: dict[str, DividendYield] = {}
    for raw_symbol in symbols:
        symbol = raw_symbol.strip().upper()
        if symbol not in synchronized_spots:
            raise MissingDividendYieldError(f"missing synchronized spot for {symbol}")
        results[symbol] = dividend_yield(
            symbol,
            observation_date,
            synchronized_spots[symbol],
            path=path,
        )
    return results
