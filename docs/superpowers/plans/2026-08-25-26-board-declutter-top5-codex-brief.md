# Codex brief 26 — board declutter: Top-5 shortlist, dominated-card collapse, compact regime view (rev 4)

**Date:** 2026-08-25 (rev 4, same day)
**Author:** Claude orchestrating session (Fable), 2026-08-25
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** HANDED OFF TO CODEX — owner-directed 2026-08-25 in-session ("hand brief 26 to codex"). Review history: round 3 PASS WITH FIXES, all applied in rev 4; the rev-4 liquidity-panel design decision in WP-C.1 was NOT itself re-reviewed — Codex should treat that one clause with extra care and flag any doubt rather than improvise. Receipt: `reports/2026-08-25-briefs-25-27-adversarial-review-receipt.md`. Landing order still binds: this brief lands FIRST (26 → 25 → 27).
**Provenance:** Repo-verified against commit `720a20e` on branch `claude/codex-handoff-plan-2026-08-22` unless labeled otherwise (line numbers re-verified at this SHA; the 2026-08-25 input-root-default fix `OPS_CHECKOUT_FALLBACK` is COMMITTED at `attractiveness_dashboard.py:57` — WP-D.3 depends on it and on nothing uncommitted). Landing order is binding: **this brief lands first, then brief 25, then brief 27.**
**Owner directive source:** Carsyn in-session 2026-08-25 ("pull up to top 5 picks each day", "wasserstein regime view needs to be fixed, there's too much information", "if the option isn't as good as another one I don't think it should be shown") — spoken, not owner-typed.

## Why this exists (plain language)

The rendered board is ~660 KB (Estimate, measured 2026-08-25; the artifact
rebuilds daily) and roughly 92% of it is 18 per-symbol panels holding 188
candidate cards, 228 tables, and 1,072 rows. Within one symbol's lane, cards
are ordered but never pruned — a card worse than a sibling on every measured
axis still renders in full. Separately, the Wasserstein regime view is
unreachable from a dev-checkout build (published only into the ops
checkout's `.tmp/dashboard/`) and verbose when reachable (full per-symbol
transition matrices for a reader who wants "what regime is each name in").

Three changes: Top-5 shortlist, dominated-card collapse (collapse, never
delete — fail-visible is repo law), and a compact regime strip with the full
report demoted to a link.

## Scope

**IN**
- WP-A: shortlist n=3 → n=5 via `config.PICK_TOP_N`.
- WP-B: within-lane dominance collapse.
- WP-C: per-symbol panels collapsed by default.
- WP-D: compact regime strip + research-views publication for non-ops builds.
- WP-E: coordinated test updates (enumerated; every break intentional).

**OUT (hard stops)**
- No change to the frozen GREEN-fraction recipe's ordering semantics:
  `_display_quality_key`, `_admissible_pick_pool` vetoes, tie-breaks, and
  one-pick-per-symbol stay behavior-identical. n changes how many winners
  DISPLAY, not how candidates are ordered or admitted.
- No ledger writes, no registration/amendment, no authority flips, no
  live-order paths, no network providers.
- No deletion of any card from the assembled payload — pruning is
  presentation-layer collapse; `sections_json()` stays complete.
- No `options_researcher.exp_*` import into `attractiveness_dashboard.py`
  (AST test `tests/test_experiments_baseline.py:92`).
- No change to `options_researcher/regime.py` math or `config.py` REGIME_*
  constants; WP-D touches rendering/publication only.
- DATA_BLOCKED / skipped / stale states are NEVER collapsed or pruned
  (pinned: `tests/test_attractiveness_dashboard.py:1116`).

## Interlock (rev-1 findings 12, 13 corrected)

