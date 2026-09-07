# Brief 39 — independent adversarial review, round 4 (2026-09-06)

**Reviewer:** Opus, adversarial round 4 (independent; read-only on tracked files).
**Target:** `docs/superpowers/plans/2026-09-06-39-attractiveness-board-redesign-codex-brief.md`
rev 4 @ `69819da` (2,327 lines).
**Spec:** `docs/superpowers/specs/2026-09-06-attractiveness-board-redesign-design.md`
(D1–D12 owner-APPROVED; D13 + I1 in the trailing "Pending owner rulings" section, unruled).
**Code base:** `origin/main` @ `f83428d` (this branch adds only docs).
**Receipts under audit:** `reports/2026-09-06-brief-39-adversarial-review-round{1,2,3}.md`.
Rev 4 claims all 18 round-3 findings (3 BLOCKER, 4 MAJOR, 6 MEDIUM, 5 MINOR) applied.

## Method — what I built and ran

I did **not** reuse round 3's scratch build. Rev 4 changes the CSS placement, the panel
open-state input (I1), the isolation guard and the Task 3 row rule, so I rebuilt from zero:

1. Two gitignored scratch overlays under `.tmp/brief39-review/`:
   `r4/repo` (real copies of `options_researcher/`, `tests/`, `config.py`,
   `pyrightconfig.json`, a real local `.tmp/`; symlinks to everything else) and
   `r4base/repo` (the same overlay, unmodified — the baseline).
2. The brief's **37 fenced blocks were extracted programmatically** from the markdown
   (`b00…b36`), not retyped.
3. Tasks 1–6 applied verbatim: constants after `config.py:929`; Task 2 snapshot captured
   from the UNMODIFIED renderer (twice, `cmp`-identical); `board_lanes.py` from block `b08`;
   `assemble(experiment_lanes=…)` + `_default_experiment_lanes` + shelf docstring + the
   `_board` `setdefault`; the D13-A guard replacement over
   `tests/test_experiments_baseline.py:92-93`; the `_symbol_panel_html` extraction
   (hoist `evaluation_date`, drop `symbol_names.append`, `symbols_html += (` → `panel_html = (`,
   dedent, `sec: Any`) + all builders; the Task 6 flag branch with the
   `...today's :5700-5721 assembly...` placeholder filled from the real file;
   `_BOARD_STYLE` placed after `_STYLE`; `board_css` at the `<style>` line; `nav_html`.
4. Task 8's `_visible_html` + parity/acceptance tests, and the `_fresh_board` lift the
   brief describes but does not supply as code.
5. Task 7 Step 3's fixture lift performed programmatically from the cited line ranges, then
   the brief's two replacement event tests run.
6. Ran: the brief's own new tests; every test file that touches the dashboard, flag-on and
   on the pristine baseline; `pyright` (repo config, `--pythonpath` at the repo venv);
   `ruff check`; byte-diff of the flag-off page; the D10 measurements; a recipe-(d) harness
   over all enumerated (d) tests; an I1-veto counterfactual. Interpreter is the repo venv
   (`.venv/bin/python`, 3.12.13) with cwd = the scratch repo — `uv run` was avoided so the
   real `.venv` is never re-synced.

No network, no ledger touch, no full suite, nothing tracked modified (`git status` clean
apart from the pre-existing `wiki/log.md`); every write landed in the scratch `.tmp/`.

Raw numbers are in "What I executed" at the end.

---

## Verdict: PASS WITH FIXES

**No BLOCKERs.** All three round-3 BLOCKERs are genuinely closed and I proved each by
execution: the flag-off page is byte-identical to the pre-change snapshot (0-byte diff)
with Tasks 4–6 in place; `uv run pyright` is 0 errors; the D13-A guard replacement passes
and leaves `test_boundary_rejects_direct_from_and_aliased_experiment_forms` and the
real-build test green. Every one of the brief's own new tests passes (16 + 10 + 3 + 9 + 5 + 2),
and the set of files that fail after Task 6 is exactly the set Task 6 Step 4 predicts.

Four MAJORs remain, all tightly scoped with exact fix text, and all in Task 7 — the
judgment-heavy task where a Codex run is most likely to stall: rev 4's own I1 change breaks
a 45th test the brief does not list and which the brief's own rules cannot repair; one
prescribed repair provably does not work and mis-describes its test; the Task 8 `ruff` gate
fails on two brief-supplied lines again; and the brief's new "only wrap what you observed to
fail" rule contradicts three entries in the list below it. Dispatch is separately gated on
D13/I1, which the brief declares honestly in all four places it matters.

