"""H7 forward-roadmap Stage 2 -- whole-universe daily data gate (BUILD-ONLY).

A dated go/no-go over the official 15-name H7 universe: is a complete,
exact-session data set present locally for a decision, BEFORE any watcher
output is read? GO requires EVERY name to have both a split-adjusted close
AND an EOD option chain for the EXACT evaluation session (the last completed
XNYS session strictly before the requested date), each structurally clean.
Anything else -- a missing file, a stale snapshot, a schema gap, an
audit BLOCK -- is a fail-closed NO_GO for the whole universe.

READ-ONLY w.r.t. every market-data store. This module reads cached parquet
DIRECTLY and never fetches: it imports no ThetaData client and calls no
fetch/topup/store path. On a missing evaluation-session file it reports the
gap; it NEVER back-fills, never treats a newer stale snapshot as the
session, and never reads the requested date's own EOD as if complete. It
writes only its deterministic JSON result artifact and immutable receipt.

Run (BUILD-ONLY; live result today is an honest whole-universe NO_GO):
    uv run python -m options_researcher.h7_data_gate [--as-of YYYY-MM-DD]

Exit codes: 0 whole-universe GO, 1 honest data NO_GO, 2 invalid invocation
or unreadable store. Operator order: source health -> THIS gate -> watcher;
never run the watcher when either preceding command is non-zero.

Stage 2 is BUILT but NOT operationally authorized; the forward window,
paid pulls, activation, and Stages 3-8 remain separate owner decisions.
"""

from __future__ import annotations

import glob
import json
import os
import re
from datetime import date
from pathlib import Path

import pandas as pd

from data.recent_topup import audit_chain
from data.thetadata_adapter import CHAIN_COLUMNS, NUMERIC_CHAIN_COLUMNS
from data.underlying_closes import adjusted_from_raw
from options_researcher.h7_scope import scope_identity, scope_symbols
from options_researcher.h7_watch import evaluation_session
from research.hashing import config_hash, diagnostic_source_hash
from research.receipts import input_files, load_receipt, make_receipt, write_immutable_receipt

SCHEMA_VERSION = 2
DEFAULT_CLOSE_DIR = Path(".cache/underlying")
DEFAULT_CHAIN_DIR = Path(".cache/chains")
DEFAULT_REPORTS_DIR = Path("reports/h7_data_gate")

# Reason codes (stable, machine-readable).
CLOSE_FILE_MISSING = "CLOSE_FILE_MISSING"
CLOSE_SESSION_MISSING = "CLOSE_SESSION_MISSING"
CLOSE_STALE = "CLOSE_STALE"
CLOSE_NONFINITE = "CLOSE_NONFINITE"
CLOSE_DUPLICATE_DATE = "CLOSE_DUPLICATE_DATE"
CHAIN_SESSION_MISSING = "CHAIN_SESSION_MISSING"
CHAIN_STALE = "CHAIN_STALE"
CHAIN_EMPTY = "CHAIN_EMPTY"
CHAIN_SCHEMA_MISSING = "CHAIN_SCHEMA_MISSING"
CHAIN_NONFINITE = "CHAIN_NONFINITE"
CHAIN_DUPLICATE_CONTRACT = "CHAIN_DUPLICATE_CONTRACT"
CHAIN_NEGATIVE_LIQUIDITY_FIELD = "CHAIN_NEGATIVE_LIQUIDITY_FIELD"
CHAIN_CROSSED_MARKET = "CHAIN_CROSSED_MARKET"
CHAIN_AUDIT_BLOCK = "CHAIN_AUDIT_BLOCK"
EXACT_SESSION_GO = "EXACT_SESSION_GO"


class GateStoreError(RuntimeError):
    """A file that EXISTS could not be read/parsed. Distinct from an absent
    file (an honest NO_GO): an unreadable store fails the invocation (exit 2),
    never a success-shaped artifact."""


