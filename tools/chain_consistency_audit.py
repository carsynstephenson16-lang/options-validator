"""Read-only receipts for display-only Schwab chain-consistency observations."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Sequence

import pandas as pd
import pandas_market_calendars as mcal

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import config  # noqa: E402
from data import underlying_closes  # noqa: E402
from data.chain_consistency import audit_pair  # noqa: E402
from data.underlying_closes import load_closes  # noqa: E402
from research.receipts import make_receipt, write_immutable_receipt  # noqa: E402

DEFAULT_CHAIN_DIR = Path(".cache/schwab_chains")
DEFAULT_OUT_DIR = Path(".tmp/chain_consistency")
OPT_IN_REPORTS_DIR = Path("reports/chain_consistency")
RECEIPT_TYPE = "chain_consistency_audit"
_SOURCE_PATHS = ("config.py", "data/chain_consistency.py", "tools/chain_consistency_audit.py")


def _session_from_name(path: Path) -> tuple[str, str] | None:
    if path.suffix != ".parquet" or "_" not in path.stem:
        return None
    symbol, session = path.stem.rsplit("_", 1)
    if not symbol:
        return None
    try:
        return symbol, date.fromisoformat(session).isoformat()
    except ValueError:
        return None


def _available_sessions(chain_dir: Path) -> dict[str, list[str]]:
    sessions: dict[str, list[str]] = {}
    for path in sorted(chain_dir.glob("*.parquet")):
        parsed = _session_from_name(path)
        if parsed is None:
            continue
        symbol, session = parsed
        sessions.setdefault(symbol, []).append(session)
    return {symbol: sorted(set(values)) for symbol, values in sorted(sessions.items())}


def _calendar_sessions(start: str, end: str) -> tuple[str, ...]:
    """XNYS sessions for the submitted range; calendar construction stays here."""
    calendar = mcal.get_calendar("XNYS")
    schedule = calendar.schedule(start_date=start, end_date=end)
    return tuple(pd.Timestamp(value).date().isoformat() for value in schedule.index)


def _close_for_session(closes: pd.Series, session: str) -> float:
    by_session = {
        pd.Timestamp(index).date().isoformat(): float(value) for index, value in closes.items()
    }
    if session not in by_session:
        raise ValueError(f"underlying close cache has no row for {session}")
    return by_session[session]


def _source_identity() -> dict[str, object]:
    source_files: dict[str, str] = {}
    for relative in _SOURCE_PATHS:
        path = REPO_ROOT / relative
        source_files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "git_sha": result.stdout.strip() if result.returncode == 0 else None,
        "source_files": source_files,
    }


def _file_record(path: Path, *, root: Path) -> dict[str, object]:
    return {
        "path": str(path.relative_to(root)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _constants() -> dict[str, float | int]:
    return {
        "CONSISTENCY_DELTA_JUMP_ABS": config.CONSISTENCY_DELTA_JUMP_ABS,
        "CONSISTENCY_UNDERLYING_SMALL_MOVE": config.CONSISTENCY_UNDERLYING_SMALL_MOVE,
        "CONSISTENCY_SPREAD_BLOWOUT_MIN_RATIO": config.CONSISTENCY_SPREAD_BLOWOUT_MIN_RATIO,
        "CONSISTENCY_MAX_EXAMPLES": config.CONSISTENCY_MAX_EXAMPLES,
        "MAX_SPREAD_PCT": config.MAX_SPREAD_PCT,
        "MIN_OPEN_INTEREST": config.MIN_OPEN_INTEREST,
    }


def _underlying_close_path(symbol: str, *, root: Path) -> Path:
    cache_dir = Path(underlying_closes.CACHE_DIR)
    if not cache_dir.is_absolute():
        cache_dir = root / cache_dir
    return cache_dir / f"{symbol}.parquet"


def _record_for_pair(
    symbol: str,
    prev_session: str,
    cur_session: str,
    *,
    chain_dir: Path,
    root: Path,
    calendar_sessions: Sequence[str],
) -> dict[str, object]:
    prev_path = chain_dir / f"{symbol}_{prev_session}.parquet"
    cur_path = chain_dir / f"{symbol}_{cur_session}.parquet"
    close_path = _underlying_close_path(symbol, root=root)
    previous = pd.read_parquet(prev_path)
    current = pd.read_parquet(cur_path)
    closes = load_closes(symbol, prev_session, cur_session, allow_oos=True)
    report = audit_pair(
        previous,
        current,
        _close_for_session(closes, prev_session),
        _close_for_session(closes, cur_session),
        prev_session=prev_session,
        cur_session=cur_session,
        calendar_sessions=calendar_sessions,
    )
    return {
        "status": "AUDITED",
        "pair": {"previous_session": prev_session, "current_session": cur_session},
        "input_files": {
            "previous_chain": _file_record(prev_path, root=root),
            "current_chain": _file_record(cur_path, root=root),
            "underlying_close": _file_record(close_path, root=root),
        },
        "report": report.as_dict(),
    }


def _select_pair(
    sessions: list[str], explicit_pair: tuple[str, str] | None
) -> tuple[str, str] | None:
    if explicit_pair is not None:
        return explicit_pair if all(session in sessions for session in explicit_pair) else None
    return tuple(sessions[-2:]) if len(sessions) >= 2 else None


def build_receipt_payload(
    symbols: dict[str, dict[str, object]],
    *,
    calendar_sessions: Sequence[str],
    max_as_of_session: str,
) -> dict[str, object]:
    return {
        "receipt_type_note": "display-only chain-consistency observations; no gate, rank, or trade authority",
        "max_as_of_session": max_as_of_session,
        "constants": _constants(),
        "constant_provenance": (
            "Brief 22 WP-0 corruption-target assumptions; IV_JUMP was removed after its pre-declared 1% clean-rate kill criterion failed."
        ),
        "calendar_sessions": list(calendar_sessions),
        "producer": _source_identity(),
        "symbols": symbols,
    }


def _output_dir(root: Path, requested: str | None) -> Path:
    root = Path(root).resolve()
    relative = DEFAULT_OUT_DIR if requested is None else Path(requested)
    output = relative if relative.is_absolute() else root / relative
    canonical_output = output.resolve()
    allowed_paths = tuple(root / candidate for candidate in (DEFAULT_OUT_DIR, OPT_IN_REPORTS_DIR))
    allowed = tuple(candidate.resolve() for candidate in allowed_paths)
    if any(path != candidate for path, candidate in zip(allowed_paths, allowed, strict=True)):
        raise ValueError(
            "--out-dir must be under .tmp/chain_consistency/ or reports/chain_consistency/"
        )
    if not any(
        canonical_output == candidate or canonical_output.is_relative_to(candidate)
        for candidate in allowed
    ):
        raise ValueError(
            "--out-dir must be under .tmp/chain_consistency/ or reports/chain_consistency/"
        )
    return canonical_output


def run_audit(
    *,
    root: Path = REPO_ROOT,
    pair: tuple[str, str] | None = None,
) -> tuple[dict[str, object], str]:
    """Build one deterministic receipt payload from local Schwab cache files."""
    root = Path(root)
    chain_dir = root / DEFAULT_CHAIN_DIR
    if not chain_dir.is_dir():
        raise FileNotFoundError(f"Schwab chain cache is absent: {chain_dir}")
    available = _available_sessions(chain_dir)
    if not available:
        raise FileNotFoundError(f"Schwab chain cache contains no dated parquet files: {chain_dir}")

    all_sessions = sorted({session for values in available.values() for session in values})
    start = (date.fromisoformat(all_sessions[0]) - timedelta(days=7)).isoformat()
    calendar = _calendar_sessions(start, all_sessions[-1])
    symbols: dict[str, dict[str, object]] = {}
    for symbol, sessions in available.items():
        selected = _select_pair(sessions, pair)
        if selected is None:
            status = "PAIR_UNAVAILABLE" if pair is not None else "INSUFFICIENT_HISTORY"
            symbols[symbol] = {"status": status, "available_sessions": sessions}
            continue
        prev_session, cur_session = selected
        symbols[symbol] = _record_for_pair(
            symbol,
            prev_session,
            cur_session,
            chain_dir=chain_dir,
            root=root,
            calendar_sessions=calendar,
        )
    latest_session = max(all_sessions)
    return (
        build_receipt_payload(
            symbols,
            calendar_sessions=calendar,
            max_as_of_session=latest_session,
        ),
        latest_session,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", nargs=2, metavar=("PREV", "CUR"))
    parser.add_argument(
        "--out-dir", help=".tmp/chain_consistency/ by default; reports/chain_consistency/ is opt-in"
    )
    return parser


def main(argv: list[str] | None = None, *, root: Path = REPO_ROOT) -> int:
    args = build_parser().parse_args(argv)
    try:
        pair = None
        if args.pair is not None:
            pair = tuple(date.fromisoformat(value).isoformat() for value in args.pair)
            if pair[0] >= pair[1]:
                raise ValueError("--pair PREV must be earlier than CUR")
        payload, latest_session = run_audit(root=root, pair=pair)
        receipt = make_receipt(RECEIPT_TYPE, payload)
        out_dir = _output_dir(Path(root), args.out_dir)
        path = out_dir / f"chain_consistency_{latest_session}_{receipt['receipt_hash'][:12]}.json"
        write_immutable_receipt(receipt, path)
        print(path)
        return 0
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"chain consistency audit failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