---

## MAJOR findings

### 1. MAJOR — I1 breaks a 45th test that the brief does not list, and its own rules forbid the only repairs; the I1-veto branch has no stated consequences

- **Brief:** `:2018-2019` "round 3 measured **44** broken tests under the flag (37 failures +
  7 errors of 203). All are listed here."; `:1966-1969` "Fail-visible contracts
  (`FailClosedFeatureTests`, `SchwabFreshnessPageDateTests`) MUST stay flag-on via (d) —
  never (a)/(c)."; `:173-178` (I1 implemented as `pinned_symbols=set()`).
- **Evidence (executed):** flag-on run of `tests/test_attractiveness_dashboard.py` in my
  rev-4 build: **217 tests, 38 failures + 7 errors = 45 broken** (44 of the 203 pre-existing
  are covered by an enumerated anchor; one is not). The extra one is
  `tests/test_attractiveness_dashboard.py:874`
  `SymbolPanelStatusTests.test_render_uses_details_and_fail_visible_open_attribute`,
  failing at its last assertion (`:894`):
  `AssertionError: '<details class="panel symbol-panel" open>' not found`.
  That assertion sits OUTSIDE the `mock.patch.object(config, "PICK_PINNED_SYMBOLS", [])`
  block and asserts precisely the behaviour I1 removes — a clean, owner-pinned AMZN panel is
  force-open today. Disposition **(d) cannot repair it**: I ran the brief's recipe
  (`mock.patch.object(config, "PICK_PINNED_SYMBOLS", <the fixture's symbols>)` around the
  render) over all 18 enumerated (d) tests — **18/18 pass** — and over this one: **still
  fails**, because pinning is the cause, not the cure. Its own name marks it a fail-visible
  contract, so the brief's rule forbids (a)/(c) as well. Round 3 could not see this: rev 3
  passed `pinned_symbols` through, so the count really was 44 then; rev 4's I1 makes it 45.
- **Second half:** the brief presents three I1-dependent assertions as unconditional while
  I1 is still vetoable. Measured on the fresh 8-symbol fixture with `pinned_symbols` passed
  through (the veto branch): **2 open panels**, visible 4 `<h2>` / 6 `<summary>`. So under a
  veto, Task 8's `assertEqual(html.count('<details class="panel symbol-panel" open>'), 0)`
  (`:2226`) and Task 7's rewrite of `SymbolPanelCollapseTests:277`
  (`assertEqual(sum(1 for p in panels if p), 0)`, `:1987`) both fail, and `:874` passes
  unchanged. The brief says what a D13=B ruling costs (`:134-135`) but says nothing about
  what an I1 veto costs.
- **Third half (owner-facing):** the spec's I1 entry asks the owner about panels "as the
  pinned hero cards were today" without showing the two artifacts that record the behaviour
  being reversed: the code comment at `attractiveness_dashboard.py:5598-5600` ("… and the
  owner-pinned names stay open **by standing directive**") and the test at `:874/:894` that
  mechanically enforces it. The owner is being asked to reinterpret a standing directive
  without being shown its enforcement.
- **Exact fix:** (a) change `:2018-2019` to "**45** broken tests in rev 4's own build (round 3
  measured 44 before I1; the 45th is caused by I1)". (b) Add to the Task 7 Step 2 dashboard
  list: "**(b)** `SymbolPanelStatusTests.test_render_uses_details_and_fail_visible_open_attribute`
  (`:874`) — I1 consequence. `:889-892` (inside the `PICK_PINNED_SYMBOLS=[]` patch) pass
  unchanged and stay flag-on. Replace `:893-894` with the flag-on contract
  `self.assertNotIn('<details class=\"panel symbol-panel\" open>', ad.render(data))` plus a
  `_legacy_layout()`-wrapped twin keeping today's assertion, each with a one-line comment
  citing I1. Disposition (d) is measured NOT to work here; this is the one fail-visible
  contract where the (d)-only rule does not apply, because the contract under test IS the
  pinned open-state." (c) Add one sentence after I1 in Global Constraints: "If the owner
  vetoes I1, pass `pinned_symbols` through instead of `set()`, revert this test to its
  current text, and change the two zero-open assertions (Task 7 `:277` rewrite, Task 8
  acceptance) to **2** — measured on the fresh 8-symbol fixture." (d) Add both artifacts
  (`attractiveness_dashboard.py:5598-5600`, `tests/test_attractiveness_dashboard.py:874`)
  to the spec's I1 pending-ruling entry so the owner rules on the evidence.

