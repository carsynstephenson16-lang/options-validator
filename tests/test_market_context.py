"""Tests for the read-only equity-research market-intelligence bridge."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from options_researcher.market_context import get_recent_market_context

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "market_context_ec1_conformance.json"


class MarketContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
        self.as_of = datetime.fromisoformat(self.fixture["as_of"])
        self.lookback = timedelta(days=self.fixture["lookback_days"])

    def _store(
        self,
        directory: Path,
        *,
        events: list[dict[str, object]],
        ec1: bool,
    ) -> Path:
        path = directory / "market_updates.sqlite3"
        connection = sqlite3.connect(path)
        ec1_columns = (
            """
                , available_at TEXT, admission_state TEXT, admission_reason TEXT,
                stale_after TEXT, purpose_authority TEXT
            """
            if ec1
            else ""
        )
        connection.executescript(
            f"""
            CREATE TABLE events (
                event_id TEXT PRIMARY KEY, title TEXT NOT NULL, summary TEXT,
                source_name TEXT NOT NULL, source_type TEXT NOT NULL,
                source_url TEXT NOT NULL, published_at TEXT NOT NULL,
                materiality_score INTEGER NOT NULL, form_type TEXT,
                topic_tags_json TEXT NOT NULL
                {ec1_columns}
            );
            CREATE TABLE event_tickers (event_id TEXT NOT NULL, ticker TEXT NOT NULL);
            """
        )
        base_columns = (
            "event_id, title, summary, source_name, source_type, source_url, "
            "published_at, materiality_score, form_type, topic_tags_json"
        )
        ec1_names = (
            ", available_at, admission_state, admission_reason, stale_after, purpose_authority"
            if ec1
            else ""
        )
        placeholders = ",".join("?" for _ in range(15 if ec1 else 10))
        rows = []
        for event in events:
            event_id = str(event["event_id"])
            values: list[object] = [
                event_id,
                f"Title for {event_id}",
                None,
                "sec_edgar",
                "sec",
                f"https://sec.example/{event_id}",
                event["published_at"],
                90,
                "8-K",
                '["filing"]',
            ]
            if ec1:
                values.extend(
                    [
                        event.get("available_at"),
                        event.get("admission_state"),
                        event.get("admission_reason"),
                        event.get("stale_after"),
                        event.get("purpose_authority"),
                    ]
                )
            rows.append(tuple(values))
        connection.executemany(
            f"INSERT INTO events ({base_columns}{ec1_names}) VALUES ({placeholders})",
            rows,
        )
        connection.executemany(
            "INSERT INTO event_tickers VALUES (?, ?)",
            [(event["event_id"], self.fixture["ticker"]) for event in events],
        )
        connection.commit()
        connection.close()
        return path

    def _read(self, db_path: Path, *, include_stale: bool = False):
        return get_recent_market_context(
            {self.fixture["ticker"]},
            as_of=self.as_of,
            lookback=self.lookback,
            db_path=db_path,
            include_stale=include_stale,
        )

    def test_legacy_schema_uses_published_at_and_labels_fallback(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            db_path = self._store(
                Path(temp_directory),
                events=self.fixture["legacy_events"],
                ec1=False,
            )
            events = self._read(db_path)

        self.assertEqual(
            [event.event_id for event in events],
            self.fixture["expected"]["legacy_default_ids"],
        )
        self.assertEqual(events[0].gating_basis, "published_at-legacy")
        self.assertEqual(events[0].admission_basis, "grandfathered-legacy")
        self.assertFalse(events[0].is_stale)

    def test_available_at_controls_as_of_window_and_ordering(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            db_path = self._store(
                Path(temp_directory),
                events=self.fixture["ec1_events"],
                ec1=True,
            )
            events = self._read(db_path)

        self.assertEqual(
            [event.event_id for event in events],
            self.fixture["expected"]["ec1_default_ids"],
        )
        by_id = {event.event_id: event for event in events}
        self.assertEqual(by_id["gated-current"].gating_basis, "available_at")
        self.assertEqual(by_id["available-in-window"].gating_basis, "available_at")
        self.assertNotIn("not-yet-available", by_id)
        self.assertNotIn("available-before-window", by_id)

    def test_nonadmitted_and_nonddecision_rows_are_excluded(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            db_path = self._store(
                Path(temp_directory),
                events=self.fixture["ec1_events"],
                ec1=True,
            )
            by_id = {event.event_id: event for event in self._read(db_path)}

        self.assertNotIn("quarantined", by_id)
        self.assertNotIn("display-only", by_id)

    def test_null_admission_reason_is_labeled_grandfathered(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            db_path = self._store(
                Path(temp_directory),
                events=self.fixture["ec1_events"],
                ec1=True,
            )
            by_id = {event.event_id: event for event in self._read(db_path)}

        self.assertEqual(
            by_id["grandfathered"].admission_basis,
            "grandfathered-legacy",
        )
        self.assertEqual(by_id["grandfathered"].gating_basis, "published_at-legacy")
        self.assertEqual(by_id["gated-current"].admission_basis, "gated")

    def test_stale_rows_are_excluded_unless_explicitly_included_and_labeled(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            db_path = self._store(
                Path(temp_directory),
                events=self.fixture["ec1_events"],
                ec1=True,
            )
            default_events = self._read(db_path)
            override_events = self._read(db_path, include_stale=True)

        self.assertEqual(
            [event.event_id for event in override_events],
            self.fixture["expected"]["ec1_include_stale_ids"],
        )
        self.assertNotIn("stale", {event.event_id for event in default_events})
        by_id = {event.event_id: event for event in override_events}
        self.assertTrue(by_id["stale"].is_stale)
        self.assertFalse(by_id["gated-current"].is_stale)

    def test_partial_ec1_schema_is_refused_instead_of_falling_back(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            db_path = self._store(
                Path(temp_directory),
                events=self.fixture["legacy_events"],
                ec1=False,
            )
            connection = sqlite3.connect(db_path)
            connection.execute("ALTER TABLE events ADD COLUMN available_at TEXT")
            connection.commit()
            connection.close()

            with self.assertRaisesRegex(RuntimeError, "partial EC-1"):
                self._read(db_path)

    def test_invalid_store_timestamps_are_refused(self):
        invalid_published_at_values = (
            sqlite3.Binary(b"2026-07-19T10:00:00+00:00"),
            "not-a-timestamp",
            "2026-07-19T10:00:00",
        )
        for invalid_published_at in invalid_published_at_values:
            with self.subTest(published_at=invalid_published_at):
                event = dict(self.fixture["ec1_events"][0])
                event["published_at"] = invalid_published_at
                with tempfile.TemporaryDirectory() as temp_directory:
                    db_path = self._store(
                        Path(temp_directory),
                        events=[event],
                        ec1=True,
                    )
                    with self.assertRaisesRegex(RuntimeError, "invalid published_at"):
                        self._read(db_path)

    def test_requires_aware_as_of_timestamp(self):
        with self.assertRaises(ValueError):
            get_recent_market_context(
                {"VST"}, as_of=datetime(2026, 7, 20), lookback=timedelta(days=1)
            )

    def test_missing_store_is_an_empty_read_only_result(self):
        events = get_recent_market_context(
            {"VST"},
            as_of=datetime(2026, 7, 20, tzinfo=timezone.utc),
            lookback=timedelta(days=1),
            db_path=Path("/private/tmp/market_updates_absent.sqlite3"),
        )
        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
