# options_researcher/board_lanes.py
"""Pure lane-board builder for the attractiveness board's agreement table.

Spec: docs/superpowers/specs/2026-09-06-attractiveness-board-redesign-design.md §3–§5.
No file, network or clock access; every input is passed in. Nothing here is a
score or a signal: "Agree" is a count of favourable-lane membership, the
registered baseline decides row order and is never re-sorted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

import config


@dataclass(frozen=True)
class LaneMember:
    symbol: str
    label: str
    value: float | None
    rank: int | None
    counts: bool = True


@dataclass(frozen=True)
class LaneColumn:
    key: str
    title: str
    kind: str
    favourable: bool
    state: str
    as_of: str | None  # the lane's OWN evidence date (spec §5); never the board's substituted
    members: tuple[LaneMember, ...]
    note: str
    as_of_mismatch: bool = (
        False  # stamped by build_lane_board: READY and (unknown or != board session)
    )


@dataclass(frozen=True)
class BoardRow:
    symbol: str
    pinned: bool
    baseline_pick: Mapping[str, object] | None
    block_reason: str | None
    marks: Mapping[str, LaneMember]
    fav_count: int
    fav_ready: int


@dataclass(frozen=True)
class LaneBoard:
    columns: tuple[LaneColumn, ...]
    rows: tuple[BoardRow, ...]
    notes: tuple[str, ...]


_ORDER_NOTE = "top {cap} by {metric}, largest first (LLM-proposed 2026-09-06 display rule)"
_CONTEXT_LABELS = {
    "VETOED": "veto",
    "BLOCKED": "blocked",
    "DIRECTION_MISMATCH": "direction mismatch",
}

# lane key -> (title, experiment_lanes key, flag state, metric, cell prefix)
_EXPERIMENTS: dict[str, tuple[str, str, str, str | None, str]] = {
    "tbill": ("T-bill carry", "exp_tbill", "ABOVE_TBILL", "carry_spread", "✓"),
    "spread": ("Spread stability", "exp_spread", "ELEVATED", "ratio", "!"),
    "tail": ("Tail shape", "exp_tail", "UNSTABLE", "jump_count", "!"),
    "beta": ("Beta to QQQ", "exp_beta", "UNSTABLE", None, "!"),
}


def _sym(item: object) -> str | None:
    if not isinstance(item, Mapping):
        return None
    s = item.get("symbol")
    return s if isinstance(s, str) and s else None


def _num(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    return float(value) if isinstance(value, (int, float)) and value == value else None


def _int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _cards(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [c for c in value if isinstance(c, Mapping)]


def _lane_dates(items: Sequence[Mapping[str, object]], *keys: str) -> tuple[str | None, str | None]:
    """(latest, earliest) evidence date over items, reading the first present key of
    *keys per item — the repo's convention is max_asof, then asof
    (experiments_dashboard.py:74). Missing dates are ignored, never defaulted."""
    dates: list[str] = []
    for item in items:
        for key in keys:
            value = item.get(key)
            if isinstance(value, str) and value:
                dates.append(value)
                break
    if not dates:
        return None, None
    return max(dates), min(dates)


def _mixed_note(latest: str | None, earliest: str | None) -> str:
    if latest and earliest and earliest != latest:
        return f" · mixed as-of (earliest {earliest})"
    return ""


def lane_from_baseline(
    picks: Sequence[Mapping[str, object]] | None, *, cap: int, board_as_of: str | None
) -> LaneColumn:
    # The baseline's cards ARE the board's chain session: its as-of is the board's by construction.
    if picks is None:
        return LaneColumn(
            "baseline",
            "Rule-based top 5",
            "ranking",
            True,
            "UNAVAILABLE:no picks",
            board_as_of,
            (),
            "registered baseline",
        )
    members: list[LaneMember] = []
    for i, p in enumerate(picks[:cap], 1):
        sym = _sym(p)
        if sym is not None:
            members.append(LaneMember(sym, f"#{i}", None, i))
    return LaneColumn(
        "baseline",
        "Rule-based top 5",
        "ranking",
        True,
        "READY",
        board_as_of,
        tuple(members),
        "registered baseline; decides row order",
    )


def lane_from_context(selection: Mapping[str, object] | None, *, cap: int) -> LaneColumn:
    note = "display-only · baseline + market-context tiebreak; only positive alignment counts"
    if not isinstance(selection, Mapping):
        return LaneColumn(
            "context", "Context lane", "ranking", True, "UNAVAILABLE:no selection", None, (), note
        )
    state = str(selection.get("state") or "UNAVAILABLE")
    if state != "READY":
        err = selection.get("error")
        tag = f"FAILED:{err}" if state == "FAILED" and err else state
        return LaneColumn("context", "Context lane", "ranking", True, tag, None, (), note)
    rows = _cards(selection.get("rows"))
    latest, earliest = _lane_dates(rows, "context_max_asof")  # context_lane.py:116-118
    members: list[LaneMember] = []
    for i, row in enumerate(rows[:cap], 1):
        sym = _sym(row)
        if sym is None:
            continue
        reason = str(row.get("context_reason") or "")
        # The selector reports aligned angle names, not a literal ALIGNED state.
        term = _num(row.get("context_term"))
        if reason not in _CONTEXT_LABELS and term is not None and term > 0:
            members.append(LaneMember(sym, f"#{i}", _num(row.get("context_term")), i, True))
        else:
            members.append(
                LaneMember(
                    sym,
                    _CONTEXT_LABELS.get(reason, reason.lower() or "?"),
                    _num(row.get("context_term")),
                    i,
                    False,
                )
            )
    return LaneColumn(
        "context",
        "Context lane",
        "ranking",
        True,
        "READY",
        latest,
        tuple(members),
        note + _mixed_note(latest, earliest),
    )


def lane_from_composite(
    cards: Sequence[Mapping[str, object]] | None, *, cap: int, baseline_order: Sequence[str]
) -> LaneColumn:
    note = "display-only · angles agreeing; ties by baseline order, then symbol"
    if cards is None:
        return LaneColumn(
            "composite", "Composite", "ranking", True, "UNAVAILABLE:no cards", None, (), note
        )
    latest, earliest = _lane_dates(list(cards), "max_asof", "asof")  # composite_signals.py:619-622
    pos = {s: i for i, s in enumerate(baseline_order)}
    usable: list[tuple[int, str, Mapping[str, object]]] = []
    for c in cards:
        sym = _sym(c)
        aligned = _int(c.get("aligned_count"))
        if sym is not None and aligned is not None:
            usable.append((aligned, sym, c))
    usable.sort(key=lambda t: (-t[0], pos.get(t[1], len(pos)), t[1]))
    members = tuple(
        LaneMember(sym, f"{c.get('grade') or '?'} · {aligned}/4", float(aligned), i)
        for i, (aligned, sym, c) in enumerate(usable[:cap], 1)
    )
    return LaneColumn(
        "composite",
        "Composite",
        "ranking",
        True,
        "READY",
        latest,
        members,
        note + _mixed_note(latest, earliest),
    )


def lane_from_qm(
    picks: Sequence[Mapping[str, object]] | None,
    *,
    cap: int,
    qm_as_of: str | None,
    qm_earliest_as_of: str | None = None,
) -> LaneColumn:
    # QM picks are board cards re-ranked by the QM movement context; the page loads that
    # context for the board's own data_as_of (attractiveness_dashboard.py:5957) and the
    # context records its session as a TOP-LEVEL "as_of" (qm_dashboard.py:364; :110 when
    # blocked) — qm_as_of is that date as the CALLER read it, never assumed equal to the board.
    if picks is None:
        return LaneColumn(
            "qm",
            "QM movement",
            "ranking",
            True,
            "UNAVAILABLE:no QM context",
            qm_as_of,
            (),
            "gated study",
        )
    members: list[LaneMember] = []
    for i, p in enumerate(picks[:cap], 1):
        sym = _sym(p)
        if sym is not None:
            members.append(LaneMember(sym, f"#{i}", None, i))
    return LaneColumn(
        "qm",
        "QM movement",
        "ranking",
        True,
        "READY",
        qm_as_of,
        tuple(members),
        "gated study · mechanical picks" + _mixed_note(qm_as_of, qm_earliest_as_of),
    )


def lane_from_experiment(key: str, cards: object, *, cap: int) -> LaneColumn:
    title, _lane_key, flag_state, metric, prefix = _EXPERIMENTS[key]
    favourable = key in config.BOARD_FAVOURABLE_LANES
    if cards is None:
        return LaneColumn(
            key,
            title,
            "describing",
            favourable,
            "UNAVAILABLE:lane not computed",
            None,
            (),
            "experiment",
        )
    card_list = _cards(cards)
    errors = [c for c in card_list if c.get("state") == "ERROR"]
    if errors:
        reason = str(errors[0].get("reason") or "lane failed")
        return LaneColumn(
            key, title, "describing", favourable, f"UNAVAILABLE:{reason}", None, (), "experiment"
        )
    latest, earliest = _lane_dates(
        card_list, "max_asof", "asof"
    )  # exp_*.py cards, same keys as experiments_dashboard.py:74
    flagged: list[tuple[float | None, str, Mapping[str, object]]] = []
    for c in card_list:
        sym = _sym(c)
        if sym is not None and c.get("state") == flag_state:
            flagged.append((_num(c.get(metric)) if metric else None, sym, c))
    if metric:
        flagged.sort(key=lambda t: (-(t[0] if t[0] is not None else float("-inf")), t[1]))
    else:
        flagged.sort(key=lambda t: t[1])
    members: list[LaneMember] = []
    for v, sym, _c in flagged[:cap]:
        members.append(LaneMember(sym, f"{prefix} {v:.2f}" if v is not None else prefix, v, None))
    note = f"experiment · {'favourable' if favourable else 'caution'} · flags names in state {flag_state}"
    if metric and len(flagged) > cap:
        note += " · " + _ORDER_NOTE.format(cap=cap, metric=metric)
    note += _mixed_note(latest, earliest)
    return LaneColumn(key, title, "describing", favourable, "READY", latest, tuple(members), note)


def build_lane_board(
    *,
    baseline_picks: Sequence[Mapping[str, object]] | None,
    context_selection: Mapping[str, object] | None,
    composite_cards: Sequence[Mapping[str, object]] | None,
    qm_picks: Sequence[Mapping[str, object]] | None,
    experiment_lanes: Mapping[str, object] | None,
    pinned: Sequence[str],
    blocked: Sequence[Mapping[str, object]] | None,
    cap: int = config.PICK_TOP_N,
    board_as_of: str | None,
    qm_as_of: str | None = None,
    qm_earliest_as_of: str | None = None,
) -> LaneBoard:
    base_picks = list(baseline_picks or [])[:cap]
    base_order: list[str] = []
    pick_by_symbol: dict[str, Mapping[str, object]] = {}
    for p in base_picks:
        sym = _sym(p)
        if sym is not None:
            base_order.append(sym)
            pick_by_symbol[sym] = p

    exp: Mapping[str, object] = experiment_lanes if isinstance(experiment_lanes, Mapping) else {}
    gather_error = exp.get("__error__")
    columns_by_key: dict[str, LaneColumn] = {
        "baseline": lane_from_baseline(baseline_picks, cap=cap, board_as_of=board_as_of),
        "context": lane_from_context(context_selection, cap=cap),
        "composite": lane_from_composite(composite_cards, cap=cap, baseline_order=base_order),
        "qm": lane_from_qm(
            qm_picks, cap=cap, qm_as_of=qm_as_of, qm_earliest_as_of=qm_earliest_as_of
        ),
    }
    for key, (_t, lane_key, _s, _m, _p) in _EXPERIMENTS.items():
        cards: object
        if gather_error is not None:
            cards = [{"symbol": "", "state": "ERROR", "reason": str(gather_error)}]
        elif experiment_lanes is None:
            cards = None
        else:
            cards = exp.get(lane_key)
        columns_by_key[key] = lane_from_experiment(key, cards, cap=cap)

    def stamp(col: LaneColumn) -> LaneColumn:
        # spec §5: a READY lane whose own evidence date is unknown, or differs from the
        # board's chain session, is marked; a non-READY lane already prints its state.
        mismatch = col.state == "READY" and (
            col.as_of is None or (bool(board_as_of) and col.as_of != board_as_of)
        )
        return replace(col, as_of_mismatch=mismatch)

    ordered_keys = tuple(config.BOARD_FAVOURABLE_LANES) + tuple(config.BOARD_CAUTION_LANES)
    columns = tuple(stamp(columns_by_key[k]) for k in ordered_keys)
    fav_ready = sum(1 for c in columns if c.favourable and c.state == "READY")

    marks: dict[str, dict[str, LaneMember]] = {}
    for col in columns:
        for m in col.members:
            marks.setdefault(m.symbol, {})[col.key] = m

    block_by_symbol: dict[str, str] = {}
    for b in blocked or []:
        sym = _sym(b)
        if sym is not None:
            code = str(b.get("reason_code") or "DATA_BLOCKED")
            detail = str(b.get("detail") or "")
            block_by_symbol[sym] = f"{code} · {detail}" if detail else code

    def fav_count(sym: str) -> int:
        return sum(
            1
            for k, m in marks.get(sym, {}).items()
            if m.counts and columns_by_key[k].favourable and columns_by_key[k].state == "READY"
        )

    pinned_set = {str(s) for s in pinned}
    # Rows: every name any lane marked, every owner-pinned name, and every
    # DATA_BLOCKED name (fail-visible in the decision area, spec §3/§6.7).
    symbols = set(marks) | pinned_set | set(block_by_symbol)
    rest = sorted((s for s in symbols if s not in base_order), key=lambda s: (-fav_count(s), s))
    rows = tuple(
        BoardRow(
            symbol=s,
            pinned=s in pinned_set,
            baseline_pick=pick_by_symbol.get(s),
            block_reason=block_by_symbol.get(s),
            marks=dict(marks.get(s, {})),
            fav_count=fav_count(s),
            fav_ready=fav_ready,
        )
        for s in [*base_order, *rest]
    )
    notes = tuple(f"{c.title}: {c.state}" for c in columns if c.state != "READY") + tuple(
        f"{c.title}: evidence as of {c.as_of or 'unknown'} ≠ board session {board_as_of or 'unknown'}"
        for c in columns
        if c.as_of_mismatch
    )
    return LaneBoard(columns=columns, rows=rows, notes=notes)
