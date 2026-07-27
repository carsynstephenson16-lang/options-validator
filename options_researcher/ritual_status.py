"""Publish the latest deterministic daily-ritual terminal status.

The hypothesis capture receipt records per-lane outcomes, but it cannot prove
that the enclosing ritual finished successfully. This mutable, atomic status
projection closes that gap for downstream descriptive research: a later
BROKEN rerun replaces an earlier OK and therefore fails closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from data.atomic_io import atomic_text_write

SCHEMA_VERSION = "daily_ritual/run_status/v1"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _current_code_sha(root: Path) -> str:
    result = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def build_status(
    *,
    as_of: str,
    run_date: str,
    status: str,
    code_sha: str,
    capture_receipt_path: str,
    capture_receipt_sha256: str,
    log_path: str,
    now_utc: datetime | None = None,
) -> dict:
    date.fromisoformat(as_of)
    date.fromisoformat(run_date)
    if status not in {"RUNNING", "OK", "BROKEN"}:
        raise ValueError("status must be RUNNING, OK, or BROKEN")
    if not _SHA1_RE.fullmatch(code_sha):
        raise ValueError("code_sha must be a 40-character lowercase Git SHA")
    if not re.fullmatch(r"[0-9a-f]{64}", capture_receipt_sha256):
        raise ValueError("capture_receipt_sha256 must be lowercase SHA-256")
    expected_capture = f"reports/ritual/capture_receipt_{as_of}.json"
    if capture_receipt_path != expected_capture:
        raise ValueError(
            f"capture receipt path must be {expected_capture}, "
            f"got {capture_receipt_path}"
        )
    timestamp = now_utc or datetime.now(timezone.utc)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("now_utc must be timezone-aware")
    timestamp = timestamp.astimezone(timezone.utc)
    return {
        "schema_version": SCHEMA_VERSION,
        "as_of": as_of,
        "run_date": run_date,
        "status": status,
        "code_sha": code_sha,
        "capture_receipt_path": capture_receipt_path,
        "capture_receipt_sha256": capture_receipt_sha256,
        "run_at_utc": timestamp.isoformat().replace("+00:00", "Z"),
        "run_at_et": timestamp.astimezone(
            ZoneInfo("America/New_York")
        ).isoformat(),
        "log_path": log_path,
    }


def publish_status(
    *,
    root: Path,
    as_of: str,
    run_date: str,
    status: str,
    log_path: str,
) -> Path:
    root = Path(root).resolve()
    capture_relative = f"reports/ritual/capture_receipt_{as_of}.json"
    capture = root / capture_relative
    if status != "RUNNING" and not capture.is_file():
        raise FileNotFoundError(f"missing capture receipt: {capture}")
    capture_sha256 = (
        _file_sha256(capture) if capture.is_file() and status != "RUNNING"
        else "0" * 64
    )
    payload = build_status(
        as_of=as_of,
        run_date=run_date,
        status=status,
        code_sha=_current_code_sha(root),
        capture_receipt_path=capture_relative,
        capture_receipt_sha256=capture_sha256,
        log_path=log_path,
    )
    output = root / "reports" / "ritual" / f"run_status_{as_of}.json"
    if status == "RUNNING" and output.exists():
        previous = output.with_name(f".{output.name}.previous")
        os.replace(output, previous)
    atomic_text_write(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        output,
    )
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--run-date", required=True)
    parser.add_argument(
        "--status", choices=("RUNNING", "OK", "BROKEN"), required=True
    )
    parser.add_argument("--log-path", required=True)
    args = parser.parse_args(argv)
    output = publish_status(
        root=args.root,
        as_of=args.as_of,
        run_date=args.run_date,
        status=args.status,
        log_path=args.log_path,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
