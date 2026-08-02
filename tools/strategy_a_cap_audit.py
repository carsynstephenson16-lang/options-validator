"""Deterministic, cache-only audit of Strategy A's D+1 hard-cap gate.

This is a mechanical replay of the entry path, not a backtest and not evidence
of edge. It reads only explicitly selected in-sample chain files, verifies their
bytes against the immutable cache manifest, freezes the production day-D legs,
and measures the production D+1 cancellation/resizing behavior.

Canonical Q8 command::

    uv run python tools/strategy_a_cap_audit.py \
      --symbols MSFT AMZN VST CEG \
      --start 2018-01-01 --end 2022-12-31 \
      --write reports/strategy-a-cap-audit/2018-01-01_2022-12-31.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import date, timedelta
from importlib.metadata import version
from pathlib import Path
from typing import cast

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import config  # noqa: E402
from data.cache_runner import trading_days  # noqa: E402
from data.thetadata_adapter import load_cached_chain  # noqa: E402
from research.hashing import (  # noqa: E402
    canonical_json,
    config_hash,
    cost_model_hash,
    sha256_file,
    sha256_hex,
)
from strategies.base import (  # noqa: E402
    economic_max_loss_per_spread,
    entry_credit_conservative,
    size_defined_risk,
)
from strategies.put_credit_spread import (  # noqa: E402
    select_put_credit_spread_candidate,
)
from tools.cache_manifest import read_manifest  # noqa: E402

SCHEMA = "strategy-a-cap-audit/v1"
ENGINE = "post-atomicity"
DEFAULT_CACHE_DIR = Path(".cache/chains")
DEFAULT_MANIFEST = Path("data/chain_cache_manifest.txt")
SOURCE_PATHS = (
    "config.py",
    "data/cache_runner.py",
    "data/thetadata_adapter.py",
    "research/hashing.py",
    "strategies/base.py",
    "strategies/put_credit_spread.py",
    "tools/cache_manifest.py",
    "tools/strategy_a_cap_audit.py",
)


class AuditBlocked(RuntimeError):
    """Selected bytes or semantics are not safe for an authoritative receipt."""


def _display_path(path: Path, root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _source_identity(root: Path = REPO_ROOT) -> dict:
    hashes: dict[str, str] = {}
    for relative in SOURCE_PATHS:
        path = root / relative
        if not path.is_file():
            raise AuditBlocked(f"source binding missing required file: {relative}")
        hashes[relative] = sha256_file(path)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "git_commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "source_files": hashes,
        "source_files_hash": sha256_hex(canonical_json(hashes)),
        "config_hash": config_hash(),
        "cost_model_hash": cost_model_hash(),
        "dependencies": {
            "pandas": version("pandas"),
            "pandas_market_calendars": version("pandas_market_calendars"),
        },
    }


def _normalize_scope(symbols: list[str], start: str, end: str) -> tuple[list[str], date, date]:
    normalized = [symbol.strip().upper() for symbol in symbols]
    if not normalized or any(not symbol for symbol in normalized):
        raise ValueError("at least one explicit symbol is required")
    if len(set(normalized)) != len(normalized):
        raise ValueError("symbols must be unique")
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    if start_date > end_date:
        raise ValueError("start must be on or before end")
    in_sample_end = date.fromisoformat(config.IN_SAMPLE_END)
    if end_date > in_sample_end:
        raise AuditBlocked(
            f"holdout access refused: end {end_date} exceeds IN_SAMPLE_END={in_sample_end}"
        )
    return normalized, start_date, end_date


def _name_session(name: str, symbol: str) -> str | None:
    prefix = f"{symbol}_"
    suffix = ".parquet"
    if not name.startswith(prefix) or not name.endswith(suffix):
        return None
    session = name[len(prefix) : -len(suffix)]
    try:
        return date.fromisoformat(session).isoformat()
    except ValueError:
        return None


def _scope_names(names: set[str], symbols: list[str], start: date, end: date) -> set[str]:
    selected: set[str] = set()
    for name in names:
        for symbol in symbols:
            session = _name_session(name, symbol)
            if session is not None and start.isoformat() <= session <= end.isoformat():
                selected.add(name)
                break
    return selected


def _verify_one(
    name: str,
    *,
    cache_dir: Path,
    manifest: dict[str, tuple[str, int]],
) -> None:
    path = cache_dir / name
    expected = manifest.get(name)
    if expected is None:
        raise AuditBlocked(f"EXTRA selected cache file is not manifested: {name}")
    if not path.is_file():
        raise AuditBlocked(f"MISSING selected manifested cache file: {name}")
    expected_hash, expected_size = expected
    if path.stat().st_size != expected_size or sha256_file(path) != expected_hash:
        raise AuditBlocked(f"MISMATCH selected cache file: {name}")


def _verified_decision_names(
    *,
    symbols: list[str],
    start: date,
    end: date,
    cache_dir: Path,
    manifest: dict[str, tuple[str, int]],
) -> list[str]:
    expected = _scope_names(set(manifest), symbols, start, end)
    actual = _scope_names(
        {path.name for path in cache_dir.iterdir() if path.is_file()},
        symbols,
        start,
        end,
    )
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise AuditBlocked(f"MISSING selected manifested cache file: {missing[0]}")
    if extra:
        raise AuditBlocked(f"EXTRA selected cache file is not manifested: {extra[0]}")
    if not expected:
        raise AuditBlocked("selected scope contains no manifested chain files")
    for name in sorted(expected):
        _verify_one(name, cache_dir=cache_dir, manifest=manifest)
    return sorted(expected)


def _exact_leg(frame: pd.DataFrame, expiration: str, strike: float):
    rows = frame[
        (frame["right"].astype(str).str.upper() == "P")
        & (frame["expiration"].astype(str) == expiration)
        & (pd.to_numeric(frame["strike"]) == strike)
    ]
    if len(rows) > 1:
        raise AuditBlocked(f"duplicate frozen leg rows for expiration={expiration} strike={strike}")
    return None if rows.empty else rows.iloc[0]


def _rate(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else round(numerator / denominator, 12)


def _round_money(value: float) -> float:
    return round(float(value) + 0.0, 2)


def run_audit(
    *,
    symbols: list[str],
    start: str,
    end: str,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> dict:
    """Reproduce the production day-D selection and D+1 cap mechanics.

    The decision window is explicit and cannot cross the in-sample boundary.
    Every opened parquet is verified against ``manifest_path`` before it is
    loaded through the cache-only adapter.
    """
    symbols, start_date, end_date = _normalize_scope(symbols, start, end)
    cache_dir = Path(cache_dir)
    manifest_path = Path(manifest_path)
    manifest = read_manifest(str(manifest_path))
    decision_names = _verified_decision_names(
        symbols=symbols,
        start=start_date,
        end=end_date,
        cache_dir=cache_dir,
        manifest=manifest,
    )
    verified_names = set(decision_names)
    used_names = set(decision_names)

    calendar_end = min(date.fromisoformat(config.IN_SAMPLE_END), end_date + timedelta(days=14))
    sessions = trading_days(start_date.isoformat(), calendar_end.isoformat())
    next_session = {current: following for current, following in zip(sessions, sessions[1:])}

    counts = {
        "cached_chain_days": len(decision_names),
        "day_d_accepted": 0,
        "cancelled_beyond_tolerance": 0,
        "allowed_d_plus_1_fills": 0,
        "allowed_fills_requiring_resize": 0,
        "exact_frozen_leg_unavailable_d_plus_1": 0,
    }
    rejected: Counter[str] = Counter()
    unavailable: list[dict] = []
    evaluated: list[dict] = []

    for name in decision_names:
        symbol = next(symbol for symbol in symbols if name.startswith(f"{symbol}_"))
        session = _name_session(name, symbol)
        assert session is not None
        chain = load_cached_chain(symbol, session, cache_dir=cache_dir)
        selection = select_put_credit_spread_candidate(
            chain,
            date.fromisoformat(session),
            width=config.A_SPREAD_WIDTH,
            delta=config.A_SHORT_PUT_DELTA,
            dte_band=config.A_TARGET_DTE,
            haircut=config.SLIPPAGE_HAIRCUT,
        )
        if not selection.accepted:
            rejected[selection.reason] += 1
            continue

        counts["day_d_accepted"] += 1
        assert selection.expiration is not None
        assert selection.short_put is not None
        assert selection.long_put is not None
        assert selection.credit is not None
        short_put = cast(pd.Series, selection.short_put)
        long_put = cast(pd.Series, selection.long_put)
        fill_session = next_session.get(session)
        missing_base = {
            "symbol": symbol,
            "decision_date": session,
            "fill_date": fill_session,
            "expiration": selection.expiration,
            "short_strike": float(short_put["strike"]),
            "long_strike": float(long_put["strike"]),
        }
        if fill_session is None:
            counts["exact_frozen_leg_unavailable_d_plus_1"] += 1
            unavailable.append({**missing_base, "reason": "no_in_sample_next_session"})
            continue

        fill_name = f"{symbol}_{fill_session}.parquet"
        fill_path = cache_dir / fill_name
        if not fill_path.is_file() and fill_name not in manifest:
            counts["exact_frozen_leg_unavailable_d_plus_1"] += 1
            unavailable.append({**missing_base, "reason": "execution_chain_missing"})
            continue
        if fill_name not in verified_names:
            _verify_one(fill_name, cache_dir=cache_dir, manifest=manifest)
            verified_names.add(fill_name)
        used_names.add(fill_name)
        fill_chain = load_cached_chain(symbol, fill_session, cache_dir=cache_dir)
        short_row = _exact_leg(
            fill_chain,
            selection.expiration,
            float(short_put["strike"]),
        )
        long_row = _exact_leg(
            fill_chain,
            selection.expiration,
            float(long_put["strike"]),
        )
        if short_row is None or long_row is None:
            counts["exact_frozen_leg_unavailable_d_plus_1"] += 1
            unavailable.append({**missing_base, "reason": "frozen_leg_missing"})
            continue

        execution_credit = round(
            entry_credit_conservative(
                short_row["bid"],
                short_row["ask"],
                long_row["bid"],
                long_row["ask"],
                config.SLIPPAGE_HAIRCUT,
            ),
            2,
        )
        signal_credit = round(float(selection.credit), 2)
        old_risk = selection.contracts * economic_max_loss_per_spread(
            config.A_SPREAD_WIDTH, execution_credit
        )
        old_breach = max(old_risk - config.MAX_LOSS_PER_TRADE, 0.0)
        minimum_credit = round(signal_credit - config.A_ENTRY_CREDIT_TOLERANCE, 2)
        row = {
            **missing_base,
            "signal_credit": signal_credit,
            "execution_credit": execution_credit,
            "day_d_contracts": selection.contracts,
            "old_policy_risk": _round_money(old_risk),
            "old_policy_cap_breach": _round_money(old_breach),
        }
        if execution_credit < minimum_credit:
            counts["cancelled_beyond_tolerance"] += 1
            evaluated.append(
                {
                    **row,
                    "outcome": "CANCELLED_BEYOND_TOLERANCE",
                    "new_policy_contracts": 0,
                    "new_policy_risk": 0.0,
                    "new_policy_cap_breach": 0.0,
                }
            )
            continue

        fill_contracts, per_spread_risk = size_defined_risk(config.A_SPREAD_WIDTH, execution_credit)
        contracts = min(selection.contracts, fill_contracts)
        if contracts <= 0:
            raise AuditBlocked(f"allowed credit produced no cap-safe quantity: {symbol} {session}")
        new_risk = contracts * per_spread_risk
        new_breach = max(new_risk - config.MAX_LOSS_PER_TRADE, 0.0)
        if new_breach > 1e-9:
            raise AuditBlocked(
                f"production sizing breached the cap: {symbol} {session} ${new_breach:.2f}"
            )
        counts["allowed_d_plus_1_fills"] += 1
        if contracts < selection.contracts:
            counts["allowed_fills_requiring_resize"] += 1
        evaluated.append(
            {
                **row,
                "outcome": "ALLOWED_RESIZED" if contracts < selection.contracts else "ALLOWED",
                "new_policy_contracts": contracts,
                "new_policy_risk": _round_money(new_risk),
                "new_policy_cap_breach": _round_money(new_breach),
            }
        )

    old_ranked = sorted(
        evaluated,
        key=lambda row: (
            -row["old_policy_cap_breach"],
            -row["old_policy_risk"],
            row["symbol"],
            row["decision_date"],
        ),
    )
    allowed = [row for row in evaluated if row["outcome"].startswith("ALLOWED")]
    new_ranked = sorted(
        allowed,
        key=lambda row: (-row["new_policy_risk"], row["symbol"], row["decision_date"]),
    )
    input_entries = {
        name: {"sha256": manifest[name][0], "size": manifest[name][1]}
        for name in sorted(used_names)
    }
    report = {
        "schema": SCHEMA,
        "engine": ENGINE,
        "classification": "MECHANICAL_ENTRY_PATH_REPLAY",
        "scope": {
            "symbols": symbols,
            "decision_start": start_date.isoformat(),
            "decision_end": end_date.isoformat(),
            "in_sample_end": config.IN_SAMPLE_END,
            "calendar": "XNYS",
        },
        "parameters": {
            "spread_width": config.A_SPREAD_WIDTH,
            "short_put_delta": config.A_SHORT_PUT_DELTA,
            "target_dte": list(config.A_TARGET_DTE),
            "entry_credit_tolerance": config.A_ENTRY_CREDIT_TOLERANCE,
            "max_loss_per_trade": config.MAX_LOSS_PER_TRADE,
            "slippage_haircut": config.SLIPPAGE_HAIRCUT,
            "commission_per_contract": config.COMMISSION_PER_CONTRACT,
            "fill_model_id": config.FILL_MODEL_ID,
            "execution_convention": config.BACKTEST_EXECUTION_CONVENTION,
        },
        "counts": counts,
        "selection_rejections": dict(sorted(rejected.items())),
        "rates": {
            "cancellation": _rate(counts["cancelled_beyond_tolerance"], counts["day_d_accepted"]),
            "resize_given_allowed": _rate(
                counts["allowed_fills_requiring_resize"],
                counts["allowed_d_plus_1_fills"],
            ),
        },
        "risk": {
            "worst_old_policy_cap_breach": (
                old_ranked[0]["old_policy_cap_breach"] if old_ranked else 0.0
            ),
            "worst_new_policy_cap_breach": (
                max((row["new_policy_cap_breach"] for row in allowed), default=0.0)
            ),
            "highest_new_policy_allowed": (new_ranked[0]["new_policy_risk"] if new_ranked else 0.0),
        },
        "worst_old_policy_rows": old_ranked[:10],
        "highest_new_policy_rows": new_ranked[:10],
        "unavailable": unavailable,
        "manifest_scope": {
            "status": "PASS",
            "path": _display_path(manifest_path, REPO_ROOT),
            "manifest_sha256": sha256_file(manifest_path),
            "input_file_count": len(input_entries),
            "input_entries_hash": sha256_hex(canonical_json(input_entries)),
        },
        "source_identity": _source_identity(),
        "integrity": {
            "holdout_read": False,
            "provider_call": False,
            "cache_mutation": False,
            "backtest_run": False,
            "verdict_use": False,
        },
    }
    report["receipt_hash"] = sha256_hex(canonical_json(report))
    return report


def write_receipt(report: dict, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload)
    os.replace(tmp, path)
    return path


def verify_receipt(
    path: Path,
    *,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> tuple[bool, list[str]]:
    expected = json.loads(Path(path).read_text())
    scope = expected["scope"]
    actual = run_audit(
        symbols=list(scope["symbols"]),
        start=scope["decision_start"],
        end=scope["decision_end"],
        cache_dir=Path(cache_dir),
        manifest_path=Path(manifest_path),
    )
    failures = [
        key
        for key in sorted(set(expected) | set(actual))
        if canonical_json(expected.get(key)) != canonical_json(actual.get(key))
    ]
    return not failures, failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "Strategy A cap audit").splitlines()[0]
    )
    parser.add_argument("--symbols", nargs="+")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", type=Path)
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.verify is not None:
            ok, failures = verify_receipt(
                args.verify,
                cache_dir=args.cache_dir,
                manifest_path=args.manifest,
            )
            print("receipt VALID" if ok else f"receipt INVALID: {failures}")
            return 0 if ok else 2
        if args.symbols is None or args.start is None or args.end is None:
            parser.error("--symbols, --start, and --end are required unless --verify is used")
        report = run_audit(
            symbols=args.symbols,
            start=args.start,
            end=args.end,
            cache_dir=args.cache_dir,
            manifest_path=args.manifest,
        )
    except (AuditBlocked, OSError, ValueError, KeyError) as exc:
        print(f"STRATEGY A CAP AUDIT BLOCKED -- {type(exc).__name__}: {exc}")
        return 2

    counts = report["counts"]
    risk = report["risk"]
    print(
        f"Strategy A cap audit {args.start}..{args.end}: "
        f"chain_days={counts['cached_chain_days']} "
        f"accepted={counts['day_d_accepted']} "
        f"cancelled={counts['cancelled_beyond_tolerance']} "
        f"allowed={counts['allowed_d_plus_1_fills']} "
        f"resized={counts['allowed_fills_requiring_resize']} "
        f"unavailable={counts['exact_frozen_leg_unavailable_d_plus_1']}"
    )
    print(
        f"worst_old_breach=${risk['worst_old_policy_cap_breach']:.2f} "
        f"worst_new_breach=${risk['worst_new_policy_cap_breach']:.2f} "
        f"highest_new_risk=${risk['highest_new_policy_allowed']:.2f}"
    )
    print(f"receipt_hash={report['receipt_hash']}")
    if args.write is not None:
        print(f"receipt: {write_receipt(report, args.write)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
