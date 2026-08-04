"""tests/test_composite_signals.py -- offline synthetic-data tests for the
composite signal lane (options_researcher/composite_signals.py).

Fully offline: synthetic pd.Series/pd.DataFrame fixtures only, plus a
tempfile.TemporaryDirectory for the derived-series persistence tests. No real
cache reads. Chain fixtures use real monthly expirations (via chains.
third_friday, the same calendar rule the production code uses) so
nearest_monthly/atm_row behave exactly as they do on real data.
"""
from __future__ import annotations

import math
import unittest
from datetime import date
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

import config
from options_researcher import composite_signals as cs
from options_researcher.chains import third_friday

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TREND_KEYS = {
    "state", "data_blocked", "reason", "ema_slow", "ema_medium", "tsmom",
    "vote_close_above_ema_slow", "vote_medium_above_slow",
    "vote_tsmom_positive", "aligned_votes",
}
VOL_PREMIUM_KEYS = {
    "state", "data_blocked", "reason", "gap", "gap_pctl", "term_slope",
    "structure_preference",
}
REGIME_KEYS = {
    "state", "data_blocked", "reason", "label", "label_frequency",
    "high_dispersion", "size_context", "as_of",
}
INTERNALS_KEYS = {
    "state", "data_blocked", "reason", "oi_delta_call", "oi_delta_put",
    "oi_change_status_call", "oi_change_status_put", "direction_agreement",
    "skew_25d", "skew_pctl", "steep_skew", "liquidity_ok",
}
CARD_KEYS = {
    "symbol", "asof", "max_asof", "grade", "aligned_count",
    "trend", "vol_premium", "regime", "internals",
}


def series(values) -> pd.Series:
    idx = pd.bdate_range("2023-01-02", periods=len(values))
    return pd.Series(np.asarray(values, dtype=float), index=idx)


def _monthly_on_or_after(start: date, min_dte: int, max_dte: int) -> date:
    """Smallest REAL monthly expiration (3rd Friday, via the production
    calendar rule) inside [min_dte, max_dte] DTE of `start`. Test-only
    convenience -- reuses chains.third_friday rather than hand-picking
    calendar dates, so fixtures always land where nearest_monthly expects."""
    for months_ahead in range(0, 8):
        year = start.year + (start.month - 1 + months_ahead) // 12
        month = (start.month - 1 + months_ahead) % 12 + 1
        tf = third_friday(year, month)
        dte = (tf - start).days
        if min_dte <= dte <= max_dte:
            return tf
    raise AssertionError(f"no monthly expiration in [{min_dte},{max_dte}] DTE of {start}")


_CHAIN_ROW_DEFAULTS = {"gamma": 0.01, "theta": -0.01, "vega": 0.1}


def _chain_for_day(day: date, *, near_iv: float = 0.30, far_iv: float = 0.32,
                   skew: float = 0.0, call_oi: int = 500,
                   put_oi: int = 500) -> pd.DataFrame:
    """One realistic cached-chain day: 0.50-delta near put/call (ATM), a
    0.50-delta far put (term structure), and 0.25-delta near put/call (skew).
    `skew` shifts the near put IV up and the near 0.25-delta put IV up by
    twice as much, so a positive `skew` produces a positive skew_25d."""
    near_exp = _monthly_on_or_after(day, *config.COMPOSITE_TERM_NEAR_DTE).isoformat()
    far_exp = _monthly_on_or_after(day, *config.COMPOSITE_TERM_FAR_DTE).isoformat()
    rows = [
        {"expiration": near_exp, "strike": 100.0, "right": "P", "bid": 2.00,
         "ask": 2.05, "open_interest": put_oi, "iv": near_iv,
         "delta": -0.50, **_CHAIN_ROW_DEFAULTS},
        {"expiration": near_exp, "strike": 100.0, "right": "C", "bid": 2.00,
         "ask": 2.05, "open_interest": call_oi, "iv": near_iv,
         "delta": 0.50, **_CHAIN_ROW_DEFAULTS},
        {"expiration": near_exp, "strike": 90.0, "right": "P", "bid": 1.00,
         "ask": 1.03, "open_interest": 300, "iv": near_iv + skew,
         "delta": -0.25, **_CHAIN_ROW_DEFAULTS},
        {"expiration": near_exp, "strike": 110.0, "right": "C", "bid": 1.00,
         "ask": 1.03, "open_interest": 300, "iv": near_iv,
         "delta": 0.25, **_CHAIN_ROW_DEFAULTS},
        {"expiration": far_exp, "strike": 100.0, "right": "P", "bid": 2.50,
         "ask": 2.58, "open_interest": 300, "iv": far_iv,
         "delta": -0.50, **_CHAIN_ROW_DEFAULTS},
    ]
    return pd.DataFrame(rows)


