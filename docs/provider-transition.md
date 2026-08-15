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
(works with a stated loss), STOPS (fail-closed blocker), PAUSED (an owner
decision closed the current path without activation).

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
| H6 / H8 forward evaluators | EOD chain freshness | Through 2026-07-27 | No historical substitute | DEGRADED → STOPS as as-of passes cache edge | OD-2 declined the final top-up; fail closed beyond exact cached coverage | README H6 section |
| H7 forward window (registered 2026-07-20) | Daily source-health + gate inputs | Earnings assertions + cached chains | Live lane only | PAUSED — do not restart now; the old namespace remains registration-only | Any later restart needs a new registration and namespace under the eight-item contract | `ledger/h7_forward/events.jsonl` (1 event); `reports/h7_forward/2026-08-02-restart-decision.md` |
| H7 Schwab restart candidate (`h7-forward-schwab-v1`) | Exact-session preclose package under `.cache/schwab_chains/` | Frozen history remains measurement input only | Read-only full Schwab chain | PREPARED / NOT REGISTERED / NOT ACTIVATED | Owner-approved divergence: the ~15:45 ET preclose snapshot is the session's official chain (`preclose_snapshot_v1`), not the old ThetaData EOD mark; every session must carry a byte-bound receipt/manifest | `reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md` |
| H9 | Spent | Receipt + census on disk | n/a | UNCHANGED — one allowed run already used; never refetched | — | `reports/h9/receipt.json` |
| Isolated v2 capture (18 symbols × 256 sessions) | Completed under a later bounded approval | 4,608 partitions; full audit passes with three exact-byte quarantines | Impossible to extend historically through Schwab | FROZEN / UNMERGED | Keep branch parked unless the owner explicitly authorizes integration | `reports/thetadata_v2/2026-08-02-od1-full-audit.md` on `codex/od1-v2-current` |
| Feature-artifact rebuilds from v2 | Would depend on integrating the audited v2 path | None authorized | None | PARKED | Do not rebuild H6/H7/H8 or claim strategy evidence from the isolated branch | H7 restart decision; isolated branch report |
| Reproducibility after cancel | — | Everything already cached replays offline | — | UNCHANGED for existing results | Tests and backtests are offline by rule | CLAUDE.md commands note |
| Provenance / citations | v1 discards provider provenance (report 09 C4) | v1 limitation is permanent for v1 files | Schwab captures carry entitlement context | DEGRADED (v1 stays provenance-poor forever) | v2-only for future gates if Phase B proceeds | report 09 |

**The one-sentence version:** the canonical historical world is frozen at the
2026-07-27 cache edge; Schwab keeps the live display lane alive and nothing
else, while any feature needing new historical option data remains fail-closed
unless a separately authorized source and registration are supplied.

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

## 6. Schwab operating path — Phase A landed 2026-08-15 (display only)

**Phase A (this brief, brief 12 rev-2): DISPLAY freshness.** The attractiveness
board and QM panel gained a read path to the newest VERIFIED Schwab pre-close
capture session through one boundary module,
`options_researcher/schwab_chain_view.py`. No staleness gate was deleted,
loosened, or re-thresholded — the gates stand down only where fresh data
genuinely exists, and the per-card `CHAIN_STALE_VS_TODAY` rule is unchanged.

What Phase A binds itself to:

- **Verified only.** Chains are consumed only for sessions where
  `tools.schwab_chain_manifest.verify_session` succeeds against the session's
  OWN manifest universe. A verification failure makes the session absent AND
  renders a loud page notice naming the session and the error; a checkout with
  no receipts says that too.
- **Never called a close.** Every date surface (page banner, header chip,
  section line, close field) labels the data `15:45 pre-close (Schwab)` with
  `close_kind = preclose_mid_1545`. A section renders fresh ONLY when the
  matching 15:45 intraday receipt supplies an unforced `stock_snapshot`
  `spot_mid`, so the underlying price and the option quotes are the same
  instant; otherwise the symbol stays on the frozen cache with a visible
  reason.
- **IV is passed through.** The store's `iv` is already decimal —
  `data/schwab_adapter.py:148-154` converts Schwab's percentage points at
  capture. Nothing in the display path converts it again.
- **Owner name scope.** `DISPLAY_EXCLUDED_SYMBOLS = {ET, USAR}`
  (owner-directed in-session 2026-08-14) applies to the FRESH path only. Both
  names still render from the frozen cache with their own older date; no
  registered universe, cohort, or capture list changed.
- **Nothing registered.** No hypothesis watcher reads this path; nothing here
  is verdict-bearing or FIRE-capable; `.cache/chains` is never written (OD-2 /
  OD-4 stand) and neither is the H5-registered feature store
  `.tmp/research/attractiveness` — schwab-session feature values are computed
  in memory and any value that cannot be computed honestly is null with a
  named reason.

**Phase B (owner-gated, NOT started): hypothesis inputs.** Feeding capture data
to H5/H6/H7/H8/H10 watchers is a per-hypothesis registered-input amendment,
draftable under the 2026-07-25 delegation with independent adversarial review.
Display precedent does not authorize it.

**Phase C (owner-gated, NOT started): `exact_session_source_active` (S1) flip
and re-registration.** The ratified S1 bar is three consecutive verifying
scheduled sessions; one exists (2026-08-14), so the earliest honest flip is
approximately 2026-08-19 after the Mon/Tue/Wed captures. Any restart carries a
new registration and namespace (OD-3) and must pass the 2026-07-24 feasibility
gate.

### Open follow-ups this brief did not close

1. **`reports/schwab_chains` is ops-only.** The capture receipts and manifests
   exist in the production execution checkout (`~/options-validator-ops`) and
   are not tracked in git. A research checkout therefore shows the honest "no
   Schwab pre-close capture receipts found" page state. Whether these receipts
   should be tracked (they are the verification evidence for a display path)
   is an open ops question.
2. **`CHAIN_STALE_WARN_SESSIONS` / `CHAIN_STALE_BLOCK_SESSIONS` remain
   LLM-asserted** (proposed 2026-08-04, owner-unconfirmed; `config.py:672-673`).
   Phase A did not touch them, and this brief made no `config.py` change at
   all — a config edit invalidates every capture receipt's `config_hash`
   (`intraday_preview.py:81`) until the next live capture.
3. **Freshness runway.** Captures are scheduled daily; a session that fails to
   capture leaves the board on the frozen cache with its true (large) age, and
   the banner says so rather than degrading quietly.
4. **The closes store (`.cache/underlying`) is still frozen at 2026-08-04.**
   That is why `rv21`, `iv_minus_rv`, and the technicals of a pre-close section
   are null / older-dated with named reasons rather than interpolated. Its
   refresh is the subject of the 2026-08-14 drill-RED disposition and is owner
   business, not this lane's.
