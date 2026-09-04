# Brief 37 — independent adversarial review, round 1 (2026-09-04)

**Reviewer:** Opus subagent dispatched by the orchestrating Claude session (read-only; no file edited).
**Target:** `docs/superpowers/plans/2026-09-04-37-dashboard-presentation-fixes-codex-brief.md` as first written (pre-fix wording; the fixes below were applied in the same session and the brief re-issued for round 2).
**Baseline:** branch `claude/post-147-2026-09-03`, HEAD `039d76e` == `origin/main`.
**Method (reviewer's words):** every citation opened and read at the cited line; the ops build (`~/options-validator-ops/.tmp/dashboard/{index,attractiveness}.html`, 09:12 ET) and ritual log parsed; `tools.job_health_digest` executed against the ops root; `FEASIBILITY_SOURCE_PATHS` imported.

## Verdict: FAIL

Two items required re-drafting: WP-E as written changed the frozen display ranking (its own OUT constraint) and WP-F's move range dropped a closing `fi`.

## Findings (severity · location · disposition in the re-issued brief)

1. **BLOCKER** · WP-E · `attractiveness.py:189-203` — `cushion` (from `rv21`) and `vrp_for_seller` (from `iv_minus_rv`) are members of `grades`; `display_rank.py:18-19` ranks on the GREEN fraction of `grades`. Making `rv21` finite on Schwab-sourced cards flips two badges per sell-lane card and reorders the top 5 and the pick-tracker arms. → **Applied option (a):** WP-E restricted to display fields (price ladder / move bands / the sentence); both badges keep NaN → UNKNOWN until the owner rules DR-5b; new acceptance test pins the frozen-baseline arm ordering byte-identical before/after.
2. **BLOCKER** · WP-F.2 · block is `tools/daily_ritual.sh:492-507` (closing `fi` at `:507`), brief said `:492-506`. → Fixed.
3. **HIGH** · WP-F · `tests/test_daily_ritual_provenance.py:131-142` pins absolute line numbers of mutation verbs (asserted `:370`); `PYTHON_DASH_C_CLASSIFICATION` line-keyed (`:390`). → Added: move must be net-zero in line count.
4. **HIGH** · WP-C · `evaluate_full_ritual()` aggregates three flags; keying the H7 heading on aggregate `ready` mis-attributes unrelated blockers. → Gate on `CURRENT_AUTHORITY.h7_active`; render only the H7 blocker.
5. **HIGH** · WP-C · `tests/test_dashboard.py:65` asserts `entries taken: 0`; neither H7 panel test injects authority. → Counts line byte-identical in the paused branch; tests inject `h7_authority=`.
6. **HIGH** · WP-F.6 · `hypothesis_evidence.py:1255` filters "not tracked" rows before details are compared; the prescribed output is unattainable and the page already prints `raw_state_counts`. No DR ID. → **Dropped** from the brief.
7. **HIGH** · WP-E · same-day close (16:00) mixed with a 15:45 IV; undisclosed. → rv21 now computed through the last close strictly BEFORE the capture session; mixing eliminated; labelled.
8. **MEDIUM** · closing paragraph · `FEASIBILITY_SOURCE_PATHS` is a frozen literal (`h7_schwab_window_registration.py:143-194`); importing it proves nothing. → Re-verify via `tests/test_h7_schwab_window_registration.py:510` (recomputed closure) + `git diff --name-only`.
9. **MEDIUM** · DR-4 · Study Hall C count is 18, not 22 (`grep -c` on the build and on `ledger/facts.log`). → Fixed.
10. **MEDIUM** · WP-E.6 · raw-closes call is `features.py:121`; unlabelled; impact confined to rows within `RV_WINDOW` of a split (`data/underlying_closes.py:208-214`, latest split 2025-12-18). → Fixed, labelled Inference, impact stated.
11. **MEDIUM** · WP-G(a) · the page's session helper is `top3_snapshot.trading_sessions_between` (`:83-92`, `np.busday_count`, holidays counted as sessions; used at `attractiveness_dashboard.py:1246`); "XNYS" was wrong. → Fixed.
12. **MEDIUM** · WP-G(a) · no rule for a missing/unparseable evaluation session. → Added: every failure stays loud unless age computed.
13. **MEDIUM** · WP-G(a) · narrows the documented loudness guarantee (`attractiveness_dashboard.py:1051-1056`) without saying so. → Acknowledged in the WP; retention window printed in the collapsed line.
14. **MEDIUM** · WP-H · any `.cache` symlink target would pass silently. → HealthRow must report the resolved cache root.
15. **MEDIUM** · Acceptance · first ritual after landing may raise `IMMUTABLE_HISTORY_CONFLICT` (`pick_tracker.py:1470-1476`; fail-soft at `daily_ritual.sh:487`). → Added; executor may not pass `--supersede-reason`.
16. **MEDIUM** · WP-B · exception set unnamed; house pattern is a named tuple (`dashboard.py:173-176`). → `(OSError, ValueError)` exactly.
17. **MEDIUM** · provenance · five inferences laundered under the blanket Repo-verified line. → Labelled inline.
18. **LOW** · WP-A · `date.today()` is local, not UTC; repo convention is the NY date. → NY-zoned date or injected `today`.
19. **LOW** · OUT list · `ritual_status` is not last (Step 8 DURABILITY follows, `daily_ritual.sh:528+`; pinned at `tests/test_daily_ritual_provenance.py:588-591`). → Reworded.
20. **LOW** · line cites · `ritual_authority.py:69-84`; `_schwab_state_html` `:1050`; `_contained_path` `:91-99`; `load_holdings` `:77-96`; receipt glob `hypothesis_evidence.py:1133`; shortlist function `_original_hero_html` `:4099-4174`. → All corrected.
21. **LOW** · WP-G(b) · requires threading a flag through `_hero_pick_html` (`:3877-3928`); no existing test asserts on `.event-chips`; dedupe fires only when every card's chip list matches (true on the 09-04 build, data-dependent). → Named and stated.
22. **LOW** · shape · Executor line form; acceptance block lacked `attractiveness_dashboard`; registry row said "committed together" while uncommitted. → Fixed; the commit that carries this receipt carries the brief and the registry row together.

## Verified correct by the reviewer (attacked and survived)

`FEASIBILITY_SOURCE_PATHS` membership exactly as the brief states (50 paths; four IN files plus `portfolio.py`, `hypothesis_evidence.py`, `schwab_chain_view.py`, `data/ritual_authority.py` outside; `features.py` and `data/underlying_closes.py` inside; the recomputation test at `tests/test_h7_schwab_window_registration.py:510-519` guards it). DR-1, DR-2, DR-3, DR-6 (174 copies of the self-contradictory sentence), DR-7 (50 citations of the 09-02 receipt; `ritual_receipt` reads only lane artifacts; nothing between `:483` and `:492` feeds the receipt block; the pick-tracker snapshot binds `reports/schwab_chains/<as_of>/preclose.json`, not the ritual receipt, so the reorder does not change that binding), DR-8a (`tests/test_attractiveness_dashboard.py:3571-3584` uses age 0 and stays loud), DR-8b (5/5 identical chip lists in both sections), DR-9 (reproduced live: `Schwab preclose | FAILED | receipt path escapes root` beside `Intraday capture (preclose) | OK | 15/15`; `.cache` appears once in the digest at `:524`), and the DR-5 exclusion.
