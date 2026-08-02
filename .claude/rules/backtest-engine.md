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
- P0.1-P0.6 and P0.8 are closed. The `$600` fill-day cap, fill-session
  `entry_date`, stable closed-trade drawdown ordering, terminal-exit exception,
  and same-session two-leg entry guard are implemented and tested. Report 12 is
  historical defect evidence; `PROJECT_STATE.md` is the current queue. The H6
  hard-kill proposal was reclassified as a prospective P2.5 amendment because
  the current code faithfully implements the registered rule.
- Every frozen number in strategy logic comes from `config.py` and is
  owner-typed or carries the "owner-delegated standing 2026-07-25" amendment
  provenance. The D+1 execution, fill-session date, terminal exception, and
  `$0.01` adverse-credit tolerance are registered in research-ledger seq 21
  (`record_hash` prefix `a540a074`).
- Tests are `unittest`, offline-only, against the local parquet cache. A test
  that holds decision and fill quotes equal cannot detect cap drift — when
  touching sizing or fills, add a drifted-quote case.
- The verdict gates on losses, cohorts, and the bootstrap CI. Capital-use
  ratios are descriptive only; never promote or reject a hypothesis on them.
