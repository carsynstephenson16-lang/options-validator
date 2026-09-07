# Brief 39 — round-6 bounded adversarial review (rev 7 lane-as-of correction)

**Date:** 2026-09-07
**Reviewer:** Opus, round 6, BOUNDED (verify the rev 6 → rev 7 correction and nothing else)
**Brief under review:** `docs/superpowers/plans/2026-09-06-39-attractiveness-board-redesign-codex-brief.md` rev 7 @ `f8bf086`
**Code under constraint:** `origin/main` @ `160fc02` (main has since moved to `293bb6d`; `160fc02` = PR #158 touched only `tools/daily_ritual.sh` + `tests/test_daily_ritual_provenance.py`, `293bb6d` is a ritual data rescue — neither touches any file this brief cites, verified)
**Trigger:** `reports/2026-09-07-brief-39-codex-stop-report.md` — Codex stopped before Task 1 because rev 6 passed the board's date to every lane adapter.

## Verdict

**PASS WITH FIXES.** The correction is sound in design and it works: per-lane dates are derived, mismatches are stamped and named, 19 module tests pass, ruff and pyright are clean. But rev 7 is **not dispatchable as written** — it ships one supplied assertion that is false against its own supplied module (Codex would hit a red on the contract it is told to trust) and one duplicated statement in the new module that no gate catches. Both fixes are exact, two lines total, and are verified green below. Three MAJOR accuracy defects and four MINOR items follow.

Counts: 1 BLOCKER, 3 MAJOR, 4 MINOR, 1 out-of-scope observation.

## Method — exactly what I re-applied and ran

Read-only on tracked files. No commits, no ledger, no network, no full suite. `.tmp/worktrees/brief39` (Codex's parked worktree) untouched.

Scratch: reused round 4's overlay `.tmp/brief39-review/r4/repo` (symlink overlay onto the main checkout with real copies of `options_researcher/`, `tests/`, `config.py`, `pyrightconfig.json`). Verified before touching it that its `options_researcher/board_lanes.py` is **byte-identical** to rev 6's Task 3 block (`git show b69a79f:` → block extracted programmatically → `diff` empty) and that its `tests/test_board_lanes.py` = round-4 header (27 lines) + rev 6's Task 3 block + `__main__` guard.

Fenced blocks were extracted programmatically from `git show <rev>:<brief>` (`.tmp/brief39-review/r6/extract.py`), never retyped: 37 blocks each for rev 6 and rev 7.

Re-applied into the overlay, in this order:

1. `options_researcher/board_lanes.py` ← rev 7 block `b08` **verbatim** (312 lines; `diff` against the extracted block empty).
2. `tests/test_board_lanes.py` ← round-4 header (unchanged) + rev 7 block `b07` **verbatim** + `__main__` guard (body lines 28..228 `diff` against `b07` empty).
3. `options_researcher/attractiveness_dashboard.py` — the four Task 5/6 deltas, each applied by exact single-occurrence string replacement: the `header(col)` renderer (brief `:1603-1613`), `_qm_as_of` inserted immediately before `_table_footnotes_html` (brief `:1670-1687`), the `.asof-mismatch` CSS line after the `.th-sub` rule (brief `:2037`), and `qm_as_of=_qm_as_of(qm_context),` at the Task 6 call site (brief `:1948`).
4. `tests/test_attractiveness_dashboard.py` — the render-test fixture change (T-bill card `"asof": "2026-09-02"`, `qm_as_of="2026-09-03"`) and the four new assertions (brief `:1390-1395`); plus rev 6's `schwab_chain_view` import-comment hunk, which round 4's overlay predated.

Ran: the rev-6 red reproduction driver (`.tmp/brief39-review/r6/red_rev6.py`, same synthetic inputs against both modules); `unittest discover -p test_board_lanes.py`; `unittest tests.test_attractiveness_dashboard.LaneBoardRenderTests`; the whole `tests/test_attractiveness_dashboard.py` file twice (with and without the rev-7 Task 5/6 patches) to isolate regressions; `uv run ruff check` on all four files from the repo root; `uv run pyright` inside the overlay. For pyright I temporarily added `venvPath`/`venv` to the overlay's (scratch, non-symlinked) `pyrightconfig.json` because pyright cannot resolve site-packages from the overlay cwd; the file has since been restored to round 4's copy. Every other pyright setting is the repo's, including round 4's `"options_researcher/board_lanes.py"` include line.

Reality checks were read from the real ops build at `~/options-validator-ops/.tmp/dashboard/` (`attractiveness.html` and `picks_snapshot.json`, written 2026-09-07 14:21; `experiments.html` from the 2026-08-26 build).

## Codex red reproduced (rev 6 module, unmodified)

Inputs: context rows `context_max_asof="2026-09-03"`, composite cards `max_asof=asof="2026-09-03"`, all four experiment lanes' cards `asof="2026-09-03"`, `board_as_of="2026-09-04"`.

| lane | input evidence date | board session | column `as_of` | state | `as_of_mismatch` |
|---|---|---|---|---|---|
| baseline | (board cards) | 2026-09-04 | 2026-09-04 | READY | attribute absent |
| context | 2026-09-03 | 2026-09-04 | **2026-09-04** | READY | attribute absent |
| composite | 2026-09-03 | 2026-09-04 | **2026-09-04** | READY | attribute absent |
| qm | 2026-09-03 | 2026-09-04 | **2026-09-04** | READY | attribute absent |
| tbill | 2026-09-03 | 2026-09-04 | **2026-09-04** | READY | attribute absent |
| spread | 2026-09-03 | 2026-09-04 | **2026-09-04** | READY | attribute absent |
| tail | 2026-09-03 | 2026-09-04 | **2026-09-04** | READY | attribute absent |
| beta | 2026-09-03 | 2026-09-04 | **2026-09-04** | READY | attribute absent |

`board.notes` was empty. Codex's report is accurate in substance and in its three-row table.

## rev 7 green (same driver, same inputs, rev 7 module)

| lane | input evidence date | board session | column `as_of` | state | `as_of_mismatch` |
|---|---|---|---|---|---|
| baseline | (board cards) | 2026-09-04 | 2026-09-04 | READY | False |
| context | 2026-09-03 | 2026-09-04 | **2026-09-03** | READY | **True** |
| composite | 2026-09-03 | 2026-09-04 | **2026-09-03** | READY | **True** |
| qm | (caller-supplied 2026-09-04) | 2026-09-04 | 2026-09-04 | READY | False |
| tbill | 2026-09-03 | 2026-09-04 | **2026-09-03** | READY | **True** |
| spread | 2026-09-03 | 2026-09-04 | **2026-09-03** | READY | **True** |
| tail | 2026-09-03 | 2026-09-04 | **2026-09-03** | READY | **True** |
| beta | 2026-09-03 | 2026-09-04 | **2026-09-03** | READY | **True** |

`board.notes` named all six:
```
Context lane: evidence as of 2026-09-03 ≠ board session 2026-09-04
Composite: evidence as of 2026-09-03 ≠ board session 2026-09-04
T-bill carry: evidence as of 2026-09-03 ≠ board session 2026-09-04
Spread stability: evidence as of 2026-09-03 ≠ board session 2026-09-04
Tail shape: evidence as of 2026-09-03 ≠ board session 2026-09-04
Beta to QQQ: evidence as of 2026-09-03 ≠ board session 2026-09-04
```

The contract failure Codex stopped on is closed.

---

## BLOCKER 1 — rev 7's own render assertion is false against rev 7's own module

Brief `:1395`:
```python
        self.assertEqual(html.count('class="asof-mismatch"'), 1)
```
Executed: `AssertionError: 2 != 1`.

Cause: that fixture passes `composite_cards=[]` — an **empty list, not `None`** — so `lane_from_composite` skips its `cards is None` guard, `_lane_dates([], "max_asof", "asof")` returns `(None, None)`, the column is `READY` with `as_of=None`, and `stamp()` marks it. Two spans are emitted:

```
Composite      | ranking · <span class="asof-mismatch" …>as of unknown ≠ board</span> · READY
T-bill carry   | describing · <span class="asof-mismatch" …>as of 2026-09-02 ≠ board</span> · READY
```

This matters because Task 3 Step 4 tells Codex "the TESTS are the contract (spec §3, §5); if the implementation disagrees, fix the code." A wrong supplied assertion in a brief whose whole purpose is to correct the module points Codex at the corrected module.

**Fix (verified green — `LaneBoardRenderTests` 9 tests OK):** replace brief `:1395` with
```python
        self.assertIn("as of unknown ≠ board", html)          # composite_cards=[] -> READY, undated
        self.assertEqual(html.count('class="asof-mismatch"'), 2)
```

## MAJOR 2 — the Task 3 module ships a duplicated `return`, and no gate catches it

Brief `:1043-1044`:
```python
    return LaneBoard(columns=columns, rows=rows, notes=notes)
    return LaneBoard(columns=columns, rows=rows, notes=notes)
```
Codex copies this block verbatim. Measured: `uv run ruff check` → `All checks passed!` (the repo selects `E4, E7, E9, F, I`; no rule covers unreachable code) and `uv run pyright` → 0 errors, 0 warnings. Dead code lands in a brand-new module with both gates green.

**Fix:** delete brief `:1044`.

## MAJOR 3 — the baseline lane still substitutes the board's date, on a premise the code does not support

Global Constraints `:174`: "baseline = the board's chain session (**its cards ARE that session**)". That is the one lane rev 7 still hands the board's date, and the justification is not a repo fact.

`_admissible_pick_pool` (`options_researcher/attractiveness_dashboard.py:316-348`) filters on `display_only`, `"skipped" in card`, liquidity `RED`, and snapshot rank-eligibility — **it never looks at the section's `as_of` or its STALE status.** Staleness is a display label only (`_panel_status`, `:817`: `section.get("features_stale") is True or section.get("symbol") in stale_symbols`), while `data_as_of` is `max(as_of)` over the **fresh** sections alone (`:987`, `:1005`). So a stale section dated well before the board session is admissible and can supply a baseline pick, whose column would print the board's date unmarked — the same substitution Codex stopped on, retained for one lane.

Measured on the 2026-09-07 ops build: baseline = `AMZN, NVDA, SMCI, PLTR, CRWV`, all fresh; the stale names are `ET, USAR` ("STALE BOARD for ET, USAR — option quotes are 30 trading sessions old"). The claim holds today by outcome, not by construction, and nothing pins it.

**Fix (documentation only, no code):** replace the parenthetical at `:174` with the true statement and its limit — e.g. "baseline = the board's own shortlist, so its column date is the board session **by definition**; per-name staleness inside the shortlist is disclosed by the STALE panel status and the status strip (`:817`, 'STALE BOARD for …'), not by this column — `_admissible_pick_pool` (`:316-348`) does not exclude stale sections."

## MAJOR 4 — `_qm_as_of`'s per-symbol fallback is unreachable and its citation is false

Global Constraints `:177-179` and the shipped `_qm_as_of` docstring both say "each per-symbol item records that `as_of`, `qm_dashboard.py:110`".

Measured: `qm_dashboard.py` writes `"as_of"` at exactly three places — `:110` (`_blocked`), `:364` (`build_qm_context`) and `:592` (movement context) — **all three top-level**. No per-symbol item carries it: `_live_signal_context`'s returns (`:158`, `:161`, `:166`, `:175`, `:189`), `_not_in_frozen_study` (`:143-147`), the `NO_DATA` / `UNEXPECTED_ERROR` shapes (`:328`, `:334`), and `enrich_qm_context_with_candidates` (`attractiveness_dashboard.py:539-573`, which adds only `option_candidates`) all lack `as_of`. `:110` is the top-level key of the *blocked* context, not a per-symbol one.

Runtime behaviour is still correct — the real context always carries a top-level `as_of`, so the first branch always fires — but the brief states a wrong Repo-verified fact, and the fallback branch has no producer and no test.

**Fix:** cite `qm_dashboard.py:364` (current context) and `:110` (blocked context) as the **top-level** key, and either label the per-symbol scan a defensive fallback with no known producer, or delete it.

## MAJOR 5 — on a real build the mark fires on almost every column, and today's page does not mark at all

Measured from the ops build (`~/options-validator-ops/.tmp/dashboard/`, 2026-09-07 14:21):

| source | date it reports | vs board `data_as_of` = 2026-09-03 |
|---|---|---|
| chain / board session | 2026-09-03 ("2 session old · WARN") | — |
| context lane (all five cards) | `context max as-of 2026-09-04` | **one session AHEAD** |
| composite chip | "max session 2026-09-04; as of 2026-09-04" | **one session AHEAD** |
| QM | "QM daily-bar context as of 2026-09-03" | equal today |
| four experiment lanes (2026-08-26 build) | 2026-08-21 / 2026-08-25 / 2026-07-27 / 2026-07-23 | far behind, and four **different** dates |

Under rev 7's rule that is context + composite + four experiments = **6 of 8 columns** rendered in `var(--watch)` bold `≠ board` on a normal day, with the differences running in **both** directions.

Two consequences. (a) The mark becomes the default state and stops discriminating. (b) It contradicts two places where this repo has already ruled a date difference is not staleness: `experiments_dashboard`'s own page sentence — "each lane keeps its own data source and max as-of stamp" — and `attractiveness_dashboard.py:381-387`, "exact-date equality would blank the panel every capture day for a reason that is not staleness". Spec §5's "as the page does today" describes *disclosure*: today's context cards print `context max as-of X · board as-of Y` side by side with no caution styling, and today's experiments page prints each lane's stamp plainly.

The correction itself is right and must stay. What is missing is the brief saying so.

**Fix (no rule change):** (i) add one sentence to the Global Constraints "Lane as-of" bullet stating that on a real build most non-baseline columns will carry the mark, that the difference is routinely in the *fresher* direction, and that the mark is disclosure, not a staleness verdict (quoting `:381-387`); (ii) add to Task 8 Step 4's manual proof one reported number, `grep -c 'class="asof-mismatch"' .tmp/dashboard/attractiveness.html`, so the count lands in the PR body as evidence rather than a surprise.

## MINOR 6 — the header's undated text changed `?` → `unknown`, unmentioned

rev 6 rendered `as of ?`; rev 7 renders `as of unknown` for every column with `as_of is None`, including non-READY ones. Measured on the render fixture: `Context lane | ranking · as of unknown · FAILED:ValueError` (no mark — correct), and the three UNAVAILABLE experiment columns likewise. No repo test asserts `as of ?` (grepped `tests/`: none), so nothing breaks and the new word is better. The brief never calls the change out. **Fix:** one clause in Task 5's step text.

## MINOR 7 — registry row, spec ruling sentence and the brief header are stale at rev 7

- `BRIEF-NUMBER-REGISTRY.md` row 39's status opens "**READY FOR HAND-OFF (rev 6, 2026-09-07)**" and then says round-6 verification is pending — self-contradictory as a status field.
- The spec's ruling paragraph ends "Brief 39 **rev 6** is written for exactly these two outcomes and is therefore dispatchable" — superseded by rev 7.
- The brief's **Date** line ends "**… — dispatchable**" while the **Status** line on the next line says "pending a bounded round-6 verification". The Date line also reads "rev 6 was rev 1–3 FAIL", which is garbled.

**Fix:** set all three to rev 7 / "round-6 verification pending"; after this review lands, to whatever the disposition is.

## MINOR 8 — provenance anchor two commits stale

Brief header: "file:line constraints are Repo-verified against origin/main @`f83428d`". `origin/main` is `293bb6d` (`f83428d` → `160fc02` → `293bb6d`). Verified: `160fc02` touched only `tools/daily_ritual.sh` and `tests/test_daily_ritual_provenance.py`; `293bb6d` is a ritual data rescue. Neither moves any constraint this brief cites. **Fix:** re-anchor to `160fc02` with that one-line justification.

## MINOR 9 — the lint escape hatch names a rule that cannot fire

Brief `:2453-2455`: "If `ruff check .` reports `I001` (or `E501`, line length 100) on a line this brief supplies…". `pyproject.toml` `[tool.ruff.lint] select = ["E4", "E7", "E9", "F", "I"]` — `E501` lives in `E5` and is not selected. Harmless, but it is a false repo fact in a section labelled Repo-verified. (The `I001` half is real and was earned: rev 6's own fix removed the trailing `# ruff isort order (round 3)` comment from the `schwab_chain_view` import, taking that line from 114 chars — where ruff `I001` demanded a wrap, reproduced — to 84, where it passes.)

## Out-of-scope observation (do NOT fix in this bounded correction)

`lane_from_composite([])` and `lane_from_qm([])` both return state `READY` with zero members. An empty composite board, and a **fully blocked QM context** — where `select_qm_top_picks` returns `[]` (`attractiveness_dashboard.py:499-503`, `_qm_context_block_reason` non-None) while the call site still passes a Mapping, so `qm_picks == []` rather than `None` — both render as READY, empty columns. rev 7 partially exposes the first (undated → marked); the QM case stays unmarked because the caller still supplies a valid `qm_as_of` from the blocked context's top-level `as_of`. This predates rev 7 and is outside the bounded scope. A later round should decide whether a READY lane with zero members is honest.

---

## Spec-conformance checks that PASSED

- **§5 rule, context lane, undated rows.** `_lane_dates(rows, "context_max_asof")` ignoring undated rows is safe here: `context_max_asof` is `None` only when the symbol has no usable composite (`context_lane.py:116-118`), and in exactly that case `_context_assessment` returns `BLOCKED` (`:63-70`). An ALIGNED row therefore always carries a date, so "latest over the rows that have one" can never silently drop a counted row's date.
- **§5 rule, composite/experiments key order.** `max_asof` is the correct and the *fail-visible* key: `confluence_card`'s docstring (`composite_signals.py:577-580`) states `max_asof` is "the latest session any input actually reflects (**bounded above by `asof`**)", so preferring it can only report an older, more conservative date — never one later than the requested session. `_lane_dates(..., "max_asof", "asof")` reproduces `experiments_dashboard.py:71-78` exactly (rev 7 returns `None` where the repo returns `"unavailable"`, and then marks — stricter, and correct per §5).
- **All four board experiment lanes emit both keys:** `exp_beta_qqq.py:47-48`, `exp_spread_stability.py:50-51`, `exp_tail_shape.py:60-61`, `exp_tbill_carry.py:59-60`.
- **Citations verified exact:** `attractiveness_dashboard.py:5957` (`qm_context = load_qm_context(data.get("data_as_of") or "")`), `composite_signals.py:619-622`, `context_lane.py:116-118`, `experiments_dashboard.py:74`, `tests/test_attractiveness_dashboard.py:2801` (def) / `:2859` (call site). The only bad citation is MAJOR 4's.
- **Task order.** `_qm_as_of` is supplied inside Task 5's block (brief `:1670`), before Task 6's call site (brief `:1948`). Correct.
- **Signature audit across the whole brief.** Every `lane_from_*` and `build_lane_board` call matches rev 7's signatures. No `as_of=board_as_of` or `as_of=as_of` survives anywhere. Task 7's parity call (brief `:2302-2305`) omits `qm_as_of`, which is legal (defaults `None`) and inert there — it only feeds `_event_line_html`, which renders no headers. Task 8's tests go through the real `render()` / `_render_result()` and therefore exercise the new kwarg; pyright is clean on that path.
- **`_esc` does not alter `≠`.** Measured: `_esc("≠ board") == "≠ board"`.
- **`dataclasses.replace` on the frozen dataclass with a defaulted trailing field** type-checks and runs.
- **No regression.** `tests/test_attractiveness_dashboard.py` in the overlay: **37** failures / 7 errors with rev 7's Task 5/6 patches reverted, **36** failures / 7 errors with them applied — the single delta is the render test. The 36/7 are inherited overlay state (round 4 applied Tasks 1–6 but not Tasks 7–8's re-pinning of the three existing test files), not rev-7 regressions.
- **Delta hygiene.** Every one of the 22 rev-6 → rev-7 brief hunks serves the correction (header/status record, D13-option-C test-count wording, the Lane-as-of bullet, the interface sketch, the fixture `qm_as_of`, the three new tests, the `replace` import, the dataclass field, `_lane_dates`/`_mixed_note`, the five adapters, `build_lane_board`'s `stamp()` and notes, the render fixture and assertions, the header renderer, `_qm_as_of`, the Task 6 kwarg, the CSS, the acceptance criteria). Nothing in the brief still says a column carries the board's date. The `:893` / `:2801` / `I001` / `E501` / D13–I1 ruling hunks visible in `acb8946..f8bf086` belong to rev 6 (`b69a79f`), not rev 7.
- **The stop-report receipt** `reports/2026-09-07-brief-39-codex-stop-report.md` exists and its three-row table is reproducible exactly (see above). One inaccuracy in the orchestrator's assessment paragraph: "closes-based lanes lag the 15:45 chain capture" is backwards on the current build — the chain is at 2026-09-03 and the closes-based lanes at 2026-09-04. The defect is real either way; the parenthetical is not.

## What I executed and raw results

```
$ .venv/bin/python .tmp/brief39-review/r6/red_rev6.py     # rev 6 module (untouched r4 overlay)
module under test: rev6 (no qm_as_of kwarg)
… all 8 columns as_of = 2026-09-04 (board), board.notes empty        → Codex's red reproduced

$ .venv/bin/python .tmp/brief39-review/r6/red_rev6.py     # after installing rev 7 b08 verbatim
module under test: rev7 (accepts qm_as_of)
… context/composite/tbill/spread/tail/beta as_of = 2026-09-03, mismatch True; 6 board notes

$ .venv/bin/python -m unittest discover -s tests -p 'test_board_lanes.py' -v
Ran 19 tests in 0.004s
OK                                                   # matches the brief's "PASS (19 tests)"

$ uv run ruff check <board_lanes.py> <test_board_lanes.py> <attractiveness_dashboard.py> <test_attractiveness_dashboard.py>
All checks passed!

$ .venv/bin/python -m pyright            # overlay, repo settings + board_lanes.py include
errors 0 warnings 0

$ .venv/bin/python -m unittest tests.test_attractiveness_dashboard.LaneBoardRenderTests
# with the brief's own assertion (count == 1):
FAIL: test_agreement_table_prints_every_column_with_state_and_asof
AssertionError: 2 != 1
# with BLOCKER 1's fix applied:
Ran 9 tests in 0.058s
OK

$ .venv/bin/python -m unittest discover -s tests -p 'test_attractiveness_dashboard.py'
Ran 217 tests — rev 7 patches reverted: FAILED (failures=37, errors=7)
Ran 217 tests — rev 7 patches applied:  FAILED (failures=36, errors=7)   # delta = the render test only
```

Rendered headers on the rev-7 render fixture (T-bill dated 2026-09-02 against a 2026-09-03 board):

```
Rule-based top 5   | ranking · as of 2026-09-03 · READY
Context lane       | ranking · as of unknown · FAILED:ValueError
Composite          | ranking · <span class="asof-mismatch" …>as of unknown ≠ board</span> · READY
QM movement        | ranking · as of 2026-09-03 · READY
T-bill carry       | describing · <span class="asof-mismatch" …>as of 2026-09-02 ≠ board</span> · READY
Spread stability   | describing · as of unknown · UNAVAILABLE:lane not computed
Tail shape         | describing · as of unknown · UNAVAILABLE:lane not computed
Beta to QQQ        | describing · as of unknown · UNAVAILABLE:lane not computed
```

## Re-dispatch condition

Apply BLOCKER 1 and MAJOR 2 (two lines, both verified), then MAJOR 3, 4 and 5 (documentation and one reported number, no code). MINOR 6–9 are editorial and can ride along. With those applied, rev 8 is re-dispatchable and Codex resumes from the parked worktree `.tmp/worktrees/brief39` — no further execution round is needed for the as-of rule itself, which is proven correct above.
