"""tests/test_iv_solver_calibration.py -- offline tests for the IV-solver
calibration tool (options_researcher/iv_solver_calibration.py).

Zero network, zero real cache: every chain is a synthetic in-memory
DataFrame injected via a monkeypatched `load_range`, and data.rates is
monkeypatched to controlled rate/dividend values. Never calibrates against
the real .cache/chains data -- that is an operational, post-merge step, not
a test.
"""
import inspect
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
import pandas as pd

import config
from data import rates as data_rates
from options_researcher import iv_solver_calibration as isc
from options_researcher.black_scholes import bs_price
from options_researcher.chains import third_friday
from research.hashing import config_hash

REPO_ROOT = Path(__file__).resolve().parents[1]

TREASURY_FIELDS_LINE = ",".join(data_rates.TREASURY_FIELDS)
DIVIDEND_FIELDS_LINE = ",".join(data_rates.DIVIDEND_FIELDS)

TODAY = date(2026, 5, 1)
EXPIRATION = third_friday(2026, 6)  # 49 DTE from TODAY -- inside 15-60
R, Q = 0.04, 0.01
STRIKE = 100.0
SPOT = 100.0


def _chain(expiration=EXPIRATION, strike=STRIKE, bid=5.0, ask=5.0,
          iv=0.30, delta=-0.50, right="P"):
    return pd.DataFrame([{
        "expiration": expiration.isoformat(), "strike": strike, "right": right,
        "bid": bid, "ask": ask, "open_interest": 500,
        "iv": iv, "delta": delta, "gamma": 0.01, "theta": -0.02, "vega": 0.10,
    }])


def _priced_chain(true_iv: float, their_iv: float, *, spot=SPOT, strike=STRIKE,
                  expiration=EXPIRATION, today=TODAY, r=R, q=Q):
    """A chain whose put quote is EXACTLY bs_price(true_iv) (zero-width
    spread), with a separately-set cached `iv` (their_iv) -- so
    result.diff == true_iv - their_iv by construction."""
    t = (expiration - today).days / 365.0
    price = bs_price(S=spot, K=strike, t=t, r=r, sigma=true_iv, right="P", q=q)
    return _chain(expiration=expiration, strike=strike, bid=price, ask=price,
                 iv=their_iv, delta=-0.50)


class _FixedRatesMixin:
    """Patches data.rates.risk_free_rate/dividend_yield to fixed values for
    the duration of a test method."""

    def _patch_rates(self, r=R, q=Q):
        patcher_r = mock.patch.object(
            data_rates, "risk_free_rate",
            return_value=SimpleNamespace(rate=r))
        patcher_q = mock.patch.object(
            data_rates, "dividend_yield",
            return_value=SimpleNamespace(yield_rate=q))
        self.addCleanup(patcher_r.stop)
        self.addCleanup(patcher_q.stop)
        patcher_r.start()
        patcher_q.start()


# ---------------------------------------------------------------------------
# _pair_for_session -- per-day pairing and skip-and-log
# ---------------------------------------------------------------------------