def _read_parquet(path: Path) -> pd.DataFrame:
    """The ONE parquet read seam (patchable in tests). Reads only; never
    fetches. A present-but-unreadable file becomes GateStoreError."""
    try:
        return pd.read_parquet(path)
    except GateStoreError:
        raise
    except Exception as exc:  # corrupt/locked/oversized -> fail the invocation
        raise GateStoreError(f"unreadable store {path}: "
                             f"{type(exc).__name__}: {exc}") from exc


def _nonfinite(values: pd.Series) -> int:
    """Count non-finite entries (NaN or +/-inf) in a numeric-coerced series."""
    v = pd.to_numeric(values, errors="coerce")
    return int((~v.apply(lambda x: x == x and x not in (
        float("inf"), float("-inf")))).sum())


def _evaluate_close(symbol: str, eval_iso: str, close_dir: Path) -> dict:
    path = close_dir / f"{symbol}.parquet"
    rec: dict = {"path": str(path), "file_exists": path.exists(),
                 "sha256": None,
                 "session_row_exists": False,
                 "latest_date_at_or_before_session": None,
                 "nonfinite_count": None, "duplicate_date_count": None}
    codes: list[str] = []
    if not path.exists():
        return rec, [CLOSE_FILE_MISSING]
    from research.hashing import sha256_file
    rec["sha256"] = sha256_file(path)
    df = _read_parquet(path)
    # A present-but-malformed store (readable parquet, wrong shape) is not an
    # honest data NO_GO -- it is a store-integrity failure. Fail the whole
    # invocation (exit 2) rather than crash on column access. The spec lists
    # CHAIN_SCHEMA_MISSING as a per-symbol NO_GO code but no closes analogue,
    # so a closes store lacking date/close is treated as unreadable.
    if not {"date", "close"}.issubset(df.columns):
        raise GateStoreError(
            f"closes store {path} missing required date/close columns; "
            f"got {list(df.columns)}")
    raw = df.copy()
    raw["date"] = raw["date"].astype(str)
    # point-in-time: never look at rows after the evaluation session
    at_or_before = raw[raw["date"] <= eval_iso]
    rec["duplicate_date_count"] = int(at_or_before["date"].duplicated().sum())
    if at_or_before.empty:
        rec["latest_date_at_or_before_session"] = None
        return rec, [CLOSE_SESSION_MISSING]
    series = pd.to_numeric(
        at_or_before.set_index("date")["close"].sort_index(), errors="coerce")
    adjusted = adjusted_from_raw(series, symbol)
    latest = str(adjusted.index[-1])
    rec["latest_date_at_or_before_session"] = latest
    rec["nonfinite_count"] = _nonfinite(pd.Series(list(adjusted.values)))
    rec["session_row_exists"] = eval_iso in set(adjusted.index)
    if not rec["session_row_exists"]:
        # unreachable-else eliminated: at_or_before is non-empty and its max
        # is < eval_iso here (== eval_iso would set session_row_exists).
        codes.append(CLOSE_STALE)
    if rec["nonfinite_count"]:
        codes.append(CLOSE_NONFINITE)
    if rec["duplicate_date_count"]:
        codes.append(CLOSE_DUPLICATE_DATE)
    return rec, codes


def _chain_days(symbol: str, chain_dir: Path) -> list[str]:
    pat = str(chain_dir / f"{symbol}_*.parquet")
    days = []
    for p in glob.glob(pat):
        m = re.search(r"_(\d{4}-\d{2}-\d{2})\.parquet$", os.path.basename(p))
        if m:
            days.append(m.group(1))
    return sorted(days)