def _gap_window(final_value: float, size: int = config.COMPOSITE_PCTL_MIN_OBS) -> pd.Series:
    """A trailing history window of `size` observations ending in
    `final_value`: ascending [1..size-1] followed by `final_value` as the
    LAST (today's own) observation. Gives an exactly-reasoned inclusive-rank
    percentile: pctl = (count of the size-1 fixed values <= final_value,
    plus 1 for final_value itself) / size."""
    base = list(range(1, size))
    values = base + [final_value]
    idx = pd.bdate_range("2023-01-02", periods=len(values))
    return pd.Series(values, index=idx, dtype=float)


def _derived_frame(gap_window: pd.Series, *, near_iv: float = 0.30,
                   far_iv: float = 0.32) -> pd.DataFrame:
    idx = gap_window.index
    return pd.DataFrame({
        "atm_iv_near": near_iv, "atm_iv_far": far_iv,
        "rv": 0.0, "gap": gap_window, "skew_25d": 0.0,
    }, index=idx)


# ---------------------------------------------------------------------------
# Angle 1 -- TREND
# ---------------------------------------------------------------------------

class TrendAngleTest(unittest.TestCase):
    def test_key_contract(self):
        snap = cs.trend_angle(series(np.full(300, 100.0)))
        self.assertEqual(set(snap.keys()), TREND_KEYS)

    def test_monotone_uptrend_is_up(self):
        result = cs.trend_angle(series(np.linspace(100.0, 250.0, 400)))
        self.assertEqual(result["state"], "UP")
        self.assertEqual(result["aligned_votes"], 3)
        self.assertTrue(result["vote_close_above_ema_slow"])
        self.assertTrue(result["vote_medium_above_slow"])
        self.assertTrue(result["vote_tsmom_positive"])
        self.assertGreater(result["tsmom"], 0.0)
        self.assertFalse(result["data_blocked"])

    def test_monotone_downtrend_is_down(self):
        result = cs.trend_angle(series(np.linspace(250.0, 100.0, 400)))
        self.assertEqual(result["state"], "DOWN")
        self.assertEqual(result["aligned_votes"], 0)
        self.assertFalse(result["vote_close_above_ema_slow"])
        self.assertFalse(result["vote_medium_above_slow"])
        self.assertFalse(result["vote_tsmom_positive"])
        self.assertLess(result["tsmom"], 0.0)

    def test_flat_series_reads_down_zero_of_three(self):
        # A dead-flat series meets none of the three STRICT ">" votes
        # (close==ema_slow, ema_medium==ema_slow, tsmom==0), so it is 0/3,
        # not a separate "flat" bucket -- pins the literal vote-count rule.
        result = cs.trend_angle(series(np.full(400, 100.0)))
        self.assertEqual(result["state"], "DOWN")
        self.assertEqual(result["aligned_votes"], 0)
        self.assertAlmostEqual(result["tsmom"], 0.0)

    def test_mixed_when_votes_split(self):
        # A long decline (defines a LOW t-252 anchor and pulls ema_slow down)
        # followed by a sharp late rally: the rally lifts the last close
        # above ema_slow (vote 1 True) while the [t-252..t-21] window is
        # still net-negative (tsmom vote False) -- verified empirically to
        # land on exactly one of the three votes, i.e. MIXED.
        n = 260
        vals = np.empty(n)
        vals[:8] = 200.0
        vals[7:239] = np.linspace(200.0, 100.0, 239 - 7)
        vals[239:260] = np.linspace(100.0, 180.0, 260 - 239)
        result = cs.trend_angle(series(vals))
        self.assertEqual(result["state"], "MIXED")
        self.assertEqual(result["aligned_votes"], 1)
        self.assertTrue(result["vote_close_above_ema_slow"])
        self.assertFalse(result["vote_medium_above_slow"])
        self.assertFalse(result["vote_tsmom_positive"])

    def test_insufficient_history_blocked(self):
        result = cs.trend_angle(series(np.full(199, 100.0)))
        self.assertTrue(result["data_blocked"])
        self.assertEqual(result["state"], "DATA_BLOCKED")
        self.assertTrue(math.isnan(result["ema_slow"]))
        self.assertTrue(math.isnan(result["tsmom"]))
        self.assertFalse(result["vote_tsmom_positive"])
        self.assertEqual(result["aligned_votes"], 0)
        # Exactly COMPOSITE_EMA_SLOW closes clears the gate (not blocked).
        ok = cs.trend_angle(series(np.linspace(80.0, 120.0, config.COMPOSITE_EMA_SLOW)))
        self.assertFalse(ok["data_blocked"])

    def test_empty_series_does_not_raise(self):
        result = cs.trend_angle(pd.Series(dtype=float))
        self.assertEqual(set(result.keys()), TREND_KEYS)
        self.assertTrue(result["data_blocked"])

    def test_tsmom_skips_the_most_recent_month(self):
        # t-252 anchor = 100.0, ramps to 150.0 exactly AT t-21, then the
        # final 21 sessions (strictly after t-21) crash to 80.0. A correct
        # skip-month tsmom reads ONLY the 100 -> 150 leg (+50%) and is
        # blind to the crash; a naive (no-skip) implementation would not be.
        n = 260
        vals = np.empty(n)
        vals[:8] = 100.0
        vals[7:239] = np.linspace(100.0, 150.0, 239 - 7)  # ends at index 238 = t-21
        vals[239:260] = np.linspace(150.0, 80.0, 260 - 239)  # after t-21, must be ignored
        result = cs.trend_angle(series(vals))
        self.assertAlmostEqual(result["tsmom"], 0.5, places=6)
        self.assertTrue(result["vote_tsmom_positive"])

    def test_tsmom_nan_when_short_of_lookback_but_ema_settled(self):
        # Between COMPOSITE_EMA_SLOW (200) and COMPOSITE_TSMOM_LOOKBACK+1
        # (253) closes: the angle is NOT data_blocked (EMAs are settled),
        # but tsmom cannot be computed and degrades to NaN/False rather than
        # raising -- so the state can reach MIXED but never UP.
        n = 220
        self.assertTrue(config.COMPOSITE_EMA_SLOW <= n < config.COMPOSITE_TSMOM_LOOKBACK + 1)
        result = cs.trend_angle(series(np.linspace(100.0, 200.0, n)))
        self.assertFalse(result["data_blocked"])
        self.assertTrue(math.isnan(result["tsmom"]))
        self.assertFalse(result["vote_tsmom_positive"])
        self.assertNotEqual(result["state"], "UP")


