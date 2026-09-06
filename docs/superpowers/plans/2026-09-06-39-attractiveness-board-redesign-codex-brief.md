# Codex brief 39 — Attractiveness board redesign (agreement table) — implementation plan

**Date:** 2026-09-06
**Author:** Claude (orchestrating session; brainstorming + spec with the owner 2026-09-06)
**Executor:** Codex (Sol, high reasoning — as briefs 07/37/38; owner may substitute at dispatch)
**Status:** DRAFT — pending independent adversarial review before hand-off
**Provenance:** file:line constraints are Repo-verified against origin/main
@f83428d unless a sentence carries its own label. Sentences labelled
**Inference** are the author's reading of the code, not a file fact.
**Spec (approved by the owner 2026-09-06, read it first):**
`docs/superpowers/specs/2026-09-06-attractiveness-board-redesign-design.md`
with the approved first-screen mockup
`docs/superpowers/specs/assets/2026-09-06-board-redesign-option-a-v2.html`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the attractiveness board's first screen with one agreement
table (names × lanes, favourable-only count), render per-name details only
for names on that table, and move everything descriptive into the existing
drawer — cutting the page from ~19 screens to under 5 without changing any
ranking, grade, snapshot, or authority.

**Architecture:** A new pure module `options_researcher/board_lanes.py` turns
the already-assembled board data (baseline picks, context rows, composite
cards, QM picks, experiment lanes) into a `LaneBoard` value. The renderer in
`options_researcher/attractiveness_dashboard.py` gains a status strip, position
tiles, the agreement table, one event line and "details for these names only",
gated by `config.BOARD_LANES_ENABLED`; when the flag is `False` the page is
byte-identical to today. Experiment lanes are computed in the gather step from
cached data (injectable for tests).

**Tech Stack:** Python 3.12, `unittest` (offline, no network), ruff, pyright,
zero-JavaScript static HTML (native `<details>`, inline SVG only).

## Why this exists (plain language)

The board is honest but ~19 screens long (771 KB, 30 headings, 362 fold-outs
on 2026-09-04). The owner wants it "less long and easier to read", with the
top picks always on top, a visible mark when several lanes share a pick, and
only each lane's five best (spec §1, decisions D1–D9). This brief implements
that spec exactly. It closes the visual half of brief 37's DR-8b (event-chip
repetition) by renegotiating the chip-parity contract (spec §7).

## Scope

**IN:** `config.py` (two new display constants, provenance-labelled),
`options_researcher/board_lanes.py` (new), `options_researcher/attractiveness_dashboard.py`
(gather/assemble injection, new section builders, `render` wiring, symbol-panel
extraction), and tests: new `tests/test_board_lanes.py`,
`tests/test_attractiveness_layout.py`, `tests/test_attractiveness_dashboard.py`,
`tests/test_event_awareness.py`.

**OUT (hard):**
- No change to `options_researcher/display_rank.py`, `options_researcher/attractiveness.py`,
  `options_researcher/context_lane.py`, `options_researcher/composite_signals.py`,
  `options_researcher/qm_signals.py`, `options_researcher/qm_dashboard.py`,
  `options_researcher/exp_*.py`, `options_researcher/experiments_dashboard.py`,
  `options_researcher/pick_tracker.py`, or any `grades` input of any card.
  Ranking, grades, the picks snapshot (`picks_snapshot/v1`, `_selection_snapshot`
  at `attractiveness_dashboard.py:5384`), `source_row_hashes`, and the HTML
  digest comment are untouched (spec §6).
- No edit to any member of `FEASIBILITY_SOURCE_PATHS`
  (`options_researcher/h7_schwab_window_registration.py:143-194`; brief 37
  verified the four IN files above are outside it; `board_lanes.py` is new and
  imports nothing from H7 modules).
- No JavaScript (`tests/test_attractiveness_layout.py:497`), no external
  assets, no network or provider call, no ledger write, no registration, no
  authority flip, no paper-book mutation, no plist/launchd change, no change
  to Mission Control (`options_researcher/dashboard.py`), no change to the
  standalone experiments page or the `EXP_*` flags.
- No new numeric constant with owner provenance: the cap reuses
  `config.PICK_TOP_N` (`config.py:650`).
- DR-5 / DR-5b stay held (brief 37 "Held" section); nothing here computes
  rv21 or changes a badge.

## Global Constraints

- Every disclaimer string asserted by `tests/test_attractiveness_layout.py:456`
  (`test_disclaimers_are_present_verbatim`) stays verbatim, including the
  footer sentence "This page and the mission-control dashboard date
  INDEPENDENTLY" (`attractiveness_dashboard.py:5740-5745`).
- The six drawer sections keep their order (`test_drawer_is_closed_and_holds_the_six_diagnostic_sections`,
  `tests/test_attractiveness_layout.py:405`; `_DRAWER_SECTIONS` at `:375`);
  relocated content is APPENDED after them.
- `config.BOARD_LANES_ENABLED = False` must reproduce today's HTML
  byte-for-byte on the layout fixture (rollback path, spec §4).
- Owner-pinned names (`pinned_picks(data)`, used at `:4662-4668`) are always
  rows.
- Fail-visible: every lane keeps its column with its state; a failed lane is
  excluded from the agreement denominator (spec §5).
- Commit after every green task; never squash the task history before the
  PR; the PR starts as a GitHub draft.

## File Structure

| File | Responsibility |
|---|---|
| `config.py` | `BOARD_LANES_ENABLED`, `BOARD_FAVOURABLE_LANES`, `BOARD_CAUTION_LANES` (display-only, LLM-proposed 2026-09-06 labels) |
| `options_researcher/board_lanes.py` (new, pure) | dataclasses `LaneMember`, `LaneColumn`, `BoardRow`, `LaneBoard`; `build_lane_board(...)`; lane-specific adapters `lane_from_baseline`, `lane_from_context`, `lane_from_composite`, `lane_from_qm`, `lane_from_experiment`; no I/O |
| `options_researcher/attractiveness_dashboard.py` | gather: `experiment_lanes` computed + injectable; render: `_status_strip_html`, `_position_tiles_html`, `_agreement_table_html`, `_event_line_html`, `_pick_details_html`, extracted `_symbol_panel_html`; `render` order behind the flag |
| `tests/test_board_lanes.py` (new) | unit tests for the pure module |
| `tests/test_attractiveness_layout.py` | layout contract re-pinned to spec §2 (flag on) + legacy byte-identity (flag off) |
| `tests/test_attractiveness_dashboard.py` | render tests for the new builders; existing tests updated only where they assert removed surfaces |
| `tests/test_event_awareness.py` | chip-parity contract re-pinned to the new surfaces (spec §7) |

Existing data shapes the module consumes (Repo-verified):

- baseline pick (`select_top_picks(data)`, `attractiveness_dashboard.py:438`):
  `{"symbol", "lane", "status" ("ELIGIBLE"|"WATCH"|…), "score", "card": {...}}`
  where `card` has `headline`, `strike`, `expiry`, `dte`, `cost`, `grades`,
  `risk: {"max_loss", "capital_required", "max_profit", "breakeven"}` and
  `top3_snapshot.candidate_id`.
- context row (`_context_lane_selection(data)["rows"]`, `:4450`; built by
  `options_researcher/context_lane.py:112-124`): `{"symbol", "lane",
  "candidate_id", "score", "context_max_asof", "board_as_of", "context_term",
  "context_reason", "aligned_angles", "pick"}`; the selection dict carries
  `state` in `{"READY","DISABLED","FAILED"}` and `error`.
- composite card (`data["composite_signals"]`, built by
  `options_researcher/composite_signals.py:619-624`): `{"symbol", "asof",
  "max_asof", "grade", "aligned_count", "trend", "vol_premium", "regime",
  "internals"}` (each angle a dict with `state`).
- QM pick (`select_qm_top_picks(data, qm_context, include_csp_watch=True)`,
  `:488`): same shape as a baseline pick.
- experiment lanes (`options_researcher.experiments_dashboard.build_experiment_lanes(symbols, asof=…)`,
  `experiments_dashboard.py:262-284`): `{"exp_beta": [card…], "exp_tail": […],
  "exp_spread": […], "exp_tbill": […]}`; every card has `symbol`, `state`,
  `experiment_id`, optional `data_blocked`, and the lane metric:
  `beta` (`exp_beta_qqq.py:132` states OK/UNSTABLE), `jump_count` + `skew`
  (`exp_tail_shape.py:132-139` states OK/UNSTABLE), `ratio`
  (`exp_spread_stability.py:169-176` states OK/ELEVATED), `carry_spread`
  (`exp_tbill_carry.py:131` states ABOVE_TBILL/BELOW_TBILL). Blocked cards
  carry `state == "DATA_BLOCKED"`.