### 2. MAJOR — the prescribed repair for `LoadContextTests:1591` provably does not work, and the brief mis-describes the test

- **Brief:** `:2053-2054` "(a) `LoadContextTests` `:1591` → its `DATA FRESHNESS`-relative
  slice inverts; re-anchor on `id=\"diagnostics\"` (content unchanged) rather than wrapping."
- **Evidence (executed):** the test has **no `DATA FRESHNESS` anchor**. Its `chip()` helper
  (`tests/test_attractiveness_dashboard.py:1600-1603`) slices
  `html[html.index("Research context") : html.index("</span>", start)]`. On the flag-on page
  `"Research context"` occurs **twice**: at offset 26,209 the drawer heading
  `Research context and coverage</h2>` (from `_research_desk_html`, drawer section 2) and at
  offset 30,053 the freshness chip `Research context EXACT — context as of 2026-07-15; …`
  (relocated after the six drawer sections). The drawer opener `id="diagnostics"` is at
  24,084 — **before both** — so the prescribed re-anchor changes nothing: after slicing from
  the drawer, `index("Research context")` still lands on
  `'Research context and coverage</h2><p class="header-sub">…'` and the test still fails.
  The chip text itself is present verbatim (measured `True`).
- **Why it matters:** Codex is told the repair is a one-line anchor change; it will apply it,
  watch the test still fail, and have to invent a disposition under a brief whose closing
  rule is "anything Codex finds that contradicts a citation is a STOP-and-report, not a
  workaround" (`:2320-2321`).
- **Exact fix:** replace that line with: "**(b)** `LoadContextTests.test_rendered_context_freshness_has_all_evidence_derived_states`
  (`:1591`) — its `chip()` helper (`:1600-1603`) anchors on the FIRST `html.index(\"Research
  context\")`; flag-on that is the drawer heading `Research context and coverage`, which now
  precedes the relocated freshness chip (measured offsets 26,209 vs 30,053). Re-anchoring on
  `id=\"diagnostics\"` does NOT fix it (measured). Change `start = html.index(\"Research
  context\")` to `start = html.rindex(\"Research context\")` and keep every assertion
  flag-on; the chip text is unchanged."

### 3. MAJOR — `ruff` fails again on two brief-supplied lines; Task 3 Step 4 and Task 8 Step 3 both gate on it

- **Brief:** `:306` `from options_researcher import board_lanes as bl   # Task 3 creates it; Task 1 tests skip it`;
  `:1312` `from options_researcher.schwab_chain_view import CHAIN_SOURCE, CHAINS_ABSENT   # ruff isort order (round 3)`.
  Gates: Task 3 Step 4 (`:938-939`, "Expected: `All checks passed!`") and Task 8 Step 3 (`:2253`).
- **Evidence (executed):** `ruff check` on the five changed files → **2 errors**, both `I001`:
  `tests/test_board_lanes.py:5` and `tests/test_attractiveness_dashboard.py:3921`.
  `ruff check --diff` shows the cause is the **three-space** gap before each inline comment
  (ruff's isort formatter normalises it to two, and on the second line it explodes the import
  into a parenthesised block). The baseline tree is `All checks passed!`. Round-3 MAJOR 7's
  substance (name order `CHAIN_SOURCE, CHAINS_ABSENT[, CONVENTION_LABEL]`) **is** applied and
  correct — the module-level import inside `_status_strip_html` (`:1363`) passes clean; the
  comment added to advertise that fix is what now breaks the gate.
- **Exact fix:** in both blocks use exactly two spaces before `#`
  (`… as bl  # Task 3 creates it; Task 1 tests skip it` and
  `… import CHAIN_SOURCE, CHAINS_ABSENT  # ruff isort order (round 3)`), and add to Task 3
  Step 4: "if ruff reports `I001` on a line this brief supplies, the brief is wrong — apply
  `ruff check --diff`'s suggestion and note it in the PR body; do not reorder names."

### 4. MAJOR — Task 7's new rule (3) contradicts three entries in the list directly below it

- **Brief:** rule (3) at `:1959-1961`: "legacy-wrap ONLY a test the executor has OBSERVED to
  fail — a passing test stays flag-on (round 3 measured `:286`, `:296`, `:337`, `:364`, `:424`
  and dashboard `:2034` passing; **do not touch them**)". Then `:2003-2005`:
  "(a) `test_composite_board_is_one_table_with_every_label_preserved` (`:337`),
  `test_blocked_angle_reason_is_still_printed` (`:364`) → legacy wrap"; and `:2009-2010`:
  "(b) `test_symbol_panels_precede_the_drawer` (`:424`) → `id=\"pick-details\"` precedes
  `id=\"diagnostics\"`".
