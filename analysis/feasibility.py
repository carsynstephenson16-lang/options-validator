"""
analysis/feasibility.py -- measured pre-backtest feasibility check.

Before any new hypothesis, answer a blunt question from the REAL cached
in-sample chains: can the configured spread width find an expiration, exact
long-leg strike, liquid legs, positive conservative credit, and at least one
contract under the hard economic-risk cap?

The old 30%-of-width credit estimate remains as ASSUMED_CREDIT_FRAC for
hash-compatibility with already-recorded research artifacts and as a clearly
labeled fallback when no cached chain observations exist. It is not used when
measured candidates are available.

Run from the repo root:
    uv run python analysis/feasibility.py
"""
from __future__ import annotations

import math
import os
import sys
from collections import Counter
from datetime import date as Date

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from data import pandas_feed  # noqa: E402
from data.thetadata_adapter import OOSDataTouchError  # noqa: E402
from strategies.base import (  # noqa: E402
    capital_at_risk_per_spread,
    economic_max_loss_per_spread,
    risk_budget,
    round_trip_commission_per_spread,
)
from strategies.put_credit_spread import select_put_credit_spread_candidate  # noqa: E402

# Hash-compatibility constant and no-data fallback only. The measured report
# below uses cached chain quotes whenever they are present.
ASSUMED_CREDIT_FRAC = 0.30


def max_loss_per_spread(width, credit):
    """Defined risk = (width - net credit) per share x 100 shares."""
    return capital_at_risk_per_spread(width, credit)


def contracts_that_fit(risk_budget, max_loss):
    if max_loss <= 0:
        return 0
    return math.floor(risk_budget / max_loss)


def _percentiles(values):
    if not values:
        return {"p25": None, "median": None, "p75": None}
    arr = np.array(values, dtype=float)
    return {
        "p25": float(np.percentile(arr, 25)),
        "median": float(np.percentile(arr, 50)),
        "p75": float(np.percentile(arr, 75)),
    }


def _contracts_summary(values):
    if not values:
        return {"min": None, "median": None, "max": None}
    arr = np.array(values, dtype=float)
    return {
        "min": int(arr.min()),
        "median": float(np.percentile(arr, 50)),
        "max": int(arr.max()),
    }


def _empty_summary(width):
    return {
        "width": width,
        "observations": 0,
        "accepted": 0,
        "skip_reasons": {},
        "credit": _percentiles([]),
        "economic_max_loss": _percentiles([]),
        "contracts": _contracts_summary([]),
    }