class PairForSessionTests(_FixedRatesMixin, unittest.TestCase):
    def setUp(self):
        self._patch_rates()
        self._parity_patcher = mock.patch.object(
            isc, "parity_spot_from_chain", return_value=SPOT)
        self.addCleanup(self._parity_patcher.stop)
        self._parity_patcher.start()

    def test_valid_pair_reports_our_iv_their_iv_and_diff(self):
        chain = _priced_chain(true_iv=0.30, their_iv=0.31)
        pair, reason = isc._pair_for_session("VST", TODAY.isoformat(), chain)
        self.assertIsNone(reason)
        self.assertIsNotNone(pair)
        self.assertAlmostEqual(pair["our_iv"], 0.30, places=4)
        self.assertEqual(pair["their_iv"], 0.31)
        self.assertAlmostEqual(pair["diff"], 0.30 - 0.31, places=4)
        self.assertEqual(pair["day"], TODAY.isoformat())

    def test_no_monthly_expiration_in_band_is_skipped(self):
        # 5 DTE -- outside the 15-60 band nearest_monthly requires.
        near_exp = TODAY + timedelta(days=5)
        chain = _chain(expiration=near_exp)
        pair, reason = isc._pair_for_session("VST", TODAY.isoformat(), chain)
        self.assertIsNone(pair)
        self.assertIn("15-60 DTE band", reason)

    def test_missing_cached_iv_is_skipped(self):
        chain = _chain(iv=float("nan"))
        pair, reason = isc._pair_for_session("VST", TODAY.isoformat(), chain)
        self.assertIsNone(pair)
        self.assertIn("cached ThetaData iv missing/non-finite", reason)

    def test_zero_cached_iv_is_skipped(self):
        chain = _chain(iv=0.0)
        pair, reason = isc._pair_for_session("VST", TODAY.isoformat(), chain)
        self.assertIsNone(pair)
        self.assertIn("cached ThetaData iv missing/non-finite", reason)

    def test_non_finite_parity_spot_is_skipped(self):
        with mock.patch.object(isc, "parity_spot_from_chain",
                               return_value=float("nan")):
            chain = _chain()
            pair, reason = isc._pair_for_session("VST", TODAY.isoformat(), chain)
        self.assertIsNone(pair)
        self.assertIn("parity spot non-finite", reason)

    def test_missing_rate_curve_is_skipped(self):
        with mock.patch.object(data_rates, "risk_free_rate",
                               side_effect=data_rates.MissingRateError("no curve")):
            chain = _chain()
            pair, reason = isc._pair_for_session("VST", TODAY.isoformat(), chain)
        self.assertIsNone(pair)
        self.assertEqual(reason, "no rate curve coverage")

    def test_missing_dividend_data_is_skipped(self):
        with mock.patch.object(
                data_rates, "dividend_yield",
                side_effect=data_rates.MissingDividendYieldError("no div")):
            chain = _chain()
            pair, reason = isc._pair_for_session("VST", TODAY.isoformat(), chain)
        self.assertIsNone(pair)
        self.assertEqual(reason, "no dividend data for VST")

    def test_price_below_intrinsic_reports_solver_reason(self):
        # Deep ITM put priced far BELOW its own intrinsic value -- the
        # bracket check in implied_vol has no root for this price.
        chain = _chain(strike=500.0, bid=0.01, ask=0.01, iv=0.30)
        pair, reason = isc._pair_for_session("VST", TODAY.isoformat(), chain)
        self.assertIsNone(pair)
        self.assertEqual(reason, "solver: no_european_bs_root")


# ---------------------------------------------------------------------------
# calibrate() -- aggregation, pass/fail thresholds, n_sessions slicing
# ---------------------------------------------------------------------------

