"""Validation-only contract for Top-3 research annotations.

This module deliberately has no filesystem, network, dashboard, ranking, or
trading dependencies.  It turns human or agent research notes into an
immutable, candidate-keyed advisory record.  The caller remains responsible
for storing the record and for all numerical candidate selection.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime, timezone
from types import MappingProxyType
from typing import Final
from urllib.parse import urlparse

_CLASSIFICATIONS: Final[frozenset[str]] = frozenset(
    {"fact", "derived_calculation", "inference", "unknown"}
)
_SOURCE_TIERS: Final[frozenset[str]] = frozenset(
    {
        "issuer_ir",
        "sec_filing",
        "regulator",
        "market_operator",
        "secondary",
        "unknown",
    }
)
_DATE_CERTAINTIES: Final[frozenset[str]] = frozenset(
    {"confirmed", "estimated", "unknown"}
)
_CONFIRMED_DATE_SOURCE_TIERS: Final[frozenset[str]] = frozenset(
    {"issuer_ir", "sec_filing", "regulator", "market_operator"}
)
_ANNOTATION_FIELDS: Final[frozenset[str]] = frozenset(
    {"research_as_of_utc", "market_as_of_date", "claims"}
)
_CLAIM_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "text",
        "classification",
        "source_url",
        "unknown_rationale",
        "source_tier",
        "fact_date",
        "date_certainty",
        "countercase",
    }
)


class AnnotationValidationError(ValueError):
    """A stable machine-readable rejection for malformed research context."""

    def __init__(self, code: str, path: str) -> None:
        self.code = code
        self.path = path
        super().__init__(f"{code}: {path}")


def _required_string(value: object, *, code: str, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AnnotationValidationError(code, path)
    return value.strip()


def _optional_string(value: object, *, code: str, path: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise AnnotationValidationError(code, path)
    return value.strip() or None


def _parse_utc_timestamp(value: object, *, path: str) -> str:
    raw = _required_string(
        value, code="research_as_of_utc_invalid", path=path
    )
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise AnnotationValidationError("research_as_of_utc_invalid", path) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AnnotationValidationError("research_as_of_utc_not_timezone_aware", path)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso_date(
    value: object, *, code: str, path: str, allow_none: bool = False
) -> str | None:
    if value is None and allow_none:
        return None
    raw = _required_string(value, code=code, path=path)
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as error:
        raise AnnotationValidationError(code, path) from error


def _validate_exact_fields(
    value: Mapping[object, object], *, allowed: frozenset[str], path: str,
    unexpected_code: str,
) -> None:
    unexpected = sorted(
        str(key) for key in value if not isinstance(key, str) or key not in allowed
    )
    if unexpected:
        raise AnnotationValidationError(unexpected_code, f"{path}.{unexpected[0]}")


def _normalize_claim(value: object, *, path: str) -> MappingProxyType:
    if not isinstance(value, Mapping):
        raise AnnotationValidationError("claim_not_object", path)
    _validate_exact_fields(
        value,
        allowed=_CLAIM_FIELDS,
        path=path,
        unexpected_code="unexpected_claim_field",
    )
    if "fact_date" not in value:
        raise AnnotationValidationError("fact_date_required", f"{path}.fact_date")

    claim_id = _required_string(value.get("id"), code="claim_id_missing", path=f"{path}.id")
    text = _required_string(value.get("text"), code="claim_text_missing", path=f"{path}.text")
    classification = _required_string(
        value.get("classification"),
        code="claim_classification_invalid",
        path=f"{path}.classification",
    )
    if classification not in _CLASSIFICATIONS:
        raise AnnotationValidationError("claim_classification_invalid", f"{path}.classification")

    source_tier = _required_string(
        value.get("source_tier"),
        code="source_tier_invalid",
        path=f"{path}.source_tier",
    )
    if source_tier not in _SOURCE_TIERS:
        raise AnnotationValidationError("source_tier_invalid", f"{path}.source_tier")

    date_certainty = _required_string(
        value.get("date_certainty"),
        code="date_certainty_invalid",
        path=f"{path}.date_certainty",
    )
    if date_certainty not in _DATE_CERTAINTIES:
        raise AnnotationValidationError("date_certainty_invalid", f"{path}.date_certainty")
    if (
        date_certainty == "confirmed"
        and source_tier not in _CONFIRMED_DATE_SOURCE_TIERS
    ):
        raise AnnotationValidationError(
            "confirmed_date_requires_primary_source", f"{path}.date_certainty"
        )

    source_url = _optional_string(
        value.get("source_url"), code="source_url_invalid", path=f"{path}.source_url"
    )
    if source_url is not None:
        parsed_url = urlparse(source_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise AnnotationValidationError("source_url_invalid", f"{path}.source_url")
    unknown_rationale = _optional_string(
        value.get("unknown_rationale"),
        code="unknown_rationale_invalid",
        path=f"{path}.unknown_rationale",
    )
    if source_url is None and unknown_rationale is None:
        raise AnnotationValidationError("claim_source_missing", path)
    if source_url is not None and unknown_rationale is not None:
        raise AnnotationValidationError("claim_source_ambiguous", path)
    if date_certainty == "confirmed" and source_url is None:
        raise AnnotationValidationError(
            "confirmed_date_requires_source_url", f"{path}.source_url"
        )

    fact_date = _parse_iso_date(
        value.get("fact_date"),
        code="fact_date_invalid",
        path=f"{path}.fact_date",
        allow_none=date_certainty == "unknown",
    )
    if date_certainty != "unknown" and fact_date is None:
        raise AnnotationValidationError("fact_date_required", f"{path}.fact_date")

    countercase = _required_string(
        value.get("countercase"),
        code="claim_countercase_missing",
        path=f"{path}.countercase",
    )
    return MappingProxyType(
        {
            "id": claim_id,
            "text": text,
            "classification": classification,
            "source_url": source_url,
            "unknown_rationale": unknown_rationale,
            "source_tier": source_tier,
            "fact_date": fact_date,
            "date_certainty": date_certainty,
            "countercase": countercase,
        }
    )


def _candidate_key_set(candidate_keys: Iterable[str]) -> frozenset[str]:
    if isinstance(candidate_keys, str):
        raise AnnotationValidationError("candidate_keys_not_iterable", "candidate_keys")
    keys: set[str] = set()
    for index, key in enumerate(candidate_keys):
        normalized = _required_string(
            key, code="candidate_key_invalid", path=f"candidate_keys[{index}]"
        )
        if key != normalized:
            raise AnnotationValidationError("candidate_key_invalid", f"candidate_keys[{index}]")
        if normalized in keys:
            raise AnnotationValidationError("candidate_key_duplicate", normalized)
        keys.add(normalized)
    return frozenset(keys)


def normalize_research_annotations(
    candidate_keys: Iterable[str], annotations_by_candidate: Mapping[str, object]
) -> MappingProxyType:
    """Return immutable, advisory-only research annotations keyed by candidate.

    ``candidate_keys`` is the authoritative set emitted by the deterministic
    options candidate builder.  Every supplied annotation must match one of
    those keys; candidates without research are intentionally omitted rather
    than receiving invented content.  This function validates and normalizes
    source metadata only.  It never returns a score, rank, or trade action.
    """
    allowed_candidates = _candidate_key_set(candidate_keys)
    if not isinstance(annotations_by_candidate, Mapping):
        raise AnnotationValidationError("annotations_not_mapping", "annotations")

    unmatched = sorted(
        str(key)
        for key in annotations_by_candidate
        if not isinstance(key, str) or key not in allowed_candidates
    )
    if unmatched:
        raise AnnotationValidationError("candidate_key_unmatched", unmatched[0])

    normalized: dict[str, MappingProxyType] = {}
    for candidate_key in sorted(annotations_by_candidate):
        raw_annotation = annotations_by_candidate[candidate_key]
        path = f"annotations[{candidate_key!r}]"
        if not isinstance(raw_annotation, Mapping):
            raise AnnotationValidationError("annotation_not_object", path)
        _validate_exact_fields(
            raw_annotation,
            allowed=_ANNOTATION_FIELDS,
            path=path,
            unexpected_code="unexpected_annotation_field",
        )
        research_as_of = _parse_utc_timestamp(
            raw_annotation.get("research_as_of_utc"), path=f"{path}.research_as_of_utc"
        )
        market_as_of = _parse_iso_date(
            raw_annotation.get("market_as_of_date"),
            code="market_as_of_date_invalid",
            path=f"{path}.market_as_of_date",
        )
        assert market_as_of is not None

        raw_claims = raw_annotation.get("claims")
        if not isinstance(raw_claims, list):
            raise AnnotationValidationError("claims_not_list", f"{path}.claims")
        claims: list[MappingProxyType] = []
        claim_ids: set[str] = set()
        for index, raw_claim in enumerate(raw_claims):
            claim = _normalize_claim(raw_claim, path=f"{path}.claims[{index}]")
            claim_id = claim["id"]
            if claim_id in claim_ids:
                raise AnnotationValidationError(
                    "claim_id_duplicate", f"{path}.claims[{index}].id"
                )
            claim_ids.add(claim_id)
            claims.append(claim)

        normalized[candidate_key] = MappingProxyType(
            {
                "research_as_of_utc": research_as_of,
                "market_as_of_date": market_as_of,
                "claims": tuple(claims),
                "advisory_only": True,
            }
        )
    return MappingProxyType(normalized)


__all__ = ["AnnotationValidationError", "normalize_research_annotations"]
