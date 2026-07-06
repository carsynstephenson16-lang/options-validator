---
name: backtest-realism-audit
description: Audit whether a backtest's SIMULATION MECHANICS are realistic — fills, costs, liquidity, assignment, margin, position sizing. Use before trusting any backtest result, after changing execution/fill/cost code, or when a result looks better than expected. Do NOT use for statistical validity or overfitting questions (that's results-red-team's job).
---

# Backtest Realism Audit

Scope: only the simulation itself. Does the code trade the way a real account at a real broker could? Statistical questions (overfitting, sample size, regime luck) belong to results-red-team — do not duplicate them here.

## Checks

**Fills and costs**
1. Entry fill: at what price does the sim assume it gets filled? Mid-price fills on options are fantasy. Realistic default: worse than mid by at least 25-50% of the half-spread per leg. State the exact assumption in the code.
2. Exit fill: same question. Exits under stress (stop-loss on a spread going wrong) fill worse than calm entries.
3. Spread cost: is bid/ask crossing cost modeled per leg, per trade?
4. Commissions and fees: per-contract commission AND regulatory/exchange fees, both sides, all legs.
5. Slippage on top of spread for market orders or fast markets.

**Liquidity**
6. Volume/open-interest gate: would the position size actually fill without moving the market? Rule of thumb to check against: position > 1% of open interest or > 5% of daily volume = flag.
7. Are quotes on the exact contracts traded real quotes, or interpolated/synthetic?

**Options-specific mechanics**
8. Early assignment: put credit spreads on dividend-paying or hard-to-borrow names can be assigned early. Is assignment simulated at all? If not, state the worst case it hides.
9. Expiration handling: pin risk, exercise-by-exception at 0.01 ITM, weekend risk between expiration and settlement.
10. Earnings and event handling: does the sim hold spreads through earnings? If yes, was that the pre-registered intent? Gaps through short strikes are where credit spreads die.

**Account mechanics**
11. Margin/buying power: is capital usage computed the way a real broker computes spread margin (width minus credit)? Does the sim ever use more capital than the stated account size?
12. Position sizing: fixed contracts, fixed risk, or compounding? Compounding on a small sample inflates results.
13. Max-loss logic: can a simulated trade lose more than the spread width says is possible? (If yes, the fill model is broken.)

## Output

**Realism grade:** A-F with one-sentence justification.
**Realistic:** what's modeled correctly, briefly.
**Fake or missing:** numbered list, each with the direction of the bias (does this flaw inflate or deflate results?) — this direction matters more than the flaw itself.
**Required fixes before the result counts:** ordered by impact.
**Ledger note:** one line for the experiment ledger.
