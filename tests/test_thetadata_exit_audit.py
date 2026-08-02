"""Offline tests for the content-addressed ThetaData exit audit."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from research.hashing import sha256_file
from tools import thetadata_exit_audit as audit

SESSION = "2026-07-10"
NY = ZoneInfo("America/New_York")


def _chain(spot: float = 100.0) -> pd.DataFrame:
    rows = []
    for expiration in ("2026-08-21", "2026-09-18", "2026-10-16"):
        for strike in (90.0, 95.0, 100.0, 105.0, 110.0):
            call_mid = max(spot - strike, 0) + 2.0
            put_mid = call_mid - (spot - strike)
            for right, mid, delta in (("C", call_mid, 0.60), ("P", put_mid, -0.25)):
                rows.append(
                    {
                        "expiration": expiration,
                        "strike": strike,
                        "right": right,
                        "bid": mid - 0.05,
                        "ask": mid + 0.05,
                        "open_interest": 500,
                        "iv": 0.40,
                        "delta": delta,
                        "gamma": 0.02,
                        "theta": -0.03,
                        "vega": 0.10,
                    }
                )
    return pd.DataFrame(rows)


class ExitAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.chains = self.root / "chains"
        self.closes = self.root / "closes"
        self.chains.mkdir()
        self.closes.mkdir()
        self.path = self.chains / f"AMD_{SESSION}.parquet"
        _chain().to_parquet(self.path, index=False)
        pd.DataFrame({"date": [SESSION], "close": [100.0]}).to_parquet(
            self.closes / "AMD.parquet", index=False
        )

    def _facts(self, *, fetched=None, digest=None):
        return {
            ("AMD", SESSION): {
                "fetched": fetched or datetime(2026, 7, 10, 18, 30, tzinfo=NY),
                "sha256": digest or sha256_file(self.path),
            }
        }

    def _run(self, **kwargs):
        facts = kwargs.pop("facts") if "facts" in kwargs else self._facts()
        return audit.run_audit(
            symbols=["AMD"],
            start=SESSION,
            end=SESSION,
            chain_dir=self.chains,
            close_dir=self.closes,
            facts=facts,
            sessions=[SESSION],
            identity={
                "commit": "test",
                "source_paths": list(audit.SOURCE_PATHS),
                "dirty": False,
                "dirty_paths": [],
            },
            **kwargs,
        )

    def _identity(self):
        return {
            "commit": "test",
            "source_paths": list(audit.SOURCE_PATHS),
            "dirty": False,
            "dirty_paths": [],
        }

    def test_clean_window_passes_and_binds_files(self):
        report = self._run()
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["counts"]["expected_symbol_sessions"], 1)
        self.assertEqual(len(report["file_hashes"]), 2)
        self.assertTrue(report["receipt_hash"])

    def test_written_receipt_recomputes_and_detects_mutation(self):
        report = self._run()
        path = audit.write_receipt(report, self.root / "reports")
        ok, failures = audit.verify_receipt(
            path,
            chain_dir=self.chains,
            close_dir=self.closes,
            facts=self._facts(),
            sessions=[SESSION],
            identity=self._identity(),
        )
        self.assertTrue(ok, failures)
        changed = _chain()
        changed.loc[0, "bid"] += 0.01
        changed.to_parquet(self.path, index=False)
        ok, failures = audit.verify_receipt(
            path,
            chain_dir=self.chains,
            close_dir=self.closes,
            facts=self._facts(digest=sha256_file(self.path)),
            sessions=[SESSION],
            identity=self._identity(),
        )
        self.assertFalse(ok)
        self.assertIn("file_hashes_hash", failures)

    def test_missing_chain_blocks_completeness(self):
        self.path.unlink()
        report = self._run(facts={})
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertTrue(any(item["check"] == 1 for item in report["blocks"]))

    def test_pre_eod_fetch_and_sha_mismatch_both_block(self):
        facts = self._facts(fetched=datetime(2026, 7, 10, 16, 30, tzinfo=NY), digest="0" * 64)
        report = self._run(facts=facts)
        details = [item["detail"] for item in report["blocks"]]
        self.assertTrue(any("sha256 mismatch" in item for item in details))
        self.assertTrue(any("before EOD report" in item for item in details))

    def test_independent_close_drift_blocks(self):
        pd.DataFrame({"date": [SESSION], "close": [50.0]}).to_parquet(
            self.closes / "AMD.parquet", index=False
        )
        report = self._run()
        self.assertTrue(
            any(item["check"] == 13 and "drift=" in item["detail"] for item in report["blocks"])
        )

    def test_parity_can_be_diagnostic_when_v2_checks_provider_spot(self):
        pd.DataFrame({"date": [SESSION], "close": [50.0]}).to_parquet(
            self.closes / "AMD.parquet", index=False
        )

        report = self._run(parity_mode="diagnostic")

        self.assertFalse(any(item["check"] == 13 for item in report["blocks"]))
        self.assertTrue(
            any(
                item["check"] == 13 and "diagnostic parity" in item["detail"]
                for item in report["warnings"]
            )
        )

    def test_unlisted_calendar_monthly_is_eligibility_warning_not_capture_block(self):
        frame = _chain()
        frame = frame[frame["expiration"] == "2026-08-21"]
        frame.to_parquet(self.path, index=False)
        report = self._run(facts=self._facts())
        self.assertFalse(any(item["check"] == 2 for item in report["blocks"]))
        self.assertTrue(
            any(item["check"] == 2 and "long-call" in item["detail"] for item in report["warnings"])
        )

    def test_extreme_iv_outside_declared_lane_is_warning_not_block(self):
        frame = _chain()
        outside = (frame["expiration"] == "2026-08-21") & frame["right"].eq("C")
        frame.loc[outside, "iv"] = 6.0
        frame.to_parquet(self.path, index=False)

        report = self._run(facts=self._facts())

        self.assertFalse(any(item["check"] == "10/11" for item in report["blocks"]))
        self.assertTrue(any(item["check"] == "10/11" for item in report["warnings"]))

    def test_extreme_iv_inside_declared_lane_still_blocks(self):
        frame = _chain()
        inside = (frame["expiration"] == "2026-09-18") & frame["right"].eq("C")
        frame.loc[inside, "iv"] = 6.0
        frame.to_parquet(self.path, index=False)

        report = self._run(facts=self._facts())

        self.assertTrue(any(item["check"] == "10/11" for item in report["blocks"]))

    def test_bad_iv_on_unselectable_deep_itm_call_is_only_a_warning(self):
        frame = _chain()
        bad = (
            (frame["expiration"] == "2026-09-18")
            & frame["right"].eq("C")
            & frame["strike"].eq(90.0)
        )
        frame.loc[bad, ["iv", "delta"]] = [0.0, 1.0]
        frame.to_parquet(self.path, index=False)

        report = self._run(facts=self._facts())

        self.assertFalse(any(item["check"] == "10/11" for item in report["blocks"]))
        self.assertTrue(any(item["check"] == "10/11" for item in report["warnings"]))

    def test_dirty_source_identity_blocks_receipt_readiness(self):
        report = audit.run_audit(
            symbols=["AMD"],
            start=SESSION,
            end=SESSION,
            chain_dir=self.chains,
            close_dir=self.closes,
            facts=self._facts(),
            sessions=[SESSION],
            identity={
                "commit": "test",
                "source_paths": list(audit.SOURCE_PATHS),
                "dirty": True,
                "dirty_paths": ["config.py"],
            },
        )
        self.assertTrue(any(item["check"] == "IDENTITY" for item in report["blocks"]))


if __name__ == "__main__":
    unittest.main()
