# Brief 39 — independent adversarial review, round 3 (2026-09-06)

**Reviewer:** Opus, adversarial round 3 (independent; read-only on tracked files).
**Target:** `docs/superpowers/plans/2026-09-06-39-attractiveness-board-redesign-codex-brief.md`
rev 3 @ `7ca00a4` (2,093 lines).
**Spec:** `docs/superpowers/specs/2026-09-06-attractiveness-board-redesign-design.md` (D1–D12, owner-APPROVED).
**Code base:** `origin/main` @ `f83428d` (this branch adds only docs; `git diff f83428d 7ca00a4 -- options_researcher/ tests/ config.py` is empty).
**Receipts under audit:** `reports/2026-09-06-brief-39-adversarial-review-round1.md` (36 findings),
`reports/2026-09-06-brief-39-adversarial-review-round2.md` (26 findings: 3 BLOCKER, 8 MAJOR, 6 MEDIUM, 9 MINOR). Rev 3 claims all 26 applied.

## Method — what I actually did

Rounds 1 and 2 reasoned about the flag-on page. Round 3 **built it**. In gitignored
`.tmp/brief39-review/r3/repo` I made a scratch checkout (real copies of
`options_researcher/`, `tests/`, `config.py`, `pyrightconfig.json`; symlinks to
everything else) and applied the brief's Tasks 1–6 **verbatim from its own code
blocks** — the 14 fenced Python/CSS blocks were extracted programmatically from the
markdown, not retyped:

1. Task 1 constants inserted after `config.py:929`.
2. Task 2 legacy snapshot captured from the UNMODIFIED scratch tree (44,370 bytes).
3. Task 3 `board_lanes.py` written from brief block `:559-821`.
4. Task 4 `assemble(experiment_lanes=…)`, `_default_experiment_lanes`, shelf docstring, `_board` `setdefault`.
5. Task 5 `_symbol_panel_html` extraction (mechanical: hoist `evaluation_date`, dedent the loop body, `symbols_html += (` → `panel_html = (`, `return panel_html, symbol_name`) + all seven new builders + the `TYPE_CHECKING` import.
6. Task 6 `_render_result` flag branch (the `...today's :5700-5721 assembly...` placeholder filled from the real file) + `nav_html` + the CSS block into `_STYLE`.
7. Appended the brief's own new tests (blocks 4, 19, 22, 31) and ran them.

Then: `unittest` on every test file that touches the dashboard (baselined on `main`
first for the two extra failures), `uv run pyright` (full repo config, with
`board_lanes.py` added to `include`), `uv run ruff check`, byte-level `difflib` on
the flag-off page, and a re-read of every `file:line` the brief cites. No network,
no ledger touch, no full suite, nothing tracked modified.

Raw numbers are in "What I executed" at the end.

---

## Verdict: FAIL

Three BLOCKERs, four MAJORs. The pure module (Task 3) and the round-2 BLOCKER-1
and BLOCKER-3 fixes are genuinely correct — I ran the flag-on page and all 12
authority sentences survive verbatim, the details test passes, and the flag-off
page is byte-identical to the pre-change snapshot **once one line of the brief is
removed**. But the brief as written cannot be executed to green: it breaks its own
rollback proof, it violates a tracked AST isolation guard it never mentions, its
pyright gate still fails, its own tile test fails against its own code, and its
re-pin enumeration names 20 of the 44 tests that actually break in
`tests/test_attractiveness_dashboard.py`.

---

## BLOCKERS

### 1. BLOCKER — Task 6 Step 3 puts the new CSS in `_STYLE`, which breaks the byte-identity rollback proof; Task 5 Step 2 then sends Codex hunting in the wrong place

- **Brief:** Task 6 Step 3, "Add to `_STYLE` (colours from the existing variables
  only; no new palette)" (`:1657-1673`); Global Constraints "`config.BOARD_LANES_ENABLED = False`
  must reproduce today's HTML byte-for-byte on the layout fixture (rollback path,
  spec §4)" (`:130-132`); Architecture "when the flag is `False` the page is
  byte-identical to today (snapshot-tested)" (`:37-38`).
- **Evidence (executed):** `_STYLE` is emitted unconditionally at
  `options_researcher/attractiveness_dashboard.py:5726`
  (`f"<style>{_STYLE}{event_css}</style></head><body>"`), OUTSIDE the flag branch.
  With the brief applied verbatim, `LegacyByteIdentityTests` fails:
  flag-off render 46,356 bytes vs snapshot 44,370. `difflib` says the delta is a
  single insert of **exactly the 1,986-byte CSS block** and nothing else. Moving
  the block to a `_BOARD_STYLE` constant emitted only when the flag is on makes the
  flag-off page byte-identical (`True`), proving the extraction, Task 4's
  `experiment_lanes={}` default and Task 6's flag-off branch are all clean.
- **Why it matters:** Task 5 Step 2 tells Codex "If it fails, the extraction moved
  or reordered something — fix the extraction, never the snapshot" (`:1113-1114`).
  The failure appears at Task 6, one task after the instruction, and the extraction
  is innocent. The plausible executor repairs are both wrong: re-capture the
  snapshot (destroys the rollback proof, which the brief says must be captured
  BEFORE any renderer change) or start editing a byte-identical extraction.
- **Exact fix:** in Task 6 Step 3 replace "Add to `_STYLE`" with:
  "Add a new module-level `_BOARD_STYLE = \"\"\"…\"\"\"` next to `_STYLE` and emit it
  only under the flag — change `attractiveness_dashboard.py:5726` to
  `f\"<style>{_STYLE}{_BOARD_STYLE if config.BOARD_LANES_ENABLED else ''}{event_css}</style></head><body>\"`.
  `_STYLE` itself must not change one byte: it is inside the flag-off page and
  `LegacyByteIdentityTests` is the rollback proof."

