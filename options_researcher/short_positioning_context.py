"""Display cards for issuer-level short positioning.

DISPLAY-ONLY. This module reads local validated artifacts and turns them into
neutral cards. It imports no provider or acquisition module, makes no network
call, and has no ranking, verdict, entry, sizing, or execution authority.

Colour carries data health, never direction: red is reserved for integrity
failures, amber for health states, and everything else is neutral. There is no
green state, because there is no good or bad short-interest reading.
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import config
from data.short_positioning.identity import load_effective_dated_aliases
from data.short_positioning.models import ShortPositioningSnapshotV1
from data.short_positioning.snapshots import resolve_short_positioning_snapshot

LANE_HEADING = "EXP-SHORT"
LANE_TITLE = "Short positioning context"
LANE_TEXT = (
    "Issuer-level reported positioning. Display-only. No ranking, verdict, entry, "
    "sizing, or execution authority."
)
CARD_CAVEAT = "Positioning snapshot, not direction or timing."
DAYS_TO_COVER_NOTE = "Source-defined liquidity ratio, not a countdown or timing forecast."

# Integrity failures. The reader must not trust the artifact at all.
RED_STATUSES = frozenset(
    {
        "SCHEMA_ERROR",
        "HASH_MISMATCH",
        "FUTURE_DATA",
        "MISSING_PROVENANCE",
        "PARTIAL_CAPTURE",
        "LICENSE_BLOCKED",
    }
)
# Data-health states. The position may still be shown.
AMBER_STATUSES = frozenset({"STALE", "REVISED", "FLOAT_UNAVAILABLE", "NOT_YET_PUBLISHED"})

UNAVAILABLE = "unavailable"


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


@dataclass(frozen=True, slots=True)
class ShortPositioningCard:
    """One issuer's positioning snapshot, ready to render."""

    symbol: str
    source: str
    issue_name: str | None
    settlement_date: str | None
    publication_date: str | None
    max_asof: str | None
    data_age_sessions: int | None
    current_short_shares: int | None
    change_shares: int | None
    change_pct: Decimal | None
    days_to_cover: Decimal | None
    short_pct_float: Decimal | None
    primary_status: str
    statuses: tuple[str, ...]
    explanation: str

    @property
    def tone(self) -> str:
        """Data-health colour. Never a directional judgement."""
        if self.primary_status in RED_STATUSES:
            return "red"
        if self.primary_status in AMBER_STATUSES:
            return "amber"
        return "neutral"


def _error_card(symbol: str, detail: str) -> ShortPositioningCard:
    return ShortPositioningCard(
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


def _card_from_snapshot(snapshot: ShortPositioningSnapshotV1, *, source: str):
    record = snapshot.short_interest
    features = snapshot.features
    return ShortPositioningCard(
        symbol=snapshot.symbol,
        source=source,
        issue_name=None if record is None else record.issue_name,
        settlement_date=None if record is None else record.settlement_date.isoformat(),
        publication_date=None if record is None else record.publication_date.isoformat(),
        max_asof=None if snapshot.max_asof is None else snapshot.max_asof.isoformat(),
        data_age_sessions=None if features is None else features.data_age_sessions,
        current_short_shares=None if record is None else record.current_short_shares,
        change_shares=None if record is None else record.change_shares,
        change_pct=None if features is None else features.change_pct,
        days_to_cover=None if record is None else record.days_to_cover,
        short_pct_float=None if features is None else features.short_pct_float,
        primary_status=snapshot.primary_status,
        statuses=snapshot.statuses,
        explanation=snapshot.explanation,
    )


def build_short_positioning_context(
    symbols: Sequence[str],
    *,
    asof: datetime,
    root: Path | None = None,
    provider_order: tuple[str, ...] | None = None,
    max_age_releases: int | None = None,
) -> tuple[ShortPositioningCard, ...]:
    """Build one fail-visible card per symbol from local artifacts."""
    root = Path(root if root is not None else config.SHORT_POSITIONING_ROOT)
    provider_order = provider_order or tuple(config.SHORT_POSITIONING_PROVIDER_ORDER)
    if max_age_releases is None:
        max_age_releases = int(config.SHORT_POSITIONING_MAX_AGE_RELEASES)

    try:
        aliases = load_effective_dated_aliases(root)
    except Exception as exc:
        return tuple(_error_card(symbol, f"{type(exc).__name__}: {exc}") for symbol in symbols)

    cards = []
    for symbol in symbols:
        try:
            snapshot = resolve_short_positioning_snapshot(
                root,
                symbol=symbol,
                asof=asof,
                provider_order=provider_order,
                max_age_releases=max_age_releases,
                aliases=aliases,
            )
            cards.append(_card_from_snapshot(snapshot, source=provider_order[0]))
        except Exception as exc:
            cards.append(_error_card(symbol, f"{type(exc).__name__}: {exc}"))
    return tuple(cards)


def _shares(value: int | None) -> str:
    return UNAVAILABLE if value is None else f"{value:,}"


def _ratio(value: Decimal | None, suffix: str = "") -> str:
    return UNAVAILABLE if value is None else f"{value.normalize():f}{suffix}"


def _sessions(value: int | None) -> str:
    if value is None:
        return UNAVAILABLE
    return f"{value} XNYS session" + ("" if value == 1 else "s")


def render_short_positioning_card(card: ShortPositioningCard) -> str:
    """Render one card. Every provider-controlled string is escaped."""
    rows = (
        ("Source", card.source),
        ("Issue", card.issue_name or UNAVAILABLE),
        ("Settlement date", card.settlement_date or UNAVAILABLE),
        ("Publication date", card.publication_date or UNAVAILABLE),
        ("Maximum as-of", card.max_asof or UNAVAILABLE),
        ("Data age", _sessions(card.data_age_sessions)),
        ("Current short shares", _shares(card.current_short_shares)),
        ("Change in shares", _shares(card.change_shares)),
        ("Change percent", _ratio(card.change_pct, " pp")),
        ("Days to cover", _ratio(card.days_to_cover)),
        ("Short percent of float", _ratio(card.short_pct_float, " pp")),
    )
    detail = "".join(
        f'<div class="label">{_esc(name)}: {_esc(value)}</div>' for name, value in rows
    )
    secondary = ", ".join(card.statuses)
    return (
        '<div class="panel composite-card">'
        f'<div class="slot-label"><span>{_esc(card.symbol)}</span>'
        f'<span class="status-badge {_esc(card.tone)}">{_esc(card.primary_status)}</span>'
        "</div>"
        f"{detail}"
        f'<div class="label">Statuses: {_esc(secondary)}</div>'
        f"<div>{_esc(card.explanation)}</div>"
        f'<div class="label">{_esc(CARD_CAVEAT)}</div>'
        f'<div class="label">Days to cover: {_esc(DAYS_TO_COVER_NOTE)}</div>'
        "</div>"
    )
