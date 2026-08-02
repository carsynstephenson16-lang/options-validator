"""Typed, isolated QuantLib reference pricing for validation tests only."""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from datetime import date
from enum import Enum

import QuantLib as ql

_QUANTLIB_LOCK = threading.Lock()
_DAY_COUNT_LABEL = "Actual/365 (Fixed)"
_MIN_GRID_SIZE = 2


class OptionRight(str, Enum):
    """Supported plain-vanilla option rights."""

    CALL = "call"
    PUT = "put"


class ExerciseStyle(str, Enum):
    """Supported exercise styles."""

    EUROPEAN = "european"
    AMERICAN = "american"


class DividendTreatment(str, Enum):
    """Mutually exclusive dividend models."""

    CONTINUOUS_YIELD = "continuous_yield"
    DISCRETE_CASH = "discrete_cash"


@dataclass(frozen=True)
class CashDividend:
    """A declared cash dividend strictly inside the option life."""

    payment_date: date
    amount: float


@dataclass(frozen=True)
class PricingRequest:
    """Validated input for one plain-vanilla reference calculation."""

    valuation_date: date
    maturity_date: date
    option_right: OptionRight
    exercise_style: ExerciseStyle
    spot: float
    strike: float
    volatility: float
    risk_free_rate: float
    dividend_treatment: DividendTreatment
    continuous_dividend_yield: float = 0.0
    cash_dividends: tuple[CashDividend, ...] = ()
    time_steps: int = 400
    grid_points: int = 200

    def validate(self) -> None:
        """Reject unsafe inputs before any QuantLib global is changed."""
        if type(self.valuation_date) is not date or type(self.maturity_date) is not date:
            raise ValueError("valuation_date and maturity_date must be date values")
        if self.maturity_date <= self.valuation_date:
            raise ValueError("maturity_date must be after valuation_date")
        if not isinstance(self.option_right, OptionRight):
            raise ValueError("option_right must be an OptionRight")
        if not isinstance(self.exercise_style, ExerciseStyle):
            raise ValueError("exercise_style must be an ExerciseStyle")
        if not isinstance(self.dividend_treatment, DividendTreatment):
            raise ValueError("dividend_treatment must be a DividendTreatment")

        _require_finite("spot", self.spot, positive=True)
        _require_finite("strike", self.strike, positive=True)
        _require_finite("volatility", self.volatility, positive=True)
        _require_finite("risk_free_rate", self.risk_free_rate)
        _require_finite("continuous_dividend_yield", self.continuous_dividend_yield)
        _require_grid("time_steps", self.time_steps)
        _require_grid("grid_points", self.grid_points)

        if self.dividend_treatment is DividendTreatment.CONTINUOUS_YIELD:
            if self.cash_dividends:
                raise ValueError("cash_dividends must be empty for continuous-yield pricing")
            return

        if self.continuous_dividend_yield != 0.0:
            raise ValueError("continuous_dividend_yield must be zero for discrete-cash pricing")
        if not self.cash_dividends:
            raise ValueError("discrete-cash pricing requires at least one dividend")

        previous_date: date | None = None
        for dividend in self.cash_dividends:
            if not isinstance(dividend, CashDividend):
                raise ValueError("cash_dividends must contain CashDividend values")
            if type(dividend.payment_date) is not date:
                raise ValueError("cash dividend payment_date must be a date")
            if not self.valuation_date < dividend.payment_date < self.maturity_date:
                raise ValueError("cash dividend dates must fall strictly inside the option life")
            _require_finite("cash dividend amount", dividend.amount, positive=True)
            if previous_date is not None and dividend.payment_date <= previous_date:
                raise ValueError("cash dividend dates must be strictly increasing")
            previous_date = dividend.payment_date


@dataclass(frozen=True)
class PricingResult:
    """Primitive-only reference result with its material assumptions."""

    price: float
    engine: str
    valuation_date: date
    maturity_date: date
    option_right: OptionRight
    exercise_style: ExerciseStyle
    dividend_treatment: DividendTreatment
    spot: float
    strike: float
    volatility: float
    risk_free_rate: float
    continuous_dividend_yield: float
    cash_dividends: tuple[CashDividend, ...]
    time_steps: int
    grid_points: int
    day_count: str
    quantlib_version: str


class QuantLibPricingError(RuntimeError):
    """QuantLib failed after the Python request passed validation."""


