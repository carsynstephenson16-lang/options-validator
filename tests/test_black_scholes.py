import math
import unittest
from unittest import mock

from options_researcher import black_scholes as bs_module
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


# ---------------------------------------------------------------------------
# implied_vol stress cases (2026-07-24: the existing solver tests above were
# found thin during the IV-solver-capture research brief -- these close the
# gap on the safeguarded-Newton edges the docstring promises: near-zero
# vega, very short DTE, and the literal sigma-->0 boundary). ZERO changes to
# options_researcher/black_scholes.py accompany these -- reuse only.
# ---------------------------------------------------------------------------
class TestImpliedVolStressCases(unittest.TestCase):
    def test_deep_otm_near_zero_vega_converges_or_reports_no_root(self):
        # S=100,K=200,T=0.05(~18d),sigma=0.20: deep OTM call so far out that
        # vega (measured while writing this test: ~1.1e-24 at the sigma=0.30
        # Newton seed) is astronomically below the module's 1e-8 bisection-
        # fallback threshold. The generated target price itself underflows
        # to a literal 0.0 in float64 at this moneyness/tenor -- a genuinely
        # flat, near-unsolvable inverse problem, not a bug. The module must
        # never be silently wrong about it: either it returns a genuine
        # self-consistent root (repricing at the returned sigma reproduces
        # the target price), or it explicitly refuses.
        S, K, t, r, sigma = 100.0, 200.0, 0.05, 0.04, 0.20
        price = bs_price(S=S, K=K, t=t, r=r, sigma=sigma, right="C")
        result = implied_vol(price=price, S=S, K=K, t=t, r=r, right="C")
        if result.ok:
            repriced = bs_price(S=S, K=K, t=t, r=r, sigma=result.iv, right="C")
            self.assertAlmostEqual(repriced, price, places=6)
        else:
            self.assertIn(result.reason, ("no_european_bs_root", "not_converged"))
            self.assertTrue(math.isnan(result.iv))

    def test_one_day_dte_atm_converges(self):
        # 1 calendar day to expiry, ATM (t tiny but > 0, so this exercises
        # the near-t-boundary region without crossing into the t<=0
        # "expired" short-circuit). ATM vega is near its maximum regardless
        # of tenor, so this is a distinct case from the near-zero-vega one
        # above -- it tests short-DTE convergence, not the safeguard.
        S, K, t, r, sigma = 100.0, 100.0, 1.0 / 365.0, 0.04, 0.25
        price = bs_price(S=S, K=K, t=t, r=r, sigma=sigma, right="C")
        result = implied_vol(price=price, S=S, K=K, t=t, r=r, right="C")
        self.assertTrue(result.ok, result.reason)
        self.assertAlmostEqual(result.iv, sigma, places=4)

    def test_bisection_fallback_branch_executes_and_still_converges(self):
        # Direct, deterministic proof that implied_vol's near-zero-vega
        # branch (`else: sigma = 0.5 * (low + high)`, taken whenever the
        # Newton derivative is <=1e-8) is reachable and correct -- rather
        # than hoping a hand-picked numeric vector happens to trip it
        # (deep-OTM vectors were tried while writing this suite and often
        # trivially "solve" at the untouched Newton seed instead, see the
        # test above), force it on EVERY iteration by patching the module's
        # own `vega` to always report zero, then confirm bisection alone
        # still finds the true root within the 100-iteration budget.
        S, K, t, r, sigma = 100.0, 105.0, 0.75, 0.04, 0.28
        price = bs_price(S=S, K=K, t=t, r=r, sigma=sigma, right="C")
        with mock.patch.object(bs_module, "vega", return_value=0.0):
            result = bs_module.implied_vol(price=price, S=S, K=K, t=t, r=r, right="C")
        self.assertTrue(result.ok, result.reason)
        self.assertAlmostEqual(result.iv, sigma, places=5)

    def test_discounted_intrinsic_zero_price_hits_sigma_to_zero_path(self):
        # Feeds bs_price's OWN sigma<=0 discounted-intrinsic branch directly
        # back into implied_vol as the target price -- literally exercising
        # the sigma-->0 boundary as the source of the inversion problem.
        # This asks the solver for a root at or below the practical
        # IV_LOW=0.01 floor; the recovered sigma must stay small (near that
        # floor, not some unrelated value) and must reprice back to the
        # original discounted-intrinsic price.
        S, K, t, r, q = 105.0, 100.0, 0.5, 0.04, 0.0
        zero_vol_price = bs_price(S=S, K=K, t=t, r=r, sigma=0.0, right="C", q=q)
        result = implied_vol(price=zero_vol_price, S=S, K=K, t=t, r=r, right="C", q=q)
        self.assertTrue(result.ok, result.reason)
        self.assertLess(result.iv, 0.05)
        repriced = bs_price(S=S, K=K, t=t, r=r, sigma=result.iv, right="C", q=q)
        self.assertAlmostEqual(repriced, zero_vol_price, places=4)

    def test_hull_textbook_reference_vector(self):
        # Hull, "Options, Futures, and Other Derivatives" (the standard
        # worked Black-Scholes-Merton example): S0=42, K=40, r=10%,
        # sigma=20%, T=0.5y, no dividend -> European call ~= 4.76.
        # Independent external check, hand-transcribed, not derived from
        # this module.
        call = bs_price(S=42.0, K=40.0, t=0.5, r=0.10, sigma=0.20, right="C", q=0.0)
        self.assertAlmostEqual(call, 4.76, places=2)


