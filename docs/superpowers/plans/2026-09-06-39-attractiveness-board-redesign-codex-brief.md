# Codex brief 39 — Attractiveness board redesign (agreement table) — implementation plan

**Date:** 2026-09-06 (rev 6, 2026-09-07 00:10 ET; rev 1–3 FAIL — `reports/2026-09-06-brief-39-adversarial-review-round{1,2,3}.md`; rev 4 PASS WITH FIXES — `…-round4.md`, 0 blockers, page rebuilt from the brief's code; rev 5 bounded verification PASS WITH FIXES — `…-round5.md`, 2 inherited majors + 3 minors, all applied here; owner decisions D10–D12 recorded in the spec; **D13 and interpretation I1 PENDING owner ruling — do not dispatch before they are recorded**)
**Author:** Claude (orchestrating session; brainstorming + spec with the owner 2026-09-06)
**Executor:** Codex (Sol, high reasoning — as briefs 07/37/38; owner may substitute at dispatch)
**Status:** READY FOR HAND-OFF — conditional on the owner recording D13 (option A assumed throughout) and not vetoing I1 in the spec's pending-rulings section; five review rounds, last two with zero blockers
**Provenance:** file:line constraints are Repo-verified against origin/main
@f83428d unless a sentence carries its own label. Counts marked "measured"
were taken from the 2026-09-04 ops build by the round-1 reviewer. Sentences
labelled **Inference** are the author's reading of the code, not a file fact.
Round 2 executed the Task 3 module and its tests verbatim (green; ruff and
pyright clean). Round 3 applied Tasks 1–6 verbatim in scratch and RENDERED the
flag-on page; every rev-4 change below is a fix to something that build
surfaced. Task 3 gains one rule (blocked names are rows) and one test.
**Spec (owner-approved 2026-09-06, amended D10–D12 the same day — read it first):**
`docs/superpowers/specs/2026-09-06-attractiveness-board-redesign-design.md`
with the approved first-screen mockup
`docs/superpowers/specs/assets/2026-09-06-board-redesign-option-a-v2.html`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Tasks carry both a plan number and a work-package label (WP-A … WP-H) so review findings can cite them.

**Goal:** Replace the attractiveness board's first screen with one agreement
table (names × lanes, favourable-only count), render per-name detail panels
only for the names on that table, and move everything descriptive into the
existing drawer — so the VISIBLE page (fold-outs closed) drops from ~19
screens to under 5 without changing any ranking, grade, snapshot, or authority.

**Architecture:** A new pure module `options_researcher/board_lanes.py` turns
the already-assembled board data (baseline picks, context selection, composite
cards, QM picks, experiment lanes, blocked records) into a `LaneBoard` value.
`options_researcher/attractiveness_dashboard.py` gains a status strip, position
tiles, the agreement table, one event line and "details for these names only",
all gated by `config.BOARD_LANES_ENABLED`; when the flag is `False` the page is
byte-identical to today (snapshot-tested). Experiment lanes are computed in the
real gather step only (never for injected test fixtures) and are injectable.

**Tech Stack:** Python 3.12, `unittest` (offline, no network), ruff, pyright,
zero-JavaScript static HTML (native `<details>`, inline SVG only).

## Why this exists (plain language)

The board is honest but ~19 screens long (782,263 bytes, 30 headings, 362
fold-outs on 2026-09-04 — measured). The owner wants it "less long and easier
to read", with the top picks always on top, a visible mark when several lanes
share a pick, and only each lane's five best (spec §1, D1–D12). This brief
implements that spec exactly. It closes the visual half of brief 37's DR-8b
(event-chip repetition) by renegotiating the chip-parity contract (spec §7,
D11).

Facts the design rests on (measured on the 2026-09-04 build): the 18 per-name
panels are 698,705 bytes (89% of the page), hold 333 of the 362 `<details>`
and 18 of the 30 `<h2>`; the 14 smallest panels sum to 497,016 bytes. So the
FILE stays large (the panels are kept byte-identical, D10) while the VISIBLE
page becomes short — which is what the owner asked for.

## Scope

**IN:** `config.py` (three display constants, provenance-labelled),
`pyrightconfig.json` (one include line), `options_researcher/board_lanes.py`
(new), `options_researcher/attractiveness_dashboard.py` (gather/assemble
injection, new section builders, symbol-panel extraction, `_render_result`
wiring, one docstring), and tests: new `tests/test_board_lanes.py`,
`tests/fixtures/attractiveness_legacy_layout.html` (new snapshot),
`tests/test_attractiveness_layout.py`, `tests/test_attractiveness_dashboard.py`,
`tests/test_event_awareness.py`, `tests/test_attractiveness_v3.py` (one legacy
wrap), and — ONLY under owner ruling D13 option A —
`tests/test_experiments_baseline.py` (the AST isolation guard, Task 4).

**OUT (hard):**
- No change to `options_researcher/display_rank.py`, `options_researcher/attractiveness.py`,
  `options_researcher/context_lane.py`, `options_researcher/composite_signals.py`,
  `options_researcher/qm_signals.py`, `options_researcher/qm_dashboard.py`,
  `options_researcher/exp_*.py`, `options_researcher/experiments_dashboard.py`,
  `options_researcher/pick_tracker.py`, `options_researcher/event_calendar.py`,
  or any `grades` input of any card. Ranking, grades, the picks snapshot
  (`_selection_snapshot`, `attractiveness_dashboard.py:5384`), the source-row
  hashes (`_render_source_row_hashes`, `:5364`), and the publish-path digest
  (`pick_tracker.py:52`, bound at `attractiveness_dashboard.py:5877`) are
  untouched (spec §6). All of these are computed OUTSIDE the flag branch
  (`:5524-5533`, `:5751-5761`; reviewer-verified in both rounds).
- No edit to any member of `FEASIBILITY_SOURCE_PATHS`
  (`options_researcher/h7_schwab_window_registration.py:143-194`; `config.py`,
  `attractiveness_dashboard.py` and the new module are all outside it —
  reviewer-verified).
- No JavaScript (`tests/test_attractiveness_layout.py:497`), no external
  assets, no network or provider call, no ledger write, no registration, no
  authority flip, no paper-book mutation, no plist/launchd change, no change
  to Mission Control (`options_researcher/dashboard.py`), no change to the
  standalone experiments page or the `EXP_*` flags.
- Authority for computing the four experiment lanes on every real build is
  spec §4 (quoted so no later auditor has to hunt for it): "The four
  experiments' own flags stay disabled for the standalone experiments page;
  the board's use of their lane builders is an owner-directed display decision
  (D5, 2026-09-06) and does not promote any experiment beyond experimental
  status (2026-08-09 authorization: promotion needs a separate owner decision —
  none is implied here)." The 2026-08-09 "disabled by default" clause binds the
  experiments' own `EXP_*` flags, which this brief does not touch. (Repo fact:
  the four dict lanes in `build_experiment_lanes` are not flag-gated —
  `experiments_dashboard.py:262-282`; only `exp_short` is.)
- No new numeric constant with owner provenance: the cap reuses
  `config.PICK_TOP_N` (`config.py:650`); the mark-age colour reuses
  `config.CHAIN_STALE_BLOCK_SESSIONS` (`config.py:690`).
- DR-5 / DR-5b stay held (brief 37 "Held" section); nothing here computes
  rv21 or changes a badge.
- Do not trim, reorder or restyle the content INSIDE a per-name panel (D10):
  `_symbol_panel_html` is a byte-identical extraction.

## Owner ruling required before dispatch — D13 (and the I1 veto window)

