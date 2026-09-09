# Brief 39 — independent adversarial review, round 5 (bounded verification) (2026-09-06)

**Reviewer:** Opus, round 5 — BOUNDED verification of the 13 round-4 findings and of
anything the rev-5 edits could have broken. Not a fresh full review; settled parts were
not re-opened except where a rev-5 edit touches them.
**Target:** `docs/superpowers/plans/2026-09-06-39-attractiveness-board-redesign-codex-brief.md`
rev 5 @ `acb8946` (2,385 lines).
**Spec:** `docs/superpowers/specs/2026-09-06-attractiveness-board-redesign-design.md`
(D1–D12 owner-APPROVED; D13 + I1 still unruled in the trailing "Pending owner rulings"
section, whose I1 entry rev 5 amended).
**Code base:** `origin/main` @ `f83428d` (this branch adds only docs).
**Receipt under audit:** `reports/2026-09-06-brief-39-adversarial-review-round4.md`
(PASS WITH FIXES: 0 blockers, 4 MAJOR, 2 MEDIUM, 7 MINOR). Rev 5 claims all 13 applied.

## Method — what I reused, what I re-applied, what I ran

I reused round 4's scratch overlays rather than rebuilding:

- `.tmp/brief39-review/r4/repo` — round 4's flag-on build (Tasks 1–6 applied verbatim,
  the brief's new tests present). `.tmp/brief39-review/r4base/repo` — the pristine
  baseline, untouched this round.
- I re-extracted rev 5's **37 fenced blocks** programmatically into
  `.tmp/brief39-review/r5/blocks` and diffed them against round 4's `r4/blocks`.
  **Exactly four code blocks changed** (`b00`, `b20`, `b21`, `b32`) and every changed
  line traces to a round-4 finding. No unexplained code delta.
- **Re-applied to `r4/repo`** (and nothing else): (1) `b00`'s two-space comment in
  `tests/test_board_lanes.py:5`; (2) `b20`'s two-space comment in
  `tests/test_attractiveness_dashboard.py`; (3) `b21`'s revised `_agreement_table_html`
  docstring in `options_researcher/attractiveness_dashboard.py`; (4) `b32`'s revised
  `LaneBoardParityAndSizeTests.test_visible_page_meets_the_d10_targets_on_a_fresh_board`;
  (5) Task 7 Step 1 for `tests/test_attractiveness_dashboard.py` (`import contextlib` +
  the `_legacy_layout()` helper — round 4 had not applied it to that file and the `:874`
  disposition needs it); (6) the prose-only `:874` disposition, in BOTH readings; (7) the
  prose-only `rindex` repair at `:1600-1603`.
- Ran: the two repaired tests; the whole flag-on `tests/test_attractiveness_dashboard.py`
  and `tests/test_attractiveness_layout.py`; every one of the brief's own new test classes;
  `ruff check` on the changed files (repo venv binary, repo `pyproject.toml` config);
  `pyright` on the two modules; the D10 measurements on both fixtures; an I1-veto
  counterfactual on both fixtures; the `EmptySlotConsolidationTests` re-measurement; a
  `_default_experiment_lanes` call spy on `test_main_loads_board_and_context_from_same_external_root`.
- Interpreter is the repo venv (`.venv/bin/python`, cwd = the scratch repo); `uv run` was
  avoided so the real `.venv` is never re-synced. No network, no ledger, no full suite,
  nothing tracked modified (`git status` clean apart from the pre-existing `wiki/log.md`).
  `r4/repo` now holds the rev-5 build; `r4base/repo` is still the pristine baseline.

Raw numbers are in "What I executed" at the end.

---

## Verdict: PASS WITH FIXES

