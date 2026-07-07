---
name: ledger-discipline
description: Enforce pre-registration and experiment-ledger logging. Use before running ANY backtest (check a pre-registration exists), after ANY backtest completes (append the result), whenever a parameter/rule/date-range/ticker change is proposed, and whenever a result is discussed that has no ledger entry.
---

# Ledger Discipline

The repo's core integrity mechanism is the append-only, hash-chained experiment ledger with pre-registration and frozen parameters. This skill makes the agent enforce it instead of hoping to remember it. This skill does not define a new ledger format — it enforces the one the repo already implements. If skill and code disagree, the code's format wins; flag the disagreement.

## Before any backtest run

1. Confirm a pre-registration entry exists for this exact configuration. Required fields: strategy name and version; tickers; entry rule; exit rule; expiration range; strike/delta selection; earnings/event handling (hold through, exit before, or skip entry — must be explicit); max loss per trade; capital assumption; liquidity filter; fill/slippage/commission assumptions; test window and out-of-sample split; the numeric result that REJECTS the idea; the numeric result that justifies more testing.
2. If any field is missing: stop. Fill it in WITH Carsyn, then run. Never fill in rejection criteria after seeing results.
3. If this configuration differs in any way from a previously registered one, it is a NEW hypothesis version (v2, v3...). Log it as such with a one-line reason. There is no such thing as "just tweaking" — a tweak after seeing results is the definition of overfitting.

## After any backtest run

4. Append the result to the ledger immediately, before discussing it, including failed and boring runs. Unlogged negative results are how selection bias enters: if only winners get written down, the ledger lies.
5. The entry records: config hash/version, data audit verdict, realism grade, raw result, and the pre-registered decision it triggers.

## Standing rules

6. If Carsyn (or the agent) proposes changing a frozen parameter mid-test: allowed only as a new logged hypothesis version. Say this plainly, once, without lecturing, then do the logging.
7. If a result is being discussed and no ledger entry exists for it, that's a break in the chain — reconstruct and log it before drawing conclusions.
8. Count and surface the running total of hypothesis versions tried per strategy. This number is the multiple-testing denominator results-red-team needs. Ten versions tried means a "significant" result was found in ten tries — say so.
