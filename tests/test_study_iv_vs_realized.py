"""tests/test_study_iv_vs_realized.py"""
import unittest

import numpy as np
import pandas as pd

from options_researcher.studies.iv_vs_realized import compute_iv_vs_realized


def fixture_features():
    """400 bdays: first 200 calm (iv .20, tiny moves), last 200 wild
    (iv .60, big moves) -- high-rank days should show larger forward vol."""
    idx = pd.bdate_range("2020-01-02", periods=400).strftime("%Y-%m-%d")
    close = [100.0]
    rng = np.random.default_rng(7)
    for i in range(1, 400):
        step = 0.001 if i < 200 else 0.03
        close.append(close[-1] * (1 + rng.choice([-1, 1]) * step))
    f = pd.DataFrame(index=idx)
    f["close"] = close
    f["atm_iv"] = [0.20] * 200 + [0.60] * 200
    f["iv_rank"] = [0.10] * 200 + [0.90] * 200
    f["earnings_week"] = False
    return f


class StudyATests(unittest.TestCase):
    def test_high_rank_bucket_shows_higher_forward_vol(self):
        out = compute_iv_vs_realized(fixture_features(), horizon_bd=21)
        hi = out[out["bucket"] == "iv_rank>=0.70"]["fwd_rv_median"].iloc[0]
        lo = out[out["bucket"] == "iv_rank<=0.30"]["fwd_rv_median"].iloc[0]
        self.assertGreater(hi, lo)

    def test_buckets_report_counts_and_iv(self):
        out = compute_iv_vs_realized(fixture_features(), horizon_bd=21)
        self.assertEqual(set(out.columns),
                         {"bucket", "n_days", "iv_median", "fwd_rv_median",
                          "fwd_absmove_median_pct", "implied_move_median_pct"})
        self.assertTrue((out["n_days"] > 0).all())


if __name__ == "__main__":
    unittest.main()
