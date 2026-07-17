"""H9 written-study CLI — census and the single gated run.

Refusal order (all BEFORE any market data module is imported):
  1. h9_prereg_gate: H9_REGISTERED fact must exist (owner external review
     precedes that fact per spec §8 order).
  2. h9_one_run_gate (run only): refuse when an H9_RESULT fact exists.
  3. run requires the census artifact with floor_met=true.
This tool never touches the H7 forward ledger or the tombstoned H7
diagnostic path.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from research.facts import read_facts

SPEC_PATH = Path("docs/superpowers/specs/2026-07-16-h9-post-earnings-historical-study-DRAFT.md")
CENSUS_ARTIFACT = Path("reports/h9/census.json")
RECEIPT_PATH = Path("reports/h9/receipt.json")


def h9_prereg_gate(base_dir="ledger") -> str | None:
    lines = read_facts(base_dir=base_dir)
    if not any(line.split("\t", 1)[-1].startswith("H9_REGISTERED") for line in lines):
        return ("H9 is not registered: no H9_REGISTERED fact in facts.log; "
                "the owner's external review and registration precede any data read. Refusing.")
    return None


def h9_one_run_gate(base_dir="ledger") -> str | None:
    lines = read_facts(base_dir=base_dir)
    if any(line.split("\t", 1)[-1].startswith("H9_RESULT") for line in lines):
        return "H9_RESULT already exists: the one-run contract is spent. Refusing."
    return None


def _code_sha() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()


def _events():
    import config
    from options_researcher.h7_earnings import load_raw_assertions
    from options_researcher.h9_events import derive_events
    return derive_events(load_raw_assertions(), symbols=tuple(config.H9_NAMES))


def _run_census(chain_dir: Path) -> dict:
    import config
    from options_researcher.h9_census import run_census
    from research.hashing import canonical_json, config_hash, sha256_file, sha256_hex
    res = run_census(_events(), chain_dir=chain_dir)
    payload = {
        "eligible_count": res.eligible_count,
        "per_symbol": res.per_symbol,
        "reasons": dict(res.reasons),
        "exit_window_gap_days": res.exit_window_gap_days,
        "floor": config.H9_MIN_ELIGIBLE_EVENTS,
        "floor_met": res.floor_met,
        "manifest_hash": sha256_hex(canonical_json(sorted(res.manifest))),
        "spec_sha256": sha256_file(SPEC_PATH),
        "code_sha": _code_sha(),
        "config_hash": config_hash(),
    }
    CENSUS_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    CENSUS_ARTIFACT.write_text(json.dumps(payload, indent=1, sort_keys=True))
    return payload


def _run_study(chain_dir: Path) -> dict:
    import config
    from data.thetadata_adapter import get_eod_chain
    from data.underlying_closes import load_closes_adjusted
    from options_researcher.h9_census import run_census
    from options_researcher.h9_study import adjudicate, simulate_trade, trigger
    from research.hashing import (
        canonical_json,
        config_hash,
        cost_model_hash,
        sha256_file,
        sha256_hex,
    )

    events = _events()
    census = run_census(events, chain_dir=chain_dir)

    def provider(sym, iso):
        return get_eod_chain(sym, iso, allow_oos=True)

    occurred_by_symbol: dict[str, list[str]] = {}
    for e in events:
        occurred_by_symbol.setdefault(e.symbol, []).append(e.occurred_date.isoformat())
    trades, log = [], []
    for e in census.eligible_events:
        closes = load_closes_adjusted(e.symbol, e.t_pre, e.t_dec, allow_oos=True)
        sig = trigger(e, closes)
        if sig != "call":
            log.append({"event": f"{e.symbol}-{e.occurred_date}", "outcome": sig})
            continue
        nxt = sorted(d for d in occurred_by_symbol[e.symbol]
                     if d > e.occurred_date.isoformat())
        trade = simulate_trade(e, provider, next_report_iso=nxt[0] if nxt else None)
        if trade is None:
            log.append({"event": f"{e.symbol}-{e.occurred_date}", "outcome": "cancel"})
            continue
        trade["event"] = f"{e.symbol}-{e.occurred_date}"
        trades.append(trade)
    board = adjudicate(trades)
    secondary_trades = [t for t in trades if t["symbol"] in config.H9_SECONDARY_COHORT]
    secondary = adjudicate(secondary_trades) if secondary_trades else {}
    receipt = {
        "study": "H9", "outcome": board["h9_outcome"], "board": board,
        "secondary_cohort_informational": secondary.get("h9_outcome"),
        "census": json.loads(CENSUS_ARTIFACT.read_text()),
        "n_trades": len(trades), "no_trade_log_count": len(log),
        "trade_log": log, "trades": trades,
        "spec_sha256": sha256_file(SPEC_PATH), "code_sha": _code_sha(),
        "config_hash": config_hash(), "cost_model_hash": cost_model_hash(),
    }
    bulk = {"trades", "trade_log", "board", "census"}
    receipt["receipt_hash"] = sha256_hex(canonical_json(
        {k: v for k, v in receipt.items() if k not in bulk}))
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=1, sort_keys=True, default=str))
    return receipt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("census", "run"))
    ap.add_argument("--chain-dir", default=".cache/chains")
    ap.add_argument("--ledger-dir", default="ledger")
    args = ap.parse_args(argv)
    refusal = h9_prereg_gate(base_dir=args.ledger_dir)
    if refusal:
        print(refusal)
        return 2
    if args.mode == "run":
        refusal = h9_one_run_gate(base_dir=args.ledger_dir)
        if refusal:
            print(refusal)
            return 2
        if not CENSUS_ARTIFACT.exists():
            print("no census artifact; run census first. Refusing.")
            return 2
        census = json.loads(CENSUS_ARTIFACT.read_text())
        if not census["floor_met"]:
            print("census floor unmet: outcome is INSUFFICIENT_SAMPLE without a run. Refusing.")
            return 2
        receipt = _run_study(Path(args.chain_dir))
        print(f"outcome={receipt['outcome']} receipt_hash={receipt['receipt_hash']}")
        return 0
    payload = _run_census(Path(args.chain_dir))
    print(f"eligible={payload['eligible_count']} floor_met={payload['floor_met']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
