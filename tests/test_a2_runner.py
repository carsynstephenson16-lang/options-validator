"""Task 3 contracts for the local-only A2 one-run controller."""

from __future__ import annotations

import json
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
    ENTRY_CONVENTION_FACT_PAYLOAD,
    A2LocalInputs,
    A2RunnerError,
    CachePaths,
    OneRunError,
    _causal_earnings,
    _load_close_bundle,
    _load_earnings,
    _load_feature_bundle,
    _load_fomc,
    _load_rates,
    _rank_cards,
    _reconstruct_signals,
    build_report,
    run_once,
    validate_governance,
    validate_report,
)

_REALISM = {"realism_grade": "fixture"}


def _receipt() -> Path:
    handle = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
    handle.write("fixture reviewed realism receipt\n")
    handle.close()
    return Path(handle.name)


def _outcome(
    symbol: str,
    *,
    decision: str = "2025-01-02",
    entry: str = "2025-01-03",
    resolution: str = "2025-01-10",
    score: float = 1.0,
    arm: str = "capture_50",
) -> A2Outcome:
    components = {name: 0.0 for name in LANE_COMPONENTS["csp"]}
    components["option_pnl"] = 0.05
    return A2Outcome(
        symbol=symbol,
        decision_date=decision,
        entry_date=entry,
        resolution_date=resolution,
        lane="csp",
        arm=arm,
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
                        realism_grade="fixture",
                        realism_receipt=_receipt(),
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
                        realism_grade="fixture",
                        realism_receipt=_receipt(),
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
            provenance={
                "chain_max_as_of": "2025-01-10",
                "close_max_as_of": "2025-01-10",
                **_REALISM,
            },
            realism_grade="fixture",
            realism_receipt=_receipt(),
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
            provenance=dict(_REALISM),
            realism_grade="fixture",
            realism_receipt=_receipt(),
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
                            realism_grade="fixture",
                            realism_receipt=_receipt(),
                        )
            with patch("options_researcher.a2_runner.validate_governance", return_value={}):
                with patch(
                    "options_researcher.a2_runner._append_ledger_result", return_value="hash"
                ):
                    retry = run_once(
                        load_inputs=lambda _: self.fail("loader touched"),
                        report_path=report_path,
                        append_result=True,
                        realism_grade="fixture",
                        realism_receipt=_receipt(),
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
                run_once(
                    load_inputs=lambda _: inputs,
                    report_path=report_path,
                    realism_grade="fixture",
                    realism_receipt=_receipt(),
                )
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
            provenance=dict(_REALISM),
            realism_grade="fixture",
            realism_receipt=_receipt(),
        )
        self.assertEqual(before, source.read_bytes())

    def test_missing_reviewed_realism_grade_refuses_report(self):
        rows = tuple(_outcome(symbol) for symbol in config.A2_UNIVERSE)
        with self.assertRaisesRegex(A2RunnerError, "realism"):
            build_report(
                outcomes=rows,
                signals={"2025-01-02": {symbol: 1.0 for symbol in config.A2_UNIVERSE}},
                audit=_audit(),
                governance={},
                provenance={},
            )

    def test_realism_receipt_requires_existing_absolute_file(self):
        for receipt in ("fixture", Path("relative-receipt.md")):
            with self.subTest(receipt=receipt), self.assertRaisesRegex(A2RunnerError, "receipt"):
                build_report(
                    outcomes=(),
                    signals={},
                    audit=_audit(),
                    governance={},
                    provenance=dict(_REALISM),
                    realism_grade="fixture",
                    realism_receipt=receipt,
                )
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing-receipt.md"
            with self.assertRaisesRegex(A2RunnerError, "receipt"):
                build_report(
                    outcomes=(),
                    signals={},
                    audit=_audit(),
                    governance={},
                    provenance=dict(_REALISM),
                    realism_grade="fixture",
                    realism_receipt=missing,
                )

    def test_audit_keys_must_be_exactly_one_through_fourteen(self):
        bad = A2AuditResult(checks={1: ()}, verdict="WARN", warnings=())
        with self.assertRaisesRegex(A2RunnerError, "fourteen"):
            build_report(
                outcomes=(),
                signals={},
                audit=bad,
                governance={},
                provenance=dict(_REALISM),
            )

    def test_absolute_override_is_required_and_fomc_is_a_cache_input(self):
        with self.assertRaises(ValueError):
            CachePaths.from_overrides(fomc="relative/fomc.csv")
        paths = CachePaths.from_overrides(fomc="/tmp/fomc.csv")
        self.assertEqual(paths.fomc, Path("/tmp/fomc.csv").resolve())

    def test_exact_fact_payload_is_required_not_a_substring(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "experiments.jsonl").write_text(
                json.dumps(
                    {
                        "seq": 19,
                        "record_hash": "684b59a2bf322a96ae375cd7b857706775eea2b971ffc456a4b09f40cb0383a2",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            facts = base / "facts.log"
            facts.write_text(
                "2026-08-15T00:00:00+00:00\tRQ2_A2_PIN_ADDENDUM_V1 source=reports/2026-07-23-pin-addendum-validation.md\n"
                f"2026-08-15T00:00:00+00:00\t{ENTRY_CONVENTION_FACT_PAYLOAD}\n",
                encoding="utf-8",
            )
            self.assertEqual(
                validate_governance(base)["entry_convention_fact"],
                "A2_ENTRY_CONVENTION_ADDENDUM_V1",
            )
            facts.write_text(
                facts.read_text(encoding="utf-8").replace(
                    "status=historical-entry-convention-complete", "status=spoofed"
                ),
                encoding="utf-8",
            )
            with self.assertRaises(A2RunnerError):
                validate_governance(base)

    def test_multi_arm_holm_family_is_applied_after_raw_values_exist(self):
        rows = []
        for arm in config.A2_CSP_ARMS:
            rows.extend(_outcome(symbol, arm=arm) for symbol in config.A2_UNIVERSE)
            rows.extend(
                _outcome(
                    symbol,
                    arm=arm,
                    decision="2025-01-13",
                    entry="2025-01-14",
                    resolution="2025-01-20",
                )
                for symbol in config.A2_UNIVERSE
            )
        with patch(
            "options_researcher.a2_battery._permutation_result",
            return_value=(0.01, 0.1, (0.0, 0.2)),
        ):
            report = build_report(
                outcomes=rows,
                signals={
                    "2025-01-02": {symbol: 1.0 for symbol in config.A2_UNIVERSE},
                    "2025-01-13": {symbol: 1.0 for symbol in config.A2_UNIVERSE},
                },
                audit=_audit(),
                governance={},
                provenance=dict(_REALISM),
                realism_grade="fixture",
                realism_receipt=_receipt(),
            )
        csp = [item for item in report["variants"] if item["lane"] == "csp"]
        self.assertEqual({item["holm_family_size"] for item in csp}, {5})
        self.assertTrue(all(item["holm_family_complete"] for item in csp))

    def test_fomc_loader_rejects_legacy_dates_only_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fomc.csv"
            path.write_text("date,source_url\n2025-01-29,https://fed.example\n", encoding="utf-8")
            with self.assertRaisesRegex(A2RunnerError, "provenance"):
                _load_fomc(path)

    def test_fomc_loader_accepts_timezone_provenance_and_hashable_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fomc.csv"
            path.write_text(
                "date,known_as_of_utc,source_id\n2025-01-29,2025-01-01T12:00:00+00:00,fed-calendar-v1\n",
                encoding="utf-8",
            )
            events = _load_fomc(path)
        self.assertEqual(events[0]["date"], date(2025, 1, 29))
        self.assertEqual(events[0]["source_id"], "fed-calendar-v1")

    def test_feature_loader_filters_post_cutoff_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AAA_features.csv"
            pd.DataFrame({"date": ["2025-01-02", "2026-07-01"], "rv21": [0.1, 0.9]}).to_csv(
                path, index=False
            )
            loaded = _load_feature_bundle(Path(tmp))
        self.assertEqual(list(loaded["AAA"].index), ["2025-01-02"])

    def test_feature_loader_rejects_malformed_in_scope_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AAA_features.csv"
            pd.DataFrame({"date": ["not-a-date"], "rv21": [0.1]}).to_csv(path, index=False)
            with self.assertRaises(A2RunnerError):
                _load_feature_bundle(Path(tmp))

    def test_actual_card_ordering_uses_local_frozen_green_fraction(self):
        cards = [
            {"grades": {"a": "GREEN"}, "expiry": "2025-02-21", "id": "late"},
            {"grades": {"a": "GREEN", "b": "GREEN"}, "expiry": "2025-01-17", "id": "best"},
        ]
        ordered = _rank_cards(cards)
        self.assertEqual([card["id"] for card in ordered], ["late", "best"])

    def test_fixture_signal_reconstruction_preserves_card_snapshot(self):
        symbol = config.A2_UNIVERSE[0]
        chain = pd.DataFrame(
            [
                {
                    "expiration": expiry,
                    "right": right,
                    "strike": 100.0,
                    "bid": 2.0,
                    "ask": 2.2,
                    "open_interest": 500,
                    "delta": delta,
                    "iv": 0.3,
                    "vega": 0.1,
                    "theta": -0.01,
                    "gamma": 0.02,
                }
                for expiry in ("2025-01-17", "2025-02-07")
                for right, delta in (("P", -0.2), ("C", 0.2))
            ]
        )
        features = pd.DataFrame(
            {"rv21": [0.2], "iv_rank": [0.4], "iv_minus_rv": [0.1]},
            index=["2025-01-02"],
        )
        inputs = A2LocalInputs(
            signals={},
            chains={symbol: {"2025-01-02": chain}},
            raw_closes={symbol: {"2025-01-02": 100.0}},
            adjusted_closes={symbol: {"2025-01-02": 100.0}},
            features={symbol: features},
            fomc_events=[],
        )

        from options_researcher.attractiveness import (
            ladder_cards,
            long_call_card_rows,
            put_card_rows,
        )

        def card_snapshot():
            cards = []
            cards.extend(
                ladder_cards(
                    put_card_rows,
                    symbol,
                    chain,
                    "2025-01-02",
                    rank_key="annualized_yield",
                    higher_is_better=True,
                    close=100.0,
                    rv21=0.2,
                    iv_rank=0.4,
                    iv_minus_rv=0.1,
                    earnings_dates=[],
                    fomc_dates=[],
                )
            )
            cards.extend(
                ladder_cards(
                    long_call_card_rows,
                    symbol,
                    chain,
                    "2025-01-02",
                    rank_key="breakeven_move",
                    higher_is_better=False,
                    close=100.0,
                    iv_rank=0.4,
                )
            )
            return json.dumps(cards, sort_keys=True, default=str)

        before = card_snapshot()
        signals = _reconstruct_signals(inputs)
        build_report(
            outcomes=(),
            signals={},
            audit=_audit(),
            governance={},
            provenance=dict(_REALISM),
            realism_grade="fixture",
            realism_receipt=_receipt(),
        )
        after = card_snapshot()
        self.assertEqual(before, after)
        self.assertEqual(_reconstruct_signals(inputs), signals)
        self.assertIn(symbol, signals["2025-01-02"])


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

    def test_causal_earnings_rejects_missing_known_timestamp(self):
        inputs = A2LocalInputs(
            signals={},
            chains={},
            raw_closes={},
            adjusted_closes={},
            earnings_records={"AAA": ({"event_date": "2025-01-20"},)},
        )
        with self.assertRaisesRegex(A2RunnerError, "known_as_of_utc"):
            _causal_earnings(inputs, "AAA", "2025-01-02")


if __name__ == "__main__":
    unittest.main()
