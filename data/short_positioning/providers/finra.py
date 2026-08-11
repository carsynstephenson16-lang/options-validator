"""FINRA Consolidated Short Interest adapter.

Official documentation (retrieved 2026-08-11): https://developer.finra.org/docs
Group ``otcMarket``, dataset ``consolidatedShortInterest``. FINRA states the
data "is available via the dataset by 4:40 PM ET on the publication date".

Strict normalization: an unknown source field, an undocumented flag value, or
a reconciliation mismatch fails closed rather than guessing.
"""

from __future__ import annotations

import json
import time as time_module
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Callable
from zoneinfo import ZoneInfo

from data.short_positioning.models import (
    ShortInterestRecordV1,
    ShortPositioningSchemaError,
    SourceProvenanceV1,
    build_source_record_key,
    validate_short_interest_record,
)
from data.short_positioning.provider import (
    CaptureInputError,
    CapturePlan,
    CaptureRequest,
    CredentialError,
    ProviderUnavailableError,
    RawCaptureResult,
    next_available_session,
)

FINRA_GROUP = "otcMarket"
FINRA_DATASET = "consolidatedShortInterest"
FINRA_DATASET_SLUG = "consolidated-short-interest"
FINRA_BASE_URL = "https://api.finra.org/data/group/{group}/name/{dataset}"
FINRA_SOURCE_DOCUMENT = "https://developer.finra.org/docs"
FINRA_FIELD_MAP_VERSION = "finra-consolidated-short-interest/v1"
FINRA_TIMEZONE = "America/New_York"

# Official-source: "available via the dataset by 4:40 PM ET on the publication
# date" (developer.finra.org/docs, retrieved 2026-08-11).
FINRA_RELEASE_LOCAL_TIME = time(16, 40)

# Names only. A value is never logged, echoed, or written to a receipt.
FINRA_CREDENTIAL_ENV_NAMES = ("FINRA_API_CLIENT_ID", "FINRA_API_CLIENT_SECRET")

FINRA_KNOWN_FIELDS = frozenset(
    {
        "accountingYearMonthNumber",
        "averageDailyVolumeQuantity",
        "changePercent",
        "changePreviousNumber",
        "currentShortPositionQuantity",
        "daysToCoverQuantity",
        "issueName",
        "issuerServicesGroupExchangeCode",
        "marketClassCode",
        "previousShortPositionQuantity",
        "revisionFlag",
        "settlementDate",
        "stockSplitFlag",
        "symbolCode",
    }
)

# Core destinations only. changePercent is reconciliation input,
# issuerServicesGroupExchangeCode is provenance, and
# accountingYearMonthNumber is a raw-only cross-check.
FINRA_FIELD_MAP = {
    "issueName": "issue_name",
    "symbolCode": "symbol",
    "marketClassCode": "market",
    "settlementDate": "settlement_date",
    "currentShortPositionQuantity": "current_short_shares",
    "previousShortPositionQuantity": "previous_short_shares",
    "changePreviousNumber": "change_shares",
    "averageDailyVolumeQuantity": "average_daily_volume_shares",
    "daysToCoverQuantity": "days_to_cover",
    "stockSplitFlag": "stock_split_flag",
    "revisionFlag": "revision_flag",
}

# Inference, not official: FINRA documents these flags as nullable but
# publishes no value dictionary. Only this explicit pair is accepted; null
# stays None and anything else fails closed.
FINRA_FLAG_VALUES = {"Y": True, "N": False}

# LLM-proposed 2026-08-11: FINRA publishes changePercent rounded, so exact
# equality would reject sound rows. Reconciliation only; not owner-ratified.
FINRA_CHANGE_PERCENT_TOLERANCE = Decimal("0.01")

# LLM-proposed 2026-08-11 transport conventions; not owner-ratified.
FINRA_MAX_ATTEMPTS = 4
FINRA_BACKOFF_BASE_SECONDS = 1.0
FINRA_REQUEST_TIMEOUT_SECONDS = 30.0
_RETRYABLE_STATUSES = frozenset({429})

Transport = Callable[..., tuple[int, dict, bytes]]


