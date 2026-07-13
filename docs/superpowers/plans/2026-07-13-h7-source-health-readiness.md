# H7 source-health readiness for the July 29 data cutoff

**Prepared 2026-07-13. BUILD-ONLY; INACTIVE; OWNER REVIEW REQUIRED.**

This is a source-preparation worksheet. It does not append raw evidence,
promote a gating assertion, open Stage 8, authorize a paid data pull, or create
a real forward event.

## What the two health numbers mean

- The latest chain-aligned run is evaluation session 2026-07-10 with the
  information cutoff at that session's close: **4/12 healthy**. Assertions
  learned after 20:00 UTC correctly remain invisible to that historical view.
- Replaying only the current assertion store at the 2026-07-13 close produces
  **11/12 healthy**. PLTR, SMCI, NVDA, AVGO, VST, CEG, and AMZN become healthy;
  CRWV remains `UNKNOWN`.
- This 11/12 replay is readiness information, not a Stage-2 result. The next
  accepted evidence must rerun source health and the exact-session data gate
  together after the corresponding EOD chains exist.

## CRWV — do not promote a guessed date

Web check on 2026-07-13:

- [CoreWeave quarterly results](https://investors.coreweave.com/financials/quarterly-results/default.aspx)
  shows Q1 2026 results but no Q2 2026 result-date announcement.
- [CoreWeave events and presentations](https://investors.coreweave.com/events-and-presentations/default.aspx)
  shows the Q1 call but no Q2 2026 call.
- [Nasdaq CRWV earnings](https://www.nasdaq.com/market-activity/stocks/crwv/earnings)
  says earnings-date data is not available.
- A lower-tier aggregator estimates 2026-08-11. That is diagnostic only and
  is not prepared for promotion while the company and Nasdaq do not publish a
  date.

Recommended owner action: wait for CoreWeave IR/PR or an SEC filing. When an
official schedule appears, first run an append dry-run with the exact URL and
publication timestamp:

```bash
uv run python tools/h7_refresh_earnings.py append-raw \
  --symbol CRWV \
  --event-id CRWV-2026Q2 \
  --fiscal-period 2026Q2 \
  --status confirmed \
  --expected-date YYYY-MM-DD \
  --timing amc \
  --source-type company_pr \
  --source-url 'https://EXACT-OFFICIAL-URL' \
  --known-as-of 'YYYY-MM-DDTHH:MM:SS+00:00' \
  --notes 'official Q2 2026 schedule; exact publication time retained' \
  --dry-run
```

After the owner reviews that output, a separately authorized append produces
an `A` id. Promotion must also be dry-run first:

```bash
uv run python tools/h7_refresh_earnings.py promote \
  --raw-id A#### \
  --event-class actual_quarterly_earnings \
  --dry-run
```

Do not replace the placeholders or remove `--dry-run` without exact source
evidence and explicit owner authorization.

## NOW — occurrence refresh after July 22

NOW's confirmed 2026-07-22 schedule is healthy before the report. Once the
date passes, the scheduled assertion alone becomes stale; source health must
not infer that results occurred. After the release:

1. Prefer the SEC 8-K acceptance timestamp and exact filing URL.
2. Append one raw `status=occurred` record for the same fiscal identity.
3. Promote it as `actual_quarterly_earnings`, superseding the scheduled gating
   row only when the correction identity is exact.
4. Run source health again. Never start post-report grace from a press rumor,
   preliminary update, or unclassified Item 2.02.

## July 29 sequence

1. Refresh CRWV/NOW source evidence under owner review before any market-data
   decision.
2. Run the cancellation checklist's 12-name top-up only with explicit paid
   pull authorization.
3. Build the immutable ThetaData exit receipt and verify it from disk.
4. Build H6's terminal-session features, create its exact-session watch
   receipt, and verify the receipt from disk. This proves offline
   reconstructability only; it cannot create or backfill an H6 paper row.
5. Run source health and the Stage-2 data gate on the same latest completed
   session; both must be 12/12.
6. Keep Stage 8 closed. Subscription preservation and source remediation do
   not fill the blank owner activation inputs.
