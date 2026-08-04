"""Covariance-aware analog and opinion tests."""

import unittest

import numpy as np
import pandas as pd

from options_researcher.flow.analogs import (
    AnalogConfig,
    AnalogResult,
    CovarianceDiagnostics,
    match_historical_analogs,
)
from options_researcher.flow.opinion import synthesize_historical_opinion
from options_researcher.flow.panel import assemble_analog_panel


def _panel() -> pd.DataFrame:
    sessions = pd.bdate_range("2025-01-02", periods=45)
    x = np.linspace(-1.0, 1.0, len(sessions))
    features = pd.DataFrame(
        {
            "symbol": "MSFT",
            "session": sessions.strftime("%Y-%m-%d"),
            "flow_a": x,
            "flow_b": 2 * x + 0.01 * np.cos(np.arange(len(sessions))),
            "return_5": 0.01 + 0.001 * np.sin(np.arange(len(sessions))),
            "excess_return_5": 0.008 + 0.001 * np.sin(np.arange(len(sessions))),
            "iv_change_5": 0.01,
        }
    )
    history_sessions = pd.bdate_range(sessions[0] - pd.offsets.BDay(20), sessions[-1])
    history_index = np.arange(len(history_sessions), dtype=float)
    atm30 = 0.20 + 0.0005 * history_index
    iv_history = pd.DataFrame(
        {
            "symbol": "MSFT",
            "session": history_sessions.strftime("%Y-%m-%d"),
            "atm30_iv": atm30,
            "atm60_iv": atm30 + 0.02,
            "put25_iv": atm30 + 0.01 + 0.0001 * history_index,
        }
    )
    close_history = pd.DataFrame(
        {
            "symbol": "MSFT",
            "session": history_sessions.strftime("%Y-%m-%d"),
            "close": 100.0 * np.exp(0.01 * history_index),
        }
    )
    quality = features.loc[:, ["symbol", "session"]].assign(data_quality="PASS")
    events = pd.DataFrame(
        columns=["symbol", "event_id", "event_type", "published_at", "effective_at"]
    )
    return assemble_analog_panel(
        features,
        data_quality=quality,
        iv_history=iv_history,
        close_history=close_history,
        events=events,
        trading_sessions=sessions.strftime("%Y-%m-%d"),
        event_coverage_complete=True,
        iv_history_window=10,
        rv_return_window=3,
        rv_tercile_history=10,
    )


