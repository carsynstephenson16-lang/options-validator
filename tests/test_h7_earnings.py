"""Earnings ban: no new H7 entries within H7_EARNINGS_BAN_SESSIONS before a
report. Estimated dates are handled conservatively: the ban starts before the
EARLIEST estimate for the symbol and stays on until past the LATEST."""

import unittest
from datetime import date

from options_researcher.h7_earnings import (
    GATE_BANNED,
    GATE_CLEAR,
    GATE_UNKNOWN,
    assertions_view,
    earnings_gate,
    entries_banned,
    load_assertions,
    load_calendar,
    next_report,
)


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


def A(symbol, expected, status="confirmed", event="E1",
      known="2026-07-01T12:00:00+00:00", url="https://example.test/ir"):
    """Assertion-record fixture in the load_assertions output shape."""
    from datetime import datetime
    ts = datetime.fromisoformat(known)
    return {"symbol": symbol, "event_id": f"{symbol}-{event}",
            "fiscal_period": "FY26Q2",
            "expected_date": date.fromisoformat(expected),
            "session_timing": "amc", "status": status, "source_url": url,
            "known_as_of_utc": ts, "checked_at_utc": ts, "notes": ""}


def _now():
    from datetime import datetime
    return datetime.fromisoformat("2026-07-10T00:00:00+00:00")


class TestEarningsGateTyped(unittest.TestCase):
    """Owner decision 2026-07-10: typed CLEAR|BANNED|UNKNOWN gate. UNKNOWN
    always fails closed. Grace starts ONLY from a verified occurred report;
    expired estimates and stale scheduled dates never start it."""

    def test_no_assertions_is_unknown(self):
        state, _ = earnings_gate("ZZZZ", date(2026, 7, 8), [], known_as_of=_now())
        self.assertEqual(state, GATE_UNKNOWN)

    def test_future_confirmed_is_clear_outside_ban(self):
        rows = [A("ZZZZ", "2026-09-18")]
        state, _ = earnings_gate("ZZZZ", date(2026, 7, 8), rows, known_as_of=_now())
        self.assertEqual(state, GATE_CLEAR)

    def test_inside_ban_window_is_banned(self):
        rows = [A("ZZZZ", "2026-07-10")]
        state, _ = earnings_gate("ZZZZ", date(2026, 7, 8), rows, known_as_of=_now())
        self.assertEqual(state, GATE_BANNED)

    def test_occurred_within_grace_is_clear(self):
        rows = [A("ZZZZ", "2026-06-18", status="occurred")]
        state, _ = earnings_gate("ZZZZ", date(2026, 7, 8), rows, known_as_of=_now())
        self.assertEqual(state, GATE_CLEAR)

    def test_grace_day_45_clear_day_46_unknown(self):
        rows = [A("ZZZZ", "2026-05-01", status="occurred")]
        day45 = date(2026, 6, 15)   # (on - reported).days == 45
        day46 = date(2026, 6, 16)
        self.assertEqual(
            earnings_gate("ZZZZ", day45, rows, known_as_of=_now())[0], GATE_CLEAR)
        self.assertEqual(
            earnings_gate("ZZZZ", day46, rows, known_as_of=_now())[0], GATE_UNKNOWN)

    def test_expired_estimate_does_not_start_grace(self):
        # an estimate 20 days in the past, never marked occurred: UNKNOWN
        rows = [A("ZZZZ", "2026-06-18", status="estimated")]
        state, _ = earnings_gate("ZZZZ", date(2026, 7, 8), rows, known_as_of=_now())
        self.assertEqual(state, GATE_UNKNOWN)

    def test_passed_confirmed_without_occurrence_is_unknown(self):
        # a confirmed schedule that passed with no occurred record: UNKNOWN
        rows = [A("ZZZZ", "2026-07-01")]
        state, _ = earnings_gate("ZZZZ", date(2026, 7, 8), rows, known_as_of=_now())
        self.assertEqual(state, GATE_UNKNOWN)

    def test_point_in_time_filter_hides_later_knowledge(self):
        from datetime import datetime
        rows = [A("ZZZZ", "2026-09-18", known="2026-07-09T18:00:00+00:00")]
        early = datetime.fromisoformat("2026-07-07T00:00:00+00:00")
        state, _ = earnings_gate("ZZZZ", date(2026, 7, 7), rows, known_as_of=early)
        self.assertEqual(state, GATE_UNKNOWN)

    def test_supersession_preserves_both_and_view_picks_latest(self):
        old = A("ZZZZ", "2026-08-04", status="estimated",
                known="2026-06-01T00:00:00+00:00")
        new = A("ZZZZ", "2026-08-11", status="confirmed",
                known="2026-07-05T00:00:00+00:00")
        rows = [old, new]
        view_now = assertions_view(rows, _now())
        self.assertEqual([a["expected_date"] for a in view_now],
                         [date(2026, 8, 11)])
        from datetime import datetime
        mid = datetime.fromisoformat("2026-06-15T00:00:00+00:00")
        view_mid = assertions_view(rows, mid)
        self.assertEqual([a["expected_date"] for a in view_mid],
                         [date(2026, 8, 4)])   # the old assertion still exists

    def test_next_report_returns_earliest_known_upcoming(self):
        rows = [A("ZZZZ", "2026-08-11", event="Q2"),
                A("ZZZZ", "2026-11-10", event="Q3")]
        self.assertEqual(
            next_report("ZZZZ", date(2026, 7, 8), rows, known_as_of=_now()),
            date(2026, 8, 11))
        self.assertIsNone(
            next_report("ZZZZ", date(2026, 12, 1), rows, known_as_of=_now()))


