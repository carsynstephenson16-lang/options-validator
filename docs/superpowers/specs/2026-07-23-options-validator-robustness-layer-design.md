# Options-validator robustness layer — design

**Date:** 2026-07-23
**Status:** implemented, research-only
**Scope guard:** moves registered RQ2/A2 validation toward their declared
verdicts without changing the frozen scanner recipe, production ranking,
ThetaData, Lumibot, order handling, portfolio accounting, or deployment.

## Decision

Add a small clean-room subsystem under `options_researcher/robustness/`. It
operates only on already-stored, point-in-time panel rows. Fast screening is a
pure calculation; Lumibot remains the event-driven engine and can receive only
explicit finalists through the `LumibotFinalistAdapter` protocol.

The subsystem never imports into `options_researcher.attractiveness`,
`attractiveness_dashboard`, the H7 path, strategies, or the backtest harness.
The frozen GREEN recipe and current ranking therefore remain unchanged by
default and by module dependency.

## Architecture

1. `models.py` — frozen `ExperimentSpec`, canonical JSON, config hash, stable
   run ID, date-window validation, owner-field validation, and ledger
   registration check.
2. `walk_forward.py` — expanding or rolling observation windows over actual
   panel dates. Sparse dates and holidays are represented by the dates that
   exist; no synthetic sessions are inserted. Forward-label observations are
   purged before every test range, and each test range exposes its embargo.
3. `screening.py` — lane-isolated top-minus-bottom bucket forward
   cost-adjusted return spread. Parameter variants are precomputed panel rows,
   evaluated deterministically, and optionally evaluated with bounded workers.
4. `statistics.py` — seeded circular block permutations, finite-sample
   empirical p-values `(extreme + 1) / (B + 1)`, effect size, null interval,
   and Holm step-down adjusted p-values.
5. `stability.py` — neighboring-parameter performance, fold rank stability,
   sign consistency, OOS decay, ticker/regime concentration, minimum counts,
   cost stress, and isolated-peak brittleness. These remain separate
   diagnostics; no invented composite weight exists.
6. `registry.py` — standard-library SQLite with `PRAGMA user_version`,
   deterministic JSON payloads, idempotent replay, conflicting-checkpoint
   refusal, corrupt/future-schema rejection, and UTC timestamps.
7. `runner.py` — fold/parameter orchestration and resumable task writes. The
   runner performs no network calls and does not construct ThetaData or broker
   clients.
8. `reporting.py` — atomic JSON, CSV, and Markdown outputs. Every report says
   `RESEARCH-ONLY`, carries claim/provenance fields, and withholds a production
   recommendation.
9. `cli.py` — `doctor`, `run`, `resume`, `report`, and `list`.

## Leakage and governance controls

- Specification windows must be strictly ordered and non-overlapping.
- `purge_observations >= forward_outcome_horizon`.
- Walk-forward folds are chronological; random train/test split is absent.
- The dataset SHA-256, point-in-time cutoff, exact Git SHA, lane, and parameter
  IDs are checked before execution.
- `status=registered` is insufficient by itself: a matching hash-chained
  ledger `run` or `trial_intent` record must exist.
- RQ2 owner controls are explicit: tercile count, adverse bottom-bucket
  minimum, Holm sidedness, and forward backstop. Missing values block.
- Rows from more than one lane or parameter variant cannot enter one primary
  metric.
- Raw and Holm-adjusted p-values are stored separately.
- The adverse-count gate and every promotion gate are stored. Production
  promotion is always `BLOCKED` here; owner action remains outside the runner.
- Historical panels are exploratory. A production verdict still requires the
  registered forward window and calendar backstop.

## Primary metric

Within each date and lane, candidates are sorted by the precomputed variant
score. For the registered `bucket_count=3`, the top third and bottom third are
formed separately. The primary metric is:

`mean_date(mean(top forward cost-adjusted return) - mean(bottom forward cost-adjusted return))`

Dates without enough names for one complete bucket are omitted, not padded.
The stored top/bottom counts make this refusal auditable.

## Checkpoint and report contract

The registry has two tables:

- `runs`: immutable experiment identity, hashes, Git SHA, seed, lane, status,
  UTC timestamps, claim label, and canonical specification.
- `tasks`: one `(run_id, fold, parameter_id)` row with metrics, raw/adjusted
  p-values, gate outcomes, errors, artifact paths, and a payload digest.

An identical write is an idempotent no-op. A different payload for the same
task raises `CheckpointConflictError`; it is never silently overwritten.
SQLite transactions protect each write. JSON/CSV/Markdown files are written
to a same-directory temporary file, fsynced, and atomically replaced.

The full field dictionary is in
`docs/robustness-experiment-data-dictionary.md`.

## External reference attribution

Reference repository:
`coding-kitties/investing-algorithm-framework`, release `v8.10.0`, resolved
commit `63483bdaa2a0defb644b6851407529d8ee6c63d5`.

Reviewed concepts and source:

- rolling windows:
  `investing_algorithm_framework/analysis/backtest_data_ranges.py`;
- checkpoint identity/validation:
  `infrastructure/services/backtesting/checkpoint_manifest.py`;
- permutation-test organization:
  `domain/backtesting/backtest_permutation_test.py`;
- multi-metric comparison:
  `analysis/ranking.py`;
- compact SQLite indexing:
  `services/backtest_index/sqlite_index.py`.

No source code was copied or adapted. The implementation uses the concepts
only, is fitted to this repository's existing ledger and outcome rules, and
uses different models, APIs, schemas, null method, governance checks, and
reports. Therefore no Apache-2.0 notice addition is required.

## Explicit exclusions

- external order or portfolio engine;
- broker and exchange adapters;
- live or paper deployment infrastructure;
- market-data providers;
- generic event backtester;
- the external dependency tree;
- web dashboard;
- cloud scaffolding;
- external framework installation or vendoring.

Lumibot and ThetaData remain the existing event engine and options provider.

## LSE comparison and retirement

The LSE item was `lse-data` by London Strategic Edge, an isolated data-feed
probe, not a validation framework. It is not an alternative to this layer.
The measured feed had no option bid/ask/open interest, no point-in-time chain
history, and returned stale expirations. It could not satisfy the frozen
liquidity, fill, or causal-backtest rules.

The disposable `test_lse_feed.py` probe and its ignored 126 MB `lse_env/`
were removed. `lse-data` was never in `pyproject.toml` or `uv.lock`, so no
production dependency or code path changed. The committed assessment remains
at `reports/2026-07-23-lse-feed-assessment.md` as audit provenance.

## Known limitations

- The fast evaluator expects variant scores and forward cost-adjusted outcomes
  to have already been built correctly. It validates identity and ordering,
  not the upstream financial label formula.
- Block length is conservatively at least the forward horizon, but this is not
  a substitute for a registered dependence study.
- Parameter neighbors are declared by the tested grid; irregular grids need
  meaningful parameter IDs and deliberate neighbor construction.
- Thread workers accelerate pure parameter evaluation only. SQLite writes
  remain single-process and deterministically ordered.
- Finalist handoff is a narrow protocol seam. A concrete lane-to-Lumibot
  adapter should be added only with that lane's registered execution brief.
