import unittest
from datetime import date

import numpy as np

import config
from analysis import power_check
from metrics import scoreboard


class SimulatorTests(unittest.TestCase):
    def test_simulate_trades_is_deterministic_per_seed(self):
        a = power_check.simulate_trades(
            104, date(2023, 1, 2), 0.02, np.random.default_rng(11))
        b = power_check.simulate_trades(
            104, date(2023, 1, 2), 0.02, np.random.default_rng(11))
        c = power_check.simulate_trades(
            104, date(2023, 1, 2), 0.02, np.random.default_rng(12))
        self.assertEqual(a[0], b[0])
        self.assertEqual(a[1], b[1])
        self.assertNotEqual(a[1], c[1])  # different stream -> different pnls

    def test_simulated_mean_tracks_requested_edge(self):
        # The shift construction must make the POPULATION mean equal the edge.
        # Aggregate many independent histories and check the sample mean.
        edge_w = 0.05
        pnls = []
        for r in range(40):
            _, p = power_check.simulate_trades(
                260, date(2018, 1, 1), edge_w, np.random.default_rng(1000 + r))
            pnls.extend(p)
        got = float(np.mean(pnls))
        want = edge_w * power_check.W
        # ~12k trades; SD ~0.33W => SE ~ $0.6. 3-sigma tolerance.
        self.assertLess(abs(got - want), 2.0)

    def test_entry_dates_stay_inside_window(self):
        start = date(2023, 1, 2)
        entries, pnls = power_check.simulate_trades(
            104, start, 0.0, np.random.default_rng(7))
        self.assertEqual(len(entries), len(pnls))
        self.assertGreater(len(entries), 50)  # ~5/month across 5 names
        last = start.fromisoformat(max(entries))
        self.assertGreaterEqual(min(entries), start.isoformat())
        self.assertLess((last - start).days, 104 * 7)


class VerdictClassificationTests(unittest.TestCase):
    def test_classification_mirrors_scoreboard_gate_order(self):
        # losses gate fires BEFORE the cohort gate, exactly like scoreboard().
        self.assertEqual(power_check.classify(5, 2, float("nan"), float("nan")),
                         "INSUFF")
        self.assertEqual(power_check.classify(12, 2, float("nan"), float("nan")),
                         "INSUFF")
        self.assertEqual(power_check.classify(12, 5, 1.0, 9.0), "PASS")
        self.assertEqual(power_check.classify(12, 5, -9.0, -1.0), "FAIL")
        self.assertEqual(power_check.classify(12, 5, -1.0, 1.0), "NO-EDGE")

    def test_insufficient_sample_agrees_with_real_scoreboard(self):
        # 12 trades in 2 ISO weeks: enough losses is impossible (<10) AND <3
        # cohorts -- both the study and the real verdict path must refuse.
        trades = [{"pnl": -5.0, "capital_at_risk": 140.0,
                   "entry_date": "2021-01-04", "symbol": "SPY"}] * 6
        trades += [{"pnl": 5.0, "capital_at_risk": 140.0,
                    "entry_date": "2021-01-11", "symbol": "SPY"}] * 6
        s = scoreboard(trades, label="thin")
        self.assertIn("INSUFFICIENT SAMPLE", s["verdict"])
        self.assertEqual(power_check.classify(6, 2, *s["expectancy_CI90"]),
                         "INSUFF")


class StatsHelperTests(unittest.TestCase):
    def test_wilson_interval_known_values(self):
        lo, hi = power_check.wilson(0, 20)
        self.assertAlmostEqual(lo, 0.0, places=6)
        self.assertAlmostEqual(hi, 0.16113, places=4)
        lo, hi = power_check.wilson(10, 20)
        self.assertAlmostEqual(lo, 0.29929, places=4)
        self.assertAlmostEqual(hi, 0.70071, places=4)

    def test_measured_dependence_lands_near_config_concentration_flag(self):
        # config flags the universe as ~1.5 independent bets; the simulator's
        # cross-sectional dependence must land in that neighbourhood, not at
        # 5 (independent) or 1 (one bet).
        rho, n_eff = power_check.measure_dependence(n_pairs=20_000, seed=3)
        self.assertGreater(rho, 0.45)
        self.assertLess(rho, 0.75)
        self.assertGreater(n_eff, 1.2)
        self.assertLess(n_eff, 1.9)

    def test_derived_parameters_come_from_config(self):
        # every strategy-shaped number must trace to config (repo rule).
        self.assertEqual(power_check.W, config.A_SPREAD_WIDTH * 100.0)
        self.assertAlmostEqual(power_check.WIN_MEAN,
                               config.A_PROFIT_TARGET * power_check.CREDIT_FRAC)
        self.assertAlmostEqual(power_check.LOSS_MEAN,
                               -config.A_STOP_LOSS * power_check.CREDIT_FRAC)


if __name__ == "__main__":
    unittest.main()
