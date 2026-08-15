"""Task 3 contracts for the local-only A2 one-run controller."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

import config
from options_researcher.a2_battery import LANE_COMPONENTS, A2Outcome
from options_researcher.a2_panel import A2AuditResult, A2Diagnostics
from options_researcher.a2_runner import (
    A2LocalInputs,
    A2RunnerError,
    CachePaths,
    OneRunError,
    _load_close_bundle,
    _load_earnings,
    _load_rates,
    _reconstruct_signals,
    build_report,
    run_once,
    validate_report,
)


def _outcome(symbol: str, *, decision: str = "2025-01-02", score: float = 1.0) -> A2Outcome:
    components = {name: 0.0 for name in LANE_COMPONENTS["csp"]}
    components["option_pnl"] = 0.05
    return A2Outcome(
        symbol=symbol,
        decision_date=decision,
        entry_date="2025-01-03",
        resolution_date="2025-01-10",
        lane="csp",
        arm="capture_50",
        score=score,
        gross_return=0.05,
        modeled_cost=0.01,
        bid_ask_cost=0.005,
        cost_adjusted_return=0.04,
        components=components,
        provenance={"source": "fixture", "contract_symbol": f"{symbol}-P"},
    )


def _audit(verdict: str = "WARN") -> A2AuditResult:
    return A2AuditResult(
        checks={number: () for number in range(1, 15)},
        verdict=verdict,
        warnings=(),
    )


class RunnerContracts(unittest.TestCase):
    def test_existing_report_refuses_before_governance_or_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "a2.json"
            report.write_text("{}", encoding="utf-8")
            with patch("options_researcher.a2_runner.validate_governance") as gate:
                with self.assertRaises(OneRunError):
                    run_once(
                        load_inputs=lambda _: self.fail("loader touched"),
                        report_path=report,
                        governance_dir=Path(tmp),
                    )
            gate.assert_not_called()

    def test_missing_registration_and_addendum_refuses_before_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "options_researcher.a2_runner.validate_governance",
                side_effect=A2RunnerError("registration evidence missing"),
            ) as gate:
                with self.assertRaisesRegex(A2RunnerError, "registration evidence"):
                    run_once(
                        load_inputs=lambda _: self.fail("loader touched"),
                        report_path=Path(tmp) / "a2.json",
                        governance_dir=Path(tmp),
                    )
            gate.assert_called_once()

    def test_blocked_audit_refuses_before_report_write(self):
        inputs = A2LocalInputs(
            signals={},
            chains={},
            raw_closes={},
            adjusted_closes={},
            audit=_audit("BLOCK"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            with patch("options_researcher.a2_runner.validate_governance", return_value={}):
                with self.assertRaisesRegex(A2RunnerError, "audit"):
                    run_once(
                        load_inputs=lambda _: inputs,
                        report_path=Path(tmp) / "a2.json",
                        governance_dir=Path(tmp),
                    )
            self.assertFalse((Path(tmp) / "a2.json").exists())

    def test_report_has_all_registered_variants_and_no_forward_verdict(self):
        rows = tuple(
            _outcome(symbol, score=float(index))
            for index, symbol in enumerate(config.A2_UNIVERSE, start=1)
        )
        report = build_report(
            outcomes=rows,
            signals={
                "2025-01-02": {
                    symbol: float(index) for index, symbol in enumerate(config.A2_UNIVERSE, start=1)
                }
            },
            audit=_audit(),
            governance={"registration_seq": 19, "registration_hash": "a" * 64},
            provenance={"chain_max_as_of": "2025-01-10", "close_max_as_of": "2025-01-10"},
        )
        self.assertEqual(report["schema"], "a2_outcome_battery_v1")
        self.assertEqual(
            set(report["lane_statuses"]), {"csp", "covered_call", "pmcc", "leaps", "tactical_call"}
        )
        self.assertEqual(len(report["variants"]), 13)
        self.assertNotIn("forward_verdict", report)
        self.assertIn("RESEARCH-ONLY / NO VERDICT", report["status"])
        validate_report(report)

    def test_incomplete_fifteen_name_cohort_is_descriptive_only(self):
        rows = tuple(_outcome(symbol) for symbol in config.A2_UNIVERSE[:-1])
        report = build_report(
            outcomes=rows,
            signals={
                "2025-01-02": {
                    symbol: float(index) for index, symbol in enumerate(config.A2_UNIVERSE, start=1)
                }
            },
            audit=_audit(),
            governance={"registration_seq": 19, "registration_hash": "a" * 64},
            provenance={},
        )
        csp = next(
            item
            for item in report["variants"]
            if item["lane"] == "csp" and item["arm"] == "capture_50"
        )
        self.assertEqual(csp["inference_count"], 0)
        self.assertEqual(csp["descriptive_count"], 14)
        self.assertEqual(csp["exclusions"]["incomplete_cohorts"], 1)

    def test_verified_report_can_retry_append_without_loader(self):
        rows = tuple(_outcome(symbol) for symbol in config.A2_UNIVERSE)
        inputs = A2LocalInputs(
            signals={}, chains={}, raw_closes={}, adjusted_closes={}, outcomes=rows, audit=_audit()
        )
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "a2.json"
            with patch("options_researcher.a2_runner.validate_governance", return_value={}):
                with patch(
                    "options_researcher.a2_runner._append_ledger_result",
                    side_effect=RuntimeError("temporary"),
                ):
                    with self.assertRaisesRegex(RuntimeError, "temporary"):
                        run_once(
                            load_inputs=lambda _: inputs,
                            report_path=report_path,
                            append_result=True,
                        )
            with patch("options_researcher.a2_runner.validate_governance", return_value={}):
                with patch(
                    "options_researcher.a2_runner._append_ledger_result", return_value="hash"
                ):
                    retry = run_once(
                        load_inputs=lambda _: self.fail("loader touched"),
                        report_path=report_path,
                        append_result=True,
                    )
            self.assertEqual(retry["schema"], "a2_outcome_battery_v1")

    def test_retry_revalidates_governance_before_append(self):
        rows = tuple(_outcome(symbol) for symbol in config.A2_UNIVERSE)
        inputs = A2LocalInputs(
            signals={
                "2025-01-02": {
                    symbol: float(index) for index, symbol in enumerate(config.A2_UNIVERSE, 1)
                }
            },
            chains={},
            raw_closes={},
            adjusted_closes={},
            outcomes=rows,
            audit=_audit(),
        )
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "a2.json"
            with patch("options_researcher.a2_runner.validate_governance", return_value={}):
                run_once(load_inputs=lambda _: inputs, report_path=report_path)
            with patch(
                "options_researcher.a2_runner.validate_governance",
                side_effect=A2RunnerError("facts changed"),
            ):
                with patch("options_researcher.a2_runner._append_ledger_result") as append:
                    with self.assertRaisesRegex(A2RunnerError, "facts changed"):
                        run_once(report_path=report_path, append_result=True)
                    append.assert_not_called()

    def test_fixture_report_does_not_mutate_scanner_source(self):
        source = Path("options_researcher/attractiveness.py")
        before = source.read_bytes()
        rows = tuple(
            _outcome(symbol, score=float(index))
            for index, symbol in enumerate(config.A2_UNIVERSE, 1)
        )
        build_report(
            outcomes=rows,
            signals={
                "2025-01-02": {
                    symbol: float(index) for index, symbol in enumerate(config.A2_UNIVERSE, 1)
                }
            },
            audit=_audit(),
            governance={},
            provenance={},
        )
        self.assertEqual(before, source.read_bytes())


class CachePathTests(unittest.TestCase):
    def test_cache_paths_are_absolute_and_local(self):
        paths = CachePaths.from_overrides(
            chain="/tmp/chain",
            underlying="/tmp/underlying",
            features="/tmp/features",
            rates="/tmp/rates",
            earnings="/tmp/earnings.csv",
            positions="/tmp/positions.csv",
        )
        self.assertTrue(all(path.is_absolute() for path in paths.as_tuple()))

    def test_close_loader_applies_split_adjustment_and_cutoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AMZN.csv"
            pd.DataFrame(
                {
                    "date": ["2022-06-03", "2022-06-06", "2026-07-01"],
                    "close": [2000.0, 100.0, 101.0],
                }
            ).to_csv(path, index=False)
            raw, adjusted = _load_close_bundle(Path(tmp))
        self.assertEqual(set(raw["AMZN"]), {"2022-06-03", "2022-06-06"})
        self.assertEqual(adjusted["AMZN"]["2022-06-03"], 100.0)
        self.assertEqual(adjusted["AMZN"]["2022-06-06"], 100.0)
        self.assertTrue(all(day <= config.BACKTEST_END for day in raw["AMZN"]))

    def test_canonical_earnings_loader_fails_closed_without_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gating_v3.csv"
            path.write_text("not,a,valid,store\n", encoding="utf-8")
            with self.assertRaisesRegex(A2RunnerError, "failed validation"):
                _load_earnings(path)

    def test_matched_tenor_rate_loader_keeps_rate_and_source_date(self):
        chain = pd.DataFrame(
            [
                {
                    "expiration": "2025-02-21",
                    "strike": 100.0,
                    "right": "P",
                    "bid": 2.0,
                    "ask": 2.2,
                    "open_interest": 500,
                    "delta": -0.2,
                    "contract_symbol": "AAA250221P00100000",
                }
            ]
        )
        result = SimpleNamespace(
            rate=0.031,
            provenance=SimpleNamespace(source_date=date(2025, 1, 2)),
        )
        with tempfile.TemporaryDirectory() as tmp:
            rate_path = Path(tmp) / "treasury_cmt.csv"
            rate_path.write_text("fixture", encoding="utf-8")
            with patch("data.rates.risk_free_rate", return_value=result) as resolver:
                rates, sources = _load_rates(rate_path, {"AAA": {"2025-01-03": chain}})
        self.assertEqual(rates, {"AAA": {"2025-01-03": 0.031}})
        self.assertEqual(sources, {"AAA:2025-01-03": "2025-01-02"})
        resolver.assert_called_once()

    def test_missing_causal_fomc_provenance_counts_and_produces_no_ranking(self):
        diagnostics = A2Diagnostics()
        inputs = A2LocalInputs(
            signals={},
            chains={},
            raw_closes={},
            adjusted_closes={},
            diagnostics=diagnostics,
        )
        self.assertEqual(_reconstruct_signals(inputs), {})
        self.assertEqual(diagnostics.skips["missing_causal_fomc_provenance"], 1)


if __name__ == "__main__":
    unittest.main()
