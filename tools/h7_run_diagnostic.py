"""tools/h7_run_diagnostic.py -- THE one mechanically gated command that can
execute an H7 lane diagnostic (7b-3; 7b-2R finding 7; 7b-2R.1 finding A).

    uv run python tools/h7_run_diagnostic.py <diagnostic_id>

There is no other launch path -- and nothing in this tool to bypass: the OOS
authorization lives INSIDE the runner's execution boundary
(research.diagnostics.authorize_oos_run, called by run_lane before any
loader touches post-IN_SAMPLE_END data), not in a token this tool issues.
This command only resolves the committed attempt, invokes the
self-authorizing runner, and ledgers the result BEFORE anything is printed
or exported; a result can never be inspected before it is ledgered.

FLOW:
  1. the ledger chain verifies AND the ledger dir has no uncommitted git
     changes (anchored);
  2. the diagnostic_attempt for <diagnostic_id> defines lane/symbols/window
     (nothing is taken from the command line but the id); the window must
     equal the registered H7 window and the symbols must be within the
     registered set;
  3. run_lane(..., diagnostic_id=...) authorizes AT THE BOUNDARY before any
     loader runs: anchored ledger, write-once result, attempt currency
     (source version + config/cost/source/registration hashes), v2 PASS
     receipt binding (receipt_hash + data_manifest_hash), and equality of
     the runner's manifest with the attempt's audited manifest hash;
  4. the raw result AND its automatic adjudication are appended to the
     write-once ledger record BEFORE anything is printed or exported; the
     ledger is verified again and the trial count is proven unchanged;
     only then is the results artifact written.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path

import config
from research import ledger
from research.diagnostics import DiagnosticError, require_anchored_ledger

RESULTS_DIR = Path("results/h7")


def run_gated_diagnostic(diagnostic_id: str, *, base_dir="ledger") -> dict:
    from harness.run_h7_backtest import run_lane
    from tools.h7_adjudicate import adjudicate_lane

    # ---- resolve the committed attempt (invocation comes from the ledger) --
    require_anchored_ledger(base_dir)
    attempts = [r for r in ledger.read_all(base_dir)
                if r.get("entry_type") == "diagnostic_attempt"
                and r.get("diagnostic_id") == diagnostic_id]
    if not attempts:
        raise DiagnosticError(
            f"no diagnostic_attempt recorded for {diagnostic_id!r} -- the "
            f"attempt must be committed before launch")
    attempt = attempts[-1]
    lane = attempt["lane"]
    symbols = list(attempt["scope"]["symbols"])
    window = attempt["window"]
    if (window.get("start") != config.H7_BACKTEST_START
            or window.get("end") != config.H7_BACKTEST_END):
        raise DiagnosticError(
            f"attempt window {window} != registered H7 window "
            f"{config.H7_BACKTEST_START}..{config.H7_BACKTEST_END}")
    unknown = [s for s in symbols if s not in config.H7_BACKTEST_SYMBOLS]
    if unknown:
        raise DiagnosticError(
            f"attempt names symbols outside the registered set: {unknown}")

    trial_count_before = ledger.current_trial_count(base_dir)

    # ---- execution: run_lane self-authorizes at the boundary ----------------
    raw = run_lane(lane, window["start"], window["end"], symbols=symbols,
                   diagnostic_id=diagnostic_id)
    adjudication = adjudicate_lane(raw["trades"], lane,
                                   coverage=raw["coverage"],
                                   gaps=raw["gaps"])

    # ---- ledger BEFORE print/export (owner rule) ----------------------------
    from research.experiments import json_safe
    result_body = {"raw": json_safe(raw), "adjudication": adjudication}
    result_hash = _record_result(diagnostic_id, result_body, base_dir)
    ledger.verify(base_dir=base_dir)
    trial_count_after = ledger.current_trial_count(base_dir)
    if trial_count_after != trial_count_before:
        raise DiagnosticError(
            f"trial count moved ({trial_count_before} -> "
            f"{trial_count_after}) -- diagnostics must be non-trial")

    # ---- only now: artifact + stdout ----------------------------------------
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact = RESULTS_DIR / f"{diagnostic_id}.json"
    artifact.write_text(json.dumps(
        {"diagnostic_id": diagnostic_id, "lane": lane,
         "attempt_hash": attempt["record_hash"],
         "result_hash": result_hash, **result_body},
        indent=1, sort_keys=True, default=str) + "\n")
    return {"diagnostic_id": diagnostic_id, "lane": lane,
            "adjudication": adjudication, "artifact": str(artifact),
            "result_hash": result_hash,
            "trial_count": trial_count_after}


def _record_result(diagnostic_id: str, result_body: dict,
                   base_dir: str) -> str:
    from research.diagnostics import record_diagnostic_result
    return record_diagnostic_result(diagnostic_id=diagnostic_id,
                                    result=result_body, base_dir=base_dir)


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("diagnostic_id",
                        help="id of the committed diagnostic_attempt")
    args = parser.parse_args(argv)
    try:
        out = run_gated_diagnostic(args.diagnostic_id)
    except (DiagnosticError, ledger.LedgerError) as e:
        print(f"LAUNCH REFUSED: {e}")
        return 2
    print(json.dumps(out["adjudication"], indent=2))
    print(f"ledgered result {out['result_hash']} "
          f"(trial count unchanged: {out['trial_count']}); "
          f"artifact: {out['artifact']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
