"""Read-only full-audit tests for the parked future-ticker capture."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from research.hashing import sha256_file
from tools import future_ticker_data_audit as audit

SYMBOL = "MU"
SESSION = "2026-07-31"


def _chain() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "expiration": "2026-09-18",
                "strike": 100.0,
                "right": "C",
                "bid": 4.9,
                "ask": 5.0,
                "open_interest": 500,
                "iv": 0.35,
                "delta": 0.60,
                "gamma": 0.02,
                "theta": -0.03,
                "vega": 0.10,
            },
            {
                "expiration": "2026-09-18",
                "strike": 100.0,
                "right": "P",
                "bid": 4.8,
                "ask": 4.9,
                "open_interest": 500,
                "iv": 0.35,
                "delta": -0.25,
                "gamma": 0.02,
                "theta": -0.03,
                "vega": 0.10,
            },
        ]
    )


class FutureTickerDataAuditTests(unittest.TestCase):
    def _fixture(self, root: Path, *, close: bool = True) -> tuple[Path, Path, Path]:
        capture = root / "capture"
        partition = capture / "raw" / SYMBOL / SESSION
        partition.mkdir(parents=True)
        chain_path = partition / "chain.parquet"
        frame = _chain()
        frame.to_parquet(chain_path, index=False)
        (partition / "receipt.json").write_text(
            json.dumps(
                {
                    "schema": "future_ticker_eod_capture_v1",
                    "status": "CAPTURED",
                    "symbol": SYMBOL,
                    "session": SESSION,
                    "rows": len(frame),
                    "parked_display_only": True,
                    "verdict_eligible": False,
                    "parquet": {"sha256": sha256_file(chain_path)},
                }
            )
        )
        (capture / "capture_summary.json").write_text(
            json.dumps(
                {
                    "schema": "future_ticker_eod_capture_summary_v1",
                    "symbols": [SYMBOL],
                    "sessions": 1,
                    "start_session": SESSION,
                    "end_session": SESSION,
                    "planned_tasks": 1,
                    "results": {"captured_or_existing": 1, "errors": 0},
                    "errors": [],
                    "source": {"worktree_dirty": False},
                    "storage": {
                        "canonical_chain_cache_touched": False,
                        "parked_display_only": True,
                        "verdict_eligible": False,
                    },
                }
            )
        )
        closes = root / "closes"
        closes.mkdir()
        if close:
            pd.DataFrame({"date": [SESSION], "close": [100.0]}).to_parquet(
                closes / f"{SYMBOL}.parquet", index=False
            )
        return capture, closes, chain_path

    def test_full_scan_binds_partition_but_v1_timestamp_gap_blocks_promotion(self):
        with tempfile.TemporaryDirectory() as temp:
            capture, closes, _ = self._fixture(Path(temp))
            report = audit.run_audit(
                capture,
                closes,
                symbols=[SYMBOL],
                sessions=[SESSION],
                identity={"dirty": False, "source_paths": [], "source_hashes": {}},
            )

        self.assertEqual(report["counts"]["expected_partitions"], 1)
        self.assertEqual(report["counts"]["hash_verified_partitions"], 1)
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertTrue(any(item["check"] == 9 for item in report["blocks"]))
        self.assertTrue(report["receipt_hash"])

    def test_hash_mismatch_and_missing_independent_close_both_block(self):
        with tempfile.TemporaryDirectory() as temp:
            capture, closes, chain_path = self._fixture(Path(temp), close=False)
            changed = pd.read_parquet(chain_path)
            changed.loc[0, "bid"] += 0.01
            changed.to_parquet(chain_path, index=False)
            report = audit.run_audit(
                capture,
                closes,
                symbols=[SYMBOL],
                sessions=[SESSION],
                identity={"dirty": False, "source_paths": [], "source_hashes": {}},
            )

        checks = {item["check"] for item in report["blocks"]}
        self.assertIn(1, checks)
        self.assertIn(13, checks)


if __name__ == "__main__":
    unittest.main()
