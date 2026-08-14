"""Normalized short-positioning schemas (v1).

These contracts are provider-neutral. A provider adapter maps its own source
fields onto them; nothing here knows how to fetch anything. Every timestamp is
timezone-aware UTC, every missing source value stays ``None``, and no ratio is
clamped.

Registered design: docs/superpowers/specs/2026-08-11-short-positioning-context-design.md
Field map and data rights: docs/data/short-positioning-contract.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal

PROVENANCE_SCHEMA = "short-positioning-provenance/v1"
IDENTITY_SCHEMA = "security-identity/v1"
CORE_SCHEMA = "short-interest-core/v1"
FEATURES_SCHEMA = "short-interest-features/v1"
SNAPSHOT_SCHEMA = "short-positioning-snapshot/v1"

AccessMethod = Literal["api", "download", "manual_csv", "sftp"]
DataClassification = Literal["public_local_only", "licensed_local_only", "synthetic_test"]
IdentityStatus = Literal["VERIFIED", "SYMBOL_ONLY", "AMBIGUOUS", "CORPORATE_ACTION"]
ShortPositioningStatus = Literal[
    "OK",
    "NO_RECORD",
    "NOT_YET_PUBLISHED",
    "STALE",
    "REVISED",
    "CORPORATE_ACTION",
    "AMBIGUOUS_SECURITY",
    "FLOAT_UNAVAILABLE",
    "PROVIDER_CONFLICT",
    "LICENSE_BLOCKED",
    "SCHEMA_ERROR",
    "HASH_MISMATCH",
    "FUTURE_DATA",
    "MISSING_PROVENANCE",
    "PARTIAL_CAPTURE",
]

ACCESS_METHODS: tuple[str, ...] = ("api", "download", "manual_csv", "sftp")
DATA_CLASSIFICATIONS: tuple[str, ...] = (
    "public_local_only",
    "licensed_local_only",
    "synthetic_test",
)
IDENTITY_STATUSES: tuple[str, ...] = ("VERIFIED", "SYMBOL_ONLY", "AMBIGUOUS", "CORPORATE_ACTION")

# Highest priority first. A snapshot carries every applicable status and one
# primary status drawn from this order.
STATUS_PRECEDENCE: tuple[str, ...] = (
    "SCHEMA_ERROR",
    "HASH_MISMATCH",
    "FUTURE_DATA",
    "MISSING_PROVENANCE",
    "PARTIAL_CAPTURE",
    "LICENSE_BLOCKED",
    "AMBIGUOUS_SECURITY",
    "CORPORATE_ACTION",
    "NOT_YET_PUBLISHED",
    "NO_RECORD",
    "PROVIDER_CONFLICT",
    "STALE",
    "REVISED",
    "FLOAT_UNAVAILABLE",
    "OK",
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}")


class ShortPositioningSchemaError(ValueError):
    """A value violates the registered v1 contract. Always fail closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ShortPositioningSchemaError(message)


def _require_sha256(value: object, label: str) -> None:
    _require(
        isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None,
        f"{label} must be a lowercase 64-character SHA-256 hex digest",
    )


def _require_utc(value: object, label: str) -> None:
    _require(isinstance(value, datetime), f"{label} must be a datetime")
    assert isinstance(value, datetime)
    _require(value.tzinfo is not None, f"{label} must be timezone-aware")
    _require(value.utcoffset() == timedelta(0), f"{label} must be expressed in UTC")


def _require_optional_int(value: object, label: str) -> None:
    if value is None:
        return
    _require(
        isinstance(value, int) and not isinstance(value, bool),
        f"{label} must be an integer share count or None",
    )


def primary_status_of(statuses: tuple[str, ...] | list[str]) -> str:
    """Return the highest-precedence status in ``statuses``."""
    _require(bool(statuses), "a snapshot must carry at least one status")
    unknown = [status for status in statuses if status not in STATUS_PRECEDENCE]
    _require(not unknown, f"unknown short-positioning status: {sorted(unknown)}")
    return min(statuses, key=STATUS_PRECEDENCE.index)


