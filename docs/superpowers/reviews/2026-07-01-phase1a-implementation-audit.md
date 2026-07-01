# Phase 1A Implementation Audit

**Date:** 2026-07-01
**Branch observed:** `phase-1a-research-integrity`
**Reviewed state:** through `0ef6a85` plus the uncommitted ledger/source,
spec/plan, and handoff-hardening patch in this audit.

## Scope

Audited the current Phase 1A implementation against:

- `docs/superpowers/specs/2026-07-01-research-integrity-foundation-design.md`
- `docs/superpowers/plans/2026-07-01-research-integrity-foundation.md`
- `docs/superpowers/handoff-2026-07-01-phase1a.md`
- Current implementation in `config.py`, `research/hashing.py`,
  `research/ledger.py`, `research/windows.py`, and
  `tests/test_research_integrity.py`

## Fixes Applied Now

### Ledger append must refuse compromised state

`research.ledger.append()` now verifies the existing ledger chain before adding
a new record. This prevents the system from building new valid-looking records
on top of an already broken or mismatched `HEAD` chain.
The implementation plan now includes the same test and code path, so a future
executor cannot reintroduce the old append behavior by following stale snippets.

### Malformed ledger JSON is an integrity failure, not a parser crash

`research.ledger.read_all()` now wraps `json.JSONDecodeError` in `LedgerError`
with the bad ledger line number. This keeps `verify` and the future CLI verify
path on the same integrity-error contract even when a ledger line is corrupted
into invalid JSON.

### Ledger metadata fields are reserved

`append()` now rejects caller bodies containing `seq`, `prev_hash`, or
`record_hash`. Without this, a caller-supplied `record_hash` key could be present
during hash calculation and produce a record that `verify()` would later reject.
The ledger should fail before writing that record.

### Test hygiene

The tamper tests now use `Path.read_text()` / `write_text()` instead of raw
`open()` calls that emitted `ResourceWarning`.

### Anchored git checks are repo-root scoped

The default anchored ledger checker now runs git with `-C REPO_ROOT`, so it does
not depend on the caller's current working directory. A new anchoring test
temporarily points `ledger.REPO_ROOT` at a temp git repo and verifies the default
checker from outside that repo.

The planned `experiments._code_sha()` helper now uses
`git -C hashing.REPO_ROOT rev-parse HEAD` for the same reason; `code_sha` is only
an audit field, but it still should not depend on the shell's current directory.

### Canonical JSON rejects non-finite values

`research.hashing.canonical_json()` now uses `allow_nan=False`, so hash surfaces
cannot silently serialize `NaN`/`Infinity` tokens that are not strict JSON.
The implementation plan now includes this test, plus the default-root
`config.py` source-surface test, so the plan and live test suite are aligned.

### Source hash added for hypothesis drift enforcement

`research.hashing.source_hash()` now hashes the verdict/backtest source surface
separately from `git rev-parse HEAD`. The spec and implementation plan now
require `register()` to store `source_hash` and `reveal_oos()` to refuse when
`config_hash`, `cost_model_hash`, or `source_hash` drift from the registered
values.

### Registration must start from recoverable source

The spec and implementation plan now require `register()` to refuse dirty,
deleted, untracked, or ignored files in the source-hash surface before writing a
run record. A registered hash of uncommitted code is not recoverable from git
later, so this guard belongs at registration time, not only at OOS reveal time.
The planned `_source_paths()` helper is scoped to explicit lock/config files plus
Python files under the source directories. That keeps future cached market-data
artifacts out of the source-clean gate; market-data content belongs in
`data_window_hash`.

### Dependency lock surface included in source hash

`source_hash()` now includes `pyproject.toml` and `uv.lock`, not only `.py`
source. A dependency/runtime change between registration and OOS reveal can
change the verdict machinery, so it belongs in the registered execution surface.

### OOS trades must match the registered OOS window

`research.windows.assert_within_window()` now rejects trades outside the
registered `[start, end]` window. The spec and plan now require `reveal_oos()` to
check this in addition to the global `IN_SAMPLE_END` boundary, so a reveal cannot
quietly use a different post-2022 subset.

### Duplicate hypothesis IDs must be refused

The spec and plan now require `register()` to reject a duplicate `hypothesis_id`.
Reusing an ID would make the write-once OOS rule ambiguous and could hide a
second pre-registration behind the same label.

### Risk-basis must be an enum, not free text

The spec and plan now require `register()` to reject unknown `risk_basis` values.
The only allowed values are `capital_at_risk` and `economic_max_loss`; a typo
would make the ledger record hard to interpret and would weaken the risk-basis
amendment.

### Registration must reject malformed preregistration metadata

The spec and plan now require `register()` to reject empty `hypothesis_id`, empty
`decision_threshold`, and malformed `data_window` objects. A preregistration that
records `is_window: null` or `oos_window: null` would turn the OOS boundary into
a runtime accident instead of a ledger commitment, so the future Task 6 snippet
now validates both `is_window` and `oos_window` before appending a run record.

