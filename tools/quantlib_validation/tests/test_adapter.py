from __future__ import annotations

import math
import unittest
from dataclasses import replace
from datetime import date
from unittest.mock import patch

import QuantLib as ql

from options_researcher.black_scholes import bs_price
from tools.quantlib_validation.adapter import (
    CashDividend,
    DividendTreatment,
    ExerciseStyle,
    OptionRight,
    PricingRequest,
    price_option,
)

VALUATION_DATE = date(2026, 1, 1)
MATURITY_DATE = date(2027, 1, 1)


def european_request(**changes: object) -> PricingRequest:
    request = PricingRequest(
        valuation_date=VALUATION_DATE,
        maturity_date=MATURITY_DATE,
        option_right=OptionRight.CALL,
        exercise_style=ExerciseStyle.EUROPEAN,
        spot=100.0,
        strike=100.0,
        volatility=0.20,
        risk_free_rate=0.05,
        dividend_treatment=DividendTreatment.CONTINUOUS_YIELD,
        continuous_dividend_yield=0.0,
    )
    return replace(request, **changes)


class TestEuropeanReference(unittest.TestCase):
    def test_matches_known_black_scholes_vector_and_records_assumptions(self):
        result = price_option(european_request())

        self.assertAlmostEqual(result.price, 10.450583572185565, delta=1e-10)
        self.assertEqual(result.engine, "AnalyticEuropeanEngine")
        self.assertEqual(result.valuation_date, VALUATION_DATE)
        self.assertEqual(result.maturity_date, MATURITY_DATE)
        self.assertEqual(result.spot, 100.0)
        self.assertEqual(result.strike, 100.0)
        self.assertEqual(result.volatility, 0.20)
        self.assertEqual(result.risk_free_rate, 0.05)
        self.assertEqual(result.continuous_dividend_yield, 0.0)
        self.assertEqual(result.cash_dividends, ())
        self.assertEqual(result.exercise_style, ExerciseStyle.EUROPEAN)
        self.assertEqual(result.dividend_treatment, DividendTreatment.CONTINUOUS_YIELD)
        self.assertEqual(result.day_count, "Actual/365 (Fixed)")
        self.assertEqual(result.quantlib_version, "1.43")

    def test_matches_internal_european_pricer_and_independent_put_call_parity(self):
        call_request = european_request(continuous_dividend_yield=0.02)
        put_request = replace(call_request, option_right=OptionRight.PUT)

        call = price_option(call_request).price
        put = price_option(put_request).price
        internal_call = bs_price(S=100.0, K=100.0, t=1.0, r=0.05, sigma=0.20, right="C", q=0.02)
        expected_parity = 100.0 * math.exp(-0.02) - 100.0 * math.exp(-0.05)

        self.assertAlmostEqual(call, internal_call, delta=1e-10)
        self.assertAlmostEqual(call - put, expected_parity, delta=1e-10)

    def test_negative_rate_is_supported_by_both_declared_engines(self):
        european = price_option(european_request(risk_free_rate=-0.01)).price
        american = price_option(
            european_request(
                risk_free_rate=-0.01,
                exercise_style=ExerciseStyle.AMERICAN,
                time_steps=400,
                grid_points=200,
            )
        ).price

        self.assertTrue(math.isfinite(european))
        self.assertTrue(math.isfinite(american))
        self.assertGreaterEqual(american + 1e-8, european)