class CalibrateTests(_FixedRatesMixin, unittest.TestCase):
    def setUp(self):
        self._patch_rates()
        self._parity_patcher = mock.patch.object(
            isc, "parity_spot_from_chain", return_value=SPOT)
        self.addCleanup(self._parity_patcher.stop)
        self._parity_patcher.start()

    def _patch_load_range(self, mapping: dict[str, dict[str, pd.DataFrame]]):
        def fake_load_range(symbol, start_iso, end_iso, *, allow_oos=False):
            return mapping.get(symbol, {})
        patcher = mock.patch.object(isc, "load_range", side_effect=fake_load_range)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_small_consistent_gap_passes(self):
        days = [(TODAY - timedelta(days=i)).isoformat() for i in range(5)]
        chains = {d: _priced_chain(true_iv=0.30, their_iv=0.31,
                                   today=date.fromisoformat(d)) for d in days}
        self._patch_load_range({"VST": chains})
        receipt = isc.calibrate(symbols=["VST"], n_sessions=5, end_iso=TODAY.isoformat())
        name = receipt["per_name"]["VST"]
        self.assertEqual(name["n_pairs"], 5)
        self.assertEqual(name["n_skipped"], 0)
        self.assertAlmostEqual(name["median_abs_diff"], 0.01, places=3)
        self.assertAlmostEqual(name["iqr_width"], 0.0, places=6)
        self.assertTrue(name["pass"])
        self.assertIn("VST", receipt["names_passed"])
        self.assertNotIn("VST", receipt["names_failed"])
        # gap-fix: the per-name receipt is fully auditable -- passing pairs'
        # days are on the receipt, not just skips.
        self.assertEqual(len(name["pairs"]), 5)
        for pair in name["pairs"]:
            self.assertEqual(
                set(pair), {"day", "our_iv", "their_iv", "diff", "expiration", "strike"})
        self.assertEqual(sorted(p["day"] for p in name["pairs"]), sorted(days))

    def test_large_gap_fails_with_reason(self):
        days = [(TODAY - timedelta(days=i)).isoformat() for i in range(5)]
        chains = {d: _priced_chain(true_iv=0.30, their_iv=0.45,
                                   today=date.fromisoformat(d)) for d in days}
        self._patch_load_range({"VST": chains})
        receipt = isc.calibrate(symbols=["VST"], n_sessions=5, end_iso=TODAY.isoformat())
        name = receipt["per_name"]["VST"]
        self.assertFalse(name["pass"])
        self.assertIn("VST", receipt["names_failed"])
        self.assertIn("median_abs_diff", receipt["names_failed"]["VST"])

    def test_insufficient_pairs_fails_closed(self):
        self._patch_load_range({"VST": {}})
        receipt = isc.calibrate(symbols=["VST"], n_sessions=5, end_iso=TODAY.isoformat())
        name = receipt["per_name"]["VST"]
        self.assertEqual(name["n_pairs"], 0)
        self.assertEqual(name["pairs"], [])
        self.assertFalse(name["pass"])
        self.assertIn("insufficient pairs", name["fail_reason"])
        self.assertIn("VST", receipt["names_failed"])

    def test_n_sessions_keeps_only_the_trailing_days(self):
        days = sorted((TODAY - timedelta(days=i)).isoformat() for i in range(10))
        chains = {d: _priced_chain(true_iv=0.30, their_iv=0.31,
                                   today=date.fromisoformat(d)) for d in days}
        self._patch_load_range({"VST": chains})
        receipt = isc.calibrate(symbols=["VST"], n_sessions=3, end_iso=TODAY.isoformat())
        name = receipt["per_name"]["VST"]
        self.assertEqual(name["n_sessions_considered"], 3)
        self.assertEqual(name["n_pairs"], 3)

    def test_median_and_iqr_match_numpy_on_a_nontrivial_sample(self):
        diffs_wanted = [-0.01, -0.01, -0.03, 0.0, 0.02]
        days = sorted((TODAY - timedelta(days=i)).isoformat()
                     for i in range(len(diffs_wanted)))
        chains = {}
        for day_iso, d in zip(days, diffs_wanted):
            # our_iv fixed at 0.30; their_iv chosen so diff == d exactly.
            chains[day_iso] = _priced_chain(true_iv=0.30, their_iv=0.30 - d,
                                            today=date.fromisoformat(day_iso))
        self._patch_load_range({"VST": chains})
        receipt = isc.calibrate(symbols=["VST"], n_sessions=len(diffs_wanted),
                                end_iso=TODAY.isoformat())
        name = receipt["per_name"]["VST"]
        expected_median_abs = float(np.median([abs(d) for d in diffs_wanted]))
        q1, q3 = (float(x) for x in np.percentile(diffs_wanted, [25, 75]))
        self.assertAlmostEqual(name["median_abs_diff"], expected_median_abs, places=6)
        self.assertAlmostEqual(name["iqr_width"], q3 - q1, places=6)

    def test_receipt_schema_and_config_hash(self):
        days = [(TODAY - timedelta(days=i)).isoformat() for i in range(3)]
        chains = {d: _priced_chain(true_iv=0.30, their_iv=0.31,
                                   today=date.fromisoformat(d)) for d in days}
        self._patch_load_range({"VST": chains, "CEG": {}})
        receipt = isc.calibrate(symbols=["VST", "CEG"], n_sessions=3,
                                end_iso=TODAY.isoformat())
        self.assertEqual(receipt["receipt_kind"], "iv_solver_calibration/v1")
        self.assertEqual(receipt["sessions_evaluated"], 3)
        self.assertEqual(receipt["end_iso"], TODAY.isoformat())
        self.assertIn("run_at_utc", receipt)
        self.assertIn("contract_selection", receipt)
        self.assertEqual(receipt["config_hash"], config_hash())
        self.assertEqual(receipt["names_passed"], ["VST"])
        self.assertIn("CEG", receipt["names_failed"])
        # JSON-serializable with the same discipline the receipt writer uses.
        import json
        json.dumps(receipt, sort_keys=True, allow_nan=False)


# ---------------------------------------------------------------------------
# Write-once receipt
# ---------------------------------------------------------------------------

