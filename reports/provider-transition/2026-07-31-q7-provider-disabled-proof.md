# Q7 / P1.4 provider-disabled proof

Date: 2026-07-31 EDT
Status: COMPLETE

## Policy result

- ThetaData acquisition is hard-disabled in `data/provider_policy.py` with no
  environment-variable re-enable.
- `ProviderDisabledError` is raised before authentication, client construction,
  cache transactions, output-directory creation, receipts, or acquisition facts.
- Existing parquet cache hits still load and validate. Missing cache entries fail
  closed; the explicit cache-only reader remains network-free.
- Live preview requires an explicit `LIVE_MARKET_DATA_PROVIDER=schwab`. An unset
  provider is an error, and `thetadata` is refused rather than replaced by a
  silent fallback.
- The dead `config.DATA_PROVIDER` setting is removed.

## Constructor and acquisition map

| Boundary | Enforcement |
|---|---|
| `data.thetadata_adapter._client` | Central guard precedes key resolution, import, singleton reuse, and `ThetaClient(...)`. |
| `get_eod_chain` | Valid cached read first; an in-sample cache miss hits the central guard before publisher checks or fetch. OOS misses remain cache-only refusals. |
| `blind_cache_chain` | Central guard precedes the publisher transaction, cache directory/lock creation, fetch, attestation, and fact append. |
| `data.cache_runner` in-sample/OOS modes | Guard precedes window calculation/execution and manifest work; `--dry-run` remains offline. |
| `data.recent_topup.run_topup` | Every non-dry run is refused before cache inventory or acquisition work; dry-run inventory remains available. |
| `smoke_test.main` | Guard precedes cache read, output, and fact append. |
| Options-flow `--execute` and default client | CLI guard precedes output-store construction; adapter guard precedes shared-client lookup. Injected fake clients remain testable. |
| ThetaData underlying-close fetch | Guard precedes shared-client lookup. Explicit Yahoo/Alpha Vantage helpers are not automatic fallbacks. |
| Live probe and intraday capture | Explicit provider selection refuses ThetaData before the shared client or receipt path; explicitly configured Schwab remains the live lane. |

Static inventory found one direct `ThetaClient(...)` construction, inside the
guarded adapter factory. The three shared-factory import sites are underlying
closes, options flow, and live quotes; each has its own boundary guard and also
inherits the factory guard.

## Zero-call integration receipt

`uv run python -m unittest tests.test_provider_disabled`

- 14 tests passed.
- Raising sentinels proved zero key resolution/client construction.
- Mutation sentinels proved zero publisher transaction, cache fetch, output
  directory, receipt, or fact append on disabled paths.
- A temp-parquet cache hit still loaded successfully.

Neighbor regression set:

`uv run python -m unittest tests.test_core tests.test_blind_cache tests.test_cache_runner tests.test_recent_topup tests.test_smoke tests.test_live_quotes tests.test_intraday_capture tests.test_options_flow_adapter tests.test_underlying_closes tests.test_provider_disabled`

- 294 tests passed.

Repository checks:

- `uv run python -m unittest discover -s tests`: 2,251 passed in 260.818s.
- `uv run ruff check .`: passed.
- `uv run ruff format --check data/provider_policy.py tests/test_provider_disabled.py`:
  passed; both new Python files are formatter-clean.
- `uv run pyright`: 0 errors, 0 warnings.
- `git diff --check`: passed.
- Research ledger: `ledger OK`.
- H7 event ledger: `VALID records=1 head=a1ea228c2abb`.

The optional formatter still reports the documented pre-existing baseline in
the older touched files; Q7 did not mass-format those unrelated legacy lines.

## Forbidden-surface review

Q7 changed no strategy threshold, registered verdict, live/paper book, v1 cache
byte, one-run record, acquisition fact, or ledger entry. No external provider
call was made. Existing unrelated worktree changes were preserved.
