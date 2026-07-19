"""Small immutable receipt primitives shared by H7 command boundaries."""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

from research.hashing import canonical_json, sha256_file, sha256_hex


def _json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def durable_sync(fd: int) -> None:
    os.fsync(fd)
    if sys.platform == "darwin":
        import fcntl

        fcntl.fcntl(fd, fcntl.F_FULLFSYNC)


def input_file_record(path: Path) -> dict:
    """Return a hash record that distinguishes a missing file from a file."""
    path = Path(path)
    if not path.is_file():
        return {"path": str(path), "exists": False, "sha256": None}
    return {"path": str(path), "exists": True, "sha256": sha256_file(path)}


def input_files(paths: dict[str, Path]) -> dict[str, dict]:
    return {label: input_file_record(path)
            for label, path in sorted(paths.items())}


def changed_input_files(receipt: dict) -> list[str]:
    """Re-hash ordinary file bindings carried by a receipt."""
    changed = []
    for label, stored in sorted(receipt.get("input_files", {}).items()):
        if not isinstance(stored, dict) or "path" not in stored:
            continue  # directory inventories have their own verifier
        actual = input_file_record(Path(stored["path"]))
        if canonical_json(actual) != canonical_json(stored):
            changed.append(label)
    return changed


def make_receipt(receipt_type: str, payload: dict) -> dict:
    """Build a content-addressed receipt; no wall-clock field is inferred."""
    raw = {
        "receipt_schema": "h7-receipt/v1",
        "receipt_type": receipt_type,
        **payload,
    }
    body = {key: _json_safe(value) for key, value in raw.items()}
    body["receipt_hash"] = sha256_hex(canonical_json(body))
    return body


def verify_receipt(receipt: dict) -> list[str]:
    """Return integrity failures; an empty list means the JSON is intact."""
    if not isinstance(receipt, dict):
        return ["root_not_object"]
    stored = receipt.get("receipt_hash")
    if not isinstance(stored, str):
        return ["receipt_hash_missing"]
    body = {key: value for key, value in receipt.items()
            if key != "receipt_hash"}
    return [] if sha256_hex(canonical_json(body)) == stored else ["receipt_hash"]


def load_receipt(path: Path, *, expected_type: str | None = None) -> dict:
    path = Path(path)
    receipt = json.loads(path.read_text())
    failures = verify_receipt(receipt)
    if failures:
        raise ValueError(f"tampered H7 receipt {path}: {failures}")
    if expected_type is not None and receipt.get("receipt_type") != expected_type:
        raise ValueError(
            f"receipt {path} has type {receipt.get('receipt_type')!r}, "
            f"expected {expected_type!r}")
    return receipt


def write_immutable_receipt(receipt: dict, path: Path) -> str:
    """Create a receipt once; identical replay is allowed, overwrite is not."""
    failures = verify_receipt(receipt)
    if failures:
        raise ValueError(f"refusing invalid H7 receipt: {failures}")
    path = Path(path)
    payload = canonical_json(receipt) + "\n"
    if path.exists():
        if path.read_text() == payload:
            return str(receipt["receipt_hash"])
        raise FileExistsError(f"refusing to overwrite H7 receipt: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        data = payload.encode("utf-8")
        offset = 0
        while offset < len(data):
            offset += os.write(fd, data[offset:])
        durable_sync(fd)
    except BaseException:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise
    finally:
        os.close(fd)
    os.replace(tmp, path)
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        durable_sync(dir_fd)
    finally:
        os.close(dir_fd)
    return str(receipt["receipt_hash"])
