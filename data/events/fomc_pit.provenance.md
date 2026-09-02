# A2 PIT FOMC calendar provenance

This file documents `data/events/fomc_pit.csv`, the provenance-bearing FOMC
input for the A2 outcome battery. It is separate from the legacy
`fomc_dates.csv`, which has a dates-only schema and is not a valid A2 input.

## Source and capture

- **Official source:** Federal Reserve press release, “Federal Open Market
  Committee announces its tentative meeting schedule for 2025 and 2026,”
  released 2024-08-09 at 1:30 p.m. EDT:
  <https://www.federalreserve.gov/newsevents/pressreleases/monetary20240809a.htm>
- **`known_as_of_utc`:** `2024-08-09T17:30:00+00:00` for every row. The
  source release time of 1:30 p.m. EDT converts to 17:30 UTC on that date.
- **`captured_at_utc`:** `2026-08-15` (retrieval date only; no capture
  seconds are asserted).

## Transformation and scope

- The source lists each meeting as a two-day window. The CSV records the
  second day as the FOMC decision date, which is the date consumed by the A2
  runner.
- Scope is all eight scheduled meetings in each of 2025 and 2026, for 16
  decision-date rows total.
- `status` is `tentative`, reflecting the status in the 2024 announcement;
  these dates were tentative until subsequently confirmed.

## Limitation

This artifact preserves what was known from the official tentative schedule
announcement and does not replace a later confirmation record. The A2 runner
uses the rows only as point-in-time scheduled-event inputs; it does not infer
that the tentative dates were immutable.