def _validate_chain_store_fields(df: pd.DataFrame, path: Path) -> None:
    """Reject readable parquet whose stored dtypes/domain values cannot be
    consumed safely. Missing columns remain a reason-coded NO_GO; malformed
    columns that are present make the store unreadable (exit 2)."""
    for col in NUMERIC_CHAIN_COLUMNS:
        if col not in df.columns:
            continue
        dtype = df[col].dtype
        if (pd.api.types.is_bool_dtype(dtype)
                or pd.api.types.is_complex_dtype(dtype)
                or not pd.api.types.is_numeric_dtype(dtype)):
            raise GateStoreError(
                f"chain store {path} column {col!r} is not a real numeric "
                f"dtype ({dtype}); refusing")

    if "right" in df.columns:
        if any(not isinstance(value, str) or value not in {"P", "C"}
               for value in df["right"].tolist()):
            raise GateStoreError(
                f"chain store {path} has invalid right values; refusing")

    if "expiration" in df.columns:
        try:
            expirations = [date.fromisoformat(value) for value in
                           df["expiration"].tolist()]
        except (TypeError, ValueError) as exc:
            raise GateStoreError(
                f"chain store {path} has a non-ISO expiration; refusing") from exc
        if any(value.isoformat() != raw for value, raw in
               zip(expirations, df["expiration"].tolist())):
            raise GateStoreError(
                f"chain store {path} has a non-canonical expiration; refusing")


def _evaluate_chain(symbol: str, eval_iso: str, chain_dir: Path) -> dict:
    expected = chain_dir / f"{symbol}_{eval_iso}.parquet"
    days = _chain_days(symbol, chain_dir)
    at_or_before = [d for d in days if d <= eval_iso]
    rec: dict = {
        "expected_path": str(expected), "file_exists": expected.exists(),
        "sha256": None,
        "newest_date_at_or_before_session":
            (at_or_before[-1] if at_or_before else None),
        "row_count": None, "columns": None, "missing_required_columns": None,
        "null_by_numeric_column": None, "nonfinite_by_numeric_column": None,
        "duplicate_contract_count": None, "negative_bid_count": None,
        "negative_ask_count": None, "negative_open_interest_count": None,
        "crossed_market_count": None, "audit": None,
    }
    codes: list[str] = []
    if not expected.exists():
        codes.append(CHAIN_SESSION_MISSING)
        if at_or_before and at_or_before[-1] < eval_iso:
            codes.append(CHAIN_STALE)
        return rec, codes

    from research.hashing import sha256_file
    rec["sha256"] = sha256_file(expected)
    df = _read_parquet(expected)   # exact-session file ONLY; never a fallback
    rec["row_count"] = int(len(df))
    rec["columns"] = list(df.columns)
    missing = [c for c in CHAIN_COLUMNS if c not in df.columns]
    rec["missing_required_columns"] = missing
    if missing:
        codes.append(CHAIN_SCHEMA_MISSING)
    # Store-integrity guard, symmetric with the closes date/close guard: a
    # present column with a malformed stored dtype/domain is an integrity
    # failure (exit 2) regardless of row count. Run it BEFORE the empty-chain
    # short-circuit so a zero-row store with bad dtypes still fails closed,
    # never into a spurious CHAIN_EMPTY NO_GO (exit 1). A valid empty store has
    # clean dtypes and passes here, then falls through to CHAIN_EMPTY below.
    _validate_chain_store_fields(df, expected)
    # A zero-row chain is not a chain: it has no contract to select, so it must
    # never audit-PASS into a spurious GO. Fail closed on the absent chain and
    # skip the row-wise checks below (all vacuous on 0 rows).
    if rec["row_count"] == 0:
        codes.append(CHAIN_EMPTY)
        return rec, codes

    nulls, nonfinite = {}, {}
    for col in NUMERIC_CHAIN_COLUMNS:
        if col in df.columns:
            nulls[col] = int(df[col].isna().sum())
            nonfinite[col] = _nonfinite(df[col])
    rec["null_by_numeric_column"] = nulls
    rec["nonfinite_by_numeric_column"] = nonfinite
    if sum(nonfinite.values()):
        codes.append(CHAIN_NONFINITE)

    if not missing:
        dup = df.duplicated(subset=["expiration", "strike", "right"],
                            keep=False)
        rec["duplicate_contract_count"] = int(dup.sum())
        if rec["duplicate_contract_count"]:
            codes.append(CHAIN_DUPLICATE_CONTRACT)
        rec["negative_bid_count"] = int((df["bid"] < 0).sum())
        rec["negative_ask_count"] = int((df["ask"] < 0).sum())
        rec["negative_open_interest_count"] = int((df["open_interest"] < 0).sum())
        if (rec["negative_bid_count"] or rec["negative_ask_count"]
                or rec["negative_open_interest_count"]):
            codes.append(CHAIN_NEGATIVE_LIQUIDITY_FIELD)
        rec["crossed_market_count"] = int((df["bid"] > df["ask"]).sum())
        if rec["crossed_market_count"]:
            codes.append(CHAIN_CROSSED_MARKET)
        # reuse the repo's liquidity/greek audit -- no thresholds re-invented
        if not sum(nonfinite.values()):
            a = audit_chain(df)
            rec["audit"] = {"verdict": a["verdict"], "block": a["block"],
                            "warn": a["warn"], "rows": a["rows"],
                            "selectable": a["selectable"]}
            if a["verdict"] == "BLOCK":
                codes.append(CHAIN_AUDIT_BLOCK)
    return rec, codes


