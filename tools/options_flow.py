"""Offline options-flow planning and historical capture CLI.

The default command is dry-run. Non-dry ThetaData execution is retained as a
historical seam but is operator-disabled before any output or provider call.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.options_flow.adapter import fetch_session
from data.options_flow.raw_store import RawFlowStore

DEFAULT_SYMBOLS = ("MSFT", "CEG", "VST")


def _trading_days(start: str, end: str) -> list[str]:
    from data.cache_runner import trading_days

    return trading_days(start, end)


def _symbols(value: str) -> list[str]:
    symbols = [item.strip().upper() for item in value.split(",") if item.strip()]
    if not symbols or any(not symbol.isalnum() for symbol in symbols):
        raise argparse.ArgumentTypeError("symbols must be comma-separated ticker names")
    return list(dict.fromkeys(symbols))


def _iso_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO date: {value}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture bounded ThetaData options flow")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="plan requests without network (the default)",
    )
    mode.add_argument(
        "--execute",
        action="store_true",
        help="retired ThetaData fetch mode; fails closed before any write",
    )
    parser.add_argument("--symbols", type=_symbols, default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--max-symbols", type=int, default=3)
    parser.add_argument("--start-date", type=_iso_date, required=True)
    parser.add_argument("--end-date", type=_iso_date, required=True)
    parser.add_argument("--output", type=Path, default=Path(".cache/options_flow"))
    return parser


def run(args: argparse.Namespace) -> int:
    if args.max_symbols < 1:
        raise ValueError("--max-symbols must be positive")
    if args.start_date > args.end_date:
        raise ValueError("--start-date must not be after --end-date")
    if getattr(args, "execute", False):
        from data import provider_policy

        provider_policy.require_thetadata_acquisition("options-flow capture")
    symbols = list(args.symbols)[: args.max_symbols]
    sessions = _trading_days(args.start_date, args.end_date)
    requests = len(symbols) * len(sessions) * 2
    print(f"symbols={','.join(symbols)} sessions={len(sessions)} requests={requests}")
    if not getattr(args, "execute", False):
        print("dry_run=true network=false")
        return 0
    store = RawFlowStore(args.output)
    for symbol in symbols:
        for session in sessions:
            fetch = fetch_session(symbol, session)
            result = store.write_fetch(fetch)
            print(
                f"captured {result['symbol']} {result['session']} "
                f"trades={result['trade_rows']} oi={result['oi_rows']}"
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
