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

_EC1_CONSUMER_COLUMNS = frozenset(
    {
        "available_at",
        "admission_state",
        "admission_reason",
        "stale_after",
        "purpose_authority",
    }
)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    return value.astimezone(timezone.utc)


def _parse_store_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise RuntimeError(f"invalid {field} in market-updates store")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"invalid {field} in market-updates store") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RuntimeError(f"invalid {field} in market-updates store")
    return parsed.astimezone(timezone.utc)


def _has_complete_ec1_schema(connection: sqlite3.Connection) -> bool:
    columns = {
        str(row["name"]) for row in connection.execute("PRAGMA table_info(events)").fetchall()
    }
    present = columns & _EC1_CONSUMER_COLUMNS
    if present and present != _EC1_CONSUMER_COLUMNS:
        missing = ", ".join(sorted(_EC1_CONSUMER_COLUMNS - present))
        raise RuntimeError(f"partial EC-1 market-updates schema; missing {missing}")
    return present == _EC1_CONSUMER_COLUMNS


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
    gating_basis: str
    admission_basis: str
    is_stale: bool


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
    include_stale: bool = False,
) -> list[StoredMarketContext]:
    """Return stored events that were publishable by the supplied ``as_of``.

    Missing optional producer state is represented by an empty result, not a
    current-data fallback. This preserves backtest integrity and keeps the
    options validator separate from news ingestion and all order paths.

    Stale records are excluded unless ``include_stale`` is explicit; returned
    records always carry ``is_stale`` so an override cannot look fresh.
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
    lower_bound = bounded_as_of - lookback
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        has_ec1 = _has_complete_ec1_schema(connection)
        if has_ec1:
            gating_expression = "COALESCE(e.available_at, e.published_at)"
            ec1_projection = """
                , e.available_at, e.admission_state, e.admission_reason,
                e.stale_after, e.purpose_authority
            """
            eligibility_filters = """
                AND (e.admission_state IS NULL OR e.admission_state = 'ADMITTED')
                AND (
                    e.purpose_authority IS NULL
                    OR e.purpose_authority = 'decision'
                )
            """
        else:
            gating_expression = "e.published_at"
            ec1_projection = """
                , NULL AS available_at, NULL AS admission_state,
                NULL AS admission_reason, NULL AS stale_after,
                NULL AS purpose_authority
            """
            eligibility_filters = ""
        query = f"""
            SELECT DISTINCT
                e.event_id, e.title, e.summary, e.source_name, e.source_type,
                e.source_url, e.published_at, e.materiality_score, e.form_type,
                e.topic_tags_json
                {ec1_projection}
            FROM events AS e
            JOIN event_tickers AS et ON et.event_id = e.event_id
            WHERE et.ticker IN ({placeholders})
              AND e.materiality_score >= ?
              AND {gating_expression} >= ?
              AND {gating_expression} <= ?
              {eligibility_filters}
            ORDER BY
                {gating_expression} DESC,
                e.materiality_score DESC,
                e.event_id ASC
        """
        parameters: list[object] = [
            *requested,
            minimum_materiality,
            lower_bound.isoformat(),
            bounded_as_of.isoformat(),
        ]
        rows = connection.execute(query, parameters).fetchall()
        result_with_gating_time: list[tuple[datetime, StoredMarketContext]] = []
        for row in rows:
            published_at = _parse_store_timestamp(
                row["published_at"],
                "published_at",
            )
            available_at = row["available_at"]
            gating_at = _parse_store_timestamp(
                available_at if available_at is not None else row["published_at"],
                "available_at" if available_at is not None else "published_at",
            )
            if not lower_bound <= gating_at <= bounded_as_of:
                continue
            stale_after = row["stale_after"]
            is_stale = (
                stale_after is not None
                and _parse_store_timestamp(stale_after, "stale_after") < bounded_as_of
            )
            if is_stale and not include_stale:
                continue
            ticker_rows = connection.execute(
                "SELECT ticker FROM event_tickers WHERE event_id=? ORDER BY ticker",
                (row["event_id"],),
            ).fetchall()
            result_with_gating_time.append(
                (
                    gating_at,
                    StoredMarketContext(
                        event_id=row["event_id"],
                        title=row["title"],
                        summary=row["summary"],
                        source_name=row["source_name"],
                        source_type=row["source_type"],
                        source_url=row["source_url"],
                        published_at=published_at,
                        tickers=tuple(ticker_row["ticker"] for ticker_row in ticker_rows),
                        materiality_score=int(row["materiality_score"]),
                        form_type=row["form_type"],
                        topic_tags=tuple(json.loads(row["topic_tags_json"])),
                        gating_basis=(
                            "available_at" if available_at is not None else "published_at-legacy"
                        ),
                        admission_basis=(
                            "gated"
                            if row["admission_reason"] is not None
                            else "grandfathered-legacy"
                        ),
                        is_stale=is_stale,
                    ),
                )
            )
        result_with_gating_time.sort(
            key=lambda item: (
                -item[0].timestamp(),
                -item[1].materiality_score,
                item[1].event_id,
            )
        )
        result = [item[1] for item in result_with_gating_time]
    except sqlite3.DatabaseError as exc:
        raise RuntimeError(f"invalid market-updates store at {path}") from exc
    finally:
        if "connection" in locals():
            connection.close()
    return result
