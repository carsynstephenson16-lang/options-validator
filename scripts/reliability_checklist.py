from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

ADVISORY_BOUNDARY = (
    "ADVISORY ONLY: this report cannot authorize trading, change research verdicts, "
    "modify evidence, enable outreach, or promote controls."
)
AUTHORED_STATUSES = {
    "ENFORCED",
    "MANUAL",
    "ADVISORY",
    "GAP",
    "NOT_APPLICABLE",
    "SUPERSEDED",
}
ALL_STATUSES = tuple(sorted(AUTHORED_STATUSES | {"STALE"}))
SHA256_LENGTH = 64
MLTS_CATEGORIES = {
    "DATA": "data",
    "INFRA": "infrastructure",
    "MODEL": "model",
    "MONITOR": "monitoring",
}


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}") from exc
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_path(root: Path, raw: object) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("evidence path must be nonempty text")
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("evidence paths must be repository-relative and cannot contain '..'")
    candidate = (root / relative).resolve()
    resolved_root = root.resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise ValueError("evidence path must remain repository-relative")
    return candidate


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )


def _git_state(root: Path) -> tuple[str | None, str]:
    head = _git(root, "rev-parse", "HEAD")
    repository_sha = head.stdout.strip() if head.returncode == 0 else None
    status = _git(root, "status", "--short")
    if status.returncode != 0:
        return repository_sha, "unborn or unavailable Git HEAD; working-tree state unavailable"
    detail = status.stdout.strip()
    return repository_sha, "clean" if not detail else f"dirty:\n{detail}"


@lru_cache(maxsize=256)
def _is_ancestor(root: Path, reviewed: str, current: str | None) -> bool:
    if current is None:
        return False
    result = _git(root, "merge-base", "--is-ancestor", reviewed, current)
    return result.returncode == 0


def _parse_utc(raw: object, field: str) -> datetime:
    if not isinstance(raw, str):
        raise TypeError(f"{field} must be a UTC timestamp")
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(UTC)


def _validate_evidence(
    root: Path,
    evidence: object,
    *,
    repository_sha: str | None,
) -> list[str]:
    if not isinstance(evidence, list):
        raise TypeError("mapping evidence must be an array")
    reasons: list[str] = []
    for record in evidence:
        if not isinstance(record, dict):
            raise TypeError("evidence entries must be objects")
        kind = record.get("kind")
        if kind not in {
            "command_receipt",
            "config_value",
            "document_procedure",
            "file_symbol",
            "runtime_state",
        }:
            raise ValueError(f"unknown evidence kind: {kind!r}")
        raw_path = record.get("receipt_path") if kind == "command_receipt" else record.get("path")
        path = _relative_path(root, raw_path)
        if not path.is_file():
            reasons.append(f"missing evidence path {path.relative_to(root.resolve())}")
            continue
        expected_hash = record.get("sha256")
        if expected_hash is not None:
            if not isinstance(expected_hash, str) or len(expected_hash) != SHA256_LENGTH:
                raise ValueError("evidence sha256 must be 64 lowercase hexadecimal characters")
            if _sha256(path) != expected_hash:
                reasons.append(f"evidence hash changed for {path.relative_to(root.resolve())}")
                continue
        if kind == "file_symbol":
            symbol = record.get("symbol")
            if symbol is not None and (
                not isinstance(symbol, str)
                or symbol not in path.read_text(encoding="utf-8", errors="replace")
            ):
                reasons.append(f"evidence symbol missing from {path.relative_to(root.resolve())}")
        elif kind == "command_receipt":
            command_id = record.get("command_id")
            receipt_file = _load_object(path)
            receipts = receipt_file.get("receipts")
            if not isinstance(receipts, dict) or command_id not in receipts:
                reasons.append(f"command receipt {command_id!r} is missing")
                continue
            receipt = receipts[command_id]
            if not isinstance(receipt, dict):
                reasons.append(f"command receipt {command_id!r} is malformed")
                continue
            argv = receipt.get("argv")
            if (
                not isinstance(argv, list)
                or not argv
                or any(not isinstance(part, str) or not part for part in argv)
            ):
                reasons.append(f"command receipt {command_id!r} has invalid structured argv")
            if receipt.get("exit_code") != 0:
                reasons.append(f"command receipt {command_id!r} did not pass")
            receipt_sha = receipt.get("repository_sha")
            if not isinstance(receipt_sha, str) or not _is_ancestor(
                root, receipt_sha, repository_sha
            ):
                reasons.append(f"command receipt {command_id!r} is not in current Git ancestry")
    return reasons


