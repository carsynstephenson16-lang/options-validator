"""Compare the local Black-Scholes implementation with Git-pinned vollib.

This is a diagnostic tool, not a production pricing adapter. It deliberately
tests only the shared European Black-Scholes-Merton price convention.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from vollib.black_scholes_merton import black_scholes_merton  # noqa: E402

from options_researcher.black_scholes import bs_price  # noqa: E402

CASES = (
    (100.0, 100.0, 1.0, 0.05, 0.20, 0.00),
    (123.0, 110.0, 0.5, 0.04, 0.35, 0.01),
    (80.0, 95.0, 0.25, 0.01, 0.60, 0.02),
    (220.0, 240.0, 1.75, 0.045, 0.28, 0.00),
)
ABS_TOL = 1e-10


def main() -> int:
    failures: list[str] = []
    comparisons = 0
    for S, K, t, r, sigma, q in CASES:
        for right in ("C", "P"):
            local = bs_price(S=S, K=K, t=t, r=r, sigma=sigma, right=right, q=q)
            reference = black_scholes_merton(right.lower(), S, K, t, r, sigma, q)
            comparisons += 1
            if not math.isclose(local, reference, rel_tol=0.0, abs_tol=ABS_TOL):
                failures.append(
                    f"{right} S={S} K={K} t={t}: local={local:.15g} "
                    f"vollib={reference:.15g}"
                )

    print(f"vollib parity comparisons: {comparisons}")
    if failures:
        print("FAIL: local Black-Scholes drifted from vollib")
        print("\n".join(failures))
        return 1
    print(f"PASS: all comparisons within {ABS_TOL:g} absolute price units")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
