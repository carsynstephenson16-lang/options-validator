"""tests/test_entry_watch.py"""
import contextlib
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

import config
from options_researcher import entry_watch as ew


def _leaps_row(oi=500, bid=40.0, ask=41.0):
    return pd.Series({"open_interest": oi, "bid": bid, "ask": ask,
                      "strike": 140.0, "delta": 0.70})


class TriggerStatusTests(unittest.TestCase):
    def test_all_conditions_met_fires(self):
        s = ew.trigger_status("VST", close=139.50, iv_rank=0.40,
                              leaps_row=_leaps_row())
        self.assertEqual(s["verdict"], "FIRE")
        self.assertEqual(s["unmet"], [])

    def test_price_above_trigger_waits(self):
        above = config.H5_ENTRY_TRIGGERS["VST"] + 5.0
        s = ew.trigger_status("VST", close=above, iv_rank=0.40,
                              leaps_row=_leaps_row())
        self.assertEqual(s["verdict"], "WAIT")
        self.assertTrue(any("trigger" in u for u in s["unmet"]))

    def test_rich_iv_waits_even_below_price(self):
        s = ew.trigger_status("VST", close=139.00, iv_rank=0.80,
                              leaps_row=_leaps_row())
        self.assertEqual(s["verdict"], "WAIT")
        self.assertTrue(any("IV-rank" in u for u in s["unmet"]))

    def test_illiquid_leaps_waits(self):
        s = ew.trigger_status("VST", close=139.00, iv_rank=0.40,
                              leaps_row=_leaps_row(oi=10))
        self.assertEqual(s["verdict"], "WAIT")

    def test_missing_leaps_candidate_waits(self):
        s = ew.trigger_status("VST", close=139.00, iv_rank=0.40,
                              leaps_row=None)
        self.assertEqual(s["verdict"], "WAIT")
        self.assertTrue(any("no LEAPS candidate" in u for u in s["unmet"]))

    def test_nan_iv_rank_waits(self):
        s = ew.trigger_status("VST", close=139.00, iv_rank=float("nan"),
                              leaps_row=_leaps_row())
        self.assertEqual(s["verdict"], "WAIT")

    def test_uses_config_constants(self):
        self.assertEqual(ew.trigger_status("AMZN", close=219.0, iv_rank=0.1,
                                           leaps_row=_leaps_row())["trigger"],
                         config.H5_ENTRY_TRIGGERS["AMZN"])

    def test_close_exactly_at_trigger_is_ok(self):
        s = ew.trigger_status("VST", close=config.H5_ENTRY_TRIGGERS["VST"],
                              iv_rank=0.40, leaps_row=_leaps_row())
        self.assertTrue(s["price_ok"])
        self.assertEqual(s["verdict"], "FIRE")

    def test_iv_rank_exactly_at_max_is_ok(self):
        s = ew.trigger_status("VST", close=139.00,
                              iv_rank=config.H5_ENTRY_IVR_MAX,
                              leaps_row=_leaps_row())
        self.assertTrue(s["iv_ok"])
        self.assertEqual(s["verdict"], "FIRE")

    def test_missing_chain_file_message_differs_from_no_candidate(self):
        no_cand = ew.trigger_status("VST", close=139.00, iv_rank=0.40,
                                    leaps_row=None)
        no_file = ew.trigger_status("VST", close=139.00, iv_rank=0.40,
                                    leaps_row=None, chain_missing=True)
        self.assertEqual(no_cand["verdict"], "WAIT")
        self.assertEqual(no_file["verdict"], "WAIT")
        self.assertTrue(any("no LEAPS candidate" in u
                            for u in no_cand["unmet"]))
        self.assertTrue(any("no cached chain file" in u
                            for u in no_file["unmet"]))
        self.assertTrue(any("top-up" in u for u in no_file["unmet"]))
        self.assertNotEqual(no_cand["unmet"], no_file["unmet"])


