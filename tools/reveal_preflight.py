"""READ-ONLY reveal preflight: checks every reveal gate that can be checked
without touching the holdout or writing anything. NEVER calls reveal_oos.

Usage: reveal_preflight.py <hypothesis_id>
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from research import hashing, ledger  # noqa: E402


def _ledger_clean_tracked_default(paths: list[str]) -> bool:
    st = subprocess.run(["git", "-C", str(hashing.REPO_ROOT), "status",
                         "--porcelain", "--", *paths],
                        capture_output=True, text=True)
    return not st.stdout.strip()


def preflight(hyp: str, base_dir: str = "ledger", *,
              live_hashes: dict | None = None,
              ledger_clean_tracked=None) -> bool:
    """True iff every checkable reveal gate would pass for `hyp`.

    `live_hashes`/`ledger_clean_tracked` are injectable for tests; the
    defaults compute the real repo hashes and git-porcelain state. Raises if
    the chain itself fails verification (a broken chain must never read as
    a passing preflight)."""
    records = ledger.read_all(base_dir)
    ledger.verify(base_dir)
    print("chain verify: OK")

    runs = [r for r in records if r.get("entry_type") == "run"
            and r.get("hypothesis_id") == hyp]
    if not runs:
        print(f"NO REGISTERED RUN for {hyp!r}")
        return False
    run = runs[-1]
    print(f"registered: run_id={run['run_id']} scope={run['scope']['symbols']} "
          f"oos_window={run['oos_window']['start']}..{run['oos_window']['end']}")

    if live_hashes is None:
        live_hashes = {"config_hash": hashing.config_hash(),
                       "cost_model_hash": hashing.cost_model_hash(),
                       "source_hash": hashing.source_hash()}
    ok = True
    for name in ("config_hash", "cost_model_hash", "source_hash"):
        match = run[name] == live_hashes[name]
        ok &= match
        print(f"{name}: {'MATCH' if match else 'DRIFTED -- reveal would refuse'}")

    reveals = [r for r in records if r.get("entry_type") == "oos_reveal"]
    attempts = [r for r in records if r.get("entry_type") == "oos_attempt"]
    touched = {r["hypothesis_id"] for r in attempts + reveals}
    print(f"budget: {len(touched)}/{config.OOS_LOOK_BUDGET} hypotheses touched "
          f"({sorted(touched) if touched else 'none'})")
    if any(r["hypothesis_id"] == hyp for r in reveals):
        ok = False
        print("WRITE-ONCE: already revealed -- reveal would refuse")
    if hyp not in touched and len(touched) >= config.OOS_LOOK_BUDGET:
        ok = False
        print("BUDGET: exhausted for new hypotheses -- reveal would refuse")

    if ledger_clean_tracked is None:
        ledger_clean_tracked = _ledger_clean_tracked_default
    anchored = ledger_clean_tracked(["ledger/experiments.jsonl", "ledger/HEAD"])
    ok &= anchored
    print(f"ledger anchored (committed clean): {'YES' if anchored else 'NO -- commit first'}")

    print(f"\nPREFLIGHT: {'ALL GATES WOULD PASS' if ok else 'REVEAL WOULD BE REFUSED'}")
    print("note: the reveal itself remains an owner decision; this script never "
          "touches the holdout or the ledger.")
    return ok


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: reveal_preflight.py <hypothesis_id>")
    sys.exit(0 if preflight(sys.argv[1]) else 1)
