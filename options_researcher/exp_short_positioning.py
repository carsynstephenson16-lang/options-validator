"""EXP-SHORT display lane.

Disabled by default (``config.EXP_SHORT_ENABLED``). Reads local validated
artifacts only, never a provider. A lane failure becomes a visible red card
rather than an empty lane, and nothing here can reach ranking, verdict, entry,
sizing, book, or live-order code.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timezone

import config
from options_researcher.short_positioning_context import (
    ShortPositioningCard,
    build_short_positioning_context,
    render_short_positioning_card,
)

__all__ = [
    "build_exp_short_board",
    "load_exp_short_lane",
    "render_short_positioning_card",
]


def _asof_datetime(asof: str) -> datetime:
    """Interpret a session date as its end-of-day UTC information cutoff.

    A plain session string means "everything known by the end of that
    session", so a record that became available later stays invisible.
    """
    parsed = date.fromisoformat(asof)
    return datetime(parsed.year, parsed.month, parsed.day, 23, 59, 59, tzinfo=timezone.utc)


def build_exp_short_board(symbols: Sequence[str], *, asof: str) -> list[ShortPositioningCard]:
    """One fail-visible EXP-SHORT card per symbol."""
    try:
        cutoff = _asof_datetime(asof)
        cards = build_short_positioning_context(symbols, asof=cutoff)
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        return [
            ShortPositioningCard(
                symbol=symbol,
                source=config.SHORT_POSITIONING_PROVIDER_ORDER[0],
                issue_name=None,
                settlement_date=None,
                publication_date=None,
                max_asof=None,
                data_age_sessions=None,
                current_short_shares=None,
                change_shares=None,
                change_pct=None,
                days_to_cover=None,
                short_pct_float=None,
                primary_status="SCHEMA_ERROR",
                statuses=("SCHEMA_ERROR",),
                explanation=detail,
            )
            for symbol in symbols
        ]
    return list(cards)


def load_exp_short_lane(symbols: Sequence[str], *, asof: str) -> list[ShortPositioningCard] | None:
    """Return lane cards when the experiment is enabled, otherwise ``None``."""
    if not getattr(config, "EXP_SHORT_ENABLED", False):
        return None
    return build_exp_short_board(symbols, asof=asof)
