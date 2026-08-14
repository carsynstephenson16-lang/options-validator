"""Causal as-of resolution of stored short-positioning records.

Reads local validated partitions only. Nothing here fetches, repairs, or
guesses: a record that was not available at the requested timestamp is
refused, and every failure resolves to a visible status.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from data.short_positioning.identity import SecurityAliasV1, resolve_security_identity
from data.short_positioning.models import (
    ShortInterestFeaturesV1,
    ShortInterestRecordV1,
    ShortPositioningSchemaError,
    ShortPositioningSnapshotV1,
    primary_status_of,
)
from data.short_positioning.normalize import NORMALIZED_FILE_GLOB, record_from_json
from data.short_positioning.provider import LICENSE_BLOCKED_PROVIDERS

DEFAULT_DATASET = "consolidated-short-interest"
DEFAULT_PROVIDER_ORDER: tuple[str, ...] = ("finra",)
DEFAULT_MAX_AGE_RELEASES = 1


def _partition_root(root: Path, provider: str, dataset: str) -> Path:
    return Path(root) / "normalized" / f"provider={provider}" / f"dataset={dataset}"


def _load_partition(path: Path) -> list[ShortInterestRecordV1]:
    try:
        document = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ShortPositioningSchemaError(f"partition {path.name} is not decodable: {exc}") from exc
    rows = document.get("records") if isinstance(document, dict) else None
    if not isinstance(rows, list):
        raise ShortPositioningSchemaError(f"partition {path.name} has no records array")
    return [record_from_json(row) for row in rows]


def _load_all(root: Path, provider: str, dataset: str) -> list[ShortInterestRecordV1]:
    base = _partition_root(root, provider, dataset)
    if not base.exists():
        return []
    records: list[ShortInterestRecordV1] = []
    for path in sorted(base.glob(f"publication_date=*/{NORMALIZED_FILE_GLOB}")):
        records.extend(_load_partition(path))
    return records


def load_latest_available_records(
    root: Path,
    *,
    provider: str,
    dataset: str,
    symbol: str,
    asof: datetime,
) -> tuple[ShortInterestRecordV1, ...]:
    """Every stored record for ``symbol`` that was available at ``asof``.

    Ordered oldest-available first. A record whose ``available_at`` is after
    ``asof`` is omitted, never shown as pending-but-known.
    """
    available = [
        record
        for record in _load_all(Path(root), provider, dataset)
        if record.symbol == symbol and record.available_at <= asof
    ]
    available.sort(key=lambda r: (r.available_at, r.publication_date, bool(r.revision_flag)))
    return tuple(available)


def _sessions_between(start: date, end: date) -> int:
    """Completed XNYS sessions after ``start`` up to and including ``end``."""
    if end < start:
        return 0
    from data.cache_runner import trading_days

    sessions = trading_days(start.isoformat(), end.isoformat())
    return max(len(sessions) - 1, 0)


def _releases_behind(
    records: list[ShortInterestRecordV1], selected: ShortInterestRecordV1, asof: datetime
) -> int:
    """Publications newer than the selected one that were already available.

    Counting observed partitions avoids inventing a release calendar: if a
    later publication exists and is available but carries no row for this
    symbol, the symbol is behind by that many releases.
    """
    newer = {
        record.publication_date
        for record in records
        if record.publication_date > selected.publication_date and record.available_at <= asof
    }
    return len(newer)


def _build_features(
    selected: ShortInterestRecordV1, *, asof: datetime, lineage_sha256: str
) -> ShortInterestFeaturesV1:
    previous = selected.previous_short_shares
    if previous is None or previous == 0:
        change_pct = None
        change_1_cycle = None
    else:
        delta = Decimal(selected.current_short_shares - previous)
        change_1_cycle = delta / Decimal(previous)
        change_pct = Decimal(100) * change_1_cycle

    return ShortInterestFeaturesV1(
        schema_version="short-interest-features/v1",
        source_record_key=selected.source_record_key,
        provider=selected.provider,
        feature_asof=asof,
        available_at=selected.available_at,
        available_session=selected.available_session,
        change_pct=change_pct,
        change_1_cycle=change_1_cycle,
        change_3_cycles=None,
        # No float source is wired in v1, so the denominator stays empty
        # rather than borrowing a current float for a historical row.
        float_shares=None,
        float_asof=None,
        float_available_at=None,
        float_source=None,
        short_pct_float=None,
        # Percentiles stay None until a documented convention exists.
        own_history_percentile=None,
        cross_sectional_percentile=None,
        data_age_sessions=_sessions_between(selected.available_session, asof.date()),
        price_return_since_settlement=None,
        price_return_since_publication=None,
        lineage_sha256=lineage_sha256,
    )


def _snapshot(
    symbol: str,
    asof: datetime,
    statuses: list[str],
    *,
    explanation: str,
    max_asof: datetime | None = None,
    record: ShortInterestRecordV1 | None = None,
    features: ShortInterestFeaturesV1 | None = None,
) -> ShortPositioningSnapshotV1:
    unique = list(dict.fromkeys(statuses)) or ["OK"]
    return ShortPositioningSnapshotV1(
        schema_version="short-positioning-snapshot/v1",
        symbol=symbol,
        asof=asof,
        max_asof=max_asof,
        primary_status=primary_status_of(tuple(unique)),  # type: ignore[arg-type]
        statuses=tuple(unique),  # type: ignore[arg-type]
        short_interest=record,
        features=features,
        provider_extension_ref=None,
        explanation=explanation,
    )


def resolve_short_positioning_snapshot(
    root: Path,
    *,
    symbol: str,
    asof: datetime,
    provider_order: tuple[str, ...] = DEFAULT_PROVIDER_ORDER,
    dataset: str = DEFAULT_DATASET,
    max_age_releases: int = DEFAULT_MAX_AGE_RELEASES,
    aliases: tuple[SecurityAliasV1, ...] = (),
) -> ShortPositioningSnapshotV1:
    """Resolve one symbol's positioning snapshot as of a causal timestamp."""
    if asof.tzinfo is None:
        raise ShortPositioningSchemaError("asof must be timezone-aware")

    blocked = [provider for provider in provider_order if provider in LICENSE_BLOCKED_PROVIDERS]
    if blocked:
        return _snapshot(
            symbol,
            asof,
            ["LICENSE_BLOCKED"],
            explanation=f"no entitlement for {', '.join(blocked)}; nothing was read",
        )

    provider = provider_order[0] if provider_order else DEFAULT_PROVIDER_ORDER[0]

    try:
        stored = _load_all(Path(root), provider, dataset)
    except ShortPositioningSchemaError as exc:
        return _snapshot(
            symbol, asof, ["SCHEMA_ERROR"], explanation=f"stored data failed validation: {exc}"
        )

    for_symbol = [record for record in stored if record.symbol == symbol]
    if not for_symbol:
        return _snapshot(
            symbol, asof, ["NO_RECORD"], explanation=f"{provider} has no stored row for {symbol}"
        )

    available = [record for record in for_symbol if record.available_at <= asof]
    if not available:
        earliest = min(record.available_at for record in for_symbol)
        return _snapshot(
            symbol,
            asof,
            ["FUTURE_DATA"],
            explanation=(
                f"the earliest stored row for {symbol} became available at "
                f"{earliest.isoformat()}, after the requested as-of; refused"
            ),
        )

    selected = max(
        available, key=lambda r: (r.available_at, r.publication_date, bool(r.revision_flag))
    )

    statuses: list[str] = []
    identity = resolve_security_identity(
        symbol,
        asof=asof.date(),
        aliases=aliases,
        market=selected.market,
        issue_name=selected.issue_name,
    )
    if identity.identity_status == "AMBIGUOUS":
        statuses.append("AMBIGUOUS_SECURITY")
    if identity.identity_status == "CORPORATE_ACTION" or selected.stock_split_flag:
        statuses.append("CORPORATE_ACTION")
    if selected.revision_flag:
        statuses.append("REVISED")

    behind = _releases_behind(stored, selected, asof)
    if behind > max_age_releases:
        statuses.append("STALE")

    derived_blocked = bool({"AMBIGUOUS_SECURITY", "CORPORATE_ACTION"} & set(statuses))
    features = (
        None
        if derived_blocked
        else _build_features(selected, asof=asof, lineage_sha256=selected.raw_sha256)
    )
    if not derived_blocked:
        statuses.append("FLOAT_UNAVAILABLE")

    if derived_blocked:
        explanation = (
            "raw source values only; identity or corporate-action ambiguity blocks derived history"
        )
    elif "STALE" in statuses:
        explanation = f"{behind} newer publications are available without a row for {symbol}"
    else:
        explanation = "position shown as reported; no float denominator is wired in v1"

    return _snapshot(
        symbol,
        asof,
        statuses,
        explanation=explanation,
        max_asof=selected.available_at,
        record=selected,
        features=features,
    )
