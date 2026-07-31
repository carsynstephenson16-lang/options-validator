"""Canonical schema metadata for ThetaData EOD chain-cache partitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

CHAIN_SCHEMA_VERSION_V1 = 1
CHAIN_SCHEMA_VERSION_V2 = 2

DISPLAY_ONLY = "display-only"
VERDICT_ELIGIBLE = "verdict-eligible"

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
