# Future-ticker ThetaData capture — parked 2026-08-01

Status: **COMPLETE / PARKED / DISPLAY-ONLY**. This capture is not eligible for
H7, H8, H5, H6, backtests, rankings, receipts, or any verdict path.

## Requested scope

- Symbols: `MU`, `HYLN`, `NBIS`, `INTC`, `ET`, `CLSK`
- `LULU` was explicitly excluded.
- Data: ThetaData daily EOD option chain, Greeks, NBBO, and open interest.
- Window requested: XNYS sessions from `2025-07-25` through `2026-07-31`
  (`256` sessions per symbol).
- Planned provider calls: `3,072` (`6 symbols x 256 sessions x 2 bulk
  endpoints`).

## Parked artifact

The raw partitions are in the ignored, separate namespace:

`.cache/future_tickers/eod_2025-07-25_to_2026-07-31/raw/<SYMBOL>/<SESSION>/`

This is deliberately separate from `.cache/chains`. No files were written to
the canonical chain cache, and the provider guard file was not edited.

## Captured coverage

| Symbol | Partitions | Coverage | Missing |
| --- | ---: | --- | ---: |
| `MU` | 256 / 256 | 2025-07-25 through 2026-07-31 | 0 |
| `HYLN` | 256 / 256 | 2025-07-25 through 2026-07-31 | 0 |
| `NBIS` | 256 / 256 | 2025-07-25 through 2026-07-31 | 0 |
| `INTC` | 256 / 256 | 2025-07-25 through 2026-07-31 | 0 |
| `ET` | 256 / 256 | 2025-07-25 through 2026-07-31 | 0 |
| `CLSK` | 256 / 256 | 2025-07-25 through 2026-07-31 | 0 |

Captured total: `1,536` immutable parquet partitions, `2,499,624` chain rows,
about `101 MB` on disk. Every captured partition has a receipt whose parquet
hash, row count, symbol/session key, and option-right schema passed the
capture-time integrity check (`bad_count=0`). This is not the independent full
data-quality audit required for promotion.

## Independent full audit — 2026-08-02

The read-only full scan completed over all `1,536` partitions and all
`2,499,624` rows. Every partition matched its saved receipt hash and row count.
The result is **BLOCK / NOT ELIGIBLE FOR PROMOTION** (`15` blockers, `3,493`
warnings; receipt `5c5a564492b7…ab65`). The permanent machine-readable report
is `reports/future_tickers/2026-08-02-full-data-audit.json`.

The blocking facts are:

- all `1,536` partitions use the legacy 11-column schema and retain no provider
  timestamps;
- the capture ran from a dirty source worktree and did not retain the two raw
  provider response tables, so its normalized join cannot be independently
  replayed;
- one CLSK session (`2025-11-24`) contains two crossed markets;
- MU, HYLN, and INTC have no independent close file; NBIS and CLSK independent
  close files stop at `2026-07-27`, leaving four sessions unverifiable.

ET had independent closes for the full requested window. None of these findings
changes the parked/display-only decision, and no market-data byte was rewritten
or deleted by the audit.

## Why the pull stopped

The first attempt encountered:

`UNAUTHENTICATED: Invalid session ID. This can occur if more than one terminal is running.`

The overlapping worker was allowed to drain, then the capture resumed with one
authenticated client. The final capture summary reports `1,536/1,536` tasks,
`3,072` planned provider calls, and `0` errors. Do not treat parked data as a
strategy result until it is explicitly promoted and independently reviewed.
