---
name: options-data-audit
description: Audit options chain data quality before any backtest run or after loading new data. Use whenever new options chain data (the immutable ThetaData cache or a Schwab-lane capture) is fetched, cached, or loaded, before running a backtest on data that hasn't been audited this session, or when results look suspicious (too good, too smooth, impossible fills).
---

# Options Data Audit

Bad data produces confident garbage. No backtest runs on unaudited data. The audit must be run by CODE that prints results, not by eyeballing a dataframe — write or run an audit script and show its output.

Provider note: the historical corpus is the immutable cached ThetaData parquet; the live lane is Schwab preclose capture. Schwab supplies no dated historical chains, point-in-time open interest, or historical Greeks, and no Schwab response enters `.cache/chains` (`.claude/rules/data-and-providers.md`). On a Schwab-lane package, checks that need OI/Greeks history report N/A explicitly — an N/A is honest; a silently skipped check is not.

## Checks (all required)

**Completeness**
1. Missing trading dates vs. the exchange calendar for the test window
2. Missing expirations that should exist (weekly/monthly cadence gaps)
3. Missing strikes near the money (gaps far OTM are normal; gaps near ATM are not)
4. Rows with missing bid or ask

**Sanity**
5. Negative bid, ask, volume, or open interest
6. Bid > ask (crossed market — almost always bad data)
7. Zero bid with large ask (may be real for far OTM, flag if near the money)
8. Bid/ask spread > 20% of mid on contracts the strategy would trade — flag each
9. Stale timestamps (quote time far from the bar time being simulated)
10. IV values that are missing, zero, negative, or > 500%
11. Greeks outside possible ranges (|delta| > 1, negative gamma on longs, etc.)

**Structural**
12. Duplicate contract rows (same date, expiry, strike, right)
13. Underlying close in the options file vs. an independent equity source — mismatch > 0.5% = flag (catches split/adjustment errors, which are the #1 silent killer for CEG/VST-type names that have had corporate actions)
14. Expiration calendar sanity: no expirations on weekends/holidays

## Verdict

- **PASS** — all checks clean
- **PASS WITH WARNINGS** — issues exist but don't touch contracts the strategy trades; list every warning
- **BLOCK** — any failed check touches tradeable contracts. State exactly which rows/dates and what fetching or cleaning step must happen first. Do not run the backtest. Do not "just exclude those rows" without logging that exclusion as a data decision in the ledger, because selective exclusion is a backdoor for bias.

## Output

**Data audited:** file/table, tickers, date range, row count.
**Failed checks:** numbered, with example rows.
**Warnings:** numbered.
**Verdict:** PASS / PASS WITH WARNINGS / BLOCK.
**Ledger note:** one line describing the audit result to append to the experiment ledger.
