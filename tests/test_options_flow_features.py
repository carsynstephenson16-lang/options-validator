"""Offline formula, baseline, and point-in-time feature tests."""

import json
import unittest
from pathlib import Path

import pandas as pd

from data.options_flow.aggregate import attach_prior_open_interest
from data.options_flow.normalize import normalize_open_interest, normalize_trade_quotes
from options_researcher.flow.features import build_flow_features
from options_researcher.flow.schema import build_session_record

FIXTURES = Path(__file__).parent / "fixtures" / "options_flow"


def _raw(name: str) -> pd.DataFrame:
    return pd.DataFrame(json.loads(line) for line in (FIXTURES / name).read_text().splitlines())


class FeatureTests(unittest.TestCase):
    def _capture(self, session: str):
        raw = _raw("trade_quote.jsonl")
        base = pd.Timestamp(f"{session}T13:30:00Z")
        raw["quote_timestamp"] = [base + pd.Timedelta(seconds=i) for i in range(4)]
        raw["trade_timestamp"] = raw["quote_timestamp"] + pd.Timedelta(milliseconds=100)
        trades = normalize_trade_quotes(
            raw,
            symbol="MSFT",
            session=session,
            acquired_at_utc="2025-01-03T00:00:00+00:00",
            source_version="fixture",
        )
        oi = normalize_open_interest(
            _raw("open_interest.jsonl"),
            symbol="MSFT",
            acquired_at_utc="2025-01-03T00:00:00+00:00",
            source_version="fixture",
        )
        return trades, oi

    def test_daily_formulas_and_directional_exclusion(self):
        trades, oi = self._capture("2025-01-02")
        out = build_flow_features(trades, oi, underlying_prices={"2025-01-02": 100.0})
        row = out.iloc[0]
        self.assertEqual(row["total_call_premium"], 10200.0)
        self.assertEqual(row["total_put_premium"], 8000.0)
        self.assertEqual(row["ask_call_premium"], 10000.0)
        self.assertEqual(row["bid_put_premium"], 2000.0)
        self.assertEqual(row["directional_net_premium"], 12000.0)
        self.assertEqual(row["sweep_count"], 0)
        self.assertEqual(row["baseline_status"], "SPARSE_BASELINE")
        self.assertEqual(
            row["direction_label"],
            "AGGRESSOR_SIGNED_NOT_CUSTOMER_OR_DEALER_INTENT",
        )
        self.assertEqual(row["short_dte_share"], 0.0)
        self.assertEqual(row["medium_dte_share"], 0.0)
        self.assertEqual(row["long_dte_share"], 1.0)
        self.assertAlmostEqual(row["atm_contract_share"], 30.0 / 51.0)
        self.assertEqual(row["moneyness_source"], "SESSION_PRICE_PROXY_OR_UNAVAILABLE")

    def test_open_interest_after_trade_session_raises(self):
        trades, oi = self._capture("2025-01-02")
        oi.loc[0, "oi_timestamp"] = pd.Timestamp("2025-01-03T11:30:00Z")

        with self.assertRaisesRegex(ValueError, "strictly prior"):
            attach_prior_open_interest(trades, oi)

    def test_same_session_prior_open_interest_joins_and_preserves_missing_rows(self):
        trades, oi = self._capture("2025-01-02")
        joined = attach_prior_open_interest(trades, oi.iloc[[0]])

        self.assertEqual(len(joined), len(trades))
        self.assertEqual(joined["prior_open_interest"].notna().sum(), 1)
        self.assertEqual(float(joined["prior_open_interest"].dropna().iloc[0]), 500.0)
        self.assertTrue(joined["prior_open_interest"].iloc[1:].isna().all())

    def test_volume_oi_ratio_uses_one_oi_value_for_repeated_contract_trades(self):
        trades, oi = self._capture("2025-01-02")
        repeated_contract_trades = pd.concat([trades.iloc[[0]]] * 3, ignore_index=True)
        contract_oi = oi.iloc[[0]]

        row = build_flow_features(repeated_contract_trades, contract_oi).iloc[0]

        self.assertEqual(row["unique_contracts"], 1)
        self.assertAlmostEqual(row["volume_oi_ratio"], 30.0 / 500.0)

    def test_prior_only_baseline_becomes_ready_after_minimum_history(self):
        frames = []
        oi_frames = []
        dates = pd.bdate_range("2025-01-02", periods=21)
        for day in dates:
            trades, oi = self._capture(day.date().isoformat())
            frames.append(trades)
            oi_frames.append(oi)
        out = build_flow_features(
            pd.concat(frames, ignore_index=True),
            pd.concat(oi_frames, ignore_index=True).drop_duplicates(
                ["symbol", "expiration", "strike", "right"]
            ),
            underlying_prices={day.date().isoformat(): 100.0 for day in dates},
        )
        self.assertEqual(out.iloc[0]["baseline_status"], "SPARSE_BASELINE")
        self.assertEqual(out.iloc[-1]["baseline_status"], "READY")
        self.assertTrue(pd.isna(out.iloc[0]["premium_spike_score"]))

    def test_strict_prior_underlying_quote_controls_moneyness(self):
        trades, oi = self._capture("2025-01-02")
        quotes = pd.DataFrame(
            {
                "symbol": ["MSFT", "MSFT"],
                "timestamp": [
                    "2025-01-02T13:29:59Z",
                    "2025-01-02T13:30:01.500Z",
                ],
                "bid": [99.0, 109.0],
                "ask": [101.0, 111.0],
            }
        )
        out = build_flow_features(trades, oi, underlying_quotes=quotes)
        row = out.iloc[0]
        self.assertEqual(row["moneyness_source"], "STRICT_PRIOR_UNDERLYING_QUOTE")
        self.assertEqual(row["moneyness_volume_coverage"], 1.0)
        self.assertGreater(row["deep_otm_contract_share"], 0.0)

    def test_complex_trade_is_excluded_from_gross_greek_exposure(self):
        trades, oi = self._capture("2025-01-02")
        trades["delta"] = [0.50, -0.50, 0.30, -0.90]
        trades["gamma"] = [0.02, 0.02, 0.01, 0.10]
        trades["vega"] = [0.10, 0.10, 0.05, 1.00]
        trades["contract_multiplier"] = 100.0
        trades["underlying_adv20_shares"] = 1_000_000.0
        trades["underlying_adv20_dollars"] = 100_000_000.0
        trades["gamma_unit_verified"] = True
        trades["vega_unit_verified"] = True
        quotes = pd.DataFrame(
            {
                "symbol": ["MSFT"],
                "timestamp": ["2025-01-02T13:29:59Z"],
                "bid": [99.0],
                "ask": [101.0],
            }
        )
        row = build_flow_features(
            trades,
            oi,
            underlying_quotes=quotes,
        ).iloc[0]
        expected_delta_shares = (0.50 * 10 + 0.50 * 20 + 0.30 * 1) * 100
        self.assertAlmostEqual(
            row["gross_delta_equiv_adv20"],
            expected_delta_shares / 1_000_000,
        )
        self.assertEqual(row["greek_volume_coverage"], 1.0)

    def test_nested_record_is_explicitly_display_only(self):
        trades, oi = self._capture("2025-01-02")
        row = (
            build_flow_features(
                trades,
                oi,
                underlying_prices={"2025-01-02": 100.0},
            )
            .iloc[0]
            .to_dict()
        )
        record = build_session_record(
            row,
            iv_context={"state": "IV_CONTEXT_UNKNOWN"},
            event_context={"state": "EVENT_CONTEXT_UNKNOWN"},
            data_quality={"verdict": "PASS WITH WARNINGS"},
            provenance={"source": "fixture"},
        )
        self.assertEqual(record["schema"], "options_flow_session_record_v2")
        self.assertEqual(record["authority"], "DISPLAY_ONLY_RESEARCH_NONCAUSAL")
        self.assertIn("optionality_features", record)
