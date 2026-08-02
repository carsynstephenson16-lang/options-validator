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
numbers (delta etc.) needed to pick contracts by delta. *v1 cache* = 31,366
canonical top-level parquet files under `.cache/chains/` (2018-01-02 →
2026-07-27 span, 26 symbol prefixes). One nested SPY snapshot is preserved and
classified as noncanonical. *v2* = the richer, provider-provenance schema in the
isolated `codex/od1-v2-current` branch. Its approved local capture was fully
audited, but that branch remains unmerged and has no strategy authority.

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
| Existing historical chains (reads) | None — reads are local | Full: 31,366 canonical v1 parquet files | None needed | UNCHANGED | Keep v1 immutable | Q9 receipt and `tools/cache_manifest.py verify` |
| New historical chain collection | Sole source (`option_history_greeks_eod` + OI, 2 calls/symbol-day) | Grows only while subscribed | **None** — Schwab has no dated historical option chains endpoint in the repo adapter | STOPS at cancel | None without a paid source (excluded by owner direction). Cache freezes at last pull | `data/thetadata_adapter.py`; `docs/schwab-market-data-setup.md` "Schwab versus ThetaData" |
| EOD quote refresh for watch/features (H6/H8 gating) | Daily top-up path | Through 2026-07-27 | Not a valid substitute for the historical cache (live-only, not written to `.cache/chains`) | STOPS growing; existing evaluators keep working on frozen data until their as-of dates pass the cache edge | Fail closed: watches must refuse as-of dates beyond cache coverage | adapter + rule file |
| Intraday quotes (live) | Was ThetaData terminal | n/a | **Yes** — snapshot quotes/chains, probe-verified 2026-07-29/30 | UNCHANGED (moves to Schwab) | Already landed on `sfix` (`54b0e76`) | `reports/live_probe/2026-07-29.json` |
| Greeks / 30-delta selection, historical-intraday | NOT entitled on Standard tier (probe 2026-07-24: PERMISSION_DENIED) | Not in cache (EOD snapshot only) | Live Greeks yes (`option_snapshot_greeks_all`); historical no | STOPS (was already blocked) | Park intraday-entry research; live display may show Schwab Greeks | report 12 §4 |
| 13:00 recorder (`INTRADAY_CAPTURE_TIMES` "midday", owner-typed 2026-07-24) | Was the quote source | Receipts under `reports/intraday_capture/` accumulate | Wired into `intraday_capture.py` per `54b0e76` | UNCHANGED via Schwab | Keep recording; display-only, zero entry authority | `config.py:731`; commit 54b0e76 |
| D+1 close backtest convention | Needs only the v1 EOD cache | Full | Not involved | UNCHANGED | Keep; research-ledger seq 21 registers D+1 close, fill-session `entry_date`, and the terminal conservative-mark exception | `ledger/experiments.jsonl` seq 21; `PROJECT_STATE.md` P0.5 |
| Live dashboard display | Was ThetaData | n/a | Yes (two-lane design; live lane on Schwab) | UNCHANGED | — | commit 54b0e76 |
| Live entry authority | None | None | **None — by design.** Adapter is allowlisted read-only; `SCHWAB_TRADING_ENABLED=false` enforced in code | UNCHANGED (still zero) | Never changes without a new registration | setup doc "Security" |
| H5 paper book marking | EOD marks | Cache + Yahoo closes | Live quotes could display marks, not record official ones | DEGRADED after cache edge | Fail closed past coverage | PROJECT_STATE data notes |
| H6 / H8 forward evaluators | EOD chain freshness | Through 2026-07-27 | No historical substitute | DEGRADED → STOPS as as-of passes cache edge | OD-2 decides a final top-up | README H6 section |
| H7 forward window (registered 2026-07-20) | Daily source-health + gate inputs | Earnings assertions + cached chains | Live lane only | OWNER — governance already unresolved (v1 receipt; registration-only window) | OD-3 below | `ledger/h7_forward/events.jsonl` (1 event) |
| H9 | Spent | Receipt + census on disk | n/a | UNCHANGED — one allowed run already used; never refetched | — | `reports/h9/receipt.json` |
| Isolated v2 capture (18 symbols × 256 sessions) | Completed under a later bounded approval | 4,608 partitions; full audit passes with three exact-byte quarantines | Impossible to extend historically through Schwab | FROZEN / UNMERGED | Keep branch parked unless the owner explicitly authorizes integration | `reports/thetadata_v2/2026-08-02-od1-full-audit.md` on `codex/od1-v2-current` |
| Feature-artifact rebuilds from v2 | Would depend on integrating the audited v2 path | None authorized | None | PARKED | Do not rebuild H6/H7/H8 or claim strategy evidence from the isolated branch | H7 restart decision; isolated branch report |
| Reproducibility after cancel | — | Everything already cached replays offline | — | UNCHANGED for existing results | Tests and backtests are offline by rule | CLAUDE.md commands note |
| Provenance / citations | v1 discards provider provenance (report 09 C4) | v1 limitation is permanent for v1 files | Schwab captures carry entitlement context | DEGRADED (v1 stays provenance-poor forever) | v2-only for future gates if Phase B proceeds | report 09 |

