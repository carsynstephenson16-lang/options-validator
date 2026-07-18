"""Pure, offline European Black-Scholes price, Greeks, and implied volatility.

Conventions are frozen in ``docs/superpowers/specs/2026-07-17-black-scholes-
attractiveness-design.md`` section 4: continuously compounded rates and
dividend yield, ACT/365 time, theta per calendar day, and vega/rho per one
percentage-point change.  This module deliberately has no I/O or third-party
dependencies.
"""
from __future__ import annotations

import math

_SQRT_2PI = math.sqrt(2.0 * math.pi)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT_2PI


def d1(S: float, K: float, t: float, r: float, sigma: float, q: float = 0.0) -> float:
    """Return the standard Black-Scholes ``d1`` term."""
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
    normalized_right = right.upper()
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
    normalized_right = right.upper()
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
    normalized_right = right.upper()
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
    normalized_right = right.upper()
    second = d2(S, K, t, r, sigma, q)
    if normalized_right == "C":
        return K * t * math.exp(-r * t) * _norm_cdf(second) / 100.0
    return -K * t * math.exp(-r * t) * _norm_cdf(-second) / 100.0
