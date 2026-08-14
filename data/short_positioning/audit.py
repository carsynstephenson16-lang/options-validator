"""Offline audit of local short-positioning artifacts.

The audit reads, reports, and blocks. It never repairs data, never reaches a
network, and never writes a row-level provider value or a credential into a
receipt: findings carry codes, symbols, and counts only.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path

from data.short_positioning.models import (
    ShortPositioningSchemaError,
    validate_short_interest_record,
)
from data.short_positioning.normalize import NORMALIZED_FILE_GLOB, record_from_json

PASS = "PASS"
WARN = "WARN"
BLOCK = "BLOCK"
REDACTED = "[REDACTED]"

_SECRET_PATTERN = re.compile(
    r"(?i)\b(token|secret|password|bearer|credential|api[_-]?key)\b([\s:=]+)(\S+)"
)


def _finding(code: str, detail: str, **extra) -> dict:
    return {"code": code, "detail": detail, **extra}


def _status(findings: list[dict]) -> str:
    if any(finding.get("severity", BLOCK) == BLOCK for finding in findings):
        return BLOCK
    return WARN if findings else PASS


def _raw_dir(root: Path, provider: str, dataset: str, publication_date: date) -> Path:
    return (
        Path(root)
        / "raw"
        / f"provider={provider}"
        / f"dataset={dataset}"
        / f"publication_date={publication_date.isoformat()}"
    )


def _normalized_dir(root: Path, provider: str, dataset: str, publication_date: date) -> Path:
    return (
        Path(root)
        / "normalized"
        / f"provider={provider}"
        / f"dataset={dataset}"
        / f"publication_date={publication_date.isoformat()}"
    )


def audit_raw_partition(root: Path, *, provider: str, dataset: str, publication_date: date) -> dict:
    """Hash, manifest, and presence checks over immutable raw artifacts."""
    partition = _raw_dir(Path(root), provider, dataset, publication_date)
    findings: list[dict] = []
    artifacts = 0

    if not partition.exists():
        findings.append(
            _finding("MISSING_PARTITION", f"no raw partition for {publication_date.isoformat()}")
        )
    else:
        for path in sorted(partition.glob("*.json")):
            if path.name.endswith(".manifest.json"):
                continue
            artifacts += 1
            manifest_path = path.with_suffix(".manifest.json")
            if not manifest_path.exists():
                findings.append(
                    _finding(
                        "MISSING_PROVENANCE", f"no manifest for {path.name}", artifact=path.name
                    )
                )
                continue
            try:
                manifest = json.loads(manifest_path.read_text())
            except json.JSONDecodeError as exc:
                findings.append(
                    _finding("SCHEMA_ERROR", f"manifest unreadable: {exc}", artifact=path.name)
                )
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != manifest.get("raw_sha256"):
                findings.append(
                    _finding(
                        "HASH_MISMATCH",
                        f"{path.name} no longer matches its manifest digest",
                        artifact=path.name,
                    )
                )
        if artifacts == 0:
            findings.append(
                _finding("PARTIAL_CAPTURE", "raw partition exists but holds no artifact")
            )

    return {
        "check": "raw_partition",
        "provider": provider,
        "dataset": dataset,
        "publication_date": publication_date.isoformat(),
        "status": _status(findings),
        "counts": {"artifacts": artifacts},
        "findings": findings,
    }


def audit_normalized_partition(
    root: Path, *, provider: str, dataset: str, publication_date: date, asof: datetime
) -> dict:
    """Schema, key, timing, and drift checks over a normalized partition."""
    partition = _normalized_dir(Path(root), provider, dataset, publication_date)
    findings: list[dict] = []
    counts = {"records": 0, "symbols": 0, "revisions": 0, "splits": 0, "captures": 0}

    capture_files = sorted(partition.glob(NORMALIZED_FILE_GLOB)) if partition.exists() else []
    if not capture_files:
        findings.append(
            _finding("MISSING_PARTITION", f"no normalized partition for {publication_date}")
        )
        return _normalized_report(provider, dataset, publication_date, findings, counts)

    counts["captures"] = len(capture_files)
    per_capture: list[tuple[str, list]] = []
    for path in capture_files:
        try:
            document = json.loads(path.read_text())
            rows = document["records"]
            per_capture.append((path.name, [record_from_json(row) for row in rows]))
        except (json.JSONDecodeError, KeyError, TypeError, ShortPositioningSchemaError) as exc:
            findings.append(
                _finding("SCHEMA_ERROR", f"capture is not readable: {exc}", artifact=path.name)
            )
            return _normalized_report(provider, dataset, publication_date, findings, counts)
    records = [record for _name, group in per_capture for record in group]

    counts["records"] = len(records)
    counts["symbols"] = len({record.symbol for record in records})
    counts["revisions"] = sum(1 for record in records if record.revision_flag)
    counts["splits"] = sum(1 for record in records if record.stock_split_flag)

    for record in records:
        try:
            validate_short_interest_record(record)
        except ShortPositioningSchemaError as exc:
            findings.append(
                _finding("SCHEMA_ERROR", f"record failed validation: {exc}", symbol=record.symbol)
            )

    # Duplicates are judged inside one capture. The same key legitimately
    # reappears in a later capture; that is a re-capture, not a corruption.
    for name, group in per_capture:
        keys = [record.source_record_key for record in group]
        for key in sorted({key for key in keys if keys.count(key) > 1}):
            findings.append(
                _finding(
                    "DUPLICATE_KEY",
                    "duplicate source record key within one capture",
                    record_key=key,
                    artifact=name,
                )
            )

    for record in records:
        if record.available_at > asof:
            findings.append(
                _finding(
                    "FUTURE_DATA",
                    "record was not available at the audited as-of timestamp",
                    symbol=record.symbol,
                )
            )
        if record.settlement_date > record.publication_date:
            findings.append(
                _finding("TIMING", "settlement follows publication", symbol=record.symbol)
            )

    versions = {record.source_provenance.source_field_map_version for record in records}
    if len(versions) > 1:
        findings.append(
            _finding("SOURCE_VERSION_DRIFT", f"{len(versions)} field-map versions in one partition")
        )

    by_settlement: dict[tuple[str, date], list] = {}
    for record in records:
        by_settlement.setdefault((record.symbol, record.settlement_date), []).append(record)
    for (symbol, _settlement), group in sorted(by_settlement.items()):
        originals = [record for record in group if not record.revision_flag]
        revisions = [record for record in group if record.revision_flag]
        if (
            originals
            and revisions
            and min(r.available_at for r in revisions) < min(o.available_at for o in originals)
        ):
            findings.append(
                _finding("REVISION_ORDER", "a revision predates its original", symbol=symbol)
            )

    return _normalized_report(provider, dataset, publication_date, findings, counts)


def _normalized_report(provider, dataset, publication_date, findings, counts) -> dict:
    return {
        "check": "normalized_partition",
        "provider": provider,
        "dataset": dataset,
        "publication_date": publication_date.isoformat(),
        "status": _status(findings),
        "counts": counts,
        "findings": findings,
    }


def audit_provider_conflicts(
    root: Path, *, dataset: str, providers: tuple[str, ...], asof: datetime
) -> dict:
    """Report disagreement between providers without picking a winner."""
    from data.short_positioning.snapshots import load_latest_available_records

    root = Path(root)
    observed: dict[tuple[str, date], dict[str, int]] = {}
    symbols: set[str] = set()
    findings: list[dict] = []

    for provider in providers:
        base = root / "normalized" / f"provider={provider}" / f"dataset={dataset}"
        for partition in sorted(base.glob(f"publication_date=*/{NORMALIZED_FILE_GLOB}")):
            try:
                document = json.loads(partition.read_text())
                for row in document.get("records", []):
                    symbols.add(row["symbol"])
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                # A corrupt or malformed partition is exactly what this audit
                # exists to diagnose; report it as a blocking finding instead
                # of letting the exception end the whole audit run.
                findings.append(
                    _finding(
                        "SCHEMA_ERROR",
                        f"partition is not readable: {exc}",
                        artifact=partition.name,
                        provider=provider,
                    )
                )

    for symbol in sorted(symbols):
        for provider in providers:
            try:
                records = load_latest_available_records(
                    root, provider=provider, dataset=dataset, symbol=symbol, asof=asof
                )
            except ShortPositioningSchemaError as exc:
                findings.append(
                    _finding(
                        "SCHEMA_ERROR",
                        f"stored data failed validation: {exc}",
                        symbol=symbol,
                        provider=provider,
                    )
                )
                continue
            for record in records:
                key = (record.symbol, record.settlement_date)
                observed.setdefault(key, {})[provider] = record.current_short_shares

    for (symbol, settlement), by_provider in sorted(observed.items()):
        if len(by_provider) > 1 and len(set(by_provider.values())) > 1:
            findings.append(
                _finding(
                    "PROVIDER_CONFLICT",
                    "providers report different positions for this settlement date",
                    symbol=symbol,
                    settlement_date=settlement.isoformat(),
                    providers=sorted(by_provider),
                )
            )

    return {
        "check": "provider_conflicts",
        "dataset": dataset,
        "providers": list(providers),
        "status": _status(findings),
        "counts": {"compared": len(observed), "symbols": len(symbols)},
        "findings": findings,
    }


def _redact(value):
    if isinstance(value, str):
        return _SECRET_PATTERN.sub(rf"\1\2{REDACTED}", value)
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def render_short_positioning_audit(report: dict) -> str:
    """Human-readable audit summary. Counts and codes only."""
    lines = ["Short-positioning audit", f"  root: {report.get('root', 'unknown')}"]
    for check in report.get("checks", []):
        lines.append(f"  [{check['status']}] {check['check']} {check.get('publication_date', '')}")
        for key, value in sorted(check.get("counts", {}).items()):
            lines.append(f"      {key}: {value}")
        for finding in check.get("findings", []):
            detail = finding.get("detail", "")
            lines.append(f"      - {finding['code']}: {detail}")
    overall = BLOCK if any(c["status"] == BLOCK for c in report.get("checks", [])) else PASS
    lines.append(f"  overall: {overall}")
    return _redact("\n".join(lines))


def write_short_positioning_audit_receipt(report: dict, path: Path) -> Path:
    """Write a redacted receipt. Never contains a row value or a credential."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_redact(report), sort_keys=True, indent=2) + "\n")
    return path
