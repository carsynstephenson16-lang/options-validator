# H7 forward-event ledger (Stage 3 — BUILD-ONLY, INACTIVE)

An append-only, hash-chained record of H7 **forward-paper** events, separate
from the research experiment ledger. Managed **only** through the typed
Python API in `options_researcher/h7_event_ledger.py`.

**This directory holds zero real events.** `events.jsonl` and `HEAD` do not
exist yet and must not be created during Stage 3 — the first real forward
event is prohibited until Stage 8 activation. Verifying the absent store
prints `VALID EMPTY` (exit 0) and creates nothing.

## Files (created only by the first authorized append, later)

- `events.jsonl` — one canonical-JSON record per line, LF-terminated,
  append-only.
- `HEAD` — the current chain tip (`record_hash` of the last record).

## Separation from the research ledger

This chain **never** touches `ledger/experiments.jsonl`, `ledger/HEAD`, or
`trial_count`, and reuses none of the research entry types (trial, run,
diagnostic, OOS). `research/ledger.py` was a design pattern only.

## Record schema

Caller-supplied **logical** fields (committed by `logical_hash`):

| field | meaning |
|---|---|
| `schema_version` | `1` |
| `event_id` | caller-supplied canonical non-empty unique id |
| `event_type` | one of the allowed types below |
| `occurred_at_utc` | UTC ISO timestamp (offset must be zero) |
| `evaluation_session` | `YYYY-MM-DD` |
| `symbol` | canonical uppercase ticker, or `null` (whole-universe) |
| `lane` | `a`, `b`, `c`, or `null` |
| `causes` | ordered list of earlier `event_id`s (no dups, no self) |
| `payload` | JSON object |

Chain fields added by `append_event()`:

| field | meaning |
|---|---|
| `seq` | 0-based, increases by exactly 1 |
| `recorded_at_utc` | append time in UTC (offset must be zero) |
| `logical_hash` | `sha256(canonical_json(logical fields))` — the idempotency identity |
| `prev_hash` | prior record's `record_hash` (64 zeroes for `seq` 0) |
| `record_hash` | `sha256(canonical_json(record without record_hash))` |

Allowed `event_type`: `source_health`, `data_gate`, `board_resolution`,
`lane_displaced`, `entry_intent`, `exit_intent`, `owner_approval`,
`paper_fill`, `skip`, `data_gap`.

Canonical JSON = sorted keys, compact separators, UTF-8, LF endings,
`allow_nan=False`, no implicit stringification of unsupported values.

## Idempotency

`append_event` keys idempotency on `(event_id, logical_hash)`:

- same `event_id` + identical logical content → **no-op**, returns the
  existing `seq`/`record_hash` with `appended=False`, writes nothing.
- same `event_id` + different logical content → **`EventConflictError`**, no
  write.

Capacity-sensitive callers may also supply `expected_head` to `append_event`.
The value is checked under the exclusive writer lock against the verified
current tip (`None` means verified empty); a mismatch raises
`LedgerHeadConflictError` before deduplication or mutation. Stage 5 uses this
optimistic precondition so a book decision cannot append from a stale capacity
snapshot.

## Concurrency & locking

The whole read-verify → duplicate-check → seq-allocate → append → fsync →
HEAD-replace critical section runs under an exclusive `flock` on the ledger
directory. Concurrent writers can never allocate the same `seq` or fork the
chain: distinct events serialize into one valid chain; identical events
produce exactly one record and one idempotent result. `verify` and
`read_events` take a shared directory lock, so a reader waits through the
writer's JSONL-fsync → HEAD-replace window and never reports false corruption
on a healthy in-progress append.

## Crash detection (honest, not two-file-atomic)

`append` fsyncs `events.jsonl`, then atomically replaces `HEAD`. JSONL + HEAD
cannot be updated atomically together, so the guarantee is **crash-detecting,
fail-closed**, not crash-atomic:

- failure before append → prior ledger stays valid;
- failure mid-record → detected as partial/corrupt;
- failure after `events.jsonl` fsync but before `HEAD` replace → **stale-HEAD
  mismatch**; the next `verify`/`append` **refuses**.

There is **no automatic repair and no silent truncation**. A recovery
procedure, if ever needed, is a separately authorized change.

## Verification

`verify(base_dir)` (and the `verify` CLI) fail closed on: exactly one of the
two files present; non-canonical or partial JSON; blank lines or trailing
garbage; `seq` not starting at 0 or not += 1; first `prev_hash` ≠ 64 zeroes
or any `prev_hash` ≠ prior `record_hash`; wrong `logical_hash`/`record_hash`;
invalid semantic fields; duplicate `event_id`; a cause not referencing an
earlier event; or `HEAD` ≠ the final `record_hash`. `read_events` verifies
before returning and never returns partially verified records.

CLI: `uv run python -m options_researcher.h7_event_ledger verify
[--base-dir PATH]` → exit 0 valid (incl. absent/empty), exit 2 on any
corruption/invalid invocation (clear message, no traceback). There is no
append CLI in Stage 3.

## Do not hand-edit

Never edit `events.jsonl` or `HEAD` by hand, and never add records by any
means other than `append_event()`. Any manual edit breaks the hash chain and
`verify` will refuse.

## Stage-7/8 prerequisites (review findings 2026-07-13)

The Stage-7 integrity prerequisites from the 2026-07-13 review are resolved:

- `verify`/`read_events` now take a shared `flock`; a deterministic
  writer-gap regression proves a reader waits until HEAD commits.
- `occurred_at_utc` and `recorded_at_utc` both require a zero UTC offset on
  append and stored-chain verification, including hash-perfect forgeries.
- The canonical-JSON round-trip guard has a direct hash-perfect,
  non-canonical serialization regression.

The ledger remains INACTIVE. The macOS durability blocker was resolved
2026-07-13: regular-file writes call portable `fsync` and then Darwin
`F_FULLFSYNC` before success; the directory `fsync` still persists the HEAD
rename. Full-sync failures propagate and leave a detectably incomplete store,
covered by deterministic failure injection. No weaker fallback is reported as
success.

Remaining crash-model note:

- **No orphan-tail recovery tool (Info, by-design).** A crash mid-append
  permanently bricks the store (intended "no auto-repair"). If ever needed, a
  guarded, lock-held truncate-orphan-tail tool is a separately authorized
  change (already noted under Crash model).

Advisory-`flock`/NFS and the O(n²)-per-append re-verify were also noted; both
are acceptable for a single-machine, low-volume forward-event ledger.