**No BLOCKERs.** Twelve of the thirteen round-4 findings are applied and I proved the
consequential ones by execution: the `rindex` repair passes flag-on; the `:874`
disposition passes on both branches once one line is kept; the tightened D10 acceptance
test passes and the legacy page now FAILS the summary leg it is meant to fail (measured
new 2/0, legacy 8/23, exactly the numbers written into the brief's comment); rule (3)
now wins over the list and the three tests it protects (`:337`, `:364`, `:424`) all pass
flag-on; the `EmptySlotConsolidationTests` measured set is exactly right and the new
flag-on twin it prescribes is satisfiable; `pyright` is 0 errors; every one of the
brief's own tests still passes (16 + 1 + 10 + 3 + 9 + 5).

Two MAJORs and three MINORs remain. Both MAJORs are inherited: rev 5 applied round 4's
prescribed text **verbatim**, and in these two places round 4's prescription was wrong.
The ruff gate still fails on a brief-supplied line (round 4 diagnosed the wrong cause),
and the `:874` repair, read literally, breaks the assertion it adds and silently vacuates
the twin it adds. Dispatch remains separately gated on D13/I1, which the brief declares
honestly in all six places it matters (header `:3`, Status `:6`, Scope `:66`, its own
section `:108-142`, Task 4 `:972`/`:1090`, Acceptance `:2355`).

---

## MAJOR findings

### 1. MAJOR — `ruff check` still fails on the brief-supplied import at `:1335`; the cause is line length (100), not the comment gap, and the escape hatch does not cover the gate that catches it

- **Brief:** `:1335` (block `b20`)
  `        from options_researcher.schwab_chain_view import CHAIN_SOURCE, CHAINS_ABSENT  # ruff isort order (round 3)`.
  Gates: Task 8 Step 3 (`:2309`, `uv run ruff check . && uv run pyright` — "both clean")
  and the whole-brief Acceptance block (`:2351`, "both exit 0").
- **Evidence (executed):** with rev 5's two-space comment applied,
  `ruff check` on the five changed files returns **1 error**, `I001` at
  `tests/test_attractiveness_dashboard.py:3934`. The line is **114 characters**;
  `pyproject.toml` sets `line-length = 100` (`:30`), so ruff's isort formatter wraps it:
  `ruff check --diff` proposes the parenthesised four-line form. The companion fix at
  `:318` (`tests/test_board_lanes.py`) **is** correct — that line is 90 characters, three
  spaces reproduces the `I001` and two spaces clears it (both measured). So round 4's
  "three-space gap" diagnosis was right for one line and wrong for the other, and rev 5
  applied it to both.
- **Why it matters:** the escape-hatch sentence rev 5 added (`:951-953`, "if ruff reports
  `I001` on a line this brief supplies, the brief is wrong — apply `ruff check --diff`'s
  suggestion…") lives in **Task 3 Step 4**, whose ruff command covers only
  `options_researcher/board_lanes.py tests/test_board_lanes.py`. The failing line is
  delivered in Task 5 and is first caught by Task 8 Step 3, where no such sentence exists.
  Codex hits a red gate at the last task with the brief's own instruction saying "both clean".
- **Exact fix:** replace `:1335` with either form (both measured `All checks passed!`):

  ```python
          from options_researcher.schwab_chain_view import (  # ruff isort order (round 3)
              CHAIN_SOURCE,
              CHAINS_ABSENT,
          )
  ```

  or drop the trailing comment entirely (`… import CHAIN_SOURCE, CHAINS_ABSENT`, 84 chars).
  And add to Task 8 Step 3 the same sentence Task 3 Step 4 carries: "if `ruff check .`
  reports `I001` on a line this brief supplies, the brief is wrong — apply
  `ruff check --diff`'s suggestion and note it in the PR body; do not reorder names."

### 2. MAJOR — the `:874` disposition, read literally, makes the assertion it adds FAIL and the twin it adds vacuous

- **Brief:** `:2060-2064` — "The assertions inside the `PICK_PINNED_SYMBOLS=[]` patch
  (`:889-892`) pass unchanged and stay flag-on. **Replace `:893-894`** with the flag-on
  contract `self.assertNotIn('<details class="panel symbol-panel" open>', ad.render(data))`
  plus a `_legacy_layout()`-wrapped twin keeping today's assertion…"
- **Evidence (executed):** `:893` is not an assertion — it is
  `data["symbols"][0]["features_stale"] = False`, the reset that undoes `:891`
  (`features_stale = True`, set inside the patch block). Replacing `:893-894` as written
  leaves the section STALE, so:
  - the new flag-on `assertNotIn` **FAILS** — measured:
    `AssertionError: '<details class="panel symbol-panel" open>' unexpectedly found`
    at the replacement line — the panel is force-open by the fail-visible STALE rule, not
    by pinning;
  - the `_legacy_layout()` twin then passes **for the wrong reason** (STALE force-open,
    not pinned force-open), i.e. it stops testing the standing directive it exists to
    preserve. That is precisely the hazard the brief's own rule (2) names.
  Keeping `:893` and replacing only `:894`: **`SymbolPanelStatusTests` Ran 4, OK** — both
  branches pass, and the twin genuinely exercises the pinned-open behaviour.
- **Exact fix:** change `:2060` to read: "The assertions inside the
  `PICK_PINNED_SYMBOLS=[]` patch (`:889-892`) pass unchanged and stay flag-on. **Keep
  `:893` (`data[\"symbols\"][0][\"features_stale\"] = False`) — without that reset the
  panel is STALE-open and both new assertions are wrong: the flag-on `assertNotIn` fails
  and the legacy twin passes vacuously (measured).** Replace only `:894` with the flag-on
  contract `self.assertNotIn(…)` plus a `_legacy_layout()`-wrapped twin keeping today's
  assertion, each with a one-line comment citing I1."

---

## MINOR findings

3. **The I1-veto branch prescribes the wrong number for one of its two sites.**
   `:186-190`: "change the two zero-open assertions (Task 7's `:277` rewrite and Task 8's
   acceptance) to **2** — measured on the fresh 8-symbol fixture". The 8-symbol figure is
   right for Task 8 (measured: 2 open, visible 4 `<h2>` / 6 `<summary>`), but Task 7's
   `:277` runs on `SymbolPanelCollapseTests._data` — a **3-symbol** fixture
   (VST, NVDA, MSFT). Measured under the veto counterfactual on that fixture: **3 panels,
   1 open** (only VST is both pinned and present; AMZN has no section). Today's test says
   so in its own comment (`:282`, `# VST only`). Fix: "…change Task 8's acceptance
   assertion to **2** (measured on the fresh 8-symbol fixture) and Task 7's `:277` rewrite
   to **1** (measured on that test's own 3-symbol fixture — VST is the only pinned name
   with a section)."

4. **Cite drift at `:1146`.** The hermeticity paragraph cites
   `tests/test_attractiveness_dashboard.py:2859` beside the test NAME
   `test_main_loads_board_and_context_from_same_external_root`; the `def` is at **`:2801`**
   (class `MainTests`). `:2859` is the `path = ad.main()` call inside it. Every other
   name+line pair in the brief cites the `def` (round-4 MINOR 7 corrected exactly this
   class of drift at `:278`). Fix: cite `:2801` (or `:2801`, call site `:2859`).

5. **The veto branch passes the tightened `<h2>` leg with zero margin, unstated.**
   MEDIUM-5's tightening takes the acceptance assertion from `<= 8` to `<= 4`. Under an I1
   veto the same fixture measures **exactly 4** visible `<h2>` (measured). `:189-190` says
   the veto numbers are "still inside the D10 targets" — true of D10's ceiling of 8
   (spec `:36`), but the test's own bar is then hit exactly. Fix: append to the veto branch
   "…and the acceptance test's `<h2> <= 4` leg then passes at exactly 4 — no margin; leave
   the limit at 4 rather than re-tightening."

**Not findings, recorded for the record:** (a) `:1993-1994`'s phrase "which sets
`protected_indexes` inside `_group_html`" is loosely placed — `protected_indexes` is
computed in the per-symbol loop (`:5556-5558`) and passed INTO `_group_html` (`:5561`),
which forwards it to `dominated_partition` (`:765`, used `:791`); the described effect is
correct and the wording is round 4's own. (b) The `:874` entry is labelled `(b)` (a §2
POSITION invariant) when it is really an open-state contract; round 4's fix text specified
the `(b)` label and the entry's own prose is unambiguous. (c) The brief says the
`:2859`/`:2801` gather costs "~2 ms on that fixture's root" (round-4 measurement); my spy
measured **12.5 ms** on the same test — same order, cold-cache variance, and the sentence
is provenance-labelled "round 4 measured".

