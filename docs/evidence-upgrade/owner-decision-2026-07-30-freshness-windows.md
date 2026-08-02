# WITHDRAWN — freshness-window proposal (packet 5, B1)

**Status: withdrawn 2026-07-30, same day it was written. Do not type numbers
against it.** Superseded by the packet 5A/5B/5C sequence recorded in D37.

The original proposal is preserved below the correction, unedited, because the
mistake is more instructive than the table was.

---

## What was wrong

The headline claim — *"the numbers unblock six of seven routes"* — is **false**.
Reproduced by execution, with my own recommended windows applied and the
availability fields as the non-SEC providers actually leave them:

```
fred                   -> QUARANTINED / temporal-missing-availability
bls                    -> QUARANTINED / temporal-missing-availability
bea                    -> QUARANTINED / temporal-missing-availability
eia                    -> QUARANTINED / temporal-missing-availability
treasury_fiscal_data   -> QUARANTINED / temporal-missing-availability
twelve_data            -> QUARANTINED / temporal-missing-availability
gdelt                  -> blocked before staleness
```

The windows unblock **zero** routes, not six. Root cause: `public_by_ts_utc`
and `availability_rule_version` are populated in exactly one place —
`providers.py:206-207`, inside the SEC submissions parser. Every other provider
constructs `RawSourceItem` without them, so they default to `None`
(`models.py:105-106`), and `admit()` quarantines at
`temporal-missing-availability` (`admission.py:225-238`) — a gate that fires
*before* the staleness gate the windows control. **Repo-verified.**

Call this **B4: there is no temporal provenance outside SEC.** B1 was masking
it: with `stale_after` returning `None` for every non-immutable class, nothing
ever got far enough down the gate order to reveal that availability was missing
too.

Three more corrections to things I asserted:

1. **B3 was framed one layer too shallow.** I wrote that `earnings.date` is
   blocked by the corroboration gate. True, but downstream of the real problem:
   **there is no `earnings.date` route at all.** The seven claim types actually
   produced are `sec.filing_event`, `sec.numeric_fact`, `company.publication`,
   `central_bank.publication`, `macro.series`, `market.quote`,
   `news.discovery`. SEC filings become `sec.filing_event`; IR records become
   `company.publication`. Nothing extracts or stores a typed earnings date.
   I had this table on screen when I wrote B3 and still framed it around
   corroboration. **Repo-verified.**
2. **"The windows are the only edit left for B1" was wrong.**
   `tests/test_admission.py:240-248` asserts that every non-immutable policy
   *raises*. Populating the windows makes that test fail by design; it has to
   change in the same edit. **Repo-verified.**
3. **The packet 8 blast-radius claim overstated reality.** I wrote in PR #16
   and in D36 that the options-validator board excludes quarantined rows.
   `market_context.py` has **no live consumer** — the only thing that
   references it is `tests/test_market_context.py`. That describes implemented
   filtering, not an active end-to-end board path. **Repo-verified.**

Also accepted without independent re-derivation, from the review: FRED's clock
is the observation date, not real-time availability, so a quarterly GDP
observation dated April 1 but first available July 30 is stale on arrival under
a 100-day window anchored on `published_at`; Twelve Data effectively uses fetch
time; `corroboration_groups` is an unvalidated list of strings, so passing
`"issuer"` satisfies the count without proving matching evidence exists; and an
8-K under Item 2.02 frequently republishes the issuer's own press release, so
SEC and IR are not automatically independent channels.

Two scope facts that also stand, **Repo-verified**: the market-updates
watchlist is 4 names (MSFT, AMZN, VST, CEG) against H7's frozen 15
(`h7-forward-15-v1`), and `twelve_data` is `enabled = false` in
`market_updates.toml`.

## What survives

- The *semantics* section below is correct: the clock starts at publication and
  is checked once at admission. That is what makes a publication-anchored
  window the wrong instrument for a series with vintages.
- `event_driven = 7 days` is provisionally accepted — after temporal provenance
  exists.
- The structural criticism I raised (that `slow` is overloaded, and that
  `earnings.date` should expire on its event rather than a fixed offset) was
  directionally right, and the review's design goes further in the same
  direction: expire macro series at the next expected release, and model an
  earnings date as a typed state machine with supersession.

`fast = 12h` and `slow = 100d` are **rejected as final policy** and should not
be entered.

## What replaces this

- **Packet 5A — temporal provenance.** A versioned availability rule for every
  registered route, plus an end-to-end matrix over all production routes.
  Nothing else can be evaluated until this exists.
- **Packet 5B — typed earnings claims.** Real date extraction, fiscal-period
  identity, status, supersession and conflict handling, evidence-backed
  corroboration.
- **Packet 5C — source-specific expiry.** Release-calendar-aware policies
  replacing the shared `slow` window.
- **Packet 8 integration.** Prove parity against H7's existing `gating_v3`
  earnings store across all 15 names before any board authority moves.

## Lesson worth keeping

I checked the gate that was broken and not the gates *upstream* of it. The
review's method — run every production route end-to-end and read the first
failure, rather than the one you are looking for — is the one that finds this
class of defect. That now joins "mutation-test the guard" and "drive the
registered config table" as a standing check.

---
---

# (Original proposal, withdrawn — preserved for the record)

## What the number actually does

Plain version: it is the shelf life of a fact. After a fact has been public
for longer than its window, the system stops treating it as current evidence
and quarantines it instead.

Two measured details that decide what a sensible number looks like:

1. **The clock starts when the fact became public, not when we fetched it.**
   `storage.py:410-412` anchors on `event.public_by_ts_utc or
   event.published_at`.
2. **It is checked once, at admission.** `admission.py:297-308` quarantines
   when `stale_after <= now`.

Which way it hurts to be wrong: too short starves the board; too long lets a
stale number be treated as current.

## Proposal table (withdrawn)

| Class | Covers | Candidates | Recommendation (withdrawn) |
|---|---|---|---|
| `fast` | `market.quote` → `twelve_data` | 1h / 12h / 36h | ~~12 hours~~ rejected |
| `slow` | `macro.series` ×6 sources; also `earnings.date` | 35d / 100d / 200d | ~~100 days~~ rejected |
| `event_driven` | `news.discovery` → `gdelt` | 7d / 30d | 7 days — provisionally accepted |
