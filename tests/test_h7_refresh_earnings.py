"""Roadmap Stage 1 refresher: owner-in-the-loop, append-only, one record
per invocation. Source hierarchy is MECHANICAL: aggregator evidence only as
disclosed `estimated` (notes required); an occurred report from a non-SEC
source needs notes saying why no SEC acceptance time is cited. Promotion
cites its raw evidence row (7b-2R.2) and the FULL load_assertions contract
runs on a temp copy BEFORE the real store is touched -- a bad row can never
poison an append-only store."""

import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from options_researcher.h7_earnings import (
    assertions_view,
    load_assertions,
    load_raw_assertions,
    next_report,
)
from tools.h7_refresh_earnings import append_raw, main, promote

NOW = "2026-07-11T00:00:00+00:00"

_RAW_HEADER = ("record_id,symbol,event_id,fiscal_period,record_type,status,"
               "expected_date,occurred_date,session_timing,source_type,"
               "source_url,known_as_of_utc,checked_at_utc,supersedes,notes")
_RAW_ROWS = [
    "A0001,MSFT,MSFT-FY26Q3,FY26Q3,assertion,occurred,,2026-04-29,amc,"
    "sec_filing,https://sec.test/a1,2026-04-29T20:03:31+00:00,"
    "2026-07-01T00:00:00+00:00,,verified release",
    "A0002,VST,VST-2026Q3,2026Q3,assertion,confirmed,2026-11-06,,bmo,"
    "company_pr,https://pr.test/a2,2026-07-01T12:00:00+00:00,"
    "2026-07-01T12:30:00+00:00,,schedule PR",
    "A0003,NVDA,NVDA-8K-2026-05-28,,assertion,occurred,,2026-05-28,amc,"
    "sec_filing,https://sec.test/a3,2026-05-28T20:05:00+00:00,"
    "2026-07-01T13:00:00+00:00,,collector-shaped row without fiscal identity",
]
_GATING_HEADER = ("record_id,symbol,event_id,fiscal_period,record_type,"
                  "event_class,status,expected_date,occurred_date,"
                  "session_timing,source_type,source_url,known_as_of_utc,"
                  "checked_at_utc,supersedes,promoted_from,notes")
_GATING_ROWS = [
    "G0001,MSFT,MSFT-FY26Q3,FY26Q3,assertion,actual_quarterly_earnings,"
    "occurred,,2026-04-29,amc,sec_filing,https://sec.test/a1,"
    "2026-04-29T20:03:31+00:00,2026-07-02T00:00:00+00:00,,A0001,promoted",
]


def _schedule_kwargs(**over):
    """A valid append-raw call; tests override single fields to probe rules."""
    kw = dict(symbol="CEG", event_id="CEG-2026Q3", fiscal_period="2026Q3",
              status="confirmed", expected_date="2026-11-05",
              occurred_date="", timing="bmo", source_type="company_ir",
              source_url="https://ir.test/ceg",
              known_as_of="2026-07-10T12:00:00+00:00", notes="", now_utc=NOW)
    kw.update(over)
    return kw


class RefreshBase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.raw = Path(tmp.name) / "assertions_v2.csv"
        self.gating = Path(tmp.name) / "gating_v3.csv"
        self.raw.write_text("\n".join([_RAW_HEADER, *_RAW_ROWS]) + "\n")
        self.gating.write_text("\n".join([_GATING_HEADER, *_GATING_ROWS]) + "\n")


