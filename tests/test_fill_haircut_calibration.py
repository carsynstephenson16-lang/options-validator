"""Offline contract tests for the descriptive fill-adversity study."""

from __future__ import annotations

import inspect
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from data import thetadata_adapter
from research.receipts import load_receipt
from tools import fill_haircut_calibration as study


def _row(
    session: str,
    *,
    symbol: str = "SYN",
    expiration: str = "2026-09-18",
    strike: float = 100.0,
    right: str = "P",
    bid: float = 1.0,
    ask: float = 1.1,
    delta: float = -0.30,
    timestamp: str | None = None,
    bid_size: int = 10,
    ask_size: int = 12,
    underlying_price: float = 100.0,
) -> dict:
    return {
        "expiration": expiration,
        "strike": strike,
        "right": right,
        "bid": bid,
        "ask": ask,
        "open_interest": 500,
        "iv": 0.30,
        "delta": delta,
        "gamma": 0.02,
        "theta": -0.04,
        "vega": 0.12,
        "timestamp": timestamp or f"{session} 12:00:00-04:00",
        "bid_size": bid_size,
        "ask_size": ask_size,
        "underlying_price": underlying_price,
        "symbol": symbol,
        "session": session,
    }


def _frame(session: str, rows: list[dict] | None = None) -> pd.DataFrame:
    rows = rows or [_row(session)]
    return pd.DataFrame(rows)


class TierLoaderTests(unittest.TestCase):
    def test_tier2_refuses_without_owner_flag_and_loads_with_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "SYN_2026-07-31.parquet"
            _frame("2026-07-31").to_parquet(path)
            with self.assertRaisesRegex(RuntimeError, "parked.*2026-08-24"):
                study.load_tier("tier2", tier2_dir=root, quarantine_path=root / "none.json")
            loaded = study.load_tier(
                "tier2",
                allow_parked_chains_v2=True,
                tier2_dir=root,
                quarantine_path=root / "none.json",
            )
            self.assertEqual(list(loaded.frames), [("SYN", "2026-07-31")])

    def test_quarantine_exclusion_holds_with_tier2_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "SYN_2026-07-31.parquet"
            _frame("2026-07-31").to_parquet(path)
            quarantine = root / "quarantine.json"
            quarantine.write_text(
                json.dumps(
                    {
                        "schema": "v2-partition-quarantine/v1",
                        "entries": [{"symbol": "SYN", "session": "2026-07-31"}],
                    }
                )
            )
            loaded = study.load_tier(
                "tier2",
                allow_parked_chains_v2=True,
                tier2_dir=root,
                quarantine_path=quarantine,
            )
            self.assertEqual(loaded.frames, {})
            self.assertEqual(loaded.quarantined, [("SYN", "2026-07-31")])

    def test_staleness_boundaries_and_over_half_loss_are_recorded(self):
        session = "2026-07-31"
        rows = [
            _row(session, strike=90, timestamp=f"{session} 09:29:59-04:00"),
            _row(session, strike=91, timestamp=f"{session} 09:30:00-04:00"),
            _row(session, strike=92, timestamp=f"{session} 16:15:00-04:00"),
            _row(session, strike=93, timestamp=f"{session} 16:15:01-04:00"),
            _row(session, strike=94, timestamp=f"{session} 00:00:00-04:00"),
        ]
        admitted, stats = study.prepare_frame(_frame(session, rows), session, tier="tier2")
        self.assertEqual(set(admitted["strike"]), {91.0, 92.0})
        self.assertEqual(stats["staleness_dropped"], 3)
        self.assertTrue(stats["excluded_from_drift"])


