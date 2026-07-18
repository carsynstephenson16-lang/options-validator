import unittest

import config
from options_researcher.quote_integrity import Tier, classify_row


def row(**overrides):
    values = {
        "right": "C",
        "strike": 100.0,
        "bid": 5.0,
        "ask": 5.4,
        "iv": 0.35,
        "delta": 0.55,
        "gamma": 0.02,
        "vega": 0.10,
        "spot": 101.0,
    }
    values.update(overrides)
    return values


class TestDetectorConfig(unittest.TestCase):
    def test_frozen_detector_tolerances(self):
        self.assertEqual(config.BS_DELTA_EPS, 0.02)
        self.assertEqual(config.BS_NOARB_TOL, 0.02)
        self.assertEqual(config.BS_IV_EXTREME_LOW, 0.02)
        self.assertEqual(config.BS_IV_EXTREME_HIGH, 5.0)


class TestDetector(unittest.TestCase):
    def test_clean_row_ok(self):
        self.assertEqual(classify_row(**row()).tier, Tier.OK)

    def test_missing_spot_not_assessed(self):
        legacy_row = row()
        legacy_row.pop("spot")
        verdict = classify_row(**legacy_row)
        self.assertEqual(verdict.tier, Tier.NOT_ASSESSED)
        self.assertIn("synchronized spot", verdict.reason)

    def test_nonfinite_vendor_field_not_assessed(self):
        self.assertEqual(
            classify_row(**row(iv=float("nan"))).tier, Tier.NOT_ASSESSED
        )

    def test_invalid_right_not_assessed(self):
        self.assertEqual(classify_row(**row(right="X")).tier, Tier.NOT_ASSESSED)

    def test_crossed_or_negative_quote_invalid(self):
        for overrides in ({"bid": 6.0, "ask": 5.0}, {"bid": -0.01}):
            with self.subTest(overrides=overrides):
                self.assertEqual(
                    classify_row(**row(**overrides)).tier, Tier.INVALID_QUOTE
                )

    def test_impossible_greeks_invalid(self):
        for overrides in (
            {"gamma": -0.01},
            {"vega": -0.01},
            {"delta": 1.5},
            {"right": "P", "delta": 0.5},
        ):
            with self.subTest(overrides=overrides):
                self.assertEqual(
                    classify_row(**row(**overrides)).tier, Tier.INVALID_GREEK
                )

    def test_delta_epsilon_boundary_is_allowed(self):
        self.assertEqual(
            classify_row(**row(delta=1.0 + config.BS_DELTA_EPS)).tier, Tier.OK
        )
        self.assertEqual(
            classify_row(
                **row(right="P", delta=-1.0 - config.BS_DELTA_EPS)
            ).tier,
            Tier.OK,
        )

    def test_executable_call_bound_violations(self):
        below_floor = classify_row(
            **row(strike=110.0, spot=160.0, bid=4.0, ask=5.0)
        )
        above_ceiling = classify_row(
            **row(strike=100.0, spot=101.0, bid=102.0, ask=103.0)
        )
        self.assertEqual(below_floor.tier, Tier.INVALID_NO_ARB)
        self.assertEqual(above_ceiling.tier, Tier.INVALID_NO_ARB)

    def test_executable_put_bound_violations(self):
        below_floor = classify_row(
            **row(
                right="P",
                strike=160.0,
                spot=110.0,
                bid=4.0,
                ask=5.0,
                delta=-0.55,
            )
        )
        above_ceiling = classify_row(
            **row(
                right="P",
                strike=100.0,
                spot=101.0,
                bid=101.0,
                ask=102.0,
                delta=-0.45,
            )
        )
        self.assertEqual(below_floor.tier, Tier.INVALID_NO_ARB)
        self.assertEqual(above_ceiling.tier, Tier.INVALID_NO_ARB)

    def test_non_executable_sides_are_not_arbitrage(self):
        self.assertEqual(
            classify_row(**row(bid=0.01, ask=150.0)).tier,
            Tier.OK,
        )

    def test_no_arb_tolerance_boundary_is_allowed(self):
        verdict = classify_row(
            **row(
                strike=100.0,
                spot=110.0,
                bid=9.0,
                ask=10.0 - config.BS_NOARB_TOL,
            )
        )
        self.assertEqual(verdict.tier, Tier.OK)

    def test_extreme_iv_band_is_inclusive(self):
        for iv in (config.BS_IV_EXTREME_LOW, config.BS_IV_EXTREME_HIGH):
            with self.subTest(iv=iv):
                self.assertEqual(classify_row(**row(iv=iv)).tier, Tier.EXTREME)

    def test_no_european_root_is_reported_but_not_invalid(self):
        verdict = classify_row(**row(), iv_reason="no_european_bs_root")
        self.assertEqual(verdict.tier, Tier.NO_EUROPEAN_BS_ROOT)

    def test_model_disagreement_is_not_flagged(self):
        self.assertEqual(classify_row(**row(iv=0.36)).tier, Tier.OK)


if __name__ == "__main__":
    unittest.main()
