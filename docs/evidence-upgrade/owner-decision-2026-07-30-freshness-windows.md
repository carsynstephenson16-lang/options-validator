# Owner decision — the three freshness windows (packet 5, B1)

**Status:** awaiting owner-typed numbers. Proposals below are LLM-asserted and
must be treated as such until you enter them.
**Prepared:** 2026-07-30. Blocks equity-research PR #17.

---

## Read this first: the windows alone will not unblock everything

Setting these three numbers fixes six of the seven starved routes. It does
**not** fix `earnings.date`. That one is blocked by a second, separate defect
(B3, written up at the bottom), proven by execution today. If you type a
window expecting earnings dates to start flowing again, they won't, and it
will look like the fix failed.

Six routes this decision does unblock: `fred`, `bls`, `bea`, `eia`,
`treasury_fiscal_data`, `twelve_data`, plus `gdelt` on the discovery path.

---

## What the number actually does

Plain version: it is the shelf life of a fact. After a fact has been public
for longer than its window, the system stops treating it as current evidence
and quarantines it instead.

Two measured details that decide what a sensible number looks like — both
**Repo-verified** today:

1. **The clock starts when the fact became public, not when we fetched it.**
   `storage.py:410-412` anchors on `event.public_by_ts_utc or
   event.published_at`. So a window of 1 hour does not mean "re-fetch hourly";
   it means "a fact more than an hour old is unusable."
2. **It is checked once, at admission.** `admission.py:297-308` quarantines
   when `stale_after <= now`. Once quarantined, a row stays out — the
   options-validator board excludes non-`ADMITTED` rows.

Which way it hurts to be wrong:

- **Too short** → the starvation we just spent a review round finding. Rows
  arrive, get quarantined, and the board quietly goes empty.
- **Too long** → a stale number is treated as current. This is the failure the
  whole architecture was commissioned to prevent.

---

## Proposal table

Type your choice in the right-hand column. Nothing is frozen until you do.

| Class | Covers (Repo-verified) | Candidates | My recommendation | **Your number** |
|---|---|---|---|---|
| `fast` | `market.quote` → `twelve_data` (declared `continuous`) | 1h / 12h / 36h | **12 hours** | |
| `slow` | `macro.series` → `fred`, `bls`, `bea`, `eia`, `treasury_fiscal_data`, `federal_reserve`; also `earnings.date` | 35d / 100d / 200d | **100 days** | |
| `event_driven` | `news.discovery` → `gdelt`, purpose `discovery` only | 7d / 30d | **7 days** | |

### Why 12 hours for `fast`

A quote is a price at a moment, so "stale equals wrong" bites hardest here.
12 hours lets a morning data pull feed the same day's board, while making
yesterday's close unusable as today's price. Over a weekend, Friday's quotes
go stale by Saturday — which is the correct answer, not a bug.

Pick 1 hour instead if you ever intend a quote to inform an intraday decision.
Pick 36 hours only if you would rather show a day-old price than show nothing;
I would not.

### Why 100 days for `slow`

This class spans sources with wildly different rhythms — Treasury publishes on
business days, BLS monthly, BEA quarterly. One number has to serve all of them,
and the binding constraint is the slowest legitimate one: if the window is
shorter than the gap between two releases of a quarterly series, that series is
starved for part of every quarter. A quarterly cadence implies roughly 13 weeks
between releases (**Assumption** — I did not fetch the official BEA/BLS release
calendars this session; worth 5 minutes to verify before you freeze it, since
the recommendation hinges on it). 100 days clears that with slack.

The honest cost: a Treasury daily series could sit 3 months past publication
and still be admitted. I think that is acceptable, because for a *series* the
real defence against staleness is supersession — a newer observation exists and
supersedes the old one — not a time window. The window's job here is narrower:
catching the case where nobody refreshed the source at all.

### Why 7 days for `event_driven`

`gdelt` is `discovery` purpose only, so nothing here ever carries decision
authority, and the registry's own note says the opened source is the evidence,
not the index record. A discovery pointer older than a week has no research
value, so quarantining it costs nothing.

---

## Two things I would change beyond the numbers

Neither is required to unblock PR #17. Both are cheaper to fix now than later.

1. **`slow` is doing too much work.** One window covering business-day Treasury
   data and quarterly BEA data guarantees it is wrong for one of them. Splitting
   into `slow_monthly` / `slow_quarterly`, or moving the window onto the source
   registry entry where `update_pattern` already lives, would make each number
   defensible on its own. **Inference.**
2. **`earnings.date` has the wrong kind of expiry.** Its natural death is the
   earnings date itself, not a fixed offset from when it was announced. A date
   announced six weeks out is still perfectly true five weeks later. A
   window is the wrong instrument; an event-anchored expiry is the right one.
   **Inference.**

---

## B3 — `earnings.date` cannot be admitted at all, window or no window

**Blocking, and separate from B1.** Measured today by execution:

- `earnings.date` requires **2** independence groups
  (`admission.py:106`, `minimum_independence_groups=2`).
- Two distinct groups do exist and could satisfy it — `sec_edgar` is group
  `sec-edgar`, `company_ir` is group `issuer` (`data/source_registry.json`).
- But `storage.py:348` defaults `corroboration_groups` to `()`, and
  **`service.py` never passes it**. Every ingested row therefore carries exactly
  one group: its own source's.

Proof, with a 100-day window already applied so only corroboration can block:

```
live ingestion path (1 group: own source only)   -> QUARANTINED / corroboration-insufficient
hypothetical corroborated (2 groups)             -> ADMITTED / gates-passed
```

So `earnings.date` is un-admittable through the live path no matter what you
type here. Structurally this is the same defect as B1 — a registered policy no
production path can satisfy — and it is the one that matters most on this side,
because earnings dates are the H7 discipline's core input.

Fixing it means ingestion must actually corroborate: match the same earnings
date across the SEC filing and the issuer's own IR publication and pass both
groups. That is real work, not a config change, and it belongs in the packet 5
fix round rather than being discovered later by an empty board.

---

## Where this goes once you have typed the numbers

`market_updates/admission.py:99-102` — the `freshness_window` argument on
`_FAST`, `_SLOW`, `_EVENT_DRIVEN`. Codex's uncommitted work already added the
fail-loud refusal and the table-driven test over the registered policies, so
the windows are the only edit left for B1 itself. B3 needs its own brief.
