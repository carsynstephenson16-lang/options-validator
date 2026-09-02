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

`A2-v1 pre-run options-data audit BLOCKED 2026-08-15: persistent streaming run completed 14 of 15 per-symbol audits before controlled stop; partial selected-contract check-10 IV failures=147, final merge/AMZN/exact contract rows unavailable; do not invoke historical A2.`

## Streaming-loader rerun at `2f36c7a`

The initial blocked attempt above predates the streaming refactor. At commit
`2f36c7a5fca6f15793aab9c5639867b3de990506`, the exact same absolute paths
were retried through the revised `_load_local_inputs(paths)` only. That code
loads and releases one ticker's chain bundle at a time, constructs its local
signals/outcomes, runs its per-symbol `audit_historical_inputs(...)`, and then
merges the fifteen audit results. `run_once` was not called.

The rerun command used the required cache-noise controls and printed the
intended audit payload only after `_load_local_inputs` returned:

```text
MPLCONFIGDIR=/private/tmp/a2-audit-mpl PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -c '<CachePaths.from_overrides with the paths above>; \
  inputs = _load_local_inputs(paths); print(audit/signals/outcomes/diagnostics)'
```

The first observation ended at the tool's 30-second output-yield boundary. It
was **not evidence that the loader terminated**. A persistent monitored
session was then used; its wrapper accumulated output until process exit, so
per-symbol prints were not visible to the intermediate monitor even while the
process was making progress.

| Rerun field | Result |
| --- | --- |
| Git HEAD | `2f36c7a5fca6f15793aab9c5639867b3de990506` |
| Input paths | Exact absolute paths listed above |
| Signal dates / rows | NOT AVAILABLE — final loader payload was not reached |
| Outcome rows | NOT AVAILABLE — final loader payload was not reached |
| Selected contracts | NOT AVAILABLE — final loader payload was not reached |
| Diagnostics skips / max-as-of | NOT AVAILABLE — final loader payload was not reached |
| Warnings | Partial per-symbol print only; no merged audit object |
| Checks 1–14 | Partial counts below; no final merged counts |
| Verdict | BLOCKED (incomplete required audit) |
| Rerun wall time | At least 15 minutes of active processing; manually stopped at the agreed monitoring limit before final merge |

### Persistent-session result

The persistent session ran `_load_local_inputs(paths)` for at least 15 minutes.
Before it was manually stopped to prevent further CPU burn, its buffered output
showed **14 completed per-symbol programmatic audits**. The fifteenth symbol
and `_merge_audits(...)` were not reached, so these are not a complete A2
verdict and must not be treated as one.

The partial aggregate of the 14 completed audit prints was:

| Check | Partial issue count | Interpretation |
| --- | ---: | --- |
| 1 | 0 | partial only |
| 2 | 14 | one cadence N/A note per completed symbol |
| 3 | 2 | partial only |
| 4 | 0 | partial only |
| 5 | 4,326 | volume metadata unavailable across 309 sessions per completed symbol |
| 6 | 0 | partial only |
| 7 | 0 | partial only |
| 8 | 0 | partial only |
| 9 | 4,326 | timestamp metadata unavailable across 309 sessions per completed symbol |
| 10 | 147 | invalid/missing IV observations on selected contracts |
| 11 | 0 | partial only |
| 12 | 0 | partial only |
| 13 | 4,326 | underlying-price metadata unavailable across 309 sessions per completed symbol |
| 14 | 0 | partial only |

Thirteen of the completed per-symbol audits printed `BLOCK`; one printed
`PASS WITH WARNINGS`. The audit implementation's selected-contract rule means
the concrete BLOCK rows must come from the final merged check records, which
were unavailable after the controlled stop. No exact-contract remediation is
therefore asserted here.

The corrected diagnosis is **execution-duration/output-observability**, not a
demonstrated loader crash or a completed data-quality result. The active
process was manually stopped after the 15-minute allowance; it did not emit a
normal final payload or exit code. A future attempt must complete all fifteen
per-symbol audits and the merge before any data verdict or historical A2
invocation is considered.

### Per-symbol partial order and check definitions

The completed audit prints follow the frozen A2 universe order. `AMZN` was the
fifteenth symbol and was still pending when the session was stopped.

| Completed symbol | Check 3 | Check 10 | Printed verdict |
| --- | ---: | ---: | --- |
| CRWV | 0 | 23 | BLOCK |
| TEM | 0 | 4 | BLOCK |
| PLTR | 1 | 6 | BLOCK |
| NOW | 1 | 1 | BLOCK |
| SMCI | 0 | 7 | BLOCK |
| NVDA | 0 | 11 | BLOCK |
| AMD | 0 | 16 | BLOCK |
| AVGO | 0 | 16 | BLOCK |
| IREN | 0 | 13 | BLOCK |
| USAR | 0 | 2 | BLOCK |
| ET | 0 | 34 | BLOCK |
| VST | 0 | 0 | PASS WITH WARNINGS |
| CEG | 0 | 3 | BLOCK |
| MSFT | 0 | 11 | BLOCK |
| AMZN | NOT RUN | NOT RUN | NOT RUN |