- open positions (`data["open_positions"]`, `:1778`; `load_open_positions`
  `:1456-1520`): `{"rows": [{"book","identifier","text"}], "missing_sources",
  "sources", "h6_last_mark"}`.

---

### Task 1: Display constants with provenance labels

**Files:**
- Modify: `config.py:929-937` (append after `CONTEXT_LANE_ENABLED`, before the
  "ATTRACTIVENESS EXPERIMENT LANES" block at `:932`)
- Test: `tests/test_board_lanes.py` (new file, first test)

**Interfaces:**
- Produces: `config.BOARD_LANES_ENABLED: bool`,
  `config.BOARD_FAVOURABLE_LANES: tuple[str, ...]`,
  `config.BOARD_CAUTION_LANES: tuple[str, ...]` — read by Tasks 2, 4, 5.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_board_lanes.py
import unittest

import config


class BoardConstantsTests(unittest.TestCase):
    def test_lane_board_constants_exist_and_are_disjoint(self):
        self.assertIsInstance(config.BOARD_LANES_ENABLED, bool)
        fav = config.BOARD_FAVOURABLE_LANES
        cau = config.BOARD_CAUTION_LANES
        self.assertEqual(fav, ("baseline", "context", "composite", "qm", "tbill"))
        self.assertEqual(cau, ("spread", "tail", "beta"))
        self.assertFalse(set(fav) & set(cau))

    def test_constants_carry_display_only_provenance_comment(self):
        source = open("config.py", encoding="utf-8").read()
        block = source[source.index("BOARD_LANES_ENABLED"):]
        block = block[: block.index("ATTRACTIVENESS EXPERIMENT LANES")]
        self.assertIn("LLM-proposed 2026-09-06", source[: source.index("BOARD_LANES_ENABLED")][-900:])
        self.assertIn("display-only", source[: source.index("BOARD_LANES_ENABLED")][-900:].lower())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest discover -s tests -p 'test_board_lanes.py' -v`
Expected: FAIL with `AttributeError: module 'config' has no attribute 'BOARD_LANES_ENABLED'`

- [ ] **Step 3: Add the constants**

Insert after `CONTEXT_LANE_ENABLED: bool = True` (`config.py:929`):

```python
# LANE BOARD — the attractiveness board's first-screen agreement table
# (spec docs/superpowers/specs/2026-09-06-attractiveness-board-redesign-design.md).
# Display-only; LLM-proposed 2026-09-06 under owner decisions D1–D9 of that
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

### Task 2: The pure lane-board module

**Files:**
- Create: `options_researcher/board_lanes.py`
- Test: `tests/test_board_lanes.py`

**Interfaces:**
- Consumes: `config.PICK_TOP_N`, `config.BOARD_FAVOURABLE_LANES`, `config.BOARD_CAUTION_LANES`.
- Produces (used by Tasks 4–5):

```python
@dataclass(frozen=True)
class LaneMember:
    symbol: str
    label: str            # what the cell prints, e.g. "#2", "A · 3/4", "✓ 1.90", "! 3.79", "veto"
    value: float | None   # the lane's own number when it has one
    rank: int | None      # 1-based for ranking lanes, None for describing lanes

@dataclass(frozen=True)
class LaneColumn:
    key: str              # "baseline" | "context" | "composite" | "qm" | "spread" | "tail" | "tbill" | "beta"
    title: str
    kind: str             # "ranking" | "describing"
    favourable: bool
    state: str            # "READY" | "DISABLED" | "FAILED:<ExceptionName>" | "UNAVAILABLE:<reason>"
    as_of: str | None
    members: tuple[LaneMember, ...]
    note: str             # header footnote, e.g. "top 5 by carry_spread (LLM-proposed 2026-09-06)"

@dataclass(frozen=True)
class BoardRow:
    symbol: str
    pinned: bool
    baseline_pick: dict | None      # the pick dict, or None
    block_reason: str | None        # DATA_BLOCKED / stale reason for the pick cell
    marks: dict[str, LaneMember]    # lane key -> member
    fav_count: int
    fav_ready: int                  # READY favourable lanes (denominator)

@dataclass(frozen=True)
class LaneBoard:
    columns: tuple[LaneColumn, ...]
    rows: tuple[BoardRow, ...]
    notes: tuple[str, ...]

def build_lane_board(*, baseline_picks, context_selection, composite_cards, qm_picks,
                     experiment_lanes, pinned, blocked, cap=config.PICK_TOP_N,
                     board_as_of) -> LaneBoard
```

- [ ] **Step 1: Write the failing tests (unit, pure)**

Append to `tests/test_board_lanes.py`:

```python
from options_researcher import board_lanes as bl


def _pick(symbol, rank_score=0, status="ELIGIBLE", lane="long_call"):
    return {
        "symbol": symbol, "lane": lane, "status": status, "score": rank_score,
        "card": {"headline": f"Buy the {symbol} call", "strike": 100.0,
                 "expiry": "2026-09-16", "dte": 10, "cost": 300.0,
                 "grades": {"liquidity": "GREEN"},
                 "risk": {"max_loss": 300.0, "breakeven": 103.0},
                 "top3_snapshot": {"candidate_id": f"{symbol}:{lane}:2026-09-16:100.00"}},
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
        context_selection={"state": "READY", "rows": [_ctx_row("AMZN"), _ctx_row("NVDA"),
                                                       _ctx_row("SMCI", term=0, reason="VETOED", angles=())], "error": None},
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
        blocked=[{"symbol": "ET", "reason": "DATA_BLOCKED: chain 29 sessions old"}],
        cap=5, board_as_of="2026-09-03",
    )
    kwargs.update(over)
    return bl.build_lane_board(**kwargs)


class LaneBoardTests(unittest.TestCase):
    def test_columns_are_the_eight_lanes_in_favourable_then_caution_order(self):
        board = _board()
        self.assertEqual([c.key for c in board.columns],
                         ["baseline", "context", "composite", "qm", "tbill", "spread", "tail", "beta"])
        self.assertEqual([c.favourable for c in board.columns], [True] * 5 + [False] * 3)

    def test_baseline_order_first_then_favourable_count_then_symbol(self):
        board = _board()
        symbols = [r.symbol for r in board.rows]
        self.assertEqual(symbols[:3], ["AMZN", "NVDA", "SMCI"])   # registered order, never re-sorted
        rest = symbols[3:]
        counts = [next(r for r in board.rows if r.symbol == s).fav_count for s in rest]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_agreement_counts_favourable_lanes_only(self):
        board = _board()
        by = {r.symbol: r for r in board.rows}
        # NVDA: baseline #2, context #2, composite A, qm #2, tbill absent -> 4/5
        self.assertEqual(by["NVDA"].fav_count, 4)
        self.assertEqual(by["NVDA"].fav_ready, 5)
        # CEG: three cautions (beta, tail, spread) + composite 2/4 -> exactly 1
        self.assertEqual(by["CEG"].fav_count, 1)
        self.assertEqual(set(by["CEG"].marks) & {"beta", "tail", "spread"}, {"beta", "tail", "spread"})

    def test_context_veto_is_shown_but_never_counted(self):
        board = _board()
        smci = next(r for r in board.rows if r.symbol == "SMCI")
        self.assertEqual(smci.marks["context"].label, "veto")
        # SMCI is in baseline (#3) and tbill (1.76 -> top 5); context vetoed; not in composite/qm
        self.assertEqual(sorted(k for k in smci.marks if board_col(board, k).favourable and smci.marks[k].label != "veto"),
                         ["baseline", "tbill"])
        self.assertEqual(smci.fav_count, 2)

    def test_ranking_lanes_are_capped_and_composite_ties_break_by_baseline_then_symbol(self):
        board = _board()
        comp = board_col(board, "composite")
        self.assertEqual([m.symbol for m in comp.members], ["AMZN", "NVDA", "PLTR", "CEG", "ET"])
        # AMZN/NVDA (baseline rows) precede PLTR at aligned=3; at aligned=2 no name is
        # a baseline row, so symbol order fills the remaining slots (CEG, ET) — NBIS/VST drop.
        self.assertEqual(len(comp.members), 5)

    def test_describing_lane_overflow_takes_largest_metric_and_says_so(self):
        board = _board()
        tbill = board_col(board, "tbill")
        self.assertEqual([m.symbol for m in tbill.members], ["NBIS", "IREN", "CRWV", "CLSK", "SMCI"])
        self.assertIn("LLM-proposed 2026-09-06", tbill.note)
        self.assertEqual(tbill.members[0].label, "✓ 2.89")

    def test_beta_lane_has_no_metric_order_and_lists_by_symbol(self):
        board = _board()
        beta = board_col(board, "beta")
        self.assertEqual([m.symbol for m in beta.members], ["CEG"])
        self.assertEqual(beta.members[0].label, "!")

    def test_failed_lane_keeps_its_column_and_leaves_the_denominator(self):
        board = _board(context_selection={"state": "FAILED", "rows": [], "error": "ValueError"})
        ctx = board_col(board, "context")
        self.assertEqual(ctx.state, "FAILED:ValueError")
        self.assertEqual(ctx.members, ())
        self.assertTrue(all(r.fav_ready == 4 for r in board.rows))

    def test_experiment_lane_exception_becomes_failed_state_not_a_raise(self):
        board = _board(experiment_lanes={"exp_tbill": [{"symbol": "AMZN", "state": "ERROR",
                                                        "experiment_id": "EXP-TBILL", "reason": "boom"}]})
        tbill = board_col(board, "tbill")
        self.assertTrue(tbill.state.startswith("UNAVAILABLE:"))
        self.assertIn("boom", tbill.state)
        self.assertTrue(all(r.fav_ready == 4 for r in board.rows))

    def test_pinned_names_are_rows_even_when_no_lane_names_them(self):
        board = _board()
        vst = next(r for r in board.rows if r.symbol == "VST")
        self.assertTrue(vst.pinned)
        self.assertIsNone(vst.baseline_pick)

    def test_blocked_name_carries_its_reason_and_is_never_promoted(self):
        board = _board()
        et = next(r for r in board.rows if r.symbol == "ET")
        self.assertEqual(et.block_reason, "DATA_BLOCKED: chain 29 sessions old")
        self.assertIsNone(et.baseline_pick)

    def test_build_never_mutates_inputs(self):
        picks = [_pick("AMZN")]
        before = repr(picks)
        _board(baseline_picks=picks)
        self.assertEqual(repr(picks), before)


def board_col(board, key):
    return next(c for c in board.columns if c.key == key)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest discover -s tests -p 'test_board_lanes.py' -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'options_researcher.board_lanes'`