class AnalogTests(unittest.TestCase):
    def test_shrinkage_mahalanobis_is_point_in_time_and_deterministic(self):
        panel = _panel()
        query = panel.iloc[34]["session"]
        config = AnalogConfig(
            covariance_minimum=12,
            observations_per_feature=2,
            covariance_maximum=30,
            effective_rank_ratio=0.50,
            maximum_analogs=5,
            minimum_analogs=3,
            separation_sessions=1,
            similarity_quantile=1.0,
            metric_jaccard_minimum=0.0,
        )
        first = match_historical_analogs(
            panel,
            query_session=query,
            feature_columns=["flow_a", "flow_b"],
            config=config,
        )
        changed = panel.copy()
        changed.loc[changed["session"] > query, ["flow_a", "flow_b"]] = 1_000.0
        second = match_historical_analogs(
            changed,
            query_session=query,
            feature_columns=["flow_a", "flow_b"],
            config=config,
        )
        self.assertEqual(first.status, "READY")
        self.assertEqual(first.as_dict(), second.as_dict())
        self.assertEqual(first.covariance.observations, 30)
        self.assertGreater(first.covariance.pre_condition_number, 100)

    def test_unknown_context_abstains(self):
        panel = _panel()
        query = panel.iloc[-1]["session"]
        panel.loc[panel["session"].eq(query), "event_state"] = "EVENT_CONTEXT_UNKNOWN"
        out = match_historical_analogs(
            panel,
            query_session=query,
            feature_columns=["flow_a", "flow_b"],
            config=AnalogConfig(covariance_minimum=10, observations_per_feature=2),
        )
        self.assertEqual(out.status, "ABSTAIN")
        self.assertIn("EVENT_CONTEXT_UNKNOWN", out.reasons)

    def test_pooled_secondary_normalizes_each_ticker_and_requires_query_symbol(self):
        msft = _panel()
        ceg = msft.copy()
        ceg["symbol"] = "CEG"
        ceg["flow_a"] = 100 + 20 * ceg["flow_a"]
        ceg["flow_b"] = -50 + 10 * ceg["flow_b"]
        panel = pd.concat([msft, ceg], ignore_index=True)
        query = msft.iloc[34]["session"]
        config = AnalogConfig(
            covariance_minimum=12,
            observations_per_feature=2,
            covariance_maximum=30,
            effective_rank_ratio=0.40,
            maximum_analogs=6,
            minimum_analogs=3,
            separation_sessions=1,
            similarity_quantile=1.0,
            metric_jaccard_minimum=0.0,
        )
        result = match_historical_analogs(
            panel,
            query_session=query,
            symbol="MSFT",
            pool_symbols=True,
            feature_columns=["flow_a", "flow_b"],
            config=config,
        )
        self.assertEqual(result.status, "READY")
        self.assertGreater(result.eligibility_counts["prior_pool"], 50)
        self.assertTrue({row["symbol"] for row in result.analogs}.issubset({"MSFT", "CEG"}))

    def test_t5_opinion_excludes_analog_without_a_query_known_outcome(self):
        panel = _panel()
        query_position = 34
        query = str(panel.iloc[query_position]["session"])
        too_recent_position = query_position - 2
        too_recent_session = str(panel.iloc[too_recent_position]["session"])
        panel.loc[panel["session"].eq(too_recent_session), "excess_return_5"] = -1.0
        config = AnalogConfig(
            covariance_minimum=12,
            observations_per_feature=2,
            covariance_maximum=30,
            effective_rank_ratio=0.50,
            maximum_analogs=10,
            minimum_analogs=10,
            separation_sessions=1,
            similarity_quantile=1.0,
            metric_jaccard_minimum=0.0,
        )

        primary = match_historical_analogs(
            panel,
            query_session=query,
            feature_columns=["flow_a", "flow_b"],
            config=config,
        )
        opinion = synthesize_historical_opinion(
            primary,
            pooled=primary,
            matched_base_positive_frequency=0.50,
        )

        positions = {str(session): position for position, session in enumerate(panel["session"])}
        self.assertEqual(primary.status, "READY")
        self.assertEqual(len(primary.analogs), 10)
        self.assertGreater(
            primary.eligibility_counts["regime_eligible"],
            primary.eligibility_counts["t5_outcome_known_regime_eligible"],
        )
        self.assertTrue(
            all(positions[str(row["session"])] + 5 <= query_position for row in primary.analogs)
        )
        self.assertNotIn(too_recent_session, {str(row["session"]) for row in primary.analogs})
        self.assertEqual(opinion.directional_opinion, "POSITIVE_HISTORICAL_LEAN")

    def test_longer_horizon_outcome_is_masked_when_not_yet_knowable(self):
        """Codex PR #19 review finding, live-reproduced: candidate eligibility
        only gates on the PRIMARY_OPINION_OUTCOME_HORIZON_SESSIONS=5 horizon
        (`_outcome_known_by_query`), but `analog_columns` also serializes
        longer-horizon outcome columns (return_21, future_rv21). A candidate
        whose T+5 outcome was legitimately known at the query session can
        still have a T+21 outcome that was NOT yet knowable -- before this
        fix, that future value was emitted verbatim (a point-in-time leak
        even though the candidate is a valid T+5 analog). Pinned with the
        same query_position=34 fixture as
        test_t5_opinion_excludes_analog_without_a_query_known_outcome: with
        maximum_analogs=10, all 10 selected analogs sit at positions 20-29
        (position+5 <= 34, so T5-eligible) but none reach position+21 <= 34
        (T21 needs position <= 13), so every emitted future_rv21 must be
        masked to NaN while return_5 stays a real, non-NaN value."""
        panel = _panel()
        # future_rv21 is not produced by assemble_analog_panel; attach a
        # column that would trivially reveal a leak (monotone in session) if
        # a future value ever slipped through unmasked.
        panel = panel.assign(future_rv21=0.30 + 0.001 * np.arange(len(panel)))
        query_position = 34
        query = str(panel.iloc[query_position]["session"])
        config = AnalogConfig(
            covariance_minimum=12,
            observations_per_feature=2,
            covariance_maximum=30,
            effective_rank_ratio=0.50,
            maximum_analogs=10,
            minimum_analogs=10,
            separation_sessions=1,
            similarity_quantile=1.0,
            metric_jaccard_minimum=0.0,
        )

        result = match_historical_analogs(
            panel,
            query_session=query,
            feature_columns=["flow_a", "flow_b"],
            config=config,
        )

        positions = {str(session): position for position, session in enumerate(panel["session"])}
        self.assertEqual(result.status, "READY")
        self.assertEqual(len(result.analogs), 10)
        # every selected candidate clears the T5 gate (return_5 real)...
        self.assertTrue(all(np.isfinite(row["return_5"]) for row in result.analogs))
        # ...but none clear the longer T21 horizon future_rv21 needs, and
        # none of the masked cells leak the real (monotone) future value.
        self.assertTrue(
            all(positions[str(row["session"])] + 21 > query_position for row in result.analogs)
        )
        self.assertTrue(all(np.isnan(row["future_rv21"]) for row in result.analogs))

    def test_similarity_cutoff_starvation_does_not_become_metric_instability(self):
        panel = _panel()
        result = match_historical_analogs(
            panel,
            query_session=str(panel.iloc[30]["session"]),
            feature_columns=["flow_a", "flow_b"],
            config=AnalogConfig(
                covariance_minimum=12,
                observations_per_feature=2,
                covariance_maximum=24,
                effective_rank_ratio=0.50,
                maximum_analogs=20,
                minimum_analogs=10,
                separation_sessions=1,
                similarity_quantile=0.10,
                metric_jaccard_minimum=0.50,
            ),
        )

        self.assertEqual(result.eligibility_counts["t5_outcome_known_regime_eligible"], 24)
        self.assertEqual(len(result.analogs), 0)
        self.assertEqual(len(result.rms_analogs), 0)
        self.assertEqual(result.metric_jaccard, None)
        self.assertEqual(result.reasons, ("INSUFFICIENT_ANALOGS_INSIDE_SIMILARITY_CUTOFF",))

    def test_opinion_requires_both_primary_and_pooled_evidence(self):
        diagnostics = CovarianceDiagnostics(200, 2, 100.0, 3.0, 1.8, 0.9, 1e-6)
        analogs = tuple(
            {
                "symbol": "MSFT",
                "session": f"2024-01-{index + 1:02d}",
                "return_5": 0.01 + index / 10_000,
                "excess_return_5": 0.008 + index / 10_000,
                "iv_change_5": 0.01 + index / 20_000,
            }
            for index in range(10)
        )
        primary = AnalogResult(
            "v2",
            "READY",
            "2025-01-02",
            "MSFT",
            (),
            {"prior_same_ticker": 200, "regime_eligible": 20},
            diagnostics,
            3.0,
            0.8,
            analogs,
            tuple(row["session"] for row in analogs),
        )
        opinion = synthesize_historical_opinion(
            primary,
            pooled=primary,
            matched_base_positive_frequency=0.50,
        )
        self.assertEqual(opinion.directional_opinion, "POSITIVE_HISTORICAL_LEAN")
        self.assertEqual(opinion.volatility_opinion, "VOLATILITY_EXPANSION_LEAN")
        abstain = synthesize_historical_opinion(
            primary,
            pooled=None,
            matched_base_positive_frequency=0.50,
        )
        self.assertEqual(abstain.status, "ABSTAIN_INSUFFICIENT_OR_UNRELIABLE_DATA")

    def test_base_positive_frequency_is_bounded_and_none_abstains(self):
        diagnostics = CovarianceDiagnostics(200, 2, 100.0, 3.0, 1.8, 0.9, 1e-6)
        analogs = tuple(
            {
                "symbol": "MSFT",
                "session": f"2024-01-{index + 1:02d}",
                "return_5": 0.01,
                "excess_return_5": 0.008,
                "iv_change_5": 0.01,
            }
            for index in range(10)
        )
        primary = AnalogResult(
            "v2",
            "READY",
            "2025-01-02",
            "MSFT",
            (),
            {"prior_same_ticker": 200, "regime_eligible": 20},
            diagnostics,
            3.0,
            0.8,
            analogs,
            tuple(row["session"] for row in analogs),
        )
        for value in (-0.01, 1.01, float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "within \\[0, 1\\]"):
                    synthesize_historical_opinion(
                        primary,
                        pooled=primary,
                        matched_base_positive_frequency=value,
                    )

        missing_base = synthesize_historical_opinion(
            primary,
            pooled=primary,
            matched_base_positive_frequency=None,
        )
        self.assertEqual(missing_base.status, "ABSTAIN_INSUFFICIENT_OR_UNRELIABLE_DATA")
        self.assertIn("MATCHED_BASE_POSITIVE_FREQUENCY_UNAVAILABLE", missing_base.reasons)

    def test_opinion_bootstrap_orders_analogs_by_session(self):
        diagnostics = CovarianceDiagnostics(200, 2, 100.0, 3.0, 1.8, 0.9, 1e-6)
        chronological = tuple(
            {
                "symbol": "MSFT",
                "session": f"2024-02-{index + 1:02d}",
                "return_5": value,
                "iv_change_5": -value,
            }
            for index, value in enumerate(
                (-0.07, -0.04, -0.02, 0.01, 0.03, 0.06, 0.10, 0.14, 0.19, 0.25)
            )
        )

        def result(analogs):
            return AnalogResult(
                "v2",
                "READY",
                "2025-01-02",
                "MSFT",
                (),
                {"prior_same_ticker": 200, "regime_eligible": 20},
                diagnostics,
                3.0,
                0.8,
                analogs,
                tuple(row["session"] for row in analogs),
            )

        distance_ordered = result(tuple(reversed(chronological)))
        session_ordered = result(chronological)
        distance_opinion = synthesize_historical_opinion(
            distance_ordered,
            pooled=distance_ordered,
            matched_base_positive_frequency=0.50,
        )
        session_opinion = synthesize_historical_opinion(
            session_ordered,
            pooled=session_ordered,
            matched_base_positive_frequency=0.50,
        )

        self.assertEqual(
            distance_opinion.return_interval_90,
            session_opinion.return_interval_90,
        )
