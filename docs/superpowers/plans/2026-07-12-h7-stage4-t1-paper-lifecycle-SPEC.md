# H7 Stage 4 — T+1 paper lifecycle: SPEC + pre-registration proposal

**Status: SPEC ONLY. Owner authorized "spec + pre-registration first"
2026-07-12 (in-session answer). NOTHING in this document is implemented.
Implementation is a separate arc gated on (1) owner sign-off of this spec,
(2) the owner typing the one proposed new parameter into `config.py`,
(3) the pre-registration fact below. The first REAL forward event remains
prohibited until Stage 8 activation regardless of this spec.**

Ratified roadmap contract (`2026-07-11-h7-forward-roadmap.md`, Stage 4):

> The watcher decides at session T; owner-approved entries execute T+1 at
> recorded quotes with the canonical adverse-price transform; exits follow
> the frozen trigger interpretations and priority; every transition lands
> in the Stage-3 event ledger with its causal inputs (chain day, closes
> day, gate reason). One position per symbol/lane; cancel-never-chase.

## 1. Timeline semantics (no look-ahead)

Session T's EOD is final only the next day, so all wall-clock runs lag the
sessions they read (the `evaluation_session` contract in `h7_watch`):

- **Day T+1 run** evaluates **session T** (watcher; unchanged). An
  ENTRY-OK becomes an `entry_intent` event.
- **Owner approval** of an intent must be recorded (event
  `recorded_at_utc`) **at or before the XNYS close of session T+1**. The
  fill itself is mechanical at T+1 quotes, so a late approval cannot
  change the price — but approving after T+1's close means approving
  *after seeing whether T+1 moved favorably*: approval-selection bias.
  A later approval expires the intent (a `skip` event, reason
  `approval_late`). No approval by that cutoff expires it with reason
  `approval_missing`.
- **Day T+2 run** computes the **paper fill at session T+1's recorded EOD
  quotes** for approved intents. The entry decision used only ≤T data;
  the fill uses only T+1's cached EOD chain. No intraday rows anywhere.
- **Exit triggers** are evaluated on each completed session T′ against
  the open book; a firing trigger emits `exit_intent` and the close fills
  at session T′+1 quotes, same mechanics. Exits are **mechanical — no
  owner approval** (a frozen trigger that waits for a human is no longer
  frozen; discretion re-enters). Stage 4 adds no discretionary manual-close
  reason to the verdict path.

## 2. Fill mechanics (existing guardrails, bound not restated)

- Quote source: the cached EOD chain parquet for the fill session
  (ThetaData 17:15 ET report; the exact-session file the Stage-2 gate passed).
- Price: every buy uses `adverse_buy(ask)` and every sell uses
  `adverse_sell(bid)`. Those canonical functions apply
  `SLIPPAGE_HAIRCUT` once and round adversely to the cent. Starting from the
  executable quote side already accounts for half-spread; do not add a second
  half-spread charge and do not price any fill from midpoint.
- Costs: `COMMISSION_PER_CONTRACT` per contract, per leg, on entry and exit.
- Liquidity: `MIN_OPEN_INTEREST` and `MAX_SPREAD_PCT` re-checked on every leg
  **at the fill session**, not just at decision time. A required leg failing
  at entry fill → `skip` (reason `liquidity_at_fill`), intent dead.
- Entry fill revalidation uses the frozen contract identity; it never selects
  a substitute. The contract must still exist, remain inside its registered
  DTE band, have a CLEAR earnings gate at the fill-session cutoff, have valid
  quotes/liquidity on every leg, and still satisfy the registered per-trade
  structure economics. Global sleeve/capacity checks remain Stage 5.
- No paper fill occurs unless the fill session's whole-universe `data_gate`
  is GO. On a session-wide NO_GO, an entry intent expires but an exit intent
  remains pending; this is conservative and keeps the Stage-2 gate meaningful.
- Missing/invalid EOD at an **entry** fill session (quote not finite,
  two-sided and uncrossed, or the whole day absent) → `data_gap` + `skip`;
  the entry intent **expires**. Cancel-never-chase means no re-pricing at
  T+2; a fresh entry requires a fresh watcher decision.
- Missing/invalid EOD at an **exit** fill session → `data_gap`, but the exit
  intent remains pending and retries on the first later session with valid
  quotes. It never silently reopens or expires; unresolved at expiration
  fails loud. This preserves the frozen exit causality already implemented in
  `strategies.h7_backtest`.

