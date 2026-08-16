# A2-v1 pre-run options-data audit — 2026-08-15

**Status:** **BLOCKED — audit did not complete; do not run A2 historical.**

This is the required dry pre-run audit attempt. It did not call `run_once`,
write `reports/a2/a2-v1.json`, or append a fact or ledger record.

## Data audited

The requested local inputs were supplied as absolute paths:

- chains: `/Users/carsynstephenson/options-validator/.cache/chains`
- underlying: `/Users/carsynstephenson/options-validator/.cache/underlying`
- features: `/Users/carsynstephenson/options-validator/.tmp/research/attractiveness`
- rates: `data/rates/`; earnings: `data/earnings/gating_v3.csv`; positions:
  `data/positions/positions.csv`; FOMC: `data/events/fomc_pit.csv`

The intended eligible universe was all 15 registered A2 names: AMD, AMZN,
AVGO, CEG, CRWV, ET, IREN, MSFT, NOW, NVDA, PLTR, SMCI, TEM, USAR, and VST.
The common feature start is **2025-04-07** and the requested hard end is
`config.BACKTEST_END = 2026-06-30`.

Filename-only cache inventory found 309 chain parquet files for every name:
4,635 files in total, each spanning 2025-04-07 through 2026-06-30. A direct
chain-bundle diagnostic successfully read 4,635 frames / 9,970,173 rows in
about 34 seconds. The underlying cache has all 15 name files (339 to 2,409
raw-close rows per name); the feature cache has all 15 name files (327 to
2,152 feature rows per name). These are scope observations, not a completed
data-quality verdict.

## Audit execution and blocker

The mandated sequence was attempted with `MPLCONFIGDIR=/private/tmp/a2-audit-mpl`
and `PYTHONDONTWRITEBYTECODE=1`:

1. `CachePaths.from_overrides(...)` with the paths above;
2. `_load_local_inputs(paths)`;
3. fresh `A2Diagnostics`, `build_historical_outcomes(...)`; and
4. `audit_historical_inputs(...)` scoped to `diagnostics.selected_contracts`,
   the 15-name universe, common start, and `BACKTEST_END`.

The full `_load_local_inputs` attempt terminated before it returned a local
input object or emitted its completion marker. A staged repeat reached
`STAGE chains 2025-04-07` and then terminated before `STAGE chains_ok`; no
Python exception or check output was emitted. The independent chain-only read
above completed, so this receipt does **not** attribute the failure to a
specific malformed contract or claim an out-of-memory cause without evidence.

Wall time recorded for the successful direct chain-bundle diagnostic was about
34 seconds. The full-loader attempts returned without a completion payload, so
there is no valid end-to-end audit wall time, selected-contract count,
signal/outcome count, or skip counter to report.

## Failed checks

Checks 1 through 14 were **not executed**. No printed check count is available
for any check because `audit_historical_inputs(...)` was not reached. Treating
these as zero issues would be false; their status is `NOT RUN`.

| Check | Status |
| --- | --- |
| 1–14 | NOT RUN — required local-input loader did not complete |

## Warnings

No strategy-selected contracts exist for this audit attempt because outcome
construction did not run. Therefore there are no representative warning rows
or selected-contract failure rows to report. The representative failure is the
loader-stage termination described above, not a chain-data finding.

## Verdict

**BLOCKED.** The programmatic audit has not produced its required fourteen
counts or a `PASS`, `PASS WITH WARNINGS`, or `BLOCK` result. Historical A2
execution remains prohibited until the full loader completes and the
programmatic audit runs against actual selected contracts. If that audit later
returns `BLOCK`, stop on its exact selected contract rows and record the data
decision rather than selectively excluding them.

## Ledger note

`A2-v1 pre-run options-data audit BLOCKED 2026-08-15: required full local-input loader did not complete after chain-stage entry; checks 1-14 NOT RUN, no selected-contract verdict; do not invoke historical A2.`
