"""Tests for the read-only equity-research market-intelligence bridge."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from options_researcher.market_context import get_recent_market_context


class MarketContextTests(unittest.TestCase):
    def _store(self, directory: Path) -> Path:
        path = directory / "market_updates.sqlite3"
        connection = sqlite3.connect(path)
        connection.executescript(
            """
            CREATE TABLE events (
                event_id TEXT PRIMARY KEY, title TEXT NOT NULL, summary TEXT,
                source_name TEXT NOT NULL, source_type TEXT NOT NULL,
                source_url TEXT NOT NULL, published_at TEXT NOT NULL,
                materiality_score INTEGER NOT NULL, form_type TEXT,
                topic_tags_json TEXT NOT NULL
            );
            CREATE TABLE event_tickers (event_id TEXT NOT NULL, ticker TEXT NOT NULL);
            """
        )
        rows = [
            (
                "past",
                "Past filing",
                None,
                "sec_edgar",
                "sec",
                "https://sec.example/past",
                "2026-07-19T15:00:00+00:00",
                90,
                "8-K",
                '["filing"]',
            ),
            (
                "future",
                "Future filing",
                None,
                "sec_edgar",
                "sec",
                "https://sec.example/future",
                "2026-07-21T15:00:00+00:00",
                90,
                "8-K",
                '["filing"]',
            ),
        ]
        connection.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
        connection.executemany(
            "INSERT INTO event_tickers VALUES (?, ?)", [("past", "VST"), ("future", "VST")]
        )
        connection.commit()
        connection.close()
        return path

    def test_excludes_future_publication_even_when_stored(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            db_path = self._store(Path(temp_directory))
            events = get_recent_market_context(
                {"VST"},
                as_of=datetime(2026, 7, 20, tzinfo=timezone.utc),
                lookback=timedelta(days=7),
                db_path=db_path,
            )
        self.assertEqual([event.event_id for event in events], ["past"])

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
