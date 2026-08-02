"""Deterministic property tests for the offline Black-Scholes implementation."""

from __future__ import annotations

import math
import unittest

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from options_researcher.black_scholes import bs_price, gamma, implied_vol, vega

PROPERTY_SETTINGS = settings(max_examples=100, deadline=None, derandomize=True)

SPOTS = st.floats(min_value=5.0, max_value=500.0, allow_nan=False, allow_infinity=False)
STRIKES = st.floats(min_value=5.0, max_value=500.0, allow_nan=False, allow_infinity=False)
TENORS = st.floats(min_value=1 / 365, max_value=5.0, allow_nan=False, allow_infinity=False)
RATES = st.floats(min_value=-0.05, max_value=0.20, allow_nan=False, allow_infinity=False)
DIVIDENDS = st.floats(min_value=0.0, max_value=0.15, allow_nan=False, allow_infinity=False)
VOLATILITIES = st.floats(
    min_value=0.01,
    max_value=2.0,
    allow_nan=False,
    allow_infinity=False,
)


class TestBlackScholesPriceProperties(unittest.TestCase):
    @PROPERTY_SETTINGS
    @given(
        spot=SPOTS,
        strike=STRIKES,
        tenor=TENORS,
        rate=RATES,
        dividend=DIVIDENDS,
        sigma=VOLATILITIES,
    )
    def test_price_is_monotone_in_spot(
        self,
        spot: float,
        strike: float,
        tenor: float,
        rate: float,
        dividend: float,
        sigma: float,
    ) -> None:
        higher_spot = spot * 1.01
        call = bs_price(
            S=spot, K=strike, t=tenor, r=rate, sigma=sigma, right="C", q=dividend
        )
        higher_call = bs_price(
            S=higher_spot,
            K=strike,
            t=tenor,
            r=rate,
            sigma=sigma,
            right="C",
            q=dividend,
        )
        put = bs_price(
            S=spot, K=strike, t=tenor, r=rate, sigma=sigma, right="P", q=dividend
        )
        higher_put = bs_price(
            S=higher_spot,
            K=strike,
            t=tenor,
            r=rate,
            sigma=sigma,
            right="P",
            q=dividend,
        )

        self.assertGreaterEqual(higher_call + 1e-10, call)
        self.assertLessEqual(higher_put, put + 1e-10)

    @PROPERTY_SETTINGS
    @given(
        spot=SPOTS,
        strike=STRIKES,
        tenor=TENORS,
        rate=RATES,
        dividend=DIVIDENDS,
        sigma=VOLATILITIES,
    )
    def test_price_is_monotone_in_strike(
        self,
        spot: float,
        strike: float,
        tenor: float,
        rate: float,
        dividend: float,
        sigma: float,
    ) -> None:
        higher_strike = strike * 1.01
        call = bs_price(
            S=spot, K=strike, t=tenor, r=rate, sigma=sigma, right="C", q=dividend
        )
        higher_call = bs_price(
            S=spot,
            K=higher_strike,
            t=tenor,
            r=rate,
            sigma=sigma,
            right="C",
            q=dividend,
        )
        put = bs_price(
            S=spot, K=strike, t=tenor, r=rate, sigma=sigma, right="P", q=dividend
        )
        higher_put = bs_price(
            S=spot,
            K=higher_strike,
            t=tenor,
            r=rate,
            sigma=sigma,
            right="P",
            q=dividend,
        )

        self.assertLessEqual(higher_call, call + 1e-10)
        self.assertGreaterEqual(higher_put + 1e-10, put)

    @PROPERTY_SETTINGS
    @given(
        spot=SPOTS,
        strike=STRIKES,
        tenor=TENORS,
        rate=RATES,
        dividend=DIVIDENDS,
        sigma=VOLATILITIES,
    )
    def test_prices_respect_discounted_european_bounds_and_parity(
        self,
        spot: float,
        strike: float,
        tenor: float,
        rate: float,
        dividend: float,
        sigma: float,
    ) -> None:
        discounted_spot = spot * math.exp(-dividend * tenor)
        discounted_strike = strike * math.exp(-rate * tenor)
        call = bs_price(
            S=spot, K=strike, t=tenor, r=rate, sigma=sigma, right="C", q=dividend
        )
        put = bs_price(
            S=spot, K=strike, t=tenor, r=rate, sigma=sigma, right="P", q=dividend
        )

        self.assertGreaterEqual(call + 1e-10, max(discounted_spot - discounted_strike, 0.0))
        self.assertLessEqual(call, discounted_spot + 1e-10)
        self.assertGreaterEqual(put + 1e-10, max(discounted_strike - discounted_spot, 0.0))
        self.assertLessEqual(put, discounted_strike + 1e-10)
        self.assertTrue(
            math.isclose(
                call - put,
                discounted_spot - discounted_strike,
                rel_tol=1e-11,
                abs_tol=1e-10,
            )
        )