def _resolve_scope(scope: dict | None, symbols) -> tuple[list[str], dict]:
    if scope is not None and symbols is not None:
        raise ValueError("provide either scope or symbols, not both")
    if scope is None:
        names = list(scope_symbols() if symbols is None else symbols)
        identity = scope_identity(names)
        if symbols is None:
            identity = scope_identity()
        return list(identity["symbols"]), identity
    required = {"scope_id", "scope_version", "symbols", "scope_hash"}
    if not required.issubset(scope):
        raise ValueError(f"scope missing fields: {sorted(required - set(scope))}")
    identity = scope_identity(scope["symbols"])
    if (identity["scope_id"], identity["scope_version"],
            identity["scope_hash"]) != (
                scope["scope_id"], scope["scope_version"], scope["scope_hash"]):
        raise ValueError("scope identity/hash does not match its symbols")
    return list(identity["symbols"]), identity


def evaluate(requested_run_date: date, *, close_dir: Path = DEFAULT_CLOSE_DIR,
             chain_dir: Path = DEFAULT_CHAIN_DIR, scope: dict | None = None,
             symbols: list[str] | tuple[str, ...] | None = None) -> dict:
    """Pure whole-universe evaluation. Filesystem inputs are injected via
    close_dir/chain_dir so tests drive fixture caches. Raises GateStoreError
    if a present file is unreadable (the caller maps that to exit 2)."""
    from data.cache_runner import session_close_utc

    close_dir, chain_dir = Path(close_dir), Path(chain_dir)
    eval_session = evaluation_session(requested_run_date)
    eval_iso = eval_session.isoformat()
    cutoff = session_close_utc(eval_iso)
    names, scope_info = _resolve_scope(scope, symbols)

    records: dict[str, dict] = {}
    for sym in sorted(names):
        close_rec, close_codes = _evaluate_close(sym, eval_iso, close_dir)
        chain_rec, chain_codes = _evaluate_chain(sym, eval_iso, chain_dir)
        codes = sorted(set(close_codes) | set(chain_codes))
        verdict = "GO" if not codes else "NO_GO"
        records[sym] = {
            "symbol": sym,
            "requested_run_date": requested_run_date.isoformat(),
            "evaluation_session": eval_iso,
            "causal_cutoff_utc": cutoff.isoformat(),
            "verdict": verdict,
            "reason_codes": codes if codes else [EXACT_SESSION_GO],
            "close": close_rec,
            "chain": chain_rec,
        }
    go = [s for s, r in records.items() if r["verdict"] == "GO"]
    return {
        "schema_version": SCHEMA_VERSION,
        "scope": scope_info,
        "requested_run_date": requested_run_date.isoformat(),
        "evaluation_session": eval_iso,
        "causal_cutoff_utc": cutoff.isoformat(),
        "universe": sorted(names),
        "go_count": len(go),
        "no_go_count": len(names) - len(go),
        "whole_universe_verdict": "GO" if len(go) == len(names) else "NO_GO",
        "symbols": records,
    }