class ReceiptWriteOnceTests(unittest.TestCase):
    def test_identical_rerun_is_a_benign_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2026-05-01.json"
            receipt = {"a": 1, "b": [1, 2, 3]}
            self.assertTrue(isc._write_receipt(receipt, path))
            first = path.read_bytes()
            self.assertTrue(isc._write_receipt(receipt, path))
            self.assertEqual(path.read_bytes(), first)

    def test_conflicting_rerun_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2026-05-01.json"
            self.assertTrue(isc._write_receipt({"a": 1}, path))
            before = path.read_bytes()
            self.assertFalse(isc._write_receipt({"a": 2}, path))
            self.assertEqual(path.read_bytes(), before)

    def test_receipt_path_is_named_by_run_date(self):
        p = isc.receipt_path(Path("reports/iv_solver_calibration"), date(2026, 5, 1))
        self.assertEqual(p, Path("reports/iv_solver_calibration/2026-05-01.json"))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class MainCLITests(unittest.TestCase):
    def test_main_forwards_args_to_calibrate(self):
        calls = {}

        def fake_calibrate(symbols=None, n_sessions=config.IV_CALIBRATION_SESSIONS,
                           end_iso=None, *, retrospective=False):
            calls["symbols"] = symbols
            calls["n_sessions"] = n_sessions
            calls["end_iso"] = end_iso
            calls["retrospective"] = retrospective
            return {"names_passed": [], "names_failed": {}}

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(isc, "calibrate", fake_calibrate), \
                 mock.patch.object(isc, "RECEIPT_DIR", Path(tmp)):
                rc = isc.main(["--symbols", "VST,CEG", "--n-sessions", "10",
                              "--end", "2026-05-01"])
        self.assertEqual(rc, 0)
        self.assertEqual(calls["symbols"], ["VST", "CEG"])
        self.assertEqual(calls["n_sessions"], 10)
        self.assertEqual(calls["end_iso"], "2026-05-01")
        # default-off: the flag is False and unset unless explicitly passed.
        self.assertFalse(calls["retrospective"])

    def test_main_forwards_retrospective_flag_when_set(self):
        calls = {}

        def fake_calibrate(symbols=None, n_sessions=config.IV_CALIBRATION_SESSIONS,
                           end_iso=None, *, retrospective=False):
            calls["retrospective"] = retrospective
            return {"names_passed": [], "names_failed": {}}

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(isc, "calibrate", fake_calibrate), \
                 mock.patch.object(isc, "RECEIPT_DIR", Path(tmp)):
                rc = isc.main(["--allow-retrospective-inputs", "--end", "2026-05-01"])
        self.assertEqual(rc, 0)
        self.assertTrue(calls["retrospective"])

    def test_main_writes_receipt_and_returns_2_on_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt_dir = Path(tmp)
            fixed_receipt = {
                "receipt_kind": "iv_solver_calibration/v1",
                "run_at_utc": datetime(2026, 5, 1, tzinfo=timezone.utc).isoformat(),
                "sessions_evaluated": 1, "end_iso": "2026-05-01",
                "contract_selection": "x", "config_hash": "abc",
                "per_name": {}, "names_passed": [], "names_failed": {},
            }
            with mock.patch.object(isc, "calibrate", return_value=fixed_receipt), \
                 mock.patch.object(isc, "RECEIPT_DIR", receipt_dir), \
                 mock.patch("options_researcher.iv_solver_calibration.date") as fake_date:
                fake_date.today.return_value = date(2026, 5, 1)
                fake_date.fromisoformat = date.fromisoformat
                rc1 = isc.main([])
                rc2 = isc.main([])
                different = dict(fixed_receipt, sessions_evaluated=999)
                with mock.patch.object(isc, "calibrate", return_value=different):
                    rc3 = isc.main([])
        self.assertEqual(rc1, 0)
        self.assertEqual(rc2, 0)
        self.assertEqual(rc3, 2)

    def test_strict_and_retrospective_receipts_coexist_same_day_write_once(self):
        # Distinct receipt path per mode; write-once semantics hold for
        # BOTH -- neither overwrites the other, and each is independently
        # idempotent on rerun.
        with tempfile.TemporaryDirectory() as tmp:
            receipt_dir = Path(tmp)
            strict_receipt = {
                "receipt_kind": "iv_solver_calibration/v1", "sessions_evaluated": 1,
                "end_iso": "2026-05-01", "names_passed": [], "names_failed": {},
            }
            retro_receipt = {
                "receipt_kind": "iv_solver_calibration/v1", "sessions_evaluated": 1,
                "end_iso": "2026-05-01", "names_passed": [], "names_failed": {},
                "inputs_mode": "retrospective_official",
            }

            def fake_calibrate(symbols=None, n_sessions=config.IV_CALIBRATION_SESSIONS,
                               end_iso=None, *, retrospective=False):
                return dict(retro_receipt) if retrospective else dict(strict_receipt)

            with mock.patch.object(isc, "calibrate", fake_calibrate), \
                 mock.patch.object(isc, "RECEIPT_DIR", receipt_dir), \
                 mock.patch("options_researcher.iv_solver_calibration.date") as fake_date:
                fake_date.today.return_value = date(2026, 5, 1)
                fake_date.fromisoformat = date.fromisoformat
                rc_strict_1 = isc.main([])
                rc_retro_1 = isc.main(["--allow-retrospective-inputs"])
                # rerun both -- idempotent no-ops, no conflict, no overwrite.
                rc_strict_2 = isc.main([])
                rc_retro_2 = isc.main(["--allow-retrospective-inputs"])

            self.assertEqual(
                [rc_strict_1, rc_retro_1, rc_strict_2, rc_retro_2], [0, 0, 0, 0])
            strict_path = receipt_dir / "2026-05-01.json"
            retro_path = receipt_dir / "2026-05-01-retrospective.json"
            self.assertTrue(strict_path.exists())
            self.assertTrue(retro_path.exists())
            self.assertNotEqual(strict_path.read_text(), retro_path.read_text())
            self.assertNotIn("inputs_mode", strict_path.read_text())
            self.assertIn("retrospective_official", retro_path.read_text())


