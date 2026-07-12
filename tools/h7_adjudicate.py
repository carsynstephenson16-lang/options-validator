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

Usage (display only -- results are never inspectable before they are
ledgered; 7b-2R.1 finding A removed the arbitrary-file CLI):
    uv run python tools/h7_adjudicate.py <diagnostic_id>

The CLI prints the STORED adjudication from the write-once ledgered
diagnostic_result; it never recomputes a verdict from caller-supplied
input. `adjudicate_lane` stays a pure library function used by the gated
launch command (tools/h7_run_diagnostic.py), which ledgers raw result +
adjudication before anything is printed.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from metrics import scoreboard

VERDICTS = ("REJECTED", "INCONCLUSIVE_INSUFFICIENT", "INCONCLUSIVE_NO_EDGE",
            "SURVIVED_NON_BLIND_DIAGNOSTIC")

_GAP_FIELDS = ("symbol", "lane", "session", "stage", "reason")


class CoverageError(ValueError):
    """The result does not account for every eligible session (7b-2R
    finding 6). A data hole must never be adjudicated as if it were an
    opportunity-free market."""


def refuse_unexplained_gaps(coverage: dict | None, gaps) -> None:
    """Raise CoverageError unless every eligible session is either
    simulated or covered by a well-formed structured gap record."""
    if coverage is None:
        raise CoverageError(
            "result carries no coverage accounting -- refusing to "
            "adjudicate (was this produced by the gated runner?)")
    for g in gaps or ():
        missing = [f for f in _GAP_FIELDS if not g.get(f)]
        if missing:
            raise CoverageError(f"malformed gap record (no {missing}): {g}")
    for sym, cov in sorted(coverage.items()):
        if cov.get("unaccounted"):
            raise CoverageError(
                f"{sym}: {len(cov['unaccounted'])} eligible session(s) "
                f"neither simulated nor gap-explained, e.g. "
                f"{cov['unaccounted'][:5]}")


def adjudicate_lane(trades: list[dict], lane: str, *,
                    coverage: dict | None = None, gaps=()) -> dict:
    """Map one lane's closed-trade dicts onto the frozen H7 vocabulary.
    Refuses (CoverageError) results with unexplained eligible-session gaps.
    Pure: no I/O, no ledger writes (recording is the caller's job)."""
    refuse_unexplained_gaps(coverage, gaps)
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


def main(argv: list[str] | None = None, *, base_dir: str = "ledger") -> int:
    """Print the STORED adjudication of an already-ledgered diagnostic
    result. Refuses (exit 2) when the ledger does not verify or no
    write-once diagnostic_result exists for the id -- never adjudicates
    arbitrary caller-supplied JSON."""
    import argparse
    import json

    from research import ledger

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("diagnostic_id",
                        help="id of a LEDGERED diagnostic_result to display")
    args = parser.parse_args(argv)
    try:
        ledger.verify(base_dir=base_dir)
    except ledger.LedgerError as e:
        print(f"REFUSED: ledger does not verify: {e}")
        return 2
    results = [r for r in ledger.read_all(base_dir)
               if r.get("entry_type") == "diagnostic_result"
               and r.get("diagnostic_id") == args.diagnostic_id]
    if not results:
        print(f"REFUSED: {args.diagnostic_id!r} has no ledgered result; "
              f"results are never inspectable before they are ledgered "
              f"(launch via tools/h7_run_diagnostic.py)")
        return 2
    print(json.dumps(results[-1]["result"]["adjudication"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