class TestLoadAssertionsV2(unittest.TestCase):
    HEADER = ("record_id,symbol,event_id,fiscal_period,record_type,status,"
              "expected_date,occurred_date,session_timing,source_type,"
              "source_url,known_as_of_utc,checked_at_utc,supersedes,notes\n")
    ROW = ("R1,MSFT,MSFT-FY26Q4,FY26Q4,assertion,confirmed,2026-07-29,,amc,"
           "company_pr,https://example.test/ir,2026-07-10T15:00:00+00:00,"
           "2026-07-10T15:00:00+00:00,,\n")

    def _load(self, text):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "assertions_v2.csv"
            p.write_text(text)
            return load_assertions(p)

    def test_valid_file_loads(self):
        rows = self._load(self.HEADER + self.ROW)
        self.assertEqual(rows[0]["symbol"], "MSFT")
        self.assertEqual(rows[0]["expected_date"], date(2026, 7, 29))
        self.assertEqual(rows[0]["record_type"], "assertion")

    def test_bad_status_fails_closed(self):
        bad = self.ROW.replace("confirmed", "rumored")
        with self.assertRaises(ValueError):
            self._load(self.HEADER + bad)

    def test_naive_timestamp_fails_closed(self):
        bad = self.ROW.replace("2026-07-10T15:00:00+00:00,2026",
                               "2026-07-10T15:00:00,2026")
        with self.assertRaises(ValueError):
            self._load(self.HEADER + bad)

    def test_checked_at_must_be_non_decreasing(self):
        row2 = self.ROW.replace("R1", "R2").replace("MSFT", "AMZN").replace(
            "2026-07-10T15:00:00+00:00,2026-07-10T15:00:00+00:00",
            "2026-07-09T15:00:00+00:00,2026-07-09T15:00:00+00:00")
        with self.assertRaises(ValueError):
            self._load(self.HEADER + self.ROW + row2)

    def test_label_placeholder_source_rejected(self):
        # 7b-2R finding 4: label:* placeholders are not causal facts
        bad = self.ROW.replace("https://example.test/ir", "label:company_pr")
        with self.assertRaises(ValueError):
            self._load(self.HEADER + bad)

    def test_duplicate_record_id_rejected(self):
        with self.assertRaises(ValueError):
            self._load(self.HEADER + self.ROW + self.ROW)

    def test_supersedes_must_reference_an_earlier_record(self):
        bad = self.ROW.replace(",2026-07-10T15:00:00+00:00,,\n",
                               ",2026-07-10T15:00:00+00:00,R99,\n")
        with self.assertRaises(ValueError):
            self._load(self.HEADER + bad)

    def test_retraction_requires_supersedes(self):
        bad = self.ROW.replace("assertion", "retraction")
        with self.assertRaises(ValueError):
            self._load(self.HEADER + self.ROW.replace("R1", "R0") + bad)

    def test_occurred_requires_occurred_date(self):
        bad = self.ROW.replace("confirmed,2026-07-29,,",
                               "occurred,2026-07-29,,")
        with self.assertRaises(ValueError):
            self._load(self.HEADER + bad)

    def test_retraction_removes_record_from_later_views(self):
        from datetime import datetime
        retract = ("R2,MSFT,MSFT-FY26Q4,FY26Q4,retraction,confirmed,"
                   "2026-07-29,,amc,company_pr,https://example.test/oops,"
                   "2026-07-12T15:00:00+00:00,2026-07-12T15:00:00+00:00,"
                   "R1,\n")
        rows = self._load(self.HEADER + self.ROW + retract)
        before = assertions_view(
            rows, datetime.fromisoformat("2026-07-11T00:00:00+00:00"))
        after = assertions_view(
            rows, datetime.fromisoformat("2026-07-13T00:00:00+00:00"))
        self.assertEqual(len(before), 1)
        self.assertEqual(after, [])
        self.assertEqual(len(rows), 2)   # append-only: nothing deleted

    def test_committed_assertions_file_is_valid(self):
        rows = load_assertions()
        self.assertGreater(len(rows), 0)
        for a in rows:
            self.assertTrue(a["source_url"].startswith("https://"))