class TestBlackScholesGreekProperties(unittest.TestCase):
    @PROPERTY_SETTINGS
    @given(
        spot=SPOTS,
        strike=STRIKES,
        tenor=TENORS,
        rate=RATES,
        dividend=DIVIDENDS,
        sigma=VOLATILITIES,
    )
    def test_gamma_and_vega_are_non_negative(
        self,
        spot: float,
        strike: float,
        tenor: float,
        rate: float,
        dividend: float,
        sigma: float,
    ) -> None:
        parameters = {
            "S": spot,
            "K": strike,
            "t": tenor,
            "r": rate,
            "sigma": sigma,
            "q": dividend,
        }

        self.assertGreaterEqual(gamma(**parameters), 0.0)
        self.assertGreaterEqual(vega(**parameters), 0.0)


class TestBlackScholesImpliedVolProperties(unittest.TestCase):
    @PROPERTY_SETTINGS
    @given(
        spot=st.floats(
            min_value=20.0, max_value=300.0, allow_nan=False, allow_infinity=False
        ),
        moneyness=st.floats(
            min_value=0.8, max_value=1.2, allow_nan=False, allow_infinity=False
        ),
        tenor=st.floats(
            min_value=0.25, max_value=2.0, allow_nan=False, allow_infinity=False
        ),
        rate=RATES,
        dividend=DIVIDENDS,
        sigma=st.floats(
            min_value=0.10, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
        right=st.sampled_from(("C", "P")),
    )
    def test_implied_vol_round_trip(
        self,
        spot: float,
        moneyness: float,
        tenor: float,
        rate: float,
        dividend: float,
        sigma: float,
        right: str,
    ) -> None:
        strike = spot * moneyness
        # A price can only identify volatility when it has meaningful vega.
        # Exclude numerically flat cases instead of asserting false precision.
        assume(
            vega(
                S=spot,
                K=strike,
                t=tenor,
                r=rate,
                sigma=sigma,
                q=dividend,
            )
            > 1e-3
        )
        price = bs_price(
            S=spot,
            K=strike,
            t=tenor,
            r=rate,
            sigma=sigma,
            right=right,
            q=dividend,
        )
        result = implied_vol(
            price=price,
            S=spot,
            K=strike,
            t=tenor,
            r=rate,
            right=right,
            q=dividend,
        )

        self.assertTrue(result.ok, result.reason)
        self.assertTrue(math.isclose(result.iv, sigma, rel_tol=2e-4, abs_tol=2e-5))


class TestBlackScholesBoundaryProperties(unittest.TestCase):
    @PROPERTY_SETTINGS
    @given(spot=SPOTS, strike=STRIKES, right=st.sampled_from(("C", "P")))
    def test_expiry_returns_intrinsic(self, spot: float, strike: float, right: str) -> None:
        expected = max(spot - strike, 0.0) if right == "C" else max(strike - spot, 0.0)
        actual = bs_price(S=spot, K=strike, t=0.0, r=0.05, sigma=0.30, right=right)
        self.assertEqual(actual, expected)

    @PROPERTY_SETTINGS
    @given(
        spot=SPOTS,
        strike=STRIKES,
        tenor=TENORS,
        rate=RATES,
        dividend=DIVIDENDS,
        right=st.sampled_from(("C", "P")),
    )
    def test_zero_volatility_returns_discounted_intrinsic(
        self,
        spot: float,
        strike: float,
        tenor: float,
        rate: float,
        dividend: float,
        right: str,
    ) -> None:
        discounted_spot = spot * math.exp(-dividend * tenor)
        discounted_strike = strike * math.exp(-rate * tenor)
        expected = (
            max(discounted_spot - discounted_strike, 0.0)
            if right == "C"
            else max(discounted_strike - discounted_spot, 0.0)
        )
        actual = bs_price(
            S=spot, K=strike, t=tenor, r=rate, sigma=0.0, right=right, q=dividend
        )
        self.assertEqual(actual, expected)

    @PROPERTY_SETTINGS
    @given(
        bad_spot=st.sampled_from((0.0, -1.0, -1e9)),
        bad_strike=st.sampled_from((0.0, -1.0, -1e9)),
        bad_sigma=st.sampled_from((-1e-12, -0.5, -10.0)),
    )
    def test_invalid_domains_fail_closed(
        self, bad_spot: float, bad_strike: float, bad_sigma: float
    ) -> None:
        with self.assertRaises(ValueError):
            bs_price(S=bad_spot, K=100.0, t=1.0, r=0.05, sigma=0.20, right="C")
        with self.assertRaises(ValueError):
            bs_price(S=100.0, K=bad_strike, t=1.0, r=0.05, sigma=0.20, right="C")
        with self.assertRaises(ValueError):
            bs_price(S=100.0, K=100.0, t=1.0, r=0.05, sigma=bad_sigma, right="C")

        for non_finite in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                bs_price(
                    S=100.0,
                    K=100.0,
                    t=1.0,
                    r=0.05,
                    sigma=non_finite,
                    right="C",
                )


if __name__ == "__main__":
    unittest.main()