def finra_available_at(
    publication_date: date, *, observed_release_at: datetime | None = None
) -> datetime:
    """Publication date at 16:40 America/New_York, expressed in UTC.

    A late release is recorded at the timestamp it was actually observed. An
    observation earlier than the scheduled release never moves availability
    backwards, so a late release can never be backdated to its schedule.
    """
    local = datetime.combine(
        publication_date, FINRA_RELEASE_LOCAL_TIME, tzinfo=ZoneInfo(FINRA_TIMEZONE)
    )
    scheduled = local.astimezone(ZoneInfo("UTC"))
    if observed_release_at is None:
        return scheduled
    return max(scheduled, observed_release_at.astimezone(ZoneInfo("UTC")))


def build_finra_request(request: CaptureRequest) -> CapturePlan:
    """Describe the request without sending it."""
    if request.dataset != FINRA_DATASET_SLUG:
        raise CaptureInputError(
            f"the FINRA adapter serves {FINRA_DATASET_SLUG!r}, not {request.dataset!r}"
        )
    url = FINRA_BASE_URL.format(group=FINRA_GROUP, dataset=FINRA_DATASET)
    query = (
        ("dataVersion", request.source_data_version),
        ("settlementDatePublished", request.publication_date.isoformat()),
        ("symbols", ",".join(request.symbols)),
    )
    root = request.output_root
    return CapturePlan(
        request=request,
        url=url,
        query=query,
        credential_env_names=FINRA_CREDENTIAL_ENV_NAMES,
        raw_partition=_partition(root, "raw", request),
        normalized_partition=_partition(root, "normalized", request),
        dry_run=not request.execute,
    )


def _partition(root, kind: str, request: CaptureRequest):
    return (
        root
        / kind
        / f"provider={request.provider}"
        / f"dataset={request.dataset}"
        / f"publication_date={request.publication_date.isoformat()}"
    )


def parse_finra_payload(payload: bytes) -> list[dict]:
    """Decode a FINRA JSON payload under strict field control."""
    try:
        decoded = json.loads(payload.decode("utf-8"), parse_float=Decimal)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ShortPositioningSchemaError(f"payload is not decodable JSON: {exc}") from exc
    if not isinstance(decoded, list):
        raise ShortPositioningSchemaError("FINRA payload must be a JSON array of rows")

    rows: list[dict] = []
    for ordinal, row in enumerate(decoded):
        if not isinstance(row, dict):
            raise ShortPositioningSchemaError(f"row {ordinal} is not a JSON object")
        unknown = sorted(set(row) - FINRA_KNOWN_FIELDS)
        if unknown:
            raise ShortPositioningSchemaError(
                f"row {ordinal} carries undocumented source fields {unknown}; "
                "the field map version must be reviewed before capture"
            )
        rows.append(row)
    return rows


