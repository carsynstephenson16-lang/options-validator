"""tests/test_qm_pooled_readings.py -- offline unit tests for the read-only
QM pooled-readings reducer (tools/qm_pooled_readings.py).

Fixtures are synthetic frames (no network, no parquet, no config QM_* values
-- params/loaders are injected). Guardrails exercised: the pure pooling core
computes median excess correctly by hand against a tiny two-name fixture,
tradability summation/rate, gate-first refusal before any loader runs, and a
disclosed OHLCV-cache-gap skip.
"""

import contextlib
import io
import unittest

import pandas as pd

from tools import qm_pooled_readings as reducer

PARAMS = {
    "QM_TRADABILITY_DTE": (30, 60),
    "QM_NTM_BAND": 0.10,
    "QM_HORIZONS": (1,),
}


def _iso(n, start="2020-01-02"):
    return [d.date().isoformat() for d in pd.bdate_range(start, periods=n)]


def _frame(closes):
    idx = _iso(len(closes))
    return pd.DataFrame(
        {"open": closes, "high": closes, "low": closes, "close": closes,
         "volume": [1.0] * len(closes)},
        index=idx,
    ).astype(float)


def _boom(*_a, **_k):
    raise AssertionError("loader called after gate refusal")


class PoolingCoreTests(unittest.TestCase):
    """Hand-checked two-name fixture (see module docstring derivation):

    Name A closes=[100,110,99]: baseline h=1 values [0.10, -0.10] -> median
    0.0; fire at pos0 -> forward return 0.10 -> excess 0.10.

    Name B closes=[50,60,51]: baseline h=1 values [0.20, -0.15] -> median
    0.025; fire at pos1 -> forward return -0.15 -> excess -0.175.

    Pooled excess = [0.10, -0.175]; median of the two = -0.0375.
    """

    def test_pool_excess_across_universe_hand_checked(self):
        frame_a = _frame([100.0, 110.0, 99.0])
        frame_b = _frame([50.0, 60.0, 51.0])
        name_fires = [
            (frame_a, [frame_a.index[0]]),
            (frame_b, [frame_b.index[1]]),
        ]
        pooled = reducer.pool_excess_across_universe(name_fires, (1,))
        self.assertEqual(len(pooled[1]), 2)
        self.assertAlmostEqual(pooled[1][0], 0.10)
        self.assertAlmostEqual(pooled[1][1], -0.175)

    def test_pooled_median_of_hand_checked_fixture(self):
        frame_a = _frame([100.0, 110.0, 99.0])
        frame_b = _frame([50.0, 60.0, 51.0])
        name_fires = [
            (frame_a, [frame_a.index[0]]),
            (frame_b, [frame_b.index[1]]),
        ]
        pooled = reducer.pool_excess_across_universe(name_fires, (1,))
        self.assertAlmostEqual(reducer.pooled_median(pooled[1]), -0.0375)

    def test_pooled_median_empty_is_none(self):
        self.assertIsNone(reducer.pooled_median([]))

    def test_pool_excludes_truncated_fire_never_imputes(self):
        # Only session with no forward window (last row) as the fire: forward
        # return is None and must be dropped, not treated as zero.
        frame_a = _frame([100.0, 110.0, 99.0])
        pooled = reducer.pool_excess_across_universe(
            [(frame_a, [frame_a.index[-1]])], (1,)
        )
        self.assertEqual(pooled[1], [])


class TradabilityPoolingTests(unittest.TestCase):
    def test_sum_tradability_and_rate(self):
        pooled = reducer.sum_tradability(
            [
                {"tradable": 1, "untradable": 2, "no_chain": 0},
                {"tradable": 3, "untradable": 1, "no_chain": 4},
            ]
        )
        self.assertEqual(pooled, {"tradable": 4, "untradable": 3, "no_chain": 4})
        self.assertAlmostEqual(reducer.tradability_rate(pooled), 4 / 7)

    def test_tradability_rate_no_denom_is_none(self):
        self.assertIsNone(
            reducer.tradability_rate({"tradable": 0, "untradable": 0, "no_chain": 5})
        )


class GateTests(unittest.TestCase):
    def test_gate_refusal_exits_2_without_touching_data(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = reducer.main(
                [],
                gate=lambda: "REFUSED: QM pre-registration incomplete",
                universe=["NVDA"],
                params=PARAMS,
                load_adjusted=_boom,
                load_raw=_boom,
                load_chain=_boom,
            )
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", buf.getvalue())


class CollectOneNameTests(unittest.TestCase):
    def test_missing_cache_disclosed_and_skipped(self):
        def _missing(*_a, **_k):
            raise FileNotFoundError("no cache")

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = reducer._collect_one_name(
                "ZZZ", _missing, _missing, _boom, PARAMS, "2026-07-14"
            )
        self.assertIsNone(result)
        self.assertIn("ZZZ", buf.getvalue())
        self.assertIn("no OHLCV cache", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