- [ ] **Step 3: Write the module**

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
    baseline_pick: dict | None
    block_reason: str | None
    marks: dict[str, LaneMember]
    fav_count: int
    fav_ready: int


@dataclass(frozen=True)
class LaneBoard:
    columns: tuple[LaneColumn, ...]
    rows: tuple[BoardRow, ...]
    notes: tuple[str, ...]


_ORDER_NOTE = "top {cap} by {metric}, largest first (LLM-proposed 2026-09-06 display rule)"

# lane key -> (title, experiment_lanes key, flag state, metric, cell prefix)
_EXPERIMENTS = {
    "tbill": ("T-bill carry", "exp_tbill", "ABOVE_TBILL", "carry_spread", "✓"),
    "spread": ("Spread stability", "exp_spread", "ELEVATED", "ratio", "!"),
    "tail": ("Tail shape", "exp_tail", "UNSTABLE", "jump_count", "!"),
    "beta": ("Beta to QQQ", "exp_beta", "UNSTABLE", None, "!"),
}


def _sym(item: Mapping[str, object]) -> str | None:
    s = item.get("symbol")
    return s if isinstance(s, str) and s else None


def _num(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) and value == value else None


def lane_from_baseline(picks: Sequence[Mapping[str, object]] | None, *, cap: int, as_of: str | None) -> LaneColumn:
    if picks is None:
        return LaneColumn("baseline", "Rule-based top 5", "ranking", True, "UNAVAILABLE:no picks", as_of, (), "registered baseline")
    members = tuple(LaneMember(s, f"#{i}", None, i) for i, p in enumerate(picks[:cap], 1) if (s := _sym(p)))
    return LaneColumn("baseline", "Rule-based top 5", "ranking", True, "READY", as_of, members, "registered baseline; decides row order")


def lane_from_context(selection: Mapping[str, object] | None, *, cap: int, as_of: str | None) -> LaneColumn:
    if not isinstance(selection, Mapping):
        return LaneColumn("context", "Context lane", "ranking", True, "UNAVAILABLE:no selection", as_of, (), "display-only")
    state = str(selection.get("state") or "UNAVAILABLE")
    if state != "READY":
        err = selection.get("error")
        tag = f"FAILED:{err}" if state == "FAILED" and err else state
        return LaneColumn("context", "Context lane", "ranking", True, tag, as_of, (), "display-only")
    rows = selection.get("rows")
    rows = rows if isinstance(rows, Sequence) else ()
    members = []
    for i, row in enumerate(rows[:cap], 1):
        if not isinstance(row, Mapping) or not (s := _sym(row)):
            continue
        vetoed = str(row.get("context_reason") or "") == "VETOED"
        members.append(LaneMember(s, "veto" if vetoed else f"#{i}", _num(row.get("context_term")), i))
    return LaneColumn("context", "Context lane", "ranking", True, "READY", as_of, tuple(members),
                      "display-only · baseline + market-context tiebreak; 'veto' is shown, never counted")


def lane_from_composite(cards: Sequence[Mapping[str, object]] | None, *, cap: int, as_of: str | None,
                        baseline_order: Sequence[str]) -> LaneColumn:
    if cards is None:
        return LaneColumn("composite", "Composite", "ranking", True, "UNAVAILABLE:no cards", as_of, (), "display-only")
    usable = [c for c in cards if isinstance(c, Mapping) and _sym(c) and isinstance(c.get("aligned_count"), int)]
    pos = {s: i for i, s in enumerate(baseline_order)}
    usable.sort(key=lambda c: (-int(c["aligned_count"]), pos.get(_sym(c), len(pos)), _sym(c)))
    members = tuple(
        LaneMember(_sym(c), f"{c.get('grade') or '?'} · {int(c['aligned_count'])}/4", float(c["aligned_count"]), i)
        for i, c in enumerate(usable[:cap], 1)
    )
    return LaneColumn("composite", "Composite", "ranking", True, "READY", as_of, members,
                      "display-only · angles agreeing; ties by baseline order, then symbol")


def lane_from_qm(picks: Sequence[Mapping[str, object]] | None, *, cap: int, as_of: str | None) -> LaneColumn:
    if picks is None:
        return LaneColumn("qm", "QM movement", "ranking", True, "UNAVAILABLE:no QM context", as_of, (), "gated study")
    members = tuple(LaneMember(s, f"#{i}", None, i) for i, p in enumerate(picks[:cap], 1) if (s := _sym(p)))
    return LaneColumn("qm", "QM movement", "ranking", True, "READY", as_of, members, "gated study · mechanical picks")


