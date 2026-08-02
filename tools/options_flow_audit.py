"""Print the mandatory options-flow data audit for a normalized parquet file."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from data.options_flow.audit import audit_options_data, render_audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit normalized options-flow data")
    parser.add_argument("trade_quote", type=Path)
    parser.add_argument(
        "--expected-session",
        action="append",
        default=[],
        help="expected ISO session; repeat to audit completeness",
    )
    return parser


def run(args: argparse.Namespace) -> int:
    frame = pd.read_parquet(args.trade_quote)
    result = audit_options_data(
        frame,
        expected_sessions=args.expected_session or None,
    )
    print(render_audit(result))
    return 2 if result.verdict == "BLOCK" else 0


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
