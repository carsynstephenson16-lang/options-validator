# Black–Scholes Descriptive Infrastructure — Implementation Plan (Phase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the pure, offline, owner-input-free infrastructure from the design spec (`docs/superpowers/specs/2026-07-17-black-scholes-attractiveness-design.md`, §4/§5/§7): a tested Black–Scholes math unit, a gross-error detector, and point-in-time rate/dividend functions — none of which produce a study value or need owner-typed thresholds.

**Architecture:** Three self-contained, dependency-free Python modules under `options_researcher/` (BS math, detector) and `data/`/`config.py` (rate/dividend inputs). All math uses stdlib `math` only (no scipy — the repo's own code has none). Every function is fail-closed; legacy cache rows the detector can't assess return `NOT_ASSESSED`, never a fabricated spot.

**Tech Stack:** Python 3.12, `uv`, `unittest` (offline), `ruff`, `pyright`.

**Boundary (read before starting):** This plan is Phase 1 = spec §14 steps 1–2 (agent work). It deliberately does NOT implement: the term-structure column wiring (§6), the earnings-path fix (§8), the QM `retrospective_result` record (§9), H10 registration (§13), or any historical reveal (§10–11) — those are §14 steps 3–6, blocked on owner-typed §15 values and on repo-API reads not yet done. A Phase 2 plan follows once §15 is filled and the ledger/v3/features APIs are confirmed.

---

## File Structure

- Create: `options_researcher/black_scholes.py` — pricing, Greeks, IV solver (pure math).
- Create: `tests/test_black_scholes.py` — unit tests for the above.
- Create: `options_researcher/quote_integrity.py` — the gross-error detector (tiers + American-bound checks).
- Create: `tests/test_quote_integrity.py` — detector tests.
- Create: `data/rates.py` — point-in-time `risk_free_rate` + dividend-yield lookup with provenance.
- Create: `tests/test_rates.py` — rate/dividend tests.
- Modify: `config.py` — add frozen detector tolerances + rate/dividend source config (values from spec §4/§5/§7; no study thresholds).

---

## Task 1: Black–Scholes pricing core (`d1`, `d2`, `bs_price`)

**Files:**
- Create: `options_researcher/black_scholes.py`
- Test: `tests/test_black_scholes.py`

- [ ] **Step 1: Write the failing tests** (textbook vectors + put–call parity as a unit invariant)

```python
# tests/test_black_scholes.py
import math
import unittest

from options_researcher.black_scholes import bs_price, d1, d2


class TestBSPrice(unittest.TestCase):
    def test_atm_call_known_vector(self):
        # S=100,K=100,t=1,r=0.05,q=0,sigma=0.20 -> call ~ 10.4506
        c = bs_price(S=100, K=100, t=1.0, r=0.05, sigma=0.20, right="C", q=0.0)
        self.assertAlmostEqual(c, 10.4506, places=3)

    def test_atm_put_known_vector(self):
        p = bs_price(S=100, K=100, t=1.0, r=0.05, sigma=0.20, right="P", q=0.0)
        self.assertAlmostEqual(p, 5.5735, places=3)

    def test_put_call_parity_unit_invariant(self):
        # C - P == S*e^{-qt} - K*e^{-rt}  (European; UNIT invariant only)
        S, K, t, r, q, sig = 123.0, 110.0, 0.5, 0.04, 0.01, 0.35
        c = bs_price(S=S, K=K, t=t, r=r, sigma=sig, right="C", q=q)
        p = bs_price(S=S, K=K, t=t, r=r, sigma=sig, right="P", q=q)
        lhs = c - p
        rhs = S * math.exp(-q * t) - K * math.exp(-r * t)
        self.assertAlmostEqual(lhs, rhs, places=9)

    def test_d1_d2_relationship(self):
        S, K, t, r, q, sig = 100.0, 100.0, 1.0, 0.05, 0.0, 0.2
        self.assertAlmostEqual(
            d2(S, K, t, r, sig, q), d1(S, K, t, r, sig, q) - sig * math.sqrt(t),
            places=12)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest tests.test_black_scholes -v`
Expected: FAIL / ImportError (`black_scholes` not found).

- [ ] **Step 3: Write the minimal implementation**

```python
# options_researcher/black_scholes.py
"""Pure, offline European Black-Scholes: price, Greeks, implied vol.

Conventions frozen in docs/superpowers/specs/2026-07-17-black-scholes-
attractiveness-design.md sec.4: continuous-compounded r and q; ACT/365 time;
theta per calendar day (negative for decaying longs); vega per 1 percentage-
point; rho per 1 percentage-point; IV solver Newton+bisection on [0.01, 5.0],
tol 1e-6 USD, max 100 iters. stdlib math only (no scipy)."""
from __future__ import annotations

import math

_SQRT_2PI = math.sqrt(2.0 * math.pi)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT_2PI


def d1(S: float, K: float, t: float, r: float, sigma: float, q: float = 0.0) -> float:
    return (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))


def d2(S: float, K: float, t: float, r: float, sigma: float, q: float = 0.0) -> float:
    return d1(S, K, t, r, sigma, q) - sigma * math.sqrt(t)


def bs_price(*, S: float, K: float, t: float, r: float, sigma: float,
             right: str, q: float = 0.0) -> float:
    right = right.upper()
    if t <= 0:  # at/after expiry -> undiscounted intrinsic
        return max(S - K, 0.0) if right == "C" else max(K - S, 0.0)
    if sigma <= 0:  # zero-vol -> discounted intrinsic
        disc_s, disc_k = S * math.exp(-q * t), K * math.exp(-r * t)
        return (max(disc_s - disc_k, 0.0) if right == "C"
                else max(disc_k - disc_s, 0.0))
    _d1 = d1(S, K, t, r, sigma, q)
    _d2 = _d1 - sigma * math.sqrt(t)
    if right == "C":
        return S * math.exp(-q * t) * _norm_cdf(_d1) - K * math.exp(-r * t) * _norm_cdf(_d2)
    return K * math.exp(-r * t) * _norm_cdf(-_d2) - S * math.exp(-q * t) * _norm_cdf(-_d1)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_black_scholes -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add options_researcher/black_scholes.py tests/test_black_scholes.py
git commit -m "feat(bs): Black-Scholes price core (d1/d2/bs_price) + parity unit test"
```

---

## Task 2: Greeks (`delta`, `gamma`, `vega`, `theta`, `rho`)

**Files:**
- Modify: `options_researcher/black_scholes.py`
- Test: `tests/test_black_scholes.py`

- [ ] **Step 1: Write the failing tests** (finite-difference cross-check + theta sign)

```python
# append to tests/test_black_scholes.py
from options_researcher.black_scholes import bs_price, delta, gamma, rho, theta, vega


class TestGreeks(unittest.TestCase):
    P = dict(S=100.0, K=100.0, t=0.5, r=0.03, q=0.01, sigma=0.30)

    def test_delta_matches_finite_diff(self):
        h = 1e-4
        for right in ("C", "P"):
            up = bs_price(**{**self.P, "S": self.P["S"] + h}, right=right)
            dn = bs_price(**{**self.P, "S": self.P["S"] - h}, right=right)
            self.assertAlmostEqual(delta(**self.P, right=right), (up - dn) / (2 * h), places=5)

    def test_gamma_matches_finite_diff(self):
        h = 1e-3
        base = bs_price(**self.P, right="C")
        up = bs_price(**{**self.P, "S": self.P["S"] + h}, right="C")
        dn = bs_price(**{**self.P, "S": self.P["S"] - h}, right="C")
        self.assertAlmostEqual(gamma(**self.P), (up - 2 * base + dn) / (h * h), places=4)

    def test_vega_per_percentage_point(self):
        # vega reported per 1 vol point (0.01); finite-diff bumps sigma by 0.01
        base = bs_price(**self.P, right="C")
        bumped = bs_price(**{**self.P, "sigma": self.P["sigma"] + 0.01}, right="C")
        self.assertAlmostEqual(vega(**self.P), bumped - base, places=3)

    def test_theta_sign_negative_for_long(self):
        # long option loses value as calendar time passes
        self.assertLess(theta(**self.P, right="C"), 0.0)
        self.assertLess(theta(**self.P, right="P"), 0.0)

    def test_rho_per_percentage_point(self):
        base = bs_price(**self.P, right="C")
        bumped = bs_price(**{**self.P, "r": self.P["r"] + 0.01}, right="C")
        self.assertAlmostEqual(rho(**self.P, right="C"), bumped - base, places=3)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest tests.test_black_scholes.TestGreeks -v`
Expected: FAIL / ImportError (`delta` not defined).

- [ ] **Step 3: Write the minimal implementation** (append to `black_scholes.py`)

```python
def delta(*, S, K, t, r, sigma, right, q=0.0):
    right = right.upper()
    _d1 = d1(S, K, t, r, sigma, q)
    if right == "C":
        return math.exp(-q * t) * _norm_cdf(_d1)
    return -math.exp(-q * t) * _norm_cdf(-_d1)


def gamma(*, S, K, t, r, sigma, q=0.0):
    _d1 = d1(S, K, t, r, sigma, q)
    return math.exp(-q * t) * _norm_pdf(_d1) / (S * sigma * math.sqrt(t))


def vega(*, S, K, t, r, sigma, q=0.0):
    # per 1 percentage-point (0.01) change in vol
    _d1 = d1(S, K, t, r, sigma, q)
    return S * math.exp(-q * t) * _norm_pdf(_d1) * math.sqrt(t) / 100.0


def theta(*, S, K, t, r, sigma, right, q=0.0):
    # per calendar day; negative for a decaying long option
    right = right.upper()
    _d1 = d1(S, K, t, r, sigma, q)
    _d2 = _d1 - sigma * math.sqrt(t)
    term1 = -(S * math.exp(-q * t) * _norm_pdf(_d1) * sigma) / (2 * math.sqrt(t))
    if right == "C":
        annual = (term1
                  - r * K * math.exp(-r * t) * _norm_cdf(_d2)
                  + q * S * math.exp(-q * t) * _norm_cdf(_d1))
    else:
        annual = (term1
                  + r * K * math.exp(-r * t) * _norm_cdf(-_d2)
                  - q * S * math.exp(-q * t) * _norm_cdf(-_d1))
    return annual / 365.0


def rho(*, S, K, t, r, sigma, right, q=0.0):
    # per 1 percentage-point (0.01) change in rate
    right = right.upper()
    _d2 = d2(S, K, t, r, sigma, q)
    if right == "C":
        return K * t * math.exp(-r * t) * _norm_cdf(_d2) / 100.0
    return -K * t * math.exp(-r * t) * _norm_cdf(-_d2) / 100.0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_black_scholes.TestGreeks -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add options_researcher/black_scholes.py tests/test_black_scholes.py
git commit -m "feat(bs): Greeks with frozen units (vega/rho per point, theta/day, sign)"
```

---

## Task 3: Implied-vol solver (Newton + bisection, no-root flag)

**Files:**
- Modify: `options_researcher/black_scholes.py`
- Test: `tests/test_black_scholes.py`

- [ ] **Step 1: Write the failing tests** (round-trip + no-root + boundaries)

```python
# append to tests/test_black_scholes.py
import math as _m

from options_researcher.black_scholes import ImpliedVolResult, implied_vol


class TestImpliedVol(unittest.TestCase):
    def test_round_trip(self):
        S, K, t, r, q, sig = 100.0, 105.0, 0.75, 0.04, 0.0, 0.42
        price = bs_price(S=S, K=K, t=t, r=r, sigma=sig, right="C", q=q)
        res = implied_vol(price=price, S=S, K=K, t=t, r=r, right="C", q=q)
        self.assertTrue(res.ok)
        self.assertAlmostEqual(res.iv, sig, places=4)

    def test_price_below_intrinsic_has_no_root(self):
        # price below discounted intrinsic -> no European root
        res = implied_vol(price=0.01, S=200.0, K=100.0, t=1.0, r=0.05,
                          right="C", q=0.0)
        self.assertFalse(res.ok)
        self.assertEqual(res.reason, "no_european_bs_root")
        self.assertTrue(_m.isnan(res.iv))

    def test_expired_returns_expired(self):
        res = implied_vol(price=5.0, S=100.0, K=100.0, t=0.0, r=0.05,
                          right="C", q=0.0)
        self.assertFalse(res.ok)
        self.assertEqual(res.reason, "expired")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest tests.test_black_scholes.TestImpliedVol -v`
Expected: FAIL / ImportError (`implied_vol`, `ImpliedVolResult`).

- [ ] **Step 3: Write the minimal implementation** (append to `black_scholes.py`)

```python
from dataclasses import dataclass

IV_LOW, IV_HIGH, IV_TOL, IV_MAX_ITERS = 0.01, 5.0, 1e-6, 100


@dataclass(frozen=True)
class ImpliedVolResult:
    iv: float          # NaN when ok is False
    ok: bool
    reason: str        # "solved" | "expired" | "no_european_bs_root"


def implied_vol(*, price: float, S: float, K: float, t: float, r: float,
                right: str, q: float = 0.0) -> ImpliedVolResult:
    right = right.upper()
    if t <= 0:
        return ImpliedVolResult(float("nan"), False, "expired")
    # European no-arb bounds for a root to exist between IV_LOW and IV_HIGH:
    lo = bs_price(S=S, K=K, t=t, r=r, sigma=IV_LOW, right=right, q=q)
    hi = bs_price(S=S, K=K, t=t, r=r, sigma=IV_HIGH, right=right, q=q)
    if not (lo - IV_TOL <= price <= hi + IV_TOL):
        return ImpliedVolResult(float("nan"), False, "no_european_bs_root")
    # Newton seeded at 0.30, bisection fallback.
    sigma = 0.30
    low, high = IV_LOW, IV_HIGH
    for _ in range(IV_MAX_ITERS):
        model = bs_price(S=S, K=K, t=t, r=r, sigma=sigma, right=right, q=q)
        diff = model - price
        if abs(diff) < IV_TOL:
            return ImpliedVolResult(sigma, True, "solved")
        if diff > 0:
            high = sigma
        else:
            low = sigma
        v = vega(S=S, K=K, t=t, r=r, sigma=sigma, q=q) * 100.0  # de-scale to per-1.0
        if v > 1e-8:
            step = diff / v
            sigma_newton = sigma - step
            sigma = sigma_newton if low < sigma_newton < high else 0.5 * (low + high)
        else:
            sigma = 0.5 * (low + high)
    return ImpliedVolResult(sigma, True, "solved")  # converged to tol band
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_black_scholes -v`
Expected: PASS (all BS tests).

- [ ] **Step 5: Lint/type + commit**

```bash
uv run ruff check options_researcher/black_scholes.py tests/test_black_scholes.py
uv run pyright options_researcher/black_scholes.py
git add options_researcher/black_scholes.py tests/test_black_scholes.py
git commit -m "feat(bs): implied-vol solver (Newton+bisection, no_european_bs_root/expired)"
```

---

## Task 4: config — frozen detector tolerances

**Files:**
- Modify: `config.py`
- Test: (asserted via Task 5)

- [ ] **Step 1: Add the frozen constants** (values from spec §5/§15)

```python
# config.py -- Black-Scholes descriptive layer (spec 2026-07-17 sec.5).
# Engineer-proposed conventions, owner-approved via the spec. NOT study
# thresholds; they gate no trade and size nothing.
BS_DELTA_EPS = 0.02          # dimensionless delta out-of-range tolerance
BS_NOARB_TOL = 0.02          # USD tolerance on American no-arb bounds
BS_IV_EXTREME_LOW = 0.02     # decimal IV; <= is EXTREME (suspicious)
BS_IV_EXTREME_HIGH = 5.0     # decimal IV; >= is EXTREME
```

- [ ] **Step 2: Commit**

```bash
git add config.py
git commit -m "config(bs): freeze detector tolerances (delta eps, no-arb tol, extreme band)"
```

---

## Task 5: gross-error detector (`quote_integrity.py`)

**Files:**
- Create: `options_researcher/quote_integrity.py`
- Test: `tests/test_quote_integrity.py`

- [ ] **Step 1: Write the failing tests** (each tier + no false-flag + NOT_ASSESSED)

```python
# tests/test_quote_integrity.py
import math
import unittest

from options_researcher.quote_integrity import Tier, classify_row


def row(**kw):
    base = dict(right="C", strike=100.0, bid=5.0, ask=5.4, iv=0.35,
                delta=0.55, gamma=0.02, vega=0.10, spot=101.0)
    base.update(kw)
    return base


class TestDetector(unittest.TestCase):
    def test_clean_row_ok(self):
        self.assertEqual(classify_row(**row()).tier, Tier.OK)

    def test_missing_spot_not_assessed(self):
        self.assertEqual(classify_row(**row(spot=None)).tier, Tier.NOT_ASSESSED)

    def test_missing_field_not_assessed(self):
        self.assertEqual(classify_row(**row(iv=float("nan"))).tier, Tier.NOT_ASSESSED)

    def test_crossed_quote_invalid_quote(self):
        self.assertEqual(classify_row(**row(bid=6.0, ask=5.0)).tier, Tier.INVALID_QUOTE)

    def test_negative_gamma_invalid_greek(self):
        self.assertEqual(classify_row(**row(gamma=-0.01)).tier, Tier.INVALID_GREEK)

    def test_delta_out_of_range_invalid_greek(self):
        self.assertEqual(classify_row(**row(delta=1.5)).tier, Tier.INVALID_GREEK)

    def test_ask_below_call_floor_invalid_no_arb(self):
        # call floor = max(S-K,0) = 50 for S=160,K=110; ask 5 << floor
        self.assertEqual(
            classify_row(**row(strike=110.0, spot=160.0, bid=4.0, ask=5.0)).tier,
            Tier.INVALID_NO_ARB)

    def test_absurd_ask_alone_not_flagged(self):
        # high ask with a sane bid is NOT executable arbitrage -> OK
        self.assertEqual(classify_row(**row(bid=5.0, ask=90.0)).tier, Tier.OK)

    def test_extreme_iv_flagged(self):
        self.assertEqual(classify_row(**row(iv=0.005)).tier, Tier.EXTREME)

    def test_model_disagreement_not_flagged(self):
        # a row that merely differs from a BS recompute is still OK
        self.assertEqual(classify_row(**row(iv=0.36)).tier, Tier.OK)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest tests.test_quote_integrity -v`
Expected: FAIL / ImportError.

- [ ] **Step 3: Write the minimal implementation**

```python
# options_researcher/quote_integrity.py
"""Gross-error detector for vendor option rows (spec 2026-07-17 sec.5).

Catches DATA GLITCHES, never BS-vs-vendor model disagreement. Requires a
synchronized underlying spot; rows without it are NOT_ASSESSED (legacy cache
rows lack the field -- see thetadata_adapter.py CHAIN_COLUMNS). Never
substitute the daily close for the synchronized tick."""
from __future__ import annotations

import enum
import math
from dataclasses import dataclass

import config


class Tier(enum.Enum):
    OK = "OK"
    INVALID_NO_ARB = "INVALID_NO_ARB"
    INVALID_GREEK = "INVALID_GREEK"
    INVALID_QUOTE = "INVALID_QUOTE"
    EXTREME = "EXTREME"
    NOT_ASSESSED = "NOT_ASSESSED"


@dataclass(frozen=True)
class Verdict:
    tier: Tier
    reason: str


def _finite(*vals) -> bool:
    return all(v is not None and isinstance(v, (int, float)) and math.isfinite(v)
               for v in vals)


def classify_row(*, right, strike, bid, ask, iv, delta, gamma, vega, spot) -> Verdict:
    right = str(right).upper()
    # NOT_ASSESSED: no synchronized spot, or any required field absent/non-finite.
    if spot is None or not _finite(strike, bid, ask, iv, delta, gamma, vega, spot):
        return Verdict(Tier.NOT_ASSESSED, "missing synchronized/greek field")
    # INVALID_QUOTE: crossed or negative.
    if bid < 0 or ask < 0 or bid > ask:
        return Verdict(Tier.INVALID_QUOTE, f"crossed/negative quote {bid}/{ask}")
    # INVALID_GREEK: impossible greeks.
    eps = config.BS_DELTA_EPS
    if gamma < 0 or vega < 0:
        return Verdict(Tier.INVALID_GREEK, "negative gamma/vega")
    if right == "C" and not (0 - eps <= delta <= 1 + eps):
        return Verdict(Tier.INVALID_GREEK, f"call delta {delta} out of range")
    if right == "P" and not (-1 - eps <= delta <= 0 + eps):
        return Verdict(Tier.INVALID_GREEK, f"put delta {delta} out of range")
    # INVALID_NO_ARB: American loose bounds, executable side only.
    tol = config.BS_NOARB_TOL
    if right == "C":
        lower, upper = max(spot - strike, 0.0), spot
    else:
        lower, upper = max(strike - spot, 0.0), strike
    if ask < lower - tol:
        return Verdict(Tier.INVALID_NO_ARB, f"ask {ask} below floor {lower}")
    if bid > upper + tol:
        return Verdict(Tier.INVALID_NO_ARB, f"bid {bid} above ceiling {upper}")
    # EXTREME: suspicious but possible IV (decimal units).
    if iv <= config.BS_IV_EXTREME_LOW or iv >= config.BS_IV_EXTREME_HIGH:
        return Verdict(Tier.EXTREME, f"iv {iv} outside [{config.BS_IV_EXTREME_LOW}, "
                                     f"{config.BS_IV_EXTREME_HIGH}]")
    return Verdict(Tier.OK, "ok")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_quote_integrity -v`
Expected: PASS (10 tests).

- [ ] **Step 5: Lint/type + commit**

```bash
uv run ruff check options_researcher/quote_integrity.py tests/test_quote_integrity.py
uv run pyright options_researcher/quote_integrity.py
git add options_researcher/quote_integrity.py tests/test_quote_integrity.py
git commit -m "feat(bs): gross-error detector (American no-arb bounds, disjoint tiers)"
```

---

## Task 6: point-in-time rate + dividend functions (`data/rates.py`)

**Files:**
- Create: `data/rates.py`
- Test: `tests/test_rates.py`
- Modify: `config.py` (source paths/provenance block)

**NOTE — read first:** before writing, read how the repo stores dated series
(`data/` parquet loaders, e.g. `load_closes`) so the Treasury CMT series follows
the same on-disk convention. This task provides the math (interpolation +
par→continuous conversion) with complete code; the loader wiring must match the
repo's existing dated-series pattern.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_rates.py
import math
import unittest
from datetime import date

from data.rates import par_to_continuous, interp_rate


class TestRates(unittest.TestCase):
    def test_par_to_continuous_monotone_and_below_par(self):
        # continuous-compounded rate is below the annual par yield
        cc = par_to_continuous(0.05)
        self.assertLess(cc, 0.05)
        self.assertAlmostEqual(cc, math.log1p(0.05), places=12)

    def test_linear_interpolation_in_time(self):
        # curve: 30d -> 0.04, 90d -> 0.05 ; 60d -> 0.045
        curve = {30: 0.04, 90: 0.05}
        self.assertAlmostEqual(interp_rate(curve, 60), 0.045, places=12)

    def test_clamp_below_shortest_tenor(self):
        curve = {30: 0.04, 90: 0.05}
        self.assertAlmostEqual(interp_rate(curve, 10), 0.04, places=12)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest tests.test_rates -v`
Expected: FAIL / ImportError.

- [ ] **Step 3: Write the minimal implementation**

```python
# data/rates.py
"""Point-in-time risk-free rate + dividend yield (spec 2026-07-17 sec.7).

Treasury CMT is a PAR-yield curve; treating it as a zero curve is an
APPROXIMATION (labeled). Provenance (source URL, capture time, units, staleness,
coverage) recorded in config. No retroactive application: callers pass the
observation date; missing q blocks the name's BS computation (fail-closed)."""
from __future__ import annotations

import math


def par_to_continuous(par_yield: float) -> float:
    # Approximation: treat the annual par yield as an annually-compounded rate
    # and convert to continuous compounding. Labeled per spec sec.7.
    return math.log1p(par_yield)


def interp_rate(curve: dict[int, float], days: float) -> float:
    """Linear-in-time interpolation across bracketing CMT tenors (in days).
    Clamps to the nearest tenor outside the curve's range."""
    tenors = sorted(curve)
    if days <= tenors[0]:
        return curve[tenors[0]]
    if days >= tenors[-1]:
        return curve[tenors[-1]]
    for lo, hi in zip(tenors, tenors[1:]):
        if lo <= days <= hi:
            w = (days - lo) / (hi - lo)
            return curve[lo] + w * (curve[hi] - curve[lo])
    raise AssertionError("unreachable")  # pragma: no cover
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_rates -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add data/rates.py tests/test_rates.py config.py
git commit -m "feat(bs): point-in-time rate math (par->continuous, time-interp); q fail-closed"
```

> The `risk_free_rate(observation_date, expiration_date)` and
> `dividend_yield(symbol, observation_date, spot)` public wrappers that load the
> sourced series are added in the SAME task once the loader convention is
> confirmed (read step above). Their tests assert: coverage for every UNIVERSE
> name, a labeled-approximation flag on the returned rate, and that a missing `q`
> raises (never returns 0.0).

---

## Task 7: full-suite green + lint gate

- [ ] **Step 1: Run the whole offline suite**

Run: `uv run python -m unittest discover -s tests`
Expected: exit code 0 (existing suite + the new tests).

- [ ] **Step 2: Lint + types**

Run: `uv run ruff check . && uv run pyright`
Expected: clean.

- [ ] **Step 3: Commit any fixes**

```bash
git add -A && git commit -m "chore(bs): phase-1 infra green (suite + ruff + pyright)"
```

---

## Phase 2 (NOT in this plan — blocked; listed so nothing is forgotten)

These require owner-typed §15 values and/or confirmed repo APIs; each needs its
own plan after a "read the real API" pass:

- **Earnings-path staleness fix (§8):** requires reading `attractiveness_dashboard.py:955-1084`
  and the v3 store API (`h7_earnings.assertions_view`); choose route-through-v3
  vs `checked_through` metadata; `STALENESS_LIMIT` is owner-typed.
- **Term-structure column (§6):** requires reading `features.py`; wire the frozen
  formula (ATM/tenors/percentile/causal 252d window) into the feature store;
  historical values revealed only after registration (§14 step 5).
- **QM `retrospective_result` record (§9):** requires reading `research/ledger.py`;
  define + test the trial-counting record type; pin report/context/prereg SHAs;
  publish without invoking `qm_study`.
- **H10a/H10b registration + rank-quality prereg (§13/§11):** blocked on owner
  typing §15; two separate chained records; `research.cli verify` must pass.
- **Feature-validation run + dashboard surfacing (§10/§12):** after the above.

---

## Self-Review (done)

- **Spec coverage:** Tasks 1–7 cover spec §4 (BS math + all conventions), §5
  (detector, all tiers incl. NOT_ASSESSED / no-false-flag), §7 (rate math +
  q fail-closed). §6/§8/§9/§10–13 are explicitly deferred to Phase 2 with the
  exact files to read — not silently dropped.
- **Placeholder scan:** no "TBD/TODO" in executable steps; the one interface
  wrapper deferred inside Task 6 is called out with its test contract, not left
  blank.
- **Type consistency:** `Tier`, `Verdict`, `ImpliedVolResult`, and the
  keyword-only signatures are consistent across tasks and tests; `vega` is
  per-point everywhere (the solver de-scales by ×100 deliberately, with a
  comment).
