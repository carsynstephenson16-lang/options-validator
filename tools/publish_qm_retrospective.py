"""Publish the QM base-rates attempt-#2 retrospective_result -- WITHOUT
re-running the study (one-run-per-vintage contract is spent).

DRY-RUN BY DEFAULT: prints the canonical record and exits. --execute performs
the real chained append; owner go required (spec 2026-07-17 sec.9)."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from research.ledger import RETROSPECTIVE_REQUIRED_LABELS, append  # noqa: E402

REPORT = REPO / "reports" / "2026-07-14-qm-base-rates.md"
CONTEXT = REPO / "reports" / "attractiveness_context" / "2026-07-15.json"
FACTS = REPO / "ledger" / "facts.log"
PREREG_MARKER = "QM_STUDY_PREREG"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prereg_line_sha(path: Path, marker: str) -> str:
    lines = [ln for ln in path.read_text().splitlines() if f"\t{marker} " in ln]
    if len(lines) != 1:
        sys.exit(f"expected exactly one {marker} line in facts.log, found {len(lines)}")
    return hashlib.sha256(lines[0].encode()).hexdigest()


def _first_commit(path: Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(REPO), "log", "--diff-filter=A", "--format=%H", "--", str(path)],
        capture_output=True, text=True, check=True).stdout.strip().splitlines()
    if not out:
        sys.exit(f"no commit found adding {path}")
    return out[-1]  # oldest = the commit that added the file


def build_record() -> dict:
    return {
        "entry_type": "retrospective_result",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subject": ("QM base-rates study (2026-07-14) attempt-#2 publication: "
                    "already-computed readings, no rerun"),
        "hypothesis_id": None,
        "report_sha256": _sha256_file(REPORT),
        "context_sha256": _sha256_file(CONTEXT),
        "prereg_ref_sha256": _prereg_line_sha(FACTS, PREREG_MARKER),
        "source_commit": _first_commit(REPORT),
        "labels": list(RETROSPECTIVE_REQUIRED_LABELS),
        "result": {
            "breakout_deduped_fires": 11,
            "breakout_reading": "descriptive only (10-19 band), no H8 decision possible",
            "parabolic_deduped_fires": 35,
            "parabolic_excess_5d": 0.0268,
            "parabolic_excess_10d": 0.0070,
            "parabolic_excess_20d": 0.0147,
            "parabolic_fade_reading": "REJECTED (median excess >= 0)",
            "h8_decision": "NO H8 arc for either setup",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true",
                    help="perform the real chained append (owner go required)")
    args = ap.parse_args()
    record = build_record()
    print(json.dumps(record, indent=2, sort_keys=True))
    if not args.execute:
        print("\nDRY RUN -- nothing appended. Re-run with --execute after owner go.")
        return
    record_hash = append(record)
    print(f"\nAPPENDED. record_hash={record_hash}")
    print("Commit ledger/experiments.jsonl + ledger/HEAD now.")


if __name__ == "__main__":
    main()
