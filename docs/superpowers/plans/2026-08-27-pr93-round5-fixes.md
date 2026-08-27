# PR 93 Round-5 Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every blocking Round-5 finding while preserving the tracker’s causal, append-only, fail-soft, and no-authority contracts.

**Architecture:** Keep the evaluator’s two time boundaries explicit: coverage validation runs only for covered lanes, current holdings observations are stamped from the machine-derived New York date, and evaluation session S consumes only observations dated on or before S. Carry source-row identity alongside the pure render result so the published HTML marker comes from the exact render-side selection, while snapshot validation continues to recompute snapshot rows, the HTML digest, the HTML hash, and `render_id` independently.

**Tech Stack:** Python 3.12, pandas, `unittest`, zsh ritual wrapper, ruff, pyright.

**Spec:** `reports/2026-08-27-pr93-round4-independent-review.md` at review commit `77ff464`

## Global Constraints

- PR #93 remains draft; no readiness, merge-to-main, deployment, ops sync, registration, ledger write, or scored-write authority.
- NEW-4 final form: live holdings observations use only the machine-derived current New York date, never `as_of` or caller input; evaluation session S consumes only observations dated `<= S`.
- The HTML source-row digest must originate from the render-side candidates, not from the snapshot payload.
- Probe A, R1, P1-b, N2, N3, N5, N6, N7, and the accepted N4 behavior must not regress.
- Final full-suite acceptance requires exit 0.

---

### Task 1: Evaluator coverage and live-session causality

**Files:**
- Modify: `tests/test_pick_tracker.py`
- Modify: `options_researcher/pick_tracker.py`

**Interfaces:**
- Consumes: `evaluate_cli(as_of)`, `_CausalCoverageValidator`, `evaluate_records(...)`.
- Produces: covered-lane-only validator calls, machine-dated live observations, causal consumption by evaluation date, and `LIVE_HOLDINGS_OBSERVATION_SESSION_MISMATCH` at the write boundary.

- [x] **Step 1: Write failing evaluator regressions**

Add real-CLI tests for a `long_call` record using `_CausalCoverageValidator`, the scheduled prior-completed-session shape, a fresh backdated tracker, a tracker whose newest artifact leaves a date gap, and a forged non-machine observation date.

- [x] **Step 2: Verify RED**

Run the tracker suite with `uv run python -m unittest discover`; expect the non-covered lane to raise `PositionSchemaError`, the obsolete equality guard to reject all three prior-session shapes, and the writer to accept the forged observation date.

- [x] **Step 3: Implement the minimal evaluator changes**

Call `coverage_validator` in `resolve_fill` only when `lane in {"cc", "pmcc"}`. Derive the live observation date inside `_CausalCoverageValidator`, filter observations by `observed_session <= evaluated session`, and independently require the machine date at `_write_evaluation_reports` with `LIVE_HOLDINGS_OBSERVATION_SESSION_MISMATCH` on mismatch.

- [x] **Step 4: Verify GREEN**

Run the new tests and the complete `test_pick_tracker.py` suite; expect exit 0.

### Task 2: Render-side source binding and render-id isolation

**Files:**
- Modify: `tests/test_attractiveness_dashboard.py`
- Modify: `tests/test_pick_tracker.py`
- Modify: `options_researcher/attractiveness_dashboard.py`

**Interfaces:**
- Consumes: `_render_result(...)`, `DashboardRenderResult`, `_write_dashboard_result(...)`, `validate_snapshot(...)`.
- Produces: immutable `render_source_row_hashes` captured during rendering and used exclusively for the HTML digest marker.

- [x] **Step 1: Write failing A3 and render-id regressions**

Publish a render result whose HTML/render-side hashes describe dataset X but whose copied snapshot describes dataset Y, then assert `validate_snapshot` raises `SNAPSHOT_HTML_SOURCE_MISMATCH`. Separately mutate only `render_id` on an otherwise valid payload and assert `SNAPSHOT_RENDER_ID_MISMATCH`.

- [x] **Step 2: Verify RED**

Run both named tests; expect A3 to be accepted by the current producer and the render-id isolation test to pass only after it is added as an independent guard.

- [x] **Step 3: Implement the minimal producer binding**

Add `render_source_row_hashes` to `DashboardRenderResult`, derive it from the selection assembled inside `_render_result`, and bind the HTML marker from that field. Continue deriving the snapshot’s `source_row_hashes` and `source_rows_sha256` from its own copied payload so X/Y disagreement survives to validator comparison.

- [x] **Step 4: Verify GREEN and non-regression**

Run the new tests, Probe A, R1, and the complete dashboard and tracker suites; expect exit 0.

### Task 3: Ritual fail-soft contract

**Files:**
- Modify: `tests/test_daily_ritual_provenance.py`

**Interfaces:**
- Consumes: the real evaluator shell line from `tools/daily_ritual.sh`.
- Produces: an execution assertion that evaluator failure returns 0 and a structural assertion that failure handling is on the non-propagating `if/elif/else` branch.

- [x] **Step 1: Strengthen the execution and structural assertions**

Assert `completed.returncode == 0` in the conflict execution test and pin the evaluator line’s `if ...; then ...; elif ...; then ...; else ...; fi` structure in the existing fail-soft placement test.

- [x] **Step 2: Verify the structural sensitivity and GREEN state**

Run the full ritual-provenance suite and expect exit 0. The workspace safety layer refused a temporary fail-hard edit to the operational ritual; retain the direct return-code assertion and structural prohibition on an `exit` in the branch.

### Task 4: Acceptance, diff review, and receipt

**Files:**
- Modify: `reports/2026-08-27-pr93-round5-receipt.md`

**Interfaces:**
- Consumes: focused test output, full-suite output, ruff, pyright, and final git diff.
- Produces: exact implementation evidence without readiness or landing claims.

- [x] **Step 1: Run focused acceptance**

Run tracker, dashboard, ritual-provenance, and shell-banner suites; all must exit 0.

- [x] **Step 2: Run repository acceptance**

Run `uv run python -m unittest discover -s tests`, `uv run ruff check .`, `uv run ruff format --check` on changed Python files, and `uv run pyright`; all must exit 0.

- [x] **Step 3: Review the final diff**

Inspect behavior, failure paths, causality, provenance, compatibility, and unrelated changes. Perform at most one correction pass if a concrete issue is found.

- [x] **Step 4: Record the evidence receipt**

Write exact commands, counts, exits, finding dispositions, remaining boundaries, and the unchanged draft/no-authority state.
