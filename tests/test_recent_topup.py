"""tests/test_recent_topup.py -- offline TDD coverage for data/recent_topup.py.

Pure functions only (no network): topup_days picks which recent trading days
to fetch, latest_cached_date reads the on-disk chain cache. The blind-cache
pull itself is orchestrator-only (like data/underlying_closes.fetch_underlying_eod)
and is exercised live by the controlling session, never by tests.
"""
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from data import recent_topup


def _row(strike, right, bid, ask, oi, iv, delta, *, expiration="2026-08-21"):
    return {"expiration": expiration, "strike": strike, "right": right,
            "bid": bid, "ask": ask, "open_interest": oi, "iv": iv,
            "delta": delta, "gamma": 0.01, "theta": -0.05, "vega": 0.1}


class TopupDaysTests(unittest.TestCase):
    def _fake_cal(self, _start, _end):
        # A fixed window spanning the 2026 July 4th holiday; the function under
        # test must do the endpoint filtering itself.
        return ["2026-06-30", "2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06"]

    def test_excludes_last_cached_boundary_and_today(self):
        days = recent_topup.topup_days(
            "2026-06-30", "2026-07-06", trading_days_fn=self._fake_cal)
        self.assertEqual(days, ["2026-07-01", "2026-07-02", "2026-07-03"])

    def test_empty_when_no_days_between(self):
        days = recent_topup.topup_days(
            "2026-07-03", "2026-07-06", trading_days_fn=self._fake_cal)
        self.assertEqual(days, [])

    def test_real_calendar_drops_holiday_and_today(self):
        # 2026-07-04 is Saturday -> observed Independence Day is Fri 2026-07-03,
        # market closed; today (2026-07-06) excluded because its EOD is not final.
        days = recent_topup.topup_days("2026-06-30", "2026-07-06")
        self.assertEqual(days, ["2026-07-01", "2026-07-02"])


class LatestCachedDateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _touch(self, symbol, date):
        (self.cache_dir / f"{symbol}_{date}.parquet").touch()

    def test_returns_min_of_per_symbol_max(self):
        # MSFT current to 07-02, AMZN lags at 07-01 -> cohort pulled from 07-01
        # so the lagging name is not left behind.
        self._touch("MSFT", "2026-06-30")
        self._touch("MSFT", "2026-07-02")
        self._touch("AMZN", "2026-07-01")
        got = recent_topup.latest_cached_date(
            ["MSFT", "AMZN"], cache_dir=self.cache_dir)
        self.assertEqual(got, "2026-07-01")

    def test_none_when_a_symbol_has_no_cache(self):
        self._touch("MSFT", "2026-07-02")
        got = recent_topup.latest_cached_date(
            ["MSFT", "AMZN"], cache_dir=self.cache_dir)
        self.assertIsNone(got)


class ScopeTests(unittest.TestCase):
    def test_core_scope_preserves_existing_four_name_default(self):
        self.assertEqual(
            recent_topup.scope_symbols("core"),
            ["MSFT", "AMZN", "VST", "CEG"],
        )

    def test_h7_scope_is_the_exact_forward_watch_universe(self):
        # IREN ACTIVATED 2026-07-15 (base chain cache built) -- now in the
        # active forward-watch scope. See IREN_ACTIVATION in facts.log.
        self.assertEqual(
            recent_topup.scope_symbols("h7"),
            [
                "CRWV", "TEM", "PLTR", "NOW", "SMCI", "NVDA",
                "AMD", "AVGO", "IREN", "VST", "CEG", "MSFT", "AMZN",
            ],
        )

    def test_unknown_scope_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unknown top-up scope"):
            recent_topup.scope_symbols("everything")


class RefreshClosesTests(unittest.TestCase):
    def test_refreshes_every_selected_symbol_and_logs_scope(self):
        calls = []
        with tempfile.TemporaryDirectory() as ledger_dir:
            result = recent_topup.refresh_closes(
                ["MSFT", "AMZN"],
                today="2026-07-29",
                ledger_dir=ledger_dir,
                fetch_fn=lambda symbol: calls.append(symbol) or f"{symbol}.parquet",
            )
            fact = (Path(ledger_dir) / "facts.log").read_text()
        self.assertEqual(calls, ["MSFT", "AMZN"])
        self.assertEqual(result, {"MSFT": "MSFT.parquet", "AMZN": "AMZN.parquet"})
        self.assertIn("Yahoo closes refresh", fact)
        self.assertIn("MSFT/AMZN", fact)


class AuditChainTests(unittest.TestCase):
    def test_clean_selectable_chain_passes(self):
        df = pd.DataFrame([
            _row(200, "C", 5.00, 5.20, 500, 0.30, 0.50),
            _row(200, "P", 4.80, 5.00, 400, 0.31, -0.50),
        ])
        result = recent_topup.audit_chain(df)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["block"], [])
        self.assertEqual(result["warn"], [])

    def test_zero_iv_on_selectable_contract_blocks(self):
        # A near-ATM, liquid contract with IV=0 is a genuine defect (unlike the
        # benign deep-ITM case below) -> BLOCK.
        df = pd.DataFrame([
            _row(200, "C", 5.00, 5.20, 500, 0.00, 0.50),
            _row(200, "P", 4.80, 5.00, 400, 0.31, -0.50),
        ])
        result = recent_topup.audit_chain(df)
        self.assertEqual(result["verdict"], "BLOCK")
        self.assertTrue(any("iv" in r.lower() for r in result["block"]))

    def test_deep_itm_zero_iv_is_warning_not_block(self):
        # |delta|=1 deep-ITM contract with IV=0 is a solver artifact the
        # strategy never selects -> warning, never a block.
        df = pd.DataFrame([
            _row(200, "C", 5.00, 5.20, 500, 0.30, 0.50),
            _row(50, "C", 150.0, 150.4, 800, 0.00, 1.00),
        ])
        result = recent_topup.audit_chain(df)
        self.assertEqual(result["verdict"], "PASS WITH WARNINGS")
        self.assertEqual(result["block"], [])
        self.assertTrue(result["warn"])


if __name__ == "__main__":
    unittest.main()
