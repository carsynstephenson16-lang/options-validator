"""Provider-neutral capture contracts and shared timing.

Acquisition lives behind this interface. Nothing in the display path imports
this module's providers, and no function here is called during rendering.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Protocol

from data.short_positioning.models import ShortInterestRecordV1

# How far past a publication date to look for the next exchange session before
# giving up. A fortnight comfortably clears any XNYS holiday cluster.
_SESSION_SEARCH_DAYS = 15

# Providers this repository knows about but has no rights to read. Naming a
# blocked provider is a licensing refusal, not an operator typo.
LICENSE_BLOCKED_PROVIDERS = frozenset({"sp_global", "sp-global", "spglobal", "nasdaq"})


class CaptureInputError(ValueError):
    """Operator input or local validation failure. CLI exit 2."""


class CredentialError(RuntimeError):
    """Credential or authentication failure. CLI exit 3."""


class ProviderUnavailableError(RuntimeError):
    """Provider unavailable or retries exhausted. CLI exit 4."""


class ArtifactIntegrityError(RuntimeError):
    """Atomic-write or hash failure. CLI exit 6."""


class PartialCaptureError(RuntimeError):
    """Publication partition incomplete and rolled back. CLI exit 7."""


class LicenseBlockedError(RuntimeError):
    """Rights or entitlement missing. CLI exit 8."""


@dataclass(frozen=True, slots=True)
class CaptureRequest:
    provider: str
    dataset: str
    publication_date: date
    symbols: tuple[str, ...]
    output_root: Path
    source_data_version: str
    request_id: str
    execute: bool = False
    # Set only when an operator observed a release later than schedule.
    observed_release_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.provider or not self.dataset:
            raise CaptureInputError("provider and dataset are required")
        if not self.symbols:
            raise CaptureInputError("at least one symbol is required")
        if any(symbol != symbol.upper() or not symbol for symbol in self.symbols):
            raise CaptureInputError(f"symbols must be non-empty and uppercase: {self.symbols}")
        if not isinstance(self.publication_date, date):
            raise CaptureInputError("publication_date must be a date")
        if not self.request_id:
            raise CaptureInputError("request_id is required")


@dataclass(frozen=True, slots=True)
class CapturePlan:
    """A fully described request that has not been sent.

    A plan may legitimately describe a future publication date so an operator
    can dry-run before a release. That pre-release exception stops here: it
    never reaches a normalized record, whose causality is enforced separately.
    """

    request: CaptureRequest
    url: str
    query: tuple[tuple[str, str], ...]
    credential_env_names: tuple[str, ...]
    raw_partition: Path
    normalized_partition: Path
    dry_run: bool


@dataclass(frozen=True, slots=True)
class RawArtifact:
    path: Path
    sha256: str
    byte_count: int
    retrieved_at: datetime
    request_id: str


@dataclass(frozen=True, slots=True)
class RawCaptureResult:
    dry_run: bool
    status: str
    payload: bytes | None
    artifact: RawArtifact | None
    attempts: int


class ShortInterestProvider(Protocol):
    """What a short-interest source must offer to be capturable."""

    provider: str
    dataset: str

    def build_plan(self, request: CaptureRequest) -> CapturePlan: ...

    def fetch(
        self,
        plan: CapturePlan,
        *,
        transport: object | None = ...,
        sleep: object = ...,
    ) -> RawCaptureResult: ...

    def parse(
        self,
        payload: bytes,
        *,
        request: CaptureRequest,
        retrieved_at: datetime,
        raw_sha256: str,
    ) -> tuple[ShortInterestRecordV1, ...]: ...


def next_available_session(publication_date: date) -> date:
    """First XNYS session strictly after ``publication_date``.

    Both defined release times (16:40 ET and the 23:59:59 ET conservative
    fallback) land after the regular close, so a report published on a session
    first enters an end-of-day information set on the following session. The
    exchange calendar decides; weekday arithmetic never does.
    """
    from data.cache_runner import trading_days

    start = publication_date + timedelta(days=1)
    end = publication_date + timedelta(days=_SESSION_SEARCH_DAYS)
    sessions = trading_days(start.isoformat(), end.isoformat())
    if not sessions:
        raise CaptureInputError(
            f"no XNYS session within {_SESSION_SEARCH_DAYS} days after {publication_date}"
        )
    return date.fromisoformat(sessions[0])
