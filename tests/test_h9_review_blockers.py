"""Regression tests for the H9 independent-review blockers (B1, B2, B4, C5, C6).

All offline, synthetic fixtures. No network, no cache reads.
"""
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

import pandas as pd

import config
from data import thetadata_adapter as ta
from options_researcher import h9_study as st
from options_researcher.h9_events import H9Event
from research.hashing import sha256_file
from tools import h9_run_study as cli


def chain(rows):
    cols = ["expiration", "strike", "right", "bid", "ask", "open_interest",
            "iv", "delta", "gamma", "theta", "vega"]
    return pd.DataFrame(
        [{"expiration": e, "strike": k, "right": r, "bid": b, "ask": a,
          "open_interest": oi, "iv": 0.5, "delta": d, "gamma": 0.0,
          "theta": 0.0, "vega": 0.0} for (e, k, r, b, a, oi, d) in rows],
        columns=cols)


def ev(symbol="MSFT", occurred=date(2026, 4, 29),
       t_pre="2026-04-29", t_dec="2026-04-30", t_entry="2026-05-01",
       exclusion=None):
    return H9Event(symbol=symbol, occurred_date=occurred,
                   accepted_utc=datetime(2026, 4, 29, 20, 3, tzinfo=timezone.utc),
                   t_pre=t_pre, t_dec=t_dec, t_entry=t_entry, exclusion=exclusion)


# --------------------------------------------------------------------------
# B1 -- chain reads are cache-ONLY; a miss NEVER constructs the paid client.
# --------------------------------------------------------------------------
class CacheOnlyChainTests(unittest.TestCase):
    def test_load_cached_chain_raises_on_miss_and_never_fetches(self):
        # Patch the client constructor to blow up if it is ever touched. A
        # genuine cache miss must raise FileNotFoundError (cache-only), NOT the
        # sentinel -- proving no fetch/spend was attempted.
        def _boom():
            raise AssertionError("H9 cache-only path constructed the ThetaData client")

        with mock.patch.object(ta, "_client", _boom):
            with self.assertRaises(FileNotFoundError):
                ta.load_cached_chain("ZZZQTESTNOCACHE", "2022-06-15", allow_oos=True)

    def test_census_codes_missing_chain_without_fetching(self):
        from options_researcher import h9_census as census

        def _boom():
            raise AssertionError("census constructed the ThetaData client on a miss")

        closes = pd.Series({"2026-04-29": 100.0, "2026-04-30": 103.0})
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(ta, "_client", _boom), \
                 mock.patch.object(census, "_closes", return_value=closes):
                # entry chain for this synthetic name is absent from the cache
                res = census.run_census([ev()], chain_dir=Path(td))
        self.assertEqual(res.reasons["missing_entry_chain"], 1)
        self.assertEqual(res.eligible_count, 0)

    def test_study_provider_is_cache_only(self):
        # The run's provider is data.thetadata_adapter.load_cached_chain -- the
        # non-fetching reader. Assert the CLI wires that one, not get_eod_chain.
        import inspect
        src = inspect.getsource(cli._run_study)
        self.assertIn("load_cached_chain", src)
        self.assertNotIn("get_eod_chain", src)


# --------------------------------------------------------------------------
# B2 -- next-report exit set is the CLASSIFIED QUARTERLY set only.
# --------------------------------------------------------------------------
class QuarterlyOnlyNextReportTests(unittest.TestCase):
    def test_business_update_never_becomes_next_report(self):
        entry = ev(occurred=date(2026, 4, 29))                       # quarterly
        biz = ev(occurred=date(2026, 5, 4), t_pre=None, t_dec=None,
                 t_entry=None, exclusion="non_earnings_event")       # 8-K, excluded
        next_q = ev(occurred=date(2026, 7, 29))                      # quarterly
        mapping = cli.next_report_map([entry, biz, next_q])
        self.assertEqual(mapping["MSFT"], ["2026-04-29", "2026-07-29"])
        self.assertNotIn("2026-05-04", mapping["MSFT"])

    def test_non_quarterly_one_session_after_entry_does_not_fail_loud(self):
        # A business_update dated one session after entry would, under the old
        # all-events map, be picked as the next report and trip the
        # contaminated-geometry ValueError. With the quarterly-only map the
        # real next report is far away and the run proceeds.
        entry = ev(occurred=date(2026, 4, 29))
        biz = ev(occurred=date(2026, 5, 4), t_pre=None, t_dec=None,
                 t_entry=None, exclusion="non_earnings_event")
        next_q = ev(occurred=date(2026, 7, 29))
        mapping = cli.next_report_map([entry, biz, next_q])
        nxt = sorted(d for d in mapping["MSFT"]
                     if d > entry.occurred_date.isoformat())
        self.assertEqual(nxt[0], "2026-07-29")  # not the 05-04 business update

        def provider(symbol, iso):
            if iso == "2026-05-01":
                return chain([("2026-06-19", 430.0, "C", 4.8, 5.0, 500, 0.32)])
            return chain([("2026-06-19", 430.0, "C", 4.0, 4.2, 500, 0.32)])

        # Must NOT raise the near-report fail-loud, and produces a trade.
        trade = st.simulate_trade(entry, provider, next_report_iso=nxt[0])
        self.assertIsNotNone(trade)
        self.assertNotEqual(trade["exit_reason"], "unresolved_data_gap")

    def test_contaminated_map_would_have_failed_loud(self):
        # Documents the bug B2 fixes: feeding the 05-04 date directly raises.
        with self.assertRaises(ValueError):
            st.simulate_trade(
                ev(),
                lambda s, i: chain([("2026-06-19", 430.0, "C", 4.8, 5.0, 500, 0.32)]),
                next_report_iso="2026-05-04")


