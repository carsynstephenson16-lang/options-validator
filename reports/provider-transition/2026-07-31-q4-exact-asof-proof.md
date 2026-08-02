# Q4 / P1.3 H5 and consumer exact-as-of proof

Date: 2026-07-31
Branch: `sfix`
Canonical task: `PROJECT_STATE.md` Q4 / P1.3
Review correction: `reports/strategy-evaluations/17_fable_adversarial_review_of_sol_plan.md`

## Verdict

Q4 closes the H5 stale-local-data `FIRE` path without changing any registered
threshold or trigger. H5 now evaluates one explicit completed XNYS session and
requires its close, IV-rank feature row, and chain filename to match that
session exactly. Missing, stale, future-only, duplicate, non-finite, or empty
required inputs cannot reach `trigger_status`; the watcher emits `DATA_GAP`,
writes the labeled report when requested, and exits nonzero.

No provider call, cache write, manifest write, ledger/facts append, book write,
one-run record change, or registered H1/H2/H9/live-book verdict change occurred.

## Authoritative consumer matrix

| Consumer | Evaluation-session contract | Beyond-edge proof | Result |
|---|---|---|---|
| H5 `entry_watch` | Exact close row + exact attractiveness-feature row + exact `.cache/chains/<symbol>_<session>.parquet` | Stale each-way, future-only, missing, non-finite-close, and empty-chain tests; real local-store smoke at 2026-07-30 | `DATA_GAP`, never `FIRE`, exit 1 |
| H5 ritual capture consumer | Artifact header, every tracked H5 name, every row's close as-of, and absence of `DATA_GAP` must match the requested session | Session mismatch, omitted-name, and data-gap tests | `REFUSED`, never `NO_SIGNAL` |
| H6 `build_snapshot` / feature manifest | Exact chain filename and manifest identity/feature row for `evaluation_session` | Prior and future chain files present with exact file absent | Error names the missing exact file; no entry |
| H7 data gate / watcher | Exact adjusted-close row, exact chain, matching source-health/data-gate receipt session | Future-only chain plus existing stale/future-close tests | `NO_GO`; no look-ahead substitution |
| H8 `build_snapshot` / feature manifest | Exact chain filename and manifest identity/feature row for `evaluation_session` | Prior and future chain files present with exact file absent | Error names the missing exact file; no entry |

## Red/green evidence

- Pre-change narrow baseline: 125 tests passed.
- Red run after adding Q4 regressions: 133 tests ran with the expected H5,
  ritual-call, and capture-consumer failures. The new H6/H7/H8 characterization
  tests already passed, confirming those implementations were exact-session.
- Final task-specific set: 136 tests passed.
- Targeted plus neighboring consumers/dashboards/ritual guards: 222 tests passed.
- Real-store read-only smoke:
  `uv run python -m options_researcher.entry_watch --as-of 2026-07-30
  --out /private/tmp/q4-h5-exact-asof.txt` returned 1 and reported both names as
  `DATA_GAP`. Visible edges were close 2026-07-27, feature 2026-07-24, and
  chain 2026-07-27. No `FIRE` appeared.

## Quality checks

- `uv run ruff check .`: passed.
- `uv run pyright`: passed with 0 errors and 0 warnings.
- The configured formatter was inspected, but the repository-wide check has a
  known baseline failure. Existing file style was preserved to avoid unrelated
  formatter churn; `git diff --check` passes.
- A scoped HEAD comparison confirmed all six edited files flagged by the
  formatter were already formatter-noncompliant at `HEAD`; the other two edited
  Python files pass the formatter check.
- `zsh -n tools/daily_ritual.sh`: passed.
- Repository-wide `uv run ruff format --check .`: existing baseline remains
  nonzero (255 unrelated files would be reformatted).
- `uv run python -m research.cli verify`: `ledger OK`.
- `uv run python -m options_researcher.h7_event_ledger verify`:
  `VALID records=1 head=a1ea228c2abb`.

## Full discovery

`uv run python -m unittest discover -s tests` completed with 2,267 tests in
262.296 seconds: `OK` (exit 0).

## Residual risk

H5's default no-argument dashboard path derives the same prior completed XNYS
session used by the existing H7 helper. The unattended ritual does not rely on
that default: it now passes its already-resolved `AS_OF` explicitly. Cache-edge
dates remain display context only and never substitute for a requested row.