def lane_from_experiment(key: str, cards: object, *, cap: int, as_of: str | None) -> LaneColumn:
    title, _lane_key, flag_state, metric, prefix = _EXPERIMENTS[key]
    favourable = key in config.BOARD_FAVOURABLE_LANES
    if cards is None:
        return LaneColumn(key, title, "describing", favourable, "UNAVAILABLE:lane not computed", as_of, (), "experiment")
    cards = [c for c in cards if isinstance(c, Mapping)] if isinstance(cards, Sequence) else []
    errors = [c for c in cards if c.get("state") == "ERROR"]
    if errors:
        reason = str(errors[0].get("reason") or "lane failed")
        return LaneColumn(key, title, "describing", favourable, f"UNAVAILABLE:{reason}", as_of, (), "experiment")
    flagged = [c for c in cards if c.get("state") == flag_state and _sym(c)]
    if metric:
        flagged.sort(key=lambda c: (-(_num(c.get(metric)) or float("-inf")), _sym(c)))
    else:
        flagged.sort(key=lambda c: _sym(c))
    members = []
    for c in flagged[:cap]:
        v = _num(c.get(metric)) if metric else None
        members.append(LaneMember(_sym(c), f"{prefix} {v:.2f}" if v is not None else prefix, v, None))
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
    base_order = [s for p in (baseline_picks or [])[:cap] if (s := _sym(p))]
    exp = experiment_lanes if isinstance(experiment_lanes, Mapping) else {}
    columns_by_key = {
        "baseline": lane_from_baseline(baseline_picks, cap=cap, as_of=board_as_of),
        "context": lane_from_context(context_selection, cap=cap, as_of=board_as_of),
        "composite": lane_from_composite(composite_cards, cap=cap, as_of=board_as_of, baseline_order=base_order),
        "qm": lane_from_qm(qm_picks, cap=cap, as_of=board_as_of),
    }
    gather_error = exp.get("__error__") if isinstance(exp, Mapping) else None
    for key in _EXPERIMENTS:
        if gather_error:
            cards: object = [{"symbol": "", "state": "ERROR", "reason": str(gather_error)}]
        else:
            cards = exp.get(_EXPERIMENTS[key][1]) if exp else None
        columns_by_key[key] = lane_from_experiment(key, cards, cap=cap, as_of=board_as_of)
    ordered_keys = tuple(config.BOARD_FAVOURABLE_LANES) + tuple(config.BOARD_CAUTION_LANES)
    columns = tuple(columns_by_key[k] for k in ordered_keys)

    fav_ready = sum(1 for c in columns if c.favourable and c.state == "READY")
    marks: dict[str, dict[str, LaneMember]] = {}
    for col in columns:
        for m in col.members:
            marks.setdefault(m.symbol, {})[col.key] = m
    pick_by_symbol = {s: p for p in (baseline_picks or [])[:cap] if (s := _sym(p))}
    block_by_symbol = {s: str(b.get("reason") or "DATA_BLOCKED")
                       for b in (blocked or []) if isinstance(b, Mapping) and (s := _sym(b))}

    def fav_count(sym: str) -> int:
        return sum(1 for k, m in marks.get(sym, {}).items()
                   if columns_by_key[k].favourable and columns_by_key[k].state == "READY" and m.label != "veto")

    symbols = set(marks) | set(pinned)
    rest = sorted((s for s in symbols if s not in base_order), key=lambda s: (-fav_count(s), s))
    rows = tuple(
        BoardRow(symbol=s, pinned=s in set(pinned), baseline_pick=pick_by_symbol.get(s),
                 block_reason=block_by_symbol.get(s), marks=dict(marks.get(s, {})),
                 fav_count=fav_count(s), fav_ready=fav_ready)
        for s in [*base_order, *rest]
    )
    notes = tuple(f"{c.title}: {c.state}" for c in columns if c.state != "READY")
    return LaneBoard(columns=columns, rows=rows, notes=notes)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest discover -s tests -p 'test_board_lanes.py' -v`
Expected: PASS (13 tests). If the composite tie test disagrees with your
implementation, the TEST is the contract (spec §3: ties by baseline order,
then symbol); fix the code.

- [ ] **Step 5: Lint and types, then commit**

Run: `uv run ruff check options_researcher/board_lanes.py tests/test_board_lanes.py && uv run pyright options_researcher/board_lanes.py`
Expected: clean.

```bash
git add options_researcher/board_lanes.py tests/test_board_lanes.py
git commit -m "feat(board): pure lane-board builder (agreement table data; favourable-only count)"
```

---

### Task 3: Experiment lanes in the gather step, injectable in `assemble`

**Files:**
- Modify: `options_researcher/attractiveness_dashboard.py:1562-1580` (`assemble` signature),
  `:1770-1782` (where `assemble` attaches `open_positions` / `schwab_lane` to `out`),
  `:1784` (`_gather_all`)
- Test: `tests/test_attractiveness_dashboard.py`

**Interfaces:**
- Consumes: `options_researcher.experiments_dashboard.build_experiment_lanes(symbols, asof=...)` (`experiments_dashboard.py:262`).
- Produces: `data["experiment_lanes"]` — the dict `build_experiment_lanes`
  returns, or `{"__error__": "<ExceptionName>: <message>"}` when it raised;
  `assemble(..., experiment_lanes=...)` keyword for injection.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_attractiveness_dashboard.py` (reuse the file's existing
`_fresh_section` / `_stale_section` helpers):

```python
class ExperimentLaneGatherTests(unittest.TestCase):
    def test_injected_experiment_lanes_are_attached_verbatim(self):
        lanes = {"exp_tbill": [{"symbol": "AMZN", "state": "ABOVE_TBILL", "carry_spread": 0.65,
                                "experiment_id": "EXP-TBILL", "asof": "2026-08-14"}]}
        data = ad.assemble(symbol_sections=[_fresh_section()], rv21_by_symbol={},
                           today="2026-08-14", experiment_lanes=lanes)
        self.assertEqual(data["experiment_lanes"], lanes)

    def test_experiment_lane_builder_failure_is_recorded_not_raised(self):
        from unittest import mock
        with mock.patch("options_researcher.experiments_dashboard.build_experiment_lanes",
                        side_effect=RuntimeError("cache missing")):
            data = ad.assemble(symbol_sections=[_fresh_section()], rv21_by_symbol={},
                               today="2026-08-14")
        self.assertEqual(data["experiment_lanes"], {"__error__": "RuntimeError: cache missing"})

    def test_experiment_lanes_use_the_board_chain_session_as_asof(self):
        from unittest import mock
        seen = {}

        def fake(symbols, *, asof):
            seen["asof"] = asof
            seen["symbols"] = tuple(symbols)
            return {}

        with mock.patch("options_researcher.experiments_dashboard.build_experiment_lanes", side_effect=fake):
            data = ad.assemble(symbol_sections=[_fresh_section()], rv21_by_symbol={}, today="2026-08-14")
        self.assertEqual(seen["asof"], data["data_as_of"])
        self.assertEqual(seen["symbols"], tuple(config.ATTRACTIVENESS_UNIVERSE))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_dashboard.py' -k ExperimentLaneGather -v`
Expected: FAIL with `TypeError: assemble() got an unexpected keyword argument 'experiment_lanes'`

- [ ] **Step 3: Implement**

In `assemble` (`:1562`): add keyword `experiment_lanes: Mapping[str, object] | None = None`.
Where `out` is built (`:1770-1782`), after `out["schwab_lane"] = schwab_state`:

```python
    if experiment_lanes is None:
        experiment_lanes = _default_experiment_lanes(out.get("data_as_of"))
    out["experiment_lanes"] = dict(experiment_lanes)
```

Add near `_gather_all` (`:1784`):

```python
def _default_experiment_lanes(as_of: object) -> dict[str, object]:
    """Compute the four parking-lot experiment lanes from cached data for the
    lane board (spec §4). Fail-visible: a builder exception becomes a recorded
    error the board prints as a lane state, never a crash of the whole page."""
    from options_researcher import experiments_dashboard

    if not isinstance(as_of, str) or not as_of:
        return {"__error__": "no board as-of session"}
    try:
        return dict(experiments_dashboard.build_experiment_lanes(
            list(config.ATTRACTIVENESS_UNIVERSE), asof=as_of))
    except Exception as exc:  # fail-visible by design (spec §5)
        return {"__error__": f"{exc.__class__.__name__}: {exc}"}
```

`build_lane_board` (Task 2) already treats a lanes dict containing
`"__error__"` as every experiment column `UNAVAILABLE:<that text>` (the
`gather_error` branch). Add the unit test for it in `tests/test_board_lanes.py`:

```python
    def test_gather_level_error_marks_every_experiment_column_unavailable(self):
        board = _board(experiment_lanes={"__error__": "RuntimeError: cache missing"})
        for key in ("tbill", "spread", "tail", "beta"):
            self.assertEqual(board_col(board, key).state, "UNAVAILABLE:RuntimeError: cache missing")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_dashboard.py' -k ExperimentLaneGather -v && uv run python -m unittest discover -s tests -p 'test_board_lanes.py' -v`
Expected: PASS. Then run the existing layout + dashboard files to prove the
new kwarg default did not change any current output:
`uv run python -m unittest discover -s tests -p 'test_attractiveness_*.py'` → OK.

- [ ] **Step 5: Commit**

```bash
git add options_researcher/attractiveness_dashboard.py options_researcher/board_lanes.py tests/test_attractiveness_dashboard.py tests/test_board_lanes.py
git commit -m "feat(board): compute experiment lanes in gather (injectable, fail-visible)"
```

---

### Task 4: New section builders (status strip, tiles, table, event line, details)

**Files:**
- Modify: `options_researcher/attractiveness_dashboard.py` — add builders next
  to `_composite_html` (`:4774`); extract `_symbol_panel_html` from the
  per-symbol loop in `_render_result` (the block that appends
  `<details class="panel symbol-panel"` to `symbols_html`, `:5590-5665`
  region — locate with `grep -n 'symbols_html += (' options_researcher/attractiveness_dashboard.py`).
- Test: `tests/test_attractiveness_dashboard.py`

**Interfaces:**
- Consumes: `LaneBoard` (Task 2); `data["open_positions"]`; `_risk_line(card)` (`:3192`);
  `_event_chips_html(card, symbol, evaluation_date, event_view)` (`:3014`);
  `_esc`.
- Produces:
  - `_status_strip_html(data, research_views_status, context) -> str`
  - `_position_tiles_html(data, event_line_text) -> str`
  - `_agreement_table_html(board: LaneBoard, *, event_view, evaluation_date) -> str`
  - `_event_line_html(board, event_view, evaluation_date) -> str`
  - `_symbol_panel_html(sec, *, context, event_view, evaluation_date, status_labels) -> str`
    (the extracted per-symbol panel; byte-identical output to the inline loop;
    it computes `open_attr` from `sec` exactly as the loop did, so DATA_BLOCKED
    and stale panels stay open by default — spec §6 invariant 7)
  - `_pick_details_html(data, board, *, context, event_view, evaluation_date, status_labels) -> str`

- [ ] **Step 1: Write the failing render tests**

Append to `tests/test_attractiveness_dashboard.py`:

