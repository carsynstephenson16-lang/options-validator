"""Point-in-time event and implied-volatility context tests."""

import unittest

import numpy as np
import pandas as pd

from options_researcher.flow.context import (
    EVENT_KNOWN,
    EVENT_NONE,
    IV_READY,
    IV_UNKNOWN,
    RV_READY,
    RV_UNKNOWN,
    build_daily_iv_snapshot,
    event_context_for_session,
    iv_context_for_session,
    realized_volatility_context_for_session,
)


class FlowContextTests(unittest.TestCase):
    def test_future_sec_filing_cannot_retroactively_create_known_event(self):
        sessions = pd.bdate_range("2025-01-02", periods=8).strftime("%Y-%m-%d").tolist()
        events = pd.DataFrame(
            {
                "symbol": ["MSFT"],
                "event_id": ["sec-8k-1"],
                "event_type": ["EARNINGS"],
                "published_at": ["2025-01-07T12:00:00Z"],
                "effective_at": ["2025-01-06T21:00:00Z"],
            }
        )
        unknown_at_query = event_context_for_session(
            symbol="MSFT",
            session="2025-01-02",
            events=events,
            trading_sessions=sessions,
            coverage_complete=True,
        )
        self.assertEqual(unknown_at_query.state, EVENT_NONE)
        known = events.copy()
        known["published_at"] = "2025-01-01T12:00:00Z"
        known_at_query = event_context_for_session(
            symbol="MSFT",
            session="2025-01-02",
            events=known,
            trading_sessions=sessions,
            coverage_complete=True,
        )
        self.assertEqual(known_at_query.state, EVENT_KNOWN)

    def test_after_close_publication_is_not_known_at_session_cutoff(self):
        sessions = pd.bdate_range("2025-01-02", periods=8).strftime("%Y-%m-%d").tolist()
        events = pd.DataFrame(
            {
                "symbol": ["MSFT"],
                "event_id": ["after-close"],
                "event_type": ["EARNINGS"],
                "published_at": ["2025-01-02T22:00:00Z"],
                "effective_at": ["2025-01-03T00:00:00Z"],
            }
        )
        result = event_context_for_session(
            symbol="MSFT",
            session="2025-01-02",
            events=events,
            trading_sessions=sessions,
            coverage_complete=True,
        )
        self.assertEqual(result.state, EVENT_NONE)

    def test_publication_exactly_at_cutoff_is_known(self):
        sessions = pd.bdate_range("2025-01-02", periods=8).strftime("%Y-%m-%d").tolist()
        events = pd.DataFrame(
            {
                "symbol": ["MSFT"],
                "event_id": ["cutoff-boundary"],
                "event_type": ["EARNINGS"],
                "published_at": ["2025-01-02T21:00:00Z"],
                "effective_at": ["2025-01-02T22:00:00Z"],
            }
        )
        result = event_context_for_session(
            symbol="MSFT",
            session="2025-01-02",
            events=events,
            trading_sessions=sessions,
            coverage_complete=True,
        )
        self.assertEqual(result.state, EVENT_KNOWN)

    def test_dst_crossing_session_uses_new_york_cutoff(self):
        sessions = ["2025-03-07", "2025-03-10", "2025-03-11", "2025-03-12"]
        events = pd.DataFrame(
            {
                "symbol": ["MSFT"],
                "event_id": ["after-edt-cutoff"],
                "event_type": ["EARNINGS"],
                "published_at": ["2025-03-10T20:30:00Z"],
                "effective_at": ["2025-03-10T21:00:00Z"],
            }
        )
        result = event_context_for_session(
            symbol="MSFT",
            session="2025-03-10",
            events=events,
            trading_sessions=sessions,
            coverage_complete=True,
        )
        self.assertEqual(result.state, EVENT_NONE)

    def test_total_variance_interpolation_and_no_extrapolation(self):
        rows = []
        for dte, call_iv, put_iv in ((20, 0.20, 0.24), (40, 0.30, 0.36), (70, 0.35, 0.41)):
            expiration = (pd.Timestamp("2025-01-02") + pd.Timedelta(days=dte)).date()
            rows.extend(
                [
                    {
                        "expiration": expiration,
                        "dte": dte,
                        "right": "C",
                        "delta": 0.50,
                        "iv": call_iv,
                        "bid": 1.0,
                        "ask": 1.1,
                    },
                    {
                        "expiration": expiration,
                        "dte": dte,
                        "right": "C",
                        "delta": 0.40,
                        "iv": call_iv + 0.01,
                        "bid": 0.9,
                        "ask": 1.0,
                    },
                    {
                        "expiration": expiration,
                        "dte": dte,
                        "right": "P",
                        "delta": -0.25,
                        "iv": put_iv,
                        "bid": 1.0,
                        "ask": 1.1,
                    },
                    {
                        "expiration": expiration,
                        "dte": dte,
                        "right": "P",
                        "delta": -0.35,
                        "iv": put_iv + 0.01,
                        "bid": 0.9,
                        "ask": 1.0,
                    },
                ]
            )
        snapshot = build_daily_iv_snapshot(pd.DataFrame(rows), session="2025-01-02")
        self.assertTrue(np.isfinite(snapshot["atm30_iv"]))
        self.assertTrue(np.isfinite(snapshot["atm60_iv"]))
        self.assertGreater(snapshot["put25_iv"], snapshot["atm30_iv"])
        no_bracket = build_daily_iv_snapshot(
            pd.DataFrame(rows).loc[lambda frame: frame["dte"] >= 40],
            session="2025-01-02",
        )
        self.assertTrue(np.isnan(no_bracket["atm30_iv"]))

    def test_iv_context_is_strictly_previous_close_and_requires_history(self):
        sessions = pd.bdate_range("2023-01-02", periods=254)
        atm30 = np.linspace(0.20, 0.40, len(sessions))
        history = pd.DataFrame(
            {
                "session": sessions.strftime("%Y-%m-%d"),
                "atm30_iv": atm30,
                "atm60_iv": np.linspace(0.22, 0.42, len(sessions)),
                "put25_iv": atm30 + 0.04 + 0.01 * np.sin(np.arange(len(sessions))),
            }
        )
        query = (sessions[-1] + pd.offsets.BDay(1)).date().isoformat()
        ready = iv_context_for_session(session=query, history=history)
        self.assertEqual(ready.state, IV_READY)
        self.assertEqual(ready.source_session, sessions[-1].date().isoformat())
        sparse = iv_context_for_session(
            session=query,
            history=history.tail(100),
        )
        self.assertEqual(sparse.state, IV_UNKNOWN)

    def test_skew_z_excludes_its_source_observation_from_prior_parameters(self):
        sessions = pd.bdate_range("2025-01-02", periods=7)
        skew = np.array((0.01, 0.02, 0.03, 0.04, 0.06, 0.09, 0.15))
        history = pd.DataFrame(
            {
                "session": sessions.strftime("%Y-%m-%d"),
                "atm30_iv": 0.20,
                "atm60_iv": 0.23,
                "put25_iv": 0.20 + skew,
            }
        )
        query = (sessions[-1] + pd.offsets.BDay(1)).date().isoformat()

        result = iv_context_for_session(session=query, history=history, minimum_history=5)

        reference = skew[-5:-1]
        expected = (skew[-1] - reference.mean()) / reference.std(ddof=1)
        self.assertEqual(result.state, IV_READY)
        self.assertAlmostEqual(result.skew_z, expected, places=12)
        self.assertEqual(result.source_session, sessions[-1].date().isoformat())
        future = pd.concat(
            [
                history,
                pd.DataFrame(
                    {
                        "session": [query],
                        "atm30_iv": [0.20],
                        "atm60_iv": [0.23],
                        "put25_iv": [4.00],
                    }
                ),
            ],
            ignore_index=True,
        )
        unchanged = iv_context_for_session(session=query, history=future, minimum_history=5)
        self.assertAlmostEqual(unchanged.skew_z, result.skew_z, places=12)
        sparse = iv_context_for_session(session=query, history=history.tail(4), minimum_history=5)
        self.assertEqual(sparse.state, IV_UNKNOWN)

    def test_realized_volatility_tercile_is_prior_only_and_abstains_when_sparse(self):
        sessions = pd.bdate_range("2025-01-02", periods=18)
        returns = np.array(
            (
                0.01,
                -0.02,
                0.03,
                -0.01,
                0.02,
                0.04,
                -0.03,
                0.01,
                0.02,
                -0.04,
                0.05,
                -0.01,
                0.03,
                -0.02,
                0.06,
                -0.05,
                0.04,
            )
        )
        closes = 100.0 * np.exp(np.r_[0.0, returns])
        history = pd.DataFrame({"session": sessions.strftime("%Y-%m-%d"), "close": closes})
        query = (sessions[-1] + pd.offsets.BDay(1)).date().isoformat()

        result = realized_volatility_context_for_session(
            session=query,
            history=history,
            return_window=3,
            tercile_history=5,
        )

        log_returns = np.diff(np.log(closes))
        expected_rv = np.std(log_returns[-3:], ddof=1) * np.sqrt(252.0)
        previous = np.array(
            [
                np.std(log_returns[end - 3 : end], ddof=1) * np.sqrt(252.0)
                for end in range(3, len(closes) - 1)
            ]
        )[-5:]
        lower, upper = np.quantile(previous, (1 / 3, 2 / 3))
        expected_tercile = 1 if expected_rv <= lower else (2 if expected_rv <= upper else 3)
        self.assertEqual(result.state, RV_READY)
        self.assertAlmostEqual(result.realized_volatility_21, expected_rv, places=12)
        self.assertEqual(result.rv_tercile, expected_tercile)
        self.assertEqual(result.observations, 5)
        future = pd.concat(
            [
                history,
                pd.DataFrame({"session": [query], "close": [1_000_000.0]}),
            ],
            ignore_index=True,
        )
        unchanged = realized_volatility_context_for_session(
            session=query,
            history=future,
            return_window=3,
            tercile_history=5,
        )
        self.assertAlmostEqual(unchanged.realized_volatility_21, result.realized_volatility_21)
        self.assertEqual(unchanged.rv_tercile, result.rv_tercile)
        sparse = realized_volatility_context_for_session(
            session=query,
            history=history.tail(9),
            return_window=3,
            tercile_history=5,
        )
        self.assertEqual(sparse.state, RV_UNKNOWN)
