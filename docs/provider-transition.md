# Provider transition — ThetaData exit, Schwab operating path (CANONICAL)

**Status:** canonical living document, created 2026-07-31.
**Supersedes:** `docs/superpowers/2026-07-07-thetadata-cancel-checklist.md` and
every reference to a `THETADATA_EXIT_PLAN` (that document was referenced but
never existed as a file). The 07-07 checklist's pre-cancel top-up idea is
carried forward below as owner decision OD-2.
**Companions:** `docs/schwab-market-data-setup.md` (setup + security),
`reports/strategy-evaluations/09_session5_refetch_gate.md` (measured refetch
cost), `reports/strategy-evaluations/12_review_of_the_two_landed_commits.md`
§4 (intraday entitlement probe).

**Owner direction (2026-07-30):** the ThetaData subscription will end. Schwab
API access remains. No new paid market-data subscription enters the plan.

Definitions used below: *EOD* = end of day. *Greeks* = option sensitivity
numbers (delta etc.) needed to pick contracts by delta. *v1 cache* = the
existing 31,367 parquet files under `.cache/chains/` (2018-01-02 →
2026-07-27 span; report 09 counted 22 active symbols, but 26 symbol prefixes
exist on disk — CRWD, IBEX, UNH, ZS appear to be legacy probes — plus one
stray `dolthub/` subdirectory holding a single SPY file; none of this changes
immutability: every byte stays). *v2* = the proposed richer cache schema that
keeps provider provenance (schema drafted; gate code exists only on the
unmerged `codex/cache-schema-v2` branch).

---

## 1. Fail-closed provider policy (binding)

When a feature needs historical depth, timestamps, Greeks, or provenance that
no available provider or cache supplies, the feature **stops with a named
blocker**. Silently substituting delayed, stale, or weaker data is forbidden.
Precedent in code: `data/schwab_adapter.py` raises on `isDelayed` chains
rather than storing them. Enforced as instruction via
`.claude/rules/data-and-providers.md`; every new adapter must follow it.

## 2. Capability and impact matrix

Legend for "after cancel": UNCHANGED (works from local data), DEGRADED
(works with a stated loss), STOPS (fail-closed blocker), OWNER (needs an
owner decision first).

| Capability | ThetaData role today | Cached support | Schwab support in repo | After cancel | Safe fallback / replacement | Evidence |
|---|---|---|---|---|---|---|
| Existing historical chains (reads) | None — reads are local | Full: 31,367 v1 parquet files | None needed | UNCHANGED | Keep v1 immutable | `.cache/chains/` count, this session |
| New historical chain collection | Sole source (`option_history_greeks_eod` + OI, 2 calls/symbol-day) | Grows only while subscribed | **None** — Schwab has no dated historical option chains endpoint in the repo adapter | STOPS at cancel | None without a paid source (excluded by owner direction). Cache freezes at last pull | `data/thetadata_adapter.py`; `docs/schwab-market-data-setup.md` "Schwab versus ThetaData" |
| EOD quote refresh for watch/features (H6/H8 gating) | Daily top-up path | Through 2026-07-27 | Not a valid substitute for the historical cache (live-only, not written to `.cache/chains`) | STOPS growing; existing evaluators keep working on frozen data until their as-of dates pass the cache edge | Fail closed: watches must refuse as-of dates beyond cache coverage | adapter + rule file |
| Intraday quotes (live) | Was ThetaData terminal | n/a | **Yes** — snapshot quotes/chains, probe-verified 2026-07-29/30 | UNCHANGED (moves to Schwab) | Already landed on `sfix` (`54b0e76`) | `reports/live_probe/2026-07-29.json` |
| Greeks / 30-delta selection, historical-intraday | NOT entitled on Standard tier (probe 2026-07-24: PERMISSION_DENIED) | Not in cache (EOD snapshot only) | Live Greeks yes (`option_snapshot_greeks_all`); historical no | STOPS (was already blocked) | Park intraday-entry research; live display may show Schwab Greeks | report 12 §4 |
| 13:00 recorder (`INTRADAY_CAPTURE_TIMES` "midday", owner-typed 2026-07-24) | Was the quote source | Receipts under `reports/intraday_capture/` accumulate | Wired into `intraday_capture.py` per `54b0e76` | UNCHANGED via Schwab | Keep recording; display-only, zero entry authority | `config.py:731`; commit 54b0e76 |
| D+1 close backtest convention | Needs only the v1 EOD cache | Full | Not involved | UNCHANGED | Keep; it is the only convention the cache supports (registration still owed — P0 item, report 12 F6) | report 12 §4 |
| Live dashboard display | Was ThetaData | n/a | Yes (two-lane design; live lane on Schwab) | UNCHANGED | — | commit 54b0e76 |
| Live entry authority | None | None | **None — by design.** Adapter is allowlisted read-only; `SCHWAB_TRADING_ENABLED=false` enforced in code | UNCHANGED (still zero) | Never changes without a new registration | setup doc "Security" |
| H5 paper book marking | EOD marks | Cache + Yahoo closes | Live quotes could display marks, not record official ones | DEGRADED after cache edge | Fail closed past coverage | PROJECT_STATE data notes |
| H6 / H8 forward evaluators | EOD chain freshness | Through 2026-07-27 | No historical substitute | DEGRADED → STOPS as as-of passes cache edge | OD-2 decides a final top-up | README H6 section |
| H7 forward window (registered 2026-07-20) | Daily source-health + gate inputs | Earnings assertions + cached chains | Live lane only | OWNER — governance already unresolved (v1 receipt; registration-only window) | OD-3 below | `ledger/h7_forward/events.jsonl` (1 event) |
| H9 | Spent | Receipt + census on disk | n/a | UNCHANGED — one allowed run already used; never refetched | — | `reports/h9/receipt.json` |
| v2 backfill (NVDA/PLTR/AMZN × 252 sessions = 756 partitions, ≤1,512 calls) | Only possible WHILE subscribed | Would create the first v2 namespace | Impossible on Schwab | OWNER — becomes permanently impossible at cancel | OD-1 below | report 09 method; handoff scope |
| Feature-artifact rebuilds from v2 | Depends on v2 backfill | None yet | None | Blocked behind OD-1 | Park Phase B if OD-1 = no | `codex/cache-schema-v2` branch |
| Reproducibility after cancel | — | Everything already cached replays offline | — | UNCHANGED for existing results | Tests and backtests are offline by rule | CLAUDE.md commands note |
| Provenance / citations | v1 discards provider provenance (report 09 C4) | v1 limitation is permanent for v1 files | Schwab captures carry entitlement context | DEGRADED (v1 stays provenance-poor forever) | v2-only for future gates if Phase B proceeds | report 09 |

