"""QM signal unit tests -- spec §8, offline, synthetic frames only.

Params are always injected explicitly; config stays None-scaffolded until the
owner types values (spec §7.1), and qm_params() must refuse loudly until then.
"""

import unittest
from unittest import mock

import pandas as pd

import config
from options_researcher import qm_signals

PARAMS = {
    "QM_RUN_LOOKBACK": 60,
    "QM_RUN_MIN_PCT": 0.30,
    "QM_BASE_MIN_DAYS": 10,
    "QM_BASE_MAX_DAYS": 40,
    "QM_BASE_MAX_DEPTH": 0.25,
    "QM_BASE_SMA": 20,
    "QM_VOL_DRYUP_RATIO": 0.65,
    "QM_PARA_LOOKBACK": 40,
    "QM_PARA_MIN_PCT": 1.00,
    "QM_PARA_GREEN_DAYS": 3,
    "QM_PARA_EXT_PCT": 0.50,
    "QM_PARA_SMA": 20,
    "QM_HORIZONS": (5, 10, 20),
    "QM_TRADABILITY_DTE": (30, 60),
}


def _frame(closes, highs=None, lows=None, volumes=None, start="2024-01-02"):
    n = len(closes)
    highs = highs if highs is not None else [c * 1.01 for c in closes]
    lows = lows if lows is not None else [c * 0.99 for c in closes]
    volumes = volumes if volumes is not None else [1_000_000.0] * n
    dates = [d.strftime("%Y-%m-%d") for d in pd.bdate_range(start, periods=n)]
    frame = pd.DataFrame(
        {
            "open": closes,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        },
        index=pd.Index(dates, name="date"),
        dtype=float,
    )
    return frame


def breakout_fixture(base_vol=500_000.0, trigger_close=146.0, base_days=15):
    """Run (100->139 over 59 sessions) -> one-day SMA-breaking shakeout dip ->
    flat tight base -> trigger.

    The dip pins the deterministic largest-L base search to exactly the flat
    base: any window reaching back past it contains a close below its own SMA.
    """
    run_closes = [100.0 + 40.0 * i / 59.0 for i in range(59)] + [130.0]
    run_vol = [2_000_000.0] * 60
    base_closes = [141.0] * base_days
    base_vols = [base_vol] * base_days
    closes = run_closes + base_closes + [trigger_close]
    highs = [c + 1.0 for c in closes]
    lows = [c - 1.0 for c in closes]
    vols = run_vol + base_vols + [3_000_000.0]
    return _frame(closes, highs, lows, vols)


class QmParamsTests(unittest.TestCase):
    def test_refuses_while_any_config_value_is_none(self):
        with self.assertRaises(RuntimeError) as ctx:
            qm_signals.qm_params()
        self.assertIn("QM_RUN_LOOKBACK", str(ctx.exception))
        self.assertIn("owner", str(ctx.exception).lower())

    def test_returns_dict_once_owner_values_exist(self):
        patchers = [
            mock.patch.object(config, name, PARAMS[name])
            for name in qm_signals.QM_PARAM_NAMES
        ]
        for p in patchers:
            p.start()
        try:
            params = qm_signals.qm_params()
        finally:
            for p in patchers:
                p.stop()
        self.assertEqual(params["QM_BASE_SMA"], 20)
        self.assertEqual(set(params), set(qm_signals.QM_PARAM_NAMES))


