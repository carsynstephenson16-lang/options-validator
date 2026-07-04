"""tests/test_chains_core.py"""
import unittest
from datetime import date
from unittest import mock

import pandas as pd

from options_researcher import chains
from options_researcher.chains import (
    atm_row,
    is_monthly,
    liquid_strikes,
    load_range,
    nearest_monthly,
    puts_in_window,
    third_friday,
)


class CalendarTests(unittest.TestCase):
    def test_third_friday_known_months(self):
        self.assertEqual(third_friday(2026, 7), date(2026, 7, 17))
        self.assertEqual(third_friday(2024, 6), date(2024, 6, 21))
        self.assertEqual(third_friday(2025, 4), date(2025, 4, 18))

    def test_monthly_is_third_friday(self):
        self.assertTrue(is_monthly(date(2024, 6, 21)))
        self.assertFalse(is_monthly(date(2024, 6, 14)))   # ordinary weekly
        self.assertFalse(is_monthly(date(2024, 6, 28)))

    def test_holiday_thursday_counts_as_monthly(self):
        # 2025-04-18 is Good Friday; listed monthly expiration moves to
        # Thursday 2025-04-17. Both dates classify as monthly.
        self.assertTrue(is_monthly(date(2025, 4, 17)))
        self.assertTrue(is_monthly(date(2025, 4, 18)))
        # A Thursday NOT adjacent to the 3rd Friday is never monthly. (The
        # Thursday immediately BEFORE a 3rd Friday is always classified
        # monthly by design: listed options only expire on such Thursdays
        # via holiday shifts, so the predicate needs no holiday calendar.)
        self.assertFalse(is_monthly(date(2024, 6, 13)))   # Thu before 2nd Friday


def fixture_chain():
    """Two expirations: weekly 2024-06-14 (thin) and monthly 2024-06-21."""
    rows = []
    for exp, oi, delta in (
        ("2024-06-14", 10, -0.48),
        ("2024-06-21", 150, -0.48),
        ("2024-06-21", 200, -0.60),
        ("2024-06-21", 50, -0.30),
    ):
        rows.append({"expiration": exp, "strike": 100.0 - 100 * delta,
                     "right": "P", "bid": 2.00, "ask": 2.10,
                     "open_interest": oi, "iv": 0.30, "delta": delta,
                     "gamma": 0.0, "theta": 0.0, "vega": 0.0})
    rows.append({"expiration": "2024-06-21", "strike": 90.0, "right": "P",
                 "bid": 1.00, "ask": 0.90,       # crossed -> never liquid
                 "open_interest": 500, "iv": 0.30, "delta": -0.20,
                 "gamma": 0.0, "theta": 0.0, "vega": 0.0})
    rows.append({"expiration": "2024-06-21", "strike": 130.0, "right": "C",
                 "bid": 2.00, "ask": 2.10, "open_interest": 300, "iv": 0.30,
                 "delta": 0.48, "gamma": 0.0, "theta": 0.0, "vega": 0.0})
    return pd.DataFrame(rows)


class SelectionTests(unittest.TestCase):
    TODAY = date(2024, 5, 24)

    def test_puts_in_window_filters_right_quotes_and_dte(self):
        win = puts_in_window(fixture_chain(), self.TODAY, 15, 60)
        self.assertTrue((win["right"] == "P").all())
        self.assertNotIn(90.0, win["strike"].values)      # crossed quote out
        self.assertTrue(win["dte"].between(15, 60).all())

    def test_nearest_monthly_skips_weekly(self):
        exp = nearest_monthly(fixture_chain(), self.TODAY)
        self.assertEqual(exp, date(2024, 6, 21))

    def test_nearest_monthly_none_when_no_monthly_in_band(self):
        chain = fixture_chain()
        weekly_only = chain[chain["expiration"] == "2024-06-14"]
        self.assertIsNone(nearest_monthly(weekly_only, self.TODAY))

    def test_atm_row_picks_nearest_abs_delta_for_right(self):
        row = atm_row(fixture_chain(), date(2024, 6, 21))
        self.assertAlmostEqual(float(row["delta"]), -0.48)
        call = atm_row(fixture_chain(), date(2024, 6, 21), right="C")
        self.assertAlmostEqual(float(call["delta"]), 0.48)

    def test_atm_row_none_for_missing_expiration(self):
        self.assertIsNone(atm_row(fixture_chain(), date(2024, 7, 19)))

    def test_liquid_strikes_uses_frozen_gates(self):
        # puts on 2024-06-21: OI 150 ok, 200 ok, 50 below floor, crossed out
        self.assertEqual(liquid_strikes(fixture_chain(), date(2024, 6, 21)), 2)

    def test_load_range_passes_allow_oos_through(self):
        with mock.patch.object(chains, "load_cached_chains",
                               return_value={}) as m:
            load_range("VST", "2024-01-01", "2024-02-01", allow_oos=True)
        m.assert_called_once_with("VST", "2024-01-01", "2024-02-01",
                                  allow_oos=True)


if __name__ == "__main__":
    unittest.main()
