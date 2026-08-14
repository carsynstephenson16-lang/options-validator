"""Offline tests for the frequency-only H7 entry-variant menu tool (brief 09).

Everything here runs without network and without the real parquet cache:
underlying closes are synthesized into a tmpdir, and chain-shaped frames are
built in memory.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

import config
from data import underlying_closes
from data.underlying_closes import load_closes_adjusted
from options_researcher import h7_signals as sig
from options_researcher import h7_watch
from strategies import h7_lanes
from tools import h7_entry_variant_menu as menu


def _synthetic_closes(start: str, days: int, first: float = 100.0) -> pd.DataFrame:
    """A deterministic daily close series (calendar days; weekends included)."""
    index = pd.date_range(start=start, periods=days, freq="D")
    closes = [first + (i % 37) - (i % 11) * 0.5 for i in range(days)]
    return pd.DataFrame({"date": [d.date().isoformat() for d in index],
                         "close": closes})


def _write_closes(tmp: Path, symbol: str, frame: pd.DataFrame) -> None:
    tmp.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(tmp / f"{symbol}.parquet")


def _chain_frame(today: date, expiration: str) -> pd.DataFrame:
    """A minimal chain frame with the columns the frozen stack reads."""
    rows = []
    for strike in range(80, 121, 5):
        for right in ("C", "P"):
            rows.append({
                "right": right, "strike": float(strike), "expiration": expiration,
                "bid": 4.90, "ask": 5.00, "iv": 0.42, "open_interest": 5000,
                "delta": 0.60 if right == "C" else -0.25,
            })
    return pd.DataFrame(rows)


class IntegrityGuardTests(unittest.TestCase):
    """Brief 09's one hard rule, enforced by code rather than by intention."""

    def test_relaxing_fill_realism_constants_raises(self):
        for key in ("MIN_OPEN_INTEREST", "MAX_SPREAD_PCT", "H7_ADMIT_MAX_SPREAD_PCT",
                    "SLIPPAGE_HAIRCUT", "COMMISSION_PER_CONTRACT"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    menu.Variant(variant_id="BAD", axis="signal_threshold",
                                 rule_change="x", rationale_drift=menu.DRIFT_LOW,
                                 config_overrides={key: 0})

    def test_relaxing_the_earnings_gate_raises(self):
        for key in ("H7_EARNINGS_BAN_SESSIONS", "H7_POST_REPORT_GRACE_DAYS",
                    "H7_EARNINGS_POST_REPORT_GRACE_D"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    menu.Variant(variant_id="BAD", axis="signal_threshold",
                                 rule_change="x", rationale_drift=menu.DRIFT_LOW,
                                 config_overrides={key: 0})

    def test_unknown_config_constant_raises(self):
        with self.assertRaises(ValueError):
            menu.Variant(variant_id="BAD", axis="signal_threshold", rule_change="x",
                         rationale_drift=menu.DRIFT_LOW,
                         config_overrides={"H7_NOT_A_REAL_CONSTANT": 1})

    def test_outcome_shaped_keys_are_refused(self):
        for bad in ("pnl", "total_return", "win_rate", "expectancy", "sharpe_ratio",
                    "net_credit", "max_loss", "entry_cost"):
            with self.subTest(key=bad):
                with self.assertRaises(ValueError):
                    menu.assert_no_outcome_fields({"a": {"b": [{bad: 1}]}})

    def test_frequency_only_receipt_passes_the_guard(self):
        menu.assert_no_outcome_fields(
            {"entry_symbol_days": 4, "base_rate": 0.01,
             "entries_per_symbol": {"NOW": 2}})

    def test_no_shipped_variant_touches_a_frozen_realism_constant(self):
        for variant in menu.build_variants():
            self.assertFalse(
                set(variant.config_overrides) & menu.FORBIDDEN_OVERRIDE_KEYS,
                f"{variant.variant_id} relaxes a frozen realism constant")

    def test_written_receipts_are_scanned_before_landing(self):
        receipt = {"receipt_kind": "x", "win_rate": 0.9}
        receipt["receipt_hash"] = menu._receipt_hash(receipt)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                menu.write_receipt(receipt, Path(tmp) / "r.json")


class VariantApplicationTests(unittest.TestCase):
    def test_apply_and_restore_leaves_no_residue(self):
        before = (config.H7A_DRAWDOWN_MIN, config.H7_IV_PAR_K,
                  sig.lane_a_armed, sig.lane_b_armed,
                  h7_lanes.decide_lane_b, h7_watch.decide_lane_b)
        variant = menu.Variant(
            variant_id="T", axis="combination", rule_change="x",
            rationale_drift=menu.DRIFT_HIGH,
            config_overrides={"H7A_DRAWDOWN_MIN": 0.05, "H7_IV_PAR_K": 1.9},
            lane_a_mode=menu.LANE_MODE_OR, lane_b_mode=menu.LANE_MODE_OR,
            lane_b_edge_trigger=False)
        with menu.applied(variant):
            self.assertEqual(config.H7A_DRAWDOWN_MIN, 0.05)
            self.assertIs(sig.lane_a_armed, menu._lane_a_armed_or)
            self.assertIs(sig.lane_b_armed, menu._lane_b_armed_or)
            self.assertIs(h7_lanes.decide_lane_b, menu._decide_lane_b_no_edge)
            self.assertIs(h7_watch.decide_lane_b, menu._decide_lane_b_no_edge)
        self.assertEqual(
            before,
            (config.H7A_DRAWDOWN_MIN, config.H7_IV_PAR_K, sig.lane_a_armed,
             sig.lane_b_armed, h7_lanes.decide_lane_b, h7_watch.decide_lane_b))

    def test_restore_happens_even_when_the_body_raises(self):
        variant = menu.Variant(variant_id="T", axis="signal_threshold",
                               rule_change="x", rationale_drift=menu.DRIFT_LOW,
                               config_overrides={"H7A_DRAWDOWN_MIN": 0.01})
        original = config.H7A_DRAWDOWN_MIN
        with self.assertRaises(RuntimeError):
            with menu.applied(variant):
                raise RuntimeError("boom")
        self.assertEqual(config.H7A_DRAWDOWN_MIN, original)

    def test_or_arming_is_strictly_weaker_than_frozen_and_arming(self):
        closes = pd.Series(
            [100.0 - i * 0.1 for i in range(300)],
            index=pd.date_range("2024-01-01", periods=300, freq="D"))
        self.assertTrue(
            menu._lane_a_armed_or(closes) or not sig.lane_a_armed(closes))
        if sig.lane_a_armed(closes):
            self.assertTrue(menu._lane_a_armed_or(closes))
        if sig.lane_b_armed(closes):
            self.assertTrue(menu._lane_b_armed_or(closes))

    def test_arming_signature_shares_work_only_between_identical_arming(self):
        variants = {v.variant_id: v for v in menu.build_variants()}
        with menu.applied(variants["V0_BASELINE"]):
            baseline = menu.arming_signature(variants["V0_BASELINE"])
        # V5 changes only IV routing, so its arming must be shareable.
        with menu.applied(variants["V5_CLOSE_ROUTE_DEADZONE"]):
            self.assertEqual(menu.arming_signature(
                variants["V5_CLOSE_ROUTE_DEADZONE"]), baseline)
        # V1 changes the drawdown threshold, so it must NOT be shareable.
        with menu.applied(variants["V1_DRAWDOWN_15"]):
            self.assertNotEqual(
                menu.arming_signature(variants["V1_DRAWDOWN_15"]), baseline)
        # V9 changes only the predicate mode, which must also split the cache.
        with menu.applied(variants["V9_LANE_A_OR"]):
            self.assertNotEqual(
                menu.arming_signature(variants["V9_LANE_A_OR"]), baseline)


class ArmingShortCircuitTests(unittest.TestCase):
    """The measurement skips unarmed symbol-days. That is only sound because an
    unarmed lane can never reach ENTRY-OK in the FROZEN state ladder."""

    def test_unarmed_never_reaches_entry_ok_in_the_frozen_ladder(self):
        for gate in ("CLEAR", "BANNED", "UNKNOWN"):
            for admitted in (True, False):
                for route in ("call", "spread", "h7c", "none"):
                    for budget in (0.0, 6000.0):
                        for basket_full in (True, False):
                            state = h7_watch._lane_state(
                                armed=False, admitted=admitted, gate=gate,
                                has_open=False, route=route, budget_left=budget,
                                basket_full=basket_full)
                            self.assertNotEqual(state, "ENTRY-OK")

    def test_armed_and_otherwise_clear_does_reach_entry_ok(self):
        self.assertEqual(
            h7_watch._lane_state(armed=True, admitted=True, gate="CLEAR",
                                 has_open=False, route="call", budget_left=6000.0,
                                 basket_full=False),
            "ENTRY-OK")

    def test_assemble_name_yields_no_entry_when_both_predicates_are_false(self):
        today = date(2026, 5, 18)
        chain = _chain_frame(today, "2026-08-21")
        closes = pd.Series([100.0] * 300,
                           index=pd.date_range("2025-07-01", periods=300, freq="D"))
        saved = (sig.lane_a_armed, sig.lane_b_armed)
        try:
            sig.lane_a_armed = lambda _closes: False
            sig.lane_b_armed = lambda _closes: False
            card = h7_watch.assemble_name(
                symbol="NOW", closes=closes, chain=chain, today=today,
                assertions=[], known_as_of=None, open_positions=(), spot=100.0)
        finally:
            sig.lane_a_armed, sig.lane_b_armed = saved
        for lane in ("lane_a", "lane_b", "lane_c"):
            self.assertNotEqual(card[lane]["state"], "ENTRY-OK")


class CausalityTests(unittest.TestCase):
    def test_closes_window_never_reaches_past_the_decision_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_closes(root, "TEST", _synthetic_closes("2025-01-01", 600))
            data = menu.PanelData(underlying_dir=root)
            window = data.closes_window("TEST", "2026-03-02")
            self.assertEqual(str(window.index[-1])[:10], "2026-03-02")
            self.assertTrue(all(str(d)[:10] <= "2026-03-02" for d in window.index))

    def test_closes_window_matches_the_frozen_loader_exactly(self):
        for symbol in ("TEST", "NVDA", "AMZN"):
            with self.subTest(symbol=symbol):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    frame = _synthetic_closes("2020-01-01", 2200)
                    _write_closes(root, symbol, frame)
                    saved = underlying_closes.CACHE_DIR
                    try:
                        underlying_closes.CACHE_DIR = str(root)
                        session = "2025-06-02"
                        start = (date.fromisoformat(session)
                                 - timedelta(days=menu.CLOSES_WINDOW_DAYS)
                                 ).isoformat()
                        expected = load_closes_adjusted(
                            symbol, start, session, allow_oos=True)
                        actual = menu.PanelData(
                            underlying_dir=root).closes_window(symbol, session)
                    finally:
                        underlying_closes.CACHE_DIR = saved
                pd.testing.assert_series_equal(actual, expected)

    def test_window_length_matches_the_frozen_feasibility_tool(self):
        self.assertEqual(menu.CLOSES_WINDOW_DAYS, 560)


class StatisticsTests(unittest.TestCase):
    def test_clopper_pearson_reproduces_the_published_baseline_interval(self):
        low, high = menu.clopper_pearson(4, 1050)
        self.assertAlmostEqual(low * 1050, 1.0908582613, places=6)
        self.assertAlmostEqual(high * 1050, 10.2111831573, places=6)

    def test_clopper_pearson_edges(self):
        low, high = menu.clopper_pearson(0, 100)
        self.assertEqual(low, 0.0)
        self.assertGreater(high, 0.0)
        low, high = menu.clopper_pearson(100, 100)
        self.assertEqual(high, 1.0)
        self.assertLess(low, 1.0)

    def test_clopper_pearson_rejects_impossible_counts(self):
        with self.assertRaises(ValueError):
            menu.clopper_pearson(5, 4)
        with self.assertRaises(ValueError):
            menu.clopper_pearson(1, 0)

    def test_rolling_window_counts_are_hand_checkable(self):
        panel = [f"2026-01-{d:02d}" for d in range(1, 11)]
        result = menu.rolling_window_counts(
            ["2026-01-01", "2026-01-02"], panel, window=5)
        self.assertEqual(result["windows"], 6)
        self.assertEqual(result["max"], 2)
        self.assertEqual(result["min"], 0)
        self.assertAlmostEqual(result["zero_entry_window_fraction"], 4 / 6)

    def test_rolling_window_reports_short_panels_instead_of_guessing(self):
        result = menu.rolling_window_counts([], ["2026-01-01"], window=70)
        self.assertEqual(result["windows"], 0)
        self.assertIn("note", result)


class OccupancyTests(unittest.TestCase):
    """One position per underlying is the constraint the clean-book replay drops."""

    def setUp(self):
        self.panel = [f"2026-01-{d:02d}" for d in range(1, 21)]

    def test_repeat_entries_on_one_name_collapse_to_one(self):
        rows = [{"session": s, "symbol": "PLTR", "lane": "a"}
                for s in self.panel[:10]]
        self.assertEqual(len(rows), 10)
        self.assertEqual(
            menu.occupancy_constrained_count(rows, self.panel, 42), 1)

    def test_different_names_do_not_block_each_other(self):
        rows = [{"session": self.panel[0], "symbol": sym, "lane": "a"}
                for sym in ("PLTR", "NOW", "MSFT")]
        self.assertEqual(
            menu.occupancy_constrained_count(rows, self.panel, 42), 3)

    def test_lockout_expiry_allows_a_second_entry(self):
        rows = [{"session": self.panel[0], "symbol": "PLTR", "lane": "a"},
                {"session": self.panel[5], "symbol": "PLTR", "lane": "a"}]
        self.assertEqual(menu.occupancy_constrained_count(rows, self.panel, 5), 2)
        self.assertEqual(menu.occupancy_constrained_count(rows, self.panel, 6), 1)

    def test_occupancy_never_exceeds_the_unconstrained_count(self):
        rows = [{"session": s, "symbol": sym, "lane": "a"}
                for s in self.panel for sym in ("PLTR", "NOW")]
        for lockout in menu.OCCUPANCY_LOCKOUT_SESSIONS:
            self.assertLessEqual(
                menu.occupancy_constrained_count(rows, self.panel, lockout),
                len(rows))

    def test_zero_or_negative_lockout_is_refused(self):
        with self.assertRaises(ValueError):
            menu.occupancy_constrained_count([], self.panel, 0)

    def test_receipt_carries_the_occupancy_sensitivity(self):
        sessions = [f"2026-01-{d:02d}" for d in range(1, 8)]
        rows = [{"session": "2026-01-02", "symbol": "NOW", "lane": "a"},
                {"session": "2026-01-03", "symbol": "NOW", "lane": "a"}]
        receipt = menu.summarize_variant(
            variant=menu.build_variants()[0], panel_id="unit",
            panel_sessions=sessions,
            sessions_by_symbol={s: list(sessions)
                                for s in menu.resolve_universe("official_scope_15")},
            entry_rows=rows, error_rows=[], window_sessions=70, code_sha="a" * 40,
            baseline_config_hash="b" * 64,
            input_files={"x": {"path": "p", "sha256": "c" * 64}})
        self.assertEqual(receipt["entry_symbol_days"], 2)
        self.assertEqual(receipt["occupancy_constrained_entries"]["42"], 1)
        menu.assert_no_outcome_fields(receipt)


class BoardPolicyTests(unittest.TestCase):
    def _cand(self, symbol, lane, at_risk):
        key = "max_loss" if lane == "c" else "cost"
        return {"symbol": symbol, "lane": lane, "session": "2026-05-18",
                "action": {key: at_risk, "credit": 1.0, "width": 5.0}}

    def test_multi_lane_board_admits_two_lanes_on_one_underlying(self):
        accepted, rejected = menu.resolve_board_multi_lane(
            [self._cand("NOW", "a", 1000.0), self._cand("NOW", "b", 1000.0)],
            sleeve_left=6000.0)
        self.assertEqual(len(accepted), 2)
        self.assertEqual(rejected, [])

    def test_frozen_board_still_admits_only_one_lane_per_underlying(self):
        accepted, rejected = menu.resolve_board(
            [self._cand("NOW", "a", 1000.0), self._cand("NOW", "b", 1000.0)],
            sleeve_left=6000.0)
        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(rejected), 1)

    def test_multi_lane_board_still_enforces_the_registered_risk_cap(self):
        accepted, rejected = menu.resolve_board_multi_lane(
            [self._cand("NOW", "a", 4000.0), self._cand("NOW", "b", 4000.0)],
            sleeve_left=6000.0)
        self.assertEqual(len(accepted), 1)
        self.assertEqual([r["rejection"] for r in rejected], ["sleeve_exhausted"])

    def test_multi_lane_board_still_enforces_the_short_premium_cap(self):
        accepted, rejected = menu.resolve_board_multi_lane(
            [self._cand("NOW", "c", 100.0), self._cand("TEM", "c", 100.0)],
            sleeve_left=6000.0)
        self.assertEqual(len(accepted), config.H7C_MAX_CONCURRENT)
        self.assertTrue(any(r["rejection"] == "h7c_basket_cap" for r in rejected))

    def test_multi_lane_board_still_blocks_an_open_underlying(self):
        accepted, rejected = menu.resolve_board_multi_lane(
            [self._cand("NOW", "a", 100.0)], sleeve_left=6000.0,
            open_symbols=("NOW",))
        self.assertEqual(accepted, [])
        self.assertEqual([r["rejection"] for r in rejected], ["underlying_open"])


class ReceiptTests(unittest.TestCase):
    def _receipt(self, entry_rows=None):
        sessions = [f"2026-01-{d:02d}" for d in range(1, 8)]
        return menu.summarize_variant(
            variant=menu.build_variants()[0], panel_id="unit",
            panel_sessions=sessions,
            sessions_by_symbol={s: list(sessions)
                                for s in menu.resolve_universe("official_scope_15")},
            entry_rows=entry_rows or [],
            error_rows=[], window_sessions=70, code_sha="a" * 40,
            baseline_config_hash="b" * 64,
            input_files={"x": {"path": "p", "sha256": "c" * 64}})

    def test_receipt_hash_detects_tampering(self):
        receipt = self._receipt()
        self.assertTrue(menu.verify_receipt(receipt))
        receipt["entry_symbol_days"] = 99
        self.assertFalse(menu.verify_receipt(receipt))

    def test_receipt_arithmetic_is_hand_checkable(self):
        rows = [{"session": "2026-01-02", "symbol": "NOW", "lane": "a"},
                {"session": "2026-01-03", "symbol": "NOW", "lane": "b"}]
        receipt = self._receipt(rows)
        self.assertEqual(receipt["symbol_days"], 7 * 15)
        self.assertEqual(receipt["entry_symbol_days"], 2)
        self.assertAlmostEqual(receipt["base_rate"], 2 / 105)
        self.assertAlmostEqual(receipt["expected_entries_per_window"],
                               (2 / 105) * 70 * 15)
        self.assertEqual(receipt["entries_per_symbol"]["NOW"], 2)
        self.assertAlmostEqual(receipt["top_symbol_share"], 1.0)
        self.assertEqual(receipt["feasibility_entry_bar"], 20)

    def test_receipt_carries_no_outcome_field(self):
        menu.assert_no_outcome_fields(self._receipt())

    def test_clears_bar_uses_the_ci_lower_bound_not_the_point_estimate(self):
        receipt = self._receipt()
        low = receipt["expected_entries_ci95_exact"]["low"]
        self.assertEqual(receipt["clears_bar_ci_lower_ge_bar"],
                         low >= receipt["feasibility_entry_bar"])

    def test_receipt_is_immutable_once_written(self):
        receipt = self._receipt()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub" / "r.json"
            menu.write_receipt(receipt, path)
            menu.write_receipt(receipt, path)  # identical rewrite is a no-op
            other = self._receipt([{"session": "2026-01-02", "symbol": "NOW",
                                    "lane": "a"}])
            with self.assertRaises(FileExistsError):
                menu.write_receipt(other, path)
            self.assertTrue(menu.verify_receipt(json.loads(path.read_text())))

    def test_write_refuses_a_receipt_whose_hash_does_not_bind(self):
        receipt = self._receipt()
        receipt["entry_symbol_days"] = 42
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                menu.write_receipt(receipt, Path(tmp) / "r.json")


class ArmingCensusTests(unittest.TestCase):
    """The long panel measures the technical trigger only, and says so."""

    def test_coverage_floor_is_the_earliest_knowable_assertion(self):
        assertions = [{"known_as_of_utc": "2026-04-02T12:00:00+00:00"},
                      {"known_as_of_utc": "2026-07-28T12:00:00+00:00"}]
        self.assertEqual(menu.earnings_coverage_floor(assertions), "2026-04-02")

    def test_coverage_floor_handles_an_empty_panel(self):
        self.assertIsNone(menu.earnings_coverage_floor([]))
        self.assertIsNone(menu.earnings_coverage_floor([{"known_as_of_utc": None}]))

    def test_arming_only_reads_no_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_closes(root, "NOW", _synthetic_closes("2024-01-01", 700))
            data = menu.PanelData(underlying_dir=root)

            def _explode(*_args, **_kwargs):
                raise AssertionError("arming census must not read a chain")

            data.chain = _explode
            sessions = ["2025-10-0{}".format(i) for i in range(1, 8)]
            result = menu.measure_variants(
                variants=[menu.build_variants()[0]],
                sessions_by_symbol={"NOW": sessions}, data=data,
                assertions=[], arming_only=True)
            self.assertEqual(result["entries"]["V0_BASELINE"], [])
            self.assertIn("V0_BASELINE", result["armed"])

    def test_arming_receipt_declares_it_is_not_an_entry_rate(self):
        sessions = [f"2026-01-{d:02d}" for d in range(1, 8)]
        receipt = menu.summarize_arming(
            variant=menu.build_variants()[0], panel_id="unit",
            panel_sessions=sessions,
            sessions_by_symbol={s: list(sessions)
                                for s in menu.resolve_universe("official_scope_15")},
            armed_rows=[{"session": "2026-01-02", "symbol": "NOW",
                         "lane_a": True, "lane_b": False}],
            error_rows=[], window_sessions=70, code_sha="a" * 40,
            baseline_config_hash="b" * 64, coverage_floor="2026-04-02")
        self.assertIn("NOT an entry rate", receipt["what_this_is_not"])
        self.assertEqual(receipt["earnings_assertion_coverage_floor"], "2026-04-02")
        self.assertEqual(receipt["armed_symbol_days"], 1)
        self.assertEqual(receipt["armed_lane_a"], 1)
        self.assertEqual(receipt["armed_lane_b"], 0)
        self.assertTrue(menu.verify_receipt(receipt))
        menu.assert_no_outcome_fields(receipt)

    def test_arming_receipt_has_no_expected_entries_field(self):
        sessions = [f"2026-01-{d:02d}" for d in range(1, 8)]
        receipt = menu.summarize_arming(
            variant=menu.build_variants()[0], panel_id="unit",
            panel_sessions=sessions,
            sessions_by_symbol={s: list(sessions)
                                for s in menu.resolve_universe("official_scope_15")},
            armed_rows=[], error_rows=[], window_sessions=70, code_sha="a" * 40,
            baseline_config_hash="b" * 64, coverage_floor="2026-04-02")
        self.assertNotIn("expected_entries_per_window", receipt)
        self.assertNotIn("clears_bar_ci_lower_ge_bar", receipt)


class MenuDefinitionTests(unittest.TestCase):
    def test_variant_ids_are_unique(self):
        ids = [v.variant_id for v in menu.build_variants()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_identity_hash_changes_with_any_rule_change(self):
        variants = menu.build_variants()
        hashes = {v.identity_hash() for v in variants}
        self.assertEqual(len(hashes), len(variants))

    def test_baseline_variant_changes_nothing(self):
        baseline = menu.build_variants()[0]
        self.assertEqual(baseline.variant_id, "V0_BASELINE")
        self.assertEqual(baseline.config_overrides, {})
        self.assertEqual(baseline.lane_a_mode, menu.LANE_MODE_AND)
        self.assertEqual(baseline.lane_b_mode, menu.LANE_MODE_AND)
        self.assertTrue(baseline.lane_b_edge_trigger)
        self.assertEqual(baseline.board_policy, menu.BOARD_ONE_PER_UNDERLYING)
        self.assertEqual(baseline.rationale_drift, menu.DRIFT_NONE)

    def test_every_variant_declares_its_rationale_drift_in_plain_english(self):
        for variant in menu.build_variants():
            self.assertIn(variant.rationale_drift,
                          (menu.DRIFT_NONE, menu.DRIFT_LOW, menu.DRIFT_HIGH))
            self.assertGreater(len(variant.rule_change), 30)

    def test_or_restructuring_variants_declare_high_drift(self):
        for variant in menu.build_variants():
            if (variant.lane_a_mode == menu.LANE_MODE_OR
                    or variant.lane_b_mode == menu.LANE_MODE_OR):
                self.assertEqual(variant.rationale_drift, menu.DRIFT_HIGH,
                                 f"{variant.variant_id} restructures a trigger")

    def test_unknown_universe_label_is_refused(self):
        with self.assertRaises(ValueError):
            menu.resolve_universe("whatever_the_owner_did_not_authorize")


class NoNetworkSurfaceTests(unittest.TestCase):
    def test_direct_script_help_resolves_repo_imports(self):
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, "tools/h7_entry_variant_menu.py", "--help"],
            cwd=root, capture_output=True, text=True, timeout=120)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("FREQUENCY ONLY", completed.stdout)

    def test_module_imports_no_provider_client(self):
        source = (Path(__file__).resolve().parents[1]
                  / "tools" / "h7_entry_variant_menu.py").read_text()
        for banned in ("requests", "urllib", "httpx", "yfinance", "schwab",
                       "thetadata"):
            self.assertNotIn(f"import {banned}", source)


if __name__ == "__main__":
    unittest.main()
