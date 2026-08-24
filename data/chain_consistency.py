"""Pure cross-session options-chain consistency observations.

These display-only observations compare caller-supplied snapshots.  This
module intentionally has no file, calendar, or network I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Mapping, Sequence

import pandas as pd

import config
from data.chain_policy import _normalize_contract_keys, passes_liquidity

FLAG_PRECEDENCE = (
    "GAP_SESSION",
    "EXPIRY_VANISHED",
    "STRIKE_VANISHED",
    "DELTA_JUMP",
    "SPREAD_BLOWOUT",
)
_KEY_COLUMNS = ("expiration", "strike", "right")
_LIQUIDITY_COLUMNS = ("open_interest", "bid", "ask")


@dataclass(frozen=True)
class ConsistencyReport:
    """Bounded, display-only observations for one submitted session pair."""

    prev_session: str
    cur_session: str
    max_as_of_session: str
    status: str
    flag_counts: Mapping[str, int]
    evaluated_counts: Mapping[str, int]
    flag_examples: Mapping[str, tuple[Mapping[str, object], ...]]
    not_evaluable_flags: tuple[str, ...]
    condition_not_met_flags: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        """JSON-ready deterministic representation for a read-only receipt."""
        return {
            "prev_session": self.prev_session,
            "cur_session": self.cur_session,
            "max_as_of_session": self.max_as_of_session,
            "status": self.status,
            "flag_counts": dict(self.flag_counts),
            "evaluated_counts": dict(self.evaluated_counts),
            "flag_examples": {
                flag: [dict(example) for example in examples]
                for flag, examples in self.flag_examples.items()
            },
            "not_evaluable_flags": list(self.not_evaluable_flags),
            "condition_not_met_flags": list(self.condition_not_met_flags),
        }


def _session_iso(value: object, *, context: str) -> str:
    try:
        return pd.Timestamp(value).date().isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context}: invalid session {value!r}") from exc


def _prepare_chain(frame: pd.DataFrame, *, context: str) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame):
        raise TypeError(f"{context}: expected pandas DataFrame")
    out = _normalize_contract_keys(frame, context)
    parsed_expiration = pd.to_datetime(out["expiration"], errors="coerce")
    if parsed_expiration.isna().any():
        raise ValueError(f"{context}: invalid expiration value")
    out["expiration"] = parsed_expiration.dt.date.astype(str)
    if out["strike"].isna().any():
        raise ValueError(f"{context}: invalid strike value")
    return out.reset_index(drop=True)


def _missing_columns(*frames: pd.DataFrame, required: Sequence[str]) -> bool:
    return any(any(column not in frame.columns for column in required) for frame in frames)


def _missing_contract_keys(frame: pd.DataFrame) -> bool:
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("chain input: expected pandas DataFrame")
    available = {str(column).strip().lower() for column in frame.columns}
    return any(column not in available for column in _KEY_COLUMNS)


def _liquid_mask(frame: pd.DataFrame) -> pd.Series:
    """The policy predicate applied row-wise to preserve its exact semantics."""
    open_interest = pd.to_numeric(frame["open_interest"], errors="coerce")
    bid = pd.to_numeric(frame["bid"], errors="coerce")
    ask = pd.to_numeric(frame["ask"], errors="coerce")
    values = (
        passes_liquidity(float(oi), float(b), float(a))
        for oi, b, a in zip(open_interest, bid, ask, strict=True)
    )
    return pd.Series(list(values), index=frame.index, dtype=bool)


def _contract_key(row: pd.Series) -> tuple[str, float, str]:
    return (str(row["expiration"]), float(row["strike"]), str(row["right"]))


def _contract_example(row: pd.Series, **details: object) -> dict[str, object]:
    return {
        "expiration": str(row["expiration"]),
        "strike": float(row["strike"]),
        "right": str(row["right"]),
        **details,
    }


def _bounded(examples: list[dict[str, object]]) -> tuple[Mapping[str, object], ...]:
    return tuple(
        MappingProxyType(example) for example in examples[: config.CONSISTENCY_MAX_EXAMPLES]
    )


def _numeric(row: pd.Series, column: str) -> float | None:
    value = pd.to_numeric(pd.Series([row[column]]), errors="coerce").iloc[0]
    if pd.isna(value):
        return None
    result = float(value)
    return result if isfinite(result) else None


def _small_move(prev_close: float, cur_close: float) -> bool | None:
    try:
        previous = float(prev_close)
        current = float(cur_close)
    except (TypeError, ValueError):
        return None
    if not (isfinite(previous) and isfinite(current)) or previous == 0:
        return None
    return abs((current / previous) - 1.0) < config.CONSISTENCY_UNDERLYING_SMALL_MOVE


def _status(flag_counts: Mapping[str, int], not_evaluable: set[str]) -> str:
    for flag in FLAG_PRECEDENCE:
        if flag_counts[flag] > 0:
            return flag
    return "NOT_EVALUABLE" if not_evaluable else "OK"


def _report(
    *,
    prev_session: str,
    cur_session: str,
    counts: dict[str, int],
    evaluated: dict[str, int],
    examples: dict[str, list[dict[str, object]]],
    not_evaluable: set[str],
    condition_not_met: set[str],
) -> ConsistencyReport:
    frozen_examples = MappingProxyType({flag: _bounded(examples[flag]) for flag in FLAG_PRECEDENCE})
    frozen_counts = MappingProxyType(dict(counts))
    frozen_evaluated = MappingProxyType(dict(evaluated))
    ordered_not_evaluable = tuple(flag for flag in FLAG_PRECEDENCE if flag in not_evaluable)
    ordered_condition_not_met = tuple(flag for flag in FLAG_PRECEDENCE if flag in condition_not_met)
    return ConsistencyReport(
        prev_session=prev_session,
        cur_session=cur_session,
        max_as_of_session=max(prev_session, cur_session),
        status=_status(frozen_counts, not_evaluable),
        flag_counts=frozen_counts,
        evaluated_counts=frozen_evaluated,
        flag_examples=frozen_examples,
        not_evaluable_flags=ordered_not_evaluable,
        condition_not_met_flags=ordered_condition_not_met,
    )


def audit_pair(
    prev_chain: pd.DataFrame,
    cur_chain: pd.DataFrame,
    prev_close: float,
    cur_close: float,
    *,
    prev_session: str,
    cur_session: str,
    calendar_sessions: Sequence[object],
) -> ConsistencyReport:
    """Compare two caller-supplied snapshots without reading or writing data.

    Missing columns make the affected observation visibly not evaluable.  They
    never act as a refusal and no result from this function has gate, rank, or
    trade authority.
    """
    prev_iso = _session_iso(prev_session, context="previous chain")
    cur_iso = _session_iso(cur_session, context="current chain")
    sessions = tuple(_session_iso(item, context="calendar") for item in calendar_sessions)

    counts = {flag: 0 for flag in FLAG_PRECEDENCE}
    evaluated = {flag: 0 for flag in FLAG_PRECEDENCE}
    examples: dict[str, list[dict[str, object]]] = {flag: [] for flag in FLAG_PRECEDENCE}
    not_evaluable: set[str] = set()
    condition_not_met: set[str] = set()

    if cur_iso not in sessions or sessions.index(cur_iso) == 0:
        not_evaluable.add("GAP_SESSION")
    else:
        evaluated["GAP_SESSION"] = 1
        if sessions[sessions.index(cur_iso) - 1] != prev_iso:
            counts["GAP_SESSION"] = 1
            examples["GAP_SESSION"].append(
                {"previous_session": prev_iso, "current_session": cur_iso}
            )

    if _missing_contract_keys(prev_chain) or _missing_contract_keys(cur_chain):
        not_evaluable.update(flag for flag in FLAG_PRECEDENCE if flag != "GAP_SESSION")
        return _report(
            prev_session=prev_iso,
            cur_session=cur_iso,
            counts=counts,
            evaluated=evaluated,
            examples=examples,
            not_evaluable=not_evaluable,
            condition_not_met=condition_not_met,
        )

    previous = _prepare_chain(prev_chain, context="previous chain")
    current = _prepare_chain(cur_chain, context="current chain")

    structural_ready = not _missing_columns(previous, required=_LIQUIDITY_COLUMNS)
    if not structural_ready:
        not_evaluable.update(("EXPIRY_VANISHED", "STRIKE_VANISHED"))
        previous_admitted = previous.iloc[0:0].copy()
    else:
        unexpired = previous["expiration"] >= cur_iso
        previous_admitted = previous.loc[_liquid_mask(previous) & unexpired].copy()

    current_keys = {_contract_key(row) for _, row in current.iterrows()}
    current_expirations = set(current["expiration"].astype(str))
    if structural_ready:
        evaluated["EXPIRY_VANISHED"] = int(previous_admitted["expiration"].nunique())
        evaluated["STRIKE_VANISHED"] = int(len(previous_admitted))
        for expiration, group in previous_admitted.groupby("expiration", sort=True):
            if str(expiration) not in current_expirations:
                counts["EXPIRY_VANISHED"] += 1
                examples["EXPIRY_VANISHED"].append(
                    {"expiration": str(expiration), "admitted_contracts": int(len(group))}
                )
        for _, row in previous_admitted.sort_values(list(_KEY_COLUMNS), kind="stable").iterrows():
            if _contract_key(row) not in current_keys:
                counts["STRIKE_VANISHED"] += 1
                examples["STRIKE_VANISHED"].append(_contract_example(row))

    current_by_key = {_contract_key(row): row for _, row in current.iterrows()}
    small_move = _small_move(prev_close, cur_close)
    if small_move is None:
        not_evaluable.add("DELTA_JUMP")
    elif not structural_ready:
        not_evaluable.add("DELTA_JUMP")
    elif _missing_columns(previous, current, required=("delta",)):
        not_evaluable.add("DELTA_JUMP")
    elif not small_move:
        condition_not_met.add("DELTA_JUMP")
    else:
        for _, prev_row in previous_admitted.sort_values(
            list(_KEY_COLUMNS), kind="stable"
        ).iterrows():
            cur_row = current_by_key.get(_contract_key(prev_row))
            if cur_row is None:
                continue
            prev_delta = _numeric(prev_row, "delta")
            cur_delta = _numeric(cur_row, "delta")
            if prev_delta is not None and cur_delta is not None:
                evaluated["DELTA_JUMP"] += 1
                if abs(cur_delta - prev_delta) > config.CONSISTENCY_DELTA_JUMP_ABS:
                    counts["DELTA_JUMP"] += 1
                    examples["DELTA_JUMP"].append(
                        _contract_example(
                            prev_row,
                            previous_delta=prev_delta,
                            current_delta=cur_delta,
                            absolute_change=abs(cur_delta - prev_delta),
                        )
                    )

    if not structural_ready or _missing_columns(current, required=("bid", "ask")):
        not_evaluable.add("SPREAD_BLOWOUT")
    else:
        for _, prev_row in previous_admitted.sort_values(
            list(_KEY_COLUMNS), kind="stable"
        ).iterrows():
            cur_row = current_by_key.get(_contract_key(prev_row))
            if cur_row is None:
                continue
            prev_bid, prev_ask = _numeric(prev_row, "bid"), _numeric(prev_row, "ask")
            cur_bid, cur_ask = _numeric(cur_row, "bid"), _numeric(cur_row, "ask")
            if None in (prev_bid, prev_ask, cur_bid, cur_ask):
                continue
            prev_mid = (prev_bid + prev_ask) / 2.0
            cur_mid = (cur_bid + cur_ask) / 2.0
            if prev_mid <= 0 or cur_mid <= 0:
                continue
            prev_spread = (prev_ask - prev_bid) / prev_mid
            cur_spread = (cur_ask - cur_bid) / cur_mid
            evaluated["SPREAD_BLOWOUT"] += 1
            if (
                cur_spread >= prev_spread * config.CONSISTENCY_SPREAD_BLOWOUT_MIN_RATIO
                and cur_spread > config.MAX_SPREAD_PCT
            ):
                counts["SPREAD_BLOWOUT"] += 1
                examples["SPREAD_BLOWOUT"].append(
                    _contract_example(
                        prev_row,
                        previous_spread_fraction=prev_spread,
                        current_spread_fraction=cur_spread,
                    )
                )

    return _report(
        prev_session=prev_iso,
        cur_session=cur_iso,
        counts=counts,
        evaluated=evaluated,
        examples=examples,
        not_evaluable=not_evaluable,
        condition_not_met=condition_not_met,
    )
