import unittest
from datetime import date

import numpy as np

import config
import metrics
from metrics import scoreboard


def _trade(pnl, date="2021-01-04", symbol="SPY", car=100.0):
    return {"pnl": pnl, "capital_at_risk": car, "entry_date": date, "symbol": symbol}


class ContractTests(unittest.TestCase):
    def test_scoreboard_raises_without_entry_date(self):
        with self.assertRaises(ValueError):
            scoreboard([{"pnl": 5.0, "capital_at_risk": 100.0, "symbol": "SPY"}])

    def test_scoreboard_raises_without_symbol(self):
        with self.assertRaises(ValueError):
            scoreboard([{"pnl": 5.0, "capital_at_risk": 100.0, "entry_date": "2021-01-04"}])

    def test_scoreboard_raises_on_non_string_symbol(self):
        with self.assertRaises(ValueError):
            scoreboard([_trade(5.0, symbol=123)])

    def test_scoreboard_raises_on_unparseable_entry_date(self):
        with self.assertRaises(ValueError):
            scoreboard([_trade(5.0, date="not-a-date")])

    def test_scoreboard_raises_on_non_date_entry_type(self):
        with self.assertRaises(ValueError):
            scoreboard([_trade(5.0, date=123)])


class CohortAndBlockTests(unittest.TestCase):
    def test_same_iso_week_trades_form_one_cohort(self):
        # 2021-01-04 (Mon) and 2021-01-08 (Fri) are the same ISO week.
        dates = ["2021-01-04", "2021-01-08", "2021-01-11"]
        pnls = __import__("numpy").array([1.0, 2.0, 3.0])
        cohorts = metrics._build_week_cohorts(dates, pnls)
        self.assertEqual(len(cohorts), 2)          # week1 {Mon,Fri}, week2 {Mon}
        self.assertEqual(sorted(cohorts[0].tolist()), [1.0, 2.0])

    def test_week_cohorts_refuse_config_label_drift(self):
        original = config.COHORT_GRANULARITY
        try:
            config.COHORT_GRANULARITY = "day"
            with self.assertRaises(ValueError):
                metrics._build_week_cohorts(["2021-01-04"], np.array([1.0]))
        finally:
            config.COHORT_GRANULARITY = original

    def test_block_lengths_are_deduped_clamped_and_theory_anchored(self):
        Ls = metrics._block_lengths(64)  # 64**(1/3)=4 -> {2,4,8,16}
        self.assertEqual(Ls, [2, 4, 8, 16])
        for L in Ls:
            self.assertGreaterEqual(L, 2)
            self.assertLessEqual(L, 63)

    def test_block_lengths_empty_below_three_cohorts(self):
        self.assertEqual(metrics._block_lengths(2), [])
        self.assertEqual(metrics._block_lengths(1), [])


class EnvelopeCiTests(unittest.TestCase):
    def _independent_weekly(self):
        # 60 trades, one per distinct ISO week, mild both-signed PnL, one symbol.
        base = date(2018, 1, 1)
        dates = [(base.toordinal() + i * 7) for i in range(60)]
        dates = [date.fromordinal(o).isoformat() for o in dates]
        rng = np.random.default_rng(0)
        pnls = rng.normal(5.0, 40.0, size=60)
        return dates, pnls

    def test_ci_is_finite_ordered_and_seed_stable_on_independent_data(self):
        dates, pnls = self._independent_weekly()
        lo1, hi1 = metrics._dependence_aware_ci(dates, pnls, n_boot=400, seed=7)
        lo2, hi2 = metrics._dependence_aware_ci(dates, pnls, n_boot=400, seed=7)
        self.assertTrue(np.isfinite(lo1) and np.isfinite(hi1))
        self.assertLess(lo1, float(pnls.mean()))
        self.assertLess(float(pnls.mean()), hi1)
        self.assertEqual((lo1, hi1), (lo2, hi2))  # deterministic under fixed seed

    def test_ci_is_nan_below_three_cohorts(self):
        dates = ["2021-01-04", "2021-01-11"]  # 2 weeks -> no valid block
        lo, hi = metrics._dependence_aware_ci(dates, np.array([1.0, -1.0]), n_boot=50)
        self.assertTrue(np.isnan(lo) and np.isnan(hi))

    def test_iid_helper_exists_and_is_not_used_by_scoreboard(self):
        _, pnls = self._independent_weekly()
        lo, hi = metrics.iid_expectancy_ci(pnls, n_boot=400, seed=1)
        self.assertLess(lo, hi)


class VerdictGuardTests(unittest.TestCase):
    def _weeks(self, n_weeks, pnl, symbol="SPY", start=date(2018, 1, 1)):
        out = []
        for w in range(n_weeks):
            d = date.fromordinal(start.toordinal() + w * 7).isoformat()
            out.append(_trade(pnl, date=d, symbol=symbol))
        return out

    def test_insufficient_when_fewer_than_three_cohorts(self):
        # 2 weeks, 20 losses -> passes the loss gate but fails the cohort gate.
        trades = ([_trade(-50.0, date="2021-01-04") for _ in range(10)]
                  + [_trade(-50.0, date="2021-01-11") for _ in range(10)])
        result = scoreboard(trades)
        self.assertIn("INSUFFICIENT SAMPLE", result["verdict"])

    def test_verdict_present_with_enough_cohorts_and_losses(self):
        # 40 weekly winners + 12 weekly losers across many weeks -> a real verdict.
        trades = self._weeks(40, 30.0) + [
            _trade(-60.0, date=date.fromordinal(date(2019, 1, 7).toordinal() + w * 7).isoformat())
            for w in range(12)]
        result = scoreboard(trades)
        self.assertNotIn("INSUFFICIENT SAMPLE", result["verdict"])


class UnderCoverageTests(unittest.TestCase):
    def _clustered(self):
        """42 'up' weeks (+10 for all 5 names) then 8 CONTIGUOUS 'down' weeks
        (-30 for all 5 names). Overall mean is mildly positive, but losses cluster
        both serially (contiguous weeks) and cross-sectionally (all names move
        together each week)."""
        dates, pnls, symbols = [], [], ["SPY", "QQQ", "MSFT", "AAPL", "NVDA"]
        start = date(2018, 1, 1).toordinal()
        week = 0
        for _ in range(42):
            for s in symbols:
                dates.append(date.fromordinal(start + week * 7).isoformat()); pnls.append(10.0)
            week += 1
        for _ in range(8):
            for s in symbols:
                dates.append(date.fromordinal(start + week * 7).isoformat()); pnls.append(-30.0)
            week += 1
        return dates, np.array(pnls, dtype=float)

    def test_iid_false_pass_but_dependence_aware_refuses(self):
        dates, pnls = self._clustered()
        iid_lo, iid_hi = metrics.iid_expectancy_ci(pnls, n_boot=2000, seed=42)
        dep_lo, dep_hi = metrics._dependence_aware_ci(dates, pnls, n_boot=2000, seed=42)

        self.assertGreater(iid_lo, 0.0)               # IID: false PASS (CI excludes 0)
        self.assertLessEqual(dep_lo, 0.0)             # dependence-aware: includes 0
        self.assertGreater(dep_hi - dep_lo, iid_hi - iid_lo)  # and is wider


if __name__ == "__main__":
    unittest.main()
