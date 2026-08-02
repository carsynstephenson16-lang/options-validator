"""Canonical schema metadata for ThetaData EOD chain-cache partitions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

CHAIN_SCHEMA_VERSION_V1 = 1
CHAIN_SCHEMA_VERSION_V2 = 2

DISPLAY_ONLY = "display-only"
VERDICT_ELIGIBLE = "verdict-eligible"
V2_FULL_AUDIT_SCHEMA = "thetadata-v2-full-audit/v1"

CHAIN_COLUMNS_V1 = [
    "expiration",
    "strike",
    "right",
    "bid",
    "ask",
    "open_interest",
    "iv",
    "delta",
    "gamma",
    "theta",
    "vega",
]

# Verified 2026-07-30 from one owner-authorized thetadata==1.0.9
# option_history_greeks_eod response. These names are provider headers.
CHAIN_V2_PROVIDER_FIELDS = [
    "timestamp",
    "bid_size",
    "bid_condition",
    "ask_size",
    "ask_condition",
    "iv_error",
    "underlying_timestamp",
    "underlying_price",
]

# Capture provenance supplied locally, not a provider response header.
THETADATA_CLIENT_VERSION_COLUMN = "thetadata_client_version"

CHAIN_V2_CAPTURE_FIELDS = [
    *CHAIN_V2_PROVIDER_FIELDS,
    THETADATA_CLIENT_VERSION_COLUMN,
]
CHAIN_COLUMNS_V2 = [*CHAIN_COLUMNS_V1, *CHAIN_V2_CAPTURE_FIELDS]


@dataclass(frozen=True)
class ChainSchemaMetadata:
    schema_version: int
    usage: str


class CacheAuditReceiptError(ValueError):
    """A schema-v2 partition lacks valid, content-bound full-audit evidence."""


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CacheAuditReceiptError(message)


def validate_v2_audit_receipt(
    cache_dir: Path,
    chain_path: Path,
    *,
    symbol: str,
    session: str,
    receipt_path: Path | None = None,
) -> dict:
    """Bind one verdict-bearing partition to a clean, passing full audit."""
    cache_dir = Path(cache_dir).resolve()
    chain_path = Path(chain_path).resolve()
    receipt_path = (
        cache_dir / "_meta" / "full_audit.json" if receipt_path is None else Path(receipt_path)
    )
    try:
        report = json.loads(receipt_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise CacheAuditReceiptError(
            f"v2 full-audit receipt unreadable at {receipt_path}: {type(exc).__name__}: {exc}"
        ) from exc
    _require(isinstance(report, dict), "v2 full-audit receipt must be an object")
    _require(report.get("schema") == V2_FULL_AUDIT_SCHEMA, "v2 full-audit schema mismatch")

    claimed_receipt = report.get("receipt_hash")
    unsigned = {key: value for key, value in report.items() if key != "receipt_hash"}
    _require(
        isinstance(claimed_receipt, str)
        and _sha256_hex(_canonical_json(unsigned)) == claimed_receipt,
        "v2 full-audit receipt hash mismatch",
    )
    try:
        recorded_namespace = Path(report["output_namespace"]).resolve()
    except (KeyError, TypeError) as exc:
        raise CacheAuditReceiptError("v2 full-audit output namespace missing") from exc
    _require(recorded_namespace == cache_dir, "v2 full-audit output namespace mismatch")
    _require(report.get("verdict") in {"PASS", "PASS WITH WARNINGS"}, "v2 full audit blocks use")
    _require(report.get("blocks") == [], "v2 full audit has effective blocks")
    _require(symbol in report.get("symbols", []), f"{symbol} absent from v2 full-audit scope")
    _require(session in report.get("sessions", []), f"{session} absent from v2 full-audit window")

    quarantines = report.get("quarantined_partitions")
    _require(isinstance(quarantines, list), "v2 quarantine list missing")
    _require(
        not any(
            isinstance(entry, dict)
            and entry.get("symbol") == symbol
            and entry.get("session") == session
            for entry in quarantines
        ),
        f"{symbol} @ {session} is quarantined from verdict use",
    )

    base = report.get("base_fourteen_check_audit")
    _require(isinstance(base, dict), "base fourteen-check audit missing")
    file_hashes = base.get("file_hashes")
    _require(isinstance(file_hashes, dict), "base audit file hashes missing")
    _require(
        base.get("file_hashes_hash") == _sha256_hex(_canonical_json(file_hashes)),
        "base audit file-hash receipt mismatch",
    )
    base_claimed = base.get("receipt_hash")
    base_unsigned = {
        key: value for key, value in base.items() if key not in {"receipt_hash", "file_hashes"}
    }
    _require(
        isinstance(base_claimed, str)
        and _sha256_hex(_canonical_json(base_unsigned)) == base_claimed,
        "base fourteen-check receipt hash mismatch",
    )
    expected_chain_hash = file_hashes.get(str(chain_path))
    _require(isinstance(expected_chain_hash, str), "partition absent from base audit file hashes")
    actual_chain_hash = _sha256_file(chain_path)
    _require(actual_chain_hash == expected_chain_hash, "partition bytes changed after full audit")

    identity = base.get("source_identity")
    _require(isinstance(identity, dict), "base audit source identity missing")
    _require(identity.get("dirty") is False, "base audit used dirty source code")
    source_paths = identity.get("source_paths")
    source_hashes = identity.get("source_hashes")
    _require(
        isinstance(source_paths, list)
        and source_paths
        and isinstance(source_hashes, dict)
        and set(source_paths) == set(source_hashes),
        "base audit source hashes missing or incomplete",
    )
    repo_root = Path(__file__).resolve().parents[1]
    for relative in source_paths:
        _require(isinstance(relative, str), "base audit source path is not text")
        current = repo_root / relative
        _require(current.is_file(), f"audited source path missing: {relative}")
        _require(
            _sha256_file(current) == source_hashes[relative],
            f"audited source changed: {relative}",
        )
    return {
        "path": str(receipt_path.resolve()),
        "receipt_hash": claimed_receipt,
        "verdict": report["verdict"],
        "partition_sha256": actual_chain_hash,
    }


def chain_schema_metadata(columns: Iterable[object]) -> ChainSchemaMetadata:
    """Classify a complete v1 or v2 partition without reading row values."""
    available = {str(column) for column in columns}
    missing_v1 = [column for column in CHAIN_COLUMNS_V1 if column not in available]
    if missing_v1:
        raise ValueError(f"chain partition missing required v1 column(s): {missing_v1}")

    present_v2 = [column for column in CHAIN_V2_CAPTURE_FIELDS if column in available]
    if not present_v2:
        return ChainSchemaMetadata(
            schema_version=CHAIN_SCHEMA_VERSION_V1,
            usage=DISPLAY_ONLY,
        )

    missing_v2 = [column for column in CHAIN_V2_CAPTURE_FIELDS if column not in available]
    if missing_v2:
        raise ValueError(
            f"chain partition has partial v2 metadata; missing column(s): {missing_v2}"
        )
    return ChainSchemaMetadata(
        schema_version=CHAIN_SCHEMA_VERSION_V2,
        usage=VERDICT_ELIGIBLE,
    )


def expected_usage(schema_version: int) -> str:
    if schema_version == CHAIN_SCHEMA_VERSION_V1:
        return DISPLAY_ONLY
    if schema_version == CHAIN_SCHEMA_VERSION_V2:
        return VERDICT_ELIGIBLE
    raise ValueError(f"unsupported chain schema_version={schema_version}")
