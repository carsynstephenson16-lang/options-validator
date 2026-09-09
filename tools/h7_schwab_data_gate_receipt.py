"""Write a durable, source-linked H7 Schwab data-gate receipt.

This command reads only the flat Schwab chain cache, underlying-close cache,
and session package supplied by the operator. It writes the result into the
Schwab-specific report namespace; it never fetches or mutates market data.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from options_researcher import h7_data_gate, h7_schwab_data_gate  # noqa: E402
from options_researcher.h7_cohort import (  # noqa: E402
    CohortUnavailableError,
    load_registered_cohort,
)
from options_researcher.h7_schwab_quote_age_gate import (  # noqa: E402
    QUOTE_AGE_OVER_THRESHOLD,
    evaluate_schwab_quote_age,
)
from options_researcher.h7_scope import scope_identity  # noqa: E402
from research.hashing import canonical_json  # noqa: E402
from research.receipts import load_receipt, write_immutable_receipt  # noqa: E402

DEFAULT_CHAIN_DIR = Path(".cache/schwab_chains")
DEFAULT_REPORTS_ROOT = Path("reports/schwab_chains")
DEFAULT_CLOSE_DIR = Path(".cache/underlying")
DEFAULT_OUTPUT_ROOT = Path("reports/h7_data_gate_schwab")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, help="run date YYYY-MM-DD")
    parser.add_argument("--source-health-receipt", type=Path, required=True)
    parser.add_argument("--chain-dir", type=Path, default=DEFAULT_CHAIN_DIR)
    parser.add_argument("--reports-root", type=Path, default=DEFAULT_REPORTS_ROOT)
    parser.add_argument("--close-dir", type=Path, default=DEFAULT_CLOSE_DIR)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser


def _package_error(result: dict) -> str | None:
    """Return the evaluator's package error for its fail-closed result shape."""
    for symbol in result.get("universe", []):
        record = result.get("symbols", {}).get(symbol, {})
        binding = record.get("chain", {}).get("audit_receipt", {})
        if binding.get("valid") is False:
            return str(binding.get("error") or h7_schwab_data_gate.SCHWAB_PACKAGE_INVALID)
    return None


def _preflight_destination(path: Path, payload: str, *, label: str) -> None:
    """Refuse a conflicting pair before either immutable output is published."""
    if path.exists() and path.read_text(encoding="utf-8") != payload:
        raise FileExistsError(f"refusing to overwrite {label}: {path}")


def _print_result(result: dict, quote_age: dict, included: tuple[str, ...], artifact: Path) -> None:
    included_go = 0
    for symbol in result["universe"]:
        row = result["symbols"][symbol]
        if symbol in included and row["verdict"] == "GO":
            included_go += 1
        print(f"{symbol:>5}: {row['verdict']:>5} [{','.join(row.get('reason_codes', []))}]")
    for symbol in included:
        row = quote_age["symbols"][symbol]
        print(f"quote_age {symbol}: {row['verdict']} [{','.join(row.get('reason_codes', []))}]")
    included_verdict = "GO" if included_go == len(included) else "NO_GO"
    print(
        f"whole_universe_verdict={result['whole_universe_verdict']} "
        f"go={result['go_count']}/{len(result['universe'])}"
    )
    print(f"included_subset_verdict={included_verdict} go={included_go}/{len(included)}")
    print(f"quote_age_verdict={quote_age['whole_universe_verdict']}")
    if quote_age.get("error"):
        print(f"quote_age_error={quote_age['error']}")
    print(f"artifact {artifact}")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    today = datetime.now(ZoneInfo("America/New_York")).date()
    try:
        legacy = h7_data_gate.DEFAULT_REPORTS_DIR.resolve()
        if args.output_root.resolve().is_relative_to(legacy):
            raise ValueError("legacy data-gate output namespace is forbidden")
        requested = date.fromisoformat(args.as_of)
        if requested.isoformat() != args.as_of:
            raise ValueError("date is not canonical YYYY-MM-DD")
        if requested > today:
            raise ValueError("date is in the future")
        session = h7_data_gate.evaluation_session(requested).isoformat()
        from data.cache_runner import trading_days

        assert trading_days(session, session) == [session]

        package_dir = args.reports_root / session
        manifest_path = package_dir / "manifest.json"
        capture_receipt_path = package_dir / "preclose.json"
        missing = [
            path.name for path in (manifest_path, capture_receipt_path) if not path.is_file()
        ]
        if missing:
            print(
                f"H7 SCHWAB DATA GATE ERROR -- NO_PACKAGE_FOR_SESSION {session}: "
                f"missing {','.join(missing)}"
            )
            return 2

        source_path = Path(args.source_health_receipt)
        source_receipt = load_receipt(source_path, expected_type="source_health")
        if source_receipt.get("evaluation_session") != session:
            raise ValueError("source-health receipt session does not match gate")
        if source_receipt.get("scope") != scope_identity():
            raise ValueError("source-health receipt scope does not match gate")

        result = h7_schwab_data_gate.evaluate(
            requested,
            close_dir=args.close_dir,
            chain_dir=args.chain_dir,
            manifest_path=manifest_path,
            receipt_path=capture_receipt_path,
        )
        if (package_error := _package_error(result)) is not None:
            print(
                f"H7 SCHWAB DATA GATE ERROR -- "
                f"{h7_schwab_data_gate.SCHWAB_PACKAGE_INVALID}: {package_error}"
            )
            return 2

        receipt = h7_data_gate.build_receipt(
            result,
            source_health_receipt=source_receipt,
            source_health_receipt_path=source_path,
        )
        cohort = load_registered_cohort()
        included = tuple(cohort.included)
        if not included or not set(included).issubset(result["universe"]):
            raise ValueError("registered cohort is not closed by the H7 scope")
        quote_age = evaluate_schwab_quote_age(
            data_gate_receipt=receipt,
            included_symbols=included,
        )

        # Revalidate the full source/package/input chain before any output path
        # is created, then preflight both immutable destinations as one pair.
        h7_data_gate.validate_durable_receipt(receipt)
        scoped_root = args.output_root / result["scope"]["scope_id"]
        artifact_path = scoped_root / f"{session}.json"
        receipt_path = scoped_root / "receipts" / f"{session}.json"
        _preflight_destination(
            artifact_path,
            h7_data_gate.to_artifact(result),
            label="data-gate artifact",
        )
        _preflight_destination(
            receipt_path,
            canonical_json(receipt) + "\n",
            label="data-gate receipt",
        )
    except (
        CohortUnavailableError,
        h7_data_gate.GateStoreError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print(
            "H7 SCHWAB DATA GATE ERROR -- invalid or unverifiable input "
            f"(no output written): {type(exc).__name__}: {exc}"
        )
        return 2

    # Publication errors after the two-path preflight deliberately surface.
    # Converting a partial I/O failure into exit 2 would falsely promise that
    # nothing was written.
    artifact = h7_data_gate.write_artifact(result, reports_dir=args.output_root)
    write_immutable_receipt(receipt, receipt_path)

    _print_result(result, quote_age, included, artifact)
    print(f"immutable receipt {receipt_path}")

    included_data_go = all(result["symbols"][symbol]["verdict"] == "GO" for symbol in included)
    if not included_data_go:
        return 1
    if any(
        QUOTE_AGE_OVER_THRESHOLD in quote_age["symbols"][symbol].get("reason_codes", [])
        for symbol in included
    ):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