# --------------------------------------------------------------------------
# B4 -- SPEC_PATH sourced from config; the configured spec exists and hashes.
# --------------------------------------------------------------------------
class SpecPathTests(unittest.TestCase):
    def test_config_spec_path_exists_and_hashes(self):
        # Stored as a repo-relative string so it stays JSON-serializable inside
        # config_hash provenance; the file it names must exist and hash.
        self.assertIsInstance(config.H9_SPEC_PATH, str)
        spec = Path(config.H9_SPEC_PATH)
        self.assertTrue(spec.exists(), f"H9 spec missing at {spec}")
        digest = sha256_file(spec)
        self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_cli_spec_path_is_the_config_one(self):
        self.assertEqual(cli.SPEC_PATH, Path(config.H9_SPEC_PATH))


# --------------------------------------------------------------------------
# C5 -- prereg gate binds the registered spec sha256 to the on-disk spec.
# --------------------------------------------------------------------------
class PreregSpecShaBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        (self.base / "facts.log").write_text("")
        self.addCleanup(self.tmp.cleanup)

    def fact(self, text):
        with open(self.base / "facts.log", "a") as f:
            f.write(f"2026-07-16T00:00:00+00:00\t{text}\n")

    def test_matching_spec_sha_clears(self):
        good = sha256_file(Path(config.H9_SPEC_PATH))
        self.fact(f"H9_REGISTERED 2026-07-XX: frozen spec_sha256={good} at commit def")
        self.assertIsNone(cli.h9_prereg_gate(base_dir=self.base))

    def test_mismatched_spec_sha_refuses(self):
        wrong = "0" * 64
        self.fact(f"H9_REGISTERED 2026-07-XX: frozen spec_sha256={wrong} at commit def")
        msg = cli.h9_prereg_gate(base_dir=self.base)
        self.assertIsNotNone(msg)
        self.assertIn("spec drift", msg)

    def test_token_less_fact_stays_backward_compatible(self):
        # A registration fact with no spec_sha256 token still clears on
        # existence (the loose legacy form).
        self.fact("H9_REGISTERED 2026-07-XX: spec sha256 abc at commit def")
        self.assertIsNone(cli.h9_prereg_gate(base_dir=self.base))


# --------------------------------------------------------------------------
# C6 -- a high unresolved-gap fraction forces INSUFFICIENT_SAMPLE.
# --------------------------------------------------------------------------
class GapRateGateTests(unittest.TestCase):
    def _trade(self, pnl, entry_date, symbol="MSFT"):
        return {"symbol": symbol, "entry_date": entry_date,
                "capital_at_risk": 300.0, "pnl": pnl,
                "worthless_quote_exit": False}

    def test_high_gap_fraction_forces_insufficient(self):
        # 3 complete + 3 gap = 50% gap rate, well over the 10% ceiling.
        dates = ["2021-01-04", "2021-01-11", "2021-01-19"]
        trades = [self._trade(-100.0, d) for d in dates]
        trades += [self._trade(None, d) for d in dates]
        board = st.adjudicate(trades)
        self.assertTrue(board["gap_gate_forced_insufficient"])
        self.assertEqual(board["h9_outcome"], "INSUFFICIENT_SAMPLE")
        self.assertGreater(board["unresolved_gap_fraction"],
                           config.H9_MAX_UNRESOLVED_GAP_FRACTION)

    def test_low_gap_fraction_does_not_force(self):
        # 1 gap out of 20 = 5% < 10% ceiling: the gate does not intervene.
        trades = [self._trade(10.0 if i % 2 else -10.0,
                              f"2021-{1 + i % 12:02d}-05") for i in range(19)]
        trades.append(self._trade(None, "2021-06-05"))
        board = st.adjudicate(trades)
        self.assertFalse(board["gap_gate_forced_insufficient"])
        self.assertLessEqual(board["unresolved_gap_fraction"],
                             config.H9_MAX_UNRESOLVED_GAP_FRACTION)


if __name__ == "__main__":
    unittest.main()
