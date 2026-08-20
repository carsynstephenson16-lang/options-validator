"""Fail-closed production and verification for attractiveness research artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Final
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from data.atomic_io import atomic_text_write
from options_researcher.top3_context import (
    AnnotationValidationError,
    normalize_research_annotations,
)
from research.hashing import canonical_json

SCHEMA_VERSION: Final = "attractiveness_research/v2"
RITUAL_STATUS_SCHEMA_VERSION: Final = "daily_ritual/run_status/v1"
NEW_YORK: Final = ZoneInfo("America/New_York")
SUCCESSFUL_RITUAL_STATUSES: Final = frozenset({"CAPTURED", "NO_SIGNAL"})
RITUAL_HYPOTHESES: Final = ("H5", "H6", "H7", "H8", "H10")
# Brief 18 owner ruling (2026-08-20): excuse chain-starved lanes only on OK_STARVED days.
CHAIN_STARVED_HYPOTHESES: Final = frozenset({"H6", "H7", "H8"})
PRIMARY_SOURCE_TIERS: Final = frozenset({"issuer_ir", "sec_filing", "regulator", "market_operator"})
SOURCE_TIERS: Final = PRIMARY_SOURCE_TIERS | frozenset({"secondary"})
PJM_SYMBOLS: Final = ("VST", "CEG")
PJM_CATALYST_ID: Final = "PJM_BRA_NEXT"
DASHBOARD_STALE_MARKERS: Final = (
    "annotations are from",
    "do not match any card",
    "Research evidence incomplete",
    "Research evidence stale",
)
# Core fields are required. The five below are the cross-project research
# source standard's remaining receipt fields (docs/evidence-upgrade/
# 2026-08-03-cross-project-source-standard.md §2), added as OPTIONAL so a
# bundle may carry a full receipt without breaking any existing source dict.
# `source_tier` already plays the standard's `source_class` role and is left
# untouched.
SOURCE_FIELDS: Final = frozenset(
    {
        "url",
        "source_tier",
        "published_at",
        "publication_time_unknown_rationale",
        "retrieved_at_utc",
        "final_url",
        "publisher",
        "fetched_via",
        "capture_sha256",
        "independence_group",
    }
)
BANNED_HOST_FRAGMENTS: Final = (
    "reddit.",
    "youtube.",
    "youtu.be",
    "seekingalpha.",
    "medium.",
    "substack.",
    "wordpress.",
    "blogspot.",
    "stocktwits.",
    "fool.",
)


class ResearchArtifactError(ValueError):
    """A stable refusal for incomplete or unverifiable research artifacts."""


class UpstreamBlocked(ResearchArtifactError):
    """The exact-session daily ritual did not complete successfully."""


@dataclass(frozen=True)
class RitualBinding:
    run_status_path: str
    run_status_sha256: str
    ritual_code_sha: str
    receipt_path: str
    receipt_sha256: str
    as_of: str
    run_date: str
    evidence_sha256: dict[str, str]

    def as_dict(self) -> dict[str, object]:
        return {
            "run_status_path": self.run_status_path,
            "run_status_sha256": self.run_status_sha256,
            "ritual_code_sha": self.ritual_code_sha,
            "receipt_path": self.receipt_path,
            "receipt_sha256": self.receipt_sha256,
            "as_of": self.as_of,
            "run_date": self.run_date,
            "evidence_sha256": dict(sorted(self.evidence_sha256.items())),
        }


@dataclass(frozen=True)
class PublicationResult:
    status: str
    run_id: str
    context_path: Path
    report_path: Path
    manifest_path: Path
    context_sha256: str


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def _require_date(value: object, *, where: str) -> str:
    if not isinstance(value, str):
        raise ResearchArtifactError(f"{where}: expected ISO date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise ResearchArtifactError(f"{where}: invalid ISO date {value!r}") from error


def _parse_timestamp(value: object, *, where: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ResearchArtifactError(f"{where}: missing timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ResearchArtifactError(f"{where}: invalid timestamp {value!r}") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ResearchArtifactError(f"{where}: timestamp must be timezone-aware")
    return parsed


def _utc_timestamp(value: object, *, where: str) -> datetime:
    parsed = _parse_timestamp(value, where=where)
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ResearchArtifactError(f"{where}: timestamp must be UTC")
    return parsed.astimezone(timezone.utc)


def _time_fields(started_at: datetime, finished_at: datetime) -> dict[str, str]:
    if started_at.tzinfo is None or started_at.utcoffset() is None:
        raise ResearchArtifactError("started_at must be timezone-aware")
    if finished_at.tzinfo is None or finished_at.utcoffset() is None:
        raise ResearchArtifactError("finished_at must be timezone-aware")
    started_utc = started_at.astimezone(timezone.utc)
    finished_utc = finished_at.astimezone(timezone.utc)
    if finished_utc <= started_utc:
        raise ResearchArtifactError("research finish must be after research start")
    return {
        "research_started_at_utc": started_utc.isoformat().replace("+00:00", "Z"),
        "research_started_at_et": started_at.astimezone(NEW_YORK).isoformat(),
        "research_finished_at_utc": finished_utc.isoformat().replace("+00:00", "Z"),
        "research_finished_at_et": finished_at.astimezone(NEW_YORK).isoformat(),
    }


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def validate_source_url(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResearchArtifactError(f"{where}: source URL is required")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ResearchArtifactError(f"{where}: invalid source URL")
    host = _host(value)
    if any(fragment in host for fragment in BANNED_HOST_FRAGMENTS):
        raise ResearchArtifactError(f"{where}: banned source host {host}")
    return value


def _optional_nonempty_string(value: object, *, where: str) -> str | None:
    """Validate an OPTIONAL string receipt field: absent stays absent, present must be non-empty."""
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ResearchArtifactError(f"{where}: non-empty string is required when present")
    return value


def validate_capture_sha256(value: object, *, where: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ResearchArtifactError(f"{where}: expected 64 lowercase hex characters")
    return value


def _require_attempt_id(value: object, *, where: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(character.isspace() for character in value)
    ):
        raise ResearchArtifactError(f"{where}: invalid producer attempt id")
    return value


def _clean_sources(
    owner: str,
    value: object,
    *,
    started_at_utc: datetime,
    finished_at_utc: datetime,
) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value:
        raise ResearchArtifactError(f"{owner}.sources: at least one source is required")
    cleaned: list[dict[str, object]] = []
    urls: set[str] = set()
    for index, raw in enumerate(value):
        where = f"{owner}.sources[{index}]"
        if not isinstance(raw, Mapping):
            raise ResearchArtifactError(f"{where}: expected source metadata object")
        unexpected = sorted(str(key) for key in raw if key not in SOURCE_FIELDS)
        if unexpected:
            raise ResearchArtifactError(f"{where}: unexpected field {unexpected[0]}")
        url = validate_source_url(raw.get("url"), where=f"{where}.url")
        if url in urls:
            raise ResearchArtifactError(f"{where}: duplicate URL")
        urls.add(url)
        source_tier = raw.get("source_tier")
        if source_tier not in SOURCE_TIERS:
            raise ResearchArtifactError(f"{where}.source_tier: invalid value")
        published_at = raw.get("published_at")
        unknown_rationale = raw.get("publication_time_unknown_rationale")
        normalized_published: str | None
        if published_at is None:
            if not isinstance(unknown_rationale, str) or not unknown_rationale.strip():
                raise ResearchArtifactError(
                    f"{where}: unknown publication time requires a rationale"
                )
            normalized_published = None
            normalized_rationale: str | None = unknown_rationale.strip()
        else:
            published = _parse_timestamp(published_at, where=f"{where}.published_at")
            normalized_published = published.isoformat()
            if unknown_rationale is not None:
                raise ResearchArtifactError(
                    f"{where}: known publication time cannot carry an unknown rationale"
                )
            normalized_rationale = None
        retrieved = _utc_timestamp(raw.get("retrieved_at_utc"), where=f"{where}.retrieved_at_utc")
        if not started_at_utc <= retrieved <= finished_at_utc:
            raise ResearchArtifactError(
                f"{where}.retrieved_at_utc: outside research start/finish window"
            )
        if published_at is not None:
            published = _parse_timestamp(published_at, where=f"{where}.published_at")
            if published.astimezone(timezone.utc) > retrieved:
                raise ResearchArtifactError(f"{where}.published_at: later than retrieval timestamp")
        final_url = raw.get("final_url")
        normalized_final_url = (
            None
            if final_url is None
            else validate_source_url(final_url, where=f"{where}.final_url")
        )
        publisher = _optional_nonempty_string(raw.get("publisher"), where=f"{where}.publisher")
        fetched_via = _optional_nonempty_string(
            raw.get("fetched_via"), where=f"{where}.fetched_via"
        )
        capture_sha256 = raw.get("capture_sha256")
        normalized_capture_sha256 = (
            None
            if capture_sha256 is None
            else validate_capture_sha256(capture_sha256, where=f"{where}.capture_sha256")
        )
        independence_group = _optional_nonempty_string(
            raw.get("independence_group"), where=f"{where}.independence_group"
        )
        cleaned.append(
            {
                "url": url,
                "source_tier": source_tier,
                "published_at": normalized_published,
                "publication_time_unknown_rationale": normalized_rationale,
                "retrieved_at_utc": retrieved.isoformat().replace("+00:00", "Z"),
                "final_url": normalized_final_url,
                "publisher": publisher,
                "fetched_via": fetched_via,
                "capture_sha256": normalized_capture_sha256,
                "independence_group": independence_group,
            }
        )
    return cleaned


def _source_index(sources: object, *, where: str) -> dict[str, Mapping[str, object]]:
    if not isinstance(sources, list):
        raise ResearchArtifactError(f"{where}: sources are missing")
    indexed: dict[str, Mapping[str, object]] = {}
    for index, source in enumerate(sources):
        if not isinstance(source, Mapping) or not isinstance(source.get("url"), str):
            raise ResearchArtifactError(f"{where}[{index}]: invalid source metadata")
        indexed[str(source["url"])] = source
    return indexed


def _safe_relative_path(value: str, *, where: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ResearchArtifactError(f"{where}: path must stay inside the declared root")
    return path


def _load_object(path: Path, *, where: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ResearchArtifactError(f"{where}: missing {path}") from error
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ResearchArtifactError(f"{where}: unreadable JSON {path}") from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ResearchArtifactError(f"{where}: JSON root must be an object")
    return value


def load_successful_ritual(
    ritual_root: Path,
    *,
    as_of: str,
    run_date: str,
) -> RitualBinding:
    """Bind research to one exact, successful daily-ritual session."""
    expected_as_of = _require_date(as_of, where="ritual.as_of")
    expected_run_date = _require_date(run_date, where="ritual.run_date")
    relative_receipt = Path("reports/ritual") / f"capture_receipt_{expected_as_of}.json"
    relative_status = Path("reports/ritual") / f"run_status_{expected_as_of}.json"
    receipt_path = ritual_root / relative_receipt
    status_path = ritual_root / relative_status
    try:
        status = _load_object(status_path, where="ritual run status")
    except ResearchArtifactError as error:
        raise UpstreamBlocked(str(error)) from error
    if status.get("schema_version") != RITUAL_STATUS_SCHEMA_VERSION:
        raise UpstreamBlocked("ritual run status schema_version is not daily_ritual/run_status/v1")
    if status.get("as_of") != expected_as_of:
        raise UpstreamBlocked(
            f"ritual run status session mismatch: expected {expected_as_of}, "
            f"got {status.get('as_of')!r}"
        )
    if status.get("run_date") != expected_run_date:
        raise UpstreamBlocked(
            f"ritual run status run_date mismatch: expected {expected_run_date}, "
            f"got {status.get('run_date')!r}"
        )
    run_status = status.get("status")
    if run_status not in {"OK", "OK_STARVED"}:
        raise UpstreamBlocked(f"ritual run status is not OK: {run_status!r}")
    ritual_code_sha = status.get("code_sha")
    if (
        not isinstance(ritual_code_sha, str)
        or len(ritual_code_sha) != 40
        or any(character not in "0123456789abcdef" for character in ritual_code_sha)
    ):
        raise UpstreamBlocked("ritual run status code_sha is not a full Git SHA")
    if status.get("capture_receipt_path") != relative_receipt.as_posix():
        raise UpstreamBlocked("ritual run status capture_receipt_path mismatch")

    try:
        receipt = _load_object(receipt_path, where="ritual receipt")
    except ResearchArtifactError as error:
        raise UpstreamBlocked(str(error)) from error
    receipt_sha = _sha256_file(receipt_path)
    if status.get("capture_receipt_sha256") != receipt_sha:
        raise UpstreamBlocked("ritual run status capture_receipt_sha256 mismatch")

    if receipt.get("as_of") != expected_as_of:
        raise UpstreamBlocked(
            f"ritual receipt session mismatch: expected {expected_as_of}, "
            f"got {receipt.get('as_of')!r}"
        )
    if receipt.get("run_date") != expected_run_date:
        raise UpstreamBlocked(
            f"ritual receipt run_date mismatch: expected {expected_run_date}, "
            f"got {receipt.get('run_date')!r}"
        )
    hypotheses = receipt.get("hypotheses")
    if not isinstance(hypotheses, dict):
        raise UpstreamBlocked("ritual receipt hypotheses are missing")

    evidence_hashes: dict[str, str] = {}
    for hypothesis in RITUAL_HYPOTHESES:
        if run_status == "OK_STARVED" and hypothesis in CHAIN_STARVED_HYPOTHESES:
            continue
        result = hypotheses.get(hypothesis)
        if not isinstance(result, dict):
            raise UpstreamBlocked(f"ritual receipt missing {hypothesis}")
        status = result.get("status")
        if status not in SUCCESSFUL_RITUAL_STATUSES:
            detail = result.get("detail")
            raise UpstreamBlocked(
                f"{hypothesis} status {status!r} is not successful"
                + (f": {detail}" if isinstance(detail, str) and detail else "")
            )
        evidence = result.get("evidence")
        if not isinstance(evidence, str) or not evidence:
            raise UpstreamBlocked(f"{hypothesis} successful status has no evidence path")
        try:
            evidence_relative = _safe_relative_path(evidence, where=f"{hypothesis} evidence")
        except ResearchArtifactError as error:
            raise UpstreamBlocked(str(error)) from error
        evidence_path = ritual_root / evidence_relative
        if not evidence_path.is_file():
            raise UpstreamBlocked(f"{hypothesis} evidence is missing: {evidence}")
        evidence_hashes[hypothesis] = _sha256_file(evidence_path)

    return RitualBinding(
        run_status_path=relative_status.as_posix(),
        run_status_sha256=_sha256_file(status_path),
        ritual_code_sha=ritual_code_sha,
        receipt_path=relative_receipt.as_posix(),
        receipt_sha256=receipt_sha,
        as_of=expected_as_of,
        run_date=expected_run_date,
        evidence_sha256=evidence_hashes,
    )


def load_input_packets(inputs_dir: Path) -> tuple[dict[str, object], dict[str, bytes]]:
    """Load researcher packets while retaining their exact bytes for lineage."""
    if not inputs_dir.is_dir():
        raise ResearchArtifactError(f"input packet directory is missing: {inputs_dir}")
    packet_bytes = {
        path.name: path.read_bytes() for path in sorted(inputs_dir.glob("*.json")) if path.is_file()
    }
    if "market.json" not in packet_bytes:
        raise ResearchArtifactError("input packets: market.json is required")

    packets: dict[str, dict[str, object]] = {}
    for name, raw in packet_bytes.items():
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ResearchArtifactError(f"input packet {name}: invalid JSON") from error
        if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
            raise ResearchArtifactError(f"input packet {name}: root must be an object")
        packets[name] = value

    symbol_research: dict[str, dict[str, object]] = {}
    for name, packet in packets.items():
        if name == "market.json":
            continue
        symbol = packet.get("symbol")
        if not isinstance(symbol, str) or not symbol:
            raise ResearchArtifactError(f"input packet {name}: symbol is required")
        expected_name = f"{symbol.lower()}.json"
        if name != expected_name:
            raise ResearchArtifactError(f"input packet {name}: expected filename {expected_name}")
        if symbol in symbol_research:
            raise ResearchArtifactError(f"input packets: duplicate symbol {symbol}")
        symbol_research[symbol] = packet

    return {
        "market": packets["market.json"],
        "symbol_research": symbol_research,
    }, packet_bytes


def required_symbols(candidate_ids: Sequence[str], pinned_symbols: Sequence[str]) -> list[str]:
    symbols: set[str] = set(PJM_SYMBOLS)
    for index, candidate_id in enumerate(candidate_ids):
        if not isinstance(candidate_id, str) or ":" not in candidate_id:
            raise ResearchArtifactError(f"candidate_ids[{index}]: invalid candidate id")
        symbols.add(candidate_id.split(":", 1)[0])
    for index, symbol in enumerate(pinned_symbols):
        if not isinstance(symbol, str) or not symbol:
            raise ResearchArtifactError(f"pinned_symbols[{index}]: invalid symbol")
        symbols.add(symbol)
    return sorted(symbols)


def _clean_claims(symbol: str, claims: object) -> list[dict[str, object]]:
    if not isinstance(claims, list) or not claims:
        raise ResearchArtifactError(f"{symbol}.claims: at least one claim is required")
    cleaned: list[dict[str, object]] = []
    fields = (
        "id",
        "text",
        "classification",
        "source_url",
        "unknown_rationale",
        "source_tier",
        "fact_date",
        "date_certainty",
        "countercase",
    )
    primary_count = 0
    for index, value in enumerate(claims):
        if not isinstance(value, Mapping):
            raise ResearchArtifactError(f"{symbol}.claims[{index}]: expected object")
        claim: dict[str, object] = {}
        for field in fields:
            claim[field] = value.get(field)
        source_url = claim.get("source_url")
        source_tier = claim.get("source_tier")
        if source_url is not None:
            validate_source_url(source_url, where=f"{symbol}.claims[{index}].source_url")
        if source_url is not None and source_tier in PRIMARY_SOURCE_TIERS:
            primary_count += 1
        cleaned.append(claim)
    if primary_count == 0:
        raise ResearchArtifactError(
            f"{symbol}.claims: at least one primary-source claim is required"
        )
    return cleaned


def _clean_blurb(
    symbol: str,
    value: object,
    *,
    started_at_utc: datetime,
    finished_at_utc: datetime,
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ResearchArtifactError(f"{symbol}: symbol research must be an object")
    fields = ("news_summary", "sentiment", "catalysts", "move_thesis", "sources")
    blurb: dict[str, object] = {}
    for field in fields:
        blurb[field] = value.get(field)
    if not isinstance(blurb["news_summary"], str) or not blurb["news_summary"].strip():
        raise ResearchArtifactError(f"{symbol}.news_summary: non-empty text is required")
    if blurb["sentiment"] not in {"bull", "bear", "neutral"}:
        raise ResearchArtifactError(f"{symbol}.sentiment: invalid value")
    if not isinstance(blurb["move_thesis"], str) or not blurb["move_thesis"].strip():
        raise ResearchArtifactError(f"{symbol}.move_thesis: non-empty text is required")
    sources = _clean_sources(
        symbol,
        blurb.get("sources"),
        started_at_utc=started_at_utc,
        finished_at_utc=finished_at_utc,
    )
    blurb["sources"] = sources
    source_index = _source_index(sources, where=f"{symbol}.sources")
    catalysts = blurb.get("catalysts")
    if not isinstance(catalysts, list):
        raise ResearchArtifactError(f"{symbol}.catalysts: expected list")
    for index, catalyst in enumerate(catalysts):
        if not isinstance(catalyst, Mapping):
            raise ResearchArtifactError(f"{symbol}.catalysts[{index}]: expected object")
        source = validate_source_url(
            catalyst.get("source"), where=f"{symbol}.catalysts[{index}].source"
        )
        if source not in source_index:
            raise ResearchArtifactError(
                f"{symbol}.catalysts[{index}]: source is absent from symbol sources"
            )
        confirmed = catalyst.get("confirmed")
        if not isinstance(confirmed, bool):
            raise ResearchArtifactError(f"{symbol}.catalysts[{index}].confirmed: expected boolean")
        catalyst_date = catalyst.get("date")
        if not isinstance(catalyst.get("what"), str) or not catalyst["what"].strip():
            raise ResearchArtifactError(
                f"{symbol}.catalysts[{index}].what: non-empty text is required"
            )
        if confirmed:
            _require_date(catalyst_date, where=f"{symbol}.catalysts[{index}].date")
            if source_index[source].get("source_tier") not in PRIMARY_SOURCE_TIERS:
                raise ResearchArtifactError(
                    f"{symbol}.catalysts[{index}]: confirmed catalyst requires primary source"
                )
        elif catalyst_date is not None:
            _require_date(catalyst_date, where=f"{symbol}.catalysts[{index}].date")
    return blurb


def _validate_pjm(symbol: str, blurb: Mapping[str, object]) -> None:
    catalysts = blurb.get("catalysts")
    assert isinstance(catalysts, list)
    matches = [
        catalyst
        for catalyst in catalysts
        if isinstance(catalyst, Mapping) and catalyst.get("id") == PJM_CATALYST_ID
    ]
    if len(matches) != 1:
        raise ResearchArtifactError(
            f"{symbol}.catalysts: exactly one {PJM_CATALYST_ID} entry is required"
        )
    catalyst = matches[0]
    if catalyst.get("confirmed") is not False:
        raise ResearchArtifactError(f"{symbol}.{PJM_CATALYST_ID}: confirmed must remain false")
    source = validate_source_url(catalyst.get("source"), where=f"{symbol}.{PJM_CATALYST_ID}.source")
    host = _host(source)
    if host != "pjm.com" and not host.endswith(".pjm.com"):
        raise ResearchArtifactError(
            f"{symbol}.{PJM_CATALYST_ID}: source must be an official PJM URL"
        )
    sources = _source_index(blurb.get("sources"), where=f"{symbol}.sources")
    if sources[source].get("source_tier") != "market_operator":
        raise ResearchArtifactError(
            f"{symbol}.{PJM_CATALYST_ID}: source_tier must be market_operator"
        )


def build_context(
    *,
    as_of: str,
    candidate_ids: Sequence[str],
    pinned_symbols: Sequence[str],
    inputs: Mapping[str, object],
    started_at: datetime,
    finished_at: datetime,
    run_id: str,
    producer_attempt_id: str,
    ritual_binding: RitualBinding,
    input_packet_sha256: Mapping[str, str],
    uv_lock_sha256: str,
) -> dict[str, object]:
    """Build a fully covered v2 context without changing candidate membership."""
    market_as_of = _require_date(as_of, where="market_as_of_date")
    attempt_id = _require_attempt_id(
        producer_attempt_id,
        where="producer_attempt_id",
    )
    time_fields = _time_fields(started_at, finished_at)
    started_utc = _utc_timestamp(
        time_fields["research_started_at_utc"], where="research_started_at_utc"
    )
    finished_utc = _utc_timestamp(
        time_fields["research_finished_at_utc"], where="research_finished_at_utc"
    )
    finished_utc_text = time_fields["research_finished_at_utc"]

    market_packet = inputs.get("market")
    symbol_packets = inputs.get("symbol_research")
    if not isinstance(market_packet, Mapping):
        raise ResearchArtifactError("market input packet is missing")
    if not isinstance(symbol_packets, Mapping):
        raise ResearchArtifactError("symbol research packets are missing")

    annotations: dict[str, dict[str, object]] = {}
    for candidate_id in candidate_ids:
        symbol = candidate_id.split(":", 1)[0]
        packet = symbol_packets.get(symbol)
        if not isinstance(packet, Mapping):
            raise ResearchArtifactError(
                f"candidate coverage missing researcher packet for {symbol}"
            )
        annotations[candidate_id] = {
            "research_as_of_utc": finished_utc_text,
            "market_as_of_date": market_as_of,
            "claims": _clean_claims(symbol, packet.get("claims")),
        }
    try:
        normalize_research_annotations(candidate_ids, annotations)
    except AnnotationValidationError as error:
        raise ResearchArtifactError(f"annotation schema rejection: {error}") from error

    symbols: dict[str, dict[str, object]] = {}
    market_symbols = market_packet.get("symbols")
    if market_symbols is not None and not isinstance(market_symbols, Mapping):
        raise ResearchArtifactError("market.symbols: expected object")
    for symbol, packet in symbol_packets.items():
        if not isinstance(symbol, str):
            raise ResearchArtifactError("symbol research key must be a string")
        symbols[symbol] = _clean_blurb(
            symbol,
            packet,
            started_at_utc=started_utc,
            finished_at_utc=finished_utc,
        )
    for symbol, packet in (market_symbols or {}).items():
        if not isinstance(symbol, str):
            raise ResearchArtifactError("market symbol key must be a string")
        if symbol in symbols:
            raise ResearchArtifactError(f"{symbol}: duplicate blurb in market and symbol packet")
        symbols[symbol] = _clean_blurb(
            symbol,
            packet,
            started_at_utc=started_utc,
            finished_at_utc=finished_utc,
        )

    required = required_symbols(candidate_ids, pinned_symbols)
    missing = sorted(set(required) - set(symbols))
    if missing:
        raise ResearchArtifactError(
            "symbol coverage missing required packets: " + ", ".join(missing)
        )
    for symbol in PJM_SYMBOLS:
        _validate_pjm(symbol, symbols[symbol])

    market = market_packet.get("market")
    if not isinstance(market, Mapping):
        raise ResearchArtifactError("market.market: expected object")
    cleaned_market_sources = _clean_sources(
        "market",
        market_packet.get("market_sources"),
        started_at_utc=started_utc,
        finished_at_utc=finished_utc,
    )
    if not isinstance(market.get("summary"), str) or not market["summary"].strip():
        raise ResearchArtifactError("market.summary: non-empty text is required")
    if market.get("regime") not in {"risk_on", "risk_off", "mixed"}:
        raise ResearchArtifactError("market.regime: invalid value")
    notes = market.get("notes")
    if not isinstance(notes, list) or not all(
        isinstance(note, str) and note.strip() for note in notes
    ):
        raise ResearchArtifactError("market.notes: expected non-empty strings")

    for candidate_id in candidate_ids:
        symbol = candidate_id.split(":", 1)[0]
        symbol_sources = _source_index(symbols[symbol].get("sources"), where=f"{symbol}.sources")
        claims = annotations[candidate_id]["claims"]
        assert isinstance(claims, list)
        for index, claim in enumerate(claims):
            source_url = claim.get("source_url")
            if source_url is not None and source_url not in symbol_sources:
                raise ResearchArtifactError(
                    f"{symbol}.claims[{index}]: source is absent from symbol sources"
                )
            if source_url is not None and (
                claim.get("source_tier") != symbol_sources[str(source_url)].get("source_tier")
            ):
                raise ResearchArtifactError(
                    f"{symbol}.claims[{index}]: source_tier differs from source metadata"
                )

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "as_of": market_as_of,
        "market_as_of_date": market_as_of,
        **time_fields,
        "researched_on": finished_at.astimezone(NEW_YORK).date().isoformat(),
        "provenance": (
            "LLM-asserted research; source and lineage validated, factual truth "
            "requires independent critic review"
        ),
        "lineage": {
            "run_id": run_id,
            "producer_attempt_id": attempt_id,
            "ritual_run_status_sha256": ritual_binding.run_status_sha256,
            "ritual_receipt_sha256": ritual_binding.receipt_sha256,
            "input_packet_sha256": dict(sorted(input_packet_sha256.items())),
            "uv_lock_sha256": uv_lock_sha256,
        },
        "candidate_ids": list(candidate_ids),
        "pinned_symbols": list(pinned_symbols),
        "required_symbols": required,
        "market": {key: market.get(key) for key in ("summary", "regime", "notes")},
        "market_sources": cleaned_market_sources,
        "symbols": symbols,
        "annotations": annotations,
    }


def validate_context(
    context: Mapping[str, object],
    *,
    candidate_ids: Sequence[str],
    pinned_symbols: Sequence[str],
) -> None:
    """Validate candidate, temporal, source, and PJM invariants."""
    if context.get("schema_version") != SCHEMA_VERSION:
        raise ResearchArtifactError("context schema_version is not attractiveness_research/v2")
    market_as_of = _require_date(context.get("market_as_of_date"), where="market_as_of_date")
    if context.get("as_of") != market_as_of:
        raise ResearchArtifactError("context as_of and market_as_of_date differ")
    if context.get("candidate_ids") != list(candidate_ids):
        raise ResearchArtifactError("context candidate_ids do not match the live board")
    if context.get("pinned_symbols") != list(pinned_symbols):
        raise ResearchArtifactError("context pinned_symbols do not match the live board")
    expected_required = required_symbols(candidate_ids, pinned_symbols)
    if context.get("required_symbols") != expected_required:
        raise ResearchArtifactError("context required_symbols do not match the live board")

    started_utc = _utc_timestamp(
        context.get("research_started_at_utc"), where="research_started_at_utc"
    )
    started_et = _parse_timestamp(
        context.get("research_started_at_et"), where="research_started_at_et"
    )
    finished_utc = _utc_timestamp(
        context.get("research_finished_at_utc"), where="research_finished_at_utc"
    )
    finished_et = _parse_timestamp(
        context.get("research_finished_at_et"), where="research_finished_at_et"
    )
    for label, utc_value, et_value in (
        ("start", started_utc, started_et),
        ("finish", finished_utc, finished_et),
    ):
        if utc_value.astimezone(timezone.utc) != et_value.astimezone(timezone.utc):
            raise ResearchArtifactError(
                f"UTC and ET research {label} timestamps refer to different instants"
            )
        if et_value.utcoffset() != et_value.astimezone(NEW_YORK).utcoffset():
            raise ResearchArtifactError(
                f"research {label} ET timestamp does not use America/New_York offset"
            )
    if finished_utc <= started_utc:
        raise ResearchArtifactError("research finish must be after research start")
    if finished_et.astimezone(NEW_YORK).date().isoformat() != context.get("researched_on"):
        raise ResearchArtifactError("researched_on does not match the America/New_York date")

    annotations = context.get("annotations")
    if not isinstance(annotations, Mapping):
        raise ResearchArtifactError("context annotations are missing")
    if set(annotations) != set(candidate_ids):
        raise ResearchArtifactError("annotation coverage is not exact for live candidates")
    try:
        normalize_research_annotations(candidate_ids, annotations)
    except AnnotationValidationError as error:
        raise ResearchArtifactError(f"annotation schema rejection: {error}") from error
    for candidate_id, annotation in annotations.items():
        assert isinstance(annotation, Mapping)
        if annotation.get("market_as_of_date") != market_as_of:
            raise ResearchArtifactError(f"{candidate_id}: annotation market_as_of_date mismatch")
        timestamp = _parse_timestamp(
            annotation.get("research_as_of_utc"),
            where=f"{candidate_id}.research_as_of_utc",
        )
        if timestamp.astimezone(timezone.utc) != finished_utc:
            raise ResearchArtifactError(
                f"{candidate_id}: annotation timestamp differs from run timestamp"
            )
        claims = annotation.get("claims")
        assert isinstance(claims, list)
        if not any(
            isinstance(claim, Mapping)
            and claim.get("source_tier") in PRIMARY_SOURCE_TIERS
            and isinstance(claim.get("source_url"), str)
            for claim in claims
        ):
            raise ResearchArtifactError(f"{candidate_id}: no primary-source claim")

    symbols = context.get("symbols")
    if not isinstance(symbols, Mapping):
        raise ResearchArtifactError("context symbols are missing")
    missing = sorted(set(expected_required) - set(symbols))
    if missing:
        raise ResearchArtifactError("context symbol coverage missing: " + ", ".join(missing))
    for symbol in expected_required:
        blurb = _clean_blurb(
            symbol,
            symbols[symbol],
            started_at_utc=started_utc,
            finished_at_utc=finished_utc,
        )
        source_index = _source_index(blurb.get("sources"), where=f"{symbol}.sources")
        for candidate_id, annotation in annotations.items():
            if not str(candidate_id).startswith(f"{symbol}:"):
                continue
            assert isinstance(annotation, Mapping)
            claims = annotation.get("claims")
            assert isinstance(claims, list)
            for index, claim in enumerate(claims):
                assert isinstance(claim, Mapping)
                source_url = claim.get("source_url")
                if source_url is None:
                    continue
                if source_url not in source_index:
                    raise ResearchArtifactError(
                        f"{symbol}.claims[{index}]: source metadata missing"
                    )
                if claim.get("source_tier") != source_index[str(source_url)].get("source_tier"):
                    raise ResearchArtifactError(
                        f"{symbol}.claims[{index}]: source_tier metadata mismatch"
                    )
        if symbol in PJM_SYMBOLS:
            _validate_pjm(symbol, blurb)
    _clean_sources(
        "market",
        context.get("market_sources"),
        started_at_utc=started_utc,
        finished_at_utc=finished_utc,
    )


def _markdown_text(value: object) -> str:
    if value is None:
        return "unknown"
    return str(value).replace("\n", " ").replace("|", "\\|")


def _source_markdown(source: object) -> str:
    assert isinstance(source, Mapping)
    publication = source.get("published_at")
    if publication is None:
        publication = "unknown: " + str(source.get("publication_time_unknown_rationale"))
    return (
        f"{source.get('url')} "
        f"(tier={source.get('source_tier')}; published_at={publication}; "
        f"retrieved_at_utc={source.get('retrieved_at_utc')})"
    )


def render_markdown(context: Mapping[str, object]) -> str:
    """Render a deterministic human report from the machine context."""
    as_of = str(context["market_as_of_date"])
    lines = [
        f"# Attractiveness research context — market as of {as_of}",
        "",
        f"- Schema: `{context['schema_version']}`",
        f"- Run ID: `{context['run_id']}`",
        f"- Research started (ET): `{context['research_started_at_et']}`",
        f"- Research started (UTC): `{context['research_started_at_utc']}`",
        f"- Research finished (ET): `{context['research_finished_at_et']}`",
        f"- Research finished (UTC): `{context['research_finished_at_utc']}`",
        "- Advisory only: this report cannot change candidate membership, ranking, or a trade verdict.",
        "",
        "## Candidate identity",
        "",
    ]
    candidate_ids = context["candidate_ids"]
    assert isinstance(candidate_ids, list)
    for candidate_id in candidate_ids:
        lines.append(f"- `{candidate_id}`")

    market = context["market"]
    assert isinstance(market, Mapping)
    lines.extend(
        [
            "",
            "## Market context",
            "",
            f"- Regime: {_markdown_text(market.get('regime'))}",
            f"- Summary: {_markdown_text(market.get('summary'))}",
        ]
    )
    notes = market.get("notes")
    if isinstance(notes, list):
        for note in notes:
            lines.append(f"- Note: {_markdown_text(note)}")
    market_sources = context["market_sources"]
    assert isinstance(market_sources, list)
    for source in market_sources:
        lines.append(f"- Source: {_source_markdown(source)}")

    symbols = context["symbols"]
    assert isinstance(symbols, Mapping)
    for symbol in sorted(symbols):
        blurb = symbols[symbol]
        assert isinstance(blurb, Mapping)
        lines.extend(
            [
                "",
                f"## {symbol}",
                "",
                f"- Sentiment: {_markdown_text(blurb.get('sentiment'))}",
                f"- News: {_markdown_text(blurb.get('news_summary'))}",
                f"- Move thesis: {_markdown_text(blurb.get('move_thesis'))}",
                "",
                "### Catalysts",
                "",
            ]
        )
        catalysts = blurb.get("catalysts")
        assert isinstance(catalysts, list)
        if not catalysts:
            lines.append("- None asserted.")
        for catalyst in catalysts:
            assert isinstance(catalyst, Mapping)
            catalyst_id = catalyst.get("id")
            prefix = f"`{catalyst_id}` — " if catalyst_id else ""
            lines.append(
                "- "
                f"{prefix}{_markdown_text(catalyst.get('date'))}: "
                f"{_markdown_text(catalyst.get('what'))} "
                f"(confirmed={str(catalyst.get('confirmed')).lower()}; "
                f"source={catalyst.get('source')})"
            )
        lines.extend(["", "### Sources", ""])
        sources = blurb.get("sources")
        assert isinstance(sources, list)
        for source in sources:
            lines.append(f"- {_source_markdown(source)}")

    annotations = context["annotations"]
    assert isinstance(annotations, Mapping)
    lines.extend(["", "## Candidate claims", ""])
    for candidate_id in candidate_ids:
        annotation = annotations[candidate_id]
        assert isinstance(annotation, Mapping)
        lines.extend([f"### `{candidate_id}`", ""])
        claims = annotation.get("claims")
        assert isinstance(claims, list)
        for claim in claims:
            assert isinstance(claim, Mapping)
            lines.extend(
                [
                    f"- Claim `{claim.get('id')}`: {_markdown_text(claim.get('text'))}",
                    (
                        "  - Evidence: "
                        f"{_markdown_text(claim.get('source_tier'))}; "
                        f"{_markdown_text(claim.get('source_url'))}; "
                        f"fact_date={_markdown_text(claim.get('fact_date'))}; "
                        f"date_certainty={_markdown_text(claim.get('date_certainty'))}"
                    ),
                    f"  - Countercase: {_markdown_text(claim.get('countercase'))}",
                ]
            )
    lines.append("")
    return "\n".join(lines)


def collect_manifest_sources(context: Mapping[str, object]) -> list[dict[str, object]]:
    """Return one deterministic manifest row per URL with every usage scope."""
    collected: dict[str, dict[str, object]] = {}

    def add(scope: str, source: object) -> None:
        if not isinstance(source, Mapping) or not isinstance(source.get("url"), str):
            raise ResearchArtifactError(f"{scope}: invalid source metadata")
        url = str(source["url"])
        metadata = {field: source.get(field) for field in sorted(SOURCE_FIELDS)}
        prior = collected.get(url)
        if prior is None:
            collected[url] = {**metadata, "used_by": [scope]}
            return
        prior_metadata = {field: prior.get(field) for field in sorted(SOURCE_FIELDS)}
        if prior_metadata != metadata:
            raise ResearchArtifactError(f"{url}: inconsistent source metadata across packets")
        used_by = prior.get("used_by")
        assert isinstance(used_by, list)
        if scope not in used_by:
            used_by.append(scope)
            used_by.sort()

    market_sources = context.get("market_sources")
    if not isinstance(market_sources, list):
        raise ResearchArtifactError("market sources are missing")
    for source in market_sources:
        add("market", source)
    symbols = context.get("symbols")
    if not isinstance(symbols, Mapping):
        raise ResearchArtifactError("symbol sources are missing")
    for symbol in sorted(symbols):
        blurb = symbols[symbol]
        if not isinstance(blurb, Mapping) or not isinstance(blurb.get("sources"), list):
            raise ResearchArtifactError(f"{symbol}: sources are missing")
        for source in blurb["sources"]:
            add(str(symbol), source)
    return [collected[url] for url in sorted(collected)]


def check_dashboard_html(html: str) -> list[str]:
    """Return stale or incomplete research markers in rendered dashboard HTML."""
    return [marker for marker in DASHBOARD_STALE_MARKERS if marker in html]


def _producer_code_sha(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ResearchArtifactError("cannot resolve producer git commit")
    return result.stdout.strip()


def _producer_source_sha(root: Path) -> str:
    paths = (
        root / "options_researcher/attractiveness_research_v2.py",
        root / "tools/research_context_assemble.py",
        root / ".claude/skills/research-refresh/SKILL.md",
    )
    payload = {path.relative_to(root).as_posix(): _sha256_file(path) for path in paths}
    return _sha256_bytes(canonical_json(payload).encode("utf-8"))


def _paths(root: Path, as_of: str) -> tuple[Path, Path, Path, Path, Path]:
    context_path = root / "reports/attractiveness_context" / f"{as_of}.json"
    report_path = root / "reports" / f"{as_of}-attractiveness-research-context.md"
    lineage_dir = root / "reports/attractiveness_research" / as_of
    final_manifest = lineage_dir / "manifest.json"
    pending_manifest = lineage_dir / "manifest.pending.json"
    previous_manifest = lineage_dir / "manifest.previous.json"
    return context_path, report_path, final_manifest, pending_manifest, previous_manifest


def publish_bundle(
    *,
    root: Path,
    as_of: str,
    candidate_ids: Sequence[str],
    pinned_symbols: Sequence[str],
    inputs_dir: Path,
    ritual_root: Path,
    run_date: str,
    started_at: datetime,
    producer_attempt_id: str,
    finished_at: datetime | None = None,
    producer_code_sha: str | None = None,
    producer_source_sha: str | None = None,
) -> PublicationResult:
    """Publish an untrusted pending bundle; dashboard finalization is separate."""
    inputs, packet_bytes = load_input_packets(inputs_dir)
    packet_hashes = {name: _sha256_bytes(raw) for name, raw in sorted(packet_bytes.items())}
    ritual_binding = load_successful_ritual(ritual_root, as_of=as_of, run_date=run_date)
    code_sha = producer_code_sha or _producer_code_sha(root)
    source_sha = producer_source_sha or _producer_source_sha(root)
    attempt_id = _require_attempt_id(
        producer_attempt_id,
        where="producer_attempt_id",
    )
    uv_lock_path = root / "uv.lock"
    if not uv_lock_path.is_file():
        raise ResearchArtifactError("uv.lock is missing")
    uv_lock_sha = _sha256_file(uv_lock_path)
    identity = {
        "schema_version": SCHEMA_VERSION,
        "market_as_of_date": as_of,
        "candidate_ids": list(candidate_ids),
        "pinned_symbols": list(pinned_symbols),
        "input_packet_sha256": packet_hashes,
        "ritual": ritual_binding.as_dict(),
        "producer_source_sha256": source_sha,
        "uv_lock_sha256": uv_lock_sha,
    }
    identity_sha = _sha256_bytes(canonical_json(identity).encode("utf-8"))
    run_id = f"research-{as_of}-{identity_sha[:16]}"
    (
        context_path,
        report_path,
        final_manifest,
        pending_manifest,
        previous_manifest,
    ) = _paths(root, as_of)

    if final_manifest.is_file():
        prior = _load_object(final_manifest, where="existing final manifest")
        if prior.get("input_identity_sha256") == identity_sha:
            verify_bundle(
                root=root,
                as_of=as_of,
                candidate_ids=candidate_ids,
                pinned_symbols=pinned_symbols,
                ritual_root=ritual_root,
                pending=False,
            )
            outputs = prior.get("outputs")
            if isinstance(outputs, dict):
                prior_context = outputs.get("context")
                if isinstance(prior_context, dict):
                    context_sha = prior_context.get("sha256")
                    if isinstance(context_sha, str):
                        return PublicationResult(
                            status="NO_NEW_INPUT",
                            run_id=str(prior.get("run_id")),
                            context_path=context_path,
                            report_path=report_path,
                            manifest_path=final_manifest,
                            context_sha256=context_sha,
                        )
        final_manifest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(final_manifest, previous_manifest)

    if pending_manifest.is_file():
        prior_pending = _load_object(pending_manifest, where="existing pending manifest")
        if prior_pending.get("input_identity_sha256") == identity_sha:
            verify_bundle(
                root=root,
                as_of=as_of,
                candidate_ids=candidate_ids,
                pinned_symbols=pinned_symbols,
                ritual_root=ritual_root,
                pending=True,
            )
            outputs = prior_pending.get("outputs")
            if isinstance(outputs, dict) and isinstance(outputs.get("context"), dict):
                context_sha = outputs["context"].get("sha256")
                if isinstance(context_sha, str):
                    return PublicationResult(
                        status="PENDING_DASHBOARD",
                        run_id=run_id,
                        context_path=context_path,
                        report_path=report_path,
                        manifest_path=pending_manifest,
                        context_sha256=context_sha,
                    )

    completed_at = finished_at or datetime.now(tz=NEW_YORK)
    context = build_context(
        as_of=as_of,
        candidate_ids=candidate_ids,
        pinned_symbols=pinned_symbols,
        inputs=inputs,
        started_at=started_at,
        finished_at=completed_at,
        run_id=run_id,
        producer_attempt_id=attempt_id,
        ritual_binding=ritual_binding,
        input_packet_sha256=packet_hashes,
        uv_lock_sha256=uv_lock_sha,
    )
    validate_context(
        context,
        candidate_ids=candidate_ids,
        pinned_symbols=pinned_symbols,
    )
    context_bytes = _json_bytes(context)
    report_bytes = render_markdown(context).encode("utf-8")
    packet_dir_relative = (
        Path("reports/attractiveness_research") / as_of / "runs" / run_id / "packets"
    )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "publication_status": "PENDING_DASHBOARD",
        "run_id": run_id,
        "producer_attempt_id": attempt_id,
        "market_as_of_date": as_of,
        "research_started_at_utc": context["research_started_at_utc"],
        "research_started_at_et": context["research_started_at_et"],
        "research_finished_at_utc": context["research_finished_at_utc"],
        "research_finished_at_et": context["research_finished_at_et"],
        "producer_code_sha": code_sha,
        "producer_source_sha256": source_sha,
        "uv_lock_sha256": uv_lock_sha,
        "candidate_ids": list(candidate_ids),
        "pinned_symbols": list(pinned_symbols),
        "required_symbols": required_symbols(candidate_ids, pinned_symbols),
        "ritual": ritual_binding.as_dict(),
        "input_identity_sha256": identity_sha,
        "input_packets": {
            name: {
                "path": (packet_dir_relative / name).as_posix(),
                "sha256": packet_hashes[name],
            }
            for name in sorted(packet_hashes)
        },
        "sources": collect_manifest_sources(context),
        "outputs": {
            "context": {
                "path": context_path.relative_to(root).as_posix(),
                "sha256": _sha256_bytes(context_bytes),
            },
            "markdown": {
                "path": report_path.relative_to(root).as_posix(),
                "sha256": _sha256_bytes(report_bytes),
            },
        },
    }

    for name, raw in sorted(packet_bytes.items()):
        packet_path = root / packet_dir_relative / name
        atomic_text_write(raw.decode("utf-8"), packet_path)
    atomic_text_write(context_bytes.decode("utf-8"), context_path)
    atomic_text_write(report_bytes.decode("utf-8"), report_path)
    atomic_text_write(_json_bytes(manifest).decode("utf-8"), pending_manifest)
    return PublicationResult(
        status="PENDING_DASHBOARD",
        run_id=run_id,
        context_path=context_path,
        report_path=report_path,
        manifest_path=pending_manifest,
        context_sha256=str(manifest["outputs"]["context"]["sha256"]),
    )


def verify_bundle(
    *,
    root: Path,
    as_of: str,
    candidate_ids: Sequence[str],
    pinned_symbols: Sequence[str],
    ritual_root: Path,
    pending: bool = False,
) -> dict[str, object]:
    """Verify either an untrusted pending bundle or the final commit marker."""
    context_path, report_path, final_manifest, pending_manifest, _previous = _paths(root, as_of)
    manifest_path = pending_manifest if pending else final_manifest
    manifest = _load_object(manifest_path, where="manifest")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ResearchArtifactError("manifest schema_version is not attractiveness_research/v2")
    expected_status = "PENDING_DASHBOARD" if pending else "FINAL"
    if manifest.get("publication_status") != expected_status:
        raise ResearchArtifactError(f"manifest publication_status is not {expected_status}")
    if manifest.get("market_as_of_date") != as_of:
        raise ResearchArtifactError("manifest market_as_of_date mismatch")
    if manifest.get("candidate_ids") != list(candidate_ids):
        raise ResearchArtifactError("manifest candidate_ids do not match the live board")
    if manifest.get("pinned_symbols") != list(pinned_symbols):
        raise ResearchArtifactError("manifest pinned_symbols do not match the live board")
    if manifest.get("required_symbols") != required_symbols(candidate_ids, pinned_symbols):
        raise ResearchArtifactError("manifest required_symbols do not match the live board")
    producer_source_sha = manifest.get("producer_source_sha256")
    if (
        not isinstance(producer_source_sha, str)
        or len(producer_source_sha) != 64
        or any(character not in "0123456789abcdef" for character in producer_source_sha)
    ):
        raise ResearchArtifactError("manifest producer_source_sha256 is invalid")
    producer_code_sha = manifest.get("producer_code_sha")
    if (
        not isinstance(producer_code_sha, str)
        or len(producer_code_sha) != 40
        or any(character not in "0123456789abcdef" for character in producer_code_sha)
    ):
        raise ResearchArtifactError("manifest producer_code_sha is invalid")
    uv_lock_sha = manifest.get("uv_lock_sha256")
    if not isinstance(uv_lock_sha, str) or len(uv_lock_sha) != 64:
        raise ResearchArtifactError("manifest uv_lock_sha256 is invalid")
    uv_lock_path = root / "uv.lock"
    if not uv_lock_path.is_file() or _sha256_file(uv_lock_path) != uv_lock_sha:
        raise ResearchArtifactError("manifest uv_lock_sha256 mismatch")

    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict):
        raise ResearchArtifactError("manifest outputs are missing")
    for label, expected_path in (("context", context_path), ("markdown", report_path)):
        output = outputs.get(label)
        if not isinstance(output, dict):
            raise ResearchArtifactError(f"manifest output {label} is missing")
        if output.get("path") != expected_path.relative_to(root).as_posix():
            raise ResearchArtifactError(f"manifest output {label} path mismatch")
        if not expected_path.is_file():
            raise ResearchArtifactError(f"manifest output {label} is missing")
        if output.get("sha256") != _sha256_file(expected_path):
            raise ResearchArtifactError(f"manifest output {label} sha256 mismatch")

    context = _load_object(context_path, where="context")
    validate_context(
        context,
        candidate_ids=candidate_ids,
        pinned_symbols=pinned_symbols,
    )
    if context.get("run_id") != manifest.get("run_id"):
        raise ResearchArtifactError("context run_id does not match manifest")
    producer_attempt_id = _require_attempt_id(
        manifest.get("producer_attempt_id"),
        where="manifest producer_attempt_id",
    )
    for field in (
        "research_started_at_utc",
        "research_started_at_et",
        "research_finished_at_utc",
        "research_finished_at_et",
    ):
        if context.get(field) != manifest.get(field):
            raise ResearchArtifactError(f"context {field} does not match manifest")
    lineage = context.get("lineage")
    if not isinstance(lineage, dict):
        raise ResearchArtifactError("context lineage is missing")
    if lineage.get("producer_attempt_id") != producer_attempt_id:
        raise ResearchArtifactError("context producer attempt does not match manifest")

    expected_report = render_markdown(context).encode("utf-8")
    if report_path.read_bytes() != expected_report:
        raise ResearchArtifactError("Markdown is not the deterministic rendering of context JSON")

    input_packets = manifest.get("input_packets")
    if not isinstance(input_packets, dict) or not input_packets:
        raise ResearchArtifactError("manifest input_packets are missing")
    packet_hashes: dict[str, str] = {}
    for name, entry in input_packets.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            raise ResearchArtifactError("manifest input packet entry is invalid")
        packet_path_value = entry.get("path")
        if not isinstance(packet_path_value, str):
            raise ResearchArtifactError(f"manifest input packet {name} path is invalid")
        expected_packet_path = (
            Path("reports/attractiveness_research")
            / as_of
            / "runs"
            / str(manifest.get("run_id"))
            / "packets"
            / name
        )
        if packet_path_value != expected_packet_path.as_posix():
            raise ResearchArtifactError(f"manifest input packet {name} path mismatch")
        packet_path = root / expected_packet_path
        if not packet_path.is_file():
            raise ResearchArtifactError(f"manifest input packet {name} is missing")
        digest = _sha256_file(packet_path)
        if entry.get("sha256") != digest:
            raise ResearchArtifactError(f"manifest input packet {name} sha256 mismatch")
        packet_hashes[name] = digest
    if lineage.get("input_packet_sha256") != dict(sorted(packet_hashes.items())):
        raise ResearchArtifactError("context input packet lineage mismatch")
    if lineage.get("uv_lock_sha256") != uv_lock_sha:
        raise ResearchArtifactError("context uv.lock lineage mismatch")

    ritual = manifest.get("ritual")
    if not isinstance(ritual, dict):
        raise ResearchArtifactError("manifest ritual binding is missing")
    run_date = ritual.get("run_date")
    if not isinstance(run_date, str):
        raise ResearchArtifactError("manifest ritual run_date is invalid")
    binding = load_successful_ritual(ritual_root, as_of=as_of, run_date=run_date)
    if binding.as_dict() != ritual:
        raise ResearchArtifactError("manifest ritual binding no longer matches exact evidence")
    if lineage.get("ritual_receipt_sha256") != binding.receipt_sha256:
        raise ResearchArtifactError("context ritual receipt lineage mismatch")
    if lineage.get("ritual_run_status_sha256") != binding.run_status_sha256:
        raise ResearchArtifactError("context ritual run status lineage mismatch")

    expected_identity = {
        "schema_version": SCHEMA_VERSION,
        "market_as_of_date": as_of,
        "candidate_ids": list(candidate_ids),
        "pinned_symbols": list(pinned_symbols),
        "input_packet_sha256": dict(sorted(packet_hashes.items())),
        "ritual": binding.as_dict(),
        "producer_source_sha256": producer_source_sha,
        "uv_lock_sha256": uv_lock_sha,
    }
    identity_sha = _sha256_bytes(canonical_json(expected_identity).encode("utf-8"))
    if manifest.get("input_identity_sha256") != identity_sha:
        raise ResearchArtifactError("manifest input_identity_sha256 mismatch")
    expected_run_id = f"research-{as_of}-{identity_sha[:16]}"
    if manifest.get("run_id") != expected_run_id:
        raise ResearchArtifactError("manifest run_id does not match its immutable inputs")
    if manifest.get("sources") != collect_manifest_sources(context):
        raise ResearchArtifactError("manifest source metadata mismatch")

    dashboard = manifest.get("dashboard_verification")
    if pending:
        if dashboard is not None:
            raise ResearchArtifactError("pending manifest cannot claim dashboard verification")
    else:
        if not isinstance(dashboard, Mapping):
            raise ResearchArtifactError("final manifest lacks dashboard verification")
        if dashboard.get("path") != ".tmp/dashboard/attractiveness.html":
            raise ResearchArtifactError("dashboard verification path mismatch")
        dashboard_sha = dashboard.get("sha256")
        if not isinstance(dashboard_sha, str) or len(dashboard_sha) != 64:
            raise ResearchArtifactError("dashboard verification sha256 is invalid")
        verified_utc = _utc_timestamp(
            dashboard.get("verified_at_utc"), where="dashboard.verified_at_utc"
        )
        verified_et = _parse_timestamp(
            dashboard.get("verified_at_et"), where="dashboard.verified_at_et"
        )
        if verified_utc != verified_et.astimezone(timezone.utc):
            raise ResearchArtifactError("dashboard verification ET/UTC mismatch")
        finished_utc = _utc_timestamp(
            manifest.get("research_finished_at_utc"),
            where="research_finished_at_utc",
        )
        if verified_utc < finished_utc:
            raise ResearchArtifactError("dashboard verified before research finished")

    return manifest


def finalize_bundle(
    *,
    root: Path,
    as_of: str,
    candidate_ids: Sequence[str],
    pinned_symbols: Sequence[str],
    ritual_root: Path,
    verified_at: datetime | None = None,
) -> dict[str, object]:
    """Publish the final manifest only after the rendered dashboard passes."""
    pending = verify_bundle(
        root=root,
        as_of=as_of,
        candidate_ids=candidate_ids,
        pinned_symbols=pinned_symbols,
        ritual_root=ritual_root,
        pending=True,
    )
    dashboard_path = root / ".tmp/dashboard/attractiveness.html"
    if not dashboard_path.is_file():
        raise ResearchArtifactError(f"dashboard output is missing: {dashboard_path}")
    dashboard_bytes = dashboard_path.read_bytes()
    try:
        dashboard_html = dashboard_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ResearchArtifactError("dashboard output is not UTF-8") from error
    problems = check_dashboard_html(dashboard_html)
    if problems:
        raise ResearchArtifactError("stale markers still present: " + "; ".join(problems))
    finalized_at = verified_at or datetime.now(NEW_YORK)
    if finalized_at.tzinfo is None or finalized_at.utcoffset() is None:
        raise ResearchArtifactError("verified_at must be timezone-aware")
    finished = _utc_timestamp(
        pending.get("research_finished_at_utc"), where="research_finished_at_utc"
    )
    if finalized_at.astimezone(timezone.utc) < finished:
        raise ResearchArtifactError("dashboard verification predates research finish")

    final_manifest = dict(pending)
    final_manifest["publication_status"] = "FINAL"
    final_manifest["dashboard_verification"] = {
        "path": ".tmp/dashboard/attractiveness.html",
        "sha256": _sha256_bytes(dashboard_bytes),
        "verified_at_utc": finalized_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verified_at_et": finalized_at.astimezone(NEW_YORK).isoformat(),
    }
    _context, _report, final_path, pending_path, _previous = _paths(root, as_of)
    atomic_text_write(_json_bytes(final_manifest).decode("utf-8"), final_path)
    try:
        pending_path.unlink()
    except FileNotFoundError:
        pass
    return final_manifest
