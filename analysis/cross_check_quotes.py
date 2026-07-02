"""
analysis/cross_check_quotes.py -- independent-source data integrity check.

Fetches the same symbol-days from DoltHub (free) and Alpha Vantage (premium
key required) and diffs bid/ask on the contracts both carry. Agreement within
a few cents on matched contracts is evidence both sources are honest; a
systematic gap means at least one is not verdict-grade.

Bypasses the parquet cache on purpose: a cross-check must compare two live
independent sources, not one source against its own cached copy.

Run:  uv run --env-file .env python analysis/cross_check_quotes.py [N_DATES]
(Read-only; makes 1 Alpha Vantage request per sampled date -- watch the quota.)
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

KEYS = ["expiration", "strike", "right"]


def compare_chains(a, b):
    """Join two CHAIN_COLUMNS frames on contract identity; diff quotes."""
    merged = a.merge(b, on=KEYS, suffixes=("_a", "_b"))
    if merged.empty:
        return {"n_matched": 0, "max_abs_bid_diff": float("nan"),
                "max_abs_ask_diff": float("nan")}
    return {
        "n_matched": int(len(merged)),
        "max_abs_bid_diff": float((merged["bid_a"] - merged["bid_b"]).abs().max()),
        "max_abs_ask_diff": float((merged["ask_a"] - merged["ask_b"]).abs().max()),
    }


def run(n_dates=5, seed=7):
    from datetime import date, timedelta
    from data import alphavantage, dolthub

    rng = random.Random(seed)
    start, end = date(2019, 3, 1), date(2026, 6, 1)
    span = (end - start).days
    symbol = config.UNIVERSE[0]
    print(f"Cross-check {symbol}: DoltHub vs Alpha Vantage, {n_dates} sampled dates")
    for _ in range(n_dates):
        d = start + timedelta(days=rng.randrange(span))
        d -= timedelta(days=max(0, d.weekday() - 4))  # weekend -> Friday
        iso = d.isoformat()
        try:
            stats = compare_chains(
                dolthub.fetch_eod_chain(symbol, iso),
                alphavantage.fetch_eod_chain(symbol, iso),
            )
        except (RuntimeError, ValueError) as exc:
            print(f"  {iso}: SKIP -- {exc}")
            continue
        print(f"  {iso}: matched {stats['n_matched']:>4} contracts | "
              f"max |bid diff| ${stats['max_abs_bid_diff']:.2f} | "
              f"max |ask diff| ${stats['max_abs_ask_diff']:.2f}")
    print("Read: diffs within a tick or two = both sources plausibly honest.")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
