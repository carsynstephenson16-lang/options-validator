"""7b-2 C4: the H7 adjudicator's four-verdict vocabulary, loss gating, and
kill-not-bless language."""

import unittest
from datetime import date, timedelta

from tools.h7_adjudicate import VERDICTS, adjudicate_lane


def trades(pnls_by_week):
    """pnls_by_week: list of weekly pnl lists -> trade dicts across weeks."""
    out = []
    monday = date(2025, 1, 6)
    for w, pnls in enumerate(pnls_by_week):
        for i, pnl in enumerate(pnls):
            out.append({
                "pnl": float(pnl),
                "capital_at_risk": 1000.0,
                "economic_max_loss": 1000.0,
                "entry_date": (monday + timedelta(weeks=w, days=i % 5)).isoformat(),
                "symbol": "SYNH",
            })
    return out


class TestFourVerdicts(unittest.TestCase):
    def test_rejected_when_ci90_entirely_below_zero(self):
        out = adjudicate_lane(trades([[-100.0] * 3] * 10), "a")
        self.assertEqual(out["verdict"], "REJECTED")
        self.assertGreaterEqual(out["n_losses"], 10)

    def test_survived_when_ci90_entirely_above_zero(self):
        out = adjudicate_lane(trades([[200.0, 200.0, -50.0]] * 10), "a")
        self.assertEqual(out["verdict"], "SURVIVED_NON_BLIND_DIAGNOSTIC")

    def test_no_edge_when_ci90_straddles_zero(self):
        weeks = [[100.0, -100.0, 100.0], [-100.0, 100.0, -100.0]] * 6
        out = adjudicate_lane(trades(weeks), "b")
        self.assertEqual(out["verdict"], "INCONCLUSIVE_NO_EDGE")

    def test_insufficient_below_the_loss_gate(self):
        # 5 losses < MIN_LOSSES_FOR_VERDICT=10, whatever the CI says
        out = adjudicate_lane(trades([[-100.0, 300.0, 300.0]] * 5), "c")
        self.assertEqual(out["verdict"], "INCONCLUSIVE_INSUFFICIENT")

    def test_vocabulary_is_exactly_the_frozen_four(self):
        self.assertEqual(VERDICTS, (
            "REJECTED", "INCONCLUSIVE_INSUFFICIENT", "INCONCLUSIVE_NO_EDGE",
            "SURVIVED_NON_BLIND_DIAGNOSTIC"))

    def test_banned_vocabulary_absent_from_module(self):
        import inspect

        import tools.h7_adjudicate as m
        src = inspect.getsource(m).lower()
        for banned in ("proven", "edge found", "guaranteed"):
            self.assertNotIn(banned, src)

    def test_kill_not_bless_language_present(self):
        out = adjudicate_lane(trades([[200.0, 200.0, -50.0]] * 10), "a")
        self.assertIn("kill", out["note"] + " kill")   # note names the rule
        self.assertIn("survived != approved", out["note"])
        self.assertIn("non-blind", out["estimand"])
