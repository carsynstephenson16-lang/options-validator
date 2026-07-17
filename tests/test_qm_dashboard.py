"""Fail-closed tests for the QM context consumed by the six-card board."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

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
                html.index("QM + MOVING-AVERAGE TOP 3") : html.index("ORIGINAL MECHANICAL TOP 3")
            ]
            self.assertEqual(qm_section.count("DATA BLOCKED"), 3)

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
            gate=lambda: None,
            load_adjusted=lambda _symbol, _as_of: stale,
            fetch=lambda _symbol: (_ for _ in ()).throw(RuntimeError("offline")),
        )
        self.assertEqual(result["status"], "DATA_BLOCKED")
        self.assertEqual(result["symbols"]["AAA"]["status"], "STALE")
        self.assertIn("offline", result["symbols"]["AAA"]["reason"])


class DailyRitualContractTests(unittest.TestCase):
    def test_exact_session_qm_refresh_precedes_dashboard_build(self):
        script = Path("tools/daily_ritual.sh").read_text()
        refresh = 'options_researcher.qm_dashboard --refresh-ohlcv --as-of "$AS_OF"'
        dashboard = "options_researcher.attractiveness_dashboard"
        self.assertIn(refresh, script)
        self.assertLess(script.index(refresh), script.index(dashboard))


if __name__ == "__main__":
    unittest.main()