# ---------------------------------------------------------------------------
# Angle 2 -- VOLATILITY PREMIUM
# ---------------------------------------------------------------------------

class VolPremiumAngleTest(unittest.TestCase):
    def test_key_contract(self):
        result = cs.vol_premium_angle(_derived_frame(_gap_window(63)))
        self.assertEqual(set(result.keys()), VOL_PREMIUM_KEYS)

    def test_blocked_when_no_derived_series(self):
        for empty in (None, pd.DataFrame()):
            result = cs.vol_premium_angle(empty)
            self.assertTrue(result["data_blocked"])
            self.assertEqual(result["state"], "DATA_BLOCKED")
            self.assertIsNone(result["structure_preference"])

    def test_blocked_when_gap_is_nan(self):
        derived = _derived_frame(_gap_window(63))
        derived.loc[derived.index[-1], "gap"] = float("nan")
        result = cs.vol_premium_angle(derived)
        self.assertTrue(result["data_blocked"])
        self.assertTrue(math.isnan(result["gap"]))

    def test_blocked_on_insufficient_percentile_history_but_gap_survives(self):
        # Only 100 obs (< COMPOSITE_PCTL_MIN_OBS=126): the STATE blocks, but
        # the raw gap and term_slope still surface (fail-visible, not
        # all-or-nothing).
        derived = _derived_frame(_gap_window(50, size=100))
        result = cs.vol_premium_angle(derived)
        self.assertTrue(result["data_blocked"])
        self.assertAlmostEqual(result["gap"], 50.0)
        self.assertTrue(math.isnan(result["gap_pctl"]))
        self.assertAlmostEqual(result["term_slope"], 0.02, places=6)

    def test_tercile_boundaries(self):
        # size=126 (exactly COMPOSITE_PCTL_MIN_OBS): pctl = (rank-among-
        # [1..125] that are <= final, +1 for final itself) / 126.
        cases = [
            (126, "RICH"),   # 126/126 = 1.000 -- max, clearly rich
            (90, "RICH"),    # 91/126 = 0.722 >= 0.667
            (80, "NEUTRAL"), # 81/126 = 0.643 -- just below the rich boundary
            (63, "NEUTRAL"), # 64/126 = 0.508 -- middle
            (45, "NEUTRAL"), # 46/126 = 0.365 -- just above the cheap boundary
            (35, "CHEAP"),   # 36/126 = 0.286 <= 0.333
            (0, "CHEAP"),    # 1/126 = 0.008 -- min, clearly cheap
        ]
        for final_value, expected_state in cases:
            derived = _derived_frame(_gap_window(final_value))
            result = cs.vol_premium_angle(derived)
            self.assertEqual(result["state"], expected_state,
                             f"final_value={final_value} pctl={result['gap_pctl']}")
            self.assertFalse(result["data_blocked"])
        self.assertEqual(
            cs.vol_premium_angle(_derived_frame(_gap_window(126)))["structure_preference"],
            "credit-side")
        self.assertEqual(
            cs.vol_premium_angle(_derived_frame(_gap_window(0)))["structure_preference"],
            "debit-side")
        self.assertEqual(
            cs.vol_premium_angle(_derived_frame(_gap_window(63)))["structure_preference"],
            "either")

    def test_term_slope_sign(self):
        contango = cs.vol_premium_angle(
            _derived_frame(_gap_window(63), near_iv=0.30, far_iv=0.35))
        self.assertAlmostEqual(contango["term_slope"], 0.05, places=6)
        backwardation = cs.vol_premium_angle(
            _derived_frame(_gap_window(63), near_iv=0.35, far_iv=0.30))
        self.assertAlmostEqual(backwardation["term_slope"], -0.05, places=6)


