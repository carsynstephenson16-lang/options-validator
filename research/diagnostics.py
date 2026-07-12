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

import subprocess
from datetime import datetime, timezone

from research import ledger
from research.hashing import (
    DIAGNOSTIC_SOURCE_HASH_VERSION,
    canonical_json,
    config_hash,
    cost_model_hash,
    diagnostic_source_hash,
    sha256_hex,
)


class DiagnosticError(Exception):
    pass


def require_h7_diagnostic_not_retired(base_dir="ledger") -> None:
    """FROZEN retirement gate (7b-2R.2, owner decision 2026-07-11): the
    2018-2026 historical H7 diagnostic was permanently WITHDRAWN as
    verdict-capable evidence by H7_AMENDMENT_V1_3. Once that amendment's
    record (hash frozen in config.H7_HISTORICAL_WITHDRAWAL_HASH) exists in
    the ledger being used, every historical-diagnostic entry point refuses
    -- before any market data is read. A future conditional historical
    study requires a NEW hypothesis and a NEW registration; it may not
    reopen H7. Synthetic test ledgers (which cannot contain the frozen
    hash) keep exercising the machinery."""
    import config
    for r in ledger.read_all(base_dir):
        if r.get("record_hash") == config.H7_HISTORICAL_WITHDRAWAL_HASH:
            raise DiagnosticError(
                "the historical H7 diagnostic is PERMANENTLY WITHDRAWN "
                "(H7_AMENDMENT_V1_3, ledger record "
                f"{config.H7_HISTORICAL_WITHDRAWAL_HASH[:12]}...); the "
                "forward paper window is the sole verdict-bearing path. A "
                "conditional historical study needs a NEW hypothesis and "
                "registration -- it may not reopen H7.")


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
                              receipt_hash: str,
                              base_dir="ledger") -> str:
    """Append the pre-execution attempt record. Returns its record hash,
    which the eventual result must bind. `receipt_hash` binds the PASS
    audit receipt this attempt is authorized by (7b-2R finding 7). The
    caller commits the ledger to git BEFORE any execution (owner rule).
    Refuses outright once the H7 retirement amendment exists in this
    ledger (7b-2R.2)."""
    require_h7_diagnostic_not_retired(base_dir)
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
        "receipt_hash": receipt_hash,
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


def verify_attempt_current(diagnostic_id: str, *, base_dir="ledger",
                           receipt=None) -> dict:
    """The 7b-3 launch gate: the recorded attempt's hashes must match the
    CURRENT code/config/cost surfaces, its source-hash version must be the
    exactly supported one, its registration bindings must match the ledger,
    and its bound audit receipt must exist, verify, be PASS, and match both
    the attempt's receipt_hash and data_manifest_hash (7b-2R finding 7 --
    the earlier version omitted receipt/registration/scope/source-version
    checks). Returns the attempt record on success."""
    attempts = [r for r in ledger.read_all(base_dir)
                if r.get("entry_type") == "diagnostic_attempt"
                and r.get("diagnostic_id") == diagnostic_id]
    if not attempts:
        raise DiagnosticError(
            f"no diagnostic_attempt recorded for {diagnostic_id!r}")
    rec = attempts[-1]
    if rec.get("source_hash_version") != DIAGNOSTIC_SOURCE_HASH_VERSION:
        raise DiagnosticError(
            f"attempt {diagnostic_id!r} binds source_hash_version "
            f"{rec.get('source_hash_version')} but only "
            f"{DIAGNOSTIC_SOURCE_HASH_VERSION} is supported")
    mismatches = []
    if rec["config_hash"] != config_hash():
        mismatches.append("config_hash")
    if rec["cost_model_hash"] != cost_model_hash():
        mismatches.append("cost_model_hash")
    if rec["source_hash_v2"] != diagnostic_source_hash():
        mismatches.append("source_hash_v2")
    if rec["registration_hashes"] != h7_registration_hashes(base_dir):
        mismatches.append("registration_hashes")
    if mismatches:
        raise DiagnosticError(
            f"attempt {diagnostic_id!r} is STALE -- {mismatches} changed "
            f"since the attempt was committed; re-record before executing")
    if receipt is None:
        import json

        from tools.h7_data_audit import RECEIPT_PATH, verify_receipt
        if not RECEIPT_PATH.exists():
            raise DiagnosticError(
                f"attempt {diagnostic_id!r}: no current audit receipt at "
                f"{RECEIPT_PATH}")
        ok, failures = verify_receipt()
        if not ok:
            raise DiagnosticError(
                f"attempt {diagnostic_id!r}: audit receipt fails verification "
                f"({failures}) -- an input mutated since the audit")
        receipt = json.loads(RECEIPT_PATH.read_text())
    if receipt.get("verdict") != "PASS":
        raise DiagnosticError(
            f"attempt {diagnostic_id!r}: bound receipt verdict is "
            f"{receipt.get('verdict')!r}, not PASS -- launch refused")
    if receipt.get("receipt_hash") != rec.get("receipt_hash"):
        raise DiagnosticError(
            f"attempt {diagnostic_id!r}: receipt_hash mismatch -- the "
            f"attempt binds a different receipt than the current one")
    if receipt.get("manifest_hash") != rec.get("data_manifest_hash"):
        raise DiagnosticError(
            f"attempt {diagnostic_id!r}: data_manifest_hash does not match "
            f"the receipt's eligible-session manifest")
    return rec


