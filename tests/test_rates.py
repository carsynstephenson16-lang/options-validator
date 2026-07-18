import csv
import math
import tempfile
import unittest
from datetime import date
from pathlib import Path

import config
from data.rates import (
    MissingDividendYieldError,
    dividend_yield,
    interp_rate,
    par_to_continuous,
    require_dividend_coverage,
    risk_free_rate,
)

RATE_FIELDS = (
    "observation_date",
    "tenor_days",
    "par_yield",
    "known_as_of_utc",
    "valid_through",
    "source_url",
    "captured_at_utc",
    "units",
)
DIVIDEND_FIELDS = (
    "symbol",
    "effective_date",
    "expected_annual_cash_dividend",
    "known_as_of_utc",
    "valid_through",
    "source_url",
    "captured_at_utc",
    "units",
)


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def rate_row(tenor: int, rate: float, **overrides) -> dict:
    values = {
        "observation_date": "2026-07-16",
        "tenor_days": str(tenor),
        "par_yield": str(rate),
        "known_as_of_utc": "2026-07-16T22:00:00+00:00",
        "valid_through": "2026-07-17",
        "source_url": "https://home.treasury.gov/example",
        "captured_at_utc": "2026-07-17T01:00:00+00:00",
        "units": "decimal_annual_par_yield",
    }
    values.update(overrides)
    return values


def dividend_row(symbol: str, cash: float, **overrides) -> dict:
    values = {
        "symbol": symbol,
        "effective_date": "2026-07-01",
        "expected_annual_cash_dividend": str(cash),
        "known_as_of_utc": "2026-07-01T12:00:00+00:00",
        "valid_through": "2026-09-30",
        "source_url": f"https://example.test/{symbol.lower()}/dividend",
        "captured_at_utc": "2026-07-01T13:00:00+00:00",
        "units": "usd_per_share_per_year",
    }
    values.update(overrides)
    return values


class TestRateMath(unittest.TestCase):
    def test_par_to_continuous_monotone_and_below_par(self):
        continuous = par_to_continuous(0.05)
        self.assertLess(continuous, 0.05)
        self.assertAlmostEqual(continuous, math.log1p(0.05), places=12)

    def test_linear_interpolation_in_time(self):
        curve = {30: 0.04, 90: 0.05}
        self.assertAlmostEqual(interp_rate(curve, 60), 0.045, places=12)

    def test_clamps_outside_curve(self):
        curve = {30: 0.04, 90: 0.05}
        self.assertEqual(interp_rate(curve, 10), 0.04)
        self.assertEqual(interp_rate(curve, 120), 0.05)

    def test_invalid_curve_fails_closed(self):
        with self.assertRaises(ValueError):
            interp_rate({}, 60)
        with self.assertRaises(ValueError):
            par_to_continuous(-1.0)


class TestPointInTimeRates(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.rate_path = self.base / "treasury.csv"
        self.dividend_path = self.base / "dividends.csv"

    def tearDown(self):
        self.temporary.cleanup()

    def test_risk_free_rate_interpolates_and_labels_approximation(self):
        write_csv(
            self.rate_path,
            RATE_FIELDS,
            [rate_row(30, 0.04), rate_row(90, 0.05)],
        )
        result = risk_free_rate(
            date(2026, 7, 17), date(2026, 9, 15), path=self.rate_path
        )
        self.assertAlmostEqual(result.rate, math.log1p(0.045), places=12)
        self.assertAlmostEqual(result.par_yield, 0.045, places=12)
        self.assertTrue(result.par_curve_as_zero_approximation)
        self.assertEqual(result.source_date, date(2026, 7, 16))
        self.assertTrue(result.provenance.source_url.startswith("https://"))
        self.assertEqual(result.provenance.units, "decimal_annual_par_yield")

    def test_rate_known_after_valuation_close_is_not_used(self):
        rows = [rate_row(30, 0.04), rate_row(90, 0.05)]
        rows.extend(
            [
                rate_row(
                    30,
                    0.09,
                    observation_date="2026-07-17",
                    known_as_of_utc="2026-07-17T22:00:00+00:00",
                    captured_at_utc="2026-07-17T23:00:00+00:00",
                ),
                rate_row(
                    90,
                    0.10,
                    observation_date="2026-07-17",
                    known_as_of_utc="2026-07-17T22:00:00+00:00",
                    captured_at_utc="2026-07-17T23:00:00+00:00",
                ),
            ]
        )
        write_csv(self.rate_path, RATE_FIELDS, rows)
        result = risk_free_rate(
            date(2026, 7, 17), date(2026, 9, 15), path=self.rate_path
        )
        self.assertEqual(result.source_date, date(2026, 7, 16))
        self.assertAlmostEqual(result.par_yield, 0.045, places=12)

    def test_missing_dividend_yield_raises_instead_of_defaulting_zero(self):
        write_csv(self.dividend_path, DIVIDEND_FIELDS, [dividend_row("MSFT", 3.32)])
        with self.assertRaises(MissingDividendYieldError):
            dividend_yield(
                "VST",
                date(2026, 7, 17),
                200.0,
                path=self.dividend_path,
            )

    def test_sourced_zero_dividend_is_allowed(self):
        write_csv(self.dividend_path, DIVIDEND_FIELDS, [dividend_row("AMZN", 0.0)])
        result = dividend_yield(
            "AMZN", date(2026, 7, 17), 225.0, path=self.dividend_path
        )
        self.assertEqual(result.yield_rate, 0.0)
        self.assertEqual(result.expected_annual_cash_dividend, 0.0)
        self.assertTrue(result.provenance.source_url.startswith("https://"))

    def test_dividend_yield_uses_expected_cash_over_synchronized_spot(self):
        write_csv(self.dividend_path, DIVIDEND_FIELDS, [dividend_row("MSFT", 4.0)])
        result = dividend_yield(
            "MSFT", date(2026, 7, 17), 400.0, path=self.dividend_path
        )
        self.assertAlmostEqual(result.yield_rate, 0.01, places=12)

    def test_expired_dividend_record_fails_closed(self):
        write_csv(
            self.dividend_path,
            DIVIDEND_FIELDS,
            [dividend_row("MSFT", 4.0, valid_through="2026-07-16")],
        )
        with self.assertRaises(MissingDividendYieldError):
            dividend_yield(
                "MSFT",
                date(2026, 7, 17),
                400.0,
                path=self.dividend_path,
            )

    def test_complete_universe_coverage(self):
        rows = [dividend_row(symbol, 0.0) for symbol in config.UNIVERSE]
        write_csv(self.dividend_path, DIVIDEND_FIELDS, rows)
        results = require_dividend_coverage(
            config.UNIVERSE,
            date(2026, 7, 17),
            {symbol: 100.0 for symbol in config.UNIVERSE},
            path=self.dividend_path,
        )
        self.assertEqual(set(results), set(config.UNIVERSE))


if __name__ == "__main__":
    unittest.main()
