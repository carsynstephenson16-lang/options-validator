# Codex brief 32 — per-quote age audit + owner-gated staleness gate (DATA-02)

**Date:** 2026-08-28
**Author:** Claude orchestrating session (Fable), deferred-closeout session
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** DRAFT — pending independent adversarial review before hand-off
**Provenance:** Repo-verified against origin/main @`704a138` unless labeled
otherwise. Finding source: 2026-08-25 audit D3-2/DATA-02
(`reports/repository-audits/2026-08-25-options-validator/agents/03-data-provenance.md:25-31`).
**Owner directive:** Carsyn in-session 2026-08-28 — "finish everything
that's deferred"; DATA-02 ruled "Commission now" via decision prompt.

## Why this exists (plain language)

The daily Schwab capture's verifier proves WHEN the package was downloaded
(the receipt's capture time) but never checks how old each option quote
inside it is. Schwab returns stale quotes for options that haven't traded
recently — the audit sampled ~3,300 rows older than 15 minutes and one from
the prior session. None was selectable, so no harm yet; this brief adds the
missing check #9 from the data-audit standard, WARN-first, with BLOCK
authority owner-gated.

## Verified facts

- Capture persists per-row `timestamp` and `trade_timestamp`
  (`options_researcher/schwab_chain_capture.py:64-65,83-84`).
- `tools/schwab_chain_manifest.py`: `build_manifest` `:85`,
  `verify_session` `:151`, receipt-time check `_captured_at_session` `:60`.
  No per-row age check anywhere in the file.
- `options_researcher/h7_data_gate.py` per-row checks (`NUMERIC_CHAIN_COLUMNS`
  loops `:182,:317`, crossed-market fields `:240`) contain no timestamp-age
  check. Its `CHAIN_STALE` is filename/session-date based, not per-row.
- Frozen-numbers rule: a decision-bearing threshold must be OWNER-TYPED.
  Nothing in this brief may activate blocking with an LLM-proposed number.

## Design (mode-gated, warn-first)

New `config.py` constants (provenance comments required):
- `SCHWAB_QUOTE_AGE_MODE = "warn"` — `"off" | "warn" | "block_selectable"`.
  Default `"warn"` adds visibility only; NO GO/NO_GO outcome may change in
  `off` or `warn` mode (golden-tested).
- `SCHWAB_QUOTE_MAX_AGE_MINUTES = None` — placeholder. The brief SHIPS it
  as `None`; `block_selectable` mode must hard-fail at import/config-load
  if the threshold is `None` (activation is impossible until the owner
  types a number). Candidate values for the owner, ALL labeled
  LLM-proposed, NOT frozen: **10** (tight; risks over-blocking thin names),
  **15** (the audit's sampling boundary; matches the receipt tolerance
  scale), **20** (loose; only catches clearly dead quotes). Prior-session
  timestamps are categorically wrong in an exact-session package and are
  flagged regardless of threshold.

Surfaces:
1. `verify_session` gains a non-fatal per-row age AUDIT: counts of rows
   older than the (configured or candidate-15 informational) age vs the
   receipt capture time, and any prior-session timestamps, reported in the
   verification output. Never changes the verify pass/fail in warn mode.
2. `h7_data_gate` selection path: in `block_selectable` mode ONLY, a
   selectable row with a prior-session quote timestamp or age beyond the
   owner-typed threshold is rejected fail-closed with a named reason code
   (e.g. `QUOTE_STALE`); in `warn` mode the same condition logs/annotates
   without changing selection or GO/NO_GO.

## Scope

**IN:** the two surfaces above + constants + tests.
**OUT (hard stops):** no ledger writes; no registered-hypothesis or receipt
FORMAT change (additive report fields only); no provider calls; no
activation of `block_selectable`; no invented frozen number; no
`tools/daily_ritual.sh` edits; no changes to existing NO_GO reason codes.

## Tests (unittest, offline, synthetic fixtures)

1. Same-session-old selectable row: warn mode → selection unchanged +
   annotation present; block mode (test-injected threshold) → rejected
   with `QUOTE_STALE`.
2. Prior-session selectable row: warn → flagged; block → rejected.
3. Golden: mode `off`/`warn` produce byte-identical gate outcomes to
   current behavior on the existing fixtures.
4. `block_selectable` + `None` threshold → hard config error (fail-closed).

## Acceptance

```
uv run python -m unittest discover -s tests
uv run ruff check . && uv run pyright
```
RED/GREEN demonstrated for tests 1-2. Land via born-draft PR (reconciler
default post-#97); the owner types the threshold and flips the mode in a
SEPARATE owner-controlled commit — an intention to activate is not an
activation.