```python
class LaneBoardRenderTests(unittest.TestCase):
    def _board(self):
        from options_researcher import board_lanes as bl
        pick = {"symbol": "AMZN", "lane": "long_call", "status": "ELIGIBLE", "score": 0,
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
        html = ad._agreement_table_html(self._board(), event_view=None, evaluation_date="2026-09-04")
        for title in ("Rule-based top 5", "Context lane", "Composite", "QM movement", "T-bill carry",
                      "Spread stability", "Tail shape", "Beta to QQQ"):
            self.assertIn(title, html)
        self.assertIn("FAILED:ValueError", html)          # failed lane keeps its column
        self.assertIn("2026-09-03", html)                  # as-of in headers
        self.assertIn('class="agree"', html)

    def test_agreement_cell_counts_favourable_ready_lanes_only(self):
        html = ad._agreement_table_html(self._board(), event_view=None, evaluation_date="2026-09-04")
        row = html[html.index("AMZN"):]
        self.assertIn("1/4", row[: row.index("</tr>")])   # baseline only; context FAILED leaves the denominator

    def test_pinned_name_without_a_pick_is_a_row_marked_pinned(self):
        html = ad._agreement_table_html(self._board(), event_view=None, evaluation_date="2026-09-04")
        self.assertIn("VST", html)
        self.assertIn("pinned", html[html.index("VST"):][:400])
        self.assertIn("not in the registered top 5", html[html.index("VST"):][:600])

    def test_position_tiles_flag_a_last_mark_older_than_the_exit_rule(self):
        data = {"open_positions": {"rows": [
            {"book": "H6", "identifier": "H6-0001", "text": "H6-0001 NVDA $220.00 call · exp 2026-09-18 · entered 2026-07-13"},
            {"book": "shares", "identifier": "VST", "text": "VST 39 shares · cost basis $142.28 · acquired 2026-06-15"}],
            "missing_sources": [], "sources": [], "h6_last_mark": "2026-07-27"},
            "evaluation_date": "2026-09-04"}
        html = ad._position_tiles_html(data, "FOMC decision · 2026-09-16")
        self.assertIn("H6-0001", html)
        self.assertIn("2026-07-27", html)
        self.assertIn("sessions unmarked", html)
        self.assertIn("VST 39", html)
        self.assertIn("FOMC decision", html)

    def test_position_tiles_say_so_when_the_book_is_unreadable(self):
        data = {"open_positions": {"rows": [], "missing_sources": ["data/positions/h6_positions.csv"],
                                   "sources": [], "h6_last_mark": None}, "evaluation_date": "2026-09-04"}
        html = ad._position_tiles_html(data, "")
        self.assertIn("UNREAD", html)
        self.assertIn("data/positions/h6_positions.csv", html)

    def test_event_line_prints_the_union_of_table_names_chips_once(self):
        from options_researcher.event_calendar import Event  # existing type used by event_view
        board = self._board()
        # event_view shape per _event_chips_html: {"calendar": [...], "complex_map": {}}
        from datetime import date
        ev = {"calendar": [Event(date=date(2026, 9, 16), title="FOMC decision", kind="fomc")],  # adjust ctor to the real Event signature
              "complex_map": {}}
        html = ad._event_line_html(board, ev, "2026-09-04")
        self.assertEqual(html.count("FOMC decision"), 1)

    def test_pick_details_render_only_table_names(self):
        data = ad.assemble(symbol_sections=[_fresh_section("AMZN"), _fresh_section("MSFT")],
                           rv21_by_symbol={}, today="2026-08-14", experiment_lanes={})
        board = self._board()
        html = ad._pick_details_html(data, board, context=None, event_view=None,
                                     evaluation_date="2026-08-14", status_labels={})
        self.assertIn('id="symbol-AMZN"', html)
        self.assertNotIn('id="symbol-MSFT"', html)
```

Executor notes: (a) read `options_researcher/event_calendar.py` for the real
`Event` constructor before pasting the event-line test; the assertion (the
title appears exactly once) is the contract, the fixture construction is
yours. (b) `_fresh_section(...)` / `_stale_section(...)` are the helpers this
test file already defines near its top; check their signatures (the stale one
takes `(symbol, as_of)`) and build two sections with different symbols.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_dashboard.py' -k LaneBoardRender -v`
Expected: FAIL with `AttributeError: module ... has no attribute '_agreement_table_html'`

- [ ] **Step 3: Implement the builders**

Add after `_composite_html` (`:4774-4800` region):

```python
def _status_strip_html(data: Mapping[str, object], research_views_status: Mapping[str, object] | None,
                       context: Mapping[str, object] | None) -> str:
    """One line, five facts, each a coloured dot + a word (spec §2.1). The
    per-notice detail keeps rendering inside the drawer (Task 5)."""
    from options_researcher.schwab_chain_view import CHAIN_SOURCE, CONVENTION_LABEL

    as_of = str(data.get("data_as_of") or "no cached data")
    source = (f"{CONVENTION_LABEL}, session {as_of}" if data.get("as_of_kind") == CHAIN_SOURCE
              else f"frozen EOD {as_of}")
    fresh = data.get("fresh_symbols") or []
    stale = data.get("stale_symbols") or []
    closes = data.get("underlying_closes_freshness") or {}
    closes_as_of = str(closes.get("max_session") or closes.get("as_of") or "unknown")
    lane = data.get("schwab_lane") or {}
    failures = lane.get("failures") if isinstance(lane, Mapping) else None
    failures = list(failures) if isinstance(failures, (list, tuple)) else []
    # "in window" = the same retention rule brief 37 WP-G gave the red notices:
    # age <= config.CHAIN_STALE_BLOCK_SESSIONS counted with trading_sessions_between;
    # when the evaluation session is missing every failure counts (fail-visible).
    evaluation = str(data.get("evaluation_date") or "")
    n_fail = len(failures)
    if evaluation:
        try:
            from options_researcher.top3_snapshot import trading_sessions_between
            n_fail = sum(1 for f in failures if isinstance(f, Mapping) and isinstance(f.get("session"), str)
                         and trading_sessions_between(str(f["session"]), evaluation) <= config.CHAIN_STALE_BLOCK_SESSIONS)
        except Exception:
            n_fail = len(failures)
    researched = str((context or {}).get("researched_on") or "never")

    def dot(cls: str, text: str) -> str:
        return f'<span class="strip-item"><span class="dot {cls}"></span>{_esc(text)}</span>'

    return ('<div class="status-strip">'
            + dot("good" if data.get("as_of_kind") == CHAIN_SOURCE else "warn", f"option quotes: {source}")
            + dot("good", f"closes through {closes_as_of}")
            + dot("warn" if stale else "good", f"{len(fresh)} names fresh · {len(stale)} stale"
                  + (f" ({', '.join(str(s) for s in stale)})" if stale else ""))
            + dot("warn" if researched != str(as_of) else "good", f"research annotations {researched}")
            + dot("crit" if n_fail else "good", f"{n_fail} capture failures in window")
            + "</div>")


def _position_tiles_html(data: Mapping[str, object], event_line_text: str) -> str:
    """Four stat tiles (spec §2.2). Reads only data['open_positions']; an
    unreadable source is printed, never treated as an empty book."""
    positions = data.get("open_positions")
    if not isinstance(positions, Mapping):
        return '<div class="tiles"><div class="tile bad"><div class="k">Positions</div><div class="v">UNREAD</div></div></div>'
    rows = positions.get("rows") if isinstance(positions.get("rows"), list) else []
    missing = positions.get("missing_sources") or []
    option_rows = [r for r in rows if r.get("book") != "shares"]
    share_rows = [r for r in rows if r.get("book") == "shares"]
    last_mark = positions.get("h6_last_mark")
    evaluation = str(data.get("evaluation_date") or "")
    mark_age = None
    if isinstance(last_mark, str) and evaluation:
        try:
            from options_researcher.top3_snapshot import trading_sessions_between
            mark_age = trading_sessions_between(last_mark, evaluation)
        except Exception:
            mark_age = None
    mark_cls = "bad" if (mark_age or 0) > 0 else ""   # see the executor note below on the registered exit rule
    tiles = []
    if missing:
        tiles.append('<div class="tile bad"><div class="k">Positions</div><div class="v">UNREAD</div>'
                     f'<div class="d">{_esc(", ".join(str(m) for m in missing))}</div></div>')
    tiles.append('<div class="tile"><div class="k">Open option</div>'
                 f'<div class="v">{_esc(option_rows[0]["identifier"]) if option_rows else "none"}</div>'
                 f'<div class="d">{_esc(option_rows[0]["text"]) if option_rows else "no open option positions"}</div></div>')
    tiles.append(f'<div class="tile {mark_cls}"><div class="k">Last mark</div>'
                 f'<div class="v">{_esc(str(last_mark) if last_mark else "none")}</div>'
                 f'<div class="d">{(str(mark_age) + " sessions unmarked") if mark_age is not None else "no mark recorded"}</div></div>')
    tiles.append('<div class="tile"><div class="k">Shares</div>'
                 f'<div class="v">{_esc(share_rows[0]["text"].split(" · ")[0]) if share_rows else "none"}</div>'
                 f'<div class="d">{_esc(share_rows[0]["text"]) if share_rows else "no share lots recorded"}</div></div>')
    tiles.append('<div class="tile"><div class="k">Event ahead</div>'
                 f'<div class="v">{_esc(event_line_text.split(" · ")[0]) if event_line_text else "none"}</div>'
                 f'<div class="d">{_esc(event_line_text)}</div></div>')
    return '<div class="tiles">' + "".join(tiles) + "</div>"
```

