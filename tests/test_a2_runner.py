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
    RETROACTIVE_UNIVERSE_DISCLOSURE,
    A2LocalInputs,
    A2RunnerError,
    CachePaths,
    OneRunError,
    _causal_earnings,
    _causal_fomc,
    _common_feature_start,
    _load_chain_bundle,
    _load_close_bundle,
    _load_earnings,
    _load_feature_bundle,
    _load_fomc,
    _load_local_inputs,
    _load_rates,
    _merge_audits,
    _rank_cards,
    _reconstruct_signals,
    _variant_rows,
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
    maximum_resolution: str | None = None,
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
        maximum_resolution_date=maximum_resolution or resolution,
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
        # F5 (independent adversarial review, 2026-08-30): ledger seq 27's
        # mandatory permanent retroactivity disclosure is a required field.
        self.assertEqual(
            report["retroactive_universe_disclosure"], RETROACTIVE_UNIVERSE_DISCLOSURE
        )
        self.assertIn("2026-08 board applied retroactively", RETROACTIVE_UNIVERSE_DISCLOSURE)
        self.assertIn("outcome-informed", RETROACTIVE_UNIVERSE_DISCLOSURE)
        validate_report(report)

    def test_validate_report_rejects_a_report_missing_the_retroactivity_disclosure(self):
        rows = tuple(_outcome(symbol) for symbol in config.A2_UNIVERSE)
        report = build_report(
            outcomes=rows,
            signals={"2025-01-02": {symbol: 1.0 for symbol in config.A2_UNIVERSE}},
            audit=_audit(),
            governance={"registration_seq": 19, "registration_hash": "a" * 64},
            provenance=dict(_REALISM),
            realism_grade="fixture",
            realism_receipt=_receipt(),
        )
        tampered = dict(report)
        tampered.pop("retroactive_universe_disclosure")
        with self.assertRaisesRegex(OneRunError, "retroactivity disclosure"):
            validate_report(tampered)

    def test_partial_board_cohort_is_used_for_inference_not_rejected(self):
        # F1 (independent adversarial review, 2026-08-30): the board is the
        # names of config.ATTRACTIVENESS_UNIVERSE with cached data (a score)
        # at the cohort's formation date; a partial board (here, 14 of the 15
        # scored names actually resolved) is USED for inference -- skip, not
        # reject -- per A2_AMENDMENT_V1_1 (ledger seq 27) and the 2026-08-15
        # breach/weekly-cohort amendment Definition 2.1. This replaces the
        # old all-or-none 15-name gate the review found at
        # a2_runner.py:359,374 (config.A2_UNIVERSE exact-set equality).
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
        self.assertEqual(csp["inference_count"], 14)
        self.assertEqual(csp["descriptive_count"], 14)
        self.assertEqual(csp["exclusions"]["incomplete_cohorts"], 1)
        self.assertIn(config.A2_UNIVERSE[-1], csp["exclusions"]["missing_names"]["2025-01-02"])
        self.assertEqual(csp["exclusions"]["weeks_without_complete_board"], 0)
        self.assertEqual(csp["exclusions"]["weeks_skipped_unresolvable_board"], 0)
        self.assertEqual(csp["exclusions"]["per_cohort_name_counts"]["2025-01-02"], 14)

    def test_report_records_weekly_candidate_and_spacing_diagnostics(self):
        # F2 (independent adversarial review, 2026-08-30): candidate
        # selection is entry-time-only.  2025-01-06's scored board is
        # unusable at entry time (only one name), so it is never a
        # candidate regardless of resolved rows; 2025-01-07 (same ISO week,
        # full board, fully resolved) is chosen instead and counted as
        # "not the first session of the week".  2025-01-20 has a scored but
        # empty board that week -> weeks_without_complete_board.
        # 2025-01-13's board is usable and resolves, but its entry_date ties
        # the prior accepted cohort's ex-ante maximum resolution -> spacing
        # skip.
        rows = (
            *(
                _outcome(
                    symbol,
                    decision="2025-01-07",
                    entry="2025-01-08",
                    resolution="2025-01-09",
                    maximum_resolution="2025-01-14",
                )
                for symbol in config.A2_UNIVERSE
            ),
            *(
                _outcome(
                    symbol,
                    decision="2025-01-13",
                    entry="2025-01-14",
                    resolution="2025-01-15",
                    maximum_resolution="2025-01-17",
                )
                for symbol in config.A2_UNIVERSE
            ),
            *(
                _outcome(
                    symbol,
                    decision="2025-01-27",
                    entry="2025-01-28",
                    resolution="2025-01-29",
                    maximum_resolution="2025-01-31",
                )
                for symbol in config.A2_UNIVERSE
            ),
        )
        signal_board = {symbol: 1.0 for symbol in config.A2_UNIVERSE}
        report = build_report(
            outcomes=rows,
            signals={
                "2025-01-06": {config.A2_UNIVERSE[0]: 1.0},
                "2025-01-07": signal_board,
                "2025-01-13": signal_board,
                "2025-01-20": {},
                "2025-01-27": signal_board,
            },
            audit=_audit(),
            governance={},
            provenance=dict(_REALISM),
            realism_grade="fixture",
            realism_receipt=_receipt(),
        )
        capture = next(
            item
            for item in report["variants"]
            if item["lane"] == "csp" and item["arm"] == "capture_50"
        )
        self.assertEqual(capture["exclusions"]["accepted_board_not_first_session_of_week"], 1)
        self.assertEqual(capture["exclusions"]["weeks_without_complete_board"], 1)
        self.assertEqual(capture["exclusions"]["weeks_skipped_by_spacing"], 1)
        self.assertEqual(capture["exclusions"]["weeks_skipped_unresolvable_board"], 0)

    def test_unresolvable_entry_time_board_skips_the_week_without_promoting_a_later_session(self):
        # F2, runner-level regression: 2025-02-03's board is usable at entry
        # time (full 15 names scored) but NO rows ever resolved that day (a
        # post-entry data gap).  A later, fully-resolved session in the SAME
        # ISO week must never be substituted -- the week is skipped and
        # counted, not silently filled from a different day.
        signal_board = {symbol: 1.0 for symbol in config.A2_UNIVERSE}
        rows = tuple(
            _outcome(
                symbol,
                decision="2025-02-04",
                entry="2025-02-05",
                resolution="2025-02-06",
                maximum_resolution="2025-02-10",
            )
            for symbol in config.A2_UNIVERSE
        )
        report = build_report(
            outcomes=rows,
            signals={"2025-02-03": signal_board, "2025-02-04": signal_board},
            audit=_audit(),
            governance={},
            provenance=dict(_REALISM),
            realism_grade="fixture",
            realism_receipt=_receipt(),
        )
        capture = next(
            item
            for item in report["variants"]
            if item["lane"] == "csp" and item["arm"] == "capture_50"
        )
        self.assertEqual(capture["inference_count"], 0)
        self.assertEqual(capture["exclusions"]["weeks_skipped_unresolvable_board"], 1)
        self.assertEqual(capture["exclusions"]["weeks_without_complete_board"], 0)

    def test_report_discloses_breach_duplication_and_path_specific_skips(self):
        rows = []
        for index, symbol in enumerate(config.A2_UNIVERSE):
            rows.append(
                _outcome(
                    symbol,
                    arm="close_21_dte",
                    resolution="2025-01-10",
                    maximum_resolution="2025-01-10",
                )
            )
            rows.append(
                _outcome(
                    symbol,
                    arm="breach_hold_21_dte",
                    resolution="2025-01-10" if index < 10 else "2025-01-17",
                    maximum_resolution="2025-01-17",
                )
            )
        diagnostics = A2Diagnostics()
        diagnostics.skips.update(
            {
                "breach_hold_21_dte_breached_invalid_resolution_quote": 2,
                "breach_hold_21_dte_unbreached_missing_raw_close": 3,
            }
        )
        diagnostics.note_breach_on_expiry_settlement()
        diagnostics.note_breach_on_expiry_settlement()
        report = build_report(
            outcomes=tuple(rows),
            signals={"2025-01-02": {symbol: 1.0 for symbol in config.A2_UNIVERSE}},
            audit=_audit(),
            governance={},
            provenance=dict(_REALISM),
            diagnostics=diagnostics,
            realism_grade="fixture",
            realism_receipt=_receipt(),
        )
        breach = next(
            item
            for item in report["variants"]
            if item["lane"] == "csp" and item["arm"] == "breach_hold_21_dte"
        )
        self.assertEqual(
            breach["duplication_against_close_21_dte"],
            {"comparable_count": 15, "identical_resolution_count": 10, "rate": 2 / 3},
        )
        self.assertEqual(breach["breach_path_skip_counts"], {"breached": 2, "unbreached": 3})
        self.assertIn("all five CSP arms", breach["data_gap_propagation"])
        # F4: breach-on-expiration terminal-exception settlements are a
        # distinct, report-level counter, not folded into the skip counts.
        self.assertEqual(report["provenance"]["breach_on_expiry_settlements"], 2)

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
    def test_chain_loader_skips_non_a2_and_pre_common_start_before_reading(self):
        symbol = config.A2_UNIVERSE[0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pre = root / f"{symbol}_2024-12-31.parquet"
            kept = root / f"{symbol}_2025-01-02.parquet"
            other = root / "NOT_A2_2025-01-02.parquet"
            for path in (pre, kept, other):
                path.touch()
            counts: dict[str, int] = {}
            with patch(
                "options_researcher.a2_runner._frame", return_value=pd.DataFrame()
            ) as reader:
                loaded = _load_chain_bundle(root, common_start="2025-01-01", file_counts=counts)
        reader.assert_called_once_with(kept)
        self.assertEqual(set(loaded[symbol]), {"2025-01-02"})
        self.assertEqual(counts[symbol], 1)

    def test_common_feature_start_refuses_missing_a2_coverage(self):
        features = {
            symbol: pd.DataFrame({"rv21": [0.1]}, index=["2025-01-02"])
            for symbol in config.A2_UNIVERSE[:-1]
        }
        with self.assertRaisesRegex(A2RunnerError, "feature coverage"):
            _common_feature_start(features)

    def test_tracked_pit_fomc_calendar_is_causal_before_2025_decisions(self):
        path = Path(__file__).resolve().parents[1] / "data" / "events" / "fomc_pit.csv"
        frame = pd.read_csv(path)
        self.assertEqual(
            list(frame.columns),
            ["date", "known_as_of_utc", "source_url", "captured_at_utc", "status"],
        )
        self.assertEqual(len(frame), 16)
        self.assertEqual(set(frame["known_as_of_utc"]), {"2024-08-09T17:30:00+00:00"})
        self.assertEqual(
            set(frame["source_url"]),
            {"https://www.federalreserve.gov/newsevents/pressreleases/monetary20240809a.htm"},
        )
        self.assertEqual(set(frame["captured_at_utc"]), {"2026-08-15"})
        self.assertEqual(set(frame["status"]), {"tentative"})
        expected = [
            date.fromisoformat(value)
            for value in (
                "2025-01-29",
                "2025-03-19",
                "2025-05-07",
                "2025-06-18",
                "2025-07-30",
                "2025-09-17",
                "2025-10-29",
                "2025-12-10",
                "2026-01-28",
                "2026-03-18",
                "2026-04-29",
                "2026-06-17",
                "2026-07-29",
                "2026-09-16",
                "2026-10-28",
                "2026-12-09",
            )
        ]
        events = _load_fomc(path)
        self.assertEqual([event["date"] for event in events], expected)
        self.assertEqual(_causal_fomc(events, date(2025, 1, 28)), expected)
        self.assertEqual(_causal_fomc(events, date(2025, 1, 30)), expected[1:])

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

    def test_streaming_loader_releases_each_symbol_after_aggregation(self):
        # Three symbols: a two-name board sits below MIN_TERCILE_COHORT_SIZE
        # (F7b) and would never form an inference cohort, which would leave
        # this streaming/release-order test unable to observe the weekly
        # cohort at all.
        symbols = ("AAA", "BBB", "CCC")
        frame = pd.DataFrame({"rv21": [0.2]}, index=["2025-01-02"])
        raw = {symbol: {"2025-01-02": 100.0} for symbol in symbols}
        seen_chain_owners: list[frozenset[str]] = []
        seen_outcome_owners: list[frozenset[str]] = []
        seen_audit_owners: list[frozenset[str]] = []

        def load_chains(_path, **kwargs):
            owners = frozenset(kwargs.get("symbols", config.ATTRACTIVENESS_UNIVERSE))
            seen_chain_owners.append(owners)
            return {symbol: {"2025-01-02": pd.DataFrame({"symbol": [symbol]})} for symbol in owners}

        def reconstruct(inputs):
            return {"2025-01-02": {symbol: 1.0 for symbol in inputs.chains}}

        def build(**kwargs):
            owners = frozenset(kwargs["chains"])
            seen_outcome_owners.append(owners)
            return tuple(_outcome(symbol) for symbol in owners)

        def audit(**kwargs):
            owners = frozenset(kwargs["chains"])
            seen_audit_owners.append(owners)
            return A2AuditResult(
                checks={
                    number: ((f"{next(iter(owners))}-check-{number}",) if number == 1 else ())
                    for number in range(1, 15)
                },
                verdict="PASS WITH WARNINGS",
                warnings=(f"{next(iter(owners))}-warning",),
            )

        with tempfile.TemporaryDirectory() as tmp:
            paths = CachePaths.from_overrides(
                chain=f"{tmp}/chains",
                underlying=f"{tmp}/underlying",
                features=f"{tmp}/features",
                rates=f"{tmp}/rates",
                earnings=f"{tmp}/earnings.csv",
                positions=f"{tmp}/positions",
                fomc=f"{tmp}/fomc.csv",
            )
            with patch.object(config, "ATTRACTIVENESS_UNIVERSE", symbols):
                with patch(
                    "options_researcher.a2_runner._load_feature_bundle",
                    return_value={symbol: frame for symbol in symbols},
                ):
                    with patch(
                        "options_researcher.a2_runner._common_feature_start",
                        return_value="2025-01-01",
                    ):
                        with patch(
                            "options_researcher.a2_runner._load_chain_bundle",
                            side_effect=load_chains,
                        ):
                            with patch(
                                "options_researcher.a2_runner._load_close_bundle",
                                return_value=(raw, raw),
                            ):
                                with patch(
                                    "options_researcher.a2_runner._load_earnings",
                                    return_value=({}, {}),
                                ):
                                    with patch(
                                        "options_researcher.a2_runner._load_fomc", return_value=[]
                                    ):
                                        with patch(
                                            "options_researcher.a2_runner._load_positions",
                                            return_value=({}, "no data"),
                                        ):
                                            with patch(
                                                "options_researcher.a2_runner._load_rates",
                                                return_value=({}, {}),
                                            ):
                                                with patch(
                                                    "options_researcher.a2_runner._reconstruct_signals",
                                                    side_effect=reconstruct,
                                                ):
                                                    with patch(
                                                        "options_researcher.a2_runner.build_historical_outcomes",
                                                        side_effect=build,
                                                    ):
                                                        with patch(
                                                            "options_researcher.a2_runner.audit_historical_inputs",
                                                            side_effect=audit,
                                                        ):
                                                            inputs = _load_local_inputs(paths)

        self.assertEqual(
            seen_chain_owners, [frozenset({"AAA"}), frozenset({"BBB"}), frozenset({"CCC"})]
        )
        self.assertEqual(
            seen_outcome_owners, [frozenset({"AAA"}), frozenset({"BBB"}), frozenset({"CCC"})]
        )
        self.assertEqual(
            seen_audit_owners, [frozenset({"AAA"}), frozenset({"BBB"}), frozenset({"CCC"})]
        )
        self.assertEqual(inputs.chains, {})
        self.assertEqual(
            inputs.signals, {"2025-01-02": {"AAA": 1.0, "BBB": 1.0, "CCC": 1.0}}
        )
        self.assertEqual({row.symbol for row in inputs.outcomes or ()}, {"AAA", "BBB", "CCC"})
        self.assertEqual(inputs.audit.verdict if inputs.audit else None, "PASS WITH WARNINGS")
        self.assertEqual(
            inputs.audit.checks[1] if inputs.audit else (), ("AAA-check-1", "BBB-check-1", "CCC-check-1")
        )
        with patch.object(config, "ATTRACTIVENESS_UNIVERSE", symbols):
            inference, _descriptive, exclusions = _variant_rows(
                inputs.outcomes or (), inputs.signals, "csp", "capture_50"
            )
        self.assertEqual({row.symbol for row in inference}, set(symbols))
        self.assertTrue(exclusions["original_bucket_identity_preserved"])

    def test_merged_symbol_audits_preserve_all_checks_and_block_severity(self):
        first = A2AuditResult(
            checks={number: (("first",) if number == 1 else ()) for number in range(1, 15)},
            verdict="PASS WITH WARNINGS",
            warnings=("first warning",),
        )
        second = A2AuditResult(
            checks={number: (("second",) if number == 14 else ()) for number in range(1, 15)},
            verdict="BLOCK",
            warnings=("second warning",),
        )
        merged = _merge_audits((first, second))
        self.assertEqual(set(merged.checks), set(range(1, 15)))
        self.assertEqual(merged.checks[1], ("first",))
        self.assertEqual(merged.checks[14], ("second",))
        self.assertEqual(merged.warnings, ("first warning", "second warning"))
        self.assertEqual(merged.verdict, "BLOCK")

    def test_default_runner_does_not_rebuild_prebuilt_inputs(self):
        rows = tuple(
            _outcome(symbol, score=float(index))
            for index, symbol in enumerate(config.A2_UNIVERSE, 1)
        )
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
            diagnostics=A2Diagnostics(),
            audit=_audit(),
        )
        with tempfile.TemporaryDirectory() as tmp:
            with patch("options_researcher.a2_runner.validate_governance", return_value={}):
                with patch(
                    "options_researcher.a2_runner._load_local_inputs", return_value=inputs
                ) as loader:
                    with patch("options_researcher.a2_runner.build_historical_outcomes") as build:
                        with patch("options_researcher.a2_runner.audit_historical_inputs") as audit:
                            run_once(
                                report_path=Path(tmp) / "a2.json",
                                realism_grade="fixture",
                                realism_receipt=_receipt(),
                            )
        loader.assert_called_once()
        build.assert_not_called()
        audit.assert_not_called()

    def test_prebuilt_outcomes_do_not_trigger_signal_reconstruction(self):
        inputs = A2LocalInputs(
            signals={},
            chains={},
            raw_closes={},
            adjusted_closes={},
            outcomes=tuple(_outcome(symbol) for symbol in config.A2_UNIVERSE),
            diagnostics=A2Diagnostics(),
            audit=_audit(),
        )
        with tempfile.TemporaryDirectory() as tmp:
            with patch("options_researcher.a2_runner.validate_governance", return_value={}):
                with patch("options_researcher.a2_runner._load_local_inputs", return_value=inputs):
                    with patch(
                        "options_researcher.a2_runner._reconstruct_signals",
                        side_effect=self.fail,
                    ):
                        run_once(
                            report_path=Path(tmp) / "a2.json",
                            realism_grade="fixture",
                            realism_receipt=_receipt(),
                        )


if __name__ == "__main__":
    unittest.main()
