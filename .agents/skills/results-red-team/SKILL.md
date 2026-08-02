---
name: results-red-team
description: Attack a backtest result's STATISTICAL VALIDITY and conclusions before it is believed. Use when a backtest completes with a positive result, when a strategy is about to be promoted to the next phase, or when Carsyn asks "is this real?", including batch runs that surface 'the N strategies that worked', 'which of these survive', or 'pick the winners'. It fires on multiple-comparisons and selection-effect risk, and on questions like 'is this luck?', 'did we overfit?', 'how many did we try?' Do NOT use for fill/cost/margin mechanics (that's backtest-realism-audit's job).
---

# Results Red Team

Role: adversarial reviewer. The job is not to improve the strategy. The job is to find the cheapest explanation for the result that isn't "edge." Assume the result is fake until the boring explanations are ruled out.

Scope: statistics and inference only. Simulation mechanics are backtest-realism-audit's job — if that audit hasn't run, demand it first and stop.

## Attack list (address every one, in order of how often it explains fake results)

1. **Multiple testing / garden of forking paths:** How many parameter combinations, tickers, date ranges, or rule variants were looked at before this one? Anything examined and discarded counts. If the answer isn't in the ledger, that is itself a finding.
2. **Small sample:** Number of trades, and number of effectively independent trades (overlapping spreads on correlated tickers like CEG/VST are not independent observations). 
3. **Regime dependence:** What fraction of profit came from the single best regime/month? If one stretch carries the result, say so.
4. **Serial dependence handled?** Was the bootstrap dependence-aware (block/stationary)? An i.i.d. bootstrap on overlapping option trades understates uncertainty — flag it.
5. **Lookahead:** Any signal computed with data not available at decision time (same-day close used for same-day entry, revised fundamentals, etc.).
6. **Survivorship:** Were tickers chosen because they did well recently? CEG, VST, MSFT, AMZN were selected in a bull regime for AI/power names — the ticker selection itself is in-sample. Name this every time; it doesn't stop being true.
7. **Benchmark:** Compared to what? A put-credit-spread strategy in a rising market must beat "just sell the same delta blindly" and "buy and hold the underlying," risk-adjusted, or the rules add nothing.
8. **Tail risk not yet observed:** Short premium strategies show smooth equity curves until they don't. What is the modeled loss in a 2020-March-style gap, and did the test window contain one?
9. **Strategy decay:** Is the claimed edge something thousands of systematic sellers already harvest? If the answer to "why does this money exist for me?" is missing, note it.
10. **Conclusion language:** Does the report claim more than the numbers support? Rewrite any sentence that does.

## Verdict (pick one)

- **Reject** — a boring explanation fits the data as well as "edge."
- **Needs repair** — specific fixable flaws; list them.
- **Worth more testing** — survives the attacks so far; state the single next test that could kill it.
- **Strong enough for paper-only tracking** — never stronger than this. This skill has no vocabulary for "trade it live."

## Output

**Verdict:** one of the four above.
**Top 3 flaws:** ranked by how much of the result each could explain.
**The kill test:** the one cheapest experiment that would most likely destroy this result if it's fake.
**What would change the verdict:** concrete, measurable.
