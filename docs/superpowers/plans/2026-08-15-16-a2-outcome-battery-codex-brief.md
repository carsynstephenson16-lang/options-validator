# Brief 16 — A2 outcome battery: historical exploratory runner (EX8, updated)

**Date:** 2026-08-15
**Author:** orchestrating Claude session (Fable), 2026-08-15 owner-directed batch
**Executor:** Codex (high reasoning)
**Status:** DRAFT — pending independent adversarial review before hand-off
**Provenance:** Repo-verified against `origin/main` @`58701e9` and branch
`claude/monday-ship-2026-08-15` unless labeled otherwise. Supersedes the EX8
stub in `docs/superpowers/plans/2026-07-23-codex-execution-queue.md:176-188`
(which predates the universe growth and cites stale bucket sizes).

## Why this exists (plain language)

A2-v1 (ledger seq 19, registered 2026-07-23, zero code) answers the owner's
actual question: do the scanner's top-ranked names produce better trades than
its bottom-ranked names, after realistic costs — measured separately for five
trade styles. This brief builds the HISTORICAL EXPLORATORY pass only. The
registration itself says: "Historical results are Card-3-class exploratory
only; the forward window is verdict-bearing." Every output must carry that
exploratory label; nothing here produces or implies a verdict.

## Binding definitions

From ledger seq 19 + `ledger/facts.log` `RQ2_A2_PIN_ADDENDUM_V1` (2026-07-23),
Repo-verified:

- Five lanes scored separately: CSP, CC, PMCC, LEAPS, tactical.
- CSP has five separately-registered exit arms (50% credit capture; close at
  21 DTE; fixed 10-session horizon w/ early-expiration completeness clause;
  breach-defensive; assignment-accepting). A roll = close trade 1 + open
  trade 2.
- CC reports short-call / stock / combined / combined-minus-stock /
  assignment incidence / lost upside separately. PMCC reports both legs,
  combined, return on committed capital, per-cycle, assignment exposure;
  empty lane = "no data", never zero.
- LEAPS marks at 21/63/126 sessions; tactical at 5/10/20.
- Costs: the frozen repo cost model (adverse fill, spread, commission,
  liquidity, annualization) + ±50% cost-stress arm.
- Buckets: terciles of the frozen GREEN-fraction ranking
  (`options_researcher/rq1_runner.py:48` `green_fraction` is the existing
  scorer — reuse, do not reimplement). Weekly non-overlapping cohorts feed
  the statistic; the staggered book is descriptive-only.
- Statistics: Holm step-down α=0.10, one-sided top-beats-bottom;
  `MIN_ADVERSE_BOTTOM_BUCKET = 10` — freeze this into `config.py` with
  provenance "owner-forwarded 2026-07-23 per ledger seq 19" (it currently
  exists only as ledger text).
- **Universe: the current 18-name `config.ATTRACTIVENESS_UNIVERSE`, terciles
  of 6** — owner ruling 2026-08-15 (in-session, supersedes the addendum's
  "15-name board gives 5 per bucket" wording; growth to 18 disclosed;
  amendment drafted in `reports/2026-08-15-rq2-a2-amendment-drafts.md`,
  pending review then append). Implementation-time check: verify the
  amendment record exists (grep for `A2_AMENDMENT_V1_1`, read-only); if
  absent, run in `PENDING_AMENDMENT` mode (outputs stamped, not
  presentable as registered-design results).

## Scope

**IN:** `options_researcher/a2_runner.py` + lane modules as needed; config
constants w/ provenance; dated outputs under `reports/a2/<date>/` stamped
"CARD-3-CLASS EXPLORATORY — NOT VERDICT-BEARING" + max as-of (cache edge
2026-07-27) + config hash; tests (unittest, offline): cost-model parity with
the frozen conventions, bucket assignment determinism, no-look-ahead
invariance, empty-lane "no data" rendering, ±50% stress arms present,
INSUFFICIENT_SAMPLE labeling below the adverse gate.

**OUT (hard):** no ledger writes; no verdict, promotion, or rejection text
anywhere in output; no forward-window code; no network; no changes to frozen
cost constants; no touching the GREEN-fraction recipe; no H7 paths.

## Work packages

- **WP-A** bucket construction from historical board rankings (causal: each
  weekly cohort uses only data at/before its formation date) + cohort
  calendar.
- **WP-B** lane simulators (CSP arms first — they carry the most registered
  structure), reusing the repo's existing fill/cost helpers (cite exact
  functions at implementation; do not fork the cost model).
- **WP-C** statistics + Holm + adverse-count gate + INSUFFICIENT_SAMPLE
  labeling; ±50% stress.
- **WP-D** report writer + tests.

## Acceptance / verification

```bash
uv run python -m unittest discover -s tests   # exit 0
uv run ruff check . && uv run pyright         # clean
uv run python -m options_researcher.a2_runner --historical  # full exploratory pass on the frozen cache
```

Done = one reproducible historical pass over the frozen cache
(2018→2026-07-27), five lanes, all disclosures present. The verdict-bearing
forward window is OUT of scope and separately gated.
