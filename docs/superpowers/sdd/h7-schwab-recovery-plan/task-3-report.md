# Task 3 report — causal earnings repair and fixed-window feasibility

## Outcome

- Production commit: `e61709c7505a9f44392d4f0de034cd371fd5f527` (`docs(h7): repair causal earnings feasibility`).
- The canonical 15 issuer schedule rows were appended to both earnings stores through the one-record `h7_refresh_earnings.py` dry-run/actual append and dry-run/actual promote path.
- Fixed census: 70 common sessions, `2026-04-16` through `2026-07-27`, 15 names, 1,050 symbol-days, 70 projected sessions.
- Result: 4 full-stack passes, base rate `0.0038095238095238095`, expected entries `4.0`, error count `0`.
- Because `4.0 < 20`, `h7-forward-schwab-v1` registration and authority work is **STOPPED**. No v1 rule, cost, scorer, ledger, or authority flag changed. A separately versioned v2 arming-bottleneck design was written; no v2 experiment was run.

## A/G record map

| Symbol | Raw | Gating |
|---|---|---|
| AMD | `A0280` | `G0026` |
| AMZN | `A0281` | `G0027` |
| AVGO | `A0282` | `G0028` |
| CEG | `A0283` | `G0029` |
| CRWV | `A0284` | `G0030` |
| ET | `A0285` | `G0031` |
| IREN | `A0286` | `G0032` |
| MSFT | `A0287` | `G0033` |
| NOW | `A0288` | `G0034` |
| NVDA | `A0289` | `G0035` |
| PLTR | `A0290` | `G0036` |
| SMCI | `A0291` | `G0037` |
| TEM | `A0292` | `G0038` |
| USAR | `A0293` | `G0039` |
| VST | `A0294` | `G0040` |

All 15 gating rows use `actual_quarterly_earnings`, cite their exact raw A record, have empty supersession fields, and use issuer-controlled `company_pr` or `company_ir` evidence. No aggregator row was promoted.

## Source and input hashes

The original packet captures were verified with `shasum -a 256 /private/tmp/h7-primary/*`. Before mutation, the later issuer-schedule upgrades were separately verified:

- CEG schedule: `b2ea3e65c13fd1da97f9c7dd9e94042058ba4b538173b09a73e11d5c1b87da90`
- NVDA schedule: `300488a598622798b6b202b76abc358403ade2a3fd077d7dd10093a312b8bbbf`
- SMCI schedule: `2ae2fdea81cc0b5d1d180c57afe3163f1c0a0ee5cf220ded503eec97638341b1`

S&P Global Events was discovery-only. No S&P Global Events or Capital IQ content entered the gating stores or repository.

| Artifact | Before SHA-256 | After SHA-256 |
|---|---|---|
| `data/earnings/assertions_v2.csv` | `d0b209cf48e8840f5e207fdb5ff473e2785797239c993f90a532a3080b1a79f2` | `124f1fa2b512f238dbf36ea07485f8839653fad3ade1b40fd276a5ba003846fb` |
| `data/earnings/gating_v3.csv` | `cf196470f5589be5a4118da0b68d1c5fa1e104dd30d0bc1cbf174c7ece1f08fd` | `da2bf6abd3d7fd0ba10c5b78fcbcec47a5a802f9372578dce503d837967e63e7` |
| old feasibility receipt file | `6f1c3c8dd869f5bd7059f7bc76236b65ca0c1d60cbd8ff69d51fb058076c207a` | unchanged |
| `ledger/h7_forward/HEAD` | `9ec2a37347346343e62c1af69885964c8d2cd98aa49acd1080f04c6cae380c20` | unchanged |
| `ledger/h7_forward/events.jsonl` | `6a9bc9820f6afb787683640f188bc4a51c086aa35d6702eb9086ea37bfa070ec` | unchanged |
| `ledger/h7_forward/README.md` | `e269ec261f0d2630a3cd8edd19c649d93a03771ecc2fbcd828111bdac0b0750f` | unchanged |
| `ledger/h7_forward_schwab/README.md` | `a21185528a6b9136f0ab2c8dc82f94f25f61e51c7b757ff2ac4733b2fdae0686` | unchanged |

Production artifact hashes:

- primary evidence packet: `50c6013180359520e7265118fe3370b48f9f73b88f39134ec1238827f35bd9be`
- new feasibility receipt file: `5f5632b7083c5c013c901ac8b28ef6d888ee3dbb606f86a0d93c886576c51d63`
- embedded new receipt hash: `d0ffe1f900b8ffc132f757f9783d4581464aaf8b3538271fe2ae337ba1702d0c`
- embedded prior receipt hash: `8b567a5eb6f1950fa32ee9ddfbd4a440e32a7e12ff7a617888e9cd67baff625c`
- v2 design: `7d85f43b766799fa5e317b622a2347f0a1627c81890508494c2675470117376e`

The new receipt binds the exact raw/gating/evidence-packet byte hashes, the prior receipt hash, the 70-by-15 census, `error_count=0`, and the canonical read-only data paths `/Users/carsynstephenson/options-validator/.cache/chains` and `/Users/carsynstephenson/options-validator/.cache/underlying`.

## Command protocol

Each symbol was processed separately with these exact command shapes and its literal packet values; no loop imported multiple rows into one invocation:

```text
uv run python tools/h7_refresh_earnings.py append-raw <literal row arguments> --dry-run
uv run python tools/h7_refresh_earnings.py append-raw <same literal row arguments>
uv run python tools/h7_refresh_earnings.py promote --raw-id <captured A id> --event-class actual_quarterly_earnings --notes <packet path, capture hash, conservative-time note> --dry-run
uv run python tools/h7_refresh_earnings.py promote --raw-id <same A id> --event-class actual_quarterly_earnings --notes <same note>
```

The fixed-window driver set `OPTIONS_CACHE_DIR=/Users/carsynstephenson/options-validator/.cache/chains` before import, rebound `data.underlying_closes.CACHE_DIR` to the canonical underlying cache, intersected the exact 15 chain-file date sets, filtered through `2026-07-27`, selected the last 70, and asserted first/last/count/denominator before calling `measure_cached_history`. Both canonical cache paths were read-only. The first attempted worktree-local census failed closed with no receipt because that local cache was empty; no data or receipt was written by that attempt.

## Focused validation

- `uv run python -m unittest discover -s tests -p 'test_h7_earnings.py'` — 57 passed.
- `uv run python -m unittest discover -s tests -p 'test_h7_earnings_causal.py'` — 9 passed.
- `uv run python -m unittest discover -s tests -p 'test_h7_refresh_earnings.py'` — 29 passed.
- `uv run python -m unittest discover -s tests -p 'test_h7_source_health.py'` — 22 passed.
- project-venv equivalent of `test_h7_schwab_feasibility.py` after a sandbox-only uv-cache denial — 5 passed.
- Total focused tests in the final set: 122 passed, 0 failed. No broad suite was run.
- Store validation: raw `VALID`, 294 records ending `A0294`; gating `VALID`, 40 records ending `G0040`.
- Receipt audit: `verify_receipt` true; exact input hashes 3/3; prior receipt hash matched.
- Append audit: raw `15 additions / 0 deletions`, gating `15 additions / 0 deletions`; byte-prefix checks passed (`+7426` raw bytes, `+8221` gating bytes).
- `git diff --check` passed.
- `uv run python tools/irreplaceable_data_guard.py verify` passed before and after.
- Focused production commit contains five files and 166 insertions. This SDD report is intentionally uncommitted and unstaged.
