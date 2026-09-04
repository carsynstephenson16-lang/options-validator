# Brief 37 — independent adversarial review, round 4 (2026-09-04)

**Reviewer:** Opus subagent dispatched by the orchestrating Claude session (read-only; no file edited).
**Target:** brief rev 4 as committed at `5e3faac`.
**Baseline:** branch `claude/post-147-2026-09-03`, tree = `origin/main` @`039d76e` + docs-only commits `12b4404`, `03c42b1`, `5e3faac`.
**Method (reviewer's words):** every rev-4 file:line opened; the two structural changes traced through the real call graphs and test files; all eight "measured" counts re-run against the ops build; `np.busday_count` executed; `bash -n tools/daily_ritual.sh` run.

## Verdict: PASS WITH FIXES

All 18 round-3 dispositions applied as claimed. Both structural changes (DR-8b withdrawal; WP-H retiring the failing containment check) sound. Fourteen findings, all wording-only; the orchestrator applied every one in rev 5 (same session, commit carrying this receipt) without a design decision.

## Findings (severity · disposition in rev 5)

1. **HIGH** · WP-E's sentence contained `;`, which `_feature_unavailable_html` uses as the per-field join (`attractiveness_dashboard.py:5073`) while the reason is appended twice (`:1974-1975`) → four unreadable clauses. → Internal `;` replaced with ` — `; the join constraint stated in the WP.
2. **HIGH** · "this lane has no realized-volatility input" was false (`adjusted_closes` exists at `:1943-1944`; only the computation is absent) and contradicted the held DR-5b design. → Sentence now says only "not computed … (see brief 37 DR-5b)".
3. **MEDIUM** · WP-H.2 replaced the guarded `_contained_path` resolve with an unguarded `resolve()`; an ELOOP would raise out of `collect_health` (`:727`). → `try/except (OSError, RuntimeError)` as at `:93-95`, FAILED row `unsafe cache root: …`.
4. **MEDIUM** · per-symbol FAILED row's `path` field unspecified (`chain_relative`, `:534`, `:541`). → Kept unchanged; only the containment argument changes.
5. **MEDIUM** · WP-C's tests inject `h7_authority=` but `assemble()` (`dashboard.py:147-153`) had no such seam. → Keyword-only `h7_authority: dict | None = None` following `:155-157`, mirroring WP-B.
6. **MEDIUM** · "seven fixes" in the brief and registry; the table has eight DR rows and eight WPs. → "eight".
7. **MEDIUM** · OUT list forbade importing any H7/activation module, which WP-C requires for `data/ritual_authority.py`. → Explicit exception (outside the closure; `tests/test_h7_schwab_window_registration.py:518`).
8. **LOW** · `HealthRow(..., FAILED, ...)` used an undefined name. → `HealthStatus.FAILED`.
9. **LOW** · WP-F.3's justification ("all sites after `:507`") was false — four mutation sites and all nine `-c` sites are before `:481`; equality asserted at `:363`, not `:390`. → Rewritten: none of the pinned numbers falls in `:481-507`.
10. **LOW** · WP-C asserted byte-identity on the `h7_active=True` path but only tested `live` present. → Test captures today's string and asserts equality.
11. **LOW** · DR-8b contract citation `:441-449` stopped short of the pinned-surface assertion at `:450`. → `:441-450`.
12. **LOW** · WP-B kept `mark(s)`. → Pluralized properly like `:1128`.
13. **LOW** · `np.busday_count` counts holidays as sessions (`top3_snapshot.py:84-88`) — a notice can collapse up to two real sessions early across a holiday week; undisclosed. → Disclosed in WP-G.2.
14. **LOW** · WP-G named the helper but not its import site (`:1058` local). → Import locally inside `_schwab_state_html`.

## Verified correct by the reviewer (attacked and survived)

All 18 round-3 dispositions present at the quoted rev-4 lines. WP-G(b) withdrawal clean (no WP references the dedupe; OUT forbids `_event_chips_html` and its four call sites and any edit to `tests/test_event_awareness.py`). WP-H.2 correct on all four sub-questions: `chain_dir` has exactly one other consumer (`verify_session` at `:550`, which uses only `path.name`, `schwab_chain_manifest.py:197`, `:244`); every existing test that expects a non-FAILED row builds `.cache/schwab_chains` via `_install_schwab_package` (`tests/test_job_health_digest.py:73-75`, `:129-146`), and the three that skip it short-circuit earlier (`:267`→`:508`, `:492`→`:475`, `:647` MISSING); `_missing()` fires at `:483-484` before the cache check; `root` already resolved at `:713`; digest output is gitignored (`tools/job_health_digest.sh:16`). Every new/changed citation confirmed at the real line (full list in the reviewer's transcript). Every measured count reproduces exactly on the 09:12 ops build (`, before this ` 174 = 26 + 148; event-chip 295; containers 180; receipt citations 50; Study Hall 8/8/18/8/16). WP-F safe (the only three `ritual_receipt` ordering assertions are handled; dashboards/pick tracker use `note` never `crit`; the pick-tracker snapshot binds `reports/schwab_chains/<as_of>/preclose.json`, `:5766-5770`). Scope/authority sweep clean; shape matches the skill; registry row 37 matched rev 4 except the count (finding 6).
