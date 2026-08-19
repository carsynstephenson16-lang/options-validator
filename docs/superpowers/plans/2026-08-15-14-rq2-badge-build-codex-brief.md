# Brief 14 — RQ2 badge build (B1 daily corner, A1 bounce, V1 calibration display) + forward recorder

**Date:** 2026-08-15
**Author:** orchestrating Claude session (Fable), 2026-08-15 owner-directed batch
**Executor:** Codex (high reasoning)
**Status:** NOT READY FOR HAND-OFF — round-3 adversarial review (2026-08-16,
independent Opus pass) returned FAIL with two feasibility blockers that text
edits cannot close: **BL-1** (B1's `ts_pctl`/`vrp_pctl` need a 252-session
IV/percentile history; the Schwab preclose lane has ~1 session as of 08-16
and splicing ThetaData IV onto Schwab IV is fabrication per
`schwab_chain_view.py` — B1 is UNAVAILABLE-by-construction for months unless
a further pre-result amendment sets its disposition) and **BL-2** (the
preclose capture universe is 15 names; AMAT/CLSK/NBIS of the registered
18-name board are never captured, so the executable options-derived board is
15 — needs an owner-gated capture-universe expansion or a further amendment).
Round-3 text fixes BL-3/BL-4 are applied in this revision. Do not hand to
Codex until BL-1/BL-2 have a recorded disposition.
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
- **K = 3:** B1, A1, V1 (seq 25). Seq 25 required the runner to refuse any
  V1 comparison until a pre-result amendment pins V1's statistic (faithful
  paraphrase — read seq 25 for the exact wording). That pin is Block 1
  clause (5) of `reports/2026-08-15-rq2-a2-amendment-drafts.md`
  (`RQ2_AMENDMENT_V1_2`). **Gate the refusal on the pin's presence:** if
  `RQ2_AMENDMENT_V1_2` exists in the ledger, V1 computes the pinned line-1
  statistic (and still refuses any BLENDED comparison — the 50/50
  destination in clause 5b needs its own future amendment); if the
  amendment is absent, V1 refuses all comparisons, as before. Both branches
  test-enforced.

Owner rulings 2026-08-15 (in-session; amendments drafted in
`reports/2026-08-15-rq2-a2-amendment-drafts.md`, pending adversarial review
then append via the typed ledger API — Codex does NOT touch the ledger):

- **B1 fires daily on every name.** The earnings gate is removed as a gate;
  earnings proximity is recorded as a mandatory per-row study column
  (`earnings_tag`: "event-priced" / "no earnings in window" / "UNKNOWN",
  fail-visible on unknown). Source (round-3 fix FX-2): the existing
  `options_researcher/h7_earnings.py` promoted store with its provenance
  labels — do NOT invent a new earnings loader or window; the event-window
  definition is the frozen one (evaluation date < report date < near-leg
  expiration) and gets a unit test. Owner wording: "i dont want that to fire if
  theres confirmed earnings i want that fired daily and studied."
- **Forward window opens 2026-08-17** (first scored session). The
  2026-09-01 date printed in older docs was never a ledger value.
- **Price source:** daily 15:45 ET preclose Schwab chain captures
  (`reports/schwab_chains/<date>/preclose.json` receipts +
  `.cache/schwab_chains/<SYM>_<date>.parquet`), verified-receipt-gated.

**Implementation-time check (REQUIRED, FAIL-CLOSED — review blocker B-5):**
before wiring any of the three 2026-08-15 rulings as active behavior, verify
the amendment record exists in the ledger (grep `ledger/experiments.jsonl`
for `RQ2_AMENDMENT_V1_2` — read-only). If absent, the recorder REFUSES to
write to the official output tree entirely. It may write diagnostics ONLY
under `reports/rq2/dryrun/<date>/`, and any session recorded there is
**permanently excluded from the scored window** — the future scorer must
hard-refuse to read anything under `dryrun/` (enforce with a test). The
scored window's first admissible session is the LATER of the registered
open date (2026-08-17) and the first session on/after the amendment's
append timestamp. No pre-amendment row can ever be retroactively counted.