## 3. Lifecycle state machine → Stage 3 events

| Transition | Event type | Required `causes[]` |
|---|---|---|
| Source health snapshot | `source_health` | — |
| Gate evaluated for the session | `data_gate` | — |
| Board contention resolved | `board_resolution` | the session's `source_health`, `data_gate` |
| Candidate loses board seat | `lane_displaced` | the `board_resolution` |
| Watcher ENTRY-OK | `entry_intent` | `data_gate`, `board_resolution`, `source_health` |
| Owner approves | `owner_approval` | the `entry_intent` |
| Entry paper fill | `paper_fill` | `entry_intent`, `owner_approval`, fill-session `source_health`, `data_gate` |
| Exit paper fill | `paper_fill` | `exit_intent`, fill-session `data_gate` |
| Intent expiry / gate-fail / liquidity-fail | `skip` | the intent (+ the failing `data_gate` or `data_gap`) |
| Missing/invalid required session data | `data_gap` | the session `data_gate` (payload names a session-wide or contract-local gap) |
| Trigger fires on open position | `exit_intent` | opening `paper_fill`, trigger-session `data_gate` (+ `source_health` for an earnings close) |

Every event's `evaluation_session` is the session whose data produced it;
`payload` carries the numbers (strikes, deltas, marks, costs). The book
state (open positions) is **derived by replaying the event ledger**. A healthy
session with no entry is represented by its green source-health/data-gate and
an empty `board_resolution`; it is not a `data_gap`. The existing
`data/positions/h7_positions.csv` remains an owner-edited legacy mirror until
Stage 5 reconciliation, never a competing source of truth for Stage-4 state.
For events without a new market-data observation, `owner_approval` copies the
entry intent's decision session; `recorded_at_utc` remains the authoritative
approval time. Entry/exit fills use the fill session, and skips/data gaps use
the session that caused the refusal.

## 4. Stage boundary and frozen entry rules

Stage 4 enforces one open position per symbol/lane from ledger-derived state.
The global one-position-per-underlying rule, basket-wide H7c concurrency, and
monthly sleeve accounting are Stage 5 book-level responsibilities; Stage 4
must not partially reimplement them. Board order remains chronological, then
`H7_LANE_PRIORITY` a>b>c, then `H7C_TIEBREAK` credit-to-width, then symbol
(`resolve_board`, unchanged). Earnings: `H7_EARNINGS_BAN_SESSIONS=5`
pre-report entry ban; unknown next report = no entry (fail closed). Structure
selection, delta/DTE bands, and admission gates remain the registered
`config.py` H7 block with `H7_DELTA_TOLERANCE=0.07` everywhere.

The Stage-4 lifecycle starts from an already-resolved candidate and records
its transitions; it does not change `resolve_board` or wire a new live watcher
path. Until Stage 5 supplies ledger-derived book inputs to the board, every
Stage-4 exercise uses synthetic upstream source-health/data-gate/board events.

## 5. Exit triggers and precedence (already frozen)

Long lanes (a/b): TP at `H7_LONG_TP_PCT=+100%` (single) /
`H7_SPREAD_TP_FRAC_MAX=75%` of max value (spread); time exit
`H7_CLOSE_AT_DTE=30`. H7c: TP buy-back at `H7C_TP_FRAC=50%` of credit;
stop when EOD conservative buy-back mark ≥ `H7C_STOP_CREDIT_MULT=2.0`×
credit (v1.2(5) realized-exit semantics); hard close at
`H7C_CLOSE_AT_DTE=7`; `H7C_CLOSE_BEFORE_EARNINGS=True` — closed by the
last session before any scheduled report, always.

Positions close **in full** (contracts=1 proposal below makes partial
exits moot), so when multiple triggers fire on the same session the only
thing precedence decides is the **recorded reason** — which matters
because Stage 6 scores per-reason cohorts. The owner already froze this order
in `ledger/facts.log` (`H7_OWNER_DECISIONS_7B01`), and
`strategies.h7_backtest.EXIT_PRIORITY` implements it:

`pre_earnings > earnings_unknown > scheduled_dte > underlying_stop > credit_stop > profit_target`.

Stage 4 reuses that exact order. It does not propose or tune a replacement.

## 6. Decision inventory — one proposed new parameter

Most apparent “parameters” in the first draft are already ratified causal or
execution rules. Only forward paper size needs a new config value.

