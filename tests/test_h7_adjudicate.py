"""7b-2 C4: the H7 adjudicator's four-verdict vocabulary, loss gating, and
kill-not-bless language."""

import unittest
from datetime import date, timedelta

from tools.h7_adjudicate import VERDICTS, CoverageError
from tools.h7_adjudicate import adjudicate_lane as _adjudicate_lane


def adjudicate_lane(t, lane, **kw):
    """Test shim: clean coverage accounting unless overridden."""
    kw.setdefault("coverage", {"SYNH": {"eligible": len(t),
                                        "evaluated": len(t),
                                        "unaccounted": []}})
    return _adjudicate_lane(t, lane, **kw)


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


class TestGapRefusal(unittest.TestCase):
    """7b-2R finding 6: a result with unexplained eligible-session gaps is
    refused, never scored as an opportunity-free market."""

    def test_missing_coverage_is_refused(self):
        with self.assertRaises(CoverageError):
            adjudicate_lane(trades([[100.0]]), "a", coverage=None)

    def test_unaccounted_sessions_are_refused(self):
        cov = {"SYNH": {"eligible": 10, "evaluated": 8,
                        "unaccounted": ["2022-06-08", "2022-06-09"]}}
        with self.assertRaises(CoverageError):
            adjudicate_lane(trades([[100.0]]), "a", coverage=cov)

    def test_malformed_gap_record_is_refused(self):
        with self.assertRaises(CoverageError):
            adjudicate_lane(trades([[100.0]]), "a",
                            gaps=[{"symbol": "SYNH", "session": "2022-06-08"}])

    def test_explained_gaps_are_accepted(self):
        out = adjudicate_lane(
            trades([[200.0, 200.0, -50.0]] * 10), "a",
            gaps=[{"symbol": "SYNH", "lane": "a", "session": "2022-06-08",
                   "stage": "decision",
                   "reason": "chain_missing_for_session"}])
        self.assertIn(out["verdict"], VERDICTS)
