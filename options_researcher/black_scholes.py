"""Pure, offline European Black-Scholes price, Greeks, and implied volatility.

Conventions are frozen in ``docs/superpowers/specs/2026-07-17-black-scholes-
attractiveness-design.md`` section 4: continuously compounded rates and
dividend yield, ACT/365 time, theta per calendar day, and vega/rho per one
percentage-point change.  This module deliberately has no I/O or third-party
dependencies.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

_SQRT_2PI = math.sqrt(2.0 * math.pi)
IV_LOW = 0.01
IV_HIGH = 5.0
IV_TOL = 1e-6
IV_MAX_ITERS = 100


def _normalize_right(right: str) -> str:
    if not isinstance(right, str) or right.upper() not in {"C", "P"}:
        raise ValueError("right must be 'C' or 'P'")
    return right.upper()


def _validate_inputs(*, S: float, K: float, t: float, r: float, sigma: float, q: float) -> None:
    values = (S, K, t, r, sigma, q)
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in values):
        raise ValueError("Black-Scholes inputs must be finite numbers")
    if S <= 0:
        raise ValueError("spot S must be positive")
    if K <= 0:
        raise ValueError("strike K must be positive")
    if sigma < 0:
        raise ValueError("sigma must be non-negative")


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT_2PI


def d1(S: float, K: float, t: float, r: float, sigma: float, q: float = 0.0) -> float:
    """Return the standard Black-Scholes ``d1`` term."""
    _validate_inputs(S=S, K=K, t=t, r=r, sigma=sigma, q=q)
    if t <= 0:
        raise ValueError("t must be positive for d1")
    if sigma == 0:
        raise ValueError("sigma must be positive for d1")
    return (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * t) / (
        sigma * math.sqrt(t)
    )


def d2(S: float, K: float, t: float, r: float, sigma: float, q: float = 0.0) -> float:
    """Return the standard Black-Scholes ``d2`` term."""
    return d1(S, K, t, r, sigma, q) - sigma * math.sqrt(t)


def bs_price(
    *,
    S: float,
    K: float,
    t: float,
    r: float,
    sigma: float,
    right: str,
    q: float = 0.0,
) -> float:
    """Price a European call (``C``) or put (``P``)."""
    normalized_right = _normalize_right(right)
    _validate_inputs(S=S, K=K, t=t, r=r, sigma=sigma, q=q)
    if t <= 0:
        return max(S - K, 0.0) if normalized_right == "C" else max(K - S, 0.0)
    if sigma <= 0:
        discounted_spot = S * math.exp(-q * t)
        discounted_strike = K * math.exp(-r * t)
        if normalized_right == "C":
            return max(discounted_spot - discounted_strike, 0.0)
        return max(discounted_strike - discounted_spot, 0.0)

    first = d1(S, K, t, r, sigma, q)
    second = first - sigma * math.sqrt(t)
    if normalized_right == "C":
        return S * math.exp(-q * t) * _norm_cdf(first) - K * math.exp(
            -r * t
        ) * _norm_cdf(second)
    return K * math.exp(-r * t) * _norm_cdf(-second) - S * math.exp(
        -q * t
    ) * _norm_cdf(-first)


def delta(
    *, S: float, K: float, t: float, r: float, sigma: float, right: str, q: float = 0.0
) -> float:
    """Return delta for a European call or put."""
    normalized_right = _normalize_right(right)
    first = d1(S, K, t, r, sigma, q)
    if normalized_right == "C":
        return math.exp(-q * t) * _norm_cdf(first)
    return -math.exp(-q * t) * _norm_cdf(-first)


def gamma(*, S: float, K: float, t: float, r: float, sigma: float, q: float = 0.0) -> float:
    """Return gamma, which is identical for European calls and puts."""
    first = d1(S, K, t, r, sigma, q)
    return math.exp(-q * t) * _norm_pdf(first) / (S * sigma * math.sqrt(t))


def vega(*, S: float, K: float, t: float, r: float, sigma: float, q: float = 0.0) -> float:
    """Return vega per one percentage-point (0.01) volatility change."""
    first = d1(S, K, t, r, sigma, q)
    return S * math.exp(-q * t) * _norm_pdf(first) * math.sqrt(t) / 100.0


def theta(
    *, S: float, K: float, t: float, r: float, sigma: float, right: str, q: float = 0.0
) -> float:
    """Return calendar-day theta, with decay negative for a typical long option."""
    normalized_right = _normalize_right(right)
    first = d1(S, K, t, r, sigma, q)
    second = first - sigma * math.sqrt(t)
    diffusion = -(S * math.exp(-q * t) * _norm_pdf(first) * sigma) / (
        2 * math.sqrt(t)
    )
    if normalized_right == "C":
        annual = (
            diffusion
            - r * K * math.exp(-r * t) * _norm_cdf(second)
            + q * S * math.exp(-q * t) * _norm_cdf(first)
        )
    else:
        annual = (
            diffusion
            + r * K * math.exp(-r * t) * _norm_cdf(-second)
            - q * S * math.exp(-q * t) * _norm_cdf(-first)
        )
    return annual / 365.0


def rho(
    *, S: float, K: float, t: float, r: float, sigma: float, right: str, q: float = 0.0
) -> float:
    """Return rho per one percentage-point (0.01) interest-rate change."""
    normalized_right = _normalize_right(right)
    second = d2(S, K, t, r, sigma, q)
    if normalized_right == "C":
        return K * t * math.exp(-r * t) * _norm_cdf(second) / 100.0
    return -K * t * math.exp(-r * t) * _norm_cdf(-second) / 100.0


@dataclass(frozen=True)
class ImpliedVolResult:
    """Result of IV inversion; ``iv`` is NaN whenever ``ok`` is false."""

    iv: float
    ok: bool
    reason: str


def implied_vol(
    *,
    price: float,
    S: float,
    K: float,
    t: float,
    r: float,
    right: str,
    q: float = 0.0,
) -> ImpliedVolResult:
    """Invert a validated option price through European Black-Scholes.

    Newton-Raphson is attempted from 0.30 volatility.  Each Newton step is
    constrained to the frozen bracket, with bisection used whenever the step
    would leave it or vega is too small.
    """
    normalized_right = _normalize_right(right)
    if not isinstance(price, (int, float)) or not math.isfinite(price) or price < 0:
        raise ValueError("price must be a finite non-negative number")
    # Reuse common validation with a harmless positive sigma; IV itself is the
    # unknown and is constrained by IV_LOW/IV_HIGH below.
    _validate_inputs(S=S, K=K, t=t, r=r, sigma=IV_LOW, q=q)
    if t <= 0:
        return ImpliedVolResult(float("nan"), False, "expired")

    lower_price = bs_price(
        S=S, K=K, t=t, r=r, sigma=IV_LOW, right=normalized_right, q=q
    )
    upper_price = bs_price(
        S=S, K=K, t=t, r=r, sigma=IV_HIGH, right=normalized_right, q=q
    )
    if not lower_price - IV_TOL <= price <= upper_price + IV_TOL:
        return ImpliedVolResult(float("nan"), False, "no_european_bs_root")

    low = IV_LOW
    high = IV_HIGH
    sigma = 0.30
    for _ in range(IV_MAX_ITERS):
        model_price = bs_price(
            S=S, K=K, t=t, r=r, sigma=sigma, right=normalized_right, q=q
        )
        difference = model_price - price
        if abs(difference) < IV_TOL:
            return ImpliedVolResult(sigma, True, "solved")
        if difference > 0:
            high = sigma
        else:
            low = sigma

        # Public vega is per 0.01; Newton needs dPrice/dSigma for a 1.0 move.
        derivative = vega(S=S, K=K, t=t, r=r, sigma=sigma, q=q) * 100.0
        if derivative > 1e-8:
            candidate = sigma - difference / derivative
            sigma = candidate if low < candidate < high else 0.5 * (low + high)
        else:
            sigma = 0.5 * (low + high)

    return ImpliedVolResult(float("nan"), False, "not_converged")