### 2. BLOCKER (owner ruling) — Task 4 violates a tracked AST isolation guard that the brief never mentions, and Task 6 Step 4 then orders Codex to STOP

- **Brief:** Task 4 Step 3's `_default_experiment_lanes` (`:938-957`) does
  `from options_researcher import experiments_dashboard` and calls
  `experiments_dashboard.build_experiment_lanes(...)`. Task 6 Step 4 (`:1690-1694`):
  "Expected: failures only in `test_attractiveness_layout.py`,
  `test_attractiveness_dashboard.py`, `test_event_awareness.py` and
  `test_attractiveness_v3.py` … Any other file failing is a regression — STOP and report."
- **Evidence (executed):** `tests/test_experiments_baseline.py:92-93`
  `ExperimentBaselineTests.test_production_dashboard_has_no_experiment_imports`
  parses `attractiveness_dashboard.py` with `ast` and asserts **zero** imports or
  calls resolving to `options_researcher.experiments_dashboard*` or `exp_*`
  (`_experiment_boundary_violations`, `:40-88`). With the brief applied it fails:
  `['from options_researcher.experiments_dashboard', 'call options_researcher.experiments_dashboard.build_experiment_lanes'] is not false`.
  Baseline on `main`: `Ran 4 tests … OK`.
- **Why it matters:** (i) it is a **source-text** test, so none of the brief's three
  dispositions works — `mock.patch.object(config, "BOARD_LANES_ENABLED", False)`
  cannot make an import disappear; (ii) `tests/test_experiments_baseline.py` is not
  in the brief's Scope IN list and the word `experiments_baseline` appears nowhere
  in the brief or the spec; (iii) the file's own docstring is "Program-level
  isolation tests for display-only experiment wiring" — it is the mechanical
  enforcement of the 2026-08-09 authorization clause `.cursorrules` states as
  "Experiments remain isolated from registered hypotheses …, verdict authority,
  FIRE authority, live-order paths, paper-book mutation, and the default baseline
  ranking". Spec §4/D5 authorises the board to *use* the lane builders, but nothing
  in the spec or the brief authorises **weakening the isolation guard that forbids
  the production dashboard from importing them**. That is an owner call, not an
  executor call, and Codex will hit "STOP and report" with no guidance.
- **Exact fix:** get an owner ruling. Then add to the brief's Scope and to Task 4 an
  explicit disposition, e.g.: "`tests/test_experiments_baseline.py:93`
  `test_production_dashboard_has_no_experiment_imports` is an AST isolation guard
  that this brief deliberately renegotiates under spec §4/D5 (owner-ruled
  2026-09-06). Amend `_experiment_boundary_violations`' `prohibited()` to allow the
  single call site `_default_experiment_lanes` and nothing else — keep every other
  fixture in `test_boundary_rejects_direct_from_and_aliased_experiment_forms`
  (`:95-107`) green, and add a fixture proving any OTHER experiment import in the
  dashboard still violates." Also add the file to the Scope IN list and to Task 6
  Step 4's expected-failure list.

### 3. BLOCKER — `uv run pyright` still fails; round-2 BLOCKER-2(c)'s prescribed annotation is the wrong one

- **Brief:** Task 5 Step 1 (`:1096-1103`) "type the extraction `sec: dict`, …
  because the body calls `_rank_groups_for_display(sec[\"groups\"], tech=tech)` …
  Byte-identical must also be type-identical." Task 8 Step 3 (`:1953-1954`) gates on
  `uv run ruff check . && uv run pyright  # both clean`.
- **Evidence (executed):** with the brief applied verbatim,
  `uv run pyright` → **1 error**:
  `attractiveness_dashboard.py:5861:35 - error: Argument of type "Unknown | None" cannot be assigned to parameter "key" of type "str" in function "get" (reportArgumentType)`,
  on the extracted line `failure = failure_map.get(sec.get("symbol")) or failure_map.get("__calendar__")`.
  Cause: today `sec` is an element of `data["symbols"]` where `data: dict` is
  `dict[Unknown, Unknown]`, so `sec` is **Unknown** and `sec.get(...)` is Unknown
  (silenced by `reportUnknownArgumentType: none`). Annotating `sec: dict` makes
  `sec.get("symbol")` a *known* `Unknown | None`, and the `None` arm is reported.
  The brief's premise ("`sec` is an element of `data: dict`" ⇒ `dict`) is wrong;
  the element type is `Unknown`, not `dict`.
  Changing the annotation to `sec: Any` (adding `Any` to the existing
  `from typing import TYPE_CHECKING` at `:44`) → **0 errors** (re-run confirmed).
  The other three round-2 error classes ARE fixed: the `TYPE_CHECKING` import
  resolves `LaneBoard`/`LaneColumn`/`BoardRow` with no runtime evaluation (all three
  appear only in annotations under `from __future__ import annotations`, `:30`);
  `_seq()` covers every `Mapping`-value iteration in the new builders; the
  `isinstance(qm_context, Mapping)` guard is correct.
- **Exact fix:** in Task 5 Step 1 replace `sec: dict` with `sec: Any` and add
  "`from typing import TYPE_CHECKING, Any` at `:44`", with the reason: "the loop
  variable is `Unknown` today, not `dict` — `Any` is what makes the extraction
  type-identical; `dict` makes it stricter and breaks `failure_map.get(sec.get(\"symbol\"))`."
  Keep `context: dict | None` (verified correct against `_render_result`'s
  `context: dict | None` at `:5509` and `_symbol_context_html(symbol: str, context: dict | None)`
  at `:4638`).

---

## MAJORS

### 4. MAJOR — Task 7 Step 2's dashboard enumeration names 20 of the 44 tests that actually break; 24 are unnamed, including four fail-visible contracts