class MainTests(unittest.TestCase):
    def _rows(self):
        return [{"symbol": "VST", "close": 158.63, "trigger": 140.0,
                 "iv_rank": 0.47, "price_ok": False, "iv_ok": True,
                 "liq_ok": True, "unmet": ["close $158.63 > trigger $140.00"],
                 "verdict": "WAIT", "close_asof": "2026-07-06",
                 "chain_asof": "2026-07-06", "iv_asof": "2026-07-02"},
                {"symbol": "AMZN", "close": 219.00, "trigger": 220.0,
                 "iv_rank": 0.30, "price_ok": True, "iv_ok": True,
                 "liq_ok": True, "unmet": [], "verdict": "FIRE",
                 "close_asof": "2026-07-06", "chain_asof": "2026-07-02",
                 "iv_asof": "2026-07-06"}]

    def _run_main(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ew.main(rows=self._rows())
        return buf.getvalue()

    def test_main_refuses_mixed_session_rows(self):
        out = self._run_main()
        self.assertIn("VST", out)
        self.assertNotIn("VST: FIRE", out)
        self.assertNotIn("AMZN: FIRE", out)
        self.assertEqual(out.count("DATA_GAP"), 2)
        self.assertIn("never auto-enters", out)

    def test_main_returns_nonzero_for_data_gap(self):
        self.assertEqual(ew.main(rows=self._rows()), 1)

    def test_main_exact_row_labels_all_three_inputs(self):
        row = self._rows()[1] | {
            "chain_asof": "2026-07-06",
            "evaluation_session": "2026-07-06",
        }
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = ew.main(rows=[row])
        output = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("AMZN: FIRE", output)
        self.assertIn("feature as of 2026-07-06", output)
        self.assertIn("chain as of 2026-07-06", output)


class ExactAsOfGatherTests(unittest.TestCase):
    EVALUATION = date(2026, 7, 15)

    @staticmethod
    def _chain() -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "expiration": "2027-07-16",
                    "strike": 140.0,
                    "right": "C",
                    "bid": 40.0,
                    "ask": 41.0,
                    "open_interest": 500,
                    "delta": 0.70,
                }
            ]
        )

    def _gather(
        self,
        *,
        close_days: tuple[str, ...] = ("2026-07-15",),
        feature_days: tuple[str, ...] = ("2026-07-15",),
        chain_days: tuple[str, ...] = ("2026-07-15",),
        close_value: float = 100.0,
        chain_frame: pd.DataFrame | None = None,
    ) -> list[dict]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chain_dir = root / ".cache" / "chains"
            chain_dir.mkdir(parents=True)
            for symbol in config.H5_ENTRY_TRIGGERS:
                for day in chain_days:
                    (chain_dir / f"{symbol}_{day}.parquet").touch()
            closes = pd.Series(
                [close_value] * len(close_days),
                index=pd.Index(close_days, name="date"),
            )
            features = pd.DataFrame(
                {"iv_rank": [0.2] * len(feature_days)},
                index=pd.Index(feature_days, name="date"),
            )
            with (
                contextlib.chdir(root),
                mock.patch("data.underlying_closes.load_closes", return_value=closes),
                mock.patch(
                    "options_researcher.features.load_features",
                    return_value=features,
                ),
                mock.patch(
                    "pandas.read_parquet",
                    return_value=self._chain() if chain_frame is None else chain_frame,
                ),
            ):
                return ew._gather(self.EVALUATION)

    def test_exact_common_session_can_fire(self):
        rows = self._gather()
        self.assertTrue(rows)
        self.assertTrue(all(row["verdict"] == "FIRE" for row in rows))
        for row in rows:
            self.assertEqual(row["evaluation_session"], "2026-07-15")
            self.assertEqual(row["close_asof"], "2026-07-15")
            self.assertEqual(row["iv_asof"], "2026-07-15")
            self.assertEqual(row["chain_asof"], "2026-07-15")

    def test_stale_close_is_data_gap_not_fire(self):
        rows = self._gather(close_days=("2026-07-14",))
        self.assertTrue(all(row["verdict"] == "DATA_GAP" for row in rows))
        self.assertTrue(all("close" in " ".join(row["data_gaps"]) for row in rows))

    def test_stale_feature_is_data_gap_not_fire(self):
        rows = self._gather(feature_days=("2026-07-14",))
        self.assertTrue(all(row["verdict"] == "DATA_GAP" for row in rows))
        self.assertTrue(all("feature" in " ".join(row["data_gaps"]) for row in rows))

    def test_stale_chain_is_data_gap_not_fire(self):
        rows = self._gather(chain_days=("2026-07-14",))
        self.assertTrue(all(row["verdict"] == "DATA_GAP" for row in rows))
        self.assertTrue(all("chain" in " ".join(row["data_gaps"]) for row in rows))

    def test_future_inputs_are_not_substituted(self):
        rows = self._gather(
            close_days=("2026-07-16",),
            feature_days=("2026-07-16",),
            chain_days=("2026-07-16",),
        )
        self.assertTrue(all(row["verdict"] == "DATA_GAP" for row in rows))
        self.assertTrue(all(row["close_asof"] is None for row in rows))
        self.assertTrue(all(row["iv_asof"] is None for row in rows))
        self.assertTrue(all(row["chain_asof"] is None for row in rows))

    def test_missing_files_are_data_gap_not_fire(self):
        with (
            mock.patch(
                "data.underlying_closes.load_closes",
                side_effect=FileNotFoundError("close missing"),
            ),
            mock.patch(
                "options_researcher.features.load_features",
                side_effect=FileNotFoundError("feature missing"),
            ),
            tempfile.TemporaryDirectory() as tmp,
            contextlib.chdir(tmp),
        ):
            rows = ew._gather(self.EVALUATION)
        self.assertTrue(all(row["verdict"] == "DATA_GAP" for row in rows))
        self.assertTrue(all(len(row["data_gaps"]) == 3 for row in rows))

    def test_nonfinite_exact_close_is_data_gap(self):
        rows = self._gather(close_value=float("nan"))
        self.assertTrue(all(row["verdict"] == "DATA_GAP" for row in rows))
        self.assertTrue(all("non-finite" in " ".join(row["data_gaps"]) for row in rows))

    def test_empty_exact_chain_is_data_gap(self):
        rows = self._gather(chain_frame=self._chain().iloc[0:0])
        self.assertTrue(all(row["verdict"] == "DATA_GAP" for row in rows))
        self.assertTrue(all("empty" in " ".join(row["data_gaps"]) for row in rows))



if __name__ == "__main__":
    unittest.main()
