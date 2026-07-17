"""H9 event timing — strict-inequality causality per spec §2 / owner rule 1."""
import csv
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

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


def _class_row(record_id, symbol, occurred, event_class,
               evidence_url="https://www.sec.gov/Archives/edgar/data/x",
               evidence_note="note", checked_at_utc="2026-07-17T00:00:00+00:00"):
    return {
        "record_id": record_id,
        "symbol": symbol,
        "occurred_date": occurred,
        "event_class": event_class,
        "evidence_url": evidence_url,
        "evidence_note": evidence_note,
        "checked_at_utc": checked_at_utc,
    }


def _write_class_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = ["record_id", "symbol", "occurred_date", "event_class",
                  "evidence_url", "evidence_note", "checked_at_utc"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


class LoadEventClassesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "h9_event_class_v1.csv"

    def test_round_trip_all_three_classes(self):
        _write_class_csv(self.path, [
            _class_row("R1", "MSFT", "2026-04-29", "quarterly_results"),
            _class_row("R2", "SMCI", "2019-06-03", "business_update"),
            _class_row("R3", "AMZN", "2020-01-01", "other_item_202"),
        ])
        out = ev.load_event_classes(self.path)
        self.assertEqual(out[("MSFT", "2026-04-29")], "quarterly_results")
        self.assertEqual(out[("SMCI", "2019-06-03")], "business_update")
        self.assertEqual(out[("AMZN", "2020-01-01")], "other_item_202")

    def test_rejects_unknown_class(self):
        _write_class_csv(self.path, [
            _class_row("R1", "MSFT", "2026-04-29", "not_a_real_class"),
        ])
        with self.assertRaises(ValueError):
            ev.load_event_classes(self.path)

    def test_rejects_non_sec_evidence_url(self):
        _write_class_csv(self.path, [
            _class_row("R1", "MSFT", "2026-04-29", "quarterly_results",
                       evidence_url="https://example.com/not-sec"),
        ])
        with self.assertRaises(ValueError):
            ev.load_event_classes(self.path)


class DeriveEventsWithClassesTests(unittest.TestCase):
    def test_quarterly_kept_with_timing_resolved(self):
        rows = [raw("MSFT", "2026-04-29", "2026-04-29T20:03:31+00:00")]
        classes = {("MSFT", "2026-04-29"): "quarterly_results"}
        events = ev.derive_events(rows, symbols=("MSFT",), event_classes=classes)
        self.assertEqual(len(events), 1)
        self.assertIsNone(events[0].exclusion)
        self.assertIsNotNone(events[0].t_entry)

    def test_business_update_excluded_with_no_timing(self):
        rows = [raw("SMCI", "2019-06-03", "2019-06-03T20:05:00+00:00")]
        classes = {("SMCI", "2019-06-03"): "business_update"}
        events = ev.derive_events(rows, symbols=("SMCI",), event_classes=classes)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].exclusion, "non_earnings_event")
        self.assertIsNone(events[0].t_entry)
        self.assertIsNone(events[0].t_dec)
        self.assertIsNone(events[0].t_pre)

    def test_missing_classification_excluded_as_unclassified(self):
        rows = [raw("MSFT", "2026-04-29", "2026-04-29T20:03:31+00:00")]
        events = ev.derive_events(rows, symbols=("MSFT",), event_classes={})
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].exclusion, "unclassified_event")
        self.assertIsNone(events[0].t_entry)

    def test_now_2019_10_21_business_update_and_10_23_quarterly(self):
        rows = [
            raw("NOW", "2019-10-21", "2019-10-23T01:41:17+00:00", "A0016"),
            raw("NOW", "2019-10-23", "2019-10-23T20:14:07+00:00", "A0017"),
        ]
        classes = {
            ("NOW", "2019-10-21"): "business_update",
            ("NOW", "2019-10-23"): "quarterly_results",
        }
        events = ev.derive_events(rows, symbols=("NOW",), event_classes=classes)
        self.assertEqual(len(events), 2)
        timed = [e for e in events if e.exclusion is None]
        self.assertEqual(len(timed), 1)
        self.assertEqual(timed[0].occurred_date, date(2019, 10, 23))
        self.assertIsNotNone(timed[0].t_entry)
