# H7 Stage 1 operational closeout → Stage 2 readiness

**Status: PROPOSED 2026-07-12 — Stage 2 is now BUILD-ONLY authorized.** This
plan does not open the forward paper window or operational GO. It scopes the
smallest safe path from a built Stage 1 to a separately authorized Stage 2 arc.

**Update 2026-07-12 (deadline-driven, build-only authorization):** The owner
authorized (a) the Arc B read-only inventory — DONE, evidence commit
`f7ff478`, whole-universe NO_GO 0/12; and (b) a **BUILD-ONLY** Stage 2
engineering arc — DONE on `feature/h7-stage2-daily-data-gate`
(`options_researcher/h7_data_gate.py`), live NO_GO 0/12 exit 1. **Neither
authorization opens operational GO, the forward window, paid data pulls,
cache refreshes, activation, or Stages 3–8.** Remaining decision gates before
Stage 2 could ever be operationally authorized, all still open:
1. **CRWV** official earnings advisory → source health 12/12 (currently 11/12,
   exit 1; no aggregator substitute permitted).
2. **ThetaData** subscription decision (~2026-07-25): a forward Stage 2 gate
   needs a *daily* 12-name EOD chain pull; today the cache is 0/12 on recency
   alone. This is the binding data blocker for any GO.
3. Land the Stage 1 operational-closeout branch (`5324426`) and this Stage 2
   build branch under owner + independent review.
Source health independently blocks Stage 2 authorization regardless of the
build being complete.

**Update 2026-07-12 (Stage 3 BUILD-ONLY):** The owner authorized a build-only
Stage 3 arc — the append-only hash-chained forward-event ledger
(`options_researcher/h7_event_ledger.py`, branch
`feature/h7-stage3-forward-event-ledger` from `28cd415`). It is BUILT and
INACTIVE: the default store `ledger/h7_forward/` holds zero real events (only
a README), and the first real event stays prohibited until Stage 8
activation. This does not change any Stage 2 blocker above (CRWV advisory,
ThetaData daily chains, source health 11/12) and authorizes no forward event,
paper position, Stage 4 lifecycle, or activation. Stages 4–8 remain
unauthorized.

## Bottom line

Do not build Stage 2 while Stage 1 reports 4/12 healthy. First ratify the
operational warning runway, backfill the eight missing watchlist names through
the owner-in-the-loop evidence workflow, and require the live source-health
CLI to exit 0. Then inventory the actual 12-name chain/close state read-only.
The inventory, not assumptions, should determine the Stage 2 implementation
brief.

This ordering moves H7 toward its declared forward verdict without reopening
the permanently withdrawn historical diagnostic, changing a frozen strategy
number, adding a crawler, or starting the window.

## Arc A — Stage 1 operational closeout

Owner decisions before mutation:

1. Ratify `H7_SOURCE_HEALTH_WARN_SESSIONS = 5` (one XNYS week), or retype a
   different operational runway. It changes warning timing only, never gate or
   verdict semantics.
2. Approve each evidence row from its exact source before promotion. Future
   schedules prefer company IR/PR; occurred reports prefer SEC acceptance
   timestamps; an aggregator may enter only as disclosed `estimated` with
   notes that no official schedule was found.

Execution, one name and one record per invocation:

1. Build an eight-name evidence worksheet for CRWV, TEM, PLTR, NOW, SMCI,
   NVDA, AMD, and AVGO: fiscal period, status, expected/occurred date, session
   timing, source type, exact HTTPS URL, causal `known_as_of_utc`, and notes.
2. Run `append-raw ... --dry-run`; require validation success. Re-run without
   `--dry-run`, then load the full raw store successfully.
3. Run `promote ... --dry-run`; confirm copied identity/source fields and the
   `actual_quarterly_earnings` classification. Re-run without `--dry-run`,
   then cross-validate the full raw + gating stores.
4. Run `uv run python -m options_researcher.h7_source_health` after each name.
   Stop on a conflict, wrong fiscal identity, missing official timestamp, or
   any store error; do not improvise around a refusal.
5. After all eight: require **12/12 healthy, exit 0**, full unittest, ruff,
   pyright, ledger verification, clean diff review, and a dated append-only
   `H7_STAGE1_OPERATIONAL_READY` fact. Commit the evidence-store changes and
   fact as one reviewable operational closeout; do not mix unrelated files.

No crawler, recurring job, live trade, historical backtest, or P&L is in this
arc.

## Arc B — read-only Stage 2 discovery

Before writing a daily-gate module, inspect the latest completed XNYS session
for the exact 12-name watcher universe and produce a dated inventory containing:

- requested run date, evaluation session, and causal cutoff;
- latest adjusted-close date and chain-snapshot date per symbol;
- exact-session alignment (no stale fallback and no same-day partial row);
- required chain columns, null/non-finite counts, duplicate contract keys, and
  whether liquidity-relevant fields (`bid`, `ask`, `open_interest`) are usable;
- per-symbol `GO | NO_GO` plus explicit reason codes; and
- whether fixing a gap requires only a local refresh or a paid ThetaData pull.

The inventory is read-only. Do not renew a subscription, hit a paid endpoint,
or mutate cache files without a separate owner decision. The ~2026-07-25
ThetaData cutoff must be resolved before any forward-window activation date.

## Stage 2 build brief — only after Arc A + inventory

If separately authorized, Stage 2 should be one read-only module/CLI that:

- imports the same `h7_scope.watch_universe()` definition and derives the same
  completed session as the watcher;
- writes one deterministic, dated, machine-readable whole-universe artifact;
- reports `GO` only when every symbol's close and chain end exactly on the
  evaluation session and every required field/partial-data guard is green;
- exits 0 for whole-universe GO, 1 for an honest data NO_GO, and 2 for an
  unreadable store or invalid invocation;
- supports point-in-time replay without lookahead;
- performs no network refresh and emits no H7 decision output; and
- has fixture-driven regressions for missing/stale/future closes, missing or
  partial chains, malformed fields, duplicate contracts, and one-name failure
  forcing whole-universe NO_GO.

Daily operator order after Stage 2 would be: source health → whole-universe
data gate → watcher. Stop after Stage 2 verification; Stage 3 remains a new,
separately authorized arc.

## Decision gate

Stage 2 implementation is ready to authorize only when all are true:

- owner has ratified/retyped the 5-session operational runway;
- source health is 12/12 with exit 0;
- the eight evidence promotions have been independently reviewed;
- the read-only 12-name data inventory exists and names every current gap;
- no new threshold is needed, or each needed threshold has been returned to
  the owner rather than guessed; and
- the historical H7 runner still refuses both in-sample and OOS history before
  manifest or market-data access.
