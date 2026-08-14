#!/usr/bin/env python3
"""Offline audit of the local short-positioning store.

Reads local artifacts only. Never repairs data and never reaches a network.

    uv run python tools/short_positioning_audit.py \\
      --root .cache/short_positioning --provider finra \\
      --dataset consolidated-short-interest \\
      --through-publication-date 2026-08-11 --strict

Exit codes: 0 = PASS or documented warning, 2 = BLOCK.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse  # noqa: E402
from datetime import date, datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

from data.short_positioning.audit import (  # noqa: E402
    BLOCK,
    WARN,
    audit_normalized_partition,
    audit_provider_conflicts,
    audit_raw_partition,
    render_short_positioning_audit,
    write_short_positioning_audit_receipt,
)
from data.short_positioning.normalize import NORMALIZED_FILE_GLOB  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="short_positioning_audit",
        description="Audit local short-positioning artifacts offline.",
    )
    parser.add_argument("--root", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--through-publication-date", required=True)
    parser.add_argument("--asof", default=None)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--receipt", default=None)
    return parser


def _publication_dates(root: Path, provider: str, dataset: str, through: date) -> list[date]:
    base = root / "normalized" / f"provider={provider}" / f"dataset={dataset}"
    dates: list[date] = []
    if base.exists():
        for partition in sorted(base.glob(f"publication_date=*/{NORMALIZED_FILE_GLOB}")):
            try:
                published = date.fromisoformat(partition.parent.name.split("=", 1)[1])
            except ValueError:
                continue
            if published <= through:
                dates.append(published)
    return dates or [through]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code not in (0, None) else 0

    try:
        through = date.fromisoformat(args.through_publication_date)
        asof = datetime.fromisoformat(args.asof) if args.asof else datetime.now(timezone.utc)
    except ValueError as exc:
        print(f"INPUT error: {exc}", file=sys.stderr)
        return 2
    if asof.tzinfo is None:
        print("INPUT error: --asof must carry a timezone offset", file=sys.stderr)
        return 2

    root = Path(args.root)
    checks = []
    for published in _publication_dates(root, args.provider, args.dataset, through):
        checks.append(
            audit_raw_partition(
                root, provider=args.provider, dataset=args.dataset, publication_date=published
            )
        )
        checks.append(
            audit_normalized_partition(
                root,
                provider=args.provider,
                dataset=args.dataset,
                publication_date=published,
                asof=asof,
            )
        )
    checks.append(
        audit_provider_conflicts(root, dataset=args.dataset, providers=(args.provider,), asof=asof)
    )

    report = {"root": str(root), "asof": asof.isoformat(), "checks": checks}
    print(render_short_positioning_audit(report))

    if args.receipt:
        write_short_positioning_audit_receipt(report, Path(args.receipt))

    statuses = {check["status"] for check in checks}
    if BLOCK in statuses:
        return 2
    if args.strict and WARN in statuses:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
