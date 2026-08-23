"""Build one read-only, receipt-backed daily job-health digest."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import cast

import pandas_market_calendars as mcal


class HealthStatus(StrEnum):
    FAILED = "FAILED"
    MISSING = "MISSING"
    DEGRADED = "DEGRADED"
    OK = "OK"
    NO_SESSION = "NO_SESSION"
    NOT_INSTRUMENTED = "NOT_INSTRUMENTED"


@dataclass(frozen=True)
class HealthRow:
    job: str
    status: HealthStatus
    reason: str
    path: str


_PROBLEM_STATUSES = {
    HealthStatus.FAILED,
    HealthStatus.MISSING,
    HealthStatus.DEGRADED,
}
_SORT_ORDER = {
    HealthStatus.FAILED: 0,
    HealthStatus.MISSING: 1,
    HealthStatus.DEGRADED: 2,
    HealthStatus.OK: 3,
    HealthStatus.NO_SESSION: 4,
    HealthStatus.NOT_INSTRUMENTED: 5,
}
_ALIGNMENT_STATUS = re.compile(r"(?:^|\s)status=([A-Z_]+)(?:\s|$)")


def _is_xnys_session(as_of: str) -> bool:
    try:
        schedule = mcal.get_calendar("XNYS").schedule(start_date=as_of, end_date=as_of)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{as_of} is outside supported XNYS calendar range") from exc
    return not schedule.empty


def _read_object(path: Path) -> tuple[dict[str, object] | None, str | None]:
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"unreadable receipt: {type(exc).__name__}"
    try:
        value = cast(object, json.loads(raw))
    except json.JSONDecodeError:
        return None, "invalid JSON"
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        return None, "invalid JSON object"
    return value, None


def _missing(job: str, path: str) -> HealthRow:
    return HealthRow(job, HealthStatus.MISSING, "receipt absent", path)


def _ritual_overall(root: Path, as_of: str) -> HealthRow:
    relative = f"reports/ritual/run_status_{as_of}.json"
    path = root / relative
    if not path.is_file():
        return _missing("Ritual overall", relative)
    payload, error = _read_object(path)
    if error is not None or payload is None:
        return HealthRow(
            "Ritual overall", HealthStatus.FAILED, error or "invalid receipt", relative
        )
    value = payload.get("status")
    mapping = {
        "OK": HealthStatus.OK,
        "OK_STARVED": HealthStatus.DEGRADED,
        "RUNNING": HealthStatus.DEGRADED,
        "BROKEN": HealthStatus.FAILED,
    }
    if not isinstance(value, str) or value not in mapping:
        return HealthRow(
            "Ritual overall",
            HealthStatus.FAILED,
            f"unknown status {value!r}",
            relative,
        )
    reasons = {
        "OK": "ritual completed",
        "OK_STARVED": "ritual completed with starved hypotheses",
        "RUNNING": "ritual has no terminal status",
        "BROKEN": "ritual reported BROKEN",
    }
    return HealthRow("Ritual overall", mapping[value], reasons[value], relative)


def _ritual_hypotheses(root: Path, as_of: str) -> HealthRow:
    relative = f"reports/ritual/capture_receipt_{as_of}.json"
    path = root / relative
    if not path.is_file():
        return _missing("Ritual hypotheses", relative)
    payload, error = _read_object(path)
    if error is not None or payload is None:
        return HealthRow(
            "Ritual hypotheses", HealthStatus.FAILED, error or "invalid receipt", relative
        )
    hypotheses = payload.get("hypotheses")
    if not isinstance(hypotheses, dict) or not hypotheses:
        return HealthRow(
            "Ritual hypotheses",
            HealthStatus.FAILED,
            "missing hypotheses object",
            relative,
        )
    healthy = {"CAPTURED", "NO_SIGNAL"}
    degraded = {"REFUSED", "MISSING"}
    problems: list[str] = []
    unknown: list[str] = []
    for name, result in sorted(hypotheses.items(), key=lambda item: str(item[0])):
        status = result.get("status") if isinstance(result, dict) else None
        if isinstance(status, str) and status in healthy:
            continue
        label = f"{name}={status}"
        if isinstance(status, str) and status in degraded:
            problems.append(label)
        else:
            unknown.append(label)
    if unknown:
        return HealthRow(
            "Ritual hypotheses",
            HealthStatus.FAILED,
            "unknown hypothesis status: " + ", ".join(unknown),
            relative,
        )
    if problems:
        return HealthRow(
            "Ritual hypotheses",
            HealthStatus.DEGRADED,
            ", ".join(problems),
            relative,
        )
    return HealthRow(
        "Ritual hypotheses",
        HealthStatus.OK,
        f"{len(hypotheses)}/{len(hypotheses)} healthy",
        relative,
    )


def _receipt_timestamp(payload: dict[str, object]) -> datetime | None:
    value = payload.get("captured_at_utc")
    if not isinstance(value, str):
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        return None
    return timestamp


def _intraday_capture(root: Path, as_of: str) -> HealthRow:
    directory_relative = f"reports/intraday_capture/{as_of}"
    directory = root / directory_relative
    candidates = sorted(directory.glob("*.json")) if directory.is_dir() else []
    if not candidates:
        return _missing("Intraday capture", f"{directory_relative}/*.json")
    parsed: list[tuple[datetime, Path, dict[str, object]]] = []
    for candidate in candidates:
        payload, error = _read_object(candidate)
        relative = candidate.relative_to(root).as_posix()
        if error is not None or payload is None:
            return HealthRow(
                "Intraday capture", HealthStatus.FAILED, error or "invalid receipt", relative
            )
        timestamp = _receipt_timestamp(payload)
        if timestamp is None:
            return HealthRow(
                "Intraday capture",
                HealthStatus.FAILED,
                "invalid captured_at_utc",
                relative,
            )
        parsed.append((timestamp, candidate, payload))
    _timestamp, newest_path, newest = max(parsed, key=lambda item: item[0])
    relative = newest_path.relative_to(root).as_posix()
    universe = newest.get("universe")
    if (
        not isinstance(universe, list)
        or not universe
        or not all(isinstance(symbol, str) and symbol for symbol in universe)
        or len(set(universe)) != len(universe)
    ):
        return HealthRow(
            "Intraday capture", HealthStatus.FAILED, "invalid symbol universe", relative
        )
    names = newest.get("names")
    if not isinstance(names, dict):
        return HealthRow(
            "Intraday capture", HealthStatus.FAILED, "missing per-symbol statuses", relative
        )
    expected = set(universe)
    actual = set(names)
    missing = sorted(expected - actual)
    if missing:
        return HealthRow(
            "Intraday capture",
            HealthStatus.FAILED,
            "missing symbol rows: " + ", ".join(missing),
            relative,
        )
    unexpected = sorted(actual - expected)
    if unexpected:
        return HealthRow(
            "Intraday capture",
            HealthStatus.FAILED,
            "unexpected symbol rows: " + ", ".join(unexpected),
            relative,
        )
    covered = 0
    unavailable = 0
    unknown: list[str] = []
    identity_mismatches: list[str] = []
    for symbol in sorted(universe):
        result = names[symbol]
        row_symbol = result.get("symbol") if isinstance(result, dict) else None
        if row_symbol != symbol:
            identity_mismatches.append(f"{symbol}={row_symbol!r}")
            continue
        status = result.get("status") if isinstance(result, dict) else None
        if status == "ok":
            covered += 1
        elif status == "unavailable":
            unavailable += 1
        else:
            unknown.append(f"{symbol}={status}")
    if identity_mismatches:
        return HealthRow(
            "Intraday capture",
            HealthStatus.FAILED,
            "symbol identity mismatch: " + ", ".join(identity_mismatches),
            relative,
        )
    if unknown:
        return HealthRow(
            "Intraday capture",
            HealthStatus.FAILED,
            "unknown symbol status: " + ", ".join(unknown),
            relative,
        )
    total = len(universe)
    if covered == total:
        status = HealthStatus.OK
    elif covered == 0:
        status = HealthStatus.FAILED
    else:
        status = HealthStatus.DEGRADED
    return HealthRow(
        "Intraday capture",
        status,
        f"{covered}/{total} symbols captured",
        relative,
    )


def _schwab_preclose(root: Path, as_of: str) -> HealthRow:
    relative = f"reports/schwab_chains/{as_of}/preclose.json"
    path = root / relative
    if not path.is_file():
        return _missing("Schwab preclose", relative)
    payload, error = _read_object(path)
    if error is not None or payload is None:
        return HealthRow(
            "Schwab preclose", HealthStatus.FAILED, error or "invalid receipt", relative
        )
    value = payload.get("overall_status")
    if value == "ok":
        return HealthRow("Schwab preclose", HealthStatus.OK, "overall_status=ok", relative)
    if value == "failed":
        return HealthRow("Schwab preclose", HealthStatus.FAILED, "overall_status=failed", relative)
    return HealthRow(
        "Schwab preclose",
        HealthStatus.FAILED,
        f"unknown overall_status {value!r}",
        relative,
    )


def _alignment_check(root: Path, as_of: str) -> HealthRow:
    relative = f".tmp/alignment_check/{as_of}.log"
    path = root / relative
    if not path.is_file():
        return _missing("Alignment check", relative)
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, UnicodeDecodeError) as exc:
        return HealthRow(
            "Alignment check",
            HealthStatus.FAILED,
            f"unreadable log: {type(exc).__name__}",
            relative,
        )
    if not lines:
        return HealthRow("Alignment check", HealthStatus.FAILED, "empty log", relative)
    match = _ALIGNMENT_STATUS.search(lines[-1])
    if match is None:
        return HealthRow(
            "Alignment check", HealthStatus.FAILED, "latest line lacks status token", relative
        )
    value = match.group(1)
    if value == "ALIGNED":
        status = HealthStatus.OK
    elif value == "AHEAD_EVIDENCE_ONLY":
        status = HealthStatus.DEGRADED
    else:
        status = HealthStatus.FAILED
    return HealthRow("Alignment check", status, f"status={value}", relative)


def _research_refresh(root: Path, as_of: str) -> HealthRow:
    relative = f".tmp/research_refresh/receipt_v2_{as_of}_premarket.json"
    if not (root / relative).is_file():
        return _missing("Research refresh (premarket)", relative)
    return HealthRow(
        "Research refresh (premarket)",
        HealthStatus.OK,
        "expected slot receipt exists",
        relative,
    )


def _research_display_refresh() -> HealthRow:
    return HealthRow(
        "Research display refresh",
        HealthStatus.NOT_INSTRUMENTED,
        "no discrete receipt",
        "N/A",
    )


def _session_rows(status: HealthStatus, reason: str, as_of: str) -> list[HealthRow]:
    return [
        HealthRow("Ritual overall", status, reason, f"reports/ritual/run_status_{as_of}.json"),
        HealthRow(
            "Ritual hypotheses",
            status,
            reason,
            f"reports/ritual/capture_receipt_{as_of}.json",
        ),
        HealthRow(
            "Intraday capture",
            status,
            reason,
            f"reports/intraday_capture/{as_of}/*.json",
        ),
        HealthRow(
            "Schwab preclose",
            status,
            reason,
            f"reports/schwab_chains/{as_of}/preclose.json",
        ),
        HealthRow("Alignment check", status, reason, f".tmp/alignment_check/{as_of}.log"),
        HealthRow(
            "Research refresh (premarket)",
            status,
            reason,
            f".tmp/research_refresh/receipt_v2_{as_of}_premarket.json",
        ),
    ]


def collect_health(root: Path, as_of: str) -> list[HealthRow]:
    """Read receipt state under ``root`` without mutating it."""
    date.fromisoformat(as_of)
    root = Path(root).resolve()
    if not _is_xnys_session(as_of):
        return [
            *_session_rows(HealthStatus.NO_SESSION, "not an XNYS session", as_of),
            _research_display_refresh(),
        ]
    # live-dashboard writes no receipt by design, so it is intentionally absent.
    return [
        _ritual_overall(root, as_of),
        _ritual_hypotheses(root, as_of),
        _intraday_capture(root, as_of),
        _schwab_preclose(root, as_of),
        _alignment_check(root, as_of),
        _research_refresh(root, as_of),
        _research_display_refresh(),
    ]


def _markdown_cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")


def render_digest(as_of: str, rows: list[HealthRow]) -> str:
    problems = sum(row.status in _PROBLEM_STATUSES for row in rows)
    headline = "ALL OK" if problems == 0 else f"{problems} PROBLEMS"
    ordered = sorted(rows, key=lambda row: (_SORT_ORDER[row.status], row.job))
    lines = [
        headline,
        "",
        f"Session: {as_of}",
        "",
        "| Job | Status | Reason | Receipt path |",
        "| --- | --- | --- | --- |",
    ]
    lines.extend(
        "| "
        + " | ".join(
            (
                _markdown_cell(row.job),
                row.status.value,
                _markdown_cell(row.reason),
                _markdown_cell(row.path),
            )
        )
        + " |"
        for row in ordered
    )
    return "\n".join(lines) + "\n"


def write_digest(
    *,
    root: Path,
    as_of: str,
    output_root: Path,
    allow_output_in_root: bool = False,
) -> Path:
    output = output_root / ".tmp" / "job_health" / f"digest_{as_of}.md"
    resolved_root = root.resolve()
    resolved_output = output.resolve()
    if not allow_output_in_root and (
        resolved_output == resolved_root or resolved_root in resolved_output.parents
    ):
        raise ValueError("digest output would be written inside explicit --root")
    digest = render_digest(as_of, collect_health(resolved_root, as_of))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(digest, encoding="utf-8")
    print(digest, end="")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args(argv)
    output_root = Path.cwd()
    try:
        write_digest(
            root=args.root if args.root is not None else output_root,
            as_of=args.as_of.isoformat(),
            output_root=output_root,
            allow_output_in_root=args.root is None,
        )
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