Executor note on the mark-age threshold: the registered H6 exit rule is
`config.H6_*` (brief 37 cited `config.py:347-348`, `h6_watch.py:446-452`,
"mandatory close at ≤ 21 days to expiry"). Read those lines; if a named
constant for the 21-day rule exists use it, otherwise print the age only and
colour the tile red when `mark_age > 0` — do NOT invent a threshold constant.
Replace the `> 0` rule above with the real constant when one exists, and say
which in the PR body.

```python
def _agreement_table_html(board: "LaneBoard", *, event_view: Mapping[str, object] | None,
                          evaluation_date: str) -> str:
    """Spec §3. Row order and the 'Agree' count come from the pure module;
    this function only prints."""
    fav = [c for c in board.columns if c.favourable]
    cau = [c for c in board.columns if not c.favourable]

    def header(col) -> str:
        return (f'<th title="{_esc(col.note)}">{_esc(col.title)}<br>'
                f'<span class="th-sub">{_esc(col.kind)} · as of {_esc(str(col.as_of or "?"))} · {_esc(col.state)}</span></th>')

    def cell(row, col) -> str:
        m = row.marks.get(col.key)
        if col.state != "READY":
            return '<td class="lane-off"></td>'
        if m is None:
            return "<td></td>"
        cls = "warn" if not col.favourable else ("veto" if m.label == "veto" else "on")
        return f'<td><span class="chip {cls}">{_esc(m.label)}</span></td>'

    def pick_cell(row) -> str:
        if row.baseline_pick is not None:
            card = row.baseline_pick.get("card") or {}
            risk = card.get("risk") or {}
            econ = (f"cost ${float(card.get('cost') or 0):,.0f} · worst -${float(risk.get('max_loss') or 0):,.0f}"
                    f" · breakeven ${float(risk.get('breakeven') or 0):,.2f} · {_esc(str(card.get('expiry') or '?'))}"
                    f" ({_esc(str(card.get('dte') or '?'))}d)")
            return (f'{_esc(str(card.get("headline") or ""))}<div class="econ">{econ} · '
                    f'<a href="#symbol-{_esc(row.symbol)}">details</a></div>')
        if row.block_reason:
            return f'<span class="blocked">{_esc(row.block_reason)}</span>'
        return '<span class="muted">not in the registered top 5</span>'

    head = ("<tr><th rowspan=\"2\">Name</th><th rowspan=\"2\">Registered pick (baseline decides the order)</th>"
            f"<th colspan=\"{len(fav)}\" class=\"group\">Favourable lanes · top {config.PICK_TOP_N} each</th>"
            "<th rowspan=\"2\">Agree</th>"
            f"<th colspan=\"{len(cau)}\" class=\"group\">Cautions (shown, never counted)</th></tr>"
            "<tr>" + "".join(header(c) for c in fav) + "".join(header(c) for c in cau) + "</tr>")
    body = []
    for row in board.rows:
        pinned = ' <span class="chip">pinned</span>' if row.pinned else ""
        agree = (f'<td class="agree-cell"><span class="bar" style="width:{row.fav_count * 14}px"></span>'
                 f'<span class="agree">{row.fav_count}/{row.fav_ready}</span></td>')
        body.append(f'<tr><td class="sym">{_esc(row.symbol)}{pinned}</td><td>{pick_cell(row)}</td>'
                    + "".join(cell(row, c) for c in fav) + agree + "".join(cell(row, c) for c in cau) + "</tr>")
    notes = "".join(f'<div class="notice info">{_esc(n)}</div>' for n in board.notes)
    return ('<section class="panel agreement" id="agreement-table">'
            '<div class="eyebrow">Today\'s picks · agreement across lanes</div>'
            '<h2>Rule-based top 5 — best policy-and-liquidity fit today</h2>'
            '<p class="header-sub">Every name any lane picked or flagged, the registered picks first. '
            'The registered baseline decides the order and is never re-ordered. "Agree" counts '
            'favourable lanes only — a description, never a score; cautions are shown but never counted.</p>'
            f'{notes}<table class="agreement-table"><thead>{head}</thead><tbody>{"".join(body)}</tbody></table></section>')
```

Keep the `<h2>` text `Rule-based top 5 — best policy-and-liquidity fit today`
byte-identical to today's (`:4162`) — `tests/test_attractiveness_layout.py`
and the pick-tracker digest locate the shortlist by it (verify with
`grep -n "Rule-based top 5" tests/*.py options_researcher/pick_tracker.py`).

```python
def _event_line_html(board: "LaneBoard", event_view: Mapping[str, object] | None,
                     evaluation_date: str) -> str:
    """The sorted union of the table names' event chips, printed once (spec §2.4)."""
    if not event_view:
        return ""
    seen: dict[str, None] = {}
    for row in board.rows:
        card = (row.baseline_pick or {}).get("card") or {}
        frag = _event_chips_html(card, row.symbol, evaluation_date, event_view)
        if frag.startswith('<div class="notice bad">'):
            return frag                      # EVENT LAYER FAILED stays loud, never deduped
        for text in re.findall(r'<span class="event-chip">EVENT · (.*?)</span>', frag):
            seen.setdefault(text, None)
    if not seen:
        return ""
    return ('<div class="event-line"><span class="event-line-label">Events ahead:</span>'
            + "".join(f'<span class="event-chip">EVENT · {t}</span>' for t in sorted(seen)) + "</div>")


def _pick_details_html(data: Mapping[str, object], board: "LaneBoard", *, context, event_view,
                       evaluation_date: str, status_labels: Mapping[str, object]) -> str:
    """One closed <details> per table name (spec §2.5); other names are not rendered."""
    wanted = [r.symbol for r in board.rows]
    by_symbol = {str(sec.get("symbol")): sec for sec in data.get("symbols", []) if isinstance(sec, Mapping)}
    parts = []
    for symbol in wanted:
        sec = by_symbol.get(symbol)
        if sec is None:
            continue
        parts.append(_symbol_panel_html(sec, context=context, event_view=event_view,
                                        evaluation_date=evaluation_date, status_labels=status_labels))
    if not parts:
        return ""
    return ('<section class="panel details" id="pick-details"><div class="eyebrow">Pick details on demand</div>'
            '<h2>Details for the names above</h2>' + "".join(parts) + "</section>")
```

Then extract `_symbol_panel_html(sec, *, context, event_view, evaluation_date, status_labels) -> str`
from the per-symbol loop body in `_render_result` so that the loop becomes:

```python
        symbols_html += _symbol_panel_html(sec, context=context, event_view=event_view,
                                           evaluation_date=evaluation_date,
                                           status_labels=status_labels)
```

Move every local the loop body used (`open_attr`, `status_html`,
`display_only_html`, `display_date_stat`, `event_failure`, `implied`,
`stale_html`, `tech_html`, `rank_note`, `groups`) into the new function
unchanged — including the rule that decides `open_attr` (owner-pinned and
fail-visible DATA_BLOCKED/stale panels open, clean panels closed;
`tests/test_attractiveness_layout.py:277`). Prove the extraction
is byte-identical by rendering the layout fixture before and after (Task 5's
byte-identity test covers it; run it now as a smoke check).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_*.py' -v 2>&1 | tail -20`
Expected: the new `LaneBoardRenderTests` PASS; every pre-existing test still
PASSES (nothing is wired into `render` yet).

- [ ] **Step 5: Commit**

```bash
git add options_researcher/attractiveness_dashboard.py tests/test_attractiveness_dashboard.py
git commit -m "feat(board): status strip, position tiles, agreement table, event line, details-on-demand builders"
```

---

### Task 5: Wire the new page order behind the flag; keep the legacy page byte-identical

**Files:**
- Modify: `options_researcher/attractiveness_dashboard.py:5682-5721` (`_render_result` body assembly),
  `:5737` (`_sticky_nav_html` call), `_STYLE` (add the new classes)
- Test: `tests/test_attractiveness_layout.py`

**Interfaces:**
- Consumes: Task 2 `build_lane_board`, Task 4 builders, `config.BOARD_LANES_ENABLED`.
- Produces: the redesigned page when the flag is on; today's page when off.

- [ ] **Step 1: Write the failing layout tests**

