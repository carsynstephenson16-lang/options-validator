"""tests/test_chains_core.py"""
import unittest
from datetime import date

from options_researcher.chains import is_monthly, third_friday


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


if __name__ == "__main__":
    unittest.main()
