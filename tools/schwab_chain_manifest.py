"""Build and verify byte-bound Schwab exact-session chain packages offline."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from data.atomic_io import atomic_text_write
from options_researcher.intraday_capture import validate_session_tag
from research.hashing import canonical_json, sha256_file, sha256_hex

SCHEMA_VERSION = "schwab-chain-manifest/v1"
PROVIDER = "schwab"
SESSION_CHAIN_CONVENTION = "preclose_snapshot_v1"
NY_TZ = ZoneInfo("America/New_York")


class SchwabChainManifestError(RuntimeError):
    """A session package is missing, stale, partial, or byte-inconsistent."""


def _session(value: str) -> str:
    try:
        parsed = date.fromisoformat(str(value))
    except ValueError as exc:
        raise SchwabChainManifestError("session must be YYYY-MM-DD") from exc
    result = parsed.isoformat()
    if result != value:
        raise SchwabChainManifestError("session must be canonical YYYY-MM-DD")
    return result


def _symbols(values) -> list[str]:
    symbols = [str(value) for value in values]
    if (
        not symbols
        or symbols != sorted(set(symbols))
        or any(not symbol or symbol != symbol.upper() for symbol in symbols)
    ):
        raise SchwabChainManifestError(
            "symbols must be a sorted, unique, non-empty uppercase universe"
        )
    return symbols


def _load_object(path: Path, label: str) -> dict:
    try:
        value = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SchwabChainManifestError(f"{label} is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise SchwabChainManifestError(f"{label} must be a JSON object")
    return value


def _captured_at_session(value: object, session: str, session_tag: str) -> datetime:
    try:
        captured_at = datetime.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise SchwabChainManifestError(
            "receipt captured_at_et must be an ISO-8601 timestamp"
        ) from exc
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise SchwabChainManifestError("receipt captured_at_et must include an offset")
    captured_at_ny = captured_at.astimezone(NY_TZ)
    if captured_at_ny.date().isoformat() != session:
        raise SchwabChainManifestError("receipt captured_at_et session does not match")
    timing_ok, timing_reason = validate_session_tag(session_tag, captured_at_ny)
    if not timing_ok:
        raise SchwabChainManifestError(
            f"receipt captured_at_et is outside {session_tag} tolerance: {timing_reason}"
        )
    return captured_at_ny


def _manifest_hash(value: dict) -> str:
    body = {key: item for key, item in value.items() if key != "manifest_hash"}
    return sha256_hex(canonical_json(body))


def build_manifest(
    session: str,
    symbols,
    chain_dir: Path,
    *,
    convention: str = SESSION_CHAIN_CONVENTION,
    receipt_filename: str = "preclose.json",
    session_tag: str = "preclose",
) -> dict:
    """Build a deterministic manifest for the exact requested file set."""
    # These two identity values are consumed by verify_session; accepting them
    # here keeps the shared build/verify API aligned without changing manifest
    # bytes under the default pre-close identity.
    _ = receipt_filename, session_tag
    session = _session(session)
    symbols = _symbols(symbols)
    chain_dir = Path(chain_dir)
    expected_names = {f"{symbol}_{session}.parquet" for symbol in symbols}
    actual_names = {path.name for path in chain_dir.glob(f"*_{session}.parquet")}
    if actual_names != expected_names:
        raise SchwabChainManifestError(
            "exact-session file universe mismatch: "
            f"missing={sorted(expected_names - actual_names)} "
            f"extra={sorted(actual_names - expected_names)}"
        )

    files = {}
    for symbol in symbols:
        path = chain_dir / f"{symbol}_{session}.parquet"
        try:
            frame = pd.read_parquet(path)
        except (OSError, ValueError) as exc:
            raise SchwabChainManifestError(f"unreadable chain file: {path}") from exc
        if "expiration" not in frame.columns:
            raise SchwabChainManifestError(f"chain file missing expiration: {path}")
        files[symbol] = {
            "path": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "row_count": int(len(frame)),
            "expiration_count": int(frame["expiration"].nunique(dropna=True)),
        }

    value = {
        "schema_version": SCHEMA_VERSION,
        "provider": PROVIDER,
        "session": session,
        "session_chain_convention": convention,
        "symbols": symbols,
        "files": files,
    }
    return {**value, "manifest_hash": _manifest_hash(value)}


def write_manifest(value: dict, path: Path) -> Path:
    """Write once, allowing an identical retry and refusing a conflict."""
    path = Path(path)
    text = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if path.exists():
        if path.read_text() != text:
            raise SchwabChainManifestError(f"manifest conflict: {path}")
        return path
    atomic_text_write(text, path)
    return path


def verify_session(
    session: str,
    symbols,
    chain_dir: Path,
    manifest_path: Path,
    receipt_path: Path,
    *,
    convention: str = SESSION_CHAIN_CONVENTION,
    receipt_filename: str = "preclose.json",
    session_tag: str = "preclose",
    receipt_kind: str = "schwab_chain_capture/v1",
) -> dict:
    """Verify exact session, universe, bytes, expirations, and receipt binding."""
    session = _session(session)
    symbols = _symbols(symbols)
    chain_dir = Path(chain_dir)
    stored = _load_object(Path(manifest_path), "manifest")
    if stored.get("schema_version") != SCHEMA_VERSION:
        raise SchwabChainManifestError("manifest schema is not supported")
    if stored.get("provider") != PROVIDER:
        raise SchwabChainManifestError("manifest provider is not schwab")
    if stored.get("session") != session:
        raise SchwabChainManifestError("manifest session does not match request")
    if stored.get("session_chain_convention") != convention:
        raise SchwabChainManifestError("manifest convention does not match")
    if stored.get("symbols") != symbols:
        raise SchwabChainManifestError("manifest universe does not match request")
    if stored.get("manifest_hash") != _manifest_hash(stored):
        raise SchwabChainManifestError("manifest hash does not verify")

    expected_names = {f"{symbol}_{session}.parquet" for symbol in symbols}
    actual_names = {path.name for path in chain_dir.glob(f"*_{session}.parquet")}
    if actual_names != expected_names:
        raise SchwabChainManifestError(
            "exact-session file universe mismatch: "
            f"missing={sorted(expected_names - actual_names)} "
            f"extra={sorted(actual_names - expected_names)}"
        )

    receipt_path = Path(receipt_path)
    if receipt_path.name != receipt_filename:
        raise SchwabChainManifestError("receipt filename does not match")
    receipt = _load_object(receipt_path, "receipt")
    if receipt.get("receipt_kind") != receipt_kind:
        raise SchwabChainManifestError("receipt kind does not match")
    if receipt.get("session") != session:
        raise SchwabChainManifestError("receipt session does not match request")
    if receipt.get("scheduled_session_tag") != session_tag:
        raise SchwabChainManifestError("receipt scheduled session tag does not match")
    _captured_at_session(receipt.get("captured_at_et"), session, session_tag)
    if receipt.get("force") is not False:
        raise SchwabChainManifestError("receipt force must be false; require force=false")
    if receipt.get("session_chain_convention") != convention:
        raise SchwabChainManifestError("receipt convention does not match")
    if receipt.get("universe") != symbols:
        raise SchwabChainManifestError("receipt universe does not match request")
    if receipt.get("overall_status") != "ok":
        raise SchwabChainManifestError("receipt marks the package failed")
    if receipt.get("manifest_hash") != stored["manifest_hash"]:
        raise SchwabChainManifestError("receipt manifest hash does not match")

    file_records = stored.get("files")
    receipt_records = receipt.get("names")
    if not isinstance(file_records, dict) or set(file_records) != set(symbols):
        raise SchwabChainManifestError("manifest file universe does not match")
    if not isinstance(receipt_records, dict) or set(receipt_records) != set(symbols):
        raise SchwabChainManifestError("receipt name universe does not match")

    for symbol in symbols:
        path = chain_dir / f"{symbol}_{session}.parquet"
        if not path.is_file():
            raise SchwabChainManifestError(f"missing exact-session file: {path}")
        record = file_records[symbol]
        receipt_record = receipt_records[symbol]
        if not isinstance(record, dict) or not isinstance(receipt_record, dict):
            raise SchwabChainManifestError(f"invalid record for {symbol}")
        if record.get("path") != path.name:
            raise SchwabChainManifestError(f"manifest path mismatch for {symbol}")
        actual_size = path.stat().st_size
        actual_hash = sha256_file(path)
        if record.get("size_bytes") != actual_size:
            raise SchwabChainManifestError(f"size mismatch for {symbol}")
        if record.get("sha256") != actual_hash:
            raise SchwabChainManifestError(f"hash mismatch for {symbol}")
        try:
            frame = pd.read_parquet(path)
        except (OSError, ValueError) as exc:
            raise SchwabChainManifestError(f"unreadable chain file for {symbol}") from exc
        if "expiration" not in frame.columns:
            raise SchwabChainManifestError(f"expiration missing for {symbol}")
        expiration_count = int(frame["expiration"].nunique(dropna=True))
        if expiration_count < 2:
            raise SchwabChainManifestError(
                f"expiration count is {expiration_count} for {symbol}; refusing"
            )
        if record.get("row_count") != len(frame):
            raise SchwabChainManifestError(f"row count mismatch for {symbol}")
        if record.get("expiration_count") != expiration_count:
            raise SchwabChainManifestError(f"expiration count mismatch for {symbol}")
        if receipt_record.get("status") != "ok":
            raise SchwabChainManifestError(f"receipt marks {symbol} failed")
        for field, actual in (
            ("sha256", actual_hash),
            ("size_bytes", actual_size),
            ("row_count", len(frame)),
            ("expiration_count", expiration_count),
        ):
            if receipt_record.get(field) != actual:
                raise SchwabChainManifestError(f"receipt {field} mismatch for {symbol}")
    return {
        "provider": PROVIDER,
        "session": session,
        "session_chain_convention": convention,
        "manifest_hash": stored["manifest_hash"],
        "manifest_path": str(manifest_path),
        "receipt_path": str(receipt_path),
    }
