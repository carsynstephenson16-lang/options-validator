"""Pure H7 signal functions, tested on synthetic frames only (no cache, no
network). 2026-08-21 is a third Friday, so it passes chains.is_monthly."""

import unittest

import pandas as pd

from options_researcher import h7_signals as sig


def closes(vals):
    idx = pd.bdate_range("2025-01-02", periods=len(vals))
    return pd.Series([float(v) for v in vals], index=idx, name="close")


class TestDrawdownAndReclaim(unittest.TestCase):
    def test_drawdown_pct_from_52wk_high(self):
        s = closes([100] * 250 + [60])
        self.assertAlmostEqual(sig.drawdown_pct(s), 0.40)

    def test_first_reclaim_of_episode_fires(self):
        s = closes([100] * 30 + [60] * 20 + [61])
        self.assertTrue(sig.reclaimed_20d_high(s))

    def test_does_not_refire_during_a_grind_up(self):
        # registration: once per drawdown episode -- 62/63/70 are not fresh
        # signals, the episode already fired at 61
        base = [100] * 30 + [60] * 20
        self.assertFalse(sig.reclaimed_20d_high(closes(base + [61, 62])))
        self.assertFalse(sig.reclaimed_20d_high(closes(base + [61, 62, 63, 70])))

    def test_rearms_after_a_new_20d_low(self):
        # fire at 61, fail lower to a fresh 20d low (55), base at 56, then a
        # new first-cross at 57 fires again
        path = [100] * 30 + [60] * 20 + [61, 62] + [55] + [56] * 20 + [57]
        self.assertTrue(sig.reclaimed_20d_high(closes(path)))

    def test_lane_a_requires_both_conditions(self):
        deep_but_no_reclaim = closes([100] * 250 + [60] * 25)
        self.assertFalse(sig.lane_a_armed(deep_but_no_reclaim))
        shallow_with_reclaim = closes([100] * 250 + [95] * 21 + [101])
        self.assertFalse(sig.lane_a_armed(shallow_with_reclaim))

    def test_lane_a_arms_on_deep_drawdown_plus_reclaim(self):
        path = [100] * 250 + [60] * 25 + [70]
        self.assertTrue(sig.lane_a_armed(closes(path)))


class TestCoil(unittest.TestCase):
    def test_range_compression(self):
        tight = closes([100] * 200 + [98, 99, 100, 101, 102] * 12)
        self.assertLessEqual(sig.range_pct(tight, 60), 0.15)
        wide = closes([100] * 200 + [80, 120] * 30)
        self.assertGreater(sig.range_pct(wide, 60), 0.15)

    def test_rv_percentile_short_history_is_ineligible(self):
        s = closes([100, 101] * 30)  # ~60 sessions < 6 months
        self.assertEqual(sig.rv_percentile(s), 1.0)


class TestIVRouting(unittest.TestCase):
    def test_routes(self):
        self.assertEqual(sig.iv_route(iv=0.50, rv=0.60), "call")     # <= 1.00x
        self.assertEqual(sig.iv_route(iv=0.66, rv=0.60), "spread")   # <= 1.15x
        self.assertEqual(sig.iv_route(iv=0.80, rv=0.60), "h7c")      # >= 1.25x
        self.assertEqual(sig.iv_route(iv=0.72, rv=0.60), "none")     # dead zone
        self.assertEqual(sig.iv_route(iv=0.50, rv=0.0), "none")      # degenerate rv

    def test_rv_annualized(self):
        s = closes([100, 101, 100, 101, 100] * 10)
        self.assertGreater(sig.rv_annualized(s, lookback=21), 0.0)


class TestAdmission(unittest.TestCase):
    def _chain(self, spread_pct, oi, n=6):
        rows = []
        for i in range(n):
            mid = 10.0
            half = mid * spread_pct / 2
            rows.append({
                "expiration": "2026-08-21", "strike": 95.0 + i, "right": "C",
                "bid": mid - half, "ask": mid + half, "open_interest": oi,
                "iv": 0.6, "delta": 0.5, "gamma": 0.0, "theta": 0.0, "vega": 0.0,
            })
        return pd.DataFrame(rows)

    def test_admission_passes_tight_monthly(self):
        ch = self._chain(spread_pct=0.04, oi=500)
        ok, n = sig.lane_admission(
            ch, spot=100.0, today=pd.Timestamp("2026-07-10").date(), dte_band=(30, 45)
        )
        self.assertTrue(ok)
        self.assertGreaterEqual(n, 5)

    def test_admission_counts_the_traded_right_only(self):
        # a calls-only chain must NOT admit a puts lane (H7c trades puts)
        ch = self._chain(spread_pct=0.04, oi=500)
        ok, n = sig.lane_admission(
            ch, spot=100.0, today=pd.Timestamp("2026-07-10").date(),
            dte_band=(30, 45), right="P",
        )
        self.assertFalse(ok)
        self.assertEqual(n, 0)

    def test_admission_fails_wide_or_thin(self):
        wide = self._chain(spread_pct=0.08, oi=500)   # > 5% admission gate
        ok, _ = sig.lane_admission(
            wide, spot=100.0, today=pd.Timestamp("2026-07-10").date(), dte_band=(30, 45)
        )
        self.assertFalse(ok)
        thin = self._chain(spread_pct=0.04, oi=50)    # < MIN_OPEN_INTEREST
        ok, _ = sig.lane_admission(
            thin, spot=100.0, today=pd.Timestamp("2026-07-10").date(), dte_band=(30, 45)
        )
        self.assertFalse(ok)