---

## Round-4 findings status (all 13)

| # | Sev | Round-4 finding | Status in rev 5 |
|---|---|---|---|
| 1 | MAJOR | I1 breaks a 45th test (`:874`), unlisted and unrepairable by the brief's rules; veto branch had no consequences; spec I1 hid the evidence | **Applied; one half wrong.** (a) `:2052` now says "**45** broken tests in rev 4's own flag-on build (round 3 measured 44 before I1; the 45th is caused by I1)" — **confirmed by execution**: my rev-5 build with the `:874` and `:1591` repairs applied runs 217 tests with **43** broken, i.e. 45 − 2, and neither repaired test appears in the list. The only surviving "44" in the brief is inside that corrected sentence. (b) the `:874` entry is present, correctly says (d) does not work and why — but its "Replace `:893-894`" instruction is wrong → **MAJOR 2 above**; with `:893` kept, `SymbolPanelStatusTests` is **Ran 4, OK** on both branches. (c) the veto branch exists at `:186-190`; its 8-symbol numbers are exact (measured 2 open panels, visible 4 `<h2>` / 6 `<summary>`) but the `:277` number is wrong → **MINOR 3**. (d) the spec I1 entry now quotes both artifacts; I re-read them: `attractiveness_dashboard.py:5598-5600` is the three-line comment ending "…and the owner-pinned names stay open by standing directive." and `tests/test_attractiveness_dashboard.py:874` is the `def`, with `:894` its last assertion. Both quoted correctly; the markdown row still has 4 cells. |
| 2 | MAJOR | The prescribed `LoadContextTests:1591` repair provably does not work | **Applied, correct (executed).** `:2097-2104` now prescribes `rindex`. Applied in scratch: `test_rendered_context_freshness_has_all_evidence_derived_states` … **ok** flag-on. The cite `:1600-1603` is exact — that is the `chip()` helper containing `start = html.index("Research context")`. |
| 3 | MAJOR | `ruff` fails on two brief-supplied import lines | **Half applied.** `:318` (`tests/test_board_lanes.py`) is fixed and verified: three spaces → `I001`, two spaces → `All checks passed!` (both measured). `:1335` is NOT fixed — two spaces still yields `I001` because the line is 114 chars against `line-length = 100` → **MAJOR 1**. The Task 3 Step 4 escape hatch (`:951-953`) was added as prescribed but does not cover the gate that catches this line. |
| 4 | MAJOR | Rule (3) contradicted three entries below it | **Applied, correct (executed).** The `:337`/`:364` disposition line is deleted; `:424` now reads "PASSES flag-on unchanged — leave it (rule 3); tightening … must not be done as a 'fix'" (`:2039-2041`); rule (3) carries "where rule (3) and an entry below disagree, rule (3) wins and the entry is stale" (`:1986`). Flag-on run: `test_composite_board_is_one_table_with_every_label_preserved`, `test_blocked_angle_reason_is_still_printed`, `test_symbol_panels_precede_the_drawer` — **all ok**. |
| 5 | MEDIUM | D10 `<h2> ≤ 8` did not discriminate | **Applied, correct (executed).** `:2279-2288` now asserts `<h2> <= 4`, keeps `<summary> <= 20`, and adds the legacy-rejection assertion. `LaneBoardParityAndSizeTests`: **Ran 3, OK**. Measured on the brief's fresh 8-symbol fixture: flag-on 54,574 B, 6 panels, 0 open, visible **2 `<h2>` / 0 `<summary>`**; legacy on the same fixture 64,218 B, visible **8 `<h2>` / 23 `<summary>`** — exactly the numbers written into the comment, and the summary leg does reject the legacy page (23 > 20). The layout file still runs 41 tests in 0.142 s despite the second render. Residual: the zero-margin interaction with the veto branch → **MINOR 5**. |
| 6 | MEDIUM | Docstring claimed a false byte-identity | **Applied, correct.** `:1485-1488` now says the `<h2>` is byte-identical to `:4213` and the eyebrow keeps `:4212`'s phrase and appends. Re-read: `:4212` = `<div class="eyebrow">Daily shortlist · TOP 5 PICKS TODAY</div>`; `:4213` = `<h2>Rule-based top 5 — best policy-and-liquidity fit today</h2>`; the brief emits that `<h2>` byte-identically (`:1541`) and the appended eyebrow at `:1540`. |
| 7 | MINOR | `test_attractiveness_v3` cite `:279` vs `:278` | **Applied, correct.** `:2108` now says `:278-288`; re-read: `:278` is the `def`, `:288` the last assertion (`assertIn("not missing UI", html)`). Task 6 Step 4's separate `:282` cite (the `hero-card` count line) is also exact — no contradiction. |
| 8 | MINOR | False byte-figure reconciliation | **Applied, correct.** `:2363-2366` now names the spec's self-contradiction. Re-read: spec `:16` (§1, lines 13–44) says "771 KB"; spec `:256` (§8, lines 239–258) says "782 KB". |
| 9 | MINOR | Rule (d) caveats missing | **Applied, correct.** `:1992-1998` adds both caveats. `:5540-5543` re-read and exact (`pinned_records = pinned_picks(data)` → `protected_card_ids.update(…)`). See the wording note above. |
| 10 | MINOR | `:2859` runs the experiment builders inside the offline suite | **Applied; cite drifts.** The paragraph is at `:1144-1151` (Task 4 Step 3, the right place). Claim re-verified by a call spy: `_default_experiment_lanes` fires **once**, returns the four lanes `['exp_beta','exp_spread','exp_tail','exp_tbill']`, the test passes. Cite → **MINOR 4**. |
| 11 | MINOR | Option C had no stated disposition | **Applied, correct.** `:136-139` — "If C, Tasks 1, 3, 4 and 6 are rewritten (both tuples, the `_EXPERIMENTS` map and four of the 16 module tests, the whole gather step, the caution group) and the brief returns to review." |
| 12 | MINOR | `EmptySlotConsolidationTests` left to a conditional | **Applied, correct (re-measured).** `:2045-2050` names the measured set. My flag-on run: `:88`, `:102`, `:111`, `:130` **ERROR** (`ValueError: substring not found` on the removed `"Context-aware Top 5"` anchor), `:122` `test_blocked_qm_slots_collapse_into_one_block` **ok** — exactly as written, and the `def` lines are exactly `:88/:102/:111/:122/:130`. The newly prescribed flag-on twin is satisfiable: on `_board(["AAA"], eligible=False)` flag-on, `"of 5 slots open"` occurs **once** above `id="agreement-table"` (twice on the whole page). |
| 13 | MINOR | Ambiguous panel-order parenthetical | **Applied, correct (measured).** `:2016-2018` now names each list. Measured on that fixture: panel order **MSFT, NVDA, VST**; `data["symbols"]` order **VST, NVDA, MSFT**. |