| Rule / constant | Value | Status |
|---|---|---|
| Intent validity | exactly T+1 or expire | Already frozen by the roadmap's T+1 + cancel-never-chase contract; derive from the trading calendar, not a tunable. |
| Approval cutoff | T+1 XNYS close | Causal-integrity rule; compare the ledger's system-written `recorded_at_utc` with `session_close_utc(T+1)`. Do not trust caller-supplied `occurred_at_utc` for the cutoff. |
| Exit approval | none; exits mechanical | Structural invariant, not a config switch. Stage 4 adds no discretionary exit reason to the verdict path. |
| Exit reason precedence | existing frozen order in §5 | Reused owner decision; implementation should expose one shared source without changing the order. |
| `H7_FORWARD_CONTRACTS` | **proposed `1` per position** | The sole LLM-proposed new value. Minimal paper size; Stage 5 enforces `H7_MONTHLY_AT_RISK`. Owner must type/ratify it before implementation. |

## 7. Idempotency and payload contract

- Event IDs are deterministic from the hypothesis, transition, decision/fill
  session, symbol, lane, and parent intent/fill ID — never from wall-clock
  time. Re-running a completed session must reproduce byte-identical logical
  events and hit Stage 3's idempotent no-op; different content under the same
  ID must fail closed.
- For mechanical market-data events, `occurred_at_utc` is the deterministic
  XNYS close of `evaluation_session`; `recorded_at_utc` records when the append
  actually happened. Owner approval is the exception: its recorded time is
  the anti-backdating cutoff evidence; the production approval path must use
  the ledger's system clock, never a caller-supplied timestamp.
- Every intent/fill payload records the exact contract legs (expiration,
  strike, right, side, quantity), whether the fill opens or closes, relevant
  decision/fill sessions, raw bid/ask per leg, adverse per-leg prices,
  haircut, commissions, net debit/credit,
  trigger/revalidation reasons, and upstream chain/closes identity. Stage 4
  must not depend on prose or `facts.log` to reconstruct a position.
- The lifecycle API verifies and replays the ledger before every transition.
  Derived state is a projection of verified events, never a second mutable
  book file.

## 8. Activation guard (structural, not procedural)

Stage 4 exposes no production CLI and accepts no implicit/default ledger path.
Its build-only API requires an explicit injected synthetic store and refuses
any path resolving to the real `ledger/h7_forward/` directory
unconditionally. Stage 8 is the separately authorized change that may add a
production entry point after defining and verifying the exact activation
record. Stage 4 must not invent a vague “activation fact exists” check before
that record's schema is frozen.

## 9. Pre-registration procedure (before any implementation)

1. Owner reads this corrected spec and accepts/rejects
   `H7_FORWARD_CONTRACTS=1`.
2. Owner types the accepted value into `config.py` (implementation arc,
   test-first); the other §6 rows are invariant/reused rules, not new knobs.
3. A fact is appended: `H7_STAGE4_SPEC_PREREG <date>: spec sha256=<hash
   of this file at the signed-off commit>, parameter typed by owner:
   H7_FORWARD_CONTRACTS=<value>; reused causal/exit rules acknowledged.
   Implementation authorized; activation still Stage 8.`
4. Only then does the implementation arc open, on its own branch, with
   independent review before merge.

## 10. Acceptance criteria for the (future) implementation arc

Tests must prove, on synthetic stores: T-decision/T+1-fill causality
(fill never reads a session the decision already read); approval-cutoff
enforcement (late approval → skip, never a fill); intent expiry after
exactly T+1; ask/bid-side adverse transforms (haircut once) + commissions vs
hand-computed fixtures; every-leg liquidity refusal at entry fill; missing
entry quote expiry vs missing exit quote pending-retry; earnings hard-close
ordering vs the gating store; same-session multi-trigger reason precedence;
healthy no-entry vs true `data_gap`; every transition's event lands with the
§3 causes; deterministic rerun no-op and conflicting rerun refusal; full
position reconstruction from ledger events alone; the real store stays
untouched through direct and symlinked-path guard tests; `verify` green after
every synthetic sequence.

## Out of scope for Stage 4 (unchanged)

Sleeve/risk-cap enforcement (Stage 5), scoring (Stage 6), synthetic
dress rehearsal (Stage 7), activation (Stage 8), any real event, any
historical H7 backtest (permanently retired), live orders (never).
