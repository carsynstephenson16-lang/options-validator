"""tests/test_chains_ladder.py"""
import unittest
from datetime import date

import pandas as pd

from options_researcher.chains import ladder_expirations


def _chain(exp_isos):
    # one throwaway put row per expiration date
    return pd.DataFrame([{"expiration": e, "strike": 100.0, "right": "P",
                          "bid": 1.0, "ask": 1.1, "open_interest": 500,
                          "iv": 0.5, "delta": -0.2} for e in exp_isos])


class LadderExpirationsTests(unittest.TestCase):
    today = date(2026, 7, 9)

    def test_picks_nearest_to_each_target_in_window(self):
        # DTE from 2026-07-09: 17, 32, 63, 95, 124
        chain = _chain(["2026-07-26", "2026-08-10", "2026-09-10",
                        "2026-10-12", "2026-11-10"])
        got = ladder_expirations(chain, self.today)
        self.assertEqual([t for t, _ in got], [14, 30, 60, 90, 120])
        self.assertEqual(got[0][1], date(2026, 7, 26))   # 17 DTE in [10,21]

    def test_skips_bucket_with_no_expiration_in_window(self):
        # only a 17 DTE expiration exists -> only the 14 bucket fills
        chain = _chain(["2026-07-26"])
        got = ladder_expirations(chain, self.today)
        self.assertEqual([t for t, _ in got], [14])

    def test_four_dte_option_excluded_from_two_week_bucket(self):
        # 2026-07-13 is 4 DTE -> below the 14-bucket floor of 10 -> no bucket
        chain = _chain(["2026-07-13"])
        got = ladder_expirations(chain, self.today)
        self.assertEqual(got, [])

    def test_nearest_wins_when_two_in_window(self):
        # 12 DTE and 20 DTE both in [10,21]; 12 is nearer target 14
        chain = _chain(["2026-07-21", "2026-07-29"])
        got = ladder_expirations(chain, self.today)
        self.assertEqual(got[0], (14, date(2026, 7, 21)))

    def test_dedups_multiple_strikes_at_same_expiration(self):
        # realistic chain shape: several strikes share one expiration date
        rows = []
        for k in (95.0, 100.0, 105.0):
            rows.append({"expiration": "2026-07-26", "strike": k, "right": "P",
                         "bid": 1.0, "ask": 1.1, "open_interest": 500,
                         "iv": 0.5, "delta": -0.2})
        chain = pd.DataFrame(rows)
        got = ladder_expirations(chain, self.today)
        self.assertEqual(got, [(14, date(2026, 7, 26))])  # one bucket, one date