class TestAmericanReference(unittest.TestCase):
    def test_american_put_respects_intrinsic_and_matched_european_bounds(self):
        european_request_value = european_request(
            option_right=OptionRight.PUT,
            spot=90.0,
            strike=100.0,
            exercise_style=ExerciseStyle.EUROPEAN,
        )
        american_request = replace(
            european_request_value,
            exercise_style=ExerciseStyle.AMERICAN,
            time_steps=600,
            grid_points=300,
        )

        european = price_option(european_request_value).price
        american = price_option(american_request).price

        self.assertGreaterEqual(american, 10.0)
        self.assertGreaterEqual(american + 1e-8, european)

    def test_dividend_paying_american_call_has_early_exercise_sensitivity(self):
        dividend = CashDividend(date(2026, 7, 1), 10.0)
        european_request_value = european_request(
            exercise_style=ExerciseStyle.EUROPEAN,
            dividend_treatment=DividendTreatment.DISCRETE_CASH,
            cash_dividends=(dividend,),
        )
        american_request = replace(
            european_request_value,
            exercise_style=ExerciseStyle.AMERICAN,
            time_steps=800,
            grid_points=400,
        )

        european = price_option(european_request_value).price
        american = price_option(american_request).price

        self.assertGreaterEqual(american, european)
        self.assertGreater(american - european, 0.01)

    def test_non_dividend_american_call_converges_toward_european(self):
        european = price_option(european_request()).price
        coarse = price_option(
            european_request(
                exercise_style=ExerciseStyle.AMERICAN,
                time_steps=50,
                grid_points=50,
            )
        ).price
        fine = price_option(
            european_request(
                exercise_style=ExerciseStyle.AMERICAN,
                time_steps=800,
                grid_points=400,
            )
        ).price

        self.assertLess(abs(fine - european), abs(coarse - european))
        self.assertAlmostEqual(fine, european, delta=0.01)

    def test_repeated_results_are_deterministic(self):
        request = european_request(
            option_right=OptionRight.PUT,
            exercise_style=ExerciseStyle.AMERICAN,
            time_steps=400,
            grid_points=200,
        )

        first = price_option(request)
        second = price_option(request)

        self.assertEqual(first, second)


class TestInputValidation(unittest.TestCase):
    def test_invalid_scalar_and_date_inputs_fail_before_native_pricing(self):
        invalid_requests = (
            european_request(maturity_date=VALUATION_DATE),
            european_request(spot=0.0),
            european_request(strike=-1.0),
            european_request(volatility=0.0),
            european_request(risk_free_rate=float("nan")),
            european_request(continuous_dividend_yield=float("inf")),
            european_request(time_steps=1),
            european_request(grid_points=1),
        )

        for request in invalid_requests:
            with self.subTest(request=request), self.assertRaises(ValueError):
                price_option(request)

    def test_invalid_dividend_schedules_fail_closed(self):
        invalid_schedules = (
            (),
            (CashDividend(VALUATION_DATE, 1.0),),
            (CashDividend(MATURITY_DATE, 1.0),),
            (CashDividend(date(2026, 7, 1), 0.0),),
            (
                CashDividend(date(2026, 9, 1), 1.0),
                CashDividend(date(2026, 6, 1), 1.0),
            ),
        )

        for cash_dividends in invalid_schedules:
            request = european_request(
                dividend_treatment=DividendTreatment.DISCRETE_CASH,
                cash_dividends=cash_dividends,
            )
            with self.subTest(cash_dividends=cash_dividends), self.assertRaises(ValueError):
                price_option(request)

        with self.assertRaises(ValueError):
            price_option(european_request(cash_dividends=(CashDividend(date(2026, 7, 1), 1.0),)))


class TestEvaluationDateRestoration(unittest.TestCase):
    def setUp(self):
        self.settings = ql.Settings.instance()
        self.previous_date = self.settings.evaluationDate
        self.sentinel_date = ql.Date(15, ql.December, 2025)
        self.settings.evaluationDate = self.sentinel_date

    def tearDown(self):
        self.settings.evaluationDate = self.previous_date

    def test_restores_evaluation_date_after_success(self):
        price_option(european_request())

        self.assertEqual(self.settings.evaluationDate, self.sentinel_date)

    def test_restores_evaluation_date_after_forced_native_failure(self):
        with patch(
            "tools.quantlib_validation.adapter._price_with_declared_engine",
            side_effect=RuntimeError("forced native failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "forced native failure"):
                price_option(european_request())

        self.assertEqual(self.settings.evaluationDate, self.sentinel_date)


if __name__ == "__main__":
    unittest.main()
