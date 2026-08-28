# Codex brief 32 — per-quote age audit + owner-gated staleness gate (DATA-02), rev 2

**Date:** 2026-08-28 (rev 2 — round-1 FAIL findings B1–B5, A1–A5, C1–C2
all addressed)
**Author:** Claude orchestrating session (Fable), deferred-closeout session
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** BLOCKED — round-2 fresh independent review (Opus, 2026-08-28)
verdict FAIL on STRUCTURAL grounds (finding N1): the production data gate
reads only the frozen v1 cache (`.cache/chains`, no timestamp columns,
newest file 2026-07-27), and `h7_schwab_data_gate` — the only module that
reads the timestamped Schwab packages — has ZERO production callers (it
is pre-wired for the future H7 Schwab window registration). As scoped,
the gate would land inert: no quote would ever be aged. Also blocking:
N2 (a per-symbol audit under `result["symbols"]` leaks into the immutable
receipt via `build_receipt`, `h7_data_gate.py:645`), N3 (test 6
unwritable — `config_hash`/`source_hash` move with this very PR), N4
(the selectable mask is private in `data/recent_topup.py:489` and
out-of-scope). Owner-relevant round-2 measurement (keep for any future
threshold ruling): worst SELECTABLE quote age across the seven
timestamped sessions on disk = 0.61–10.38 min (08-25 peaked at 10.38 —
a 10-minute block threshold would have NO_GO'd 1 of 7 sessions; 15/20
would have blocked none; n=7, LLM-measured, not owner-typed). DO NOT
IMPLEMENT from this revision. Routing decision pending owner 2026-08-28:
descriptive daily age report now + gate deferred to the H7 Schwab
registration arc, vs everything deferred to that arc, vs a rev-3
standalone redesign.
**Provenance:** Repo-verified against origin/main @`704a138`; round-1
review measurements (2026-08-27 package: 78% of rows timestamped AFTER the
receipt's capture-start time; 0 of 7,746 selectable rows >15 min old) are
Reviewer-measured 2026-08-28.
**Owner directive:** Carsyn in-session 2026-08-28 — DATA-02 "Commission
now".

## Why this exists (plain language)

The Schwab package verifier proves when the download happened but never
checks how old each quote inside is. This adds the missing per-quote age
check — warn-first, with blocking authority impossible until the owner
types a threshold. Round 1 failed because the obvious design breaks three
real mechanisms; this rev is built around them.

## The three mechanisms this rev is built around (round-1 B1/B2/B3)

1. **Reason codes ARE the verdict.** `options_researcher/h7_data_gate.py:417`:
   `verdict = "GO" if not codes else "NO_GO"`. Therefore warn-mode output
   MUST NEVER touch `reason_codes` — it goes in a separate
   `quote_age_audit` summary surfaced via `_print_summary`
   (`h7_data_gate.py:786-796`, which the ritual echoes at
   `tools/daily_ritual.sh:185`). Only `block_selectable` mode may append
   the new `QUOTE_STALE` code.
2. **The receipt capture time is NOT an age reference.** `captured_at_et`
   is stamped at capture START (`schwab_chain_capture.py:315`); on the
   real 2026-08-27 package, 78% of quote timestamps are LATER than it.
   Reference time = the package's own MAXIMUM quote timestamp per symbol.
   Age of a row = `max_ts - row_ts`, floored at 0. Prior-session detection
   is absolute: `date(row_ts) < session`. Reuse
   `options_researcher/live_quotes.py:127 quote_is_fresh` semantics for
   None/naive/future handling where applicable rather than re-inventing.
3. **The gate receipt is re-verified by exact dict equality.**
   `options_researcher/h7_schwab_data_gate.py:73-77` compares the stored
   `audit_receipt` against a fresh `verify_session(...)` result and raises
   on ANY difference (reached from `h7_schwab_window_registration.py:150`).
   Therefore `verify_session`'s RETURN DICT IS UNTOUCHABLE, and no age
   output may enter any immutable receipt. The age audit is a separate
   pure function (new helper in `options_researcher/h7_data_gate.py`)
   whose output lives only in the run summary/log.

## Design

`config.py` constants (both appended, with provenance comments):
- `SCHWAB_QUOTE_AGE_MODE = "warn"` (`"off" | "warn" | "block_selectable"`).
- `SCHWAB_QUOTE_MAX_AGE_MINUTES = None` — owner-typed only. Candidates for
  the owner, ALL labeled LLM-proposed, NOT frozen: 10 / 15 / 20 minutes.
  (Context, round-1 A1: the live display lane has
  `LIVE_QUOTE_MAX_AGE_SECONDS = 120` at `config.py:690` — a different
  regime, real-time display vs preclose package; do not conflate, say so
  in the constant's comment. This brief's owner-typed insistence is
  deliberately stricter than the `CHAIN_STALE_WARN/BLOCK_SESSIONS`
  precedent at `config.py:676-677`.)
- The `block_selectable`+`None` fail-closed check lives AT GATE ENTRY in
  `h7_data_gate.py` (round-1 A3: never raise inside `config.py` — that
  breaks every importer including `config_hash()`).

Surfaces:
1. New pure helper computing the per-symbol age audit (counts over/under
   threshold-or-candidate-15-informational, prior-session count, max/min
   quote ts) from a chain frame. Called from the gate evaluation path for
   frames that carry a `timestamp` column ONLY — Schwab/v2. Legacy v1
   partitions (`data/cache_schema.py:43-54` — no timestamp column) are
   explicitly reported `quote_age_audit: NOT_EVALUABLE_V1` (round-1 A5).
2. `warn` mode: audit summary added to `_print_summary` output and the
   gate's log line. NO change to `reason_codes`, NO change to any receipt,
   NO change to GO/NO_GO — golden-tested.
3. `block_selectable` mode (inert until owner-typed threshold): within the
   gate's own per-row evaluation (`h7_data_gate.py:302-355` region), a row
   that passes all EXISTING checks but has a prior-session timestamp or
   age beyond threshold gets `QUOTE_STALE` appended per current code
   conventions. Do NOT touch `data/recent_topup.py` (round-1 A4/C2 — the
   selectable-mask there is out of bounds; brief 33 owns that file).

## Required same-commit updates (round-1 B4/A2)

- `tests/test_ritual_switch_on_hash_containment.py:147` pins the exact
  tuple of uppercase config names (`FROZEN_CONFIG_UPPERCASE_NAMES`) —
  update the pin in the same commit; that is its sanctioned maintenance
  path.
- `config.py` edits change `config_hash()` (`config.py:528`;
  compared at `research/diagnostics.py:152`, `research/experiments.py:272`).
  State in the PR body that stored-vs-live hash comparisons will show the
  new baseline — the established batch-landing disclosure.
- **v2 audit closure (round-1 C1):** `config.py` and
  `options_researcher/h7_data_gate.py` are in `V2_FULL_AUDIT_SOURCE_PATHS`
  (`data/cache_schema.py:20-40`); `validate_v2_audit_receipt` re-hashes
  them and a live receipt exists at
  `.cache/chains_v2/od1-2026-08-01/_meta/full_audit.json`. Landing this
  invalidates that receipt (`CHAIN_V2_AUDIT_RECEIPT_INVALID` → NO_GO on
  the v2 lane) until re-audited. Check for live receipts before landing
  and DISCLOSE the consequence in the PR body; the Schwab lane's override
  insulates the daily ritual.

## Scope

**IN:** the helper, the two mode behaviors, the constants, the same-commit
pin updates, tests.
**OUT (hard stops):** no change to `verify_session`'s return or ANY
receipt content; no `reason_codes` change outside `block_selectable`; no
edits to `data/recent_topup.py`, `tools/schwab_chain_manifest.py`, or
`tools/daily_ritual.sh`; no provider calls; no activation (mode flip +
threshold are a separate owner-controlled commit); no ledger writes.

## Tests (unittest, offline, synthetic frames)

1. Warn mode, stale + prior-session rows present: `reason_codes`
   byte-identical to pre-change, GO/NO_GO unchanged, audit summary
   present.
2. Block mode (test-injected threshold): stale selectable row →
   `QUOTE_STALE` in codes → NO_GO; prior-session row likewise.
3. Age reference: rows newer than max_ts impossible by construction;
   age floors at 0 (no negative ages).
4. v1 frame (no timestamp column) → `NOT_EVALUABLE_V1`, no error.
5. Block mode + `None` threshold → fail-closed error at gate entry.
6. Receipt-stability regression: `verify_session` output and the gate
   receipt dict are byte-identical to pre-change on existing fixtures
   (this is the round-1 B3 protection — make it an explicit test).

## Acceptance

```
uv run python -m unittest discover -s tests
uv run ruff check . && uv run pyright
```
RED/GREEN for tests 1-2. Born-draft PR; owner types threshold + flips
mode in a separate commit if/when desired.
