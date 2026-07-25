# data/rates/treasury_cmt.csv — provenance log

This CSV has no separate machine-readable provenance store; every row carries
its own provenance (`source_url`, `known_as_of_utc`, `valid_through`,
`captured_at_utc`) per the schema enforced by `data/rates.py`. This file is a
human-readable capture log, appended each time rows are added — never edit or
delete an existing entry here, and never edit or delete a row already written
to the CSV.

## Capture 1 — 2026-07-23 (initial data unlock)

- Source: treasury.gov daily par yield curve rates.
- Rows added: `2026-07-09` through `2026-07-22` (10 business days x 8 tenors
  = 80 rows).
- Recorded by commit `b06416e` ("docs(scanner)+data: 12-month research
  program, audit resolution, three data unlocks").
- `known_as_of_utc` / `captured_at_utc`: `2026-07-23T05:54:37+00:00` for
  every row in this batch.

## Capture 2 — 2026-07-24 (backfill, this session)

- **Why:** the IV-solver calibration tool (`options_researcher/
  iv_solver_calibration.py`) ran for real on 2026-07-24 and 59/60 sessions
  per name were skipped ("no rate curve coverage", n_pairs=1 for all 15
  names). Root cause: Capture 1 only covered two calendar weeks
  (2026-07-09..22); `data/rates.py`'s point-in-time gate correctly refuses
  any row whose `known_as_of_utc` postdates the observation date's 16:00
  America/New_York valuation close, so almost every historical session in
  the calibration window had no eligible curve row.
- **Source:** treasury.gov daily par yield curve rates, official public CSV
  download endpoint (same endpoint already recorded in every row's
  `source_url` column):
  `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all?type=daily_treasury_yield_curve`
  Fetched with an honest identifying User-Agent
  (`options-validator-research/1.0 (contact: carsynstephenson16@gmail.com)`),
  HTTP 200.
- **Rows added:** all business days `2026-01-02` through `2026-07-23`
  (inclusive) that were NOT already present from Capture 1 — 130 dates x 8
  tenors = 1,040 rows. Combined with Capture 1, the file now covers
  `2026-01-02` through `2026-07-23` (140 distinct business days, 1,120 data
  rows total), the full year-to-date span, with no gaps.
- **Tenor mapping** (unchanged from Capture 1's convention, verified against
  the raw treasury.gov columns and the already-committed 2026-07-22 row —
  exact match): `1 Mo -> 30d`, `1.5 Month -> 45d`, `2 Mo -> 61d`,
  `3 Mo -> 91d`, `4 Mo -> 121d`, `6 Mo -> 182d`, `1 Yr -> 365d`,
  `2 Yr -> 730d`. The raw feed's longer tenors (`3 Yr`/`5 Yr`/`7 Yr`/`10 Yr`/
  `20 Yr`/`30 Yr`) are dropped — not part of the existing grid, and not
  needed for the short-DTE options this repo studies.
- **`valid_through`:** `observation_date + 4 calendar days`, matching
  Capture 1's rule exactly (verified across all 10 Capture-1 dates,
  including weekend-adjacent ones).
- **`known_as_of_utc` / `captured_at_utc`:** `2026-07-24T15:03:36+00:00`
  (the actual wall-clock time this backfill ran) for every row in this
  batch — **honest capture timestamp, not a fabricated historical one.**
  This is intentional and load-bearing: it means `data/rates.py`'s
  point-in-time gate still correctly refuses these rows for any historical
  `observation_date` (the gate is checking "did we know this by the
  session's valuation close," and for a backfill run today the honest
  answer is no for any date before today). That gate must not change; see
  `options_researcher/iv_solver_calibration.py`'s `--allow-retrospective-inputs`
  flag for the calibration-tool-only, explicitly-labeled workaround.
- **Existing rows:** untouched. This capture only appends; `git diff` on
  this commit is pure additions against the Capture-1 rows.
