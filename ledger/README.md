# Experiment ledger

Append-only, hash-chained research record written by `research/ledger.py`.

- `experiments.jsonl` — one JSON record per line, each committing to the previous
  via `prev_hash`/`record_hash` (the chain IS the tamper-evidence).
- `HEAD` — the current chain tip, tracked so it is diffable in git.

Do not hand-edit these files: `uv run python -m research.cli verify` (and
`--anchored` before any OOS reveal) will detect tampering, a HEAD mismatch, or an
uncommitted tree. They are created when the first run is registered.
