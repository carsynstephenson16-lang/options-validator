# Task 6 stop brief — mechanically enforce the failed v1 feasibility gate

Work only in `/Users/carsynstephenson/options-validator/.tmp/worktrees/h7-schwab-recovery` on top of `e61709c`. The independently replayed immutable receipt has 4/1,050 passes and 4.0 expected entries, below the required 20. Therefore no registration, authority flip, ops advance, or ritual status/execution is allowed. This task makes that stop mechanically unavoidable and updates stale operator documentation.

Use TDD. Add a registration-level guard in `options_researcher/h7_schwab_window_registration.py`, not only a CLI check, so every synthetic/real caller refuses a feasibility receipt whose `expected_entries` is below `2 * config.MIN_LOSSES_FOR_VERDICT`. Preserve the existing arithmetic/hash validation. The specific `h7-forward-schwab-v1` lane no longer permits the generic starvation-risk acceptance path; the user selected redesign.

Require a second owner field for any future qualifying v1 registration. Define one small deterministic helper/constant for the exact required line, binding the namespace and qualifying feasibility receipt hash while explicitly rejecting the old 3/1,050 starvation path. Recommended exact text:

`REJECT OLD 3/1050 STARVATION-RISK PATH; BIND h7-forward-schwab-v1 TO QUALIFYING FEASIBILITY RECEIPT <receipt_hash>`

Add this field to the frozen owner authorization payload and validate exact equality after receipt validation. Do not fabricate or store an operative owner line in production; tests use explicit fixtures only. Keep the existing OD-3 field required and ensure the namespace appears in the test fixture line. Do not weaken the guarded door or add another append path.

Tests must prove:

- a valid/hash-correct 4/1,050 or 3/1,050 receipt refuses before any ledger append;
- exactly 20 projected entries is the lower accepted boundary;
- a qualifying receipt with a missing, stale-hash, or wrong-namespace owner decision line refuses;
- a qualifying receipt with the exact line still passes existing synthetic and manual-CLI composition tests;
- the real store and old ledger remain untouched.

Update all affected Schwab test fixtures to qualifying arithmetic (use exact 15 x 70 = 1,050 denominator and 20 passes/20 expected entries where a happy path is intended). Do not change the feasibility measurement tool, config threshold, strategy, costs, scorer, or v1 receipt.

Update `reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md` truthfully:

- status `STOPPED_FEASIBILITY / NOT REGISTERED / NOT ACTIVATED`;
- replace the old readiness row with `2026-08-11-feasibility-primary-earnings.json`, embedded hash `d0ffe1f900b8ffc132f757f9783d4581464aaf8b3538271fe2ae337ba1702d0c`, 4/1,050 and 4.0 expected;
- record that the owner selected redesign and rejected starvation acceptance;
- leave OD-3 untyped/inoperative because v1 did not qualify;
- show the second owner-line template but state it cannot be typed/bound to this nonqualifying receipt;
- make the prepared authority patch explicitly forbidden for v1 and remove any remaining ordered wording that implies registration/flip may continue;
- point to the design-only `2026-08-11-v2-arming-bottleneck-design.md` and state v2 needs separate versioning/preregistration before experiments.

Update the H7 Schwab row in `docs/provider-transition.md` from PREPARED to `STOPPED_FEASIBILITY / NOT REGISTERED / NOT ACTIVATED`, citing 4.0 < 20 and the new receipt/design. Keep the read-only capture lane/canary machinery operationally prepared; the real canary and restore are still required evidence work but cannot activate v1.

Run focused registration/manual activation/one-door tests, Ruff, formatting, Pyright for changed Python, and `git diff --check`. Verify authority booleans and `ledger/h7_forward*` bytes are unchanged. Commit code/tests/docs as one focused stop-gate commit. Write ignored `.superpowers/sdd/h7-schwab-recovery-plan/task-6-stop-report.md`; do not commit SDD reports. Return final state explicitly NOT READY / NOT ACTIVATED.