class TestAppendRaw(RefreshBase):
    def test_happy_path_appends_one_validated_row(self):
        before = self.raw.read_bytes()
        row = append_raw(**_schedule_kwargs(), path=self.raw)
        self.assertEqual(row["record_id"], "A0004")
        after = self.raw.read_bytes()
        self.assertTrue(after.startswith(before))   # append-only: old bytes intact
        loaded = load_raw_assertions(self.raw)
        self.assertEqual(len(loaded), 4)
        self.assertEqual(loaded[-1]["record_id"], "A0004")
        self.assertEqual(loaded[-1]["expected_date"], date(2026, 11, 5))

    def test_aggregator_must_be_estimated(self):
        with self.assertRaises(SystemExit):
            append_raw(**_schedule_kwargs(source_type="aggregator",
                                          notes="nasdaq calendar"),
                       path=self.raw)

    def test_aggregator_estimated_requires_disclosure_notes(self):
        with self.assertRaises(SystemExit):
            append_raw(**_schedule_kwargs(source_type="aggregator",
                                          status="estimated"),
                       path=self.raw)
        # with the disclosure it is accepted
        row = append_raw(**_schedule_kwargs(
            source_type="aggregator", status="estimated",
            notes="aggregator estimate; NO official source found"),
            path=self.raw)
        self.assertEqual(row["status"], "estimated")

    def test_occurred_from_non_sec_source_requires_notes(self):
        with self.assertRaises(SystemExit):
            append_raw(**_schedule_kwargs(status="occurred",
                                          expected_date="",
                                          occurred_date="2026-11-05",
                                          source_type="company_pr"),
                       path=self.raw)

    def test_occurred_from_sec_needs_no_notes(self):
        row = append_raw(**_schedule_kwargs(status="occurred",
                                            expected_date="",
                                            occurred_date="2026-11-05",
                                            source_type="sec_filing",
                                            source_url="https://sec.test/c1"),
                         path=self.raw)
        self.assertEqual(row["status"], "occurred")

    def test_dry_run_writes_nothing(self):
        before = self.raw.read_bytes()
        row = append_raw(**_schedule_kwargs(), path=self.raw, dry_run=True)
        self.assertEqual(row["record_id"], "A0004")
        self.assertEqual(self.raw.read_bytes(), before)

    def test_naive_timestamp_is_refused_and_store_untouched(self):
        before = self.raw.read_bytes()
        with self.assertRaises(ValueError):
            append_raw(**_schedule_kwargs(known_as_of="2026-07-10T12:00:00"),
                       path=self.raw)
        self.assertEqual(self.raw.read_bytes(), before)

    def test_regressive_checked_at_is_refused_and_store_untouched(self):
        # append-only means checked_at never decreases; a clock stuck in the
        # past must refuse rather than corrupt the store
        before = self.raw.read_bytes()
        with self.assertRaises(ValueError):
            append_raw(**_schedule_kwargs(now_utc="2026-06-01T00:00:00+00:00"),
                       path=self.raw)
        self.assertEqual(self.raw.read_bytes(), before)

    def test_notes_with_commas_round_trip(self):
        append_raw(**_schedule_kwargs(
            notes="IR page; date read via search index, direct fetch timed out"),
            path=self.raw)
        loaded = load_raw_assertions(self.raw)
        self.assertIn("search index, direct fetch", loaded[-1]["notes"])


