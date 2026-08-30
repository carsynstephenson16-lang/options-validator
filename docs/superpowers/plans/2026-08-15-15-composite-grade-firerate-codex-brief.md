# Brief 15 — Composite letter-grade fire-rate receipt + clean grade display

**Date:** 2026-08-15
**Author:** orchestrating Claude session (Fable), 2026-08-15 owner-directed batch
**Executor:** Codex (high reasoning)
**Status:** DRAFT — pending independent adversarial review before hand-off
**Provenance:** Repo-verified against `origin/main` @`58701e9` unless labeled
otherwise.

## Why this exists (plain language)

The composite lane's A/B/C letter grades (`confluence_grade`,
`options_researcher/composite_signals.py:552`) are computed and rendered but
nothing anywhere measures how often each grade even fires. The owner directed
2026-08-15: show the grades firing and clean this up. The cheap honest first
step is a fire-rate receipt — a counted history of how many symbol-days
landed A, B, and C — which is also exactly the base-rate input the
2026-07-24 registration feasibility gate demands if any grade is ever
proposed as a real trigger. This stays display/diagnostic-only.

## Scope

**IN:**
- `tools/composite_grade_firerate.py` — walks cached sessions causally,
  runs the existing `confluence_card()` per symbol-day over
  `config.ATTRACTIVENESS_UNIVERSE` (18 names; the `.tmp/composite_cache/`
  contents cited below are locally verified 2026-08-15 on the main checkout
  — `.tmp/` is gitignored local state, not verifiable at a SHA, and the
  tool must rebuild it via the incremental builder when absent), counts
  grades, writes ONE
  hashed JSON receipt + a small markdown summary under
  `reports/composite_firerate/`. Model the receipt mechanics EXACTLY on
  `tools/h7_schwab_feasibility.py` (`_receipt_hash`, `RECEIPT_KIND`,
  `STACK_VERSION`, canonical-JSON) — that file is the working template
  (Repo-verified).
- Receipt contents: per-grade counts and fractions, pooled AND per-symbol;
  VETO-cap incidence counted separately (a C caused by VETO is not the same
  fact as a C from low alignment); window covered; `max_asof` stamp;
  universe hash; config hash of the two cutoff constants.
- Dashboard cleanup (display only): the grade pill on the composite lane
  additionally shows the receipt's pooled fire-fraction for that grade
  ("A — fires 4% of symbol-days") when a receipt exists, with the receipt
  date; absent receipt ⇒ render exactly as today (no invented numbers).
- Tests (unittest, offline): determinism (same cache ⇒ same receipt hash);
  no-look-ahead invariance (append future rows to a fixture cache ⇒
  historical counts unchanged — mirror `tests/test_composite_signals.py::`
  `test_no_look_ahead_invariance`); VETO-vs-low-alignment C's counted
  distinctly; empty/short cache ⇒ explicit refusal, not zeros.

**OUT (hard):** no ledger writes; no registration; the grades gate/trigger
NOTHING (the lane stays display-only per the 2026-08-03 `.cursorrules`
amendment); no change to `COMPOSITE_GRADE_A_MIN_ALIGNED` /
`COMPOSITE_GRADE_B_MIN_ALIGNED` (config.py:804-832 — their LLM-proposed
provenance labels stay as-is); no network; no change to the frozen
GREEN-fraction baseline; no H5/H6/H7/H8/H10/RQ2/A2 paths.

## Work packages

- **WP-A** receipt tool + receipt schema. Data source: the derived series
  cached in `.tmp/composite_cache/` via `composite_signals.py`'s own
  incremental builder (36 files = 18 symbols × parquet+meta, locally
  verified 2026-08-15 on the main checkout) backed by `.cache/chains/`
  (frozen edge 2026-07-27) and
  `data/underlying_closes.py`. The walk must reuse `confluence_card()`'s own
  as-of truncation — do NOT reimplement the causal logic.
- **WP-B** dashboard grade-pill enrichment + fail-silent-absent behavior.
- **WP-C** tests per IN list.

## Acceptance / verification

```bash
uv run python -m unittest discover -s tests   # exit 0
uv run ruff check . && uv run pyright         # clean
uv run python -m tools.composite_grade_firerate   # writes receipt, prints summary
```

Done = receipt reproducibly hashes, counts A/B/C + VETO split over the full
cached window for 18 names, dashboard shows fire-fractions sourced ONLY from
the receipt. Feasibility-gate use of the numbers is a later owner decision,
not this brief.
