#!/usr/bin/env python3
"""Operator CLI for capturing issuer-level short interest to local storage.

Dry-run is the default and performs zero network calls. ``--execute`` is
explicit and operator-controlled. Credential NAMES are logged; credential
values never are. Captured data stays local and gitignored.

    uv run python tools/short_positioning_capture.py \\
      --provider finra --dataset consolidated-short-interest \\
      --publication-date 2026-08-11 --symbols MSFT,AMZN,VST,CEG \\
      --output-root .cache/short_positioning --dry-run
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse  # noqa: E402
import time as time_module  # noqa: E402
from datetime import date, datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

from data.short_positioning.models import ShortPositioningSchemaError  # noqa: E402
from data.short_positioning.normalize import write_normalized_partition  # noqa: E402
from data.short_positioning.provider import (  # noqa: E402
    LICENSE_BLOCKED_PROVIDERS,
    ArtifactIntegrityError,
    CaptureInputError,
    CaptureRequest,
    CredentialError,
    LicenseBlockedError,
    PartialCaptureError,
    ProviderUnavailableError,
)
from data.short_positioning.providers.finra import (  # noqa: E402
    FinraConsolidatedShortInterestAdapter,
)
from data.short_positioning.raw_store import verify_raw_artifact, write_raw_artifact  # noqa: E402

EXIT_CODE_MEANINGS = {
    0: "success or dry-run",
    2: "CLI input or local validation failure",
    3: "credential or authentication failure",
    4: "provider unavailable or retry exhaustion",
    5: "source schema or field-map mismatch",
    6: "atomic-write or hash failure",
    7: "partial capture rolled back",
    8: "license or entitlement blocked",
}

_ADAPTERS = {"finra": FinraConsolidatedShortInterestAdapter}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="short_positioning_capture",
        description="Capture issuer-level short interest to local, gitignored storage.",
    )
    parser.add_argument("--provider", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--publication-date", required=True)
    parser.add_argument("--symbols", required=True, help="comma-separated, uppercase")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--data-version", default="1.0")
    parser.add_argument("--request-id", default=None)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", dest="execute", action="store_false", default=False)
    mode.add_argument("--execute", dest="execute", action="store_true")
    return parser


def _request_from_args(args: argparse.Namespace) -> CaptureRequest:
    try:
        publication_date = date.fromisoformat(args.publication_date)
    except ValueError as exc:
        raise CaptureInputError(f"--publication-date {args.publication_date!r} is not ISO") from exc

    symbols = tuple(part.strip().upper() for part in args.symbols.split(",") if part.strip())
    if not symbols:
        raise CaptureInputError("--symbols requires at least one symbol")

    request_id = args.request_id or (
        f"{args.provider}-{publication_date.isoformat()}-"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    return CaptureRequest(
        provider=args.provider,
        dataset=args.dataset,
        publication_date=publication_date,
        symbols=symbols,
        output_root=Path(args.output_root),
        source_data_version=args.data_version,
        request_id=request_id,
        execute=bool(args.execute),
    )


def _adapter_for(provider: str):
    if provider in LICENSE_BLOCKED_PROVIDERS:
        raise LicenseBlockedError(
            f"provider {provider!r} is LICENSE BLOCKED in this repository; no entitlement, "
            "field dictionary, or rights confirmation exists"
        )
    if provider not in _ADAPTERS:
        raise CaptureInputError(f"unknown provider {provider!r}; available: {sorted(_ADAPTERS)}")
    return _ADAPTERS[provider]()


def _print_plan(plan) -> None:
    print("DRY RUN — no network call was made and nothing was written.")
    print(f"  provider          : {plan.request.provider}")
    print(f"  dataset           : {plan.request.dataset}")
    print(f"  publication date  : {plan.request.publication_date.isoformat()}")
    print(f"  symbols requested : {', '.join(plan.request.symbols)}")
    print(f"  url               : {plan.url}")
    print(f"  query             : {dict(plan.query)}")
    print(f"  credential names  : {', '.join(plan.credential_env_names)} (values never logged)")
    print(f"  raw partition     : {plan.raw_partition}")
    print(f"  normalized        : {plan.normalized_partition}")


def main(argv: list[str] | None = None, *, transport=None, sleep=time_module.sleep) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code not in (0, None) else int(exc.code or 0)

    try:
        adapter = _adapter_for(args.provider)
        request = _request_from_args(args)
        plan = adapter.build_plan(request)

        if plan.dry_run:
            _print_plan(plan)
            return 0

        result = adapter.fetch(plan, transport=transport, sleep=sleep)
        payload = result.payload or b""
        retrieved_at = datetime.now(timezone.utc)

        artifact = write_raw_artifact(
            payload, root=request.output_root, request=request, retrieved_at=retrieved_at
        )
        verify_raw_artifact(artifact)

        records = adapter.parse(
            payload, request=request, retrieved_at=retrieved_at, raw_sha256=artifact.sha256
        )
        partition = write_normalized_partition(records, root=request.output_root, request=request)
    except LicenseBlockedError as exc:
        print(f"LICENSE BLOCKED: {exc}", file=sys.stderr)
        return 8
    except PartialCaptureError as exc:
        print(f"PARTIAL CAPTURE, rolled back: {exc}", file=sys.stderr)
        return 7
    except ArtifactIntegrityError as exc:
        print(f"ARTIFACT INTEGRITY failure: {exc}", file=sys.stderr)
        return 6
    except ShortPositioningSchemaError as exc:
        print(f"SOURCE SCHEMA mismatch: {exc}", file=sys.stderr)
        return 5
    except ProviderUnavailableError as exc:
        print(f"PROVIDER UNAVAILABLE: {exc}", file=sys.stderr)
        return 4
    except CredentialError as exc:
        print(f"CREDENTIAL failure: {exc}", file=sys.stderr)
        return 3
    except CaptureInputError as exc:
        print(f"INPUT error: {exc}", file=sys.stderr)
        return 2

    print(f"captured {len(records)} records -> {partition}")
    print(f"raw artifact sha256 {artifact.sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
