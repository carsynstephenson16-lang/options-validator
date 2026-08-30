# Task 2 independent review

## Re-review verdict — candidate `7cf667f`

- **Spec compliance: PASS**
- **Code quality: PASS**
- **Final readiness: READY for the parent Task 2 gate.** The two prior findings
  are resolved with focused regression evidence. This does not authorize or
  perform registration or activation.

This review is limited to Task 2 machinery. It does not treat a runtime canary,
OAuth renewal, Restic execution, registration, or activation as completed.

## Re-review of prior findings

### RESOLVED — Append-time backup/restore path substitution

**Evidence:** `tools/h7_schwab_manual_activate.py:204-269, 310-367` and
`options_researcher/h7_schwab_window_registration.py:387-411` at candidate
`7cf667f`.

Initial assembly now captures both the backup receipt hash and restore receipt
hash. Append-time `_make_recheck` reloads the pair, verifies their internal
snapshot/session/scope/inventory relationship, and compares both hashes to the
assembly-time values. It returns the exact revalidated restore hash.
`register_window_real` separately requires that returned hash to equal
`evidence["backup_restore_receipt_hash"]` before its final VALID-EMPTY check and
append.

The regression `test_append_time_valid_backup_pair_substitution_refuses`
replaces both paths with a second internally valid same-session pair between
assembly and append, expects `ActivationRefused`, and proves the temporary
ledger remains empty. It passed.

Regression quality is adequate for the reported failure: it exercises a valid
pair rather than a trivially malformed receipt, performs the substitution at
the second data-gate evaluation immediately before receipt reload, and checks
the no-write postcondition.

### RESOLVED — Stale Monday-canary reference

**Evidence:**
`reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md:16` at candidate
`7cf667f` now says `blocked pending the next valid completed-session 15:45 ET
canary`.

`git grep -ni monday 7cf667f --
reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md` returned no matches.

## What passed review

- `restore-check` loads a hash-valid `backup` receipt, derives and refuses
  `latest`, refuses a mismatched caller snapshot/session/scope, restores the
  receipt snapshot, and compares the complete `backup_inventory()` result with
  `input_files` before writing a restore receipt.
- The restore receipt carries the exact snapshot ID, backup receipt hash,
  restored inventory, scope, session, and verification result.
- The new CLI exposes no trim or custom-universe argument. It requires the
  canonical 15-name scope, all 15 source-health rows, all 15 Schwab data-gate
  rows, one exact package identity, a clean/matching HEAD, a fresh guard, and a
  VALID-EMPTY store.
- The CLI contains no `append_event` call and delegates to the existing Schwab
  `register_window_real` door. Static one-door tests passed.
- No authority boolean or old H7 ledger path is changed by the reviewed diff.

## Commands and evidence reviewed

- Read the Task 2 brief, implementer report, and authoritative
  `review-f9aad05..5648b29.diff`.
- Inspected candidate objects with `git show 5648b29:<path>` for the backup
  tool, Schwab CLI, activation guard, registration door, and focused tests.
- Confirmed the review worktree was clean; current HEAD was `97d1646`, not the
  candidate, so the supplied diff/candidate objects were used as authority.
  The later commit does not change Task 2 implementation files.
- `git grep -ni -E 'monday([ _-]+)(canary|boundary)|BLOCKED_PENDING_MONDAY' 5648b29 -- reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md`
  found the remaining line 16 token.
- Focused unittest command covering `test_h7_backup.py`,
  `test_h7_schwab_manual_activate.py`, `test_h7_one_door.py`, and
  `test_h7_schwab_window_registration.py`: exit 0. The visible groups reported
  7, 4, and 8 passes before the final group continued; existing unclosed-event-
  loop `ResourceWarning`s were emitted.
- Re-review package `review-5648b29..7cf667f.diff` and candidate objects at
  `7cf667f` were inspected directly.
- `test_h7_schwab_manual_activate.py`: 5 passed, including valid-pair path
  substitution refusal and VALID-EMPTY postcondition.
- `test_h7_schwab_window_registration.py`: 10 passed.
- `git diff --check 5648b29..7cf667f`: passed.
- Candidate-scoped Monday grep: no matches.

## Unsupported assumptions / limits

- No real Restic repository or real Schwab canary was exercised; those belong
  to later tasks.
- No real filesystem race or hostile symlink manipulation was attempted; the
  deterministic regression exercises the relevant path-substitution state
  transition directly.
- This review did not authorize registration or activation.
