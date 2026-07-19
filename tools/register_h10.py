"""H10a/H10b + rank-quality chained registrations. DRY-RUN BY DEFAULT.

Owner-locked values (2026-07-18, spec sec.15 LOCKED block): delta 0.40-0.60,
DTE 30-60, verdict gate >=7 losses (H10 override of repo default 10, weaker
verdict disclosed), own $2,000/month premium cap (not shared with H6+H8),
windows H10a 2026-10-06 / H10b 2027-01-06. Signal selection is OUTCOME-INFORMED
and permanently disclosed; only observations after registration count."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from research.ledger import append  # noqa: E402

_COMMON = (
    "structure=defined-risk single long call, premium<=$600 (MAX_LOSS_PER_TRADE); "
    "contract=delta 0.40-0.60 within +/-10 pct of spot; 30-60 DTE; "
    "universe=H7_WATCHLIST names passing H7 admission at entry "
    "(>=5 NTM monthly contracts, spread<=5 pct, OI>=100), re-measured at entry; "
    "fills=mid-or-worse + SLIPPAGE_HAIRCUT + COMMISSION_PER_CONTRACT both legs; "
    "sizing=1 contract; concurrency=own cap $2,000/month premium at risk "
    "(NOT shared with H6+H8); earnings=skip entry if a known report lands inside "
    "the option life, source-health UNHEALTHY = per-name entry ban; "
    "exit priority=(1) +100 pct target (2) time-exit 20 trading sessions "
    "(3) 21 DTE; receipts=forward paper book only, no order path; "
    "verdict gates at >=7 losses (owner override of MIN_LOSSES_FOR_VERDICT=10, "
    "weaker verdict disclosed); reject=90 pct bootstrap CI upper<=0 on after-cost "
    "expectancy/trade; further-testing=CI lower>0; "
    "signal selection is outcome-informed (QM study 2026-07-14) and permanently "
    "disclosed; only observations recorded after this registration count."
)

REGISTRATIONS = [
    {
        "entry_type": "trial_intent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hypothesis_id": "H10a",
        "reason": ("H10a REGISTRATION -- QM parabolic long-continuation, forward "
                   "paper only, window ends 2026-10-06. " + _COMMON),
    },
    {
        "entry_type": "trial_intent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hypothesis_id": "H10b",
        "reason": ("H10b REGISTRATION -- QM breakout continuation, forward paper "
                   "only, window ends 2027-01-06 (low fire rate disclosed: 11 "
                   "historical fires; may stay INSUFFICIENT_SAMPLE). " + _COMMON),
    },
    {
        "entry_type": "trial_intent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hypothesis_id": "RQ1",
        "reason": ("RANK-QUALITY DESCRIPTIVE PREREG -- no-verdict study: Spearman "
                   "rho between attractiveness GREEN-fraction and forward "
                   "21-trading-day realized vol (and separately forward IV "
                   "change); |rho|>=0.30 flagged notable, DESCRIPTIVE ONLY; "
                   "synthetic and lookahead-contaminated rows excluded; big 4 are "
                   "outcome-selected so no rho is ever edge without a fresh "
                   "forward preregistration."),
    },
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true",
                    help="perform the real chained appends (owner go required)")
    args = ap.parse_args()
    for body in REGISTRATIONS:
        print(json.dumps(body, indent=2, sort_keys=True))
    if not args.execute:
        print("\nDRY RUN -- nothing appended. Re-run with --execute after owner go.")
        return
    for body in REGISTRATIONS:
        record_hash = append(dict(body))
        print(f"APPENDED {body['hypothesis_id']}: {record_hash}")
    print("Commit ledger/experiments.jsonl + ledger/HEAD now; then update README "
          "scope status (four -> six live hypotheses) in the same commit.")


if __name__ == "__main__":
    main()
