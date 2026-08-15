# Brief 14 — RQ2 badge build (B1 daily corner, A1 bounce, V1 calibration display) + forward recorder

**Date:** 2026-08-15
**Author:** orchestrating Claude session (Fable), 2026-08-15 owner-directed batch
**Executor:** Codex (high reasoning)
**Status:** DRAFT — pending independent adversarial review before hand-off
**Provenance:** Repo-verified against `origin/main` @`58701e9` and branch
`claude/monday-ship-2026-08-15` @`22e801d` unless labeled otherwise.

## Why this exists (plain language)

RQ2-v1 is a registered research question (ledger seq 18, amended seq 25) with
zero code: three candidate scanner badges must be computed daily and later
scored against what actually happened. The owner directed on 2026-08-15:
build the badges now, fire B1 daily on every name (not only near earnings),
and open the forward window Monday 2026-08-17. This brief builds the badge
modules and the daily forward recorder. It closes the "badge modules not yet
built" gap named in ledger seq 25 and README "Scope status".

## Binding definitions — read the LEDGER, not the old draft

The 2026-07-22 briefs doc's delegated-values table is WRONG in four places;
its 2026-08-15 correction banner (this branch @`22e801d`) lists them. Binding
values (Repo-verified, `ledger/experiments.jsonl` seq 18 owner-typed
2026-07-23; seq 25 owner-ruled 2026-08-10):

- **B1 corner:** `ts_pctl >= 0.75` AND `vrp_pctl <= 0.25`.
- **A1 bounce:** `dist_52w_high <= -0.20` AND `mom_1m > 0` AND
  `rv21 percentile >= 0.70`.
- **K = 3:** B1, A1, V1 — V1 is membership-only; its scoring statistic is NOT
  pinned; **the runner MUST refuse any V1 comparison** until a further
  pre-result amendment pins it (seq 25 verbatim requirement).

Owner rulings 2026-08-15 (in-session; amendments drafted in
`reports/2026-08-15-rq2-a2-amendment-drafts.md`, pending adversarial review
then append via the typed ledger API — Codex does NOT touch the ledger):

- **B1 fires daily on every name.** The earnings gate is removed as a gate;
  earnings proximity is recorded as a mandatory per-row study column
  (`earnings_tag`: "event-priced" / "no earnings in window" / "UNKNOWN",
  fail-visible on unknown). Owner wording: "i dont want that to fire if
  theres confirmed earnings i want that fired daily and studied."
- **Forward window opens 2026-08-17** (first scored session). The
  2026-09-01 date printed in older docs was never a ledger value.
- **Price source:** daily 15:45 ET preclose Schwab chain captures
  (`reports/schwab_chains/<date>/preclose.json` receipts +
  `.cache/schwab_chains/<SYM>_<date>.parquet`), verified-receipt-gated.

**Implementation-time check (REQUIRED):** before wiring any of the three
2026-08-15 rulings as active behavior, verify the corresponding amendment
record exists in the ledger (grep `ledger/experiments.jsonl` for
`RQ2_AMENDMENT_V1_2` — read-only). If absent, the recorder must run in
`PENDING_AMENDMENT` mode: compute and write everything, but stamp every
output `amendment_pending: true` and refuse to label any output as
window-official. Fail closed, never silent.

## Scope

**IN:**
- `options_researcher/rq2_badges.py` — pure functions: `ts_slope`, `ts_pctl`,
  `vrp_pctl`, `corner_flag` (B1); `dist_52w_high`, `mom_1m`, `rv21_pctl`,
  `bounce_flag` (A1); V1 calibration pair series (display values only).
- `options_researcher/rq2_recorder.py` — daily runner: loads the newest
  verified preclose capture + `data/underlying_closes.py`, computes all three
  badges for `config.ATTRACTIVENESS_UNIVERSE` (18 names), writes one dated
  JSON + one markdown row-table under `reports/rq2/<date>/`, stamped with
  max as-of session, capture receipt path, `config_hash`, and
  `amendment_pending` flag. Idempotent per date; refuses to overwrite.
- Constants in `config.py`, each with provenance comment citing ledger seq
  (owner-typed) — no new invented numbers. Percentile lookbacks/min-obs reuse
  the BS-spec conventions already cited in the 2026-07-22 brief body
  (252 trailing / min 60, LLM-proposed 2026-07-24 delegated — label them so).
- `tests/` — unittest, offline: threshold boundary cases both sides for B1
  and A1; V1-comparison refusal test (any code path that would compare or
  rank on V1 raises); no-look-ahead invariance (future rows don't change
  historical values — mirror `tests/test_composite_signals.py`
  `test_no_look_ahead_invariance`); PENDING_AMENDMENT fail-closed test;
  missing/stale capture ⇒ per-name `DATA_BLOCKED`, never a silent skip.

**OUT (hard):** no ledger writes of any kind; no registration or amendment
appends; no verdict/scoring/bucket-spread computation (that is a later,
separately-gated runner); no change to any frozen value; no network calls —
tests run against fixtures/cache only; no live-order paths; no changes to
the frozen GREEN-fraction baseline ranking or the attractiveness dashboard
default view; no H7 paths.

## Work packages

- **WP-A** `rq2_badges.py` + config constants + unit tests (offline
  fixtures). Acceptance: boundary tests prove `0.75/0.25` and
  `>0 / 0.70 / -0.20` exactly (a value AT the threshold behaves per ledger
  text's `>=`/`<=`).
- **WP-B** `rq2_recorder.py` + receipt-gated capture loading + dated outputs
  + `amendment_pending` logic. Acceptance: run against the real 2026-08-14
  capture produces 18 rows (or honest per-name `DATA_BLOCKED`), stamped and
  idempotent.
- **WP-C** V1 display series (median implied-vs-realized gap over completed
  cycles + post-earnings IV-drop history, exactly as described in the
  2026-07-22 brief §V1) with `min completed cycles = 6` (LLM-proposed
  2026-07-24, label it) — rendered as columns, NEVER ranked or compared;
  refusal enforced in code and tested.
- **WP-D** wire the daily invocation into the existing preclose flow the same
  way the display-freshness lane consumes captures (read-only consumer; do
  NOT modify `schwab_chain_capture` itself).

## Acceptance / verification

```bash
uv run python -m unittest discover -s tests   # exit 0
uv run ruff check . && uv run pyright         # clean
uv run python -m options_researcher.rq2_recorder --date 2026-08-14  # 18 rows or honest blocks
```

Every constraint above is Repo-verified at the cited commits except where
labeled LLM-proposed/owner-worded. Merge timing, ledger appends, the V1
statistic pin, and anything owner-typed stay with the owner.
