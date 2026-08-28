# Codex brief 33 — hash-bound provenance receipt for closes refreshes (DATA-03), rev 2

**Date:** 2026-08-28 (rev 2 — round-1 FAIL findings B1–B4, A1–A6, C1/C3
all addressed)
**Author:** Claude orchestrating session (Fable), deferred-closeout session
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** DRAFT rev 2 — pending FRESH independent adversarial review
(round 1 verdict was FAIL).
**Provenance:** Repo-verified against origin/main @`704a138`. Finding
source: 2026-08-25 audit D3-3/DATA-03. Guard non-interaction adjudication:
R3-F14 at `docs/superpowers/plans/2026-08-25-29-schwab-inventory-binding-codex-brief.md:77`
(round-1 A5 corrected the citation).
**Owner directive:** Carsyn in-session 2026-08-28 — DATA-03 "Commission
now".
**Landing order (binding):** lands AFTER brief 35 (both touch
`tests/test_daily_ritual_provenance.py`; round-1 C3).

## Why this exists (plain language)

Daily closing-price refreshes keep no durable record of what was acquired
when. Round 1 failed on two hard facts: the fetcher never returns a data
frame (so rev-1's "hash the fetched frame" was unimplementable), and a
careless durability edit can silently kill the ENTIRE daily evidence
commit. This rev is built around both.

## The two mechanisms this rev is built around (round-1 B1/B2)

1. **There is no fetched frame.** `fetch_underlying_eod_yahoo(symbol) -> str`
   returns a PATH (`data/underlying_closes.py:265`, `:341` returns
   `store_closes(...)`); `refresh_closes_guarded`
   (`data/recent_topup.py:107`) even discards the return (`:168`) and
   re-reads from disk. So the receipt binds exactly ONE hash class:
   the STORED close file's sha256 immediately after the refresh step, per
   symbol, plus acquisition metadata. Label it `stored_file_sha256` and
   state in the receipt schema that it is a stored-artifact binding at
   acquisition time, NOT a raw provider-response hash — the fetcher does
   not retain raw bytes, and claiming otherwise would be false provenance.
2. **A missing path in `DATA_TIER_PATHS` kills the whole evidence
   commit.** `git add -- <realdir> <nonexistent>` fails pathspec-fatal
   with NOTHING staged (reviewer-reproduced, git 2.39.5);
   `tools/daily_ritual.sh:570` discards stderr and `:571-573` reports
   "nothing new to persist" as a mere note. Therefore this brief MUST
   commit `reports/closes_receipts/.gitkeep` in the same PR AND add a test
   asserting the directory exists in-tree.

## Design

Receipt: `reports/closes_receipts/<YYYY-MM-DD>/<scope>.json` (dated
subdirectory + scope discriminator, the `reports/schwab_chains/<date>/`
precedent — round-1 A2; two same-day runs with different scopes get
distinct files; an exact re-run refuses to overwrite via
`atomic_text_write`'s exclusive create — note its TEXT-FIRST argument
order, `data/atomic_io.py` (round-1 A1)).

Contents: schema version; provider identity; retrieval UTC timestamp;
requested symbols; per-symbol OUTCOME — one of
`refreshed | restored | failed | skipped` — with `stored_file_sha256` and
max session for every symbol that has a stored file after the run.
`restored` (the guard rolled the file back, `data/recent_topup.py:197-220`)
records the RESTORED file's hash — that is the true post-run state
(round-1 A3). All-failed runs still emit the receipt with `failed`
outcomes — fail-visible (round-1 A4).

Producers: wire into `refresh_closes_guarded` (`data/recent_topup.py:107` —
the ONLY production caller, via `tools/daily_ritual.sh:290`) AND plain
`refresh_closes` (`:84`, reachable via `--refresh-closes`, `:714-715`)
(round-1 A1). The `DATA_PULL` facts line's TEXT gains the receipt path —
this IS a (harmless, additive) change to the line's content; facts.log
append-only semantics untouched (round-1 A6 wording fixed).

Verify helper (`--verify <receipt>` or a small module main): recomputes
`stored_file_sha256` for each symbol; exit 1 on mismatch. **Validity
window (round-1 B4):** close files are rewritten in place daily
(`data/underlying_closes.py:24-25` one file per symbol), so a receipt's
hashes are a CURRENT-BYTES claim only until that symbol's next refresh;
after that it is a historical acquisition record. The helper must check
whether a NEWER receipt exists for the symbol and report "superseded (not
a mismatch)" instead of failing — only a mismatch with the LATEST receipt
is an integrity alarm.

## Ritual durability edit (round-1 B3 — exact constraint)

`tests/test_daily_ritual_provenance.py:88-134` pins `tools/daily_ritual.sh`
BY EXACT LINE NUMBER (python-dash-c sites at keys 120…437; mutation verbs:
`git add` 570, `git commit` 573, `git fetch` 583, `git merge` 584,
`git push` 585, `restic backup` 602; asserted with `assertEqual` at
`:352,:359,:365`). Therefore the `DATA_TIER_PATHS` addition MUST be an
INLINE edit on the existing path-list line (`tools/daily_ritual.sh:550`,
the `reports/pick_tracker` precedent) — NO inserted lines at or above
`:570`, no comment blocks. If the receipt-producer call itself must be
added to the ritual, it goes through the same inline/no-shift discipline
or below `:602`, and the pinned registries are updated in the same commit
ONLY if a shift is truly unavoidable (prefer: no shift at all).

## v2 audit closure (round-1 C1)

`data/recent_topup.py` and `data/underlying_closes.py` are in
`V2_FULL_AUDIT_SOURCE_PATHS` (`data/cache_schema.py:20-40`); a live
receipt exists at `.cache/chains_v2/od1-2026-08-01/_meta/full_audit.json`
and re-hash validation raises on change → `CHAIN_V2_AUDIT_RECEIPT_INVALID`
on the v2 lane until re-audited. Check for live receipts before landing;
disclose the consequence in the PR body. The Schwab-lane override
insulates the daily ritual.

## Scope

**IN:** receipt producer + schema, `.gitkeep` + in-tree test, inline
`DATA_TIER_PATHS` edit, verify helper, tests.
**OUT (hard stops):** no change to the restoration guard's
tolerance/decision logic; no rewriting prior data or facts; no provider
calls in tests (synthetic `fetch_fn`); no guard/inventory changes
(R3-F14); no changes to `fetch_fn`'s contract; no edits to
`options_researcher/h7_data_gate.py` or `config.py` (brief 32 owns those).

## Tests (unittest, offline)

1. Guarded refresh, synthetic fetch: receipt written with per-symbol
   `refreshed` outcomes + correct hashes + max sessions; facts line
   references it; dir-exists-in-tree assertion.
2. Mutate a stored close file, no newer receipt → verify exits 1 naming
   the symbol; unmutated → exit 0.
3. Restore case: guarded refresh that restores → outcome `restored`,
   hash equals the restored (pre-fetch) content.
4. Superseded receipt: refresh again (new receipt) → verifying the OLD
   receipt reports superseded, exit 0.
5. All-fetches-fail run → receipt with `failed` outcomes (fail-visible).
6. Ritual line-pin regression: `tests/test_daily_ritual_provenance.py`
   passes unmodified (proving the inline edit shifted nothing).

## Acceptance

```
uv run python -m unittest discover -s tests
uv run ruff check . && uv run pyright
```
RED/GREEN for tests 1-2. Born-draft PR; owner reviews the receipt schema
before un-drafting.