# ---------------------------------------------------------------------------
# Angle 3 -- REGIME
# ---------------------------------------------------------------------------

class RegimeAngleTest(unittest.TestCase):
    def test_key_contract_blocked(self):
        result = cs.regime_angle(series(np.full(50, 100.0)))
        self.assertEqual(set(result.keys()), REGIME_KEYS)
        self.assertTrue(result["data_blocked"])
        self.assertEqual(result["state"], "DATA_BLOCKED")
        self.assertIsNone(result["label"])
        self.assertFalse(result["high_dispersion"])

    def test_produces_a_label_with_enough_history(self):
        min_rows = (config.REGIME_WINDOW_DAYS
                   + config.REGIME_MIN_FIT_WINDOWS * config.REGIME_STEP_DAYS)
        n = min_rows + 80
        rng = np.random.default_rng(3)
        closes = 100.0 * np.exp(np.cumsum(rng.normal(0.0002, 0.012, n)))
        result = cs.regime_angle(series(closes))
        self.assertEqual(set(result.keys()), REGIME_KEYS)
        self.assertFalse(result["data_blocked"])
        self.assertIn(result["state"], ("TYPICAL", "HIGH_DISPERSION"))
        self.assertIsInstance(result["label"], int)
        self.assertTrue(0.0 < result["label_frequency"] <= 1.0)
        self.assertIsNotNone(result["as_of"])
        self.assertIn("historical", result["size_context"])


# ---------------------------------------------------------------------------
# Angle 4 -- OPTIONS-MARKET INTERNALS
# ---------------------------------------------------------------------------

