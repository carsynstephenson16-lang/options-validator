# PR #93 second fix-round receipt — 2026-08-27

## Scope and exact heads

- Controlling review: `reports/2026-08-27-pr93-fix-round-independent-review.md` from review head `1c8ad253fcec2614fec953283e37a25d7ab03733`, reviewing failed PR head `36a167e6bf2942ea54a993790acc692f0b288a3f`.
- Branch: `codex/brief27-implementation`.
- Current main merged without rebasing: `origin/main@c1b5bf06e373ddb62af1037e6e73832c7079a0af` (already up to date).
- Exact implementation head tested: `0de1457d8cb760952da01009fb9ed50ee941faa0` (`5bebadb589365eacf72e6480b7633b8ab1f50c16` plus the acceptance-discovered shell-banner correction).
- This receipt commit becomes the PR head. A commit cannot contain its own SHA; the final receipt-commit/PR-head SHA is recorded in PR #93's body and the controller handoff.

This receipt records implementation evidence only. It does not claim an independent-review PASS, owner A6 readiness, or landing authority.

## Step 0 acceptance bar

PR #116 was OPEN and unmerged at the start of this round (`2494f3d77ffd8e938ca57faf944fb8f5c84500c2`). Therefore the applicable full-suite bar was exit `1` with **exactly** these two inherited schedule failures and no others:

1. `test_research_refresh_guard.ProducerPlistTest.test_checked_in_schedule_and_environment_are_exact`
2. `test_research_view_launchagents.ResearchViewLaunchAgentTest.test_refresh_template_runs_weekdays_at_0730_et`

The final acceptance run met that bar exactly.

## Finding dispositions

| Finding | Disposition | Change and precise evidence |
|---|---|---|
| P1-a: self-consistent snapshot/render divergence | Closed for the specified digest-binding design and both recorded guards | The producer derives one aggregate digest from candidate source-row hashes and embeds it in the published HTML bytes (`options_researcher/attractiveness_dashboard.py:5276-5286`). Validation recomputes every row hash, the aggregate digest, the digest embedded in HTML, the HTML hash, and `render_id` (`options_researcher/pick_tracker.py:99-125`, `options_researcher/pick_tracker.py:128-229`). Probe A and the R1 row-hash guard are separate regressions (`tests/test_pick_tracker.py:192-219`). |
| P1-b / N1: current portfolio rewrites historical CC/PMCC status | Closed for prospective observations; historical reconstruction is not claimed | Coverage identity is keyed and persisted by observed session. The validator uses only observations dated on or before the session being evaluated, observes live holdings only at the current `as_of`, and treats a change as effective from that first observed session (`options_researcher/pick_tracker.py:645-764`). Outcome status is an append-event sequence, so the prior OPEN event remains unchanged and a later cancellation carries its observed session (`options_researcher/pick_tracker.py:1087-1134`, `options_researcher/pick_tracker.py:1190-1206`). Dated coverage observations are written with the outcome artifacts (`options_researcher/pick_tracker.py:1595-1632`, `options_researcher/pick_tracker.py:1767-1801`). Probe B is `tests/test_pick_tracker.py:942-1041`. |
| N2: chain-load explosion | Closed for one evaluation run | `evaluate_records` memoizes both successful frames and expected loader errors by `(symbol, session)` and routes fill and mark reads through that cache (`options_researcher/pick_tracker.py:1019-1031`, `options_researcher/pick_tracker.py:1063-1070`, `options_researcher/pick_tracker.py:1143-1157`). Scale regression: `tests/test_pick_tracker.py:1171-1217`. |
| N3: silent permanent conflict; no recovery | Closed with explicit, append-only recovery | The ritual writes evaluator output to a dedicated log, names `IMMUTABLE_HISTORY_CONFLICT` in its note, and never passes the supersede flag (`tools/daily_ritual.sh:475`; behavior regression `tests/test_daily_ritual_provenance.py:250-288`). Manual `--supersede-reason` preserves canonical bytes, writes hash-bound replacements under `supersedes/`, and writes a reason-bearing receipt; readers validate and resolve the one active supersede (`options_researcher/pick_tracker.py:1595-1698`, `options_researcher/pick_tracker.py:1711-1737`, `options_researcher/pick_tracker.py:1767-1816`). Recovery is documented in the module docstring (`options_researcher/pick_tracker.py:8-14`) and tested at `tests/test_pick_tracker.py:854-921`. |
| N4: unavailable-arm allowlist/denylist asymmetry | Closed | Journal membership now preserves slots and emits no transitions for every state other than `READY` (`options_researcher/pick_tracker.py:424-432`); the `PAUSED` regression is `tests/test_pick_tracker.py:456-486`. |
| N5: stale exclusive-create temp leaks `FileExistsError` | Closed | `_immutable_write` converts the exclusive-create collision to `TrackerConflict: TRACKER_TEMP_CONFLICT` and does not unlink a temp it did not create (`options_researcher/pick_tracker.py:1457-1490`; regression `tests/test_pick_tracker.py:922-928`). |
| N6: evaluation writer bypasses dry-run boundary | Closed | `_write_evaluation_reports` enforces the destination before building/writing artifacts, and also checks replacement and receipt paths (`options_researcher/pick_tracker.py:1595-1610`, `options_researcher/pick_tracker.py:1664-1697`; regression `tests/test_pick_tracker.py:930-941`). |
| N7: missing scheduled mark does not increment unreachable count | Closed | A scheduled checkpoint with no daily mark appends `MARK_UNREACHABLE` and increments the count (`options_researcher/pick_tracker.py:1171-1189`; regression assertion `tests/test_pick_tracker.py:1303-1367`). |
| P1-c, P2-a, P2-b | Confirmed-closed; not reinterpreted | Daily zero-entry marking remains covered at `tests/test_pick_tracker.py:1086-1130`; unavailable-arm continuity remains covered at `tests/test_pick_tracker.py:424-454`; WP-D content remains covered at `tests/test_pick_tracker.py:1467-1501`. Focused tracker, dashboard, and ritual suites remained green. |

