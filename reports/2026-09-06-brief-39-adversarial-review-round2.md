# Brief 39 — independent adversarial review, round 2 (2026-09-06)

**Reviewer:** Opus, adversarial round 2 (independent; read-only on tracked files).
**Target:** `docs/superpowers/plans/2026-09-06-39-attractiveness-board-redesign-codex-brief.md`
rev 2 @ `f83963d` (1846 lines).
**Spec:** `docs/superpowers/specs/2026-09-06-attractiveness-board-redesign-design.md` (D1–D12, owner-APPROVED).
**Code base:** `origin/main` @ `f83428d`; `git diff --stat f83428d f83963d -- options_researcher/ tests/ config.py` is empty, so the working tree is the cited code.
**Round-1 receipt under audit:** `reports/2026-09-06-brief-39-adversarial-review-round1.md` (36 findings + 7 placeholders; rev 2 claims all applied).

**Method — what I actually ran** (scratch only, under gitignored `.tmp/brief39-review/`; nothing tracked was modified, no network, no ledger touch, no full suite):

1. Extracted the Task 3 module (brief `:559-821`) and the Task 1 + Task 3 tests (`:205-233`, `:394-548`) **verbatim** into a scratch package, added the three Task 1 constants to a copied `config.py`, injected the module as `options_researcher.board_lanes`, and ran the 15 unit tests.
2. `uv run ruff check` on the extracted module and test file.
3. `uv run pyright` on the extracted module (isolated project, repo's `basic` settings + the four `reportUnknown*: none` overrides).
4. Task 2's snapshot capture from the UNMODIFIED tree, twice, `cmp`'d.
5. Isolated pyright probes for the exact typing patterns the brief's Task 5/6 code uses.
6. Executed the Task 8 `_visible_html` helper (brief `:1732-1758`) against four hand-built nesting cases and against the real captured page.
7. Re-read every `file:line` the brief cites in `options_researcher/attractiveness_dashboard.py`, `config.py`, `options_researcher/experiments_dashboard.py`, `options_researcher/top3_snapshot.py`, `options_researcher/pick_tracker.py`, `research/hashing.py`, and the three test files.
8. Baseline `uv run python -m unittest discover -s tests -p 'test_attractiveness_layout.py'` → 27 tests OK in 0.12 s.

---

## Verdict: FAIL

Three BLOCKERs (one needs an owner ruling), eight MAJORs. The pure module (Task 3) remains
the strong part and is now genuinely typed — 15/15 green verbatim, ruff-clean, pyright-clean
once the Task 1 constants exist. Everything that touches the renderer is not yet safe to hand
off: the pyright gate the brief promises cannot pass as written, two brief-supplied tests are
unsatisfiable against the repo's own fixtures, the re-pin enumeration still misses tests
(including a hard-coded SHA-256 golden-bytes test), and the flag-on page structurally drops
three disclaimer sentences that the owner-approved spec and the brief's own Global Constraints
say stay verbatim.

---

## BLOCKERS

### 1. BLOCKER (owner ruling) — the flag-on page cannot satisfy the disclaimer contract the brief and spec both assert

- **Brief:** Global Constraints `:94-97` ("Every disclaimer string asserted by
  `tests/test_attractiveness_layout.py:456` … stays verbatim"); Task 6's replacement test
  `:1453-1456` asserts only 2 of the 13 sentences.
- **Spec:** §2.7 "every existing disclaimer string verbatim
  (`test_disclaimers_are_present_verbatim`)"; §6 invariant 4 "Every disclaimer string verbatim".
- **Evidence:** `tests/test_attractiveness_layout.py:434-454` lists 13 sentences. Three of them
  live only in sections the redesign removes from the flag-on page:
  - `options_researcher/attractiveness_dashboard.py:4215` "This is a fit ranking, not a
    prediction" — inside `_original_hero_html`, reachable only via `hero_html` (`:5683`), which
    the brief's flag-on branch never emits (`:1506-1530`).
  - `options_researcher/attractiveness_dashboard.py:4707` "owner-pinned visibility — not ranked;
    these cards do not compete with or reorder the Top-5 shortlist." — inside `_pinned_html`
    (`:4662`), removed under the flag.
  - `options_researcher/attractiveness_dashboard.py:4443` `_CONTEXT_LANE_DISCLAIMER`
    ("Experimental re-ordering by market context. …") — inside `_context_lane_html` (`:4468`),
    reached only through `_hero_html` (`:4423`), removed by D12.
  (`_quant_want_html:4585` and `_qm_hero_html:4312` survive because `qm_lanes_html` stays in the
  drawer — I checked both.)
- **Why it matters:** `test_disclaimers_are_present_verbatim` (`:456`) is a rendering test with
  the DEFAULT flag, so it FAILS the moment Task 6 lands, and it is not in Task 7's enumeration
  (brief `:1626`). Worse, the two documents Codex is told to obey say the strings survive, so
  the "correct" resolution is not derivable from the brief. This is authority wording — the
  class of regression `AuthorityWordingSurvivesLayoutTests` exists to prevent.
- **Exact fix:** get an owner ruling on the three sentences (they belong to sections D4/D12
  delete). Then amend the spec (§2.7, §6.4) and the brief's Global Constraints to read: "the ten
  disclaimer sentences whose sections survive stay verbatim; the hero fit-ranking sentence
  (`:4215`), the pinned-strip sentence (`:4707`) and `_CONTEXT_LANE_DISCLAIMER` (`:4443`) leave
  the page with their sections (owner-ruled 2026-09-06)". Add `:456` to Task 7 as **(c)**:
  legacy-wrap the existing test AND add a flag-on twin asserting the surviving ten verbatim.
  If the owner instead wants all thirteen kept, the brief must name where the three relocate
  (drawer) — that is a different implementation.

### 2. BLOCKER — `uv run pyright` (Task 8 Step 3 gate) cannot pass as written; four distinct error classes, all reproduced

`attractiveness_dashboard.py` is in `pyrightconfig.json` `include`. I reproduced each class in an
isolated scratch project with the repo's settings.

(a) **Undefined forward references.** Brief `:1262`, `:1270`, `:1274`, `:1283`, `:1326`, `:1361`
annotate `board: "LaneBoard"`, `col: "LaneColumn"`, `row: "BoardRow"`. `board_lanes` is imported
only *inside* the flag branch of `_render_result` (brief `:1475`), so those names are undefined at
module scope. Reproduced: `error: "LaneBoard" is not defined (reportUndefinedVariable)`.
`from __future__ import annotations` is present (`attractiveness_dashboard.py:30`) so runtime is
fine; pyright is not.
**Fix:** the file already has `if TYPE_CHECKING:` at `:50` — instruct Codex to add
`from options_researcher.board_lanes import BoardRow, LaneBoard, LaneColumn` there.

(b) **`Mapping[str, object]` iteration.** Reproduced 3 errors from the brief's own expressions:
- `:1178` `fresh = list(data.get("fresh_symbols") or [])` → `Argument of type "object | list[_T]" cannot be assigned to parameter "iterable"`
- `:1179` `stale = [str(s) for s in (data.get("stale_symbols") or [])]` → `"object" is not iterable`
- `:1368` `{... for sec in data.get("symbols", []) if isinstance(sec, Mapping)}` → `"object" is not iterable`
(The `positions.get("rows") or []` and `lane.get("failures")` forms at `:1229` and `:1186` do pass.)
**Fix:** guard each with an `isinstance(..., (list, tuple))` narrowing, as `_schwab_state_html`
does at `attractiveness_dashboard.py:1075-1076`.

(c) **The extraction signature makes previously-clean code dirty.** Brief `:1039` declares
`sec: Mapping[str, object]`. The moved body calls `_rank_groups_for_display(sec["groups"], tech=tech)`
(`:5550`, parameter is `list[dict]` at `:690`) and `float(sec["close"])` (`:5560`). Reproduced 3
errors (`object` not assignable to `list[dict]`; `object | None` not assignable to `dict | None`;
`object` not assignable to `ConvertibleToFloat`). Today the loop is clean only because `sec` is
inferred from `data: dict`. `context: Mapping[str, object] | None` (`:1039`) is likewise passed to
`_symbol_context_html(symbol: str, context: dict | None)` (`:4638`).
**Fix:** type the extraction `sec: dict`, `data: dict`, `context: dict | None` — the byte-identical
extraction must be type-identical too.

(d) **`select_qm_top_picks` called with a possibly-None context.** Brief `:1483`:
`qm_picks=select_qm_top_picks(data, qm_context, include_csp_watch=True)`. At that point
`qm_context = enrich_qm_context_with_candidates(data, qm_context)`
(`attractiveness_dashboard.py:5534`) whose declared return is `Mapping[str, object] | None`
(`:540`), while `select_qm_top_picks`'s parameter is non-optional `Mapping[str, object]` (`:489`).
The repo's ONLY other call site guards it with `assert isinstance(qm_context, Mapping)` at
`:4281` for exactly this reason. Round-1's "Verified correct by the reviewer" line
("`select_qm_top_picks` call valid and `qm_context` non-None at the call site") is wrong.
**Fix:** `qm_picks=(select_qm_top_picks(data, qm_context, include_csp_watch=True) if isinstance(qm_context, Mapping) else None)`
— `None` is already the module's "lane unavailable" input (`board_lanes.lane_from_qm`, brief `:708-710`).

### 3. BLOCKER — `test_details_render_only_for_table_names` is unsatisfiable, and the obvious "fix the code" reading breaks spec §6.6

- **Brief:** `:1437-1442`
  `self.assertEqual(rendered, names_on_table)` where `rendered = set(re.findall(r'id="symbol-([A-Z]+)"', html))`
  and `names_on_table` comes from `<td class="sym">`.
- **Evidence:** `pinned_picks` (`attractiveness_dashboard.py:576-594`) returns one record per
  `config.PICK_PINNED_SYMBOLS` (`config.py:660` = `["VST", "AMZN"]`) **whether or not the symbol
  has a section**. The brief feeds those into `pinned=` (`:1485`), and `build_lane_board` makes
  every pinned name a row (brief `:811-819`, proven by
  `test_pinned_names_are_rows_even_when_no_lane_names_them`, which I ran green). But
  `_pick_details_html` skips a row with no section (`if sec is None: continue`, brief `:1372-1373`).
  On the test's own fixture `_board(["NVDA","AMZN","MSFT"])`, VST is a table row with no panel, so
  `rendered ⊊ names_on_table` and the assertion fails.
- **Why it matters:** the brief tells Codex "The TESTS are the contract … if the implementation
  disagrees, fix the code" (`:827`). Satisfying this test by dropping pinned rows without sections
  violates spec §6 invariant 6 and the 2026-07-16 owner ruling. Satisfying it by rendering a panel
  for a symbol with no data is impossible.
- **Exact fix:** replace the assertion with
  `self.assertTrue(rendered <= names_on_table)` plus
  `self.assertIn("NVDA", rendered)` and `self.assertNotIn("VST", rendered)`, and add one line to
  the brief stating explicitly that a pinned row with no section renders a row but no detail panel.

---

## MAJORS

### 4. MAJOR — Task 7's re-pin enumeration is still materially incomplete, including a hard-coded golden SHA-256

Round-1 finding 15 said the dashboard file was under-scoped; rev 2 enumerated ~17 tests. Still missing:

- `tests/test_attractiveness_layout.py:179`, `:191`, `:200`, `:208`, `:220` — five tests in
  `PositionsAndRiskFirstTests` all slice
  `html[html.index("POSITIONS &amp; RISK"):html.index("Rule-based top 5")]`. Under the flag,
  "POSITIONS &amp; RISK" (from `_registered_bets_tracker_html`, `:4956`) moves into the drawer
  (brief `:1526`) i.e. AFTER the agreement table's h2, so the slice becomes the empty string:
  four fail on `assertIn`, and `:200` passes **vacuously** on an empty slice — a silently lost
  contract. Brief `:1626` enumerates only `:165` from this class.
- `tests/test_attractiveness_dashboard.py:2239`
  `test_flag_off_matches_post_brief26_golden_bytes` asserts
  `hashlib.sha256(pre_tracker_bytes).hexdigest() == "3407b733…"` (`:2263-2266`) on a default-flag
  render. It fails under the flag and is unlisted. The dangerous repair is re-pinning the digest;
  the correct one is adding `mock.patch.object(config, "BOARD_LANES_ENABLED", False)` next to the
  existing `CONTEXT_LANE_ENABLED` patch at `:2245`.
- `tests/test_attractiveness_layout.py:456` — see BLOCKER 1.
- Two more `Rule-based top 5` order pins the brief does not name: `test_attractiveness_dashboard.py:3341`
  and `tests/test_attractiveness_v3.py:285`. Both likely survive, but Task 6 Step 4 (brief `:1580-1582`)
  tells Codex "Any other file failing is a regression — STOP and report", so an unlisted failure in
  `test_attractiveness_v3.py` halts the run.
- **Fix:** add the five `PositionsAndRiskFirstTests` line anchors and `:2239` to the enumeration with
  explicit (c) dispositions, and add one sentence: "re-pinning a hard-coded digest or golden hash is
  never an acceptable repair — legacy-wrap it."

### 5. MAJOR — the prescribed fix for the panel tests ignores a panel-ORDER inversion the redesign introduces

- **Brief:** `:1626` — `:277`, `:286`, `:296` → "these still hold for the panels inside
  `#pick-details`; re-point their slice to that section".
- **Evidence:** `_pick_details_html` iterates `wanted = [r.symbol for r in board.rows]`
  (brief `:1367`), i.e. baseline-pick order, not `data["symbols"]` order. I ran the actual fixture
  from `SymbolPanelCollapseTests._data()` (`tests/test_attractiveness_layout.py:254-275`):
  `data["symbols"]` order is `['VST','NVDA','MSFT']` but `select_top_picks` order is
  `['MSFT','NVDA','VST']`. `test_clean_panels_are_closed_except_owner_pinned_symbols` (`:283`)
  slices `html[html.index('id="symbol-VST"'):html.index('id="symbol-NVDA"')]`, which inverts to an
  empty slice — re-pointing the slice to `#pick-details` does not fix it.
- **Fix:** state in the brief that the flag-on page renders panels in board-row order, and rewrite
  `:277` to locate the VST panel by
  `vst = html[html.index('id="symbol-VST"'):]` truncated at the next `id="symbol-` (or by regex on
  the panel opener), not by a pair of anchors assumed to be in universe order.

### 6. MAJOR — `test_relocated_content_is_appended_after_the_six_drawer_sections` raises `ValueError` on its own fixture

- **Brief:** `:1444-1451`, `six = [drawer.index(s) for s in DiagnosticsDrawerTests._DRAWER_SECTIONS]`,
  rendered through `LaneBoardLayoutTests._html()` (`:1420-1422`) which passes no `context`,
  `qm_context` or `research_views_status`.
- **Evidence (executed):** on the captured render of `_board(["NVDA","AMZN","MSFT"])` with no
  context, `"Quant-want background"` and `"Market context"` are **absent** — `_quant_want_html`
  returns `""` without `quant_want` (`attractiveness_dashboard.py:4563-4566`) and `_market_html`
  returns `""` without `context["market"]` (`:4593-4597`), and `_diagnostics_drawer_html` drops
  empty sections (`:5493`). The existing `DiagnosticsDrawerTests._rendered()`
  (`tests/test_attractiveness_layout.py:384-403`) supplies all three inputs precisely so the six
  exist.
- **Fix:** give `LaneBoardLayoutTests._html()` the same `context` / `qm_context` /
  `research_views_status` payload as `DiagnosticsDrawerTests._rendered()`, or assert only over the
  sections actually rendered.

### 7. MAJOR — the new CSS is an unverified transplant from the mockup: an undefined variable and no base `.chip` rule

- **Brief:** `:1552-1566`. `:1562` uses `background:var(--surface-2)` for `.agreement-table td.lane-off`;
  `:1564` defines only `.chip.on`, `.chip.warn`, `.chip.veto`, each setting `border-color` alone.
- **Evidence:** `_STYLE`'s `:root` (`attractiveness_dashboard.py:2316-2341`) defines
  `--good`, `--watch`, `--bad`, `--line` but **not** `--surface-2`. Grepping `_STYLE`
  (`:2315-2998`) finds `.meta-chip`, `.evidence-chip`, `.event-chip` — there is **no base `.chip`
  rule**, so `<span class="chip">` has no `border-style` and `border-color` alone paints nothing.
  The approved mockup `docs/superpowers/specs/assets/2026-09-06-board-redesign-option-a-v2.html`
  does define `.chip{…border:1px solid var(--line);background:var(--surface-2)…}` plus its own
  `--surface-2`, `--seq4`, `--seq6`, `--serious`, `--ink-2` palette — none of which exists in `_STYLE`.
- **Why it matters:** the colour-coded agreement chips and the "lane off" shading are the visual
  contract of the owner-approved Option A (D7), and the fail-visible lane-off cell loses its only
  marker. The brief's hedge at `:1569-1571` ("substitute the real names") turns a copy-verbatim block
  into a judgement call Codex has to get right silently.
- **Fix:** add an explicit base rule to the CSS block and replace the undefined token, e.g.
  `.chip{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:1px 8px;font-size:12px;margin:1px 2px 1px 0}`
  and `.agreement-table td.lane-off{background:var(--surface-soft)}` (`--surface-soft` exists at `:2320`).

### 8. MAJOR — the D10 acceptance measurement does not measure what D10 rules

- **Brief:** `:1732-1735` `_visible_html` docstring "What the reader sees with fold-outs closed"; the
  openers tuple is `'<details class="panel symbol-panel"'` (no trailing `>`), so it strips panels that
  render with the ` open` attribute too. Test `:1771-1777`.
- **Evidence (executed):** the helper's nesting logic is CORRECT (4/4 of my probe cases pass,
  including nested and unclosed `<details>`). But on the real captured render of
  `_board(["NVDA","AMZN","MSFT"])` **all three symbol panels carry ` open`** (status `STALE`, forced
  open by `attractiveness_dashboard.py:5601-5602` / `_panel_status:826`), and `_visible_html` drops
  all three: 44,370 bytes → 31,095, `<h2>` 13 → 6, `<summary>` 20 → 10. On the acceptance fixture
  (brief `:1773`, eight symbols including pinned VST and AMZN) the same happens — pinned names are
  force-opened by `:5602` — so the ≤ 8 / ≤ 20 test passes while the reader's actual first screen
  still contains large open panels.
- **Why it matters:** D10 is the owner's ruling on how "less long" is measured, taken specifically
  because round-1 killed the byte target. An acceptance test that cannot fail is not acceptance.
- **Fix:** either (i) count force-open panels as visible (drop only `<details class="panel symbol-panel">`
  with no ` open`, and `diagnostics-drawer`), or (ii) keep the counterfactual measure but add to the
  test and the PR body a second reported number — how many panels render `open` on Friday's data —
  and say in the brief that D10 is measured with every fold-out treated as closed.

### 9. MAJOR — the ruff gate the brief promises fails twice, in code the brief itself supplies

- **Brief `:209-213` + `:829-830`:** the Task 1 test import block is
  `from pathlib import Path` / `import unittest` / blank / `import config` / `from options_researcher import board_lanes as bl`,
  and Step 4 states `uv run ruff check … tests/test_board_lanes.py` → "All checks passed!".
  **Executed:** `I001 Import block is un-sorted or un-formatted` (isort is enabled —
  `pyproject.toml:40` `select = ["E4","E7","E9","F","I"]`). Fix: `import unittest` before
  `from pathlib import Path`.
- **Brief `:1609-1618`:** Task 7 Step 1 adds `import contextlib` immediately above the helper,
  i.e. mid-file. **Executed:** `E402 Module level import not at top of file` (E402 ∈ `E4`). The brief
  warns about exactly this at `:202` and then commits it. Fix: put `import contextlib` in each file's
  top import block (`tests/test_attractiveness_dashboard.py:2-16`,
  `tests/test_event_awareness.py:5-19`, `tests/test_attractiveness_layout.py:10-19`).
- Also `:1607` says "Add the flag-off helper to **both** files" while three files are in scope.

### 10. MAJOR — Task 7 Step 3 points Codex at the wrong lines for a "copy verbatim" move, and drops a needed patch

- **Brief `:1704-1705`:** "the old test renders through a specific entry point at `:396-410` (read it);
  call the same one so `event_view` reaches `render`."
  **Evidence:** `tests/test_event_awareness.py:396-410` is `def card_fragment(page, symbol, surface)`,
  a fragment extractor. The actual render is `:419` `html = ad.render(data, event_view=view)`, inside
  `with (mock.patch.object(config, "CONTEXT_LANE_ENABLED", True), mock.patch.object(config, "PICK_PINNED_SYMBOLS", ["NVDA"]))`
  at `:415-418`. The brief's replacement test (`:1693-1694`) patches only `BOARD_LANES_ENABLED`.
- **Brief `:1642-1643, :1648, :1653, :1657`:** the lift ranges are wrong.
  Real: `card()` body `:313-338` (the closing `}` is `:338`); `symbols` `:340`; `data` `:341-368`;
  `view` `:374-391`; `chips()` `:393-394` (only this one is right). `:339-375` sweeps in
  `grades_before` (`:369-371`), `picks_before` (`:372`) and `sections_before` (`:373`), which are
  not part of the fixture; `:376-392` starts two lines inside the `view` dict.
- **Fix:** correct all four ranges, replace `:396-410` with "`:419`, keeping the `CONTEXT_LANE_ENABLED`
  and `PICK_PINNED_SYMBOLS` patches from `:415-418`", and state which of those two patches the new
  tests need (the second one matters: without it `config.PICK_PINNED_SYMBOLS` = `["VST","AMZN"]`,
  neither of which is in the fixture).

### 11. MAJOR — the change invalidates H7 diagnostic source-hash receipts, and the brief never says so

- **Evidence:** `research/hashing.py:132`
  `DIAGNOSTIC_SOURCE_PATHS_V2 = SOURCE_HASH_PATHS + ("options_researcher", "tools")`, walked as a
  directory (`:99-109`). Adding `options_researcher/board_lanes.py` and editing
  `attractiveness_dashboard.py` and `config.py` therefore change `diagnostic_source_hash()`.
  `options_researcher/h7_data_gate.py:748` rejects any receipt whose `source_hash` no longer matches.
- **Why it matters:** CLAUDE.md's H7 operator order is source health → data gate → watcher. Landing
  this on a session whose source-health receipt was already written invalidates that session's
  real-entry authority. The brief's closing note (`:1844-1846`) names the pick tracker's
  `IMMUTABLE_HISTORY_CONFLICT` but not this. `FEASIBILITY_SOURCE_PATHS` is correctly untouched
  (I verified `h7_schwab_window_registration.py:143-194` contains none of the three files) — that
  is a different gate.
- **Fix:** add one line to Acceptance/PR-body: "landing changes `diagnostic_source_hash()`
  (`research/hashing.py:132`); H7 source-health and data-gate receipts written before the merge are
  invalidated and must be re-run before the next entry window (owner-only)."

---

## MEDIUM

12. **MEDIUM — a false claim is baked into shipped code.** Brief `:1264-1266`:
    `_agreement_table_html`'s docstring says the `<h2>` text is kept "because tests and **the pick
    tracker** locate the shortlist by it". The pick tracker binds an HTML comment digest
    (`options_researcher/pick_tracker.py:52` `_HTML_SOURCE_DIGEST_PREFIX`, bound at
    `attractiveness_dashboard.py:5877`); grep for `Rule-based top 5` across `*.py` returns only
    `attractiveness_dashboard.py:4213` and test files. Fix: delete "and the pick tracker" from the
    docstring. (The rest of the claim is true — 20+ test assertions key on that string.)

13. **MEDIUM — new cite drift in rev 2** (round-1 finding 18 was "fixed"):
    - `:1023-1028` "`stale_symbols` (`:5550`), `pinned_symbols` (`:5551`)" — actually `:5544` and
      `:5545`; `:5550`/`:5551` are `ranked_groups` and `section_stale`. `protected_card_ids` is
      `:5539` (+ update `:5541-5543`), not `:5541-5544`.
    - `:150` "`qm_context` is a Mapping at the call site (`enrich_qm_context_with_candidates`, `:5521`)"
      — the call is `:5534`; `:5521` is a docstring line. (And it is not a Mapping — see BLOCKER 2d.)
    - `:74` "computed OUTSIDE the flag branch (`:5515-5528`…)" — the computations are `:5524-5533`;
      `:5515` is the return annotation.
    - `:966` "`_board` (`:44-58`)" — `_board` is `:54-69`; `:44-58` straddles `_put_section`.
    - `:311-312` "the import block at `:10-18`" — it is `:10-19`.
    - `:177` CHAINS_ABSENT "not a failure (`:1069-1080`)" — that branch is `:1081-1091`.
    - `:162` `_error_card` "(`:250-259`)" is right, but its key is `max_asof`, not `asof`
      (`experiments_dashboard.py:257`), and it sets `symbol: "ALL"`.
    - `:1011` lists `_panel_status` under "Consumes" with `:5594` (a call site); the definition is
      `:806-827`.

14. **MEDIUM — a stated Inference is false.** Brief `:1033`: hoisting `evaluation_date` "also fixes
    the latent `NameError` when `data['symbols']` is empty — **Inference**". Today `evaluation_date`
    is not referenced after the loop (`attractiveness_dashboard.py:5665-5762` uses
    `str(data.get("evaluation_date") or data_as_of)` at `:5716`), so there is no latent bug; the
    NameError would be *introduced* by Task 6. Fix: restate as "required by Task 6, which reads it
    after the loop".

15. **MEDIUM — the D5 authority for computing experiment lanes on the board is not carried into the
    brief.** `.cursorrules` (2026-08-09 authorization) requires the attractiveness experiments to be
    "display-only, **disabled by default**". `BOARD_LANES_ENABLED: bool = True` (brief `:259`) makes
    all four lanes compute and display on every real build. Spec §4 covers this ("owner-directed
    display decision (D5)"); the brief's Scope only says "no change to … the `EXP_*` flags" (`:83`).
    Fix: quote the spec §4 sentence in the brief's Scope so the executor and any later auditor see
    the authority. (For the record: none of the four dict lanes is flag-gated —
    `experiments_dashboard.py:262-282`; only `exp_short` is — so the columns will have members.)

16. **MEDIUM — brief-supplied test slices a panel with a naive `</details>` search.** Brief `:1698-1699`:
    `panel = html[panel_start: html.index("</details>", panel_start)]`. Symbol panels nest up to three
    levels (`<details class="panel symbol-panel">` → `<details class="group-section">`
    (`attractiveness_dashboard.py:3340`) → `<details><summary>payoff ladder</summary>`
    (`:3296`)), so the slice stops at the first *inner* close. It only works because the event fixture's
    cards carry `"scenarios": []`. Fix: reuse the (correct) nesting walker from `_visible_html` or slice
    to the next `id="symbol-` anchor.

17. **MEDIUM — spec §2.2 says four tiles; the code can emit five.** Brief `:1248-1258` prepends a
    "Positions / UNREAD" tile when `missing_sources` is non-empty, into a
    `grid-template-columns:repeat(4,…)` grid (`:1556`). Fix: fold the UNREAD state into the
    existing "Open option" tile, or state that the grid wraps.

---

## MINOR

18. `_symbol_panel_html` keeps a `data` parameter that is unused after the `evaluation_date` hoist
    (brief `:1039` vs the loop body `:5549-5664`, which reads only `sec`, `context`, `event_view`,
    `evaluation_date`, `stale_symbols`, `pinned_symbols`, `protected_card_ids`). Round-1 finding 33
    ("unused params") is not applied here.
19. Round-1's file-handle-leak finding is not applied to the brief's own commands: `:301`
    `open(...,"w",encoding="utf-8").write(html)` and `:1801` `open('.tmp/dashboard/attractiveness.html').read()`.
20. Task 5 never says WHERE `_symbol_panel_html` is placed in the file (Step 1 `:1036-1048` only says
    "move the loop body into"). Harmless, but two readings.
21. Flag-on `event_css` (brief `:1504-1505`) probes `hero_html` and `pinned_html`, which are not on the
    flag-on page — a false-positive `_EVENT_STYLE` inclusion, and it keeps two dead strings alive.
22. The flag-on path still builds `symbols_html` (all 18 panels, ~700 KB on Friday's data) and discards
    it, then re-renders the table names in `_pick_details_html` — the panels are rendered twice per build.
    Worth a note in the PR body next to the added `build_experiment_lanes` cost (~3.3 s, round-1 measured).
23. The `LANE BOARD FAILED` fallback (brief `:1499-1501`) emits `_open_slots_notice_html` AND
    `hero_html`, whose `_original_hero_html` already appends its own open-slot block
    (`attractiveness_dashboard.py:4200-4203`) — the notice prints twice in the failure path.
24. `_open_slots_notice_html` under the flag emits `class="hero-card … empty-slot"` markup
    (`_open_slot_group_html:4096`) with no `hero-grid` parent; the card will not lay out as it does today.
25. `row.fav_count * 14` (brief `:1308`) is a bare pixel constant in rendering code. Display-only, so
    `.cursorrules`' "every number in strategy logic comes from config.py" does not bind, but it is the
    only unexplained number in the brief.
26. Task 8 Step 4 / Acceptance (`:1798`, `:1830`) overwrite the local `.tmp/dashboard/attractiveness.html`
    and `picks_snapshot.json`. Safe (it reads ops, writes locally) but should be said.

---

## Verified correct (so a later round does not re-litigate)

- **Task 3 module + 15 tests: green verbatim** (see raw output below), ruff-clean, and pyright-clean
  once `BOARD_FAVOURABLE_LANES` / `BOARD_CAUTION_LANES` exist (the only 3 errors without them are
  the missing attributes). Round-1 finding 8 is genuinely fixed for this module.
- **Task 2 capture is deterministic**: two runs, 44,370 bytes, `cmp` identical.
- `_visible_html`'s nesting walker is correct (nested, sibling, unclosed, and non-target `<details>`).
- All `config.py` cites exact: `PICK_TOP_N` `:650`, `CHAIN_STALE_BLOCK_SESSIONS` `:690`,
  `CONTEXT_LANE_ENABLED` `:929`, experiment block `:932`, `PICK_PINNED_SYMBOLS` `:660`,
  `ATTRACTIVENESS_UNIVERSE` `:674`.
- Task 4's anchors exact: `assemble` `:1562-1571`, `open_positions` gate `:1745`,
  `page_as_of = _page_data_as_of(canonical_symbols)` `:1751`, `out` `:1755-1776`, attach `:1777`,
  `_gather_all` `:1784`. `data["blocked"]` exists (`:1757`). `mock.patch("options_researcher.experiments_dashboard.build_experiment_lanes")`
  does intercept, because `_default_experiment_lanes` resolves the attribute at call time (brief `:944-950`).
  `build_experiment_lanes(symbols, *, asof)` matches `experiments_dashboard.py:262`.
- The hermeticity fix works: `assemble(symbol_sections=…)` sets `real_assembly=False` (`:1584`), so no
  injected test computes lanes. Baseline layout suite: 27 tests, 0.12 s, no disk.
- Ranking / grades / snapshot / source-row hashes are computed outside the flag branch
  (`:5524-5533`, `:5751-5761`) and are structurally untouched. `source_rows_sha256` derives from quote
  rows, not the HTML (`:5875`), so the Task 8 parity claim holds. Output paths and keys check out:
  `OUTPUT_PATH` `:53`, `PICKS_SNAPSHOT_PATH` `:55`, `frozen_baseline.candidates[].symbol` `:5408-5412`
  + `:5300`, `source_rows_sha256` `:5886`.
- `FEASIBILITY_SOURCE_PATHS` (`h7_schwab_window_registration.py:143-194`) contains none of
  `config.py`, `attractiveness_dashboard.py`, `board_lanes.py`.
- Data-shape claims re-verified: baseline pick `:357-364` (no top-level `status`), `_block` `:1866-1870`,
  `_open_slots_html` `:4104` / `_empty_hero_slot` `:4116`, the watch-inclusive slot count `:4200-4203`,
  `_event_chips_html` `:3065-3079` (the brief's regex matches its exact markup),
  `_freshness_html`'s positional/keyword signature `:3691-3698` (the brief's drawer call matches),
  `trading_sessions_between` `top3_snapshot.py:83` (returns a negative int when `start > end`, raises on
  a bad date — both handled), `DashboardRenderResult` `:61-67`, `render(… event_view=)` `:5765-5773`.
- The brief's flag-on drawer list reproduces today's six calls exactly (compare brief `:1516-1521` with
  `attractiveness_dashboard.py:5712-5719`), with the five relocated items appended after them.
- The `test_removed_surfaces_are_absent` targets are all present in today's page (checked against the
  captured render), so the assertions are meaningful rather than vacuous.
- `29 sessions unmarked` and `1 capture failure in window` in the Task 5 tests are arithmetically right
  (`np.busday_count`: 2026-07-27→2026-09-04 = 29; 09-01→09-04 = 3 ≤ `CHAIN_STALE_BLOCK_SESSIONS`;
  08-01→09-04 = 24 > 3).
- The status strip mirrors `_schwab_state_html`'s retention rule faithfully (`:1058-1110`).
- No ledger write, no registration, no authority flip, no live-order path, no network call, no
  provider call, no JavaScript, no owner-provenance number invented; `PICK_TOP_N` and
  `CHAIN_STALE_BLOCK_SESSIONS` are reused rather than restated. Brief 39 is reserved in
  `docs/superpowers/plans/BRIEF-NUMBER-REGISTRY.md:22`. Header block and body order conform to
  `.agents/skills/codex-brief-writing/SKILL.md`.
- D1–D9, D11, D12 are all delivered by the brief. D10 is delivered in wording but not in measurement
  (MAJOR 8).

---

## Round-1 findings status

| # | Round-1 finding | Status in rev 2 |
|---|---|---|
| 1 | Acceptance targets impossible → restate as VISIBLE | **Applied, defective** — D10 recorded, but the measurement strips force-open panels (MAJOR 8) |
| 2 | `evaluation_date` / `status_labels` are loop-locals | Applied (`:1030-1032`); the supporting Inference is false (MEDIUM 14) |
| 3 | `_symbol_panel_html` signature + `symbol_names.append` | Applied; cite drift on `stale_symbols`/`pinned_symbols` and an unused `data` param (MEDIUM 13, MINOR 18) |
| 4 | `class="drawer"` does not exist → `id="diagnostics"` | Applied |
| 5 | `_render_populated()` / nested `chips()` | **Partial** — fixture lift added, but wrong line ranges and a wrong "entry point" (MAJOR 10) |
| 6 | Event-line union contract | Applied (D11) |
| 7 | Ungated experiment default hits 65 test sites | Applied and verified (`real_assembly` gate) |
| 8 | 11 pyright errors in the module | **Partial** — module is clean; Task 5/6 code has four new error classes (BLOCKER 2) |
| 9 | Blocked-record shape has no `reason` | Applied |
| 10 | `_open_slots_notice_html(data, watch_picks)` | Applied, matches `:4200-4203` |
| 11 | WP-G retention rule mis-stated | Applied |
| 12 | Closes dot hard-coded green | Applied |
| 13 | Digest is bound in the publish path | Applied |
| 14 | `event_css` before `body_html`; hoist `details_html` | Applied |
| 15 | Dashboard test file under-scoped | **Partial** — `:2239` golden-bytes and the five `POSITIONS &amp; RISK` tests still missing (MAJOR 4) |
| 16 | `_experiments_shelf_html` docstring forbids it | Applied |
| 17 | Legacy snapshot captured too late | Applied (Task 2 precedes Tasks 4–6) |
| 18 | Cite drift | **Partial** — the six named cites are fixed; eight new ones introduced (MEDIUM 13) |
| 19 | Baseline pick has no `status` key | Applied |
| 20 | Class is `DiagnosticsDrawerTests` | Applied |
| 21 | Heading is `DATA FRESHNESS` | Applied |
| 22 | `mock` not imported in the layout file | Applied (`:311-312`; range off by one line) |
| 23 | Mid-file import → E402 | **Partial** — fixed in Task 1, re-introduced in Task 7 (`import contextlib`), and Task 1's block now fails I001 instead (MAJOR 9) |
| 24 | `pyrightconfig.json` include | Applied |
| 25 | `exp_short` dataclasses; 09-04 beta/tbill measurements | Applied (`asof` vs `max_asof` nit, MEDIUM 13) |
| 26 | Spec D4 vs "remove the context cards" | Applied (D12) |
| 27 | API deviates from spec §4 sketch | Applied (deviation note `:179-184`) |
| 28 | Only `ALIGNED` counts | Applied; proven by the test I ran |
| 29 | CSS class list incomplete | **Partial** — still no base `.chip`, and `--surface-2` does not exist (MAJOR 7) |
| 30 | No WP-* labels | Applied (WP-A…WP-H) |
| 31 | Test count is 15, not 13 | Applied |
| 32 | Helper locations `:3427`, `:3454` | Applied and verified |
| 33 | File-handle leak / unused params | **Missing** — `:301` and `:1801` still leak; `data` param unused (MINOR 18–19) |
| 34 | 782,263 bytes | Applied |
| 35 | `_board` kwargs collision | Applied (`setdefault`) |
| 36 | (grouped LOW) | Applied |
| P1 | Placeholder: Event ctor | Applied (fixture lift replaces it) |
| P2 | Placeholder: mark-age rule | Applied (`CHAIN_STALE_BLOCK_SESSIONS` reused) |
| P3 | Placeholder: "today's assembly" ellipsis | Applied as an instruction (`:1536`, "copied verbatim", exact range) |
| P4 | Placeholder: class name | Applied |
| P5 | Placeholder: `tests/__init__.py` | Applied (`PYTHONPATH=tests`, "do not add one") |
| P6 | Placeholder: digest marker | Applied |
| P7 | Placeholder: Task 6 delegation | **Partial** — Task 7 still delegates ("the executor confirms the exact set") and the set is incomplete (MAJOR 4) |

---

## What I executed and the raw results

### A. Task 3 module + Task 1/3 tests, verbatim from the brief

Setup: brief `:559-821` → `.tmp/brief39-review/pkg/board_lanes.py`; brief `:205-233` + `:394-548`
→ `.tmp/brief39-review/tests/test_board_lanes.py`; `config.py` copied and the brief's `:249-261`
constant block appended; the module injected as `options_researcher.board_lanes`.

```
test_constants_carry_display_only_provenance_comment ... ok
test_lane_board_constants_exist_and_are_disjoint ... ok
test_agreement_counts_favourable_lanes_only ... ok
test_baseline_order_first_then_favourable_count_then_symbol ... ok
test_beta_lane_has_no_metric_order_and_lists_by_symbol ... ok
test_blocked_name_carries_reason_code_and_detail_and_is_never_promoted ... ok
test_build_never_mutates_inputs ... ok
test_columns_are_the_eight_lanes_in_favourable_then_caution_order ... ok
test_context_marks_other_than_aligned_are_shown_but_never_counted ... ok
test_describing_lane_overflow_takes_largest_metric_and_says_so ... ok
test_experiment_lane_error_card_becomes_unavailable_state_not_a_raise ... ok
test_failed_lane_keeps_its_column_and_leaves_the_denominator ... ok
test_gather_level_error_marks_every_experiment_column_unavailable ... ok
test_pinned_names_are_rows_even_when_no_lane_names_them ... ok
test_ranking_lanes_are_capped_and_composite_ties_break_by_baseline_then_symbol ... ok
----------------------------------------------------------------------
Ran 15 tests in 0.002s
OK
```

### B. ruff

```
$ uv run ruff check <board_lanes.py copy> <test_board_lanes.py copy>
I001 [*] Import block is un-sorted or un-formatted
 --> tests/test_board_lanes.py:5:1
Found 1 error.
```
(Module itself: clean. See MAJOR 9.)

```
$ uv run ruff check <import contextlib placed mid-file>
E402 Module level import not at top of file
```

### C. pyright

```
$ uv run pyright   # module only, repo settings, config WITHOUT the Task 1 constants
board_lanes.py:164:32 - error: "BOARD_FAVOURABLE_LANES" is not a known attribute of module "config"
board_lanes.py:230:33 - error: "BOARD_FAVOURABLE_LANES" is not a known attribute of module "config"
board_lanes.py:230:72 - error: "BOARD_CAUTION_LANES" is not a known attribute of module "config"
3 errors

$ uv run pyright   # same, with the constants present
0 errors, 0 warnings, 0 informations
```

Probes for the Task 5/6 patterns (BLOCKER 2):

```
# forward reference with no import
def f(x: "LaneBoard") -> str: ...
  error: "LaneBoard" is not defined (reportUndefinedVariable)

# Mapping[str, object] iteration
list(data.get("fresh_symbols") or [])                 -> error: "object | list[_T]" not assignable to "Iterable[_T]"
[str(s) for s in (data.get("stale_symbols") or [])]   -> error: "object" is not iterable
{... for sec in data.get("symbols", []) ...}          -> error: "object" is not iterable
[r for r in (positions.get("rows") or [])]            -> (no error)
lane.get("failures") if isinstance(lane, Mapping)     -> (no error)

# sec: Mapping[str, object] in the extraction
rank(sec["groups"], tech=sec.get("technicals"))       -> 2 errors (object -> list[dict]; object|None -> dict|None)
float(sec["close"])                                   -> error: object not assignable to ConvertibleToFloat
```

### D. Task 2 snapshot capture (determinism)

```
$ PYTHONPATH=tests uv run python -c "…ad.render(_board(['NVDA','AMZN','MSFT']))…"   # run 1
44370 bytes
$ …                                                                                  # run 2
44370 bytes
$ cmp legacy_1.html legacy_2.html
DETERMINISTIC: identical
```

### E. `_visible_html` (brief `:1732-1758`), executed

```
OK  nested details inside a symbol panel  -> '<a><b>'
OK  open symbol panel + drawer            -> '<p1><p2><p3>'
OK  non-target <details class="group-section"> preserved
OK  unclosed <details> tail dropped       -> '<z>'
legacy: bytes 44370 -> visible 31095 | h2 13 -> 6 | summary 20 -> 10 | open panels 3
```
All three symbol panels in that fixture render with ` open` (status `STALE`) and are stripped anyway.

### F. Ordering and fixture probes

```
data["symbols"] order:      ['VST', 'NVDA', 'MSFT']
select_top_picks order:     ['MSFT', 'NVDA', 'VST']     # => flag-on panel order inverts (MAJOR 5)
pinned_picks:               ['VST', 'AMZN']             # VST has no section in the _board fixture (BLOCKER 3)

drawer sections present on _board(["NVDA","AMZN","MSFT"]) with no context/qm_context:
  PRESENT  QM MOVEMENT LANE
  PRESENT  QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5
  PRESENT  Research context and coverage
  PRESENT  Passive research views
  ABSENT   Quant-want background          # => MAJOR 6
  ABSENT   Market context                 # => MAJOR 6
removed-surface markers, all PRESENT today (so the NotIn assertions are meaningful):
  sticky-nav, id="context-aware-top-5", VST / AMZN — ALWAYS SHOWN,
  CONTEXT-AWARE SHORTLIST, QM MOVEMENT LANE</h2>, CORE NAMES
```

### G. Baseline suite (unchanged tree)

```
$ uv run python -m unittest discover -s tests -p 'test_attractiveness_layout.py'
Ran 27 tests in 0.120s
OK
```

No tracked file was modified; nothing was staged or committed; `ledger/` was not touched;
no network call was made; the full suite was not run.