class TestPropertyGrid(unittest.TestCase):
    """Grid coverage over the frozen solver's advertised operating range
    (docs/superpowers/specs/2026-07-17-black-scholes-attractiveness-design.md
    Section 4.2): monotonicity of price in sigma, and implied_vol
    round-tripping bs_price, across moneyness x tenor x vol. r/q are held at
    representative constants (0.04, 0.01) -- not specified by the frozen
    spec; the properties below must hold for ANY fixed r/q, so the specific
    choice is not load-bearing.

    Direct sigma recovery to 1e-4 (implied_vol(bs_price(sigma)).iv == sigma)
    holds across the interior of the grid but -- measured while writing this
    test, not assumed -- genuinely breaks down at a specific corner: sigma
    =0.15 combined with moneyness far from 1.0 at short-to-medium tenor
    (ILL_CONDITIONED_AT_SIGMA_015 below). That is the same near-zero-vega
    regime TestImpliedVolStressCases probes directly: vega there is small
    enough that many sigmas price to observationally-identical values, so
    DIRECT recovery is not a well-posed request. What holds EVERYWHERE
    tested, with zero exceptions across all 160 grid points, is the weaker
    and more fundamental property: implied_vol always converges (never
    silently fails) and repricing at whatever sigma it returns reproduces
    the original price to within the module's own IV_TOL=1e-6 -- a genuine
    root, never a silently wrong answer.
    """

    MONEYNESS = (0.7, 0.85, 1.0, 1.15, 1.3)
    TENOR_DAYS = (15, 45, 90, 120)
    SIGMAS = (0.15, 0.30, 0.50, 0.80)
    R, Q = 0.04, 0.01
    K = 100.0
    REPRICE_TOL = 1.1e-6
    # (moneyness, tenor_days) pairs where sigma=0.15 sits in the near-zero-
    # vega corner; measured empirically while writing this test (2026-07-24).
    ILL_CONDITIONED_AT_SIGMA_015 = {
        (0.7, 15), (0.7, 45), (0.7, 90),
        (0.85, 15), (1.15, 15), (1.3, 15), (1.3, 45),
    }

    def test_price_strictly_increasing_in_sigma(self):
        for moneyness in self.MONEYNESS:
            for days in self.TENOR_DAYS:
                with self.subTest(moneyness=moneyness, days=days):
                    S = moneyness * self.K
                    t = days / 365.0
                    prices = [
                        bs_price(S=S, K=self.K, t=t, r=self.R, sigma=s,
                                right="C", q=self.Q)
                        for s in self.SIGMAS
                    ]
                    for lower, upper in zip(prices, prices[1:]):
                        self.assertLess(lower, upper)

    def test_implied_vol_never_fails_and_always_reprices_consistently(self):
        for moneyness in self.MONEYNESS:
            for days in self.TENOR_DAYS:
                for sigma in self.SIGMAS:
                    for right in ("C", "P"):
                        with self.subTest(moneyness=moneyness, days=days,
                                          sigma=sigma, right=right):
                            S = moneyness * self.K
                            t = days / 365.0
                            price = bs_price(S=S, K=self.K, t=t, r=self.R,
                                             sigma=sigma, right=right, q=self.Q)
                            result = implied_vol(price=price, S=S, K=self.K,
                                                 t=t, r=self.R, right=right,
                                                 q=self.Q)
                            self.assertTrue(result.ok, result.reason)
                            repriced = bs_price(S=S, K=self.K, t=t, r=self.R,
                                                sigma=result.iv, right=right,
                                                q=self.Q)
                            self.assertAlmostEqual(
                                repriced, price, delta=self.REPRICE_TOL)

    def test_direct_sigma_recovery_to_1e4_on_the_well_conditioned_interior(self):
        for moneyness in self.MONEYNESS:
            for days in self.TENOR_DAYS:
                for sigma in self.SIGMAS:
                    if (sigma == 0.15
                            and (moneyness, days) in self.ILL_CONDITIONED_AT_SIGMA_015):
                        continue
                    for right in ("C", "P"):
                        with self.subTest(moneyness=moneyness, days=days,
                                          sigma=sigma, right=right):
                            S = moneyness * self.K
                            t = days / 365.0
                            price = bs_price(S=S, K=self.K, t=t, r=self.R,
                                             sigma=sigma, right=right, q=self.Q)
                            result = implied_vol(price=price, S=S, K=self.K,
                                                 t=t, r=self.R, right=right,
                                                 q=self.Q)
                            self.assertTrue(result.ok, result.reason)
                            self.assertAlmostEqual(result.iv, sigma, places=4)


if __name__ == "__main__":
    unittest.main()
