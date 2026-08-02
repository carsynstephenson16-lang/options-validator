# 16 — P0 cap enforcement and execution-convention closeout

**Date:** 2026-07-31
**Implementation:** `a48a7fd`
**Typed registration:** `ledger/experiments.jsonl` seq 21,
record `a540a074df29704b25d554ccb0efa31c6c963c1e35e6cf4144f3daa986fb89e8`

## Owner decisions implemented

- OD-A: cancel when D+1 net credit is more than $0.01 below the day-D signal;
  at the allowed boundary, reduce quantity only when the actual permitted fill
  would otherwise exceed the hard $600 economic-max-loss cap.
- OD-B: keep `D_PLUS_1_CLOSE`; `entry_date` is the fill session;
  `entry_decision_date` is retained; a final-session exit with no later engine
  iteration is labeled `terminal_conservative_mark` and uses that session's
  conservative executable mark.

The legs, direction, expiration, and maximum quantity remain frozen on day D.
D+1 may only fill the exact intent, reduce quantity, or cancel it. It may not
reselect or increase exposure.

## Why the hybrid was used

Pre-sizing every intent at signal credit minus $0.01 would cut a canonical
four-contract $0.53 signal to three contracts even when D+1 credit improves: a
25% exposure haircut unrelated to realized adverse movement. The hybrid avoids
that distortion while making the $600 ceiling invariant at the permitted fill.

Lumibot's official documentation says a multi-leg SMART_LIMIT can fill
atomically as a package, but its backtest price is net midpoint plus/minus
slippage. That would replace this repository's registered conservative
bid/ask-plus-haircut model, not merely enforce a $0.01 floor. Therefore it was
not adopted for this repair:

- <https://lumibot.lumiwealth.com/smart_limit.html>
- <https://lumibot.lumiwealth.com/entities.order.html>

## Test-first evidence

Before implementation, the new causal-fill tests failed on the $0.50→$0.35
audit case, a two-cent adverse move, the one-cent resize boundary, absent
constants, and provenance expectations. After implementation:

- `$0.50 → $0.35`: canceled; no over-cap position.
- `$0.53 → $0.51`: canceled because the move is worse than $0.01.
- `$0.53 → $0.52`: allowed, but resized from four to three contracts because
  four would carry $602.40 of economic max loss.
- Exact cent comparison is normalized before gating, avoiding binary-float
  rejection of `0.519999...` at the permitted $0.52 boundary.
- A separate regression fixes the stale scoreboard label to say total P&L /
  total economic max loss.

Validation: 2,236 offline unit tests passed; Ruff passed; Pyright reported zero
errors and warnings. The real H7 scoring-store test passed after confirming
that Strategy A's execution policy is config provenance, not part of H7's
registered shared cost-model identity.

## Dataset-wide cap audit

Read-only scan of every cached in-sample Strategy A chain day in
2018-01-01..2022-12-31 for MSFT/AMZN/VST/CEG, using the production selector,
XNYS next-session map, exact frozen strikes/expiration, production conservative
entry credit, and production economic-risk sizing:

| Measure | Result |
|---|---:|
| Cached chain-days | 4,002 |
| Day-D accepted candidates at configured $2 width | 192 |
| Canceled beyond $0.01 tolerance | 102 |
| Allowed D+1 fills | 89 |
| Allowed fills requiring resize | 0 |
| Exact frozen leg unavailable on D+1 | 1 |
| Worst old-policy cap breach | **$505.80** ($1,105.80 modeled risk) |
| Worst new-policy cap breach | **$0.00** |
| Highest new-policy allowed risk | **$556.80** ($43.20 below cap) |

The worst old-policy case was MSFT decision 2018-10-23 / fill 2018-10-24:
signal credit $0.35, D+1 executable credit −$1.66, three frozen contracts.
The new tolerance gate cancels it.

## Registered-hypothesis preservation

`FILL_MODEL_ID` remains `conservative_bid_ask_plus_haircut_v1`; the underlying
quote-side fill model did not change. H6 snapshots that identifier, so keeping
it fixed avoids an unreviewed H6 amendment. H7 binds the shared
`cost_model_hash`; the Strategy A-only execution fields are deliberately
excluded from that shared hash and included by the all-uppercase `config_hash`
instead. Targeted real-store tests and the full suite confirm both registered
identities remain usable.

Seq 21 scopes the convention to future `PutCreditSpread` backtests. It states
that no H1/H2 result and no registered H6/H7/H8 semantic is retrofitted or
amended. It is a methodology registration only: no backtest, result, OOS
reveal, or verdict was produced. The typed API conservatively advanced the
trial count from 21 to 22.

## Limitations

The dataset audit is a mechanical entry-path replay, not a new strategy
backtest and not evidence of edge. It reads in-sample cache only, does not
simulate exits or P&L, and does not touch the OOS holdout. The single missing
D+1 frozen leg remains a loud fail-closed engine path rather than a modeled
fill. No claim is made about live broker atomicity; this repository remains an
offline validator with no live-order path.