## Rev-5 delta — every changed line traced

`git diff 69819da..acb8946` touches three files: the brief (124 lines), the spec's I1 row
(1 line), and the round-4 receipt (added). Every brief hunk maps to a round-4 finding:
header/Status (revision bookkeeping), `:136-139` → MINOR 11, `:181-190` → MAJOR 1(c)(d),
`:318` and `:1335` → MAJOR 3, `:951-953` → MAJOR 3, `:1144-1151` → MINOR 10,
`:1485-1488` → MEDIUM 6, `:1984-1998` → MAJOR 4 + MINOR 9, `:2016-2018` → MINOR 13,
`:2039-2041` → MAJOR 4, `:2045-2050` → MINOR 12, `:2052-2064` → MAJOR 1(a)(b),
`:2097-2104` → MAJOR 2, `:2108` → MINOR 7, `:2279-2288` → MEDIUM 5,
`:2363-2366` → MINOR 8, spec `:288` → MAJOR 1(d). **Nothing unexplained.** Block-level
check: of the brief's 37 fenced blocks, exactly four differ from rev 4 (`b00`, `b20`,
`b21`, `b32`) and each is one of the four code-bearing fixes above.

## D13 / I1 still declared pending

Header `:3`; Status `:6`; Scope `:66` ("ONLY under owner ruling D13 option A"); its own
section `## Owner ruling required before dispatch — D13 (and the I1 veto window)` at
`:108` with the non-dispatch sentence at `:141-142`; Task 4 `:972` and `:1090`; Acceptance
`:2355` ("owner ruling D13 recorded in the spec BEFORE dispatch (and I1 not vetoed)").
The spec's pending-rulings section (`:277-290`) still ends with the blank owner line.

