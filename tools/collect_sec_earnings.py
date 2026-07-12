"""tools/collect_sec_earnings.py -- ONE bounded collection pass (7b-2R
section 8, owner-authorized 2026-07-11) over the eight H7 backtest names.

Collects RAW Item 2.02 filing records from SEC EDGAR into the v2 RAW
evidence store (data/earnings/assertions_v2.csv), with the filing's
acceptanceDateTime as the true point-in-time known_as_of and the filing's
period-of-report as the occurred date.

7b-2R.1: RAW COLLECTION ONLY. An Item 2.02 filing is not automatically an
earnings report (it may be a preliminary release or a business update).
Rows collected here are UNCLASSIFIED and can never gate; promotion into
the v3 gating store (data/earnings/gating_v3.csv) is a separate,
per-record, classified and source-verified act.

WHAT THIS DELIBERATELY DOES NOT DO (owner rules):
  * no announcement-date inference from eventual report dates;
  * no modern aggregator calendars;
  * no assumed-notice proxy;
  * does NOT write data/earnings/coverage.json -- completeness
    declarations are owner-ratified, not collector output.

This is a one-time archive builder, not recurring automation (deferred by
owner decision). Network: data.sec.gov only (free public API, authorized).

Usage:
    uv run python tools/collect_sec_earnings.py --dry-run
    uv run python tools/collect_sec_earnings.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import config
from options_researcher.h7_earnings import (
    RAW_ASSERTIONS_PATH,
    load_raw_assertions,
)


def _user_agent() -> str:
    """SEC requires an identifying User-Agent. It comes from the
    environment (SEC_USER_AGENT in .env), never from committed source
    (7b-2R.1 E); missing configuration fails closed."""
    ua = os.environ.get("SEC_USER_AGENT", "").strip()
    if not ua:
        raise SystemExit(
            "SEC_USER_AGENT is not set -- refusing to hit data.sec.gov. "
            "Add e.g. SEC_USER_AGENT='project-name contact@example.com' "
            "to .env (see .env.example).")
    return ua


CIKS = {
    "NOW": 1373715, "NVDA": 1045810, "PLTR": 1321655, "MSFT": 789019,
    "AMZN": 1018724, "VST": 1692819, "CEG": 1868275, "SMCI": 1375365,
}
NY = ZoneInfo("America/New_York")


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _filing_batches(cik: int):
    """The recent-filings block plus every archived submissions page."""
    root = _get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
    yield root["filings"]["recent"]
    for extra in root["filings"].get("files", []):
        time.sleep(0.15)   # stay far under SEC's 10 req/s guidance
        yield _get(f"https://data.sec.gov/submissions/{extra['name']}")


def occurred_filings(symbol: str, cik: int, start: str, end: str) -> list[dict]:
    """Every 8-K with item 2.02 whose period-of-report is in [start, end];
    one record per report date, EARLIEST acceptance (the announcement)."""
    by_report: dict[str, dict] = {}
    for batch in _filing_batches(cik):
        rows = zip(batch["form"], batch["items"], batch["reportDate"],
                   batch["acceptanceDateTime"], batch["accessionNumber"])
        for form, items, report, accepted, accession in rows:
            if not form.startswith("8-K") or "2.02" not in (items or ""):
                continue
            if not report or not (start <= report <= end):
                continue
            acc = datetime.fromisoformat(accepted.replace("Z", "+00:00"))
            cur = by_report.get(report)
            if cur is None or acc < cur["accepted"]:
                by_report[report] = {
                    "symbol": symbol, "report": report, "accepted": acc,
                    "accession": accession.replace("-", ""),
                    "url": (f"https://www.sec.gov/Archives/edgar/data/"
                            f"{cik}/{accession.replace('-', '')}/"),
                }
    return [by_report[k] for k in sorted(by_report)]


def _timing(accepted_utc: datetime) -> str:
    h = accepted_utc.astimezone(NY)
    if h.hour < 9 or (h.hour == 9 and h.minute < 30):
        return "bmo"
    if h.hour >= 16:
        return "amc"
    return "unknown"


def to_rows(filings: list[dict], existing, next_id: int,
            checked_at: str) -> tuple[list[list], int]:
    rows = []
    for f in filings:
        if (f["symbol"], f["report"]) in existing:
            continue
        rows.append([
            f"A{next_id:04d}", f["symbol"], f"{f['symbol']}-8K-{f['report']}",
            "", "assertion", "occurred", "", f["report"],
            _timing(f["accepted"]), "sec_filing", f["url"],
            f["accepted"].isoformat(), checked_at, "",
            "SEC EDGAR 8-K item 2.02; acceptanceDateTime is the "
            "point-in-time known_as_of (7b-2R bounded collection pass)",
        ])
        next_id += 1
    return rows, next_id


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    current = load_raw_assertions()
    existing = {(a["symbol"], (a["occurred_date"] or a["expected_date"]))
                for a in current if a["status"] == "occurred"}
    existing = {(s, d.isoformat() if d else "") for s, d in existing}
    next_id = max(int(a["record_id"][1:]) for a in current) + 1
    checked_at = datetime.now(timezone.utc).isoformat()

    all_rows: list[list] = []
    for symbol in config.H7_BACKTEST_SYMBOLS:
        filings = occurred_filings(symbol, CIKS[symbol],
                                   config.H7_BACKTEST_START,
                                   config.H7_BACKTEST_END)
        rows, next_id = to_rows(filings, existing, next_id, checked_at)
        all_rows.extend(rows)
        print(f"{symbol}: {len(filings)} item-2.02 reports in window, "
              f"{len(rows)} new rows"
              + (f" (first {filings[0]['report']}, last "
                 f"{filings[-1]['report']})" if filings else ""))
        time.sleep(0.2)

    if args.dry_run:
        print(f"DRY RUN: {len(all_rows)} rows NOT appended")
        return 0
    with Path(RAW_ASSERTIONS_PATH).open("a", newline="") as f:
        csv.writer(f).writerows(all_rows)
    load_raw_assertions()   # fail loud if the append broke the store
    print(f"appended {len(all_rows)} RAW (non-gating) Item 2.02 records to "
          f"{RAW_ASSERTIONS_PATH}; store re-validates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
