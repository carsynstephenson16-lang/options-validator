# Robustness experiment data dictionary

## Panel CSV

| Field | Type | Meaning |
|---|---|---|
| `panel_date` | ISO date | Point-in-time scanner/evaluation date |
| `ticker` | text | Underlying identifier |
| `lane` | enum | `sell_put`, `covered_call`, `pmcc`, `leaps`, or `tactical_call` |
| `parameter_id` | text | Exact immutable parameter-grid member |
| `score` | finite float | Research variant's within-lane rank score |
| `gross_forward_return` | finite float | Lane-specific forward return before modeled costs |
| `modeled_cost` | non-negative float | Registered total cost deduction |
| `bid_ask_cost` | non-negative float | Bid/ask component inside the modeled cost |
| `forward_cost_adjusted_return` | finite float | Lane-specific forward return after registered costs |
| `regime` | text | Descriptive regime label; never pooled into a verdict |

The file must contain one lane. No universal cross-lane target is accepted.
`forward_cost_adjusted_return` must equal
`gross_forward_return - modeled_cost`; disagreement is rejected. The explicit
cost fields support the registered ±50% total-cost and bid/ask stress views.

## Run record

| Field | Meaning |
|---|---|
| `run_id` | Stable RQ/lane/config-hash identity |
| `parent_experiment_id` | Optional lineage pointer |
| `config_hash` | SHA-256 of the canonical immutable specification |
| `dataset_fingerprint` | SHA-256 of the exact panel CSV |
| `git_sha` | Exact registered source commit |
| `started_at_utc`, `completed_at_utc` | Execution timestamps |
| `status` | `RUNNING`, `COMPLETE`, `BLOCKED`, or `FAILED` |
| `seed` | Registered random seed |
| `lane` | One options lane |
| `spec_json`, `spec_digest` | Canonical spec and integrity digest |
| `claim_label` | Repository claim-discipline label |
| `error_detail` | Explicit terminal error, if any |

## Task/checkpoint record

| Field | Meaning |
|---|---|
| `fold` | Deterministic walk-forward fold number |
| `parameter_id` | Parameter-grid member |
| `status` | `COMPLETE` or `FAILED` |
| `metrics_json` | Spread, counts, decay, stability, concentration, null effect, and fold ranges |
| `raw_p_value` | Finite-sample empirical p-value |
| `adjusted_p_value` | Holm step-down adjusted p-value |
| `gate_outcomes_json` | Passed, failed, blocked, or unregistered gates |
| `error_detail` | Failure detail |
| `artifact_paths_json` | Related artifact paths; never secrets |
| `payload_digest` | Checkpoint idempotency/integrity digest |
| `completed_at_utc` | Task completion time |

`PRAGMA user_version=1` is the schema contract. Future schemas are refused
until a deliberate migration is implemented.
