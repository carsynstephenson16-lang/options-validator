"""Read-only bridge to equity-research market intelligence.

This module deliberately reads the producer's SQLite evidence store directly.
It makes no network calls, cannot write the store, and requires a caller's
explicit historical ``as_of`` timestamp so strategy code cannot look ahead.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class StoredMarketContext:
    event_id: str
    title: str
    summary: str | None
    source_name: str
    source_type: str
    source_url: str
    published_at: datetime
    tickers: tuple[str, ...]
    materiality_score: int
    form_type: str | None
    topic_tags: tuple[str, ...]


def default_market_updates_db_path() -> Path:
    """Return the local sibling-repository store, overridable for tests/CI."""
    configured = os.environ.get("EQUITY_RESEARCH_MARKET_UPDATES_DB", "").strip()
    if configured:
        return Path(configured).expanduser()
    return (
        Path(__file__).resolve().parents[2]
        / "equity-research"
        / ".local"
        / "market_updates"
        / "market_updates.sqlite3"
    )


def get_recent_market_context(
    tickers: Collection[str],
    *,
    as_of: datetime,
    lookback: timedelta,
    minimum_materiality: int = 50,
    db_path: Path | str | None = None,
) -> list[StoredMarketContext]:
    """Return stored events that were publishable by the supplied ``as_of``.

    Missing optional producer state is represented by an empty result, not a
    current-data fallback. This preserves backtest integrity and keeps the
    options validator separate from news ingestion and all order paths.
    """
    bounded_as_of = _ensure_utc(as_of)
    if lookback.total_seconds() < 0:
        raise ValueError("lookback must not be negative")
    path = Path(db_path) if db_path is not None else default_market_updates_db_path()
    if not path.exists():
        return []
    requested = tuple(sorted({ticker.upper() for ticker in tickers}))
    if not requested:
        return []
    placeholders = ",".join("?" for _ in requested)
    query = f"""
        SELECT DISTINCT e.event_id, e.title, e.summary, e.source_name, e.source_type,
            e.source_url, e.published_at, e.materiality_score, e.form_type,
            e.topic_tags_json
        FROM events AS e
        JOIN event_tickers AS et ON et.event_id = e.event_id
        WHERE et.ticker IN ({placeholders})
          AND e.materiality_score >= ?
          AND e.published_at >= ?
          AND e.published_at <= ?
        ORDER BY e.published_at DESC, e.materiality_score DESC, e.event_id ASC
    """
    parameters: list[object] = [
        *requested,
        minimum_materiality,
        (bounded_as_of - lookback).isoformat(),
        bounded_as_of.isoformat(),
    ]
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, parameters).fetchall()
        result: list[StoredMarketContext] = []
        for row in rows:
            ticker_rows = connection.execute(
                "SELECT ticker FROM event_tickers WHERE event_id=? ORDER BY ticker",
                (row["event_id"],),
            ).fetchall()
            result.append(
                StoredMarketContext(
                    event_id=row["event_id"],
                    title=row["title"],
                    summary=row["summary"],
                    source_name=row["source_name"],
                    source_type=row["source_type"],
                    source_url=row["source_url"],
                    published_at=datetime.fromisoformat(row["published_at"]),
                    tickers=tuple(ticker_row["ticker"] for ticker_row in ticker_rows),
                    materiality_score=int(row["materiality_score"]),
                    form_type=row["form_type"],
                    topic_tags=tuple(json.loads(row["topic_tags_json"])),
                )
            )
    except sqlite3.DatabaseError as exc:
        raise RuntimeError(f"invalid market-updates store at {path}") from exc
    finally:
        if "connection" in locals():
            connection.close()
    return result