class TestPromote(RefreshBase):
    def test_happy_path_cites_and_copies_verbatim(self):
        row = promote(raw_id="A0002", event_class="actual_quarterly_earnings",
                      supersedes="", notes="q3 schedule", now_utc=NOW,
                      gating_path=self.gating, raw_path=self.raw)
        self.assertEqual(row["record_id"], "G0002")
        self.assertEqual(row["promoted_from"], "A0002")
        loaded = load_assertions(self.gating, self.raw)  # contract re-proves
        g = [r for r in loaded if r["record_id"] == "G0002"][0]
        self.assertEqual(g["symbol"], "VST")
        self.assertEqual(g["expected_date"], date(2026, 11, 6))
        self.assertEqual(g["source_url"], "https://pr.test/a2")
        self.assertEqual(g["known_as_of_utc"],
                         datetime.fromisoformat("2026-07-01T12:00:00+00:00"))

    def test_gating_class_requires_fiscal_identity_in_the_evidence(self):
        with self.assertRaisesRegex(SystemExit, "fiscal"):
            promote(raw_id="A0003", event_class="actual_quarterly_earnings",
                    supersedes="", notes="", now_utc=NOW,
                    gating_path=self.gating, raw_path=self.raw)

    def test_non_gating_class_accepts_collector_shaped_rows(self):
        row = promote(raw_id="A0003", event_class="business_update",
                      supersedes="", notes="classified as business update",
                      now_utc=NOW, gating_path=self.gating, raw_path=self.raw)
        self.assertEqual(row["event_class"], "business_update")
        load_assertions(self.gating, self.raw)

    def test_foreign_raw_id_is_refused(self):
        with self.assertRaises(SystemExit):
            promote(raw_id="A9999", event_class="business_update",
                    supersedes="", notes="", now_utc=NOW,
                    gating_path=self.gating, raw_path=self.raw)

    def test_double_promotion_is_refused(self):
        promote(raw_id="A0002", event_class="actual_quarterly_earnings",
                supersedes="", notes="", now_utc=NOW,
                gating_path=self.gating, raw_path=self.raw)
        with self.assertRaisesRegex(SystemExit, "already promoted"):
            promote(raw_id="A0002", event_class="actual_quarterly_earnings",
                    supersedes="", notes="", now_utc=NOW,
                    gating_path=self.gating, raw_path=self.raw)

    def test_supersedes_must_name_a_gating_record(self):
        with self.assertRaises(SystemExit):
            promote(raw_id="A0002", event_class="actual_quarterly_earnings",
                    supersedes="G9999", notes="", now_utc=NOW,
                    gating_path=self.gating, raw_path=self.raw)

    def test_correction_flow_supersedes_the_old_schedule(self):
        # promote the original schedule, then a corrected raw row supersedes it
        promote(raw_id="A0002", event_class="actual_quarterly_earnings",
                supersedes="", notes="", now_utc=NOW,
                gating_path=self.gating, raw_path=self.raw)
        append_raw(**_schedule_kwargs(
            symbol="VST", event_id="VST-2026Q3", fiscal_period="2026Q3",
            status="confirmed", expected_date="2026-11-07",
            source_type="company_pr", source_url="https://pr.test/a4",
            known_as_of="2026-07-10T18:00:00+00:00"), path=self.raw)
        row = promote(raw_id="A0004", event_class="actual_quarterly_earnings",
                      supersedes="G0002", notes="corrected date", now_utc=NOW,
                      gating_path=self.gating, raw_path=self.raw)
        self.assertEqual(row["record_id"], "G0003")
        loaded = load_assertions(self.gating, self.raw)
        late = datetime(2027, 1, 1, tzinfo=timezone.utc)
        ids = {a["record_id"] for a in assertions_view(loaded, late)}
        self.assertIn("G0003", ids)
        self.assertNotIn("G0002", ids)   # superseded record leaves the view
        self.assertEqual(
            next_report("VST", date(2026, 10, 1), loaded, known_as_of=late),
            date(2026, 11, 7))

    def test_dry_run_writes_nothing(self):
        before = self.gating.read_bytes()
        row = promote(raw_id="A0002", event_class="actual_quarterly_earnings",
                      supersedes="", notes="", now_utc=NOW,
                      gating_path=self.gating, raw_path=self.raw,
                      dry_run=True)
        self.assertEqual(row["record_id"], "G0002")
        self.assertEqual(self.gating.read_bytes(), before)


class TestMainCLI(RefreshBase):
    def test_append_raw_dry_run_via_cli(self):
        before = self.raw.read_bytes()
        rc = main(["append-raw", "--symbol", "CEG", "--event-id", "CEG-2026Q3",
                   "--fiscal-period", "2026Q3", "--status", "confirmed",
                   "--expected-date", "2026-11-05", "--timing", "bmo",
                   "--source-type", "company_ir",
                   "--source-url", "https://ir.test/ceg",
                   "--known-as-of", "2026-07-10T12:00:00+00:00",
                   "--raw-path", str(self.raw), "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertEqual(self.raw.read_bytes(), before)

    def test_promote_via_cli(self):
        rc = main(["promote", "--raw-id", "A0002",
                   "--event-class", "actual_quarterly_earnings",
                   "--notes", "q3 schedule",
                   "--raw-path", str(self.raw),
                   "--gating-path", str(self.gating)])
        self.assertEqual(rc, 0)
        loaded = load_assertions(self.gating, self.raw)
        self.assertEqual(loaded[-1]["promoted_from"], "A0002")


if __name__ == "__main__":
    unittest.main()
