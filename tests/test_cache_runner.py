"""tests/test_cache_runner.py -- offline TDD coverage for data/cache_runner.py.

No network: get_eod_chain / blind_cache_chain are monkeypatched as module
attributes on cache_runner (module-attribute assignment with try/finally
restore -- the established pattern, see tests/test_blind_cache.py and
tests/test_smoke.py). CACHE_DIR is redirected via thetadata_adapter so
cache_runner._cache_path (the same function object, reading the same module
global at call time) resolves under a tempdir.
"""
import json
import tempfile
import unittest
from pathlib import Path

import config
from data import cache_runner, thetadata_adapter
from research import facts


class TradingDaysTests(unittest.TestCase):
    def test_excludes_holiday_and_includes_both_endpoints(self):
        days = cache_runner.trading_days("2022-12-27", "2023-01-04")

        self.assertEqual(days, [
            "2022-12-27", "2022-12-28", "2022-12-29", "2022-12-30",
            "2023-01-03", "2023-01-04",
        ])

    def test_endpoints_are_inclusive_when_both_are_trading_days(self):
        days = cache_runner.trading_days("2023-01-03", "2023-01-04")

        self.assertEqual(days[0], "2023-01-03")
        self.assertEqual(days[-1], "2023-01-04")

    def test_returns_plain_iso_strings(self):
        days = cache_runner.trading_days("2023-01-03", "2023-01-04")

        for d in days:
            self.assertIsInstance(d, str)
            self.assertRegex(d, r"^\d{4}-\d{2}-\d{2}$")


