"""Pure contracts and descriptive/inference views for the A2 outcome battery.

This module deliberately has no data loaders or order-path imports.  It accepts
already-resolved, point-in-time outcomes and provides two structurally separate
views: a weekly non-overlapping cohort view for inference and an all-row
staggered view for descriptive realism.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from statistics import median
from types import MappingProxyType
from typing import Mapping, MutableMapping, Sequence, cast

import metrics
from options_researcher.robustness.runner import _permutation_result, _stress_metrics
from options_researcher.robustness.screening import (
    PanelObservation,
    cost_adjusted_primary_metric,
)
from options_researcher.robustness.statistics import holm_step_down

RECONCILIATION_TOLERANCE = 1e-12
BUCKET_COUNT = 3
PERMUTATION_COUNT = 5_000
HOLM_ALPHA = 0.10
COST_STRESS_MULTIPLIERS = (0.5, 1.0, 1.5)
PROVENANCE_IDENTITY_KEYS = ("source", "source_id", "receipt", "receipt_id")

# These are the literal A2 registration arms.  The values are intentionally
# local to this pure boundary; Task 2 may import them but must not redefine
# them in a selector or resolver.
LANE_COMPONENTS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "csp": (
            "option_pnl",
            "assigned_stock_result",
            "collateral_return",
            "cash_return_forgone",
            "max_adverse_excursion",
            "final_loss",
        ),
        "covered_call": (
            "short_call_result",
            "stock_result",
            "combined_result",
            "combined_minus_stock_only",
            "assignment_incidence",
            "lost_upside",
        ),
        "pmcc": (
            "long_leg_result",
            "short_leg_result",
            "combined_result",
            "return_on_original_capital",
            "per_cycle_result",
            "assignment_exposure",
        ),
        "leaps": (
            "option_result",
            "stock_result",
            "delta_adjusted_stock_result",
            "spread_cost",
            "vega_contribution",
            "earnings_exposure_count",
            "drawdown",
        ),
        "tactical_call": (
            "stock_price",
            "iv",
            "decay",
            "cross_effects",
            "spread_cost",
            "residual",
        ),
    }
)

LANE_ARMS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "csp": (
            "capture_50",
            "close_21_dte",
            "fixed_10_sessions",
            "breach_hold_21_dte",
            "assignment_accepting",
        ),
        "covered_call": ("covered_call",),
        "pmcc": ("pmcc",),
        "leaps": ("21_sessions", "63_sessions", "126_sessions"),
        "tactical_call": ("5_sessions", "10_sessions", "20_sessions"),
    }
)

# Existing presentation code calls the covered-call and tactical lanes ``cc``
# and ``tactical`` in a few places.  They are accepted only as explicit aliases
# and are normalized before any pooling or metric calculation.
LANE_ALIASES = {"cc": "covered_call", "tactical": "tactical_call"}


def _canonical_lane(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("A2 lane must be non-empty text")
    lane = LANE_ALIASES.get(value, value)
    if lane not in LANE_COMPONENTS:
        raise ValueError(f"unknown A2 lane: {value!r}")
    return lane


def _validate_arm(lane: str, arm: object) -> str:
    if not isinstance(arm, str) or arm not in LANE_ARMS[lane]:
        raise ValueError(f"unknown A2 arm {arm!r} for lane {lane!r}")
    return arm


def _as_iso(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO date")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date") from exc
    return value


def _finite(value: object, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be finite")
    try:
        # ``float`` accepts a wider runtime protocol than pyright can infer
        # from ``object`` (for example Decimal and numpy scalar values).  The
        # cast is type-only; the conversion and finite check remain the
        # fail-closed runtime boundary.
        result = float(cast(str | float | int, value))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field} must be finite") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def _validate_provenance_identity(provenance: Mapping[str, object]) -> None:
    identity_keys = [key for key in PROVENANCE_IDENTITY_KEYS if key in provenance]
    if not identity_keys:
        raise ValueError("A2 provenance requires a named source or receipt identity field")
    for key in identity_keys:
        value = provenance[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError("A2 provenance source/receipt identity must be non-empty text")


@dataclass(frozen=True, slots=True)
class A2Outcome:
    """One fully resolved A2 observation.

    ``components`` is intentionally a mapping rather than a single P&L value:
    lane-specific attribution remains visible and cannot be reconstructed from
    the headline return.  ``provenance`` must carry at least one non-empty
    source identity.  Mapping values are copied into read-only proxies.
    """

    symbol: str
    decision_date: str
    entry_date: str
    resolution_date: str
    maximum_resolution_date: str
    lane: str
    arm: str
    score: float
    gross_return: float
    modeled_cost: float
    bid_ask_cost: float
    cost_adjusted_return: float
    components: Mapping[str, float]
    provenance: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("A2 symbol must be non-empty text")
        decision = _as_iso(self.decision_date, "decision_date")
        entry = _as_iso(self.entry_date, "entry_date")
        resolution = _as_iso(self.resolution_date, "resolution_date")
        maximum_resolution = _as_iso(self.maximum_resolution_date, "maximum_resolution_date")
        if date.fromisoformat(entry) <= date.fromisoformat(decision):
            raise ValueError("A2 entry_date must be after decision_date")
        if date.fromisoformat(resolution) < date.fromisoformat(entry):
            raise ValueError("A2 resolution_date cannot precede entry_date")
        if date.fromisoformat(maximum_resolution) < date.fromisoformat(resolution):
            raise ValueError("A2 maximum_resolution_date cannot precede resolution_date")

        lane = _canonical_lane(self.lane)
        arm = _validate_arm(lane, self.arm)
        object.__setattr__(self, "decision_date", decision)
        object.__setattr__(self, "entry_date", entry)
        object.__setattr__(self, "resolution_date", resolution)
        object.__setattr__(self, "maximum_resolution_date", maximum_resolution)
        object.__setattr__(self, "lane", lane)
        object.__setattr__(self, "score", _finite(self.score, "score"))
        gross = _finite(self.gross_return, "gross_return")
        modeled = _finite(self.modeled_cost, "modeled_cost")
        bid_ask = _finite(self.bid_ask_cost, "bid_ask_cost")
        adjusted = _finite(self.cost_adjusted_return, "cost_adjusted_return")
        if modeled < 0.0 or bid_ask < 0.0:
            raise ValueError("A2 costs must be non-negative")
        if bid_ask > modeled + RECONCILIATION_TOLERANCE:
            raise ValueError("A2 bid/ask cost cannot exceed modeled cost")
        if not math.isclose(
            adjusted,
            gross - modeled,
            rel_tol=0.0,
            abs_tol=RECONCILIATION_TOLERANCE,
        ):
            raise ValueError("A2 cost-adjusted return must equal gross return minus modeled cost")

        if not isinstance(self.components, Mapping):
            raise ValueError("A2 components must be a mapping")
        missing = set(LANE_COMPONENTS[lane]) - set(self.components)
        if missing:
            raise ValueError(
                f"A2 {lane} outcome missing accounting component(s): {sorted(missing)}"
            )
        components = {
            str(key): _finite(value, f"component {key!r}") for key, value in self.components.items()
        }
        if not isinstance(self.provenance, Mapping) or not self.provenance:
            raise ValueError("A2 provenance must be a non-empty mapping")
        provenance = dict(self.provenance)
        if any(not isinstance(key, str) or not key.strip() for key in provenance):
            raise ValueError("A2 provenance keys must be non-empty text")
        _validate_provenance_identity(provenance)
        object.__setattr__(self, "arm", arm)
        object.__setattr__(self, "gross_return", gross)
        object.__setattr__(self, "modeled_cost", modeled)
        object.__setattr__(self, "bid_ask_cost", bid_ask)
        object.__setattr__(self, "cost_adjusted_return", adjusted)
        object.__setattr__(self, "components", MappingProxyType(components))
        object.__setattr__(self, "provenance", MappingProxyType(provenance))

    @property
    def ticker(self) -> str:
        return self.symbol

    @property
    def parameter_id(self) -> str:
        return self.arm

    @property
    def identity(self) -> tuple[str, str, str, str, str, str]:
        return (
            self.symbol,
            self.decision_date,
            self.entry_date,
            self.resolution_date,
            self.lane,
            self.arm,
        )


def _outcome_from_mapping(raw: Mapping[str, object]) -> A2Outcome:
    def value(*names: str, default: object = None) -> object:
        for name in names:
            if name in raw:
                return raw[name]
        return default

    def required_text(*names: str) -> str:
        candidate = value(*names)
        if not isinstance(candidate, str):
            raise ValueError(f"A2 outcome field {names[0]!r} must be text")
        return candidate

    def required_number(*names: str) -> float:
        return _finite(value(*names), f"A2 outcome field {names[0]!r}")

    def required_components() -> Mapping[str, float]:
        candidate = value("components", "accounting")
        if not isinstance(candidate, Mapping):
            raise ValueError("A2 outcome components must be a mapping")
        converted: dict[str, float] = {}
        for key, component in candidate.items():
            if not isinstance(key, str):
                raise ValueError("A2 outcome component keys must be text")
            converted[key] = _finite(component, f"component {key!r}")
        return converted

    def required_provenance() -> Mapping[str, object]:
        candidate = value("provenance", "source_provenance")
        if not isinstance(candidate, Mapping):
            raise ValueError("A2 outcome provenance must be a mapping")
        if any(not isinstance(key, str) for key in candidate):
            raise ValueError("A2 outcome provenance keys must be text")
        return dict(candidate)

    return A2Outcome(
        symbol=required_text("symbol", "ticker"),
        decision_date=required_text("decision_date", "decision"),
        entry_date=required_text("entry_date", "entry"),
        resolution_date=required_text("resolution_date", "resolution"),
        maximum_resolution_date=required_text("maximum_resolution_date", "maximum_resolution"),
        lane=required_text("lane"),
        arm=required_text("arm", "parameter_id"),
        score=required_number("score"),
        gross_return=required_number("gross_return", "gross_forward_return", "return"),
        modeled_cost=required_number("modeled_cost", "cost"),
        bid_ask_cost=required_number("bid_ask_cost", "bid_ask"),
        cost_adjusted_return=required_number(
            "cost_adjusted_return", "forward_cost_adjusted_return", "net_return"
        ),
        components=required_components(),
        provenance=required_provenance(),
    )


def _coerce_outcomes(outcomes: Sequence[A2Outcome | Mapping[str, object]]) -> tuple[A2Outcome, ...]:
    result: list[A2Outcome] = []
    for index, raw in enumerate(outcomes):
        if isinstance(raw, A2Outcome):
            result.append(raw)
        elif isinstance(raw, Mapping):
            try:
                result.append(_outcome_from_mapping(raw))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid A2 outcome at index {index}: {exc}") from exc
        else:
            raise ValueError(f"invalid A2 outcome at index {index}")
    return tuple(result)


def validate_outcomes(
    outcomes: Sequence[A2Outcome | Mapping[str, object]],
    *,
    lane: str | None = None,
    arm: str | None = None,
) -> tuple[A2Outcome, ...]:
    """Validate and return one immutable, single-lane/single-arm cohort."""

    rows = _coerce_outcomes(outcomes)
    if not rows:
        return ()
    expected_lane = _canonical_lane(lane) if lane is not None else rows[0].lane
    expected_arm = arm if arm is not None else rows[0].arm
    _validate_arm(expected_lane, expected_arm)
    if any(row.lane != expected_lane for row in rows):
        raise ValueError("A2 outcomes from different lanes cannot be pooled")
    if any(row.arm != expected_arm for row in rows):
        raise ValueError("A2 outcomes from different arms cannot be pooled")
    identities = [row.identity for row in rows]
    if len(set(identities)) != len(identities):
        raise ValueError("A2 outcomes contain duplicate identities")
    return tuple(sorted(rows, key=lambda row: (row.entry_date, row.symbol, row.resolution_date)))


def non_overlapping_inference_rows(
    outcomes: Sequence[A2Outcome | Mapping[str, object]],
    *,
    lane: str | None = None,
    arm: str | None = None,
    expected_symbols: Sequence[str] | None = None,
    decision_dates: Sequence[str] | None = None,
    diagnostics: MutableMapping[str, int] | None = None,
) -> tuple[A2Outcome, ...]:
    """Retain each ISO week's earliest complete, ex-ante non-overlapping board.

    A spacing failure rejects the week's candidate rather than promoting a
    later board.  The strict comparison is intentional: an ex-ante maximum
    resolution on the next board's entry date is still overlapping.
    """

    rows = validate_outcomes(outcomes, lane=lane, arm=arm)
    expected = None
    if expected_symbols is not None:
        expected = tuple(expected_symbols)
        if (
            not expected
            or len(set(expected)) != len(expected)
            or any(not isinstance(symbol, str) or not symbol for symbol in expected)
        ):
            raise ValueError("A2 expected_symbols must be unique non-empty text")

    grouped: dict[str, list[A2Outcome]] = {}
    for row in rows:
        grouped.setdefault(row.decision_date, []).append(row)
    observed_dates = set(grouped)
    if decision_dates is not None:
        observed_dates.update(_as_iso(value, "decision_date") for value in decision_dates)
    weeks: dict[tuple[int, int], list[str]] = {}
    for decision_day in sorted(observed_dates):
        iso = date.fromisoformat(decision_day).isocalendar()
        weeks.setdefault((iso.year, iso.week), []).append(decision_day)

    def count(key: str) -> None:
        if diagnostics is not None:
            diagnostics[key] = diagnostics.get(key, 0) + 1

    accepted: list[A2Outcome] = []
    prior_max: date | None = None
    for week_dates in weeks.values():
        candidates: list[tuple[str, tuple[A2Outcome, ...]]] = []
        for decision_day in week_dates:
            cohort = tuple(grouped.get(decision_day, ()))
            symbols = tuple(row.symbol for row in cohort)
            entries = {row.entry_date for row in cohort}
            complete = (
                bool(cohort)
                and len(entries) == 1
                and (
                    expected is None
                    or (len(symbols) == len(expected) and set(symbols) == set(expected))
                )
            )
            if complete:
                candidates.append((decision_day, cohort))
        if not candidates:
            count("weeks_without_complete_board")
            continue
        candidate_day, cohort = candidates[0]
        entry = date.fromisoformat(cohort[0].entry_date)
        if prior_max is not None and not prior_max < entry:
            count("weeks_skipped_by_spacing")
            continue
        accepted.extend(cohort)
        if candidate_day != week_dates[0]:
            count("accepted_board_not_first_session_of_week")
        prior_max = max(date.fromisoformat(row.maximum_resolution_date) for row in cohort)
    return tuple(accepted)


def staggered_descriptive_rows(
    outcomes: Sequence[A2Outcome | Mapping[str, object]],
    *,
    lane: str | None = None,
    arm: str | None = None,
) -> tuple[A2Outcome, ...]:
    """Return every valid row; this path never calls inference helpers."""

    return validate_outcomes(outcomes, lane=lane, arm=arm)


def _group_by_entry_date(
    rows: Sequence[A2Outcome],
) -> tuple[tuple[str, tuple[A2Outcome, ...]], ...]:
    grouped: dict[str, list[A2Outcome]] = {}
    for row in rows:
        grouped.setdefault(row.entry_date, []).append(row)
    return tuple(
        (entry_date, tuple(sorted(group, key=lambda row: row.symbol)))
        for entry_date, group in sorted(grouped.items())
    )


def _panel_rows(rows: Sequence[A2Outcome]) -> tuple[PanelObservation, ...]:
    return tuple(
        PanelObservation(
            panel_date=row.entry_date,
            ticker=row.symbol,
            lane=row.lane,
            parameter_id=row.arm,
            score=row.score,
            gross_forward_return=row.gross_return,
            modeled_cost=row.modeled_cost,
            bid_ask_cost=row.bid_ask_cost,
            forward_cost_adjusted_return=row.cost_adjusted_return,
            regime=str(row.provenance.get("regime", "unknown")),
        )
        for row in rows
    )


def _daily_summary(
    rows: Sequence[A2Outcome],
) -> tuple[tuple[str, float, tuple[str, ...], tuple[str, ...], float, float, float], ...]:
    output = []
    for entry_date, cohort in _group_by_entry_date(rows):
        ordered = sorted(cohort, key=lambda row: (-row.score, row.symbol))
        bucket = len(ordered) // BUCKET_COUNT
        if bucket < 1:
            continue
        top, middle, bottom = ordered[:bucket], ordered[bucket : 2 * bucket], ordered[-bucket:]
        means = tuple(
            sum(row.cost_adjusted_return for row in group) / len(group)
            for group in (top, middle, bottom)
        )
        output.append(
            (
                entry_date,
                means[0] - means[2],
                tuple(row.symbol for row in top),
                tuple(row.symbol for row in bottom),
                means[0],
                means[1],
                means[2],
            )
        )
    return tuple(output)


def _drawdown(values: Sequence[float]) -> float:
    peak = 0.0
    running = 0.0
    maximum = 0.0
    for value in values:
        running += value
        peak = max(peak, running)
        maximum = max(maximum, peak - running)
    return maximum


@dataclass(frozen=True, slots=True)
class A2VariantSummary:
    lane: str
    arm: str
    status: str
    inference_count: int = 0
    descriptive_count: int = 0
    top_count: int = 0
    middle_count: int = 0
    bottom_count: int = 0
    spread: float = float("nan")
    middle_monotonicity: bool | None = None
    positive_cohort_win_rate: float = float("nan")
    median_cohort_spread: float = float("nan")
    worst_cohort: float = float("nan")
    worst_cohort_date: str | None = None
    cumulative_spread_drawdown: float = float("nan")
    top_bucket_turnover: float = float("nan")
    bottom_bucket_observation_count: int = 0
    cost_stress: Mapping[float, float] = MappingProxyType({})
    bid_ask_stress: Mapping[float, float] = MappingProxyType({})
    raw_p_value: float | None = None
    adjusted_p_value: float | None = None
    confidence_interval: tuple[float, float] | None = None
    expectancy_confidence_interval: tuple[float, float] | None = None
    claim_status: str = "NO_DATA"
    effective_k: int = 1
    holm_family_complete: bool = False
    holm_family_size: int = 0

    @property
    def parameter_id(self) -> str:
        return self.arm

    @property
    def median(self) -> float:
        return self.median_cohort_spread

    @property
    def worst_period(self) -> float:
        return self.worst_cohort

    @property
    def drawdown(self) -> float:
        return self.cumulative_spread_drawdown

    @property
    def turnover(self) -> float:
        return self.top_bucket_turnover


def summarize_lane(
    outcomes: Sequence[A2Outcome | Mapping[str, object]],
    lane: str,
    arm: str | None = None,
    *,
    effective_k: int = 1,
    measured_dependence: bool = False,
    family_raw_p_values: Mapping[str, float] | None = None,
    random_seed: int = 42,
    permutations: int = PERMUTATION_COUNT,
) -> A2VariantSummary:
    """Summarize exactly one lane/arm using only inference rows.

    ``staggered_descriptive_rows`` is intentionally not called here.  A caller
    that wants the realism view must request it separately, preventing a flag
    from accidentally admitting overlapping rows into inference.
    """

    canonical_lane = _canonical_lane(lane)
    selected_arm = arm or (LANE_ARMS[canonical_lane][0])
    if effective_k < 1:
        raise ValueError("effective_k must be positive")
    if permutations < 1:
        raise ValueError("permutations must be positive")
    if not outcomes:
        _validate_arm(canonical_lane, selected_arm)
        return A2VariantSummary(
            lane=canonical_lane,
            arm=selected_arm,
            status="no data",
            effective_k=effective_k,
        )

    rows = non_overlapping_inference_rows(outcomes, lane=canonical_lane, arm=selected_arm)
    if not rows:
        return A2VariantSummary(
            lane=canonical_lane,
            arm=selected_arm,
            status="no data",
            effective_k=effective_k,
        )
    panel = _panel_rows(rows)
    metric = cost_adjusted_primary_metric(panel, bucket_count=BUCKET_COUNT)
    daily = _daily_summary(rows)
    spreads = tuple(item[1] for item in daily)
    middle_ok = all(item[4] >= item[5] >= item[6] for item in daily) if daily else None
    turnover_values = []
    for previous, current in zip(daily, daily[1:], strict=False):
        previous_top, current_top = set(previous[2]), set(current[2])
        if previous_top and current_top:
            turnover_values.append(
                1.0 - len(previous_top & current_top) / len(previous_top | current_top)
            )
    turnover = sum(turnover_values) / len(turnover_values) if turnover_values else 0.0
    cost_stress, bid_ask_stress = _stress_metrics(panel, bucket_count=BUCKET_COUNT)

    raw_p: float | None = None
    effect_ci: tuple[float, float] | None = None
    try:
        raw_p, _, effect_ci = _permutation_result(
            panel,
            observed=metric.spread,
            bucket_count=BUCKET_COUNT,
            block_size=2,
            permutations=permutations,
            seed=random_seed,
        )
    except (ValueError, FloatingPointError):
        # Thin historical fixtures have no valid circular block envelope; the
        # descriptive summary remains useful, but no p-value claim is emitted.
        pass

    expectancy_ci: tuple[float, float] | None = None
    try:
        expectancy_ci = metrics.dependence_aware_expectancy_ci(
            [row.entry_date for row in rows],
            [row.cost_adjusted_return for row in rows],
            n_boot=permutations,
            seed=random_seed,
        )
        if any(not math.isfinite(value) for value in expectancy_ci):
            expectancy_ci = None
    except (ValueError, FloatingPointError):
        pass

    claim_status = "DESCRIPTIVE_ONLY"
    adjusted_p: float | None = None
    family_complete = False
    family_size = 0
    family_values: dict[str, float] = {}
    if family_raw_p_values is not None:
        if not isinstance(family_raw_p_values, Mapping):
            raise ValueError("family_raw_p_values must be a mapping")
        family_values = dict(family_raw_p_values)
        family_size = len(family_values)
        for parameter_id, p_value in family_values.items():
            if (
                not isinstance(parameter_id, str)
                or parameter_id not in LANE_ARMS[canonical_lane]
                or not isinstance(p_value, (int, float))
                or isinstance(p_value, bool)
                or not math.isfinite(float(p_value))
                or not 0.0 <= float(p_value) <= 1.0
            ):
                raise ValueError("family_raw_p_values contains an invalid arm or p-value")
        family_complete = set(family_values) == set(LANE_ARMS[canonical_lane])
        if selected_arm in family_values:
            supplied = float(family_values[selected_arm])
            if raw_p is not None and not math.isclose(
                raw_p, supplied, rel_tol=0.0, abs_tol=RECONCILIATION_TOLERANCE
            ):
                raise ValueError("selected raw p-value disagrees with supplied Holm family")
            raw_p = supplied
    if effective_k >= 10 or measured_dependence:
        claim_status = "BLOCKED_ROMANO_WOLF_UNAVAILABLE"
    elif family_complete:
        adjusted_p = holm_step_down(family_values, alpha=HOLM_ALPHA)[selected_arm].adjusted_p_value
    elif family_raw_p_values is not None:
        claim_status = "HOLM_FAMILY_INCOMPLETE"
    return A2VariantSummary(
        lane=canonical_lane,
        arm=selected_arm,
        status="ok",
        inference_count=len(rows),
        descriptive_count=len(outcomes),
        top_count=metric.top_count,
        middle_count=metric.observation_count - metric.top_count - metric.bottom_count,
        bottom_count=metric.bottom_count,
        spread=metric.spread,
        middle_monotonicity=middle_ok,
        positive_cohort_win_rate=(
            sum(spread > 0.0 for spread in spreads) / len(spreads) if spreads else float("nan")
        ),
        median_cohort_spread=median(spreads) if spreads else float("nan"),
        worst_cohort=min(spreads) if spreads else float("nan"),
        worst_cohort_date=(min(daily, key=lambda item: item[1])[0] if daily else None),
        cumulative_spread_drawdown=_drawdown(spreads),
        top_bucket_turnover=turnover,
        bottom_bucket_observation_count=metric.bottom_count,
        cost_stress=MappingProxyType(dict(cost_stress)),
        bid_ask_stress=MappingProxyType(dict(bid_ask_stress)),
        raw_p_value=raw_p,
        adjusted_p_value=adjusted_p,
        confidence_interval=effect_ci,
        expectancy_confidence_interval=expectancy_ci,
        claim_status=claim_status,
        effective_k=effective_k,
        holm_family_complete=family_complete,
        holm_family_size=family_size,
    )


__all__ = [
    "A2Outcome",
    "A2VariantSummary",
    "BUCKET_COUNT",
    "COST_STRESS_MULTIPLIERS",
    "HOLM_ALPHA",
    "LANE_ARMS",
    "LANE_COMPONENTS",
    "PERMUTATION_COUNT",
    "non_overlapping_inference_rows",
    "staggered_descriptive_rows",
    "summarize_lane",
    "validate_outcomes",
]
