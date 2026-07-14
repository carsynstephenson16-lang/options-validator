import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import pandas as pd

from data import underlying_closes
from options_researcher.chains import third_friday
from options_researcher.h6_features import (
    build_symbol_features,
    feature_manifest_path,
    verify_feature_manifest,
)
from research.hashing import sha256_file

AS_OF = date(2026, 7, 10)


def next_monthly(day: date) -> date:
    probe = day + timedelta(days=15)
    for offset in range(4):
        month = probe.month + offset
        year = probe.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        exp = third_friday(year, month)
        if 15 <= (exp - day).days <= 60:
            return exp
    raise AssertionError("no synthetic monthly")


class H6FeatureBuildTests(unittest.TestCase):
    def test_builds_exact_feature_from_cache_only(self):
        sessions = list(pd.bdate_range(end=AS_OF.isoformat(), periods=126).date)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chains = root / "chains"
            features = root / "features"
            closes_dir = root / "closes"
            chains.mkdir()
            by_path = {}
            for i, day in enumerate(sessions):
                path = chains / f"NVDA_{day.isoformat()}.parquet"
                path.touch()
                by_path[path] = pd.DataFrame(
                    {
                        "expiration": [next_monthly(day).isoformat()],
                        "right": ["P"],
                        "bid": [5.0],
                        "ask": [5.1],
                        "delta": [-0.50],
                        "iv": [0.20 + i / 1000.0],
                    }
                )
            closes_idx = pd.bdate_range(
                start=(sessions[0] - timedelta(days=60)).isoformat(),
                end=AS_OF.isoformat(),
            )
            closes = pd.Series(100.0, index=closes_idx.strftime("%Y-%m-%d"))
            close_frame = pd.DataFrame(
                {"date": closes.index, "close": closes.to_numpy()}
            )
            close_path = closes_dir / "NVDA.parquet"
            closes_dir.mkdir()
            close_frame.to_parquet(close_path, index=False)
            by_path[close_path] = close_frame
            facts_path = root / "facts.log"
            fact_lines = [
                "2026-07-11T00:00:00+00:00\tBLIND_CACHE "
                f"symbol=NVDA date={day.isoformat()} rows=1 "
                f"sha256={sha256_file(chains / f'NVDA_{day.isoformat()}.parquet')}"
                for day in sessions
            ]
            facts_path.write_text("\n".join(fact_lines) + "\n")
            with (
                mock.patch(
                    "options_researcher.h6_features.pd.read_parquet",
                    side_effect=lambda path: by_path[Path(path)],
                ),
                mock.patch.object(
                    underlying_closes, "CACHE_DIR", str(closes_dir)
                ),
            ):
                output = build_symbol_features(
                    "NVDA",
                    AS_OF,
                    chain_dir=chains,
                    feature_dir=features,
                    facts_path=facts_path,
                )
            frame = pd.read_parquet(output)
            self.assertEqual(frame.index[-1], AS_OF.isoformat())
            self.assertEqual(float(frame.iloc[-1]["iv_rank"]), 1.0)
            self.assertEqual(len(frame), 126)
            manifest_path = feature_manifest_path("NVDA", features)
            self.assertTrue(manifest_path.is_file())
            with mock.patch.object(
                underlying_closes, "CACHE_DIR", str(closes_dir)
            ):
                manifest = verify_feature_manifest(
                    "NVDA",
                    AS_OF,
                    feature_dir=features,
                    chain_dir=chains,
                    facts_path=facts_path,
                )
            self.assertEqual(manifest["feature_window"]["chain_count"], 126)
            self.assertEqual(manifest["output"]["path"], str(output.resolve()))

            chain_path = chains / f"NVDA_{sessions[0].isoformat()}.parquet"
            chain_path.write_bytes(b"mutated")
            with (
                mock.patch.object(
                    underlying_closes, "CACHE_DIR", str(closes_dir)
                ),
                self.assertRaisesRegex(ValueError, "mutated file"),
            ):
                verify_feature_manifest(
                    "NVDA",
                    AS_OF,
                    feature_dir=features,
                    chain_dir=chains,
                    facts_path=facts_path,
                )

            chain_path.write_bytes(b"")
            facts_path.write_text("\n".join(fact_lines[1:]) + "\n")
            with (
                mock.patch.object(
                    underlying_closes, "CACHE_DIR", str(closes_dir)
                ),
                self.assertRaisesRegex(ValueError, "provenance"),
            ):
                verify_feature_manifest(
                    "NVDA",
                    AS_OF,
                    feature_dir=features,
                    chain_dir=chains,
                    facts_path=facts_path,
                )

    def test_refuses_latest_fallback_when_exact_session_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            chains = Path(tmp)
            (chains / "NVDA_2026-07-09.parquet").touch()
            with self.assertRaises(FileNotFoundError):
                build_symbol_features("NVDA", AS_OF, chain_dir=chains)

    def test_manifest_is_required_and_self_hash_is_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            features = Path(tmp)
            pd.DataFrame(
                {"iv_rank": [0.2]}, index=pd.Index([AS_OF.isoformat()])
            ).to_parquet(features / "NVDA_features.parquet")
            with self.assertRaisesRegex(ValueError, "feature manifest"):
                verify_feature_manifest("NVDA", AS_OF, feature_dir=features)

            path = feature_manifest_path("NVDA", features)
            path.write_text('{"manifest_hash":"' + "0" * 64 + '"}\n')
            with self.assertRaisesRegex(ValueError, "manifest_hash"):
                verify_feature_manifest("NVDA", AS_OF, feature_dir=features)


if __name__ == "__main__":
    unittest.main()
