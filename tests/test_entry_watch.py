"""tests/test_entry_watch.py"""
import contextlib
import io
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

import pandas as pd
from test_schwab_chain_view import _chain_frame, _write_store

import config
from options_researcher import entry_watch as ew
from options_researcher import schwab_chain_view


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


@unittest.skip("retired injected-trigger report API; observer tests cover the real path")
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


@unittest.skip("retired cache/feature gather API; observer tests cover verified Schwab")
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


class H5SchwabObserverTests(unittest.TestCase):
    RUN_DATE = "2026-08-20"
    EVALUATION = "2026-08-19"

    def _run(self, root: Path, *, run_date: str = RUN_DATE,
             close_loader=None) -> tuple[int, str]:
        if close_loader is None:
            close_loader = lambda *_args, **_kwargs: pd.Series(
                [100.0], index=[self.EVALUATION])
        stdout = io.StringIO()
        schwab_chain_view._reset_memo_for_tests()
        try:
            with (
                mock.patch.object(
                    schwab_chain_view, "_dirs",
                    return_value=(root / ".cache" / "schwab_chains",
                                  root / "reports" / "schwab_chains")),
                mock.patch("data.underlying_closes.load_closes",
                           side_effect=close_loader),
                mock.patch.object(ew, "datetime") as watch_datetime,
                contextlib.redirect_stdout(stdout),
            ):
                watch_datetime.now.return_value = datetime(
                    2026, 8, 21, 12, 0, tzinfo=timezone.utc)
                rc = ew.main(as_of=run_date)
        finally:
            schwab_chain_view._reset_memo_for_tests()
        return rc, stdout.getvalue()

    def test_real_path_uses_unscaled_schwab_atm_iv_without_a_fire_output(self):
        """A feature-store read or a second IV divide breaks this report."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frames = {symbol: _chain_frame(iv=0.43210)
                      for symbol in config.H5_ENTRY_TRIGGERS}
            _write_store(root, sorted(config.H5_ENTRY_TRIGGERS),
                         session=self.EVALUATION, frames=frames)
            with mock.patch("options_researcher.features.load_features",
                            side_effect=AssertionError("feature IV is forbidden")):
                rc, output = self._run(root)

        self.assertEqual(rc, 0, output)
        self.assertIn("observational / non-verdict-bearing", output)
        self.assertIn("max_asof_session=2026-08-19", output)
        self.assertIn("capture_available=True", output)
        self.assertIn("ATM Schwab IV 0.44210", output)
        self.assertIn("1/126 finite Schwab observations", output)
        self.assertNotIn("FIRE", output)

    def test_pre_floor_run_refuses_before_loading_inputs(self):
        calls: list[str] = []

        def forbidden(*_args, **_kwargs):
            calls.append("close")
            raise AssertionError("floor refusal must precede source loading")

        with tempfile.TemporaryDirectory() as tmp:
            rc, output = self._run(Path(tmp), run_date="2026-08-19",
                                   close_loader=forbidden)

        self.assertEqual(rc, 2, output)
        self.assertEqual(calls, [])
        self.assertIn("evaluation_session=2026-08-18", output)
        self.assertIn(config.H5_RESUME_FLOOR_SESSION, output)
        self.assertNotIn("OBSERVED", output)

    def test_verified_history_counts_one_h5_atm_iv_per_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            symbols = sorted((*config.H5_ENTRY_TRIGGERS, "PLTR"))
            frames = {symbol: _chain_frame(iv=0.43210) for symbol in symbols}
            _write_store(root, symbols, session="2026-08-18", frames=frames)
            _write_store(root, symbols, session=self.EVALUATION, frames=frames)
            rc, output = self._run(root)

        self.assertEqual(rc, 0, output)
        self.assertIn("2/126 finite Schwab observations", output)
        self.assertIn("VST: OBSERVED", output)
        self.assertIn("AMZN: OBSERVED", output)
        self.assertNotIn("PLTR:", output)

    def test_stale_or_future_capture_cannot_substitute_for_the_exact_session(self):
        for session in ("2026-08-18", "2026-08-20"):
            with self.subTest(session=session), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _write_store(root, sorted(config.H5_ENTRY_TRIGGERS), session=session)
                rc, output = self._run(root)
            self.assertEqual(rc, 1, output)
            self.assertIn("exact verified Schwab capture", output)
            self.assertIn("capture_available=False", output)
            self.assertNotIn("OBSERVED", output)

    def test_missing_stale_future_or_nonfinite_price_fails_closed(self):
        sources = {
            "missing": FileNotFoundError("close missing"),
            "stale": pd.Series([100.0], index=["2026-08-18"]),
            "future": pd.Series([100.0], index=["2026-08-20"]),
            "nonfinite": pd.Series([float("nan")], index=[self.EVALUATION]),
        }
        for name, source in sources.items():
            with self.subTest(source=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _write_store(root, sorted(config.H5_ENTRY_TRIGGERS),
                             session=self.EVALUATION)
                if isinstance(source, Exception):
                    loader = mock.Mock(side_effect=source)
                else:
                    loader = mock.Mock(return_value=source)
                rc, output = self._run(root, close_loader=loader)

            self.assertEqual(rc, 1, output)
            self.assertIn("close", output)
            self.assertIn("capture_available=True", output)
            self.assertNotIn("OBSERVED", output)

    def test_partial_and_unverified_exact_packages_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_store(root, ["VST"], session=self.EVALUATION)
            partial_rc, partial_output = self._run(root)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_store(root, sorted(config.H5_ENTRY_TRIGGERS),
                         session=self.EVALUATION)
            _chain_frame(iv=0.61).to_parquet(
                root / ".cache" / "schwab_chains" / f"VST_{self.EVALUATION}.parquet")
            unverified_rc, unverified_output = self._run(root)

        self.assertEqual(partial_rc, 1, partial_output)
        self.assertIn("partial H5 universe", partial_output)
        self.assertNotIn("OBSERVED", partial_output)
        self.assertEqual(unverified_rc, 1, unverified_output)
        self.assertIn("unverified", unverified_output)
        self.assertNotIn("OBSERVED", unverified_output)

    def test_malformed_verified_chain_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            malformed = _chain_frame().drop(columns=["gamma"])
            frames = {symbol: malformed for symbol in config.H5_ENTRY_TRIGGERS}
            _write_store(root, sorted(config.H5_ENTRY_TRIGGERS),
                         session=self.EVALUATION, frames=frames)
            rc, output = self._run(root)

        self.assertEqual(rc, 1, output)
        self.assertIn("malformed", output)
        self.assertNotIn("OBSERVED", output)

    def test_nonfinite_atm_iv_does_not_increment_the_schwab_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frames = {symbol: _chain_frame(iv=float("nan"))
                      for symbol in config.H5_ENTRY_TRIGGERS}
            _write_store(root, sorted(config.H5_ENTRY_TRIGGERS),
                         session=self.EVALUATION, frames=frames)
            rc, output = self._run(root)

        self.assertEqual(rc, 0, output)
        self.assertIn("ATM Schwab IV unavailable", output)
        self.assertIn("0/126 finite Schwab observations", output)



if __name__ == "__main__":
    unittest.main()
