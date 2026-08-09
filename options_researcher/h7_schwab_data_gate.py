"""H7 row-integrity gate for byte-bound Schwab preclose chain packages."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from data.cache_schema import CacheAuditReceiptError
from options_researcher import h7_data_gate
from options_researcher.h7_scope import scope_identity
from tools.schwab_chain_manifest import verify_session

EVIDENCE_MODE = "REAL-H7-SCHWAB-PRECLOSE-AUDIT"


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
    package = verify_session(
        session,
        names,
        Path(chain_dir),
        Path(manifest_path),
        Path(receipt_path),
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
