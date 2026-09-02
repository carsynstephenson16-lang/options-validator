"""Callable H7 Schwab quote-age gate; intentionally unwired to production.

The quote-age report sidecar is descriptive and unauthenticated. This module
recomputes its decision statistic from the manifest-bound chain bytes instead.
Until an owner creates a dedicated absolute-age threshold, it reports the
computed evidence without entry-banning any name.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pandas as pd

import config
from data.cache_runner import session_close_utc
from options_researcher.h7_schwab_data_gate import (
    EVIDENCE_MODE,
    validate_receipt_scope_closure,
)
from options_researcher.schwab_quote_age_report import (
    SCHEMA_VERSION as REPORT_SCHEMA_VERSION,
)
from options_researcher.schwab_quote_age_report import (
    SchwabQuoteAgeReportError,
    selectable_timestamp_population,
    sidecar_filename,
)
from research.hashing import sha256_file

SCHEMA_VERSION = "h7_schwab_quote_age_gate/v2"
QUOTE_AGE_GO = "SCHWAB_SELECTABLE_QUOTE_AGE_GO"
QUOTE_AGE_OVER_THRESHOLD = "SCHWAB_SELECTABLE_QUOTE_AGE_OVER_THRESHOLD"
QUOTE_AGE_EVIDENCE_INVALID = "SCHWAB_QUOTE_AGE_EVIDENCE_INVALID"
QUOTE_AGE_AWAITING_OWNER_THRESHOLD = "AWAITING_OWNER_THRESHOLD"
QUOTE_AGE_SIDECAR_MISSING = "SCHWAB_QUOTE_AGE_SIDECAR_MISSING"
QUOTE_AGE_SIDECAR_UNREADABLE = "SCHWAB_QUOTE_AGE_SIDECAR_UNREADABLE"
QUOTE_AGE_SIDECAR_IDENTITY_MISMATCH = "SCHWAB_QUOTE_AGE_SIDECAR_IDENTITY_MISMATCH"


def _included_names(values: Sequence[str]) -> tuple[str, ...]:
    names = tuple(str(value) for value in values)
    if (
        not names
        or len(set(names)) != len(names)
        or any(not name or name != name.strip() for name in names)
    ):
        raise ValueError("included_symbols must be unique non-empty text")
    return names


def _absolute_threshold() -> tuple[bool, object]:
    """Return ``(blocking_mode, threshold)`` without inventing a default."""
    threshold = getattr(config, "H7_SCHWAB_QUOTE_AGE_ABSOLUTE_MAX_MINUTES", None)
    return threshold is not None, threshold


def _sidecar_unavailable() -> dict:
    return {
        "path": None,
        "sha256": None,
        "status": "UNAVAILABLE",
        "reason_codes": [],
    }


def _sidecar_diagnostic(
    *,
    capture_receipt_path: Path,
    session: str,
    manifest_hash: str,
) -> dict:
    path = capture_receipt_path.with_name(sidecar_filename(capture_receipt_path.name))
    base = {"path": str(path), "sha256": None}
    try:
        raw = path.read_text(encoding="utf-8")
        report = json.loads(raw)
    except FileNotFoundError:
        return {**base, "status": "MISSING", "reason_codes": [QUOTE_AGE_SIDECAR_MISSING]}
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {
            **base,
            "status": "UNREADABLE",
            "reason_codes": [QUOTE_AGE_SIDECAR_UNREADABLE],
        }
    try:
        digest = sha256_file(path)
    except OSError:
        digest = None
    if (
        not isinstance(report, dict)
        or report.get("schema_version") != REPORT_SCHEMA_VERSION
        or report.get("session") != session
        or report.get("manifest_hash") != manifest_hash
    ):
        return {
            **base,
            "sha256": digest,
            "status": "IDENTITY_MISMATCH",
            "reason_codes": [QUOTE_AGE_SIDECAR_IDENTITY_MISMATCH],
        }
    return {**base, "sha256": digest, "status": "MATCHED", "reason_codes": []}


def _invalid_result(
    *,
    names: tuple[str, ...],
    session: object,
    threshold: object,
    blocking_mode: bool,
    error: str,
    sidecar_diagnostic: dict | None = None,
) -> dict:
    rows = {
        symbol: {
            "symbol": symbol,
            "verdict": "EVIDENCE_INVALID",
            "entry_banned": blocking_mode,
            "reason_codes": [QUOTE_AGE_EVIDENCE_INVALID],
            "worst_absolute_selectable_quote_age_minutes": None,
            "selectable_timestamp_min_utc": None,
            "error": error,
        }
        for symbol in names
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "evaluation_session": session,
        "absolute_threshold_minutes": threshold,
        "dispersion_reference_minutes": config.H7_SCHWAB_QUOTE_AGE_DISPERSION_REFERENCE_MINUTES,
        "metric_path": "manifest_bound_chain_bytes.<symbol>.timestamp.selectable.min_utc",
        "absolute_age_reference_utc": None,
        "universe": list(names),
        "go_count": 0,
        "no_go_count": len(names) if blocking_mode else 0,
        "awaiting_owner_threshold_count": 0,
        "evidence_invalid_count": len(names),
        "whole_universe_verdict": "EVIDENCE_INVALID",
        "entry_banned_symbols": list(names) if blocking_mode else [],
        "symbols": rows,
        "sidecar_diagnostic": sidecar_diagnostic or _sidecar_unavailable(),
        "error": error,
    }


def _numeric_blocking_threshold(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) and result >= 0 else None


def evaluate_schwab_quote_age(
    *,
    data_gate_receipt: dict,
    included_symbols: Sequence[str],
) -> dict:
    """Compute absolute selectable quote ages from verified chain package bytes.

    A sidecar is retained only as a non-blocking diagnostic because its bytes
    are not authenticated by the capture manifest. The production checkout has
    no caller for this callable gate; future Schwab arming wiring is a separate
    explicitly-authorized successor work package.
    """
    names = _included_names(included_symbols)
    blocking_mode, threshold = _absolute_threshold()
    numeric_threshold = _numeric_blocking_threshold(threshold) if blocking_mode else None
    session = (
        data_gate_receipt.get("evaluation_session") if isinstance(data_gate_receipt, dict) else None
    )
    if blocking_mode and numeric_threshold is None:
        return _invalid_result(
            names=names,
            session=session,
            threshold=threshold,
            blocking_mode=True,
            error="absolute quote-age threshold is invalid",
        )
    if (
        not isinstance(data_gate_receipt, dict)
        or data_gate_receipt.get("receipt_type") != "data_gate"
        or data_gate_receipt.get("evidence_mode") != EVIDENCE_MODE
        or not isinstance(session, str)
    ):
        return _invalid_result(
            names=names,
            session=session,
            threshold=threshold,
            blocking_mode=blocking_mode,
            error="Schwab data-gate receipt is malformed",
        )
    universe = data_gate_receipt.get("universe")
    records = data_gate_receipt.get("symbols")
    if (
        not isinstance(universe, list)
        or any(not isinstance(symbol, str) for symbol in universe)
        or universe != sorted(set(universe))
        or not set(names).issubset(universe)
        or not isinstance(records, dict)
    ):
        return _invalid_result(
            names=names,
            session=session,
            threshold=threshold,
            blocking_mode=blocking_mode,
            error="included symbols are not closed by the data-gate receipt",
        )
    try:
        binding = validate_receipt_scope_closure(data_gate_receipt, universe)
        manifest_hash = binding["schwab_manifest_hash"]
        capture_paths = {
            Path(records[symbol]["chain"]["audit_receipt"]["receipt_path"]) for symbol in names
        }
        chain_paths = {symbol: Path(records[symbol]["chain"]["expected_path"]) for symbol in names}
        if len(capture_paths) != 1:
            raise ValueError("included symbols do not share one capture receipt")
        reference_utc = session_close_utc(session)
        reference = pd.Timestamp(reference_utc)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return _invalid_result(
            names=names,
            session=session,
            threshold=threshold,
            blocking_mode=blocking_mode,
            error=f"manifest-bound chain evidence is invalid: {exc}",
        )

    sidecar = _sidecar_diagnostic(
        capture_receipt_path=next(iter(capture_paths)),
        session=session,
        manifest_hash=manifest_hash,
    )
    rows: dict[str, dict] = {}
    try:
        for symbol in names:
            frame = pd.read_parquet(chain_paths[symbol])
            timestamps = selectable_timestamp_population(frame)
            if timestamps.empty:
                raise ValueError(f"{symbol} selectable timestamp population is empty")
            if timestamps.isna().any():
                raise ValueError(f"{symbol} selectable timestamp population contains null")
            if (timestamps > reference).any():
                raise ValueError(f"{symbol} selectable timestamp is post-reference")
            ages = (reference - timestamps).dt.total_seconds() / 60.0
            if ages.isna().any() or (ages < 0).any():
                raise ValueError(
                    f"{symbol} selectable timestamp produced a negative or invalid age"
                )
            worst = round(float(ages.max()), 4)
            if not math.isfinite(worst):
                raise ValueError(f"{symbol} selectable timestamp age is not finite")
            timestamp_minimum = timestamps.min()
            if not isinstance(timestamp_minimum, pd.Timestamp):
                raise ValueError(f"{symbol} selectable timestamp minimum is invalid")
            timestamp_minimum_utc = cast(pd.Timestamp, timestamp_minimum).isoformat()
            if blocking_mode:
                if numeric_threshold is None:
                    raise ValueError("absolute quote-age threshold is invalid")
                over = worst > numeric_threshold
                verdict = "NO_GO" if over else "GO"
                reason_codes = [QUOTE_AGE_OVER_THRESHOLD if over else QUOTE_AGE_GO]
                entry_banned = over
            else:
                verdict = QUOTE_AGE_AWAITING_OWNER_THRESHOLD
                reason_codes = [QUOTE_AGE_AWAITING_OWNER_THRESHOLD]
                entry_banned = False
            rows[symbol] = {
                "symbol": symbol,
                "verdict": verdict,
                "entry_banned": entry_banned,
                "reason_codes": reason_codes,
                "worst_absolute_selectable_quote_age_minutes": worst,
                "selectable_timestamp_min_utc": timestamp_minimum_utc,
                "error": None,
            }
    except (OSError, ValueError, TypeError, SchwabQuoteAgeReportError) as exc:
        return _invalid_result(
            names=names,
            session=session,
            threshold=threshold,
            blocking_mode=blocking_mode,
            error=f"selectable timestamp evidence is invalid: {exc}",
            sidecar_diagnostic=sidecar,
        )

    banned = [symbol for symbol in names if rows[symbol]["entry_banned"]]
    go_count = sum(row["verdict"] == "GO" for row in rows.values())
    awaiting = sum(row["verdict"] == QUOTE_AGE_AWAITING_OWNER_THRESHOLD for row in rows.values())
    whole = (
        QUOTE_AGE_AWAITING_OWNER_THRESHOLD
        if not blocking_mode
        else ("GO" if not banned else "NO_GO")
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "evaluation_session": session,
        "absolute_threshold_minutes": threshold,
        "dispersion_reference_minutes": config.H7_SCHWAB_QUOTE_AGE_DISPERSION_REFERENCE_MINUTES,
        "metric_path": "manifest_bound_chain_bytes.<symbol>.timestamp.selectable.min_utc",
        "absolute_age_reference_utc": reference_utc.isoformat(),
        "universe": list(names),
        "go_count": go_count,
        "no_go_count": len(banned),
        "awaiting_owner_threshold_count": awaiting,
        "evidence_invalid_count": 0,
        "whole_universe_verdict": whole,
        "entry_banned_symbols": banned,
        "symbols": rows,
        "sidecar_diagnostic": sidecar,
        "error": None,
    }
