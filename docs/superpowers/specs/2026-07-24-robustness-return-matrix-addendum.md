# Robustness return-matrix addendum (2026-07-24)

**Status: observability addition only.** This addendum does not register a
new hypothesis, does not change the registered RQ2-v1/A2-v1 designs, does not
implement CSCV/PBO, and does not gate, grade, rank, or promote anything. It
extends the frozen `docs/superpowers/specs/2026-07-23-options-validator-robustness-layer-design.md`
design without editing it, following that document's own precedent for
addenda (see `docs/superpowers/2026-07-17-qm-dashboard-remediation-addendum.md`).

Provenance: owner-directed 2026-07-24. Design (capture point, schema,
literature mapping) LLM-drafted from a deep-research brief the owner
commissioned, covering Bailey & Lopez de Prado (2012, 2014), Bailey, Borwein,
Lopez de Prado & Zhu (CSCV / probability of backtest overfitting), Romano &
Wolf (2005), White (2000), Hansen (2005), and Harvey & Liu (2015). This
document and the code it describes were produced by a Claude Code
implementation agent following that brief; the owner has not yet reviewed or
ratified either.

## What is added

1. `options_researcher/robustness/return_matrix.py` — a new module that:
   - `ReturnMatrixWriter` accumulates, per experiment run, the per-day,
     per-parameter-variant OOS cost-adjusted spread series that
     `screening.cost_adjusted_primary_metric(...).daily_spreads` already
     computes inside `runner.run_experiment` but previously discarded.
     Captured at DAILY granularity (not per-fold aggregates) to maximize T,
     per Bailey et al.'s guidance that the selection-window sample should be
     doubled where possible.
   - Writes one `return_matrix.parquet` (columns: `parameter_id`,
     `panel_date`, `cost_adjusted_return`, `fold`, `observation_count`) via
     the shared `data.atomic_io.atomic_parquet_write`, and one
     `return_matrix.manifest.json` via `research.hashing.canonical_json` /
     `sha256_hex`, written exactly once (`write_manifest_once`): an
     identical-bytes retry on the same `run_id` is a no-op; differing bytes
     on the same `run_id` raise `ReturnMatrixError`. This mirrors
     `options_researcher/h7_data_gate.py`'s `write_artifact()` convention.
   - Default path: `.tmp/robustness/matrices/{run_id}/return_matrix.parquet`
     and `return_matrix.manifest.json`, overridable via a `matrix_root`
     keyword threaded through `run_experiment` and `write_reports`.
   - `measured_trial_sr_stats(matrix_path)` reads the parquet back and
     computes `(mean_trial_sr, trial_sr_variance, n_trials)` from the
     per-variant Sharpe ratios (`mean / std(ddof=1)` of each variant's own
     daily series) — a MEASURED trial population instead of the
     `config.DSR_DEFAULT_MEAN_TRIAL_SR = 0.0` neutral assumption that was the
     only option before this addition. Raises `ReturnMatrixError` if fewer
     than `config.DSR_MIN_N_TRIALS` variants are usable, feeding unchanged
     into the EXISTING `metrics.expected_max_sr` / `metrics.dsr` (Phase-1B,
     unmodified by this task).
2. `options_researcher/robustness/screening.py` gained one new, purely
   additive function, `daily_spread_series(rows, *, bucket_count)`, returning
   `(panel_date, spread, observation_count)` tuples aligned 1:1 with
   `cost_adjusted_primary_metric(...).daily_spreads`. It duplicates that
   function's per-day skip rule and sort/slice/sum/divide arithmetic exactly
   so its output floats are the SAME values the registered metric computes,
   not a second source of truth — verified by
   `test_daily_spread_series_matches_registered_primary_metric` in
   `tests/test_robustness_return_matrix.py` (`assertEqual`, exact float
   equality, not `assertAlmostEqual`). Nothing in `cost_adjusted_primary_metric`
   itself, or any other existing function in `screening.py`, was touched.