class MeasurementTests(unittest.TestCase):
    def test_drift_pairs_use_adjacent_exchange_sessions_and_record_survivorship(self):
        day = _frame(
            "2026-08-19",
            [
                _row("2026-08-19", strike=100),
                _row("2026-08-19", strike=101),
            ],
        )
        next_day = _frame("2026-08-20", [_row("2026-08-20", strike=100)])
        data = study.TieredData(
            "Tier 1",
            frames={("SYN", "2026-08-19"): day, ("SYN", "2026-08-20"): next_day},
            raw_frames={
                ("SYN", "2026-08-19"): day,
                ("SYN", "2026-08-20"): next_day,
            },
            stage_counts={
                ("SYN", "2026-08-19"): {"excluded_from_drift": False},
                ("SYN", "2026-08-20"): {"excluded_from_drift": False},
            },
        )
        vectors, stages = study.compute_overnight_drift(data)
        self.assertEqual(len(vectors), 1)
        self.assertEqual(stages["SYN@2026-08-19->2026-08-20"]["vanished"], 1)

    def test_overnight_and_two_leg_math_is_pinned(self):
        day = _frame(
            "2026-08-19",
            [
                _row("2026-08-19", strike=100, bid=4.0, ask=6.0, delta=-0.4),
                _row("2026-08-19", strike=95, bid=1.0, ask=3.0, delta=-0.2),
            ],
        )
        nxt = _frame(
            "2026-08-20",
            [
                _row("2026-08-20", strike=100, bid=5.0, ask=7.0, delta=-0.4),
                _row("2026-08-20", strike=95, bid=2.0, ask=4.0, delta=-0.2),
            ],
        )
        drift = study.overnight_vectors(day, nxt, "2026-08-19", "2026-08-20")
        self.assertEqual(list(drift["delta_mid"]), [1.0, 1.0])
        self.assertEqual(list(drift["abs_delta_mid"]), [1.0, 1.0])

        # The two legs move by a dollar each, while the net-credit analogue
        # remains unchanged; single-leg movement must not stand in for it.
        verticals = study.two_leg_vectors(day, nxt, "2026-08-19", "2026-08-20")
        self.assertEqual(len(verticals), 1)
        self.assertAlmostEqual(float(verticals.iloc[0]["delta_net_credit"]), 0.0)
        self.assertEqual(float(verticals.iloc[0]["abs_leg_delta_mid_max"]), 1.0)

    def test_one_sided_adverse_fraction_uses_registered_tolerance_direction(self):
        vectors = pd.DataFrame(
            {
                "delta_net_credit": [-0.02, -0.01, 0.03],
                "bucket": ["x", "x", "x"],
            }
        )
        result = study.summarize_two_leg(vectors)
        self.assertAlmostEqual(result["adverse_fraction"], 1 / 3)

    def test_decomposition_shares_sum_to_one(self):
        components = study.decompose_quote(1.00, 1.20)
        self.assertAlmostEqual(
            components["half_spread_share"]
            + components["haircut_share"]
            + components["cent_rounding_share"],
            1.0,
            places=12,
        )

    def test_floor_and_out_of_band_are_explicit(self):
        rows = pd.DataFrame(
            {
                "dte": [3, 3, 3],
                "delta": [0.05, 1.2, float("nan")],
                "value": [1.0, 2.0, 3.0],
            }
        )
        bucketed = study.assign_buckets(rows)
        self.assertEqual(int((bucketed["delta_bucket"] == "OUT_OF_BAND").sum()), 2)
        rendered = study.render_bucket_table(bucketed, min_obs=2)
        self.assertIn("INSUFFICIENT (n=1)", rendered)
        self.assertIn("OUT_OF_BAND", rendered)

    def test_tier_tables_are_never_pooled(self):
        rows = pd.DataFrame(
            {
                "tier": ["Tier 1", "Tier 2"],
                "bucket": ["same", "same"],
                "value": [0.1, 0.2],
            }
        )
        tables = study.render_tier_tables(rows, value_column="value", min_obs=1)
        self.assertEqual(set(tables), {"Tier 1", "Tier 2"})
        self.assertNotIn("0.150", tables["Tier 1"])

    def test_touch_depth_reports_side_fractions_and_weighted_spread(self):
        data = study.TieredData(
            "Tier 2",
            frames={
                ("SYN", "2026-07-31"): _frame(
                    "2026-07-31",
                    [
                        _row("2026-07-31", strike=100, bid_size=1, ask_size=2),
                        _row("2026-07-31", strike=101, bid_size=0, ask_size=3),
                    ],
                )
            },
        )
        result = study._touch_depth_summary(data, min_obs=1)
        self.assertEqual(result["n"], 2)
        self.assertAlmostEqual(result["bid_ge_one"], 0.5)
        self.assertAlmostEqual(result["ask_ge_one"], 1.0)
        self.assertIn("size_weighted_mean_spread_fraction", result)


