"""Board/session allocation resolver (7b-0.1). H7_LANE_PRIORITY and
H7C_TIEBREAK become ENFORCED runtime behavior, not documentation: the watcher
prints ENTRY-OK only for candidates that survive this resolution, and every
displaced candidate carries an explicit rejection reason."""

import random
import unittest

from options_researcher.h7_board import resolve_board


def C(symbol, lane, session="2026-07-09", cost=1000.0, credit=None, width=None):
    action = {"lane": lane, "cost": cost}
    if credit is not None:
        action = {"lane": lane, "credit": credit, "width": width,
                  "max_loss": (width - credit) * 100}
    return {"symbol": symbol, "lane": lane, "session": session,
            "action": action}


class TestLanePriority(unittest.TestCase):
    def test_lane_a_defeats_lane_b_on_one_underlying(self):
        accepted, rejected = resolve_board(
            [C("NVDA", "b"), C("NVDA", "a")], sleeve_left=6000.0)
        self.assertEqual([(c["symbol"], c["lane"]) for c in accepted],
                         [("NVDA", "a")])
        self.assertEqual(rejected[0]["rejection"], "lane_a_takes_underlying")

    def test_lane_priority_orders_same_session_allocation(self):
        # sleeve fits only one: a wins over b and c
        accepted, rejected = resolve_board(
            [C("PLTR", "c", credit=3.0, width=10.0),
             C("SMCI", "b", cost=900.0),
             C("NVDA", "a", cost=900.0)],
            sleeve_left=1000.0)
        self.assertEqual([(c["symbol"], c["lane"]) for c in accepted],
                         [("NVDA", "a")])
        reasons = {r["symbol"]: r["rejection"] for r in rejected}
        self.assertEqual(reasons["SMCI"], "sleeve_exhausted")
        self.assertEqual(reasons["PLTR"], "sleeve_exhausted")

    def test_chronological_order_beats_lane_priority(self):
        # an earlier-session lane-b opportunity outranks a later lane-a one
        accepted, _ = resolve_board(
            [C("NVDA", "a", session="2026-07-09", cost=900.0),
             C("SMCI", "b", session="2026-07-08", cost=900.0)],
            sleeve_left=1000.0)
        self.assertEqual([(c["symbol"], c["lane"]) for c in accepted],
                         [("SMCI", "b")])


class TestLaneC(unittest.TestCase):
    def test_two_same_session_h7c_higher_credit_to_width_wins(self):
        accepted, rejected = resolve_board(
            [C("PLTR", "c", credit=3.0, width=10.0),    # 0.30
             C("SMCI", "c", credit=2.0, width=5.0)],    # 0.40 wins
            sleeve_left=6000.0)
        self.assertEqual([c["symbol"] for c in accepted], ["SMCI"])
        self.assertEqual(rejected[0]["symbol"], "PLTR")
        self.assertEqual(rejected[0]["rejection"], "h7c_basket_cap")

    def test_exact_credit_to_width_tie_breaks_symbol_ascending(self):
        accepted, rejected = resolve_board(
            [C("SMCI", "c", credit=3.0, width=10.0),
             C("PLTR", "c", credit=3.0, width=10.0)],
            sleeve_left=6000.0)
        self.assertEqual([c["symbol"] for c in accepted], ["PLTR"])
        self.assertEqual(rejected[0]["rejection"], "h7c_basket_cap")

    def test_open_h7c_blocks_all_candidates(self):
        accepted, rejected = resolve_board(
            [C("PLTR", "c", credit=3.0, width=10.0)],
            open_h7c=1, sleeve_left=6000.0)
        self.assertEqual(accepted, [])
        self.assertEqual(rejected[0]["rejection"], "h7c_basket_cap")


class TestBookConstraints(unittest.TestCase):
    def test_open_underlying_rejects_candidate(self):
        accepted, rejected = resolve_board(
            [C("NVDA", "a")], sleeve_left=6000.0, open_symbols=("NVDA",))
        self.assertEqual(accepted, [])
        self.assertEqual(rejected[0]["rejection"], "underlying_open")

    def test_accepted_candidate_takes_the_underlying(self):
        # same underlying, two sessions: chronological winner takes it
        accepted, rejected = resolve_board(
            [C("NVDA", "a", session="2026-07-08", cost=900.0),
             C("NVDA", "a", session="2026-07-09", cost=900.0)],
            sleeve_left=6000.0)
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["session"], "2026-07-08")
        self.assertEqual(rejected[0]["rejection"], "underlying_taken")

    def test_sleeve_decrements_as_candidates_accept(self):
        accepted, rejected = resolve_board(
            [C("NVDA", "a", cost=900.0), C("SMCI", "a", cost=900.0)],
            sleeve_left=1500.0)
        self.assertEqual([c["symbol"] for c in accepted], ["NVDA"])
        self.assertEqual(rejected[0]["rejection"], "sleeve_exhausted")

    def test_closed_this_month_risk_still_consumes_the_sleeve(self):
        # the caller nets sleeve_left through open_h7_book, whose month_spent
        # includes rows opened-and-closed this month (durable accounting);
        # the resolver sees the already-reduced capacity.
        import tempfile
        from datetime import date
        from pathlib import Path

        from options_researcher.h7_watch import open_h7_book

        text = ("symbol,lane,opened,at_risk,closed\n"
                "NVDA,a,2026-07-02,5500,2026-07-06\n")
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "h7_positions.csv"
            p.write_text(text)
            _, _, month_spent = open_h7_book(date(2026, 7, 10), path=p)
        import config
        sleeve_left = config.H7_MONTHLY_AT_RISK - month_spent   # 500 left
        accepted, rejected = resolve_board(
            [C("SMCI", "a", cost=900.0)], sleeve_left=sleeve_left)
        self.assertEqual(accepted, [])
        self.assertEqual(rejected[0]["rejection"], "sleeve_exhausted")


class TestDeterminism(unittest.TestCase):
    def test_result_independent_of_input_iteration_order(self):
        base = [
            C("NVDA", "a", cost=2000.0),
            C("NVDA", "b", cost=1500.0),
            C("PLTR", "c", credit=3.0, width=10.0),
            C("SMCI", "c", credit=2.0, width=5.0),
            C("AMD", "b", cost=1800.0),
            C("AVGO", "a", session="2026-07-08", cost=1200.0),
        ]
        rng = random.Random(7)
        baseline = None
        for _ in range(12):
            shuffled = base[:]
            rng.shuffle(shuffled)
            accepted, rejected = resolve_board(shuffled, sleeve_left=6000.0)
            key = ([(c["symbol"], c["lane"], c["session"]) for c in accepted],
                   sorted((r["symbol"], r["lane"], r["rejection"])
                          for r in rejected))
            if baseline is None:
                baseline = key
            self.assertEqual(key, baseline)

    def test_every_displaced_candidate_has_a_reason(self):
        accepted, rejected = resolve_board(
            [C("NVDA", "a"), C("NVDA", "b"),
             C("PLTR", "c", credit=3.0, width=10.0),
             C("SMCI", "c", credit=2.0, width=5.0)],
            sleeve_left=100.0)
        self.assertEqual(len(accepted) + len(rejected), 4)
        for r in rejected:
            self.assertTrue(r["rejection"])
