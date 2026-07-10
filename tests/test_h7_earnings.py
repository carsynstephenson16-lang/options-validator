"""Earnings ban: no new H7 entries within H7_EARNINGS_BAN_SESSIONS before a
report. Estimated dates are handled conservatively: the ban starts before the
EARLIEST estimate for the symbol and stays on until past the LATEST."""

import unittest
from datetime import date

from options_researcher.h7_earnings import entries_banned, load_calendar


class TestEarningsBan(unittest.TestCase):
    def _cal(self):
        return load_calendar()  # reads data/earnings/calendar.csv

    def test_confirmed_date_bans_window_before(self):
        cal = self._cal()
        # NOW reports 2026-07-22 (confirmed). 5 sessions before = banned.
        self.assertTrue(entries_banned("NOW", date(2026, 7, 20), cal))
        self.assertTrue(entries_banned("NOW", date(2026, 7, 15), cal))
        self.assertFalse(entries_banned("NOW", date(2026, 7, 10), cal))
        # day after the report: allowed again
        self.assertFalse(entries_banned("NOW", date(2026, 7, 23), cal))

    def test_estimated_dates_ban_conservatively(self):
        cal = self._cal()
        # CRWV: estimates 08-11 and 08-18 -> ban from 5 sessions before 08-11
        # through 08-18 inclusive.
        self.assertTrue(entries_banned("CRWV", date(2026, 8, 5), cal))
        self.assertTrue(entries_banned("CRWV", date(2026, 8, 14), cal))
        self.assertTrue(entries_banned("CRWV", date(2026, 8, 18), cal))
        self.assertFalse(entries_banned("CRWV", date(2026, 8, 19), cal))
        self.assertFalse(entries_banned("CRWV", date(2026, 7, 28), cal))

    def test_unknown_symbol_is_never_banned(self):
        cal = self._cal()
        self.assertFalse(entries_banned("MSFT", date(2026, 7, 20), cal))

    def test_confirmed_supersedes_estimates(self):
        cal = {"X": {"confirmed": [date(2026, 8, 20)], "estimated": [date(2026, 9, 30)]}}
        # confirmed date governs; the stale September estimate must not extend the ban
        self.assertFalse(entries_banned("X", date(2026, 9, 1), cal))
        self.assertTrue(entries_banned("X", date(2026, 8, 18), cal))