- **Evidence (executed):** in my rev-4 flag-on run, `:337`, `:364` and `:424` all **PASS**
  (13 broken of 27 in `tests/test_attractiveness_layout.py`; none of the three is among them).
  Legacy-wrapping `:337`/`:364` moves the composite-table label contract off the page that
  ships — exactly the coverage loss round-3 MEDIUM 13 raised, which rule (3) was added to
  prevent. Codex has two mutually exclusive instructions and no tiebreak.
- **Exact fix:** delete the `:337`/`:364` line; change the `:424` entry to "PASSES flag-on
  unchanged — leave it (rule 3). Optional tightening to `id=\"pick-details\"` before
  `id=\"diagnostics\"` is not required and must not be done as a 'fix'."; and add to rule (3):
  "where rule (3) and an entry below disagree, rule (3) wins and the entry is stale."

---

## MEDIUM findings

### 5. MEDIUM — the D10 acceptance test's `<h2> ≤ 8` leg still does not discriminate: today's page scores exactly 8 on the same fixture

- **Brief:** `:2217-2231`, and the claim at `:2221-2222` "The measure can therefore FAIL if
  the flag-on page leaves too much in the main flow — which is what D10 rules on."
- **Evidence (executed)** on the brief's own fresh 8-symbol acceptance fixture:
  - flag-on: 54,574 bytes, 6 panels (0 open), `_visible_html` = 27,151 bytes,
    **2 `<h2>`, 0 `<summary>`** against limits 8 and 20.
  - the **pre-redesign** page on the same fixture: 64,218 bytes, 20 `<h2>` / 44 `<summary>`;
    `_visible_html` = **8 `<h2>`, 23 `<summary>`**. So the `<h2> ≤ 8` assertion is satisfied by
    the very page the redesign replaces — it has zero discriminating power. The
    `<summary> ≤ 20` leg does discriminate (23 vs 0).
  - the flag-on FALLBACK page (`build_lane_board` raising, so `hero_html` + `symbols_html` sit
    in the main flow) measures 4 `<h2>` / **21 `<summary>`** — it fails the summary leg only.
  - a deliberate leak (the whole composite table left in the decision area) moved visible
    `<h2>` from 2 to **3** — still 5 below the limit.
  Round-3 MAJOR 6's numbers (2 and 0) are therefore unchanged in rev 4; what changed is the
  fixture's honesty (0 force-open panels instead of 6) and that the summary leg can now fail.
  The spec §1 vs §8 wording conflict IS named and ruled in Global Constraints (`:167-172`) —
  that half of round-3 MAJOR 6 is applied.
- **Exact fix:** tighten to what the redesign actually achieves and prove the direction:
  `self.assertLessEqual(visible.count("<h2"), 4)`, keep `<= 20` for `<summary>`, and add one
  assertion that the same measure REJECTS the legacy page —
  `with mock.patch.object(config, "BOARD_LANES_ENABLED", False): legacy = ad.render(_fresh_board(symbols), **…)`
  then `self.assertGreater(_visible_html(legacy).count("<summary"), 20)` — with the measured
  numbers (new 2/0, legacy 8/23) written into the comment.

### 6. MEDIUM — a shipped docstring claims a byte-identity that is false

- **Brief:** `:1462-1465`, `_agreement_table_html`'s docstring: "The eyebrow phrase and the
  `<h2>` text are byte-identical to today's shortlist heading (`:4212-4213`)".