- RQ2-v1/A2-v1 do not consume top-3 membership. Correct citations: ledger
  **seq 27** (`A2_AMENDMENT_V1_1`, single clause: "TERCILES IS THE RULE;
  'top 6 versus bottom 6' is its instantiation on the current 18-name
  board") and **seq 18** ("no badge reorders the frozen GREEN-fraction
  baseline"). Repo-verified in `ledger/experiments.jsonl`.
- Brief 25 consumes `PICK_TOP_N` and inserts its (flag-gated) section after
  this brief's renamed hero heading; brief 27 records `PICK_TOP_N` picks.
  This brief owns ALL heading-string renames and the shared ordering-test
  edits; briefs 25/27 add only their own new, flag-gated tests.

## Work packages

### WP-A — Top-5 shortlist

1. `config.py`: `PICK_TOP_N: int = 5` beside the PICK_* display constants
   (`config.py:635-646` region), comment: "display-layer shortlist width;
   owner-directed in-session 2026-08-25 (spoken, not owner-typed);
   presentation only, never a strategy gate."
2. Thread it: `select_top_picks` (`attractiveness_dashboard.py:421` @720a20e)
   and `select_qm_top_picks` (`:470`) default `n=config.PICK_TOP_N`; replace
   ALL SIX slot literals (rev-1 finding 14; Repo-verified @720a20e):
   - `:3278` `for slot in range(len(py_picks) + 1, 4):`
   - `:3283` `open_count = max(0, 3 - len(py_picks))`
   - `:3348` `for slot in range(1, 4)`
   - `:3350` `selected_count, open_count = 0, 3`
   - `:3371` `for slot in range(len(cards) + 1, 4):`
   - `:3373` `selected_count, open_count = len(picks), max(0, 3 - len(picks))`
   After editing, grep `range(1, 4)|range(len(|, 4)|0, 3` in the module to
   confirm no seventh site exists at the final SHA.
3. Copy updates (this brief owns them): "TOP 3 PICKS TODAY" → "TOP 5 PICKS
   TODAY"; "Rule-based top 3" → "Rule-based top 5"; "…FOR MECHANICAL TOP 3"
   → "…FOR MECHANICAL TOP 5". Then grep user-visible "top 3"/"Top-3"/"Pick 3"
   strings; update display copy only. Identifiers (`top3_snapshot`,
   `top3_context`, schema strings) stay — renaming identity plumbing buys
   nothing.
4. Update `render()`'s page-order docstring (rev-1 finding 38; the "rule-based
   Top-3 -> movement lane" lines at `attractiveness_dashboard.py:4024`
   @720a20e — rev-2 finding N-10 corrected the line).
5. `tools/research_context_assemble.py` inherits n via `select_top_picks`
   (`:49-60,:67-69`) with no edit. The cost consequence (more research
   packets per run) is an OWNER decision surfaced in brief 25 WP-E.4 D-2 —
   not silently shipped here and not buried in a PR description.

### WP-B — dominated-card collapse (rev-1 findings 16, 17, 18, 40 applied)

1. Pure function `dominated_partition(cards, lane_kind, close)` in the
   dashboard module. Per-lane axis sets, each field Repo-verified to exist on
   that lane's cards (`options_researcher/attractiveness.py`):
   - `put` (`:223-227`): numeric axes `annualized_yield` (higher better),
     `cushion` (higher better).
   - `cc` (`:280-284`): numeric axes `annualized_yield` (higher better) AND
     `upside` (higher better) — a higher-yield card must not hide a card
     preserving materially more upside; that trade-off is the lane's point
     (rev-2 finding N-5).
   - `pmcc` (`:339-343`): EXEMPT from collapse entirely. It carries neither
     `cushion` nor `upside`; one numeric axis plus grade-dominance would
     degenerate "dominated" into "lower yield," hiding real structure
     choices. State the exemption in the function docstring.
   - `long_call` (`:421-429`): numeric axes `cost` (lower better),
     `breakeven_move` (lower better).
   - `leaps` (`:379-381`): numeric axes `cost` (lower better), breakeven
     distance `abs(breakeven - close)/close` (lower better) — `close` is the
     SECTION's close, passed in as the third argument.
   Plus grade-dominance on every lane: over badge keys present on BOTH
   cards, Y's rank ≥ X's for all (GREEN>AMBER>RED>UNKNOWN).
   **Dominance rule:** Y dominates X iff Y is equal-or-better on every
   numeric axis AND grade-dominant, AND strictly better on at least one
   numeric axis or at least one badge (single strictness clause — rev-1
   finding 40). Cards with a missing/None value on any compared axis are
   NEVER dominated (incomparable ≠ worse).
2. **Fixpoint against the retained set** (rev-1 finding 17): iterate — a card
   may be hidden only if a card that REMAINS SHOWN dominates it; recompute
   until stable. Named test: every hidden card's dominator is in the shown
   set (no hidden-by-a-hidden-card chains).
3. Exclusions from hiding (never collapsed): DATA_BLOCKED/skipped cards;
   `rank_leader` cards; Top-5 or pinned picks; **any card carrying a RED
   grade on a SAFETY badge — `liquidity` only** (rev-2 finding N-4
   correcting rev-1 finding 18: 77% of live cards carry a RED somewhere,
   dominated by `portfolio` (143/222) and `fits_cap` (53/222)
   concentration/fit flags — a blanket RED exclusion nullifies the collapse
   and defeats the owner's request; a RED on `portfolio`/`fits_cap`/
   `iv_for_buyer`/`yield`/`cushion` is an assessment, not a data-safety
   warning, and may be hidden behind the expandable block); lanes with ≤2
   candidates.