def score_priority(priority: dict[str, Any], *, gap_item_ids: frozenset[str]) -> dict[str, Any]:
    input_fields = (
        "risk_reduction",
        "recurrence",
        "auditability_gain",
        "cross_project_reuse",
        "implementation_effort",
        "maintenance_burden",
    )
    inputs: dict[str, int] = {}
    for field in input_fields:
        value = priority.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError(f"priority {field} must be an integer from 1 through 5")
        inputs[field] = value
    item_ids = priority.get("item_ids")
    if (
        not isinstance(item_ids, list)
        or not item_ids
        or any(not isinstance(item_id, str) for item_id in item_ids)
    ):
        raise ValueError("priority item_ids must be a nonempty string array")
    benefit = (
        inputs["risk_reduction"] * 0.40
        + inputs["recurrence"] * 0.20
        + inputs["auditability_gain"] * 0.20
        + inputs["cross_project_reuse"] * 0.20
    )
    cost = inputs["implementation_effort"] * 0.70 + inputs["maintenance_burden"] * 0.30
    score = round(20 * benefit / cost, 2)
    equivalent = priority.get("equivalent_evidence")
    if not isinstance(equivalent, bool):
        raise TypeError("priority equivalent_evidence must be boolean")
    has_gap = bool(set(item_ids) & gap_item_ids)
    if equivalent or not has_gap:
        band = "BUILD_NOTHING"
    elif score < 25:
        band = "KEEP_MANUAL"
    elif score < 40:
        band = "ISOLATED_PILOT"
    else:
        band = "AUTOMATION_CANDIDATE"
    return {
        "priority_id": str(priority.get("priority_id", "")),
        "item_ids": item_ids,
        "proposed_control": str(priority.get("proposed_control", "")),
        "equivalent_evidence": equivalent,
        "inputs": inputs,
        "priority_score": score,
        "decision_band": band,
        "owner_decision_required": str(priority.get("owner_decision_required", "")),
    }


def _mlts_score(
    mappings: dict[str, dict[str, Any]],
    effective_status: dict[str, str],
    applicability: object,
) -> dict[str, Any] | None:
    if applicability == "NOT_AN_ML_SYSTEM":
        return None
    if applicability != "APPLICABLE":
        raise ValueError("mlts_applicability must be APPLICABLE or NOT_AN_ML_SYSTEM")
    category_scores = dict.fromkeys(MLTS_CATEGORIES.values(), 0)
    category_counts = dict.fromkeys(MLTS_CATEGORIES.values(), 0)
    modified = False
    points = {"ENFORCED": 2, "MANUAL": 1}
    for item_id, mapping in mappings.items():
        if not item_id.startswith("MLTS-"):
            continue
        parts = item_id.split("-")
        category = MLTS_CATEGORIES.get(parts[1])
        if category is None:
            raise ValueError(f"unknown MLTS category in {item_id}")
        category_counts[category] += 1
        if mapping["status"] == "NOT_APPLICABLE":
            modified = True
        category_scores[category] += points.get(effective_status[item_id], 0)
    if any(count != 7 for count in category_counts.values()):
        raise ValueError("catalog must contain four MLTS categories of seven items")
    return {
        "category_scores": category_scores,
        "final_score": min(category_scores.values()),
        "modified_applicability": modified,
        "scoring_note": (
            "Minimum of the four seven-item category totals; ENFORCED=2, MANUAL=1, "
            "all other effective statuses=0."
        ),
    }


