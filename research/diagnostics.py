"""research/diagnostics.py -- H7 isolated-lane diagnostic ledger records
(7b-2, owner decision 2026-07-10, ledger H7_OWNER_DECISIONS_7B01).

Diagnostics are NON-TRIAL entries: recording them never increments the
project trial count and never touches IS/OOS semantics (the generic `run`
path stays for pre-registered trials). An attempt is committed BEFORE any
execution and binds lane, scope, window, estimand text, and every
verdict-affecting hash; a result is write-once and refers to exactly one
prior attempt by its record hash.
"""

from __future__ import annotations

from datetime import datetime, timezone

from research import ledger
from research.hashing import (
    DIAGNOSTIC_SOURCE_HASH_VERSION,
    config_hash,
    cost_model_hash,
    diagnostic_source_hash,
)


class DiagnosticError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _code_sha() -> str:
    import subprocess
    out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                         text=True, cwd=ledger.REPO_ROOT)
    if out.returncode != 0:
        raise DiagnosticError("cannot resolve git HEAD for code_sha")
    return out.stdout.strip()


def h7_registration_hashes(base_dir="ledger") -> list[str]:
    """Every H7 trial_intent record hash (registration + amendments), in
    chain order -- the attempt binds the exact registered rule set."""
    hashes = [r["record_hash"] for r in ledger.read_all(base_dir)
              if r.get("entry_type") == "trial_intent"
              and r.get("hypothesis_id") == "H7"]
    if not hashes:
        raise DiagnosticError("no H7 trial_intent records found to bind")
    return hashes


def record_diagnostic_attempt(*, diagnostic_id: str, lane: str,
                              symbols: list[str], window: dict,
                              estimand: str, data_manifest_hash: str,
                              base_dir="ledger") -> str:
    """Append the pre-execution attempt record. Returns its record hash,
    which the eventual result must bind. The caller commits the ledger to
    git BEFORE any execution (owner rule)."""
    body = {
        "entry_type": "diagnostic_attempt",
        "timestamp": _now(),
        "diagnostic_id": diagnostic_id,
        "hypothesis_id": "H7",
        "lane": lane,
        "scope": {"symbols": list(symbols)},
        "window": dict(window),
        "estimand": estimand,
        "code_sha": _code_sha(),
        "config_hash": config_hash(),
        "cost_model_hash": cost_model_hash(),
        "source_hash_v2": diagnostic_source_hash(),
        "source_hash_version": DIAGNOSTIC_SOURCE_HASH_VERSION,
        "data_manifest_hash": data_manifest_hash,
        "registration_hashes": h7_registration_hashes(base_dir),
    }
    return ledger.append(body, base_dir=base_dir)


def record_diagnostic_result(*, diagnostic_id: str, result: dict,
                             base_dir="ledger") -> str:
    """Append the write-once result bound to its attempt's record hash."""
    attempts = [r for r in ledger.read_all(base_dir)
                if r.get("entry_type") == "diagnostic_attempt"
                and r.get("diagnostic_id") == diagnostic_id]
    if not attempts:
        raise DiagnosticError(
            f"no diagnostic_attempt recorded for {diagnostic_id!r}")
    body = {
        "entry_type": "diagnostic_result",
        "timestamp": _now(),
        "diagnostic_id": diagnostic_id,
        "attempt_hash": attempts[-1]["record_hash"],
        "result": dict(result),
    }
    return ledger.append(body, base_dir=base_dir)


def verify_attempt_current(diagnostic_id: str, *, base_dir="ledger") -> dict:
    """The 7b-3 launch gate: the recorded attempt's hashes must match the
    CURRENT code/config/cost surfaces, or the attempt is stale and execution
    must not proceed. Returns the attempt record on success."""
    attempts = [r for r in ledger.read_all(base_dir)
                if r.get("entry_type") == "diagnostic_attempt"
                and r.get("diagnostic_id") == diagnostic_id]
    if not attempts:
        raise DiagnosticError(
            f"no diagnostic_attempt recorded for {diagnostic_id!r}")
    rec = attempts[-1]
    mismatches = []
    if rec["config_hash"] != config_hash():
        mismatches.append("config_hash")
    if rec["cost_model_hash"] != cost_model_hash():
        mismatches.append("cost_model_hash")
    if rec["source_hash_v2"] != diagnostic_source_hash():
        mismatches.append("source_hash_v2")
    if mismatches:
        raise DiagnosticError(
            f"attempt {diagnostic_id!r} is STALE -- {mismatches} changed "
            f"since the attempt was committed; re-record before executing")
    return rec