- **Brief:** Task 7 Step 2 (`:1737-1759`) enumerates for
  `tests/test_attractiveness_dashboard.py`: `:2239`; the freshness slices
  `:3089, :3097, :3130, :3162, :3272, :3291, :3304`; the order pins
  `:2036, :2061, :2112, :2145, :2152, :2155, :2171, :2632-2633, :3067-3075, :3253-3264, :3317, :3341`;
  and `:3191-3193`. It closes with "Any failure NOT in this list gets the same
  (a)/(b)/(c) treatment" — but Task 6 Step 4 has already told Codex to STOP on
  anything outside four files, and the (a)/(b)/(c) rule does not resolve the cases below.
- **Evidence (executed):** flag-on run of `tests/test_attractiveness_dashboard.py`:
  **203 tests, 37 failures + 7 errors = 44 broken.** Mapping each to its `def` line,
  **24 fall in no enumerated range**:

| line | test | first failing assertion |
|---|---|---|
| 291 | `RenderTests.test_render_has_label_and_no_external_assets` | panel content gone |
| 301 | `RenderTests.test_render_shows_empty_state_line` | " |
| 305 | `RenderTests.test_render_shows_grade_badges` | `'yield · AMBER' not found` |
| 310 | `RenderTests.test_render_escapes_dynamic_text` | " |
| 338 | `RenderTests.test_render_pmcc_note_and_leaps_countdown` | " |
| 1240 | `StrategySectionRankingTests.test_render_numbers_and_orders_strategy_sections` | `ValueError: substring not found` |
| 1307 | `PinnedPicksTests.test_render_pinned_strip_labeled_not_ranked` | `'no eligible liquid card' not found` |
| 1360 | `BlockedSectionsTests.test_display_only_chip_is_pinned_on_success_and_blocked_rows` | |
| 1393 | `HypothesisEvidencePanelTests.test_panel_escapes_all_values_and_keeps_intraday_separate` | `'<details class="hypothesis-evidence">' not found` |
| 1591 | `LoadContextTests.test_rendered_context_freshness_has_all_evidence_derived_states` | |
| 1725 | `V2RenderTests.test_hero_with_matched_context_pick` | |
| 1733 | `V2RenderTests.test_hero_unmatched_pick_warns_and_discloses_disagreement` | |
| 1803 | `V2RenderTests.test_provenance_label_on_every_narrative_surface` | |
| 1825 | `V2RenderTests.test_symbol_panel_shows_technicals_line_and_news` | `'above all MAs' not found` |
| 1831 | `V2RenderTests.test_render_survives_sections_without_technicals` | |
| 1841 | `V2RenderTests.test_cards_render_in_grid_with_collapsed_ladder_and_bbb` | |
| 2332 | `ContextLaneRenderTests.test_context_membership_is_independent_of_event_view` | |
| 2358 | `ContextLaneRenderTests.test_render_result_selects_tracker_arms_once_and_returns_rendered_membership` | `ValueError: substring not found` |
| 2642 | `ContextLaneRenderTests.test_selected_blocked_composite_stays_in_slot_with_reason` | |
| 2660 | `ContextLaneRenderTests.test_flag_on_shows_zero_credit_for_vetoed_down_and_mixed_context` | |
| 2687 | `ContextLaneRenderTests.test_scoring_exception_renders_loud_failure` | `'CONTEXT LANE FAILED — RuntimeError' not found` |
| 3551 | `SchwabFreshnessPageDateTests.test_section_states_its_source_and_that_the_price_is_a_1545_mid` | |
| 3561 | `SchwabFreshnessPageDateTests.test_refused_fresh_chain_is_visible_not_silent` | `'no verified 15:45 spot for 2026-08-14' not found` |
| 3691 | `FailClosedFeatureTests.test_unavailable_iv_rank_is_words_not_a_number` | |
| 3698 | `FailClosedFeatureTests.test_unavailable_features_are_named_with_their_reason` | |
| 3705 | `FailClosedFeatureTests.test_absent_scenario_table_says_why` | `'Scenario table unavailable' not found` |
| 3720 | `FailClosedFeatureTests.test_atm_iv_from_the_fresh_session_is_shown` | |

  (27 rows; `:2036` and `:3067-3075` etc. cover the other 20 — one enumerated anchor,
  `:2036`, sits inside `test_movement_lane_sits_between_mechanical_top_three_and_retained_comparison`
  (`:2034`), which **passes** under the flag.)