## RED-first and probe-flip evidence

| Construction | Pre-fix / revert result | Final result |
|---|---|---|
| Probe A: mutate `raw_quote.bid`, rederive row hash, aggregate hashes/digest, and `render_id`, leave HTML untouched | Rejected expectation failed; validator accepted the payload; exit `1` | Rejected with `SNAPSHOT_HTML_SOURCE_MISMATCH`; one-test discover exit `0` |
| R1: delete only the per-row `SNAPSHOT_SOURCE_ROW_MISMATCH` guard | New R1 test failed because no error was raised; exit `1` | Guard restored; one-test discover exit `0` |
| Probe B: day-1 CC OPEN, mutate holdings before day 2 | Day-2 result had no daily history because current holdings were back-applied to the day-1 fill; exit `1` | Day-1 bytes and OPEN event unchanged; cancellation appended at day 2; one-test discover exit `0` |
| N2 duplicated-arm LEAPS scale probe | `254` loads for `127` distinct pairs; exit `1` | `127` loads for `127` distinct pairs; exit `0` |
| N3 ritual conflict | Output contained only generic `FAILED (isolated)` note; exit `1` | Output names `pick tracker evaluator: IMMUTABLE_HISTORY_CONFLICT`; focused test exit `0` |
| N4 / N5 / N7 | Each focused regression exited `1` (N5 surfaced raw `FileExistsError`) | Each focused regression exit `0` |
| N6 enforcement revert probe | Removing only `_enforce_write_path` left the outside write accepted and made the new test fail; exit `1` | Enforcement restored; focused test exit `0` |

Focused final verification at the implementation tree:

- `uv run python -m unittest discover -s tests -p 'test_pick_tracker.py'`: 44 tests, exit `0`.
- `uv run python -m unittest discover -s tests -p 'test_attractiveness_dashboard.py'`: 198 tests, exit `0`.
- `uv run python -m unittest discover -s tests -p 'test_daily_ritual_provenance.py'`: 41 tests, exit `0`.
- `uv run python -m unittest discover -s tests -p 'test_shell_banner_guard.py'`: 4 tests, exit `0`.

## Required acceptance at `0de1457d8cb760952da01009fb9ed50ee941faa0`

| Command | Exit code | Result |
|---|---:|---|
| `uv run python -m unittest discover -s tests` | 1 | 3,421 tests; exactly the two inherited schedule failures named above; 5 skipped. This meets the applicable Step 0 bar because #116 was not merged. |
| `uv run ruff check .` | 0 | All checks passed. |
| `uv run pyright` | 0 | 0 errors, 0 warnings, 0 informations. |

The first full run at `5bebadb589365eacf72e6480b7633b8ab1f50c16` exposed one additional shell-banner-guard failure caused by Python command substitution. That task-caused failure was corrected in `0de1457d8cb760952da01009fb9ed50ee941faa0`; the full acceptance set above is the fresh rerun after that correction.

## Remaining boundaries and gaps

- No fresh independent review of this new head has been obtained in this round; that remains the next gate.
- For dates predating any persisted coverage observation, the causal validator treats frozen coverage as unchanged until the first actual observation. This prevents look-ahead but is not a reconstruction of unobserved historical portfolio state.
- Snapshot/HTML closure follows the controller's accepted embedded-digest design: validation binds snapshot rows to the digest embedded by the producer in the HTML bytes; it does not parse every human-visible quote token back out of the rendered markup.
- The explicit recovery design permits one unambiguous active supersede per date. A second distinct supersede receipt fails closed rather than choosing among competing histories.

PR #93 remains draft. No readiness, merge, deployment, install, ops-checkout mutation, ledger write, registration, or frozen-value change is authorized by this receipt.
