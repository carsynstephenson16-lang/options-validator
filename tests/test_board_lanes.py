# tests/test_board_lanes.py
"""Unit tests for the lane-board display constants and the pure lane-board
module (spec docs/superpowers/specs/2026-09-06-attractiveness-board-redesign-design.md).
Nothing here asserts a ranking, a signal, or an authority change."""

import unittest
from pathlib import Path

import config
from options_researcher import board_lanes as bl


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


def _pick(symbol, lane="long_call"):
    # Real shape (attractiveness_dashboard.py:357-364): no top-level "status".
    return {
        "symbol": symbol,
        "lane": lane,
        "strike": 100.0,
        "expiry": "2026-09-16",
        "dte": 10,
        "score": 0,
        "card": {
            "headline": f"Buy the {symbol} call",
            "strike": 100.0,
            "expiry": "2026-09-16",
            "dte": 10,
            "cost": 300.0,
            "grades": {"liquidity": "GREEN"},
            "risk": {"max_loss": 300.0, "breakeven": 103.0},
            "top3_snapshot": {
                "candidate_id": f"{symbol}:{lane}:2026-09-16:100.00",
                "policy": {"status": "ELIGIBLE", "reason_codes": []},
            },
        },
    }


def _ctx_row(symbol, term=3, reason="ALIGNED", angles=("TREND", "REGIME", "INTERNALS")):
    return {
        "symbol": symbol,
        "lane": "long_call",
        "candidate_id": f"{symbol}:long_call",
        "score": (0,),
        "context_max_asof": "2026-09-03",
        "board_as_of": "2026-09-03",
        "context_term": term,
        "context_reason": reason,
        "aligned_angles": tuple(angles),
        "pick": _pick(symbol),
    }


def _comp(symbol, grade="A", aligned=3):
    return {
        "symbol": symbol,
        "asof": "2026-09-03",
        "max_asof": "2026-09-03",
        "grade": grade,
        "aligned_count": aligned,
        "trend": {"state": "UP"},
        "vol_premium": {"state": "RICH"},
        "regime": {"state": "TYPICAL"},
        "internals": {"state": "CONFIRM"},
    }


def _exp(symbol, state, **metric):
    card = {"symbol": symbol, "state": state, "experiment_id": "X", "asof": "2026-09-03"}
    card.update(metric)
    return card