class InternalsAngleTest(unittest.TestCase):
    TODAY = date(2024, 3, 4)  # a stable, month-boundary-safe Monday

    def _chains(self, *, call_oi_today, call_oi_prior, put_oi_today,
               put_oi_prior, skew=0.0):
        today_chain = _chain_for_day(self.TODAY, call_oi=call_oi_today,
                                     put_oi=put_oi_today, skew=skew)
        prior_chain = _chain_for_day(self.TODAY, call_oi=call_oi_prior,
                                     put_oi=put_oi_prior)
        return today_chain, prior_chain

    def test_key_contract(self):
        today_chain, prior_chain = self._chains(
            call_oi_today=600, call_oi_prior=500,
            put_oi_today=500, put_oi_prior=500)
        result = cs.internals_angle(today_chain, prior_chain, "UP",
                                    today=self.TODAY, prior_gap_days=1)
        self.assertEqual(set(result.keys()), INTERNALS_KEYS)

    def test_blocked_no_chain(self):
        for blocked_chain in (None, pd.DataFrame()):
            result = cs.internals_angle(blocked_chain, None, "UP", today=self.TODAY)
            self.assertTrue(result["data_blocked"])
            self.assertEqual(result["state"], "DATA_BLOCKED")

    def test_blocked_no_near_expiration(self):
        # A chain with only a wildly-out-of-band expiration (e.g. 400 DTE).
        far_off = (self.TODAY.replace(year=self.TODAY.year + 1)).isoformat()
        chain = pd.DataFrame([
            {"expiration": far_off, "strike": 100.0, "right": "P", "bid": 1.0,
             "ask": 1.05, "open_interest": 500, "iv": 0.30, "delta": -0.5,
             **_CHAIN_ROW_DEFAULTS},
        ])
        result = cs.internals_angle(chain, None, "UP", today=self.TODAY)
        self.assertTrue(result["data_blocked"])
        self.assertIn("near-tenor", result["reason"])

    def test_veto_on_illiquid_leg(self):
        # call OI below MIN_OPEN_INTEREST -> liquidity fails -> VETO,
        # regardless of a same-direction OI move.
        self.assertLess(50, config.MIN_OPEN_INTEREST)
        today_chain, prior_chain = self._chains(
            call_oi_today=50, call_oi_prior=40,
            put_oi_today=500, put_oi_prior=500)
        result = cs.internals_angle(today_chain, prior_chain, "UP",
                                    today=self.TODAY, prior_gap_days=1)
        self.assertEqual(result["state"], "VETO")
        self.assertFalse(result["liquidity_ok"])

    def test_confirm_on_up_agreement(self):
        # call OI +100, put OI +0 -> diff=+100>0 -> agrees with UP.
        today_chain, prior_chain = self._chains(
            call_oi_today=600, call_oi_prior=500,
            put_oi_today=500, put_oi_prior=500)
        result = cs.internals_angle(today_chain, prior_chain, "UP",
                                    today=self.TODAY, prior_gap_days=1)
        self.assertEqual(result["oi_delta_call"], 100)
        self.assertEqual(result["oi_delta_put"], 0)
        self.assertTrue(result["direction_agreement"])
        self.assertEqual(result["state"], "CONFIRM")
        self.assertTrue(result["liquidity_ok"])

    def test_confirm_on_down_agreement(self):
        # put OI +100, call OI +0 -> diff=-100<0 -> agrees with DOWN.
        today_chain, prior_chain = self._chains(
            call_oi_today=500, call_oi_prior=500,
            put_oi_today=600, put_oi_prior=500)
        result = cs.internals_angle(today_chain, prior_chain, "DOWN",
                                    today=self.TODAY, prior_gap_days=1)
        self.assertTrue(result["direction_agreement"])
        self.assertEqual(result["state"], "CONFIRM")

    def test_neutral_on_disagreement(self):
        # trend UP but put OI grew relative to call OI -> diff<0 -> disagree.
        today_chain, prior_chain = self._chains(
            call_oi_today=500, call_oi_prior=500,
            put_oi_today=600, put_oi_prior=500)
        result = cs.internals_angle(today_chain, prior_chain, "UP",
                                    today=self.TODAY, prior_gap_days=1)
        self.assertFalse(result["direction_agreement"])
        self.assertEqual(result["state"], "NEUTRAL")

    def test_neutral_on_mixed_trend(self):
        today_chain, prior_chain = self._chains(
            call_oi_today=600, call_oi_prior=500,
            put_oi_today=500, put_oi_prior=500)
        result = cs.internals_angle(today_chain, prior_chain, "MIXED",
                                    today=self.TODAY, prior_gap_days=1)
        self.assertFalse(result["direction_agreement"])
        self.assertEqual(result["state"], "NEUTRAL")

    @staticmethod
    def _skew_history_ranking_top(final_value: float) -> pd.Series:
        """A trailing skew-history window whose LAST (today's own) value is
        the clear maximum -- COMPOSITE_PCTL_MIN_OBS-1 small values well
        below `final_value`, then `final_value` itself. Distinct from
        _gap_window (which uses ascending integer placeholders unsuitable
        for a small IV-scale value like a skew of 0.20)."""
        n = config.COMPOSITE_PCTL_MIN_OBS
        values = [0.01] * (n - 1) + [final_value]
        idx = pd.bdate_range("2023-01-02", periods=n)
        return pd.Series(values, index=idx, dtype=float)

    def test_steep_skew_suppresses_confirm_while_up(self):
        today_chain, prior_chain = self._chains(
            call_oi_today=600, call_oi_prior=500,
            put_oi_today=500, put_oi_prior=500, skew=0.20)
        # skew_25d for this fixture is near_iv(0.25d put)-near_iv(0.25d call)
        # = (0.30+0.20) - 0.30 = 0.20; rank it at the top of its own history.
        skew_history = self._skew_history_ranking_top(0.20)
        result = cs.internals_angle(
            today_chain, prior_chain, "UP", today=self.TODAY,
            prior_gap_days=1, skew_history=skew_history)
        self.assertTrue(result["direction_agreement"])
        self.assertTrue(result["steep_skew"])
        self.assertEqual(result["state"], "NEUTRAL")

    def test_steep_skew_does_not_suppress_confirm_while_down(self):
        today_chain, prior_chain = self._chains(
            call_oi_today=500, call_oi_prior=500,
            put_oi_today=600, put_oi_prior=500, skew=0.20)
        skew_history = self._skew_history_ranking_top(0.20)
        result = cs.internals_angle(
            today_chain, prior_chain, "DOWN", today=self.TODAY,
            prior_gap_days=1, skew_history=skew_history)
        self.assertTrue(result["direction_agreement"])
        self.assertTrue(result["steep_skew"])
        self.assertEqual(result["state"], "CONFIRM")

    def test_missing_skew_history_degrades_not_blocks(self):
        today_chain, prior_chain = self._chains(
            call_oi_today=600, call_oi_prior=500,
            put_oi_today=500, put_oi_prior=500)
        result = cs.internals_angle(today_chain, prior_chain, "UP",
                                    today=self.TODAY, prior_gap_days=1,
                                    skew_history=None)
        self.assertFalse(result["data_blocked"])
        self.assertTrue(math.isnan(result["skew_pctl"]))
        self.assertFalse(result["steep_skew"])
        self.assertEqual(result["state"], "CONFIRM")