# ---------------------------------------------------------------------------
# Retrospective helpers (--allow-retrospective-inputs) -- direct unit tests
# ---------------------------------------------------------------------------

class RetrospectiveHelpersTests(unittest.TestCase):
    """Offline, fixture-CSV tests: no network, no real .cache/data files."""

    def _write_treasury_csv(self, tmp: Path, rows: list[str]) -> Path:
        path = Path(tmp) / "treasury_cmt.csv"
        path.write_text(TREASURY_FIELDS_LINE + "\n" + "\n".join(rows) + "\n")
        return path

    def _write_dividend_csv(self, tmp: Path, rows: list[str]) -> Path:
        path = Path(tmp) / "expected_dividends.csv"
        path.write_text(DIVIDEND_FIELDS_LINE + "\n" + "\n".join(rows) + "\n")
        return path

    def test_retrospective_rate_finds_a_historical_date_strict_mode_refuses(self):
        # A row "backfilled today" for a historical observation_date: its
        # known_as_of_utc is honestly AFTER that date's 16:00 ET valuation
        # close, so the strict point-in-time gate correctly refuses it.
        obs = date(2026, 1, 5)
        exp = date(2026, 3, 1)
        k = "2026-07-24T15:00:00+00:00"  # captured "today" -- backfilled known_as_of
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_treasury_csv(tmp, [
                f"2026-01-05,30,0.030000,{k},2026-01-09,https://home.treasury.gov/x,"
                f"{k},decimal_annual_par_yield",
                f"2026-01-05,91,0.032000,{k},2026-01-09,https://home.treasury.gov/x,"
                f"{k},decimal_annual_par_yield",
            ])

            with self.assertRaises(data_rates.MissingRateError):
                data_rates.risk_free_rate(obs, exp, path=path)

            rate = isc._retrospective_risk_free_rate(obs, exp, path=path)

        days = (exp - obs).days
        expected_par = data_rates.interp_rate({30: 0.030000, 91: 0.032000}, days)
        expected_rate = data_rates.par_to_continuous(expected_par)
        self.assertAlmostEqual(rate, expected_rate, places=10)

    def test_retrospective_rate_selects_exact_observation_date_row(self):
        # Two dates on file; the retrospective lookup must use the row for
        # the OBSERVATION DATE ITSELF, not a nearby/forward-filled one.
        known = "2026-07-24T15:00:00+00:00"
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_treasury_csv(tmp, [
                f"2026-01-05,30,0.030000,{known},2026-01-09,https://home.treasury.gov/x,"
                f"{known},decimal_annual_par_yield",
                f"2026-01-06,30,0.099000,{known},2026-01-10,https://home.treasury.gov/x,"
                f"{known},decimal_annual_par_yield",
            ])
            rate_05 = isc._retrospective_risk_free_rate(
                date(2026, 1, 5), date(2026, 2, 4), path=path)
            rate_06 = isc._retrospective_risk_free_rate(
                date(2026, 1, 6), date(2026, 2, 5), path=path)
        self.assertAlmostEqual(rate_05, data_rates.par_to_continuous(0.030000), places=10)
        self.assertAlmostEqual(rate_06, data_rates.par_to_continuous(0.099000), places=10)

    def test_retrospective_rate_raises_missing_rate_error_when_no_row_for_date(self):
        known = "2026-07-24T15:00:00+00:00"
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_treasury_csv(tmp, [
                f"2026-01-05,30,0.030000,{known},2026-01-09,https://home.treasury.gov/x,"
                f"{known},decimal_annual_par_yield",
            ])
            with self.assertRaises(data_rates.MissingRateError):
                isc._retrospective_risk_free_rate(
                    date(2026, 1, 6), date(2026, 2, 5), path=path)

    def test_retrospective_dividend_finds_a_historical_date_strict_mode_refuses(self):
        # The dividend's effective_date is AFTER the historical
        # observation_date -- strict mode's window (effective_date <= obs)
        # correctly refuses it. Retrospective mode ignores the window
        # entirely and applies the current estimate.
        obs = date(2026, 1, 5)
        known = "2026-07-24T15:00:00+00:00"
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_dividend_csv(tmp, [
                f"VST,2026-04-30,0.916,{known},2026-08-03,"
                f"https://example.com/ir,{known},usd_per_share_per_year",
            ])
            with self.assertRaises(data_rates.MissingDividendYieldError):
                data_rates.dividend_yield("VST", obs, 100.0, path=path)

            q = isc._retrospective_dividend_yield("VST", 100.0, path=path)
        self.assertAlmostEqual(q, 0.916 / 100.0, places=10)

    def test_retrospective_dividend_picks_the_freshest_row_for_symbol(self):
        known = "2026-07-24T15:00:00+00:00"
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_dividend_csv(tmp, [
                f"VST,2026-01-30,0.500,{known},2026-05-03,"
                f"https://example.com/ir,{known},usd_per_share_per_year",
                f"VST,2026-04-30,0.916,{known},2026-08-03,"
                f"https://example.com/ir,{known},usd_per_share_per_year",
            ])
            q = isc._retrospective_dividend_yield("VST", 100.0, path=path)
        self.assertAlmostEqual(q, 0.916 / 100.0, places=10)

    def test_retrospective_dividend_raises_when_symbol_absent(self):
        known = "2026-07-24T15:00:00+00:00"
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_dividend_csv(tmp, [
                f"VST,2026-04-30,0.916,{known},2026-08-03,"
                f"https://example.com/ir,{known},usd_per_share_per_year",
            ])
            with self.assertRaises(data_rates.MissingDividendYieldError):
                isc._retrospective_dividend_yield("CEG", 100.0, path=path)


