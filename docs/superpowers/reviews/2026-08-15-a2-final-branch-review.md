# A2 final branch review — 2026-08-15

**Scope:** final independent, read-only review of `58701e9..620dd49` for the
research-only A2-v1 outcome battery. This receipt neither authorizes a run nor
changes any data, ledger, report, or implementation state.

## Verdict: NEEDS REPAIR — historical execution remains prohibited

Two semantic findings prevent a governed A2 historical invocation, independent
of the already-recorded selected-contract data block.

1. **Breach-defensive CSP arm is not distinct (High).**
   `options_researcher/a2_panel.py` resolves `breach_hold_21_dte` at the same
   `close21` date and by the same resolver as `close_21_dte`. It neither
   detects nor records a breach. That contradicts A2-v1 sequence 19 and the
   entry-convention addendum, which define a distinct arm: breach, then hold to
   21 DTE, then mechanically close. The governing records do not pin a precise
   breach trigger, so the repair must not invent a threshold; it must either
   obtain a governed definition or fail closed for that arm.

2. **Inference cadence differs from registration (High).**
   Sequence 19 calls for weekly non-overlapping inference cohorts. The current
   `non_overlapping_inference_rows` greedily accepts the earliest available
   daily cohort after the previous cohort resolves, with no weekly anchor or
   cadence validation. That can change which observations enter the primary
   top-minus-bottom statistic. The later implementation plan's greedy wording
   cannot override the append-only registration; establish a valid superseding
   owner record or implement/refuse the registered weekly schedule.

## Current controlled state

- The programmatic selected-contract audit is **BLOCKED** on exact CRWV
  implied-volatility defects (21 zero-IV rows and two rows above 500 percent),
  as recorded in `reports/2026-08-15-a2-options-data-audit.md`. This remains an
  independent no-go; no selective exclusion or IV reconstruction is allowed.
- `reports/a2/a2-v1.json` is absent.
- `ledger/experiments.jsonl` contains zero `retrospective_result` records for
  `A2-v1`.
- The runner's report/result write path was not invoked by this review.

## Validation evidence

- A2-targeted tests previously passed: 72 tests.
- Full-suite evidence at commit `d9f27f1`: 3,130 tests OK, 5 skipped.
- The targeted Pyright errors identified during review were repaired in
  `ba50b37`; the scoped formatting failures were repaired in `620dd49`.
- Final full-suite, lint, formatting, type, and focused semantic tests must be
  rerun after any repair to either high-severity finding. No prior green result
  validates a changed breach rule or cohort schedule.

## Required next action

Resolve both semantic findings under the registration boundary, then rerun the
programmatic audit. Any audit `BLOCK` continues to prohibit the one-shot
historical command.
