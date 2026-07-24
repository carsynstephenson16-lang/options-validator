"""Pure fast screening over stored panel rows; no orders, positions, or data fetches."""

from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from itertools import groupby
from typing import Protocol, Sequence


@dataclass(frozen=True, slots=True)
class PanelObservation:
    panel_date: str
    ticker: str
    lane: str
    parameter_id: str
    score: float
    gross_forward_return: float
    modeled_cost: float
    bid_ask_cost: float
    forward_cost_adjusted_return: float
    regime: str = "unknown"

    def __post_init__(self) -> None:
        if not all((self.panel_date, self.ticker, self.lane, self.parameter_id)):
            raise ValueError("panel identity fields must be non-empty")
        try:
            date.fromisoformat(self.panel_date)
        except ValueError as exc:
            raise ValueError("panel_date must be an ISO date") from exc
        values = (
            self.score,
            self.gross_forward_return,
            self.modeled_cost,
            self.bid_ask_cost,
            self.forward_cost_adjusted_return,
        )
        if any(not math.isfinite(value) for value in values):
            raise ValueError("panel score, returns, and costs must be finite")
        if self.modeled_cost < 0 or self.bid_ask_cost < 0:
            raise ValueError("panel costs must be non-negative")
        if self.bid_ask_cost > self.modeled_cost:
            raise ValueError("bid/ask cost cannot exceed total modeled cost")
        if not math.isclose(
            self.forward_cost_adjusted_return,
            self.gross_forward_return - self.modeled_cost,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("cost-adjusted return must equal gross return minus modeled cost")


@dataclass(frozen=True, slots=True)
class PrimaryMetric:
    spread: float
    top_count: int
    bottom_count: int
    observation_count: int
    daily_spreads: tuple[float, ...]
    ticker_spread_contributions: tuple[tuple[str, float], ...]


def cost_adjusted_primary_metric(
    rows: Sequence[PanelObservation], *, bucket_count: int
) -> PrimaryMetric:
    if bucket_count < 2:
        raise ValueError("bucket_count must be at least two")
    lanes = {row.lane for row in rows}
    parameters = {row.parameter_id for row in rows}
    if len(lanes) > 1:
        raise ValueError("primary metric requires a single lane")
    if len(parameters) > 1:
        raise ValueError("primary metric requires a single parameter variant")
    identities = [(row.panel_date, row.ticker) for row in rows]
    if len(set(identities)) != len(identities):
        raise ValueError("primary metric refuses duplicate date/ticker rows")

    ordered = sorted(rows, key=lambda row: (row.panel_date, row.ticker))
    daily_spreads: list[float] = []
    top_count = 0
    bottom_count = 0
    contribution: dict[str, float] = {}
    for _, daily_iter in groupby(ordered, key=lambda row: row.panel_date):
        daily = sorted(daily_iter, key=lambda row: (-row.score, row.ticker))
        bucket_size = len(daily) // bucket_count
        if bucket_size < 1:
            continue
        top = daily[:bucket_size]
        bottom = daily[-bucket_size:]
        top_mean = sum(row.forward_cost_adjusted_return for row in top) / len(top)
        bottom_mean = sum(row.forward_cost_adjusted_return for row in bottom) / len(bottom)
        daily_spreads.append(top_mean - bottom_mean)
        top_count += len(top)
        bottom_count += len(bottom)
        for row in top:
            contribution[row.ticker] = contribution.get(row.ticker, 0.0) + (
                row.forward_cost_adjusted_return / len(top)
            )
        for row in bottom:
            contribution[row.ticker] = contribution.get(row.ticker, 0.0) - (
                row.forward_cost_adjusted_return / len(bottom)
            )
    spread = sum(daily_spreads) / len(daily_spreads) if daily_spreads else float("nan")
    return PrimaryMetric(
        spread=spread,
        top_count=top_count,
        bottom_count=bottom_count,
        observation_count=len(ordered),
        daily_spreads=tuple(daily_spreads),
        ticker_spread_contributions=tuple(
            (ticker, value / len(daily_spreads)) for ticker, value in sorted(contribution.items())
        ),
    )


def daily_spread_series(
    rows: Sequence[PanelObservation], *, bucket_count: int
) -> tuple[tuple[str, float, int], ...]:
    """(panel_date, spread, observation_count) aligned 1:1 with
    ``cost_adjusted_primary_metric(rows, bucket_count=...).daily_spreads``.

    Companion read-only view for the robustness return-matrix capture
    (options_researcher/robustness/return_matrix.py) -- it never feeds back
    into the registered metric. It mirrors cost_adjusted_primary_metric's
    per-day skip rule exactly (bucket_size = len(daily) // bucket_count;
    skip if < 1) using the identical single-lane/single-parameter/
    no-duplicate-identity validation and the identical sort/slice/sum/divide
    arithmetic, so the returned spread floats are the SAME values
    cost_adjusted_primary_metric computes internally -- this is not a second
    source of truth, just a second view of the one computation.
    ``observation_count`` is ``len(top) + len(bottom)`` for that day (i.e.
    2 * bucket_size), the same quantity PrimaryMetric accumulates into
    top_count/bottom_count across all days.
    """
    if bucket_count < 2:
        raise ValueError("bucket_count must be at least two")
    lanes = {row.lane for row in rows}
    parameters = {row.parameter_id for row in rows}
    if len(lanes) > 1:
        raise ValueError("daily spread series requires a single lane")
    if len(parameters) > 1:
        raise ValueError("daily spread series requires a single parameter variant")
    identities = [(row.panel_date, row.ticker) for row in rows]
    if len(set(identities)) != len(identities):
        raise ValueError("daily spread series refuses duplicate date/ticker rows")

    ordered = sorted(rows, key=lambda row: (row.panel_date, row.ticker))
    series: list[tuple[str, float, int]] = []
    for panel_date, daily_iter in groupby(ordered, key=lambda row: row.panel_date):
        daily = sorted(daily_iter, key=lambda row: (-row.score, row.ticker))
        bucket_size = len(daily) // bucket_count
        if bucket_size < 1:
            continue
        top = daily[:bucket_size]
        bottom = daily[-bucket_size:]
        top_mean = sum(row.forward_cost_adjusted_return for row in top) / len(top)
        bottom_mean = sum(row.forward_cost_adjusted_return for row in bottom) / len(bottom)
        series.append((panel_date, top_mean - bottom_mean, len(top) + len(bottom)))
    return tuple(series)


def evaluate_parameter_variants(
    rows: Sequence[PanelObservation], *, bucket_count: int, workers: int = 1
) -> tuple[tuple[str, PrimaryMetric], ...]:
    if workers < 1 or workers > 8:
        raise ValueError("workers must be between one and eight")
    grouped: dict[str, list[PanelObservation]] = {}
    for row in rows:
        grouped.setdefault(row.parameter_id, []).append(row)
    items = sorted(grouped.items())

    def evaluate(item: tuple[str, list[PanelObservation]]) -> tuple[str, PrimaryMetric]:
        parameter_id, parameter_rows = item
        return parameter_id, cost_adjusted_primary_metric(parameter_rows, bucket_count=bucket_count)

    if workers == 1 or len(items) < 2:
        return tuple(evaluate(item) for item in items)
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as executor:
        results = list(executor.map(evaluate, items))
    return tuple(sorted(results, key=lambda item: item[0]))


class LumibotFinalistAdapter(Protocol):
    def validate_finalists(self, parameter_ids: tuple[str, ...]) -> object: ...


def handoff_finalists(adapter: LumibotFinalistAdapter, finalists: tuple[str, ...]) -> object:
    if not finalists:
        raise ValueError("at least one finalist is required for Lumibot handoff")
    if len(set(finalists)) != len(finalists):
        raise ValueError("finalist ids must be unique")
    return adapter.validate_finalists(finalists)
