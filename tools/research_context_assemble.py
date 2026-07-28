"""Produce and verify fail-closed attractiveness research artifacts.

The deterministic board owns candidate identity. The daily ritual owns data
freshness and feature production. This tool only researches and annotates a
successfully completed, exact ritual session.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from data.atomic_io import atomic_text_write
from options_researcher.attractiveness_research_v2 import (
    NEW_YORK,
    ResearchArtifactError,
    UpstreamBlocked,
    check_dashboard_html,
    finalize_bundle,
    load_successful_ritual,
    publish_bundle,
    verify_bundle,
)
from tools.research_refresh_guard import GuardError, record_outcome


def _live_board() -> tuple[dict, str, list[str], list[str]]:
    from options_researcher.attractiveness_dashboard import (
        assemble,
        pinned_picks,
        select_qm_top_picks,
        select_top_picks,
    )
    from options_researcher.qm_dashboard import load_qm_context

    data = assemble()
    as_of = data.get("data_as_of")
    if not isinstance(as_of, str) or not as_of:
        raise ResearchArtifactError("no data_as_of on the assembled board")
    qm = load_qm_context(as_of)
    candidate_ids: list[str] = []
    for pick in select_top_picks(data, include_csp_watch=True):
        candidate_ids.append(pick["card"]["top3_snapshot"]["candidate_id"])
    for pick in select_qm_top_picks(data, qm, include_csp_watch=True):
        candidate_id = pick["card"]["top3_snapshot"]["candidate_id"]
        if candidate_id not in candidate_ids:
            candidate_ids.append(candidate_id)
    pinned_symbols = [pick["symbol"] for pick in pinned_picks(data)]
    return data, as_of, candidate_ids, pinned_symbols


def _ritual_root(value: str | None) -> Path:
    resolved = value or os.environ.get("RESEARCH_RITUAL_ROOT")
    if not resolved:
        raise UpstreamBlocked(
            "RESEARCH_RITUAL_ROOT is required; refusing to guess the authoritative ritual checkout"
        )
    return Path(resolved).resolve()


def _run_date(value: str | None) -> str:
    return value or os.environ.get("RESEARCH_RUN_DATE") or datetime.now(NEW_YORK).date().isoformat()


def _started_at(value: str | None) -> datetime:
    raw = value or os.environ.get("RESEARCH_STARTED_AT")
    if not raw:
        raise ResearchArtifactError(
            "RESEARCH_STARTED_AT or --started-at is required for run lineage"
        )
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise ResearchArtifactError("research start timestamp is invalid") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ResearchArtifactError("research start timestamp must be timezone-aware")
    return parsed


def _attempt_id(value: str | None) -> str:
    resolved = value or os.environ.get("RESEARCH_REFRESH_ATTEMPT_ID")
    if (
        not resolved
        or any(character.isspace() for character in resolved)
    ):
        raise ResearchArtifactError(
            "RESEARCH_REFRESH_ATTEMPT_ID or --attempt-id is required"
        )
    return resolved


def reconcile_final_attempt(
    manifest: dict[str, object],
    *,
    guard_state_dir: Path,
    now_et: datetime | None = None,
) -> str:
    """Close the paid attempt bound to an already verified final manifest."""
    if manifest.get("publication_status") != "FINAL":
        raise ResearchArtifactError("only a final manifest can reconcile a paid attempt")
    producer_attempt_id = manifest.get("producer_attempt_id")
    if not isinstance(producer_attempt_id, str):
        raise ResearchArtifactError("final manifest lacks producer_attempt_id")
    try:
        return record_outcome(
            guard_state_dir.expanduser().resolve(),
            attempt_id=producer_attempt_id,
            succeeded=True,
            published_success=True,
            now_et=now_et or datetime.now(NEW_YORK),
        )
    except GuardError as error:
        raise ResearchArtifactError(
            f"published attempt reconciliation failed: {error}"
        ) from error


def _cmd_print_ids() -> None:
    _data, as_of, candidate_ids, pinned_symbols = _live_board()
    print(
        json.dumps(
            {
                "data_as_of": as_of,
                "candidate_ids": candidate_ids,
                "pinned_symbols": pinned_symbols,
            }
        )
    )


def _cmd_preflight(
    *,
    as_of: str,
    ritual_root: str | None,
    run_date: str | None,
    receipt_out: str | None = None,
) -> None:
    binding = load_successful_ritual(
        _ritual_root(ritual_root),
        as_of=as_of,
        run_date=_run_date(run_date),
    )
    if receipt_out:
        atomic_text_write(
            json.dumps(
                {
                    "schema_version": "attractiveness_research/preflight/v1",
                    "as_of": binding.as_of,
                    "run_date": binding.run_date,
                    "ritual_run_status_sha256": binding.run_status_sha256,
                    "ritual_receipt_sha256": binding.receipt_sha256,
                    "status": "OK",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            Path(receipt_out),
        )
    print(
        "PREFLIGHT_OK "
        f"as_of={binding.as_of} run_date={binding.run_date} "
        f"ritual_run_status_sha256={binding.run_status_sha256} "
        f"ritual_receipt_sha256={binding.receipt_sha256}"
    )


def _cmd_assemble(
    *,
    inputs_dir: str,
    ritual_root: str | None,
    run_date: str | None,
    started_at: str | None,
    attempt_id: str | None,
) -> None:
    root = Path(".").resolve()
    _data, as_of, candidate_ids, pinned_symbols = _live_board()
    result = publish_bundle(
        root=root,
        as_of=as_of,
        candidate_ids=candidate_ids,
        pinned_symbols=pinned_symbols,
        inputs_dir=Path(inputs_dir),
        ritual_root=_ritual_root(ritual_root),
        run_date=_run_date(run_date),
        started_at=_started_at(started_at),
        producer_attempt_id=_attempt_id(attempt_id),
    )
    print(
        f"{result.status} run_id={result.run_id} as_of={as_of} "
        f"context_sha256={result.context_sha256} "
        f"annotations={len(candidate_ids)}/{len(candidate_ids)}"
    )


def _cmd_verify(
    *,
    ritual_root: str | None,
    receipt_out: str | None = None,
    bundle_only: bool = False,
    pending: bool = False,
    reconcile_published_attempt: bool = False,
    guard_state_dir: str | None = None,
) -> None:
    root = Path(".").resolve()
    _data, as_of, candidate_ids, pinned_symbols = _live_board()
    if pending and receipt_out:
        raise ResearchArtifactError(
            "pending bundle cannot produce a verified receipt"
        )
    if reconcile_published_attempt and pending:
        raise ResearchArtifactError(
            "pending bundle cannot reconcile a published attempt"
        )
    if reconcile_published_attempt and not guard_state_dir:
        raise ResearchArtifactError(
            "--reconcile-published-attempt requires --guard-state-dir"
        )
    manifest = verify_bundle(
        root=root,
        as_of=as_of,
        candidate_ids=candidate_ids,
        pinned_symbols=pinned_symbols,
        ritual_root=_ritual_root(ritual_root),
        pending=pending,
    )
    if reconcile_published_attempt:
        reconcile_final_attempt(
            manifest,
            guard_state_dir=Path(str(guard_state_dir)),
        )
    if not bundle_only:
        html_path = root / ".tmp/dashboard/attractiveness.html"
        if not html_path.is_file():
            raise ResearchArtifactError(f"dashboard output is missing: {html_path}")
        problems = check_dashboard_html(html_path.read_text(encoding="utf-8"))
        if problems:
            raise ResearchArtifactError("stale markers still present: " + "; ".join(problems))
    outputs = manifest["outputs"]
    assert isinstance(outputs, dict)
    output = outputs["context"]
    assert isinstance(output, dict)
    if receipt_out:
        ritual = manifest["ritual"]
        assert isinstance(ritual, dict)
        atomic_text_write(
            json.dumps(
                {
                    "schema_version": manifest["schema_version"],
                    "run_id": manifest["run_id"],
                    "producer_attempt_id": manifest["producer_attempt_id"],
                    "market_as_of_date": as_of,
                    "context_sha256": output["sha256"],
                    "ritual_run_status_sha256": ritual["run_status_sha256"],
                    "ritual_receipt_sha256": ritual["receipt_sha256"],
                    "status": "verified",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            Path(receipt_out),
        )
    print(f"VERIFY_OK run_id={manifest['run_id']} as_of={as_of} context_sha256={output['sha256']}")


def _cmd_finalize(
    *,
    ritual_root: str | None,
    receipt_out: str | None = None,
) -> None:
    root = Path(".").resolve()
    _data, as_of, candidate_ids, pinned_symbols = _live_board()
    manifest = finalize_bundle(
        root=root,
        as_of=as_of,
        candidate_ids=candidate_ids,
        pinned_symbols=pinned_symbols,
        ritual_root=_ritual_root(ritual_root),
    )
    outputs = manifest["outputs"]
    assert isinstance(outputs, dict)
    output = outputs["context"]
    assert isinstance(output, dict)
    ritual = manifest["ritual"]
    assert isinstance(ritual, dict)
    if receipt_out:
        atomic_text_write(
            json.dumps(
                {
                    "schema_version": manifest["schema_version"],
                    "run_id": manifest["run_id"],
                    "producer_attempt_id": manifest["producer_attempt_id"],
                    "market_as_of_date": as_of,
                    "context_sha256": output["sha256"],
                    "ritual_run_status_sha256": ritual["run_status_sha256"],
                    "ritual_receipt_sha256": ritual["receipt_sha256"],
                    "status": "verified",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            Path(receipt_out),
        )
    print(f"FINALIZED run_id={manifest['run_id']} as_of={as_of} context_sha256={output['sha256']}")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--print-ids", action="store_true")
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--assemble", action="store_true")
    group.add_argument("--verify", action="store_true")
    group.add_argument("--finalize", action="store_true")
    parser.add_argument("--inputs", help="directory of researcher JSON packets")
    parser.add_argument("--as-of", help="exact market session for --preflight")
    parser.add_argument("--ritual-root", help="authoritative daily-ritual checkout")
    parser.add_argument("--run-date", help="America/New_York ritual run date")
    parser.add_argument("--started-at", help="timezone-aware research start timestamp")
    parser.add_argument("--attempt-id", help="durable paid-attempt identifier")
    parser.add_argument("--receipt-out", help="atomic JSON receipt path for --verify")
    parser.add_argument(
        "--bundle-only",
        action="store_true",
        help="verify v2 lineage before rendering the dashboard",
    )
    parser.add_argument("--pending", action="store_true", help="verify pending manifest")
    parser.add_argument(
        "--reconcile-published-attempt",
        action="store_true",
        help="mark the verified final manifest's paid attempt successful",
    )
    parser.add_argument(
        "--guard-state-dir",
        help="durable guard state used with --reconcile-published-attempt",
    )
    args = parser.parse_args(argv)

    try:
        if args.print_ids:
            _cmd_print_ids()
        elif args.preflight:
            if not args.as_of:
                parser.error("--preflight requires --as-of YYYY-MM-DD")
            _cmd_preflight(
                as_of=args.as_of,
                ritual_root=args.ritual_root,
                run_date=args.run_date,
                receipt_out=args.receipt_out,
            )
        elif args.assemble:
            if not args.inputs:
                parser.error("--assemble requires --inputs DIR")
            _cmd_assemble(
                inputs_dir=args.inputs,
                ritual_root=args.ritual_root,
                run_date=args.run_date,
                started_at=args.started_at,
                attempt_id=args.attempt_id,
            )
        elif args.verify:
            _cmd_verify(
                ritual_root=args.ritual_root,
                receipt_out=args.receipt_out,
                bundle_only=args.bundle_only,
                pending=args.pending,
                reconcile_published_attempt=args.reconcile_published_attempt,
                guard_state_dir=args.guard_state_dir,
            )
        else:
            _cmd_finalize(
                ritual_root=args.ritual_root,
                receipt_out=args.receipt_out,
            )
    except UpstreamBlocked as error:
        print(f"UPSTREAM_BLOCKED: {error}")
        return 3
    except ResearchArtifactError as error:
        print(f"RESEARCH_ARTIFACT_REJECTED: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