def build_receipt(result: dict, *, source_health_receipt: dict,
                  source_health_receipt_path: Path) -> dict:
    """Bind the gate result to the current code/config and source receipt.

    The source-health link is MANDATORY. A gate receipt written without it is
    immutable and permanently revokes that session's real-entry authority --
    ``h7_session.open_real_session`` refuses an unlinked chain -- so an
    unlinked receipt must never reach disk in the first place.
    """
    if source_health_receipt is None or source_health_receipt_path is None:
        raise ValueError(
            "data gate requires a linked source_health receipt; refusing to "
            "write an unlinked receipt (it would be immutable and would "
            "revoke this session's entry authority)")
    if source_health_receipt.get("receipt_type") != "source_health":
        raise ValueError("data gate requires a source_health receipt")
    if (source_health_receipt.get("evaluation_session")
            != result["evaluation_session"]):
        raise ValueError("source-health receipt session does not match gate")
    if source_health_receipt.get("scope", {}).get("scope_hash") != \
            result["scope"]["scope_hash"]:
        raise ValueError("source-health receipt scope does not match gate")
    source_receipt_hash = source_health_receipt.get("receipt_hash")
    payload = {
        "evaluation_session": result["evaluation_session"],
        "requested_run_date": result["requested_run_date"],
        "scope": result["scope"],
        "whole_universe_verdict": result["whole_universe_verdict"],
        "go_count": result["go_count"],
        "no_go_count": result["no_go_count"],
        "symbols": result["symbols"],
        "input_files": dict(sorted(input_files({
            f"{kind}:{symbol}": Path(
                result["symbols"][symbol][section][path_key])
            for symbol in result["universe"]
            for kind, section, path_key in (
                ("close", "close", "path"),
                ("chain", "chain", "expected_path"),
            )
        }).items())),
        "source_health_receipt_hash": source_receipt_hash,
        "source_health_receipt_path": str(source_health_receipt_path),
        "config_hash": config_hash(),
        "source_hash": diagnostic_source_hash(),
    }
    return make_receipt("data_gate", payload)


def to_artifact(result: dict) -> str:
    """Deterministic serialization: sorted keys, LF, trailing newline, no
    wall-clock field. Identical inputs -> byte-identical output."""
    import json
    return json.dumps(result, sort_keys=True, indent=1,
                      ensure_ascii=True, allow_nan=False) + "\n"


