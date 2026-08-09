"""Restic backup and restore checks for H7 forward evidence.

Restic supplies encryption and remote-provider support; this module supplies
the allow-list, receipt contract, and restore verification. It never accepts a
password on the command line. Configure ``RESTIC_REPOSITORY`` and either
``RESTIC_PASSWORD_COMMAND`` or ``RESTIC_PASSWORD_FILE`` in the environment.

No command in this module is run by the H7 watcher or activation check. The
owner runs ``backup`` after a completed refresh and ``restore-check`` during a
restore drill; activation consumes the resulting immutable receipt.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from options_researcher.h7_scope import scope_identity
from research.hashing import sha256_file
from research.receipts import (
    input_file_record,
    load_receipt,
    make_receipt,
    write_immutable_receipt,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKUP_TAG = "options-validator-h7-forward"

# Explicit allow-list: no broad .cache/ or repository-root backup is allowed.
BACKUP_PATHS = (
    Path(".cache/chains"),
    Path(".cache/schwab_chains"),
    Path(".cache/underlying"),
    Path("data/earnings/gating_v3.csv"),
    Path("data/earnings/assertions_v2.csv"),
    Path("data/earnings/assertions.csv"),
    Path("data/chain_cache_manifest.txt"),
    Path("ledger/facts.log"),
    Path("reports/h7_data_gate"),
    Path("reports/h7_receipts"),
    Path("reports/h7_forward"),
    Path("reports/schwab_chains"),
    Path("reports/h7_forward_schwab"),
    Path("ledger/h7_forward_schwab"),
)
EXCLUDE_PATTERNS = (
    ".env", ".env.*", "*.pem", "*.key", "credentials*", ".tmp/*",
    "__pycache__/*", "*.pyc",
)


def backup_paths(root: Path = REPO_ROOT) -> list[Path]:
    """Return only existing allow-listed paths, resolved under ``root``."""
    root = Path(root).resolve()
    return [root / relative for relative in BACKUP_PATHS
            if (root / relative).exists()]


def backup_inventory(root: Path = REPO_ROOT) -> dict[str, dict]:
    """Hash files and directory contents included in the Restic allow-list."""
    root = Path(root).resolve()
    inventory = {}
    for path in backup_paths(root):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            files = {}
            for child in sorted(p for p in path.rglob("*") if p.is_file()):
                child_rel = child.relative_to(root).as_posix()
                if any(fnmatch.fnmatch(child_rel, pattern)
                       or fnmatch.fnmatch(child.name, pattern)
                       for pattern in EXCLUDE_PATTERNS):
                    continue
                files[child_rel] = {
                    "sha256": sha256_file(child), "size": child.stat().st_size,
                }
            inventory[relative] = {"kind": "directory", "files": files}
        else:
            inventory[relative] = {
                "kind": "file", "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
    return inventory


def _require_restic_environment() -> None:
    if not os.environ.get("RESTIC_REPOSITORY"):
        raise RuntimeError("RESTIC_REPOSITORY is required")
    if not (os.environ.get("RESTIC_PASSWORD_COMMAND") or
            os.environ.get("RESTIC_PASSWORD_FILE")):
        raise RuntimeError(
            "set RESTIC_PASSWORD_COMMAND or RESTIC_PASSWORD_FILE; "
            "passwords are never accepted as command arguments")


def _run_restic(args: list[str], *, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    _require_restic_environment()
    return subprocess.run(["restic", *args], cwd=cwd, text=True,
                          capture_output=True, check=True)


def _snapshot_id(stdout: str) -> str:
    """Extract the last JSON snapshot id from ``restic backup --json``."""
    found = None
    for line in stdout.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("snapshot_id"):
            found = str(value["snapshot_id"])
    if not found:
        raise RuntimeError("restic backup returned no snapshot id")
    return found


def run_backup(*, completed_session: str, root: Path = REPO_ROOT,
               receipt_path: Path | None = None) -> Path:
    """Create an encrypted restic snapshot and an immutable backup receipt."""
    root = Path(root).resolve()
    paths = backup_paths(root)
    if not paths:
        raise RuntimeError("no H7 backup inputs exist; refusing empty backup")
    relative_paths = [str(path.relative_to(root)) for path in paths]
    args = ["backup", "--json", "--tag", BACKUP_TAG,
            *[item for pattern in EXCLUDE_PATTERNS
              for item in ("--exclude", pattern)],
            *relative_paths]
    result = _run_restic(args, cwd=root)
    snapshot = _snapshot_id(result.stdout)
    payload = {
        "completed_session": completed_session,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_id": snapshot,
        "tag": BACKUP_TAG,
        "scope": scope_identity(),
        "input_files": backup_inventory(root),
        "excluded_patterns": list(EXCLUDE_PATTERNS),
        "encrypted_by_restic": True,
    }
    receipt = make_receipt("backup", payload)
    path = (Path(receipt_path) if receipt_path else
            root / "reports/h7_receipts/backup" /
            f"{completed_session}.json")
    write_immutable_receipt(receipt, path)
    return path


def _rebase_record(record: dict, restored_root: Path) -> dict:
    original = Path(record["path"])
    try:
        relative = original.resolve().relative_to(REPO_ROOT)
    except (ValueError, OSError):
        relative = Path(str(original).lstrip("/"))
    candidate = restored_root / relative
    return input_file_record(candidate)


def verify_restored_tree(restored_root: Path) -> dict:
    """Verify manifest bytes and every restored H7 receipt/data-gate input."""
    restored_root = Path(restored_root).resolve()
    checks = {"manifest": "NOT_PRESENT", "receipts": 0, "data_gates": 0,
              "problems": []}
    manifest = restored_root / "data/chain_cache_manifest.txt"
    chains = restored_root / ".cache/chains"
    if manifest.exists() and chains.exists():
        from tools.cache_manifest import verify_manifest

        checks["manifest"] = "OK" if not (problems := verify_manifest(
            str(chains), str(manifest))) else "BLOCK"
        checks["problems"].extend(problems)
    elif manifest.exists() or chains.exists():
        checks["manifest"] = "BLOCK"
        checks["problems"].append("manifest and chain cache must restore together")

    receipt_root = restored_root / "reports/h7_receipts"
    receipt_paths = list(receipt_root.rglob("*.json")) if receipt_root.exists() else []
    # data_gate receipts are written under reports/h7_data_gate/<scope>/receipts/,
    # NOT reports/h7_receipts -- scan that tree too, or a restored data_gate is
    # never counted and verification fails closed with data_gates=0 even on a
    # complete backup (found by the 2026-07-20 restore drill).
    dg_root = restored_root / "reports/h7_data_gate"
    if dg_root.exists():
        receipt_paths += list(dg_root.glob("*/receipts/*.json"))
    for path in sorted(receipt_paths):
        try:
            receipt = load_receipt(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            checks["problems"].append(f"{path}: {exc}")
            continue
        checks["receipts"] += 1
        if receipt.get("receipt_type") != "data_gate":
            continue
        checks["data_gates"] += 1
        if (receipt.get("scope") != scope_identity()
                or receipt.get("whole_universe_verdict") != "GO"
                or receipt.get("go_count") != len(scope_identity()["symbols"])):
            checks["problems"].append(f"{path}: stale scope")
        for label, record in receipt.get("input_files", {}).items():
            actual = _rebase_record(record, restored_root)
            if (actual.get("exists") != record.get("exists")
                    or actual.get("sha256") != record.get("sha256")):
                checks["problems"].append(f"{path}: changed input {label}")
    checks["ok"] = not checks["problems"] and checks["data_gates"] > 0
    return checks


def run_restore_check(*, snapshot: str = "latest", completed_session: str,
                      root: Path = REPO_ROOT,
                      receipt_path: Path | None = None) -> Path:
    """Restore into a temporary directory, verify it, then write evidence."""
    root = Path(root).resolve()
    with tempfile.TemporaryDirectory(prefix="h7-restic-restore-") as temp:
        _run_restic(["restore", snapshot, "--target", temp,
                     "--tag", BACKUP_TAG], cwd=root)
        verification = verify_restored_tree(Path(temp))
        if not verification["ok"]:
            raise RuntimeError(f"restored H7 state failed verification: {verification}")
    receipt = make_receipt("backup_restore", {
        "completed_session": completed_session,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot": snapshot,
        "scope": scope_identity(),
        "verification": verification,
    })
    path = (Path(receipt_path) if receipt_path else
            root / "reports/h7_receipts/backup_restore" /
            f"{datetime.now(timezone.utc).date().isoformat()}.json")
    write_immutable_receipt(receipt, path)
    return path


def backup_receipt_is_fresh(path: Path, *, completed_session: str) -> bool:
    """Activation freshness rule: backup must cover the current completed session."""
    receipt = load_receipt(path, expected_type="backup_restore")
    return (receipt.get("scope") == scope_identity()
            and receipt.get("verification", {}).get("ok") is True
            and receipt.get("verified_at_utc") is not None
            and receipt.get("completed_session") == completed_session)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    backup = sub.add_parser("backup")
    backup.add_argument("--completed-session", required=True)
    backup.add_argument("--receipt", type=Path)
    restore = sub.add_parser("restore-check")
    restore.add_argument("--snapshot", default="latest")
    restore.add_argument("--completed-session", required=True)
    restore.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        path = (run_backup(completed_session=args.completed_session,
                           receipt_path=args.receipt)
                if args.command == "backup" else
                run_restore_check(snapshot=args.snapshot,
                                  completed_session=args.completed_session,
                                  receipt_path=args.receipt))
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"H7 BACKUP ERROR -- {type(exc).__name__}: {exc}")
        return 2
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
