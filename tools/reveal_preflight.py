"""READ-ONLY reveal preflight: checks every reveal gate that can be checked
without touching the holdout or writing anything. NEVER calls reveal_oos.

Usage: reveal_preflight.py <hypothesis_id>
"""
import subprocess
import sys

import config
from research import hashing, ledger

hyp = sys.argv[1]
records = ledger.read_all()
ledger.verify()
print("chain verify: OK")

runs = [r for r in records if r.get("entry_type") == "run"
        and r.get("hypothesis_id") == hyp]
if not runs:
    sys.exit(f"NO REGISTERED RUN for {hyp!r}")
run = runs[-1]
print(f"registered: run_id={run['run_id']} scope={run['scope']['symbols']} "
      f"oos_window={run['oos_window']['start']}..{run['oos_window']['end']}")

ok = True
for name, live in (("config_hash", hashing.config_hash()),
                   ("cost_model_hash", hashing.cost_model_hash()),
                   ("source_hash", hashing.source_hash())):
    match = run[name] == live
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

st = subprocess.run(["git", "-C", str(hashing.REPO_ROOT), "status", "--porcelain",
                     "--", "ledger/experiments.jsonl", "ledger/HEAD"],
                    capture_output=True, text=True)
anchored = not st.stdout.strip()
ok &= anchored
print(f"ledger anchored (committed clean): {'YES' if anchored else 'NO -- commit first'}")

print(f"\nPREFLIGHT: {'ALL GATES WOULD PASS' if ok else 'REVEAL WOULD BE REFUSED'}")
print("note: the reveal itself remains an owner decision; this script never "
      "touches the holdout or the ledger.")
