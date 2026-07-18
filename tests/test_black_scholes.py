import math
import unittest

from options_researcher.black_scholes import (
    bs_price,
    d1,
    d2,
    delta,
    gamma,
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


if __name__ == "__main__":
    unittest.main()
