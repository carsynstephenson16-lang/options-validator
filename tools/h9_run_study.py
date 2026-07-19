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
import re
import subprocess
import sys
from pathlib import Path

import config
from research.facts import read_facts

# B4: the frozen spec path is sourced from config (H9_SPEC_PATH), so the freeze
# commit renames the spec and updates config atomically -- the CLI never carries
# a stale "-DRAFT" filename that would FileNotFoundError after the rename.
SPEC_PATH = Path(config.H9_SPEC_PATH)
CENSUS_ARTIFACT = Path("reports/h9/census.json")
RECEIPT_PATH = Path("reports/h9/receipt.json")

# C5: a registration fact may bind the frozen spec's sha256 as `spec_sha256=<hex>`.
_SPEC_SHA_RE = re.compile(r"spec_sha256=([0-9a-f]{64})")


def h9_prereg_gate(base_dir="ledger") -> str | None:
    lines = read_facts(base_dir=base_dir)
    registered = [line for line in lines
                  if line.split("\t", 1)[-1].startswith("H9_REGISTERED")]
    if not registered:
        return ("H9 is not registered: no H9_REGISTERED fact in facts.log; "
                "the owner's external review and registration precede any data read. Refusing.")
    # C5: when the registration fact binds a spec sha256, the on-disk spec MUST
    # match it -- otherwise the frozen spec drifted after registration and the
    # census/run would bind a different document than the one owner-reviewed.
    on_disk = None
    for line in registered:
        m = _SPEC_SHA_RE.search(line)
        if not m:
            continue
        if on_disk is None:
            from research.hashing import sha256_file
            on_disk = sha256_file(SPEC_PATH)
        if m.group(1) != on_disk:
            return ("H9 spec drift: registered spec_sha256="
                    f"{m.group(1)} != on-disk {on_disk} ({SPEC_PATH}); the frozen "
                    "spec changed after registration. Refusing.")
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
    from options_researcher.h7_earnings import load_raw_assertions
    from options_researcher.h9_events import derive_events, load_event_classes
    return derive_events(load_raw_assertions(), symbols=tuple(config.H9_NAMES),
                         event_classes=load_event_classes())


def next_report_map(events) -> dict[str, list[str]]:
    """Per-symbol sorted next-report exit set, from the CLASSIFIED QUARTERLY
    events ONLY (spec §2).

    B2: `derive_events` also returns the excluded events (business_update,
    other_item_202, unclassified) with `occurred_date` populated but
    `exclusion` set. Those must NEVER become a "next report": a non-quarterly
    8-K inside the near-report window would either trip the contaminated-
    geometry fail-loud in h9_study (voiding the one run) or silently shorten a
    hold. Only quarterly events (exclusion is None) time out and gate exits.
    """
    out: dict[str, list[str]] = {}
    for e in events:
        if e.exclusion is not None:
            continue
        out.setdefault(e.symbol, []).append(e.occurred_date.isoformat())
    for sym in out:
        out[sym].sort()
    return out


def _run_census(chain_dir: Path) -> dict:
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
    from data.thetadata_adapter import load_cached_chain
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
        # Cache-ONLY (spec §1): a missing chain raises FileNotFoundError, which
        # simulate_trade records as a data gap -- the paid client is never built.
        return load_cached_chain(sym, iso, allow_oos=True)

    occurred_by_symbol = next_report_map(events)
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
    try:
        from options_researcher.h9_events import load_event_classes
        load_event_classes()
    except FileNotFoundError:
        print("no event-classification file (data/earnings/h9_event_class_v1.csv); "
              "the SEC classification pass must complete before census. Refusing.")
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
