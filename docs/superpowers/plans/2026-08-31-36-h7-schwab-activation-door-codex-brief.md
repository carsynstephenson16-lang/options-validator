# Brief 36 — H7 Schwab activation door, rebuilt on main

**Date:** 2026-08-31
**Author:** Claude orchestrating session (PR #71 unfreeze arc; plan:
`docs/superpowers/plans/2026-08-30-pr71-unfreeze-pr115-closeout.md`)
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** DRAFT — pending independent adversarial review before hand-off
**Provenance:** Repo-verified against `origin/main` @ `1d83453` unless labeled
otherwise.

## Why this exists (plain language)

PR #71 (`codex/h7-schwab-recovery`, closed 2026-08-31 per owner ruling 2) built
the owner-confirmed command that performs the real H7 Schwab window
registration, but it froze 2026-08-11 and main superseded its foundations. The
owner has now given the final go on registering the bar-7 V0 forward window
(ruling 1, `reports/2026-08-31-owner-rulings-h7-unfreeze.md`), so the missing
piece is a trustworthy activation door built on TODAY's main. This brief also
closes three recorded findings:

- **Codex-bot P1** (PR #71 review, 2026-08-24, on `_validate_feasibility`):
  "Bind feasibility to the measured input bytes" — the validator never rehashes
  the measurement inputs, so a stale qualifying receipt could register a window
  against data that no longer matches what produced it.
- **Codex-bot P2** (same review, misanchored at the CLI; actual defect
  Repo-verified in the BUILDERS on main): `bool(evidence["darwin_durability_verified"])`
  at `options_researcher/h7_schwab_window_registration.py:391` AND
  `options_researcher/h7_window_registration.py:243` records the string
  `"false"` as `true`. This is live today; the second module built the existing
  seq-0 registration.
- **Brief 32 round-3 finding F2** (quoted in packet row 7): a caller of
  `h7_schwab_data_gate.evaluate()` does NOT satisfy the quote-age obligation —
  a real blocking gate with the owner-typed threshold is required.

## Scope

**IN:**
- `options_researcher/h7_schwab_window_registration.py` (validator + builder)
- `options_researcher/h7_window_registration.py` (builder coercion fix only)
- NEW `tools/h7_schwab_manual_activate.py` + NEW `tests/test_h7_schwab_manual_activate.py`
- NEW quote-age gate module or function co-located per WP-E, + `config.py`
  constant with owner-typed provenance
- Tests for every WP; updates to `tests/test_h7_schwab_window_registration.py`

**OUT (executor over-reach stops here):**
- NO ledger writes, NO execution of any registration, NO appending to
  `ledger/h7_forward/*` in any test against the real store (temp stores only).
- NO authority flips, NO live-order paths, NO paper-mode changes.
- NO changes to frozen values; NO new numbers not already owner-typed — the
  quote-age threshold's single source of truth is ruling 3 of
  `reports/2026-08-31-owner-rulings-h7-unfreeze.md`; the loss bar is an
  owner-typed registration field, never a config lookup.
- NO `owner_fields` parameter (or any caller-supplied field-list) on
  `options_researcher/h7_activation_guard.py` — the module-constant check at
  `h7_activation_guard.py:197` is the sole owner-input backstop and stays
  non-parameterized (Repo-verified; PR #71's version of this change was
  classified guardrail-loosening and explicitly not ported).
- NO copying code from the deleted `codex/h7-schwab-recovery` branch; rebuild
  against main (the branch's salvage map is in PR #71's close comment).
- The implementation PR starts and stays a GitHub draft; green checks are
  review evidence, not landing authority.

## Work packages

### WP-A — Validator input binding (closes Codex-bot P1)

`_validate_feasibility` (`options_researcher/h7_schwab_window_registration.py:111`)
currently validates the receipt's self-hash, kind, provenance, and arithmetic
only (Repo-verified @1d83453). Extend it to:

1. Require the receipt to carry per-input content hashes and canonical data
   paths. The preserved receipt
   `reports/h7_forward_schwab/2026-08-11-feasibility-primary-earnings.json`
   (fields incl. `canonical_data_paths`, per-input sha256, `config_hash`,
   `code_sha`, `error_count`) is the reference shape (Repo-verified — on main
   via PR #137).
2. At validation time, recompute the sha256 of each listed input file and
   refuse with a distinct error on any mismatch or missing file.
3. Bind `config_hash` to the current computed config hash, require
   `error_count == 0`, and require the canonical 9-name cohort universe and the
   stack/tool identity labels to match the registered scope.

Acceptance tests (names indicative, one per refusal path): stale-input-hash
refusal, missing-input-file refusal, config-drift refusal, nonzero-error-count
refusal, wrong-universe refusal, happy path with a fixture receipt whose
hashes are computed from fixture files.

### WP-B — Feasibility gate in its owner-ruled form

Enforce the 2026-07-24 registration feasibility gate exactly as `.cursorrules`
states it (Repo-verified): registration is valid only if
`expected_entries >= 2 × (owner-typed loss bar)` **OR** the registration
carries a present, non-empty, owner-typed starvation pre-acceptance field that
quotes the computed `expected_entries`. Constraints:

- The loss bar is read from the owner-typed registration fields (bar 7 for
  this window — Official-source: owner ruling 2026-08-14,
  `reports/2026-08-14-owner-answers-decision-menu.md`). `config.MIN_LOSSES_FOR_VERDICT`
  (`config.py:184`) and `H10_MIN_LOSSES_FOR_VERDICT` (`config.py:612`) must
  not appear in this gate.
- A blank or missing pre-acceptance combined with a failing bar REFUSES. A
  pre-acceptance that does not quote the computed `expected_entries` value
  REFUSES (prevents rubber-stamp text).

Acceptance tests: bar-met path; bar-failed + valid pre-acceptance path
(expected for this window: 4.0 < 14, pre-acceptance quoting 4.0); bar-failed +
blank pre-acceptance refusal; pre-acceptance-without-quoted-number refusal.

### WP-C — Owner-confirmed activation CLI (rebuild)

NEW `tools/h7_schwab_manual_activate.py`: an operator CLI that assembles the
registration evidence and delegates to `register_window_real`
(`options_researcher/h7_schwab_window_registration.py:436`) — the sole real
append door. Requirements:

- The owner types the confirmation string and every owner field at use time,
  including the OD-3 namespace line; the CLI defaults NONE of them and refuses
  blanks (the `h7_activation_guard` module-constant check must be exercised,
  not bypassed).
- No direct append: the existing one-door AST protection in
  `tests/test_h7_one_door.py` must still pass and must cover the new CLI.
- Evidence revalidation before delegation: source-health, data-gate, backup +
  restore receipts, WP-A's input-hash validation, WP-B's gate, WP-D's strict
  durability check, and WP-E's quote-age gate.
- Tests run only against temporary stores; the CLI must hard-refuse if pointed
  at the real store without the owner confirmation string.

### WP-D — Durability-evidence coercion fix ON MAIN (live defect; land first)

In BOTH builders — `options_researcher/h7_schwab_window_registration.py:391`
and `options_researcher/h7_window_registration.py:243` — replace
`bool(evidence["darwin_durability_verified"])` with a strict check that only
the JSON boolean `true` passes (`evidence["darwin_durability_verified"] is True`),
plus a validation-layer type assertion (extend `_require` at
`h7_schwab_window_registration.py:92` or add a typed check beside it) so a
non-boolean value refuses with a clear error before building the event.

Acceptance tests (regression, both modules): `"false"` refuses, `"true"`
refuses, `0` refuses, `1` refuses, `None` refuses, `True` passes, `False`
refuses-with-unverified-error. This WP touches the module behind the live
seq-0 registration; it changes REFUSAL behavior only and must not alter any
existing event or replay path (prove with the existing suite untouched-green).
Deliver WP-D as the first commit so it is independently cherry-pickable.

### WP-E — Quote-age blocking gate (closes F2; owner-typed threshold exists)

Implement the blocking gate the registration commitment requires (packet row
7). Requirements:

- Add the config constant for the threshold with provenance comment citing
  ruling 3 of `reports/2026-08-31-owner-rulings-h7-unfreeze.md` (owner-typed
  2026-08-31: quotes older than 1 hour block). Do not restate the number in
  strategy logic; read it from `config.py` per the no-magic-numbers rule.
- The gate consumes the worst SELECTABLE quote age from the merged quote-age
  sidecar lane (`options_researcher/schwab_quote_age_report.py`, PR #131) for
  the session being armed; if the sidecar report for that session is missing
  or unparseable, the gate FAILS CLOSED (refuses to arm) — silence is never a
  pass.
- Per amendment v1.4 precedent, a name exceeding the threshold is entry-banned
  per-name; the gate emits a visible per-name verdict, not a silent skip.
- A bare call to `h7_schwab_data_gate.evaluate()` (`options_researcher/h7_schwab_data_gate.py:134`)
  without the quote-age check does NOT satisfy this WP (finding F2, verbatim
  constraint).

Acceptance tests: over-threshold name banned; under-threshold passes; missing
sidecar report fails closed; threshold read from config (test asserts the
constant is the single source).

### WP-F — Test alignment

Extend `tests/test_h7_schwab_window_registration.py` against main's current
file for WP-A/B/D; new `tests/test_h7_schwab_manual_activate.py` for WP-C;
gate tests for WP-E. All tests offline (unittest, no network, no provider
calls), per repo policy.

## Acceptance / verification

Done is defined by exit codes at the implementation head:

```
uv run python -m unittest discover -s tests   # exit 0
uv run ruff check .                            # exit 0
uv run pyright                                 # exit 0
```

plus: every refusal path named in WP-A/B/D/E has a test that FAILED before its
implementation commit and passes after (red-green evidence recorded in the PR
description); `tests/test_h7_one_door.py` still passes and covers the new CLI;
no diff outside the Scope-IN file list. The implementation PR is a GitHub
draft; hand-off ends there — merge timing, registration execution, and every
owner field remain with the owner.