def audit_repository(
    repository_root: Path,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    root = repository_root.resolve()
    reliability = root / "docs" / "reliability"
    lock = _load_object(reliability / "catalog.lock.json")
    snapshot_path = _relative_path(root, lock.get("snapshot_path"))
    expected_digest = lock.get("catalog_sha256")
    if (
        not isinstance(expected_digest, str)
        or len(expected_digest) != SHA256_LENGTH
        or _sha256(snapshot_path) != expected_digest
    ):
        raise ValueError("catalog snapshot digest mismatch")
    snapshot = _load_object(snapshot_path)
    profile = _load_object(reliability / "profile.json")
    if lock.get("catalog_version") != snapshot.get("catalog_version"):
        raise ValueError("catalog lock version mismatch")
    if profile.get("catalog_version") != snapshot.get("catalog_version"):
        raise ValueError("profile catalog version mismatch")
    if profile.get("catalog_sha256") != expected_digest:
        raise ValueError("profile catalog digest mismatch")
    if lock.get("advisory_boundary") != ADVISORY_BOUNDARY:
        raise ValueError("catalog lock advisory boundary mismatch")

    items = snapshot.get("items")
    sources = snapshot.get("source_identities")
    crosswalks = snapshot.get("crosswalks")
    mappings_raw = profile.get("mappings")
    priorities = profile.get("priorities")
    if (
        not isinstance(items, list)
        or not isinstance(sources, list)
        or not isinstance(crosswalks, list)
    ):
        raise TypeError("catalog snapshot arrays are malformed")
    if not isinstance(mappings_raw, list) or not isinstance(priorities, list):
        raise TypeError("profile mappings and priorities must be arrays")
    item_by_id = {str(item["item_id"]): item for item in items if isinstance(item, dict)}
    mappings: dict[str, dict[str, Any]] = {}
    for mapping in mappings_raw:
        if not isinstance(mapping, dict):
            raise TypeError("profile mappings must be objects")
        item_id = mapping.get("item_id")
        if not isinstance(item_id, str) or item_id in mappings:
            raise ValueError(f"duplicate or invalid profile item_id {item_id!r}")
        mappings[item_id] = mapping
    if set(mappings) != set(item_by_id):
        missing = sorted(set(item_by_id) - set(mappings))
        extra = sorted(set(mappings) - set(item_by_id))
        raise ValueError(f"profile mapping mismatch missing={missing[:3]} extra={extra[:3]}")

    repository_sha, dirty_disclosure = _git_state(root)
    checked_at = (now or datetime.now(UTC)).astimezone(UTC)
    effective_status: dict[str, str] = {}
    stale_findings: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    status_counts: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(ALL_STATUSES, 0))
    local_controls: dict[str, list[str]] = defaultdict(list)
    evidence_cache: dict[str, list[str]] = {}

    for item_id in sorted(mappings):
        mapping = mappings[item_id]
        status = mapping.get("status")
        if status not in AUTHORED_STATUSES:
            raise ValueError(f"{item_id}: invalid authored status {status!r}")
        raw_evidence = mapping.get("evidence")
        evidence_key = json.dumps(raw_evidence, sort_keys=True, separators=(",", ":"))
        if evidence_key not in evidence_cache:
            evidence_cache[evidence_key] = _validate_evidence(
                root,
                raw_evidence,
                repository_sha=repository_sha,
            )
        reasons = list(evidence_cache[evidence_key])
        reviewed = mapping.get("reviewed_at_commit")
        if status in {"ENFORCED", "MANUAL", "SUPERSEDED"}:
            if not isinstance(reviewed, str) or not _is_ancestor(root, reviewed, repository_sha):
                reasons.append("reviewed commit is not in current Git ancestry")
            if not mapping.get("evidence"):
                reasons.append(f"{status} requires evidence")
        elif reviewed is not None and (
            not isinstance(reviewed, str) or not _is_ancestor(root, reviewed, repository_sha)
        ):
            reasons.append("reviewed commit is not in current Git ancestry")
        expires_at = mapping.get("expires_at")
        if status == "NOT_APPLICABLE":
            if expires_at is None or _parse_utc(expires_at, f"{item_id}.expires_at") <= checked_at:
                reasons.append("NOT_APPLICABLE rationale expired or has no expiry")
        elif expires_at is not None:
            _parse_utc(expires_at, f"{item_id}.expires_at")
        effective = "STALE" if reasons else str(status)
        effective_status[item_id] = effective
        item = item_by_id[item_id]
        source_id = str(item["source_id"])
        status_counts[source_id][effective] += 1
        local_control_id = mapping.get("local_control_id")
        if isinstance(local_control_id, str) and local_control_id:
            local_controls[local_control_id].append(item_id)
        if reasons:
            stale_findings.append(
                {
                    "item_id": item_id,
                    "local_control_id": local_control_id,
                    "reason": "; ".join(reasons),
                }
            )
        elif effective == "GAP":
            gaps.append(
                {
                    "item_id": item_id,
                    "local_control_id": local_control_id,
                    "reason": str(
                        mapping.get("notes") or "Applicable control lacks sufficient evidence."
                    ),
                }
            )

    consolidations = [
        {"local_control_id": control_id, "item_ids": sorted(item_ids)}
        for control_id, item_ids in sorted(local_controls.items())
        if len(item_ids) >= 2
    ]
    gap_ids = frozenset(item["item_id"] for item in gaps)
    priority_reports = [
        score_priority(priority, gap_item_ids=gap_ids)
        for priority in priorities
        if isinstance(priority, dict)
    ]
    priority_reports.sort(key=lambda item: (-item["priority_score"], item["priority_id"]))
    return {
        "schema_version": 1,
        "catalog_digest": expected_digest,
        "repository_sha": repository_sha,
        "dirty_state_disclosure": dirty_disclosure,
        "source_status_counts": dict(sorted(status_counts.items())),
        "stale_findings": stale_findings,
        "gaps": gaps,
        "crosswalk_consolidations": consolidations,
        "mlts_score": _mlts_score(mappings, effective_status, profile.get("mlts_applicability")),
        "priority_candidates": priority_reports,
        "advisory_boundary": ADVISORY_BOUNDARY,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Reliability checklist advisory report",
        "",
        report["advisory_boundary"],
        "",
        f"- Catalog SHA-256: `{report['catalog_digest']}`",
        f"- Repository SHA: `{report['repository_sha'] or 'UNBORN'}`",
        f"- Dirty state: {report['dirty_state_disclosure']}",
        f"- Stale mappings: {len(report['stale_findings'])}",
        f"- Verified gaps: {len(report['gaps'])}",
        "",
        "## Status by source",
        "",
        "| Source | ENFORCED | MANUAL | ADVISORY | GAP | N/A | SUPERSEDED | STALE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for source_id, counts in report["source_status_counts"].items():
        lines.append(
            f"| {source_id} | {counts['ENFORCED']} | {counts['MANUAL']} | "
            f"{counts['ADVISORY']} | {counts['GAP']} | {counts['NOT_APPLICABLE']} | "
            f"{counts['SUPERSEDED']} | {counts['STALE']} |"
        )
    lines.extend(["", "## Marginal-value candidates", ""])
    if not report["priority_candidates"]:
        lines.append("- None declared.")
    for candidate in report["priority_candidates"]:
        lines.append(
            f"- `{candidate['priority_id']}`: {candidate['decision_band']} "
            f"({candidate['priority_score']:.2f}) — {candidate['proposed_control']}"
        )
    lines.extend(["", "Every experiment or promotion still requires explicit approval.", ""])
    return "\n".join(lines)


def _default_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "docs" / "reliability" / "catalog.lock.json").is_file():
            return parent
    return Path.cwd()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reliability-checklist")
    parser.add_argument("--root", type=Path, default=_default_root())
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit")
    audit.add_argument("--format", choices=("json", "markdown", "both"), default="both")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_repository(args.root)
    except (OSError, TypeError, ValueError) as exc:
        print(f"reliability audit failed: {exc}", file=sys.stderr)
        return 1
    if args.format in {"json", "both"}:
        print(json.dumps(report, indent=2, sort_keys=True))
    if args.format == "both":
        print("\n---\n")
    if args.format in {"markdown", "both"}:
        print(render_markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
