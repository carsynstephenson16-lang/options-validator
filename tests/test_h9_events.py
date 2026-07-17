"""H9 event timing — strict-inequality causality per spec §2 / owner rule 1."""
import unittest
from datetime import date, datetime, timezone

from options_researcher import h9_events as ev


def raw(symbol, occurred, accepted_iso, record_id="A0001", status="occurred"):
    return {
        "record_id": record_id,
        "symbol": symbol,
        "event_id": f"{symbol}-{occurred}",
        "status": status,
        "occurred_date": date.fromisoformat(occurred),
        "expected_date": None,
        "known_as_of_utc": datetime.fromisoformat(accepted_iso),
        "supersedes": "",
    }


class TimingTests(unittest.TestCase):
    # 2026-07-01 (Wed), 07-02 (Thu) are XNYS sessions; 07-03 observed holiday;
    # 07-06 (Mon) next session. Regular close 20:00 UTC (EDT).

    def test_amc_filing_decides_next_session(self):
        e = ev.resolve_timing("MSFT", datetime(2026, 7, 1, 20, 3, 31, tzinfo=timezone.utc),
                              start_iso="2026-06-24", end_iso="2026-07-10")
        self.assertEqual(e, ("2026-07-01", "2026-07-02", "2026-07-06"))

    def test_bmo_filing_decides_same_session(self):
        e = ev.resolve_timing("MSFT", datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
                              start_iso="2026-06-24", end_iso="2026-07-10")
        self.assertEqual(e, ("2026-06-30", "2026-07-01", "2026-07-02"))

    def test_acceptance_exactly_at_close_is_after(self):
        from data.cache_runner import session_close_utc
        close = session_close_utc("2026-07-01")
        e = ev.resolve_timing("MSFT", close, start_iso="2026-06-24", end_iso="2026-07-10")
        self.assertEqual(e[0], "2026-06-30")  # t_pre must be STRICTLY before
        self.assertEqual(e[1], "2026-07-02")  # decision rolls to the next session

    def test_holiday_gap_entry(self):
        e = ev.resolve_timing("MSFT", datetime(2026, 7, 2, 21, 0, tzinfo=timezone.utc),
                              start_iso="2026-06-24", end_iso="2026-07-10")
        self.assertEqual(e, ("2026-07-02", "2026-07-06", "2026-07-07"))

    def test_window_edge_returns_none(self):
        e = ev.resolve_timing("MSFT", datetime(2026, 7, 9, 21, 0, tzinfo=timezone.utc),
                              start_iso="2026-06-24", end_iso="2026-07-10")
        self.assertIsNone(e[2])


class DedupeTests(unittest.TestCase):
    def test_earliest_acceptance_wins_and_amendment_ignored(self):
        rows = [
            raw("MSFT", "2026-04-29", "2026-04-29T20:03:31+00:00", "A0001"),
            raw("MSFT", "2026-04-29", "2026-05-02T10:00:00+00:00", "A0002"),
        ]
        events = ev.derive_events(rows, symbols=("MSFT",))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].accepted_utc.isoformat(), "2026-04-29T20:03:31+00:00")

    def test_non_occurred_rows_excluded(self):
        rows = [raw("MSFT", "2026-04-29", "2026-04-29T20:03:31+00:00", status="confirmed")]
        self.assertEqual(ev.derive_events(rows, symbols=("MSFT",)), [])

    def test_symbols_outside_universe_excluded(self):
        rows = [raw("TSLA", "2026-04-29", "2026-04-29T20:03:31+00:00")]
        self.assertEqual(ev.derive_events(rows, symbols=("MSFT",)), [])
