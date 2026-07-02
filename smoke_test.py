"""
smoke_test.py -- Phase 0 sanity check: fetch ONE symbol's chain for ONE day and
print it. Proves data access works before anything else is built.

Run from repo root:  python smoke_test.py
(Raises NotImplementedError until the ThetaData fetch is wired in
data/thetadata_adapter.py -- that is expected at Phase 0.)
"""
import config
from data.thetadata_adapter import get_eod_chain

SMOKE_TEST_DATE = "2022-12-30"  # last trading day before IN_SAMPLE_END


def main():
    symbol = config.UNIVERSE[0]
    date = SMOKE_TEST_DATE
    print(f"Fetching EOD chain: {symbol} @ {date}")
    chain = get_eod_chain(symbol, date)
    print(chain.head(20).to_string())
    print(f"\nrows: {len(chain)}   expirations: {chain['expiration'].nunique()}")


if __name__ == "__main__":
    main()
