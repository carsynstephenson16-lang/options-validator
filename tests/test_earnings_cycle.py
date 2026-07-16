"""tests/test_earnings_cycle.py

Contract-cycle earnings badge (options_researcher/earnings_cycle.py).
The badge answers a RANGE question — does a known report land in
(chain_date, expiry]? — from the v3 point-in-time store. It is not
earnings_gate() (a single-date entry gate) and must never be falsely
GREEN: no evidence, passed-only schedules, or a next-known report too
far out to rule out a hidden quarter all stay UNKNOWN.
"""
import unittest
from datetime import date, datetime

import config
from options_researcher.earnings_cycle import (
    CYCLE_AMBER,
    CYCLE_GREEN,
    CYCLE_UNKNOWN,
    cycle_badge,
)


def A(symbol, expected, status="confirmed", event="E1", occurred=None,
      known="2026-07-01T12:00:00+00:00", clazz="actual_quarterly_earnings",
      record_id=None, supersedes=None, record_type="assertion"):
    """Assertion-record fixture in the load_assertions output shape."""
    ts = datetime.fromisoformat(known)
    return {"symbol": symbol, "event_id": f"{symbol}-{event}",
            "fiscal_period": "FY26Q2", "event_class": clazz,
            "expected_date": date.fromisoformat(expected),
            "occurred_date": (date.fromisoformat(occurred)
                              if occurred else None),
            "session_timing": "amc", "status": status,
            "source_url": "https://example.test/ir",
            "known_as_of_utc": ts, "checked_at_utc": ts, "notes": "",
            "record_id": record_id, "supersedes": supersedes,
            "record_type": record_type}


def _now():
    return datetime.fromisoformat("2026-07-16T00:00:00+00:00")


CHAIN = date(2026, 7, 15)


class CycleBadgeTests(unittest.TestCase):
    def test_no_evidence_is_unknown(self):
        state, _ = cycle_badge("ZZZZ", CHAIN, date(2026, 9, 18), [],
                               known_as_of=_now())
        self.assertEqual(state, CYCLE_UNKNOWN)

    def test_confirmed_report_inside_window_is_amber(self):
        rows = [A("AMZN", "2026-07-30")]
        state, reason = cycle_badge("AMZN", CHAIN, date(2026, 9, 18), rows,
                                    known_as_of=_now())
        self.assertEqual(state, CYCLE_AMBER)
        self.assertIn("2026-07-30", reason)

    def test_window_is_exclusive_of_chain_date_inclusive_of_expiry(self):
        on_chain_date = [A("X", "2026-07-15")]
        state, _ = cycle_badge("X", CHAIN, date(2026, 7, 25), on_chain_date,
                               known_as_of=_now())
        self.assertNotEqual(state, CYCLE_AMBER)  # report is not in the cycle
        on_expiry = [A("X", "2026-07-25")]
        state, _ = cycle_badge("X", CHAIN, date(2026, 7, 25), on_expiry,
                               known_as_of=_now())
        self.assertEqual(state, CYCLE_AMBER)

    def test_next_report_after_expiry_within_horizon_is_green(self):
        rows = [A("MSFT", "2026-07-29")]
        state, reason = cycle_badge("MSFT", CHAIN, date(2026, 7, 24), rows,
                                    known_as_of=_now())
        self.assertEqual(state, CYCLE_GREEN)
        self.assertIn("2026-07-29", reason)

    def test_next_report_beyond_coverage_horizon_is_unknown(self):
        # Next known report 139d out: an unrecorded earlier quarter could
        # still land inside the cycle. Never falsely GREEN.
        far = CHAIN.toordinal() + config.EARNINGS_COVERAGE_DAYS + 41
        far_iso = date.fromordinal(far).isoformat()
        rows = [A("X", far_iso)]
        state, _ = cycle_badge("X", CHAIN, date(2026, 7, 24), rows,
                               known_as_of=_now())
        self.assertEqual(state, CYCLE_UNKNOWN)

    def test_passed_schedule_only_is_unknown(self):
        rows = [A("X", "2026-04-29")]
        state, _ = cycle_badge("X", CHAIN, date(2026, 9, 18), rows,
                               known_as_of=_now())
        self.assertEqual(state, CYCLE_UNKNOWN)

    def test_point_in_time_future_knowledge_is_invisible(self):
        rows = [A("X", "2026-08-05", known="2026-07-20T12:00:00+00:00")]
        state, _ = cycle_badge("X", CHAIN, date(2026, 9, 18), rows,
                               known_as_of=_now())  # known 07-20 > as-of 07-16
        self.assertEqual(state, CYCLE_UNKNOWN)

    def test_estimated_report_inside_window_is_amber_and_labeled(self):
        rows = [A("IREN", "2026-08-27", status="estimated")]
        state, reason = cycle_badge("IREN", CHAIN, date(2026, 9, 18), rows,
                                    known_as_of=_now())
        self.assertEqual(state, CYCLE_AMBER)
        self.assertIn("estimated", reason)

    def test_non_gating_event_class_is_invisible(self):
        rows = [A("X", "2026-08-05", clazz="business_update")]
        state, _ = cycle_badge("X", CHAIN, date(2026, 9, 18), rows,
                               known_as_of=_now())
        self.assertEqual(state, CYCLE_UNKNOWN)

    def test_superseded_date_move_uses_latest_record(self):
        rows = [A("X", "2026-08-05", record_id="R1"),
                A("X", "2026-09-30", record_id="R2", supersedes="R1",
                  known="2026-07-10T12:00:00+00:00")]
        state, _ = cycle_badge("X", CHAIN, date(2026, 8, 20), rows,
                               known_as_of=_now())
        self.assertNotEqual(state, CYCLE_AMBER)  # 08-05 was superseded

    def test_occurred_report_inside_window_is_amber(self):
        rows = [A("X", "2026-07-20", status="occurred",
                  occurred="2026-07-20")]
        state, _ = cycle_badge("X", CHAIN, date(2026, 9, 18), rows,
                               known_as_of=_now())
        self.assertEqual(state, CYCLE_AMBER)


if __name__ == "__main__":
    unittest.main()
