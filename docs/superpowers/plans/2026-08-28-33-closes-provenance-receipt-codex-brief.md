# Codex brief 33 — hash-bound provenance receipt for closes refreshes (DATA-03)

**Date:** 2026-08-28
**Author:** Claude orchestrating session (Fable), deferred-closeout session
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** DRAFT — pending independent adversarial review before hand-off
**Provenance:** Repo-verified against origin/main @`704a138` unless labeled
otherwise. Finding source: 2026-08-25 audit D3-3/DATA-03
(`agents/03-data-provenance.md:33-39` in the audit bundle).
**Owner directive:** Carsyn in-session 2026-08-28 — DATA-03 ruled
"Commission now" via decision prompt.

## Why this exists (plain language)

When the platform refreshes daily closing stock prices, it saves the
cleaned result but keeps no fingerprint of what the provider actually
returned — months later nobody can prove where a close came from. The
chain-cache top-up path in the SAME file already does this right
(`_sha256` machinery). This brief copies that pattern to the closes path.
Additive only: a new receipt, no behavior change.

## Verified facts

- `data/underlying_closes.py:28` `store_closes` — validates, dedupes,
  atomic-writes; no hash, no receipt (full-file grep confirmed).
- `data/recent_topup.py:84` `refresh_closes` — fetches per symbol via
  `fetch_fn`, appends one descriptive `DATA_PULL` line to facts.log; no
  hashing on this path.
- `data/recent_topup.py:270` `_sha256` + uses at `:312,:338,:405` — the
  in-file pattern to copy (chain top-up path).
- Honesty constraint: `fetch_fn` returns a transformed frame, not raw
  provider bytes. The receipt binds a DETERMINISTIC canonical
  serialization of the fetched frame (sorted, fixed dtypes/format) —
  label this in the receipt as `fetched_frame_sha256`, NOT a raw HTTP
  response hash. Do not claim raw-response binding the code cannot make.

## Design

One receipt per refresh run: `reports/closes_receipts/<YYYY-MM-DD>.json`
(atomic write via `data/atomic_io.py`), containing: provider identity,
retrieval UTC timestamp + timezone, requested symbols + range, per-symbol
`fetched_frame_sha256` (canonical serialization, documented), per-symbol
post-write close-file sha256 + max session, and the receipt schema version.
The existing `DATA_PULL` facts line is UNCHANGED (append-only) but gains
the receipt path in its text. A small read-only verify helper
(`--verify <receipt>`) recomputes stored-file hashes and reports
mismatches, exit 1 on any.

## Scope

**IN:** receipt producer wired into `refresh_closes` (+ the guarded
variant), the verify helper, `reports/closes_receipts` added to
`DATA_TIER_PATHS` in `tools/daily_ritual.sh` (durability; the PR #76
pattern — tracked receipts auto-commit; do NOT touch the guard's
namespaces: tracked ritual-grown dirs never carry inventory floors, per
the brief-29 A1 adjudication).
**OUT (hard stops):** no change to restoration-guard semantics or
tolerance logic; no rewriting of prior data or facts; no provider calls
in tests (synthetic `fetch_fn` only); no ledger API changes; no guard /
inventory changes.

## Tests (unittest, offline)

1. Synthetic `fetch_fn` refresh → receipt exists with correct per-symbol
   hashes and max sessions; facts line references it.
2. Mutate a stored close file after refresh → `--verify` exits 1 naming
   the symbol; untouched receipt verifies exit 0.
3. Guarded-refresh path produces the same receipt.
4. Golden: refresh outputs (frames, facts semantics) byte-identical to
   pre-change behavior apart from the additive receipt + path reference.

## Acceptance

```
uv run python -m unittest discover -s tests
uv run ruff check . && uv run pyright
```
RED/GREEN for tests 1-2. Born-draft PR; owner reviews the receipt schema
in the PR body before un-drafting.
