# Short-positioning claim ledger

**Date:** 2026-08-11. Every claim that the short-positioning subsystem relies
on, with its evidence label per `.cursorrules` claim discipline:
Official-source, Repo-verified, Test-verified, Inference, Assumption.

Retrieval of all Official-source items below: 2026-08-11, America/New_York,
from <https://developer.finra.org/docs>. No FINRA API request was made; only
the public documentation page was read.

## 1. Provider and dataset

| # | Claim | Label | Evidence |
|---:|---|---|---|
| 1 | FINRA publishes a Consolidated Short Interest dataset covering OTC short-interest position submissions across all exchanges | Official-source | developer.finra.org/docs, "Consolidated Short Interest" section |
| 2 | The dataset is addressed as group `otcMarket`, dataset `consolidatedShortInterest` | Official-source | Same page, "Dataset Info" |
| 3 | A mock dataset `consolidatedShortInterestMock` exists for testing | Official-source | Same page, "test dataset" |
| 4 | "The Consolidated Short Interest data is available via the dataset by 4:40 PM ET on the publication date" | Official-source | Same page, "Dataset Details", quoted verbatim |
| 5 | The publication schedule is published separately at finra.org/filing-reporting/regulatory-filing-systems/short-interest | Official-source | Same page, linked |
| 6 | The 14 source field names in the contract's field map all appear in FINRA's documented response | Official-source | Same page, sample response; each name checked individually 2026-08-11 |

## 2. Semantics that are NOT officially documented

| # | Claim | Label | Handling |
|---:|---|---|---|
| 7 | `revisionFlag` and `stockSplitFlag` use `"Y"`/`"N"` values | Inference | Only that explicit pair is mapped; `null` stays `None`; any other non-null value fails closed with `SCHEMA_ERROR` |
| 8 | A zero `averageDailyVolumeQuantity` may be a translated null rather than a real zero | Inference | Treated as ambiguous; never used as a divisor |
| 9 | `changePercent` is computed by FINRA as `100 × (current − previous) / previous` | Inference | Used only as a reconciliation input against the derived value, never stored as truth |
| 10 | FINRA's public view exposes only the latest corrected data, so pre-capture revision history is unrecoverable | Inference | Recorded as a permanent limitation; local captures are immutable so forward history is preserved |
| 11 | `issuerServicesGroupExchangeCode` is not equivalent to `marketClassCode` | Assumption | Kept in provenance only; never mapped to the shared `market` field |

## 3. Repository facts

| # | Claim | Label | Evidence |
|---:|---|---|---|
| 12 | An XNYS exchange calendar helper already exists and is offline-safe | Repo-verified | `data/cache_runner.trading_days` / `session_close_utc`; imported and exercised 2026-08-11 |
| 13 | A durable atomic text-write helper already exists | Repo-verified | `data/atomic_io.atomic_text_write` |
| 14 | The experiments dashboard is display-only and separate from production ranking | Repo-verified | `options_researcher/experiments_dashboard.py` module docstring and lane structure |
| 15 | Tests are `unittest`, run offline, and the exit code is the verdict | Repo-verified | `CLAUDE.md` Commands section; full suite run on the pinned commit |
| 16 | Pyright's `include` list does not cover `data/short_positioning`, `tools/`, or `tests/` | Repo-verified | `pyrightconfig.json` include/exclude lists |

## 4. Claims established by this branch's tests

| # | Claim | Label | Evidence |
|---:|---|---|---|
| 17 | Missing source values stay `None` and never become zero | Test-verified | `tests/test_short_positioning_models.py` |
| 18 | Ratios above 100 percent survive unclamped | Test-verified | `tests/test_short_positioning_models.py` |
| 19 | Naive or non-UTC timestamps are refused | Test-verified | `tests/test_short_positioning_models.py` |
| 20 | `source_record_key` is deterministic and separates original from revised captures | Test-verified | `tests/test_short_positioning_models.py` |
| 21 | Unknown schema versions, access methods, and statuses fail closed | Test-verified | `tests/test_short_positioning_models.py` |
| 22 | A record may not be available after it was retrieved | Test-verified | `tests/test_short_positioning_models.py` |
| 23 | Publication timing places a report in the next XNYS session | Test-verified | `tests/test_short_positioning_timing.py` |
| 24 | Future-dated records are refused with `FUTURE_DATA` | Test-verified | `tests/test_short_positioning_timing.py` |
| 25 | Every documented CLI exit code is reachable | Test-verified | `tests/test_short_positioning_capture_cli.py` |
| 26 | Interrupted partition writes leave no normalized output | Test-verified | `tests/test_short_positioning_store.py` |
| 27 | A modified raw artifact is detected as `HASH_MISMATCH` | Test-verified | `tests/test_short_positioning_store.py` |
| 28 | Rendering performs no network access | Test-verified | `tests/test_short_positioning_boundaries.py` |
| 29 | Ranking, strategy, book, verdict, and live modules import no short-positioning module | Test-verified | `tests/test_short_positioning_boundaries.py` |
| 30 | Provider-controlled strings are HTML-escaped in the lane | Test-verified | `tests/test_exp_short_positioning.py` |

## 5. Explicit non-claims

- No claim is made that short interest predicts returns, direction, or timing.
- No claim is made about squeeze risk. The subsystem emits no such concept.
- `days_to_cover` is a source-defined liquidity ratio and is **not** a
  countdown or a timing forecast.
- No securities-lending, utilization, or borrow-fee claim is made; those
  providers are LICENSE BLOCKED and unimplemented.
- No S&P Global or Nasdaq data, schema, export, or score is used anywhere.
- No FINRA API request has been made from this repository. All adapter tests
  run against invented fixtures and mocked transports.