Append to `tests/test_attractiveness_layout.py` (the file's `_board` helper
builds fixtures; add `experiment_lanes={}` to its `assemble` call so the
fixture never touches the cache):

```python
class LaneBoardLayoutTests(unittest.TestCase):
    """Spec §2 page order, with the flag on."""

    def _html(self, **kw):
        with mock.patch.object(config, "BOARD_LANES_ENABLED", True):
            data = _board(["NVDA", "AMZN", "MSFT"], **kw)
            return ad.render(data)

    def test_page_order_is_strip_tiles_table_event_details_drawer(self):
        html = self._html()
        anchors = ['class="status-strip"', 'class="tiles"', 'id="agreement-table"',
                   'id="pick-details"', 'class="drawer"']
        offsets = [html.index(a) for a in anchors]
        self.assertEqual(offsets, sorted(offsets))

    def test_removed_surfaces_are_absent(self):
        html = self._html()
        for gone in ('id="context-aware-top-5"', 'id="composite-board"', 'class="sticky-nav"',
                     "VST / AMZN — ALWAYS SHOWN", "CONTEXT-AWARE SHORTLIST"):
            self.assertNotIn(gone, html)

    def test_details_render_only_for_table_names(self):
        html = self._html()
        table = html[html.index('id="agreement-table"'):html.index('id="pick-details"')]
        names_on_table = set(re.findall(r'<td class="sym">([A-Z]+)', table))
        rendered = set(re.findall(r'id="symbol-([A-Z]+)"', html))
        self.assertEqual(rendered, names_on_table)

    def test_relocated_content_is_appended_after_the_six_drawer_sections(self):
        html = self._html()
        drawer = html[html.index('class="drawer"'):]
        six = [drawer.index(s) for s in DrawerTests._DRAWER_SECTIONS]   # reuse the existing tuple
        self.assertEqual(six, sorted(six))
        for relocated in ("Registered-bets tracker", "Shortlist outcome scoreboard", "Data freshness"):
            self.assertGreater(drawer.index(relocated), six[-1])

    def test_disclaimers_survive_verbatim_with_flag_on(self):
        html = self._html()
        self.assertIn("mission-control dashboard date INDEPENDENTLY", html)
        self.assertIn("Payoffs are at-expiration scenarios, not predictions.", html)

    def test_flag_off_renders_the_legacy_page_byte_for_byte(self):
        data = _board(["NVDA", "AMZN", "MSFT"])
        with mock.patch.object(config, "BOARD_LANES_ENABLED", False):
            legacy = ad.render(data)
        self.assertEqual(legacy, LEGACY_RENDER_SNAPSHOT(data))

    def test_zero_javascript_with_flag_on(self):
        self.assertNotIn("<script", self._html().lower())
```

`LEGACY_RENDER_SNAPSHOT` is a module-level helper you add to the test file:

```python
def LEGACY_RENDER_SNAPSHOT(_data):
    with open("tests/fixtures/attractiveness_legacy_layout.html", encoding="utf-8") as fh:
        return fh.read()
```

The snapshot is **captured in Step 3 BEFORE wiring** (the pre-change page on
a deterministic fixture: fixed `today`, injected sections,
`experiment_lanes={}`), so the flag-off path is compared against today's
renderer, not against itself. `DrawerTests._DRAWER_SECTIONS` in the test
above means the tuple defined at `tests/test_attractiveness_layout.py:375` —
use the name of the class that actually holds it.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_layout.py' -k LaneBoardLayout -v`
Expected: FAIL (`status-strip` not found; snapshot fixture missing).

- [ ] **Step 3: Capture the legacy snapshot BEFORE wiring**

```bash
uv run python - <<'EOF'
import config
from tests.test_attractiveness_layout import _board   # add tests/__init__.py if import fails; see note
from options_researcher import attractiveness_dashboard as ad
config.BOARD_LANES_ENABLED = False
html = ad.render(_board(["NVDA", "AMZN", "MSFT"]))
open("tests/fixtures/attractiveness_legacy_layout.html", "w").write(html)
print(len(html))
EOF
```

Note: `tests/` has no `__init__.py`; run the snippet with `PYTHONPATH=tests`
and `from test_attractiveness_layout import _board` instead of adding one.

- [ ] **Step 4: Wire `render`**

In `_render_result` (`:5682-5721`) replace the `body_html = (...)` assembly with:

```python
    if config.BOARD_LANES_ENABLED:
        from options_researcher import board_lanes as _bl

        try:
            board = _bl.build_lane_board(
                baseline_picks=qualified_picks,
                context_selection=context_selection,
                composite_cards=data.get("composite_signals"),
                qm_picks=(select_qm_top_picks(data, qm_context, include_csp_watch=True)
                          if isinstance(qm_context, Mapping) else None),
                experiment_lanes=data.get("experiment_lanes"),
                pinned=[str(p.get("symbol")) for p in pinned_records or []],
                blocked=data.get("blocked") or [],
                board_as_of=str(data.get("data_as_of") or ""),
            )
            board_error = None
        except Exception as exc:  # fail-visible: never blank the decision area
            board, board_error = None, exc.__class__.__name__
        event_line_html = _event_line_html(board, event_view, evaluation_date) if board else ""
        event_text = re.sub(r"<[^>]+>", "", event_line_html).replace("Events ahead:", "").strip()
        decision_html = (
            _agreement_table_html(board, event_view=event_view, evaluation_date=evaluation_date)
            if board else
            f'<div class="notice bad">LANE BOARD FAILED — {_esc(board_error)}; showing the registered picks only.</div>{hero_html}'
        )
        body_html = (
            f"{_status_strip_html(data, research_views_status, context)}"
            f"{warn_html}"
            f"{_blocked_html(data.get('blocked') or [])}"
            f"{_position_tiles_html(data, event_text)}"
            f"{_open_slots_notice_html(qualified_picks)}"
            f"{decision_html}"
            f"{event_line_html}"
            f"{_pick_details_html(data, board, context=context, event_view=event_view, evaluation_date=evaluation_date, status_labels=status_labels) if board else symbols_html}"
            + _diagnostics_drawer_html([
                qm_lanes_html,
                _research_desk_html(data, context, context_warning, annotation_notice),
                _regime_strip_html(research_views_status, str(data.get("evaluation_date") or data_as_of)),
                _experiments_shelf_html(research_views_status),
                _quant_want_html(qm_context),
                _market_html(context),
                # relocated (spec §2.6) — appended AFTER the six, text unchanged
                _freshness_html(data, context, qm_context, research_views_status, context_evidence, annotation_integrity=annotation_integrity),
                age_html,
                _registered_bets_tracker_html(data),
                _composite_html(data),
                _pick_tracker_html(research_views_status),
            ])
        )
        nav_html = ""
    else:
        body_html = ( ...today's assembly, byte-identical... )
        nav_html = _sticky_nav_html(body_html, symbol_names)
```

and use `nav_html` where `_sticky_nav_html(...)` is interpolated at `:5737`.
`_open_slots_notice_html(qualified_picks)` renders today's consolidated
open-slot block (`_open_slots_html`, `:4104`) for `PICK_TOP_N - len(picks)`
slots and nothing when all slots are filled — implement as a 6-line wrapper
around the existing helper. Add the CSS classes used by Task 4
(`status-strip`, `dot`, `tiles`, `tile`, `agreement-table`, `chip.on/.warn/.veto`,
`agree`, `bar`, `event-line`, `lane-off`, `th-sub`, `group`) to `_STYLE`,
using the existing colour variables only.

`event_css` (`:5694-5695`) must also consider `event_line_html` and the
details HTML so the chip styles load when chips render only there.

- [ ] **Step 5: Run the layout tests, then the whole suite**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_layout.py' -v`
Expected: `LaneBoardLayoutTests` PASS; `test_flag_off_renders_the_legacy_page_byte_for_byte` PASS. Several
PRE-EXISTING layout tests now FAIL because they pin the old order — that is
Task 6's job; list them in the commit body.

Run: `uv run python -m unittest discover -s tests 2>&1 | tail -5`
Expected: failures only in `test_attractiveness_layout.py`,
`test_attractiveness_dashboard.py`, `test_event_awareness.py`; nothing else.
If any other file fails, STOP — that is a regression, not a contract change.

- [ ] **Step 6: Commit**

```bash
git add options_researcher/attractiveness_dashboard.py tests/test_attractiveness_layout.py tests/fixtures/attractiveness_legacy_layout.html
git commit -m "feat(board): wire the lane-board page order behind BOARD_LANES_ENABLED (legacy page byte-identical when off)"
```

---

### Task 6: Re-pin the two contracts (layout, event-chip parity)

**Files:**
- Modify: `tests/test_attractiveness_layout.py` (the tests that assert removed
  surfaces), `tests/test_attractiveness_dashboard.py` (same), `tests/test_event_awareness.py:311-460`
- Test: the same files

**Interfaces:** none new.