3. `options_researcher/robustness/runner.py` — `run_experiment` gained one
   optional `matrix_root` keyword (default
   `.tmp/robustness/matrices`, matching the CLI's existing `.tmp/robustness/`
   convention for `--registry`). Inside the existing per-parameter loop that
   already computes `aggregate_metric = cost_adjusted_primary_metric(...)`
   (previously runner.py lines ~372-383, now shifted by the added
   writer-setup block), one `matrix_writer.capture(...)` call was added,
   guarded by its own `try/except Exception: logger.warning(...)`. One
   `matrix_writer.finalize()` call was added immediately before
   `registry.finish_run(spec.run_id)`, under the same guard. Every guard
   swallows its exception and continues; none can change `computed`,
   `fold_results`, `parameter_nulls`, `adjusted`, `stability`, prevent
   `registry.record_completed_task`/`finish_run`, or prevent `write_reports`.
4. `options_researcher/robustness/reporting.py` — `write_reports` gained the
   same optional `matrix_root` keyword and one additive Governance bullet,
   computed by `_governance_dsr_bullet(run_id, matrix_root)`: a best-effort,
   wholly try/except-wrapped read of the manifest (if present) that reports
   either a computed DSR value, `INSUFFICIENT SAMPLE FOR DSR` (below
   `config.DSR_MIN_T`, matching `metrics.scoreboard`'s existing vocabulary),
   or `matrix unavailable` (no manifest — the capture path never ran or
   never produced rows). The bullet always states the population it draws
   from is diagnostic-only and never gates promotion. The JSON and CSV
   report bodies do not reference the matrix at all; only the Markdown
   report's Governance section changed.
5. `config.py` gained two new, currently-unenforced constants:
   `CSCV_MIN_VARIANTS_M = 10` and `CSCV_MIN_SPLITS_S = 16`, cited verbatim
   from Bailey, Borwein, Lopez de Prado & Zhu's CSCV paper ("N >> 10 is
   required"; "S=16 is a reasonable value in most cases"). No CSCV/PBO
   implementation exists anywhere in this repo; these are forward-looking
   floors only, so that a future CSCV run cannot quietly launch
   under-powered. See "CSCV floors are forward-looking" below.

## What is provably unchanged

The registered robustness outputs — SQLite `runs`/`tasks` rows, and the
JSON/CSV/Markdown report bytes — are byte-identical whether return-matrix
capture succeeds, is disabled, or fails mid-run. This is asserted by
`ByteIdentityPinTests.test_reports_and_registry_rows_are_pinned` in
`tests/test_robustness_return_matrix.py`, which runs `run_experiment` twice
on the identical fixture (same spec, same panel rows) — once with capture
working normally, once with `ReturnMatrixWriter.capture` monkeypatched to
always raise `OSError` — under a frozen registry clock
(`registry._utc_now` patched to a fixed timestamp, since `finish_run` always
re-stamps "now" on every call regardless of this addition; that is
pre-existing behavior, not something introduced here) so wall-clock drift
cannot confound the comparison. The test asserts:

- the queried SQLite `runs` and `tasks` records are fully equal (dict
  equality) between the two runs;
- the `.json` report bytes are fully equal, with zero exception (the JSON
  payload never references the matrix at all);
- the `.csv` report bytes are fully equal, with zero exception (same
  reason);
- the `.md` report has the same line count in both runs, and EXACTLY one
  line differs — the added Governance DSR bullet — asserted by index,
  prefix (`"- DSR (measured-from-return-matrix):"` in both), and content
  (`"matrix unavailable"` present only in the broken-capture run's line).

This is the stricter of the two workable designs the task brief named
("bullet renders in both paths… bytes differ ONLY inside that one line" vs.
"exclude markdown from comparison entirely"): JSON and CSV get zero
tolerance, and Markdown gets a single, named, precisely asserted line rather
than being excluded from comparison altogether.

Two further fail-safe tests (`FailSafeTests`) independently break `capture`
and `finalize` (simulated disk errors) and assert the run still reaches
`COMPLETE`, all task rows are written, and all three report files exist —
covering the "mid-run failure" case the pin test's all-calls-fail case
doesn't exercise by itself.

`tests/test_robustness_layer.py`'s existing 17 tests are unmodified in
assertion content; the one test that calls `run_experiment` directly
(`test_runner_resumes_without_rewriting_completed_tasks`) now passes an
explicit `matrix_root` pointing into its existing temp directory, so it
continues writing nothing outside that temp directory — without this, the
new `matrix_root` default would have made that pre-existing, previously
fully-isolated test start writing real files into this repo's `.tmp/`
during every test run. `.tmp/` is gitignored and disposable per
`CLAUDE.md`, but an existing test silently acquiring a new disk side effect
from an unrelated change is still worth naming explicitly.

## Population-distinction honesty note

The Governance bullet's `N` is **not** the whole-program trial count. It is
the number of usable parameter variants inside the ONE experiment run whose
report is being read — i.e. the width of that run's own `parameter_grid`
(currently 2-3 for RQ2-v1, 1-5 per lane for A2-v1; see below). Deflating
against this narrow, single-run population understates the true selection
bias if the same panel, signal, or idea was tried across other experiments,
sessions, or earlier abandoned designs that never became a registered run.
The bullet's fixed language ("population = parameter-variant selection
within this one experiment, NOT the whole-program trial count") exists
specifically so this is never silently misread as "the DSR corrected for
everything this research program has ever tried" — it did not. The
loss-gated forward-window verdict (`metrics.scoreboard`'s `verdict` field)
remains computed with zero knowledge of any of this, unchanged, per the
existing Phase-1B PSR/DSR contract in `config.py` and `metrics.py`.

`tools/score_backtest.py`'s separate `--dsr-n-source=ledger` path answers a
different, wider question (the whole-program registered-trial count from the
ledger) and was deliberately left untouched by this task — the two `N`
populations are answering different questions and must not be merged or
compared as if interchangeable. Which population is the "right" one for any
given claim is an orchestrator/owner decision, not something this addendum
resolves.

## CSCV floors are forward-looking, not yet applicable

`CSCV_MIN_VARIANTS_M = 10` and `CSCV_MIN_SPLITS_S = 16` are pre-registered
floors for a Combinatorially Symmetric Cross-Validation / Probability of
Backtest Overfitting implementation that does not exist yet anywhere in this
repo. No code reads or enforces them. They exist now, ahead of that
implementation, so a future CSCV run cannot be quietly launched
under-powered by a grid nobody checked against the literature's own stated
floor.

Honest flag: **the currently-registered grids do not meet the variant floor**
and CSCV/PBO are inapplicable to them by design, not by oversight:

- RQ2-v1 (ledger seq 18): "Candidate badges K=2" — 2-3 parameter variants
  depending on how the baseline is counted, against a floor of
  `CSCV_MIN_VARIANTS_M = 10`. *(2026-08-10: superseded by ledger seq 25,
  RQ2_AMENDMENT_V1_1 — owner-directed K=3 candidate badges B1/A1/V1, with
  V1 registered membership-only and its statistic unpinned. K=3 remains far
  below the floor, so the conclusion of this flag is unchanged.)*
- A2-v1 (ledger seq 19): five lanes (CSP, CC, PMCC, LEAPS, tactical) scored
  separately, each with its own arm count — CSP alone declares multiple
  registered exit arms while other lanes have as few as one — giving a
  per-lane range of roughly 1-5 variants, likewise far below the floor.

Neither grid can be widened retroactively without re-registration (this repo
gates parameter grids as immutable per `ExperimentSpec`), so CSCV/PBO stay a
forward-looking capability for a future, deliberately wider registered grid,
not something to bolt onto RQ2-v1 or A2-v1 as currently frozen.

## Interpreting the measured DSR bullet responsibly

The Governance bullet is a diagnostic, not a gate — nothing in `runner.py`,
`reporting.py`, or `metrics.py` reads it to change a decision. Reading it
correctly still requires holding two things in mind at once: (1) it already
corrects for having picked the best of the variants that were actually run
inside this one experiment, which is a real and useful correction over the
zero-trial-adjustment default; and (2) it does NOT correct for however many
times a human or an LLM tried, discarded, or silently reformulated an idea
before that experiment was registered — the honest whole-program answer to
"how much should I discount this" still lives with the ledger-sourced `N`
tools/score_backtest.py's `--dsr-n-source=ledger` path answers, not this one.