def _board(**over):
    kwargs = dict(
        baseline_picks=[_pick("AMZN"), _pick("NVDA"), _pick("SMCI")],
        context_selection={
            "state": "READY",
            "error": None,
            "rows": [
                _ctx_row("AMZN"),
                _ctx_row("NVDA"),
                _ctx_row("SMCI", term=0, reason="VETOED", angles=()),
                _ctx_row("CRWV", term=0, reason="BLOCKED", angles=()),
            ],
        },
        composite_cards=[
            _comp("PLTR"),
            _comp("NVDA"),
            _comp("AMZN"),
            _comp("ET", "C", 2),
            _comp("VST", "C", 2),
            _comp("CEG", "C", 2),
            _comp("NBIS", "C", 2),
            _comp("AMD", "C", 1),
        ],
        qm_picks=[_pick("AMZN"), _pick("NVDA")],
        experiment_lanes={
            "exp_beta": [_exp("AMZN", "OK", beta=1.1), _exp("CEG", "UNSTABLE", beta=0.4)],
            "exp_tail": [
                _exp("NVDA", "UNSTABLE", jump_count=1),
                _exp("CEG", "UNSTABLE", jump_count=1),
            ],
            "exp_spread": [
                _exp("TEM", "ELEVATED", ratio=3.79),
                _exp("CEG", "ELEVATED", ratio=2.16),
            ],
            "exp_tbill": [
                _exp(s, "ABOVE_TBILL", carry_spread=v)
                for s, v in (
                    ("NBIS", 2.89),
                    ("IREN", 2.33),
                    ("CRWV", 1.90),
                    ("CLSK", 1.895),
                    ("USAR", 1.73),
                    ("SMCI", 1.76),
                    ("AMZN", 0.65),
                )
            ],
        },
        pinned=("VST", "AMZN"),
        # Real blocked-record shape (attractiveness_dashboard.py:1866-1870).
        blocked=[
            {
                "symbol": "ET",
                "reason_code": "DATA_BLOCKED",
                "detail": "chain 29 sessions old",
                "last_known_date": "2026-07-27",
                "unexpected": False,
            }
        ],
        cap=5,
        board_as_of="2026-09-03",
        qm_as_of="2026-09-03",
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
        self.assertEqual(
            [c.key for c in board.columns],
            ["baseline", "context", "composite", "qm", "tbill", "spread", "tail", "beta"],
        )
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
        self.assertEqual(
            set(_row(board, "CEG").marks) & {"beta", "tail", "spread"}, {"beta", "tail", "spread"}
        )

    def test_context_marks_other_than_aligned_are_shown_but_never_counted(self):
        board = _board()
        smci = _row(board, "SMCI")
        self.assertEqual(smci.marks["context"].label, "veto")
        self.assertFalse(smci.marks["context"].counts)
        self.assertEqual(smci.fav_count, 2)  # baseline #3 + tbill 1.76
        crwv = _row(board, "CRWV")
        self.assertEqual(crwv.marks["context"].label, "blocked")
        self.assertFalse(crwv.marks["context"].counts)
        self.assertEqual(crwv.fav_count, 1)  # tbill 1.90 only

    def test_ranking_lanes_are_capped_and_composite_ties_break_by_baseline_then_symbol(self):
        board = _board()
        comp = _col(board, "composite")
        # aligned=3: AMZN, NVDA (baseline rows first), PLTR; aligned=2: no baseline
        # row, so symbol order fills the last two slots (CEG, ET); NBIS/VST drop.
        self.assertEqual([m.symbol for m in comp.members], ["AMZN", "NVDA", "PLTR", "CEG", "ET"])

    def test_describing_lane_overflow_takes_largest_metric_and_says_so(self):
        board = _board()
        tbill = _col(board, "tbill")
        self.assertEqual(
            [m.symbol for m in tbill.members], ["NBIS", "IREN", "CRWV", "CLSK", "SMCI"]
        )
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
        board = _board(
            experiment_lanes={
                "exp_tbill": [
                    {
                        "symbol": "AMZN",
                        "state": "ERROR",
                        "experiment_id": "EXP-TBILL",
                        "reason": "boom",
                    }
                ]
            }
        )
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
        board = _board(
            experiment_lanes={},
            blocked=[
                {
                    "symbol": "IREN",
                    "reason_code": "DATA_BLOCKED",
                    "detail": "no chain",
                    "last_known_date": None,
                    "unexpected": False,
                }
            ],
        )
        iren = _row(board, "IREN")
        self.assertEqual(iren.block_reason, "DATA_BLOCKED · no chain")
        self.assertEqual(iren.fav_count, 0)
        self.assertFalse(iren.pinned)
        self.assertIsNone(iren.baseline_pick)

    def test_each_lane_carries_its_own_evidence_date_and_a_board_mismatch_is_marked(self):
        # Spec §5: every column carries ITS OWN as-of; a lane dated off the board's chain
        # session is marked. (Codex stop-and-report 2026-09-07: rev 6 stamped every column
        # with the board date and could not mark a mismatch.)
        board = _board(board_as_of="2026-09-04", qm_as_of="2026-09-04")
        self.assertEqual(_col(board, "baseline").as_of, "2026-09-04")  # the board's own cards
        self.assertFalse(_col(board, "baseline").as_of_mismatch)
        self.assertEqual(_col(board, "context").as_of, "2026-09-03")  # rows' context_max_asof
        self.assertTrue(_col(board, "context").as_of_mismatch)
        self.assertEqual(_col(board, "composite").as_of, "2026-09-03")  # cards' max_asof
        self.assertTrue(_col(board, "composite").as_of_mismatch)
        self.assertEqual(_col(board, "tbill").as_of, "2026-09-03")  # cards' asof
        self.assertTrue(_col(board, "tbill").as_of_mismatch)
        self.assertFalse(_col(board, "qm").as_of_mismatch)
        self.assertIn(
            "Context lane: evidence as of 2026-09-03 ≠ board session 2026-09-04", board.notes
        )
        self.assertEqual(
            sum(1 for c in board.columns if c.as_of_mismatch), 6
        )  # context, composite, 4 experiments

    def test_matching_dates_raise_no_mismatch_and_mixed_dates_inside_a_lane_take_the_latest(self):
        board = _board()  # every input dated 2026-09-03 == board_as_of
        self.assertFalse(any(c.as_of_mismatch for c in board.columns))
        self.assertFalse(any("≠ board" in n for n in board.notes))
        cards = [_comp("PLTR"), dict(_comp("NVDA"), max_asof="2026-09-02", asof="2026-09-02")]
        comp = _col(_board(composite_cards=cards), "composite")
        self.assertEqual(comp.as_of, "2026-09-03")
        self.assertIn("mixed as-of (earliest 2026-09-02)", comp.note)
        self.assertFalse(comp.as_of_mismatch)

    def test_a_ready_lane_with_no_evidence_date_is_marked_not_defaulted(self):
        board = _board(
            experiment_lanes={
                "exp_tbill": [
                    {
                        "symbol": "NBIS",
                        "state": "ABOVE_TBILL",
                        "carry_spread": 2.89,
                        "experiment_id": "EXP-TBILL",
                    }
                ]
            }
        )
        tbill = _col(board, "tbill")
        self.assertEqual(tbill.state, "READY")
        self.assertIsNone(tbill.as_of)
        self.assertTrue(tbill.as_of_mismatch)
        self.assertIn(
            "T-bill carry: evidence as of unknown ≠ board session 2026-09-03", board.notes
        )

    def test_build_never_mutates_inputs(self):
        picks = [_pick("AMZN")]
        before = repr(picks)
        _board(baseline_picks=picks)
        self.assertEqual(repr(picks), before)


class QmMixedDateTests(unittest.TestCase):
    def test_qm_preserves_earliest_evidence_date_in_the_column_note(self):
        board = _board(qm_as_of="2026-09-03", qm_earliest_as_of="2026-09-02")
        qm = _col(board, "qm")
        self.assertEqual(qm.as_of, "2026-09-03")
        self.assertIn("mixed as-of (earliest 2026-09-02)", qm.note)
        self.assertFalse(qm.as_of_mismatch)
