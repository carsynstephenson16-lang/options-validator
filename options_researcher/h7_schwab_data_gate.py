"""H7 row-integrity gate for byte-bound Schwab preclose chain packages."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from data.cache_schema import CacheAuditReceiptError
from options_researcher import h7_data_gate
from options_researcher.h7_scope import scope_identity
from research.hashing import sha256_file
from tools.schwab_chain_manifest import SchwabChainManifestError, verify_session

EVIDENCE_MODE = "REAL-H7-SCHWAB-PRECLOSE-AUDIT"
SCHWAB_PACKAGE_INVALID = "SCHWAB_PACKAGE_INVALID"
logger = logging.getLogger(__name__)


def validate_receipt_scope_closure(
    result: dict, expected_symbols: list[str]
) -> dict[str, str]:
    """Re-verify the complete Schwab package used by a gate result.

    Receipt construction calls this independently of ``evaluate`` so a
    previously valid result cannot outlive manifest, capture-receipt, or
    parquet tampering.
    """
    records = result.get("symbols")
    if not isinstance(records, dict):
        raise ValueError("data-gate result lacks a verified Schwab package")

    chain_dirs: set[Path] = set()
    manifest_paths: set[Path] = set()
    receipt_paths: set[Path] = set()
    claimed_bindings: dict[str, dict] = {}
    for symbol in expected_symbols:
        record = records.get(symbol)
        if not isinstance(record, dict):
            raise ValueError("data-gate result lacks a verified Schwab package")
        chain = record.get("chain")
        if not isinstance(chain, dict):
            raise ValueError("data-gate result lacks a verified Schwab package")
        expected_path = chain.get("expected_path")
        claimed = chain.get("audit_receipt")
        if not isinstance(expected_path, str) or not isinstance(claimed, dict):
            raise ValueError("data-gate result lacks a verified Schwab package")
        manifest_path = claimed.get("manifest_path")
        receipt_path = claimed.get("receipt_path")
        if not isinstance(manifest_path, str) or not isinstance(receipt_path, str):
            raise ValueError("data-gate result lacks a verified Schwab package")
        chain_dirs.add(Path(expected_path).parent)
        manifest_paths.add(Path(manifest_path))
        receipt_paths.add(Path(receipt_path))
        claimed_bindings[symbol] = claimed

    if len(chain_dirs) != 1 or len(manifest_paths) != 1 or len(receipt_paths) != 1:
        raise ValueError("data-gate result lacks a verified Schwab package")
    chain_dir = next(iter(chain_dirs))
    manifest_path = next(iter(manifest_paths))
    receipt_path = next(iter(receipt_paths))
    try:
        package = verify_session(
            str(result.get("evaluation_session")),
            expected_symbols,
            chain_dir,
            manifest_path,
            receipt_path,
        )
    except SchwabChainManifestError as exc:
        raise ValueError("data-gate result lacks a verified Schwab package") from exc

    expected_binding = {"valid": True, **package}
    if any(
        claimed_bindings[symbol] != expected_binding for symbol in expected_symbols
    ):
        raise ValueError("data-gate result lacks a verified Schwab package")
    try:
        capture_receipt_hash = sha256_file(receipt_path)
    except OSError as exc:
        raise ValueError("data-gate result lacks a verified Schwab package") from exc
    return {
        "causal_cutoff_utc": str(result.get("causal_cutoff_utc")),
        "schwab_manifest_hash": package["manifest_hash"],
        "schwab_capture_receipt_hash": capture_receipt_hash,
    }


def _package_no_go(
    requested_run_date: date,
    *,
    close_dir: Path,
    chain_dir: Path,
    scope: dict | None,
    names: list[str],
    session: str,
    error: str,
) -> dict:
    from data.cache_runner import session_close_utc

    cutoff = session_close_utc(session).isoformat()
    scope_info = scope if scope is not None else scope_identity(names)
    records = {
        symbol: {
            "symbol": symbol,
            "requested_run_date": requested_run_date.isoformat(),
            "evaluation_session": session,
            "causal_cutoff_utc": cutoff,
            "verdict": "NO_GO",
            "reason_codes": [SCHWAB_PACKAGE_INVALID],
            "close": {"path": str(Path(close_dir) / f"{symbol}.parquet")},
            "chain": {
                "expected_path": str(Path(chain_dir) / f"{symbol}_{session}.parquet"),
                "audit_receipt": {"valid": False, "error": error},
            },
        }
        for symbol in names
    }
    return {
        "schema_version": h7_data_gate.SCHEMA_VERSION,
        "evidence_mode": EVIDENCE_MODE,
        "scope": scope_info,
        "requested_run_date": requested_run_date.isoformat(),
        "evaluation_session": session,
        "causal_cutoff_utc": cutoff,
        "universe": names,
        "go_count": 0,
        "no_go_count": len(names),
        "whole_universe_verdict": "NO_GO",
        "symbols": records,
    }


def evaluate(
    requested_run_date: date,
    *,
    close_dir: Path,
    chain_dir: Path,
    manifest_path: Path,
    receipt_path: Path,
    scope: dict | None = None,
    symbols: list[str] | tuple[str, ...] | None = None,
) -> dict:
    """Verify the complete Schwab package, then run existing H7 checks."""
    if scope is not None and symbols is not None:
        raise ValueError("provide either scope or symbols, not both")
    if scope is not None:
        names = sorted(scope.get("symbols") or [])
    elif symbols is not None:
        names = sorted(symbols)
    else:
        names = list(scope_identity()["symbols"])
        scope = scope_identity()

    session = h7_data_gate.evaluation_session(requested_run_date).isoformat()
    try:
        package = verify_session(
            session,
            names,
            Path(chain_dir),
            Path(manifest_path),
            Path(receipt_path),
        )
    except SchwabChainManifestError as exc:
        logger.exception("Schwab package verification failed: %s", exc)
        return _package_no_go(
            requested_run_date,
            close_dir=Path(close_dir),
            chain_dir=Path(chain_dir),
            scope=scope,
            names=names,
            session=session,
            error=str(exc),
        )

    def validate_binding(
        validator_chain_dir,
        chain_path,
        *,
        symbol,
        session: str,
        consumer_scope: str,
    ) -> dict:
        expected = Path(chain_dir) / f"{symbol}_{session}.parquet"
        if Path(validator_chain_dir) != Path(chain_dir):
            raise CacheAuditReceiptError("Schwab chain directory changed")
        if Path(chain_path) != expected:
            raise CacheAuditReceiptError("Schwab exact-session path changed")
        if symbol not in names or consumer_scope != "H7":
            raise CacheAuditReceiptError("Schwab package scope changed")
        return dict(package)

    return h7_data_gate.evaluate_exact_session_package(
        requested_run_date,
        close_dir=Path(close_dir),
        chain_dir=Path(chain_dir),
        scope=scope,
        symbols=symbols,
        receipt_validator=validate_binding,
        evidence_mode=EVIDENCE_MODE,
    )