class ReportAndBoundaryTests(unittest.TestCase):
    def test_report_has_no_prohibited_vocabulary_or_headline_exceedance(self):
        report = study.render_report(
            {
                "tier1": {"headline": "p50=0.02", "exceedance": "67%"},
                "tier2": {"headline": "INSUFFICIENT", "exceedance": "98%"},
                "receipt_hash": "a" * 64,
                "max_asof": "2026-08-20",
            }
        )
        appendix = report.split("## Appendix", 1)[1]
        headline = report.split("## Appendix", 1)[0]
        for word in ("proven", "confirmed", "validated", "correct"):
            self.assertNotRegex(report.lower(), rf"\\b{word}\\b")
        self.assertNotIn("67%", headline)
        self.assertNotIn("98%", headline)
        self.assertIn("67%", appendix)
        self.assertIn("98%", appendix)

    def test_raw_close_loader_is_used_and_adjusted_loader_is_not(self):
        frames = {("SYN", "2026-08-19"): _frame("2026-08-19")}
        with (
            mock.patch.object(
                study.underlying_closes,
                "load_closes",
                return_value=pd.Series([100.0], index=["2026-08-19"]),
            ) as raw,
            mock.patch.object(
                study.underlying_closes,
                "load_closes_adjusted",
                side_effect=AssertionError("adjusted closes are forbidden"),
            ) as adjusted,
        ):
            study.attach_tier1_spots(frames)
        raw.assert_called_once_with("SYN", "2026-08-19", "2026-08-19", allow_oos=True)
        adjusted.assert_not_called()

    def test_missing_close_is_recorded_without_interpolation(self):
        frames = {("SYN", "2026-08-19"): _frame("2026-08-19")}
        with mock.patch.object(
            study.underlying_closes, "load_closes", return_value=pd.Series(dtype=float)
        ):
            spots, missing = study.attach_tier1_spots(frames)
        self.assertEqual(missing, [("SYN", "2026-08-19")])
        self.assertTrue(spots[("SYN", "2026-08-19")]["spot"].isna().all())

    def test_emitted_receipt_proves_missing_close_exclusion_and_stage_count(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chain_path = root / "SYN_2026-08-19.parquet"
            _frame("2026-08-19").to_parquet(chain_path)
            report_path = root / "report.md"
            receipt_path = root / "receipt.json"
            with mock.patch.object(
                study.underlying_closes, "load_closes", return_value=pd.Series(dtype=float)
            ):
                code = study.main(
                    [
                        "--tier1-dir",
                        str(root),
                        "--report",
                        str(report_path),
                        "--receipt",
                        str(receipt_path),
                    ]
                )
            self.assertEqual(code, 0)
            receipt = load_receipt(receipt_path, expected_type="fill_adversity_context")
            self.assertNotIn("wall_clock", receipt)
            self.assertEqual(receipt["missing_close_sessions"]["Tier 1"], [["SYN", "2026-08-19"]])
            stage = receipt["stage_counts"]["Tier 1"]["SYN@2026-08-19"]
            self.assertEqual(stage["admitted_rows"], 1)
            self.assertTrue(stage["missing_close"])
            self.assertEqual(stage["missing_close_dropped"], 1)
            self.assertEqual(receipt["measurements"]["Tier 1"]["decomposition"]["n"], 0)
            self.assertEqual(receipt["numeric_tables"]["Tier 1"]["decomposition"], {})

    def test_cli_is_behaviorally_offline_and_does_not_import_reveal_path(self):
        self.assertNotIn("research.experiments", inspect.getsource(study))
        original = socket.socket

        class DeniedSocket:
            def __init__(self, *args, **kwargs):
                raise AssertionError("network socket opened")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _frame("2026-08-19").to_parquet(root / "SYN_2026-08-19.parquet")
            report = root / "report.md"
            receipt = root / "receipt.json"
            with (
                mock.patch("socket.socket", DeniedSocket),
                mock.patch.object(study.underlying_closes, "fetch_underlying_eod") as fetch_raw,
                mock.patch.object(study.underlying_closes, "fetch_underlying_eod_av") as fetch_av,
                mock.patch.object(
                    study.underlying_closes, "fetch_underlying_eod_yahoo"
                ) as fetch_yahoo,
                mock.patch.object(thetadata_adapter, "get_eod_chain") as get_chain,
                mock.patch.object(thetadata_adapter, "blind_cache_chain") as cache_chain,
            ):
                code = study.main(
                    [
                        "--tier1-dir",
                        str(root),
                        "--report",
                        str(report),
                        "--receipt",
                        str(receipt),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertTrue(report.is_file())
            self.assertTrue(receipt.is_file())
            for fetch in (fetch_raw, fetch_av, fetch_yahoo, get_chain, cache_chain):
                fetch.assert_not_called()
        socket.socket = original


if __name__ == "__main__":
    unittest.main()
