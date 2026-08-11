# H7 Schwab owner gate packet — stopped at feasibility

**Status:** STOPPED_FEASIBILITY / NOT REGISTERED / NOT ACTIVATED. The owner
selected redesign and rejected starvation-risk acceptance for
`h7-forward-schwab-v1`. This document is not operative owner wording and grants
no authority. Live trading remains disabled.

## Readiness snapshot

| Contract item | Evidence | State |
|---|---|---|
| Provider and cache identity | Schwab read-only; `.cache/schwab_chains/`; `preclose_snapshot_v1` | machinery ready; live canary absent |
| Exact historical boundary | Manifest + capture receipts bind exact session and every Parquet byte | machinery ready; evidence from the next valid completed-session 15:45 ET canary is absent |
| Scope and source health | immutable 15-name H7 scope; gate requires exact receipt package | machinery ready; the next valid completed-session 15:45 ET canary receipt is absent |
| Measured feasibility | `2026-08-11-feasibility-primary-earnings.json`, embedded hash `d0ffe1f900b8ffc132f757f9783d4581464aaf8b3538271fe2ae337ba1702d0c`; 4/1,050 passes; 4.0 expected entries | **FAIL: 4.0 < 20; v1 stopped** |
| Window identity | builder preserves unchanged strategy/cost/scoring identity and now mechanically refuses projected entries below 20 | v1 cannot qualify from this receipt |
| New store | `ledger/h7_forward_schwab/` verifies VALID-EMPTY | remains untouched; no v1 registration permitted |
| Backup/restore | Restic allow-list includes new chain/report/ledger paths | real canary and byte-exact restore remain evidence work only; they cannot activate v1 |
| Independent adversarial review | prior review material remains non-authoritative | cannot override the failed feasibility gate |

## OD-3 template — OWNER MUST TYPE THE OPERATIVE LINE

`OD-3 2026-__-__: future H7 paper observations MUST USE NEW NAMESPACE h7-forward-schwab-v1. The prior registration and event remain immutable. The chosen namespace must bind provider, cache manifest, final as-of boundary, scope identity, source-health receipt, and activation date before any new observation.`

Blank owner action: **[NOT TYPED / NOT AUTHORIZED]**

OD-3 remains untyped and inoperative because v1 did not qualify. It must not be
typed to authorize this failed receipt.

## Feasibility result — owner selected redesign

The independently replayed, cached-only frozen entry stack passed **4 of 1,050
symbol-days** over the exact 15-name by 70-session denominator. Its base rate
projects **4.0 expected entries** for the proposed 70-session, 15-name window.
The feasibility floor is `2 * min_losses_for_verdict = 20`. Therefore
`4.0 < 20`, and v1 registration is mechanically refused.

The owner selected redesign and rejected the old starvation-risk acceptance
path. No generic starvation-risk clause can reopen `h7-forward-schwab-v1`.

Had the repaired v1 receipt qualified, registration would additionally have
required this exact second owner-line shape, bound to that qualifying receipt's
hash:

`REJECT OLD 3/1050 STARVATION-RISK PATH; BIND h7-forward-schwab-v1 TO QUALIFYING FEASIBILITY RECEIPT <receipt_hash>`

This line cannot be typed or bound to the nonqualifying
`d0ffe1f900b8ffc132f757f9783d4581464aaf8b3538271fe2ae337ba1702d0c`
receipt.

No later v1 rerun may reopen this stopped lane. The only research path is the
separately versioned v2 design below.

## New numeric parameter provenance

| Value | Role | Provenance / authority | Frozen? |
|---|---|---|---|
| 15:45 ET | official preclose capture slot | owner-approved brief, 2026-08-09 | no activation performed |
| minimum 2 expirations per symbol | rejects an intraday-style single-expiry package | owner-approved brief, 2026-08-09 | capture validation only |
| 70 lookback sessions | immutable replay denominator | receipt-bound measurement input | observation, not a new v1 parameter |
| 70 proposed window sessions | projection input matching the existing planned window | receipt-bound scenario | no registration occurred |
| 4 / 1,050 and 4.0 expected entries | independently replayed measured result | LLM/tool-computed from cached inputs; receipt-bound | observation, not parameter |
| 10 minimum losses | unchanged frozen H7 scorer rule | inherited from existing registration/config | unchanged |

## Prepared authority change — FORBIDDEN FOR v1

The patch is stored at
`reports/h7_forward_schwab/2026-08-09-authority-flip.PREPARED.patch`. It changes
only `exact_session_source_active=True`, `h7_active=True`, and matching tests.
It must not be applied or committed for `h7-forward-schwab-v1`. The failed
feasibility receipt cannot be cured by a 15/15 canary, restore drill, owner
wording, or review. The read-only capture lane remains operationally prepared;
the next real 15:45 ET canary and byte-exact restore are still required evidence
work, but neither can register or activate v1.

## Adversarial review request for orchestrating Claude/Opus

> Review branch `feat/h7-forward-schwab-v1` adversarially: show me how this
> could be lying. Focus on look-ahead, hidden prior-day/intraday fallback,
> partial-universe acceptance, receipt/manifest/hash drift, Schwab field
> normalization, feasibility denominator and stack equivalence, guarded-door
> bypass, old-ledger mutation, backup omissions, and any path that activates
> H7 or trading before owner authorization. Do not merely confirm tests pass.
> Return blocking findings first with file/line evidence and an explicit
> merge/registration recommendation.

## Design-only next path

See `reports/h7_forward_schwab/2026-08-11-v2-arming-bottleneck-design.md`.
Any v2 work requires a separate namespace, entry-stack version, feasibility
receipt, and preregistration before experiments. The design itself authorizes
no experiment, registration, authority change, ops advance, or ritual run.
