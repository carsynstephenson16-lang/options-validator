"""
analysis/feasibility.py -- a-priori feasibility check.

Before any backtest, answer a blunt question: given your risk sleeve and the
1%-per-trade rule, can a single spread even FIT? With small accounts and wide
spreads the sizing rule often (correctly) buys ZERO contracts. Better to learn
that here than to run a 7-year backtest that silently trades nothing.

This version uses ASSUMED credit estimates. Once the ThetaData adapter works,
replace ASSUMED_CREDIT_FRAC with the median credit actually observed in the
fetched chains.

Run from the repo root:  python analysis/feasibility.py
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

# Rule of thumb: a 30-delta, $W-wide put credit spread collects on the order of
# 25-35% of the width in net credit. We use the midpoint; it is an ASSUMPTION
# to be replaced by measured chain data.
ASSUMED_CREDIT_FRAC = 0.30


def max_loss_per_spread(width, credit):
    """Defined risk = (width - net credit) per share x 100 shares."""
    return (width - credit) * 100.0


def contracts_that_fit(risk_budget, max_loss):
    if max_loss <= 0:
        return 0
    return math.floor(risk_budget / max_loss)


def run():
    widths = config.A_SPREAD_WIDTH_SWEEP
    sleeves = config.RISK_SLEEVE_CANDIDATES
    rpt = config.RISK_PER_TRADE
    commission = config.COMMISSION_PER_CONTRACT

    print("=" * 78)
    print("FEASIBILITY: can a single spread fit the 1%-per-trade rule?")
    print(f"(assumed net credit = {ASSUMED_CREDIT_FRAC:.0%} of width "
          "-- replace with measured data)")
    print("=" * 78)

    for width in widths:
        credit = ASSUMED_CREDIT_FRAC * width
        mloss = max_loss_per_spread(width, credit)
        rt_comm = commission * 4          # 2 legs x open+close
        comm_drag = rt_comm / (credit * 100.0)
        print(f"\nWidth ${width}  |  assumed credit ${credit:.2f}  |  "
              f"max loss ${mloss:.0f}/contract")
        print(f"   round-trip commission ${rt_comm:.2f} = "
              f"{comm_drag:.1%} of the ${credit*100:.0f} credit (before bid-ask)")
        for sleeve in sleeves:
            budget = sleeve * rpt
            n = contracts_that_fit(budget, mloss)
            fit = "FITS" if n >= 1 else "ZERO -- does not fit"
            tail = f"  using ${n*mloss:.0f} buying power" if n >= 1 else ""
            print(f"   sleeve ${sleeve:>6,} -> 1% budget ${budget:>6.0f} -> "
                  f"{n} contract(s)  [{fit}]{tail}")

    print("\n" + "-" * 78)
    print("Reading this: if a width shows ZERO across your real sleeve size, that")
    print("width is INFEASIBLE for you at 1% risk -- narrow the width or use a")
    print("larger sleeve. Do NOT raise RISK_PER_TRADE just to make a trade fit.")
    print("-" * 78)


if __name__ == "__main__":
    run()