**The one-sentence version:** cancellation freezes the historical world at the
cache edge (2026-07-27) forever; Schwab keeps the live display lane alive and
nothing else; anything that needs new historical option data either happens
before cancel day or never.

## 3. Reconciling the v2 backfill with cancellation

The 756-partition v2 backfill is only executable while the ThetaData
subscription is active. It therefore cannot sit in the P2 backlog as if it
were schedulable later — it must be decided as a **pre-cancel owner decision
(OD-1)**, and if declined, Phase B's H6/H8 v2 rebuild moves to the
abandoned-work list. It does not belong in a Schwab redesign: Schwab cannot
produce it at any price available to this project. No request is triggered by
this document.

## 4. Before cancel day (read-only until owner approves)

1. Owner decides OD-1 and OD-2 (below).
2. If any pull is approved: written call-count estimate first, one approval
   per pull, results land in the approved namespace only, manifest regenerated
   (`tools/cache_manifest.py`), `DATA_PULL` fact appended via the typed API.
3. Verify `ledger/facts.log` records the final cache edge and the cancel date.
4. After cancel: no code path may attempt a ThetaData call; the terminal
   dependency becomes dead configuration to be removed in a later cleanup task
   (roadmap P1).

## 5. Owner decisions (recommendation + safe default)

- **OD-1 — v2 backfill (756 partitions, ≤1,512 calls) before cancel?**
  Recommendation: authorize it as the final ThetaData pull IF Phase B (v2-gated
  H6/H8) is still wanted within ~6 months — the cost is small and the window
  closes permanently. Safe default if uncertain: decline and move Phase B to
  abandoned; the v1 evaluators keep working on frozen data.
- **OD-2 — plain EOD top-up of the forward names through the last session
  before cancel?** (The 07-07 checklist's surviving idea; the cache edge is
  2026-07-27.) Recommendation: yes — it is cheap, bounded, and extends every
  forward evaluator's usable life. Safe default: skip; evaluators fail closed
  at the edge.
- **OD-3 — H7 governance:** continue future v2-era sessions under the existing
  2026-07-20 registration, or register a new typed ledger + window namespace.
  Recommendation: new namespace (the old window holds only its registration
  event and its gate receipt is v1-based); the old record stays untouched
  (append-only). Safe default: make no new registrations until decided.
- **OD-4 — cancellation date itself.** Repo records conflict (07-07 checklist
  said "ends 2026-07-29"; PROJECT_STATE 07-23 said "confirmed to 2026-11-30,
  decision ~10-01"; owner 07-30 says it will end). The owner holds the real
  date; record it in `facts.log` when known. Nothing in this pass cancels
  anything.