class _CacheRunnerTestCase(unittest.TestCase):
    """Shared tempdir/CACHE_DIR/patch-restore scaffolding."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self._old_cache_dir = thetadata_adapter.CACHE_DIR
        thetadata_adapter.CACHE_DIR = tmp / "chains"
        thetadata_adapter.CACHE_DIR.mkdir(parents=True)
        self.ledger_dir = str(tmp / "ledger")

        self._old_get_eod_chain = cache_runner.get_eod_chain
        self._old_blind_cache_chain = cache_runner.blind_cache_chain
        self._old_trading_days = cache_runner.trading_days

    def tearDown(self):
        cache_runner.get_eod_chain = self._old_get_eod_chain
        cache_runner.blind_cache_chain = self._old_blind_cache_chain
        cache_runner.trading_days = self._old_trading_days
        thetadata_adapter.CACHE_DIR = self._old_cache_dir
        self._tmp.cleanup()

    def _touch_cache_file(self, symbol, day):
        """Create an existing cache file so _cache_path(...).exists() is True.
        A plain touch is enough -- cache_runner only ever calls .exists()."""
        path = thetadata_adapter._cache_path(symbol, day)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()


class CacheInSampleTests(_CacheRunnerTestCase):
    def test_fetches_missing_skips_cached_and_returns_exact_counts(self):
        days = ["2022-12-28", "2022-12-29", "2022-12-30"]
        symbols = ["SPY", "QQQ"]
        cache_runner.trading_days = lambda start, end: days
        self._touch_cache_file("SPY", "2022-12-28")  # 1 of 6 tasks pre-cached

        calls = []

        def fake_get_eod_chain(symbol, date):
            calls.append((symbol, date))

        cache_runner.get_eod_chain = fake_get_eod_chain

        result = cache_runner.cache_in_sample(symbols, ledger_dir=self.ledger_dir)

        self.assertEqual(len(calls), 5)
        self.assertNotIn(("SPY", "2022-12-28"), calls)
        self.assertEqual(result, {
            "fetched": 5,
            "repaired": 0,
            "verified": 0,
            "skipped_cached": 1,
            "gaps": 0,
            "total_days": 3,
            "symbols": 2,
        })

    def test_gap_runtime_error_is_logged_as_a_fact_and_counted_not_raised(self):
        days = ["2022-12-28"]
        symbols = ["SPY"]
        cache_runner.trading_days = lambda start, end: days

        def fake_get_eod_chain(symbol, date):
            raise RuntimeError(
                f"ThetaData eod returned no rows for {symbol} @ {date}."
            )

        cache_runner.get_eod_chain = fake_get_eod_chain

        result = cache_runner.cache_in_sample(symbols, ledger_dir=self.ledger_dir)

        self.assertEqual(result, {
            "fetched": 0,
            "repaired": 0,
            "verified": 0,
            "skipped_cached": 0,
            "gaps": 1,
            "total_days": 1,
            "symbols": 1,
        })
        lines = facts.read_facts(self.ledger_dir)
        self.assertEqual(len(lines), 1)
        for token in ("CACHE_GAP", "symbol=SPY", "date=2022-12-28",
                      "reason=empty_fetch"):
            self.assertIn(token, lines[0])

    def test_unrelated_runtime_error_propagates(self):
        cache_runner.trading_days = lambda start, end: ["2022-12-28"]

        def fake_get_eod_chain(symbol, date):
            raise RuntimeError("boom")

        cache_runner.get_eod_chain = fake_get_eod_chain

        with self.assertRaises(RuntimeError):
            cache_runner.cache_in_sample(["SPY"], ledger_dir=self.ledger_dir)

        self.assertEqual(facts.read_facts(self.ledger_dir), [])

    def test_unrelated_value_error_is_not_swallowed(self):
        """A non-RuntimeError exception must never be caught as a gap."""
        cache_runner.trading_days = lambda start, end: ["2022-12-28"]

        def fake_get_eod_chain(symbol, date):
            raise ValueError("not a gap")

        cache_runner.get_eod_chain = fake_get_eod_chain

        with self.assertRaises(ValueError):
            cache_runner.cache_in_sample(["SPY"], ledger_dir=self.ledger_dir)

    def test_defaults_symbols_to_config_universe(self):
        cache_runner.trading_days = lambda start, end: ["2022-12-28"]
        calls = []
        cache_runner.get_eod_chain = lambda symbol, date: calls.append(symbol)

        result = cache_runner.cache_in_sample(ledger_dir=self.ledger_dir)

        self.assertEqual(sorted(calls), sorted(config.UNIVERSE))
        self.assertEqual(result["symbols"], len(config.UNIVERSE))

    def test_uses_backtest_start_and_in_sample_end_as_the_window(self):
        seen = {}

        def fake_trading_days(start, end):
            seen["start"] = start
            seen["end"] = end
            return []

        cache_runner.trading_days = fake_trading_days
        cache_runner.cache_in_sample(["SPY"], ledger_dir=self.ledger_dir)

        self.assertEqual(seen["start"], config.BACKTEST_START)
        self.assertEqual(seen["end"], config.IN_SAMPLE_END)


class CacheOosBlindTests(_CacheRunnerTestCase):
    def test_fetches_missing_and_verifies_cached_with_exact_counts(self):
        days = ["2023-01-03", "2023-01-04"]
        symbols = ["SPY", "QQQ"]
        cache_runner.trading_days = lambda start, end: days
        self._touch_cache_file("QQQ", "2023-01-03")  # 1 of 4 tasks pre-cached

        calls = []

        def fake_blind_cache_chain(symbol, date, *, ledger_dir="ledger"):
            calls.append((symbol, date, ledger_dir))
            status = (
                "VERIFIED_NOOP"
                if thetadata_adapter._cache_path(symbol, date).exists()
                else "FETCHED_ATTESTED"
            )
            return {
                "symbol": symbol,
                "date": date,
                "attestation_status": status,
            }

        cache_runner.blind_cache_chain = fake_blind_cache_chain

        result = cache_runner.cache_oos_blind(symbols, ledger_dir=self.ledger_dir)

        self.assertEqual(len(calls), 4)
        self.assertIn(("QQQ", "2023-01-03", self.ledger_dir), calls)
        for call in calls:
            self.assertEqual(call[2], self.ledger_dir)
        self.assertEqual(result, {
            "fetched": 3,
            "repaired": 0,
            "verified": 1,
            "skipped_cached": 0,
            "gaps": 0,
            "total_days": 2,
            "symbols": 2,
        })

    def test_never_calls_get_eod_chain(self):
        cache_runner.trading_days = lambda start, end: ["2023-01-03"]
        cache_runner.blind_cache_chain = (
            lambda symbol, date, *, ledger_dir="ledger": {"ok": True}
        )

        def raiser(symbol, date):
            raise AssertionError(
                "cache_oos_blind must never call get_eod_chain"
            )

        cache_runner.get_eod_chain = raiser

        cache_runner.cache_oos_blind(["SPY"], ledger_dir=self.ledger_dir)
        # no assertion error raised => get_eod_chain was never invoked

    def test_existing_cache_file_is_verified_by_blind_cache_chain(self):
        cache_runner.trading_days = lambda start, end: ["2023-01-03"]
        self._touch_cache_file("SPY", "2023-01-03")

        calls = []

        def verifier(symbol, date, *, ledger_dir="ledger"):
            calls.append((symbol, date))
            return {"attestation_status": "VERIFIED_NOOP"}

        cache_runner.blind_cache_chain = verifier

        result = cache_runner.cache_oos_blind(["SPY"], ledger_dir=self.ledger_dir)

        self.assertEqual(calls, [("SPY", "2023-01-03")])
        self.assertEqual(result["verified"], 1)
        self.assertEqual(result["skipped_cached"], 0)
        self.assertEqual(result["fetched"], 0)

    def test_gap_runtime_error_is_logged_as_a_fact_and_counted_not_raised(self):
        cache_runner.trading_days = lambda start, end: ["2023-01-03"]

        def fake_blind_cache_chain(symbol, date, *, ledger_dir="ledger"):
            raise RuntimeError(
                f"ThetaData eod returned no rows for {symbol} @ {date}."
            )

        cache_runner.blind_cache_chain = fake_blind_cache_chain

        result = cache_runner.cache_oos_blind(["SPY"], ledger_dir=self.ledger_dir)

        self.assertEqual(result["gaps"], 1)
        self.assertEqual(result["fetched"], 0)
        self.assertEqual(result["repaired"], 0)
        self.assertEqual(result["verified"], 0)
        lines = facts.read_facts(self.ledger_dir)
        self.assertEqual(len(lines), 1)
        for token in ("CACHE_GAP", "symbol=SPY", "date=2023-01-03",
                      "reason=empty_fetch"):
            self.assertIn(token, lines[0])

    def test_unrelated_runtime_error_propagates(self):
        cache_runner.trading_days = lambda start, end: ["2023-01-03"]

        def fake_blind_cache_chain(symbol, date, *, ledger_dir="ledger"):
            raise RuntimeError("boom")

        cache_runner.blind_cache_chain = fake_blind_cache_chain

        with self.assertRaises(RuntimeError):
            cache_runner.cache_oos_blind(["SPY"], ledger_dir=self.ledger_dir)

    def test_provenance_mismatch_is_durable_typed_refusal(self):
        cache_runner.trading_days = lambda start, end: ["2023-01-03"]
        manifest = Path(self._tmp.name) / "cache-run.json"

        def mismatched(symbol, date, *, ledger_dir="ledger"):
            raise thetadata_adapter.CacheProvenanceError("hash mismatch")

        cache_runner.blind_cache_chain = mismatched

        with self.assertRaisesRegex(
            thetadata_adapter.CacheProvenanceError, "hash mismatch"
        ):
            cache_runner.cache_oos_blind(
                ["SPY"],
                ledger_dir=self.ledger_dir,
                manifest_path=manifest,
            )

        payload = json.loads(manifest.read_text())
        self.assertEqual(payload["status"], "FAILED")
        self.assertEqual(
            payload["tasks"]["SPY@2023-01-03"],
            "MISMATCH_REFUSED",
        )

    def test_drops_in_sample_end_and_earlier_days_from_the_window(self):
        # deliberately include config.IN_SAMPLE_END plus later days; the
        # in-sample day must never be processed by the OOS blind path.
        cache_runner.trading_days = lambda start, end: [
            config.IN_SAMPLE_END, "2023-01-03", "2023-01-04",
        ]
        calls = []

        def fake_blind_cache_chain(symbol, date, *, ledger_dir="ledger"):
            calls.append(date)
            return {"ok": True}

        cache_runner.blind_cache_chain = fake_blind_cache_chain

        result = cache_runner.cache_oos_blind(["SPY"], ledger_dir=self.ledger_dir)

        self.assertNotIn(config.IN_SAMPLE_END, calls)
        self.assertEqual(sorted(calls), ["2023-01-03", "2023-01-04"])
        self.assertEqual(result["total_days"], 2)

    def test_window_starts_at_in_sample_end_and_ends_at_backtest_end(self):
        seen = {}

        def fake_trading_days(start, end):
            seen["start"] = start
            seen["end"] = end
            return []

        cache_runner.trading_days = fake_trading_days
        cache_runner.cache_oos_blind(["SPY"], ledger_dir=self.ledger_dir)

        self.assertEqual(seen["start"], config.IN_SAMPLE_END)
        self.assertEqual(seen["end"], config.BACKTEST_END)

    def test_defaults_symbols_to_config_universe(self):
        cache_runner.trading_days = lambda start, end: ["2023-01-03"]
        calls = []

        def fake_blind_cache_chain(symbol, date, *, ledger_dir="ledger"):
            calls.append(symbol)
            return {"ok": True}

        cache_runner.blind_cache_chain = fake_blind_cache_chain

        result = cache_runner.cache_oos_blind(ledger_dir=self.ledger_dir)

        self.assertEqual(sorted(calls), sorted(config.UNIVERSE))
        self.assertEqual(result["symbols"], len(config.UNIVERSE))


class DryRunTests(_CacheRunnerTestCase):
    def test_dry_run_does_not_raise_and_writes_no_facts(self):
        def raiser(*args, **kwargs):
            raise AssertionError("dry-run must never touch the network")

        cache_runner.get_eod_chain = raiser
        cache_runner.blind_cache_chain = raiser
        # dry_run() takes no ledger_dir (it must never write facts anywhere),
        # so compare the real ledger's fact count before/after rather than
        # asserting it is empty -- other runs may have already populated it.
        before = len(facts.read_facts("ledger"))

        result = cache_runner.dry_run()

        self.assertEqual(len(facts.read_facts("ledger")), before)
        self.assertIsInstance(result, dict)

    def test_dry_run_reports_counts_for_both_windows(self):
        result = cache_runner.dry_run()

        n_in_sample_days = len(
            cache_runner.trading_days(config.BACKTEST_START, config.IN_SAMPLE_END)
        )
        n_oos_days = len([
            d for d in cache_runner.trading_days(
                config.IN_SAMPLE_END, config.BACKTEST_END)
            if d > config.IN_SAMPLE_END
        ])
        n_symbols = len(config.UNIVERSE)

        self.assertEqual(result["in_sample"]["trading_days"], n_in_sample_days)
        self.assertEqual(result["in_sample"]["symbols"], n_symbols)
        self.assertEqual(
            result["in_sample"]["total_tasks"], n_in_sample_days * n_symbols)

        self.assertEqual(result["oos_blind"]["trading_days"], n_oos_days)
        self.assertEqual(result["oos_blind"]["symbols"], n_symbols)
        self.assertEqual(
            result["oos_blind"]["total_tasks"], n_oos_days * n_symbols)

    def test_dry_run_counts_already_cached_tasks_via_cache_path_exists(self):
        cache_runner.trading_days = lambda start, end: ["2022-12-28", "2022-12-29"]
        self._touch_cache_file(config.UNIVERSE[0], "2022-12-28")

        result = cache_runner.dry_run()

        # both windows use the same stubbed trading_days here, and only one
        # of the 2 days x len(UNIVERSE) symbols x 2 windows tasks is cached.
        total_already_cached = (
            result["in_sample"]["already_cached"]
            + result["oos_blind"]["already_cached"]
        )
        self.assertEqual(total_already_cached, 1)


class _FakeRpcError(Exception):
    """Stand-in for grpc.RpcError carrying a status code. Declared lazily as a
    grpc.RpcError subclass inside tests so the except clause in the runner
    genuinely matches it."""


def _make_rpc_error(code):
    import grpc

    class FakeRpcError(grpc.RpcError):
        def code(self):
            return code

        def __str__(self):
            return f"fake rpc error {code}"

    return FakeRpcError()


class TransportRetryTests(_CacheRunnerTestCase):
    """A long sequential run WILL hit transport-level gRPC failures (observed
    live 2026-07-03: UNAVAILABLE 'Stream removed (Socket closed)' ~3,890 calls
    in). The runner must retry those with a client reset + backoff, propagate
    everything non-transport immediately, and give up after a bounded number
    of attempts."""

    def setUp(self):
        super().setUp()
        import grpc  # hard dep of thetadata; offline-safe

        self.grpc = grpc
        self._old_sleep = cache_runner._sleep
        self._old_reset = thetadata_adapter._reset_client
        self.sleeps = []
        self.resets = []
        cache_runner._sleep = self.sleeps.append
        thetadata_adapter._reset_client = lambda: self.resets.append(True)
        cache_runner.trading_days = lambda start, end: ["2022-12-28"]

    def tearDown(self):
        cache_runner._sleep = self._old_sleep
        thetadata_adapter._reset_client = self._old_reset
        super().tearDown()

    def test_unavailable_is_retried_with_reset_and_backoff_then_succeeds(self):
        attempts = []

        def flaky(symbol, date):
            attempts.append(1)
            if len(attempts) <= 2:
                raise _make_rpc_error(self.grpc.StatusCode.UNAVAILABLE)

        cache_runner.get_eod_chain = flaky

        result = cache_runner.cache_in_sample(["SPY"], ledger_dir=self.ledger_dir)

        self.assertEqual(result["fetched"], 1)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(len(self.resets), 2)
        self.assertEqual(self.sleeps, [
            cache_runner._RETRY_BASE_SLEEP_S,
            cache_runner._RETRY_BASE_SLEEP_S * 2,
        ])

    def test_permission_denied_propagates_immediately_without_retry(self):
        attempts = []

        def denied(symbol, date):
            attempts.append(1)
            raise _make_rpc_error(self.grpc.StatusCode.PERMISSION_DENIED)

        cache_runner.get_eod_chain = denied

        with self.assertRaises(self.grpc.RpcError):
            cache_runner.cache_in_sample(["SPY"], ledger_dir=self.ledger_dir)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(self.resets, [])
        self.assertEqual(self.sleeps, [])

    def test_retries_exhaust_then_propagate(self):
        attempts = []

        def always_down(symbol, date):
            attempts.append(1)
            raise _make_rpc_error(self.grpc.StatusCode.UNAVAILABLE)

        cache_runner.get_eod_chain = always_down

        with self.assertRaises(self.grpc.RpcError):
            cache_runner.cache_in_sample(["SPY"], ledger_dir=self.ledger_dir)
        self.assertEqual(len(attempts), cache_runner._RETRY_MAX + 1)
        self.assertEqual(len(self.sleeps), cache_runner._RETRY_MAX)

    def test_gap_runtime_error_is_untouched_by_the_retry_wrapper(self):
        cache_runner.get_eod_chain = lambda s, d: (_ for _ in ()).throw(
            RuntimeError("ThetaData greeks_eod returned no rows for SPY @ x"))

        result = cache_runner.cache_in_sample(["SPY"], ledger_dir=self.ledger_dir)

        self.assertEqual(result["gaps"], 1)
        self.assertEqual(self.resets, [])
        self.assertEqual(self.sleeps, [])

    def test_reset_client_clears_the_module_singleton(self):
        old = thetadata_adapter._client_singleton
        try:
            thetadata_adapter._client_singleton = object()
            self._old_reset()  # the REAL _reset_client saved in setUp
            self.assertIsNone(thetadata_adapter._client_singleton)
        finally:
            thetadata_adapter._client_singleton = old


if __name__ == "__main__":
    unittest.main()
