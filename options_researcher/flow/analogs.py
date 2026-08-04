"""Outcome-blind, point-in-time historical analog matching."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np
import pandas as pd

from options_researcher.flow.horizons import required_horizon_for
from options_researcher.flow.panel import ANALOG_REGIME_READY

# Outcome columns a matched analog record may carry, in the order they are
# emitted. Each name's own trailing-integer horizon (required_horizon_for)
# may exceed PRIMARY_OPINION_OUTCOME_HORIZON_SESSIONS -- see
# `_mask_unknowable_outcomes`.
ANALOG_OUTCOME_COLUMNS = (
    "return_1",
    "return_5",
    "return_21",
    "excess_return_5",
    "future_rv21",
    "iv_change_5",
    "skew_change_5",
)

METHODOLOGY_VERSION = "options_flow_analogs_v2"
PRIMARY_OPINION_OUTCOME_HORIZON_SESSIONS = 5


@dataclass(frozen=True, slots=True)
class AnalogConfig:
    covariance_minimum: int = 126
    observations_per_feature: int = 8
    covariance_maximum: int = 252
    shrinkage: float = 0.5
    winsor_limit: float = 5.0
    eigenvalue_floor_ratio: float = 1e-6
    effective_rank_ratio: float = 0.75
    iv_percentile_caliper: float = 0.20
    skew_z_caliper: float = 1.0
    maximum_analogs: int = 20
    minimum_analogs: int = 10
    separation_sessions: int = 5
    similarity_quantile: float = 0.10
    metric_jaccard_minimum: float = 0.50


@dataclass(frozen=True, slots=True)
class CovarianceDiagnostics:
    observations: int
    features: int
    pre_condition_number: float
    post_condition_number: float
    effective_rank: float
    effective_rank_ratio: float
    eigenvalue_floor: float


@dataclass(frozen=True, slots=True)
class AnalogResult:
    methodology_version: str
    status: str
    query_session: str
    symbol: str
    reasons: tuple[str, ...]
    eligibility_counts: dict[str, int]
    covariance: CovarianceDiagnostics | None
    similarity_cutoff: float | None
    metric_jaccard: float | None
    analogs: tuple[dict[str, object], ...]
    rms_analogs: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["covariance"] = asdict(self.covariance) if self.covariance else None
        return payload


def _robust_transform(
    history: np.ndarray,
    *arrays: np.ndarray,
    winsor_limit: float,
) -> tuple[np.ndarray, ...]:
    center, scale = _robust_parameters(history)
    return tuple(
        np.clip((values - center) / scale, -winsor_limit, winsor_limit) for values in arrays
    )


def _robust_parameters(history: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    center = np.median(history, axis=0)
    mad = np.median(np.abs(history - center), axis=0)
    scale = 1.4826 * mad
    fallback = np.std(history, axis=0, ddof=1)
    scale = np.where(scale > 0, scale, np.where(fallback > 0, fallback, 1.0))
    return center, scale


def _apply_robust_parameters(
    values: np.ndarray,
    parameters: tuple[np.ndarray, np.ndarray],
    winsor_limit: float,
) -> np.ndarray:
    center, scale = parameters
    return np.clip((values - center) / scale, -winsor_limit, winsor_limit)


def _covariance(
    standardized: np.ndarray,
    config: AnalogConfig,
) -> tuple[np.ndarray, CovarianceDiagnostics]:
    sample = np.atleast_2d(np.cov(standardized, rowvar=False, ddof=1))
    diagonal = np.diag(np.diag(sample))
    shrunk = (1.0 - config.shrinkage) * sample + config.shrinkage * diagonal
    sample_eigenvalues = np.linalg.eigvalsh(sample)
    eigenvalues, eigenvectors = np.linalg.eigh(shrunk)
    positive = eigenvalues[eigenvalues > 0]
    reference = float(np.median(positive)) if len(positive) else 1.0
    floor = max(config.eigenvalue_floor_ratio * reference, np.finfo(float).eps)
    floored = np.maximum(eigenvalues, floor)
    inverse = (eigenvectors * (1.0 / floored)) @ eigenvectors.T
    effective_rank = float(floored.sum() ** 2 / np.square(floored).sum())
    positive_sample = sample_eigenvalues[sample_eigenvalues > 0]
    pre_condition = (
        float(positive_sample.max() / positive_sample.min()) if len(positive_sample) else np.inf
    )
    diagnostics = CovarianceDiagnostics(
        observations=len(standardized),
        features=standardized.shape[1],
        pre_condition_number=pre_condition,
        post_condition_number=float(floored.max() / floored.min()),
        effective_rank=effective_rank,
        effective_rank_ratio=effective_rank / standardized.shape[1],
        eigenvalue_floor=floor,
    )
    return inverse, diagnostics


def _pairwise_mahalanobis(values: np.ndarray, inverse: np.ndarray) -> np.ndarray:
    differences = values[:, None, :] - values[None, :, :]
    squared = np.einsum("...i,ij,...j->...", differences, inverse, differences)
    return np.sqrt(np.maximum(squared, 0.0))


def _nonoverlapping(
    candidates: pd.DataFrame,
    calendar: Sequence[str],
    *,
    count: int,
    separation: int,
) -> pd.DataFrame:
    positions = {session: index for index, session in enumerate(calendar)}
    chosen: list[object] = []
    chosen_positions: list[int] = []
    for index, row in candidates.iterrows():
        position = positions[str(row["session"])]
        if all(abs(position - previous) >= separation for previous in chosen_positions):
            chosen.append(index)
            chosen_positions.append(position)
        if len(chosen) == count:
            break
    return candidates.loc[chosen]


def _outcome_known_by_query(
    candidates: pd.DataFrame,
    calendar: Sequence[str],
    *,
    query_session: str,
    horizon_sessions: int,
) -> pd.DataFrame:
    """Keep candidates whose forward outcome was knowable on the query session."""
    positions = {session: index for index, session in enumerate(calendar)}
    query_position = positions[query_session]
    latest_eligible_position = query_position - horizon_sessions
    candidate_positions = np.asarray(
        [positions[str(session)] for session in candidates["session"].tolist()],
        dtype=int,
    )
    return candidates.loc[candidate_positions <= latest_eligible_position].copy()


def _mask_unknowable_outcomes(
    frame: pd.DataFrame,
    calendar: Sequence[str],
    *,
    query_session: str,
    columns: Sequence[str],
) -> pd.DataFrame:
    """Per-column point-in-time knowability mask for emitted analog outcomes.

    `_outcome_known_by_query` (above) only gates candidacy on the PRIMARY
    T+5 opinion horizon (PRIMARY_OPINION_OUTCOME_HORIZON_SESSIONS). A
    candidate that legitimately clears that T+5 gate can still carry
    longer-horizon outcome columns -- return_21, future_rv21 -- that were
    NOT yet knowable at `query_session` (candidate_session + 21 > query
    session). Emitting those raw values would be a point-in-time leak even
    though the candidate itself is a valid T+5 analog. Each column's own
    horizon is parsed from its name via `required_horizon_for`; any cell
    whose horizon has not yet elapsed as of `query_session` is masked to NaN
    -- never the future value. NaN (not None) is used deliberately: analog
    records flow into `options_researcher.flow.opinion`, which already
    filters outcome arrays with `np.isfinite`, so NaN is silently and safely
    excluded there, while None would crash its `float(...)` conversion.
    """
    positions = {session: index for index, session in enumerate(calendar)}
    query_position = positions[query_session]
    out = frame.copy()
    candidate_positions = np.asarray(
        [positions[str(session)] for session in out["session"].tolist()],
        dtype=int,
    )
    for column in columns:
        if column not in out.columns:
            continue
        horizon = required_horizon_for(column)
        unknowable = candidate_positions + horizon > query_position
        if unknowable.any():
            out.loc[unknowable, column] = np.nan
    return out


def match_historical_analogs(
    panel: pd.DataFrame,
    *,
    query_session: str,
    feature_columns: Sequence[str],
    symbol: str | None = None,
    pool_symbols: bool = False,
    config: AnalogConfig = AnalogConfig(),
) -> AnalogResult:
    """Return point-in-time, T+5-outcome-known analogs or fail-closed abstention.

    Covariance and distance calibration use prior feature observations only.
    Candidates that can feed the T+5 historical opinion must also have had their
    T+5 outcome available by ``query_session``.
    """
    regime_columns = {
        "symbol",
        "session",
        "data_quality",
        "event_state",
        "event_type",
        "iv_state",
        "iv_percentile_252",
        "term_slope",
        "skew_z",
        "rv_tercile",
        "analog_regime_state",
    }
    required = regime_columns | set(feature_columns)
    missing = sorted(required - set(panel.columns))
    if missing:
        raise ValueError(f"analog panel missing columns: {missing}")
    if not feature_columns:
        raise ValueError("at least one analog feature is required")
    ordered = panel.copy().sort_values(["symbol", "session"]).reset_index(drop=True)
    query_rows = ordered.loc[ordered["session"].eq(query_session)]
    if symbol is not None:
        query_rows = query_rows.loc[query_rows["symbol"].eq(symbol.upper())]
    if len(query_rows) != 1:
        raise ValueError("query session must identify exactly one panel row")
    query = query_rows.iloc[0]
    query_symbol = str(query["symbol"])
    reasons: list[str] = []
    if query["data_quality"] == "BLOCK":
        reasons.append("QUERY_DATA_BLOCKED")
    if query["event_state"] == "EVENT_CONTEXT_UNKNOWN":
        reasons.append("EVENT_CONTEXT_UNKNOWN")
    if query["iv_state"] == "IV_CONTEXT_UNKNOWN":
        reasons.append("IV_CONTEXT_UNKNOWN")
    if query["analog_regime_state"] != ANALOG_REGIME_READY:
        reasons.append("ANALOG_REGIME_UNKNOWN")
    try:
        query_numeric = np.asarray(
            [query["iv_percentile_252"], query["term_slope"], query["skew_z"]],
            dtype=float,
        )
        query_rv_tercile = float(query["rv_tercile"])
    except (TypeError, ValueError):
        query_numeric = np.full(3, np.nan)
        query_rv_tercile = np.nan
    if not np.isfinite(query_numeric).all() or query_rv_tercile not in (1, 2, 3):
        reasons.append("ANALOG_REGIME_UNKNOWN")
    if reasons:
        return AnalogResult(
            METHODOLOGY_VERSION,
            "ABSTAIN",
            query_session,
            query_symbol,
            tuple(reasons),
            {"prior_same_ticker": 0, "regime_eligible": 0},
            None,
            None,
            None,
            (),
            (),
        )

    prior_mask = ordered["session"].lt(query_session) & ordered["data_quality"].ne("BLOCK")
    if not pool_symbols:
        prior_mask &= ordered["symbol"].eq(query_symbol)
    prior = ordered.loc[prior_mask].copy()
    covariance_minimum = max(
        config.covariance_minimum,
        config.observations_per_feature * len(feature_columns),
    )
    valid_history = prior.dropna(subset=list(feature_columns))
    covariance_history = (
        valid_history.groupby("symbol", group_keys=False, sort=True)
        .tail(config.covariance_maximum)
        .copy()
        if pool_symbols
        else valid_history.tail(config.covariance_maximum).copy()
    )
    counts = {
        "prior_same_ticker": int(
            (
                ordered["symbol"].eq(query_symbol)
                & ordered["session"].lt(query_session)
                & ordered["data_quality"].ne("BLOCK")
            ).sum()
        ),
        "prior_pool": len(prior),
        "regime_eligible": 0,
        "t5_outcome_known_regime_eligible": 0,
    }
    query_ticker_history = covariance_history.loc[covariance_history["symbol"].eq(query_symbol)]
    history_sufficient = (
        len(query_ticker_history) >= covariance_minimum
        if pool_symbols
        else len(covariance_history) >= covariance_minimum
    )
    if not history_sufficient:
        reasons.append(f"COVARIANCE_HISTORY_BELOW_{covariance_minimum}")
        return AnalogResult(
            METHODOLOGY_VERSION,
            "ABSTAIN",
            query_session,
            query_symbol,
            tuple(reasons),
            counts,
            None,
            None,
            None,
            (),
            (),
        )

    event_match = prior["event_state"].eq(query["event_state"]) & prior["event_type"].eq(
        query["event_type"]
    )
    iv_match = (
        prior["analog_regime_state"].eq(ANALOG_REGIME_READY)
        & prior["iv_state"].eq(query["iv_state"])
        & prior["iv_percentile_252"]
        .sub(float(query["iv_percentile_252"]))
        .abs()
        .le(config.iv_percentile_caliper)
        & np.sign(prior["term_slope"]).eq(np.sign(float(query["term_slope"])))
        & prior["skew_z"].sub(float(query["skew_z"])).abs().le(config.skew_z_caliper)
        & prior["rv_tercile"].eq(query["rv_tercile"])
    )
    eligible = prior.loc[event_match & iv_match].dropna(subset=list(feature_columns)).copy()
    counts["regime_eligible"] = len(eligible)
    outcome_calendar = tuple(sorted(ordered["session"].astype(str).unique()))
    eligible = _outcome_known_by_query(
        eligible,
        outcome_calendar,
        query_session=query_session,
        horizon_sessions=PRIMARY_OPINION_OUTCOME_HORIZON_SESSIONS,
    )
    counts["t5_outcome_known_regime_eligible"] = len(eligible)
    if len(eligible) < config.minimum_analogs:
        reasons.append("INSUFFICIENT_T5_OUTCOME_KNOWN_REGIME_MATCHED_ANALOGS")
        return AnalogResult(
            METHODOLOGY_VERSION,
            "ABSTAIN",
            query_session,
            query_symbol,
            tuple(reasons),
            counts,
            None,
            None,
            None,
            (),
            (),
        )

    query_values = query.loc[list(feature_columns)].to_numpy(float).reshape(1, -1)
    if pool_symbols:
        parameters: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        history_parts: list[np.ndarray] = []
        accepted_symbols: list[str] = []
        for ticker, group in covariance_history.groupby("symbol", sort=True):
            ticker_name = str(ticker)
            if len(group) < covariance_minimum:
                continue
            values = group.loc[:, feature_columns].to_numpy(float)
            ticker_parameters = _robust_parameters(values)
            parameters[ticker_name] = ticker_parameters
            accepted_symbols.append(ticker_name)
            history_parts.append(
                _apply_robust_parameters(
                    values,
                    ticker_parameters,
                    config.winsor_limit,
                )
            )
        if query_symbol not in parameters:
            reasons.append(f"COVARIANCE_HISTORY_BELOW_{covariance_minimum}")
            return AnalogResult(
                METHODOLOGY_VERSION,
                "ABSTAIN",
                query_session,
                query_symbol,
                tuple(reasons),
                counts,
                None,
                None,
                None,
                (),
                (),
            )
        eligible = eligible.loc[eligible["symbol"].isin(accepted_symbols)].reset_index(drop=True)
        counts["t5_outcome_known_regime_eligible"] = len(eligible)
        if len(eligible) < config.minimum_analogs:
            reasons.append("INSUFFICIENT_T5_OUTCOME_KNOWN_REGIME_MATCHED_ANALOGS")
            return AnalogResult(
                METHODOLOGY_VERSION,
                "ABSTAIN",
                query_session,
                query_symbol,
                tuple(reasons),
                counts,
                None,
                None,
                None,
                (),
                (),
            )
        candidate_z = np.empty((len(eligible), len(feature_columns)), dtype=float)
        for ticker, positions in eligible.groupby("symbol", sort=True).groups.items():
            ticker_name = str(ticker)
            position_list = list(positions)
            candidate_z[position_list] = _apply_robust_parameters(
                eligible.loc[position_list, feature_columns].to_numpy(float),
                parameters[ticker_name],
                config.winsor_limit,
            )
        history_z = np.vstack(history_parts)
        query_z = _apply_robust_parameters(
            query_values,
            parameters[query_symbol],
            config.winsor_limit,
        )
    else:
        history_values = covariance_history.loc[:, feature_columns].to_numpy(float)
        candidate_values = eligible.loc[:, feature_columns].to_numpy(float)
        history_z, candidate_z, query_z = _robust_transform(
            history_values,
            history_values,
            candidate_values,
            query_values,
            winsor_limit=config.winsor_limit,
        )
    inverse, diagnostics = _covariance(history_z, config)
    if diagnostics.effective_rank_ratio < config.effective_rank_ratio:
        reasons.append("COVARIANCE_EFFECTIVE_RANK_FAILURE")
        return AnalogResult(
            METHODOLOGY_VERSION,
            "ABSTAIN",
            query_session,
            query_symbol,
            tuple(reasons),
            counts,
            diagnostics,
            None,
            None,
            (),
            (),
        )

    differences = candidate_z - query_z
    eligible["mahalanobis_distance"] = np.sqrt(
        np.maximum(np.einsum("...i,ij,...j->...", differences, inverse, differences), 0.0)
    )
    eligible["rms_distance"] = np.sqrt(np.mean(np.square(differences), axis=1))
    pairwise = _pairwise_mahalanobis(history_z, inverse)
    upper_triangle = pairwise[np.triu_indices_from(pairwise, k=1)]
    cutoff = float(np.quantile(upper_triangle, config.similarity_quantile))
    within_cutoff = eligible.loc[eligible["mahalanobis_distance"].le(cutoff)].sort_values(
        ["mahalanobis_distance", "session"]
    )
    eligible_symbols = eligible["symbol"].astype(str).tolist()
    calendar = sorted(
        ordered.loc[
            ordered["symbol"].astype(str).isin(eligible_symbols),
            "session",
        ]
        .astype(str)
        .unique()
    )
    selected = _nonoverlapping(
        within_cutoff,
        calendar,
        count=config.maximum_analogs,
        separation=config.separation_sessions,
    )
    rms_selected = _nonoverlapping(
        within_cutoff.sort_values(["rms_distance", "session"]),
        calendar,
        count=config.maximum_analogs,
        separation=config.separation_sessions,
    )
    neighbor_sets_sufficient = (
        len(selected) >= config.minimum_analogs and len(rms_selected) >= config.minimum_analogs
    )
    jaccard: float | None = None
    if not neighbor_sets_sufficient:
        reasons.append("INSUFFICIENT_ANALOGS_INSIDE_SIMILARITY_CUTOFF")
    else:
        primary_dates = set(selected["session"].astype(str))
        rms_dates = set(rms_selected["session"].astype(str))
        union = primary_dates | rms_dates
        jaccard = len(primary_dates & rms_dates) / len(union)
        if jaccard < config.metric_jaccard_minimum:
            reasons.append("METRIC_INSTABILITY")
    status = "READY" if not reasons else "DESCRIPTIVE_ONLY"
    outcome_columns = [column for column in ANALOG_OUTCOME_COLUMNS if column in selected]
    # `outcome_calendar` (built above from the full ordered panel) is used
    # rather than the narrower `calendar` local: it is guaranteed to contain
    # `query_session` itself, which the per-column knowability mask needs.
    selected = _mask_unknowable_outcomes(
        selected,
        outcome_calendar,
        query_session=query_session,
        columns=outcome_columns,
    )
    analog_columns = [
        "symbol",
        "session",
        "mahalanobis_distance",
        "rms_distance",
        *outcome_columns,
    ]
    return AnalogResult(
        METHODOLOGY_VERSION,
        status,
        query_session,
        query_symbol,
        tuple(reasons),
        counts,
        diagnostics,
        cutoff,
        jaccard,
        tuple(selected.loc[:, analog_columns].to_dict(orient="records")),
        tuple(rms_selected["session"].astype(str)),
    )