def _optional_int(value: object, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ShortPositioningSchemaError(f"{field} must be an integer share count, got {value!r}")
    return value


def _optional_decimal(value: object, field: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool) or not isinstance(value, int):
        raise ShortPositioningSchemaError(f"{field} must be numeric, got {value!r}")
    return Decimal(value)


def _flag(value: object, field: str) -> bool | None:
    if value is None:
        return None
    if value not in FINRA_FLAG_VALUES:
        raise ShortPositioningSchemaError(
            f"{field} value {value!r} is not a documented flag; null is preserved, "
            "unknown values fail closed"
        )
    return FINRA_FLAG_VALUES[str(value)]


def _reconcile_change_percent(reported: Decimal | None, current: int, previous: int | None) -> None:
    if reported is None or previous in (None, 0):
        return
    assert previous is not None
    derived = Decimal(100) * (Decimal(current - previous) / Decimal(previous))
    if abs(derived - reported) > FINRA_CHANGE_PERCENT_TOLERANCE:
        raise ShortPositioningSchemaError(
            f"changePercent {reported} disagrees with the derived {derived} beyond the "
            f"{FINRA_CHANGE_PERCENT_TOLERANCE} rounding tolerance"
        )


def normalize_finra_row(
    row: dict,
    *,
    request: CaptureRequest,
    retrieved_at: datetime,
    row_ordinal: int,
    raw_sha256: str,
) -> ShortInterestRecordV1:
    """Map one documented FINRA row onto the normalized v1 record."""
    if request.dataset != FINRA_DATASET_SLUG:
        raise ShortPositioningSchemaError(
            f"{request.dataset!r} is not reported short interest; daily short-sale volume "
            "and other datasets may not be normalized through this adapter"
        )
    unknown = sorted(set(row) - FINRA_KNOWN_FIELDS)
    if unknown:
        raise ShortPositioningSchemaError(f"undocumented source fields {unknown}")

    symbol = row.get("symbolCode")
    if not isinstance(symbol, str) or not symbol.strip():
        raise ShortPositioningSchemaError(f"symbolCode must be a non-empty string, got {symbol!r}")
    symbol = symbol.strip().upper()

    settlement_raw = row.get("settlementDate")
    if not isinstance(settlement_raw, str):
        raise ShortPositioningSchemaError(
            f"settlementDate must be an ISO date, got {settlement_raw!r}"
        )
    try:
        settlement_date = date.fromisoformat(settlement_raw)
    except ValueError as exc:
        raise ShortPositioningSchemaError(f"settlementDate {settlement_raw!r} is not ISO") from exc

    current = _optional_int(row.get("currentShortPositionQuantity"), "currentShortPositionQuantity")
    if current is None:
        raise ShortPositioningSchemaError("currentShortPositionQuantity may not be null")
    previous = _optional_int(
        row.get("previousShortPositionQuantity"), "previousShortPositionQuantity"
    )
    change_shares = _optional_int(row.get("changePreviousNumber"), "changePreviousNumber")
    average_daily_volume = _optional_int(
        row.get("averageDailyVolumeQuantity"), "averageDailyVolumeQuantity"
    )
    try:
        days_to_cover = _optional_decimal(row.get("daysToCoverQuantity"), "daysToCoverQuantity")
    except InvalidOperation as exc:  # pragma: no cover - defensive
        raise ShortPositioningSchemaError("daysToCoverQuantity is not a usable decimal") from exc

    _reconcile_change_percent(
        _optional_decimal(row.get("changePercent"), "changePercent"), current, previous
    )

    accounting = row.get("accountingYearMonthNumber")
    if accounting is not None:
        expected = settlement_date.year * 100 + settlement_date.month
        if accounting != expected:
            raise ShortPositioningSchemaError(
                f"accountingYearMonthNumber {accounting} disagrees with the settlement cycle "
                f"{expected}"
            )

    revision_flag = _flag(row.get("revisionFlag"), "revisionFlag")
    stock_split_flag = _flag(row.get("stockSplitFlag"), "stockSplitFlag")

    market = row.get("marketClassCode")
    issue_name = row.get("issueName")
    available_at = finra_available_at(
        request.publication_date, observed_release_at=request.observed_release_at
    )

    provenance = SourceProvenanceV1(
        schema_version="short-positioning-provenance/v1",
        provider=request.provider,
        dataset=request.dataset,
        source_document=FINRA_SOURCE_DOCUMENT,
        access_method="api",
        source_data_version=request.source_data_version,
        source_release_at=available_at,
        source_timezone=FINRA_TIMEZONE,
        source_field_map_version=FINRA_FIELD_MAP_VERSION,
        source_row_ordinal=row_ordinal,
        request_id=request.request_id,
        raw_sha256=raw_sha256,
        data_classification="public_local_only",
    )

    record = ShortInterestRecordV1(
        schema_version="short-interest-core/v1",
        provider=request.provider,
        dataset=request.dataset,
        source_record_key=build_source_record_key(
            provider=request.provider,
            dataset=request.dataset,
            market=market if isinstance(market, str) else None,
            symbol=symbol,
            settlement_date=settlement_date,
            source_revision="revised" if revision_flag else "original",
        ),
        security_id=None,
        symbol=symbol,
        market=market if isinstance(market, str) else None,
        issue_name=issue_name if isinstance(issue_name, str) else None,
        settlement_date=settlement_date,
        publication_date=request.publication_date,
        available_at=available_at,
        available_session=next_available_session(request.publication_date),
        retrieved_at=retrieved_at,
        current_short_shares=current,
        previous_short_shares=previous,
        change_shares=change_shares,
        average_daily_volume_shares=average_daily_volume,
        days_to_cover=days_to_cover,
        revision_flag=revision_flag,
        stock_split_flag=stock_split_flag,
        raw_sha256=raw_sha256,
        source_provenance=provenance,
    )
    validate_short_interest_record(record)
    return record


def _http_transport(url: str, *, headers: dict, timeout: float) -> tuple[int, dict, bytes]:
    """Real transport. Never exercised by the test suite."""
    import urllib.error
    import urllib.request

    request = urllib.request.Request(url, headers=dict(headers))  # noqa: S310 - https only
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


class FinraConsolidatedShortInterestAdapter:
    """Capture side of the FINRA lane. Display code never imports this."""

    provider = "finra"
    dataset = FINRA_DATASET_SLUG

    def build_plan(self, request: CaptureRequest) -> CapturePlan:
        return build_finra_request(request)

    def fetch(
        self,
        plan: CapturePlan,
        *,
        transport: Transport | None = None,
        sleep: Callable[[float], object] = time_module.sleep,
    ) -> RawCaptureResult:
        """Fetch raw bytes, or return a no-network dry-run result."""
        if plan.dry_run:
            return RawCaptureResult(
                dry_run=True, status="DRY_RUN", payload=None, artifact=None, attempts=0
            )

        send = transport or _http_transport
        url = plan.url
        headers = self._headers()
        last_reason = "no attempt completed"

        for attempt in range(1, FINRA_MAX_ATTEMPTS + 1):
            retry_after: float | None = None
            try:
                status, response_headers, body = send(
                    url, headers=headers, timeout=FINRA_REQUEST_TIMEOUT_SECONDS
                )
            except TimeoutError as exc:
                last_reason = f"timeout: {exc}"
            else:
                if status == 200:
                    return RawCaptureResult(
                        dry_run=False,
                        status="FETCHED",
                        payload=body,
                        artifact=None,
                        attempts=attempt,
                    )
                if status in (401, 403):
                    raise CredentialError(
                        f"provider refused the request with HTTP {status}; check the "
                        f"credentials named {', '.join(plan.credential_env_names)}"
                    )
                if status == 400:
                    raise CaptureInputError("provider rejected the request with HTTP 400")
                if status in _RETRYABLE_STATUSES or 500 <= status < 600:
                    last_reason = f"HTTP {status}"
                    retry_after = _retry_after_seconds(response_headers)
                else:
                    raise ProviderUnavailableError(f"unexpected provider status HTTP {status}")

            if attempt == FINRA_MAX_ATTEMPTS:
                break
            delay = (
                retry_after
                if retry_after is not None
                else FINRA_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
            )
            sleep(delay)

        raise ProviderUnavailableError(
            f"exhausted {FINRA_MAX_ATTEMPTS} attempts; last reason: {last_reason}"
        )

    def parse(
        self,
        payload: bytes,
        *,
        request: CaptureRequest,
        retrieved_at: datetime,
        raw_sha256: str,
    ) -> tuple[ShortInterestRecordV1, ...]:
        wanted = set(request.symbols)
        records = []
        for ordinal, row in enumerate(parse_finra_payload(payload)):
            record = normalize_finra_row(
                row,
                request=request,
                retrieved_at=retrieved_at,
                row_ordinal=ordinal,
                raw_sha256=raw_sha256,
            )
            if record.symbol in wanted:
                records.append(record)
        return tuple(records)

    def _headers(self) -> dict:
        import os

        headers = {"Accept": "application/json"}
        client_id = os.environ.get(FINRA_CREDENTIAL_ENV_NAMES[0])
        client_secret = os.environ.get(FINRA_CREDENTIAL_ENV_NAMES[1])
        if client_id and client_secret:
            import base64

            token = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            headers["Authorization"] = f"Basic {token}"
        return headers


def _retry_after_seconds(headers: dict) -> float | None:
    for key, value in (headers or {}).items():
        if str(key).lower() == "retry-after":
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None
