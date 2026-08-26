"""Shared pure helpers for the frozen display-ranking recipe."""

from __future__ import annotations

from collections.abc import Mapping

SELL_LANES = ("put", "cc", "pmcc")
BUY_LANES = ("leaps", "long_call")


def display_quality_key(
    card: Mapping[str, object],
    kind: str,
    tech: Mapping[str, object] | None,
) -> tuple[float, int, int]:
    """Return the frozen lane-neutral quality tuple; better sorts first."""
    grades_value = card.get("grades")
    grades = grades_value if isinstance(grades_value, Mapping) else {}
    greens = sum(1 for value in grades.values() if value == "GREEN")
    fraction = greens / len(grades) if grades else 0.0
    leader = 1 if card.get("rank_leader") else 0
    technical_confluence = 0
    if tech:
        if kind in BUY_LANES and (tech.get("trend") == "up" or tech.get("breakout_20d")):
            technical_confluence = 1
        elif kind in SELL_LANES and tech.get("ma_posture") != "below_all":
            technical_confluence = 1
    return (-fraction, -leader, -technical_confluence)
