"""Cached-only full-stack base-rate measurement for h7-forward-schwab-v1.

The tool evaluates the frozen H7 watcher decisions and board allocator over
exact cached chain sessions. It performs no provider construction and emits no
accept/reject decision; the owner decides what the measured sparsity means.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from data.atomic_io import atomic_text_write  # noqa: E402
from data.cache_runner import session_close_utc  # noqa: E402
from data.underlying_closes import (  # noqa: E402
    CACHE_DIR as UNDERLYING_CACHE_DIR,
)
from data.underlying_closes import (
    adjustment_factor,
    load_closes_adjusted,
)
from options_researcher.chains import load_range  # noqa: E402
from options_researcher.h7_board import resolve_board  # noqa: E402
from options_researcher.h7_earnings import (  # noqa: E402
    ASSERTIONS_PATH,
    RAW_ASSERTIONS_PATH,
    load_assertions,
)
from options_researcher.h7_watch import assemble_name  # noqa: E402
from research.hashing import (  # noqa: E402
    canonical_json,
    config_hash,
    sha256_file,
    sha256_hex,
)
from tools.h7_entry_variant_menu import (  # noqa: E402
    OCCUPANCY_LOCKOUT_SESSIONS,
    occupancy_constrained_count,
)

RECEIPT_KIND = "h7_schwab_feasibility/v1"
STACK_VERSION = "h7-frozen-entry-stack-plus-board/v1"
DEFAULT_CHAIN_DIR = Path(".cache/chains")


def _receipt_hash(receipt: dict) -> str:
    unhashed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    return sha256_hex(canonical_json(unhashed))


def verify_receipt(receipt: dict) -> bool:
    return receipt.get("receipt_hash") == _receipt_hash(receipt)


def summarize_counts(
    *,
    sessions: list[str],
    symbols: list[str],
    passing_symbol_days: set[tuple[str, str]],
    window_sessions: int,
    code_sha: str,
    stack_version: str,
    errors: list[dict],
    input_paths: dict[str, Path] | None = None,
    entry_rows: list[dict] | None = None,
) -> dict:
    """Apply the owner-approved arithmetic without interpreting the result."""
    if not sessions or not symbols or window_sessions <= 0:
        raise ValueError("sessions, symbols, and positive window_sessions are required")
    possible = {(session, symbol) for session in sessions for symbol in symbols}
    if not passing_symbol_days <= possible:
        raise ValueError("passing_symbol_days contains a row outside the census")
    symbol_days = len(possible)
    passes = len(passing_symbol_days)
    base_rate = passes / symbol_days
    expected_entries = base_rate * window_sessions * len(symbols)
    rows = (
        [
            {"session": session, "symbol": symbol, "lane": "unknown"}
            for session, symbol in passing_symbol_days
        ]
        if entry_rows is None
        else entry_rows
    )
    occupancy_count = occupancy_constrained_count(
        rows, sessions, OCCUPANCY_LOCKOUT_SESSIONS[0]
    )
    occupancy_expected = occupancy_count * window_sessions / len(sessions)
    input_files = {
        label: {"path": str(path), "sha256": sha256_file(path)}
        for label, path in sorted((input_paths or {}).items())
    }
    receipt = {
        "receipt_kind": RECEIPT_KIND,
        "provenance": "LLM/tool-computed",
        "tool_label": "cached-only read-only measurement; no verdict",
        "lookback_start": sessions[0],
        "lookback_end": sessions[-1],
        "lookback_sessions": len(sessions),
        "stack_version": stack_version,
        "code_sha": code_sha,
        "config_hash": config_hash(),
        "universe": symbols,
        "universe_size": len(symbols),
        "window_sessions": window_sessions,
        "symbol_days": symbol_days,
        "full_stack_passes": passes,
        "base_rate": base_rate,
        "expected_entries": expected_entries,
        "occupancy_constrained_expected_entries": occupancy_expected,
        "occupancy_lockout_sessions": OCCUPANCY_LOCKOUT_SESSIONS[0],
        "input_files": input_files,
        "passing_symbol_days": [
            {"session": session, "symbol": symbol}
            for session, symbol in sorted(passing_symbol_days)
        ],
        "errors": errors,
        "error_count": len(errors),
        "method": {
            "signal_and_execution": "options_researcher.h7_watch.assemble_name",
            "allocation": "options_researcher.h7_board.resolve_board",
            "data": "existing .cache/chains plus .cache/underlying only",
            "error_policy": "unavailable symbol-day counts in denominator and cannot pass",
            "portfolio_state_assumption": (
                "each historical session starts with no open H7 positions and "
                "the full frozen monthly sleeve; same-session board caps apply"
            ),
        },
    }
    receipt["receipt_hash"] = _receipt_hash(receipt)
    return receipt


def write_receipt(receipt: dict, path: Path) -> None:
    if not verify_receipt(receipt):
        raise ValueError("refusing to write a receipt with an invalid hash")
    text = json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
    path = Path(path)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise FileExistsError(f"immutable feasibility receipt conflict: {path}")
        return
    atomic_text_write(text, path)


def common_cached_sessions(
    symbols: list[str], chain_dir: Path, lookback_sessions: int
) -> list[str]:
    """Return the last N dates with an exact chain file for every symbol."""
    common: set[str] | None = None
    for symbol in symbols:
        dates = {
            path.stem.removeprefix(f"{symbol}_")
            for path in Path(chain_dir).glob(f"{symbol}_????-??-??.parquet")
        }
        common = dates if common is None else common & dates
    ordered = sorted(common or set())
    if len(ordered) < lookback_sessions:
        raise RuntimeError(
            f"only {len(ordered)} common cached sessions; need {lookback_sessions}"
        )
    return ordered[-lookback_sessions:]


def measure_cached_history(
    *,
    sessions: list[str],
    symbols: list[str],
    window_sessions: int,
    code_sha: str,
) -> dict:
    assertions = load_assertions()
    passing: set[tuple[str, str]] = set()
    passing_rows: list[dict] = []
    errors: list[dict] = []
    for session in sessions:
        today = date.fromisoformat(session)
        start = (today - timedelta(days=560)).isoformat()
        cards: list[tuple[str, dict]] = []
        for symbol in symbols:
            try:
                closes = load_closes_adjusted(
                    symbol, start, session, allow_oos=True
                )
                if closes.empty or str(closes.index[-1])[:10] != session:
                    raise RuntimeError("adjusted closes do not end on session")
                chain = load_range(symbol, session, session, allow_oos=True).get(
                    session
                )
                if chain is None:
                    raise RuntimeError("exact-session chain unavailable")
                spot = float(closes.iloc[-1]) * adjustment_factor(symbol, session)
                card = assemble_name(
                    symbol=symbol,
                    closes=closes,
                    chain=chain,
                    today=today,
                    assertions=assertions,
                    known_as_of=session_close_utc(session),
                    open_positions=(),
                    spot=spot,
                    open_h7c=0,
                    month_spent=0.0,
                )
                cards.append((symbol, card))
            except Exception as exc:
                errors.append(
                    {
                        "session": session,
                        "symbol": symbol,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
        candidates = [
            {
                "symbol": symbol,
                "lane": lane[-1],
                "session": session,
                "action": card[lane]["action"],
            }
            for symbol, card in cards
            for lane in ("lane_a", "lane_b", "lane_c")
            if card[lane]["state"] == "ENTRY-OK"
        ]
        accepted, _ = resolve_board(
            candidates,
            open_h7c=0,
            sleeve_left=config.H7_MONTHLY_AT_RISK,
            open_symbols=(),
        )
        passing.update((session, row["symbol"]) for row in accepted)
        passing_rows.extend(
            {"session": session, "symbol": row["symbol"], "lane": row["lane"]}
            for row in accepted
        )
    input_paths: dict[str, Path] = {
        "gating_assertions": ASSERTIONS_PATH,
        "raw_assertions": RAW_ASSERTIONS_PATH,
    }
    for symbol in symbols:
        input_paths[f"underlying:{symbol}"] = (
            Path(UNDERLYING_CACHE_DIR) / f"{symbol}.parquet"
        )
        for session in sessions:
            input_paths[f"chain:{symbol}:{session}"] = (
                DEFAULT_CHAIN_DIR / f"{symbol}_{session}.parquet"
            )
    return summarize_counts(
        sessions=sessions,
        symbols=symbols,
        passing_symbol_days=passing,
        window_sessions=window_sessions,
        code_sha=code_sha,
        stack_version=STACK_VERSION,
        errors=errors,
        input_paths=input_paths,
        entry_rows=passing_rows,
    )


def _code_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compute cached-only H7 full-stack base rate; no verdict."
    )
    parser.add_argument("--lookback-sessions", type=int, default=70)
    parser.add_argument("--window-sessions", type=int, default=70)
    parser.add_argument(
        "--symbols",
        nargs="+",
        required=True,
        help="Explicit cohort symbols; no default universe is inferred.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/h7_forward_schwab/2026-08-09-feasibility.json"),
    )
    args = parser.parse_args(argv)
    symbols = sorted(dict.fromkeys(symbol.upper() for symbol in args.symbols))
    sessions = common_cached_sessions(
        symbols, DEFAULT_CHAIN_DIR, args.lookback_sessions
    )
    receipt = measure_cached_history(
        sessions=sessions,
        symbols=symbols,
        window_sessions=args.window_sessions,
        code_sha=_code_sha(),
    )
    write_receipt(receipt, args.output)
    print(f"receipt={args.output}")
    print(
        "LLM/tool-computed: "
        f"passes={receipt['full_stack_passes']}/{receipt['symbol_days']} "
        f"base_rate={receipt['base_rate']:.12f} "
        f"expected_entries={receipt['expected_entries']:.6f}"
    )
    print("NO PASS/FAIL DECISION EMITTED; OWNER DECIDES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
