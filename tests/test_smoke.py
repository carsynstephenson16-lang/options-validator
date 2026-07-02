"""tests/test_smoke.py -- offline TDD coverage for smoke_test.py.

No network: get_eod_chain is monkeypatched (module attribute assignment with
try/finally restore, matching tests/test_core.py) to return a synthetic chain
built to the same CHAIN_COLUMNS schema thetadata_adapter enforces.
"""
import tempfile
import unittest

import pandas as pd

import config
import smoke_test
from research import facts


def _valid_chain():
    """Synthetic chain covering every summarize_chain bucket:
    - put inside the 0.25-0.35 |delta| candidate short-put band (liquid)
    - put outside that band (liquid)
    - a call
    - an illiquid row (open_interest below config.MIN_OPEN_INTEREST) that is
      ALSO inside the delta band -- candidate_short_puts is delta-only, so
      this row must count there even though it fails passes_liquidity.
    Fixture shape copied from tests/test_core.py ChainCacheTests._valid_chain.
    """
    return pd.DataFrame([
        {
            # candidate short put: |delta| = 0.30, inside [0.25, 0.35]
            "expiration": "2022-02-18", "strike": 390.0, "right": "P",
            "bid": 1.00, "ask": 1.05, "open_interest": 500,
            "iv": 0.25, "delta": -0.30, "gamma": 0.02, "theta": -0.04, "vega": 0.12,
        },
        {
            # put outside the candidate band: |delta| = 0.10 (liquid: tight
            # spread, well within config.MAX_SPREAD_PCT)
            "expiration": "2022-02-18", "strike": 410.0, "right": "P",
            "bid": 0.95, "ask": 1.00, "open_interest": 500,
            "iv": 0.22, "delta": -0.10, "gamma": 0.01, "theta": -0.02, "vega": 0.08,
        },
        {
            # a call -- must not be counted as a candidate short put
            "expiration": "2022-02-18", "strike": 400.0, "right": "C",
            "bid": 1.20, "ask": 1.25, "open_interest": 500,
            "iv": 0.24, "delta": 0.30, "gamma": 0.02, "theta": -0.03, "vega": 0.11,
        },
        {
            # illiquid: open_interest below config.MIN_OPEN_INTEREST
            "expiration": "2022-02-18", "strike": 380.0, "right": "P",
            "bid": 0.20, "ask": 0.25, "open_interest": config.MIN_OPEN_INTEREST - 1,
            "iv": 0.30, "delta": -0.32, "gamma": 0.03, "theta": -0.05, "vega": 0.15,
        },
    ])


class SummarizeChainTests(unittest.TestCase):
    def test_returns_exact_expected_counts_for_fixture(self):
        summary = smoke_test.summarize_chain(_valid_chain())

        self.assertEqual(summary, {
            "rows": 4,
            "expirations": 1,
            "puts": 3,
            "calls": 1,
            "liquid_rows": 3,
            "candidate_short_puts": 2,
        })


class SmokeTestDateTests(unittest.TestCase):
    def test_smoke_test_date_is_in_sample(self):
        self.assertLessEqual(smoke_test.SMOKE_TEST_DATE, config.IN_SAMPLE_END)


class MainTests(unittest.TestCase):
    def test_main_appends_one_audit_fact_with_symbol_and_rows(self):
        old_fetch = smoke_test.get_eod_chain
        fixture = _valid_chain()

        def fake_get_eod_chain(symbol, date):
            return fixture

        smoke_test.get_eod_chain = fake_get_eod_chain
        try:
            with tempfile.TemporaryDirectory() as tmp:
                smoke_test.main(ledger_dir=tmp)

                lines = facts.read_facts(tmp)
                self.assertEqual(len(lines), 1)
                for token in ("SMOKE_TEST", config.UNIVERSE[0], "rows="):
                    self.assertIn(token, lines[0])
        finally:
            smoke_test.get_eod_chain = old_fetch

    def test_main_refuses_a_date_after_in_sample_end(self):
        old_date = smoke_test.SMOKE_TEST_DATE
        smoke_test.SMOKE_TEST_DATE = "2023-01-01"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):
                    smoke_test.main(ledger_dir=tmp)
        finally:
            smoke_test.SMOKE_TEST_DATE = old_date


if __name__ == "__main__":
    unittest.main()