The implementation defines the relevant checks as follows:

- **2:** a per-symbol `weekly cadence N/A for A2 monthly/explicit-expiry
  selectors` record, plus any missing monthly expiration. The single result
  for each completed symbol was the N/A record, not a cadence failure.
- **3:** no finite strike within 10% of that session's independent raw close.
- **5:** missing/negative bid, ask, volume, or open interest. The 4,326 partial
  records are the generic `volume metadata unavailable` record for every
  completed chain session.
- **9:** absent/malformed/off-bar quote timestamp. The 4,326 partial records
  are the generic `missing timestamp` record for every completed chain session.
- **10:** selected contract has missing, non-positive, or greater-than-500% IV.
- **13:** missing independent close or missing/mismatched `underlying_price`.
  The 4,326 partial records are the generic `underlying_price metadata
  unavailable` record for every completed chain session.

Representative rows from the completed partial surface are:

| Check | Representative row / condition | Meaning for BLOCK |
| --- | --- | --- |
| 2 | `CRWV: weekly cadence N/A for A2 monthly/explicit-expiry selectors` | Informational N/A; generic text cannot match a selected contract identity. |
| 3 | `NOW 2025-12-18: no near-ATM strike`; independent close 153.3800, available strikes 280.0–340.0 | Generic session-quality warning; not itself a selected-contract identity. |
| 5 | `CRWV 2025-04-07: volume metadata unavailable` | Generic missing-column warning, repeated once per session; it is not a selected-contract failure. |
| 9 | `CRWV 2025-04-07: missing timestamp` | Generic missing-column warning, repeated once per session; it is not a selected-contract failure. |
| 10 | Partial print established 23 selected-contract IV failures for CRWV (147 across the 14 completed symbols), but contract identities were lost when the run was stopped before merge. | This alone is sufficient to explain every printed BLOCK, because it is selection-scoped. Exact contracts require a completed audit. |
| 13 | `CRWV 2025-04-07: underlying_price metadata unavailable` | Generic missing-column warning, repeated once per session; it is not a selected-contract failure. |

Accordingly, checks 5, 9, and 13 are implementation-multiplied generic
metadata warnings: they are emitted once for each chain session and cannot
match the selected-contract tag used by the audit's `BLOCK` decision. They are
not, on this partial evidence, the cause of a `BLOCK`. Check 10 is a confirmed
selection-scoped material issue; check 3 could also be selection-scoped when it
reports an invalid selected strike, but the available NOW example is generic
and the interrupted merge did not preserve the other exact check-3 row. The
completion requirement is exact selected-contract identities and values, not
selective suppression of generic metadata warnings.

### Exact CRWV selected-contract evidence

A bounded reconstruction of CRWV completed independently of the interrupted
fifteen-symbol merge: 309 chain sessions produced 259 signal days and 1,531
selected rows. Check 10 found exactly **23 selected-contract failures**: 21
with `iv = 0`, and two with `iv > 5`. This establishes a formal `BLOCK` on
actual selected contracts, regardless of the incomplete all-symbol aggregate.

Representative selected rows are:

| Session | Right / expiration / strike | Bid / ask / delta | IV | Other reported Greeks | Check-10 reason |
| --- | --- | --- | ---: | --- | --- |
| 2025-05-14 | C / 2025-05-16 / 45 | 21.60 / 23.10 / 1.0000 | 0 | vega=0, gamma=0, theta=0 | non-positive IV |
| 2026-04-17 | C / 2026-04-17 / 87 | 29.40 / 30.85 / 0.9670 | 8.2888 | — | IV exceeds 500% |
| 2026-04-17 | C / 2026-04-17 / 90 | 26.65 / 27.10 / 0.9953 | 5.0531 | — | IV exceeds 500% |

The alternate `chains_v2` corpus preserves the same invalid IV observations
and provides no repair: older required dates are absent, no alternate IV
column exists, and the implied-volatility solver is inadmissible for these
rows. Do not substitute that corpus or solve/fill IV values. The formal audit
result is therefore **BLOCK**, and historical A2 remains prohibited until the
selected-contract IV defects are resolved through a governed data decision and
a complete rerun produces the final merged audit.

The historical A2 command remains prohibited. The next safe step is to obtain
a completed programmatic streaming audit with its printed fourteen counts; it
is not permissible to treat this partial attempt as a warning-only pass or to
selectively exclude unknown rows.