Round 3 found a tracked mechanical guardrail the spec and this brief did not
know about: `tests/test_experiments_baseline.py:92-93`
`test_production_dashboard_has_no_experiment_imports` parses
`attractiveness_dashboard.py` with `ast` and asserts ZERO imports or calls of
`options_researcher.experiments_dashboard*` / `options_researcher.exp_*`
(`_experiment_boundary_violations`, `:40-88`; module docstring "Program-level
isolation tests for display-only experiment wiring"). It is the mechanical form
of the 2026-08-09 clause (`.cursorrules`: experiments isolated from "… the
default baseline ranking"). Spec D5/§4 requires the board to call the four lane
builders, which this guard forbids. It is a source-text test: no flag can
satisfy it. The owner types one letter:

- **A (recommended):** keep the guard's PURPOSE and make it precise — the only
  permitted experiment import/call site in the production dashboard is
  `_default_experiment_lanes` (display-only, gather-side, fail-visible), and a
  new assertion proves no experiment reference exists anywhere else in the file
  (the ranking path stays provably clean; the Task 8 parity test proves the
  picks snapshot and source-row hashes are identical flag on/off). Task 4 below
  is written for A.
- **B:** compute the lanes out of process — a new `experiments_dashboard` CLI
  mode writes `.tmp/dashboard/experiment_lanes.json` inside the ritual before
  the board build, and the dashboard only READS that file (guard untouched).
  Costs: an experiments-module edit and a `tools/daily_ritual.sh` step (both
  out of this brief's scope today), and every non-ritual build shows all four
  columns UNAVAILABLE because the artifact is absent. If B, Task 4 is rewritten
  and the brief returns to review.
- **C:** drop the four experiment columns (reverses D5). If C, Tasks 1, 3, 4
  and 6 are rewritten (both tuples, the `_EXPERIMENTS` map and four of the 16
  module tests, the whole gather step, the caution group) and the brief returns
  to review.

Until the owner records D13 in the spec's pending-rulings section, Codex must
not be dispatched. I1 (pinned panels not force-open under the flag) is an
interpretation the owner may veto in the same reply; the default is to proceed.

## Global Constraints

- All twelve sentences in `AuthorityWordingSurvivesLayoutTests._SENTENCES`
  (`tests/test_attractiveness_layout.py:434-454`; twelve entries, several
  wrapped over two source lines) stay on the flag-on page verbatim, plus the
  footer sentence "This page and the mission-control dashboard date
  INDEPENDENTLY" (`attractiveness_dashboard.py:5740-5745`). Nine live in
  sections that still render (drawer or panels). Three live only in
  sections the redesign removes, so the agreement table carries them (spec
  §2.7 / §6.4 say "verbatim"; this keeps them verbatim without a spec
  amendment): (1) the hero sentence "This is a fit ranking, not a prediction"
  (`:4215`) → the table's `header-sub` paragraph; (2) the pinned-strip sentence
  "owner-pinned visibility — not ranked; these cards do not compete with or
  reorder the Top-5 shortlist." (`:4707-4708`) → a footnote under the table;
  (3) `_CONTEXT_LANE_DISCLAIMER` (`:4442-4447`) → a footnote under the table
  prefixed "Context lane column:". Its phrase "the rule-based list above" now
  refers to the baseline column; the wording is kept because verbatim is the
  contract — dropping or rewording any of the three would be a spec amendment
  and an owner ruling, not this brief. `test_disclaimers_are_present_verbatim`
  (`:456`) renders with the DEFAULT flag (True after Task 1) and must stay
  green untouched; Task 6 adds a flag-off twin. The two footnotes are emitted by
  one helper (`_table_footnotes_html`) that BOTH the agreement table and the
  `LANE BOARD FAILED` fallback print, so the invariant holds on the failure
  path too (round 3 measured the fallback dropping the pinned sentence).
- "Visible" (D10) means what a reader sees without clicking: everything
  outside a CLOSED `<details>`. A force-open panel (STALE/BLOCKED/SKIPPED) IS
  visible and is counted. D10's targets are therefore measured on a FRESH
  fixture where nothing is force-open (Task 8), and the Friday-data proof
  REPORTS how many panels are force-open and why (fail-visibility is not a
  defect to hide). Spec §1/D10 says "with fold-outs closed"; this is the same
  measure taken where the fold-outs actually are closed.
- **I1 (interpretation, owner may veto — recorded in the spec's pending
  section):** under the flag, owner-pinned names satisfy the 2026-07-16
  "always shown" ruling as table rows; their detail panels open only for
  fail-visible statuses, not because they are pinned. Implemented by passing
  `pinned_symbols=set()` to `_pick_details_html` in the flag branch; the
  extraction and the flag-off page are untouched. I1 REVERSES a recorded
  behaviour: the code comment at `attractiveness_dashboard.py:5598-5600`
  ("… the owner-pinned names stay open by standing directive") and the test
  `tests/test_attractiveness_dashboard.py:874/:894` that enforces it — both
  are quoted in the spec's pending-ruling entry so the owner rules on the
  evidence. **If the owner vetoes I1:** pass `pinned_symbols` through instead
  of `set()`, leave `:874` at its current text, and change the two zero-open
  assertions: Task 8's acceptance to **2** (measured on the fresh 8-symbol
  fixture: 2 open panels, visible 4 `<h2>` / 6 `<summary>`) and Task 7's
  `:277` rewrite to **1** (measured on that test's own 3-symbol fixture — VST
  is the only pinned name with a section; AMZN has none). Under the veto the
  acceptance test's `<h2> <= 4` leg passes at exactly 4 — no margin; leave the
  limit at 4 rather than re-tightening.
- Names that are on no lane, not pinned and not blocked are not named on the
  flag-on page (spec §2.5/D4 — the open-slot notice explains the shortlist
  gap); STALE names in that position are still NAMED in the status strip;
  DATA_BLOCKED names are ALWAYS rows (their reason in the pick cell, spec §3)
  and stay in the `_blocked_html` banner. Tests asserting panel CONTENT for a
  symbol that is no longer a row are re-pointed, not deleted (Task 7 rule (d)).
- The six drawer sections keep their order (`test_drawer_is_closed_and_holds_the_six_diagnostic_sections`,
  `tests/test_attractiveness_layout.py:405`; `DiagnosticsDrawerTests._DRAWER_SECTIONS`
  at `:374-382`); relocated content is APPENDED after them. The drawer element
  is `<details class="panel diagnostics-drawer" id="diagnostics">` — anchor
  tests on `id="diagnostics"`, never on `class="drawer"` (does not exist).
- `config.BOARD_LANES_ENABLED = False` must reproduce today's HTML
  byte-for-byte on the layout fixture (rollback path, spec §4), proven by a
  snapshot captured BEFORE any change to `_render_result` (Task 2).
- Owner-pinned names (`pinned_picks(data)` → `[{"symbol", "pick"}]`,
  `:576-594`; `config.PICK_PINNED_SYMBOLS`) are always rows.
- Fail-visible: every lane keeps its column with its state; a non-READY lane
  leaves the agreement denominator (spec §5).
- Every `assemble(...)` call that injects `symbol_sections` must stay
  hermetic (no disk, no cache): the experiment-lane default runs only on the
  real gather path (Task 4).
- Commit after every green task; never squash the task history before the
  PR; the PR starts as a GitHub draft.

## File Structure

| File | Responsibility |
|---|---|
| `config.py` | `BOARD_LANES_ENABLED`, `BOARD_FAVOURABLE_LANES`, `BOARD_CAUTION_LANES` (display-only, LLM-proposed 2026-09-06 labels) |
| `pyrightconfig.json` | add `"options_researcher/board_lanes.py"` to `include` so the repo type gate covers the new module |
| `options_researcher/board_lanes.py` (new, pure) | dataclasses `LaneMember`, `LaneColumn`, `BoardRow`, `LaneBoard`; `build_lane_board(...)`; adapters `lane_from_baseline`, `lane_from_context`, `lane_from_composite`, `lane_from_qm`, `lane_from_experiment`; no I/O |
| `options_researcher/attractiveness_dashboard.py` | gather: `_default_experiment_lanes` (real path only) + `assemble(experiment_lanes=…)`; render: `_symbol_panel_html` (extracted), `_status_strip_html`, `_position_tiles_html`, `_agreement_table_html`, `_event_line_html`, `_pick_details_html`, `_open_slots_notice_html`; `_render_result` order behind the flag; `_experiments_shelf_html` docstring amended |
| `tests/fixtures/attractiveness_legacy_layout.html` | pre-change render of the layout fixture (rollback proof) |
| `tests/test_board_lanes.py` (new) | unit tests for the pure module |
| `tests/test_attractiveness_layout.py` | legacy byte-identity (flag off); layout contract re-pinned to spec §2 (flag on) |
| `tests/test_attractiveness_dashboard.py` | render tests for the new builders; existing tests re-pinned per Task 7 |
| `tests/test_event_awareness.py` | fixture lifted to module level; chip contract re-pinned to D11 |

**Data shapes the module consumes (Repo-verified; corrected per review):**

- baseline pick (`select_top_picks(data)`, `attractiveness_dashboard.py:438`;
  built at `:357-364`): `{"symbol", "lane", "strike", "expiry", "dte", "score",
  "card"}` — there is NO top-level `status`; policy status lives at
  `card["top3_snapshot"]["policy"]["status"]`. `card` has `headline`,
  `strike`, `expiry`, `dte`, `cost`, `grades`, `risk: {"max_loss",
  "capital_required", "max_profit", "breakeven"}`, `top3_snapshot.candidate_id`.
- context selection (`_context_lane_selection(data)`, `:4450-4465`):
  `{"state": "READY"|"DISABLED"|"FAILED", "rows": [...], "error": <ExceptionName>|None}`;
  each row (`options_researcher/context_lane.py:112-124`): `{"symbol", "lane",
  "candidate_id", "score", "context_max_asof", "board_as_of", "context_term",
  "context_reason", "aligned_angles", "pick"}`; `context_reason` takes
  `"ALIGNED"`, `"VETOED"`, `"BLOCKED"`, `"DIRECTION_MISMATCH"` (branches at
  `attractiveness_dashboard.py:4497-4500`).
- composite card (`data["composite_signals"]`, `options_researcher/composite_signals.py:619-624`):
  `{"symbol", "asof", "max_asof", "grade", "aligned_count": int, "trend",
  "vol_premium", "regime", "internals"}` (each angle a dict with `state`).
- QM pick (`select_qm_top_picks(data, qm_context, include_csp_watch=True)`,
  `:488-491`): same shape as a baseline pick. At the call site
  `qm_context = enrich_qm_context_with_candidates(data, qm_context)` (`:5534`)
  is typed `Mapping[str, object] | None` (`:540`) while `select_qm_top_picks`
  requires a Mapping (`:489`); the repo's only other caller guards with
  `assert isinstance(qm_context, Mapping)` (`:4281`). Task 6 guards with
  `isinstance` and passes `None` (= lane UNAVAILABLE) otherwise.
- experiment lanes (`experiments_dashboard.build_experiment_lanes(symbols, asof=…)`,
  `experiments_dashboard.py:262-282`): dict with keys `exp_beta`, `exp_tail`,
  `exp_spread`, `exp_tbill` (lists of card dicts) AND `exp_short` (a list of
  `ShortPositioningCard` dataclasses, NOT JSON-serialisable — ignored here;
  only the four dict lanes are stored, Task 4). Every card dict has `symbol`,
  `state`, `experiment_id`, optional `data_blocked`, and the lane metric:
  `beta` (`exp_beta_qqq.py:132`, states `OK`/`UNSTABLE`), `jump_count` +
  `skew` (`exp_tail_shape.py:132-139`, `OK`/`UNSTABLE`), `ratio`
  (`exp_spread_stability.py:169-176`, `OK`/`ELEVATED`), `carry_spread`
  (`exp_tbill_carry.py:131`, `ABOVE_TBILL`/`BELOW_TBILL`); blocked cards carry
  `state == "DATA_BLOCKED"`; a lane whose builder raised is a one-card list
  `{"symbol": "ALL", "state": "ERROR", "reason", "experiment_id", "max_asof"}`
  (`_error_card`, `:250-259`; the key is `max_asof`, not `asof`). Measured 2026-09-04: `exp_beta` is `OK` for all 18 names (the
  beta caution column renders empty) and `exp_tbill` is `ABOVE_TBILL` for all
  18 (the T-bill column is effectively "top 5 by carry").
- blocked record (`_block`, `:1866-1870`): `{"symbol", "reason_code",
  "detail", "last_known_date", "unexpected"}` plus optional `display_only`.
  There is NO `reason` key.
- open positions (`data["open_positions"]`, `load_open_positions` `:1485`):
  `{"rows": [{"book", "identifier", "text"}], "missing_sources", "sources",
  "h6_last_mark"}`.
- closes freshness (`data["underlying_closes_freshness"]`,
  `_underlying_closes_store_freshness` `:1412-1459`): `{"state": "available",
  "as_of"}` or `{"state": "unavailable", "detail"}`. No `max_session` key.
- Schwab lane (`data["schwab_lane"]`): `{"verified_sessions", "failures":
  [{"session", "kind", "reason"}], "receipts_found"}`; `kind == CHAINS_ABSENT`
  is an expected research-checkout state, not a failure (`:1081-1091`).

**Deviations from spec §4's sketch (deliberate, reviewer-flagged; the spec's
sketch was illustrative):** `build_lane_board` takes `context_selection`
(the whole `{"state","rows","error"}` dict, so a FAILED lane can be shown)
instead of `context_rows`; it takes `blocked` so a DATA_BLOCKED name can show
its reason in the pick cell (spec §3); `BoardRow` gains `block_reason`; the
event line is rendered from the rows rather than stored on `LaneBoard`.

---

### Task 1 (WP-A): Display constants with provenance labels

**Files:**
- Modify: `config.py:929` (append after `CONTEXT_LANE_ENABLED: bool = True`, before the "ATTRACTIVENESS EXPERIMENT LANES" block at `:932`)
- Test: `tests/test_board_lanes.py` (new file)

**Interfaces:**
- Produces: `config.BOARD_LANES_ENABLED: bool`,
  `config.BOARD_FAVOURABLE_LANES: tuple[str, ...]`,
  `config.BOARD_CAUTION_LANES: tuple[str, ...]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_board_lanes.py` with ALL imports at the top (Task 3 adds
tests below; the import block is final now — a mid-file import fails ruff E402,
and `import x` lines sort before `from x import y` lines under ruff's isort
(`pyproject.toml:40` selects `I`)):

```python
# tests/test_board_lanes.py
"""Unit tests for the lane-board display constants and the pure lane-board
module (spec docs/superpowers/specs/2026-09-06-attractiveness-board-redesign-design.md).
Nothing here asserts a ranking, a signal, or an authority change."""
import unittest
from pathlib import Path

import config
from options_researcher import board_lanes as bl  # Task 3 creates it; Task 1 tests skip it


class BoardConstantsTests(unittest.TestCase):
    def test_lane_board_constants_exist_and_are_disjoint(self):
        self.assertIsInstance(config.BOARD_LANES_ENABLED, bool)
        fav = config.BOARD_FAVOURABLE_LANES
        cau = config.BOARD_CAUTION_LANES
        self.assertEqual(fav, ("baseline", "context", "composite", "qm", "tbill"))
        self.assertEqual(cau, ("spread", "tail", "beta"))
        self.assertFalse(set(fav) & set(cau))

    def test_constants_carry_display_only_provenance_comment(self):
        source = Path("config.py").read_text(encoding="utf-8")
        preamble = source[: source.index("BOARD_LANES_ENABLED")][-900:]
        self.assertIn("LLM-proposed 2026-09-06", preamble)
        self.assertIn("display-only", preamble.lower())


if __name__ == "__main__":
    unittest.main()
```

For Task 1 only, temporarily comment out the `board_lanes` import line (Task 3
restores it); otherwise the file fails to import.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest discover -s tests -p 'test_board_lanes.py' -v`
Expected: FAIL with `AttributeError: module 'config' has no attribute 'BOARD_LANES_ENABLED'`

- [ ] **Step 3: Add the constants**

Insert after `CONTEXT_LANE_ENABLED: bool = True` (`config.py:929`):

```python
# LANE BOARD — the attractiveness board's first-screen agreement table
# (spec docs/superpowers/specs/2026-09-06-attractiveness-board-redesign-design.md).
# Display-only; LLM-proposed 2026-09-06 under owner decisions D1–D12 of that
# spec (owner-directed in chat, not owner-typed). Nothing here changes
# shortlist ranking, grades, the picks snapshot, registered hypotheses,
# verdicts, FIRE authority, or paper-book state. BOARD_LANES_ENABLED=False
# renders the pre-redesign page byte-for-byte (rollback path). The favourable
# / caution split is spec §3 (D8): only favourable lanes count toward
# "Agree"; cautions are shown, never counted. Changing either tuple is an
# owner decision.
BOARD_LANES_ENABLED: bool = True
BOARD_FAVOURABLE_LANES: tuple[str, ...] = ("baseline", "context", "composite", "qm", "tbill")
BOARD_CAUTION_LANES: tuple[str, ...] = ("spread", "tail", "beta")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest discover -s tests -p 'test_board_lanes.py' -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_board_lanes.py
git commit -m "feat(board): lane-board display constants (LLM-proposed 2026-09-06, display-only)"
```

---

### Task 2 (WP-B): Capture the legacy page snapshot BEFORE any renderer change

**Files:**
- Create: `tests/fixtures/attractiveness_legacy_layout.html`
- Modify: `tests/test_attractiveness_layout.py` (append the snapshot helper + test)
- Test: `tests/test_attractiveness_layout.py`

**Interfaces:**
- Produces: `LEGACY_RENDER_SNAPSHOT()` in the layout test module; the snapshot
  file every later task is compared to. (The `mock` import and the `_board`
  `experiment_lanes` default land in Task 4, when `assemble` learns the kwarg.)

- [ ] **Step 1: Capture the snapshot from the UNMODIFIED renderer**

This must run before Tasks 4–6 touch `assemble`/`_render_result`. `tests/`
has no `__init__.py`; do not add one — use `PYTHONPATH=tests`:

```bash
mkdir -p tests/fixtures
PYTHONPATH=tests uv run python - <<'EOF'
from pathlib import Path
from test_attractiveness_layout import _board
from options_researcher import attractiveness_dashboard as ad
html = ad.render(_board(["NVDA", "AMZN", "MSFT"]))
Path("tests/fixtures/attractiveness_legacy_layout.html").write_text(html, encoding="utf-8")
print(len(html), "bytes")
EOF
```

Run the capture twice into two paths and `cmp` them to prove determinism
(fixed `today`, injected sections, no cache reads).

- [ ] **Step 2: Write the byte-identity test**

Append to `tests/test_attractiveness_layout.py`. Extend the import block at
`:10-19` NOW, in isort order, with `from pathlib import Path` and
`from unittest import mock` — neither is imported today, and adding them later
mid-file fails ruff E402. (`import contextlib` is added in Task 7, when it is
first used; adding it now trips ruff F401 in the meantime, and the repo's
pre-commit config would auto-delete it.)

```python
def LEGACY_RENDER_SNAPSHOT() -> str:
    """The pre-redesign render of the layout fixture, captured before any change
    to _render_result (brief 39 Task 2). The flag-off path must equal it byte
    for byte — that is the rollback guarantee."""
    return Path("tests/fixtures/attractiveness_legacy_layout.html").read_text(encoding="utf-8")


class LegacyByteIdentityTests(unittest.TestCase):
    def test_flag_off_renders_the_legacy_page_byte_for_byte(self):
        data = _board(["NVDA", "AMZN", "MSFT"])
        with mock.patch.object(config, "BOARD_LANES_ENABLED", False):
            legacy = ad.render(data)
        self.assertEqual(legacy, LEGACY_RENDER_SNAPSHOT())
```

- [ ] **Step 3: Run the test**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_layout.py' -k LegacyByteIdentity -v`
Expected: PASS (Task 1 already added the flag, so `mock.patch.object` works;
the renderer is still unmodified).

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/attractiveness_legacy_layout.html tests/test_attractiveness_layout.py
git commit -m "test(board): capture the legacy layout snapshot before the redesign (rollback proof)"
```

---

### Task 3 (WP-C): The pure lane-board module (typed)

**Files:**
- Create: `options_researcher/board_lanes.py`
- Modify: `pyrightconfig.json` (`include`: add `"options_researcher/board_lanes.py"` after the `attractiveness_dashboard.py` entry)
- Test: `tests/test_board_lanes.py`

**Interfaces:**
- Consumes: `config.PICK_TOP_N`, `config.BOARD_FAVOURABLE_LANES`, `config.BOARD_CAUTION_LANES`.
- Produces (used by Tasks 5–6):

```python
@dataclass(frozen=True)
class LaneMember:
    symbol: str
    label: str            # cell text: "#2", "A · 3/4", "✓ 1.90", "! 3.79", "veto", "blocked", "direction mismatch"
    value: float | None
    rank: int | None
    counts: bool = True   # False for context marks that are not ALIGNED

@dataclass(frozen=True)
class LaneColumn:
    key: str; title: str; kind: str; favourable: bool; state: str
    as_of: str | None; members: tuple[LaneMember, ...]; note: str

@dataclass(frozen=True)
class BoardRow:
    symbol: str; pinned: bool
    baseline_pick: Mapping[str, object] | None
    block_reason: str | None
    marks: Mapping[str, LaneMember]
    fav_count: int; fav_ready: int

@dataclass(frozen=True)
class LaneBoard:
    columns: tuple[LaneColumn, ...]; rows: tuple[BoardRow, ...]; notes: tuple[str, ...]

def build_lane_board(*, baseline_picks, context_selection, composite_cards, qm_picks,
                     experiment_lanes, pinned, blocked, cap=config.PICK_TOP_N,
                     board_as_of) -> LaneBoard
```

- [ ] **Step 1: Write the failing tests**

Restore the `from options_researcher import board_lanes as bl` import at the
top of `tests/test_board_lanes.py` (Task 1 commented it out) and append:

```python
def _pick(symbol, lane="long_call"):
    # Real shape (attractiveness_dashboard.py:357-364): no top-level "status".
    return {
        "symbol": symbol, "lane": lane, "strike": 100.0, "expiry": "2026-09-16", "dte": 10, "score": 0,
        "card": {"headline": f"Buy the {symbol} call", "strike": 100.0, "expiry": "2026-09-16",
                 "dte": 10, "cost": 300.0, "grades": {"liquidity": "GREEN"},
                 "risk": {"max_loss": 300.0, "breakeven": 103.0},
                 "top3_snapshot": {"candidate_id": f"{symbol}:{lane}:2026-09-16:100.00",
                                   "policy": {"status": "ELIGIBLE", "reason_codes": []}}},
    }


def _ctx_row(symbol, term=3, reason="ALIGNED", angles=("TREND", "REGIME", "INTERNALS")):
    return {"symbol": symbol, "lane": "long_call", "candidate_id": f"{symbol}:long_call",
            "score": (0,), "context_max_asof": "2026-09-03", "board_as_of": "2026-09-03",
            "context_term": term, "context_reason": reason,
            "aligned_angles": tuple(angles), "pick": _pick(symbol)}


def _comp(symbol, grade="A", aligned=3):
    return {"symbol": symbol, "asof": "2026-09-03", "max_asof": "2026-09-03",
            "grade": grade, "aligned_count": aligned,
            "trend": {"state": "UP"}, "vol_premium": {"state": "RICH"},
            "regime": {"state": "TYPICAL"}, "internals": {"state": "CONFIRM"}}


def _exp(symbol, state, **metric):
    card = {"symbol": symbol, "state": state, "experiment_id": "X", "asof": "2026-09-03"}
    card.update(metric)
    return card


def _board(**over):
    kwargs = dict(
        baseline_picks=[_pick("AMZN"), _pick("NVDA"), _pick("SMCI")],
        context_selection={"state": "READY", "error": None, "rows": [
            _ctx_row("AMZN"), _ctx_row("NVDA"),
            _ctx_row("SMCI", term=0, reason="VETOED", angles=()),
            _ctx_row("CRWV", term=0, reason="BLOCKED", angles=())]},
        composite_cards=[_comp("PLTR"), _comp("NVDA"), _comp("AMZN"), _comp("ET", "C", 2),
                         _comp("VST", "C", 2), _comp("CEG", "C", 2), _comp("NBIS", "C", 2), _comp("AMD", "C", 1)],
        qm_picks=[_pick("AMZN"), _pick("NVDA")],
        experiment_lanes={
            "exp_beta": [_exp("AMZN", "OK", beta=1.1), _exp("CEG", "UNSTABLE", beta=0.4)],
            "exp_tail": [_exp("NVDA", "UNSTABLE", jump_count=1), _exp("CEG", "UNSTABLE", jump_count=1)],
            "exp_spread": [_exp("TEM", "ELEVATED", ratio=3.79), _exp("CEG", "ELEVATED", ratio=2.16)],
            "exp_tbill": [_exp(s, "ABOVE_TBILL", carry_spread=v) for s, v in
                          (("NBIS", 2.89), ("IREN", 2.33), ("CRWV", 1.90), ("CLSK", 1.895),
                           ("USAR", 1.73), ("SMCI", 1.76), ("AMZN", 0.65))],
        },
        pinned=("VST", "AMZN"),
        # Real blocked-record shape (attractiveness_dashboard.py:1866-1870).
        blocked=[{"symbol": "ET", "reason_code": "DATA_BLOCKED", "detail": "chain 29 sessions old",
                  "last_known_date": "2026-07-27", "unexpected": False}],
        cap=5, board_as_of="2026-09-03",
    )
    kwargs.update(over)
    return bl.build_lane_board(**kwargs)


def _col(board, key):
    return next(c for c in board.columns if c.key == key)


def _row(board, symbol):
    return next(r for r in board.rows if r.symbol == symbol)


class LaneBoardTests(unittest.TestCase):
    def test_columns_are_the_eight_lanes_in_favourable_then_caution_order(self):
        board = _board()
        self.assertEqual([c.key for c in board.columns],
                         ["baseline", "context", "composite", "qm", "tbill", "spread", "tail", "beta"])
        self.assertEqual([c.favourable for c in board.columns], [True] * 5 + [False] * 3)

    def test_baseline_order_first_then_favourable_count_then_symbol(self):
        board = _board()
        symbols = [r.symbol for r in board.rows]
        self.assertEqual(symbols[:3], ["AMZN", "NVDA", "SMCI"])
        counts = [_row(board, s).fav_count for s in symbols[3:]]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_agreement_counts_favourable_lanes_only(self):
        board = _board()
        # NVDA: baseline #2, context #2, composite A·3/4, qm #2; not in tbill -> 4/5
        self.assertEqual(_row(board, "NVDA").fav_count, 4)
        self.assertEqual(_row(board, "NVDA").fav_ready, 5)
        # CEG: composite C·2/4 counts; beta/tail/spread are cautions -> 1/5
        self.assertEqual(_row(board, "CEG").fav_count, 1)
        self.assertEqual(set(_row(board, "CEG").marks) & {"beta", "tail", "spread"}, {"beta", "tail", "spread"})

    def test_context_marks_other_than_aligned_are_shown_but_never_counted(self):
        board = _board()
        smci = _row(board, "SMCI")
        self.assertEqual(smci.marks["context"].label, "veto")
        self.assertFalse(smci.marks["context"].counts)
        self.assertEqual(smci.fav_count, 2)          # baseline #3 + tbill 1.76
        crwv = _row(board, "CRWV")
        self.assertEqual(crwv.marks["context"].label, "blocked")
        self.assertFalse(crwv.marks["context"].counts)
        self.assertEqual(crwv.fav_count, 1)          # tbill 1.90 only

    def test_ranking_lanes_are_capped_and_composite_ties_break_by_baseline_then_symbol(self):
        board = _board()
        comp = _col(board, "composite")
        # aligned=3: AMZN, NVDA (baseline rows first), PLTR; aligned=2: no baseline
        # row, so symbol order fills the last two slots (CEG, ET); NBIS/VST drop.
        self.assertEqual([m.symbol for m in comp.members], ["AMZN", "NVDA", "PLTR", "CEG", "ET"])

    def test_describing_lane_overflow_takes_largest_metric_and_says_so(self):
        board = _board()
        tbill = _col(board, "tbill")
        self.assertEqual([m.symbol for m in tbill.members], ["NBIS", "IREN", "CRWV", "CLSK", "SMCI"])
        self.assertIn("LLM-proposed 2026-09-06", tbill.note)
        self.assertEqual(tbill.members[0].label, "✓ 2.89")

    def test_beta_lane_has_no_metric_order_and_lists_by_symbol(self):
        board = _board()
        beta = _col(board, "beta")
        self.assertEqual([m.symbol for m in beta.members], ["CEG"])
        self.assertEqual(beta.members[0].label, "!")

    def test_failed_lane_keeps_its_column_and_leaves_the_denominator(self):
        board = _board(context_selection={"state": "FAILED", "rows": [], "error": "ValueError"})
        ctx = _col(board, "context")
        self.assertEqual(ctx.state, "FAILED:ValueError")
        self.assertEqual(ctx.members, ())
        self.assertTrue(all(r.fav_ready == 4 for r in board.rows))

    def test_experiment_lane_error_card_becomes_unavailable_state_not_a_raise(self):
        board = _board(experiment_lanes={"exp_tbill": [{"symbol": "AMZN", "state": "ERROR",
                                                        "experiment_id": "EXP-TBILL", "reason": "boom"}]})
        self.assertEqual(_col(board, "tbill").state, "UNAVAILABLE:boom")
        self.assertTrue(all(r.fav_ready == 4 for r in board.rows))

    def test_gather_level_error_marks_every_experiment_column_unavailable(self):
        board = _board(experiment_lanes={"__error__": "RuntimeError: cache missing"})
        for key in ("tbill", "spread", "tail", "beta"):
            self.assertEqual(_col(board, key).state, "UNAVAILABLE:RuntimeError: cache missing")

    def test_pinned_names_are_rows_even_when_no_lane_names_them(self):
        vst = _row(_board(), "VST")
        self.assertTrue(vst.pinned)
        self.assertIsNone(vst.baseline_pick)

    def test_blocked_name_carries_reason_code_and_detail_and_is_never_promoted(self):
        et = _row(_board(), "ET")
        self.assertEqual(et.block_reason, "DATA_BLOCKED · chain 29 sessions old")
        self.assertIsNone(et.baseline_pick)

    def test_blocked_name_on_no_lane_is_still_a_row(self):
        board = _board(experiment_lanes={},
                       blocked=[{"symbol": "IREN", "reason_code": "DATA_BLOCKED", "detail": "no chain",
                                 "last_known_date": None, "unexpected": False}])
        iren = _row(board, "IREN")
        self.assertEqual(iren.block_reason, "DATA_BLOCKED · no chain")
        self.assertEqual(iren.fav_count, 0)
        self.assertFalse(iren.pinned)
        self.assertIsNone(iren.baseline_pick)

    def test_build_never_mutates_inputs(self):
        picks = [_pick("AMZN")]
        before = repr(picks)
        _board(baseline_picks=picks)
        self.assertEqual(repr(picks), before)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest discover -s tests -p 'test_board_lanes.py' -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'options_researcher.board_lanes'`

- [ ] **Step 3: Write the module (typed — pyright basic must pass)**

```python
# options_researcher/board_lanes.py
"""Pure lane-board builder for the attractiveness board's agreement table.

Spec: docs/superpowers/specs/2026-09-06-attractiveness-board-redesign-design.md §3–§5.
No file, network or clock access; every input is passed in. Nothing here is a
score or a signal: "Agree" is a count of favourable-lane membership, the
registered baseline decides row order and is never re-sorted.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import config


@dataclass(frozen=True)
class LaneMember:
    symbol: str
    label: str
    value: float | None
    rank: int | None
    counts: bool = True


@dataclass(frozen=True)
class LaneColumn:
    key: str
    title: str
    kind: str
    favourable: bool
    state: str
    as_of: str | None
    members: tuple[LaneMember, ...]
    note: str


@dataclass(frozen=True)
class BoardRow:
    symbol: str
    pinned: bool
    baseline_pick: Mapping[str, object] | None
    block_reason: str | None
    marks: Mapping[str, LaneMember]
    fav_count: int
    fav_ready: int


@dataclass(frozen=True)
class LaneBoard:
    columns: tuple[LaneColumn, ...]
    rows: tuple[BoardRow, ...]
    notes: tuple[str, ...]


_ORDER_NOTE = "top {cap} by {metric}, largest first (LLM-proposed 2026-09-06 display rule)"
_CONTEXT_LABELS = {"VETOED": "veto", "BLOCKED": "blocked", "DIRECTION_MISMATCH": "direction mismatch"}

# lane key -> (title, experiment_lanes key, flag state, metric, cell prefix)
_EXPERIMENTS: dict[str, tuple[str, str, str, str | None, str]] = {
    "tbill": ("T-bill carry", "exp_tbill", "ABOVE_TBILL", "carry_spread", "✓"),
    "spread": ("Spread stability", "exp_spread", "ELEVATED", "ratio", "!"),
    "tail": ("Tail shape", "exp_tail", "UNSTABLE", "jump_count", "!"),
    "beta": ("Beta to QQQ", "exp_beta", "UNSTABLE", None, "!"),
}


def _sym(item: object) -> str | None:
    if not isinstance(item, Mapping):
        return None
    s = item.get("symbol")
    return s if isinstance(s, str) and s else None


def _num(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    return float(value) if isinstance(value, (int, float)) and value == value else None


def _int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _cards(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [c for c in value if isinstance(c, Mapping)]


def lane_from_baseline(picks: Sequence[Mapping[str, object]] | None, *, cap: int,
                       as_of: str | None) -> LaneColumn:
    if picks is None:
        return LaneColumn("baseline", "Rule-based top 5", "ranking", True, "UNAVAILABLE:no picks",
                          as_of, (), "registered baseline")
    members: list[LaneMember] = []
    for i, p in enumerate(picks[:cap], 1):
        sym = _sym(p)
        if sym is not None:
            members.append(LaneMember(sym, f"#{i}", None, i))
    return LaneColumn("baseline", "Rule-based top 5", "ranking", True, "READY", as_of,
                      tuple(members), "registered baseline; decides row order")


def lane_from_context(selection: Mapping[str, object] | None, *, cap: int,
                      as_of: str | None) -> LaneColumn:
    note = "display-only · baseline + market-context tiebreak; only ALIGNED counts"
    if not isinstance(selection, Mapping):
        return LaneColumn("context", "Context lane", "ranking", True, "UNAVAILABLE:no selection", as_of, (), note)
    state = str(selection.get("state") or "UNAVAILABLE")
    if state != "READY":
        err = selection.get("error")
        tag = f"FAILED:{err}" if state == "FAILED" and err else state
        return LaneColumn("context", "Context lane", "ranking", True, tag, as_of, (), note)
    members: list[LaneMember] = []
    for i, row in enumerate(_cards(selection.get("rows"))[:cap], 1):
        sym = _sym(row)
        if sym is None:
            continue
        reason = str(row.get("context_reason") or "")
        if reason == "ALIGNED":
            members.append(LaneMember(sym, f"#{i}", _num(row.get("context_term")), i, True))
        else:
            members.append(LaneMember(sym, _CONTEXT_LABELS.get(reason, reason.lower() or "?"),
                                      _num(row.get("context_term")), i, False))
    return LaneColumn("context", "Context lane", "ranking", True, "READY", as_of, tuple(members), note)


def lane_from_composite(cards: Sequence[Mapping[str, object]] | None, *, cap: int, as_of: str | None,
                        baseline_order: Sequence[str]) -> LaneColumn:
    note = "display-only · angles agreeing; ties by baseline order, then symbol"
    if cards is None:
        return LaneColumn("composite", "Composite", "ranking", True, "UNAVAILABLE:no cards", as_of, (), note)
    pos = {s: i for i, s in enumerate(baseline_order)}
    usable: list[tuple[int, str, Mapping[str, object]]] = []
    for c in cards:
        sym = _sym(c)
        aligned = _int(c.get("aligned_count"))
        if sym is not None and aligned is not None:
            usable.append((aligned, sym, c))
    usable.sort(key=lambda t: (-t[0], pos.get(t[1], len(pos)), t[1]))
    members = tuple(
        LaneMember(sym, f"{c.get('grade') or '?'} · {aligned}/4", float(aligned), i)
        for i, (aligned, sym, c) in enumerate(usable[:cap], 1)
    )
    return LaneColumn("composite", "Composite", "ranking", True, "READY", as_of, members, note)


def lane_from_qm(picks: Sequence[Mapping[str, object]] | None, *, cap: int, as_of: str | None) -> LaneColumn:
    if picks is None:
        return LaneColumn("qm", "QM movement", "ranking", True, "UNAVAILABLE:no QM context", as_of, (),
                          "gated study")
    members: list[LaneMember] = []
    for i, p in enumerate(picks[:cap], 1):
        sym = _sym(p)
        if sym is not None:
            members.append(LaneMember(sym, f"#{i}", None, i))
    return LaneColumn("qm", "QM movement", "ranking", True, "READY", as_of, tuple(members),
                      "gated study · mechanical picks")


def lane_from_experiment(key: str, cards: object, *, cap: int, as_of: str | None) -> LaneColumn:
    title, _lane_key, flag_state, metric, prefix = _EXPERIMENTS[key]
    favourable = key in config.BOARD_FAVOURABLE_LANES
    if cards is None:
        return LaneColumn(key, title, "describing", favourable, "UNAVAILABLE:lane not computed", as_of, (),
                          "experiment")
    card_list = _cards(cards)
    errors = [c for c in card_list if c.get("state") == "ERROR"]
    if errors:
        reason = str(errors[0].get("reason") or "lane failed")
        return LaneColumn(key, title, "describing", favourable, f"UNAVAILABLE:{reason}", as_of, (), "experiment")
    flagged: list[tuple[float | None, str, Mapping[str, object]]] = []
    for c in card_list:
        sym = _sym(c)
        if sym is not None and c.get("state") == flag_state:
            flagged.append((_num(c.get(metric)) if metric else None, sym, c))
    if metric:
        flagged.sort(key=lambda t: (-(t[0] if t[0] is not None else float("-inf")), t[1]))
    else:
        flagged.sort(key=lambda t: t[1])
    members: list[LaneMember] = []
    for v, sym, _c in flagged[:cap]:
        members.append(LaneMember(sym, f"{prefix} {v:.2f}" if v is not None else prefix, v, None))
    note = f"experiment · {'favourable' if favourable else 'caution'} · flags names in state {flag_state}"
    if metric and len(flagged) > cap:
        note += " · " + _ORDER_NOTE.format(cap=cap, metric=metric)
    return LaneColumn(key, title, "describing", favourable, "READY", as_of, tuple(members), note)


def build_lane_board(
    *,
    baseline_picks: Sequence[Mapping[str, object]] | None,
    context_selection: Mapping[str, object] | None,
    composite_cards: Sequence[Mapping[str, object]] | None,
    qm_picks: Sequence[Mapping[str, object]] | None,
    experiment_lanes: Mapping[str, object] | None,
    pinned: Sequence[str],
    blocked: Sequence[Mapping[str, object]] | None,
    cap: int = config.PICK_TOP_N,
    board_as_of: str | None,
) -> LaneBoard:
    base_picks = list(baseline_picks or [])[:cap]
    base_order: list[str] = []
    pick_by_symbol: dict[str, Mapping[str, object]] = {}
    for p in base_picks:
        sym = _sym(p)
        if sym is not None:
            base_order.append(sym)
            pick_by_symbol[sym] = p

    exp: Mapping[str, object] = experiment_lanes if isinstance(experiment_lanes, Mapping) else {}
    gather_error = exp.get("__error__")
    columns_by_key: dict[str, LaneColumn] = {
        "baseline": lane_from_baseline(baseline_picks, cap=cap, as_of=board_as_of),
        "context": lane_from_context(context_selection, cap=cap, as_of=board_as_of),
        "composite": lane_from_composite(composite_cards, cap=cap, as_of=board_as_of, baseline_order=base_order),
        "qm": lane_from_qm(qm_picks, cap=cap, as_of=board_as_of),
    }
    for key, (_t, lane_key, _s, _m, _p) in _EXPERIMENTS.items():
        cards: object
        if gather_error is not None:
            cards = [{"symbol": "", "state": "ERROR", "reason": str(gather_error)}]
        elif experiment_lanes is None:
            cards = None
        else:
            cards = exp.get(lane_key)
        columns_by_key[key] = lane_from_experiment(key, cards, cap=cap, as_of=board_as_of)

    ordered_keys = tuple(config.BOARD_FAVOURABLE_LANES) + tuple(config.BOARD_CAUTION_LANES)
    columns = tuple(columns_by_key[k] for k in ordered_keys)
    fav_ready = sum(1 for c in columns if c.favourable and c.state == "READY")

    marks: dict[str, dict[str, LaneMember]] = {}
    for col in columns:
        for m in col.members:
            marks.setdefault(m.symbol, {})[col.key] = m

    block_by_symbol: dict[str, str] = {}
    for b in blocked or []:
        sym = _sym(b)
        if sym is not None:
            code = str(b.get("reason_code") or "DATA_BLOCKED")
            detail = str(b.get("detail") or "")
            block_by_symbol[sym] = f"{code} · {detail}" if detail else code

    def fav_count(sym: str) -> int:
        return sum(
            1 for k, m in marks.get(sym, {}).items()
            if m.counts and columns_by_key[k].favourable and columns_by_key[k].state == "READY"
        )

    pinned_set = {str(s) for s in pinned}
    # Rows: every name any lane marked, every owner-pinned name, and every
    # DATA_BLOCKED name (fail-visible in the decision area, spec §3/§6.7).
    symbols = set(marks) | pinned_set | set(block_by_symbol)
    rest = sorted((s for s in symbols if s not in base_order), key=lambda s: (-fav_count(s), s))
    rows = tuple(
        BoardRow(symbol=s, pinned=s in pinned_set, baseline_pick=pick_by_symbol.get(s),
                 block_reason=block_by_symbol.get(s), marks=dict(marks.get(s, {})),
                 fav_count=fav_count(s), fav_ready=fav_ready)
        for s in [*base_order, *rest]
    )
    notes = tuple(f"{c.title}: {c.state}" for c in columns if c.state != "READY")
    return LaneBoard(columns=columns, rows=rows, notes=notes)
```

- [ ] **Step 4: Run tests, lint, types**

Run: `uv run python -m unittest discover -s tests -p 'test_board_lanes.py' -v`
Expected: PASS (16 tests). The TESTS are the contract (spec §3); if the
implementation disagrees, fix the code.
Run: `uv run ruff check options_researcher/board_lanes.py tests/test_board_lanes.py`
Expected: `All checks passed!` (if ruff reports `I001` on a line this brief
supplies, the brief is wrong — apply `ruff check --diff`'s suggestion and note
it in the PR body; do not reorder names).
Add `"options_researcher/board_lanes.py"` to `pyrightconfig.json` `include`
(after `"options_researcher/attractiveness_dashboard.py"`), then
`uv run pyright` → `0 errors`.

- [ ] **Step 5: Commit**

```bash
git add options_researcher/board_lanes.py tests/test_board_lanes.py pyrightconfig.json
git commit -m "feat(board): pure lane-board builder (agreement table data; favourable-only count)"
```

---

### Task 4 (WP-D): Experiment lanes on the real gather path only; injectable in `assemble`

**Files:**
- Modify: `options_researcher/attractiveness_dashboard.py:1562-1571` (`assemble` signature), `:1745-1780` (gating + `out`), `:1784` (`_gather_all` neighbourhood), `:3775-3776` (`_experiments_shelf_html` docstring)
- Modify: `tests/test_attractiveness_layout.py:54-69` (`_board` default)
- Modify (D13 option A only): `tests/test_experiments_baseline.py:92-93`
- Test: `tests/test_attractiveness_dashboard.py`, `tests/test_experiments_baseline.py`

**Interfaces:**
- Consumes: `options_researcher.experiments_dashboard.build_experiment_lanes(symbols, asof=...)` (`experiments_dashboard.py:262`).
- Produces: `data["experiment_lanes"]` — present only when computed (real
  path) or injected; a dict of the four card lists, or `{"__error__": "<ExceptionName>: <message>"}`;
  `assemble(..., experiment_lanes=...)` keyword; `_default_experiment_lanes(as_of)`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_attractiveness_dashboard.py` (its helpers
`_fresh_section(symbol="NVDA", as_of="2026-08-14", **overrides)` and
`_stale_section(symbol="MSFT", as_of="2026-07-27", **overrides)` are defined
at `:3427` and `:3454`, near the bottom of the file):

```python
class ExperimentLaneGatherTests(unittest.TestCase):
    def test_injected_experiment_lanes_are_attached_verbatim(self):
        lanes = {"exp_tbill": [{"symbol": "AMZN", "state": "ABOVE_TBILL", "carry_spread": 0.65,
                                "experiment_id": "EXP-TBILL", "asof": "2026-08-14"}]}
        data = ad.assemble(symbol_sections=[_fresh_section()], rv21_by_symbol={},
                           today="2026-08-14", experiment_lanes=lanes)
        self.assertEqual(data["experiment_lanes"], lanes)

    def test_injected_fixtures_never_compute_experiment_lanes(self):
        # Hermeticity: an injected assemble() must not touch the cache (65 test sites depend on it).
        from unittest import mock
        with mock.patch("options_researcher.experiments_dashboard.build_experiment_lanes",
                        side_effect=AssertionError("must not be called")):
            data = ad.assemble(symbol_sections=[_fresh_section()], rv21_by_symbol={}, today="2026-08-14")
        self.assertNotIn("experiment_lanes", data)

    def test_default_experiment_lanes_records_a_builder_failure(self):
        from unittest import mock
        with mock.patch("options_researcher.experiments_dashboard.build_experiment_lanes",
                        side_effect=RuntimeError("cache missing")):
            lanes = ad._default_experiment_lanes("2026-08-14")
        self.assertEqual(lanes, {"__error__": "RuntimeError: cache missing"})

    def test_default_experiment_lanes_keeps_only_the_four_dict_lanes(self):
        from unittest import mock
        seen = {}

        def fake(symbols, *, asof):
            seen["asof"] = asof
            seen["symbols"] = tuple(symbols)
            return {"exp_beta": [], "exp_tail": [], "exp_spread": [], "exp_tbill": [],
                    "exp_short": [object()]}   # dataclass cards, not JSON-serialisable
        with mock.patch("options_researcher.experiments_dashboard.build_experiment_lanes", side_effect=fake):
            lanes = ad._default_experiment_lanes("2026-08-14")
        self.assertEqual(set(lanes), {"exp_beta", "exp_tail", "exp_spread", "exp_tbill"})
        self.assertEqual(seen, {"asof": "2026-08-14", "symbols": tuple(config.ATTRACTIVENESS_UNIVERSE)})

    def test_default_experiment_lanes_without_a_session_is_an_error_record(self):
        self.assertEqual(ad._default_experiment_lanes(None), {"__error__": "no board as-of session"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_dashboard.py' -k ExperimentLaneGather -v`
Expected: FAIL with `TypeError: assemble() got an unexpected keyword argument 'experiment_lanes'`

- [ ] **Step 3: Implement**

`assemble` (`:1562`): add keyword `experiment_lanes: Mapping[str, object] | None = None`
and document it in the docstring next to `open_positions`.

Gate exactly like `open_positions` (`:1745`, `if open_positions is None and real_assembly:`):

```python
    if experiment_lanes is None and real_assembly:
        experiment_lanes = _default_experiment_lanes(page_as_of)
```

placed after `page_as_of = _page_data_as_of(canonical_symbols)` (`:1751`) so
the board's own chain session is the as-of. Then, next to
`if open_positions is not None: out["open_positions"] = dict(open_positions)` (`:1777`):

```python
    if experiment_lanes is not None:
        out["experiment_lanes"] = dict(experiment_lanes)
```

Add near `_gather_all` (`:1784`):

```python
_EXPERIMENT_DICT_LANES = ("exp_beta", "exp_tail", "exp_spread", "exp_tbill")


def _default_experiment_lanes(as_of: object) -> dict[str, object]:
    """Compute the four parking-lot experiment lanes from cached data for the
    lane board (spec §4), on the REAL gather path only. Fail-visible: a builder
    exception becomes a recorded error the board prints as a lane state.
    ``exp_short`` (dataclass cards) is deliberately dropped: it is not a lane
    of this board and is not JSON-serialisable."""
    from options_researcher import experiments_dashboard

    if not isinstance(as_of, str) or not as_of:
        return {"__error__": "no board as-of session"}
    try:
        lanes = experiments_dashboard.build_experiment_lanes(
            list(config.ATTRACTIVENESS_UNIVERSE), asof=as_of)
    except Exception as exc:  # fail-visible by design (spec §5)
        return {"__error__": f"{exc.__class__.__name__}: {exc}"}
    return {key: list(lanes.get(key) or []) for key in _EXPERIMENT_DICT_LANES}
```

Amend the docstring at `:3775-3776` so the two sources of truth agree
(CLAUDE.md: say so when sources conflict):

```python
    """Passive local-view links only: this shelf never imports or runs an
    experiment builder. (The lane board's gather step does run the four
    builders for its agreement table — brief 39 / spec §4, owner-directed
    2026-09-06; that is the ONLY place the board computes experiments.)"""
```

**D13 option A — make the isolation guard precise (owner-ruled; see the
section before Global Constraints).** Replace
`test_production_dashboard_has_no_experiment_imports`
(`tests/test_experiments_baseline.py:92-93`) with:

```python
    def test_production_dashboard_experiment_imports_are_confined_to_the_lane_gather(self):
        # D13 (owner-ruled, spec pending-rulings section): the ONLY experiment
        # import/call site the production dashboard may contain is the display-only
        # gather helper `_default_experiment_lanes` (brief 39 / spec §4, D5). Every
        # other line of the file must be as clean as before.
        source = Path(dashboard.__file__).read_text()
        tree = ast.parse(source)
        sites = [node for node in ast.walk(tree)
                 if isinstance(node, ast.FunctionDef) and node.name == "_default_experiment_lanes"]
        self.assertEqual(len(sites), 1)
        lo, hi = sites[0].lineno, sites[0].end_lineno or sites[0].lineno
        lines = source.splitlines(keepends=True)
        outside = "".join(lines[: lo - 1]) + "\n" * (hi - lo + 1) + "".join(lines[hi:])
        self.assertFalse(_experiment_boundary_violations(outside))
        self.assertEqual(
            sorted(_experiment_boundary_violations(source)),
            ["call options_researcher.experiments_dashboard.build_experiment_lanes",
             "from options_researcher.experiments_dashboard"],
        )
```

Keep `test_boundary_rejects_direct_from_and_aliased_experiment_forms` (`:95-105`)
untouched — it proves the detector still rejects every form. Run the file:
`uv run python -m unittest discover -s tests -p 'test_experiments_baseline.py' -v`
→ 4 tests OK. (`test_module_entry_no_args_matches_production_command`, `:107`,
runs the real build from the repo root; under the flag it now also computes the
four lanes on that cache — a few seconds slower, and any failure is recorded as
a lane state, never an exception.)

In `tests/test_attractiveness_layout.py` make `_board` (`:54-69`) hermetic by
default while letting a caller override:

```python
def _board(symbols, *, eligible=True, today="2026-08-25", **assemble_kwargs):
    assemble_kwargs.setdefault("experiment_lanes", {})
    data = ad.assemble(
        symbol_sections=[_put_section(symbol) for symbol in symbols],
        rv21_by_symbol={},
        today=today,
        composite_signals=[],
        **assemble_kwargs,
    )
    ...unchanged...
```

(`setdefault` avoids the `TypeError: got multiple values` a hard-coded kwarg
would cause when a test passes `experiment_lanes=`.)

One EXISTING test takes the real gather path and therefore now runs the four
builders inside the offline suite:
`tests/test_attractiveness_dashboard.py:2801`
`test_main_loads_board_and_context_from_same_external_root` (call site
`:2859`) patches
`ad._gather_all`, so `assemble()` sees `real_assembly=True` and
`_default_experiment_lanes` fires (round 4 measured: one call, ~2 ms on that
fixture's root, four lanes returned, test passes). Name it in the PR body so a
future cache-dependent slowdown there is not a mystery.

- [ ] **Step 4: Run tests**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_*.py' -v 2>&1 | tail -5`
Expected: OK — the new tests pass and the 203 + 28 existing tests still pass
in about the same time as before (no cache reads: the layout suite must still
run in well under a second). `LegacyByteIdentityTests` still PASS (the
injected fixture path is unchanged).

- [ ] **Step 5: Commit**

```bash
git add options_researcher/attractiveness_dashboard.py tests/test_attractiveness_dashboard.py tests/test_attractiveness_layout.py tests/test_experiments_baseline.py
git commit -m "feat(board): experiment lanes on the real gather path (injectable, fail-visible, four dict lanes only); isolation guard made precise per D13"
```

---

### Task 5 (WP-E): Extract the symbol panel byte-identically; add the new section builders

**Files:**
- Modify: `options_researcher/attractiveness_dashboard.py` — extraction from the
  per-symbol loop at `:5548-5664` (`for sec in data["symbols"]:` … `symbols_html += (…)`),
  new builders placed after `_composite_html` (`:4774`)
- Test: `tests/test_attractiveness_dashboard.py`, `tests/test_attractiveness_layout.py` (byte-identity)

**Interfaces:**
- Consumes: `LaneBoard` (Task 3); `_risk_line` (`:3192`); `_event_chips_html(card, symbol, evaluation_date, event_view)` (`:3065`; `event_chips` at `:3024`); `_open_slots_html` (`:4104`), `_empty_hero_slot(data, slot)` (`:4116`); `_panel_status(sec, stale_symbols)` (defined `:806-827`, called `:5594`; returns `(status_labels, panel_open)`); `trading_sessions_between` (`top3_snapshot.py:83`); `CHAIN_SOURCE`, `CONVENTION_LABEL`, `CHAINS_ABSENT` (`schwab_chain_view.py`).
- Produces:
  - `_symbol_panel_html(sec, *, context, event_view, evaluation_date, stale_symbols, pinned_symbols, protected_card_ids) -> tuple[str, str]` — `(panel_html, symbol_name)`, byte-identical to the loop body (no `data` parameter: the body does not read it once `evaluation_date` is hoisted)
  - `_table_footnotes_html() -> str` — the two relocated authority sentences (pinned, context lane), printed by the agreement table AND by the `LANE BOARD FAILED` fallback
  - `_status_strip_html(data, context) -> str`
  - `_position_tiles_html(data, event_line_text: str) -> str`
  - `_agreement_table_html(board) -> str`
  - `_event_line_html(board, event_view, evaluation_date) -> str`
  - `_pick_details_html(data, board, *, context, event_view, evaluation_date, stale_symbols, pinned_symbols, protected_card_ids) -> str`
  - `_open_slots_notice_html(data, watch_picks) -> str`

- [ ] **Step 1: Extract the per-symbol panel (no behaviour change)**

The loop at `:5548-5664` reads these enclosing locals: `context`,
`event_view`, `stale_symbols` (`:5544`), `pinned_symbols` (`:5545`),
`protected_card_ids` (`:5539`, extended `:5541-5543`), and computes
`evaluation_date` INSIDE the loop (`:5554`,
`str(data.get("evaluation_date") or data.get("data_as_of") or "")` — the only
place the body touches `data`, and loop-invariant) and
`status_labels, panel_open = _panel_status(sec, stale_symbols)` (`:5594`) and
`open_attr` (`:5601-5602`). It appends `symbol_names` at `:5633`. The panel
markup is `<div class="symbol-anchor" id="symbol-{symbol}"></div>` followed by
`<details class="panel symbol-panel"{open_attr}>` (`:5635-5636`) — tests anchor
on the `symbol-anchor` id, not on the `<details>` tag.

1. Hoist `evaluation_date = str(data.get("evaluation_date") or data.get("data_as_of") or "")`
   to immediately BEFORE `for sec in data["symbols"]:` (`:5548`). Delete the
   in-loop copy at `:5554`. (Loop-invariant. Required because Task 6 reads
   `evaluation_date` AFTER the loop; today nothing after the loop reads it —
   `:5716` recomputes its own — so there is no latent bug, only one that Task 6
   would introduce on an empty `data["symbols"]` without the hoist.)
2. Move the loop body (from `tech = sec.get("technicals")` through the
   `symbols_html += (…)` closing paren at `:5664`) into

```python
def _symbol_panel_html(
    sec: Any, *, context: dict | None, event_view: Mapping[str, object] | None,
    evaluation_date: str, stale_symbols: set[str], pinned_symbols: set[str],
    protected_card_ids: set[int],
) -> tuple[str, str]:
    """One per-symbol panel, byte-identical to the pre-brief-39 inline loop.
    Returns (panel_html, symbol_name). It decides its own open/closed state
    (fail-visible DATA_BLOCKED/STALE/SKIPPED, and owner-pinned names when the
    caller passes them in pinned_symbols)."""
    ...the moved body, with exactly two mechanical edits, ending with:
    return panel_html, symbol_name
```

   The two mechanical edits: delete the line `symbol_names.append(symbol_name)`
   (`:5633`; the caller appends) and rename the accumulator `symbols_html += (`
   (`:5634`) to `panel_html = (`. Nothing else in the body changes. Place the
   function immediately ABOVE `_render_result` (`:5506`). Add `Any` to the
   typing import at `:45` (`from typing import TYPE_CHECKING, Any`). The
   annotation is `sec: Any` — deliberately, because that is what the body sees
   today: `sec` iterates `data["symbols"]` where `data: dict` (`:5507`), so
   pyright infers `Unknown`; round 3 proved `sec: dict` (rev 3's choice) fails
   pyright on `failure_map.get(sec.get("symbol"))` (`reportArgumentType`) and
   `sec: Any` gives 0 errors. `context: dict | None` matches `:5509` and
   `_symbol_context_html(symbol, context)` (`:4638`). Byte-identical must also
   be type-identical. If the moved body turns out to reference `data` anywhere,
   keep a `data: dict` parameter and say so in the PR body (rounds 2 and 3 found
   no such reference). `status_labels`/`panel_open` are computed inside via
   `_panel_status(sec, stale_symbols)` as today.
3. The loop becomes exactly:

```python
    for sec in data["symbols"]:
        panel_html, symbol_name = _symbol_panel_html(
            sec, context=context, event_view=event_view, evaluation_date=evaluation_date,
            stale_symbols=stale_symbols, pinned_symbols=pinned_symbols, protected_card_ids=protected_card_ids)
        symbol_names.append(symbol_name)
        symbols_html += panel_html
```

- [ ] **Step 2: Prove the extraction is byte-identical**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_layout.py' -k LegacyByteIdentity -v`
Expected: PASS (the Task 2 snapshot). If it fails, the extraction moved or
reordered something — fix the extraction, never the snapshot.

- [ ] **Step 3: Write the failing render tests for the new builders**

Append to `tests/test_attractiveness_dashboard.py`:

```python
class LaneBoardRenderTests(unittest.TestCase):
    def _board(self):
        from options_researcher import board_lanes as bl
        pick = {"symbol": "AMZN", "lane": "long_call", "strike": 265.0, "expiry": "2026-09-16", "dte": 13,
                "score": 0,
                "card": {"headline": "Buy the AMZN $265 call", "strike": 265.0, "expiry": "2026-09-16",
                         "dte": 13, "cost": 319.0, "grades": {"liquidity": "GREEN"},
                         "risk": {"max_loss": 319.0, "breakeven": 268.19},
                         "top3_snapshot": {"candidate_id": "AMZN:long_call:2026-09-16:265.00"}}}
        return bl.build_lane_board(
            baseline_picks=[pick], context_selection={"state": "FAILED", "rows": [], "error": "ValueError"},
            composite_cards=[], qm_picks=[], experiment_lanes={"exp_tbill": [
                {"symbol": "NBIS", "state": "ABOVE_TBILL", "carry_spread": 2.89, "experiment_id": "EXP-TBILL"}]},
            pinned=("VST",), blocked=[], cap=5, board_as_of="2026-09-03")

    def test_agreement_table_prints_every_column_with_state_and_asof(self):
        html = ad._agreement_table_html(self._board())
        for title in ("Rule-based top 5", "Context lane", "Composite", "QM movement", "T-bill carry",
                      "Spread stability", "Tail shape", "Beta to QQQ"):
            self.assertIn(title, html)
        self.assertIn("FAILED:ValueError", html)
        self.assertIn("2026-09-03", html)
        self.assertIn('class="agree"', html)
        self.assertIn("Rule-based top 5 — best policy-and-liquidity fit today", html)   # h2 text kept (see step 4)
        self.assertIn("TOP 5 PICKS TODAY", html)                                        # eyebrow text kept
        # The three authority sentences whose sections leave the flag-on page (Global Constraints):
        self.assertIn("This is a fit ranking, not a prediction", html)
        self.assertIn("owner-pinned visibility — not ranked; these cards do not compete with or reorder "
                      "the Top-5 shortlist.", html)
        self.assertIn(ad._CONTEXT_LANE_DISCLAIMER, html)

    def test_agreement_cell_counts_favourable_ready_lanes_only(self):
        html = ad._agreement_table_html(self._board())
        row = html[html.index('<td class="sym">AMZN'):]
        self.assertIn("1/4", row[: row.index("</tr>")])

    def test_pinned_name_without_a_pick_is_a_row_marked_pinned(self):
        html = ad._agreement_table_html(self._board())
        vst = html[html.index('<td class="sym">VST'):]
        self.assertIn("pinned", vst[:400])
        self.assertIn("not in the registered top 5", vst[:800])

    def test_position_tiles_flag_a_stale_last_mark(self):
        data = {"open_positions": {"rows": [
            {"book": "H6", "identifier": "H6-0001", "text": "H6-0001 NVDA $220.00 call · exp 2026-09-18 · entered 2026-07-13"},
            {"book": "shares", "identifier": "VST", "text": "VST 39 shares · cost basis $142.28 · acquired 2026-06-15"}],
            "missing_sources": [], "sources": [], "h6_last_mark": "2026-07-27"},
            "evaluation_date": "2026-09-04"}
        html = ad._position_tiles_html(data, "FOMC decision · 2026-09-16")
        self.assertIn("H6-0001", html)
        self.assertIn("2026-07-27", html)
        self.assertIn("29 sessions unmarked", html)
        self.assertIn('class="tile bad"', html)          # older than CHAIN_STALE_BLOCK_SESSIONS
        self.assertIn("VST 39 shares", html)
        self.assertIn("FOMC decision", html)

    def test_position_tiles_say_so_when_the_book_is_unreadable(self):
        data = {"open_positions": {"rows": [], "missing_sources": ["data/positions/h6_positions.csv"],
                                   "sources": [], "h6_last_mark": None}, "evaluation_date": "2026-09-04"}
        html = ad._position_tiles_html(data, "")
        self.assertIn('<div class="v">UNREAD</div>', html)
        self.assertIn("data/positions/h6_positions.csv", html)
        self.assertEqual(html.count('<div class="k">'), 4)          # spec §2.2: always four tiles (the wrapper is "tiles")

    def test_position_tiles_are_four_even_when_the_book_was_not_assembled(self):
        # Every injected fixture hits this branch: assemble() loads the book only on the real path (:1745).
        html = ad._position_tiles_html({"evaluation_date": "2026-09-04"}, "")
        self.assertEqual(html.count('<div class="k">'), 4)
        self.assertIn("open_positions not assembled", html)

    def test_status_strip_is_fail_visible_for_closes_and_ignores_chains_absent(self):
        from options_researcher.schwab_chain_view import CHAIN_SOURCE, CHAINS_ABSENT
        data = {"data_as_of": "2026-09-03", "as_of_kind": CHAIN_SOURCE, "evaluation_date": "2026-09-04",
                "fresh_symbols": ["AMZN"], "stale_symbols": ["ET"],
                "underlying_closes_freshness": {"state": "unavailable", "detail": "missing store files: X"},
                "schwab_lane": {"verified_sessions": ["2026-09-03"], "receipts_found": True, "failures": [
                    {"session": "2026-09-03", "kind": CHAINS_ABSENT, "reason": "research checkout"},
                    {"session": "2026-09-01", "kind": "UNVERIFIED", "reason": "manifest missing"},
                    {"session": "2026-08-01", "kind": "UNVERIFIED", "reason": "old"}]}}
        html = ad._status_strip_html(data, context=None)
        self.assertIn('class="dot crit"></span>closes unavailable', html)
        self.assertIn("1 capture failure in window", html)     # 09-01 counts (3 sessions), 08-01 aged out, CHAINS_ABSENT ignored
        self.assertIn("1 names fresh · 1 stale (ET)", html)

    def test_open_slots_notice_mirrors_the_hero_slot_count(self):
        data = ad.assemble(symbol_sections=[_fresh_section()], rv21_by_symbol={}, today="2026-08-14",
                           experiment_lanes={})
        watch = ad.select_top_picks(data, include_csp_watch=True)
        html = ad._open_slots_notice_html(data, watch)
        self.assertEqual(html.count("intentional open slot") > 0, len(watch) < config.PICK_TOP_N)

    def test_pick_details_render_only_table_names(self):
        data = ad.assemble(symbol_sections=[_fresh_section("AMZN"), _fresh_section("MSFT")],
                           rv21_by_symbol={}, today="2026-08-14", experiment_lanes={})
        html = ad._pick_details_html(
            data, self._board(), context=None, event_view=None, evaluation_date="2026-08-14",
            stale_symbols=set(), pinned_symbols=set(), protected_card_ids=set())
        self.assertIn('id="symbol-AMZN"', html)
        self.assertNotIn('id="symbol-MSFT"', html)
        self.assertNotIn('id="symbol-VST"', html)    # pinned row WITHOUT a section: a row, never a panel
```

- [ ] **Step 4: Implement the builders**

Add after `_composite_html` (`:4774`). Reuse the existing helpers by exact
name; `re` is already imported at `:38`; `config` is module-level. Add
`from options_researcher.board_lanes import BoardRow, LaneBoard, LaneColumn`
inside the existing `if TYPE_CHECKING:` block (`:50-51`) so the annotations
below resolve for pyright (`from __future__ import annotations` at `:30` makes
them free at runtime; round 2 reproduced `reportUndefinedVariable` without
this). Two narrowing helpers keep `Mapping[str, object]` values iterable for
pyright (round 2 reproduced the `"object" is not iterable` errors):

```python
def _seq(value: object) -> list[object]:
    """pyright-safe list view of a Mapping value that should be a sequence."""
    return list(value) if isinstance(value, (list, tuple)) else []


def _status_strip_html(data: dict, context: dict | None) -> str:
    """One line, five facts, each a coloured dot + a word (spec §2.1). Every
    dot is state-driven; an unavailable closes store is CRIT, never green."""
    from options_researcher.schwab_chain_view import CHAIN_SOURCE, CHAINS_ABSENT, CONVENTION_LABEL
    from options_researcher.top3_snapshot import trading_sessions_between

    as_of = str(data.get("data_as_of") or "no cached data")
    on_schwab = data.get("as_of_kind") == CHAIN_SOURCE
    source = f"{CONVENTION_LABEL}, session {as_of}" if on_schwab else f"frozen EOD {as_of}"
    fresh = _seq(data.get("fresh_symbols"))
    stale = [str(s) for s in _seq(data.get("stale_symbols"))]
    closes = data.get("underlying_closes_freshness")
    closes = closes if isinstance(closes, Mapping) else {"state": "unavailable", "detail": "not assembled"}
    closes_ok = closes.get("state") == "available"
    closes_text = (f"closes through {closes.get('as_of')}" if closes_ok
                   else f"closes unavailable — {closes.get('detail', 'unknown')}")
    lane = data.get("schwab_lane")
    failures = lane.get("failures") if isinstance(lane, Mapping) else None
    failures = [f for f in (failures or []) if isinstance(f, Mapping) and f.get("kind") != CHAINS_ABSENT]
    # Same retention rule as _schwab_state_html (brief 37 WP-G, :1058-1110): a failure
    # is "in window" when age <= CHAIN_STALE_BLOCK_SESSIONS; when the age cannot be
    # computed the failure stays counted (fail-visible).
    evaluation = data.get("evaluation_date")
    in_window = 0
    for f in failures:
        age: int | None = None
        if isinstance(evaluation, str) and isinstance(f.get("session"), str):
            try:
                age = trading_sessions_between(str(f["session"]), evaluation)
            except Exception:
                age = None
        if not isinstance(age, int) or age <= config.CHAIN_STALE_BLOCK_SESSIONS:
            in_window += 1
    researched = str((context or {}).get("researched_on") or "never")

    def dot(cls: str, text: str) -> str:
        return f'<span class="strip-item"><span class="dot {cls}"></span>{_esc(text)}</span>'

    plural = "failure" if in_window == 1 else "failures"
    return ('<div class="status-strip">'
            + dot("good" if on_schwab else "warn", f"option quotes: {source}")
            + dot("good" if closes_ok else "crit", closes_text)
            + dot("warn" if stale else "good",
                  f"{len(fresh)} names fresh · {len(stale)} stale" + (f" ({', '.join(stale)})" if stale else ""))
            + dot("good" if researched == as_of else "warn", f"research annotations {researched}")
            + dot("crit" if in_window else "good", f"{in_window} capture {plural} in window")
            + "</div>")


def _position_tiles_html(data: dict, event_line_text: str) -> str:
    """Exactly four stat tiles (spec §2.2). Reads only data['open_positions'];
    an unreadable source is printed in the first tile, never treated as an empty
    book. The last-mark
    tile is red when the mark is older than the board's own staleness limit
    (config.CHAIN_STALE_BLOCK_SESSIONS — reused, not a new number)."""
    from options_researcher.top3_snapshot import trading_sessions_between

    positions = data.get("open_positions")
    if not isinstance(positions, Mapping):
        # Not assembled (every injected fixture; :1745 loads the book on the real path only).
        # Still exactly four tiles, first one fail-visible.
        positions = {"rows": [], "missing_sources": ["open_positions not assembled"], "sources": [],
                     "h6_last_mark": None}
    rows = [r for r in (positions.get("rows") or []) if isinstance(r, Mapping)]
    missing = [str(m) for m in (positions.get("missing_sources") or [])]
    option_rows = [r for r in rows if r.get("book") != "shares"]
    share_rows = [r for r in rows if r.get("book") == "shares"]
    last_mark = positions.get("h6_last_mark")
    evaluation = data.get("evaluation_date")
    mark_age: int | None = None
    if isinstance(last_mark, str) and isinstance(evaluation, str):
        try:
            mark_age = trading_sessions_between(last_mark, evaluation)
        except Exception:
            mark_age = None
    mark_bad = isinstance(mark_age, int) and mark_age > config.CHAIN_STALE_BLOCK_SESSIONS

    def tile(k: str, v: str, d: str, cls: str = "") -> str:
        return (f'<div class="tile{(" " + cls) if cls else ""}"><div class="k">{_esc(k)}</div>'
                f'<div class="v">{_esc(v)}</div><div class="d">{_esc(d)}</div></div>')

    tiles: list[str] = []
    if missing:   # spec §2.2 is FOUR tiles: an unreadable/unassembled book takes over the first tile, never a fifth
        tiles.append(tile("Open option", "UNREAD", "could not be read: " + ", ".join(missing), "bad"))
    else:
        tiles.append(tile("Open option", str(option_rows[0].get("identifier")) if option_rows else "none",
                          str(option_rows[0].get("text")) if option_rows else "no open option positions"))
    tiles.append(tile("Last mark", str(last_mark) if last_mark else "none",
                      f"{mark_age} sessions unmarked" if isinstance(mark_age, int) else "no mark recorded",
                      "bad" if mark_bad else ""))
    tiles.append(tile("Shares", str(share_rows[0].get("text", "")).split(" · ")[0] if share_rows else "none",
                      str(share_rows[0].get("text")) if share_rows else "no share lots recorded"))
    tiles.append(tile("Event ahead", event_line_text.split(" · ")[0] if event_line_text else "none",
                      event_line_text or "no upcoming event for the registered picks"))
    return '<div class="tiles">' + "".join(tiles) + "</div>"


_AGREE_BAR_PX = 14   # display-only: bar width per agreeing lane (LLM-proposed 2026-09-06; not a strategy number)


def _agreement_table_html(board: LaneBoard) -> str:
    """Spec §3. Row order and the 'Agree' count come from the pure module;
    this function only prints. The <h2> text is byte-identical to today's
    shortlist heading (:4213); the eyebrow keeps today's phrase (:4212) and
    appends " · agreement across lanes". 20+ test assertions locate the
    shortlist by them. It also carries, verbatim, the
    three authority sentences whose sections leave the flag-on page (hero
    :4215 in header-sub; pinned strip :4707-4708 and context lane :4442-4447
    via _table_footnotes_html) — see the brief's Global Constraints."""
    fav = [c for c in board.columns if c.favourable]
    cau = [c for c in board.columns if not c.favourable]

    def header(col: LaneColumn) -> str:
        return (f'<th title="{_esc(col.note)}">{_esc(col.title)}<br>'
                f'<span class="th-sub">{_esc(col.kind)} · as of {_esc(str(col.as_of or "?"))} · {_esc(col.state)}</span></th>')

    def cell(row: BoardRow, col: LaneColumn) -> str:
        if col.state != "READY":
            return '<td class="lane-off"></td>'
        m = row.marks.get(col.key)
        if m is None:
            return "<td></td>"
        cls = "warn" if not col.favourable else ("veto" if not m.counts else "on")
        return f'<td><span class="chip {cls}">{_esc(m.label)}</span></td>'

    def pick_cell(row: BoardRow) -> str:
        if row.baseline_pick is not None:
            card = row.baseline_pick.get("card")
            card = card if isinstance(card, Mapping) else {}
            risk = card.get("risk")
            risk = risk if isinstance(risk, Mapping) else {}
            cost = _num_or_zero(card.get("cost"))
            worst = _num_or_zero(risk.get("max_loss"))
            be = _num_or_zero(risk.get("breakeven"))
            econ = (f"cost ${cost:,.0f} · worst -${worst:,.0f} · breakeven ${be:,.2f} · "
                    f"{_esc(str(card.get('expiry') or '?'))} ({_esc(str(card.get('dte') or '?'))}d)")
            return (f'{_esc(str(card.get("headline") or ""))}<div class="econ">{econ} · '
                    f'<a href="#symbol-{_esc(row.symbol)}">details</a></div>')
        if row.block_reason:
            return f'<span class="blocked">{_esc(row.block_reason)}</span>'
        return '<span class="muted">not in the registered top 5</span>'

    head = ('<tr><th rowspan="2">Name</th><th rowspan="2">Registered pick (baseline decides the order)</th>'
            f'<th colspan="{len(fav)}" class="group">Favourable lanes · top {config.PICK_TOP_N} each</th>'
            '<th rowspan="2">Agree</th>'
            f'<th colspan="{len(cau)}" class="group">Cautions (shown, never counted)</th></tr>'
            "<tr>" + "".join(header(c) for c in fav) + "".join(header(c) for c in cau) + "</tr>")
    body: list[str] = []
    for row in board.rows:
        pinned = ' <span class="chip">pinned</span>' if row.pinned else ""
        agree = (f'<td class="agree-cell"><span class="bar" style="width:{row.fav_count * _AGREE_BAR_PX}px"></span>'
                 f'<span class="agree">{row.fav_count}/{row.fav_ready}</span></td>')
        body.append(f'<tr><td class="sym">{_esc(row.symbol)}{pinned}</td><td>{pick_cell(row)}</td>'
                    + "".join(cell(row, c) for c in fav) + agree + "".join(cell(row, c) for c in cau) + "</tr>")
    notes = "".join(f'<div class="notice info">{_esc(n)}</div>' for n in board.notes)
    foot = _table_footnotes_html()
    return ('<section class="panel agreement" id="agreement-table">'
            '<div class="eyebrow">Daily shortlist · TOP 5 PICKS TODAY · agreement across lanes</div>'
            '<h2>Rule-based top 5 — best policy-and-liquidity fit today</h2>'
            '<p class="header-sub">Every name any lane picked or flagged, the registered picks first. '
            'The registered baseline decides the order and is never re-ordered. '
            'This is a fit ranking, not a prediction. "Agree" counts favourable lanes only — '
            'a description, never a score; cautions are shown but never counted.</p>'
            f'{notes}<table class="agreement-table"><thead>{head}</thead><tbody>{"".join(body)}</tbody></table>'
            f'{foot}</section>')


def _num_or_zero(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def _table_footnotes_html() -> str:
    """The two authority sentences whose sections leave the flag-on page, verbatim
    (pinned strip :4707-4708; context lane :4442-4447). Printed under the agreement
    table AND by the LANE BOARD FAILED fallback, so spec §6.4 holds on both paths."""
    return ('<p class="table-foot">Pinned rows: owner-pinned visibility — not ranked; these cards do not '
            'compete with or reorder the Top-5 shortlist.</p>'
            f'<p class="table-foot">Context lane column: {_esc(_CONTEXT_LANE_DISCLAIMER)}</p>')


def _event_line_html(board: LaneBoard, event_view: Mapping[str, object] | None,
                     evaluation_date: str) -> str:
    """D11: the sorted union of the REGISTERED PICKS' event chips, printed once.
    Names without a baseline pick contribute nothing (their chips stay in
    their detail panel). An EVENT LAYER FAILED banner is returned as-is."""
    if not event_view:
        return ""
    seen: dict[str, None] = {}
    for row in board.rows:
        if row.baseline_pick is None:
            continue
        card = row.baseline_pick.get("card")
        if not isinstance(card, Mapping):
            continue
        frag = _event_chips_html(dict(card), row.symbol, evaluation_date, event_view)
        if frag.startswith('<div class="notice bad">'):
            return frag
        for text in re.findall(r'<span class="event-chip">EVENT · (.*?)</span>', frag):
            seen.setdefault(text, None)
    if not seen:
        return ""
    return ('<div class="event-line"><span class="event-line-label">Events ahead for the registered picks:</span>'
            + "".join(f'<span class="event-chip">EVENT · {t}</span>' for t in sorted(seen)) + "</div>")


def _open_slots_notice_html(data: dict, watch_picks: Sequence[Mapping[str, object]]) -> str:
    """Today's consolidated open-slot notice, unchanged in text (:4200-4203 uses
    the watch-inclusive pick list to size the range). Wrapped in the same
    `hero-grid` parent the hero gives it (:4708 pattern), because
    `_open_slot_group_html` (:4096) emits `hero-card … empty-slot` markup whose
    layout rules live on that parent. Empty when there is no open slot."""
    inner = _open_slots_html(
        [_empty_hero_slot(data, slot)
         for slot in range(len(watch_picks) + 1, config.PICK_TOP_N + 1)],
        prefix="Pick", total=config.PICK_TOP_N)
    return f'<div class="hero-grid open-slots">{inner}</div>' if inner else ""


def _pick_details_html(
    data: dict, board: LaneBoard, *, context: dict | None,
    event_view: Mapping[str, object] | None, evaluation_date: str, stale_symbols: set[str],
    pinned_symbols: set[str], protected_card_ids: set[int],
) -> str:
    """One per-name panel per table row, in BOARD-ROW order (spec §2.5) — not in
    data["symbols"] order. A row whose symbol has no section (a pinned name
    with no cached chain; every DATA_BLOCKED row) renders a row in the table
    but no panel here; other names are not rendered at all. The panel HTML is
    byte-identical to today's (D10); the caller decides whether pinned names
    are force-open (I1: under the flag they are not)."""
    wanted = [r.symbol for r in board.rows]
    by_symbol = {str(sec.get("symbol")): sec for sec in _seq(data.get("symbols")) if isinstance(sec, dict)}
    parts: list[str] = []
    for symbol in wanted:
        sec = by_symbol.get(symbol)
        if sec is None:
            continue
        panel_html, _name = _symbol_panel_html(
            sec, context=context, event_view=event_view, evaluation_date=evaluation_date,
            stale_symbols=stale_symbols, pinned_symbols=pinned_symbols, protected_card_ids=protected_card_ids)
        parts.append(panel_html)
    if not parts:
        return ""
    return ('<section class="panel details" id="pick-details"><div class="eyebrow">Pick details on demand</div>'
            '<h2>Details for the names above</h2>' + "".join(parts) + "</section>")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_*.py' -v 2>&1 | tail -5`
Expected: `LaneBoardRenderTests` PASS; every pre-existing test still PASSES
(nothing is wired into `_render_result` yet); `LegacyByteIdentityTests` PASS.

- [ ] **Step 6: Commit**

```bash
git add options_researcher/attractiveness_dashboard.py tests/test_attractiveness_dashboard.py
git commit -m "feat(board): extract the symbol panel byte-identically; add status strip, tiles, agreement table, event line, details builders"
```

---

### Task 6 (WP-F): Wire the new page order behind the flag

**Files:**
- Modify: `options_researcher/attractiveness_dashboard.py:5690-5721` (`event_css` at `:5694-5695`, `body_html` at `:5700-5721`), `:5726` (`<style>` emission), `:5737` (`_sticky_nav_html` call); NEW module constant `_BOARD_STYLE` placed directly after `_STYLE` (never inside it — `_STYLE` is emitted on BOTH paths, so any byte added to it breaks the Task 2 byte-identity proof; round 3 measured exactly that, 1,986 bytes)
- Test: `tests/test_attractiveness_layout.py`

**Interfaces:**
- Consumes: Task 3 `build_lane_board`, Task 5 builders, `config.BOARD_LANES_ENABLED`.
- Produces: the redesigned page when the flag is on; today's page, byte-identical, when off.

- [ ] **Step 1: Write the failing layout tests**

Append to `tests/test_attractiveness_layout.py` (the drawer element is
`<details class="panel diagnostics-drawer" id="diagnostics">`; the freshness
heading is `DATA FRESHNESS`; the class holding `_DRAWER_SECTIONS` is
`DiagnosticsDrawerTests` at `:374`):

```python
class LaneBoardLayoutTests(unittest.TestCase):
    """Spec §2 page order, with the flag on."""

    # Mirrors DiagnosticsDrawerTests._rendered (:385-402): without context /
    # qm_context / research_views_status, "Quant-want background" and "Market
    # context" are not rendered at all (:4563-4566, :4593-4597) and the drawer
    # drops empty sections (:5493) — the six-section assertion would raise.
    _DRAWER_INPUTS = dict(
        context={"as_of": "2026-08-25", "researched_on": "2026-08-25", "provenance": "fixture provenance",
                 "market": {"summary": "Fixture market context.", "regime": "mixed"},
                 "symbols": {"NVDA": {"news_summary": "covered"}}},
        qm_context={"status": "DATA_BLOCKED",
                    "quant_want": {"trend": {"status": "UP", "plain_language": "fixture trend"}},
                    "source_commit": "fixture"},
        research_views_status={"state": "absent"},
    )

    def _html(self, symbols=("NVDA", "AMZN", "MSFT"), **kw):
        with mock.patch.object(config, "BOARD_LANES_ENABLED", True):
            return ad.render(_board(list(symbols), **kw), **self._DRAWER_INPUTS)

    def test_page_order_is_strip_tiles_table_event_details_drawer(self):
        html = self._html()
        anchors = ['class="status-strip"', 'class="tiles"', 'id="agreement-table"',
                   'id="pick-details"', 'id="diagnostics"']
        offsets = [html.index(a) for a in anchors]
        self.assertEqual(offsets, sorted(offsets))

    def test_removed_surfaces_are_absent(self):
        html = self._html()
        for gone in ('id="context-aware-top-5"', 'class="sticky-nav"', "VST / AMZN — ALWAYS SHOWN",
                     "CONTEXT-AWARE SHORTLIST", "QM MOVEMENT LANE</h2>"):
            self.assertNotIn(gone, html[: html.index('id="diagnostics"')])

    def test_details_render_only_for_table_names(self):
        html = self._html()
        table = html[html.index('id="agreement-table"'):html.index('id="pick-details"')]
        names_on_table = set(re.findall(r'<td class="sym">([A-Z]+)', table))
        rendered = set(re.findall(r'<div class="symbol-anchor" id="symbol-([A-Z]+)"', html))
        # pinned_picks (:576-594) always yields VST and AMZN, section or not
        # (config.PICK_PINNED_SYMBOLS, config.py:660), so VST is a ROW with no
        # panel on this fixture. Equality is therefore the wrong contract.
        self.assertTrue(rendered <= names_on_table)   # never a panel for a name that is not on the table
        self.assertIn("NVDA", rendered)               # a table name WITH a section gets its panel
        self.assertIn("VST", names_on_table)          # pinned → always a row (owner ruling 2026-07-16)
        self.assertNotIn("VST", rendered)             # … but no panel: the fixture has no VST section

    def test_relocated_content_is_appended_after_the_six_drawer_sections(self):
        html = self._html()
        drawer = html[html.index('id="diagnostics"'):]
        six = [drawer.index(s) for s in DiagnosticsDrawerTests._DRAWER_SECTIONS]
        self.assertEqual(six, sorted(six))
        for relocated in ("REGISTERED-BETS TRACKER", "Shortlist outcome scoreboard", "DATA FRESHNESS",
                          "Composite signal board"):
            self.assertGreater(drawer.index(relocated), six[-1])

    def test_every_disclaimer_survives_with_flag_off_too(self):
        # test_disclaimers_are_present_verbatim (:456) covers the DEFAULT flag
        # (True). This twin pins the rollback path with the same fixture.
        data = _board(["VST", "AAA"])
        data["composite_signals"] = [_composite_card("AAA")]
        with mock.patch.object(config, "BOARD_LANES_ENABLED", False):
            html = ad.render(data, context={"as_of": "2026-08-25", "provenance": "fixture",
                                            "market": {"summary": "Fixture."}, "symbols": {}},
                             qm_context=self._DRAWER_INPUTS["qm_context"],
                             research_views_status={"state": "absent"})
        for sentence in AuthorityWordingSurvivesLayoutTests._SENTENCES:
            with self.subTest(sentence=sentence[:48]):
                self.assertIn(sentence, html)
        self.assertIn("mission-control dashboard date INDEPENDENTLY", html)

    def test_flag_on_carries_the_three_relocated_sentences_inside_the_agreement_table(self):
        html = self._html()
        table = html[html.index('id="agreement-table"'):html.index('id="pick-details"')]
        self.assertIn("This is a fit ranking, not a prediction", table)
        self.assertIn("owner-pinned visibility — not ranked; these cards do not compete with or reorder "
                      "the Top-5 shortlist.", table)
        self.assertIn(ad._CONTEXT_LANE_DISCLAIMER, table)

    def test_lane_board_failure_keeps_every_disclaimer(self):
        data = _board(["VST", "AAA"])
        data["composite_signals"] = [_composite_card("AAA")]
        with (mock.patch.object(config, "BOARD_LANES_ENABLED", True),
              mock.patch("options_researcher.board_lanes.build_lane_board", side_effect=RuntimeError("boom"))):
            html = ad.render(data, context={"as_of": "2026-08-25", "provenance": "fixture",
                                            "market": {"summary": "Fixture."}, "symbols": {}},
                             qm_context=self._DRAWER_INPUTS["qm_context"],
                             research_views_status={"state": "absent"})
        self.assertIn("LANE BOARD FAILED — RuntimeError", html)
        for sentence in AuthorityWordingSurvivesLayoutTests._SENTENCES:
            with self.subTest(sentence=sentence[:48]):
                self.assertIn(sentence, html)

    def test_blocked_name_is_a_row_with_its_reason_and_no_panel(self):
        data = _board(["NVDA", "AMZN", "MSFT"])
        data["blocked"] = list(data.get("blocked") or []) + [{
            "symbol": "ET", "reason_code": "DATA_BLOCKED", "detail": "chain 29 sessions old",
            "last_known_date": "2026-07-27", "unexpected": False}]
        with mock.patch.object(config, "BOARD_LANES_ENABLED", True):
            html = ad.render(data, **self._DRAWER_INPUTS)
        table = html[html.index('id="agreement-table"'):html.index('id="pick-details"')]
        self.assertIn('<td class="sym">ET', table)
        self.assertIn("DATA_BLOCKED · chain 29 sessions old", table)
        self.assertNotIn('id="symbol-ET"', html)          # no section → no panel; the banner still names it
        self.assertIn("<strong>ET</strong>", html)         # _blocked_html banner (:5129)

    def test_stale_name_that_is_not_a_row_is_still_named_in_the_status_strip(self):
        symbols = ("NVDA", "AMZN", "MSFT", "PLTR", "SMCI", "CRWV", "CEG", "VST")
        data = _board(list(symbols))
        with mock.patch.object(config, "BOARD_LANES_ENABLED", True):
            html = ad.render(data, **self._DRAWER_INPUTS)
        table = html[html.index('id="agreement-table"'):html.index('id="pick-details"')]
        rows = set(re.findall(r'<td class="sym">([A-Z]+)', table))
        stale_not_rows = {str(s) for s in data["stale_symbols"]} - rows
        self.assertTrue(stale_not_rows)   # fixture guarantee: eight stale names, five slots (round-3 measured PLTR, SMCI)
        strip = html[html.index('class="status-strip"'):html.index('class="tiles"')]
        for name in stale_not_rows:
            self.assertIn(name, strip)

    def test_zero_javascript_with_flag_on(self):
        self.assertNotIn("<script", self._html().lower())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_layout.py' -k LaneBoardLayout -v`
Expected: FAIL with `ValueError: substring not found` (`class="status-strip"`).

- [ ] **Step 3: Wire `_render_result`**

Replace `:5694-5721` (from `event_css = (...)` through the end of the
`body_html = (...)` assignment) with the following. The flag-off branch is
today's code verbatim — copy it from the file, do not retype it:

```python
    if config.BOARD_LANES_ENABLED:
        from options_researcher import board_lanes as _bl

        board: LaneBoard | None
        try:
            board = _bl.build_lane_board(
                baseline_picks=qualified_picks,
                context_selection=context_selection,
                composite_cards=data.get("composite_signals"),
                # select_qm_top_picks requires a Mapping (:489); None = "lane unavailable".
                # Same guard the only other caller uses (:4281).
                qm_picks=(select_qm_top_picks(data, qm_context, include_csp_watch=True)
                          if isinstance(qm_context, Mapping) else None),
                experiment_lanes=data.get("experiment_lanes"),
                pinned=[str(r.get("symbol")) for r in pinned_records],
                blocked=data.get("blocked") or [],
                board_as_of=str(data.get("data_as_of") or ""),
            )
            board_error = None
        except Exception as exc:  # fail-visible: never blank the decision area (spec §5)
            board, board_error = None, exc.__class__.__name__
        if board is not None:
            event_line_html = _event_line_html(board, event_view, evaluation_date)
            # I1: pinned names are rows; their panels open only for fail-visible statuses.
            details_html = _pick_details_html(
                data, board, context=context, event_view=event_view, evaluation_date=evaluation_date,
                stale_symbols=stale_symbols, pinned_symbols=set(), protected_card_ids=protected_card_ids)
            decision_html = _open_slots_notice_html(data, watch_picks) + _agreement_table_html(board)
        else:
            # hero_html already carries its own open-slot block (:4200-4203): no separate notice here.
            # The two relocated authority sentences must survive the failure path too (spec §6.4).
            event_line_html, details_html = "", symbols_html
            decision_html = (f'<div class="notice bad">LANE BOARD FAILED — {_esc(str(board_error))}; '
                             f'showing the registered picks only.</div>{hero_html}{_table_footnotes_html()}')
        event_text = re.sub(r"<[^>]+>", " ", event_line_html).replace("Events ahead for the registered picks:", "").strip()
        event_text = " ".join(event_text.split())
        # Probe only fragments that are ON the flag-on page (qm_lanes_html sits in the drawer).
        event_css = (_EVENT_STYLE if 'class="event-chip"' in
                     (decision_html + event_line_html + details_html + qm_lanes_html) else "")
        body_html = (
            f"{_status_strip_html(data, context)}"
            f"{warn_html}"
            f"{_blocked_html(data.get('blocked') or [])}"
            f"{_position_tiles_html(data, event_text)}"
            f"{decision_html}"
            f"{event_line_html}"
            f"{details_html}"
            + _diagnostics_drawer_html([
                qm_lanes_html,
                _research_desk_html(data, context, context_warning, annotation_notice),
                _regime_strip_html(research_views_status, str(data.get("evaluation_date") or data_as_of)),
                _experiments_shelf_html(research_views_status),
                _quant_want_html(qm_context),
                _market_html(context),
                # relocated (spec §2.6, D9) — appended AFTER the six, text unchanged
                _freshness_html(data, context, qm_context, research_views_status, context_evidence,
                                annotation_integrity=annotation_integrity),
                age_html,
                _registered_bets_tracker_html(data),
                _composite_html(data),
                _pick_tracker_html(research_views_status),
            ])
        )
        nav_html = ""
        board_css = _BOARD_STYLE
    else:
        event_css = (_EVENT_STYLE if 'class="event-chip"' in
                     (symbols_html + hero_html + qm_lanes_html + pinned_html) else "")
        body_html = (
            ...today's :5700-5721 assembly, copied verbatim...
        )
        nav_html = _sticky_nav_html(body_html, symbol_names)
        board_css = ""
```

At `:5726` change `f"<style>{_STYLE}{event_css}</style></head><body>"` to
`f"<style>{_STYLE}{board_css}{event_css}</style></head><body>"` (flag off:
`board_css == ""`, so the bytes are unchanged), and at `:5737` replace
`f"{_sticky_nav_html(body_html, symbol_names)}"` with `f"{nav_html}"`. `symbols_html`, `hero_html`, `qm_lanes_html`, `pinned_html`,
`age_html`, `warn_html`, `qualified_picks`, `watch_picks`, `context_selection`,
`pinned_records`, `stale_symbols`, `pinned_symbols`, `protected_card_ids`,
`evaluation_date` (hoisted in Task 5), `annotation_notice`,
`research_views_status`, `context_evidence`, `annotation_integrity`,
`data_as_of`, `qm_context` are all in scope at this point (reviewer-verified
in both rounds). The six drawer calls above are today's `:5712-5719` calls,
unchanged; the five relocated items follow them. Under the flag the page still
builds `symbols_html` for all names (needed by the failure fallback) and then
re-renders the table names inside `_pick_details_html` — a known double render
of ~700 KB of string work; say so in the PR body next to the
`build_experiment_lanes` cost (~3.3 s, round-1 measured).

Add a NEW module constant directly after `_STYLE` (NOT inside it — see Files
above), colours from the existing variables only:

```python
_BOARD_STYLE = """
.status-strip{display:flex;flex-wrap:wrap;gap:16px;font-size:13px;padding:6px 0 10px;border-bottom:1px solid var(--line)}
.strip-item{white-space:nowrap}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;vertical-align:middle}
.dot.good{background:var(--good)}.dot.warn{background:var(--watch)}.dot.crit{background:var(--bad)}
.tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:12px 0}
.tile{border:1px solid var(--line);border-radius:8px;padding:10px 12px}.tile.bad{border-color:var(--bad)}
.tile .k{font-size:11px;text-transform:uppercase;letter-spacing:.06em;opacity:.7}.tile .v{font-size:20px;font-weight:600}.tile .d{font-size:12px;opacity:.8}
.chip{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:1px 8px;font-size:12px;margin:1px 2px 1px 0}
.agreement-table{width:100%;border-collapse:collapse;font-size:13px}.agreement-table th{font-size:11px;text-transform:uppercase;letter-spacing:.05em;text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}
.agreement-table th.group{text-align:center;border-left:1px solid var(--line)}.agreement-table .th-sub{font-weight:400;text-transform:none;letter-spacing:0;opacity:.75}
.agreement-table td{padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top;font-variant-numeric:tabular-nums}
.agreement-table td.sym{font-weight:700}.agreement-table td.lane-off{background:var(--surface-soft)}.agreement-table .econ{font-size:12px;opacity:.8}
.table-foot{font-size:12px;opacity:.8;margin:8px 0 0}
.agreement-table .blocked{color:var(--bad)}.agreement-table .muted{opacity:.6}
.chip.on{border-color:var(--good)}.chip.warn{border-color:var(--watch)}.chip.veto{border-color:var(--bad)}
.agree-cell .bar{display:inline-block;height:8px;border-radius:4px;background:var(--good);vertical-align:middle;margin-right:6px}.agree{font-weight:700}
.event-line{margin:10px 0;font-size:13px}.event-line-label{margin-right:8px;opacity:.75}
"""
```

Every `var(--…)` above exists in `_STYLE`'s `:root` (`:2316-2341`): `--line`,
`--good`, `--watch`, `--bad`, `--surface-soft`. `_STYLE` has no base `.chip`
rule today (only `.meta-chip`, `.evidence-chip`, `.event-chip`), so the base
`.chip` rule above is REQUIRED — without it the `.chip.on/.warn/.veto` border
colours paint nothing. Do not introduce new colour tokens and do not copy the
mockup's palette (`--surface-2`, `--seq4`, `--ink-2` … do not exist here).

- [ ] **Step 4: Run the layout tests, then the whole suite**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_layout.py' -v`
Expected: `LaneBoardLayoutTests` and `LegacyByteIdentityTests` PASS. Several
PRE-EXISTING layout tests now FAIL because they pin the old order — that is
Task 7's job; list them in the commit body.
Run: `uv run python -m unittest discover -s tests 2>&1 | tail -5`
Expected: failures only in `test_attractiveness_layout.py`,
`test_attractiveness_dashboard.py`, `test_event_awareness.py` and
`test_attractiveness_v3.py` (its `:282` counts `hero-card` divs, a flag-off
surface — Task 7 legacy-wraps it). `tests/test_experiments_baseline.py` was
re-pinned in Task 4 and must be GREEN here. Any other file failing is a
regression — STOP and report.

- [ ] **Step 5: Commit**

```bash
git add options_researcher/attractiveness_dashboard.py tests/test_attractiveness_layout.py
git commit -m "feat(board): wire the lane-board page order behind BOARD_LANES_ENABLED (legacy page byte-identical when off)"
```

---

### Task 7 (WP-G): Re-pin the contracts (layout, dashboard, event-chip)

**Files:**
- Modify: `tests/test_attractiveness_layout.py`, `tests/test_attractiveness_dashboard.py`, `tests/test_event_awareness.py`

**Interfaces:** none new. Rule for every re-pin, recorded in a one-line
comment above the test: **(a)** the test asserts the CONTENT of a section
(what a fact says) → keep the assertion and render with the flag OFF using the
helper below, because the section still renders inside the drawer with the
same text; **(b)** the test asserts a spec §2 POSITION invariant → rewrite it
against the new anchors with the same intent; **(c)** the test asserts a
surface that no longer exists on the flag-on page → wrap with the flag off.
Never delete a test.

- [ ] **Step 1: Add the flag-off helper to the three test files**

`import contextlib` goes in each file's TOP import block, in isort order — a
mid-file import fails ruff E402: `tests/test_attractiveness_layout.py:10-19`
(before `import re`), `tests/test_attractiveness_dashboard.py:2-7` (before
`import json`), `tests/test_event_awareness.py:5-13` (before `import json`;
that file already imports `mock`). Then, once per file:

```python
@contextlib.contextmanager
def _legacy_layout():
    """Render the pre-brief-39 page: the flag-off path is byte-identical to the
    legacy snapshot (tests/test_attractiveness_layout.py LegacyByteIdentityTests)."""
    with mock.patch.object(config, "BOARD_LANES_ENABLED", False):
        yield
```

- [ ] **Step 2: Enumerate the failures (paste the list into the PR body)**

Run each of the three files and collect `FAIL:`/`ERROR:` lines. Expected
members (Repo-verified anchors; the executor confirms the exact set):

Four standing rules for every re-pin: **(1)** re-pinning a hard-coded digest
or golden hash is never an acceptable repair — legacy-wrap the test instead;
**(2)** a slice that becomes EMPTY under the flag (its two anchors invert) is a
silently vacuous test, so every `html[html.index(A):html.index(B)]` slice in a
re-pinned test must be checked for anchor order, not just for passing;
**(3)** legacy-wrap ONLY a test the executor has OBSERVED to fail under the
flag — a passing test stays flag-on (rounds 3–4 measured `:286`, `:296`,
`:337`, `:364`, `:424` and dashboard `:2034` passing; do not touch them; where
rule (3) and an entry below disagree, rule (3) wins and the entry is stale);
**(4)** a
fourth disposition **(d) re-point** exists for tests that assert panel CONTENT
for a symbol that is no longer a table row: wrap the render in
`mock.patch.object(config, "PICK_PINNED_SYMBOLS", [<that symbol>])` so the
symbol is a row and its panel renders (closed under I1, but present in the
HTML), and keep every assertion flag-ON. Two caveats: pinning also feeds
`pinned_picks(data)` → `protected_card_ids` (`:5540-5543`), which sets
`protected_indexes` inside `_group_html` — measured harmless for all 18
enumerated (d) tests, but a test asserting card ORDER inside a group must be
re-checked; and (d) presumes the symbol HAS a section — a pinned symbol
without one gets a row and no panel, so a panel-content assertion still
fails (use a fixture with a section). Root cause, stated once: under the
flag a section whose symbol is on no lane, not pinned and not blocked renders
no panel (spec §2.5/D4). Fail-visible contracts (`FailClosedFeatureTests`,
`SchwabFreshnessPageDateTests`) MUST stay flag-on via (d) — never (a)/(c).

`tests/test_attractiveness_layout.py` —
(b) `test_tracker_renders_before_the_shortlist_with_positions_kicker` (`:165`)
→ under the flag the tiles precede the agreement table; rewrite the two
`assertLess` calls against `class="tiles"` / `id="agreement-table"`, keep the
two `assertIn`s.
(a) the five `PositionsAndRiskFirstTests` that slice
`html[html.index("POSITIONS &amp; RISK"):html.index("Rule-based top 5")]`
(`:179`, `:191`, `:200`, `:208`, `:220`) → legacy wrap. Under the flag
"POSITIONS &amp; RISK" moves into the drawer, AFTER the h2, so the slice is
empty: four fail and `:200` (`assertNotIn`) passes vacuously — wrap all five.
(b) `SymbolPanelCollapseTests.test_clean_panels_are_closed_except_owner_pinned_symbols`
(`:277`) — the only one of the class's four tests that fails (round 3
measured; `:286`, `:296` and `:304` pass and stay untouched). Two things
change under the flag: panels render in BOARD-ROW order (measured
`MSFT, NVDA, VST` on this fixture), not `data["symbols"]` order
(`VST, NVDA, MSFT`), so the slice at `:283` inverts to empty; and under I1 the
pinned VST panel is CLOSED on a
fresh board (zero `open` panels). Rewrite: `assertEqual(len(panels), 3)`,
`assertEqual(sum(1 for p in panels if p), 0)` with a comment citing I1, and
locate a panel with the helper below; add a legacy-wrapped twin keeping the
old "VST only is open" assertion for the flag-off page. Module-level helper:

```python
def _panel_slice(html: str, symbol: str) -> str:
    """One symbol's panel: from its anchor to the next symbol anchor, the drawer, or the end."""
    start = html.index(f'id="symbol-{symbol}"')
    ends = [p for p in (html.find('id="symbol-', start + 1), html.find('id="diagnostics"', start)) if p != -1]
    return html[start:min(ends)] if ends else html[start:]
```

(c) `test_nav_links_every_present_section_and_symbol` (`:314`),
`test_nav_never_links_a_section_that_is_not_on_the_page` (`:326`) → legacy wrap
(the sticky nav is removed under the flag, D2/§2).
(b) `test_scoreboard_and_pinned_strip_stay_in_the_main_flow` (`:416`) →
REWRITE per D9/§2: the scoreboard is inside `id="diagnostics"`, and the pinned
names appear as `<td class="sym">VST` / `AMZN` rows above it.
`test_symbol_panels_precede_the_drawer` (`:424`) PASSES flag-on unchanged —
leave it (rule 3); tightening it to `id="pick-details"` before
`id="diagnostics"` is not required and must not be done as a "fix".
`test_disclaimers_are_present_verbatim` (`:456`) → must pass UNCHANGED
(Global Constraints); if it fails, the agreement table is missing a sentence —
fix the renderer, never the test.
(c) `EmptySlotConsolidationTests` — round 4 measured four of the five as
`ERROR` under the flag: `:88`, `:102`, `:111`, `:130` → legacy wrap (they
locate the hero grid, a removed surface); `:122`
(`test_blocked_qm_slots_collapse_into_one_block`) PASSES — leave it. Add one
flag-on twin asserting the consolidated notice text (`"of 5 slots open"`)
appears exactly once above `id="agreement-table"`.

`tests/test_attractiveness_dashboard.py` — **45** broken tests in rev 4's own
flag-on build (round 3 measured 44 before I1; the 45th is caused by I1). All
are listed here.
(b) `SymbolPanelStatusTests.test_render_uses_details_and_fail_visible_open_attribute`
(`:874`) — I1 consequence, NOT a (d) case: disposition (d) is measured NOT to
work here because pinning is the cause, not the cure — this is the one
fail-visible contract where the contract under test IS the pinned open-state.
The assertions inside the `PICK_PINNED_SYMBOLS=[]` patch (`:889-892`) pass
unchanged and stay flag-on. **Keep `:893`**
(`data["symbols"][0]["features_stale"] = False`) — without that reset the
panel is STALE-open and both new assertions are wrong: the flag-on
`assertNotIn` fails and the legacy twin passes vacuously (round 5 measured).
Replace only `:894` with the flag-on contract
`self.assertNotIn('<details class="panel symbol-panel" open>', ad.render(data))`
plus a `_legacy_layout()`-wrapped twin keeping today's assertion, each with a
one-line comment citing I1 (round 5 measured: `SymbolPanelStatusTests` 4 tests
OK on both branches).
(c) `test_flag_off_matches_post_brief26_golden_bytes` (`:2239`) asserts a
hard-coded SHA-256 (`:2263-2266`) on a default-flag render → add
`mock.patch.object(config, "BOARD_LANES_ENABLED", False)` beside the existing
`CONTEXT_LANE_ENABLED` patch at `:2245`. NEVER re-pin the digest.
(a) every test slicing `html[html.index("DATA FRESHNESS"):html.index("Rule-based top 5")]`
(`:3089`, `:3097`, `:3130`, `:3162`, `:3272`, `:3291`, `:3304`) → legacy wrap
(the freshness block's TEXT is unchanged; under the flag it sits after the h2
so the slice inverts to empty — vacuous, not passing).
(a)/(c) the order pins at `:2061`, `:2112`, `:2145`, `:2152`, `:2155`,
`:2171`, `:2632-2633`, `:3067-3075`, `:3253-3264`, `:3317`, `:3341` → legacy
wrap unless the assertion is a §2 invariant (`:2034`'s test PASSES — leave it).
(b) tracker-before-shortlist at `:3191-3193` → becomes tiles-before-table
under the flag: rewrite.
(d) panel-CONTENT tests whose symbol is no longer a row — pin the fixture's
symbol and keep every assertion flag-on: `RenderTests` `:291`, `:301`, `:305`,
`:310`, `:338`; `StrategySectionRankingTests` `:1240` (its `ValueError` is a
missing panel anchor); `BlockedSectionsTests` `:1360` (the success-row chip is
in the panel; the blocked row is now ALSO an agreement-table row — assert both);
`HypothesisEvidencePanelTests` `:1393`; `V2RenderTests` `:1803`, `:1825`,
`:1831`, `:1841`; `SchwabFreshnessPageDateTests` `:3551`, `:3561` (fail-visible:
"no verified 15:45 spot …" lives in the STALE NVDA panel, which is force-open
once NVDA is a row); `FailClosedFeatureTests` `:3691`, `:3698`, `:3705`,
`:3720` (fail-visible: `_fresh_section()`'s NVDA is not a pick on those
fixtures — pin it).
(c) surfaces removed by D4/D12 — legacy wrap AND add a flag-on twin where the
contract moved: `PinnedPicksTests` `:1307` ("no eligible liquid card" was the
pinned STRIP; twin asserts the pinned ROW text "not in the registered top 5");
`V2RenderTests` `:1725`, `:1733` (hero cards); `ContextLaneRenderTests`
`:2332`, `:2358`, `:2642`, `:2660` (context CARDS; the membership/tracker-arm
assertions in `:2358` are computed outside the flag — keep them, wrap only the
HTML lookups) and `:2687` (twin: the agreement table header shows
`FAILED:RuntimeError` for the context column — `_col`-style substring on the
`<th>` — and the loud-failure text is in `board.notes`).
(b) `LoadContextTests.test_rendered_context_freshness_has_all_evidence_derived_states`
(`:1591`) — its `chip()` helper (`:1600-1603`) anchors on the FIRST
`html.index("Research context")`; flag-on that is the drawer heading
"Research context and coverage", which now precedes the relocated freshness
chip (measured offsets 26,209 vs 30,053). Re-anchoring on `id="diagnostics"`
does NOT fix it (measured). Change `start = html.index("Research context")`
to `start = html.rindex("Research context")` and keep every assertion
flag-on; the chip text is unchanged.

`tests/test_attractiveness_v3.py` —
(c) `test_partial_shortlist_keeps_configured_visible_slots_in_each_list`
(`:278-288`) counts `<div class="hero-card '` == 3 and asserts
`Picks 2–{PICK_TOP_N}` → legacy wrap (under the flag only the open-slot notice
emits `hero-card` markup). `:262-267` and `:269-276` keep "TOP 5 PICKS TODAY"
/ "This is an intentional open slot" because the eyebrow phrase and the notice
survive; if either fails, the renderer dropped text — fix the renderer.

Any failure NOT in this list gets the same (a)/(b)/(c)/(d) treatment, is never
deleted, and is listed in the PR body with its disposition and a one-line
reason — that is a disposition rule, not a design delegation.

`tests/test_event_awareness.py` — `test_populated_hero_lane_context_and_pinned_surfaces_share_exact_chip_list` (`:311`) and possibly `test_pure_render_all_card_surfaces_and_failure_notice` (`:215`) → Step 3.

- [ ] **Step 3: Lift the event fixture, then re-pin the chip contract (D11)**

First, a no-behaviour-change commit: move `card()` (`:313-338`), `symbols`
(`:340`), `data` (`:341-368`), `view` (`:374-391`) and `chips()` (`:393-394`)
out of the test at `:311` into module-level helpers, and make the old test
call them. Leave `grades_before` / `picks_before` / `sections_before`
(`:369-373`) and `card_fragment` (`:396-413`) inside the old test — they are
its own assertions' scaffolding, not fixture:

```python
def _populated_card(symbol):
    ...the body of card() at :313-337, unchanged...


def _populated_data():
    symbols = ["NVDA", "AMD", "AVGO"]
    return {...the dict at :341-368, using _populated_card(symbol)...}


def _populated_view(calendar):
    return {...the dict at :374-391 with "calendar": calendar...}


def _chips(fragment):
    return re.findall(r'<span class="event-chip">(.*?)</span>', fragment)
```

Run the file: 16 tests still OK. Commit
(`test(events): lift the populated fixture to module level (no behaviour change)`).

Then replace `test_populated_hero_lane_context_and_pinned_surfaces_share_exact_chip_list`
with two tests that keep its intent under D11 (each registered pick's chips
appear once on the line and match that pick's own panel; no cross-panel
equality is asserted because panels legitimately differ by symbol/expiry):

```python
    def test_event_line_is_the_sorted_union_of_the_registered_picks_chips_printed_once(self):
        from options_researcher import board_lanes as bl
        data = _populated_data()
        view = _populated_view(self.calendar)
        picks = ad.select_top_picks(data)
        board = bl.build_lane_board(
            baseline_picks=picks, context_selection={"state": "DISABLED", "rows": [], "error": None},
            composite_cards=data["composite_signals"], qm_picks=[], experiment_lanes={},
            pinned=(), blocked=[], cap=config.PICK_TOP_N, board_as_of=data["data_as_of"])
        line = ad._event_line_html(board, view, data["evaluation_date"])
        expected = set()
        for pick in picks:
            expected |= set(_chips(ad._event_chips_html(pick["card"], pick["symbol"], data["evaluation_date"], view)))
        self.assertEqual(_chips(line), sorted(expected))
        for chip in expected:
            self.assertEqual(line.count(chip), 1)

    def test_each_registered_pick_line_entry_appears_in_that_picks_own_panel(self):
        data = _populated_data()
        view = _populated_view(self.calendar)
        with (
            mock.patch.object(config, "BOARD_LANES_ENABLED", True),
            mock.patch.object(config, "CONTEXT_LANE_ENABLED", True),
            mock.patch.object(config, "PICK_PINNED_SYMBOLS", ["NVDA"]),   # (:417) — the fixture has no VST/AMZN
        ):
            html = ad.render(data, event_view=view)   # same entry the old test uses at :419
        line = html[html.index('class="event-line"'):]
        line = line[: line.index("</div>") + 6]
        for pick in ad.select_top_picks(data):
            # Panels nest <details> three deep (:3340, :3296); slice to the next
            # symbol anchor or the drawer, never to the first "</details>".
            start = html.index(f'id="symbol-{pick["symbol"]}"')
            ends = [p for p in (html.find('id="symbol-', start + 1), html.find('id="diagnostics"', start)) if p != -1]
            panel = html[start:min(ends)] if ends else html[start:]
            for chip in _chips(line):
                self.assertIn(chip, panel)
```

Executor note: the old test's render is `:419`
(`html = ad.render(data, event_view=view)`) inside the two `mock.patch.object`
guards at `:415-418`; both new tests keep those two patches — without
`PICK_PINNED_SYMBOLS=["NVDA"]` the default `["VST","AMZN"]` (neither in the
fixture) would add two empty pinned rows. Keep
`test_pure_render_all_card_surfaces_and_failure_notice` (`:215`) green by
wrapping it in `_legacy_layout()` if it asserts hero/pinned surfaces.

- [ ] **Step 4: Run the three files, then the whole suite**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_*.py' 2>&1 | tail -3 && uv run python -m unittest discover -s tests -p 'test_event_awareness.py' 2>&1 | tail -3`
Expected: OK, OK.
Run: `uv run python -m unittest discover -s tests 2>&1 | tail -3` → `OK` (skips allowed).

- [ ] **Step 5: Commit**

```bash
git add tests/test_attractiveness_layout.py tests/test_attractiveness_dashboard.py tests/test_event_awareness.py
git commit -m "test(board): re-pin layout, dashboard and event-chip contracts to the lane-board page (spec §7, D11)"
```

---

### Task 8 (WP-H): Parity proof, visible-length acceptance, gates, PR

**Files:**
- Test: `tests/test_attractiveness_layout.py`

- [ ] **Step 1: Write the parity and acceptance tests**

```python
def _visible_html(html: str) -> str:
    """D10's measure = what the reader sees without clicking: drop every CLOSED
    symbol panel and the (closed) diagnostics drawer, nesting-aware. A
    force-open panel (STALE/BLOCKED/SKIPPED) stays in — it IS visible. The
    acceptance fixture below is fresh, so nothing is force-open and the
    targets are meaningful; Friday's force-open count is REPORTED (Step 4)."""
    openers = ('<details class="panel symbol-panel">', '<details class="panel diagnostics-drawer"')
    out, i = [], 0
    while True:
        starts = [p for p in (html.find(o, i) for o in openers) if p != -1]
        if not starts:
            out.append(html[i:])
            return "".join(out)
        s = min(starts)
        out.append(html[i:s])
        depth, p = 0, s
        while True:
            o = html.find("<details", p + 1)
            c = html.find("</details>", p + 1)
            if c == -1:
                p = len(html)
                break
            if o != -1 and o < c:
                depth, p = depth + 1, o
            elif depth == 0:
                p = c + len("</details>")
                break
            else:
                depth, p = depth - 1, c
        i = p


class LaneBoardParityAndSizeTests(unittest.TestCase):
    def test_selection_snapshot_and_source_row_hashes_are_identical_flag_on_and_off(self):
        data = _board(["NVDA", "AMZN", "MSFT"])
        with mock.patch.object(config, "BOARD_LANES_ENABLED", False):
            off = ad._render_result(data)
        with mock.patch.object(config, "BOARD_LANES_ENABLED", True):
            on = ad._render_result(data)
        self.assertEqual(on.selection_snapshot, off.selection_snapshot)
        self.assertEqual(on.render_source_row_hashes, off.render_source_row_hashes)

    def test_visible_page_meets_the_d10_targets_on_a_fresh_board(self):
        # FRESH board (same construction as SymbolPanelCollapseTests._data, :254-275,
        # lifted to a module-level `_fresh_board(symbols)` in a no-behaviour commit):
        # nothing is STALE, so no panel is force-open, and under I1 the pinned
        # VST/AMZN panels are closed too. The measure can therefore FAIL if the
        # flag-on page leaves too much in the main flow — which is what D10 rules on.
        symbols = ["NVDA", "AMZN", "MSFT", "PLTR", "SMCI", "CRWV", "CEG", "VST"]
        with mock.patch.object(config, "BOARD_LANES_ENABLED", True):
            html = ad.render(_fresh_board(symbols), **LaneBoardLayoutTests._DRAWER_INPUTS)
        self.assertEqual(html.count('<details class="panel symbol-panel" open>'), 0)   # I1 + fresh
        self.assertGreaterEqual(html.count('<details class="panel symbol-panel">'), 5)  # the table names' panels exist
        visible = _visible_html(html)
        # Measured (round 4): new page 2 <h2> / 0 <summary>; the PRE-redesign page on the
        # same fixture scores 8 / 23 — so "<= 8" would not discriminate. D10's ceiling is 8;
        # the redesign's own bar is 4, and the legacy page must FAIL the summary leg.
        self.assertLessEqual(visible.count("<h2"), 4)
        self.assertLessEqual(visible.count("<summary"), 20)
        self.assertNotIn('class="panel symbol-panel"', visible)
        with mock.patch.object(config, "BOARD_LANES_ENABLED", False):
            legacy = ad.render(_fresh_board(symbols), **LaneBoardLayoutTests._DRAWER_INPUTS)
        self.assertGreater(_visible_html(legacy).count("<summary"), 20)   # the measure rejects today's page

    def test_force_open_panels_count_as_visible(self):
        # A STALE table name keeps its fail-visible open panel, and the measure counts it.
        with mock.patch.object(config, "BOARD_LANES_ENABLED", True):
            html = ad.render(_board(["NVDA", "AMZN", "MSFT"]), **LaneBoardLayoutTests._DRAWER_INPUTS)
        self.assertGreater(html.count('<details class="panel symbol-panel" open>'), 0)   # layout fixture is STALE
        self.assertIn('class="panel symbol-panel" open', _visible_html(html))
```

`_render_result(data)` is called with the same defaults `render()` uses
(`:5765-5780`; read it and pass the same keyword defaults if any are required).

- [ ] **Step 2: Run tests**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_layout.py' -k LaneBoardParity -v`
Expected: PASS.

- [ ] **Step 3: Full gates**

```bash
uv run python -m unittest discover -s tests        # exit 0
uv run ruff check . && uv run pyright              # both clean (board_lanes.py is now in pyrightconfig include)
```

If `ruff check .` reports `I001` (or `E501`, line length 100) on a line this
brief supplies, the brief is wrong — apply `ruff check --diff`'s suggestion and
note it in the PR body; do not reorder names.

- [ ] **Step 4: Manual proof on Friday's data (orchestrator/owner runs it; include the commands and paste the numbers into the PR body)**

```bash
ATTRACTIVENESS_INPUT_ROOT=/Users/carsynstephenson/options-validator-ops uv run python -m options_researcher.attractiveness_dashboard
wc -c .tmp/dashboard/attractiveness.html                          # REPORTED (D10), not a target
grep -c "<script" .tmp/dashboard/attractiveness.html              # 0
PYTHONPATH=tests uv run python -c "from pathlib import Path; from test_attractiveness_layout import _visible_html; h=Path('.tmp/dashboard/attractiveness.html').read_text(); v=_visible_html(h); c=h.replace(' open>', '>'); vc=_visible_html(c); print('visible h2', v.count('<h2'), 'summaries', v.count('<summary'), '| all-closed counterfactual h2', vc.count('<h2'), 'summaries', vc.count('<summary'), '| force-open panels', h.count('<details class=\"panel symbol-panel\" open>'))"   # REPORT all five numbers; the D10 targets bind the fresh-fixture TEST, the Friday numbers are evidence
python3 -c "import json; d=json.load(open('.tmp/dashboard/picks_snapshot.json')); print([c['symbol'] for c in d['frozen_baseline']['candidates']], d['source_rows_sha256'])"
```

The snapshot symbol list and `source_rows_sha256` must equal the pre-change
values for the same session (record both in the PR body). These commands
overwrite the LOCAL `.tmp/dashboard/attractiveness.html` and
`picks_snapshot.json` of the checkout they run in (they read the ops cache,
write locally) — expected and harmless.

- [ ] **Step 5: Commit and open the DRAFT PR**

```bash
git add tests/test_attractiveness_layout.py
git commit -m "test(board): parity (flag on/off) and D10 visible-length acceptance tests"
git push -u origin <branch>
gh pr create --draft --title "Attractiveness board redesign — agreement table (brief 39)" --body-file <body.md>
```

PR body must contain: the spec path and D1–D12; the list of re-pinned tests
with the (a)/(b)/(c) decision for each; the Friday-data numbers (bytes
reported, visible h2, visible summaries, force-open panel count with each
panel's status label, snapshot symbol list and `source_rows_sha256`
before/after); the double-render and `build_experiment_lanes` cost note; the
docstring amendment at `:3775`; the source-hash consequence below; and the
standard authority paragraph (draft; no ready/merge/sync/ledger).

---

## Acceptance / verification (whole brief)

```bash
uv run python -m unittest discover -s tests        # offline; exit code is the verdict
uv run ruff check . && uv run pyright              # both exit 0
ATTRACTIVENESS_INPUT_ROOT=~/options-validator-ops uv run python -m options_researcher.attractiveness_dashboard
```

Plus: owner ruling D13 recorded in the spec BEFORE dispatch (and I1 not
vetoed); `LegacyByteIdentityTests` green (flag off == pre-change snapshot);
`LaneBoardParityAndSizeTests` green; `tests/test_board_lanes.py` 16 tests
green; the three re-pinned files green with no deleted test; zero `<script`;
every disclaimer verbatim; six drawer sections in order; the layout suite
still runs in well under a second (no cache reads on injected fixtures).

**Byte figure:** this brief quotes the round-1 reviewer's measurement of the
2026-09-04 build, 782,263 bytes. Spec §1 says "771 KB" and spec §8 says
"782 KB" for the same build — the spec contradicts itself; the measured
782,263 bytes is the figure to compare against, and spec §1 should be
corrected in a later editorial pass (not by this brief).

**Operational consequence to state in the PR body (owner-only to act on):**
landing changes `diagnostic_source_hash()` — `research/hashing.py:132` walks
`options_researcher/` and `tools/` as directories, so the new
`board_lanes.py`, the edited `attractiveness_dashboard.py` and `config.py` all
move it. `h7_data_gate.py:748` rejects a receipt whose `source_hash` no longer
matches, so H7 source-health and data-gate receipts written before the merge
are invalidated and must be re-run (source health → data gate → watcher,
CLAUDE.md order) before the next entry window. This is a different gate from
`FEASIBILITY_SOURCE_PATHS`, which is untouched.

Every constraint above is labelled; anything Codex finds that contradicts a
citation is a STOP-and-report, not a workaround. The implementation PR starts
as a GitHub draft; the executor may not make it ready, merge, deploy, sync
`~/options-validator-ops` or `~/options-validator-research`, or touch
`ledger/`. Green checks are review evidence for the owner, not landing
authority. First ritual after landing may raise the pick tracker's
`IMMUTABLE_HISTORY_CONFLICT` for an already-recorded session (board bytes
change); that is expected, fail-soft, and owner-only to resolve.
