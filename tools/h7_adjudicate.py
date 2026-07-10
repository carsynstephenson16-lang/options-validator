"""tools/h7_adjudicate.py -- dedicated H7 lane adjudicator (7b-2 C4).

Vocabulary is FROZEN to exactly four verdicts (owner decision 2026-07-10):

    REJECTED                        CI90 entirely below zero with enough losses
    INCONCLUSIVE_INSUFFICIENT       loss/cohort gates not met; ratios unreliable
    INCONCLUSIVE_NO_EDGE            CI90 straddles zero
    SURVIVED_NON_BLIND_DIAGNOSTIC   CI90 entirely above zero

KILL-NOT-BLESS: this diagnostic runs on a disclosed NON-BLIND window
(v1.2(6) isolated-lane estimand). "Survived" is NOT approval, NOT
validation, and NOT evidence the strategy makes money live -- it only means
this one non-blind test failed to kill the lane. A REJECTED lane is dead
without a forward window; a SURVIVED lane still owes the registered forward
paper window before any further step. The verdict gates on LOSSES
(config.MIN_LOSSES_FOR_VERDICT), never on win rate.

Usage (7b-3 only, after the audit receipt + committed diagnostic_attempt):
    uv run python tools/h7_adjudicate.py results/h7/lane_a.json
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from metrics import scoreboard

VERDICTS = ("REJECTED", "INCONCLUSIVE_INSUFFICIENT", "INCONCLUSIVE_NO_EDGE",
            "SURVIVED_NON_BLIND_DIAGNOSTIC")


def adjudicate_lane(trades: list[dict], lane: str) -> dict:
    """Map one lane's closed-trade dicts onto the frozen H7 vocabulary.
    Pure: no I/O, no ledger writes (recording is the caller's job)."""
    board = scoreboard(trades, label=f"H7{lane} isolated diagnostic")
    n_losses = board["n_losses"]
    ci_lo, ci_hi = board["expectancy_CI90"]
    insufficient = board["verdict"].startswith("INSUFFICIENT SAMPLE")
    if insufficient or n_losses < config.MIN_LOSSES_FOR_VERDICT:
        verdict = "INCONCLUSIVE_INSUFFICIENT"
    elif ci_hi < 0:
        verdict = "REJECTED"
    elif ci_lo > 0:
        verdict = "SURVIVED_NON_BLIND_DIAGNOSTIC"
    else:
        verdict = "INCONCLUSIVE_NO_EDGE"
    return {
        "lane": lane,
        "verdict": verdict,
        "n_trades": board["n_trades"],
        "n_losses": n_losses,
        "expectancy_per_trade": board["expectancy_per_trade"],
        "expectancy_CI90": [ci_lo, ci_hi],
        "estimand": ("isolated-lane, per-symbol, disclosed non-blind "
                     "diagnostic; portfolio caps not simulated (v1.2(6))"),
        "note": ("survived != approved: a non-blind diagnostic can kill a "
                 "lane, never bless one; the forward paper window carries "
                 "the registered test"),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results_json",
                        help="path to a lane result file: "
                             '{"lane": "a", "trades": [...]}')
    args = parser.parse_args(argv)
    payload = json.loads(Path(args.results_json).read_text())
    out = adjudicate_lane(payload["trades"], payload["lane"])
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
