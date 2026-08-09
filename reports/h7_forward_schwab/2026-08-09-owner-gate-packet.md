# DRAFT — H7 Schwab owner gate packet

**Status:** PREPARED / NOT REGISTERED / NOT ACTIVATED. This document is not
operative owner wording and grants no authority. Live trading remains disabled.

## Readiness snapshot

| Contract item | Evidence | State |
|---|---|---|
| Provider and cache identity | Schwab read-only; `.cache/schwab_chains/`; `preclose_snapshot_v1` | machinery ready; live canary absent |
| Exact historical boundary | Manifest + capture receipts bind exact session and every Parquet byte | machinery ready; Monday boundary absent |
| Scope and source health | immutable 15-name H7 scope; gate requires exact receipt package | machinery ready; Monday receipt absent |
| Measured feasibility | `2026-08-09-feasibility.json`, hash `8b567a5eb6f1950fa32ee9ddfbd4a440e32a7e12ff7a617888e9cd67baff625c` | complete; owner decision pending |
| Window identity | builder derives start/count/end and freezes unchanged strategy/cost/scoring identity | prepared; owner fields blank |
| New store | `ledger/h7_forward_schwab/` verifies VALID-EMPTY | ready for guarded first event only |
| Backup/restore | Restic allow-list includes new chain/report/ledger paths | `BLOCKED_PENDING_MONDAY_CANARY` |
| Independent adversarial review | prompt below | pending orchestrating Claude/Opus |

## OD-3 template — OWNER MUST TYPE THE OPERATIVE LINE

`OD-3 2026-__-__: future H7 paper observations MUST USE NEW NAMESPACE h7-forward-schwab-v1. The prior registration and event remain immutable. The chosen namespace must bind provider, cache manifest, final as-of boundary, scope identity, source-health receipt, and activation date before any new observation.`

Blank owner action: **[NOT TYPED / NOT AUTHORIZED]**

## Fresh starvation measurement — decision intentionally blank

The cached-only frozen entry stack passed **3 of 1,050 symbol-days** over 70
common sessions (2026-04-16 through 2026-07-27), a base rate of
`0.002857142857142857`. For a 70-session, 15-name window, the required formula
projects **3.0 expected entries**. The frozen scorer remains
`min_losses_for_verdict: 10`. The tool emitted no acceptance verdict.

Owner must choose and type exactly one path after review:

- **[OWNER TYPES REDESIGN DECISION HERE]**, or
- **[OWNER TYPES EXPLICIT STARVATION-RISK PRE-ACCEPTANCE CLAUSE HERE, quoting 3/1050, base rate 0.002857142857142857, expected entries 3.0, and the 10-loss bar].**

Current state: **[NO CHOICE TYPED]**.

## New numeric parameter provenance

| Value | Role | Provenance / authority | Frozen? |
|---|---|---|---|
| 15:45 ET | official preclose capture slot | owner-approved brief, 2026-08-09 | no activation performed |
| minimum 2 expirations per symbol | rejects an intraday-style single-expiry package | owner-approved brief, 2026-08-09 | capture validation only |
| 70 lookback sessions | fresh base-rate measurement horizon | LLM-asserted implementation choice, pending owner confirmation | no |
| 70 proposed window sessions | projection input matching the existing planned window | LLM/tool-computed scenario; owner must type final count | no |
| 3 / 1,050 and 3.0 expected entries | measured result | LLM/tool-computed from cached inputs; receipt-bound | observation, not parameter |
| 10 minimum losses | unchanged frozen H7 scorer rule | inherited from existing registration/config | unchanged |

## Prepared authority change — NOT APPLIED

The patch is stored at
`reports/h7_forward_schwab/2026-08-09-authority-flip.PREPARED.patch`. It changes
only `exact_session_source_active=True`, `h7_active=True`, and matching tests.
It must not be applied or committed until all of these occur in order:

1. Monday canary is 15/15 and its manifest verifies.
2. Owner types OD-3 and the starvation decision.
3. Backup/restore drill succeeds byte-for-byte.
4. Independent adversarial review is resolved.
5. Owner registers `h7-forward-schwab-v1` through the guarded door.
6. Owner explicitly authorizes the authority-flip commit.

## Adversarial review request for orchestrating Claude/Opus

> Review branch `feat/h7-forward-schwab-v1` adversarially: show me how this
> could be lying. Focus on look-ahead, hidden prior-day/intraday fallback,
> partial-universe acceptance, receipt/manifest/hash drift, Schwab field
> normalization, feasibility denominator and stack equivalence, guarded-door
> bypass, old-ledger mutation, backup omissions, and any path that activates
> H7 or trading before owner authorization. Do not merely confirm tests pass.
> Return blocking findings first with file/line evidence and an explicit
> merge/registration recommendation.

## Owner-only actions remaining

OD-3 typing; starvation accept/redesign; registration through the guarded
door; authority-flip authorization/commit; any merge to main.
