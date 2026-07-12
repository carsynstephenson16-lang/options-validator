"""Roadmap Stage 1: source health over the v3 GATING store. Health is
observability ONLY -- it adds no gate semantics: MISSING is the owner's
refresh work-list (no live future schedule), STALE means the post-report
grace window lapses within H7_SOURCE_HEALTH_WARN_SESSIONS sessions (the
gate is ABOUT to start failing closed), and unhealthy is gate-UNKNOWN or
STALE. BANNED stays healthy (an informed pre-report ban)."""

import io
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime

import config
from options_researcher.h7_earnings import GATE_CLEAR, GATE_UNKNOWN
from options_researcher.h7_source_health import (
    FLAG_MISSING,
    FLAG_STALE,
    _sessions_between,
    main,
    symbol_health,
    watch_universe,
)


def A(symbol, expected=None, *, status="confirmed", event="E1",
      record_id="G0001", occurred=None, known="2026-07-01T12:00:00+00:00",
      source_type="company_pr", clazz="actual_quarterly_earnings",
      fiscal="FY26Q2"):
    """Assertion-record fixture in the load_assertions output shape."""
    ts = datetime.fromisoformat(known)
    return {"record_id": record_id, "symbol": symbol,
            "event_id": f"{symbol}-{event}", "fiscal_period": fiscal,
            "event_class": clazz, "record_type": "assertion",
            "status": status,
            "expected_date": date.fromisoformat(expected) if expected else None,
            "occurred_date": date.fromisoformat(occurred) if occurred else None,
            "session_timing": "amc", "source_type": source_type,
            "source_url": "https://example.test/ir",
            "known_as_of_utc": ts, "checked_at_utc": ts,
            "supersedes": "", "promoted_from": "", "notes": ""}


def _now():
    return datetime.fromisoformat("2026-07-10T00:00:00+00:00")


ON = date(2026, 7, 8)
WARN = config.H7_SOURCE_HEALTH_WARN_SESSIONS


