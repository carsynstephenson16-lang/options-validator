# H7 Schwab v2 arming-bottleneck design

Status: design only; unregistered, inactive, not verdict-bearing, and not authorized for experiments or authority activation.

## v1 decision

The repaired primary-source earnings rerun produced 4 full-stack passes over the fixed 1,050 symbol-day census, for 4.0 projected entries over 70 sessions. Because `4.0 < 20`, `h7-forward-schwab-v1` registration and authority work is **STOPPED**. The v1 universe, strategy rules, thresholds, costs, scorer, earnings gate, liquidity gate, ledgers, and authority flags remain unchanged.

Evidence: `reports/h7_forward_schwab/2026-08-11-feasibility-primary-earnings.json`.

## Separately versioned v2 design

Any future work must use a new `h7-forward-schwab-v2` identity and a separately frozen entry-stack version. It must not reinterpret or overwrite the v1 result.

The first v2 step is a read-only arming waterfall over a predeclared cached-data window. For every symbol-day and lane, it would count the first blocking condition in the unchanged causal order and retain a non-overlapping census for:

1. source/timing/data completeness;
2. earnings gate;
3. options liquidity gate;
4. lane-specific technical arming rule;
5. cost and max-loss feasibility;
6. board allocation and portfolio caps.

The earnings and options-liquidity gates are hard constraints and are not candidates for relaxation. The waterfall exists only to identify whether the remaining starvation is concentrated in entry logic, costs, or board allocation. Any proposed entry-logic change must then be written as a distinct v2 preregistration with its own frozen parameters, feasibility gate, rejection criterion, and multiple-testing count before a single v2 experiment is run.

No v2 variants, counterfactuals, thresholds, backtests, or experiments were run for this design.
