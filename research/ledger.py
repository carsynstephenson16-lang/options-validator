"""
research/ledger.py -- append-only, hash-chained JSONL experiment ledger.

The chain IS the tamper-evidence: each record commits to the previous one.
A second tracked file, HEAD, holds the current tip so it is diffable in git.
"""
from __future__ import annotations
from pathlib import Path

from research.hashing import canonical_json, sha256_hex

GENESIS_PREV = "0" * 64
TRIAL_TYPES = {"run", "trial_intent"}
RESERVED_KEYS = {"seq", "prev_hash", "record_hash"}
REPO_ROOT = Path(__file__).resolve().parents[1]


class LedgerError(Exception):
    pass


def _paths(base_dir):
    base = Path(base_dir)
    return base / "experiments.jsonl", base / "HEAD"


def read_all(base_dir="ledger") -> list[dict]:
    jsonl, _ = _paths(base_dir)
    if not jsonl.exists():
        return []
    import json
    records = []
    for lineno, line in enumerate(jsonl.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise LedgerError(f"invalid JSON at ledger line {lineno}: {exc}") from exc
    return records


def tip(base_dir="ledger") -> str:
    _, head = _paths(base_dir)
    return head.read_text().strip() if head.exists() else GENESIS_PREV


def _record_hash(record_without_hash: dict) -> str:
    return sha256_hex(canonical_json(record_without_hash))


def append(body: dict, base_dir="ledger") -> str:
    reserved = RESERVED_KEYS & body.keys()
    if reserved:
        raise LedgerError(f"ledger body uses reserved field(s): {sorted(reserved)}")
    verify(base_dir)
    jsonl, head = _paths(base_dir)
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    records = read_all(base_dir)
    prev = tip(base_dir)
    record = dict(body)
    record["seq"] = len(records)
    record["prev_hash"] = prev
    record["record_hash"] = _record_hash(record)  # record has no record_hash key yet
    with jsonl.open("a") as f:
        f.write(canonical_json(record) + "\n")
    head.write_text(record["record_hash"] + "\n")
    return record["record_hash"]


def verify(base_dir="ledger", anchored=False, git_clean_tracked=None) -> None:
    records = read_all(base_dir)
    prev = GENESIS_PREV
    for i, rec in enumerate(records):
        if rec.get("seq") != i:
            raise LedgerError(f"seq mismatch at index {i}: {rec.get('seq')}")
        if rec.get("prev_hash") != prev:
            raise LedgerError(f"prev_hash break at seq {i}")
        body = {k: v for k, v in rec.items() if k != "record_hash"}
        if rec.get("record_hash") != _record_hash(body):
            raise LedgerError(f"record_hash mismatch at seq {i}")
        prev = rec["record_hash"]
    if tip(base_dir) != prev:
        raise LedgerError("HEAD does not match chain tip")
    if anchored:
        _require_committed_clean(base_dir, git_clean_tracked)


def current_trial_count(base_dir="ledger") -> int:
    return sum(1 for r in read_all(base_dir) if r.get("entry_type") in TRIAL_TYPES)


def _require_committed_clean(base_dir, git_clean_tracked=None) -> None:
    jsonl, head = _paths(base_dir)
    checker = git_clean_tracked or _git_clean_tracked_default
    if not checker([str(jsonl), str(head)]):
        raise LedgerError(
            "ledger not committed / working tree dirty -- commit ledger before OOS reveal")


def _git_clean_tracked_default(paths) -> bool:
    """True iff every path is git-tracked and has no uncommitted changes."""
    import subprocess
    for p in paths:
        tracked = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch", p],
            capture_output=True, text=True)
        if tracked.returncode != 0:
            return False
        status = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--", p],
            capture_output=True, text=True)
        if status.stdout.strip():
            return False
    return True