- **Why it matters:** these are not position pins. The dominant root cause is new and
  unstated: under the flag a symbol that is on no lane and is not pinned renders **no
  panel at all**, so every test asserting panel CONTENT for a non-pick symbol loses its
  subject. Four of them — `FailClosedFeatureTests` (×4) and `SchwabFreshnessPageDateTests`
  (×2) — are fail-visible contracts ("Scenario table unavailable", "no verified 15:45
  spot"), i.e. exactly the class spec §6 invariant 7 protects. Legacy-wrapping them, the
  disposition the brief's rule (c) implies, moves the whole fail-visible rendering
  contract into the rollback path and leaves it untested on the page that actually ships.
- **Exact fix:** add the 24 tests above to Task 7 Step 2 with explicit dispositions, and
  add one paragraph to the brief stating the root cause and the ruling: "a section whose
  symbol is on no lane and is not pinned renders no panel under the flag (spec §2.5/D4).
  Tests asserting panel CONTENT must be re-pointed at a fixture whose symbol IS a board
  row (preferred — keeps the contract on the shipped page), and only legacy-wrapped when
  the surface itself is gone. The `FailClosedFeatureTests` and `SchwabFreshnessPageDateTests`
  fail-visible assertions must stay flag-ON."

### 5. MAJOR — a brief-supplied test fails against the brief's own implementation (`5 != 4`)

- **Brief:** Task 5 Step 3 (`:1224`)
  `self.assertEqual(html.count('<div class="tile'), 4)   # spec §2.2: always four tiles`.
- **Evidence (executed):** `test_position_tiles_say_so_when_the_book_is_unreadable` FAILS:
  `AssertionError: 5 != 4`. `_position_tiles_html` wraps its four tiles in
  `<div class="tiles">` (brief `:1310`, `:1330`), and the substring `<div class="tile`
  is a prefix of `<div class="tiles">` — so the wrapper is counted too.
- **Why it matters:** the brief tells Codex "The TESTS are the contract … if the
  implementation disagrees, fix the code" (`:827`). Obeying that here means adding a
  fifth-tile-removing edit or dropping the wrapper — both wrong. Same failure class as
  round-2 BLOCKER-3.
- **Exact fix:** `self.assertEqual(html.count('<div class="tile"') + html.count('<div class="tile '), 4)`,
  or simply `self.assertEqual(html.count('<div class="k">'), 4)`.

### 6. MAJOR — the D10 acceptance test still cannot fail, and the brief does not resolve the spec's own two definitions of "visible"

- **Brief:** Task 8 Step 1 (`:1898-1930`): `_visible_html` "drop every symbol panel and
  the diagnostics drawer … Panels that render force-open … are counted as closed here on
  purpose"; the test asserts `visible.count("<h2") <= 8`, `visible.count("<summary") <= 20`,
  and `assertGreaterEqual(forced_open, 2)   # VST and AMZN are pinned`.
- **Evidence (executed) on the brief's own 8-symbol acceptance fixture
  `_board(["NVDA","AMZN","MSFT","PLTR","SMCI","CRWV","CEG","VST"])`:**
  - flag-on page: 51,617 bytes, 15 `<h2>`, 19 `<summary>`.
  - panels rendered: **6**, of which **6 are force-open and 0 are closed** (`_board`'s
    `today="2026-08-25"` marks all eight symbols stale — measured
    `stale_symbols = ['AMZN','CEG','CRWV','MSFT','NVDA','PLTR','SMCI','VST']` —
    so `_panel_status` (`:806-827`) opens every one).
  - `_visible_html` therefore strips 100% of the panel content: visible = 26,855 bytes,
    **2 `<h2>`, 0 `<summary>`** against targets of ≤ 8 and ≤ 20.
  - `forced_open` = **6**, so `assertGreaterEqual(forced_open, 2)` is trivially true and
    the brief's stated rationale ("VST and AMZN are pinned") is wrong on its own fixture.
  - Measuring the way spec §8 actually words it — "`<h2>` outside any **closed**
    `<details>`", i.e. dropping only `<details class="panel symbol-panel">` with no
    ` open` — gives 42,201 bytes, **8 `<h2>`, 18 `<summary>`**: exactly at both limits.
- **Why it matters:** D10 exists because round 1 killed the byte target. An acceptance
  test whose measured values are 2 and 0 against limits of 8 and 20, on a fixture where
  no panel is closed, is not an acceptance test. Separately, spec §1/D10 ("with fold-outs
  closed") and spec §8 ("outside any closed `<details>`") define "visible" oppositely;
  the brief silently adopts the first and never names the conflict, which CLAUDE.md
  requires it to do ("If sources conflict, say so instead of picking one silently").
- **Exact fix:** (a) add one sentence to Task 8 Step 1 and to the spec §8 line naming the
  conflict and the ruling; (b) assert BOTH numbers — keep the counterfactual assertion and
  add `visible_actual` (strip only closed panels + the drawer) with the same ≤ 8 / ≤ 20
  limits, which the fixture meets at 8 and 18; (c) replace the `forced_open >= 2` comment
  with the measured truth: "on this fixture every symbol is STALE, so all rendered panels
  are force-open; the count is REPORTED, and the second measure above is what makes the
  test able to fail."

### 7. MAJOR — `uv run ruff check .` (Task 8 Step 3 gate) fails on two import blocks the brief supplies

- **Evidence (executed):**
  - `options_researcher/attractiveness_dashboard.py:5563:5 I001` — brief `:1243`
    `from options_researcher.schwab_chain_view import CHAINS_ABSENT, CHAIN_SOURCE, CONVENTION_LABEL`;
    ruff wants `CHAIN_SOURCE, CHAINS_ABSENT, CONVENTION_LABEL`.
  - `tests/test_attractiveness_dashboard.py:3874:9 I001` — brief `:1192`
    `from options_researcher.schwab_chain_view import CHAINS_ABSENT, CHAIN_SOURCE`;
    ruff wants `CHAIN_SOURCE, CHAINS_ABSENT` (confirmed with `ruff check --diff`).
  `I` is selected at `pyproject.toml:40`.
- **Exact fix:** reorder both to `CHAIN_SOURCE, CHAINS_ABSENT[, CONVENTION_LABEL]` in the
  brief's code blocks. (Round-2 MAJOR-9's two instances ARE fixed: the Task 1 test block
  and the E402 placement both pass ruff in my run.)

---

## MEDIUM

8. **MEDIUM — `_position_tiles_html` emits ONE tile on the branch every injected fixture
   hits, while its own docstring says "Exactly four stat tiles (spec §2.2)".**
   Brief `:1300-1303`: `if not isinstance(positions, Mapping): return '<div class="tiles"><div class="tile bad">…Positions…UNREAD…'`.
   Measured on the disclaimer fixture `_board(["VST","AAA"])` (no `open_positions` key,
   because `assemble` only loads the book on the real path, `:1745`): the flag-on page
   contains **2** `<div class="tile` matches = the wrapper + one tile. Round-2 MEDIUM 17
   folded the fifth tile away but left this branch. Fix: emit four tiles in that branch
   too (first = `Open option / UNREAD / open_positions not assembled`, the other three
   `none`), or amend the docstring and spec §2.2.

9. **MEDIUM — the `LANE BOARD FAILED` fallback drops an authority sentence.**
   Executed: patching `board_lanes.build_lane_board` to raise, the flag-on page renders
   the loud notice but **1 of the 12 `_SENTENCES` is missing** — "owner-pinned visibility
   — not ranked; these cards do not compete with or reorder the Top-5 shortlist."
   (`_pinned_html` is not emitted and the agreement-table footnote never runs).
   `test_disclaimers_are_present_verbatim` would fail in that state. Spec §6.4 states the
   invariant unconditionally. Fix: emit the two table footnotes from the fallback branch
   too, or state the exception in Global Constraints. (The `_open_slots_notice_html`
   double-print of round-2 MINOR 23 IS fixed — measured exactly 1 open-slot notice.)

10. **MEDIUM — names with a section but no lane membership disappear from the page, and
    nothing tests it.** On the 8-symbol acceptance fixture, `PLTR` and `SMCI` have
    sections and are STALE, but are not board rows: measured panels are
    `['AMZN','CEG','CRWV','MSFT','NVDA','VST']` and both names survive only inside the
    status strip's stale list. That is D4 working as designed, but spec §6 invariant 7
    ("DATA_BLOCKED / stale names remain fail-visible") is then satisfied by a comma-list
    entry rather than a visible panel, and the brief never says so. Fix: add one sentence
    to the brief and one test asserting a stale non-pick name is still NAMED on the page.
    (`_blocked_html` remains in the flag-on body, so DATA_BLOCKED records are unaffected.)

11. **MEDIUM — the sentence count is wrong, in the prose and in a test name.**
    `AuthorityWordingSurvivesLayoutTests._SENTENCES`
    (`tests/test_attractiveness_layout.py:434-454`) has **12** entries, not thirteen
    (executed: `COUNT = 12`). So brief `:107` "All thirteen sentences", `:111` "Ten live in
    sections that still render" (it is nine), and the Task 6 test name
    `test_all_thirteen_disclaimers_survive_with_flag_off_too` (`:1564`) are all off by one.
    The test itself iterates `_SENTENCES`, so it is correct in behaviour — but a brief that
    miscounts the contract it is auditing invites the next reviewer to re-derive it.
    Fix: "All twelve sentences … Nine live in sections that still render"; rename the test
    `test_every_disclaimer_survives_with_flag_off_too`.

12. **MEDIUM — three cite regressions introduced or left in rev 3.**
    - `:112-113` "the pinned-strip sentence … (`:4705-4706`)" — `:4705` is
      `'<div class="eyebrow">CORE NAMES</div>'` and `:4706` is the `ALWAYS SHOWN` `<h2>`.
      The sentence is at **`:4707-4708`**. (Round 2 had it right at `:4707`.)
    - Scope `:71` "the publish-path digest (`pick_tracker.py:52`, bound at
      `attractiveness_dashboard.py:5876`)" — `:5876` computes
      `render_source_rows_sha256`; the bind is **`:5877`**. (Round-2 MEDIUM 12 said `:5877`.)
    - Task 4 Files `:883` "`tests/test_attractiveness_layout.py:44-58` (`_board` default)"
      — `_board` is **`:54-69`**, as Task 4 Step 3 itself says. Round-2 MEDIUM 13's
      sub-item is applied in the step but not in the Files header.