## Scope

**IN:**
- `options_researcher/rq2_badges.py` — pure functions: `ts_slope`, `ts_pctl`,
  `vrp_pctl`, `corner_flag` (B1); `dist_52w_high`, `mom_1m`, `rv21_pctl`,
  `bounce_flag` (A1); V1 calibration pair series (display values only).
- `options_researcher/rq2_recorder.py` — daily runner: loads the newest
  verified preclose capture + `data/underlying_closes.py`, computes all three
  badges for `config.ATTRACTIVENESS_UNIVERSE` (18 names; round-3 fix FX-3:
  stamp a universe hash in every output like brief 15 does, and add a freeze
  test so a display-layer edit to the list cannot silently change this
  registered forward window's universe), writes one dated
  JSON + one markdown row-table under `reports/rq2/<date>/`, stamped with
  max as-of session, capture receipt path, `config_hash`, and
  `amendment_pending` flag. Idempotent per date; refuses to overwrite.
- Constants in `config.py`, each with provenance comment citing ledger seq
  (owner-typed) — no new invented numbers. Percentile construction:
  252-session trailing lookback with **min-obs 126**, ALIGNED to the repo's
  own conventions (`features.PCT_MIN_OBS = 126`,
  `COMPOSITE_PCTL_MIN_OBS = 126`) rather than the 2026-07-22 brief body's
  min-60 draft — a badge firing on half the history every other lane
  requires would be an unexplained inconsistency (review fix F-3; value
  LLM-proposed 2026-08-15 by alignment, label it so). Names below min-obs
  render the percentile as UNAVAILABLE, fail-visible.
- `tests/` — unittest, offline: threshold boundary cases both sides for B1
  and A1; V1 gated-refusal tests matching the K=3 bullet above (round-3 fix
  BL-3: with `RQ2_AMENDMENT_V1_2` present, V1 computes the pinned line-1
  statistic and any RANKING or BLENDED-comparison path raises; with the
  amendment absent, ALL V1 comparison paths raise — both branches
  test-enforced); no-look-ahead invariance (future rows don't change
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
- **WP-C** V1 display series. BINDING SPEC (round-3 fix BL-3): ledger seq 26
  clause (5a) — NOT the 2026-07-22 brief §V1, whose cycle definition,
  `VRP_CAL_*` constants, and UNKNOWN-earnings handling are SUPERSEDED. The
  pinned line-1 statistic: monthly `E_k→E_k+1` earnings-to-earnings cycles,
  median implied-vs-realized gap, sample std ddof=1, 252-session
  annualization, 24-cycle cap, UNKNOWN earnings dates render fail-visible
  (never guessed, never silently excluded); `min completed cycles = 6`
  (pinned by seq 25, 2026-08-10; originally LLM-proposed). Rendered as
  columns; ranking/blended-comparison refusal per the K=3 bullet's gated
  rule, enforced in code and tested.
- **WP-D** wire the daily invocation into the existing preclose flow the same
  way the display-freshness lane consumes captures (read-only consumer; do
  NOT modify `schwab_chain_capture` itself). HARD ISOLATION (review fix
  F-4): a failure anywhere in `rq2_recorder` must be INCAPABLE of changing
  the capture lane's exit status or receipts — invoke after and independent
  of the capture's own success path, never inside it; test this. NOTE FOR
  THE OPERATOR: this lands new code that the 15:45 ops flow runs, so the ops
  checkout must be fast-forwarded to the merged main BEFORE the next 15:45
  ET session, per the alignment guard and runbook rule R1.

## Acceptance / verification

```bash
uv run python -m unittest discover -s tests   # exit 0
uv run ruff check . && uv run pyright         # clean
uv run python -m options_researcher.rq2_recorder --date 2026-08-14  # 18 rows or honest blocks
```

Every constraint above is Repo-verified at the cited commits except where
labeled LLM-proposed/owner-worded. Merge timing, ledger appends, the V1
statistic pin, and anything owner-typed stay with the owner.
