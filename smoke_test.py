"""
smoke_test.py -- minute-one check for the paid ThetaData month: fetch ONE
symbol's chain for ONE in-sample day, summarize it, and record an audit fact.

The adapter (data/thetadata_adapter.py) is wired, not stubbed. This script
reads a cached parquet chain when available and otherwise fetches through the
official ThetaData Python client. There is no synthetic fallback path: missing
credentials, missing options entitlement, or unexpected provider schema must
fail loud.

SMOKE_TEST_DATE must NEVER be moved to a date after config.IN_SAMPLE_END --
this script only ever touches in-sample data (the adapter also guards this,
but main() refuses first, belt-and-braces).

Run from repo root:  python smoke_test.py
"""
import pandas as pd

import config
from data.thetadata_adapter import get_eod_chain, passes_liquidity
from research import facts

SMOKE_TEST_DATE = "2022-12-30"  # last trading day before IN_SAMPLE_END

# Candidate short-put band: config.A_SHORT_PUT_DELTA = 0.30 is the target
# ~30-delta short put; 0.25-0.35 is the surrounding band summarize_chain
# reports as "candidates" for that leg -- not a strict match on 0.30 itself.
# The +/-0.05 width is a REPORTING band only (strike grids are discrete, so
# the nearest-|delta| match rarely sits exactly on 0.30); it feeds no verdict
# and no selection logic -- strike selection matches nearest |delta| in the
# strategy, not this band.
CANDIDATE_SHORT_PUT_DELTA_LOW = 0.25
CANDIDATE_SHORT_PUT_DELTA_HIGH = 0.35


def summarize_chain(chain: pd.DataFrame) -> dict:
    puts = chain[chain["right"] == "P"]
    calls = chain[chain["right"] == "C"]
    liquid = chain[chain.apply(
        lambda row: passes_liquidity(row["open_interest"], row["bid"], row["ask"]),
        axis=1,
    )]
    candidate_short_puts = puts[
        puts["delta"].abs().between(
            CANDIDATE_SHORT_PUT_DELTA_LOW, CANDIDATE_SHORT_PUT_DELTA_HIGH
        )
    ]
    return {
        "rows": len(chain),
        "expirations": chain["expiration"].nunique(),
        "puts": len(puts),
        "calls": len(calls),
        "liquid_rows": len(liquid),
        "candidate_short_puts": len(candidate_short_puts),
    }


def main(ledger_dir="ledger"):
    if SMOKE_TEST_DATE > config.IN_SAMPLE_END:
        raise ValueError(
            f"SMOKE_TEST_DATE={SMOKE_TEST_DATE} is after "
            f"IN_SAMPLE_END={config.IN_SAMPLE_END}; this script must never "
            "touch post-in-sample data."
        )

    symbol = config.UNIVERSE[0]
    date = SMOKE_TEST_DATE
    print(f"Fetching EOD chain: {symbol} @ {date}")
    chain = get_eod_chain(symbol, date)
    print(chain.head(20).to_string())

    summary = summarize_chain(chain)
    print()
    for key, value in summary.items():
        print(f"{key}: {value}")

    fact = (
        f"SMOKE_TEST symbol={symbol} date={date} "
        + " ".join(f"{key}={value}" for key, value in summary.items())
    )
    facts.append_fact(fact, base_dir=ledger_dir)


if __name__ == "__main__":
    main()
