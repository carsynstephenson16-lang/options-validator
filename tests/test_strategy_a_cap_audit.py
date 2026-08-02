"""Q8 reproducibility tests for the read-only Strategy A cap audit."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from tools.cache_manifest import write_manifest
from tools.strategy_a_cap_audit import (
    AuditBlocked,
    run_audit,
    verify_receipt,
    write_receipt,
)


def _chain(
    *,
    short_bid: float = 1.20,
    short_ask: float = 1.30,
    long_bid: float = 0.60,
    long_ask: float = 0.64,
    long_strike: float = 98.0,
) -> pd.DataFrame:
    expiration = "2022-07-08"
    return pd.DataFrame(
        [
            {
                "expiration": expiration,
                "strike": 100.0,
                "right": "P",
                "bid": short_bid,
                "ask": short_ask,
                "open_interest": 500,
                "iv": 0.25,
                "delta": -0.30,
                "gamma": 0.01,
                "theta": -0.05,
                "vega": 0.10,
            },
            {
                "expiration": expiration,
                "strike": long_strike,
                "right": "P",
                "bid": long_bid,
                "ask": long_ask,
                "open_interest": 500,
                "iv": 0.25,
                "delta": -0.25,
                "gamma": 0.01,
                "theta": -0.05,
                "vega": 0.10,
            },
        ]
    )


class StrategyACapAuditTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.cache = self.root / "chains"
        self.cache.mkdir()
        self.manifest = self.root / "manifest.txt"
        _chain().to_parquet(self.cache / "SYN_2022-06-01.parquet", index=False)
        _chain().to_parquet(self.cache / "SYN_2022-06-02.parquet", index=False)
        write_manifest(str(self.cache), str(self.manifest))

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self):
        return run_audit(
            symbols=["SYN"],
            start="2022-06-01",
            end="2022-06-01",
            cache_dir=self.cache,
            manifest_path=self.manifest,
        )

    def test_tiny_golden_fixture_is_deterministic_and_cache_only(self):
        with mock.patch(
            "data.thetadata_adapter._fetch_merged_chain",
            side_effect=AssertionError("provider path called"),
        ):
            first = self._run()
            second = self._run()

        self.assertEqual(first, second)
        self.assertEqual(first["schema"], "strategy-a-cap-audit/v1")
        self.assertEqual(first["engine"], "post-atomicity")
        self.assertEqual(first["classification"], "MECHANICAL_ENTRY_PATH_REPLAY")
        self.assertEqual(
            first["counts"],
            {
                "cached_chain_days": 1,
                "day_d_accepted": 1,
                "cancelled_beyond_tolerance": 0,
                "allowed_d_plus_1_fills": 1,
                "allowed_fills_requiring_resize": 0,
                "exact_frozen_leg_unavailable_d_plus_1": 0,
            },
        )
        self.assertAlmostEqual(first["risk"]["highest_new_policy_allowed"], 598.40)
        self.assertAlmostEqual(first["risk"]["worst_new_policy_cap_breach"], 0.0)
        self.assertEqual(first["rates"]["cancellation"], 0.0)
        self.assertEqual(first["rates"]["resize_given_allowed"], 0.0)
        self.assertEqual(first["manifest_scope"]["status"], "PASS")
        self.assertFalse(first["integrity"]["holdout_read"])
        self.assertFalse(first["integrity"]["provider_call"])

    def test_missing_frozen_leg_is_reported_not_substituted(self):
        _chain(long_strike=97.0).to_parquet(self.cache / "SYN_2022-06-02.parquet", index=False)
        write_manifest(str(self.cache), str(self.manifest))

        report = self._run()

        self.assertEqual(report["counts"]["day_d_accepted"], 1)
        self.assertEqual(report["counts"]["exact_frozen_leg_unavailable_d_plus_1"], 1)
        self.assertEqual(report["counts"]["allowed_d_plus_1_fills"], 0)
        self.assertEqual(report["unavailable"][0]["reason"], "frozen_leg_missing")

    def test_selected_manifest_mismatch_blocks_before_measurement(self):
        _chain(short_bid=9.0).to_parquet(self.cache / "SYN_2022-06-01.parquet", index=False)

        with self.assertRaisesRegex(AuditBlocked, "MISMATCH.*SYN_2022-06-01"):
            self._run()

    def test_receipt_round_trip_recomputes_every_field(self):
        report = self._run()
        receipt = write_receipt(report, self.root / "receipt.json")

        ok, failures = verify_receipt(
            receipt,
            cache_dir=self.cache,
            manifest_path=self.manifest,
        )

        self.assertTrue(ok, failures)
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
