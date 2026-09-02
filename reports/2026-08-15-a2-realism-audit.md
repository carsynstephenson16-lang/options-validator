# A2-v1 historical outcome battery — realism audit

**Scope:** reviewed source only: `options_researcher/a2_panel.py`,
`options_researcher/a2_battery.py`, and `options_researcher/a2_runner.py`.
This is a rank-outcome research battery, not an order-sizing or portfolio
backtest. No historical A2 execution, facts append, or ledger append occurred.

## Realism grade: B-

The battery uses exact cached contracts, adverse quote-side fills, two-sided
commission, entry/resolution liquidity checks, and explicit missing-data
exclusions, but it does not model regulatory/exchange fees, capacity, full
early-assignment/pin mechanics, or portfolio capital constraints.

## Realistic

- **Fills and spread:** long entries use adverse buys at the ask and exits use
  adverse sells at the bid; short options use the opposite adverse sides.
  Penny rounding from the shared adverse-fill helpers is retained. Bid/ask
  friction is reported separately and included in modeled cost per outcome.
- **Exact, causal quotes:** the selected contract is re-identified by
  expiration, strike, right, and deterministic symbol tie-break at each
  resolution. A missing, crossed, zero-bid, or illiquid resolution quote is
  excluded; the battery never substitutes a later quote. Entry is exact T+1.
- **Commissions:** option entry/exit paths charge the configured per-contract
  commission per side; long paths charge both sides. CSP expiry settlement and
  covered-call expiry use the documented one-side close convention.
- **Liquidity:** entry and marked resolution contracts must pass the existing
  open-interest, quote-validity, and spread gates. The data audit separately
  surfaces selected-contract defects.
- **Expiration and assignment visibility:** CSP settlement uses intrinsic value
  against the raw underlying close; CSP assignment-accepting and covered-call
  assignment/lost-upside are explicit components. Covered calls use a
  same-close hypothetical 100-share benchmark rather than a hidden stock basis.
- **Earnings:** LEAPS records a point-in-time earnings-exposure count; earnings
  assertions supplied to ranking reconstruction are filtered at decision time.

## Fake or missing

1. **Regulatory/exchange/clearing fees are absent.** Bias: inflates net results,
   especially short-dated/high-turnover arms.
2. **No market-impact or size-versus-OI/volume capacity model exists.** The
   liquidity gate establishes contract eligibility, not whether a specified
   portfolio could fill. Bias: can inflate scalability; per-one-contract outcome
   direction is otherwise indeterminate.
3. **Early assignment, ex-dividend exercise incentives, pin risk, and
   expiration-weekend settlement details are not fully simulated.** Intrinsic
   expiry payoff and two assignment-related components do not cover forced
   early exercise or operational closing costs. Bias: generally inflates short
   option/CSP/covered-call results; direction for long calls is mixed.
4. **CSP collateral carry uses one matched Treasury rate and calendar-day
   compounding, but does not model broker-specific margin, interest-crediting,
   tax, or cash-sweep rules.** Bias: ambiguous for the reported return; it can
   over- or understate realized account economics.
5. **No portfolio capital, buying-power, concentration, concurrent-position,
   or max-loss cap is applied.** This is appropriate to the stated
   cross-sectional rank-outcome question, but it means results cannot describe
   account-level deployability. Bias: can inflate a portfolio interpretation;
   no direct bias to a per-contract spread.
6. **No separate fast-market slippage beyond displayed bid/ask adverse fills is
   modeled.** Bias: generally inflates results during stressed exits.
7. **PIT FOMC provenance is currently an execution-data blocker.** The runner
   refuses a missing or dates-only FOMC file; without a provenance-bearing
   input, ranking rows requiring the FOMC feature cannot be constructed. This
   is distinct from the B- simulation grade: it makes the governed historical
   run **NO-GO**, rather than lowering the modeled-fill grade.

## Required fixes before the result counts

1. Before any invocation, provide and validate the provenance-bearing PIT FOMC
   input required by the runner; do not replace it with a hindsight dates list.
2. Run the programmatic data audit over actual selected contracts and stop on
   any `BLOCK`; retain warnings and exclusions in the immutable report.
3. Disclose the missing fees, capacity, early-assignment/pin mechanics, and
   absent portfolio sizing/capital controls in the report and red-team review;
   do not translate a rank outcome into a deployable strategy claim.
4. If the work is ever extended to portfolio or live-paper decisions, add
   broker-specific buying power, position sizing, concentration/max-loss limits,
   fees, ex-dividend assignment treatment, and stressed-exit assumptions under
   a separately approved registration.

## Ledger note

`A2-v1 realism audit: B- for per-contract historical rank-outcome mechanics; NO-GO pending PIT FOMC provenance and actual selected-contract data audit; research-only, no verdict or promotion.`