class BreakoutTests(unittest.TestCase):
    def test_fires_on_run_base_newhigh_fixture(self):
        frame = breakout_fixture()
        t = frame.index[-1]
        detail = qm_signals.breakout_detail(frame, t, PARAMS)
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail["t"], t)
        self.assertEqual(detail["base_end"], frame.index[-2])

    def test_refuses_without_new_high(self):
        frame = breakout_fixture(trigger_close=141.0)
        self.assertIsNone(qm_signals.breakout_detail(frame, frame.index[-1], PARAMS))

    def test_refuses_when_volume_not_drying(self):
        frame = breakout_fixture(base_vol=2_000_000.0)
        self.assertIsNone(qm_signals.breakout_detail(frame, frame.index[-1], PARAMS))

    def test_refuses_without_prior_run(self):
        frame = breakout_fixture()
        flat = [140.0] * 60
        frame.iloc[:60, frame.columns.get_loc("close")] = flat
        frame.iloc[:60, frame.columns.get_loc("open")] = flat
        frame.iloc[:60, frame.columns.get_loc("high")] = [c + 1.0 for c in flat]
        frame.iloc[:60, frame.columns.get_loc("low")] = [c - 1.0 for c in flat]
        self.assertIsNone(qm_signals.breakout_detail(frame, frame.index[-1], PARAMS))

    def test_refuses_when_base_too_deep(self):
        frame = breakout_fixture()
        # Crater one base session's low far below: depth blows past 0.25.
        crater = len(frame) - 8
        frame.iloc[crater, frame.columns.get_loc("low")] = 90.0
        self.assertIsNone(qm_signals.breakout_detail(frame, frame.index[-1], PARAMS))

    def test_refuses_when_a_base_close_slips_below_sma(self):
        # Declining base under a tight 5-day SMA: every late close < its SMA.
        run_closes = [100.0 + 40.0 * i / 59.0 for i in range(60)]
        base_closes = [140.0 - 1.5 * i for i in range(15)]
        closes = run_closes + base_closes + [146.0]
        vols = [2_000_000.0] * 60 + [500_000.0] * 15 + [3_000_000.0]
        frame = _frame(closes, [c + 1.0 for c in closes], [c - 1.0 for c in closes], vols)
        params = dict(PARAMS, QM_BASE_SMA=5)
        self.assertIsNone(qm_signals.breakout_detail(frame, frame.index[-1], params))

    def test_no_look_ahead_truncation_invariance(self):
        frame = breakout_fixture()
        extended = pd.concat([frame, _frame([200.0] * 5, start="2024-06-03")])
        t = frame.index[-1]
        self.assertEqual(
            qm_signals.breakout_detail(frame, t, PARAMS),
            qm_signals.breakout_detail(extended, t, PARAMS),
        )

    def test_scan_fires_once_per_base(self):
        frame = breakout_fixture()
        # Follow the trigger with more qualifying-looking up days.
        tail = _frame(
            [147.0, 148.0, 149.0],
            [148.0, 149.0, 150.0],
            [146.0, 147.0, 148.0],
            [3_000_000.0] * 3,
            start="2024-06-03",
        )
        fires = qm_signals.breakout_fires(pd.concat([frame, tail]), PARAMS)
        self.assertEqual(len(fires), 1)
        self.assertEqual(fires[0]["t"], frame.index[-1])

    def test_raises_on_unknown_session(self):
        frame = breakout_fixture()
        with self.assertRaises(ValueError):
            qm_signals.breakout_detail(frame, "2030-01-01", PARAMS)


def parabolic_fixture():
    """Flat 100s, then a vertical: doubles inside 40 sessions, 3 green closes."""
    flat = [100.0] * 50
    ramp = [110.0, 125.0, 140.0, 160.0, 185.0, 215.0, 250.0, 290.0, 340.0, 400.0]
    closes = flat + ramp
    return _frame(closes, [c + 2.0 for c in closes], [c - 2.0 for c in closes])


class ParabolicTests(unittest.TestCase):
    def test_fires_on_vertical_fixture(self):
        frame = parabolic_fixture()
        self.assertTrue(qm_signals.parabolic_qualifies(frame, frame.index[-1], PARAMS))

    def test_refuses_when_green_streak_broken(self):
        frame = parabolic_fixture()
        # Make t-1 a down close (340 -> 280) while gain/extension still hold.
        frame.iloc[-2, frame.columns.get_loc("close")] = 280.0
        self.assertFalse(qm_signals.parabolic_qualifies(frame, frame.index[-1], PARAMS))

    def test_refuses_when_extension_insufficient(self):
        frame = parabolic_fixture()
        params = dict(PARAMS, QM_PARA_EXT_PCT=5.0)
        self.assertFalse(qm_signals.parabolic_qualifies(frame, frame.index[-1], params))

    def test_refuses_when_gain_insufficient(self):
        frame = parabolic_fixture()
        params = dict(PARAMS, QM_PARA_MIN_PCT=50.0)
        self.assertFalse(qm_signals.parabolic_qualifies(frame, frame.index[-1], params))

    def test_refuses_on_thin_history(self):
        frame = parabolic_fixture().iloc[-10:]
        self.assertFalse(qm_signals.parabolic_qualifies(frame, frame.index[-1], PARAMS))

    def test_no_look_ahead_truncation_invariance(self):
        frame = parabolic_fixture()
        extended = pd.concat([frame, _frame([50.0] * 5, start="2024-06-03")])
        t = frame.index[-1]
        self.assertEqual(
            qm_signals.parabolic_qualifies(frame, t, PARAMS),
            qm_signals.parabolic_qualifies(extended, t, PARAMS),
        )

    def test_streak_counts_once_and_refires_after_gap(self):
        frame = parabolic_fixture()
        # Two more green closes extend the qualifying streak, then a hard
        # two-day drop (streak broken), then a fresh vertical qualifies again.
        tail = _frame(
            [430.0, 460.0, 300.0, 290.0, 340.0, 400.0, 470.0],
            [432.0, 462.0, 302.0, 292.0, 342.0, 402.0, 472.0],
            [428.0, 458.0, 298.0, 288.0, 338.0, 398.0, 468.0],
            start="2024-06-03",
        )
        combined = pd.concat([frame, tail])
        fires = qm_signals.parabolic_fires(combined, PARAMS)
        first_qualifying = next(
            t for t in frame.index if qm_signals.parabolic_qualifies(frame, t, PARAMS)
        )
        self.assertEqual(fires, [first_qualifying, tail.index[-1]])


if __name__ == "__main__":
    unittest.main()