### Bootstrap implementation plan corrected before execution

Task 12's independent-data assertion now matches the spec (`lo < sample mean <
hi`, not merely `lo < hi`). Task 13's expected failing-test note now describes
the real pre-implementation failure mode: the two-cohort all-loss sample returns
a verdict instead of `INSUFFICIENT SAMPLE` because the cohort guard is absent.
The demo snippet also now computes the 2020-01-06 ordinal directly instead of
using a wrong literal.

### OOS reveal must append, not mutate

The spec now explicitly says the original `run` record remains immutable with
`oos_result: null`, and a successful reveal appends a separate `oos_reveal`
record containing the result and look-budget metadata. That resolves the
append-only ledger semantics before Task 7 is implemented.

### CLI seams must include register and reveal-oos

The implementation plan's CLI task now creates distinct `register` and
`reveal-oos` subcommands in addition to `verify` and `trial-log`. The original
plan advertised those seams in the usage string but only implemented two
commands. The tamper test also now uses `Path.read_text()` / `write_text()` so it
does not truncate the file before reading or leak handles. `--ledger` is defined
on each subcommand, matching the planned command shape (`trial-log ... --ledger
...`) instead of relying on argparse top-level option ordering.

### Handoff updated to the reconciled spec

`docs/superpowers/handoff-2026-07-01-phase1a.md` no longer tells a fresh session
to build hooks in Phase 1A or to use the older stationary/entry-date-cohort
bootstrap framing. It now points to the current reconciled spec, plan, and audit
notes; states threat model C/no hooks for 1A; fixes the look budget to 3; and
describes the weekly-cohort block primary plus stationary cross-check.

The external `.claude` memory file
`phase-1a-research-integrity.md` still contains stale pre-reconciliation language
about hooks and entry-date cohorts. I did not edit files outside the repo; the
in-repo handoff now explicitly says the reconciled spec/plan/audit supersede the
rough memory guidance anywhere they differ.

### Commit checkpoints made conditional

The implementation plan no longer tells agents to commit after each task by
default. The `git add` / `git commit` blocks remain as optional checkpoints for a
user-approved committing run, but the default is to implement and verify without
writing git history.

The plan also no longer claims the spec is already committed at a fixed SHA; it
points implementers to the current worktree and tells them to check `git status`
before assuming commit state.

## Verification

- `uv run python -m unittest tests.test_research_integrity -v`
  - 32 tests passed.
- `uv run python -m unittest discover -s tests -v`
  - 44 tests passed.
- `git diff --check`
  - clean.

## Findings For The Next Implementation Step

### Task 5 window split reviewed

Task 5 is committed in `0ef6a85`:

- `research/windows.py`
- `tests/test_research_integrity.py` imports `research.windows` and includes
  `WindowTests`

Quick review: the logic correctly keys on entry date and treats
`entry <= IN_SAMPLE_END` as in-sample and strictly later entries as OOS. The
full suite passes with this committed file present.

### P0 — Verify OOS reveal guards full hypothesis drift when Task 7 lands

The plan has been patched so `research.experiments.register()` must refuse dirty,
deleted, untracked, or ignored source-hash files, and
`research.experiments.reveal_oos()` must check `config_hash`,
`cost_model_hash`, and `source_hash` drift, plus exact registered OOS-window
membership. When Tasks 6 and 7 land, review the actual implementation and tests
to ensure those checks are present.
Without them, a strategy change between registration and OOS reveal could slip
through as long as cost/fill constants stayed unchanged. Examples:

- `A_SHORT_PUT_DELTA` changes.
- `A_SPREAD_WIDTH` changes.
- exit logic changes in `strategies/put_credit_spread.py`.
- verdict logic changes in `metrics.py`.

This would violate the pre-registration guarantee: the OOS result would no
longer correspond to the registered hypothesis.

Do **not** enforce exact `git rev-parse HEAD` equality: each ledger append is
supposed to be committed, so the commit SHA naturally changes when the ledger is
anchored even if research code is unchanged.

### P1 — Clarify anchoring semantics

`ledger.verify(..., anchored=True)` currently proves the ledger files are
tracked and clean, not that the entire research worktree is clean. That is fine
for a ledger verifier, but insufficient as the only OOS reveal protection.

Recommended split:

- `ledger.verify(anchored=True)` owns ledger integrity.
- `reveal_oos()` owns research-state integrity via `config_hash`,
  `cost_model_hash`, and `source_hash`.

## Current Status

Current implemented slice is green and stronger after the ledger/source-hash
patch. The P0 drift guard, append-only reveal semantics, CLI seams, conditional
commit policy, and current handoff are reflected in the spec and plan; when
Tasks 6-8 land, verify the actual implementations and tests enforce them.
