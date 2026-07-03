"""tests/test_charge_on_touch.py -- OOS charge-on-touch policy (pre-registration
decision doc 2026-07-03, §5).

Three interlocking behaviors:
  * run records carry a required `scope` ({"symbols": [...]}) so the reveal
    path can never guess which universe a hypothesis registered;
  * `oos_attempt` ledger records: the auditable "holdout data about to be
    touched" event, appended BEFORE the OOS backtest executes, and the budget
    counts TOUCHED hypotheses (attempts union reveals), not successful reveals;
  * the harness OOS seam unseals: it derives symbols + window from the
    registered record only, never from config.UNIVERSE.

All ledgers are temp dirs; no .cache/ dependency; git checks injected.
"""
import tempfile
import unittest
from unittest import mock

import config
from harness import run_backtest
from research import experiments, hashing, ledger

TEST_CODE_SHA = "e" * 40
TEST_CONFIG_HASH = "a" * 64
TEST_COST_MODEL_HASH = "b" * 64
TEST_SOURCE_HASH = "c" * 64
TEST_DATA_WINDOW_HASH = "d" * 64


def _run_body(hypothesis_id="H1", run_id="run1", scope=None):
    body = {
        "entry_type": "run",
        "timestamp": "2026-07-03T00:00:00+00:00",
        "run_id": run_id,
        "hypothesis_id": hypothesis_id,
        "decision_threshold": "expectancy CI lower bound > 0",
        "code_sha": TEST_CODE_SHA,
        "config_hash": TEST_CONFIG_HASH,
        "cost_model_hash": TEST_COST_MODEL_HASH,
        "source_hash": TEST_SOURCE_HASH,
        "data_window_hash": TEST_DATA_WINDOW_HASH,
        "risk_basis": "economic_max_loss",
        "is_window": {"start": "2018-01-01", "end": "2022-12-31"},
        "is_result": {"verdict": "x"},
        "oos_window": {"start": "2023-01-01", "end": "2026-06-30"},
        "oos_result": None,
        "deflated_sharpe": None,
        "pbo": None,
        "notes": "",
        "scope": {"symbols": ["SPY", "QQQ"]} if scope is None else scope,
    }
    if scope == "OMIT":
        del body["scope"]
    return body


def _window():
    return {"is_window": {"start": "2018-01-01", "end": "2022-12-31"},
            "oos_window": {"start": "2023-01-01", "end": "2026-06-30"}}


class RunScopeSchemaTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_run_with_scope_appends_and_verifies(self):
        ledger.append(_run_body(), self.base)
        ledger.verify(self.base)
        rec = ledger.read_all(self.base)[-1]
        self.assertEqual(rec["scope"], {"symbols": ["SPY", "QQQ"]})

    def test_run_without_scope_is_rejected(self):
        with self.assertRaises(ledger.LedgerError):
            ledger.append(_run_body(scope="OMIT"), self.base)

    def test_run_scope_rejects_malformed_shapes(self):
        bad_scopes = [
            {"symbols": []},                       # empty universe
            {"symbols": ["SPY", "SPY"]},           # duplicate would double-run
            {"symbols": ["spy"]},                  # not upper-case canonical
            {"symbols": [" SPY "]},                # untrimmed
            {"symbols": [""]},                     # empty symbol
            {"symbols": [123]},                    # non-string symbol
            {"symbols": "SPY"},                    # not a list
            {"symbols": ["SPY"], "extra": True},   # unknown scope key
            ["SPY"],                               # not an object
        ]
        for bad in bad_scopes:
            with self.subTest(scope=bad):
                with self.assertRaises(ledger.LedgerError):
                    ledger.append(_run_body(scope=bad), self.base)

    def test_verify_detects_hash_valid_run_missing_scope(self):
        ledger.append(_run_body(), self.base)
        records = ledger.read_all(self.base)
        del records[0]["scope"]
        body = {k: v for k, v in records[0].items() if k != "record_hash"}
        records[0]["record_hash"] = ledger._record_hash(body)
        jsonl = ledger._paths(self.base)[0]
        jsonl.write_text(hashing.canonical_json(records[0]) + "\n")
        ledger._paths(self.base)[1].write_text(records[0]["record_hash"] + "\n")
        with self.assertRaises(ledger.LedgerError):
            ledger.verify(self.base)


class RegisterScopeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name
        self.clean = lambda paths: True

    def tearDown(self):
        self._tmp.cleanup()

    def _register(self, scope, hyp="H1"):
        return experiments.register(
            hyp, "t", is_result={}, data_window=_window(), scope=scope,
            risk_basis="economic_max_loss", base_dir=self.base,
            code_sha=TEST_CODE_SHA, source_clean_tracked=self.clean)

    def test_register_writes_scope_into_the_run_record(self):
        self._register({"symbols": ["SPY", "QQQ"]})
        rec = ledger.read_all(self.base)[-1]
        self.assertEqual(rec["scope"], {"symbols": ["SPY", "QQQ"]})
        ledger.verify(self.base)

    def test_register_rejects_malformed_scope_as_gate_error(self):
        for bad in ({"symbols": []}, {"symbols": ["spy"]}, {"symbols": "SPY"},
                    None, {"symbols": ["SPY"], "x": 1}):
            with self.subTest(scope=bad):
                with self.assertRaises(experiments.OOSGateError):
                    self._register(bad, hyp="Hbad")


class OOSAttemptSchemaTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _attempt(self, hypothesis_id="H1", run_id="run1", budget_used=1,
                 budget_total=3):
        return {
            "entry_type": "oos_attempt",
            "timestamp": "2026-07-03T00:00:00+00:00",
            "hypothesis_id": hypothesis_id,
            "run_id": run_id,
            "budget_used": budget_used,
            "budget_total": budget_total,
        }

    def _reveal(self, hypothesis_id="H1", run_id="run1", budget_used=1,
                budget_total=3):
        return {
            "entry_type": "oos_reveal",
            "timestamp": "2026-07-03T00:00:00+00:00",
            "hypothesis_id": hypothesis_id,
            "run_id": run_id,
            "oos_result": {"verdict": "x"},
            "budget_used": budget_used,
            "budget_total": budget_total,
        }

    def test_attempt_appends_and_does_not_count_a_trial(self):
        ledger.append(_run_body(), self.base)
        ledger.append(self._attempt(), self.base)
        ledger.verify(self.base)
        records = ledger.read_all(self.base)
        self.assertEqual(records[-1]["entry_type"], "oos_attempt")
        self.assertEqual([r["trial_count"] for r in records], [1, 1])
        self.assertEqual(ledger.current_trial_count(self.base), 1)

    def test_attempt_without_registered_run_is_rejected(self):
        with self.assertRaises(ledger.LedgerError):
            ledger.append(self._attempt(), self.base)

    def test_attempt_with_mismatched_run_id_is_rejected(self):
        ledger.append(_run_body(run_id="run1"), self.base)
        with self.assertRaises(ledger.LedgerError):
            ledger.append(self._attempt(run_id="other"), self.base)

    def test_attempt_rejects_unknown_fields(self):
        ledger.append(_run_body(), self.base)
        bad = self._attempt()
        bad["oos_result"] = {"verdict": "smuggled"}
        with self.assertRaises(ledger.LedgerError):
            ledger.append(bad, self.base)

    def test_reveal_without_prior_attempt_is_rejected(self):
        ledger.append(_run_body(), self.base)
        with self.assertRaises(ledger.LedgerError):
            ledger.append(self._reveal(), self.base)

    def test_reveal_after_attempt_verifies(self):
        ledger.append(_run_body(), self.base)
        ledger.append(self._attempt(), self.base)
        ledger.append(self._reveal(), self.base)
        ledger.verify(self.base)

    def test_budget_counts_touched_hypotheses_not_reveals(self):
        ledger.append(_run_body("H1", "run1"), self.base)
        ledger.append(_run_body("H2", "run2"), self.base)
        # H1 touched (attempt, never revealed); H2 touched second.
        ledger.append(self._attempt("H1", "run1", budget_used=1), self.base)
        ledger.append(self._attempt("H2", "run2", budget_used=2), self.base)
        ledger.append(self._reveal("H2", "run2", budget_used=2), self.base)
        ledger.verify(self.base)

    def test_retry_attempt_for_same_hypothesis_keeps_budget_slot(self):
        ledger.append(_run_body(), self.base)
        ledger.append(self._attempt(budget_used=1), self.base)
        ledger.append(self._attempt(budget_used=1), self.base)  # crash retry
        ledger.verify(self.base)

    def test_attempt_with_inflated_budget_used_is_rejected(self):
        ledger.append(_run_body(), self.base)
        with self.assertRaises(ledger.LedgerError):
            ledger.append(self._attempt(budget_used=2), self.base)

    def test_budget_total_must_match_across_attempts_and_reveals(self):
        ledger.append(_run_body(), self.base)
        ledger.append(self._attempt(budget_total=3), self.base)
        with self.assertRaises(ledger.LedgerError):
            ledger.append(self._reveal(budget_total=4), self.base)


def _oos_trades():
    return [{"pnl": 1.0, "capital_at_risk": 100.0,
             "entry_date": "2023-06-01", "symbol": "SPY"}]


class ChargeOnTouchRevealTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name
        self.clean = lambda paths: True

    def tearDown(self):
        self._tmp.cleanup()

    def _register(self, hyp="H1"):
        experiments.register(hyp, "t", is_result={}, data_window=_window(),
                             scope={"symbols": ["SPY", "QQQ"]},
                             risk_basis="economic_max_loss", base_dir=self.base,
                             code_sha=TEST_CODE_SHA, source_clean_tracked=self.clean)

    def _reveal(self, hyp="H1", run_fn=_oos_trades):
        return experiments.reveal_oos(
            hyp, run_fn=run_fn, base_dir=self.base,
            scoreboard_fn=lambda t: {"verdict": "x"},
            git_clean_tracked=self.clean)

    def test_successful_reveal_writes_attempt_then_reveal(self):
        self._register()
        self._reveal()
        records = ledger.read_all(self.base)
        self.assertEqual([r["entry_type"] for r in records],
                         ["run", "oos_attempt", "oos_reveal"])
        self.assertEqual(records[1]["hypothesis_id"], "H1")
        self.assertEqual(records[1]["budget_used"], 1)
        ledger.verify(self.base)

    def test_attempt_is_charged_before_run_fn_executes(self):
        self._register()

        def crashing_run_fn():
            # the attempt record must already be on the ledger when the
            # holdout data path starts executing
            records = ledger.read_all(self.base)
            self.assertEqual(records[-1]["entry_type"], "oos_attempt")
            raise RuntimeError("backtest crashed mid-run")

        with self.assertRaises(RuntimeError):
            self._reveal(run_fn=crashing_run_fn)
        records = ledger.read_all(self.base)
        self.assertEqual([r["entry_type"] for r in records],
                         ["run", "oos_attempt"])
        ledger.verify(self.base)  # crashed attempt still leaves a valid chain

    def test_budget_exhausted_by_attempts_alone_refuses_new_hypothesis(self):
        for i in range(config.OOS_LOOK_BUDGET):
            self._register(f"H{i}")
            with self.assertRaises(RuntimeError):
                self._reveal(f"H{i}", run_fn=self._crash)
        self._register("Hnew")
        sentinel = mock.Mock(side_effect=AssertionError("run_fn must not run"))
        with self.assertRaises(experiments.OOSGateError):
            self._reveal("Hnew", run_fn=sentinel)
        sentinel.assert_not_called()
        # and no attempt record was written for the refused hypothesis
        touched = {r["hypothesis_id"] for r in ledger.read_all(self.base)
                   if r["entry_type"] == "oos_attempt"}
        self.assertNotIn("Hnew", touched)

    @staticmethod
    def _crash():
        raise RuntimeError("simulated infrastructure failure")

    def test_retry_after_crashed_attempt_completes_the_same_look(self):
        self._register()
        with self.assertRaises(RuntimeError):
            self._reveal(run_fn=self._crash)
        out = self._reveal()  # same hypothesis: completing the look, not a new one
        self.assertEqual(out["verdict"], "x")
        records = ledger.read_all(self.base)
        self.assertEqual([r["entry_type"] for r in records],
                         ["run", "oos_attempt", "oos_attempt", "oos_reveal"])
        self.assertEqual([r["budget_used"] for r in records[1:]], [1, 1, 1])

    def test_reveal_stays_write_once_after_success(self):
        self._register()
        self._reveal()
        with self.assertRaises(experiments.OOSGateError):
            self._reveal()


class HarnessOOSSeamTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name
        self.clean = lambda paths: True

    def tearDown(self):
        self._tmp.cleanup()

    def _register(self, hyp="H1", symbols=("SPY", "QQQ")):
        experiments.register(hyp, "t", is_result={}, data_window=_window(),
                             scope={"symbols": list(symbols)},
                             risk_basis="economic_max_loss", base_dir=self.base,
                             code_sha=TEST_CODE_SHA, source_clean_tracked=self.clean)

    def test_oos_backtest_derives_everything_from_the_registered_record(self):
        self._register()
        with mock.patch.object(run_backtest, "run",
                               return_value=_oos_trades()) as fake_run:
            trades = run_backtest._oos_backtest_trades("H1", base_dir=self.base)
        self.assertEqual(trades, _oos_trades())
        from strategies.put_credit_spread import PutCreditSpread
        fake_run.assert_called_once_with(
            PutCreditSpread, start="2023-01-01", end="2026-06-30",
            symbols=["SPY", "QQQ"], allow_oos=True)

    def test_oos_backtest_refuses_unregistered_hypothesis(self):
        with self.assertRaises(experiments.OOSGateError):
            run_backtest._oos_backtest_trades("Hmissing", base_dir=self.base)

    def test_reveal_out_of_sample_runs_the_registered_scope_end_to_end(self):
        # The dry-run rehearsal: registered record -> gates -> attempt record ->
        # (patched) offline backtest -> scoreboard -> reveal record.
        self._register()
        with mock.patch.object(run_backtest, "run",
                               return_value=_oos_trades()) as fake_run:
            out = run_backtest.reveal_out_of_sample(
                "H1", base_dir=self.base, git_clean_tracked=self.clean)
        self.assertIn("verdict", out)
        fake_run.assert_called_once()
        self.assertEqual(fake_run.call_args.kwargs["symbols"], ["SPY", "QQQ"])
        self.assertTrue(fake_run.call_args.kwargs["allow_oos"])
        records = ledger.read_all(self.base)
        self.assertEqual([r["entry_type"] for r in records],
                         ["run", "oos_attempt", "oos_reveal"])
        ledger.verify(self.base)


if __name__ == "__main__":
    unittest.main()