def _ledger_git_status(base_dir: str) -> str:
    """Porcelain git status for the ledger dir (a seam for test mocking)."""
    out = subprocess.run(["git", "status", "--porcelain", base_dir],
                         capture_output=True, text=True,
                         cwd=ledger.REPO_ROOT)
    return out.stdout.strip()


def require_anchored_ledger(base_dir: str = "ledger") -> None:
    """The ledger chain must verify AND the ledger dir must carry no
    uncommitted git changes: an attempt authorizes execution only once it
    is anchored (committed). Raises DiagnosticError otherwise."""
    ledger.verify(base_dir=base_dir)
    dirty = _ledger_git_status(base_dir)
    if dirty:
        raise DiagnosticError(
            f"ledger dir {base_dir!r} has uncommitted changes -- the "
            f"attempt must be anchored (committed) before execution:\n"
            f"{dirty}")


def authorize_oos_run(diagnostic_id, *, lane, window, symbols, manifest,
                      base_dir="ledger") -> dict:
    """The OOS gate at the execution boundary (7b-2R.1 finding A).

    Called by harness.run_h7_backtest.run_lane BEFORE any loader touches
    post-IN_SAMPLE_END data. There is no freely constructible authorization
    object: the only thing that opens an OOS window is a committed, current
    diagnostic_attempt whose bound v2 PASS receipt manifest is exactly the
    manifest the runner is about to consume. Returns the attempt record on
    success; raises DiagnosticError on the first failing gate. The FIRST
    gate is the frozen retirement check (7b-2R.2): once H7_AMENDMENT_V1_3
    exists in the ledger, no H7 historical run can ever be authorized."""
    require_h7_diagnostic_not_retired(base_dir)
    if not diagnostic_id:
        raise DiagnosticError(
            "OOS window requires a verified diagnostic id -- run_lane past "
            "IN_SAMPLE_END launches only via tools/h7_run_diagnostic.py")
    require_anchored_ledger(base_dir)
    results = [r for r in ledger.read_all(base_dir)
               if r.get("entry_type") == "diagnostic_result"
               and r.get("diagnostic_id") == diagnostic_id]
    if results:
        raise DiagnosticError(
            f"{diagnostic_id!r} already has a write-once result; a "
            f"diagnostic is never rerun under the same id")
    attempt = verify_attempt_current(diagnostic_id, base_dir=base_dir)
    if attempt["lane"] != lane:
        raise DiagnosticError(
            f"attempt {diagnostic_id!r} authorizes lane "
            f"{attempt['lane']!r}, not {lane!r}")
    if sorted(attempt["scope"]["symbols"]) != sorted(symbols):
        raise DiagnosticError(
            f"attempt {diagnostic_id!r} authorizes symbols "
            f"{sorted(attempt['scope']['symbols'])}, not {sorted(symbols)}")
    if dict(attempt["window"]) != dict(window):
        raise DiagnosticError(
            f"attempt {diagnostic_id!r} authorizes window "
            f"{attempt['window']}, not {window}")
    manifest_hash = sha256_hex(canonical_json(manifest))
    if manifest_hash != attempt.get("data_manifest_hash"):
        raise DiagnosticError(
            f"attempt {diagnostic_id!r}: runner manifest hash "
            f"{manifest_hash} != the attempt's data_manifest_hash -- the "
            f"runner would not consume exactly the audited inputs")
    return attempt
