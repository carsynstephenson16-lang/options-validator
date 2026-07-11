"""tools/h7_run_diagnostic.py -- THE one mechanically gated command that can
execute an H7 lane diagnostic (7b-3; 7b-2R finding 7).

    uv run python tools/h7_run_diagnostic.py <diagnostic_id>

There is no other launch path: run_lane's public allow_oos escape hatch is
removed, and the OOS capability token is issued only here, after every gate
below holds. The multi-command sequence (attempt -> run -> record ->
standalone adjudicator) is gone; a result can never be inspected before it
is ledgered.

GATES (all verified BEFORE any execution):
  1. the ledger chain verifies AND the attempt is committed to git
     (anchored -- no uncommitted ledger edits);
  2. a diagnostic_attempt exists for <diagnostic_id> and NO prior
     diagnostic_result does (results are write-once);
  3. the attempt's lane/symbols/window define this invocation (nothing is
     taken from the command line but the id), and the window must equal the
     registered H7 window;
  4. source_hash_version is exactly the supported version;
  5. the attempt's registration hashes match the current ledger, and its
     config/cost/source hashes match the CURRENT surfaces (stale -> refuse);
  6. the bound v2 audit receipt exists, re-verifies against current repo
     state, has verdict PASS, and matches the attempt's receipt_hash;
  7. the runner's inputs are exactly the receipt's manifest: the manifest
     is recomputed and its hash must equal the receipt's manifest_hash
     (== the attempt's data_manifest_hash).

EXECUTION: deterministic run_lane over the receipt manifest; the raw result
AND its automatic adjudication are appended to the write-once ledger record
BEFORE anything is printed or exported; the ledger is verified again and
the trial count is proven unchanged; only then is the results artifact
written.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import subprocess
from pathlib import Path

import config
from research import ledger
from research.diagnostics import DiagnosticError, verify_attempt_current
from research.hashing import canonical_json, sha256_hex

RESULTS_DIR = Path("results/h7")


def _require_anchored_ledger(base_dir: str) -> None:
    ledger.verify(base_dir=base_dir)
    out = subprocess.run(["git", "status", "--porcelain", base_dir],
                         capture_output=True, text=True).stdout.strip()
    if out:
        raise DiagnosticError(
            f"ledger dir {base_dir!r} has uncommitted changes -- the "
            f"attempt must be anchored (committed) before execution:\n{out}")


def run_gated_diagnostic(diagnostic_id: str, *, base_dir="ledger") -> dict:
    from data.h7_manifest import eligible_manifest
    from harness.run_h7_backtest import DiagnosticCapability, run_lane
    from tools.h7_adjudicate import adjudicate_lane
    from tools.h7_data_audit import RECEIPT_PATH

    # ---- gates 1..2 --------------------------------------------------------
    _require_anchored_ledger(base_dir)
    results = [r for r in ledger.read_all(base_dir)
               if r.get("entry_type") == "diagnostic_result"
               and r.get("diagnostic_id") == diagnostic_id]
    if results:
        raise DiagnosticError(
            f"{diagnostic_id!r} already has a write-once result; a "
            f"diagnostic is never rerun under the same id")

    # ---- gates 3..6 (attempt freshness, receipt PASS + hash binding) -------
    attempt = verify_attempt_current(diagnostic_id, base_dir=base_dir)
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

    # ---- gate 7: runner inputs are EXACTLY the receipt manifest ------------
    manifest = eligible_manifest(symbols=symbols, start=window["start"],
                                 end=window["end"])
    receipt = json.loads(RECEIPT_PATH.read_text())
    if sha256_hex(canonical_json(manifest)) != receipt["manifest_hash"]:
        raise DiagnosticError(
            "recomputed eligible-session manifest != receipt manifest_hash "
            "-- the runner would not consume exactly the audited inputs")

    trial_count_before = ledger.current_trial_count(base_dir)

    # ---- execution ----------------------------------------------------------
    capability = DiagnosticCapability(attempt_hash=attempt["record_hash"])
    raw = run_lane(lane, window["start"], window["end"], symbols=symbols,
                   manifest=manifest, capability=capability)
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
