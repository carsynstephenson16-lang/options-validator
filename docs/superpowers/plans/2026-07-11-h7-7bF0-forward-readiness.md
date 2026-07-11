# 7b-F0 — H7 forward-paper readiness plan (PROPOSED, NOT AUTHORIZED)

**Status: PROPOSAL ONLY (7b-2R.1 hard-stop deliverable). Nothing in this
file is implemented or activated. The next independent review authorizes
7b-F0.**

Owner decision 2026-07-11 (ledger H7_7B2R1_DECISIONS): the 2018–2026
historical diagnostic is withdrawn as verdict-capable evidence; the
**point-in-time forward paper window is the sole verdict-bearing path**
for H7. This plan enumerates what must be true before that window can
start ticking, so the review can ratify a concrete checklist.

## F0-1  Append-only current-earnings refresher (manual cadence, no crawler)

- A small CLI (`tools/refresh_earnings_gating.py`) that APPENDS to the v3
  gating store only: next-report schedule assertions and realized-report
  occurrences for the H7 watch/backtest names, each with event identity,
  fiscal period, event_class, exact https:// source URL, known_as_of_utc
  (publication or SEC acceptance time, else disclosed retrieval time),
  checked_at_utc, and supersession targets. It never rewrites rows.
- Sourcing precedence (F0-2): SEC 8-K acceptance timestamps for occurred
  reports; company IR/PR pages for scheduled dates; aggregator estimates
  ONLY as `estimated` with the aggregator URL and a disclosed-limitation
  note (they gate conservatively via ban windows, never via grace).
- Owner-in-the-loop: the tool prints a proposed batch; the owner approves
  before append (pre-registration hygiene — numbers/dates are owner-typed
  or owner-approved). Recurring crawl automation stays DEFERRED.

## F0-2  Per-symbol source-health report

- `uv run python -m options_researcher.h7_watch --source-health` (or a
  sibling CLI): for every watch name print the newest gating assertion,
  its class/status/source type, days until expected report, and STALE /
  MISSING flags (e.g. no live future schedule and grace expiring within N
  sessions). Exit non-zero when any name is source-unhealthy, so the
  daily routine surfaces rot before the gate silently turns UNKNOWN.

## F0-3  Watcher smoke tests (evidence, not vibes)

- A dated smoke run of `options_researcher.h7_watch` on a fresh top-up:
  every name resolves DATA-GAP-free, gates print CLEAR/BANNED/UNKNOWN
  with reasons, board resolver output shown, at least one historical
  `--as-of` replay demonstrating the session-close cutoff (no wall-clock
  knowledge). Output pasted into the ledger as a fact.

## F0-4  Forward ledger accounting

- Pre-register the forward window in the ledger BEFORE the first paper
  entry: start date, duration, the exact decision procedure (watcher +
  board resolver output is the only entry authority), position book
  conventions (data/positions/h7_positions.csv, append-only, owner-edited),
  benchmark logging (underlying move alongside every trade), and the
  verdict gate (expectancy after costs, MIN_LOSSES_FOR_VERDICT losses —
  vocabulary: survived/rejected/inconclusive only).
- Every fill, skip, DISPLACED lane, and earnings-gate refusal gets a
  dated fact; month-sleeve accounting mirrors `open_h7_book` semantics.
- ThetaData renewal question (2026-07-25 gate) feeds this: the forward
  window needs daily EOD chains for the watch names, so the renewal
  decision should precede the window's start date.

## Explicitly out of scope for 7b-F0

- Any historical backtest or P&L (withdrawn as verdict-capable).
- A post-earnings-only historical study — if ever wanted, it is a NEW
  conditional hypothesis with its own registration and can never reject
  or validate H7.
- Crawlee/scrapy recurring automation (deferred by owner decision).