def measured_feasibility(
    symbols=None,
    widths=None,
    *,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    """Measure entry-candidate feasibility from cached in-sample chains only.

    Missing cache files are treated as unavailable observations, not network
    fetch tasks. Any post-IN_SAMPLE_END request is refused here; OOS values are
    reachable only through the reveal gate.
    """
    symbols = list(config.UNIVERSE) if symbols is None else list(symbols)
    widths = list(config.A_SPREAD_WIDTH_SWEEP) if widths is None else list(widths)
    start = start or config.BACKTEST_START
    end = end or config.IN_SAMPLE_END

    start_d = Date.fromisoformat(start)
    end_d = Date.fromisoformat(end)
    if end_d < start_d:
        raise ValueError(f"end {end} is before start {start}")
    if end_d > Date.fromisoformat(config.IN_SAMPLE_END):
        raise OOSDataTouchError(
            f"feasibility end {end} is past IN_SAMPLE_END={config.IN_SAMPLE_END}; "
            "OOS chain values may only be opened through the reveal gate."
        )

    raw = {
        width: {
            "observations": 0,
            "accepted": 0,
            "skip_reasons": Counter(),
            "credits": [],
            "economic_max_losses": [],
            "contracts": [],
        }
        for width in widths
    }
    cached_chain_days = 0

    for symbol in symbols:
        chains = pandas_feed.load_cached_chains(symbol, start, end, allow_oos=False)
        cached_chain_days += len(chains)
        for iso_day, chain in chains.items():
            today = Date.fromisoformat(iso_day)
            for width in widths:
                stats = raw[width]
                stats["observations"] += 1
                selection = select_put_credit_spread_candidate(
                    chain,
                    today,
                    width=width,
                    delta=config.A_SHORT_PUT_DELTA,
                    dte_band=config.A_TARGET_DTE,
                    haircut=config.SLIPPAGE_HAIRCUT,
                )
                if not selection.accepted:
                    stats["skip_reasons"][selection.reason] += 1
                    continue
                assert selection.credit is not None
                assert selection.economic_max_loss is not None
                stats["accepted"] += 1
                stats["credits"].append(float(selection.credit))
                stats["economic_max_losses"].append(float(selection.economic_max_loss))
                stats["contracts"].append(int(selection.contracts))

    summaries = {}
    for width, stats in raw.items():
        summary = _empty_summary(width)
        summary.update({
            "observations": stats["observations"],
            "accepted": stats["accepted"],
            "skip_reasons": dict(sorted(stats["skip_reasons"].items())),
            "credit": _percentiles(stats["credits"]),
            "economic_max_loss": _percentiles(stats["economic_max_losses"]),
            "contracts": _contracts_summary(stats["contracts"]),
        })
        summaries[width] = summary

    return {
        "start": start,
        "end": end,
        "symbols": symbols,
        "cached_chain_days": cached_chain_days,
        "widths": summaries,
    }


def _fmt_money(value):
    return "n/a" if value is None else f"${value:.2f}"


def _fmt_num(value):
    return "n/a" if value is None else f"{value:g}"


def _print_measured_report(report):
    print("MEASURED FROM CACHED IN-SAMPLE CHAINS")
    print(
        f"Window {report['start']}..{report['end']} | "
        f"symbols={','.join(report['symbols'])} | "
        f"cached chain-days={report['cached_chain_days']}"
    )
    if report["cached_chain_days"] == 0:
        print("No cached in-sample chains found; measured feasibility unavailable.")
        return

    for width, stats in report["widths"].items():
        credit = stats["credit"]
        economic = stats["economic_max_loss"]
        contracts = stats["contracts"]
        obs = stats["observations"]
        accepted = stats["accepted"]
        rate = accepted / obs if obs else 0.0
        print(f"\nWidth ${width} | observations {obs} | accepted {accepted} ({rate:.1%})")
        print(
            "   conservative credit p25/median/p75: "
            f"{_fmt_money(credit['p25'])} / "
            f"{_fmt_money(credit['median'])} / "
            f"{_fmt_money(credit['p75'])}"
        )
        print(
            "   economic max loss p25/median/p75: "
            f"{_fmt_money(economic['p25'])} / "
            f"{_fmt_money(economic['median'])} / "
            f"{_fmt_money(economic['p75'])}"
        )
        print(
            "   contracts that fit min/median/max: "
            f"{_fmt_num(contracts['min'])} / "
            f"{_fmt_num(contracts['median'])} / "
            f"{_fmt_num(contracts['max'])}"
        )
        if stats["skip_reasons"]:
            reasons = ", ".join(
                f"{reason}={count}" for reason, count in stats["skip_reasons"].items()
            )
            print(f"   skipped: {reasons}")
        else:
            print("   skipped: none")


def _print_assumption_fallback(widths):
    budget = risk_budget()
    print("\nASSUMPTION FALLBACK ONLY")
    print(
        f"ASSUMED_CREDIT_FRAC={ASSUMED_CREDIT_FRAC:.0%} is retained for old hashes "
        "and no-cache what-if arithmetic; measured rows above are authoritative."
    )
    for width in widths:
        credit = ASSUMED_CREDIT_FRAC * width
        margin = max_loss_per_spread(width, credit)
        rt_comm = round_trip_commission_per_spread()
        economic = economic_max_loss_per_spread(width, credit)
        comm_drag = rt_comm / (credit * 100.0)
        n = contracts_that_fit(budget, economic)
        fit = "FITS" if n >= 1 else "ZERO -- does not fit"
        tail = f" using ${n * economic:.2f} economic risk" if n >= 1 else ""
        print(
            f"   Width ${width}: assumed credit ${credit:.2f}, "
            f"margin ${margin:.0f}, economic max loss ${economic:.2f}, "
            f"commission drag {comm_drag:.1%}, cap -> {n} [{fit}]{tail}"
        )


def _print_portfolio_view():
    budget = risk_budget()
    n_names = len(config.UNIVERSE)
    worst = n_names * budget
    print("\n" + "-" * 78)
    print(f"PORTFOLIO CONCENTRATION ({n_names} names, ~1.5 effective bets):")
    print(
        f"   {n_names} concurrent positions x ${budget:,.0f} cap = "
        f"${worst:,.0f} at SIMULTANEOUS risk = "
        f"{worst / config.RISK_SLEEVE:.1%} of the sleeve."
    )
    print("   These names lose together in a tech drawdown; treat the worst")
    print("   case as one bet of that size, not independent bets.")
    print("-" * 78)
    print("Reading this: measured ZERO means the real chain gates found no fit.")
    print("Do NOT raise MAX_LOSS_PER_TRADE just to make a width fit -- that is")
    print("reverse-engineering risk to fit the trade.")
    print("-" * 78)


def run():
    widths = config.A_SPREAD_WIDTH_SWEEP
    budget = risk_budget()
    cap_pct = budget / config.RISK_SLEEVE

    print("=" * 78)
    print(
        f"FEASIBILITY: hard ${budget:,.0f}/trade economic-risk cap "
        f"({cap_pct:.1%} of the ${config.RISK_SLEEVE:,} sleeve)"
    )
    print("Sizing basis: broker margin plus round-trip commissions")
    print("=" * 78)

    report = measured_feasibility(widths=widths)
    _print_measured_report(report)
    _print_assumption_fallback(widths)
    _print_portfolio_view()


if __name__ == "__main__":
    run()