---

## What I executed and raw results

Scratch only, under gitignored `.tmp/brief39-review/`. Nothing tracked modified; no
network, no ledger, no full suite. Interpreter `.venv/bin/python` 3.12, cwd = scratch repo.

```
# rev-5 delta extraction
37 fenced blocks extracted from rev 5 -> .tmp/brief39-review/r5/blocks
diff vs r4/blocks: 4 changed (b00, b20, b21, b32), 33 identical

# re-applied to .tmp/brief39-review/r4/repo
b00 two-space comment            tests/test_board_lanes.py:5
b20 two-space comment            tests/test_attractiveness_dashboard.py (import line)
b21 revised docstring            options_researcher/attractiveness_dashboard.py
b32 revised acceptance test      tests/test_attractiveness_layout.py
Task 7 Step 1 (this file)        import contextlib + _legacy_layout() in the dashboard tests
:874 disposition                 both readings; :1591 rindex repair

# the two repaired tests
SymbolPanelStatusTests.test_render_uses_details_and_fail_visible_open_attribute
    literal "replace :893-894"   FAIL  -> AssertionError: '<details class="panel symbol-panel" open>'
                                          unexpectedly found (section still STALE from :891)
    keeping :893, replacing :894 SymbolPanelStatusTests  Ran 4  OK   (flag-on + legacy twin)
LoadContextTests.test_rendered_context_freshness_has_all_evidence_derived_states
    with rindex                  ok (flag-on)

# flag-on enumeration, rev-5 build (both repairs applied)
tests/test_attractiveness_dashboard.py   Ran 217  FAILED (failures=36, errors=7) = 43 broken
    = 45 - 2; neither repaired test appears in the broken list  -> the "45" statement holds
tests/test_attractiveness_layout.py      Ran 41   FAILED (failures=7, errors=6)  = 13 broken
    :337 ok | :364 ok | :424 ok        (rule (3)'s three protected tests)
EmptySlotConsolidationTests  Ran 5  FAILED (errors=4)
    :88 ERROR  :102 ERROR  :111 ERROR  :130 ERROR  |  :122 ok
    cause: ValueError: substring not found -> html.index("Context-aware Top 5")

# the brief's own tests, after the rev-5 edits
tests/test_board_lanes.py                     Ran 16  OK
LegacyByteIdentityTests                       Ran 1   OK   (flag-off == Task 2 snapshot)
LaneBoardLayoutTests                          Ran 10  OK
LaneBoardParityAndSizeTests                   Ran 3   OK   (incl. the tightened D10 test)
LaneBoardRenderTests                          Ran 9   OK
ExperimentLaneGatherTests                     Ran 5   OK

# gates
ruff check <5 changed files>   1 error
    I001  tests/test_attractiveness_dashboard.py:3934   (brief :1335)
    line length 114 vs pyproject line-length = 100
    ruff check --diff -> parenthesised 4-line import
    candidate A (parenthesised)      -> All checks passed!
    candidate B (comment dropped, 84) -> All checks passed!
ruff check options_researcher/board_lanes.py tests/test_board_lanes.py  ->  All checks passed!
    counterfactual: restore the three-space gap -> I001 reappears (round-4 diagnosis
    correct for THIS line only)
pyright options_researcher/attractiveness_dashboard.py options_researcher/board_lanes.py
    0 errors, 0 warnings, 0 informations   (exit 0)
    (tests/ is excluded by pyrightconfig.json; the only rev-5 module delta is a docstring)

# D10, fresh 8-symbol board (NVDA AMZN MSFT PLTR SMCI CRWV CEG VST), _DRAWER_INPUTS
flag-on   54,574 B | panels 6 | open 0 | visible 27,151 B, 2 <h2>, 0 <summary>
legacy    64,218 B | visible 40,761 B, 8 <h2>, 23 <summary>     -> summary leg rejects it
I1-VETO counterfactual (pinned_symbols passed through instead of set()):
          panels 6 | open 2 | visible 32,796 B, 4 <h2>, 6 <summary>
          -> Task 8's "0" becomes 2 (brief correct); <h2> hits the new limit of 4 exactly

# :277 fixture (SymbolPanelCollapseTests._data = VST, NVDA, MSFT), flag-on
ACCEPT (rev-5 code)   panels 3 | open 0     -> the brief's :277 rewrite is correct
VETO   counterfactual panels 3 | open 1     -> the brief's veto branch says 2 (MINOR 3)
panel order MSFT, NVDA, VST in both         -> MINOR 13's wording confirmed

# EmptySlot flag-on twin feasibility, _board(["AAA"], eligible=False)
'of 5 slots open'  page total 2 | above id="agreement-table" 1   -> prescribed twin holds

# hermeticity spy, tests/test_attractiveness_dashboard.py MainTests
test_main_loads_board_and_context_from_same_external_root  ok
_default_experiment_lanes calls: 1 | arg ('2026-07-24',) | 12.5 ms
    | lanes ['exp_beta','exp_spread','exp_tail','exp_tbill']
def line is :2801 (brief cites :2859 = the ad.main() call)

# cites re-read on origin/main @ f83428d
attractiveness_dashboard.py :4212 eyebrow | :4213 <h2> (byte-identical to the brief's emit)
                            :5540-5543 pinned_picks -> protected_card_ids
                            :5556-5558 protected_indexes computed | :5561 passed to _group_html
                            :5598-5600 the standing-directive comment
tests/test_attractiveness_dashboard.py :874 def | :889-892 in-patch | :893 reset | :894 assertion
                                       :1600-1603 chip() helper | :2801 def (not :2859)
tests/test_attractiveness_layout.py :88/:102/:111/:122/:130 defs | :254-275 _data | :278 comment
tests/test_attractiveness_v3.py :278 def, :282 hero-card count, :288 last assertion
config.py :660 PICK_PINNED_SYMBOLS = ["VST", "AMZN"]
pyproject.toml :30 line-length = 100
spec :16 (§1) "771 KB" | :256 (§8) "782 KB" | :36 D10 "≤ 8 … ≤ 20"
```

**Recommendation:** apply MAJOR 1 and MAJOR 2 (both one-paragraph edits, neither touching
code the brief supplies elsewhere) and the three MINORs, then the brief is ready for
hand-off the moment the owner records D13 and the I1 accept/veto. No re-review round is
warranted for edits of this size; a re-read of the five changed sentences is enough.
