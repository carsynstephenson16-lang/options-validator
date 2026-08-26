"""Build one read-only, receipt-backed daily job-health digest."""

from __future__ import annotations

import argparse
import errno
import hashlib
import io
import json
import os
import re
from contextlib import redirect_stdout
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

import config


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
_EXPECTED_HYPOTHESES = frozenset(("H5", "H6", "H7", "H8", "H10"))
_NY_TZ = ZoneInfo("America/New_York")


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


def _contained_path(root: Path, relative: str) -> tuple[Path | None, str | None]:
    candidate = root / relative
    try:
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        return None, f"unsafe receipt path: {type(exc).__name__}"
    if resolved != root and root not in resolved.parents:
        return None, "receipt path escapes root"
    return candidate, None


def _ritual_overall(root: Path, as_of: str) -> HealthRow:
    relative = f"reports/ritual/run_status_{as_of}.json"
    path, path_error = _contained_path(root, relative)
    if path_error is not None or path is None:
        return HealthRow(
            "Ritual overall",
            HealthStatus.FAILED,
            path_error or "unsafe receipt path",
            relative,
        )
    if not path.is_file():
        return _missing("Ritual overall", relative)
    payload, error = _read_object(path)
    if error is not None or payload is None:
        return HealthRow(
            "Ritual overall", HealthStatus.FAILED, error or "invalid receipt", relative
        )
    if payload.get("schema_version") != "daily_ritual/run_status/v1":
        return HealthRow(
            "Ritual overall",
            HealthStatus.FAILED,
            "schema_version mismatch",
            relative,
        )
    if payload.get("as_of") != as_of:
        return HealthRow(
            "Ritual overall",
            HealthStatus.FAILED,
            f"session mismatch: expected {as_of}",
            relative,
        )
    capture_relative = f"reports/ritual/capture_receipt_{as_of}.json"
    if payload.get("capture_receipt_path") != capture_relative:
        return HealthRow(
            "Ritual overall",
            HealthStatus.FAILED,
            "capture_receipt_path mismatch",
            relative,
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
    if value != "RUNNING":
        capture_path, capture_path_error = _contained_path(root, capture_relative)
        if capture_path_error is not None or capture_path is None:
            return HealthRow(
                "Ritual overall",
                HealthStatus.FAILED,
                capture_path_error or "unsafe capture receipt path",
                relative,
            )
        if not capture_path.is_file():
            return HealthRow(
                "Ritual overall",
                HealthStatus.FAILED,
                "bound capture receipt absent",
                relative,
            )
        try:
            capture_sha256 = hashlib.sha256(capture_path.read_bytes()).hexdigest()
        except OSError as exc:
            return HealthRow(
                "Ritual overall",
                HealthStatus.FAILED,
                f"unreadable capture receipt: {type(exc).__name__}",
                relative,
            )
        if payload.get("capture_receipt_sha256") != capture_sha256:
            return HealthRow(
                "Ritual overall",
                HealthStatus.FAILED,
                "capture_receipt_sha256 mismatch",
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
    path, path_error = _contained_path(root, relative)
    if path_error is not None or path is None:
        return HealthRow(
            "Ritual hypotheses",
            HealthStatus.FAILED,
            path_error or "unsafe receipt path",
            relative,
        )
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
    actual_hypotheses = set(hypotheses)
    if actual_hypotheses != _EXPECTED_HYPOTHESES:
        missing = ",".join(sorted(_EXPECTED_HYPOTHESES - actual_hypotheses))
        unexpected = ",".join(sorted(actual_hypotheses - _EXPECTED_HYPOTHESES))
        details = []
        if missing:
            details.append(f"missing={missing}")
        if unexpected:
            details.append(f"unexpected={unexpected}")
        return HealthRow(
            "Ritual hypotheses",
            HealthStatus.FAILED,
            "hypothesis key mismatch: " + "; ".join(details),
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


def _intraday_capture(root: Path, as_of: str, tag: str) -> HealthRow:
    job = f"Intraday capture ({tag})"
    relative = f"reports/intraday_capture/{as_of}/{tag}.json"
    path, path_error = _contained_path(root, relative)
    if path_error is not None or path is None:
        return HealthRow(
            job,
            HealthStatus.FAILED,
            path_error or "unsafe receipt path",
            relative,
        )
    if not path.is_file():
        return _missing(job, relative)
    payload, error = _read_object(path)
    if error is not None or payload is None:
        return HealthRow(job, HealthStatus.FAILED, error or "invalid receipt", relative)
    timestamp = _receipt_timestamp(payload)
    if timestamp is None:
        return HealthRow(
            job,
            HealthStatus.FAILED,
            "invalid captured_at_utc",
            relative,
        )
    if payload.get("receipt_kind") != "intraday_capture/v1":
        return HealthRow(
            job,
            HealthStatus.FAILED,
            "receipt_kind mismatch: expected intraday_capture/v1",
            relative,
        )
    if payload.get("force") is not False:
        return HealthRow(
            job,
            HealthStatus.FAILED,
            "force must be false for a scheduled capture",
            relative,
        )
    if payload.get("session_tag") != tag:
        return HealthRow(
            job,
            HealthStatus.FAILED,
            f"session_tag mismatch: expected {tag}",
            relative,
        )
    scheduled_et = config.INTRADAY_CAPTURE_TIMES[tag]
    if payload.get("scheduled_et") != scheduled_et:
        return HealthRow(
            job,
            HealthStatus.FAILED,
            f"scheduled_et mismatch: expected {scheduled_et}",
            relative,
        )
    if timestamp.astimezone(_NY_TZ).date().isoformat() != as_of:
        return HealthRow(
            job,
            HealthStatus.FAILED,
            f"session mismatch: expected {as_of}",
            relative,
        )
    universe = payload.get("universe")
    if (
        not isinstance(universe, list)
        or not universe
        or not all(isinstance(symbol, str) and symbol for symbol in universe)
        or len(set(universe)) != len(universe)
    ):
        return HealthRow(job, HealthStatus.FAILED, "invalid symbol universe", relative)
    names = payload.get("names")
    if not isinstance(names, dict):
        return HealthRow(job, HealthStatus.FAILED, "missing per-symbol statuses", relative)
    expected = set(universe)
    actual = set(names)
    missing = sorted(expected - actual)
    if missing:
        return HealthRow(
            job,
            HealthStatus.FAILED,
            "missing symbol rows: " + ", ".join(missing),
            relative,
        )
    unexpected = sorted(actual - expected)
    if unexpected:
        return HealthRow(
            job,
            HealthStatus.FAILED,
            "unexpected symbol rows: " + ", ".join(unexpected),
            relative,
        )
    covered = 0
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
            continue
        else:
            unknown.append(f"{symbol}={status}")
    if identity_mismatches:
        return HealthRow(
            job,
            HealthStatus.FAILED,
            "symbol identity mismatch: " + ", ".join(identity_mismatches),
            relative,
        )
    if unknown:
        return HealthRow(
            job,
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
        job,
        status,
        f"{covered}/{total} symbols captured",
        relative,
    )


def _schwab_preclose(root: Path, as_of: str) -> HealthRow:
    relative = f"reports/schwab_chains/{as_of}/preclose.json"
    path, path_error = _contained_path(root, relative)
    if path_error is not None or path is None:
        return HealthRow(
            "Schwab preclose",
            HealthStatus.FAILED,
            path_error or "unsafe receipt path",
            relative,
        )
    if not path.is_file():
        return _missing("Schwab preclose", relative)
    payload, error = _read_object(path)
    if error is not None or payload is None:
        return HealthRow(
            "Schwab preclose", HealthStatus.FAILED, error or "invalid receipt", relative
        )
    value = payload.get("overall_status")
    if value == "failed":
        return HealthRow("Schwab preclose", HealthStatus.FAILED, "overall_status=failed", relative)
    if value != "ok":
        return HealthRow(
            "Schwab preclose",
            HealthStatus.FAILED,
            f"unknown overall_status {value!r}",
            relative,
        )
    universe = payload.get("universe")
    if not isinstance(universe, list) or not all(isinstance(symbol, str) for symbol in universe):
        return HealthRow(
            "Schwab preclose",
            HealthStatus.FAILED,
            "invalid universe for manifest verification",
            relative,
        )
    manifest_relative = f"reports/schwab_chains/{as_of}/manifest.json"
    manifest_path, manifest_error = _contained_path(root, manifest_relative)
    if manifest_error is not None or manifest_path is None:
        return HealthRow(
            "Schwab preclose",
            HealthStatus.FAILED,
            manifest_error or "unsafe manifest path",
            manifest_relative,
        )
    chain_dir_relative = ".cache/schwab_chains"
    chain_dir, chain_dir_error = _contained_path(root, chain_dir_relative)
    if chain_dir_error is not None or chain_dir is None:
        return HealthRow(
            "Schwab preclose",
            HealthStatus.FAILED,
            chain_dir_error or "unsafe chain directory",
            chain_dir_relative,
        )
    for symbol in universe:
        chain_relative = f"{chain_dir_relative}/{symbol}_{as_of}.parquet"
        _chain_path, chain_error = _contained_path(root, chain_relative)
        if chain_error is not None:
            return HealthRow(
                "Schwab preclose",
                HealthStatus.FAILED,
                chain_error,
                chain_relative,
            )
    # The existing verifier imports the capture module, whose dependencies emit
    # import-time informational lines to stdout. Keep the digest's stdout contract
    # exact while still reusing the canonical offline verification implementation.
    with redirect_stdout(io.StringIO()):
        from tools import schwab_chain_manifest

    try:
        schwab_chain_manifest.verify_session(as_of, universe, chain_dir, manifest_path, path)
    except (schwab_chain_manifest.SchwabChainManifestError, OSError) as exc:
        return HealthRow(
            "Schwab preclose",
            HealthStatus.FAILED,
            f"manifest verification failed: {exc}",
            relative,
        )
    if payload.get("invocation_source") != "launchd":
        return HealthRow(
            "Schwab preclose",
            HealthStatus.DEGRADED,
            "invocation_source must be launchd",
            relative,
        )
    return HealthRow(
        "Schwab preclose",
        HealthStatus.OK,
        "overall_status=ok; force=false; invocation_source=launchd; manifest verified",
        relative,
    )


def _alignment_check(root: Path, as_of: str) -> HealthRow:
    relative = f".tmp/alignment_check/{as_of}.log"
    path, path_error = _contained_path(root, relative)
    if path_error is not None or path is None:
        return HealthRow(
            "Alignment check",
            HealthStatus.FAILED,
            path_error or "unsafe receipt path",
            relative,
        )
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


def _research_refresh(root: Path, as_of: str, invocation_date: date) -> HealthRow:
    relative = f".tmp/research_refresh/receipt_v2_{as_of}_premarket.json"
    path, path_error = _contained_path(root, relative)
    if path_error is not None or path is None:
        return HealthRow(
            "Research refresh (premarket)",
            HealthStatus.FAILED,
            path_error or "unsafe receipt path",
            relative,
        )
    if not path.is_file():
        return _missing("Research refresh (premarket)", relative)
    try:
        receipt_date = datetime.fromtimestamp(path.stat().st_mtime, _NY_TZ).date()
    except OSError as exc:
        return HealthRow(
            "Research refresh (premarket)",
            HealthStatus.FAILED,
            f"unreadable receipt mtime: {type(exc).__name__}",
            relative,
        )
    if receipt_date != invocation_date:
        return HealthRow(
            "Research refresh (premarket)",
            HealthStatus.MISSING,
            f"receipt mtime {receipt_date} not fresh for invocation date {invocation_date}",
            relative,
        )
    return HealthRow(
        "Research refresh (premarket)",
        HealthStatus.OK,
        f"expected slot receipt is fresh for invocation date {invocation_date}",
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
        *[
            HealthRow(
                f"Intraday capture ({tag})",
                status,
                reason,
                f"reports/intraday_capture/{as_of}/{tag}.json",
            )
            for tag in config.INTRADAY_CAPTURE_TIMES
        ],
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


def collect_health(
    root: Path,
    as_of: str,
    *,
    research_root: Path | None = None,
    invocation_date: date | None = None,
) -> list[HealthRow]:
    """Read receipt state under both roots without mutating either one."""
    date.fromisoformat(as_of)
    root = Path(root).resolve()
    research_root = Path(research_root if research_root is not None else root).resolve()
    invocation_date = invocation_date or datetime.now(_NY_TZ).date()
    if not _is_xnys_session(as_of):
        return [
            *_session_rows(HealthStatus.NO_SESSION, "not an XNYS session", as_of),
            _research_display_refresh(),
        ]
    # live-dashboard writes no receipt by design, so it is intentionally absent.
    return [
        _ritual_overall(root, as_of),
        _ritual_hypotheses(root, as_of),
        *[_intraday_capture(root, as_of, tag) for tag in config.INTRADAY_CAPTURE_TIMES],
        _schwab_preclose(root, as_of),
        _alignment_check(root, as_of),
        _research_refresh(research_root, as_of, invocation_date),
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
    research_root: Path,
    as_of: str,
    out_dir: Path,
    invocation_date: date,
    cwd: Path,
) -> Path:
    resolved_root = root.resolve()
    resolved_research_root = research_root.resolve()
    resolved_out_dir = out_dir.resolve()
    resolved_cwd = cwd.resolve()
    for label, read_root in (
        ("--root", resolved_root),
        ("--research-root", resolved_research_root),
    ):
        if read_root != resolved_cwd and (
            resolved_out_dir == read_root or read_root in resolved_out_dir.parents
        ):
            raise ValueError(f"--out-dir resolves inside {label} for a different checkout")
    output = resolved_out_dir / f"digest_{as_of}.md"
    if output.is_symlink():
        raise ValueError("digest output path must not be a symlink")
    resolved_output = output.resolve(strict=False)
    if resolved_output.parent != resolved_out_dir:
        raise ValueError("digest output path resolves outside --out-dir")
    digest = render_digest(
        as_of,
        collect_health(
            resolved_root,
            as_of,
            research_root=resolved_research_root,
            invocation_date=invocation_date,
        ),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(output, flags, 0o666)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise ValueError("digest output path must not be a symlink") from exc
        raise
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(digest)
    print(digest, end="")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    parser.add_argument("--root", type=Path)
    parser.add_argument(
        "--research-root",
        type=Path,
        default=Path("~/options-validator-research").expanduser(),
    )
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args(argv)
    cwd = Path.cwd()
    try:
        write_digest(
            root=args.root if args.root is not None else cwd,
            research_root=args.research_root,
            as_of=args.as_of.isoformat(),
            out_dir=args.out_dir if args.out_dir is not None else cwd / ".tmp" / "job_health",
            invocation_date=datetime.now(_NY_TZ).date(),
            cwd=cwd,
        )
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
