# H7 Stage 6 — forward-window scoring: SPEC

**Status: PRE-REGISTRATION CANDIDATE. BUILD-ONLY, SYNTHETIC-ONLY, INACTIVE.
This stage defines and implements the frozen scoring procedure before any
forward entry. It has no CLI, accepts only an explicit synthetic Stage-3
ledger directory, creates no event, and cannot register or activate a window.
Stage 8 remains the only owner activation gate.**

Ratified roadmap contract:

> The forward window's verdict machinery, pre-registered BEFORE the first
> entry: expectancy per trade after costs with bootstrap CI, verdict gating on
> `MIN_LOSSES_FOR_VERDICT` losses, per-lane cohorts, benchmark columns
> (underlying move alongside every trade). Vocabulary stays frozen: survived /
> rejected / inconclusive.

## 1. Authority, bounds, and completeness

The verified Stage-3 event ledger is the sole trade source. The scorer takes
an explicit synthetic ledger directory plus `window_start` and `window_end`
decision sessions. Those dates are test inputs in Stages 6–7; only a future
Stage-8 registration may make them operational or verdict-bearing.

The cohort contains every opening `paper_fill` whose immutable
`decision_session` is within the inclusive bounds. It is never selected by
symbol, lane, outcome, exit reason, entry date, or availability. Every
included opening fill must have exactly one causally valid closing fill; an
open/pending included position makes the score incomplete and fails closed.
Skipped entry intents remain ledger evidence but are not trades.

The scorer verifies and semantically replays the ledger before calculation.
It records the verified ledger head and window bounds in its returned object.
It writes nothing and exposes no incremental/peek verdict path.

## 2. Trade economics after costs

For quantity `H7_FORWARD_CONTRACTS`, each closed trade is reconstructed from
the opening and closing fill payloads:

`pnl = (exit_net_close_credit - entry_net_debit) * 100 * quantity
       - entry_commission - exit_commission`

The sign convention works for long debit positions and lane-c credits because
opening credits and closing debits are negative net debits/credits. The scorer
uses the opening fill's actual `at_risk` as both `capital_at_risk` and
`economic_max_loss`, and refuses missing, boolean, non-finite, non-positive,
or inconsistent numbers. It does not re-price trades from current market data.

## 3. Benchmark columns

Every opening and closing fill must commit the adjusted underlying close for
that exact fill session. Each reconstructed trade carries:

- `underlying_entry_close`
- `underlying_exit_close`
- `underlying_move` = exit minus entry
- `underlying_return` = exit / entry minus one

Missing, non-finite, non-positive, or session-mismatched benchmark data fails
closed. The benchmark is descriptive and never changes the strategy verdict.

## 4. Score and confidence interval

Stage 6 reuses the repository's dependence-aware `metrics.scoreboard` without
an IID fallback. Thus the headline is mean expectancy per trade after all
recorded costs, with the existing 90% weekly-cohort block/stationary-bootstrap
envelope using frozen `BOOTSTRAP_SAMPLES=5000` and seed 42. The result includes
the full overall scoreboard and one scoreboard for each lane `a`, `b`, and
`c`, including empty lanes; all trade rows are returned in deterministic
entry-session/symbol/lane/position order for audit.

## 5. Frozen forward verdict mapping

Each overall/lane scoreboard maps to exactly one public verdict:

- fewer than `MIN_LOSSES_FOR_VERDICT=10` losses, or fewer than the scoreboard's
  required entry-week cohorts → `INCONCLUSIVE`, with the specific gate reason;
- CI90 entirely below zero → `REJECTED`;
- CI90 entirely above zero → `SURVIVED`;
- CI90 touching or spanning zero → `INCONCLUSIVE` (`no_edge`).

`SURVIVED` means only that this registered forward paper cohort did not reject
the lane; it is not approval, validation, a live-trading authorization, or a
claim of future profitability. No alternate vocabulary is emitted.

## 6. Determinism and look control

The scorer is a pure read: same verified ledger head, bounds, config, and code
produce canonical-equal results. Changed event content is already prohibited
by the Stage-3 chain. Stage 6 does not append score snapshots because repeated
pre-window peeks would create an unregistered sequential-testing surface.
Stage 8 must bind one registered final scoring call to the registered window
and decision procedure; that authorization is explicitly out of scope here.

## 7. Acceptance tests

The implementation is complete only when tests prove:

- debit and credit PnL signs, all commissions, quantity, and actual at-risk;
- exact inclusive decision-session cohort selection with no cherry-pick seam;
- strict one-open/one-close causal reconstruction and incomplete-window refusal;
- entry/exit benchmark columns and malformed benchmark refusal;
- overall plus lanes a/b/c, all three verdicts, the loss/cohort gates, exact
  frozen vocabulary, deterministic trade order, and deterministic reruns;
- no ledger/CSV mutation, explicit synthetic-path enforcement, and the real
  forward ledger remaining `VALID EMPTY`;
- focused tests, the complete suite, Ruff, Pyright, pre-commit, and independent
  review pass.

## 8. Stage boundary

Stage 6 does not run stages 1–6 end to end (Stage 7), choose or register window
dates/duration, authorize a first event, or activate any watcher (Stage 8).

