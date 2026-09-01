"""Fail-closed quote-age gate for the H7 Schwab arming lane.

This is a pure read over a durable data-gate receipt and its capture-package
sidecar. It does not register a window, append an event, or arm an entry lane.
The sidecar metric is the report's selectable timestamp dispersion, not
trade_timestamp and not wall-clock age.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from pathlib import Path

import config
from options_researcher.h7_schwab_data_gate import EVIDENCE_MODE
from options_researcher.schwab_quote_age_report import (
    SCHEMA_VERSION as REPORT_SCHEMA_VERSION,
)
from options_researcher.schwab_quote_age_report import (
    sidecar_filename,
)
from research.hashing import sha256_file

SCHEMA_VERSION = "h7_schwab_quote_age_gate/v1"
QUOTE_AGE_GO = "SCHWAB_SELECTABLE_QUOTE_AGE_GO"
QUOTE_AGE_OVER_THRESHOLD = "SCHWAB_SELECTABLE_QUOTE_AGE_OVER_THRESHOLD"
QUOTE_AGE_EVIDENCE_INVALID = "SCHWAB_QUOTE_AGE_EVIDENCE_INVALID"


def _invalid_result(
    *,
    names: tuple[str, ...],
    session: object,
    threshold: object,
    sidecar_path: Path | None,
    error: str,
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "evaluation_session": session,
        "threshold_minutes": threshold,
        "metric_path": ("symbols.<symbol>.columns.timestamp.selectable.age_minutes.max"),
        "sidecar_path": (str(sidecar_path) if sidecar_path is not None else None),
        "sidecar_sha256": None,
        "universe": list(names),
        "go_count": 0,
        "no_go_count": len(names),
        "whole_universe_verdict": "NO_GO",
        "symbols": {
            symbol: {
                "symbol": symbol,
                "verdict": "NO_GO",
                "reason_codes": [QUOTE_AGE_EVIDENCE_INVALID],
                "worst_selectable_quote_age_minutes": None,
                "error": error,
            }
            for symbol in names
        },
        "error": error,
    }


def _included_names(values: Sequence[str]) -> tuple[str, ...]:
    names = tuple(str(value) for value in values)
    if (
        not names
        or len(set(names)) != len(names)
        or any(not name or name != name.strip() for name in names)
    ):
        raise ValueError("included_symbols must be unique non-empty text")
    return names


def evaluate_schwab_quote_age(
    *,
    data_gate_receipt: dict,
    included_symbols: Sequence[str],
) -> dict:
    """Evaluate one capture sidecar at the owner-typed quote-age threshold."""
    names = _included_names(included_symbols)
    threshold = getattr(config, "H7_SCHWAB_MAX_SELECTABLE_QUOTE_AGE_MINUTES", None)
    session = (
        data_gate_receipt.get("evaluation_session") if isinstance(data_gate_receipt, dict) else None
    )
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not math.isfinite(float(threshold))
        or float(threshold) < 0
    ):
        return _invalid_result(
            names=names,
            session=session,
            threshold=threshold,
            sidecar_path=None,
            error="quote-age threshold is invalid",
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
            sidecar_path=None,
            error="Schwab data-gate receipt is malformed",
        )
    universe = data_gate_receipt.get("universe")
    records = data_gate_receipt.get("symbols")
    if (
        not isinstance(universe, list)
        or not set(names).issubset(universe)
        or not isinstance(records, dict)
    ):
        return _invalid_result(
            names=names,
            session=session,
            threshold=threshold,
            sidecar_path=None,
            error="included symbols are not closed by the data-gate receipt",
        )

    capture_paths: set[Path] = set()
    try:
        for symbol in names:
            audit = records[symbol]["chain"]["audit_receipt"]
            if audit.get("valid") is not True:
                raise ValueError(f"{symbol} capture receipt is not valid")
            raw_path = audit["receipt_path"]
            if not isinstance(raw_path, str) or not raw_path:
                raise ValueError(f"{symbol} capture receipt path is missing")
            capture_paths.add(Path(raw_path).resolve(strict=False))
    except (KeyError, TypeError, ValueError) as exc:
        return _invalid_result(
            names=names,
            session=session,
            threshold=threshold,
            sidecar_path=None,
            error=f"capture receipt binding is malformed: {exc}",
        )
    if len(capture_paths) != 1:
        return _invalid_result(
            names=names,
            session=session,
            threshold=threshold,
            sidecar_path=None,
            error="included symbols do not share one capture receipt",
        )
    capture_path = next(iter(capture_paths))
    sidecar_path = capture_path.with_name(sidecar_filename(capture_path.name))
    try:
        report = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _invalid_result(
            names=names,
            session=session,
            threshold=threshold,
            sidecar_path=sidecar_path,
            error=f"quote-age sidecar not found: {sidecar_path}",
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return _invalid_result(
            names=names,
            session=session,
            threshold=threshold,
            sidecar_path=sidecar_path,
            error=f"quote-age sidecar is unreadable: {type(exc).__name__}: {exc}",
        )
    if (
        not isinstance(report, dict)
        or report.get("schema_version") != REPORT_SCHEMA_VERSION
        or report.get("session") != session
        or not isinstance(report.get("symbols_requested"), list)
        or not set(names).issubset(report["symbols_requested"])
        or not isinstance(report.get("symbols"), dict)
    ):
        return _invalid_result(
            names=names,
            session=session,
            threshold=threshold,
            sidecar_path=sidecar_path,
            error="quote-age sidecar identity is malformed or mismatched",
        )

    rows: dict[str, dict] = {}
    for symbol in names:
        try:
            age = report["symbols"][symbol]["columns"]["timestamp"]["selectable"]["age_minutes"][
                "max"
            ]
            if (
                isinstance(age, bool)
                or not isinstance(age, (int, float))
                or not math.isfinite(float(age))
                or float(age) < 0
            ):
                raise ValueError("max age is not finite non-negative numeric")
        except (KeyError, TypeError, ValueError) as exc:
            rows[symbol] = {
                "symbol": symbol,
                "verdict": "NO_GO",
                "reason_codes": [QUOTE_AGE_EVIDENCE_INVALID],
                "worst_selectable_quote_age_minutes": None,
                "error": f"selectable timestamp age is malformed: {exc}",
            }
            continue
        number = float(age)
        over = number > float(threshold)
        rows[symbol] = {
            "symbol": symbol,
            "verdict": "NO_GO" if over else "GO",
            "reason_codes": [QUOTE_AGE_OVER_THRESHOLD if over else QUOTE_AGE_GO],
            "worst_selectable_quote_age_minutes": number,
            "error": None,
        }

    go_count = sum(row["verdict"] == "GO" for row in rows.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "evaluation_session": session,
        "threshold_minutes": threshold,
        "metric_path": ("symbols.<symbol>.columns.timestamp.selectable.age_minutes.max"),
        "sidecar_path": str(sidecar_path),
        "sidecar_sha256": sha256_file(sidecar_path),
        "universe": list(names),
        "go_count": go_count,
        "no_go_count": len(names) - go_count,
        "whole_universe_verdict": ("GO" if go_count == len(names) else "NO_GO"),
        "symbols": rows,
        "error": None,
    }
