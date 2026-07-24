"""tests/test_score_backtest_cli.py -- read-only scoreboard command."""

import contextlib
import io
import json
import unittest
from unittest import mock

from tools import score_backtest


def _trade(pnl, entry_date, symbol):
    return {
        "pnl": pnl,
        "capital_at_risk": 100.0,
        "economic_max_loss": 102.60,
        "entry_date": entry_date,
        "symbol": symbol,
    }


class ScoreBacktestCliTests(unittest.TestCase):
    def test_json_mode_runs_in_sample_harness_with_requested_symbols(self):
        calls = []

        def fake_run(strategy_cls, start=None, end=None, *, symbols=None, allow_oos=False):
            calls.append({
                "strategy_cls": strategy_cls,
                "start": start,
                "end": end,
                "symbols": symbols,
                "allow_oos": allow_oos,
            })
            return [
                _trade(10.0, "2022-01-03", "SPY"),
                _trade(-5.0, "2022-01-10", "QQQ"),
            ]

        out = io.StringIO()
        with mock.patch.object(score_backtest.run_backtest, "run", fake_run):
            with contextlib.redirect_stdout(out):
                code = score_backtest.main([
                    "--symbols",
                    "SPY,QQQ",
                    "--start",
                    "2022-01-03",
                    "--end",
                    "2022-01-31",
                    "--json",
                ])

        self.assertEqual(code, 0)
        self.assertEqual(calls[0]["symbols"], ["SPY", "QQQ"])
        self.assertEqual(calls[0]["start"], "2022-01-03")
        self.assertEqual(calls[0]["end"], "2022-01-31")
        self.assertFalse(calls[0]["allow_oos"])
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["n_trades"], 2)
        self.assertEqual(payload["label"], "PutCreditSpread SPY,QQQ 2022-01-03..2022-01-31")

    def test_refuses_oos_end_before_running_backtest(self):
        err = io.StringIO()
        run = mock.Mock(side_effect=AssertionError("must not touch OOS"))

        with mock.patch.object(score_backtest.run_backtest, "run", run):
            with contextlib.redirect_stderr(err):
                code = score_backtest.main(["--symbols", "SPY", "--end", "2023-01-03"])

        self.assertEqual(code, 1)
        self.assertIn("past IN_SAMPLE_END", err.getvalue())
        run.assert_not_called()

    def test_dsr_off_by_default_adds_no_dsr_keys(self):
        def fake_run(strategy_cls, start=None, end=None, *, symbols=None, allow_oos=False):
            return [
                _trade(10.0, "2022-01-03", "SPY"),
                _trade(-5.0, "2022-01-10", "QQQ"),
            ]

        out = io.StringIO()
        with mock.patch.object(score_backtest.run_backtest, "run", fake_run):
            with contextlib.redirect_stdout(out):
                code = score_backtest.main(["--symbols", "SPY,QQQ", "--json"])

        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        for key in ("dsr", "psr_vs_zero", "dsr_n_trials", "dsr_n_provenance",
                    "dsr_note", "dsr_trial_sr_variance_input"):
            self.assertNotIn(key, payload)

    def test_dsr_ledger_source_requires_trial_sr_var(self):
        run = mock.Mock(side_effect=AssertionError("must not run the backtest"))
        err = io.StringIO()

        with mock.patch.object(score_backtest.run_backtest, "run", run):
            with contextlib.redirect_stderr(err):
                code = score_backtest.main(
                    ["--symbols", "SPY", "--dsr-n-source", "ledger"])

        self.assertEqual(code, 1)
        self.assertIn("--dsr-trial-sr-var is required", err.getvalue())
        run.assert_not_called()

    def test_dsr_ledger_source_reads_real_ledger_trial_count(self):
        def fake_run(strategy_cls, start=None, end=None, *, symbols=None, allow_oos=False):
            return [
                _trade(10.0, "2022-01-03", "SPY"),
                _trade(-5.0, "2022-01-10", "QQQ"),
            ]

        out = io.StringIO()
        with mock.patch.object(score_backtest.run_backtest, "run", fake_run):
            with contextlib.redirect_stdout(out):
                code = score_backtest.main([
                    "--symbols", "SPY,QQQ",
                    "--dsr-n-source", "ledger",
                    "--dsr-trial-sr-var", "0.05",
                    "--json",
                ])

        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["dsr_n_provenance"], "ledger-trial-count")
        self.assertEqual(
            payload["dsr_n_trials"], score_backtest.research_ledger.current_trial_count())
        self.assertEqual(payload["dsr_trial_sr_variance_input"], 0.05)
        # Only 2 trades in this fake run: below DSR_MIN_T -> the string path.
        self.assertEqual(payload["dsr"], "INSUFFICIENT SAMPLE FOR DSR")

    def test_dsr_ledger_source_echoes_variance_in_text_mode(self):
        def fake_run(strategy_cls, start=None, end=None, *, symbols=None, allow_oos=False):
            return [
                _trade(10.0, "2022-01-03", "SPY"),
                _trade(-5.0, "2022-01-10", "QQQ"),
            ]

        out = io.StringIO()
        with mock.patch.object(score_backtest.run_backtest, "run", fake_run):
            with contextlib.redirect_stdout(out):
                code = score_backtest.main([
                    "--symbols", "SPY,QQQ",
                    "--dsr-n-source", "ledger",
                    "--dsr-trial-sr-var", "0.05",
                ])

        self.assertEqual(code, 0)
        self.assertIn("DSR trial_sr_variance input", out.getvalue())
        self.assertIn("0.05", out.getvalue())


if __name__ == "__main__":
    unittest.main()