# ---------------------------------------------------------------------------
# Composition: aligned_count / confluence_grade
# ---------------------------------------------------------------------------

def _trend(state: str, blocked: bool = False) -> dict:
    return {"state": state, "data_blocked": blocked}


def _vol(state: str, blocked: bool = False) -> dict:
    return {"state": state, "data_blocked": blocked}


def _regime(high_dispersion: bool, blocked: bool = False) -> dict:
    return {"high_dispersion": high_dispersion, "data_blocked": blocked}


def _internals(state: str, blocked: bool = False) -> dict:
    return {"state": state, "data_blocked": blocked}


class AlignedCountTest(unittest.TestCase):
    def test_no_direction_is_always_zero(self):
        for trend_state in ("MIXED", "DATA_BLOCKED"):
            blocked = trend_state == "DATA_BLOCKED"
            count = cs.aligned_count(
                _trend(trend_state, blocked), _vol("CHEAP"),
                _regime(False), _internals("CONFIRM"))
            self.assertEqual(count, 0)

    def test_trend_alone_contributes_one(self):
        count = cs.aligned_count(
            _trend("UP"), _vol("NEUTRAL"), _regime(True), _internals("NEUTRAL"))
        self.assertEqual(count, 1)

    def test_vol_premium_only_cheap_contributes(self):
        base = (_trend("UP"), _regime(True), _internals("NEUTRAL"))
        self.assertEqual(cs.aligned_count(base[0], _vol("CHEAP"), *base[1:]), 2)
        self.assertEqual(cs.aligned_count(base[0], _vol("RICH"), *base[1:]), 1)
        self.assertEqual(cs.aligned_count(base[0], _vol("NEUTRAL"), *base[1:]), 1)
        self.assertEqual(
            cs.aligned_count(base[0], _vol("CHEAP", blocked=True), *base[1:]), 1)

    def test_regime_only_not_high_dispersion_contributes(self):
        base = (_trend("UP"), _vol("NEUTRAL"), _internals("NEUTRAL"))
        self.assertEqual(cs.aligned_count(base[0], base[1], _regime(False), base[2]), 2)
        self.assertEqual(cs.aligned_count(base[0], base[1], _regime(True), base[2]), 1)
        self.assertEqual(
            cs.aligned_count(base[0], base[1], _regime(False, blocked=True), base[2]), 1)

    def test_internals_only_confirm_contributes(self):
        base = (_trend("UP"), _vol("NEUTRAL"), _regime(True))
        self.assertEqual(cs.aligned_count(*base, _internals("CONFIRM")), 2)
        self.assertEqual(cs.aligned_count(*base, _internals("NEUTRAL")), 1)
        self.assertEqual(cs.aligned_count(*base, _internals("VETO")), 1)
        self.assertEqual(
            cs.aligned_count(*base, _internals("CONFIRM", blocked=True)), 1)

    def test_all_four_align(self):
        count = cs.aligned_count(
            _trend("UP"), _vol("CHEAP"), _regime(False), _internals("CONFIRM"))
        self.assertEqual(count, 4)

    def test_down_trend_symmetric(self):
        count = cs.aligned_count(
            _trend("DOWN"), _vol("CHEAP"), _regime(False), _internals("CONFIRM"))
        self.assertEqual(count, 4)


class ConfluenceGradeTest(unittest.TestCase):
    """Grade logic table: every branch of confluence_grade."""

    def test_four_aligned_is_a(self):
        grade, count = cs.confluence_grade(
            _trend("UP"), _vol("CHEAP"), _regime(False), _internals("CONFIRM"))
        self.assertEqual((grade, count), ("A", 4))

    def test_exactly_three_aligned_is_a(self):
        grade, count = cs.confluence_grade(
            _trend("UP"), _vol("RICH"), _regime(False), _internals("CONFIRM"))
        self.assertEqual((grade, count), ("A", 3))

    def test_exactly_two_aligned_is_b(self):
        grade, count = cs.confluence_grade(
            _trend("UP"), _vol("RICH"), _regime(True), _internals("CONFIRM"))
        self.assertEqual((grade, count), ("B", 2))

    def test_one_aligned_is_c(self):
        grade, count = cs.confluence_grade(
            _trend("UP"), _vol("RICH"), _regime(True), _internals("NEUTRAL"))
        self.assertEqual((grade, count), ("C", 1))

    def test_mixed_trend_is_c(self):
        grade, count = cs.confluence_grade(
            _trend("MIXED"), _vol("CHEAP"), _regime(False), _internals("CONFIRM"))
        self.assertEqual((grade, count), ("C", 0))

    def test_data_blocked_trend_is_c(self):
        grade, count = cs.confluence_grade(
            _trend("DATA_BLOCKED", blocked=True), _vol("CHEAP"), _regime(False),
            _internals("CONFIRM"))
        self.assertEqual((grade, count), ("C", 0))

    def test_veto_caps_grade_at_c_even_with_four_aligned(self):
        grade, count = cs.confluence_grade(
            _trend("UP"), _vol("CHEAP"), _regime(False), _internals("VETO"))
        self.assertEqual(grade, "C")
        # aligned_count itself is unaffected by VETO (VETO never contributes
        # to the count in the first place, so this is already 3, not 4).
        self.assertEqual(count, 3)


