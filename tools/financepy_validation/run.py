"""Evaluate FinancePy's analytic Black-Scholes engine against local BS.

FinancePy stays isolated because its GPL-3.0-or-later license and broad
dependency surface are not appropriate for the root runtime.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from financepy.models.black_scholes import BlackScholes, BlackScholesTypes  # noqa: E402
from financepy.utils.global_types import OptionTypes  # noqa: E402

from options_researcher.black_scholes import bs_price  # noqa: E402

CASES = (
    (100.0, 100.0, 1.0, 0.05, 0.20, 0.00),
    (123.0, 110.0, 0.5, 0.04, 0.35, 0.01),
    (80.0, 95.0, 0.25, 0.01, 0.60, 0.02),
    (220.0, 240.0, 1.75, 0.045, 0.28, 0.00),
)
MAX_ALLOWED_DRIFT = 1e-4


def main() -> int:
    failures: list[str] = []
    comparisons = 0
    max_drift = 0.0
    for S, K, t, r, sigma, q in CASES:
        model = BlackScholes(sigma, BlackScholesTypes.ANALYTICAL)
        for right, option_type in (
            ("C", OptionTypes.EUROPEAN_CALL),
            ("P", OptionTypes.EUROPEAN_PUT),
        ):
            local = bs_price(S=S, K=K, t=t, r=r, sigma=sigma, right=right, q=q)
            reference = model.value(S, t, K, r, q, option_type)
            comparisons += 1
            drift = abs(local - reference)
            max_drift = max(max_drift, drift)
            if not math.isclose(local, reference, rel_tol=0.0, abs_tol=MAX_ALLOWED_DRIFT):
                failures.append(
                    f"{right} S={S} K={K} t={t}: local={local:.15g} "
                    f"FinancePy={reference:.15g} drift={drift:.6g}"
                )

    print(f"FinancePy analytic comparisons: {comparisons}; max drift={max_drift:.6g}")
    if failures:
        print("FAIL: FinancePy and local Black-Scholes differ")
        print("\n".join(failures))
        return 1
    print(
        "PASS: all comparisons within "
        f"{MAX_ALLOWED_DRIFT:g} absolute price units; numerical drift is reported"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
