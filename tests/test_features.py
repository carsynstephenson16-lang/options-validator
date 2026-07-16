"""tests/test_features.py"""
import os
import tempfile
import unittest
from datetime import date
from unittest import mock

import numpy as np
import pandas as pd

from options_researcher import features
from options_researcher.features import build_daily_features


def chain_day(iv, expiration):
    return pd.DataFrame([{
        "expiration": expiration, "strike": 100.0, "right": "P",
        "bid": 2.0, "ask": 2.1, "open_interest": 500, "iv": iv,
        "delta": -0.50, "gamma": 0.0, "theta": 0.0, "vega": 0.0}])


def fixture(n_days=300, last_iv=0.90):
    days = pd.bdate_range("2019-01-02", periods=n_days)
    isos = days.strftime("%Y-%m-%d")
    closes = pd.Series(np.full(n_days, 100.0), index=isos)
    chains = {}
    for i, (ts, iso) in enumerate(zip(days, isos)):
        # nearest monthly ~35 calendar days out: use the 3rd Friday trick by
        # just offsetting 35 days -- tests only need SOME in-band expiration;
        # is_monthly is not consulted by atm_iv (nearest_monthly is), so give
        # a REAL 3rd-Friday date to stay honest:
        d = ts.date()
        month = d.month + (2 if d.day > 10 else 1)
        year = d.year + (1 if month > 12 else 0)
        month = month if month <= 12 else month - 12
        from options_researcher.chains import third_friday
        exp_date = third_friday(year, month)
        chains[iso] = chain_day(0.20 if i < n_days - 1 else last_iv,
                                exp_date.isoformat())
    return isos, closes, chains


class FeatureFrameTests(unittest.TestCase):
    def test_constant_closes_give_zero_rv(self):
        isos, closes, chains = fixture(60)
        f = build_daily_features("VST", isos[0], isos[-1],
                                 closes=closes, chains=chains, earnings=[])
        self.assertAlmostEqual(float(f["rv21"].iloc[-1]), 0.0)
        self.assertTrue(np.isnan(float(f["rv21"].iloc[5])))  # warmup NaN

    def test_iv_rank_high_on_spike_day_only_with_min_obs(self):
        isos, closes, chains = fixture(300, last_iv=0.90)
        f = build_daily_features("VST", isos[0], isos[-1],
                                 closes=closes, chains=chains, earnings=[])
        self.assertGreaterEqual(float(f["iv_rank"].iloc[-1]), 0.99)
        short = fixture(100, last_iv=0.90)
        f2 = build_daily_features("VST", short[0][0], short[0][-1],
                                  closes=short[1], chains=short[2], earnings=[])
        self.assertTrue(np.isnan(float(f2["iv_rank"].iloc[-1])))  # <126 obs

    def test_earnings_week_window(self):
        isos, closes, chains = fixture(60)
        e = [date.fromisoformat(isos[40])]
        f = build_daily_features("VST", isos[0], isos[-1],
                                 closes=closes, chains=chains, earnings=e)
        self.assertTrue(bool(f["earnings_week"].loc[isos[35]]))   # 5 bd before
        self.assertTrue(bool(f["earnings_week"].loc[isos[41]]))   # day after
        self.assertFalse(bool(f["earnings_week"].loc[isos[20]]))

    def test_missing_chain_day_gives_nan_iv_not_crash(self):
        isos, closes, chains = fixture(60)
        del chains[isos[30]]
        f = build_daily_features("VST", isos[0], isos[-1],
                                 closes=closes, chains=chains, earnings=[])
        self.assertNotIn(isos[30], f.index)  # day simply absent (fail closed)


class StoreSeparationTests(unittest.TestCase):
    """Regression: 2026-07-16 a features.build_all() run overwrote the
    H6-manifested AMZN artifact (manifest sha 0c14de... vs file fb847e...),
    because both builders wrote .tmp/research/{symbol}_features.parquet.
    The attractiveness store must never share a file path with the
    manifest-bound H6 store."""

    def test_stores_are_different_directories(self):
        from options_researcher import h6_features
        att = os.path.abspath(features.FEATURES_DIR)
        h6 = os.path.abspath(str(h6_features.FEATURE_DIR))
        self.assertNotEqual(att, h6)

    def test_save_features_cannot_clobber_h6_artifact(self):
        import config
        from options_researcher import h6_features
        shared = set(config.UNIVERSE) & set(config.H6_NAMES)
        self.assertTrue(shared, "fixture assumption: universes overlap")
        for symbol in shared:
            att_path = os.path.abspath(os.path.join(
                features.FEATURES_DIR, f"{symbol}_features.parquet"))
            h6_path = os.path.abspath(str(
                h6_features.FEATURE_DIR / f"{symbol}_features.parquet"))
            self.assertNotEqual(att_path, h6_path, symbol)


class CacheRoundTripTests(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        isos, closes, chains = fixture(60)
        f = build_daily_features("VST", isos[0], isos[-1],
                                 closes=closes, chains=chains, earnings=[])
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(features, "FEATURES_DIR", tmp):
                path = features.save_features("VST", f)
                self.assertTrue(os.path.exists(path))
                back = features.load_features("VST")
        pd.testing.assert_frame_equal(back, f)


if __name__ == "__main__":
    unittest.main()
