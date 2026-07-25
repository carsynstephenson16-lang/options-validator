"""
research/ledger.py -- append-only, hash-chained JSONL experiment ledger.

The chain IS the tamper-evidence: each record commits to the previous one.
A second tracked file, HEAD, holds the current tip so it is diffable in git.
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime
from pathlib import Path

import config
from research.hashing import canonical_json, sha256_hex

GENESIS_PREV = "0" * 64
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
TRIAL_TYPES = {"run", "trial_intent", "retrospective_result"}
# OOS record types share budget accounting: an oos_attempt is the auditable
# charge-on-touch event appended BEFORE the holdout backtest executes; the
# budget counts TOUCHED hypotheses (attempts union reveals), never just
# successful reveals, so a crashed attempt still burned its look.
OOS_TYPES = {"oos_attempt", "oos_reveal"}
# Diagnostic records (7b-2, owner decision 2026-07-10): isolated-lane H7
# diagnostics are NON-TRIAL entries -- they never increment trial_count and
# never carry IS/OOS semantics. An attempt is committed BEFORE execution and
# binds lane/scope/window/estimand plus every verdict-affecting hash; a
# result is write-once and refers to exactly one prior attempt.
DIAGNOSTIC_TYPES = {"diagnostic_attempt", "diagnostic_result"}
VALID_ENTRY_TYPES = TRIAL_TYPES | OOS_TYPES | DIAGNOSTIC_TYPES
VALID_RISK_BASES = {"capital_at_risk", "economic_max_loss"}
RESERVED_KEYS = {"seq", "prev_hash", "record_hash"}
CHAIN_KEYS = RESERVED_KEYS | {"trial_count", "entry_type"}
TRIAL_INTENT_KEYS = CHAIN_KEYS | {"timestamp", "reason", "hypothesis_id"}
# retrospective_result (BS-arc spec 2026-07-17 sec.9): a TRIAL-COUNTING record
# publishing a result whose inputs already exist (no new run). A post-result
# trial_intent would be semantically false ("intent" implies pre-result).
# The attempt number IS this record's chain-computed trial_count -- never
# restated in prose (owner correction 2026-07-18). Labels are mandatory
# honesty markers; result is the summary readings being published.
RETROSPECTIVE_REQUIRED_LABELS = (
    "outcome-selected",
    "self-deceiving",
    "descriptive-only",
    "no-verdict",
    "cannot-promote",
)
RETROSPECTIVE_RESULT_KEYS = CHAIN_KEYS | {
    "timestamp",
    "subject",
    "hypothesis_id",
    "report_sha256",
    "context_sha256",
    "prereg_ref_sha256",
    "source_commit",
    "labels",
    "result",
}
RUN_KEYS = CHAIN_KEYS | {
    "timestamp",
    "run_id",
    "hypothesis_id",
    "decision_threshold",
    "code_sha",
    "config_hash",
    "cost_model_hash",
    "source_hash",
    "data_window_hash",
    "risk_basis",
    "is_window",
    "is_result",
    "oos_window",
    "oos_result",
    "deflated_sharpe",
    "pbo",
    "notes",
    "scope",
}
OOS_ATTEMPT_KEYS = CHAIN_KEYS | {
    "timestamp",
    "hypothesis_id",
    "run_id",
    "budget_used",
    "budget_total",
}
OOS_REVEAL_KEYS = CHAIN_KEYS | {
    "timestamp",
    "hypothesis_id",
    "run_id",
    "oos_result",
    "budget_used",
    "budget_total",
}
DIAGNOSTIC_ATTEMPT_KEYS = CHAIN_KEYS | {
    "timestamp",
    "diagnostic_id",
    "hypothesis_id",
    "lane",
    "scope",
    "window",
    "estimand",
    "code_sha",
    "config_hash",
    "cost_model_hash",
    "source_hash_v2",
    "source_hash_version",
    "data_manifest_hash",
    "receipt_hash",
    "registration_hashes",
}
DIAGNOSTIC_RESULT_KEYS = CHAIN_KEYS | {
    "timestamp",
    "diagnostic_id",
    "attempt_hash",
    "result",
}
H7_LANES = {"a", "b", "c"}
ALLOWED_KEYS_BY_TYPE = {
    "trial_intent": TRIAL_INTENT_KEYS,
    "retrospective_result": RETROSPECTIVE_RESULT_KEYS,
    "run": RUN_KEYS,
    "oos_attempt": OOS_ATTEMPT_KEYS,
    "oos_reveal": OOS_REVEAL_KEYS,
    "diagnostic_attempt": DIAGNOSTIC_ATTEMPT_KEYS,
    "diagnostic_result": DIAGNOSTIC_RESULT_KEYS,
}
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


def _expected_trial_count(records: list[dict], entry_type: str):
    count = sum(1 for r in records if r.get("entry_type") in TRIAL_TYPES)
    if entry_type in TRIAL_TYPES:
        return count + 1
    if entry_type in OOS_TYPES | DIAGNOSTIC_TYPES:
        return count   # diagnostics are NON-trials: the count never moves
    return None


def _require_text(rec: dict, key: str, seq: int) -> str:
    value = rec.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LedgerError(f"{key} must be a non-empty string at seq {seq}")
    return value


def _require_canonical_text(rec: dict, key: str, seq: int) -> str:
    value = _require_text(rec, key, seq)
    if value != value.strip():
        raise LedgerError(f"{key} must be trimmed at seq {seq}")
    return value


def _require_optional_canonical_text(rec: dict, key: str, seq: int) -> str | None:
    value = rec.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise LedgerError(f"{key} must be a non-empty string at seq {seq}")
    if value != value.strip():
        raise LedgerError(f"{key} must be trimmed at seq {seq}")
    return value


def _require_sha256_hex(rec: dict, key: str, seq: int) -> str:
    value = _require_canonical_text(rec, key, seq)
    if not SHA256_RE.fullmatch(value):
        raise LedgerError(f"{key} must be a 64-character lowercase SHA-256 hex at seq {seq}")
    return value


def _require_git_sha(rec: dict, key: str, seq: int) -> str:
    value = _require_canonical_text(rec, key, seq)
    if not GIT_SHA_RE.fullmatch(value):
        raise LedgerError(f"{key} must be a full Git object hash at seq {seq}")
    return value


def _require_positive_int(rec: dict, key: str, seq: int) -> int:
    value = rec.get(key)
    if type(value) is not int or value <= 0:
        raise LedgerError(f"{key} must be a positive integer at seq {seq}")
    return value


def _require_dict(rec: dict, key: str, seq: int) -> dict:
    value = rec.get(key)
    if not isinstance(value, dict):
        raise LedgerError(f"{key} must be an object at seq {seq}")
    return value


def _reject_unknown_fields(rec: dict, entry_type: str, seq: int) -> None:
    allowed = ALLOWED_KEYS_BY_TYPE[entry_type]
    unknown = sorted(set(rec) - allowed)
    if unknown:
        raise LedgerError(f"unknown field(s) at seq {seq}: {unknown}")


def _require_timestamp(rec: dict, key: str, seq: int) -> datetime:
    value = _require_text(rec, key, seq)
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LedgerError(f"{key} must be an ISO timestamp at seq {seq}") from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise LedgerError(f"{key} must be timezone-aware at seq {seq}")
    return stamp


def _require_date(value, key: str, seq: int) -> date:
    if not isinstance(value, str):
        raise LedgerError(f"{key} must be an ISO date string at seq {seq}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise LedgerError(f"{key} must be an ISO date string at seq {seq}") from exc


def _require_window(rec: dict, key: str, seq: int) -> dict:
    window = _require_dict(rec, key, seq)
    start = _require_date(window.get("start"), f"{key}.start", seq)
    end = _require_date(window.get("end"), f"{key}.end", seq)
    if start > end:
        raise LedgerError(f"{key}.start must be <= {key}.end at seq {seq}")
    return window


def _require_scope(rec: dict, seq: int) -> dict:
    """scope = {"symbols": [...]}: the registered universe the OOS reveal must
    run -- canonical upper-case symbols, no duplicates (a duplicate would
    double-run a name), no extra keys to smuggle state through."""
    scope = _require_dict(rec, "scope", seq)
    if set(scope) != {"symbols"}:
        raise LedgerError(f"scope must contain exactly 'symbols' at seq {seq}")
    symbols = scope["symbols"]
    if not isinstance(symbols, list) or not symbols:
        raise LedgerError(f"scope.symbols must be a non-empty list at seq {seq}")
    for s in symbols:
        if not isinstance(s, str) or not s or s != s.strip() or s != s.upper():
            raise LedgerError(
                f"scope.symbols must be canonical upper-case tickers at seq {seq}: {s!r}")
    if len(set(symbols)) != len(symbols):
        raise LedgerError(f"scope.symbols must not contain duplicates at seq {seq}")
    return scope


# Phase-1B (2026-07-24): deflated_sharpe is a DISPLAY/DIAGNOSTIC add-on, never
# a certifier (see metrics.py psr()/dsr() and docs/superpowers/specs/
# 2026-07-01-research-integrity-foundation-design.md:400). It must stay
# EITHER null (every Phase-1A record, and any record that never computed a
# DSR) OR this fully-shaped dict recording the PSR/DSR computation and its
# provenance. Any other type -- a bare number, a string, a partially-shaped
# dict -- is rejected so a future caller can never smuggle an unvalidated
# number onto the hash chain. `pbo` enforcement is UNCHANGED (still always
# null; PBO stays out of scope for this mission).
DEFLATED_SHARPE_KEYS = {
    "value", "psr_vs_zero", "t", "skew", "kurt",
    "n_trials", "n_provenance", "trial_sr_variance", "note",
}


def _require_finite_number(d: dict, key: str, seq: int, ctx: str) -> float:
    value = d.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LedgerError(f"{ctx}{key} must be a finite number at seq {seq}")
    if not math.isfinite(value):
        raise LedgerError(f"{ctx}{key} must be a finite number at seq {seq}")
    return float(value)


def _require_deflated_sharpe(rec: dict, seq: int) -> None:
    value = rec.get("deflated_sharpe")
    if value is None:
        return
    if not isinstance(value, dict):
        raise LedgerError(f"deflated_sharpe must be null or an object at seq {seq}")
    unknown = sorted(set(value) - DEFLATED_SHARPE_KEYS)
    if unknown:
        raise LedgerError(f"deflated_sharpe has unknown field(s) at seq {seq}: {unknown}")
    missing = sorted(DEFLATED_SHARPE_KEYS - set(value))
    if missing:
        raise LedgerError(f"deflated_sharpe missing field(s) at seq {seq}: {missing}")

    _require_finite_number(value, "value", seq, "deflated_sharpe.")
    _require_finite_number(value, "psr_vs_zero", seq, "deflated_sharpe.")
    _require_finite_number(value, "skew", seq, "deflated_sharpe.")
    _require_finite_number(value, "kurt", seq, "deflated_sharpe.")
    _require_finite_number(value, "trial_sr_variance", seq, "deflated_sharpe.")

    t = value.get("t")
    if type(t) is not int or t < config.DSR_MIN_T:
        raise LedgerError(
            f"deflated_sharpe.t must be an int >= DSR_MIN_T ({config.DSR_MIN_T}) "
            f"at seq {seq}"
        )
    n_trials = value.get("n_trials")
    if type(n_trials) is not int or n_trials < config.DSR_MIN_N_TRIALS:
        raise LedgerError(
            f"deflated_sharpe.n_trials must be an int >= DSR_MIN_N_TRIALS "
            f"({config.DSR_MIN_N_TRIALS}) at seq {seq}"
        )
    n_provenance = value.get("n_provenance")
    if not isinstance(n_provenance, str) or not n_provenance.strip():
        raise LedgerError(
            f"deflated_sharpe.n_provenance must be a non-empty string at seq {seq}")
    note = value.get("note")
    if not isinstance(note, str) or not note.strip():
        raise LedgerError(f"deflated_sharpe.note must be a non-empty string at seq {seq}")


def _verify_semantic_records(records: list[dict]) -> None:
    trial_count = 0
    runs_by_hypothesis = {}
    run_ids = set()
    touched_hypotheses = set()   # attempts union reveals: the budget basis
    revealed_hypotheses = set()
    oos_budget_total = None
    diagnostic_attempts: dict[str, str] = {}   # diagnostic_id -> record_hash
    diagnostic_results: set[str] = set()       # write-once per diagnostic_id

    for i, rec in enumerate(records):
        entry_type = rec.get("entry_type")
        if entry_type not in VALID_ENTRY_TYPES:
            raise LedgerError(f"unknown entry_type at seq {i}: {entry_type!r}")
        _reject_unknown_fields(rec, entry_type, i)

        if entry_type in TRIAL_TYPES:
            trial_count += 1
            expected_trial_count = trial_count
        else:
            expected_trial_count = trial_count

        if rec.get("trial_count") != expected_trial_count:
            raise LedgerError(
                f"trial_count mismatch at seq {i}: "
                f"{rec.get('trial_count')!r} != {expected_trial_count}"
            )

        if entry_type == "trial_intent":
            _require_timestamp(rec, "timestamp", i)
            _require_canonical_text(rec, "reason", i)
            _require_optional_canonical_text(rec, "hypothesis_id", i)
        elif entry_type == "retrospective_result":
            _require_timestamp(rec, "timestamp", i)
            _require_canonical_text(rec, "subject", i)
            _require_optional_canonical_text(rec, "hypothesis_id", i)
            _require_sha256_hex(rec, "report_sha256", i)
            _require_sha256_hex(rec, "context_sha256", i)
            _require_sha256_hex(rec, "prereg_ref_sha256", i)
            _require_git_sha(rec, "source_commit", i)
            labels = rec.get("labels")
            if (not isinstance(labels, list) or not labels
                    or not all(isinstance(x, str) and x and x == x.strip()
                               for x in labels)):
                raise LedgerError(
                    f"labels must be a non-empty list of trimmed strings at seq {i}")
            missing = [x for x in RETROSPECTIVE_REQUIRED_LABELS if x not in labels]
            if missing:
                raise LedgerError(
                    f"retrospective_result missing required label(s) at seq {i}: "
                    f"{missing}")
            _require_dict(rec, "result", i)
        elif entry_type == "run":
            hypothesis_id = _require_canonical_text(rec, "hypothesis_id", i)
            run_id = _require_canonical_text(rec, "run_id", i)
            _require_timestamp(rec, "timestamp", i)
            _require_canonical_text(rec, "decision_threshold", i)
            _require_git_sha(rec, "code_sha", i)
            _require_sha256_hex(rec, "config_hash", i)
            _require_sha256_hex(rec, "cost_model_hash", i)
            _require_sha256_hex(rec, "source_hash", i)
            _require_sha256_hex(rec, "data_window_hash", i)
            risk_basis = _require_canonical_text(rec, "risk_basis", i)
            if risk_basis not in VALID_RISK_BASES:
                raise LedgerError(f"unknown risk_basis at seq {i}: {risk_basis!r}")
            is_window = _require_window(rec, "is_window", i)
            _require_dict(rec, "is_result", i)
            oos_window = _require_window(rec, "oos_window", i)
            if _require_date(is_window["end"], "is_window.end", i) >= _require_date(
                oos_window["start"], "oos_window.start", i
            ):
                raise LedgerError(f"is_window.end must be before oos_window.start at seq {i}")
            if rec.get("oos_result") is not None:
                raise LedgerError(f"run oos_result must be null at seq {i}")
            _require_deflated_sharpe(rec, i)
            if rec.get("pbo") is not None:
                raise LedgerError(f"pbo must be null at seq {i}")
            if not isinstance(rec.get("notes"), str):
                raise LedgerError(f"notes must be a string at seq {i}")
            _require_scope(rec, i)
            if hypothesis_id in runs_by_hypothesis:
                raise LedgerError(f"duplicate run hypothesis_id at seq {i}: {hypothesis_id!r}")
            if run_id in run_ids:
                raise LedgerError(f"duplicate run_id at seq {i}: {run_id!r}")
            runs_by_hypothesis[hypothesis_id] = run_id
            run_ids.add(run_id)
        elif entry_type in OOS_TYPES:
            _require_timestamp(rec, "timestamp", i)
            hypothesis_id = _require_canonical_text(rec, "hypothesis_id", i)
            run_id = _require_canonical_text(rec, "run_id", i)
            if hypothesis_id not in runs_by_hypothesis:
                raise LedgerError(
                    f"{entry_type} at seq {i} has no registered run: {hypothesis_id!r}"
                )
            if runs_by_hypothesis[hypothesis_id] != run_id:
                raise LedgerError(f"{entry_type} run_id mismatch at seq {i}")
            if entry_type == "oos_reveal":
                _require_dict(rec, "oos_result", i)
                if hypothesis_id not in touched_hypotheses:
                    raise LedgerError(
                        f"oos_reveal at seq {i} has no prior oos_attempt "
                        f"(charge-on-touch) for {hypothesis_id!r}")
                if hypothesis_id in revealed_hypotheses:
                    raise LedgerError(f"duplicate oos_reveal at seq {i}: {hypothesis_id!r}")
            expected_budget_used = len(touched_hypotheses | {hypothesis_id})
            if rec.get("budget_used") != expected_budget_used:
                raise LedgerError(
                    f"budget_used mismatch at seq {i}: "
                    f"{rec.get('budget_used')!r} != {expected_budget_used}"
                )
            budget_total = _require_positive_int(rec, "budget_total", i)
            if budget_total < expected_budget_used:
                raise LedgerError(f"budget_total below budget_used at seq {i}")
            if oos_budget_total is None:
                oos_budget_total = budget_total
            elif budget_total != oos_budget_total:
                raise LedgerError(f"budget_total changed at seq {i}")
            touched_hypotheses.add(hypothesis_id)
            if entry_type == "oos_reveal":
                revealed_hypotheses.add(hypothesis_id)
        elif entry_type == "diagnostic_attempt":
            _require_timestamp(rec, "timestamp", i)
            diagnostic_id = _require_canonical_text(rec, "diagnostic_id", i)
            if diagnostic_id in diagnostic_attempts:
                raise LedgerError(
                    f"duplicate diagnostic_attempt at seq {i}: {diagnostic_id!r}")
            _require_canonical_text(rec, "hypothesis_id", i)
            lane = _require_canonical_text(rec, "lane", i)
            if lane not in H7_LANES:
                raise LedgerError(f"unknown diagnostic lane at seq {i}: {lane!r}")
            _require_scope(rec, i)
            _require_window(rec, "window", i)
            _require_canonical_text(rec, "estimand", i)
            _require_git_sha(rec, "code_sha", i)
            _require_sha256_hex(rec, "config_hash", i)
            _require_sha256_hex(rec, "cost_model_hash", i)
            _require_sha256_hex(rec, "source_hash_v2", i)
            _require_positive_int(rec, "source_hash_version", i)
            _require_sha256_hex(rec, "data_manifest_hash", i)
            _require_sha256_hex(rec, "receipt_hash", i)
            reg = rec.get("registration_hashes")
            if (not isinstance(reg, list) or not reg
                    or not all(isinstance(h, str) and SHA256_RE.fullmatch(h)
                               for h in reg)):
                raise LedgerError(
                    f"registration_hashes must be a non-empty list of "
                    f"sha256 hex strings at seq {i}")
            diagnostic_attempts[diagnostic_id] = rec.get("record_hash", "")
        elif entry_type == "diagnostic_result":
            _require_timestamp(rec, "timestamp", i)
            diagnostic_id = _require_canonical_text(rec, "diagnostic_id", i)
            if diagnostic_id not in diagnostic_attempts:
                raise LedgerError(
                    f"diagnostic_result at seq {i} has no prior "
                    f"diagnostic_attempt: {diagnostic_id!r}")
            if diagnostic_id in diagnostic_results:
                raise LedgerError(
                    f"duplicate diagnostic_result at seq {i}: "
                    f"{diagnostic_id!r} (results are write-once)")
            attempt_hash = _require_sha256_hex(rec, "attempt_hash", i)
            if attempt_hash != diagnostic_attempts[diagnostic_id]:
                raise LedgerError(
                    f"diagnostic_result attempt_hash mismatch at seq {i}: "
                    f"does not bind the recorded attempt for "
                    f"{diagnostic_id!r}")
            _require_dict(rec, "result", i)
            diagnostic_results.add(diagnostic_id)


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
    entry_type = record.get("entry_type")
    if not isinstance(entry_type, str):
        raise LedgerError(f"ledger entry_type must be a string: {entry_type!r}")
    expected_trial_count = _expected_trial_count(records, entry_type)
    if expected_trial_count is not None:
        actual_trial_count = record.get("trial_count")
        if actual_trial_count is None:
            record["trial_count"] = expected_trial_count
        elif actual_trial_count != expected_trial_count:
            raise LedgerError(
                f"trial_count mismatch for next {record.get('entry_type')}: "
                f"{actual_trial_count!r} != {expected_trial_count}"
            )
    record["seq"] = len(records)
    record["prev_hash"] = prev
    record["record_hash"] = _record_hash(record)  # record has no record_hash key yet
    _verify_semantic_records(records + [record])
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
    _verify_semantic_records(records)
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