# ---------------------------------------------------------------------------
# Full pipeline -- confluence_card
# ---------------------------------------------------------------------------

class ConfluenceCardTest(unittest.TestCase):
    def _closes_and_chains(self, n_closes: int = 320, n_chain_days: int = 8,
                           base: str = "2023-06-01"):
        idx = pd.bdate_range(base, periods=n_closes)
        rng = np.random.default_rng(11)
        vals = 100.0 * np.exp(np.cumsum(rng.normal(0.0004, 0.01, n_closes)))
        closes = pd.Series(vals, index=[d.date().isoformat() for d in idx])
        chain_days = [d.date() for d in idx[-n_chain_days:]]
        chains = {d.isoformat(): _chain_for_day(d, call_oi=500 + i * 5,
                                                 put_oi=500)
                  for i, d in enumerate(chain_days)}
        return closes, chains

    def test_key_contract(self):
        closes, chains = self._closes_and_chains()
        asof = closes.index[-1]
        with TemporaryDirectory() as tmp:
            card = cs.confluence_card("TEST", asof, closes=closes,
                                      chains=chains, cache_dir=tmp)
        self.assertEqual(set(card.keys()), CARD_KEYS)
        self.assertEqual(set(card["trend"].keys()), TREND_KEYS)
        self.assertEqual(set(card["vol_premium"].keys()), VOL_PREMIUM_KEYS)
        self.assertEqual(set(card["regime"].keys()), REGIME_KEYS)
        self.assertEqual(set(card["internals"].keys()), INTERNALS_KEYS)
        self.assertIn(card["grade"], ("A", "B", "C"))

    def test_max_asof_is_max_of_input_sessions(self):
        closes, chains = self._closes_and_chains()
        asof = closes.index[-1]
        with TemporaryDirectory() as tmp:
            card = cs.confluence_card("TEST", asof, closes=closes,
                                      chains=chains, cache_dir=tmp)
        candidates = [closes.index[-1], sorted(chains)[-1]]
        self.assertEqual(card["max_asof"], max(candidates))
        self.assertLessEqual(card["max_asof"], asof)

    def test_fully_blocked_symbol_still_produces_a_well_formed_card(self):
        empty_closes = pd.Series(dtype=float)
        card = cs.confluence_card("TEST", "2024-01-02", closes=empty_closes,
                                  chains={}, cache_dir="/tmp/does-not-matter")
        self.assertEqual(set(card.keys()), CARD_KEYS)
        self.assertEqual(card["grade"], "C")
        self.assertEqual(card["aligned_count"], 0)
        for angle_name in ("trend", "vol_premium", "regime", "internals"):
            self.assertTrue(card[angle_name]["data_blocked"], angle_name)

    def test_no_look_ahead_invariance(self):
        """THE key property: a card computed at session T from the FULL
        series (which extends past T) must be byte-identical to a card
        computed from the series/chains TRUNCATED at T. Future-dated rows,
        wherever they appear in the input, can never change the result."""
        closes, chains = self._closes_and_chains(n_closes=320, n_chain_days=6,
                                                  base="2023-06-01")
        asof_index = 260
        asof = closes.index[asof_index]

        # Extend both closes AND chains with deliberately distinguishing
        # "future" rows dated AFTER asof, so a look-ahead leak would change
        # the result if the module ever read them.
        future_days = pd.bdate_range(
            pd.Timestamp(asof) + pd.Timedelta(days=3), periods=10)
        future_closes = pd.Series(
            [10_000.0] * len(future_days),
            index=[d.date().isoformat() for d in future_days])
        full_closes = pd.concat([closes, future_closes])

        future_chain_days = [d.date() for d in future_days[:3]]
        future_chains = {
            d.isoformat(): _chain_for_day(d, near_iv=9.0, far_iv=9.0,
                                          call_oi=999_999, put_oi=999_999)
            for d in future_chain_days
        }
        full_chains = {**chains, **future_chains}

        truncated_closes = closes.loc[:asof]
        truncated_chains = {d: c for d, c in chains.items() if d <= asof}

        with TemporaryDirectory() as tmp_full, TemporaryDirectory() as tmp_trunc:
            card_from_full = cs.confluence_card(
                "TEST", asof, closes=full_closes, chains=full_chains,
                cache_dir=tmp_full)
            card_from_truncated = cs.confluence_card(
                "TEST", asof, closes=truncated_closes, chains=truncated_chains,
                cache_dir=tmp_trunc)

        self.assertEqual(card_from_full, card_from_truncated)
        # Sanity: the fixture actually has history past asof (a vacuous pass
        # would mean this test proves nothing).
        self.assertGreater(len(full_closes), len(truncated_closes))
        self.assertGreater(len(full_chains), len(truncated_chains))