def _require_finite(name: str, value: float, *, positive: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")


def _require_grid(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < _MIN_GRID_SIZE:
        raise ValueError(f"{name} must be an integer >= {_MIN_GRID_SIZE}")


def _to_ql_date(value: date) -> ql.Date:
    return ql.Date(value.day, value.month, value.year)


def _dividend_schedule(dividends: tuple[CashDividend, ...]) -> ql.DividendSchedule:
    schedule = ql.DividendSchedule()
    for dividend in dividends:
        schedule.push_back(ql.FixedDividend(dividend.amount, _to_ql_date(dividend.payment_date)))
    return schedule


def _price_with_declared_engine(request: PricingRequest) -> PricingResult:
    valuation_date = _to_ql_date(request.valuation_date)
    maturity_date = _to_ql_date(request.maturity_date)
    day_count = ql.Actual365Fixed()
    calendar = ql.NullCalendar()
    spot = ql.QuoteHandle(ql.SimpleQuote(request.spot))
    risk_free_curve = ql.YieldTermStructureHandle(
        ql.FlatForward(valuation_date, request.risk_free_rate, day_count)
    )
    dividend_curve = ql.YieldTermStructureHandle(
        ql.FlatForward(valuation_date, request.continuous_dividend_yield, day_count)
    )
    volatility = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(valuation_date, calendar, request.volatility, day_count)
    )
    process = ql.BlackScholesMertonProcess(spot, dividend_curve, risk_free_curve, volatility)
    option_type = ql.Option.Call if request.option_right is OptionRight.CALL else ql.Option.Put
    payoff = ql.PlainVanillaPayoff(option_type, request.strike)
    if request.exercise_style is ExerciseStyle.EUROPEAN:
        exercise = ql.EuropeanExercise(maturity_date)
    else:
        exercise = ql.AmericanExercise(valuation_date, maturity_date)
    option = ql.VanillaOption(payoff, exercise)

    if (
        request.exercise_style is ExerciseStyle.EUROPEAN
        and request.dividend_treatment is DividendTreatment.CONTINUOUS_YIELD
    ):
        engine_name = "AnalyticEuropeanEngine"
        engine = ql.AnalyticEuropeanEngine(process)
    elif request.dividend_treatment is DividendTreatment.DISCRETE_CASH:
        engine_name = "FdBlackScholesVanillaEngine(discrete-cash)"
        engine = ql.FdBlackScholesVanillaEngine(
            process,
            _dividend_schedule(request.cash_dividends),
            request.time_steps,
            request.grid_points,
        )
    else:
        engine_name = "FdBlackScholesVanillaEngine(continuous-yield)"
        engine = ql.FdBlackScholesVanillaEngine(process, request.time_steps, request.grid_points)

    option.setPricingEngine(engine)
    price = float(option.NPV())
    if not math.isfinite(price):
        raise RuntimeError("QuantLib returned a non-finite price")
    return PricingResult(
        price=price,
        engine=engine_name,
        valuation_date=request.valuation_date,
        maturity_date=request.maturity_date,
        option_right=request.option_right,
        exercise_style=request.exercise_style,
        dividend_treatment=request.dividend_treatment,
        spot=float(request.spot),
        strike=float(request.strike),
        volatility=float(request.volatility),
        risk_free_rate=float(request.risk_free_rate),
        continuous_dividend_yield=float(request.continuous_dividend_yield),
        cash_dividends=request.cash_dividends,
        time_steps=request.time_steps,
        grid_points=request.grid_points,
        day_count=_DAY_COUNT_LABEL,
        quantlib_version=ql.__version__,
    )


def price_option(request: PricingRequest) -> PricingResult:
    """Price one request while serializing and restoring QuantLib global state."""
    if not isinstance(request, PricingRequest):
        raise ValueError("request must be a PricingRequest")
    request.validate()
    with _QUANTLIB_LOCK:
        settings = ql.Settings.instance()
        previous_date = settings.evaluationDate
        try:
            settings.evaluationDate = _to_ql_date(request.valuation_date)
            try:
                return _price_with_declared_engine(request)
            except Exception as exc:
                raise QuantLibPricingError(
                    "QuantLib pricing failed for "
                    f"{request.exercise_style.value}/"
                    f"{request.dividend_treatment.value}: {exc}"
                ) from exc
        finally:
            settings.evaluationDate = previous_date
