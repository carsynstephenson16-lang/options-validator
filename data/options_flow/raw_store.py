"""Immutable local storage and receipts for flow captures."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import pandas as pd

from research.hashing import canonical_json, sha256_hex
from research.receipts import make_receipt, write_immutable_receipt

from .adapter import FlowFetch
from .normalize import normalize_open_interest, normalize_trade_quotes


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _immutable_parquet(frame: pd.DataFrame, path: Path) -> str:
    """Publish parquet once; identical replay is allowed, mutation is refused."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp = Path(temp_name)
    try:
        os.close(fd)
        frame.to_parquet(temp, index=False)
        payload_hash = hashlib.sha256(temp.read_bytes()).hexdigest()
        if path.exists():
            if _sha256_file(path) != payload_hash:
                raise FileExistsError(f"refusing to overwrite immutable flow file: {path}")
        else:
            try:
                os.link(temp, path)
            except FileExistsError:
                if _sha256_file(path) != payload_hash:
                    raise FileExistsError(
                        f"competing flow write differs for immutable file: {path}"
                    ) from None
        return payload_hash
    finally:
        temp.unlink(missing_ok=True)


class RawFlowStore:
    """Content-addressed symbol/session store under a caller-selected root."""

    def __init__(self, root: Path | str = ".cache/options_flow") -> None:
        self.root = Path(root)

    def session_dir(self, symbol: str, session: str) -> Path:
        return self.root / "raw" / symbol.upper() / session

    def write_fetch(self, fetch: FlowFetch) -> dict[str, object]:
        """Normalize and immutably publish one fetch plus a hash-bound receipt."""
        directory = self.session_dir(fetch.symbol, fetch.session)
        trades = normalize_trade_quotes(
            fetch.trade_quote,
            symbol=fetch.symbol,
            session=fetch.session,
            acquired_at_utc=fetch.acquired_at_utc,
            source_version=fetch.source_version,
        )
        oi = normalize_open_interest(
            fetch.open_interest,
            symbol=fetch.symbol,
            acquired_at_utc=fetch.acquired_at_utc,
            source_version=fetch.source_version,
        )
        trade_path = directory / "trade_quote.parquet"
        oi_path = directory / "open_interest.parquet"
        trade_hash = _immutable_parquet(trades, trade_path)
        oi_hash = _immutable_parquet(oi, oi_path)
        manifest = {
            "schema": "options_flow_raw_manifest_v1",
            "symbol": fetch.symbol,
            "session": fetch.session,
            "source": "ThetaData OPRA trade_quote + open_interest",
            "source_version": fetch.source_version,
            "acquisition_timestamp": fetch.acquired_at_utc,
            "requests": list(fetch.requests),
            "query": {
                "expiration": "*",
                "regular_session": ["09:30:00", "16:00:00"],
                "trade_quote_exclusive": True,
            },
            "files": {
                "trade_quote": {
                    "path": str(trade_path),
                    "rows": len(trades),
                    "sha256": trade_hash,
                },
                "open_interest": {
                    "path": str(oi_path),
                    "rows": len(oi),
                    "sha256": oi_hash,
                },
            },
        }
        manifest["manifest_hash"] = sha256_hex(canonical_json(manifest))
        manifest_path = directory / "manifest.json"
        _immutable_json(manifest, manifest_path)
        receipt = make_receipt(
            "options_flow_capture",
            {
                "schema": "options_flow_receipt_v1",
                "symbol": fetch.symbol,
                "session": fetch.session,
                "source": manifest["source"],
                "source_version": fetch.source_version,
                "acquisition_timestamp": fetch.acquired_at_utc,
                "manifest": {"path": str(manifest_path), "sha256": _sha256_file(manifest_path)},
            },
        )
        receipt_path = directory / "receipt.json"
        write_immutable_receipt(receipt, receipt_path)
        return {
            "symbol": fetch.symbol,
            "session": fetch.session,
            "manifest": str(manifest_path),
            "receipt": str(receipt_path),
            "trade_rows": len(trades),
            "oi_rows": len(oi),
            "manifest_hash": manifest["manifest_hash"],
        }


def _immutable_json(payload: dict[str, object], path: Path) -> None:
    text = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise FileExistsError(f"refusing to overwrite immutable flow manifest: {path}")
        return
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp.write_text(text, encoding="utf-8")
        os.link(temp, path)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != text:
            raise FileExistsError(f"competing flow manifest differs: {path}") from None
    finally:
        temp.unlink(missing_ok=True)