- **Evidence:** `attractiveness_dashboard.py:4212` is
  `'<div class="eyebrow">Daily shortlist · TOP 5 PICKS TODAY</div>'`; the brief emits
  `'<div class="eyebrow">Daily shortlist · TOP 5 PICKS TODAY · agreement across lanes</div>'`
  (`:1516`). The `<h2>` at `:4213` **is** byte-identical (verified); the eyebrow is not — it
  keeps the phrase and appends to it. The brief's own test asserts only
  `assertIn("TOP 5 PICKS TODAY", html)` (`:1265`), i.e. the weaker, true claim. (The "20+ test
  assertions locate the shortlist by them" claim is fine: 38 occurrences across four test files.)
  This is the round-2 MEDIUM 12 class — a false factual claim in code that ships.
- **Exact fix:** "The `<h2>` text is byte-identical to today's shortlist heading (`:4213`); the
  eyebrow keeps today's phrase (`:4212`) and appends ` · agreement across lanes`. 20+ test
  assertions locate the shortlist by them."

---

## MINOR findings

7. **Cite drift:** `:2057` cites `test_partial_shortlist_keeps_configured_visible_slots_in_each_list`
   as `tests/test_attractiveness_v3.py:279-288`; the `def` is at **`:278`** (body `:279-288`).
   Round 3 cited `:278`.
8. **The byte-figure reconciliation is false.** `:2306-2308` says the brief's 782,263 bytes and
   spec §1's "771 KB" differ by "different unit convention". 782,263 B = 782.3 kB = 763.9 KiB;
   no convention yields 771. Worse, the spec contradicts *itself*: §1 (`:16`) says 771 KB and
   §8 (`:256`) says 782 KB. Fix: "spec §1 says 771 KB and spec §8 says 782 KB for the same
   build; the measured 782,263 bytes is the figure to compare against, and spec §1 should be
   corrected in a later editorial pass."
9. **Recipe (d) is not behaviour-neutral, and it presumes a section exists.** Patching
   `PICK_PINNED_SYMBOLS` also feeds `pinned_picks(data)` → `protected_card_ids`
   (`attractiveness_dashboard.py:5540-5543`), which sets `protected_indexes` inside
   `_group_html`; and if the pinned symbol has no section, `_pick_details_html` renders a row
   but no panel, so a panel-CONTENT assertion still fails. Measured: all 18 enumerated (d)
   tests pass regardless. Add both caveats to rule (d) at `:1962-1966`.
10. **One existing test now runs the experiment builders inside the offline suite.**
    `tests/test_attractiveness_dashboard.py:2859`
    `test_main_loads_board_and_context_from_same_external_root` patches `ad._gather_all`, so
    `assemble()` takes the REAL path and `_default_experiment_lanes` fires (measured: 1 call,
    2.1 ms, four lanes returned; the test passes). The brief's hermeticity constraint
    (`:197-199`) and its `test_injected_fixtures_never_compute_experiment_lanes` cover only
    the injected case. Name this site so a future cache-dependent slowdown is not a mystery.
11. **Option C has no stated disposition.** `:134-135` says a D13=B ruling means "Task 4 is
    rewritten and the brief returns to review"; C ("drop the four experiment columns") is
    listed with no consequence, though it would change Task 1's two tuples, Task 3's
    `_EXPERIMENTS` map and four of the 16 `test_board_lanes` tests, all of Task 4, and the
    agreement table's caution group. Add "If C, Tasks 1, 3, 4 and 6 are rewritten and the
    brief returns to review."
12. **`EmptySlotConsolidationTests` left to a conditional.** `:2014-2016` says "(a) legacy wrap
    only if one locates the hero by a removed marker; otherwise unchanged". Measured: **4 of
    the 5 fail** (all `ERROR`) — `:88`, `:102`, `:111`, `:130`; `:122`
    (`test_blocked_qm_slots_collapse_into_one_block`) passes. Replace the conditional with the
    measured set, as the dashboard list does.
13. **Ambiguous parenthetical.** `:1984-1986` "panels render in BOARD-ROW order, not
    `data[\"symbols\"]` order (`[VST, NVDA, MSFT]` vs picks `[MSFT, NVDA, VST]` …)" reads as if
    the first list is the board-row order. Measured board-row panel order on that fixture is
    **`MSFT, NVDA, VST`**; `[VST, NVDA, MSFT]` is the `data["symbols"]` order. The conclusion
    (the `:283` slice inverts) is correct. Re-word to name each list.

---

## Round-3 findings status (all 18)

| # | Sev | Round-3 finding | Status in rev 4 |
|---|---|---|---|
| 1 | BLOCKER | CSS inside `_STYLE` breaks the byte-identity rollback proof | **Applied, correct (executed)** — `_BOARD_STYLE` is a separate constant after `_STYLE`, emitted via `board_css` at the `<style>` line (`:5726`), `""` in the flag-off branch. `LegacyByteIdentityTests` PASSES: flag-off render == the 44,370-byte pre-change snapshot, **0-byte diff**, with Tasks 4–6 all in place. |
| 2 | BLOCKER | Task 4 violates the tracked AST isolation guard | **Applied, correct (executed)** — D13 raised as an owner ruling in the spec's pending section and declared in the brief header, Status, Scope, its own section, Task 4 and Acceptance. The D13-A replacement test passes; the `outside`-blanking trick parses (module-level `def`, `end_lineno` present, `assertEqual(len(sites), 1)` guards uniqueness) and is as strong as round 3 asked: a stray experiment import elsewhere trips `assertFalse`, a second call inside the helper trips the exact-list assertion. `test_boundary_rejects_direct_from_and_aliased_experiment_forms` untouched and green; `test_module_entry_no_args_matches_production_command` green, **"EXPERIMENTS SHELF" still present**, 39.6 s vs 36.5 s baseline (**+3.1 s** — the brief's "a few seconds slower" is accurate). File is green, as Task 6 Step 4 now promises. |
| 3 | BLOCKER | `uv run pyright` fails; `sec: dict` is the wrong annotation | **Applied, correct (executed)** — `sec: Any` + `from typing import TYPE_CHECKING, Any` at `:45` (cite exact). `pyright` with the repo config and `board_lanes.py` added to `include`: **0 errors, 0 warnings** (baseline also 0). `_table_footnotes_html`, `_seq`, `_num_or_zero`, `board_css`/`nav_html` and `_BOARD_STYLE` all type-clean. |
| 4 | MAJOR | Enumeration named 20 of 44 dashboard failures | **Partial** — all 44 of round 3's are now covered (19 by `def` line under (d)/(c), 17 by an internal anchor, the rest by name), and the root cause is stated. But rev 4's own I1 change makes the true count **45**, and the 45th (`:874`) is unlisted and unrepairable by the brief's rules → **MAJOR 1**. The `(d)` recipe itself is sound: 18/18 measured. |
| 5 | MAJOR | A brief-supplied tile test fails against the brief's own code (`5 != 4`) | **Applied, correct (executed)** — `html.count('<div class="k">') == 4` passes on **both** branches; all 9 `LaneBoardRenderTests` pass. |
| 6 | MAJOR | D10 measure cannot fail; spec §1 vs §8 conflict unstated | **Partial** — the conflict is now named and ruled (`:167-172`), the fixture is fresh, force-open panels count as visible, and `test_force_open_panels_count_as_visible` passes. But the measured values are still **2 `<h2>` / 0 `<summary>`** vs limits 8/20, and the legacy page scores exactly 8 on the same fixture → **MEDIUM 5**. |
| 7 | MAJOR | `ruff check .` fails on two brief-supplied import lines | **Partial** — name order fixed and verified; the explanatory comments added alongside reintroduce two `I001`s (three-space gap) → **MAJOR 3**. |
| 8 | MEDIUM | One tile on the branch every injected fixture hits | **Applied, correct (executed)** — four tiles on the unassembled branch; `test_position_tiles_are_four_even_when_the_book_was_not_assembled` passes. |
| 9 | MEDIUM | `LANE BOARD FAILED` fallback drops an authority sentence | **Applied, correct (executed)** — `_table_footnotes_html` prints on both paths; `test_lane_board_failure_keeps_every_disclaimer` passes with **12/12** sentences. It also confirms `mock.patch("options_researcher.board_lanes.build_lane_board")` intercepts the `_bl.build_lane_board(…)` call (attribute lookup at call time). |
| 10 | MEDIUM | Stale non-row names disappear, untested | **Applied, correct (executed)** — Global Constraints sentence + `test_stale_name_that_is_not_a_row_is_still_named_in_the_status_strip` passes; measured `stale_not_rows = {PLTR, SMCI}`, `data["stale_symbols"]` is a `list[str]`, and the strip prints `0 names fresh · 8 stale (AMZN, CEG, CRWV, MSFT, NVDA, PLTR, SMCI, VST)` between `class="status-strip"` and `class="tiles"`. |
| 11 | MEDIUM | Sentence count off by one (prose + test name) | **Applied, correct** — "twelve"/"Nine" and `test_every_disclaimer_survives_with_flag_off_too`; measured `len(_SENTENCES) == 12`. |
| 12 | MEDIUM | Three cite regressions | **Applied, correct** — `:4707-4708` (pinned sentence), `:5877` (`_bind_source_rows_html`), Task 4 Files now `tests/test_attractiveness_layout.py:54-69`. All three re-read and exact. |
| 13 | MEDIUM | Dispositions prescribed for passing tests | **Partial** — rule (3) added and `:304` named, but the list below still prescribes dispositions for `:337`, `:364` and `:424`, all measured passing → **MAJOR 4**. |
| 14 | MINOR | Transient `contextlib` F401 between Tasks 2 and 7 | **Applied, correct** — moved to Task 7 with the pre-commit reason stated in Task 2 (`:408-410`). |
| 15 | MINOR | "Move the loop body unchanged" hides two edits | **Applied, correct** — `:1204-1206` names both, plus the `evaluation_date` hoist as a separate step. |
| 16 | MINOR | `_CONTEXT_LANE_DISCLAIMER` range | **Applied, correct** — `:4442-4447` verified exact. |
| 17 | MINOR | `card_fragment` range | **Applied, correct** — `:396-413` verified exact (as are `:313-338`, `:340`, `:341-368`, `:374-391`, `:393-394`, `:415-418`, `:417`, `:419`). |
| 18 | MINOR | 782,263 bytes vs spec's 771 KB | **Applied but the explanation is false** — "different unit convention" does not reconcile them, and spec §8 already says 782 KB → **MINOR 8**. |