# ---------------------------------------------------------------------------
# Retrospective mode wired through _pair_for_session / calibrate()
# ---------------------------------------------------------------------------

class RetrospectiveIntegrationTests(_FixedRatesMixin, unittest.TestCase):
    def setUp(self):
        self._patch_rates()  # strict-mode data_rates.* stay mocked to R, Q
        self._parity_patcher = mock.patch.object(
            isc, "parity_spot_from_chain", return_value=SPOT)
        self.addCleanup(self._parity_patcher.stop)
        self._parity_patcher.start()

    def test_pair_for_session_uses_retrospective_helpers_when_flag_set(self):
        retro_r, retro_q = 0.10, 0.05  # deliberately different from R, Q
        chain = _priced_chain(true_iv=0.30, their_iv=0.31, r=retro_r, q=retro_q)
        with mock.patch.object(isc, "_retrospective_risk_free_rate",
                               return_value=retro_r) as fake_r, \
             mock.patch.object(isc, "_retrospective_dividend_yield",
                               return_value=retro_q) as fake_q:
            pair, reason = isc._pair_for_session(
                "VST", TODAY.isoformat(), chain, retrospective=True)
        self.assertIsNone(reason)
        self.assertAlmostEqual(pair["our_iv"], 0.30, places=4)
        fake_r.assert_called_once()
        fake_q.assert_called_once()

    def test_pair_for_session_default_off_never_calls_retrospective_helpers(self):
        chain = _priced_chain(true_iv=0.30, their_iv=0.31)
        with mock.patch.object(isc, "_retrospective_risk_free_rate") as fake_r, \
             mock.patch.object(isc, "_retrospective_dividend_yield") as fake_q:
            pair, reason = isc._pair_for_session("VST", TODAY.isoformat(), chain)
        self.assertIsNone(reason)
        fake_r.assert_not_called()
        fake_q.assert_not_called()

    def test_retrospective_missing_rate_is_skipped_same_as_strict(self):
        chain = _chain()
        with mock.patch.object(
                isc, "_retrospective_risk_free_rate",
                side_effect=data_rates.MissingRateError("no curve")):
            pair, reason = isc._pair_for_session(
                "VST", TODAY.isoformat(), chain, retrospective=True)
        self.assertIsNone(pair)
        self.assertEqual(reason, "no rate curve coverage")

    def test_calibrate_default_off_receipt_has_no_retrospective_keys(self):
        days = [(TODAY - timedelta(days=i)).isoformat() for i in range(3)]
        chains = {d: _priced_chain(true_iv=0.30, their_iv=0.31,
                                   today=date.fromisoformat(d)) for d in days}
        with mock.patch.object(isc, "load_range",
                               side_effect=lambda s, a, b, allow_oos=False: chains):
            receipt = isc.calibrate(symbols=["VST"], n_sessions=3, end_iso=TODAY.isoformat())
        self.assertNotIn("inputs_mode", receipt)
        self.assertNotIn("disclosure", receipt)

    def test_calibrate_retrospective_receipt_discloses_inputs_mode_and_disclosures(self):
        days = [(TODAY - timedelta(days=i)).isoformat() for i in range(3)]
        chains = {d: _priced_chain(true_iv=0.30, their_iv=0.31,
                                   today=date.fromisoformat(d)) for d in days}
        with mock.patch.object(isc, "load_range",
                               side_effect=lambda s, a, b, allow_oos=False: chains), \
             mock.patch.object(isc, "_retrospective_risk_free_rate", return_value=R), \
             mock.patch.object(isc, "_retrospective_dividend_yield", return_value=Q):
            receipt = isc.calibrate(symbols=["VST"], n_sessions=3, end_iso=TODAY.isoformat(),
                                    retrospective=True)
        self.assertEqual(receipt["inputs_mode"], "retrospective_official")
        self.assertEqual(
            receipt["disclosure"]["rates"],
            "official published Treasury par yields used retrospectively — "
            "immutable public record, no revision risk; acceptable for "
            "convention-diff measurement, banned for strategy backtests")
        self.assertEqual(
            receipt["disclosure"]["dividends"],
            "current expected-dividend estimates applied retrospectively — an "
            "approximation; dividend sensitivity at 15-60 DTE is small but nonzero")
        # JSON-serializable with the same discipline the receipt writer uses.
        import json
        json.dumps(receipt, sort_keys=True, allow_nan=False)


