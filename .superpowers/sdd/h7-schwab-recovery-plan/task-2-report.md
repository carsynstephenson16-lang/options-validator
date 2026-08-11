# Task 2 report — narrow H7 Schwab completion interfaces

## Status

COMPLETE for the scoped implementation. The real registration path was not
run. No authority switch, operations checkout, OAuth state, market data,
cache, or ledger content was changed.

Implementation commit: `5648b29` (`feat(h7): add receipt-bound Schwab completion interfaces`).

## Files changed

- `tools/h7_forward_backup.py`
  - `restore-check` now requires an immutable `backup` receipt.
  - The exact `snapshot_id` is derived from the receipt; `latest` is refused.
  - A caller-supplied snapshot must match the receipt.
  - The restored allow-listed tree is re-inventoried with `backup_inventory()`
    and must equal the receipt's `input_files` exactly.
  - The restore receipt binds the exact snapshot, backup receipt hash, and
    restored inventory.
- `tools/h7_schwab_manual_activate.py`
  - Added an owner-confirmed, full-15-only operator CLI.
  - Revalidates immutable source-health, Schwab data-gate, backup, and restore
    receipts; reruns the exact preclose package and append-time gates; checks
    reviewed evidence hashes; and delegates to the existing Schwab
    `register_window_real` door.
  - Exposes no trim or custom-universe option and contains no direct append.
- `options_researcher/h7_activation_guard.py`
  - Added a provider-specific `owner_fields` seam while preserving the legacy
    default, allowing the shared fresh guard to validate Schwab owner fields.
- `options_researcher/h7_schwab_window_registration.py`
  - Requires and freezes the backup-restore receipt hash in the registration
    event's gate evidence.
- `reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md`
  - Replaced stale Monday-bound wording with the next valid completed-session
    15:45 ET canary wording.
- `tests/test_h7_backup.py`
  - Added exact inventory, wrong snapshot/type/session, missing file, extra
    file, changed size, and same-size changed-hash coverage.
- `tests/test_h7_schwab_manual_activate.py`
  - Added full-15 happy-path composition and partial-scope, stale-session,
    dirty-tree, and moved-HEAD refusals against a temporary ledger.
- `tests/test_h7_one_door.py`
  - Added static direct-append protection for the Schwab CLI.
- `tests/test_h7_schwab_window_registration.py`
  - Extended the evidence fixture for the required restore receipt hash.

## TDD evidence

### Restore receipt binding cycle

RED command:

`MPLCONFIGDIR=/private/tmp/h7-schwab-recovery-mpl PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_h7_backup.py' -v`

Observed RED: exit 1; six expected errors reported
`TypeError: run_restore_check() got an unexpected keyword argument 'backup_receipt_path'`.

GREEN command: same command after the minimal implementation.

Observed GREEN: 7 tests passed.

### Schwab operator composition cycle

RED command:

`MPLCONFIGDIR=/private/tmp/h7-schwab-recovery-mpl PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_h7_schwab_manual_activate.py' -v`

Observed RED: exit 1 with the expected missing-module import for
`tools.h7_schwab_manual_activate`.

GREEN command: same command after implementation.

Observed GREEN: 4 tests passed.

## Focused validation

- `test_h7_backup.py`: 7 passed.
- `test_h7_schwab_manual_activate.py`: 4 passed.
- `test_h7_schwab_window_registration.py`: 10 passed.
- `test_h7_one_door.py`: 8 passed.
- `test_h7_activation_guard.py`: 8 passed.
- `test_h7_trim_at_append.py`: 15 passed, preserving legacy guard behavior.
- `test_h7_schwab_data_gate.py`: 7 passed.
- Ruff check over every changed Python file: passed.
- Ruff format check over the two new Python files: passed.
- Pyright over the new CLI, backup tool, guard seam, and focused tests:
  0 errors, 0 warnings.
- `git diff --check`: passed before the implementation commit and again after.
- CLI help smoke via
  `.venv/bin/python -m tools.h7_schwab_manual_activate --help`: exit 0; only
  fixed evidence inputs are exposed, with no trim/custom-universe option.

The parent agent explicitly reserved broader full-repository validation and
independent review; no full-suite run is claimed here.

## Self-review

- Append-only boundary: the new CLI has no `append_event` call. The existing
  AST scan still finds only each namespace's guarded `register_window_real`
  constructor, and the synthetic CLI test reaches sequence zero only through
  that door.
- Owner authority: the confirmation token, exact owner fields, reviewed spec
  hash, and evidence hashes are required. No owner wording is inferred and no
  authority boolean is changed.
- Scope closure: both source-health and Schwab data-gate receipts must match
  the exact official 15-name identity; the CLI exposes no subset parameter.
- Evidence freshness: completed session, source link, full recomputed Schwab
  result, exact manifest identity, receipt hashes, current clean/matching HEAD,
  guard age, VALID-EMPTY store, and append-time reruns are all fail-closed.
- Backup closure: wrong receipt type/session/snapshot, missing/extra paths,
  size drift, and hash drift all refuse before a restore receipt is written.
- Compatibility: the shared guard's legacy owner-field behavior remains the
  default and its existing activation/trim tests passed.
- Scope audit: no files under operations, OAuth, market-data caches, either H7
  ledger, or authority configuration were edited.

## Concerns and unsupported assumptions

- No real Restic repository or real canary package was exercised; the tests
  use controlled filesystem restores and the existing offline Schwab package
  evaluator. Task 4 must supply the real completed-session evidence.
- No real registration was attempted. The production store remains outside
  this task's mutation scope and registration remains owner-gated.
- Focused tests emitted the repository's existing unclosed-event-loop
  `ResourceWarning` in some modules; all affected test processes exited 0.
- Full-repository tests and independent adversarial review remain for the
  parent task, as explicitly directed.

## Final decision

READY FOR PARENT REVIEW. NOT REGISTERED and NOT ACTIVATED.