## New cites in rev 4 — all re-read

Exact: `attractiveness_dashboard.py` `:45` (`from typing import TYPE_CHECKING`), `:4212-4213`,
`:4215`, `:4442-4447`, `:4707-4708`, `:5129` (`_blocked_html`, and it really emits
`<li><strong>ET</strong>` at `:5147`), `:5493`, `:5548`, `:5554`, `:5598-5602`, `:5633-5634`,
`:5664`, `:5690-5721`, `:5726`, `:5737`, `:5877`; `config.py` `:650`, `:660`, `:674`, `:690`,
`:929`, `:932`; `tests/test_attractiveness_layout.py:254-275` (`SymbolPanelCollapseTests._data`),
`:434-454`, `:456`, `:497`; `tests/test_experiments_baseline.py:92-93`, `:95-105`, `:107`
(and `:136` is where `EXPERIMENTS SHELF` is asserted); `tests/test_event_awareness.py:396-413`,
`:417`; `experiments_dashboard.py:250-259`, `:262-282`; `exp_beta_qqq.py:132`;
`exp_tbill_carry.py:131`; `top3_snapshot.py:83`. Drifted: `tests/test_attractiveness_v3.py:279`
(def is `:278`, MINOR 7).

---

## What I executed and raw results

Scratch only, under gitignored `.tmp/brief39-review/r4/` (build) and `…/r4base/` (baseline).
Nothing tracked modified; no network, no ledger, no full suite.

