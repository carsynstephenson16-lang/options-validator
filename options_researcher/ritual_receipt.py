"""Summarize the daily ritual's per-hypothesis capture evidence.

The receipt is deliberately date-driven: callers must provide both the
evaluation session and run date.  This module only inspects artifacts already
written by the ritual; it never runs a watcher, fetches data, or derives dates
from the wall clock.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Literal, TypedDict

import config
from options_researcher.h7_scope import scope_identity
from options_researcher.h10_observe import (
    ObservationLogMalformed,
    read_h10b_observation_union,
)

CaptureStatus = Literal["CAPTURED", "NO_SIGNAL", "REFUSED", "MISSING"]


class CaptureResult(TypedDict):
    status: CaptureStatus
    evidence: str | None
    detail: str


class CaptureReceipt(TypedDict):
    as_of: str
    run_date: str
    hypotheses: dict[str, CaptureResult]


_DATED_NAME = re.compile(r"\d{4}-\d{2}-\d{2}")


def _result(status: CaptureStatus, *, evidence: str | None = None, detail: str) -> CaptureResult:
    return {"status": status, "evidence": evidence, "detail": detail}


def _evidence(root: Path, path: Path) -> str:
    return str(path.relative_to(root))


def _has_stale_sibling(path: Path) -> bool:
    if not path.parent.is_dir():
        return False
    return any(
        candidate.is_file() and candidate != path and _DATED_NAME.search(candidate.name) is not None
        for candidate in path.parent.iterdir()
    )


def _missing_path(path: Path) -> CaptureResult:
    detail = "stale" if _has_stale_sibling(path) else "artifact missing"
    return _result("MISSING", detail=detail)


def _load_text(path: Path) -> tuple[str | None, CaptureResult | None]:
    if not path.is_file():
        return None, _missing_path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None, _result("MISSING", detail="unreadable artifact")
    if not text.strip():
        return None, _result("MISSING", detail="empty artifact")
    return text, None


def _load_json(path: Path) -> tuple[dict[str, object] | None, CaptureResult | None]:
    if not path.is_file():
        return None, _missing_path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None, _result("MISSING", detail="unreadable JSON")
    if not raw.strip():
        return None, _result("MISSING", detail="empty JSON")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None, _result("MISSING", detail="unparseable JSON")
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        return None, _result("MISSING", detail="invalid JSON root")
    return value, None


def _object_list(value: object) -> list[dict[str, object]] | None:
    if not isinstance(value, list):
        return None
    rows: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict) or not all(isinstance(key, str) for key in item):
            return None
        rows.append(item)
    return rows


def _h5(root: Path, as_of: str) -> CaptureResult:
    path = root / "reports/h5" / f"entry_watch_{as_of}.txt"
    text, failure = _load_text(path)
    if failure is not None:
        return failure
    assert text is not None
    session = re.search(r"\bevaluation_session=(\d{4}-\d{2}-\d{2})\b", text)
    if session is None or session.group(1) != as_of:
        return _result("REFUSED", evidence=_evidence(root, path), detail="session mismatch")
    rows = re.findall(r"(?m)^([A-Z0-9.-]+):\s+(WAIT|FIRE|DATA_GAP)\b(.*)$", text)
    if len(rows) != len(config.H5_ENTRY_TRIGGERS) or {symbol for symbol, _, _ in rows} != set(
        config.H5_ENTRY_TRIGGERS
    ):
        return _result(
            "REFUSED",
            evidence=_evidence(root, path),
            detail="tracked-name coverage mismatch",
        )
    if any(status == "DATA_GAP" for _, status, _ in rows):
        return _result("REFUSED", evidence=_evidence(root, path), detail="data gap")
    required_asof_labels = (
        f"(as of {as_of})",
        f"feature as of {as_of}",
        f"chain as of {as_of}",
    )
    if any(any(label not in detail for label in required_asof_labels) for _, _, detail in rows):
        return _result("REFUSED", evidence=_evidence(root, path), detail="session mismatch")
    count = sum(status == "FIRE" for _, status, _ in rows)
    if count:
        return _result(
            "CAPTURED",
            evidence=_evidence(root, path),
            detail=f"{count} signal(s) captured",
        )
    return _result("NO_SIGNAL", evidence=_evidence(root, path), detail="no signal")


def _h6(root: Path, as_of: str) -> CaptureResult:
    path = root / "reports/h6_forward" / f"{as_of}.json"
    receipt, failure = _load_json(path)
    if failure is not None:
        return failure
    assert receipt is not None
    snapshot = receipt.get("snapshot")
    if not isinstance(snapshot, dict):
        return _result("MISSING", detail="invalid H6 JSON")
    if snapshot.get("evaluation_session") != as_of:
        return _result("MISSING", detail="stale")
    entries = _object_list(snapshot.get("entries"))
    exits = _object_list(snapshot.get("exits"))
    if entries is None or exits is None:
        return _result("MISSING", detail="invalid H6 JSON")
    if any(row.get("action") == "BLOCKED" for row in exits):
        return _result("REFUSED", evidence=_evidence(root, path), detail="exit evaluation blocked")
    count = sum(row.get("status") == "ELIGIBLE" for row in entries) + sum(
        row.get("action") == "CLOSE" for row in exits
    )
    status: CaptureStatus = "CAPTURED" if count else "NO_SIGNAL"
    detail = f"{count} signal(s) captured" if count else "no signal"
    return _result(status, evidence=_evidence(root, path), detail=detail)


def _h7(root: Path, as_of: str, scope_id: str) -> CaptureResult:
    gate_path = root / "reports/h7_data_gate" / scope_id / "receipts" / f"{as_of}.json"
    watcher_path = root / "reports/h7_receipts" / scope_id / "watcher" / f"{as_of}.json"
    preflight_path = root / "reports/h7_receipts" / scope_id / "preflight" / f"{as_of}.txt"
    gate, failure = _load_json(gate_path)
    if failure is not None:
        return failure
    assert gate is not None
    if gate.get("evaluation_session") != as_of:
        return _result("MISSING", detail="stale")
    if gate.get("whole_universe_verdict") != "GO":
        return _result("REFUSED", evidence=_evidence(root, gate_path), detail="data gate NO_GO")

    watcher, failure = _load_json(watcher_path)
    if failure is not None:
        return failure
    assert watcher is not None
    if watcher.get("evaluation_session") != as_of:
        return _result("MISSING", detail="stale")
    errors = watcher.get("errors")
    if not isinstance(errors, list):
        return _result("MISSING", detail="invalid H7 watcher JSON")
    if errors:
        return _result("REFUSED", evidence=_evidence(root, watcher_path), detail="watcher errors")

    preflight, failure = _load_text(preflight_path)
    if failure is not None:
        return failure
    assert preflight is not None
    match = re.search(r"(?:^|\n)exit_code=(\d+)\s*$", preflight)
    if match is None:
        return _result("MISSING", detail="preflight exit code missing")
    if match.group(1) != "0":
        return _result(
            "REFUSED",
            evidence=_evidence(root, preflight_path),
            detail=f"preflight exit {match.group(1)}",
        )
    count = watcher.get("actionable_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        return _result("MISSING", detail="invalid H7 watcher JSON")
    status: CaptureStatus = "CAPTURED" if count else "NO_SIGNAL"
    detail = f"{count} signal(s) captured" if count else "no signal"
    return _result(status, evidence=_evidence(root, watcher_path), detail=detail)


def _h8(root: Path, as_of: str) -> CaptureResult:
    path = root / "reports/h8_forward" / f"{as_of}.json"
    payload, failure = _load_json(path)
    if failure is not None:
        return failure
    assert payload is not None
    if payload.get("evaluation_session") != as_of:
        return _result("MISSING", detail="stale")
    entries = _object_list(payload.get("entries"))
    exits = _object_list(payload.get("exits"))
    errors = payload.get("errors")
    if entries is None or exits is None or not isinstance(errors, list):
        return _result("MISSING", detail="invalid H8 JSON")
    if errors:
        return _result("REFUSED", evidence=_evidence(root, path), detail="watcher errors")
    if any(row.get("action") == "BLOCKED" for row in exits):
        return _result("REFUSED", evidence=_evidence(root, path), detail="exit evaluation blocked")
    count = sum(row.get("status") == "ENTRY-OK" for row in entries) + sum(
        row.get("action") == "EXIT" for row in exits
    )
    status: CaptureStatus = "CAPTURED" if count else "NO_SIGNAL"
    detail = f"{count} signal(s) captured" if count else "no signal"
    return _result(status, evidence=_evidence(root, path), detail=detail)


def _load_observations(path: Path) -> tuple[list[dict[str, object]] | None, CaptureResult | None]:
    if not path.is_file():
        return None, _missing_path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None, _result("MISSING", detail="unreadable JSON")
    if not raw.strip():
        return None, _result("MISSING", detail="empty JSON")
    rows: list[dict[str, object]] = []
    try:
        for line in raw.splitlines():
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
                return None, _result("MISSING", detail="invalid JSON root")
            rows.append(value)
    except json.JSONDecodeError:
        return None, _result("MISSING", detail="unparseable JSON")
    return rows, None


def _h10(root: Path, as_of: str, run_date: str) -> CaptureResult:
    receipt_path = root / "reports/h10/receipts" / f"h10_watch_{run_date}.json"
    legacy_observation_path = root / "reports/h10/observations.jsonl"
    h10b_observation_path = root / "reports/h10/h10b_observations.jsonl"
    receipt, failure = _load_json(receipt_path)
    if failure is not None:
        return failure
    assert receipt is not None
    if receipt.get("as_of") != run_date:
        return _result("MISSING", detail="stale")
    if receipt.get("evaluation_session") != as_of:
        return _result(
            "REFUSED",
            evidence=_evidence(root, receipt_path),
            detail="session mismatch",
        )

    try:
        union = read_h10b_observation_union(
            root=root,
            legacy_observations_path=legacy_observation_path,
            h10b_observations_path=h10b_observation_path,
        )
    except ObservationLogMalformed as exc:
        return _result(
            "REFUSED",
            evidence=_evidence(root, h10b_observation_path),
            detail=f"malformed H10b observation union: {exc}",
        )
    observations = union["observations"]
    matching = [
        row
        for row in observations
        if row.get("hypothesis") == "H10b" and row.get("as_of") == run_date
    ]
    if not matching:
        observation_path = h10b_observation_path
        return _missing_path(observation_path)
    if len(matching) != 1:
        return _result("REFUSED", detail="duplicate H10 observation")
    observation = matching[0]
    observation_path = (
        h10b_observation_path
        if observation.get("evaluation_session") >= config.H10B_RESUME_FLOOR_SESSION
        else legacy_observation_path
    )
    expected_receipt = str(receipt_path.relative_to(root))
    try:
        receipt_hash = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    except (OSError, PermissionError):
        return _result("MISSING", detail="receipt unreadable")
    if (
        observation.get("receipt") != expected_receipt
        or observation.get("receipt_sha256") != receipt_hash
    ):
        return _result(
            "REFUSED",
            evidence=_evidence(root, observation_path),
            detail="H10 observation receipt binding mismatch",
        )

    evaluations = _object_list(receipt.get("evaluations"))
    if not evaluations:
        return _result("MISSING", detail="invalid H10 JSON")
    unresolved: list[dict[str, object]] = []
    for row in evaluations:
        signals = row.get("signals")
        if (
            row.get("status") == "SKIPPED"
            and isinstance(signals, dict)
            and signals.get("H10b") is not True
        ):
            unresolved.append(row)
    if unresolved:
        reason = unresolved[0].get("reason")
        detail = f"watcher skipped: {reason}" if isinstance(reason, str) else "watcher skipped"
        return _result("REFUSED", evidence=_evidence(root, receipt_path), detail=detail)
    count = 0
    for row in evaluations:
        signals = row.get("signals")
        if isinstance(signals, dict) and signals.get("H10b") is True:
            count += 1
    status: CaptureStatus = "CAPTURED" if count else "NO_SIGNAL"
    detail = f"{count} signal(s) captured" if count else "no signal"
    return _result(status, evidence=_evidence(root, receipt_path), detail=detail)


def build_capture_receipt(
    *, as_of: str, run_date: str, root: Path, scope_id: str
) -> CaptureReceipt:
    """Inspect one ritual run and return its five-hypothesis summary."""
    return {
        "as_of": as_of,
        "run_date": run_date,
        "hypotheses": {
            "H5": _h5(root, as_of),
            "H6": _h6(root, as_of),
            "H7": _h7(root, as_of, scope_id),
            "H8": _h8(root, as_of),
            "H10": _h10(root, as_of, run_date),
        },
    }


def main(
    argv: list[str] | None = None,
    *,
    root: Path = Path("."),
    scope_id: str | None = None,
) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Write the daily ritual per-hypothesis capture receipt"
    )
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    parser.add_argument("--run-date", required=True, type=date.fromisoformat)
    args = parser.parse_args(argv)

    as_of = args.as_of.isoformat()
    run_date = args.run_date.isoformat()
    resolved_scope = scope_id or str(scope_identity()["scope_id"])
    receipt = build_capture_receipt(
        as_of=as_of,
        run_date=run_date,
        root=Path(root),
        scope_id=resolved_scope,
    )
    output = Path(root) / "reports/ritual" / f"capture_receipt_{as_of}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    for hypothesis in ("H5", "H6", "H7", "H8", "H10"):
        result = receipt["hypotheses"][hypothesis]
        print(f"{hypothesis}: {result['status']} - {result['detail']}")
    print(f"receipt={_evidence(Path(root), output)}")
    return int(
        any(result["status"] in {"MISSING", "REFUSED"} for result in receipt["hypotheses"].values())
    )


if __name__ == "__main__":
    raise SystemExit(main())
