---
paths:
  - "strategies/**"
  - "harness/**"
  - "metrics.py"
  - "config.py"
  - "tests/**"
---

# Backtest engine and metrics rules

- The hard research guardrails (no look-ahead, conservative fills, costs,
  liquidity, EOD gaps) are in `.cursorrules` and load in every session.
- **Do not build further on the engine until the P0 defects are closed.** The
  open list with code line references is
  `reports/strategy-evaluations/12_review_of_the_two_landed_commits.md`;
  the tracked fix plan is the P0 section of `PROJECT_STATE.md`. Headlines:
  the $600 cap is checked on decision day but realized at fill-day prices (F1);
  `entry_date` silently became fill-day and feeds verdict cohorts (F2); an exit
  trigger on a chunk's last session crashes the year-end guard (F3);
  `return_on_economic_max_loss` still divides by the MEAN economic max loss
  (F4); `_max_drawdown` has no ordering contract (F5).
- Every frozen number in strategy logic comes from `config.py` and is
  owner-typed or carries the "owner-delegated standing 2026-07-25" amendment
  provenance. `BACKTEST_EXECUTION_CONVENTION` is currently UNREGISTERED
  (report 12 F6) — do not cite it as owner-typed.
- Tests are `unittest`, offline-only, against the local parquet cache. A test
  that holds decision and fill quotes equal cannot detect cap drift — when
  touching sizing or fills, add a drifted-quote case.
- The verdict gates on losses, cohorts, and the bootstrap CI. Capital-use
  ratios are descriptive only; never promote or reject a hypothesis on them.
