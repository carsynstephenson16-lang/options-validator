# PR #93 Fix-Round Receipt — 2026-08-27

## Scope and provenance

- Controller finding source: `.superpowers/sdd/2026-08-26-audit-closeout-handoff-package/progress.md`, A6 independent bounded review, `FAIL / NOT READY` at `58779390528719ed6c8447c9b8f1aad0ede741ce`.
- Branch: `codex/brief27-implementation`.
- Current `origin/main` merged without rebasing: `c1b5bf06e373ddb62af1037e6e73832c7079a0af`.
- Exact implementation head tested below: `890492471d73a6cc572ab1d09b1fc6f3fed13694`.
- This receipt commit becomes the PR head. A commit cannot embed its own SHA in its contents; the final receipt-commit/PR-head SHA is recorded in PR #93's body and in the controller handoff.

This receipt records the bounded fix round. It is not an independent-review receipt, does not claim A6 PASS, and does not authorize readiness or landing.

## Finding dispositions

| Finding | Disposition | Change and evidence |
|---|---|---|
| P1-a: snapshot validation accepts source-row/render divergence | Fixed | Snapshot validation now requires the complete source-row field set, verifies candidate/leg identity, recomputes each source-row hash, checks the aggregate source hashes, and recomputes `render_id` from the validated snapshot plus rendered HTML (`options_researcher/pick_tracker.py:128-185`). Snapshot production now embeds the complete hashed source row (`options_researcher/attractiveness_dashboard.py:4840-4849`). The regression mutates a source row, updates its row and aggregate hashes, leaves the rendered identity stale, and expects fail-closed rejection (`tests/test_pick_tracker.py:162-171`). |
| P1-b: mutable current portfolio can retroactively rewrite historical CC/PMCC outcomes | Fixed | Dated outcome, scoreboard JSON, and scoreboard Markdown artifacts now use create-once/idempotent immutable writes; divergent reruns raise `IMMUTABLE_HISTORY_CONFLICT` (`options_researcher/pick_tracker.py:1264-1274`, `options_researcher/pick_tracker.py:1396-1438`). The regression records outcomes, mutates the portfolio holdings, reruns, and asserts every recorded artifact remains byte-stable (`tests/test_pick_tracker.py:688-776`). |
| P1-c: daily marking absent; drawdown ignores zero-return entry point | Fixed | Evaluation now emits an entry-session daily mark at return zero, marks each subsequent trading session through the recorded horizon, and computes drawdown from that daily series including the zero entry point (`options_researcher/pick_tracker.py:933-1061`). Regressions assert the zero-return entry, daily sequence, and settlement-horizon stop (`tests/test_pick_tracker.py:815-906`). |
| P2-a: FAILED/DISABLED arms synthesize exits/re-entries | Fixed | Membership append carries the prior slots unchanged and emits no entries, restrikes, or exits when an arm is `FAILED` or `DISABLED` (`options_researcher/pick_tracker.py:377-384`). The three-session lifecycle regression covers both states (`tests/test_pick_tracker.py:380-411`). |
| P2-b: WP-D reports omit required cohort/cancellation/scoreboard content | Fixed | WP-D Markdown now includes cancellation counts by kind, arm availability, unmatched-lane counts, a primary contrast, and weekly non-overlapping cohort disclosures with paired/unmatched/arm-only outcomes (`options_researcher/pick_tracker.py:1302-1393`). Report regressions require those sections and fields (`tests/test_pick_tracker.py:1158-1188`). |

## TDD evidence

Each testable finding was observed RED before its implementation:

| Finding | RED command scope | Expected failing exit |
|---|---|---:|
| P1-a | strengthened snapshot source-row/render-divergence regression | 1 |
| P1-b | historical-artifact byte-stability regression | 1 |
| P1-c | daily marks, zero entry point, and settlement-horizon regressions | 1 |
| P2-a | FAILED/DISABLED three-session lifecycle regression | 1 |
| P2-b | WP-D required-content regression | 1 |

Focused post-fix verification:

- `uv run python -m unittest tests.test_pick_tracker`: 36 tests, exit `0`.
- `uv run python -m unittest tests.test_attractiveness_dashboard`: 198 tests, exit `0`.

## Required acceptance commands

Acceptance was run at exact implementation head `890492471d73a6cc572ab1d09b1fc6f3fed13694`.

| Command | Exit code | Result |
|---|---:|---|
| `uv run python -m unittest discover -s tests` | 1 | 3,412 tests; 2 failures; 5 skipped. The failures are the inherited schedule assertions `test_research_refresh_guard.ProducerPlistTest.test_checked_in_schedule_and_environment_are_exact` and `test_research_view_launchagents.ResearchViewLaunchAgentTest.test_refresh_template_runs_weekdays_at_0730_et`. |
| `uv run ruff check .` | 0 | All checks passed. |
| `uv run pyright` | 0 | 0 errors, 0 warnings. |

The two unittest failures reproduce on the untouched current-main checkout with `uv run python -m unittest tests/test_research_refresh_guard.py tests/test_research_view_launchagents.py` (18 tests, the same 2 failures, exit `1`). They are outside this fix round and the authority boundary forbids the associated schedule/configuration scope. Therefore this receipt does **not** claim the full acceptance set passed.

## Authority boundary

PR #93 remains draft. This receipt supplies fix-round evidence only. Independent review of the new head and the owner's A6 readiness decision remain separate required gates; no merge, deployment, ops-checkout mutation, ledger write, registration, or readiness transition is authorized here.