4. Rendering: hidden cards go into one collapsed `<details>` per lane,
   summary exactly: "N candidates hidden — each is matched or beaten by a
   shown card on every measure (expand to verify)". Expanding shows full
   existing card HTML unchanged; nothing leaves the DOM.

### WP-C — collapsed symbol panels

1. Wrap each per-symbol panel body in `<details>` with the symbol heading +
   one-line summary visible (close, as-of, best card headline, panel
   status). Panels containing any DATA_BLOCKED card or stale banner render
   OPEN by default; all other panels collapsed. Rev-4 design decision
   (responding to round-3 finding NEW-1, LLM-proposed 2026-08-25): a
   liquidity-RED card does NOT force its panel open — 14 of 18 live panels
   contain one, so a liquidity-open rule would nullify WP-C. The safety
   guarantee liquidity-RED keeps is WP-B.3's: such a card is never buried a
   second level down inside the dominated-cards block; a collapsed panel is
   one click from visible and its summary line states the panel status.
   Fail-visible law stays absolute for DATA_BLOCKED/stale.
2. No content change inside panels beyond WP-B.

### WP-D — regime view (rev-1 findings 19, 20 applied)

1. **Machine-readable sidecar, not text parsing:** `regime_report.py` gains a
   JSON sidecar named **`wasserstein-regime.json`** (rev-2 finding N-7):
   `{"schema": "regime_report/v1", "as_of_written": <ISO ts>, "symbols":
   {SYM: {"label", "high_dispersion", "max_asof", "skipped_reason"}}}`.
   `tools/research_display_refresh.sh` must publish `{wasserstein-regime.txt,
   wasserstein-regime.json}` as ONE atomic set (both to temp names, then two
   renames back-to-back after both writes succeed; on any failure neither is
   renamed) — its current pattern renames the `.txt` alone
   (`research_display_refresh.sh:13-14,25-37`), which would let a reader see
   a sidecar disagreeing with the linked report. The report's markdown
   layout ALSO moves tables below a per-symbol "— details —" separator
   (latest label + dispersion + as-of stay on top). Sidecar first, then
   layout — the dashboard never parses markdown.
2. Shared disclaimer constant: move the DISCLAIMER string to
   `options_researcher/regime_constants.py` (no heavy imports); both
   `regime_report.py` and the dashboard import it — no duplicated drifting
   string, no regime-math import into the dashboard.
3. Compact strip: new dashboard section "REGIME (descriptive)" — one line per
   `REGIME_SYMBOLS` name from the SIDECAR: label, high-dispersion yes/no, max
   as-of. Staleness rule (rev-2 N-7; round-3 NEW-6 pins the reference): the
   strip-level banner fires when the NEWEST per-symbol `max_asof` across the
   sidecar is more than 5 trading sessions older than the BUILD's NY
   evaluation date — computed with `trading_sessions_between`, the same
   convention `_page_chain_age_sessions` uses for chain age (threshold
   LLM-proposed, display-only) — OR the sidecar is absent/malformed;
   rendering loudly: "regime view unpublished/stale — see Experiments
   shelf". Per-symbol lines always show their own `max_asof`.
   Strip always carries the shared DISCLAIMER sentence.