def write_artifact(result: dict, *,
                   reports_dir: Path = DEFAULT_REPORTS_DIR) -> Path:
    """Atomically create one gate artifact; identical replay is allowed."""
    reports_dir = Path(reports_dir)
    scoped_dir = reports_dir / result["scope"]["scope_id"]
    scoped_dir.mkdir(parents=True, exist_ok=True)
    path = scoped_dir / f"{result['evaluation_session']}.json"
    payload = to_artifact(result)
    if path.exists():
        if path.read_text() != payload:
            raise FileExistsError(f"refusing to overwrite data-gate artifact: {path}")
        return path
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("x") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    dir_fd = os.open(scoped_dir, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
    return path


def _print_summary(result: dict, artifact: Path) -> None:
    print(f"H7 DATA GATE requested={result['requested_run_date']} "
          f"session={result['evaluation_session']} "
          f"cutoff={result['causal_cutoff_utc']} "
          f"(read-only; BUILD-ONLY, not operationally authorized)")
    for sym in result["universe"]:
        r = result["symbols"][sym]
        v = "GO" if r["verdict"] == "GO" else "NO_GO"
        print(f"{sym:>5}: {v:>5} [{','.join(r['reason_codes'])}]")
    print(f"whole-universe {result['whole_universe_verdict']}: "
          f"{result['go_count']}/{len(result['universe'])} GO; "
          f"artifact {artifact}")


def main(argv: list[str] | None = None) -> int:
    import argparse
    from datetime import datetime
    from zoneinfo import ZoneInfo

    parser = argparse.ArgumentParser(
        description="H7 Stage 2 whole-universe daily data gate (read-only; "
                    "exit 0 GO, 1 NO_GO, 2 invalid/unreadable)")
    parser.add_argument("--as-of", help="requested run date YYYY-MM-DD "
                                        "(default today America/New_York)")
    parser.add_argument("--close-dir", default=str(DEFAULT_CLOSE_DIR))
    parser.add_argument("--chain-dir", default=str(DEFAULT_CHAIN_DIR))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--scope", default=None,
                        help="scope JSON file; defaults to official H7 scope")
    parser.add_argument("--source-health-receipt", default=None,
                        help="REQUIRED immutable source-health receipt for the "
                             "same evaluation session; the gate refuses to "
                             "write an unlinked receipt")
    parser.add_argument("--write-receipt", default=None,
                        help="immutable data-gate receipt path")
    args = parser.parse_args(argv)

    ny_today = datetime.now(ZoneInfo("America/New_York")).date()
    try:
        requested = (date.fromisoformat(args.as_of) if args.as_of
                     else ny_today)
    except ValueError:
        print(f"--as-of {args.as_of!r} is not YYYY-MM-DD; refusing.")
        return 2
    if requested > ny_today:
        print(f"--as-of {requested} is in the future; refusing.")
        return 2
    if not args.source_health_receipt:
        print("H7 DATA GATE ERROR -- --source-health-receipt is required "
              "(fail closed, no artifact written). A gate receipt with no "
              "source-health link is immutable and permanently revokes this "
              "session's real-entry authority. Run "
              "`python -m options_researcher.h7_source_health` first and pass "
              "the receipt path it prints, or use tools/daily_ritual.sh, "
              "which chains them for you.")
        return 2

    try:
        scope = (json.loads(Path(args.scope).read_text())
                 if args.scope else None)
        source_receipt = (load_receipt(Path(args.source_health_receipt),
                                       expected_type="source_health")
                          if args.source_health_receipt else None)
        result = evaluate(requested, close_dir=Path(args.close_dir),
                          chain_dir=Path(args.chain_dir), scope=scope)
    except GateStoreError as exc:
        print(f"H7 DATA GATE ERROR -- unreadable store (fail closed, no "
              f"artifact written): {exc}")
        return 2
    except (ValueError, OSError) as exc:
        print(f"H7 DATA GATE ERROR -- invalid invocation: "
              f"{type(exc).__name__}: {exc}")
        return 2

    try:
        receipt = build_receipt(
            result, source_health_receipt=source_receipt,
            source_health_receipt_path=(
                Path(args.source_health_receipt)
                if args.source_health_receipt else None))
        artifact = write_artifact(result, reports_dir=Path(args.reports_dir))
        receipt_path = (Path(args.write_receipt) if args.write_receipt else
                        Path(args.reports_dir) / result["scope"]["scope_id"] /
                        "receipts" /
                        f"{result['evaluation_session']}.json")
        write_immutable_receipt(receipt, receipt_path)
    except (OSError, ValueError) as exc:
        print(f"H7 DATA GATE ERROR -- cannot write artifact: "
              f"{type(exc).__name__}: {exc}")
        return 2
    _print_summary(result, artifact)
    print(f"immutable receipt {receipt_path}")
    return 0 if result["whole_universe_verdict"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
