"""Durable read-only Schwab preclose chains for a future H7 namespace.

This capture lane never places orders, writes a ledger, or writes the canonical
ThetaData cache. Its only market-data input is ``SchwabMarketData``'s existing
read-only option-chain endpoint.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from authlib.integrations.base_client.errors import OAuthError

from data.atomic_io import (
    atomic_text_write,
    publish_staged_file,
    stage_parquet_write,
)
from options_researcher.h7_scope import watch_universe
from options_researcher.intraday_capture import validate_session_tag
from options_researcher.live_quotes import in_regular_session
from options_researcher.schwab_auth_failure import (
    expired_auth_line,
    is_expired_refresh_token_error,
)
from research.hashing import config_hash, sha256_file
from tools.schwab_chain_manifest import (
    SESSION_CHAIN_CONVENTION,
    build_manifest,
    verify_session,
    write_manifest,
)

NY_TZ = "America/New_York"
CHAIN_DIR = Path(".cache/schwab_chains")
REPORTS_DIR = Path("reports/schwab_chains")
H7_CHAIN_COLUMNS = [
    "expiration",
    "strike",
    "right",
    "bid",
    "ask",
    "open_interest",
    "iv",
    "delta",
    "gamma",
    "theta",
    "vega",
]
ADAPTER_COLUMNS = [
    "expiration",
    "strike",
    "right",
    "bid",
    "ask",
    "open_interest",
    "implied_vol",
    "delta",
    "gamma",
    "theta",
    "vega",
]


class SchwabChainCaptureError(RuntimeError):
    """A symbol or immutable output failed closed."""


def _default_client():
    from data.schwab_adapter import _client

    return _client()


def _code_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _normalize(frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
    missing = [column for column in ADAPTER_COLUMNS if column not in frame.columns]
    if missing:
        raise SchwabChainCaptureError(
            f"{symbol}: full chain missing required columns entirely: {missing}"
        )
    normalized = frame.loc[:, ADAPTER_COLUMNS].rename(
        columns={"implied_vol": "iv"}
    )
    normalized = normalized.reindex(columns=H7_CHAIN_COLUMNS)
    if normalized.empty:
        raise SchwabChainCaptureError(f"{symbol}: full chain is empty")
    expiration_count = int(normalized["expiration"].nunique(dropna=True))
    if expiration_count < 2:
        raise SchwabChainCaptureError(
            f"{symbol}: full chain has {expiration_count} expiration; "
            "at least two expirations are required"
        )
    rights = set(normalized["right"].dropna().astype(str))
    if rights != {"C", "P"}:
        raise SchwabChainCaptureError(
            f"{symbol}: full chain must contain both C and P rights; got {sorted(rights)}"
        )
    return normalized


def _write_parquet_once(frame: pd.DataFrame, path: Path) -> None:
    staged = stage_parquet_write(frame, path)
    try:
        if path.exists():
            if sha256_file(staged) != sha256_file(path):
                raise SchwabChainCaptureError(
                    f"exact-session chain conflict; refusing overwrite: {path}"
                )
            staged.unlink()
            return
        publish_staged_file(staged, path)
    except BaseException:
        try:
            staged.unlink()
        except FileNotFoundError:
            pass
        raise


def _write_receipt(value: dict, path: Path) -> bool:
    text = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if path.exists():
        return path.read_text() == text
    atomic_text_write(text, path)
    return True


def capture(
    *,
    client=None,
    now_ny: datetime | None = None,
    universe: list[str] | None = None,
    chain_dir: Path = CHAIN_DIR,
    reports_dir: Path = REPORTS_DIR,
    force: bool = False,
) -> tuple[int, dict | None]:
    """Capture one official preclose package; 0 ok, 1 failed, 2 conflict."""
    if now_ny is None:
        now_ny = datetime.now(ZoneInfo(NY_TZ))
    if not in_regular_session(now_ny):
        print(
            f"schwab_chain_capture refused: {now_ny.isoformat()} ET is outside "
            "the NY regular session"
        )
        return 1, None
    timing_ok, timing_reason = validate_session_tag("preclose", now_ny, force=force)
    if not timing_ok:
        print(f"schwab_chain_capture refused: {timing_reason}")
        return 1, None

    names = sorted(universe if universe is not None else watch_universe())
    if not names or len(names) != len(set(names)) or any(name != name.upper() for name in names):
        raise ValueError("capture universe must be unique, non-empty, and uppercase")
    if client is None:
        client = _default_client()

    session = now_ny.date().isoformat()
    now_utc = now_ny.astimezone(timezone.utc)
    chain_dir = Path(chain_dir)
    session_reports = Path(reports_dir) / session
    records: dict[str, dict] = {}
    for symbol in names:
        try:
            normalized = _normalize(client.option_full_chain(symbol), symbol)
            path = chain_dir / f"{symbol}_{session}.parquet"
            _write_parquet_once(normalized, path)
            records[symbol] = {
                "status": "ok",
                "row_count": int(len(normalized)),
                "expiration_count": int(
                    normalized["expiration"].nunique(dropna=True)
                ),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
                "path": str(path),
            }
        except Exception as exc:
            if is_expired_refresh_token_error(exc):
                raise
            records[symbol] = {
                "status": "failed",
                "note": f"{type(exc).__name__}: {exc}",
            }

    complete = all(record["status"] == "ok" for record in records.values())
    manifest_hash = None
    manifest_path = session_reports / "manifest.json"
    if complete:
        built = build_manifest(session, names, chain_dir)
        write_manifest(built, manifest_path)
        manifest_hash = built["manifest_hash"]

    receipt = {
        "receipt_kind": "schwab_chain_capture/v1",
        "session": session,
        "session_chain_convention": SESSION_CHAIN_CONVENTION,
        "captured_at_et": now_ny.isoformat(),
        "captured_at_utc": now_utc.isoformat(),
        "scheduled_session_tag": "preclose",
        "timing_validation": timing_reason,
        "force": bool(force),
        "provider": getattr(client, "provider_name", "schwab"),
        "provider_version": getattr(client, "provider_version", "unknown"),
        "universe": names,
        "overall_status": "ok" if complete else "failed",
        "names": records,
        "manifest_path": str(manifest_path) if complete else None,
        "manifest_hash": manifest_hash,
        "config_hash": config_hash(),
        "code_sha": _code_sha(),
    }
    receipt_path = session_reports / "preclose.json"
    if not _write_receipt(receipt, receipt_path):
        print(f"schwab_chain_capture receipt CONFLICT: {receipt_path}")
        return 2, receipt
    if complete:
        verify_session(session, names, chain_dir, manifest_path, receipt_path)
        print(f"schwab_chain_capture complete: {len(names)}/{len(names)} {receipt_path}")
        return 0, receipt
    failed = [symbol for symbol, record in records.items() if record["status"] != "ok"]
    print(f"schwab_chain_capture failed: {failed}; receipt={receipt_path}")
    return 1, receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only full Schwab preclose chain capture; never trades."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="bypass only the preclose timing tolerance; regular session still required",
    )
    args = parser.parse_args(argv)
    try:
        exit_code, _ = capture(force=args.force)
    except OAuthError as exc:
        if not is_expired_refresh_token_error(exc):
            raise
        print(expired_auth_line("schwab_chain_capture"))
        return 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