- [ ] **Step 1: Enumerate the failures**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_layout.py' 2>&1 | grep -E "^(FAIL|ERROR):"`
and the same for `test_attractiveness_dashboard.py` and `test_event_awareness.py`.
Paste the list into the PR body. Expected members (Repo-verified names, the
executor confirms): in the layout file `test_tracker_renders_before_the_shortlist_with_positions_kicker`
(`:165`), `test_clean_panels_are_closed_except_owner_pinned_symbols` (`:277`),
`test_panel_summary_is_one_line_with_source_asof_and_grade` (`:286`),
`test_frozen_eod_panels_name_their_source_in_the_summary` (`:296`),
`test_nav_links_every_present_section_and_symbol` (`:314`),
`test_nav_never_links_a_section_that_is_not_on_the_page` (`:326`),
`test_composite_board_is_one_table_with_every_label_preserved` (`:337`),
`test_blocked_angle_reason_is_still_printed` (`:364`),
`test_scoreboard_and_pinned_strip_stay_in_the_main_flow` (`:416`),
`test_symbol_panels_precede_the_drawer` (`:424`), and the empty-slot
consolidation tests (`:88-130`) if they locate the hero section by a removed
marker; in `test_event_awareness.py`,
`test_populated_hero_lane_context_and_pinned_surfaces_share_exact_chip_list` (`:311`)
and possibly `test_pure_render_all_card_surfaces_and_failure_notice` (`:215`).

- [ ] **Step 2: Re-pin each layout test to spec §2 — one decision per test**

For each failing layout test, decide and record in a comment above it:
(a) the assertion is about a surface that no longer exists → rewrite it to
the new surface with the SAME intent (e.g. "tracker before shortlist" becomes
"position tiles before the agreement table"; "composite is one table" becomes
"composite is one column with every angle label preserved in the column
title/notes"; "nav links every section" becomes "no sticky nav; every table
name has a details anchor"); or (b) the assertion still holds and only the
fixture needs `BOARD_LANES_ENABLED=False` → wrap it. Never delete a test. The
disclaimer, drawer, digest and zero-JS tests must pass without edits.

- [ ] **Step 3: Rewrite the chip-parity contract**

Replace `test_populated_hero_lane_context_and_pinned_surfaces_share_exact_chip_list`
(`tests/test_event_awareness.py:311`) with two tests that keep its intent:

```python
    def test_every_details_panel_renders_the_symbol_panels_exact_chip_list(self):
        # Spec §7: the per-name details fold-outs are the only per-name surface
        # left; each must render exactly what the symbol panel rendered before.
        html = self._render_populated()          # the existing fixture builder in this test class
        panels = re.findall(r'<details class="panel symbol-panel"[^>]*>(.*?)</details>', html, re.S)
        self.assertGreaterEqual(len(panels), 3)
        expected = chips(panels[0])
        self.assertGreaterEqual(len(expected), 3)
        for panel in panels:
            self.assertEqual(chips(panel), expected)

    def test_event_line_is_the_sorted_union_of_table_chips_printed_once(self):
        html = self._render_populated()
        line = html[html.index('class="event-line"'):]
        line = line[: line.index("</div>") + 6]
        table_chips = set()
        for panel in re.findall(r'<details class="panel symbol-panel"[^>]*>(.*?)</details>', html, re.S):
            table_chips |= set(chips(panel))
        self.assertEqual(chips(line), sorted(table_chips))
        for chip in table_chips:
            self.assertEqual(line.count(chip), 1)
```

`chips(...)` is the helper the original test already defines (`:436-440`
region); keep it.

- [ ] **Step 4: Run the three files, then the whole suite**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_*.py' -v 2>&1 | tail -5 && uv run python -m unittest discover -s tests -p 'test_event_awareness.py' -v 2>&1 | tail -5`
Expected: OK.
Run: `uv run python -m unittest discover -s tests 2>&1 | tail -3`
Expected: `OK` (skips allowed).

- [ ] **Step 5: Commit**

```bash
git add tests/test_attractiveness_layout.py tests/test_attractiveness_dashboard.py tests/test_event_awareness.py
git commit -m "test(board): re-pin layout and event-chip parity contracts to the lane-board page (spec §7)"
```

---

### Task 7: Parity proof, acceptance targets, lint, types, PR

**Files:**
- Test: `tests/test_attractiveness_layout.py` (two tests), `tests/test_board_lanes.py` (none)
- Modify: none (PR body)

- [ ] **Step 1: Write the parity and acceptance tests**

```python
class LaneBoardParityAndSizeTests(unittest.TestCase):
    def test_baseline_selection_and_snapshot_are_identical_flag_on_and_off(self):
        data = _board(["NVDA", "AMZN", "MSFT"])
        with mock.patch.object(config, "BOARD_LANES_ENABLED", False):
            off = ad.select_top_picks(data)
            off_html = ad.render(data)
        with mock.patch.object(config, "BOARD_LANES_ENABLED", True):
            on = ad.select_top_picks(data)
            on_html = ad.render(data)
        self.assertEqual([p["symbol"] for p in on], [p["symbol"] for p in off])
        digest_re = r"<!-- pick-tracker-digest:.*?-->"     # adjust to the real digest comment marker (see _render_source_row_hashes)
        self.assertEqual(re.findall(digest_re, on_html), re.findall(digest_re, off_html))

    def test_acceptance_targets_on_the_layout_fixture(self):
        with mock.patch.object(config, "BOARD_LANES_ENABLED", True):
            html = ad.render(_board(["NVDA", "AMZN", "MSFT", "PLTR", "SMCI", "CRWV", "CEG", "VST"]))
        above_drawer = html[: html.index('class="drawer"')]
        self.assertLessEqual(html.count("<h2"), 8)
        self.assertLessEqual(above_drawer.count("<details"), 20)
```

Executor note: locate the real digest-comment marker with
`grep -n "<!--" options_researcher/attractiveness_dashboard.py` and use it;
the assertion "the digest comment is identical with the flag on and off" is
the contract.

- [ ] **Step 2: Run tests**

Run: `uv run python -m unittest discover -s tests -p 'test_attractiveness_layout.py' -k LaneBoardParity -v`
Expected: PASS.

- [ ] **Step 3: Full gates**

```bash
uv run python -m unittest discover -s tests        # exit 0
uv run ruff check . && uv run pyright              # both clean
```

- [ ] **Step 4: Manual proof on Friday's data (orchestrator/owner runs it; you include the commands)**

```bash
ATTRACTIVENESS_INPUT_ROOT=/Users/carsynstephenson/options-validator-ops uv run python -m options_researcher.attractiveness_dashboard
wc -c .tmp/dashboard/attractiveness.html                          # target < 150000
grep -c "<h2" .tmp/dashboard/attractiveness.html                  # target <= 8
grep -c "<script" .tmp/dashboard/attractiveness.html              # 0
python3 -c "import json; d=json.load(open('.tmp/dashboard/picks_snapshot.json')); print([c['symbol'] for c in d['frozen_baseline']['candidates']])"
```

The snapshot symbol list must equal the pre-change list for the same session
(record both in the PR body).

- [ ] **Step 5: Commit and open the DRAFT PR**

```bash
git add tests/test_attractiveness_layout.py
git commit -m "test(board): parity (flag on/off) and acceptance-target tests"
git push -u origin <branch>
gh pr create --draft --title "Attractiveness board redesign — agreement table (brief 39)" --body-file <body.md>
```

PR body must contain: the spec path; the list of re-pinned tests with the
one-line intent decision for each; the H6 mark-age rule you used (Task 4
note); the digest-comment marker used; the Friday-data numbers (bytes, h2
count, details count, snapshot symbol list before/after); and the standard
authority boundary paragraph (draft; no ready/merge/sync/ledger).

---

## Acceptance / verification (whole brief)

```bash
uv run python -m unittest discover -s tests        # offline; exit code is the verdict
uv run ruff check . && uv run pyright              # both exit 0
ATTRACTIVENESS_INPUT_ROOT=~/options-validator-ops uv run python -m options_researcher.attractiveness_dashboard
```

Plus: `BOARD_LANES_ENABLED=False` byte-identity test green; parity test green;
`tests/test_board_lanes.py` ≥ 14 tests green; the three re-pinned files green
with no deleted tests; zero `<script`; every disclaimer verbatim; six drawer
sections in order.

Every constraint above is labelled; anything Codex finds that contradicts a
citation is a STOP-and-report, not a workaround. The implementation PR starts
as a GitHub draft; the executor may not make it ready, merge, deploy, sync
`~/options-validator-ops` or `~/options-validator-research`, or touch
`ledger/`. Green checks are review evidence for the owner, not landing
authority. First ritual after landing may raise the pick tracker's
`IMMUTABLE_HISTORY_CONFLICT` for an already-recorded session (board bytes
change); that is expected, fail-soft, and owner-only to resolve.
