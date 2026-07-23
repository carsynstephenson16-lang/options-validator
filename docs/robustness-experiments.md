# Robustness experiments — operator guide

This path is research-only. It reads a registered immutable specification and
a precomputed point-in-time CSV. It does not fetch data, simulate orders,
alter scanner ranking, or promote a result.

## 1. Prepare the panel

Create one CSV with the schema in
`docs/robustness-experiment-data-dictionary.md`. It must contain exactly one
lane and every `parameter_id` declared in the specification. Outcomes must
already be cost-adjusted and lane-specific.

Compute its identity:

```bash
shasum -a 256 path/to/panels.csv
git rev-parse HEAD
```

Put those exact values in `dataset_fingerprint` and `git_commit_sha`.

## 2. Prepare the immutable JSON specification

Required fields:

```json
{
  "experiment_name": "rq2-scanner-enrichment",
  "version": "1",
  "research_question_id": "RQ2-v1",
  "lane": "sell_put",
  "signal_version": "green-v1",
  "dataset_fingerprint": "<64 hex characters>",
  "point_in_time_cutoff": "2026-07-20",
  "train_window": {"start": "2025-01-01", "end": "2025-06-30"},
  "validation_window": {"start": "2025-07-01", "end": "2025-09-30"},
  "test_window": {"start": "2025-10-01", "end": "2026-07-20"},
  "purge_observations": 10,
  "embargo_observations": 2,
  "forward_outcome_horizon": 10,
  "walk_forward_mode": "expanding",
  "train_observations": 126,
  "test_observations": 21,
  "step_observations": 23,
  "cost_model": {"model": "repo-frozen", "stress": 1.0},
  "parameter_grid": [
    {"parameter_id": "baseline"},
    {"parameter_id": "badge-b"}
  ],
  "random_seed": 42,
  "permutation_count": 5000,
  "permutation_method": "circular_block",
  "multiple_testing_method": "holm",
  "multiple_testing_alpha": 0.1,
  "git_commit_sha": "<40 hex characters>",
  "status": "registered",
  "claim_label": "Repo-verified",
  "owner_controls": {
    "bucket_count": 3,
    "minimum_adverse_bottom_bucket": 10,
    "holm_sidedness": "one-sided-positive",
    "forward_backstop": "2027-07-23"
  }
}
```

The dates and walk-forward sizes above are examples, not owner decisions.
Copy the signed values from the governing registration.

## 3. Doctor first

```bash
uv run python -m options_researcher.robustness doctor \
  --spec path/to/spec.json \
  --panels path/to/panels.csv
```

Doctor refuses an unregistered question, wrong dataset hash, wrong Git SHA,
wrong lane/grid, future row, incomplete owner control, or empty panel.

## 4. Run or resume

```bash
uv run python -m options_researcher.robustness run \
  --spec path/to/spec.json \
  --panels path/to/panels.csv \
  --registry .tmp/robustness/experiments.sqlite3 \
  --artifacts reports/robustness \
  --workers 1

uv run python -m options_researcher.robustness resume \
  --spec path/to/spec.json \
  --panels path/to/panels.csv \
  --registry .tmp/robustness/experiments.sqlite3 \
  --artifacts reports/robustness
```

Resume deterministically skips completed `(fold, parameter_id)` tasks.
Conflicting checkpoints and incompatible schemas fail loudly.

## 5. Inspect or rebuild reports

```bash
uv run python -m options_researcher.robustness list \
  --registry .tmp/robustness/experiments.sqlite3

uv run python -m options_researcher.robustness report \
  --run-id <run-id> \
  --registry .tmp/robustness/experiments.sqlite3 \
  --artifacts reports/robustness
```

Outputs are one deterministic JSON record, one flat CSV, and one concise
Markdown report. No output is a production recommendation.
