"""Display-only context-aware shortlist ranking.

The context term is deliberately the second lexicographic level and is never
summed with the frozen quality levels. Its UP-only rule for both buy and sell
lanes is LLM-proposed 2026-08-25: a confirmed DOWN trend never promotes a
premium-selling candidate. This module consumes an already-admitted pool and
cannot admit a card, alter policy, or carry verdict or trade authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from options_researcher.display_rank import BUY_LANES, SELL_LANES

_KNOWN_LANES = frozenset((*BUY_LANES, *SELL_LANES))


def _composite_by_symbol(cards: object) -> dict[str, Mapping[str, object]]:
    if not isinstance(cards, (list, tuple)):
        raise ValueError("composite board is not a sequence")
    by_symbol: dict[str, Mapping[str, object]] = {}
    for card in cards:
        if not isinstance(card, Mapping):
            raise ValueError("composite card is not a mapping")
        symbol = card.get("symbol")
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("composite card symbol is invalid")
        if symbol in by_symbol:
            raise ValueError(f"duplicate composite card for {symbol}")
        by_symbol[symbol] = card
    return by_symbol


def _aligned_angle_names(card: Mapping[str, object]) -> tuple[str, ...]:
    names = ["TREND"]
    vol = card.get("vol_premium")
    if isinstance(vol, Mapping) and not vol.get("data_blocked") and vol.get("state") == "CHEAP":
        names.append("VOL_PREMIUM")
    regime = card.get("regime")
    if (
        isinstance(regime, Mapping)
        and not regime.get("data_blocked")
        and regime.get("high_dispersion") is False
    ):
        names.append("REGIME")
    internals = card.get("internals")
    if (
        isinstance(internals, Mapping)
        and not internals.get("data_blocked")
        and internals.get("state") == "CONFIRM"
    ):
        names.append("INTERNALS")
    return tuple(names)


def _context_assessment(
    composite: Mapping[str, object] | None,
    lane: str,
) -> tuple[int, str, tuple[str, ...]]:
    if lane not in _KNOWN_LANES:
        raise ValueError(f"unknown context-lane kind: {lane}")
    if composite is None or composite.get("data_blocked") is True:
        return 0, "BLOCKED", ()
    trend = composite.get("trend")
    if not isinstance(trend, Mapping):
        return 0, "BLOCKED", ()
    trend_state = trend.get("state")
    if trend.get("data_blocked") or trend_state == "DATA_BLOCKED":
        return 0, "BLOCKED", ()
    if composite.get("grade") == "C":
        return 0, "VETOED", ()
    if trend_state != "UP":
        return 0, "DIRECTION_MISMATCH", ()
    aligned_count = composite.get("aligned_count")
    if isinstance(aligned_count, bool) or not isinstance(aligned_count, int) or aligned_count < 0:
        raise ValueError("composite aligned_count is invalid")
    aligned_angles = _aligned_angle_names(composite)
    if len(aligned_angles) != aligned_count:
        raise ValueError("composite aligned_count disagrees with angle states")
    return aligned_count, ", ".join(aligned_angles), aligned_angles


def rank_context_lane(
    admissible_pool: Sequence[tuple[tuple, dict]],
    composite_board: object,
    *,
    board_as_of: str,
    n: int,
) -> list[dict]:
    """Rank the full admitted pool, then retain at most one pick per symbol."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError("context shortlist width is invalid")
    composites = _composite_by_symbol(composite_board)
    scored: list[tuple[tuple, dict]] = []
    for frozen_key, pick in admissible_pool:
        if not isinstance(frozen_key, tuple) or len(frozen_key) != 7:
            raise ValueError("frozen admissible key is invalid")
        symbol = pick.get("symbol")
        lane = pick.get("lane")
        if not isinstance(symbol, str) or not isinstance(lane, str):
            raise ValueError("admissible pick identity is invalid")
        card = pick.get("card")
        snapshot = card.get("top3_snapshot") if isinstance(card, Mapping) else None
        candidate_id = snapshot.get("candidate_id") if isinstance(snapshot, Mapping) else None
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ValueError("admissible candidate_id is invalid")
        composite = composites.get(symbol)
        context_term, reason, aligned_angles = _context_assessment(composite, lane)
        score = (frozen_key[0], -context_term, *frozen_key[1:])
        row = {
            "symbol": symbol,
            "lane": lane,
            "candidate_id": candidate_id,
            "score": score,
            "context_max_asof": (
                composite.get("max_asof") if isinstance(composite, Mapping) else None
            ),
            "board_as_of": board_as_of,
            "context_term": context_term,
            "context_reason": reason,
            "aligned_angles": aligned_angles,
            "pick": pick,
        }
        scored.append((score, row))

    scored.sort(key=lambda item: item[0])
    selected: list[dict] = []
    seen: set[str] = set()
    for _score, row in scored:
        symbol = row["symbol"]
        if symbol in seen:
            continue
        seen.add(symbol)
        selected.append(row)
        if len(selected) == n:
            break
    return selected
