# Task 6 stop report

## Verdict

Implemented the failed-feasibility stop gate for `h7-forward-schwab-v1`.
Final state: **NOT READY / NOT ACTIVATED**. No registration, ledger append,
authority patch, ops advance, ritual, or status command was performed.

## TDD evidence

RED, before production changes:

- `uv run python -m unittest discover -s tests -p 'test_h7_schwab_window_registration.py'`
- 13 tests ran; five expected failures proved the absent behavior: missing,
  stale-hash, and wrong-namespace owner lines were accepted, and hash-correct
  3/1,050 and 4/1,050 receipts appended instead of refusing.
- The manual-composition suite remained 5/5 at RED after its qualifying fixture
  was changed to exact 20-entry arithmetic.

GREEN, after the minimum builder change:

- Schwab registration: 13/13 passed.
- Schwab manual activation composition: 5/5 passed.
- H7 one-door: 8/8 passed.
- Tests emitted the existing LumiBot asyncio `ResourceWarning`; no test failed.

## Changes

- `options_researcher/h7_schwab_window_registration.py`: validates the immutable
  feasibility receipt's hash and arithmetic, refuses calculated expected entries
  below `2 * config.MIN_LOSSES_FOR_VERDICT`, and then requires exact equality of
  `H7_SCHWAB_FEASIBILITY_DECISION` to the receipt-hash and namespace binding line.
  The field is frozen into `owner_authorization` through `OWNER_FIELDS`.
- `tests/test_h7_schwab_window_registration.py`: qualifying fixtures use exact
  15 x 70 = 1,050 arithmetic with 20 passes and 20.0 expected entries; covers
  3/1,050 and 4/1,050 pre-append refusal, the exact-20 lower boundary, and
  missing/stale-hash/wrong-namespace owner-line refusal.
- `tests/test_h7_schwab_manual_activate.py`: qualifying CLI composition fixture
  uses the same exact boundary and explicit namespace/hash-bound owner line.
- `reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md`: records the
  2026-08-11 receipt, embedded hash, 4/1,050 and 4.0 < 20 stop, owner redesign,
  inoperative OD-3, forbidden v1 authority patch, evidence-only canary/restore,
  and separately versioned design-only v2 path.
- `docs/provider-transition.md`: marks the H7 Schwab row
  `STOPPED_FEASIBILITY / NOT REGISTERED / NOT ACTIVATED`.

## Static and formatting validation

The focused chain passed after rerunning outside the sandbox because uv's
existing global cache was not readable inside the sandbox:

- Ruff check: all checks passed.
- Ruff format check: 3 files already formatted.
- Pyright: 0 errors, 0 warnings, 0 informations.
- `git diff --check`: passed.

## Immutable-state proof

- `data/ritual_authority.py` remains `h7_active=False` and
  `exact_session_source_active=False`.
- Its Git object is identical at base and worktree:
  `4dc8ce229e12c60433cd3742d9effd871ab61e30`.
- `git diff --exit-code e61709c -- ledger/h7_forward ledger/h7_forward_schwab`
  passed.
- Tracked ledger blob IDs match base exactly:
  - `ledger/h7_forward/HEAD`: `060a0766e77497dc9805eb32175316428941659e`
  - `ledger/h7_forward/README.md`: `461d6e395dce4c2e57c2fd4a1036f5ef49be6485`
  - `ledger/h7_forward/events.jsonl`: `9e4dcbe35e1c9461a2bb4a3393cb35745e41eba4`
  - `ledger/h7_forward_schwab/README.md`: `07aee03f0f3ce85094945ade7a44eb0245c00ac0`
- No untracked or modified file exists under either ledger directory.

## Commit

Single focused production commit:
`47f4d78 fix(h7): enforce Schwab v1 feasibility stop`.

## Corrective review cycle

Independent review reproduced two hash-correct bypasses in the first commit:
a shortened 4/210 denominator could manufacture exactly 20 projected entries,
and receipt symbols were not compared with the canonical registration cohort.

Corrective RED recorded nine failures for the shortened denominator, fake
universe, alternate stack/tool/lookback dates/session count, nonzero or hidden
errors, and stale config identity. GREEN after the correction:

- Schwab registration: 16/16 passed.
- Schwab manual activation composition: 5/5 passed.
- H7 one-door: 8/8 passed.
- Ruff and formatting passed; Pyright reported 0 errors; `git diff --check`
  passed.

The builder now reuses the feasibility tool's receipt-kind and stack-version
constants and binds the exact task-3 study contract: 2026-04-16 through
2026-07-27, 70 lookback sessions, 70 window sessions, current config hash,
zero errors, the exact ordered canonical 15-name scope, and the derived 1,050
symbol-day denominator. The registration manifest's `included` list must equal
the receipt universe exactly. Authority and both H7 ledger directories remain
byte-identical to `e61709c`.

Corrective commit:
`06ecf75 fix(h7): bind Schwab feasibility study identity`.
