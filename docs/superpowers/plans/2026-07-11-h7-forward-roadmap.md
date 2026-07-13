# H7 forward-paper roadmap (dependency-ordered) — DOCUMENTATION ONLY

**Status: Stages 1–5 BUILT (Stage 1 hardened; Stages 2, 4, and 5 build-only;
Stage 3 inactive with zero real events). Stages 6–7 remain PROPOSED, NOT
IMPLEMENTED, NOT ACTIVATED; each is a separately authorized arc.
Stage 8 — the activation gate — belongs to the next independent review,
not to any implementation session. (Original 7b-2R.2 deliverable replacing
the retired 7b-F0 proposal.)**

Context: H7's 2018–2026 historical diagnostic is permanently withdrawn
(amendment v1.3, `6faa4945…`); the point-in-time forward paper window is
the sole verdict-bearing path. Each stage below depends on every stage
above it; none may be built out of order, and building any of them is a
separately authorized arc.

## Stage 1 — Source health — BUILT 2026-07-11; HARDENED 2026-07-12

*(Implemented as `options_researcher/h7_source_health.py` +
`tools/h7_refresh_earnings.py`; plan
`2026-07-11-h7-stage1-source-health.md`. Independent review added exact
watcher replay, locked/validated appends, same-event supersession, and fully
evidence-backed gating rows. Operational acceptance remains: backfill all 12
names and make the live health command exit 0 before authorizing Stage 2.)*

Per-symbol source-health reporting over the v3 gating store: newest gating
assertion, event class/status/source type, days to expected report, STALE
/ MISSING flags (no live future schedule; grace expiring within N
sessions). Exit non-zero when any name is unhealthy. Owner-in-the-loop
append-only refresher for schedules/occurrences (SEC acceptance times
first, company IR/PR second, aggregator estimates only as disclosed
`estimated`); every promotion cites its raw evidence row (the 7b-2R.2
promotion contract). No crawler — recurring automation stays deferred.

## Stage 2 — 12-name daily data gate — BUILT 2026-07-12; NOT OPERATIONALLY AUTHORIZED

*Implemented as `options_researcher/h7_data_gate.py` +
`tests/test_h7_data_gate.py` on `feature/h7-stage2-daily-data-gate` (base:
Arc B inventory evidence `f7ff478`). BUILD-ONLY owner authorization
2026-07-12: the module exists and is tested, but operational GO, the forward
window, paid data pulls, and activation remain separate owner decisions.
The first whole-universe data result reached GO 12/12 for evaluation session
2026-07-10 after the separately authorized chain/close top-up (`36c9e1a`;
dated artifact `reports/h7_data_gate/2026-07-10.json`). This is data-readiness
evidence only: source health and operational authorization still gate any
watcher run. Readiness/authorization boundary:
`2026-07-12-h7-stage1-closeout-stage2-readiness.md`. The original spec
paragraph below is unchanged.*

A daily go/no-go over the full H7 universe (8 watchlist + 4 core names):
chains and closes both end exactly at the evaluation session, session
alignment verified, liquidity-relevant fields present, staleness and
same-day-partial guards green. The watcher already fails closed per name;
this stage makes the whole-universe gate a single dated artifact so a
partially-degraded day is visible BEFORE any decision output is read.

## Stage 3 — Hash-chained forward event ledger — BUILT 2026-07-12; INACTIVE (zero real events)

*Implemented as `options_researcher/h7_event_ledger.py` +
`tests/test_h7_event_ledger.py` + `ledger/h7_forward/README.md` on
`feature/h7-stage3-forward-event-ledger` (parent Stage 2 build `28cd415`).
BUILD-ONLY owner authorization 2026-07-12. A SEPARATE hash-chained ledger
(`ledger/h7_forward/events.jsonl` + `HEAD`) with its own verifier — it never
touches `ledger/experiments.jsonl`, `ledger/HEAD`, or trial_count. Public
API append_event/read_events/verify + `verify` CLI; idempotent by
(event_id, logical_hash), conflicting content refused, causal references
enforced backward, concurrent writers serialized by an exclusive lock,
crash-DETECTING (a crash between events.jsonl fsync and HEAD replace leaves a
stale-HEAD mismatch the next verify refuses — no auto-repair). The default
store is ABSENT and the first real event is prohibited until Stage 8
activation; the default verifier prints VALID EMPTY (exit 0). Stage-7 review
prerequisites landed 2026-07-13: shared reader locks, strict UTC fields, and a
direct canonical-JSON regression. The original
spec paragraph below is unchanged.*

An append-only, hash-chained event log (the experiments-ledger pattern)
for every forward-window event: gate states, board resolutions, DISPLACED
lanes, entry/exit intents, owner approvals, fills, skips, data-gap days.
Write-once, verified like `ledger/experiments.jsonl`; nothing about the
forward window is reconstructed from memory or prose.

## Stage 4 — T+1 lifecycle (paper) — BUILT 2026-07-13; INACTIVE

