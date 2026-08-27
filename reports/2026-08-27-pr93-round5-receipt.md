# PR #93 round-5 implementation receipt — 2026-08-27

## Scope and exact bases

- Controlling review/addendum: `reports/2026-08-27-pr93-round4-independent-review.md` at review commit `77ff464` on draft PR #117. Addendum #3 supersedes only Addendum #2's Task-4 form.
- Implementation branch: `codex/brief27-implementation` (draft PR #93).
- Pre-round implementation head: `fd38aa22e21b9bd680d37b984730c23ec622ec1d`.
- Current main incorporated before implementation: `origin/main@5652c04ca032a681d2b0fcd93d164792af0be6eb`; merge commit `d43221e1822167fe7070c41da6d5968bd788da76`.
- The final implementation/receipt commit becomes the PR head. A commit cannot contain its own SHA; record the final SHA in the PR handoff after commit/push.

This is implementation evidence only. It does not claim an independent-review PASS, readiness, landing, deployment, ops synchronization, registration, ledger-write, or scored-write authority.

## Blocking finding dispositions

| Finding | Disposition | Change and evidence |
|---|---|---|
| NEW-1 | Closed | `resolve_fill` invokes coverage validation only for `cc`/`pmcc`; a real `_CausalCoverageValidator` no longer crashes `long_call`. CLI regression writes OPEN outcomes for the non-covered lane. |
| NEW-2 / R2 | Closed | A standalone valid-source/valid-HTML test mutates only `render_id` and requires `SNAPSHOT_RENDER_ID_MISMATCH`. |
| NEW-3 | Closed | Ritual tests pin the evaluator’s `if/elif/else` non-propagating structure, prohibit `exit` in the branch, and require the real conflict execution to return 0. The operational shell bytes were not changed. |
| NEW-4 final form | Closed | `_CausalCoverageValidator` stamps each newly observed coverage key with its internally machine-derived `America/New_York` date, never `as_of` or CLI input. Evaluation session S filters both prior and newly observed rows to `observed_session <= S`; a current observation therefore cannot rewrite an earlier session. `_write_evaluation_reports` independently raises distinct `LIVE_HOLDINGS_OBSERVATION_SESSION_MISMATCH` before any write if a supplied observation date differs from the machine date. There is no override flag. |
| P1-a / A3 | Closed | `DashboardRenderResult` captures source-row hashes from the exact qualified, watch-inclusive, and context selections used by the render path. `_write_dashboard_result` binds the HTML marker from those render-side hashes while deriving snapshot hashes/digest separately from the detached snapshot. A real X-rendered/Y-snapshotted producer probe now rejects with `SNAPSHOT_HTML_SOURCE_MISMATCH`. |

## RED-first and guard evidence

- Initial evaluator RED: 48 tracker tests produced exactly two assertion failures (fresh and gap backdates accepted) plus the expected non-covered `_coverage_key` crash. NEW-1 remained closed after the final Task-4 rework.
- Addendum #3 scheduled probe RED: `as_of=2026-08-26`, machine session `2026-08-27` failed at the superseded `LIVE_HOLDINGS_SESSION_MISMATCH` guard. Final: outcomes publish normally as OPEN and the persisted observation is dated `2026-08-27`, never `as_of`.
- Addendum #3 backdate probes RED: both the fresh tracker and Aug-25-newest/Aug-26-gap shapes failed at the same obsolete equality guard. Final: with machine session `2026-08-28`, both write observations dated only `2026-08-28`; neither can stamp current holdings into Aug 26.
- Writer-boundary probe RED: a supplied Aug-26 observation was accepted while the machine session was Aug 27. Final: it raises `LIVE_HOLDINGS_OBSERVATION_SESSION_MISMATCH` before creating the destination.
- A3 RED: 199 dashboard tests produced exactly one failure because X-rendered/Y-snapshotted artifacts validated. After the fix: 199 tests, exit 0.
- R2 was restored as an independent regression and passed against the retained render-id guard.
- Probe A and R1 remained in the tracker suite and passed after A3.
- The older two-day Probe B now explicitly advances its mocked New York session from Aug 26 to Aug 27; its original day-1 byte-stability and day-2 cancellation assertions are unchanged.
- An attempted temporary fail-hard mutation of the operational ritual was refused by the workspace safety layer, so no mutation was made. The final tests exercise the real evaluator line, require return code 0, and structurally reject an `exit` in the branch.

## Final validation

| Command | Exit | Result |
|---|---:|---|
| `uv run python -m unittest discover -s tests -p 'test_pick_tracker.py'` | 0 | 50 tests, OK. |
| `uv run python -m unittest discover -s tests -p 'test_attractiveness_dashboard.py'` | 0 | 199 tests, OK. |
| `MPLCONFIGDIR=/private/tmp/pr93-round5-mpl uv run python -m unittest discover -s tests -p 'test_daily_ritual_provenance.py'` | 0 | 41 tests, OK. |
| `MPLCONFIGDIR=/private/tmp/pr93-round5-mpl uv run python -m unittest discover -s tests -p 'test_shell_banner_guard.py'` | 0 | 4 tests, OK. |
| `MPLCONFIGDIR=/private/tmp/pr93-round5-mpl uv run python -m unittest discover -s tests` | 0 | 3,428 tests, OK, 5 skipped. |
| `uv run ruff check .` | 0 | All checks passed. |
| `uv run pyright` | 0 | 0 errors, 0 warnings, 0 informations. |
| `git diff --check` | 0 | No whitespace errors. |

`ruff format --check` remains unsuitable as a file-wide gate for the three legacy files it flags: its proposed diff is more than 7,000 lines of pre-existing repository formatting normalization. No unrelated normalization was applied; task-local code follows the surrounding style and ruff lint is clean.

## Remaining boundaries and unsupported assumptions

- “Machine-derived current New York session” is the current civil date in `America/New_York`. The scheduled caller intentionally evaluates the strictly prior completed XNYS session; the present-day observation is persisted but cannot affect that earlier evaluation because causal filtering is by `observed_session <= evaluated session`.
- The render-side digest binds the selected source-row identities carried by the render path; it does not parse human-visible HTML tokens back into quote rows. Post-publication Probe A, per-row R1, duplicate-marker refusal, HTML byte hashing, and `render_id` validation remain separate guards.
- NEW-5 through NEW-9 and the accepted N4 diagnostic-precision divergence remain non-blocking exactly as adjudicated by the controlling review.
- No live-order path, paper-book mutation, network provider, ledger append, registration, authority flip, or operations checkout was touched.

## Decision

Implementation tree: **ready for a fresh independent review of the new PR #93 head after commit/push; not ready for landing or operations.** PR #93 must remain draft.