4. Publication for non-ops builds: when the deployment checkout's
   `.tmp/dashboard/research-views-status.txt` is absent AND board inputs were
   read from a different root (`_input_root_cwd` window; the ops default
   fallback is committed at `attractiveness_dashboard.py:57,61-90` @720a20e),
   copy the SET {status file, `experiments.html`, `wasserstein-regime.txt`,
   regime sidecar} from `<input_root>/.tmp/dashboard/` into the deployment
   `.tmp/dashboard/` **atomically as a set** (temp dir + rename), deciding
   freshness by the PUBLISHED STATUS FILE's timestamp line — never by file
   mtimes (rev-1 finding 20: mtimes are reset by git/restic and are not this
   repo's freshness discipline). If the local status timestamp is newer,
   skip and note. Stamp the copied-from root visibly on the Experiments
   shelf ("views copied from ops checkout, published <ts>").

### WP-E — coordinated test updates (rev-1 findings 15, 36 applied)

Intentional updates (same commit as the feature that breaks them):
- `tests/test_attractiveness_v3.py:279` hero-card count 6 → `2*PICK_TOP_N`;
  `:280` "…FOR MECHANICAL TOP 3" string; `:281` "Rule-based top 3 — best
  policy-and-liquidity fit today"; `:282` "Pick 3" → "Pick 5". RENAME the
  now-false test names too (rev-2 finding N-11):
  `test_partial_top3_keeps_three_visible_slots_in_each_list` and
  `test_six_slots_render_as_two_lists_and_duplicate_is_allowed`
  (`tests/test_attractiveness_dashboard.py:1685`) get n-neutral names.
- `tests/test_attractiveness_dashboard.py:2260`
  (`test_full_lane_board_order_keeps_named_sections_distinct`), `:1677`,
  `:1776`, `:1790`, and the freshness/shelf ordering tests — heading strings
  only (all line numbers @720a20e).
- Slot tests: `:1685`-area (six slots → `2*PICK_TOP_N`), blocked-QM-slot
  tests (`test_stale_qm_context_renders_three_blocked_slots…` and sibling —
  three → `PICK_TOP_N`).
- `select_top_picks` invariance tests that pin membership on fixtures where
  more than 3 candidates qualify (locate by name:
  `test_evidence_cannot_change_top3_order_or_card_grades`,
  `test_tracker_attachment_cannot_change_mechanical_selection_bytes`
  (`:2230`),
  `test_movement_fires_leave_canonical_mechanical_selection_bytes_unchanged`
  (`:1661`) — the byte-identity pair compares like-for-like builds and is
  expected to pass unmodified; verify rather than edit).
- `tests/test_research_context_assemble.py` mocks that patch
  `select_top_picks` (locate by grep) — confirm they are n-agnostic.
- NEW tests (names track the rev-3/rev-4 rules — round-3 finding NEW-5):
  dominance partition units (incomparable-never-dominated,
  **liquidity-RED-never-hidden**, blocked-never-hidden,
  **portfolio-RED-only-card-IS-hideable** (positive case), ≤2-card lane
  exemption, pmcc exemption, fixpoint shown-dominator property);
  collapsed-panel default states (**DATA_BLOCKED/stale panel open**,
  liquidity-RED-only panel COLLAPSED with its card outside the dominated
  block, clean panel collapsed); regime strip present/absent-is-loud;
  sidecar schema round-trip; atomic set-copy (fresher-local never
  clobbered; status and artifacts never split).
- MUST NOT change: `SelectTopPicksTests` recipe tests except the n default;
  fail-visible pins `:1116`, `:1126`, `:1137` (the exact
  `DISPLAY_ONLY_LABEL` count of 2 must survive WP-B/WP-C); AST boundary
  test.

## Acceptance / verification

```bash
uv run python -m unittest discover -s tests    # exit 0, offline
uv run ruff check . && uv run pyright          # exit 0
```
Plus, on the REAL board (rev-1 finding 15; rev-2 N-4; round-3 NEW-1 — no
speculative percentage): the display metric is "candidate cards visible
without user interaction" (i.e., not inside any CLOSED `<details>`).
(a) BEFORE implementation, run a dry rule-application over the current live
board (round-3 measured basis: 18 panels, 14 with a liquidity-RED card, 222
badge blocks, 82 liquidity-RED) computing exactly which cards the WP-B/WP-C
rules hide/collapse; record the predicted before/after counts in the PR.
(b) Acceptance = the implementation reproduces the dry run's predicted set
EXACTLY (rule-faithfulness, not a percentage); if the predicted reduction
is below 30%, STOP and report the measured ceiling to the owner before
building — never loosen an exclusion to manufacture a number.
(c) Every `candidate_id` present in the payload before the change is still
present after. (d) Top-5 membership equals the first 5 of the unchanged
admission+order pipeline. (e) The hidden-card shown-dominator property test
from WP-E passes.

## Claim-discipline register

- Page composition percentages/byte figures: Estimate, measured 2026-08-25
  (artifact rebuilds daily; not byte-reproducible later).
- Six slot literals and both selector defs: Repo-verified @720a20e (lines
  quoted in WP-A.2).
- Card field availability per lane: Repo-verified
  `options_researcher/attractiveness.py:223-227,280-284,339-343,379-381,421-429`.
- RQ2/A2 non-consumption of top-3 membership: Repo-verified ledger seq 27
  (single clause) + seq 18.
- Ops-default input root committed: Repo-verified
  `attractiveness_dashboard.py:57,61-90` @720a20e.
- RED-badge prevalence (170/222 blocks carry ≥1 RED; portfolio 143,
  liquidity 82, fits_cap 53): Repo-verified, measured on the live board
  2026-08-25 by the round-2 reviewer (rev-2 finding N-4).
- `cc` carries `upside`; `pmcc` carries neither `cushion` nor `upside`:
  Repo-verified `attractiveness.py:280-284,339-343`.
- Dominance axis sets, ≤2-card exemption, pmcc exemption, 5-session sidecar
  staleness threshold, 50% acceptance floor: LLM-proposed 2026-08-25
  (display-only), labeled in code; Assumption until re-review passes them.
