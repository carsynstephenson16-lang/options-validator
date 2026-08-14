---
name: ledger-discipline
description: Enforce pre-registration and experiment-ledger logging. Use before running ANY backtest (check a pre-registration exists), after ANY backtest completes (append the result), whenever a parameter/rule/date-range/ticker change is proposed, whenever a result is discussed that has no ledger entry, and when drafting a new hypothesis, forward-window registration, amendment, or owner registration packet.
---

# Ledger Discipline

The repo's core integrity mechanism is the append-only, hash-chained experiment ledger with pre-registration and frozen parameters. This skill makes the agent enforce it instead of hoping to remember it. This skill does not define a new ledger format — it enforces the one the repo already implements. If skill and code disagree, the code's format wins; flag the disagreement.

## Before any backtest run

1. Confirm a pre-registration entry exists for this exact configuration. Required fields: strategy name and version; tickers; entry rule; exit rule; expiration range; strike/delta selection; earnings/event handling (hold through, exit before, or skip entry — must be explicit); max loss per trade; capital assumption; liquidity filter; fill/slippage/commission assumptions; test window and validation design (legacy backtests: an IS/OOS split; the current norm: a declared forward-paper window with its loss bar); the numeric result that REJECTS the idea; the numeric result that justifies more testing.
2. If any field is missing: stop. Fill it in WITH Carsyn, then run. Never fill in rejection criteria after seeing results.
3. If this configuration differs in any way from a previously registered one, it is a NEW hypothesis version (v2, v3...). Log it as such with a one-line reason. There is no such thing as "just tweaking" — a tweak after seeing results is the definition of overfitting.

## After any backtest run

4. Append the result to the ledger immediately, before discussing it, including failed and boring runs. Unlogged negative results are how selection bias enters: if only winners get written down, the ledger lies.
5. The entry records: config hash/version, data audit verdict, realism grade, raw result, and the pre-registered decision it triggers.

## Before registering a new hypothesis or forward window

- Current registrations are forward-paper windows: a declared window, an entry
  stack, and a loss bar (a `MIN_LOSSES_FOR_VERDICT`-style constant in
  `config.py`, per hypothesis). IS/OOS-split fields belong to the legacy
  backtest shape only; do not demand them from a forward registration.
- The 2026-07-24 feasibility gate is a registration precondition: projected
  expected entries >= 2x the loss bar over the declared window, or the
  registration explicitly pre-accepts starvation risk quoting the computed
  number (`docs/superpowers/2026-07-24-registration-feasibility-gate.md`;
  Schwab-lane tool: `tools/h7_schwab_feasibility.py`).
- Provenance-label every number in a draft: owner-typed, owner-approved,
  LLM-proposed, or tool-computed. The owner types every frozen number and new
  registration. Leave owner-decision fields literally blank in drafts — never
  pre-fill a recommendation into an owner blank.
- A draft registration packet gets its own independent adversarial review
  before hand-off; drafting and reviewing are different sessions.
- Amendments to already-registered specs may be drafted and recorded by the
  implementing agent only after independent adversarial review and sign-off,
  carrying the provenance label "owner-delegated standing 2026-07-25"
  (CLAUDE.md, Division of labor). New registrations and frozen numbers are
  never delegated.

## Standing rules

6. If Carsyn (or the agent) proposes changing a frozen parameter mid-test: allowed only as a new logged hypothesis version. Say this plainly, once, without lecturing, then do the logging.
7. If a result is being discussed and no ledger entry exists for it, that's a break in the chain — reconstruct and log it before drawing conclusions.
8. Count and surface the running total of hypothesis versions tried per strategy. This number is the multiple-testing denominator results-red-team needs. Ten versions tried means a "significant" result was found in ten tries — say so.
