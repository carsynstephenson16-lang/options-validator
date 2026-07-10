"""Earnings ban: no new H7 entries within H7_EARNINGS_BAN_SESSIONS before a
report. Estimated dates are handled conservatively: the ban starts before the
EARLIEST estimate for the symbol and stays on until past the LATEST."""

import unittest
from datetime import date

from options_researcher.h7_earnings import earnings_covered, entries_banned, load_calendar


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


class TestReviewCounterexamples(unittest.TestCase):
    def test_holiday_cluster_does_not_shorten_the_ban(self):
        # R3: report Mon 2026-11-30; Thanksgiving 11-26 -- Fri 11-20 IS the
        # 5th session before and must be banned
        cal = {"X": {"confirmed": [date(2026, 11, 30)], "estimated": []}}
        self.assertTrue(entries_banned("X", date(2026, 11, 20), cal))

    def test_past_confirmation_does_not_disable_next_quarters_estimate(self):
        # R4: stale confirmed 07-22 + next quarter's estimate 10-20
        cal = {"X": {"confirmed": [date(2026, 7, 22)],
                     "estimated": [date(2026, 10, 20)]}}
        self.assertTrue(entries_banned("X", date(2026, 10, 15), cal))

    def test_two_quarters_do_not_collapse_into_one_long_ban(self):
        # R5: confirmed July and October reports; September must be free
        cal = {"X": {"confirmed": [date(2026, 7, 22), date(2026, 10, 21)],
                     "estimated": []}}
        self.assertFalse(entries_banned("X", date(2026, 9, 1), cal))


class TestEarningsCoverage(unittest.TestCase):
    """NO-GO remediation: a symbol whose next report the calendar does not
    know must FAIL CLOSED (no entry), not silently pass as never-banned."""

    def test_unknown_symbol_is_not_covered(self):
        self.assertFalse(earnings_covered("ZZZZ", date(2026, 7, 8), {}))

    def test_future_date_covers(self):
        cal = {"ZZZZ": {"confirmed": [date(2026, 9, 18)], "estimated": []}}
        self.assertTrue(earnings_covered("ZZZZ", date(2026, 7, 8), cal))

    def test_recent_past_report_covers(self):
        # reported 20 days ago -> next report ~a quarter away, ban horizon clear
        cal = {"ZZZZ": {"confirmed": [date(2026, 6, 18)], "estimated": []}}
        self.assertTrue(earnings_covered("ZZZZ", date(2026, 7, 8), cal))

    def test_stale_past_only_calendar_does_not_cover(self):
        # last known report 120 days ago: the NEXT report is due and unknown
        cal = {"ZZZZ": {"confirmed": [date(2026, 3, 10)], "estimated": []}}
        self.assertFalse(earnings_covered("ZZZZ", date(2026, 7, 8), cal))

    def test_estimated_rows_also_cover(self):
        cal = {"ZZZZ": {"confirmed": [], "estimated": [date(2026, 8, 11)]}}
        self.assertTrue(earnings_covered("ZZZZ", date(2026, 7, 8), cal))
