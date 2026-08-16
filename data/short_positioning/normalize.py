"""Normalized publication partitions.

A partition is written whole or not at all: every record validates, keys are
unique, and every requested symbol is present. Normalization never mutates raw
bytes and never repairs a value.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from data.short_positioning.models import (
    ShortInterestRecordV1,
    ShortPositioningSchemaError,
    SourceProvenanceV1,
    validate_short_interest_record,
)
from data.short_positioning.provider import (
    ArtifactIntegrityError,
    CaptureRequest,
    PartialCaptureError,
)

# One immutable file per capture. A revision is a NEW capture beside the
# original, never a rewrite of it: FINRA exposes only the latest corrected
# view, so overwriting would destroy the only copy of the original row.
NORMALIZED_FILE_GLOB = "records-*.json"


def normalized_capture_filename(request_id: str) -> str:
    return f"records-{request_id}.json"


def _sync(fd: int) -> None:
    os.fsync(fd)
    if sys.platform == "darwin":
        import fcntl

        fcntl.fcntl(fd, fcntl.F_FULLFSYNC)


def normalized_partition_dir(root: Path, request: CaptureRequest) -> Path:
    return (
        Path(root)
        / "normalized"
        / f"provider={request.provider}"
        / f"dataset={request.dataset}"
        / f"publication_date={request.publication_date.isoformat()}"
    )


def record_to_json(record: ShortInterestRecordV1) -> dict:
    """Serialize a record losslessly. Decimals become strings, not floats."""
    provenance = record.source_provenance
    return {
        "schema_version": record.schema_version,
        "provider": record.provider,
        "dataset": record.dataset,
        "source_record_key": record.source_record_key,
        "security_id": record.security_id,
        "symbol": record.symbol,
        "market": record.market,
        "issue_name": record.issue_name,
        "settlement_date": record.settlement_date.isoformat(),
        "publication_date": record.publication_date.isoformat(),
        "available_at": record.available_at.isoformat(),
        "available_session": record.available_session.isoformat(),
        "retrieved_at": record.retrieved_at.isoformat(),
        "current_short_shares": record.current_short_shares,
        "previous_short_shares": record.previous_short_shares,
        "change_shares": record.change_shares,
        "average_daily_volume_shares": record.average_daily_volume_shares,
        "days_to_cover": None if record.days_to_cover is None else str(record.days_to_cover),
        "revision_flag": record.revision_flag,
        "stock_split_flag": record.stock_split_flag,
        "raw_sha256": record.raw_sha256,
        "source_provenance": {
            "schema_version": provenance.schema_version,
            "provider": provenance.provider,
            "dataset": provenance.dataset,
            "source_document": provenance.source_document,
            "access_method": provenance.access_method,
            "source_data_version": provenance.source_data_version,
            "source_release_at": (
                None
                if provenance.source_release_at is None
                else provenance.source_release_at.isoformat()
            ),
            "source_timezone": provenance.source_timezone,
            "source_field_map_version": provenance.source_field_map_version,
            "source_row_ordinal": provenance.source_row_ordinal,
            "request_id": provenance.request_id,
            "raw_sha256": provenance.raw_sha256,
            "data_classification": provenance.data_classification,
        },
    }


def record_from_json(row: dict) -> ShortInterestRecordV1:
    """Rebuild a record from a stored partition. Malformed rows fail closed."""
    try:
        provenance_row = row["source_provenance"]
        release_at = provenance_row.get("source_release_at")
        provenance = SourceProvenanceV1(
            schema_version=provenance_row["schema_version"],
            provider=provenance_row["provider"],
            dataset=provenance_row["dataset"],
            source_document=provenance_row["source_document"],
            access_method=provenance_row["access_method"],
            source_data_version=provenance_row.get("source_data_version"),
            source_release_at=None if release_at is None else datetime.fromisoformat(release_at),
            source_timezone=provenance_row["source_timezone"],
            source_field_map_version=provenance_row["source_field_map_version"],
            source_row_ordinal=provenance_row.get("source_row_ordinal"),
            request_id=provenance_row.get("request_id"),
            raw_sha256=provenance_row["raw_sha256"],
            data_classification=provenance_row["data_classification"],
        )
        days_to_cover = row.get("days_to_cover")
        return ShortInterestRecordV1(
            schema_version=row["schema_version"],
            provider=row["provider"],
            dataset=row["dataset"],
            source_record_key=row["source_record_key"],
            security_id=row.get("security_id"),
            symbol=row["symbol"],
            market=row.get("market"),
            issue_name=row.get("issue_name"),
            settlement_date=date.fromisoformat(row["settlement_date"]),
            publication_date=date.fromisoformat(row["publication_date"]),
            available_at=datetime.fromisoformat(row["available_at"]),
            available_session=date.fromisoformat(row["available_session"]),
            retrieved_at=datetime.fromisoformat(row["retrieved_at"]),
            current_short_shares=row["current_short_shares"],
            previous_short_shares=row.get("previous_short_shares"),
            change_shares=row.get("change_shares"),
            average_daily_volume_shares=row.get("average_daily_volume_shares"),
            days_to_cover=None if days_to_cover is None else Decimal(days_to_cover),
            revision_flag=row.get("revision_flag"),
            stock_split_flag=row.get("stock_split_flag"),
            raw_sha256=row["raw_sha256"],
            source_provenance=provenance,
        )
    except ShortPositioningSchemaError:
        raise
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise ShortPositioningSchemaError(f"stored record is not readable: {exc}") from exc


def write_normalized_partition(
    records: Sequence[ShortInterestRecordV1],
    *,
    root: Path,
    request: CaptureRequest,
) -> Path:
    """Validate then atomically publish one publication partition."""
    for record in records:
        validate_short_interest_record(record)

    keys = [record.source_record_key for record in records]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise ShortPositioningSchemaError(
            f"duplicate source_record_key values block the partition: {duplicates}"
        )

    missing = sorted(set(request.symbols) - {record.symbol for record in records})
    if missing:
        raise PartialCaptureError(
            f"requested symbols missing from the response: {missing}; the partition is "
            "incomplete and was rolled back"
        )

    partition = normalized_partition_dir(root, request)
    path = partition / normalized_capture_filename(request.request_id)
    if path.exists():
        raise ArtifactIntegrityError(
            f"normalized capture {path.name} already exists; captures are immutable"
        )
    document = {
        "schema_version": "short-interest-core/v1",
        "provider": request.provider,
        "dataset": request.dataset,
        "publication_date": request.publication_date.isoformat(),
        "record_count": len(records),
        "records": [record_to_json(record) for record in records],
    }

    partition.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temp.open("x") as handle:
            handle.write(json.dumps(document, sort_keys=True, indent=2) + "\n")
            handle.flush()
            _sync(handle.fileno())
        os.replace(temp, path)
        dir_fd = os.open(partition, os.O_RDONLY)
        try:
            _sync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise

    return path
