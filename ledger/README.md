# Experiment ledger

Append-only, hash-chained research record written by `research/ledger.py`.

- `experiments.jsonl` — one JSON record per line, each committing to the previous
  via `prev_hash`/`record_hash` (the chain IS the tamper-evidence).
- `HEAD` — the current chain tip, tracked so it is diffable in git.

Do not hand-edit these files: `uv run python -m research.cli verify` (and
`--anchored` before any OOS reveal) will detect tampering, a HEAD mismatch, or an
uncommitted tree. They are created when the first run is registered.

## facts.log is NOT part of the chain

`facts.log` (written by `research/facts.py`) is a plain timestamped
append-only text log with **no hash chain, no HEAD, and no verifier** — this
is deliberate: it is a descriptive research-notes stream, never
verdict-feeding. Consequences:

- Nothing can prove a past `facts.log` line wasn't edited. Treat it as
  advisory context, not an audit record.
- Any decision that freezes a number (sizing caps, triggers, thresholds)
  belongs in the **chained** ledger (`experiments.jsonl` via `research/ledger.py`
  or a registered note), with `facts.log` at most carrying a pointer to it.
- Git history provides weak, incidental tamper-evidence for committed
  `facts.log` states, but that is not a guarantee the chain gives.
