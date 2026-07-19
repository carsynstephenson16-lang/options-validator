"""tools/h7_refresh_earnings.py -- owner-in-the-loop earnings refresher
(forward-roadmap Stage 1). TWO append-only acts, ONE record per invocation:

  append-raw  add one schedule/occurrence assertion or evidence-backed
              retraction to the v2 RAW store from owner-provided evidence
              (no network, no crawler);
  promote     copy one raw record into the v3 GATING store with an owner
              classification, citing it via promoted_from (the 7b-2R.2
              promotion contract). Retractions must target the gating row
              promoted from the same raw record they retract.

Source hierarchy, mechanically enforced (roadmap Stage 1 + amendment v1.4):
SEC acceptance times first, company IR/PR second, aggregator estimates only
as disclosed diagnostic `estimated` raw evidence (notes required; promotion
as quarterly-earnings gating evidence is refused); an occurred report from a
non-SEC source needs notes saying why no SEC acceptance time is cited.

Neither subcommand ever rewrites or reorders an existing row; corrections
append a NEW raw row and promote it with --supersedes <old G id>. Store locks
cover id allocation, FULL temp-copy validation (including the promotion-
citation contract), and the flushed append. Dry runs perform the same
validation but skip the append. A supersession must identify the same symbol
and event/fiscal identity, so a typo cannot tombstone another name.

Usage:
    uv run python tools/h7_refresh_earnings.py append-raw --symbol VST \
        --event-id VST-2026Q3 --fiscal-period 2026Q3 --status confirmed \
        --expected-date 2026-11-06 --timing bmo --source-type company_pr \
        --source-url https://... --known-as-of 2026-10-10T12:00:00+00:00 \
        --notes "company PR; publication time not retained"
    uv run python tools/h7_refresh_earnings.py promote --raw-id A0266 \
        --event-class actual_quarterly_earnings [--supersedes G0007] [--dry-run]
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
import fcntl
import shutil
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from options_researcher.h7_earnings import (
    _GATING_COLUMNS,
    _PROMOTION_FIELDS,  # single source of truth for the citation contract
    _RAW_COLUMNS,
    ASSERTIONS_PATH,
    EVENT_CLASSES,
    GATING_EVENT_CLASS,
    RAW_ASSERTIONS_PATH,
    load_assertions,
    load_raw_assertions,
    validate_supersession_identity,
)

_ = _PROMOTION_FIELDS  # promote() copies these verbatim via the raw record


def _next_id(rows: list[dict], prefix: str) -> int:
    ids = [int(r["record_id"][1:]) for r in rows
           if r["record_id"].startswith(prefix)]
    return max(ids, default=0) + 1


@contextmanager
def _locked_stores(*paths: Path):
    """Serialize every cooperating refresher touching these stores.

    Locking the stores themselves avoids a disposable lock-file artifact and
    keeps id allocation, full-store validation, and append in one critical
    section. Paths are sorted so a promotion (raw + gating) cannot deadlock
    an append-raw invocation.
    """
    streams = []
    try:
        for path in sorted({Path(p) for p in paths}, key=str):
            stream = path.open("r+", newline="")
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            streams.append(stream)
        yield
    finally:
        for stream in reversed(streams):
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            stream.close()


def _validated_append(path: Path, row: dict, columns: tuple, loader, *,
                      write: bool) -> None:
    """Append-only with a pre-flight: the FULL store validation runs on a
    temp COPY carrying the new row BEFORE the real file is touched."""
    fd, tmp_name = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        shutil.copy(path, tmp)
        with tmp.open("a", newline="") as f:
            csv.writer(f, lineterminator="\n").writerow(
                [row[c] for c in columns])
        loader(tmp)   # raises on ANY store violation, including the new row
        if write:
            with path.open("a", newline="") as f:
                csv.writer(f, lineterminator="\n").writerow(
                    [row[c] for c in columns])
                f.flush()
                os.fsync(f.fileno())
    finally:
        tmp.unlink(missing_ok=True)


def append_raw(*, symbol: str, event_id: str, fiscal_period: str, status: str,
               expected_date: str, occurred_date: str, timing: str,
               source_type: str, source_url: str, known_as_of: str,
               notes: str, now_utc: str, record_type: str = "assertion",
               supersedes: str = "", path: Path = RAW_ASSERTIONS_PATH,
               dry_run: bool = False) -> dict:
    """ONE raw evidence row from owner-provided evidence. The Stage 1
    source-hierarchy rules live here; everything structural (https URL,
    tz-aware stamps, monotone checked_at, status/date coherence) is
    enforced by the store loader via _validated_append. Retractions name the
    earlier raw A id they invalidate; promotion maps that target to the
    corresponding gating G id."""
    if record_type not in ("assertion", "retraction"):
        raise SystemExit(
            "REFUSED: record_type must be assertion or retraction")
    if record_type == "retraction" and not supersedes:
        raise SystemExit(
            "REFUSED: a raw retraction requires --supersedes <raw A id>")
    if source_type == "aggregator" and status != "estimated":
        raise SystemExit(
            "REFUSED: aggregator evidence may only enter as status=estimated "
            "(Stage 1 source hierarchy -- confirmed/occurred need the company "
            "or the SEC)")
    if source_type == "aggregator" and not notes.strip():
        raise SystemExit(
            "REFUSED: aggregator evidence requires --notes disclosing that "
            "no official source was found at check time")
    if status == "occurred" and source_type != "sec_filing" \
            and not notes.strip():
        raise SystemExit(
            "REFUSED: an occurred report from a non-SEC source requires "
            "--notes explaining why no SEC acceptance time is cited "
            "(SEC first -- Stage 1 source hierarchy)")
    path = Path(path)
    with _locked_stores(path):
        current = load_raw_assertions(path)
        row = {
            "record_id": f"A{_next_id(current, 'A'):04d}",
            "symbol": symbol.upper(),
            "event_id": event_id,
            "fiscal_period": fiscal_period,
            "record_type": record_type,
            "status": status,
            "expected_date": expected_date,
            "occurred_date": occurred_date,
            "session_timing": timing,
            "source_type": source_type,
            "source_url": source_url,
            "known_as_of_utc": known_as_of,
            "checked_at_utc": now_utc,
            "supersedes": supersedes,
            "notes": notes,
        }
        _validated_append(
            path, row, _RAW_COLUMNS, load_raw_assertions, write=not dry_run)
    return row


def promote(*, raw_id: str, event_class: str, supersedes: str, notes: str,
            now_utc: str, gating_path: Path = ASSERTIONS_PATH,
            raw_path: Path = RAW_ASSERTIONS_PATH,
            dry_run: bool = False) -> dict:
    """Promotion is a per-record, classified act that CITES its raw
    evidence (7b-2R.2): _PROMOTION_FIELDS are copied verbatim from the raw
    record and load_assertions re-proves the citation before the real
    append. Nothing unpromoted can gate; nothing promoted may drift from
    its evidence."""
    if event_class not in EVENT_CLASSES:
        raise SystemExit(
            f"REFUSED: event_class must be one of {EVENT_CLASSES}")
    raw_path = Path(raw_path)
    gating_path = Path(gating_path)
    with _locked_stores(raw_path, gating_path):
        raw = {r["record_id"]: r for r in load_raw_assertions(raw_path)}
        source = raw.get(raw_id)
        if source is None:
            raise SystemExit(
                f"REFUSED: {raw_id!r} is not a record in {raw_path}")
        if event_class == GATING_EVENT_CLASS and not source["fiscal_period"]:
            raise SystemExit(
                f"REFUSED: {raw_id} carries no fiscal_period; a "
                f"{GATING_EVENT_CLASS} promotion requires fiscal identity IN "
                f"THE RAW EVIDENCE -- append-raw a row carrying event identity "
                f"first, then promote that")
        if (event_class == GATING_EVENT_CLASS
                and source["source_type"] == "aggregator"):
            raise SystemExit(
                f"REFUSED: {raw_id} is aggregator evidence; H7 amendment v1.4 "
                "keeps aggregator estimates diagnostic-only and prohibits "
                "promoting them as gating evidence")
        gating = load_assertions(gating_path, raw_path)
        already = [g["record_id"] for g in gating
                   if g.get("promoted_from") == raw_id]
        if already:
            raise SystemExit(
                f"REFUSED: {raw_id} is already promoted as {already}; "
                f"corrections append a NEW raw evidence row and promote it "
                f"with --supersedes <old G id>")
        by_id = {g["record_id"]: g for g in gating}
        if supersedes and supersedes not in by_id:
            raise SystemExit(
                f"REFUSED: --supersedes {supersedes!r} names no gating record")
        if supersedes:
            try:
                validate_supersession_identity(
                    source, by_id[supersedes], ctx=f"--supersedes {supersedes}")
            except ValueError as exc:
                raise SystemExit(f"REFUSED: {exc}") from exc
        if source["record_type"] == "retraction":
            if not supersedes:
                raise SystemExit(
                    "REFUSED: promoting a raw retraction requires "
                    "--supersedes <gating G id>")
            target_raw_id = by_id[supersedes]["promoted_from"]
            if source["supersedes"] != target_raw_id:
                raise SystemExit(
                    f"REFUSED: raw retraction {raw_id} targets "
                    f"{source['supersedes']}, but gating target {supersedes} "
                    f"promotes {target_raw_id}; both layers must retract the "
                    "same evidence")
        row = {
            "record_id": f"G{_next_id(gating, 'G'):04d}",
            "symbol": source["symbol"],
            "event_id": source["event_id"],
            "fiscal_period": source["fiscal_period"],
            "record_type": source["record_type"],
            "event_class": event_class,
            "status": source["status"],
            "expected_date": (source["expected_date"].isoformat()
                              if source["expected_date"] else ""),
            "occurred_date": (source["occurred_date"].isoformat()
                              if source["occurred_date"] else ""),
            "session_timing": source["session_timing"],
            "source_type": source["source_type"],
            "source_url": source["source_url"],
            "known_as_of_utc": source["known_as_of_utc"].isoformat(),
            "checked_at_utc": now_utc,
            "supersedes": supersedes,
            "promoted_from": raw_id,
            "notes": notes,
        }
        _validated_append(
            gating_path, row, _GATING_COLUMNS,
            lambda p: load_assertions(p, raw_path), write=not dry_run)
    return row


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Owner-in-the-loop earnings refresher: append ONE raw "
                    "evidence row, or promote ONE raw record into the "
                    "gating store (append-only; validates on a temp copy "
                    "before touching the real store)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ar = sub.add_parser(
        "append-raw",
        help="append one assertion/retraction to the v2 RAW store")
    ar.add_argument("--symbol", required=True)
    ar.add_argument("--event-id", required=True)
    ar.add_argument("--fiscal-period", default="",
                    help="required in the evidence before a gating promotion")
    ar.add_argument("--record-type", default="assertion",
                    choices=["assertion", "retraction"])
    ar.add_argument("--supersedes", default="",
                    help="earlier raw A id (required for a retraction)")
    ar.add_argument("--status", required=True,
                    choices=["estimated", "confirmed", "occurred"])
    ar.add_argument("--expected-date", default="",
                    help="YYYY-MM-DD (estimated/confirmed schedules)")
    ar.add_argument("--occurred-date", default="",
                    help="YYYY-MM-DD (realized reports)")
    ar.add_argument("--timing", required=True,
                    choices=["bmo", "amc", "unknown"])
    ar.add_argument("--source-type", required=True,
                    choices=["sec_filing", "company_pr", "company_ir",
                             "exchange_notice", "aggregator"])
    ar.add_argument("--source-url", required=True,
                    help="exact https:// URL of the evidence")
    ar.add_argument("--known-as-of", required=True,
                    help="timezone-aware ISO timestamp when this became "
                         "knowable (SEC acceptanceDateTime when available)")
    ar.add_argument("--notes", default="")
    ar.add_argument("--raw-path", default=str(RAW_ASSERTIONS_PATH),
                    help="non-default store (rehearsals/tests only)")
    ar.add_argument("--dry-run", action="store_true")

    pr = sub.add_parser("promote",
                        help="promote one raw record into the v3 GATING store")
    pr.add_argument("--raw-id", required=True,
                    help="record_id of the raw evidence row to cite")
    pr.add_argument("--event-class", required=True,
                    choices=list(EVENT_CLASSES))
    pr.add_argument("--supersedes", default="",
                    help="gating record_id this row corrects/replaces")
    pr.add_argument("--notes", default="")
    pr.add_argument("--raw-path", default=str(RAW_ASSERTIONS_PATH),
                    help="non-default store (rehearsals/tests only)")
    pr.add_argument("--gating-path", default=str(ASSERTIONS_PATH),
                    help="non-default store (rehearsals/tests only)")
    pr.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    now_utc = datetime.now(timezone.utc).isoformat()
    try:
        if args.cmd == "append-raw":
            row = append_raw(symbol=args.symbol, event_id=args.event_id,
                             fiscal_period=args.fiscal_period,
                             status=args.status,
                             expected_date=args.expected_date,
                             occurred_date=args.occurred_date,
                             timing=args.timing, source_type=args.source_type,
                             source_url=args.source_url,
                             known_as_of=args.known_as_of, notes=args.notes,
                             now_utc=now_utc, record_type=args.record_type,
                             supersedes=args.supersedes,
                             path=Path(args.raw_path),
                             dry_run=args.dry_run)
            store = args.raw_path
        else:
            row = promote(raw_id=args.raw_id, event_class=args.event_class,
                          supersedes=args.supersedes, notes=args.notes,
                          now_utc=now_utc, gating_path=Path(args.gating_path),
                          raw_path=Path(args.raw_path), dry_run=args.dry_run)
            store = args.gating_path
    except SystemExit as exc:
        print(str(exc))
        return 2
    except (OSError, ValueError, csv.Error) as exc:
        print(f"REFUSED: {type(exc).__name__}: {exc}")
        return 2
    outcome = ("DRY RUN (nothing written)" if args.dry_run
               else f"appended to {store}; store re-validated")
    print(f"{outcome}: {row}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