13. **MEDIUM — Task 7's dispositions are prescribed for five tests that pass under the
    flag, which silently reduces flag-on coverage.** Measured passes:
    `test_panel_summary_is_one_line_with_source_asof_and_grade` (`:286`),
    `test_frozen_eod_panels_name_their_source_in_the_summary` (`:296`),
    `test_composite_board_is_one_table_with_every_label_preserved` (`:337`),
    `test_blocked_angle_reason_is_still_printed` (`:364`),
    `test_symbol_panels_precede_the_drawer` (`:424`), plus dashboard `:2036`'s test.
    Only `test_clean_panels_are_closed_except_owner_pinned_symbols` (`:277`) of the four
    `SymbolPanelCollapseTests` actually fails, and the class's fourth test
    (`test_symbol_heading_text_is_unchanged_inside_the_panel`, `:304`) is not enumerated
    at all. Fix: add "legacy-wrap ONLY a test the executor has observed to fail; a passing
    test stays flag-on", and add `:304` to the list.

---

## MINOR

14. Transient ruff failure between Task 2 and Task 7: Task 2 Step 2 (`:311-314`) adds
    `import contextlib` "NOW" but nothing uses it until Task 7, so
    `tests/test_attractiveness_layout.py:10:8 F401 'contextlib' imported but unused`
    (executed). No brief step runs ruff in that window, but `.pre-commit-config.yaml`
    registers `uv run ruff check --fix`, which would **delete** the import if the hook is
    ever installed (it is not installed today: `.git/hooks/pre-commit` does not exist).
    Say so in Task 2, or add contextlib at Task 7 inside the top block by editing the block.
