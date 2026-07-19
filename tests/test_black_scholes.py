import math
import unittest

from options_researcher.black_scholes import (
    ImpliedVolResult,
    bs_price,
    d1,
    d2,
    delta,
    gamma,
    implied_vol,
    rho,
    theta,
    vega,
)


class TestBSPrice(unittest.TestCase):
    def test_atm_call_known_vector(self):
        # S=100,K=100,t=1,r=0.05,q=0,sigma=0.20 -> call ~ 10.4506
        call = bs_price(
            S=100,
            K=100,
            t=1.0,
            r=0.05,
            sigma=0.20,
            right="C",
            q=0.0,
        )
        self.assertAlmostEqual(call, 10.4506, places=3)

    def test_atm_put_known_vector(self):
        put = bs_price(
            S=100,
            K=100,
            t=1.0,
            r=0.05,
            sigma=0.20,
            right="P",
            q=0.0,
        )
        self.assertAlmostEqual(put, 5.5735, places=3)

    def test_put_call_parity_unit_invariant(self):
        # C - P == S*e^{-qt} - K*e^{-rt} (European; unit invariant only).
        spot, strike, tenor, rate, dividend, sigma = (
            123.0,
            110.0,
            0.5,
            0.04,
            0.01,
            0.35,
        )
        call = bs_price(
            S=spot,
            K=strike,
            t=tenor,
            r=rate,
            sigma=sigma,
            right="C",
            q=dividend,
        )
        put = bs_price(
            S=spot,
            K=strike,
            t=tenor,
            r=rate,
            sigma=sigma,
            right="P",
            q=dividend,
        )
        lhs = call - put
        rhs = spot * math.exp(-dividend * tenor) - strike * math.exp(-rate * tenor)
        self.assertAlmostEqual(lhs, rhs, places=9)

    def test_d1_d2_relationship(self):
        spot, strike, tenor, rate, dividend, sigma = 100.0, 100.0, 1.0, 0.05, 0.0, 0.2
        self.assertAlmostEqual(
            d2(spot, strike, tenor, rate, sigma, dividend),
            d1(spot, strike, tenor, rate, sigma, dividend) - sigma * math.sqrt(tenor),
            places=12,
        )

    def test_expiry_and_zero_volatility_boundaries(self):
        self.assertEqual(
            bs_price(S=105.0, K=100.0, t=0.0, r=0.05, sigma=0.2, right="C"),
            5.0,
        )
        discounted = bs_price(
            S=105.0,
            K=100.0,
            t=1.0,
            r=0.05,
            sigma=0.0,
            right="C",
            q=0.01,
        )
        expected = max(105.0 * math.exp(-0.01) - 100.0 * math.exp(-0.05), 0.0)
        self.assertAlmostEqual(discounted, expected, places=12)

    def test_invalid_inputs_raise(self):
        with self.assertRaisesRegex(ValueError, "right"):
            bs_price(S=100.0, K=100.0, t=1.0, r=0.05, sigma=0.2, right="X")
        with self.assertRaisesRegex(ValueError, "spot"):
            bs_price(S=0.0, K=100.0, t=1.0, r=0.05, sigma=0.2, right="C")
        with self.assertRaisesRegex(ValueError, "finite"):
            bs_price(
                S=100.0,
                K=100.0,
                t=1.0,
                r=0.05,
                sigma=float("nan"),
                right="C",
            )


class TestGreeks(unittest.TestCase):
    PARAMETERS = {
        "S": 100.0,
        "K": 100.0,
        "t": 0.5,
        "r": 0.03,
        "q": 0.01,
        "sigma": 0.30,
    }

    def test_delta_matches_finite_difference(self):
        bump = 1e-4
        for right in ("C", "P"):
            with self.subTest(right=right):
                up = bs_price(
                    **{**self.PARAMETERS, "S": self.PARAMETERS["S"] + bump},
                    right=right,
                )
                down = bs_price(
                    **{**self.PARAMETERS, "S": self.PARAMETERS["S"] - bump},
                    right=right,
                )
                expected = (up - down) / (2 * bump)
                self.assertAlmostEqual(
                    delta(**self.PARAMETERS, right=right), expected, places=5
                )

    def test_gamma_matches_finite_difference(self):
        bump = 1e-2
        base = bs_price(**self.PARAMETERS, right="C")
        up = bs_price(
            **{**self.PARAMETERS, "S": self.PARAMETERS["S"] + bump}, right="C"
        )
        down = bs_price(
            **{**self.PARAMETERS, "S": self.PARAMETERS["S"] - bump}, right="C"
        )
        expected = (up - 2 * base + down) / (bump * bump)
        self.assertAlmostEqual(gamma(**self.PARAMETERS), expected, places=5)

    def test_vega_per_percentage_point(self):
        bump = 1e-5
        up = bs_price(
            **{**self.PARAMETERS, "sigma": self.PARAMETERS["sigma"] + bump},
            right="C",
        )
        down = bs_price(
            **{**self.PARAMETERS, "sigma": self.PARAMETERS["sigma"] - bump},
            right="C",
        )
        expected_per_point = (up - down) / (2 * bump) * 0.01
        self.assertAlmostEqual(vega(**self.PARAMETERS), expected_per_point, places=7)

    def test_theta_sign_negative_for_long(self):
        for right in ("C", "P"):
            with self.subTest(right=right):
                self.assertLess(theta(**self.PARAMETERS, right=right), 0.0)

    def test_rho_per_percentage_point(self):
        bump = 1e-5
        up = bs_price(
            **{**self.PARAMETERS, "r": self.PARAMETERS["r"] + bump}, right="C"
        )
        down = bs_price(
            **{**self.PARAMETERS, "r": self.PARAMETERS["r"] - bump}, right="C"
        )
        expected_per_point = (up - down) / (2 * bump) * 0.01
        self.assertAlmostEqual(
            rho(**self.PARAMETERS, right="C"), expected_per_point, places=7
        )


class TestImpliedVol(unittest.TestCase):
    def test_round_trip(self):
        spot, strike, tenor, rate, dividend, sigma = 100.0, 105.0, 0.75, 0.04, 0.0, 0.42
        price = bs_price(
            S=spot,
            K=strike,
            t=tenor,
            r=rate,
            sigma=sigma,
            right="C",
            q=dividend,
        )
        result = implied_vol(
            price=price,
            S=spot,
            K=strike,
            t=tenor,
            r=rate,
            right="C",
            q=dividend,
        )
        self.assertIsInstance(result, ImpliedVolResult)
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.iv, sigma, places=4)

    def test_price_below_intrinsic_has_no_root(self):
        result = implied_vol(
            price=0.01,
            S=200.0,
            K=100.0,
            t=1.0,
            r=0.05,
            right="C",
            q=0.0,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "no_european_bs_root")
        self.assertTrue(math.isnan(result.iv))

    def test_expired_returns_expired(self):
        result = implied_vol(
            price=5.0,
            S=100.0,
            K=100.0,
            t=0.0,
            r=0.05,
            right="C",
            q=0.0,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "expired")
        self.assertTrue(math.isnan(result.iv))

    def test_invalid_target_price_raises(self):
        with self.assertRaisesRegex(ValueError, "price"):
            implied_vol(
                price=float("nan"),
                S=100.0,
                K=100.0,
                t=1.0,
                r=0.05,
                right="C",
            )


if __name__ == "__main__":
    unittest.main()
