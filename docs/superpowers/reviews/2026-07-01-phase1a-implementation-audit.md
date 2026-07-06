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

---

## Final Branch Review Pass

**Observed HEAD:** `e86b79b` plus the Codex post-review patch in this working
tree. Tasks 9-16 are implemented on `phase-1a-research-integrity`.

### Fix-now — CLI reveal must use the harness seam

`research.cli reveal-oos` had its own local unwired closure instead of delegating
to `harness.run_backtest.reveal_out_of_sample()`. That created two OOS entry
points that could drift when ThetaData is wired. The CLI now delegates to the
harness seam, and tests pin that delegation.

### Fix-now — CLI commands should fail cleanly on ledger errors

`register` and `reveal-oos` could surface `LedgerError` as a traceback in some
corruption/dirty-ledger paths. The CLI now catches `LedgerError` and returns a
nonzero status with a gate/refusal message, matching `verify` and `trial-log`.

### Fix-now — trial intents need a reason

`log_trial_intent()` now rejects an empty `reason`. The monotonic counter is only
useful if each non-run trial leaves an audit rationale; blank intent rows weaken
the multiple-testing audit trail.

### Fix-now — economic max-loss diagnostic must be real if present

The risk-basis amendment says `capital_at_risk` remains the headline denominator
but `economic_max_loss` must be reported as a secondary diagnostic. `metrics.py`
now reports `return_on_economic_max_loss` when every trade supplies a valid
`economic_max_loss`, rejects partial economic-risk data, and rejects any
`economic_max_loss < capital_at_risk`. The verdict remains driven only by the
PnL expectancy CI.

### Fix-now — cohort granularity must fail closed

`COHORT_GRANULARITY` is frozen and hashed as `"week"`. The cohort builder now
raises if that config label is changed without corresponding implementation
support, instead of silently running weekly cohorts under a different label.

### Fix-now — economic max-loss sizing must be executable, not only documented

The spec correctly separated `capital_at_risk` from `economic_max_loss`, but the
strategy sizing path still needed the actual enforcement before any real
ThetaData run. `size_defined_risk()` now gates on economic max loss, impossible
vertical credits fail closed, the feasibility report uses the same shared
economic-risk helper, and the $2-wide zero-slack case is tested: $140 broker
margin plus $2.60 round-trip commission is $142.60, so a $140 budget fits 0
contracts.

### Fix-now — OOS data-contract failures must surface as gate refusals

`reveal_oos()` wrapped missing `entry_date` as `OOSGateError`, but raw window
validation failures and scoreboard contract failures could escape as `ValueError`.
That would bypass the CLI's gate-refusal handling exactly when a bad OOS run
returned leaked dates or malformed trades. The OOS reveal boundary now wraps
window-validation and scoreboard `ValueError`s as `OOSGateError`, and tests pin
in-sample leaks, outside-window trades, and missing-symbol OOS trades.

### Fix-now — reveal must verify ledger structure before trusting run fields

`reveal_oos()` previously read the ledger and dereferenced registered-run fields
before asking the ledger verifier to recompute the chain. A malformed or tampered
run record could therefore escape as a raw `KeyError` before the intended
`LedgerError`/`OOSGateError` boundary. The reveal path now verifies the chain
before trusting records and explicitly refuses a valid chain with missing required
run fields.

### Fix-now — trial counts must be verified, not only written

The spec says the trial counter is monotonic and stored in the chained ledger, but
`ledger.verify()` only checked hashes, sequence numbers, and `HEAD`. A hash-valid
manual row could reset or misstate `trial_count` while still passing verify. The
ledger now fills or validates the expected counter on append and recomputes the
counter during verify, including the "reveal does not increment" rule.

### Fix-now — reveal records must be semantically possible

The hash chain alone allowed a hash-valid `oos_reveal` with no registered run, a
duplicate reveal for the same hypothesis, or incorrect look-budget metadata. Those
states contradict the write-once OOS contract even if the bytes hash correctly.
`ledger.verify()` now validates run identity, trial-intent rationale, reveal
run-id matching, reveal uniqueness, and monotonic `budget_used` / stable
`budget_total` semantics; `ledger.append()` refuses the same impossible records
before writing them.

### Fix-now — run records must satisfy the pre-registration schema

The spec's run record has a real schema: non-empty identity, threshold, source /
config / cost / data-window hashes, risk basis, explicit IS/OOS windows, null
OOS/Phase-1B fields, and notes. `ledger.verify()` now rejects hash-valid run
records missing that preregistration metadata and rejects duplicate `run_id`
values, so `verify` cannot bless a ledger that would only fail later during
reveal.

### Fix-now — ledger records must not hide behind unknown types

`ledger.verify()` accepted hash-valid records with an unrecognized `entry_type`,
which would let a hand-edited row sit outside both the trial counter and the OOS
budget semantics. The ledger now has a closed Phase-1A record taxonomy
(`trial_intent`, `run`, `oos_reveal`) and rejects unknown types on both append
and verify. The same pass tightened run-window verification: `is_window` and
`oos_window` must contain parseable ISO start/end bounds with `start <= end`, not
merely be JSON objects.

### Fix-now — intent and reveal records need complete audit payloads

The semantic verifier still allowed a `trial_intent` without a timestamp and an
`oos_reveal` without an `oos_result` object. That left the ledger capable of
counting an intent without a usable audit time, or spending a write-once reveal
without recording the OOS scoreboard payload. `ledger.verify()` and
`ledger.append()` now require timestamps on intents/reveals and require
`oos_result` to be an object on reveal records.

### Notes-later — failed OOS attempts need a data-path-aware budget rule

