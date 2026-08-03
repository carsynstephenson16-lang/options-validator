# ThetaData Options-Flow Intelligence — Point-in-Time Historical Analogs

**Status:** IMPLEMENTED OFFLINE / DISPLAY-ONLY / DATA ACQUISITION NOT AUTHORIZED

**Methodology:** `options_flow_analogs_v2`
**Authority:** This work cannot change H5–H10 triggers, scoring, ranking, sizing,
registration, paper-trading authority, or live execution.

## 1. Audit decisions

The implementation accepts the market-reality criticism without adopting
statistically or causally invalid shortcuts.

| Proposed correction | Decision | Implemented treatment |
|---|---|---|
| Replace RMS with Mahalanobis | Accept the covariance criticism; reject raw 60-session inversion | Prior-only robust standardization, fixed 0.50 diagonal shrinkage, eigendecomposition, eigenvalue floor, effective-rank gate, and RMS neighbor-stability comparison |
| Restore DTE and moneyness | Accept | Nonredundant DTE shares, weighted median `log1p(DTE)`, option-correct log moneyness, ATM/deep-OTM shares, and explicit timestamp-safe coverage |
| Embargo every future SEC filing | Reject as lookahead | Match events only when public by the historical cutoff; later filings are sensitivity labels only |
| Add IV regime | Accept | Previous-close ATM30 IV percentile, one-day IV change, ATM60–ATM30 term slope, 25-delta put skew, and no-extrapolation total-variance interpolation |
| Use net notional to identify dealer hedging | Reject as unidentified | Gross premium/ADV and gross delta/gamma/vega intensity, with complex exclusions, verified units, and 90% eligible-volume coverage |

Equal-weight Euclidean distance does not literally assume independence; its
defect here is duplicated influence from correlated coordinates. Likewise,
small option premium relative to stock ADV is not proof of zero predictability.
Economic scale is measured and tested rather than hardcoded as a verdict.

## 2. Data and point-in-time contract

Raw ThetaData trade/quote and prior-known OI remain immutable and receipt-bound.
No test performs a paid request.

- Option trade classification uses the strict-prior option NBBO.
- Trade-time moneyness uses the most recent underlying midpoint at or before the
  trade. Session prices remain visibly labeled as proxies and cannot qualify a
  validated point-in-time analog.
- Missing OI remains missing, never zero.
- Previous-close IV context requires 252 valid earlier sessions. The planned
  acquisition must therefore include at least 300 completed sessions before the
  first evaluated flow date.
- Contract multiplier and Greek units must be verified before exposure fields
  become available.
- The executable audit checks missing sessions, quotes, invalid markets,
  excessive spreads, stale/future quotes, IV and Greek bounds, duplicate trade
  identities, independent-underlying mismatches, and expiration sanity.
- Audit verdicts are `PASS`, `PASS WITH WARNINGS`, and `BLOCK`. A block cannot be
  bypassed by silently dropping rows.

Provider authorities:

- [ThetaData trade and quote](https://docs.thetadata.us/operations/option_history_trade_quote.html)
- [ThetaData open interest](https://docs.thetadata.us/operations/option_history_open_interest.html)
- [ThetaData first-order Greeks](https://docs.thetadata.us/operations/option_history_greeks_first_order.html)
- [ThetaData EOD Greeks](https://docs.thetadata.us/operations_python/option_history_greeks_eod.html)

## 3. Evidence blocks

The public session schema is `options_flow_session_record_v2` and contains
separate blocks. No combined “smart money” score exists.

### Activity

- Log total contracts and log unique contracts.
- Call-contract share and volume/prior-OI.
- Largest-trade concentration.
- Auction, complex, and sweep shares.

These fields describe activity and execution form, not bullishness.

### Optionality structure

- `<5 DTE`, `5–30 DTE`, and `>30 DTE` shares.
- Volume-weighted median `log1p(DTE)`.
- Call moneyness `log(K/S)` and put moneyness `log(S/K)`.
- ATM share where absolute log moneyness is at most 0.02.
- Deep-OTM share where option-correct log moneyness exceeds 0.10.
- Moneyness coverage and source.

Long-DTE and residual-moneyness shares are reported but omitted from the
distance vector because their respective compositions sum to one.

### Aggressor-signed evidence

- Exchange-explicit aggressor conditions.
- Quote-location proxy.
- Unknown.

Explicit and proxy premium and volume coverage remain separate. Auctions,
crosses, sweeps, corrections, and complex trades do not acquire directional
meaning from quote position. Outputs say “aggressor-signed,” never customer
intent, institutional conviction, or dealer positioning.

### Gross economic intensity

- Gross traded option premium / underlying ADV20 dollars.
- Gross absolute delta-equivalent shares / underlying ADV20 shares.
- Gross gamma dollars for a 1% move / underlying ADV20 dollars.
- Gross vega dollars per verified volatility unit / underlying ADV20 dollars.

Complex trades are excluded. Greek fields require at least 90% coverage of
eligible single-leg volume. Gamma and vega remain unavailable unless their
provider units are explicitly verified.

## 4. Event and IV topology

An event record contains symbol, event ID/type, publication time, effective
time, source, capture time, and SEC accession/item where applicable.

At query date `D`, only events with `published_at <= D cutoff` are knowable.
States are:

- `NO_KNOWN_EVENT_WITHIN_T5`
- `KNOWN_EVENT_WITHIN_T5`
- `EVENT_CONTEXT_UNKNOWN`

A later 8-K cannot retroactively alter a historical decision record. This is
necessary because Form 8-K commonly follows the underlying event:
[SEC filing rule](https://www.sec.gov/rules-regulations/2004/03/additional-form-8-k-disclosure-requirements-acceleration-filing-date).
SEC data is supplemented by point-in-time earnings and corporate-action
calendars. VST and CEG retain the repository-required PJM auction catalyst.

IV snapshots:

- Choose valid near-0.50-delta calls for ATM IV and near--0.25-delta puts for
  downside IV.
- Interpolate total variance between expirations bracketing 30 and 60 days.
- Never extrapolate when a bracket is missing.
- At `D`, use only the latest completed session before `D`.
- Require 252 valid prior ATM30 observations.

Analog regime eligibility requires:

- Identical event state and event type.
- ATM30 IV-percentile difference no greater than 20 percentage points.
- Same term-slope sign.
- Absolute skew-z difference no greater than 1.0.
- Same realized-volatility tercile.

Unknown event or IV context forces abstention.

## 5. Analog topology

Primary analogs are same-ticker and strictly earlier than the query. Pooled
cross-ticker analogs are sensitivity evidence only.

For `p` preregistered distance features:

1. Use between 126 and 252 previous same-ticker observations, with a minimum of
   `max(126, 8p)`.
2. Learn median/MAD only from that prior window; use standard deviation only
   when MAD is zero.
3. Winsorize standardized coordinates at ±5.
4. Estimate sample covariance `Σ`.
5. Apply fixed shrinkage `Σ* = 0.5Σ + 0.5diag(Σ)`.
6. Invert with symmetric eigendecomposition and an eigenvalue floor of
   `1e-6 × median positive eigenvalue`.
7. Require effective rank of at least `0.75p`.
8. Learn the outcome-blind distance cutoff from the prior pairwise-distance
   distribution.
9. Keep at most 20 analogs, at least 10, separated by at least five sessions.

Robust RMS is computed as a sensitivity metric. Mahalanobis/RMS neighbor
Jaccard overlap below 0.50 produces `METRIC_INSTABILITY` and reduces the result
to descriptive-only. No metric is selected after observing returns.

## 6. Outcomes and opinion

T+5 is primary; T+1 and T+21 are secondary. Available outcomes include raw and
excess return, maximum favorable/adverse excursion, future realized
volatility, ATM30-IV change, skew change, event crossings, and regime base
rates.

Opinion labels:

- `POSITIVE_HISTORICAL_LEAN`
- `NEGATIVE_HISTORICAL_LEAN`
- `VOLATILITY_EXPANSION_LEAN`
- `VOLATILITY_COMPRESSION_LEAN`
- `MIXED_OR_INDETERMINATE`
- `ABSTAIN_INSUFFICIENT_OR_UNRELIABLE_DATA`

A directional lean requires:

- At least 10 nonoverlapping same-ticker analogs.
- Ready same-ticker and pooled sensitivity results with matching median sign.
- A deterministic 90% moving-block bootstrap interval excluding zero.
- Positive-return frequency at least 10 percentage points away from its
  matched-regime base rate.
- No event, IV, covariance, similarity, or metric-stability failure.

The output includes sample size, covariance diagnostics, both neighbor sets,
feature distances, coverage, counterexamples, worst outcomes, and an explicit
noncausal/non-recommendation disclaimer.

Audit note (2026-07-28): at 10–20 analogs a block-bootstrap interval has no
asymptotic justification; it is a rough indicator only and is deliberately
never sufficient alone for a lean.

## 7. Incremental-value study

The corrected walk-forward design includes the baseline validator, IV/event/
liquidity context in both models, and flow only in the expanded model. The
implementation fixes the former design-matrix defect that accidentally omitted
the named baseline regressor.

- Chronological fitting only.
- Purge and embargo around test folds.
- Optional final 42-session untouched holdout.
- Identical complete cases for baseline and expanded comparisons.
- Registered but NOT yet implemented in `study.py` (verification audit
  2026-07-28): ticker-aware negative controls, dependence-aware inference, and
  multiplicity correction across preregistered feature/outcome families. The
  current negative control is a non-ticker-aware seeded sign permutation.
  These remain mandatory before any empirical incremental-value conclusion.

The maximum favorable research conclusion is “survived this paper test.”
Current implementation contains no result claiming an edge.

Statistical governance follows the cautions in
[Harvey, Liu, and Zhu 2016](https://academic.oup.com/rfs/article-abstract/29/1/5/1843824)
and
[Arnott, Harvey, and Markowitz 2018](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3275654).

## 8. Implementation map

- `data/options_flow/`: bounded provider adapter, immutable raw storage,
  normalization, classification, aggregation, timestamp-safe underlying
  alignment, and executable data audit.
- `options_researcher/flow/`: feature construction, event/IV context,
  shrinkage-Mahalanobis analogs, calibrated opinion, versioned nested schema,
  display contract, labels, and incremental-value study.
- `tools/options_flow.py`: dry-run-default bounded capture.
- `tools/options_flow_audit.py`: offline audit printer with blocking exit code.
- `tools/options_flow_analogs.py`: offline same-ticker/pooled analog and opinion
  CLI; it never fetches data or imports ranking code.
- `tests/test_options_flow_*.py`: no-network formula, leakage, covariance,
  context, opinion, audit, schema, and walk-forward tests.

No module imports ranking, scoring, broker, or order-routing code.

## 9. Remaining external gates

Implementation does not authorize the historical pull. Before acquisition:

1. Verify account entitlement and exact endpoint response columns.
2. Confirm private retention and derived-data rights.
3. Run a three-session pilot and the executable audit.
4. Measure storage and stop if the preregistered cap would be exceeded.
5. Obtain explicit approval for the bounded paid pull.

Until then, live-data status is **HOLD**. The offline implementation and
synthetic tests do not constitute data validation, edge evidence, or permission
to fetch or trade.