15. Task 5 Step 1 item 2 (`:1080-1105`) says "Move the loop body … unchanged" but the body
    contains `symbol_names.append(symbol_name)` and `symbols_html += (`, neither of which
    exists in the function scope. The new loop at Step 1 item 3 makes the intent
    inferable; state it explicitly ("drop the `symbol_names.append` line and rename
    `symbols_html += (` to `panel_html = (`").
16. `:117` cites `_CONTEXT_LANE_DISCLAIMER` as `:4442-4446`; the constant runs `:4442-4447`
    (closing paren). Harmless.
17. Task 7 Step 3 (`:1781`) says `card_fragment` is `:396-410`; it runs to `:413`.
18. Brief `:32` "782,263 bytes" and `:47` "782 KB" vs spec §1 "771 KB" — the two documents
    quote different sizes for the same 2026-09-04 build. Pick one.

---

## Verified correct (so round 4 does not re-litigate)

Executed, not reasoned:

- **All 12 `_SENTENCES` are present verbatim on the flag-on page** (`12 / 12`), and
  `test_disclaimers_are_present_verbatim` passes untouched. The three carried sentences
  are byte-exact against `_SENTENCES` (em dashes included), and
  `_esc(_CONTEXT_LANE_DISCLAIMER) == _CONTEXT_LANE_DISCLAIMER` (no `&<>"'` in it).
  Emitter trace for the nine that survive: `_composite_html` (`:4774`) → sentences 1–2;
  `_registered_bets_tracker_html` (`:4956`) → 3; `_pick_tracker_html` (`:5426`) → 4;
  `_qm_movement_lane_html` (`:4339`) → 5, 7; `_qm_hero_html` (`:4265`) → 5, 6;
  `_quant_want_html` (`:4563`) → 11; `_render_result` footer (`:5740`) → 12. All eleven
  drawer entries in the brief's flag-on list render on the fixture. Round-2 BLOCKER 1 is
  genuinely closed.
- **Round-2 BLOCKER 3 is closed.** `test_details_render_only_for_table_names` passes.
  Measured on `_board(["NVDA","AMZN","MSFT"])`: `select_top_picks` →
  `['AMZN','MSFT','NVDA']` (all three eligible, all three stale), `blocked = []`,
  `pinned_picks` → `VST` (no pick) + `AMZN`. So `rendered ⊆ names_on_table`,
  `NVDA ∈ rendered`, `VST ∈ names_on_table`, `VST ∉ rendered` all hold.
  The anchor literal `<div class="symbol-anchor" id="symbol-X"` is exact (`:5635`), and
  `<details class="panel symbol-panel" open>` is exact (`:5636` + `open_attr` at `:5601-5602`).
- **All ten of the brief's own new layout tests pass** on a verbatim implementation
  (`LaneBoardLayoutTests` ×7, `LegacyByteIdentityTests`, `LaneBoardParityAndSizeTests` ×2),
  and 7 of 8 `LaneBoardRenderTests` (the 8th is MAJOR 5).
- **Spec §6 invariants 1 and 3 hold**: `test_selection_snapshot_and_source_row_hashes_are_identical_flag_on_and_off`
  passes — ranking, snapshot and source-row hashes are byte-identical flag on vs off.
- **Round-2 MAJOR 6 closed**: `_DRAWER_INPUTS` makes all six `_DRAWER_SECTIONS` render and
  the five relocated items land after them (`test_relocated_content_is_appended_after_the_six_drawer_sections` passes).
- **Round-2 MAJOR 5 closed**: `_panel_slice` is correct on all four shapes I fed it
  (mid-page panel, last panel before the drawer, no-drawer fragment, single panel). Only
  `:277` of the four `SymbolPanelCollapseTests` actually inverts.
- **Round-2 MAJOR 7's CSS content is correct**: `--surface-soft` (`:2320`), `--line`
  (`:2323`), `--good` (`:2326`), `--watch` (`:2329`), `--bad` (`:2332`) all exist inside
  `:root` (`:2316-2341`); `grep 'class="chip'` over the renderer returns **nothing**, so
  the new base `.chip` rule cannot restyle `.meta-chip` / `.evidence-chip` / `.event-chip`
  (distinct class tokens). Only the CSS's *placement* is wrong (BLOCKER 1).
- **Round-2 MAJOR 10 closed**: `tests/test_event_awareness.py` lift ranges verified exact
  — `card()` `:313-338`, `symbols` `:340`, `data` `:341-368`, `view` `:374-391`,
  `chips()` `:393-394`, patches `:415-418`, render `:419`.
- **Round-2 MAJOR 11 closed and accurate**: `research/hashing.py:132`
  `DIAGNOSTIC_SOURCE_PATHS_V2 = SOURCE_HASH_PATHS + ("options_researcher", "tools")`,
  walked as a directory via `path.is_dir()` → `rglob("*.py")` (`:99-101`);
  `options_researcher/h7_data_gate.py:748`
  `if receipt.get("source_hash") != diagnostic_source_hash():` — both exact.
- **Round-2 MEDIUM 15 closed**: the D5 quote in the brief's Scope is verbatim identical to
  spec lines 177-181.
- **Round-2 BLOCKER 2(a)(b)(d) closed**: `TYPE_CHECKING` import resolves the three names
  with no runtime evaluation; `_seq()` covers every `Mapping`-value iteration; and
  `enrich_qm_context_with_candidates(data, None)` returns **`None`** (measured), so the
  `isinstance` guard fires and the QM column renders
  `ranking · as of 2026-08-25 · UNAVAILABLE:no QM context` — exactly as
  `lane_from_qm(None)` promises.
- Removed-surface anchors are all real strings today: `id="context-aware-top-5"`
  (`:4482`, `:4552`), `CONTEXT-AWARE SHORTLIST` (`:4483`), `class="sticky-nav"` (`:5480`),
  `<h2>QM MOVEMENT LANE</h2>` (`:4397`), and `_pinned_html`'s
  `f'<h2>{names} — ALWAYS SHOWN</h2>'` (`:4706`) with
  `names = " / ".join(...)` (`:4672`) over `config.PICK_PINNED_SYMBOLS = ["VST","AMZN"]`
  (`config.py:660`) ⇒ `VST / AMZN — ALWAYS SHOWN`. No test asserts the full old eyebrow as
  a whole string or counts `TOP 5 PICKS TODAY` / `hero-grid` occurrences, so the eyebrow
  change to `Daily shortlist · TOP 5 PICKS TODAY · agreement across lanes` and the
  `hero-grid open-slots` wrapper are safe (`tests/test_event_awareness.py:434` uses the old
  eyebrow as a prefix index and is inside the test Task 7 replaces).
- Every other `file:line` I re-read is exact: `config.py` `:650 / :660 / :674 / :690 / :929 / :932`;
  `attractiveness_dashboard.py` `:30, :38, :50, :357, :438, :489, :540, :576, :690, :806, :1058-1091,
  :1412, :1485, :1745, :1751, :1777, :1784, :1866, :3024, :3065, :3192, :4104, :4116, :4200-4203,
  :4212-4213, :4215, :4281, :4450, :4497, :4563, :4593, :4638, :4774, :5364, :5384, :5493,
  :5506, :5524-5533, :5534, :5539, :5544, :5545, :5548, :5550, :5554, :5594, :5601-5602,
  :5633-5636, :5664, :5690-5721, :5712-5719, :5737, :5740`;
  `experiments_dashboard.py:250-262`; `top3_snapshot.py:83`; `pick_tracker.py:52`;
  `tests/test_attractiveness_layout.py` `:10-19, :88-130, :165, :179, :191, :200, :208, :220,
  :277, :286, :296, :314, :326, :337, :364, :374-382, :405, :416, :424, :434-454, :456, :497`;
  `tests/test_attractiveness_dashboard.py:2-7`; `tests/test_event_awareness.py:5-13`.
- Round-2 MINOR 18–26 are all applied and correct: the extracted body genuinely needs no
  `data` parameter (proved by compiling and running it); the brief's own commands use
  `Path(...).write_text/read_text`; the placement of `_symbol_panel_html` is stated;
  `event_css` probes only flag-on fragments; the double-render and
  `build_experiment_lanes` costs are noted; the fallback prints one open-slot notice;
  `hero-grid` wraps the notice; `_AGREE_BAR_PX = 14` carries provenance; and Task 8's
  local-overwrite note is present. Round-2 MEDIUM 12, 14 and 16 are applied and correct.
- No ledger write, registration, authority flip, live-order path, network or provider call,
  JavaScript, or owner-provenance number is introduced anywhere in rev 3.
  `FEASIBILITY_SOURCE_PATHS` remains untouched. Zero `<script` on the flag-on page (verified).

---

## Round-2 findings status (all 26)

| # | Sev | Round-2 finding | Status in rev 3 |
|---|---|---|---|
| 1 | BLOCKER | Flag-on page drops 3 disclaimer sentences | **Applied, correct** — verified 12/12 on the rendered flag-on page; three carried byte-exactly. (Prose still says "thirteen"/"Ten" — MEDIUM 11.) |
| 2 | BLOCKER | pyright cannot pass; 4 error classes | **Partial** — (a)(b)(d) correct; (c) `sec: dict` is the WRONG annotation and still yields 1 error → BLOCKER 3 |
| 3 | BLOCKER | `test_details_render_only_for_table_names` unsatisfiable | **Applied, correct** — test passes; fixture measured |
| 4 | MAJOR | Re-pin enumeration incomplete incl. golden SHA-256 | **Partial** — five `PositionsAndRiskFirstTests` anchors and `:2239` and v3 all correct; 24 of 44 dashboard failures still unnamed, and `tests/test_experiments_baseline.py` missing entirely → MAJOR 4 + BLOCKER 2 |
| 5 | MAJOR | Panel ORDER inversion | **Applied, correct** — `_panel_slice` verified on four shapes |
| 6 | MAJOR | Drawer test raises on its own fixture | **Applied, correct** — `_DRAWER_INPUTS` makes the six render |
| 7 | MAJOR | CSS: undefined `--surface-2`, no base `.chip` | **Applied for content, wrong for placement** — variables and `.chip` verified; putting it in `_STYLE` breaks byte-identity → BLOCKER 1 |
| 8 | MAJOR | D10 measure does not measure what D10 rules | **Partial** — option (ii) taken (counterfactual + reported count) but still unfalsifiable on the brief's own fixture (0 closed panels; 2 vs ≤8, 0 vs ≤20), and the spec §8 conflict is unstated → MAJOR 6 |
| 9 | MAJOR | ruff fails twice (I001, E402) | **Partial** — both round-2 instances fixed and verified; two NEW I001s in brief-supplied imports → MAJOR 7; plus transient F401 → MINOR 14 |
| 10 | MAJOR | Wrong lines for the event fixture lift; missing patch | **Applied, correct** — all five ranges + `:415-418` + `:419` verified |
| 11 | MAJOR | Source-hash consequence unstated | **Applied, correct** — both cites verified, directory-walk claim true |
| 12 | MEDIUM | False "pick tracker" claim in a shipped docstring | **Applied** — clause removed. (Scope cite regressed to `:5876` → MEDIUM 12) |
| 13 | MEDIUM | Cite drift (8 items) | **Mostly applied** — `:5544/:5545/:5539/:5534/:5524-5533/:1081-1091/:10-19/max_asof` all now exact; `:44-58` for `_board` remains, and `:4705-4706` / `:5876` are new drift → MEDIUM 12 |
| 14 | MEDIUM | False "latent NameError" Inference | **Applied, correct** |
| 15 | MEDIUM | D5 authority not carried into the brief | **Applied, correct** — quote verbatim vs spec `:177-181` |
| 16 | MEDIUM | Naive `</details>` slice in a brief-supplied test | **Applied, correct** — anchor/drawer slice |
| 17 | MEDIUM | Spec says four tiles; code can emit five | **Partial** — fifth tile folded into "Open option", but the no-`open_positions` branch emits ONE tile against a docstring claiming four, and the brief's own 4-tile assertion fails → MAJOR 5 + MEDIUM 8 |
| 18 | MINOR | Unused `data` parameter | **Applied, correct** (proved by running the extraction) |
| 19 | MINOR | File-handle leaks in the brief's commands | **Applied** |
| 20 | MINOR | Task 5 never says where `_symbol_panel_html` goes | **Applied** |
| 21 | MINOR | Flag-on `event_css` probes absent fragments | **Applied** |
| 22 | MINOR | Panels rendered twice per build | **Applied** (noted in Task 6 Step 3 and the PR body) |
| 23 | MINOR | Fallback double-prints the open-slot notice | **Applied, correct** — measured exactly 1 |
| 24 | MINOR | Open-slot card has no `hero-grid` parent | **Applied** |
| 25 | MINOR | Bare `* 14` pixel constant | **Applied** — `_AGREE_BAR_PX` with provenance |
| 26 | MINOR | Task 8 overwrites local `.tmp` files | **Applied** |

---

## What I executed and raw results

Scratch only, under gitignored `.tmp/brief39-review/r3/`. Nothing tracked was modified;
no network, no ledger, no full suite.

```
# baseline, main checkout
uv run python -m unittest discover -s tests -p 'test_attractiveness_layout.py'
  -> Ran 27 tests in 0.153s  OK
PYTHONPATH=tests ... select_top_picks(_board(['NVDA','AMZN','MSFT']))
  picks        ['AMZN', 'MSFT', 'NVDA']
  watch picks  ['AMZN', 'MSFT', 'NVDA']
  stale        ['AMZN', 'MSFT', 'NVDA']
  blocked      []
  pinned recs  [('VST', False), ('AMZN', True)]
  symbols ord  ['NVDA', 'AMZN', 'MSFT']
AuthorityWordingSurvivesLayoutTests._SENTENCES  -> COUNT = 12
_esc(_CONTEXT_LANE_DISCLAIMER) == _CONTEXT_LANE_DISCLAIMER  -> True
uv run python -m unittest ... test_experiments_baseline.py        -> Ran 4  OK
uv run python -m unittest ... test_short_positioning_boundaries.py -> Ran 10 OK

# scratch repo, brief Tasks 1-6 applied verbatim (flag default True)
Task 2 snapshot capture                       -> 44370 bytes
flag-OFF vs snapshot, CSS in _STYLE            -> False; 46356 vs 44370
  difflib opcodes: one insert of 1986 bytes == the Task 6 CSS block, nothing else
flag-OFF vs snapshot, CSS gated behind flag    -> True   (byte-identical)
flag-ON page order (3-sym): status-strip 18934 < tiles 19442 < agreement-table 20137
                            < pick-details 25158 < diagnostics 33141;  'LANE BOARD FAILED' absent

uv run pyright  (sec: dict, brief as written)  -> 1 error
  attractiveness_dashboard.py:5861:35 - error: Argument of type "Unknown | None"
    cannot be assigned to parameter "key" of type "str" in function "get" (reportArgumentType)
uv run pyright  (sec: Any)                     -> 0 errors, 0 warnings, 0 informations

uv run ruff check <5 changed files>            -> 3 errors
  options_researcher/attractiveness_dashboard.py:5563:5 I001   (brief :1243)
  tests/test_attractiveness_dashboard.py:3874:9 I001           (brief :1192)
  tests/test_attractiveness_layout.py:10:8 F401 'contextlib' unused
  ruff check --diff -> wants `CHAIN_SOURCE, CHAINS_ABSENT`

# flag-on failure enumeration (pre-existing tests)
test_attractiveness_layout       Ran 27  FAILED (failures=7, errors=6)   [13]
test_attractiveness_dashboard    Ran 203 FAILED (failures=37, errors=7)  [44 ; 24 unnamed]
test_attractiveness_v3           Ran 24  FAILED (failures=1)             [:278, enumerated]
test_event_awareness             Ran 16  FAILED (errors=1)               [:311, enumerated]
test_experiments_baseline        Ran 4   FAILED (failures=1)             [UN-ENUMERATED, outside the 4 named files]
  -> test_production_dashboard_has_no_experiment_imports:
     ['from options_researcher.experiments_dashboard',
      'call options_researcher.experiments_dashboard.build_experiment_lanes'] is not false
test_attractiveness, test_composite_signals, test_display_rank, test_oi_change_line,
test_qm_dashboard, test_ritual_receipt, test_schwab_freshness_gather,
test_daily_ritual_provenance, test_research_context_assemble   -> all OK
(test_short_positioning_boundaries' 5 failures are an artifact of my symlinked scratch
 checkout — git cannot resolve `.gitignore` through it; it is OK on main and in-scratch-only.)

# brief-supplied new tests
LaneBoardLayoutTests (7) + LegacyByteIdentityTests + LaneBoardParityAndSizeTests (2)
  -> Ran 10 in 0.102s  OK      (with the CSS gated; see BLOCKER 1)
LaneBoardRenderTests -> Ran 8  FAILED (failures=1)
  test_position_tiles_say_so_when_the_book_is_unreadable: AssertionError: 5 != 4

# D10 measurement, brief's own 8-symbol acceptance fixture
flag-off page                 60944 bytes, 18 <h2>, 42 <summary>
flag-on  page                 51617 bytes, 15 <h2>, 19 <summary>
panels rendered 6 : force-open 6, closed 0     (all eight symbols STALE)
sections dropped entirely     {'PLTR', 'SMCI'}  (named only in the status strip)
_visible_html (brief's counterfactual)  26855 bytes,  2 <h2>,  0 <summary>   [targets <=8, <=20]
"outside any closed <details>" (spec §8)  42201 bytes,  8 <h2>, 18 <summary>
forced_open = 6  (the brief's comment predicts 2)

# LANE BOARD FAILED fallback (build_lane_board patched to raise)
'LANE BOARD FAILED' present: True
disclaimers missing in fallback: 1
  - "owner-pinned visibility — not ranked; these cards do not compete with or reorder the Top-5 shortlist."
open-slot notice count: 1   (no double print)

# flag-on disclaimer check, test_disclaimers_are_present_verbatim fixture
12 / 12 sentences present;  tiles emitted on that fixture: 1 (+1 wrapper)

# qm_context guard
enrich_qm_context_with_candidates(data, None) -> NoneType, isinstance(_, Mapping) = False
QM column header -> "ranking · as of 2026-08-25 · UNAVAILABLE:no QM context"
```
