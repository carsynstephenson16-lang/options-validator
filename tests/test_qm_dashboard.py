"""Fail-closed tests for the QM context consumed by the six-card board."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import config
from options_researcher import attractiveness_dashboard as ad
from options_researcher import qm_dashboard


def _frame(*, periods: int = 220, end: str = "2026-07-01") -> pd.DataFrame:
    index = [d.date().isoformat() for d in pd.bdate_range(end=end, periods=periods)]
    closes = [100.0 + i for i in range(periods)]
    return pd.DataFrame(
        {
            "open": closes,
            "high": [value * 1.01 for value in closes],
            "low": [value * 0.99 for value in closes],
            "close": closes,
            "volume": [1_000_000.0] * periods,
        },
        index=index,
    )


def _study(symbol: str = "AAA") -> dict:
    return {
        "schema_version": 1,
        "study": {
            "data_vintage": "2026-07-14",
            "breakout": {"fires": 11, "evidence_status": "DESCRIPTIVE_ONLY"},
            "parabolic": {"fires": 35, "evidence_status": "FADE_REJECTED"},
        },
        "symbols": {
            symbol: {
                "breakout_fire_dates": ["2026-06-29"],
                "parabolic_fire_dates": [],
            }
        },
        "thesis": "A qualifying base can precede continuation.",
        "counter_case": "Small hindsight-selected sample; option P&L was not tested.",
        "provenance": "Frozen QM report.",
    }


def _bound_source(report: Path, ledger: Path) -> dict[str, str]:
    fact = "2026-07-14T00:00:00+00:00\tQM_STUDY_RESULT 2026-07-14: frozen"
    ledger.write_text(fact + "\n")
    return {
        "report_path": str(report),
        "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        "ledger_path": str(ledger),
        "ledger_fact_prefix": "QM_STUDY_RESULT 2026-07-14:",
        "ledger_fact_sha256": hashlib.sha256(fact.encode()).hexdigest(),
    }


class StudySidecarTests(unittest.TestCase):
    def test_committed_sidecar_matches_committed_report(self):
        loaded = qm_dashboard.load_study_sidecar()
        self.assertEqual(loaded["study"]["breakout"]["fires"], 11)
        self.assertEqual(loaded["study"]["parabolic"]["fires"], 35)

    def test_load_accepts_exact_source_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text("frozen report\n")
            ledger = Path(tmp) / "facts.log"
            sidecar = Path(tmp) / "context.json"
            payload = _study()
            payload["source"] = _bound_source(report, ledger)
            sidecar.write_text(json.dumps(payload))

            loaded = qm_dashboard.load_study_sidecar(sidecar)

            self.assertEqual(
                loaded["source"]["report_sha256"],
                hashlib.sha256(report.read_bytes()).hexdigest(),
            )

    def test_load_rejects_source_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text("changed report\n")
            sidecar = Path(tmp) / "context.json"
            payload = _study()
            payload["source"] = {
                "report_path": str(report),
                "report_sha256": "0" * 64,
            }
            sidecar.write_text(json.dumps(payload))

            with self.assertRaisesRegex(qm_dashboard.QmContextError, "source hash mismatch"):
                qm_dashboard.load_study_sidecar(sidecar)

            with mock.patch.object(qm_dashboard.qm_signals, "qm_prereg_gate", return_value=None):
                visible = qm_dashboard.load_qm_context("2026-07-01", sidecar_path=sidecar)
            self.assertEqual(visible["status"], "DATA_BLOCKED")
            self.assertIn("source hash mismatch", visible["reason"])
            html = ad.render({"data_as_of": "2026-07-01", "symbols": []}, qm_context=visible)
            qm_section = html[
                html.index("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5") :
            ]
            self.assertEqual(qm_section.count("DATA BLOCKED"), config.PICK_TOP_N)

    def test_load_rejects_ledger_fact_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text("frozen report\n")
            ledger = Path(tmp) / "facts.log"
            sidecar = Path(tmp) / "context.json"
            payload = _study()
            source = _bound_source(report, ledger)
            source["ledger_fact_sha256"] = "0" * 64
            payload["source"] = source
            sidecar.write_text(json.dumps(payload))

            with self.assertRaisesRegex(qm_dashboard.QmContextError, "ledger fact hash mismatch"):
                qm_dashboard.load_study_sidecar(sidecar)


class ContextBuildTests(unittest.TestCase):
    def test_current_context_contains_signal_mas_and_provenance(self):
        frame = _frame()
        with (
            mock.patch.object(
                qm_dashboard.qm_signals, "breakout_fires", return_value=[{"t": "2026-07-01"}]
            ),
            mock.patch.object(qm_dashboard.qm_signals, "parabolic_fires", return_value=[]),
        ):
            context = qm_dashboard.build_qm_context(
                ["AAA"],
                "2026-07-01",
                study=_study(),
                params={"QM_HORIZONS": (5, 10, 20)},
                gate=lambda: None,
                load_adjusted=lambda _symbol, _as_of: frame,
            )

        item = context["symbols"]["AAA"]
        self.assertEqual(context["status"], "CURRENT")
        self.assertTrue(item["breakout_fire"])
        self.assertFalse(item["parabolic_fire"])
        self.assertTrue(item["ma_supports_bullish"])
        self.assertGreater(item["price"], item["sma20"])
        self.assertGreater(item["sma20"], item["sma50"])
        self.assertGreater(item["sma50"], item["sma200"])
        self.assertEqual(item["study"]["evidence_status"], "DESCRIPTIVE_ONLY")
        self.assertIn("option P&L", item["counter_case"])
        self.assertNotIn("breakout_mfe_20d", item)

    def test_standalone_movement_state_reads_uncovered_cache_without_frozen_fields(self):
        """A live movement fire is separate from the frozen-study evidence contract."""
        frame = _frame()
        with (
            mock.patch.object(
                qm_dashboard.qm_signals, "breakout_fires", return_value=[{"t": "2026-07-01"}]
            ),
            mock.patch.object(qm_dashboard.qm_signals, "parabolic_fires", return_value=[]),
        ):
            movement = qm_dashboard.build_qm_movement_context(
                ["AAA", "BBB"],
                "2026-07-01",
                study=_study("AAA"),
                params={"QM_HORIZONS": (5, 10, 20)},
                gate=lambda: None,
                load_adjusted=lambda _symbol, _as_of: frame,
            )

        self.assertEqual(list(movement), ["AAA", "BBB"])
        uncovered = movement["BBB"]
        self.assertEqual(uncovered["status"], "CURRENT")
        self.assertEqual(uncovered["signal_status"], "BREAKOUT")
        self.assertEqual(uncovered["frozen_study_coverage"], "NOT_COVERED")
        self.assertIn("not covered by the frozen study", uncovered["frozen_study_reason"])
        for forbidden in (
            "historical_breakout_fires", "historical_parabolic_fires", "study",
            "parabolic_study", "thesis", "counter_case", "provenance",
        ):
            self.assertNotIn(forbidden, uncovered)

    def test_loaded_context_keeps_frozen_mapping_separate_from_uncovered_live_state(self):
        """The retained comparison stays NOT_IN_FROZEN_STUDY while movement is live."""
        frame = _frame()
        with (
            mock.patch.object(qm_dashboard, "load_study_sidecar", return_value=_study("AAA")),
            mock.patch("options_researcher.h7_scope.watch_universe", return_value=["AAA", "BBB"]),
            mock.patch.object(qm_dashboard.qm_signals, "qm_prereg_gate", return_value=None),
            mock.patch.object(
                qm_dashboard.qm_signals, "breakout_fires", return_value=[{"t": "2026-07-01"}]
            ),
            mock.patch.object(qm_dashboard.qm_signals, "parabolic_fires", return_value=[]),
        ):
            context = qm_dashboard.load_qm_context(
                "2026-07-01", load_adjusted=lambda _symbol, _as_of: frame
            )

        self.assertEqual(context["symbols"]["BBB"]["status"], "NOT_IN_FROZEN_STUDY")
        uncovered = context["movement_symbols"]["BBB"]
        self.assertEqual(uncovered["status"], "CURRENT")
        self.assertEqual(uncovered["signal_status"], "BREAKOUT")
        self.assertEqual(uncovered["frozen_study_coverage"], "NOT_COVERED")
        self.assertNotIn("historical_breakout_fires", uncovered)

    def test_one_stale_symbol_blocks_whole_qm_ranking_context(self):
        stale = _frame(end="2026-06-30")
        context = qm_dashboard.build_qm_context(
            ["AAA"],
            "2026-07-01",
            study=_study(),
            params={"QM_HORIZONS": (5, 10, 20)},
            gate=lambda: None,
            load_adjusted=lambda _symbol, _as_of: stale,
        )
        self.assertEqual(context["status"], "DATA_BLOCKED")
        self.assertEqual(context["symbols"]["AAA"]["status"], "STALE")
        self.assertIn("2026-06-30", context["symbols"]["AAA"]["reason"])

    def test_bullish_ma_support_means_price_above_all_not_perfect_stack(self):
        frame = _frame()
        frame.loc[frame.index[-50:], "close"] = 180.0
        frame.loc[frame.index[-20:], "close"] = 160.0
        frame.loc[frame.index[-1], "close"] = 200.0
        with (
            mock.patch.object(qm_dashboard.qm_signals, "breakout_fires", return_value=[]),
            mock.patch.object(qm_dashboard.qm_signals, "parabolic_fires", return_value=[]),
        ):
            context = qm_dashboard.build_qm_context(
                ["AAA"],
                "2026-07-01",
                study=_study(),
                params={"QM_HORIZONS": (5, 10, 20)},
                gate=lambda: None,
                load_adjusted=lambda _symbol, _as_of: frame,
            )
        item = context["symbols"]["AAA"]
        self.assertLess(item["sma20"], item["sma50"])
        self.assertGreater(item["price"], item["sma20"])
        self.assertGreater(item["price"], item["sma50"])
        self.assertGreater(item["price"], item["sma200"])
        self.assertTrue(item["ma_supports_bullish"])

    def test_gate_refusal_touches_no_data(self):
        def boom(*_args):
            raise AssertionError("data touched after gate refusal")

        context = qm_dashboard.build_qm_context(
            ["AAA"],
            "2026-07-01",
            study=_study(),
            params={"QM_HORIZONS": (5, 10, 20)},
            gate=lambda: "not registered",
            load_adjusted=boom,
        )
        self.assertEqual(context["status"], "DATA_BLOCKED")
        self.assertIn("not registered", context["reason"])

    def test_stock_move_frequency_is_withheld_without_a_frozen_per_fire_source(self):
        evidence = qm_dashboard.underlying_breakeven_frequency(
            {"breakout_mfe_20d": [0.05, 0.12, 0.20]},
            {"breakeven_move": 0.10},
            "long_call",
        )
        self.assertFalse(evidence["available"])
        self.assertEqual((evidence["hits"], evidence["sample"]), (None, 0))
        self.assertIn("underlying", evidence["label"].lower())
        self.assertIn("not shown", evidence["label"].lower())
        self.assertIn("not recomputed", evidence["label"].lower())
        self.assertIn("not an option win probability", evidence["warning"].lower())
        self.assertEqual(evidence["option_win_rate"], None)

    def test_every_non_long_call_lane_withholds_breakeven_comparison(self):
        for lane in ("put", "cc", "pmcc"):
            with self.subTest(lane=lane):
                evidence = qm_dashboard.underlying_breakeven_frequency(
                    {"breakout_mfe_20d": [0.05, 0.12, 0.20]},
                    {"breakeven_move": 0.10},
                    lane,
                )

                self.assertFalse(evidence["available"])
                self.assertEqual((evidence["hits"], evidence["sample"]), (None, 0))
                self.assertIn("not applicable", evidence["label"].lower())
                self.assertIn("not tested by qm", evidence["label"].lower())
                self.assertIsNone(evidence["option_win_rate"])

    def test_one_stale_symbol_blocks_all_three_qm_slots(self):
        current = _frame()
        stale = _frame(end="2026-06-30")
        frames = {"AAA": current, "BBB": stale, "CCC": current}
        context = qm_dashboard.build_qm_context(
            ["AAA", "BBB", "CCC"],
            "2026-07-01",
            study=_study(),
            params={"QM_HORIZONS": (5, 10, 20)},
            gate=lambda: None,
            load_adjusted=lambda symbol, _as_of: frames[symbol],
        )

        html = ad.render({"data_as_of": "2026-07-01", "symbols": []}, qm_context=context)
        start = html.index("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5")
        self.assertEqual(context["status"], "DATA_BLOCKED")
        self.assertEqual(
            html[start:].count("QM context withheld"), config.PICK_TOP_N
        )

    def test_symbol_missing_from_frozen_sidecar_is_per_name_not_a_board_blocker(self):
        # REWRITTEN for brief 12 D5 (was: ..._blocks_qm_without_touching_its_cache).
        # A name the frozen study never covered can NEVER become current, so
        # blocking every covered name on it made the panel permanently dark.
        # The covered name still renders; the uncovered one says so per name;
        # its cache is still never touched.
        frame = _frame()
        touched: list[str] = []

        def load(symbol: str, _as_of: str) -> pd.DataFrame:
            touched.append(symbol)
            return frame

        with (
            mock.patch.object(
                qm_dashboard.qm_signals, "breakout_fires", return_value=[]
            ),
            mock.patch.object(
                qm_dashboard.qm_signals, "parabolic_fires", return_value=[]
            ),
        ):
            context = qm_dashboard.build_qm_context(
                ["AAA", "BBB"],
                "2026-07-01",
                study=_study("AAA"),
                params={"QM_HORIZONS": (5, 10, 20)},
                gate=lambda: None,
                load_adjusted=load,
            )

        self.assertEqual(context["status"], "CURRENT")
        self.assertEqual(context["symbols"]["AAA"]["status"], "CURRENT")
        self.assertEqual(context["symbols"]["BBB"]["status"], "NOT_IN_FROZEN_STUDY")
        self.assertIn("not in the frozen QM study", context["symbols"]["BBB"]["reason"])
        self.assertEqual(context["not_covered"], ["BBB"])
        self.assertEqual(touched, ["AAA"])

    def test_explicitly_uncovered_symbol_renders_per_name_without_touching_its_cache(self):
        # REWRITTEN for brief 12 D5 (was: ..._blocks_all_qm_slots_...).
        frame = _frame()
        touched: list[str] = []
        study = _study("AAA")
        study["symbols"]["BBB"] = {
            "breakout_fire_dates": [],
            "parabolic_fire_dates": [],
            "evidence_status": "NOT_IN_FROZEN_STUDY",
        }

        def load(symbol: str, _as_of: str) -> pd.DataFrame:
            touched.append(symbol)
            return frame

        with (
            mock.patch.object(
                qm_dashboard.qm_signals, "breakout_fires", return_value=[]
            ),
            mock.patch.object(
                qm_dashboard.qm_signals, "parabolic_fires", return_value=[]
            ),
        ):
            context = qm_dashboard.build_qm_context(
                ["AAA", "BBB"],
                "2026-07-01",
                study=study,
                params={"QM_HORIZONS": (5, 10, 20)},
                gate=lambda: None,
                load_adjusted=load,
            )
        html = ad.render({"data_as_of": "2026-07-01", "symbols": []}, qm_context=context)
        qm_section = html[
            html.index("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5") :
        ]

        self.assertEqual(context["status"], "CURRENT")
        self.assertEqual(context["symbols"]["BBB"]["status"], "NOT_IN_FROZEN_STUDY")
        self.assertEqual(qm_section.count("QM context withheld"), 0)
        self.assertIn("Not covered by the frozen study: BBB", qm_section)
        self.assertEqual(touched, ["AAA"])

    def test_a_covered_name_that_is_stale_still_blocks_the_board(self):
        # The per-name change must NOT loosen the real staleness gate.
        stale = _frame(end="2026-06-30")
        study = _study("AAA")
        study["symbols"]["BBB"] = {
            "breakout_fire_dates": [],
            "parabolic_fire_dates": [],
            "evidence_status": "NOT_IN_FROZEN_STUDY",
        }
        context = qm_dashboard.build_qm_context(
            ["AAA", "BBB"],
            "2026-07-01",
            study=study,
            params={"QM_HORIZONS": (5, 10, 20)},
            gate=lambda: None,
            load_adjusted=lambda _symbol, _as_of: stale,
        )
        self.assertEqual(context["status"], "DATA_BLOCKED")
        self.assertIn("not exact-session current for: AAA", context["reason"])

    def test_one_stale_covered_name_blocks_even_beside_a_current_one(self):
        # The load-bearing case for the per-name change: a CURRENT covered name
        # must not carry a STALE covered name onto the board.
        frames = {"AAA": _frame(), "BBB": _frame(end="2026-06-30")}
        study = _study("AAA")
        study["symbols"]["BBB"] = {"breakout_fire_dates": [],
                                   "parabolic_fire_dates": []}
        with (
            mock.patch.object(
                qm_dashboard.qm_signals, "breakout_fires", return_value=[]
            ),
            mock.patch.object(
                qm_dashboard.qm_signals, "parabolic_fires", return_value=[]
            ),
        ):
            context = qm_dashboard.build_qm_context(
                ["AAA", "BBB"],
                "2026-07-01",
                study=study,
                params={"QM_HORIZONS": (5, 10, 20)},
                gate=lambda: None,
                load_adjusted=lambda symbol, _as_of: frames[symbol],
            )
        self.assertEqual(context["symbols"]["AAA"]["status"], "CURRENT")
        self.assertEqual(context["symbols"]["BBB"]["status"], "STALE")
        self.assertEqual(context["status"], "DATA_BLOCKED")
        self.assertIn("not exact-session current for: BBB", context["reason"])

    def test_all_uncovered_universe_has_nothing_honest_to_show(self):
        study = _study("AAA")
        context = qm_dashboard.build_qm_context(
            ["BBB"],
            "2026-07-01",
            study=study,
            params={"QM_HORIZONS": (5, 10, 20)},
            gate=lambda: None,
            load_adjusted=lambda *_: _frame(),
        )
        self.assertEqual(context["status"], "DATA_BLOCKED")
        self.assertEqual(context["reason"], "not covered by the frozen QM study: BBB")

    def test_blocked_reason_separates_study_coverage_from_staleness(self):
        study = _study("AAA")
        study["symbols"]["BBB"] = {
            "breakout_fire_dates": [],
            "parabolic_fire_dates": [],
            "evidence_status": "NOT_IN_FROZEN_STUDY",
        }

        context = qm_dashboard.build_qm_context(
            ["AAA", "BBB"],
            "2026-07-02",
            study=study,
            gate=lambda: None,
            load_adjusted=lambda *_: _frame(),
        )

        self.assertEqual(context["status"], "DATA_BLOCKED")
        self.assertNotEqual(context["symbols"]["AAA"]["status"], "CURRENT")
        self.assertIn("not covered by the frozen QM study: BBB", context["reason"])
        self.assertIn("QM context is not exact-session current for: AAA", context["reason"])

    def test_blocked_reason_omits_staleness_clause_when_only_coverage_blocks(self):
        study = _study("AAA")
        study["symbols"]["BBB"] = {
            "breakout_fire_dates": [],
            "parabolic_fire_dates": [],
            "evidence_status": "NOT_IN_FROZEN_STUDY",
        }

        context = qm_dashboard.build_qm_context(
            ["BBB"],
            "2026-07-01",
            study=study,
            params={"QM_HORIZONS": (5, 10, 20)},
            gate=lambda: None,
            load_adjusted=lambda *_: _frame(),
        )

        self.assertEqual(context["status"], "DATA_BLOCKED")
        self.assertEqual(
            context["reason"], "not covered by the frozen QM study: BBB"
        )

    def test_unexpected_context_exception_is_visible_and_nonzero(self):
        context = qm_dashboard.build_qm_context(
            ["AAA"],
            "2026-07-01",
            study=_study(),
            params={"QM_HORIZONS": (5, 10, 20)},
            gate=lambda: None,
            load_adjusted=lambda _symbol, _as_of: (_ for _ in ()).throw(
                RuntimeError("signal implementation failure")
            ),
        )

        self.assertEqual(context["status"], "DATA_BLOCKED")
        self.assertEqual(context["symbols"]["AAA"]["status"], "UNEXPECTED_ERROR")
        self.assertTrue(context["unexpected"])
        self.assertEqual(ad._run_exit_code([], qm_context=context), 1)


class RefreshTests(unittest.TestCase):
    def test_refresh_fetches_only_stale_names_and_rechecks_exact_date(self):
        current = _frame()
        stale = _frame(end="2026-06-30")
        frames = {"AAA": current, "BBB": stale}
        fetched: list[str] = []

        def load(symbol: str, _as_of: str) -> pd.DataFrame:
            return frames[symbol]

        def fetch(symbol: str) -> str:
            fetched.append(symbol)
            frames[symbol] = current
            return f"{symbol}.parquet"

        result = qm_dashboard.refresh_qm_ohlcv(
            ["AAA", "BBB"],
            "2026-07-01",
            study={"symbols": {"AAA": {}, "BBB": {}}},
            gate=lambda: None,
            load_adjusted=load,
            fetch=fetch,
        )

        self.assertEqual(fetched, ["BBB"])
        self.assertEqual(result["status"], "CURRENT")

    def test_refresh_failure_remains_visible_and_blocked(self):
        stale = _frame(end="2026-06-30")
        result = qm_dashboard.refresh_qm_ohlcv(
            ["AAA"],
            "2026-07-01",
            study={"symbols": {"AAA": {}}},
            gate=lambda: None,
            load_adjusted=lambda _symbol, _as_of: stale,
            fetch=lambda _symbol: (_ for _ in ()).throw(RuntimeError("offline")),
        )
        self.assertEqual(result["status"], "DATA_BLOCKED")
        self.assertEqual(result["symbols"]["AAA"]["status"], "STALE")
        self.assertIn("offline", result["symbols"]["AAA"]["reason"])

    def test_refresh_never_loads_or_fetches_an_explicitly_uncovered_symbol(self):
        current = _frame()
        touched: list[str] = []
        fetched: list[str] = []
        study = _study("AAA")
        study["symbols"]["BBB"] = {
            "breakout_fire_dates": [],
            "parabolic_fire_dates": [],
            "evidence_status": "NOT_IN_FROZEN_STUDY",
        }

        def load(symbol: str, _as_of: str) -> pd.DataFrame:
            touched.append(symbol)
            return current

        def fetch(symbol: str) -> str:
            fetched.append(symbol)
            return f"{symbol}.parquet"

        result = qm_dashboard.refresh_qm_ohlcv(
            ["AAA", "BBB"],
            "2026-07-01",
            study=study,
            gate=lambda: None,
            load_adjusted=load,
            fetch=fetch,
        )

        # REWRITTEN for brief 12 D5: an uncovered name is never loaded or
        # fetched, so calling the refresh "incomplete" because of it turned a
        # structural coverage fact into a permanently red ritual step. It is
        # reported per name instead; the covered name's gate is unchanged.
        self.assertEqual(result["status"], "CURRENT")
        self.assertEqual(result["symbols"]["BBB"]["status"], "NOT_IN_FROZEN_STUDY")
        self.assertEqual(result["not_covered"], ["BBB"])
        self.assertEqual(touched, ["AAA"])
        self.assertEqual(fetched, [])

    def test_a_covered_name_that_cannot_refresh_still_blocks(self):
        stale = _frame(end="2026-06-30")
        study = _study("AAA")
        study["symbols"]["BBB"] = {
            "breakout_fire_dates": [],
            "parabolic_fire_dates": [],
            "evidence_status": "NOT_IN_FROZEN_STUDY",
        }
        result = qm_dashboard.refresh_qm_ohlcv(
            ["AAA", "BBB"],
            "2026-07-01",
            study=study,
            gate=lambda: None,
            load_adjusted=lambda _symbol, _as_of: stale,
            fetch=lambda _symbol: (_ for _ in ()).throw(RuntimeError("offline")),
        )
        self.assertEqual(result["status"], "DATA_BLOCKED")
        self.assertIn("AAA", result["reason"])
        self.assertNotIn("BBB", result["reason"])


class SessionDecouplingTests(unittest.TestCase):
    """QM targets its own newest complete daily session (brief 12 D5)."""

    def _sidecar(self, tmp: str, symbols: tuple[str, ...] = ("AAA", "BBB")) -> Path:
        report = Path(tmp) / "report.md"
        report.write_text("frozen report\n")
        ledger = Path(tmp) / "facts.log"
        sidecar = Path(tmp) / "context.json"
        payload = _study(symbols[0])
        for symbol in symbols[1:]:
            payload["symbols"][symbol] = {
                "breakout_fire_dates": [],
                "parabolic_fire_dates": [],
            }
        payload["source"] = _bound_source(report, ledger)
        sidecar.write_text(json.dumps(payload))
        return sidecar

    def test_target_is_the_newest_session_every_covered_name_has(self):
        frames = {"AAA": _frame(end="2026-08-13"), "BBB": _frame(end="2026-08-12")}
        target, lasts = qm_dashboard.newest_complete_session(
            ["AAA", "BBB"], "2026-08-14",
            load_adjusted=lambda symbol, _as_of: frames[symbol])
        self.assertEqual(target, "2026-08-12")
        self.assertEqual(lasts, {"AAA": "2026-08-13", "BBB": "2026-08-12"})

    def test_target_never_runs_ahead_of_the_board_session(self):
        target, _lasts = qm_dashboard.newest_complete_session(
            ["AAA"], "2026-08-10",
            load_adjusted=lambda _symbol, _as_of: _frame(end="2026-08-13"))
        self.assertEqual(target, "2026-08-10")

    def test_no_cached_bars_is_reported_not_guessed(self):
        target, _lasts = qm_dashboard.newest_complete_session(
            ["AAA"], "2026-08-14",
            load_adjusted=lambda *_: (_ for _ in ()).throw(OSError("absent")))
        self.assertIsNone(target)

    def test_same_day_chain_session_does_not_re_block_the_panel(self):
        # The board reads a 15:45 chain for 2026-08-14; the daily bar for an
        # open session does not exist. Demanding equality blanked the panel on
        # every capture day. QM self-targets 08-13 and says both dates.
        with tempfile.TemporaryDirectory() as tmp:
            sidecar = self._sidecar(tmp, ("AAA",))
            with (
                mock.patch.object(
                    qm_dashboard.qm_signals, "qm_prereg_gate", return_value=None
                ),
                mock.patch.object(
                    qm_dashboard.qm_signals, "breakout_fires", return_value=[]
                ),
                mock.patch.object(
                    qm_dashboard.qm_signals, "parabolic_fires", return_value=[]
                ),
                mock.patch(
                    "options_researcher.h7_scope.watch_universe",
                    return_value=["AAA"],
                ),
            ):
                context = qm_dashboard.load_qm_context(
                    "2026-08-14",
                    sidecar_path=sidecar,
                    load_adjusted=lambda _symbol, _as_of: _frame(end="2026-08-13"),
                )

        self.assertEqual(context["status"], "CURRENT")
        self.assertEqual(context["as_of"], "2026-08-13")
        self.assertEqual(context["board_session"], "2026-08-14")

        data = {"data_as_of": "2026-08-14", "as_of_kind": "schwab_preclose",
                "symbols": []}
        self.assertIsNone(ad._qm_context_block_reason(data, context))
        html = ad.render(data, qm_context=context)
        self.assertIn("QM daily-bar context as of 2026-08-13", html)
        self.assertIn("board option chains 15:45 pre-close (Schwab) 2026-08-14", html)

    def test_context_built_for_another_board_session_is_refused(self):
        data = {"data_as_of": "2026-08-14", "symbols": []}
        context = {"status": "CURRENT", "as_of": "2026-08-13",
                   "board_session": "2026-08-12", "symbols": {}}
        reason = ad._qm_context_block_reason(data, context)
        self.assertIsNotNone(reason)
        self.assertIn("built for board session 2026-08-12", str(reason))

    def test_qm_context_dated_after_the_board_is_refused(self):
        data = {"data_as_of": "2026-08-13", "symbols": []}
        context = {"status": "CURRENT", "as_of": "2026-08-14", "symbols": {}}
        reason = ad._qm_context_block_reason(data, context)
        self.assertIsNotNone(reason)
        self.assertIn("ahead of dashboard market date", str(reason))


class DailyRitualContractTests(unittest.TestCase):
    def test_exact_session_qm_refresh_precedes_dashboard_build(self):
        script = Path("tools/daily_ritual.sh").read_text()
        refresh = 'options_researcher.qm_dashboard --refresh-ohlcv --as-of "$AS_OF"'
        dashboard = "options_researcher.attractiveness_dashboard"
        self.assertIn(refresh, script)
        self.assertLess(script.index(refresh), script.index(dashboard))


if __name__ == "__main__":
    unittest.main()