`reveal_oos()` currently spends the look budget only after the injected OOS
runner returns trades and the result is scored. Charging every exception would
be too blunt in Phase 1A because the injected function cannot tell the gate
whether it failed before or after touching holdout data. When ThetaData is wired,
the data seam should expose "post-2022 data opened" as an auditable event, so a
failure after touching the holdout consumes or records a look while pre-data
infrastructure failures do not.

### Fix-now — smoke tests must not peek at the OOS window

`smoke_test.py` is outside the verdict source hash by design, but it still opens
market data once ThetaData is wired. It previously hardcoded `2024-01-31`, which
is inside the post-2022 holdout and would create an unbudgeted OOS peek under the
guise of an environment check. The smoke probe now uses `2022-12-30`, the last
trading day before `IN_SAMPLE_END`, and a test pins `SMOKE_TEST_DATE <=
IN_SAMPLE_END`.

### Fix-now — loss counts must come from realized PnL, not caller flags

`scoreboard()` accepted an optional `is_win` flag and computed losses as
`not is_win`. That let malformed extraction data classify positive-PnL trades as
losses, satisfying the minimum-loss verdict floor without actual negative trades;
it also counted flat `pnl == 0` trades as losses. The scoreboard now derives
wins/losses from net realized PnL only (`pnl > 0` / `pnl < 0`), treats flats as
neither, and rejects any supplied `is_win` flag that contradicts the PnL sign.

### Fix-now — conservative credit must actually cross the spread

`HALF_SPREAD_COST` was frozen and hashed, but `entry_credit_conservative()` still
used a near-mid fill with a small haircut. That overstated credit on option
spreads and could admit trades that only fit under optimistic fills. The helper
now fills the short leg at bid and the long leg at ask when `HALF_SPREAD_COST` is
enabled, then applies the adverse `SLIPPAGE_HAIRCUT` on top. Invalid/crossed
quotes raise instead of producing a credit.
`FILL_MODEL_ID` was bumped to `conservative_bid_ask_plus_haircut_v1` so future
ledger records identify the changed fill logic.

### Fix-now — cached chain data must fail closed at the adapter boundary

`get_eod_chain()` returned cached parquet without validating the cache key or
chain schema. A malformed cache file could therefore reach strategy logic missing
load-bearing fields like `delta`, or a malformed symbol/date could produce unsafe
cache paths. The adapter now normalizes safe symbols, requires ISO dates, and
validates cached chains for required columns, valid option rights, and finite
numeric fields before returning them.

### Fix-now — ledger schemas and timestamps must be exact

The semantic verifier required timestamp fields but accepted any non-empty string,
and it allowed arbitrary extra top-level fields on otherwise valid record types.
That made the ledger less auditable than its closed Phase-1A taxonomy implied:
manual records could carry invalid audit times or ambiguous unversioned payload.
`ledger.verify()` and `ledger.append()` now require timezone-aware ISO timestamps
and reject unknown fields for `trial_intent`, `run`, and `oos_reveal` records.

### Fix-now — registration identity must be canonical before hashing

`register()` rejected empty hypothesis IDs but did not normalize non-empty text
before the duplicate check and ledger write. That left `"H1"` and `" H1 "` as two
hash-valid hypothesis IDs, weakening the single-use ID and write-once reveal
contract. Registration, reveal, and trial-intent logging now trim identity fields
before storage/lookup, reject blank `run_id`, require `notes` to be text, and
require `is_result` to be a scoreboard object instead of letting malformed payloads
fall through to lower-level ledger errors. The ledger verifier now independently
rejects hash-valid records with untrimmed identity/audit strings, so a direct
`ledger.append()` or hand-rehashed JSONL row cannot reintroduce the whitespace-ID
bypass.

### Fix-now — frozen hashes must be real digests

The semantic verifier accepted non-empty strings for `config_hash`,
`cost_model_hash`, `source_hash`, and `data_window_hash`. A manually constructed
record could therefore carry `source_hash: "source-hash"` and still verify after
the row bytes were rehashed. Those fields are now validated as 64-character
lowercase SHA-256 hex digests, and tests cover both append-time rejection and
hash-valid tampered-row rejection.

### Fix-now — code SHA must be reconstructable provenance

`code_sha` is intentionally audit-only, not the reveal-time drift guard, but it
still needs to identify a real code state. The gate and ledger verifier now reject
abbreviated or fake values such as `deadbeef`; `_code_sha()` fails closed if
`git rev-parse HEAD` cannot produce a full Git object hash.

### Fix-now — ledger windows must be chronologically disjoint

`register()` refused OOS windows that overlapped the in-sample boundary, but a
direct ledger row could still declare overlapping `is_window` / `oos_window`
objects and pass semantic verification if the hash chain was recomputed. The
ledger verifier now requires `is_window.end < oos_window.start` on every run
record. The verdict input contract was also tightened so `symbol` must be a
non-empty string, not merely any truthy value.

### Final verification

- `uv run python -m unittest discover -s tests -v`
  - 147 tests passed.
- `uv run python -m research.cli verify`
  - `ledger OK`.
- `uv run python metrics.py`
  - demo prints the expected `INSUFFICIENT SAMPLE (6 losses; need >= 10)` verdict.
- `uv run python analysis/feasibility.py`
  - feasibility table now uses economic max loss and shows the $14k sleeve /
    $2-wide zero-slack case fits 0 contracts.
- `uv sync --locked --check`
  - `Would make no changes`.
- `git diff --check`
  - clean.
- `git check-ignore ledger/README.md`
  - exit 1 with no output, so `ledger/` is not ignored.
