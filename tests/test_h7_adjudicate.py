"""7b-2 C4: the H7 adjudicator's four-verdict vocabulary, loss gating, and
kill-not-bless language. 7b-2R.1 finding A: the CLI displays only
already-ledgered results; arbitrary JSON is never adjudicated."""

import contextlib
import io
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone

from research import diagnostics, ledger
from tools import h7_adjudicate
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


class TestGatedCLI(unittest.TestCase):
    """7b-2R.1 finding A: the CLI accepts a diagnostic id, refuses anything
    not already ledgered, and prints the STORED adjudication -- it never
    recomputes a verdict from caller-supplied input."""

    @staticmethod
    def _seed_result(base, adjudication):
        ledger.append({
            "entry_type": "trial_intent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hypothesis_id": "H7",
            "reason": "synthetic H7 registration",
        }, base_dir=base)
        diagnostics.record_diagnostic_attempt(
            diagnostic_id="H7a-diag-1", lane="a", symbols=["NVDA"],
            window={"start": "2018-01-02", "end": "2026-06-30"},
            estimand="isolated-lane non-blind diagnostic",
            data_manifest_hash="c" * 64, receipt_hash="b" * 64,
            base_dir=base)
        diagnostics.record_diagnostic_result(
            diagnostic_id="H7a-diag-1",
            result={"raw": {"trades": []}, "adjudication": adjudication},
            base_dir=base)

    def test_unledgered_id_is_refused_with_exit_2(self):
        with tempfile.TemporaryDirectory() as base:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = h7_adjudicate.main(["some-id"], base_dir=base)
        self.assertEqual(rc, 2)
        self.assertIn("never inspectable", buf.getvalue())

    def test_prints_only_the_stored_adjudication(self):
        stored = {"lane": "a", "verdict": "REJECTED", "n_trades": 30,
                  "n_losses": 30}
        with tempfile.TemporaryDirectory() as base:
            self._seed_result(base, stored)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = h7_adjudicate.main(["H7a-diag-1"], base_dir=base)
        self.assertEqual(rc, 0)
        self.assertIn('"REJECTED"', buf.getvalue())

    def test_cli_never_adjudicates_arbitrary_files(self):
        import inspect
        src = inspect.getsource(h7_adjudicate.main)
        self.assertNotIn("results_json", src)      # no file-path argument
        self.assertNotIn("adjudicate_lane(", src)  # never recomputes
