import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import pandas as pd

from options_researcher.chains import third_friday
from options_researcher.h6_features import build_symbol_features

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
            with (
                mock.patch(
                    "options_researcher.h6_features.pd.read_parquet",
                    side_effect=lambda path: by_path[Path(path)],
                ),
                mock.patch(
                    "options_researcher.h6_features.load_closes", return_value=closes
                ),
            ):
                output = build_symbol_features(
                    "NVDA", AS_OF, chain_dir=chains, feature_dir=features
                )
            frame = pd.read_parquet(output)
            self.assertEqual(frame.index[-1], AS_OF.isoformat())
            self.assertEqual(float(frame.iloc[-1]["iv_rank"]), 1.0)
            self.assertEqual(len(frame), 126)

    def test_refuses_latest_fallback_when_exact_session_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            chains = Path(tmp)
            (chains / "NVDA_2026-07-09.parquet").touch()
            with self.assertRaises(FileNotFoundError):
                build_symbol_features("NVDA", AS_OF, chain_dir=chains)


if __name__ == "__main__":
    unittest.main()
