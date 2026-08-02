"""Canonical options-flow analog panel assembly tests."""

import unittest

import numpy as np
import pandas as pd

from options_researcher.flow.analogs import AnalogConfig, match_historical_analogs
from options_researcher.flow.context import EVENT_KNOWN, EVENT_NONE, EVENT_UNKNOWN, EventContext
from options_researcher.flow.features import build_flow_features
from options_researcher.flow.panel import (
    ANALOG_REGIME_READY,
    ANALOG_REGIME_UNKNOWN,
    EVENT_TYPE_NONE,
    EVENT_TYPE_UNKNOWN,
    assemble_analog_panel,
    collapse_event_type,
)


def _daily_feature_output(sessions: pd.DatetimeIndex) -> pd.DataFrame:
    """Use the real flow-feature producer, not a hand-assembled feature panel."""
    trades = pd.DataFrame(
        {
            "symbol": "MSFT",
            "expiration": [
                (session + pd.Timedelta(days=45)).date().isoformat() for session in sessions
            ],
            "strike": 100.0,
            "right": "C",
            "trade_timestamp": [
                pd.Timestamp(f"{session.date().isoformat()}T15:00:00Z") for session in sessions
            ],
            "size": np.arange(10, 10 + len(sessions), dtype=float),
            "premium": np.arange(10, 10 + len(sessions), dtype=float) * 100.0,
            "prior_open_interest": 500.0,
            "side": "LIKELY_ASK_SIDE",
            "condition_class": "CONDITION_FLAG_ONLY",
            "proxy_directional_eligible": True,
            "explicit_directional_eligible": False,
            "explicit_aggressor_side": "UNKNOWN",
        }
    )
    return build_flow_features(
        trades,
        underlying_prices={session.date().isoformat(): 100.0 for session in sessions},
    )


def _histories(sessions: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    history_sessions = pd.bdate_range(sessions[0] - pd.offsets.BDay(20), sessions[-1])
    values = np.arange(len(history_sessions), dtype=float)
    atm30 = 0.20 + 0.0005 * values
    iv_history = pd.DataFrame(
        {
            "symbol": "MSFT",
            "session": history_sessions.strftime("%Y-%m-%d"),
            "atm30_iv": atm30,
            "atm60_iv": atm30 + 0.02,
            "put25_iv": atm30 + 0.04 + 0.01 * np.sin(values),
        }
    )
    log_returns = 0.01 * np.sin(values[1:]) + 0.002 * np.cos(2.0 * values[1:])
    closes = 100.0 * np.exp(np.r_[0.0, np.cumsum(log_returns)])
    close_history = pd.DataFrame(
        {
            "symbol": "MSFT",
            "session": history_sessions.strftime("%Y-%m-%d"),
            "close": closes,
        }
    )
    return iv_history, close_history


class AnalogPanelTests(unittest.TestCase):
    def test_event_type_collapse_handles_none_single_multi_and_unknown(self):
        self.assertEqual(
            collapse_event_type(EventContext(EVENT_NONE, (), (), "2025-01-02")),
            EVENT_TYPE_NONE,
        )
        self.assertEqual(
            collapse_event_type(EventContext(EVENT_KNOWN, ("earnings",), ("e1",), "2025-01-02")),
            "SINGLE:EARNINGS",
        )
        self.assertEqual(
            collapse_event_type(
                EventContext(
                    EVENT_KNOWN,
                    ("earnings", "dividend", "earnings"),
                    ("e1", "e2", "e3"),
                    "2025-01-02",
                )
            ),
            "MULTI:DIVIDEND|EARNINGS",
        )
        self.assertEqual(
            collapse_event_type(EventContext(EVENT_UNKNOWN, (), (), "2025-01-02")),
            EVENT_TYPE_UNKNOWN,
        )

    def test_end_to_end_assembly_produces_all_regime_fields_for_analog_engine(self):
        sessions = pd.bdate_range("2025-01-21", periods=30)
        features = _daily_feature_output(sessions)
        quality = features.loc[:, ["symbol", "session"]].assign(data_quality="PASS")
        iv_history, close_history = _histories(sessions)
        events = pd.DataFrame(
            columns=["symbol", "event_id", "event_type", "published_at", "effective_at"]
        )
        panel = assemble_analog_panel(
            features,
            data_quality=quality,
            iv_history=iv_history,
            close_history=close_history,
            events=events,
            trading_sessions=sessions.strftime("%Y-%m-%d"),
            event_coverage_complete=True,
            iv_history_window=8,
            rv_return_window=3,
            rv_tercile_history=8,
        )
        query = str(panel.iloc[-1]["session"])

        self.assertTrue(
            {
                "event_state",
                "event_type",
                "iv_state",
                "iv_percentile_252",
                "term_slope",
                "skew_z",
                "rv_tercile",
                "analog_regime_state",
            }.issubset(panel.columns)
        )
        self.assertEqual(panel.iloc[-1]["analog_regime_state"], ANALOG_REGIME_READY)
        result = match_historical_analogs(
            panel,
            query_session=query,
            symbol="MSFT",
            feature_columns=["log_total_contracts"],
            config=AnalogConfig(
                covariance_minimum=5,
                observations_per_feature=1,
                covariance_maximum=10,
                effective_rank_ratio=0.50,
                maximum_analogs=5,
                minimum_analogs=3,
                separation_sessions=1,
                similarity_quantile=1.0,
                metric_jaccard_minimum=0.0,
            ),
        )
        self.assertIn(result.status, {"READY", "ABSTAIN", "DESCRIPTIVE_ONLY"})

    def test_insufficient_regime_history_is_explicit_and_abstains(self):
        sessions = pd.bdate_range("2025-01-21", periods=8)
        features = _daily_feature_output(sessions)
        quality = features.loc[:, ["symbol", "session"]].assign(data_quality="PASS")
        iv_history, close_history = _histories(sessions)
        events = pd.DataFrame(
            columns=["symbol", "event_id", "event_type", "published_at", "effective_at"]
        )
        panel = assemble_analog_panel(
            features,
            data_quality=quality,
            iv_history=iv_history,
            close_history=close_history,
            events=events,
            trading_sessions=sessions.strftime("%Y-%m-%d"),
            event_coverage_complete=True,
            iv_history_window=50,
            rv_return_window=3,
            rv_tercile_history=50,
        )
        query = str(panel.iloc[-1]["session"])

        self.assertEqual(panel.iloc[-1]["analog_regime_state"], ANALOG_REGIME_UNKNOWN)
        result = match_historical_analogs(
            panel,
            query_session=query,
            symbol="MSFT",
            feature_columns=["log_total_contracts"],
            config=AnalogConfig(covariance_minimum=5, observations_per_feature=1),
        )
        self.assertEqual(result.status, "ABSTAIN")
        self.assertIn("ANALOG_REGIME_UNKNOWN", result.reasons)
