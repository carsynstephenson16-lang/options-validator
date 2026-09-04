# Brief 37 — independent adversarial review, round 2 (2026-09-04)

**Reviewer:** Opus subagent dispatched by the orchestrating Claude session (read-only; no file edited).
**Target:** brief rev 2 as committed at `12b4404`.
**Baseline:** branch `claude/post-147-2026-09-03`, tree = `origin/main` @`039d76e` + docs-only commit `12b4404`.
**Method (reviewer's words):** every rev-2 file:line opened; the WP-F relocation executed in memory and re-run against every registry/ordering invariant in `tests/test_daily_ritual_provenance.py`; `bash -n` on the moved script; `Path.resolve()` symlink semantics measured; `np.busday_count` measured; the ops build re-counted.

## Verdict: FAIL

All 22 round-1 findings were confirmed applied (none falsely claimed); findings 1 and 12 were applied incompletely and finding 4's fix introduced a fragility. Two new blockers: WP-G(a) prescribed an output location (`_diagnostics_drawer_html`, a fixed six-element list at `:5660-5669`, pinned by `tests/test_attractiveness_layout.py:405`) unreachable from the function it scoped; WP-E never named the one mechanism (`rv21_display` at `:2032`/`:2213`) that keeps badges NaN while the ladder gets a value, and re-created the DR-6 sentence on `iv_minus_rv`.

## Findings (severity · disposition in rev 3)

1. **BLOCKER** · WP-G(a) collapsed line cannot reach the drawer from `_schwab_state_html` (sole caller `_chain_age_html:1122`, spliced at `:5651`; drawer list `:5660-5669`; six-sections test `:405`). → **Rev 3 renders the collapsed line in place** (one `notice info` div in `_schwab_state_html`'s own return); drawer untouched.
2. **BLOCKER** · WP-E display/grade split mechanism unnamed (`ladder_cards` at `:2032` takes `rv21`; `_gather_symbol` returns `rv21` at `:2213` → `rv21_by_symbol:1912` → `scenario_rows:1612` / `bbb_rows:1614`). → **Rev 3 removes the rv21 computation from this brief**; the mechanism is recorded in the held DR-6 design for the owner ruling.
3. **HIGH** · `iv_minus_rv` `feature_unavailable` entry (`:1975`) would reuse the false `gap` sentence. → Rev 3 WP-E is a text-only fix that replaces the sentence at `:1972-1973` (feeding `:1974-1975` and the `bbb_absent` copies at `:1619-1625`) with a true one.
4. **HIGH** · per-card wiggle sentence `attractiveness.py:211-215` would contradict a finite ladder; file outside IN. → Moot under rev 3 (no computation); recorded in the held design.
5. **HIGH** · parity test must compare at `last_close_date`, not `day` (`features.py:50-51`, `:68`). → Recorded in the held design.
6. **HIGH** · `tests/test_schwab_freshness_gather.py` (drives the Schwab branch; `:174`, `:188`, `:197-199`) not in Scope IN. → Added to IN with the survival note.
7. **MEDIUM** · WP-C substring filter `"H7" in b` can return `[]` silently. → Rev 3 constructs `RitualAuthority(h7_active=CURRENT_AUTHORITY.h7_active, exact_session_source_active=True, ritual_data_phase_active=True)` so only the H7 blocker can be produced; empty result renders `H7 BLOCKER TEXT UNAVAILABLE (ritual_authority contract changed)`; test pins it.
8. **MEDIUM** · WP-E lacked a fail-closed rule for `trading_sessions_between` errors / negative counts. → Recorded in the held design.
9. **MEDIUM** · `busday_count` is `[start, end)`; admissible band is `1 <= n <= 3`. → Recorded in the held design.
10. **MEDIUM** · `iv_minus_rv` had no display consumer. → Moot under rev 3.
11. **MEDIUM** · WP-G(b) dedupe would collapse `EVENT LAYER FAILED` banners (`:3024-3025`). → Dedupe applies only to output beginning `<div class="event-chips">`.
12. **MEDIUM** · WP-B: no rule for a missing VST row → `IndexError` or silent 0. → `Held — shares UNKNOWN (no holdings.csv row for VST)` + stderr + test.
13. **MEDIUM** · WP-H: `.cache` symlink-to-file or dangling passes containment, fails later with the wrong cause (`:551-556`). → FAILED row `cache root is not a directory: …` before the loop; tests for both cases.
14. **LOW** · DR-6 count: `"Unavailable for this session"` = 13; the quoted sentence = 174 (also repeated in `bbb_absent`, `:1619-1625`). → Fixed.
15. **LOW** · DR-8b: 295 chips on the page (180 FOMC); WP-G(b) removes 8 of the 12 above the fold, none elsewhere. → Residual stated.
16. **LOW** · cite drift: `_schwab_state_html:1050-1093`; `CURRENT_AUTHORITY:38-50`; `load_holdings` raises `:79-95`; `trading_sessions_between` call `:1248` (import `:1246`); `_achievements_grid:373-388`; `_default_closes:112-121`; `_default_data_as_of:124-144`; `bbb_rows` def `:236`. → All corrected.
17. **LOW** · WP-D did not say where the collapse happens. → In `assemble()` (changes `data["achievements"]`).
18. **LOW** · no "context-lane card builder" exists; the chip call is inline at `:4463`. → Fixed.

## Verified correct by the reviewer (attacked and survived)

WP-F executed in memory: line count identical, `bash -n` passes, `PYTHON_DASH_C_CLASSIFICATION` and `MUTATION_VERB_SITES` line sets unchanged, all four region markers intact, all three ordering pins hold; only `test_pick_tracker_is_fail_soft_between_board_and_capture_receipt` needs the promised edit. WP-F.2 independence and WP-F.5 binding claims confirmed. DR-1..DR-4 and DR-7..DR-9 all reproduce on the ops build. DR-5/DR-5b exclusion correct (`display_rank.py:18-19`; `attractiveness.py:200-201`, `:203`). WP-A safe (`data/underlying_closes.py:53-59`; `tests/test_dashboard.py:131-176` survive). WP-G(a) keeps `tests/test_attractiveness_dashboard.py:3571-3584` loud (age 0). WP-H's cited containment tests unaffected; no test pins the OK reason string. `FEASIBILITY_SOURCE_PATHS` membership re-verified (50 paths; `features.py:162`, `underlying_closes.py:157` inside; every IN file outside). `data/ritual_authority.py` import is pure. Shape compliant with the skill.
