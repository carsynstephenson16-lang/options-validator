# Short-positioning data contract (v1)

Issuer-level reported short interest. Display-only. This contract binds the
normalized schemas in `data/short_positioning/models.py`, the FINRA adapter,
and the `EXP-SHORT` display lane.

**Scope:** FINRA Consolidated Short Interest only. S&P Global and any other
securities-finance provider remain LICENSE BLOCKED and unimplemented.

## 1. What this data is, in plain language

Short interest is the number of shares that investors have borrowed and sold,
counted on a specific settlement date and published later by FINRA. It is a
**snapshot of a reported position**, not a direction, a forecast, or a timing
signal.

Three things that sound similar and are deliberately kept apart:

| Concept | What it counts | Used here |
|---|---|---|
| Issuer-level short interest | Borrowed-and-sold shares in the stock, per settlement date | Yes, this contract |
| Options open interest | Live option contracts outstanding | No — separate subsystem |
| Daily short-sale volume | Shares sold short during a session | No — different dataset, never mapped here |
| Securities-lending measures | Shares on loan, utilization, borrow fee | No — LICENSE BLOCKED |

## 2. Official source

- Documentation: <https://developer.finra.org/docs> (retrieved 2026-08-11, America/New_York).
- Group `otcMarket`, dataset `consolidatedShortInterest`; test dataset
  `consolidatedShortInterestMock`.
- Publication schedule: <https://www.finra.org/filing-reporting/regulatory-filing-systems/short-interest>.
- Official-source quote on availability: "The Consolidated Short Interest data
  is available via the dataset by 4:40 PM ET on the publication date."

## 3. Field map

Field-map version `finra-consolidated-short-interest/v1`. Every source field
below was confirmed present in the official documentation on 2026-08-11.

| FINRA source field | Normalized destination | Rule |
|---|---|---|
| `issueName` | `issue_name` | Preserve the source string verbatim |
| `symbolCode` | `symbol` | Uppercase; never treated as permanent identity |
| `marketClassCode` | `market` | Preserve the source code |
| `settlementDate` | `settlement_date` | ISO date; the economic position date |
| `currentShortPositionQuantity` | `current_short_shares` | Non-negative integer |
| `previousShortPositionQuantity` | `previous_short_shares` | Nullable integer |
| `changePreviousNumber` | `change_shares` | Nullable signed integer |
| `averageDailyVolumeQuantity` | `average_daily_volume_shares` | Zero is ambiguous, not a real zero |
| `daysToCoverQuantity` | `days_to_cover` | Source-defined `Decimal`, preserved as supplied |
| `stockSplitFlag` | `stock_split_flag` | Null preserved; unknown non-null value fails closed |
| `revisionFlag` | `revision_flag` | Null preserved; unknown non-null value fails closed |
| `changePercent` | reconciliation input only | Compared against the derived percent |
| `issuerServicesGroupExchangeCode` | provenance only | Not a shared market field |
| `accountingYearMonthNumber` | raw-only cross-check | Must agree with the settlement cycle |

Unknown source fields and source-version drift fail closed with
`SCHEMA_ERROR` under strict normalization. No field is invented, and no field
is dropped silently.

### Flag semantics (Inference, not official)

FINRA's documentation shows `revisionFlag` and `stockSplitFlag` as nullable but
does not publish the value dictionary. The adapter therefore maps only the
explicit pair `{"Y": True, "N": False}`, preserves `null` as `None`, and
refuses any other non-null value with `SCHEMA_ERROR`. Null is never coerced to
`False`. Revisit if FINRA publishes the metadata semantics.

## 4. Units

| Field | Unit |
|---|---|
| All share counts | Whole shares, integer |
| `days_to_cover` | Source-defined liquidity ratio, `Decimal` |
| `change_pct` | Percentage points, `100 × (current - previous) / previous` |
| `change_1_cycle`, `change_3_cycles` | Decimal returns |
| `short_pct_float` | Percentage points |
| Percentiles | Decimal in `[0, 1]`; `None` in v1 |
| `data_age_sessions` | XNYS sessions |

No ratio is clamped. A value above 100 percent is preserved unchanged.
`change_pct` is `None` when previous shares are zero or missing.

## 5. Timing (the information clock)

```text
settlement_date   = economic position date
publication_date  = official dissemination date
available_at      = publication_date 16:40 America/New_York, stored as UTC
available_session = the next eligible XNYS session
retrieved_at      = local UTC capture time
```

Because 16:40 ET falls after the regular close, a report published on a
session first enters an end-of-day information set on the **following** XNYS
session. Sessions come from the exchange calendar
(`data/cache_runner.trading_days`), never from weekday arithmetic.

Conservative fallback: where a publication date exists but the time is not
verified, `available_at` is `23:59:59` America/New_York on the publication date
and `available_session` is the next XNYS session. No open, noon, or close
assumption is permitted.

Late release: use the actual source timestamp when supplied, otherwise the
retrieval time. A late release is never backdated to its scheduled time.

Revisions: every observed revision is stored as a new immutable capture keyed
by `source_revision`. A revision never overwrites the original, and a revised
row never replaces the original row in point-in-time research. FINRA's public
view exposes only the latest corrected data, so revision history from before
local capture began is unrecoverable.

## 6. Float denominators

`short_pct_float` is populated only when all of the following hold:

```text
float_available_at <= record.available_at
float_asof         <= record.publication_date
security identity is VERIFIED
float source and units are documented
```

Current float never backfills a historical record. When the denominator fails
any condition, the status is `FLOAT_UNAVAILABLE` and shares still display.

No float source is wired in v1, so `short_pct_float` is always `None` today.

## 7. Data rights and Git policy

- FINRA raw payloads, normalized partitions, and row-level derived data stay
  **local and gitignored**. Ignored roots: `.cache/short_positioning/`,
  `.local/short_positioning/`, `data/short_positioning/raw/`,
  `data/short_positioning/licensed/`, plus `*.spglobal.csv` and
  `*.securities-finance.csv`.
- Only invented synthetic fixtures are tracked. FINRA's own published sample
  rows are **not** copied into this repository.
- No S&P Global or Nasdaq material of any kind is present.
- Audit receipts and logs carry counts and statuses, never row-level provider
  values, and never a credential value.

## 8. Statuses

Precedence, highest first:

```text
SCHEMA_ERROR, HASH_MISMATCH, FUTURE_DATA, MISSING_PROVENANCE, PARTIAL_CAPTURE,
LICENSE_BLOCKED, AMBIGUOUS_SECURITY, CORPORATE_ACTION, NOT_YET_PUBLISHED,
NO_RECORD, PROVIDER_CONFLICT, STALE, REVISED, FLOAT_UNAVAILABLE, OK
```

A snapshot carries every applicable status plus one primary status derived
from this order. Missing data never inherits a prior value, never becomes
zero, and never renders as `OK`.
