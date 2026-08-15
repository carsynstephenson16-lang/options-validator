"""Restic backup and restore checks for H7 forward evidence.

Restic supplies encryption and remote-provider support; this module supplies
the allow-list, receipt contract, and restore verification. It never accepts a
password on the command line. Configure ``RESTIC_REPOSITORY`` and either
``RESTIC_PASSWORD_COMMAND`` or ``RESTIC_PASSWORD_FILE`` in the environment.

No command in this module is run by the H7 watcher or activation check. The
owner runs ``backup`` after a completed refresh and ``restore-check`` during a
restore drill; activation consumes the resulting immutable receipt.

Recorded input-binding invalidations (drill disposition B, owner-directed
in-session 2026-08-14, ``reports/2026-08-14-owner-answers-decision-menu.md``
ruling 1): the restore check re-hashes every input a sealed receipt binds,
inside the restored tree. When an owner-approved data refresh rewrites bytes a
sealed receipt already committed to, that binding becomes permanently
unverifiable -- the pre-refresh bytes are gone and the receipt is append-only,
so it can never be repointed. Disposition B says: record the invalidation
explicitly, then accept exactly what was recorded. ``record-invalidation``
appends a typed fact through ``research/facts.py``; the restore check then turns
a mismatch into PASS-WITH-NOTE only when a well-formed fact names that exact
receipt (by content hash), that exact label, and that exact sealed hash. Every
uncovered mismatch still FAILS, and a malformed or partial fact covers nothing.

Deliberate limit of the mechanism, stated so nobody reads more into it: a
recorded invalidation pins the SEALED side of the binding, not the replacement.
The observed post-refresh hash is recorded as evidence but is not a coverage
condition, because the closes cache is refreshed on an ordinary operating
cadence; pinning the replacement would re-break the drill -- and invite a
reflexive "append another fact" habit -- every refresh. The covered binding is
already unverifiable forever, so nothing further is given up. Coverage never
extends to a missing file: a vanished input is data loss, not drift, and fails.
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
from typing import TypeGuard

from options_researcher.h7_scope import scope_identity
from research.facts import append_fact, read_facts
from research.hashing import canonical_json, sha256_file, sha256_hex
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


INVALIDATION_TOKEN = "H7_INPUT_BINDING_INVALIDATION"
INVALIDATION_SCHEMA = "h7-input-binding-invalidation/v1"
# Exact key set: a record missing a field, or carrying an unexpected one, is a
# partial/garbled record and must cover nothing.
INVALIDATION_KEYS = frozenset({
    "schema", "receipt", "receipt_hash", "bindings", "observed",
    "invalidated_by", "recorded_session", "provenance",
})
_HEX = frozenset("0123456789abcdef")


def _is_sha256(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX


def _is_nonempty_text(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and bool(value.strip())


def _is_hash_map(value: object, *, allow_empty: bool) -> bool:
    if not isinstance(value, dict) or (not value and not allow_empty):
        return False
    return all(_is_nonempty_text(label) and _is_sha256(digest)
               for label, digest in value.items())


def parse_invalidation_fact(text: str) -> dict | None:
    """Return the payload of a well-formed invalidation fact, else ``None``.

    Fail closed in every direction: an unknown token, unparseable JSON, a
    missing or extra field, a non-hex hash, an absolute or traversing receipt
    path, or a path that disagrees with the payload all yield ``None`` (covers
    nothing), never a partial acceptance.
    """
    if not isinstance(text, str) or not text.startswith(f"{INVALIDATION_TOKEN} "):
        return None
    receipt_path, separator, body = text[len(INVALIDATION_TOKEN) + 1:].partition(" ")
    if not separator:
        return None
    try:
        payload = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict) or set(payload) != INVALIDATION_KEYS:
        return None
    if payload["schema"] != INVALIDATION_SCHEMA:
        return None
    receipt = payload["receipt"]
    if (not _is_nonempty_text(receipt) or receipt != receipt_path
            or receipt.startswith("/") or "\\" in receipt
            or ".." in Path(receipt).parts):
        return None
    if not _is_sha256(payload["receipt_hash"]):
        return None
    if not _is_hash_map(payload["bindings"], allow_empty=False):
        return None
    if not _is_hash_map(payload["observed"], allow_empty=True):
        return None
    if not all(_is_nonempty_text(payload[key])
               for key in ("invalidated_by", "recorded_session", "provenance")):
        return None
    return payload


def invalidation_fact_id(payload: dict) -> str:
    """Stable short id for a fact line (facts.log itself is not hash-chained)."""
    return sha256_hex(canonical_json(payload))[:12]


def load_invalidations(ledger_dir: Path) -> dict[tuple[str, str, str], dict]:
    """Index recorded invalidations by (receipt hash, label, sealed hash)."""
    index: dict[tuple[str, str, str], dict] = {}
    for line in read_facts(str(ledger_dir)):
        _, separator, text = line.partition("\t")
        if not separator:
            continue
        payload = parse_invalidation_fact(text.rstrip("\n"))
        if payload is None:
            continue
        for label, sealed in payload["bindings"].items():
            index[(payload["receipt_hash"], label, sealed)] = payload
    return index


def _covering_invalidation(*, receipt_relative: str, receipt: dict, label: str,
                           stored: dict, actual: dict,
                           index: dict[tuple[str, str, str], dict]) -> dict | None:
    """Return the fact covering this exact mismatch, or ``None``.

    Covers only a CHANGED hash of a still-present file whose sealed hash the
    fact names. A missing (or newly appearing) input is never covered.
    """
    if stored.get("exists") is not True or actual.get("exists") is not True:
        return None
    sealed = stored.get("sha256")
    if not _is_sha256(sealed) or not _is_sha256(actual.get("sha256")):
        return None
    receipt_hash = receipt.get("receipt_hash")
    if not _is_sha256(receipt_hash):
        return None
    payload = index.get((receipt_hash, label, sealed))
    if payload is None:
        return None
    # The receipt is identified by its content hash; the recorded path must
    # still agree with where the receipt actually restored (the restore layout
    # may carry a prefix, so a trailing-component match is what is required).
    recorded = payload["receipt"]
    if receipt_relative != recorded and not receipt_relative.endswith(f"/{recorded}"):
        return None
    return payload


def _rebase_record(record: dict, restored_root: Path) -> dict:
    original = Path(record["path"])
    try:
        relative = original.resolve().relative_to(REPO_ROOT)
    except (ValueError, OSError):
        relative = Path(str(original).lstrip("/"))
    candidate = restored_root / relative
    return input_file_record(candidate)


def verify_restored_tree(restored_root: Path, *,
                         invalidations: dict | None = None) -> dict:
    """Verify manifest bytes and every restored H7 receipt/data-gate input.

    ``invalidations`` defaults to the facts recorded INSIDE the restored tree:
    the acceptance evidence has to be part of the backup being drilled, not
    supplied by whatever happens to be on the operator's disk today.
    """
    restored_root = Path(restored_root).resolve()
    checks = {"manifest": "NOT_PRESENT", "receipts": 0, "data_gates": 0,
              "problems": [], "notes": []}
    if invalidations is None:
        invalidations = load_invalidations(restored_root / "ledger")
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
        try:
            receipt_relative = path.resolve().relative_to(restored_root).as_posix()
        except (ValueError, OSError):
            receipt_relative = ""
        for label, record in sorted(receipt.get("input_files", {}).items()):
            actual = _rebase_record(record, restored_root)
            if (actual.get("exists") == record.get("exists")
                    and actual.get("sha256") == record.get("sha256")):
                continue
            covering = _covering_invalidation(
                receipt_relative=receipt_relative, receipt=receipt, label=label,
                stored=record, actual=actual, index=invalidations)
            if covering is None:
                checks["problems"].append(f"{path}: changed input {label}")
                continue
            checks["notes"].append(
                f"{path}: changed input {label} accepted by recorded "
                f"{INVALIDATION_TOKEN} fact id={invalidation_fact_id(covering)} "
                f"recorded_session={covering['recorded_session']} "
                f"invalidated_by={covering['invalidated_by']} "
                f"provenance={covering['provenance']} (ledger/facts.log)")
    checks["ok"] = not checks["problems"] and checks["data_gates"] > 0
    return checks


def run_restore_check(*, backup_receipt_path: Path,
                      completed_session: str,
                      snapshot: str | None = None,
                      root: Path = REPO_ROOT,
                      receipt_path: Path | None = None) -> Path:
    """Restore the receipt-bound snapshot and prove an exact inventory match."""
    root = Path(root).resolve()
    backup_receipt = load_receipt(
        Path(backup_receipt_path), expected_type="backup"
    )
    receipt_session = backup_receipt.get("completed_session")
    if receipt_session != completed_session:
        raise RuntimeError(
            "backup receipt completed session does not match restore request"
        )
    if backup_receipt.get("scope") != scope_identity():
        raise RuntimeError("backup receipt scope does not match current H7 scope")
    receipt_snapshot = backup_receipt.get("snapshot_id")
    if (
        not isinstance(receipt_snapshot, str)
        or not receipt_snapshot
        or receipt_snapshot == "latest"
    ):
        raise RuntimeError("backup receipt carries no exact snapshot id")
    if snapshot is not None and snapshot != receipt_snapshot:
        raise RuntimeError("caller snapshot does not match backup receipt snapshot")
    expected_inventory = backup_receipt.get("input_files")
    if not isinstance(expected_inventory, dict):
        raise RuntimeError("backup receipt carries no input inventory")

    with tempfile.TemporaryDirectory(prefix="h7-restic-restore-") as temp:
        _run_restic(["restore", receipt_snapshot, "--target", temp,
                     "--tag", BACKUP_TAG], cwd=root)
        restored_root = Path(temp)
        restored_inventory = backup_inventory(restored_root)
        if restored_inventory != expected_inventory:
            raise RuntimeError(
                "restored H7 inventory does not exactly match backup receipt"
            )
        verification = verify_restored_tree(restored_root)
        if not verification["ok"]:
            raise RuntimeError(f"restored H7 state failed verification: {verification}")
        for note in verification.get("notes", ()):
            print(f"PASS-WITH-NOTE {note}")
    receipt = make_receipt("backup_restore", {
        "completed_session": completed_session,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot": receipt_snapshot,
        "snapshot_id": receipt_snapshot,
        "backup_receipt_hash": backup_receipt["receipt_hash"],
        "scope": scope_identity(),
        "restored_inventory": restored_inventory,
        "verification": verification,
    })
    path = (Path(receipt_path) if receipt_path else
            root / "reports/h7_receipts/backup_restore" /
            f"{datetime.now(timezone.utc).date().isoformat()}.json")
    write_immutable_receipt(receipt, path)
    return path


def build_invalidation_fact(*, receipt_path: Path, label_prefix: str,
                            invalidated_by: str, recorded_session: str,
                            provenance: str, root: Path = REPO_ROOT) -> str | None:
    """Build the fact line for one sealed receipt, or ``None`` if it is intact.

    Only labels that are ACTUALLY mismatched right now are recorded: a fact
    never pre-authorizes a binding that still verifies.
    """
    root = Path(root).resolve()
    receipt_path = Path(receipt_path)
    if not receipt_path.is_absolute():
        receipt_path = root / receipt_path
    receipt = load_receipt(receipt_path)
    relative = receipt_path.resolve().relative_to(root).as_posix()
    bindings, observed = {}, {}
    for label, record in sorted(receipt.get("input_files", {}).items()):
        if not label.startswith(label_prefix) or record.get("exists") is not True:
            continue
        sealed = record.get("sha256")
        current = input_file_record(root / record["path"])
        if (not _is_sha256(sealed) or current.get("exists") is not True
                or current.get("sha256") == sealed):
            continue
        bindings[label] = sealed
        observed[label] = current["sha256"]
    if not bindings:
        return None
    payload = {
        "schema": INVALIDATION_SCHEMA,
        "receipt": relative,
        "receipt_hash": receipt["receipt_hash"],
        "bindings": bindings,
        "observed": observed,
        "invalidated_by": invalidated_by,
        "recorded_session": recorded_session,
        "provenance": provenance,
    }
    return f"{INVALIDATION_TOKEN} {relative} {canonical_json(payload)}"


def record_invalidations(*, receipt_paths: list[Path], label_prefix: str,
                         invalidated_by: str, recorded_session: str,
                         provenance: str, root: Path = REPO_ROOT,
                         ledger_dir: Path | None = None,
                         dry_run: bool = False) -> list[str]:
    """Append one typed invalidation fact per sealed receipt (append-only)."""
    root = Path(root).resolve()
    ledger_dir = Path(ledger_dir) if ledger_dir else root / "ledger"
    lines = []
    for receipt_path in receipt_paths:
        text = build_invalidation_fact(
            receipt_path=receipt_path, label_prefix=label_prefix,
            invalidated_by=invalidated_by, recorded_session=recorded_session,
            provenance=provenance, root=root)
        if text is None:
            continue
        if parse_invalidation_fact(text) is None:  # never write what cannot be read
            raise RuntimeError(f"refusing to record unparseable fact for {receipt_path}")
        if not dry_run:
            prefix = text[:text.index("{")]
            append_fact(text, str(ledger_dir), dedupe_prefix=prefix)
        lines.append(text)
    return lines


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
    restore.add_argument("--backup-receipt", type=Path, required=True)
    restore.add_argument("--snapshot")
    restore.add_argument("--completed-session", required=True)
    restore.add_argument("--receipt", type=Path)
    record = sub.add_parser(
        "record-invalidation",
        help="append a typed input-binding invalidation fact (disposition B)")
    record.add_argument("--receipt", dest="receipts", type=Path, action="append",
                        required=True, help="sealed receipt (repeatable)")
    record.add_argument("--label-prefix", default="close:")
    record.add_argument("--invalidated-by", required=True)
    record.add_argument("--recorded-session", required=True)
    record.add_argument("--provenance", required=True)
    record.add_argument("--root", type=Path, default=REPO_ROOT,
                        help="tree the receipts' input paths are resolved against")
    record.add_argument("--ledger-dir", type=Path,
                        help="ledger directory to append to (default <root>/ledger)")
    record.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "record-invalidation":
            lines = record_invalidations(
                receipt_paths=args.receipts, label_prefix=args.label_prefix,
                invalidated_by=args.invalidated_by,
                recorded_session=args.recorded_session,
                provenance=args.provenance, root=args.root,
                ledger_dir=args.ledger_dir, dry_run=args.dry_run)
            for line in lines:
                print(line)
            print(f"{'would record' if args.dry_run else 'recorded'} "
                  f"{len(lines)} invalidation fact(s)")
            return 0
        path = (run_backup(completed_session=args.completed_session,
                           receipt_path=args.receipt)
                if args.command == "backup" else
                run_restore_check(backup_receipt_path=args.backup_receipt,
                                  snapshot=args.snapshot,
                                  completed_session=args.completed_session,
                                  receipt_path=args.receipt))
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"H7 BACKUP ERROR -- {type(exc).__name__}: {exc}")
        return 2
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