class TestConflictSemantics(unittest.TestCase):
    """Owner decision 2026-07-11 (7b-2R finding 4): multiple unresolved
    dates for one symbol/fiscal period -> UNKNOWN, never BANNED (do not
    silently trust either source, do not paper over the conflict by
    banning both)."""

    def test_conflicting_same_period_schedules_are_unknown(self):
        a = A("ZZZZ", "2026-08-04", event="Qx")
        b = A("ZZZZ", "2026-08-18", event="Qy")
        state, reason = earnings_gate("ZZZZ", date(2026, 8, 4), [a, b],
                                      known_as_of=_now())
        self.assertEqual(state, GATE_UNKNOWN)
        self.assertIn("conflicting", reason)

    def test_distinct_quarters_are_not_a_conflict(self):
        a = A("ZZZZ", "2026-08-11", event="Q2")
        b = A("ZZZZ", "2026-11-10", event="Q3")
        b["fiscal_period"] = "FY26Q3"
        state, _ = earnings_gate("ZZZZ", date(2026, 7, 8), [a, b],
                                 known_as_of=_now())
        self.assertEqual(state, GATE_CLEAR)

    def test_superseded_estimate_is_not_a_conflict(self):
        old = A("ZZZZ", "2026-08-04", status="estimated",
                known="2026-06-01T00:00:00+00:00")
        new = A("ZZZZ", "2026-08-11", status="confirmed",
                known="2026-07-05T00:00:00+00:00")
        state, _ = earnings_gate("ZZZZ", date(2026, 7, 8), [old, new],
                                 known_as_of=_now())
        self.assertEqual(state, GATE_CLEAR)   # same event_id: view keeps latest

    def test_supersession_key_includes_the_symbol(self):
        # 7b-2R finding 4: two symbols sharing an event_id string must not
        # supersede each other
        a = A("AAAA", "2026-08-11")
        b = A("BBBB", "2026-09-15", known="2026-07-05T00:00:00+00:00")
        a["event_id"] = b["event_id"] = "SHARED"
        view = assertions_view([a, b], _now())
        self.assertEqual(len(view), 2)


class TestSessionCloseCutoff(unittest.TestCase):
    """7b-2R finding 4 regressions: an 8-K accepted AFTER the close is
    invisible at that session's information cutoff and visible the next
    session. MSFT and AMZN filed their 2026-04-29 results at 20:03:31Z and
    20:18:55Z; the XNYS close that day was 20:00:00Z."""

    def _occurred(self, symbol, accepted_utc):
        from datetime import datetime
        ts = datetime.fromisoformat(accepted_utc)
        return {"symbol": symbol, "event_id": f"{symbol}-Q", "fiscal_period":
                "Q", "expected_date": None,
                "occurred_date": date(2026, 4, 29), "session_timing": "amc",
                "status": "occurred", "source_url": "https://sec.gov/x",
                "known_as_of_utc": ts, "checked_at_utc": ts, "notes": ""}

    def test_after_close_filing_invisible_same_session(self):
        from data.cache_runner import session_close_utc
        for sym, accepted in (("MSFT", "2026-04-29T20:03:31+00:00"),
                              ("AMZN", "2026-04-29T20:18:55+00:00")):
            rows = [self._occurred(sym, accepted)]
            state, _ = earnings_gate(
                sym, date(2026, 4, 29), rows,
                known_as_of=session_close_utc("2026-04-29"))
            self.assertEqual(state, GATE_UNKNOWN, sym)   # not yet knowable
            state, _ = earnings_gate(
                sym, date(2026, 4, 30), rows,
                known_as_of=session_close_utc("2026-04-30"))
            self.assertEqual(state, GATE_CLEAR, sym)     # visible next session

    def test_early_close_session_uses_real_close(self):
        from data.cache_runner import session_close_utc
        c = session_close_utc("2018-07-03")   # 1pm ET early close
        self.assertEqual((c.hour, c.minute), (17, 0))
        self.assertEqual(str(c.tzinfo), "UTC")
        with self.assertRaises(ValueError):
            session_close_utc("2018-07-04")   # holiday: not a session
