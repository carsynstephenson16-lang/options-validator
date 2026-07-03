"""
analysis/feasibility.py -- a-priori feasibility check.

Before any backtest, answer a blunt question: given the hard per-trade dollar
cap (MAX_LOSS_PER_TRADE), can a single spread even FIT, and what does the
PORTFOLIO look like when every universe name holds a position at once? Small
caps and wide spreads can (correctly) buy ZERO contracts -- better to learn
that here than to run a 7-year backtest that silently trades nothing. And a
per-trade cap that looks tame can still stack into a large simultaneous risk
across a ~1.5-effective-bet universe.

This version uses ASSUMED credit estimates. Once the ThetaData adapter works,
replace ASSUMED_CREDIT_FRAC with the median credit actually observed in the
fetched chains.

Run from the repo root:  python analysis/feasibility.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from strategies.base import (  # noqa: E402
    capital_at_risk_per_spread,
    economic_max_loss_per_spread,
    risk_budget,
    round_trip_commission_per_spread,
)

# Rule of thumb: a 30-delta, $W-wide put credit spread collects on the order of
# 25-35% of the width in net credit. We use the midpoint; it is an ASSUMPTION
# to be replaced by measured chain data.
ASSUMED_CREDIT_FRAC = 0.30


def max_loss_per_spread(width, credit):
    """Defined risk = (width - net credit) per share x 100 shares."""
    return capital_at_risk_per_spread(width, credit)


def contracts_that_fit(risk_budget, max_loss):
    if max_loss <= 0:
        return 0
    return math.floor(risk_budget / max_loss)


def run():
    widths = config.A_SPREAD_WIDTH_SWEEP
    budget = risk_budget()
    cap_pct = budget / config.RISK_SLEEVE

    print("=" * 78)
    print(f"FEASIBILITY: what fits a hard ${budget:,.0f}/trade cap "
          f"({cap_pct:.1%} of the ${config.RISK_SLEEVE:,} sleeve)?")
    print(f"(assumed net credit = {ASSUMED_CREDIT_FRAC:.0%} of width "
          "-- replace with measured data)")
    print("Sizing basis: ECONOMIC max loss = broker margin + round-trip commissions")
    print("=" * 78)

    for width in widths:
        credit = ASSUMED_CREDIT_FRAC * width
        margin = max_loss_per_spread(width, credit)
        rt_comm = round_trip_commission_per_spread()
        economic = economic_max_loss_per_spread(width, credit)
        comm_drag = rt_comm / (credit * 100.0)
        n = contracts_that_fit(budget, economic)
        fit = "FITS" if n >= 1 else "ZERO -- does not fit"
        tail = f"  using ${n * economic:.2f} economic risk" if n >= 1 else ""
        print(f"\nWidth ${width}  |  assumed credit ${credit:.2f}  |  "
              f"broker margin ${margin:.0f}/contract  |  "
              f"economic max loss ${economic:.2f}/contract")
        print(f"   round-trip commission ${rt_comm:.2f} = "
              f"{comm_drag:.1%} of the ${credit*100:.0f} credit (before bid-ask)")
        print(f"   cap ${budget:,.0f} -> {n} contract(s)  [{fit}]{tail}")

    # ---- the portfolio view the per-trade cap hides -------------------------
    n_names = len(config.UNIVERSE)
    worst = n_names * budget
    print("\n" + "-" * 78)
    print(f"PORTFOLIO CONCENTRATION ({n_names} names, ~1.5 effective bets):")
    print(f"   {n_names} concurrent positions x ${budget:,.0f} cap = "
          f"${worst:,.0f} at SIMULTANEOUS risk = {worst / config.RISK_SLEEVE:.1%} "
          "of the sleeve.")
    print("   These names lose TOGETHER in a tech drawdown -- treat the worst")
    print("   case as one bet of that size, not five independent ones.")
    print("-" * 78)
    print("Reading this: a width showing ZERO is INFEASIBLE at the current cap.")
    print("Do NOT raise MAX_LOSS_PER_TRADE just to make a width fit -- that is")
    print("reverse-engineering risk to fit the trade.")
    print("-" * 78)


if __name__ == "__main__":
    run()
