# H7 Stage 4 — T+1 paper lifecycle: SPEC + pre-registration proposal

**Status: SPEC ONLY. Owner authorized "spec + pre-registration first"
2026-07-12 (in-session answer). NOTHING in this document is implemented.
Implementation is a separate arc gated on (1) owner sign-off of this spec,
(2) the owner typing the proposed parameters into `config.py` themselves,
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
  `approval_late`).
- **Day T+2 run** computes the **paper fill at session T+1's recorded EOD
  quotes** for approved intents. The entry decision used only ≤T data;
  the fill uses only T+1's cached EOD chain. No intraday rows anywhere.
- **Exit triggers** are evaluated on each completed session T′ against
  the open book; a firing trigger emits `exit_intent` and the close fills
  at session T′+1 quotes, same mechanics. Exits are **mechanical — no
  owner approval** (a frozen trigger that waits for a human is no longer
  frozen; discretion re-enters). Owner retains a manual-close path: an
  owner-initiated `exit_intent` (reason `owner_close`) that fills T+1
  like any other.

## 2. Fill mechanics (existing guardrails, bound not restated)

- Quote source: the cached EOD chain parquet for the fill session
  (ThetaData 17:15 ET report; the same file the audit passed).
- Price: quote mid, then the canonical `adverse_buy`/`adverse_sell`
  transform (ceil/floor to cent), then `SLIPPAGE_HAIRCUT`.
- Costs: `COMMISSION_PER_CONTRACT` both legs each way + half-spread on
  each leg.
- Liquidity: `MIN_OPEN_INTEREST` and `MAX_SPREAD_PCT` re-checked on BOTH
  legs **at the fill session**, not just at decision time. A leg failing
  at fill → `skip` (reason `liquidity_at_fill`), intent dead.
- Missing/invalid EOD at the fill session (quote not finite/two-sided/
  uncrossed, or the whole day absent) → `data_gap` + `skip`; the intent
  **expires** — cancel-never-chase means no re-pricing at T+2. A fresh
  entry requires a fresh watcher decision.

## 3. Lifecycle state machine → Stage 3 events

| Transition | Event type | Required `causes[]` |
|---|---|---|
| Gate evaluated for the session | `data_gate` | — (first event of the session) |
| Source health snapshot | `source_health` | — |
| Board contention resolved | `board_resolution` | the session's `data_gate` |
| Candidate loses board seat | `lane_displaced` | the `board_resolution` |
| Watcher ENTRY-OK | `entry_intent` | `data_gate`, `board_resolution`, `source_health` |
| Owner approves | `owner_approval` | the `entry_intent` |
| Paper fill (entry or exit) | `paper_fill` | the intent + (`owner_approval` for entries) |
| Intent expiry / gate-fail / liquidity-fail | `skip` | the intent (+ the failing `data_gate` if any) |
| No-decision day | `data_gap` | — |
| Trigger fires on open position | `exit_intent` | opening `paper_fill` + the session's `data_gate` |

Every event's `evaluation_session` is the session whose data produced it;
`payload` carries the numbers (strikes, deltas, marks, costs). The book
state (open positions) is **derived by replaying the event ledger** — the
existing `data/positions/h7_positions.csv` stays the owner-edited mirror
the watcher reads (fail-closed), reconciled in Stage 5, but the ledger is
the source of truth for the forward window.

## 4. Entry rules already frozen (pointers)

One position per underlying (`H7_MAX_OPEN_PER_UNDERLYING=1`); one H7c
basket-wide (`H7C_MAX_CONCURRENT=1`); board order = chronological, then
`H7_LANE_PRIORITY` a>b>c, then `H7C_TIEBREAK` credit-to-width, then
symbol (`resolve_board`, unchanged). Earnings: `H7_EARNINGS_BAN_SESSIONS=5`
pre-report entry ban; unknown next report = no entry (fail closed).
Structure selection, delta/DTE bands, admission gates: the registered
`config.py` H7 block, `H7_DELTA_TOLERANCE=0.07` everywhere.

## 5. Exit triggers (frozen values; precedence PROPOSED below)

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
because Stage 6 scores per-reason cohorts. No precedence is frozen
anywhere today (verified: absent from config, code, and all H7 docs).

## 6. Proposed NEW parameters — owner types these; all LLM-proposed

Per the operating manual: these are proposals with reasoning, **not**
values I may freeze. Every one is `LLM-asserted` until you type it into
`config.py` in the implementation arc and the pre-reg fact records it.

| Proposed constant | Proposed value | Reasoning |
|---|---|---|
| `H7_T1_INTENT_VALID_SESSIONS` | `1` | Execute at exactly T+1 or die. Any longer window is chasing a stale signal — the roadmap's cancel-never-chase phrase made into a number. |
| `H7_T1_APPROVAL_CUTOFF` | T+1 XNYS session close | Blocks approval-selection bias (§1). An event timestamp, mechanically checkable at fill time. |
| `H7_EXIT_APPROVAL` | none (mechanical exits) | Frozen triggers must not wait on discretion; owner keeps the manual `owner_close` path. |
| `H7_EXIT_REASON_PRECEDENCE` | `earnings_close > stop > dte_close > take_profit` | Risk-driven reasons outrank profit-taking in cohort attribution: a trade that hit stop AND TP-mark on the same EOD is a stop for scoring honesty. |
| `H7_FORWARD_CONTRACTS` | `1` per position | Minimal paper size; sleeve math (`H7_MONTHLY_AT_RISK=6000`) is enforced at Stage 5 — Stage 4 should not embed sizing logic it can't yet reconcile. |

## 7. Activation guard (structural, not procedural)

The lifecycle runner refuses to write to the real store
(`ledger/h7_forward/`) unless a Stage 8 activation fact exists and is
verified — the same default-absent pattern Stage 3 shipped with. Tests
exercise everything on synthetic stores only. This guard is part of the
spec, not an implementation nicety.

## 8. Pre-registration procedure (before any implementation)

1. Owner reads this spec; edits/rejects any row of §6.
2. Owner types the accepted values into `config.py` (implementation arc,
   test-first).
3. A fact is appended: `H7_STAGE4_SPEC_PREREG <date>: spec sha256=<hash
   of this file at the signed-off commit>, parameters typed by owner:
   <the five values>. Implementation authorized; activation still Stage 8.`
4. Only then does the implementation arc open, on its own branch, with
   independent review before merge.

## 9. Acceptance criteria for the (future) implementation arc

Tests must prove, on synthetic stores: T-decision/T+1-fill causality
(fill never reads a session the decision already read); approval-cutoff
enforcement (late approval → skip, never a fill); intent expiry after
exactly `H7_T1_INTENT_VALID_SESSIONS`; adverse-transform + haircut +
commission + half-spread arithmetic vs hand-computed fixtures; both-leg
liquidity refusal at fill; earnings hard-close ordering vs the gating
store; same-session multi-trigger reason precedence; every transition's
event lands with the §3 causes; the real store stays untouched (guard
test); `verify` green after every synthetic sequence.

## Out of scope for Stage 4 (unchanged)

Sleeve/risk-cap enforcement (Stage 5), scoring (Stage 6), synthetic
dress rehearsal (Stage 7), activation (Stage 8), any real event, any
historical H7 backtest (permanently retired), live orders (never).