class TestSymbolHealth(unittest.TestCase):
    def _health(self, rows, symbol="ZZZZ", on=ON):
        return symbol_health(symbol, on, rows, known_as_of=_now(),
                             warn_sessions=WARN)

    def test_live_schedule_is_healthy_with_exact_days(self):
        h = self._health([A("ZZZZ", "2026-09-18")])
        self.assertTrue(h["healthy"])
        self.assertEqual(h["gate"], GATE_CLEAR)
        self.assertEqual(h["coverage"], "schedule")
        self.assertEqual(h["flags"], [])
        self.assertEqual(h["next_report"], date(2026, 9, 18))
        self.assertEqual(h["days_to_report"], 72)
        self.assertIsNone(h["grace_end"])

    def test_grace_with_runway_is_missing_but_healthy(self):
        # occurred 20 days ago, nothing scheduled: normal post-report state
        h = self._health([A("ZZZZ", occurred="2026-06-18", status="occurred")])
        self.assertTrue(h["healthy"])
        self.assertEqual(h["gate"], GATE_CLEAR)
        self.assertEqual(h["coverage"], "grace")
        self.assertEqual(h["flags"], [FLAG_MISSING])
        self.assertEqual(h["grace_end"], date(2026, 8, 2))
        self.assertGreater(h["grace_sessions_left"], WARN)
        self.assertIsNone(h["next_report"])
        self.assertIsNone(h["days_to_report"])

    def test_grace_lapsing_within_warn_sessions_is_stale_and_unhealthy(self):
        # occurred 2026-05-27 -> grace ends Sat 2026-07-11; from Wed 07-08
        # only 07-09 and 07-10 remain: 2 sessions <= WARN -> STALE
        h = self._health([A("ZZZZ", occurred="2026-05-27", status="occurred")])
        self.assertFalse(h["healthy"])
        self.assertEqual(h["gate"], GATE_CLEAR)   # gate not yet failing
        self.assertEqual(h["coverage"], "grace")
        self.assertEqual(h["flags"], [FLAG_MISSING, FLAG_STALE])
        self.assertEqual(h["grace_end"], date(2026, 7, 11))
        self.assertEqual(h["grace_sessions_left"], 2)

    def test_grace_expired_is_unknown_and_unhealthy(self):
        h = self._health([A("ZZZZ", occurred="2026-05-01", status="occurred")])
        self.assertFalse(h["healthy"])
        self.assertEqual(h["gate"], GATE_UNKNOWN)
        self.assertEqual(h["coverage"], "none")
        self.assertEqual(h["flags"], [FLAG_MISSING])

    def test_no_assertions_is_unknown_missing_unhealthy(self):
        h = self._health([])
        self.assertFalse(h["healthy"])
        self.assertEqual(h["gate"], GATE_UNKNOWN)
        self.assertEqual(h["coverage"], "none")
        self.assertEqual(h["flags"], [FLAG_MISSING])
        self.assertIsNone(h["newest_record_id"])
        self.assertIsNone(h["status"])
        self.assertIsNone(h["source_type"])

    def test_conflict_is_unhealthy_without_flags(self):
        # two live schedules for ONE fiscal period: gate UNKNOWN (conflict);
        # coverage is schedule and flags empty -- unhealthy comes from the gate
        rows = [A("ZZZZ", "2026-09-18", event="E1", record_id="G0001"),
                A("ZZZZ", "2026-09-25", event="E2", record_id="G0002")]
        h = self._health(rows)
        self.assertFalse(h["healthy"])
        self.assertEqual(h["gate"], GATE_UNKNOWN)
        self.assertEqual(h["coverage"], "schedule")
        self.assertEqual(h["flags"], [])

    def test_point_in_time_schedule_known_later_is_invisible(self):
        rows = [A("ZZZZ", "2026-09-18", known="2026-07-12T09:00:00+00:00")]
        h = self._health(rows)   # cutoff 2026-07-10: the row is NOT in view
        self.assertFalse(h["healthy"])
        self.assertEqual(h["gate"], GATE_UNKNOWN)
        self.assertEqual(h["flags"], [FLAG_MISSING])

    def test_newest_assertion_fields(self):
        rows = [A("ZZZZ", occurred="2026-05-01", status="occurred",
                  event="Q1", record_id="G0001", source_type="sec_filing",
                  known="2026-05-01T20:10:00+00:00"),
                A("ZZZZ", "2026-09-18", event="Q2", record_id="G0002",
                  known="2026-07-01T12:00:00+00:00")]
        h = self._health(rows)
        self.assertEqual(h["newest_record_id"], "G0002")
        self.assertEqual(h["status"], "confirmed")
        self.assertEqual(h["source_type"], "company_pr")
        self.assertEqual(h["event_class"], "actual_quarterly_earnings")
        self.assertEqual(h["newest_known_as_of"],
                         datetime.fromisoformat("2026-07-01T12:00:00+00:00"))


class TestUniverseAndSessions(unittest.TestCase):
    def test_watch_universe_is_the_watcher_universe(self):
        names = watch_universe()
        self.assertEqual(len(names), 12)
        self.assertNotIn("HYLN", names)
        for sym in ("CRWV", "NVDA", "VST", "AMZN"):
            self.assertIn(sym, names)

    def test_sessions_between_is_weekend_aware(self):
        # (Fri 07-10, Mon 07-13] -> exactly the Monday session
        self.assertEqual(_sessions_between(date(2026, 7, 10), date(2026, 7, 13)), 1)
        # (Wed 07-08, Sat 07-11] -> Thu + Fri
        self.assertEqual(_sessions_between(date(2026, 7, 8), date(2026, 7, 11)), 2)
        self.assertEqual(_sessions_between(date(2026, 7, 10), date(2026, 7, 9)), 0)


class TestMainCLI(unittest.TestCase):
    def test_as_of_replay_against_the_committed_store(self):
        # Cutoff = close of Fri 2026-07-10 (20:00 UTC). G0006/7/8 became
        # known 21:39 UTC that day -- AFTER the close -- so AMZN/VST/CEG
        # have no in-view schedule and their Q1 grace is expired: honest
        # point-in-time UNHEALTHY. MSFT's G0005 (known 07-08) is in view.
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--as-of", "2026-07-11"])
        out = buf.getvalue()
        self.assertEqual(rc, 1)
        self.assertRegex(out, r"MSFT:\s+ok")
        self.assertRegex(out, r"VST:\s+UNHEALTHY")
        self.assertIn("1/12 healthy", out)

    def test_future_as_of_is_refused(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--as-of", "2999-01-01"])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