```
# scratch construction
r4/repo, r4base/repo   = real copies of options_researcher/, tests/, config.py,
                         pyrightconfig.json, real local .tmp/; symlinks for the rest
brief blocks extracted  37 fenced blocks (b00..b36), programmatically

# Task 2 (unmodified renderer)
snapshot capture         44,370 bytes; captured twice into two paths, cmp -> identical

# brief's own new tests (all in the flag-on build)
tests/test_board_lanes.py                     Ran 16   OK
LegacyByteIdentityTests                       Ran 1    OK   (flag-off == snapshot, 0-byte diff)
LaneBoardLayoutTests                          Ran 10   OK
LaneBoardParityAndSizeTests                   Ran 3    OK
LaneBoardRenderTests                          Ran 9    OK
ExperimentLaneGatherTests                     Ran 5    OK
Task 7 Step 3 replacement event tests         Ran 2    OK   (after the prescribed fixture lift)

# gates
pyright (repo config + board_lanes.py in include, --pythonpath = repo venv)
   baseline  0 errors, 0 warnings, 0 informations
   build     0 errors, 0 warnings, 0 informations
ruff check .        baseline: All checks passed!
ruff check <changed files>  build: 2 errors
   tests/test_board_lanes.py:5                I001   (brief :306, three-space comment gap)
   tests/test_attractiveness_dashboard.py:3921 I001  (brief :1312, same cause)
   ruff check --diff -> two spaces / parenthesised import

# flag-on failure enumeration (pre-existing tests)
test_attractiveness_dashboard   Ran 217  FAILED (failures=38, errors=7)  = 45 broken of 203
                                44 covered by an enumerated anchor; 1 UNNAMED:
                                :874 SymbolPanelStatusTests.test_render_uses_details_and_fail_visible_open_attribute
                                     (fails at :894 — the I1 consequence)
test_attractiveness_layout      Ran 41   FAILED (failures=7, errors=6)   = 13 broken of 27
                                :337, :364, :424, :286, :296, :304 all PASS
test_attractiveness_v3          Ran 24   FAILED (failures=1)   [:278, enumerated]
test_event_awareness            Ran 16   FAILED (errors=1)     [:311, enumerated]
test_experiments_baseline       Ran 4    OK  in 101.1 s        [D13-A guard green]
test_attractiveness, test_composite_signals, test_display_rank, test_oi_change_line,
test_qm_dashboard, test_ritual_receipt, test_schwab_freshness_gather,
test_daily_ritual_provenance, test_research_context_assemble    -> all OK
test_short_positioning_boundaries  FAILED (5) in BOTH the build and the pristine baseline
   -> symlinked-scratch artifact, not caused by the brief
=> Task 6 Step 4's expected-failure list matches exactly.

# baselines (pristine scratch)
test_attractiveness_layout 27 OK (0.118 s) | test_attractiveness_dashboard 203 OK (0.276 s)
test_attractiveness_v3 24 OK | test_event_awareness 16 OK
test_experiments_baseline module_entry alone: 36.5 s  ->  flag-on 39.6 s  (+3.1 s)

# recipe (d): render wrapped in mock.patch.object(config, "PICK_PINNED_SYMBOLS", <fixture symbols>)
PASS  RenderTests :291 :301 :305 :310 :338
PASS  StrategySectionRankingTests :1240 | BlockedSectionsTests :1360 | HypothesisEvidencePanelTests :1393
PASS  V2RenderTests :1803 :1825 :1831 :1841
PASS  SchwabFreshnessPageDateTests :3551 :3561        (both, incl. the STALE force-open one)
PASS  FailClosedFeatureTests :3691 :3698 :3705 :3720  (all four)
STILL FAILS  SymbolPanelStatusTests :874              (d) cannot repair the pinned-open contract
(LoadContextTests :1591 and PinnedPicksTests :1307 also fail under (d) — expected, they are (a)/(c))

# D10, fresh 8-symbol board (NVDA AMZN MSFT PLTR SMCI CRWV CEG VST)
flag-on   54,574 bytes | panels 6 (open 0) | rows = panels = AMZN CEG CRWV MSFT NVDA VST
  _visible_html   27,151 bytes,  2 <h2>,  0 <summary>   [targets <=8, <=20]
  'class="panel symbol-panel"' in visible -> False
flag-off  64,218 bytes, 20 <h2>, 44 <summary>
  _visible_html(legacy)            8 <h2>, 23 <summary>   <- passes the <h2> leg
flag-on FALLBACK (build_lane_board raises)
  _visible_html                    4 <h2>, 21 <summary>
leak probe (composite table left in the decision area)   3 <h2>
I1-VETO counterfactual (pinned_symbols passed through)
  open panels 2 | _visible_html 4 <h2>, 6 <summary>

# stale 3-symbol layout fixture
panels 3, all force-open | _visible_html 5 <h2>, 10 <summary> | open panel IS in visible: True
drawer never rendered open (only `<details class="panel diagnostics-drawer" id="diagnostics">`)

# fresh collapse fixture (VST NVDA MSFT), flag-on
panels 3 | open 0  -> the brief's :277 rewrite (len==3, open==0) is correct
panel order MSFT, NVDA, VST (board-row order; data["symbols"] order is VST, NVDA, MSFT)

# Task 3 rev-4 rule and Task 6 blocked-row test
blocked ET row renders 'DATA_BLOCKED · chain 29 sessions old' in the pick cell,
no id="symbol-ET" panel, and <strong>ET</strong> still in the _blocked_html banner  -> PASS

# hermeticity
_default_experiment_lanes calls across 541 tests in 11 dashboard-touching files: 4
  3 are the brief's own gather tests (mocked builder)
  1 is tests/test_attractiveness_dashboard.py:2859 test_main_loads_board_and_context_from_same_external_root
    (patches _gather_all -> real assemble path), 2.1 ms, four lanes returned, test passes

# _symbol_panel_html and I1
pinned_symbols is referenced in exactly one place in the extracted function — the
open_attr expression. I1 changes no panel byte except the ` open` attribute.

# misc
len(AuthorityWordingSurvivesLayoutTests._SENTENCES) == 12
'TOP 5 PICKS TODAY' / 'Rule-based top 5' assertions in tests: 10 + 25 + 2 + 1 = 38
test_flag_off_matches_post_brief26_golden_bytes with BOTH flags patched off -> sha matches
'Research context' occurrences on the flag-on page: 2  (26,209 drawer heading; 30,053 chip)
   id="diagnostics" at 24,084 -> the prescribed re-anchor does not help
```
