"""Read-only, network-free preflight for the 2026-07-29 ThetaData cutoff.

This tool never fetches data, writes a receipt, appends a fact/event, opens
H7 Stage 8, or authorizes the paid top-up. It derives the terminal completed
session, proves the exact 12-name scope, inventories every required cache
file and BLIND_CACHE fact, runs the current exit audit, checks H6 feature-input
readiness, verifies the real H7 ledger, and prints the exact future commands.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from data import recent_topup  # noqa: E402
from data.cache_provenance import load_blind_cache_facts  # noqa: E402
from data.cache_runner import session_close_utc, trading_days  # noqa: E402
from options_researcher import h7_event_ledger  # noqa: E402
from options_researcher.h6_features import PCT_MIN_OBS, PCT_WINDOW  # noqa: E402
from options_researcher.h7_data_gate import evaluate as evaluate_data_gate  # noqa: E402
from options_researcher.h7_earnings import load_assertions  # noqa: E402
from options_researcher.h7_source_health import symbol_health  # noqa: E402
from research.hashing import sha256_file  # noqa: E402
from tools import thetadata_exit_audit as exit_audit  # noqa: E402

SCHEMA = "thetadata-cutoff-preflight/v1"
DEFAULT_CUTOFF = date(2026, 7, 29)
DEFAULT_CHAIN_DIR = Path(".cache/chains")
DEFAULT_CLOSE_DIR = Path(".cache/underlying")
DEFAULT_FACTS_PATH = Path("ledger/facts.log")
DEFAULT_LEDGER_DIR = Path("ledger/h7_forward")

# FROZEN cutoff-decision scope for the 2026-07-25 ThetaData renewal gate.
# This preflight audits a decision that was REGISTERED on exactly these 12
# names before IREN existed anywhere in H7 scope. H7_AMENDMENT_V1_5
# (2026-07-14, ledger/facts.log) added IREN to config.H7_WATCHLIST, growing
# the *live* watch universe (recent_topup.scope_symbols("h7") /
# options_researcher.h7_scope.watch_universe()) to 13 names. That growth
# must never silently widen THIS frozen decision's scope, so the list below
# is a hardcoded constant, deliberately decoupled from H7_WATCHLIST /
# watch_universe() -- it does not read config.H7_WATCHLIST and must not be
# derived from it. Revisiting the cutoff-decision scope itself (e.g. to add
# IREN) is a new pre-registered decision, not a silent widen of this one.
FROZEN_CUTOFF_SCOPE = (
    "CRWV", "TEM", "PLTR", "NOW", "SMCI", "NVDA", "AMD", "AVGO",
    "VST", "CEG", "MSFT", "AMZN",
)
SOURCE_PATHS = (
    "config.py",
    "data/cache_provenance.py",
    "data/cache_runner.py",
    "data/recent_topup.py",
    "options_researcher/h6_features.py",
    "options_researcher/h7_event_ledger.py",
    "options_researcher/h7_data_gate.py",
    "options_researcher/h7_earnings.py",
    "options_researcher/h7_scope.py",
    "options_researcher/h7_source_health.py",
    "tools/thetadata_cutoff_preflight.py",
    "tools/thetadata_exit_audit.py",
)


def source_identity() -> dict:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    status = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            *SOURCE_PATHS,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "source_paths": list(SOURCE_PATHS),
        "dirty": bool(status.stdout.strip()) or status.returncode != 0,
        "dirty_paths": sorted(line[3:] for line in status.stdout.splitlines()),
    }


def _terminal_session(cutoff: date, trading_days_fn=trading_days) -> str:
    start = cutoff - timedelta(days=14)
    sessions = [
        day
        for day in trading_days_fn(start.isoformat(), cutoff.isoformat())
        if day < cutoff.isoformat()
    ]
    if not sessions:
        raise ValueError(f"no completed XNYS session before cutoff {cutoff}")
    return sessions[-1]


def _h6_input_readiness(
    as_of: str,
    *,
    chain_dir: Path,
    facts: dict[tuple[str, str], dict],
) -> dict:
    per_symbol: dict[str, dict] = {}
    ready = True
    for symbol in config.H6_NAMES:
        prefix = f"{symbol}_"
        dated: list[tuple[str, Path]] = []
        for path in Path(chain_dir).glob(f"{prefix}*.parquet"):
            raw = path.stem[len(prefix):]
            try:
                date.fromisoformat(raw)
            except ValueError as exc:
                raise ValueError(f"malformed chain filename: {path}") from exc
            if raw <= as_of:
                dated.append((raw, path))
        dated = sorted(dated)[-PCT_WINDOW:]
        issues: list[str] = []
        if len(dated) < PCT_MIN_OBS:
            issues.append(f"only {len(dated)} chain sessions; need {PCT_MIN_OBS}")
        if not dated or dated[-1][0] != as_of:
            issues.append(f"exact chain missing for {as_of}")
        matched = 0
        for day, path in dated:
            fact = facts.get((symbol, day))
            if fact is None:
                issues.append(f"{day}: missing BLIND_CACHE fact")
            elif fact["sha256"] != sha256_file(path):
                issues.append(f"{day}: BLIND_CACHE sha256 mismatch")
            else:
                matched += 1
        symbol_ready = not issues
        ready = ready and symbol_ready
        per_symbol[symbol] = {
            "ready": symbol_ready,
            "chain_count": len(dated),
            "provenance_matches": matched,
            "latest": dated[-1][0] if dated else None,
            "issues": issues,
        }
    return {"ready": ready, "symbols": per_symbol}


def _commands(terminal: str, cutoff: date) -> dict[str, str]:
    receipt = f"reports/thetadata_exit/{terminal}.json"
    h6_receipt = f"reports/h6_forward/{terminal}.json"
    return {
        "pre_pull_inventory": (
            "uv run python data/recent_topup.py --scope h7 --dry-run"
        ),
        "owner_authorized_paid_pull": (
            "uv run python data/recent_topup.py --scope h7 --refresh-closes"
        ),
        "write_exit_receipt": (
            "uv run python tools/thetadata_exit_audit.py "
            f"--scope h7 --as-of {cutoff.isoformat()} --write"
        ),
        "verify_exit_receipt": (
            "uv run python tools/thetadata_exit_audit.py " f"--verify {receipt}"
        ),
        "source_health": (
            "uv run python -m options_researcher.h7_source_health "
            f"--as-of {cutoff.isoformat()}"
        ),
        "data_gate": (
            "uv run python -m options_researcher.h7_data_gate "
            f"--as-of {cutoff.isoformat()}"
        ),
        "verify_real_ledger": (
            "uv run python -m options_researcher.h7_event_ledger verify"
        ),
        "build_h6_features": (
            "uv run python -m options_researcher.h6_features " f"--as-of {terminal}"
        ),
        "write_h6_receipt": (
            "uv run python -m options_researcher.h6_watch "
            f"--as-of {terminal} --write-receipt {h6_receipt} --json"
        ),
        "verify_h6_receipt": (
            "uv run python -m options_researcher.h6_watch "
            f"--as-of {terminal} --verify-receipt {h6_receipt} --json"
        ),
    }


def _source_health_readiness(as_of: str) -> dict:
    on = date.fromisoformat(as_of)
    known_as_of = session_close_utc(as_of)
    assertions = load_assertions()
    health = [
        symbol_health(
            symbol,
            on,
            assertions,
            known_as_of=known_as_of,
            warn_sessions=config.H7_SOURCE_HEALTH_WARN_SESSIONS,
        )
        for symbol in FROZEN_CUTOFF_SCOPE
    ]
    unhealthy = [row["symbol"] for row in health if not row["healthy"]]
    return {
        "evaluation_session": as_of,
        "known_as_of_utc": known_as_of.isoformat(),
        "healthy_count": len(health) - len(unhealthy),
        "unhealthy_count": len(unhealthy),
        "unhealthy_symbols": unhealthy,
        "activation_ready": not unhealthy,
    }


def build_preflight(
    *,
    cutoff: date = DEFAULT_CUTOFF,
    today: date,
    chain_dir: Path = DEFAULT_CHAIN_DIR,
    close_dir: Path = DEFAULT_CLOSE_DIR,
    facts_path: Path = DEFAULT_FACTS_PATH,
    ledger_dir: Path = DEFAULT_LEDGER_DIR,
    trading_days_fn=trading_days,
    facts: dict[tuple[str, str], dict] | None = None,
    audit_fn=exit_audit.run_audit,
    audit_identity_fn=exit_audit.source_identity,
    data_gate_fn=evaluate_data_gate,
    source_health_fn=_source_health_readiness,
    source_identity_fn=source_identity,
    ledger_verify_fn=h7_event_ledger.verify,
    h6_readiness_fn=_h6_input_readiness,
) -> dict:
    """Build a deterministic cutoff report without any write/network path."""
    symbols = list(FROZEN_CUTOFF_SCOPE)
    if len(symbols) != 12 or len(symbols) != len(set(symbols)):
        raise ValueError(f"H7 cutoff scope must be 12 unique names; got {symbols}")
    terminal = _terminal_session(cutoff, trading_days_fn)
    required_sessions = [
        day
        for day in trading_days_fn(exit_audit.DEFAULT_START, terminal)
        if exit_audit.DEFAULT_START <= day <= terminal
    ]
    if not required_sessions or required_sessions[-1] != terminal:
        raise ValueError("required session calendar does not reach terminal session")

    chain_dir = Path(chain_dir)
    close_dir = Path(close_dir)
    facts = load_blind_cache_facts(facts_path) if facts is None else facts
    missing: dict[str, list[str]] = {}
    provenance_missing: list[str] = []
    provenance_mismatch: list[str] = []
    premature_present: list[str] = []
    present = 0
    for session in required_sessions:
        absent: list[str] = []
        for symbol in symbols:
            path = chain_dir / f"{symbol}_{session}.parquet"
            if not path.is_file():
                absent.append(symbol)
                continue
            present += 1
            if session >= today.isoformat():
                premature_present.append(f"{symbol} {session}")
            fact = facts.get((symbol, session))
            identity = f"{symbol} {session}"
            if fact is None:
                provenance_missing.append(identity)
            elif fact["sha256"] != sha256_file(path):
                provenance_mismatch.append(identity)
        if absent:
            missing[session] = absent

    cohort_latest = recent_topup.latest_cached_date(symbols, cache_dir=chain_dir)
    audited_end = min(cohort_latest, terminal) if cohort_latest else None
    audit_summary = {
        "verdict": "NOT_RUN",
        "counts": {"blocks": 0, "warnings": 0},
        "window": None,
    }
    if audited_end is not None and audited_end >= exit_audit.DEFAULT_START:
        current_sessions = [day for day in required_sessions if day <= audited_end]
        audit = audit_fn(
            symbols=symbols,
            start=exit_audit.DEFAULT_START,
            end=audited_end,
            chain_dir=chain_dir,
            close_dir=close_dir,
            facts=facts,
            sessions=current_sessions,
            identity=audit_identity_fn(),
        )
        audit_summary = {
            "verdict": audit["verdict"],
            "counts": audit["counts"],
            "window": audit["window"],
        }

    data_gate = {
        "evaluation_session": None,
        "whole_universe_verdict": "NOT_RUN",
        "go_count": 0,
        "no_go_count": len(symbols),
    }
    source_health = {
        "evaluation_session": None,
        "healthy_count": 0,
        "unhealthy_count": len(symbols),
        "unhealthy_symbols": symbols,
        "activation_ready": False,
    }
    if audited_end is not None:
        requested_gate_date = date.fromisoformat(audited_end) + timedelta(days=1)
        gate = data_gate_fn(
            requested_gate_date,
            close_dir=close_dir,
            chain_dir=chain_dir,
        )
        data_gate = {
            "evaluation_session": gate["evaluation_session"],
            "whole_universe_verdict": gate["whole_universe_verdict"],
            "go_count": gate["go_count"],
            "no_go_count": gate["no_go_count"],
        }
        source_health = source_health_fn(audited_end)

    ledger = ledger_verify_fn(base_dir=ledger_dir)
    h6 = (
        h6_readiness_fn(audited_end, chain_dir=chain_dir, facts=facts)
        if audited_end is not None
        else {"ready": False, "symbols": {}, "reason": "no cohort cache"}
    )
    source = source_identity_fn()
    blockers: list[str] = []
    if source.get("dirty"):
        blockers.append(f"dirty preflight source: {source.get('dirty_paths', [])}")
    if not ledger.valid or not ledger.empty or ledger.count != 0:
        blockers.append("real H7 forward ledger is not VALID EMPTY")
    if provenance_missing:
        blockers.append(f"present chains missing provenance: {len(provenance_missing)}")
    if provenance_mismatch:
        blockers.append(f"present chains with provenance mismatch: {len(provenance_mismatch)}")
    if premature_present:
        blockers.append(
            f"current/future session chains present before EOD finality: {len(premature_present)}"
        )
    if audit_summary["verdict"] == "BLOCK":
        blockers.append("current ThetaData exit audit is BLOCK")
    if audited_end is not None and (
        data_gate["evaluation_session"] != audited_end
        or data_gate["whole_universe_verdict"] != "GO"
        or data_gate["go_count"] != len(symbols)
    ):
        blockers.append("current Stage-2 data gate is not exact-session 12/12 GO")
    if not h6.get("ready"):
        blockers.append("H6 current feature-input surface is not ready")

    terminal_complete = not missing
    actionable_missing = {
        session: names
        for session, names in missing.items()
        if session < today.isoformat()
    }
    future_sessions = [
        session for session in required_sessions if session >= today.isoformat()
    ]
    if blockers:
        status = "BLOCK"
    elif terminal_complete and audited_end == terminal:
        status = "READY_FOR_RECEIPTS"
    elif today >= cutoff:
        status = "OWNER_AUTHORIZED_PULL_REQUIRED"
    elif actionable_missing:
        status = "OWNER_AUTHORIZED_TOPUP_AVAILABLE"
    else:
        status = "WAITING_FOR_CUTOFF"

    return {
        "schema": SCHEMA,
        "mode": "READ_ONLY_NO_NETWORK",
        "stage8_open": False,
        "paid_pull_authorized": False,
        "cutoff": cutoff.isoformat(),
        "today": today.isoformat(),
        "terminal_session": terminal,
        "status": status,
        "blockers": blockers,
        "scope": symbols,
        "cache": {
            "audit_start": exit_audit.DEFAULT_START,
            "cohort_latest": cohort_latest,
            "required_sessions": required_sessions,
            "required_symbol_sessions": len(symbols) * len(required_sessions),
            "present_symbol_sessions": present,
            "terminal_complete": terminal_complete,
            "missing_by_session": missing,
            "actionable_missing_by_session": actionable_missing,
            "future_sessions": future_sessions,
        },
        "provenance": {
            "missing": provenance_missing,
            "mismatches": provenance_mismatch,
            "premature_present": premature_present,
        },
        "current_exit_audit": audit_summary,
        "current_data_gate": data_gate,
        "current_source_health": source_health,
        "h6_feature_inputs": h6,
        "real_h7_ledger": {
            "valid": ledger.valid,
            "empty": ledger.empty,
            "count": ledger.count,
            "head": ledger.head,
        },
        "source_identity": source,
        "commands": _commands(terminal, cutoff),
        "manual_final_action": "Cancel in the ThetaData account portal only after every receipt verifies.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--cutoff", type=date.fromisoformat, default=DEFAULT_CUTOFF)
    parser.add_argument("--today", type=date.fromisoformat)
    parser.add_argument("--chain-dir", type=Path, default=DEFAULT_CHAIN_DIR)
    parser.add_argument("--close-dir", type=Path, default=DEFAULT_CLOSE_DIR)
    parser.add_argument("--facts", type=Path, default=DEFAULT_FACTS_PATH)
    parser.add_argument("--ledger-dir", type=Path, default=DEFAULT_LEDGER_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    today = args.today or datetime.now(ZoneInfo("America/New_York")).date()
    try:
        report = build_preflight(
            cutoff=args.cutoff,
            today=today,
            chain_dir=args.chain_dir,
            close_dir=args.close_dir,
            facts_path=args.facts,
            ledger_dir=args.ledger_dir,
        )
    except (OSError, ValueError, csv.Error, h7_event_ledger.LedgerError) as exc:
        print(f"THETADATA CUTOFF PREFLIGHT ERROR -- {type(exc).__name__}: {exc}")
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        cache = report["cache"]
        audit = report["current_exit_audit"]
        print(
            f"ThetaData cutoff preflight: {report['status']} -- cutoff "
            f"{report['cutoff']}, terminal {report['terminal_session']}"
        )
        print(
            f"scope={len(report['scope'])} cohort_latest={cache['cohort_latest']} "
            f"present={cache['present_symbol_sessions']}/"
            f"{cache['required_symbol_sessions']} audit={audit['verdict']}"
        )
        print(
            f"H6 inputs={'READY' if report['h6_feature_inputs']['ready'] else 'BLOCK'} "
            "H7 ledger="
            + (
                "VALID EMPTY"
                if report["real_h7_ledger"]["valid"]
                and report["real_h7_ledger"]["empty"]
                and report["real_h7_ledger"]["count"] == 0
                else "BLOCK"
            )
        )
        print(
            f"data_gate={report['current_data_gate']['whole_universe_verdict']} "
            f"source_health={report['current_source_health']['healthy_count']}/"
            f"{len(report['scope'])} (activation remains closed)"
        )
        for blocker in report["blockers"]:
            print(f"  BLOCK: {blocker}")
        print("paid pull authorized: NO (explicit owner authorization still required)")
    return 2 if report["status"] == "BLOCK" else 0


if __name__ == "__main__":
    raise SystemExit(main())
