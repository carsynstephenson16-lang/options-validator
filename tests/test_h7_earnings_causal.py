"""7b-2 C1: the eight owner-required causal proofs for the point-in-time
earnings gate (ledger H7_OWNER_DECISIONS_7B01). Each test is named for its
checklist item. Some overlap coverage in test_h7_earnings.py /
test_h7_backtest_engine.py; they are restated here verbatim-by-name so the
7b-2 gate review can tick the list without archaeology."""

import unittest
from datetime import date, datetime

from options_researcher.h7_earnings import (
    GATE_CLEAR,
    GATE_UNKNOWN,
    assertions_view,
    earnings_gate,
)


def A(symbol, expected, status="confirmed", event="E1",
      known="2026-01-01T00:00:00+00:00", url="https://example.test/ir"):
    ts = datetime.fromisoformat(known)
    return {"symbol": symbol, "event_id": f"{symbol}-{event}",
            "fiscal_period": "FYX",
            "event_class": "actual_quarterly_earnings",
            "expected_date": date.fromisoformat(expected),
            "session_timing": "amc", "status": status, "source_url": url,
            "known_as_of_utc": ts, "checked_at_utc": ts, "notes": ""}


def AT(iso):
    return datetime.fromisoformat(iso)


class TestCausalGateProofs(unittest.TestCase):
    def test_1_later_confirmation_cannot_affect_earlier_sessions(self):
        rows = [A("ZZZZ", "2026-08-11", known="2026-07-20T12:00:00+00:00")]
        # evaluating 2026-07-15 with the information set of 2026-07-15:
        # the 07-20 confirmation does not exist yet
        state, _ = earnings_gate("ZZZZ", date(2026, 7, 15), rows,
                                 known_as_of=AT("2026-07-15T23:59:59+00:00"))
        self.assertEqual(state, GATE_UNKNOWN)
        # ...and with the 07-21 information set it does
        state, _ = earnings_gate("ZZZZ", date(2026, 7, 21), rows,
                                 known_as_of=AT("2026-07-21T23:59:59+00:00"))
        self.assertEqual(state, GATE_CLEAR)

    def test_2_changed_estimate_preserves_both_historical_assertions(self):
        old = A("ZZZZ", "2026-08-04", status="estimated",
                known="2026-06-01T00:00:00+00:00")
        new = A("ZZZZ", "2026-08-11", known="2026-07-05T00:00:00+00:00")
        rows = [old, new]
        june_view = assertions_view(rows, AT("2026-06-15T00:00:00+00:00"))
        july_view = assertions_view(rows, AT("2026-07-06T00:00:00+00:00"))
        self.assertEqual([a["expected_date"] for a in june_view],
                         [date(2026, 8, 4)])
        self.assertEqual([a["expected_date"] for a in july_view],
                         [date(2026, 8, 11)])
        self.assertEqual(len(rows), 2)   # nothing was overwritten

    def test_3_expired_estimate_does_not_initiate_the_grace_period(self):
        rows = [A("ZZZZ", "2026-06-20", status="estimated")]
        state, _ = earnings_gate("ZZZZ", date(2026, 7, 8), rows,
                                 known_as_of=AT("2026-07-08T23:59:59+00:00"))
        self.assertEqual(state, GATE_UNKNOWN)

    def test_4_scheduled_report_passing_without_occurrence_becomes_unknown(self):
        rows = [A("ZZZZ", "2026-07-01")]   # confirmed, then... silence
        before, _ = earnings_gate("ZZZZ", date(2026, 6, 20), rows,
                                  known_as_of=AT("2026-06-20T23:59:59+00:00"))
        after, _ = earnings_gate("ZZZZ", date(2026, 7, 2), rows,
                                 known_as_of=AT("2026-07-02T23:59:59+00:00"))
        self.assertEqual(before, GATE_CLEAR)
        self.assertEqual(after, GATE_UNKNOWN)

    def test_5_day_45_covered_day_46_unknown_absent_future_assertion(self):
        rows = [A("ZZZZ", "2026-05-01", status="occurred")]
        day45, _ = earnings_gate("ZZZZ", date(2026, 6, 15), rows,
                                 known_as_of=AT("2026-06-15T23:59:59+00:00"))
        day46, _ = earnings_gate("ZZZZ", date(2026, 6, 16), rows,
                                 known_as_of=AT("2026-06-16T23:59:59+00:00"))
        self.assertEqual(day45, GATE_CLEAR)
        self.assertEqual(day46, GATE_UNKNOWN)

    def test_6_july_9_knowledge_cannot_affect_a_july_7_evaluation(self):
        rows = [A("ZZZZ", "2026-09-18", known="2026-07-09T18:00:00+00:00")]
        state, _ = earnings_gate("ZZZZ", date(2026, 7, 7), rows,
                                 known_as_of=AT("2026-07-07T23:59:59+00:00"))
        self.assertEqual(state, GATE_UNKNOWN)

    def test_7_malformed_or_conflicting_provenance_fails_closed(self):
        import tempfile
        from pathlib import Path

        from options_researcher.h7_earnings import load_assertions

        header = ("record_id,symbol,event_id,fiscal_period,record_type,"
                  "event_class,status,expected_date,occurred_date,"
                  "session_timing,source_type,source_url,known_as_of_utc,"
                  "checked_at_utc,supersedes,promoted_from,notes\n")
        cases = (
            # unknown status
            "R1,Z,Z-1,FY,assertion,actual_quarterly_earnings,leaked,2026-08-01,,amc,company_pr,"
            "https://x,2026-07-01T00:00:00+00:00,"
            "2026-07-01T00:00:00+00:00,,,\n",
            # timezone-naive timestamp
            "R1,Z,Z-1,FY,assertion,actual_quarterly_earnings,confirmed,2026-08-01,,amc,company_pr,"
            "https://x,2026-07-01T00:00:00,2026-07-01T00:00:00+00:00,,\n",
            # missing source URL
            "R1,Z,Z-1,FY,assertion,actual_quarterly_earnings,confirmed,2026-08-01,,amc,company_pr,,"
            "2026-07-01T00:00:00+00:00,2026-07-01T00:00:00+00:00,,\n",
            # label:* placeholder source (7b-2R: not a causal fact)
            "R1,Z,Z-1,FY,assertion,actual_quarterly_earnings,confirmed,2026-08-01,,amc,company_pr,"
            "label:pr,2026-07-01T00:00:00+00:00,"
            "2026-07-01T00:00:00+00:00,,,\n",
            # append-only violation (checked_at decreases)
            "R1,Z,Z-1,FY,assertion,actual_quarterly_earnings,confirmed,2026-08-01,,amc,company_pr,"
            "https://x,2026-07-02T00:00:00+00:00,"
            "2026-07-02T00:00:00+00:00,,\n"
            "R2,Z,Z-2,FY,assertion,actual_quarterly_earnings,confirmed,2026-11-01,,amc,company_pr,"
            "https://x,2026-07-01T00:00:00+00:00,"
            "2026-07-01T00:00:00+00:00,,,\n",
        )
        for body in cases:
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / "assertions_v2.csv"
                p.write_text(header + body)
                with self.assertRaises(ValueError):
                    load_assertions(p)
        # conflicting unresolved dates for the SAME symbol/fiscal period ->
        # UNKNOWN (owner decision 2026-07-11: the archive cannot say which
        # source is right, so the next report date is not known -- never
        # silently pick one, never merely ban both)
        rows = [A("ZZZZ", "2026-08-04", event="Qx"),
                A("ZZZZ", "2026-08-18", event="Qy")]
        on = date(2026, 8, 4)
        state, reason = earnings_gate(
            "ZZZZ", on, rows, known_as_of=AT("2026-08-04T23:59:59+00:00"))
        self.assertEqual(state, GATE_UNKNOWN)
        self.assertIn("conflicting", reason)

    def test_8_h7c_earnings_risk_reevaluated_every_session_while_open(self):
        # engine-level proof lives in
        # tests/test_h7_backtest_engine.py::EarningsUnknownWhileOpen (an open
        # H7c position exits the session after the gate turns UNKNOWN);
        # here: the gate itself is stateless in the session, so per-session
        # reevaluation is a property of calling it with each session's date.
        rows = [A("ZZZZ", "2026-04-25", status="occurred")]
        states = [
            earnings_gate("ZZZZ", d, rows,
                          known_as_of=AT(f"{d.isoformat()}T23:59:59+00:00"))[0]
            for d in (date(2026, 6, 8), date(2026, 6, 9), date(2026, 6, 10))
        ]
        self.assertEqual(states, [GATE_CLEAR, GATE_CLEAR, GATE_UNKNOWN])