def build_source_record_key(
    *,
    provider: str,
    dataset: str,
    market: str | None,
    symbol: str,
    settlement_date: date,
    source_revision: str,
) -> str:
    """Deterministic identity of one captured provider row.

    ``source_revision`` distinguishes an original capture from a later revised
    capture of the same settlement date, so both persist side by side instead
    of one overwriting the other.
    """
    parts = (provider, dataset, market or "-", symbol, settlement_date.isoformat(), source_revision)
    for part in parts:
        _require("|" not in part, f"source-record-key component may not contain '|': {part!r}")
    return "|".join(parts)


@dataclass(frozen=True, slots=True)
class SourceProvenanceV1:
    schema_version: Literal["short-positioning-provenance/v1"]
    provider: str
    dataset: str
    source_document: str
    access_method: AccessMethod
    source_data_version: str | None
    source_release_at: datetime | None
    source_timezone: str
    source_field_map_version: str
    source_row_ordinal: int | None
    request_id: str | None
    raw_sha256: str
    data_classification: DataClassification

    def __post_init__(self) -> None:
        _require(
            self.schema_version == PROVENANCE_SCHEMA,
            f"provenance schema_version must be {PROVENANCE_SCHEMA}",
        )
        _require(
            self.access_method in ACCESS_METHODS, f"unknown access method {self.access_method}"
        )
        _require(
            self.data_classification in DATA_CLASSIFICATIONS,
            f"unknown data classification {self.data_classification}",
        )
        _require_sha256(self.raw_sha256, "provenance raw_sha256")
        if self.source_release_at is not None:
            _require_utc(self.source_release_at, "source_release_at")


@dataclass(frozen=True, slots=True)
class SecurityIdentityV1:
    schema_version: Literal["security-identity/v1"]
    security_id: str | None
    security_id_scheme: str | None
    symbol: str
    market: str | None
    issue_name: str | None
    effective_from: date | None
    effective_to: date | None
    identity_status: IdentityStatus

    def __post_init__(self) -> None:
        _require(
            self.schema_version == IDENTITY_SCHEMA,
            f"identity schema_version must be {IDENTITY_SCHEMA}",
        )
        _require(
            self.identity_status in IDENTITY_STATUSES,
            f"unknown identity status {self.identity_status}",
        )
        if self.effective_from is not None and self.effective_to is not None:
            _require(
                self.effective_from <= self.effective_to,
                "identity effective_from must not follow effective_to",
            )


@dataclass(frozen=True, slots=True)
class ShortInterestRecordV1:
    schema_version: Literal["short-interest-core/v1"]
    provider: str
    dataset: str
    source_record_key: str

    security_id: str | None
    symbol: str
    market: str | None
    issue_name: str | None

    settlement_date: date
    publication_date: date
    available_at: datetime
    available_session: date
    retrieved_at: datetime

    current_short_shares: int
    previous_short_shares: int | None
    change_shares: int | None
    average_daily_volume_shares: int | None
    days_to_cover: Decimal | None

    revision_flag: bool | None
    stock_split_flag: bool | None

    raw_sha256: str
    source_provenance: SourceProvenanceV1

    def __post_init__(self) -> None:
        _require(
            self.schema_version == CORE_SCHEMA,
            f"record schema_version must be {CORE_SCHEMA}",
        )


