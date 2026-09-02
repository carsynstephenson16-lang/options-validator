# A2-v1 entry-convention validation

Date: 2026-08-15

This implementation report records the pre-result validation surface for the
owner-approved A2-v1 entry convention. It is not a historical result and does
not append a fact, ledger record, or report artifact.

## Frozen evidence

- Registration: ledger sequence 19, record hash
  `684b59a2bf322a96ae375cd7b857706775eea2b971ffc456a4b09f40cb0383a2`.
- Existing pin: `RQ2_A2_PIN_ADDENDUM_V1`.
- New fact token required by the controller:
  `A2_ENTRY_CONVENTION_ADDENDUM_V1`.
- The controller requires the new fact to cite this report path exactly.

The exact one-line fact payload to be appended by the owner-gated run step is:

```text
A2_ENTRY_CONVENTION_ADDENDUM_V1 owner-approved 2026-08-15 source=reports/2026-08-15-a2-entry-convention-validation.md status=historical-entry-convention-complete research-only=no-verdict
```

That payload is intentionally not appended during Task 3 implementation.

## Implementation checks

The runner validates governance before invoking any cache loader, refuses an
existing report before governance unless `--append-result` is explicit, and
allows publication retry only after re-validating the existing report hash and
the governance evidence. It writes canonical JSON with exclusive create and
fsync, then verifies the report hash before any retrospective-result append.

The local loader accepts explicit absolute overrides for chains, underlying
closes, features, rates, earnings, and positions. It applies adjusted-close
conversion locally, resolves matched-tenor Treasury rates through the
point-in-time rate loader, validates the canonical earnings store with its raw
lineage, and keeps generic positions as PMCC `no data`. It loads only local
files, applies `config.BACKTEST_END`, and refuses ranking reconstruction when
FOMC provenance is unavailable rather than awarding an empty-calendar badge.

The tracked `data/events/fomc_dates.csv` is a legacy dates-plus-source-URL
calendar without `known_as_of_utc` provenance. It is insufficient for the
governed run. Task 3 therefore requires an explicit local provenance-bearing
FOMC artifact and keeps the governed run **BLOCKED** until that artifact is
owned and reviewed.

The report carries all five lane statuses, every registered CSP arm and
LEAPS/tactical horizon, complete-fifteen-name inference exclusions, separate
staggered descriptive counts, cost stresses, provenance/max-as-of values,
fourteen audit checks, and an explicit unsupported-forward-fields list. No
forward verdict is serialized.

## Execution boundary

Task 3 stops before the governed historical invocation. The owner-approved
fact append, adversarial review receipt, data audit, realism audit, one-shot
historical run, retrospective append, and statistical red-team are subsequent
owner-gated steps.