# ---------------------------------------------------------------------------
# Boundary: the retrospective bypass stays local to this module
# ---------------------------------------------------------------------------

class RetrospectiveBoundaryTests(unittest.TestCase):
    def test_data_rates_public_functions_have_no_retrospective_or_bypass_param(self):
        banned_substrings = ("retrospective", "bypass", "ignore_known_as_of",
                             "skip_known_as_of", "allow_stale")
        for func in (data_rates.risk_free_rate, data_rates.dividend_yield,
                    data_rates.require_dividend_coverage):
            for param_name in inspect.signature(func).parameters:
                lowered = param_name.lower()
                self.assertFalse(
                    any(banned in lowered for banned in banned_substrings),
                    f"data.rates.{func.__name__} must not gain a retrospective/"
                    f"bypass parameter (found {param_name!r})")

    def test_no_module_outside_iv_solver_calibration_imports_retrospective_helpers(self):
        helper_names = ("_retrospective_risk_free_rate", "_retrospective_dividend_yield")
        offenders = []
        for py_file in sorted(REPO_ROOT.rglob("*.py")):
            if any(part in (".venv", "__pycache__", ".git", "node_modules")
                  for part in py_file.parts):
                continue
            if py_file.name == "iv_solver_calibration.py":
                continue
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                stripped = line.strip()
                if not stripped.startswith(("from ", "import ")):
                    continue
                if any(name in stripped for name in helper_names):
                    offenders.append(f"{py_file}: {stripped}")
        self.assertEqual(
            offenders, [],
            f"retrospective helpers must only be imported inside "
            f"iv_solver_calibration.py itself: {offenders}")


if __name__ == "__main__":
    unittest.main()