**The one-sentence version:** cancellation freezes the historical world at the
cache edge (2026-07-27) forever; Schwab keeps the live display lane alive and
nothing else; anything that needs new historical option data either happens
before cancel day or never.

## 3. Reconciling the v2 capture with cancellation

The owner later approved one bounded OD-1 v2 capture in an isolated worktree.
It completed 4,608 partitions and passed the full data audit with three
whole-partition quarantines. Acquisition is now disabled. The local data and
audit report are preserved, but the branch is not integrated into `sfix` and
cannot drive H6, H7, H8, a backtest, or a strategy claim without a separate,
explicit owner integration decision.

## 4. Closed operating state

1. Canonical v1 bytes are immutable and the 31,366-entry manifest verifies.
2. The nested SPY snapshot is preserved as a noncanonical alternate.
3. ThetaData acquisition paths are disabled; cached reads remain available.
4. The isolated v2 and future-ticker captures remain parked under their own
   audit receipts. Neither is silently promoted into canonical research use.

## 5. Owner decisions (P1.1 closeout recorded 2026-07-31)

- **OD-1 — LIMITED LATER REVERSAL FOR ISOLATED CAPTURE ONLY.** A bounded
  18-symbol, 256-session v2 pull completed under approval token
  `OD1-V2-9500-APPROVED`. Its audit passes with three quarantines. This did not
  authorize merging the branch, rebuilding strategy artifacts, restarting H7,
  or changing any verdict.
- **OD-2 — DECLINE the final EOD top-up.** No ThetaData or fallback-provider
  call is authorized. The final canonical chain edge remains 2026-07-27 and
  decision-authoritative consumers must fail closed beyond exact cached
  coverage. P1.1 does not regenerate the manifest.
- **OD-3 — H7 remains paused.** Do not restart now. Any later restart must use
  a new registration and namespace; the existing one-record store remains
  untouched. See `reports/h7_forward/2026-08-02-restart-decision.md`.
- **OD-4 — commercial end and operational disablement.** The owner states that
  commercial ThetaData access ends 2026-08-01; the account information
  available to the owner does not specify an exact cutoff time. New acquisition
  is operationally disabled effective 2026-07-31 21:26:46 EDT. Immutable cached
  reads remain enabled; no credential probe was performed.

P1.1 proof is the single `P1_1_PROVIDER_CLOSEOUT` fact appended through
`research.facts.append_fact` at `2026-08-01T01:30:00.910690+00:00`; exact
payload SHA-256:
`4a793409a44b88a9915fb75bdf698a08cf584f02ec1416a8eebbcb2dc72b6f84`.
The canonical top-up stayed declined. The later v2 capture was isolated from
v1. Q7/P1.4 provider-disabled enforcement and Q9 offline readiness are complete;
new acquisition remains refused.
