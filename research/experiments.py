"""
research/experiments.py -- pre-registration, trial counting, and the OOS gate.

register()        -> write a run record (IS result), oos_result null; +1 trial.
log_trial_intent()-> record an intent-to-select that was not a full run; +1 trial.
reveal_oos()      -> the ONLY path that populates an out-of-sample result (Task 7).
"""
from __future__ import annotations
import math
import uuid
from datetime import datetime, timezone

import config
from research import hashing, ledger, windows


class OOSGateError(Exception):
    pass


VALID_RISK_BASES = {"capital_at_risk", "economic_max_loss"}


def json_safe(obj):
    """Recursively replace non-finite floats (NaN/Infinity) with None so a value
    is valid JSON. RFC 8259 forbids NaN/Infinity, and the ledger serializes with
    allow_nan=False; a scoreboard is_result/oos_result legitimately contains
    float('nan') (e.g. Sharpe/Sortino/CI on an insufficient-sample run), so it
    must be sanitized before it enters the ledger or append() would raise."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    return obj


def _now():
    return datetime.now(timezone.utc).isoformat()


def _code_sha():
    import subprocess
    out = subprocess.run(
        ["git", "-C", str(hashing.REPO_ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True)
    return out.stdout.strip() or "unknown"


def _require_non_empty_text(value, field_name) -> None:
    if not isinstance(value, str) or not value.strip():
        raise OOSGateError(f"{field_name} must be a non-empty string")


def _require_window(data_window, key) -> dict:
    if not isinstance(data_window, dict) or not isinstance(data_window.get(key), dict):
        raise OOSGateError(f"data_window.{key} must contain start/end")
    window = data_window[key]
    try:
        # start<=end check: both sentinel dates lie within [start,end] iff start<=end
        windows.assert_within_window([window["start"], window["end"]], window)
    except (KeyError, TypeError, ValueError) as exc:
        raise OOSGateError(f"data_window.{key} must contain valid start/end") from exc
    return dict(window)


def _source_paths():
    import subprocess
    tracked = subprocess.run(
        ["git", "-C", str(hashing.REPO_ROOT), "ls-files", *hashing.SOURCE_HASH_PATHS],
        capture_output=True, text=True)
    paths = set(hashing.source_snapshot().keys())
    explicit_files = {
        p for p in hashing.SOURCE_HASH_PATHS
        if "." in p.rsplit("/", 1)[-1]
    }
    dir_prefixes = [
        f"{p.rstrip('/')}/" for p in hashing.SOURCE_HASH_PATHS
        if p not in explicit_files
    ]
    if tracked.returncode == 0:
        for p in tracked.stdout.splitlines():
            if not p:
                continue
            if p in explicit_files:
                paths.add(p)
            elif (
                p.endswith(".py")
                and "__pycache__" not in p.split("/")
                and any(p.startswith(prefix) for prefix in dir_prefixes)
            ):
                paths.add(p)
    return sorted(paths)


def _source_clean_tracked_default(paths) -> bool:
    import subprocess
    for p in paths:
        tracked = subprocess.run(
            ["git", "-C", str(hashing.REPO_ROOT), "ls-files", "--error-unmatch", p],
            capture_output=True, text=True)
        if tracked.returncode != 0:
            return False
        status = subprocess.run(
            ["git", "-C", str(hashing.REPO_ROOT), "status", "--porcelain", "--", p],
            capture_output=True, text=True)
        if status.stdout.strip():
            return False
    return True


def _require_source_clean(source_clean_tracked=None) -> None:
    checker = source_clean_tracked or _source_clean_tracked_default
    if not checker(_source_paths()):
        raise OOSGateError("source hash surface is not committed clean")


def current_trial_count(base_dir="ledger") -> int:
    return ledger.current_trial_count(base_dir)


def register(hypothesis_id, decision_threshold, is_result, *, data_window,
             risk_basis, notes="", run_id=None, code_sha=None,
             source_clean_tracked=None, base_dir="ledger") -> str:
    _require_non_empty_text(hypothesis_id, "hypothesis_id")
    _require_non_empty_text(decision_threshold, "decision_threshold")
    if risk_basis not in VALID_RISK_BASES:
        raise OOSGateError(f"unknown risk_basis {risk_basis!r}")
    is_window = _require_window(data_window, "is_window")
    oos_window = _require_window(data_window, "oos_window")
    _require_source_clean(source_clean_tracked)
    if any(r.get("entry_type") == "run" and r.get("hypothesis_id") == hypothesis_id
           for r in ledger.read_all(base_dir)):
        raise OOSGateError(f"hypothesis_id {hypothesis_id!r} is already registered")
    safe_is_result = json_safe(is_result)
    try:
        hashing.canonical_json(safe_is_result)
    except (TypeError, ValueError) as exc:
        raise OOSGateError(f"is_result is not JSON-serializable: {exc}") from exc
    body = {
        "entry_type": "run",
        "timestamp": _now(),
        "run_id": run_id or uuid.uuid4().hex,
        "hypothesis_id": hypothesis_id,
        "decision_threshold": decision_threshold,
        "code_sha": code_sha or _code_sha(),
        "config_hash": hashing.config_hash(),
        "cost_model_hash": hashing.cost_model_hash(),
        "source_hash": hashing.source_hash(),
        "data_window_hash": hashing.data_window_hash(data_window),
        "risk_basis": risk_basis,
        "is_window": is_window,
        "is_result": safe_is_result,
        "oos_window": oos_window,
        "oos_result": None,
        "deflated_sharpe": None,  # Phase-1B stub -- never computed in 1A
        "pbo": None,              # Phase-1B stub -- never computed in 1A
        "notes": notes,
    }
    body["trial_count"] = current_trial_count(base_dir) + 1
    return ledger.append(body, base_dir)


def log_trial_intent(reason, *, hypothesis_id=None, base_dir="ledger") -> str:
    body = {
        "entry_type": "trial_intent",
        "timestamp": _now(),
        "reason": reason,
        "hypothesis_id": hypothesis_id,
    }
    body["trial_count"] = current_trial_count(base_dir) + 1
    return ledger.append(body, base_dir)


def reveal_oos(hypothesis_id, run_fn, *, scoreboard_fn=None, base_dir="ledger",
               git_clean_tracked=None):
    """Write-once OOS reveal. Refuses unless a matching registration exists, the
    registered config/source/cost surfaces are unchanged, the global look budget
    is not spent, no prior reveal exists for this hypothesis, and the ledger is
    committed+clean. Only then does it run the (injected) backtest, assert the
    OOS partition and registered window, and append the oos_reveal record."""
    records = ledger.read_all(base_dir)
    runs = [r for r in records
            if r.get("entry_type") == "run" and r.get("hypothesis_id") == hypothesis_id]
    if not runs:
        raise OOSGateError(f"no registered hypothesis {hypothesis_id!r} to reveal")
    run = runs[-1]

    if run["config_hash"] != hashing.config_hash():
        raise OOSGateError("registered config params drifted since registration")
    if run["cost_model_hash"] != hashing.cost_model_hash():
        raise OOSGateError("frozen cost-model params drifted since registration")
    if run["source_hash"] != hashing.source_hash():
        raise OOSGateError("registered source code drifted since registration")

    reveals = [r for r in records if r.get("entry_type") == "oos_reveal"]
    if any(r.get("hypothesis_id") == hypothesis_id for r in reveals):
        raise OOSGateError(f"OOS already revealed for {hypothesis_id!r} (write-once)")

    revealed_hyps = {r.get("hypothesis_id") for r in reveals}
    if len(revealed_hyps) >= config.OOS_LOOK_BUDGET:
        raise OOSGateError(
            f"global OOS look budget exhausted ({config.OOS_LOOK_BUDGET})")

    # The pre-registration must be immutable in git BEFORE we peek at the holdout.
    ledger.verify(base_dir, anchored=True, git_clean_tracked=git_clean_tracked)

    oos_trades = run_fn()
    entry_dates = [t["entry_date"] for t in oos_trades]
    windows.assert_oos_only(entry_dates, config.IN_SAMPLE_END)
    windows.assert_within_window(entry_dates, run["oos_window"])

    if scoreboard_fn is None:
        from metrics import scoreboard as scoreboard_fn  # local import avoids cycle
    safe_oos = json_safe(scoreboard_fn(oos_trades))
    try:
        hashing.canonical_json(safe_oos)
    except (TypeError, ValueError) as exc:
        raise OOSGateError(f"oos_result is not JSON-serializable: {exc}") from exc

    body = {
        "entry_type": "oos_reveal",
        "timestamp": _now(),
        "run_id": run["run_id"],
        "hypothesis_id": hypothesis_id,
        "oos_result": safe_oos,
        "budget_used": len(revealed_hyps) + 1,
        "budget_total": config.OOS_LOOK_BUDGET,
    }
    body["trial_count"] = current_trial_count(base_dir)  # reveal adds no new trial
    ledger.append(body, base_dir)
    return safe_oos