@dataclass(frozen=True, slots=True)
class ShortInterestFeaturesV1:
    schema_version: Literal["short-interest-features/v1"]
    source_record_key: str
    provider: str

    feature_asof: datetime
    available_at: datetime
    available_session: date

    change_pct: Decimal | None
    change_1_cycle: Decimal | None
    change_3_cycles: Decimal | None

    float_shares: int | None
    float_asof: date | None
    float_available_at: datetime | None
    float_source: str | None
    short_pct_float: Decimal | None

    own_history_percentile: Decimal | None
    cross_sectional_percentile: Decimal | None

    data_age_sessions: int
    price_return_since_settlement: Decimal | None
    price_return_since_publication: Decimal | None

    lineage_sha256: str

    def __post_init__(self) -> None:
        _require(
            self.schema_version == FEATURES_SCHEMA,
            f"features schema_version must be {FEATURES_SCHEMA}",
        )
        _require_utc(self.feature_asof, "feature_asof")
        _require_utc(self.available_at, "features available_at")
        _require_sha256(self.lineage_sha256, "lineage_sha256")
        _require(
            isinstance(self.data_age_sessions, int) and self.data_age_sessions >= 0,
            "data_age_sessions must be a non-negative XNYS session count",
        )
        if self.short_pct_float is not None:
            _require(
                self.float_available_at is not None and self.float_asof is not None,
                "short_pct_float requires a point-in-time float denominator",
            )
            _require_utc(self.float_available_at, "float_available_at")
            _require(
                self.float_available_at is not None
                and self.float_available_at <= self.available_at,
                "float denominator must be available no later than the position record",
            )


@dataclass(frozen=True, slots=True)
class ShortPositioningSnapshotV1:
    schema_version: Literal["short-positioning-snapshot/v1"]
    symbol: str
    asof: datetime
    max_asof: datetime | None
    primary_status: ShortPositioningStatus
    statuses: tuple[ShortPositioningStatus, ...]
    short_interest: ShortInterestRecordV1 | None
    features: ShortInterestFeaturesV1 | None
    provider_extension_ref: str | None
    explanation: str

    def __post_init__(self) -> None:
        _require(
            self.schema_version == SNAPSHOT_SCHEMA,
            f"snapshot schema_version must be {SNAPSHOT_SCHEMA}",
        )
        _require(bool(self.statuses), "a snapshot must carry at least one status")
        _require(
            len(set(self.statuses)) == len(self.statuses),
            f"snapshot statuses must be unique: {self.statuses}",
        )
        _require(
            self.primary_status == primary_status_of(self.statuses),
            f"primary_status {self.primary_status} does not follow the registered precedence",
        )
        _require_utc(self.asof, "snapshot asof")
        if self.max_asof is not None:
            _require_utc(self.max_asof, "snapshot max_asof")


def validate_short_interest_record(record: ShortInterestRecordV1) -> None:
    """Raise ``ShortPositioningSchemaError`` unless the record is causally sound.

    Construction stays cheap; this is the gate every capture, store write, and
    snapshot read must pass. It never repairs a value.
    """
    _require(
        isinstance(record.current_short_shares, int)
        and not isinstance(record.current_short_shares, bool),
        "current_short_shares must be an integer share count",
    )
    _require(record.current_short_shares >= 0, "current_short_shares must be non-negative")
    _require_optional_int(record.previous_short_shares, "previous_short_shares")
    _require_optional_int(record.change_shares, "change_shares")
    _require_optional_int(record.average_daily_volume_shares, "average_daily_volume_shares")
    if record.days_to_cover is not None:
        _require(
            isinstance(record.days_to_cover, Decimal),
            "days_to_cover must preserve the source value as a Decimal",
        )

    _require(bool(record.symbol) and record.symbol == record.symbol.upper(), "symbol must be upper")
    _require(
        record.settlement_date <= record.publication_date,
        "settlement_date must not follow publication_date",
    )
    _require_utc(record.available_at, "available_at")
    _require_utc(record.retrieved_at, "retrieved_at")
    _require(
        record.available_at <= record.retrieved_at,
        "a normalized record may not be available after it was retrieved",
    )

    _require_sha256(record.raw_sha256, "record raw_sha256")
    _require(
        record.raw_sha256 == record.source_provenance.raw_sha256,
        "record raw_sha256 must match its provenance raw_sha256",
    )
    _require(
        record.provider == record.source_provenance.provider
        and record.dataset == record.source_provenance.dataset,
        "record provider/dataset must match its provenance",
    )

    expected_key = build_source_record_key(
        provider=record.provider,
        dataset=record.dataset,
        market=record.market,
        symbol=record.symbol,
        settlement_date=record.settlement_date,
        source_revision="revised" if record.revision_flag else "original",
    )
    _require(
        record.source_record_key == expected_key,
        f"source_record_key {record.source_record_key!r} is not the derived key",
    )