# ---------------------------------------------------------------------------
# Percentile-history persistence
# ---------------------------------------------------------------------------

class BuildDerivedSeriesTest(unittest.TestCase):
    def _closes(self, n=80, base="2023-09-01"):
        idx = pd.bdate_range(base, periods=n)
        rng = np.random.default_rng(5)
        vals = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, n)))
        return pd.Series(vals, index=[d.date().isoformat() for d in idx])

    def test_persisted_columns_and_metadata(self):
        closes = self._closes()
        days = [date.fromisoformat(d) for d in list(closes.index)[-4:]]
        chains = {d.isoformat(): _chain_for_day(d) for d in days}
        asof = days[-1].isoformat()
        with TemporaryDirectory() as tmp:
            derived = cs.build_derived_series(
                "TEST", closes=closes, chains=chains, asof=asof, cache_dir=tmp)
            self.assertEqual(len(derived), 4)
            self.assertEqual(set(derived.columns), set(cs.DERIVED_COLUMNS))

            import json
            import os

            on_disk = pd.read_parquet(os.path.join(tmp, "TEST.parquet"))
            self.assertEqual(list(on_disk.columns),
                             ["session", *cs.DERIVED_COLUMNS])
            with open(os.path.join(tmp, "TEST.meta.json")) as fh:
                meta = json.load(fh)
            self.assertEqual(meta["method_version"], cs.DERIVED_METHOD_VERSION)
            self.assertEqual(meta["max_asof"], asof)

    def test_incremental_append_only_computes_missing_sessions(self):
        closes = self._closes()
        all_days = [date.fromisoformat(d) for d in list(closes.index)[-6:]]
        first_days, later_days = all_days[:4], all_days[4:]

        with TemporaryDirectory() as tmp:
            first_chains = {d.isoformat(): _chain_for_day(d) for d in first_days}
            first = cs.build_derived_series(
                "TEST", closes=closes, chains=first_chains,
                asof=first_days[-1].isoformat(), cache_dir=tmp)
            self.assertEqual(len(first), 4)

            # Second call's `chains` dict deliberately OMITS the first four
            # days -- if the implementation tried to recompute an
            # already-stored session it would KeyError here.
            second_chains = {d.isoformat(): _chain_for_day(d) for d in later_days}
            second = cs.build_derived_series(
                "TEST", closes=closes, chains=second_chains,
                asof=later_days[-1].isoformat(), cache_dir=tmp)
            self.assertEqual(len(second), 6)
            # The first four rows are byte-identical to the first call's
            # output (never recomputed).
            pd.testing.assert_frame_equal(
                second.loc[[d.isoformat() for d in first_days]], first)


# ---------------------------------------------------------------------------
# Dashboard panel smoke test
# ---------------------------------------------------------------------------

class DashboardPanelSmokeTest(unittest.TestCase):
    def test_panel_renders_and_shows_data_blocked(self):
        from options_researcher import attractiveness_dashboard as ad

        blocked_card = cs._card_blocked(
            "ZZZ", "no cached closes (FileNotFoundError)", asof="2024-06-03")
        data = ad.assemble(symbol_sections=[], rv21_by_symbol={}, blocked=[],
                           composite_signals=[blocked_card])
        self.assertEqual(data["composite_signals"], [blocked_card])
        html = ad.render(data)
        self.assertIn("Composite signal board", html)
        self.assertIn("ZZZ", html)
        self.assertIn("DATA_BLOCKED", html)
        self.assertIn("GRADE C", html)

    def test_panel_omitted_when_no_cards(self):
        from options_researcher import attractiveness_dashboard as ad

        data = ad.assemble(symbol_sections=[], rv21_by_symbol={}, blocked=[],
                           composite_signals=[])
        self.assertEqual(data["composite_signals"], [])
        html = ad.render(data)
        self.assertNotIn("Composite signal board", html)

    def test_default_composite_signals_key_present_without_injection(self):
        from options_researcher import attractiveness_dashboard as ad

        data = ad.assemble(symbol_sections=[], rv21_by_symbol={})
        self.assertEqual(data["composite_signals"], [])


if __name__ == "__main__":
    unittest.main()