*Corrected spec, owner parameter (`H7_FORWARD_CONTRACTS=1`), and spec-hash
pre-registration completed before implementation. Implemented as
`options_researcher/h7_paper_lifecycle.py` +
`tests/test_h7_paper_lifecycle.py` in commit `03d3922`. Independent review
passed after remediation; 31 focused tests and the complete 886-test suite
passed with Ruff, Pyright, and focused pre-commit hooks. BUILD-ONLY,
SYNTHETIC-ONLY, INACTIVE: no real forward event or activation is authorized.*

The watcher decides at session T; owner-approved entries execute T+1 at
recorded quotes with the canonical adverse-price transform; exits follow
the frozen trigger interpretations and priority; every transition lands in
the Stage-3 event ledger with its causal inputs (chain day, closes day,
gate reason). One position per symbol/lane; cancel-never-chase.

## Stage 5 — Global risk accounting — BUILT 2026-07-13; INACTIVE

*Pre-registered specification plus reservation-continuity amendment implemented
as `options_researcher/h7_forward_book.py`, with optimistic ledger-head
preconditions added to Stage 3 and fill/intent integration added to Stage 4.
Commit `87a17f3`; independent review PASS after remediation; 32 focused Stage-5
tests, 34 Stage-4 integration tests, and the complete 924-test suite passed
with Ruff, Pyright, and focused pre-commit hooks. BUILD-ONLY, SYNTHETIC-ONLY,
INACTIVE: the CSV mirror remains read-only and no real forward event exists.*

Cross-symbol enforcement of the monthly sleeve (H7_MONTHLY_AT_RISK),
H7C_MAX_CONCURRENT, and one-open-per-underlying at the BOOK level (the
live analogue of the board resolver), reconciled daily against
`data/positions/h7_positions.csv` with `open_h7_book` semantics.

## Stage 6 — Scoring — BUILT 2026-07-13; INACTIVE

*Pre-registered scoring procedure implemented as
`options_researcher/h7_forward_scoring.py` in commit `f032ba1`, with
exact-session benchmark commitments added to Stage 4 and strict action,
contract, quote, cost, risk, and cohort replay. Independent review PASS after
three adversarial remediation rounds; 19 Stage-6 tests, 32 Stage-5 tests, 35
Stage-4 tests, and the complete 944-test suite passed with Ruff, Pyright, and
focused pre-commit hooks. BUILD-ONLY, SYNTHETIC-ONLY, INACTIVE: no window is
registered and the real forward ledger remains `VALID EMPTY`.*

The forward window's verdict machinery, pre-registered BEFORE the first
entry: expectancy per trade after costs with bootstrap CI, verdict gating
on MIN_LOSSES_FOR_VERDICT losses, per-lane cohorts, benchmark columns
(underlying move alongside every trade). Vocabulary stays frozen:
survived / rejected / inconclusive.

## Stage 7 — Synthetic proof — BUILT 2026-07-13; INACTIVE

*Pre-registered disposable-fixture proof implemented as
`options_researcher/h7_synthetic_proof.py` +
`tests/test_h7_stage7_synthetic_proof.py` in commit `b632feb`. Independent
review PASS: 13-event verified synthetic ledger; 12/12 source health and data
gate; decision 2026-07-10 → T+1 entry 2026-07-13 → exit 2026-07-15; monthly
risk retained after close; after-cost P&L reconstructed; all required refusal
arcs passed. Stage-7 tests 4/4, focused H7 tests 474/474, full suite 948/948,
Ruff, Pyright, and focused pre-commit passed. The default forward ledger
remained `VALID EMPTY`. BUILD-ONLY, SYNTHETIC-ONLY, INACTIVE; the fixture dates
do not register a window.*

Before live-tick activation: a full synthetic dress rehearsal of stages
1–6 on fixture data (the engine-test idiom) proving gate refusals, event
ledger integrity, T+1 causality, risk caps and scoring end-to-end, with
the results pasted into facts.log as dated evidence.

## Stage 8 — Activation gate (separate; not this roadmap's to open)

*Readiness packet prepared 2026-07-13 at
`2026-07-13-h7-stage8-activation-readiness.md`; the gate remains explicitly
NOT OPEN. Current blockers include 4/12 source health, unconfirmed paid-data
continuity, unresolved Darwin durability strength, blank owner window inputs,
and an uncommitted code/config identity. No registration or real event was
created.*

A distinct owner + independent-review decision that: pre-registers the
window (start, duration, decision procedure, verdict gate) in the ledger;
confirms ThetaData renewal for daily EOD chains (the 2026-07-25 question
precedes any start date); and only then starts the clock. No stage below
it authorizes activation.

## Explicitly out of scope, permanently or until re-registered

- Any historical H7 backtest or P&L (withdrawn; the retirement gate
  refuses mechanically).
- A post-earnings-only historical study — a NEW conditional hypothesis
  with its own registration; it can never reject or validate H7.
- Live order placement of any kind (this repo is a validator).
