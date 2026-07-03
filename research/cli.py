"""
research/cli.py -- the integrity seams as distinct subcommands.

Distinct subcommands so a future PreToolUse hook can gate them individually
(allow an in-sample run, block an OOS reveal or a ledger rewrite). No hook is
built in Phase 1A -- these are the seams it would attach to.

Usage: uv run python -m research.cli <verify|trial-log|register|reveal-oos> ...
"""
from __future__ import annotations

import argparse
import json
import sys

from research import experiments, ledger


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="research.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_ledger(p):
        p.add_argument("--ledger", default="ledger", help="ledger base dir")
        return p

    p_verify = sub.add_parser("verify")
    add_ledger(p_verify)
    p_verify.add_argument("--anchored", action="store_true")

    p_trial = sub.add_parser("trial-log")
    add_ledger(p_trial)
    p_trial.add_argument("--reason", required=True)

    p_register = sub.add_parser("register")
    add_ledger(p_register)
    p_register.add_argument("--hypothesis-id", required=True)
    p_register.add_argument("--decision-threshold", required=True)
    p_register.add_argument("--is-result-json", required=True)
    p_register.add_argument("--data-window-json", required=True)
    p_register.add_argument("--risk-basis", required=True)
    p_register.add_argument("--notes", default="")

    p_reveal = sub.add_parser("reveal-oos")
    add_ledger(p_reveal)
    p_reveal.add_argument("--hypothesis-id", required=True)

    args = parser.parse_args(argv)

    if args.cmd == "verify":
        try:
            ledger.verify(args.ledger, anchored=args.anchored)
        except ledger.LedgerError as exc:
            print(f"INTEGRITY FAIL: {exc}", file=sys.stderr)
            return 1
        print("ledger OK")
        return 0

    if args.cmd == "trial-log":
        try:
            experiments.log_trial_intent(args.reason, base_dir=args.ledger)
        except ledger.LedgerError as exc:
            print(f"INTEGRITY FAIL: {exc}", file=sys.stderr)
            return 1
        print(f"trial logged; count = {experiments.current_trial_count(args.ledger)}")
        return 0

    if args.cmd == "register":
        try:
            experiments.register(
                args.hypothesis_id,
                args.decision_threshold,
                json.loads(args.is_result_json),
                data_window=json.loads(args.data_window_json),
                risk_basis=args.risk_basis,
                notes=args.notes,
                base_dir=args.ledger,
            )
        except (ValueError, experiments.OOSGateError, ledger.LedgerError) as exc:
            print(f"REGISTER REFUSED: {exc}", file=sys.stderr)
            return 1
        print("hypothesis registered")
        return 0

    if args.cmd == "reveal-oos":
        from harness import run_backtest
        try:
            run_backtest.reveal_out_of_sample(args.hypothesis_id, base_dir=args.ledger)
        except (experiments.OOSGateError, ledger.LedgerError) as exc:
            print(f"OOS GATE REFUSED: {exc}", file=sys.stderr)
            return 1
        except NotImplementedError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print("OOS revealed")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
