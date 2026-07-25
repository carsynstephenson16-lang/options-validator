# Final report — intraday volume periodicity for the attractiveness scanner

- **Workflow run:** 2026-07-24 (research fan-out) → 2026-07-25 (decision,
  verification, synthesis). Research cutoff for web evidence: 2026-07-24;
  verifier spot-checks re-fetched key pages 2026-07-25.
- **Branch:** `feature/strategy-enhancement` (created from
  `docs/replan-2026-07-22` @ `eb927c8`; nothing committed — commits are
  owner-gated).

## 1. Main decision

**`RESEARCH-VALID, IMPLEMENTATION-REJECTED`.** Intraday volume periodicity is
a real, well-documented phenomenon, but it cannot be honestly implemented in
this repo today: no free live data source with full-market coverage exists,
no source connects the signal to options selection, and the repo's
architecture (EOD-grain features, 5 discrete live snapshots/day) cannot host
it as a focused change. No production code was written — by design, and
git-verified by an independent adversarial pass.

## 2. Decision-gate outcome (detail: `.research/decision.md`)

- **C1, intraday volume periodicity (anchor):** FAILS gates 1 (free live
  inputs), 2 (terms on the inputs that matter), 5 (mechanism to options
  selection), 6 (architecture fit), 9 (risk/value); passes 3 and 4;
  7–8 partial/moot.
- **C2, options OI-change display line (lead alternative):** PASSES gates
  1–8 with primary evidence; FAILS gate 9 only for *direct implementation
  this session* — badge thresholds are frozen-number work the owner types,
  and five owner-reviewed RQ2 badges are already queued. Routed to a
  ready-to-ratify brief instead.

## 3. Lead candidate and runner-up

- **Lead:** C2 — per-card open-interest build-up context line (zero new
  data; live endpoint probe-confirmed entitled; look-ahead-free by the
  adapter's documented design). Brief:
  `.research/05_lead_candidate_brief.md`.
- **Runner-up (parked):** C4 — IV skew steepness (strike-axis smirk slope;
  strongest peer-reviewed mechanism of the batch, Xing/Zhang/Zhao 2010, JFQA;
  needs a frozen strike/tenor convention and a small-universe
  external-validity memo first).

## 4. Reason for rejection (C1, condensed)

1. **Data:** ThetaData live stock endpoint is PERMISSION_DENIED on the
   current FREE stock tier (primary evidence:
   `reports/live_probe/2026-07-24.json`). QuantConnect's minute data is free
   only inside its cloud — local download needs a paid tier + per-file
   credits under an internal-LEAN-only, no-conversion license; live needs a
   paid tier + paid node. Yahoo scraping is ToS-prohibited. Alpha Vantage
   free is 25 req/day and non-live. Polygon free is EOD-batch. The only $0
   real-time feed (Alpaca Basic, IEX) carries ~3–6% of consolidated volume —
   insufficient coverage for a volume-shape signal. Verifier independently
   confirmed and additionally ruled out Databento/Cboe One/Nasdaq Basic.
2. **Mechanism:** no fetched source ties periodicity to option IV, skew,
   direction, or strike choice; the one defensible link (execution timing)
   is unusable at 5 snapshots/day.
3. **Architecture:** the signal needs continuous intraday ingestion; the
   repo's feature layer is one-row-per-day by construction.

## 5. Repository architecture findings (detail: `.research/04_repo_architecture.md`)

No typed Signal abstraction exists — badges are dict keys graded by
`grade()` (`options_researcher/attractiveness.py:26`); per-day scalars live
in `options_researcher/features.py` (EOD store, `.tmp/research/attractiveness`);
ranking is GREEN-fraction lexicographic
(`attractiveness_dashboard.py::_display_quality_key`); freshness/eligibility
flow through `top3_snapshot.py` with a consistently-applied `DATA_BLOCKED`
fail-visible pattern; the scanner is presentation-layer and provably
disconnected from the Lumibot backtest path; all five RQ2-planned badges are
confirmed not yet implemented.

## 6. Code changes

**None to production code.** Files created/changed (all docs/research):

- Created: `.research/00_baseline.md`, `01_periodicity.md`,
  `02_licensing.md`, `03_strategy_candidates.md`, `04_repo_architecture.md`,
  `decision.md`, `05_lead_candidate_brief.md`, `07_verification.md`,
  `final_report.md` (this file); daily note `2026-07-25.md` (gitignored).
- Modified: `ideas-parking-lot.md` — pure append at end of file (three
  parked entries dated 2026-07-25).
- NOT touched by this workstream (pre-existing, other sessions'):
  `docs/superpowers/plans/2026-07-22-rq2-scanner-enrichment-briefs.md`
  (modified before this workstream began; verifier confirmed content
  unrelated) and `reports/live_probe/` (consumed read-only as evidence).

## 7. Tests added

None — correct for a rejected implementation (the workflow forbids
placeholder code). The brief specifies the full test plan for if/when the
owner ratifies: formula tests, causal truncation property, UNKNOWN paths,
thin-base handling, timestamp boundaries, and the byte-identical-board
acceptance test.

## 8. Verification commands and results

| Stage | Command | Exit | Result |
|---|---|---|---|
| Baseline (2026-07-24) | `uv run ruff check .` | 0 | All checks passed |
| Baseline | `uv run pyright` | 0 | 0 errors/warnings |
| Baseline | `uv run python -m unittest discover -s tests` | 0 | Ran 1774 tests, OK |
| Post-change (2026-07-25) | `uv run python -m unittest discover -s tests` | 0 | Ran 1774 tests in 199.3s, OK |
| Post-change | `uv run ruff check .` | 0 | All checks passed (also re-run independently by verifier) |
| Post-change | `uv run pyright` | 0 | 0 errors |

Zero new failures vs. baseline (docs-only changes, as expected).

## 9. Pre-existing failures

None. The repo was fully green at baseline and remains fully green.

## 10. Remaining risks and unanswered questions

- The QuantConnect research page's exact backtest numbers and dataset name
  were never independently corroborated (SSRN 403; AI-summarized fetches) —
  deliberately treated as non-load-bearing.
- ThetaData stock-tier exact pricing is ambiguous across fetches (paid is
  certain; the amount is not) — matters only if the owner later considers
  the upgrade that would un-park C1.
- The C2 brief's mechanism is a disclosed adaptation (literature is
  option-volume-based, not OI-based); the brief therefore ships it as
  neutral context with no validity claim.
- Whether `option_snapshot_trade` (true volume-based put/call ratio, C3) is
  entitled remains untested.
- Minor audit gaps recorded and dispositioned in `decision.md`'s
  post-verification addendum (14-vs-15 wording; Databento/Cboe One/Nasdaq
  Basic enumerated post-hoc by the verifier, all paid).

## 11. Git branch and working-tree status

Branch `feature/strategy-enhancement`, nothing committed. Working tree:
`ideas-parking-lot.md` modified (this workstream's append), RQ2 briefs doc
modified (pre-existing, other workstream), `.research/` and
`reports/live_probe/` untracked. Verifier's adversarial verdict on the whole
decision: **UPHELD-WITH-CORRECTIONS** (0 critical, 0 major, 3 minor — all
dispositioned).

## 12. Owner actions (if desired — none required)

1. Ratify (type) the four proposed constants in
   `.research/05_lead_candidate_brief.md` → hand to Codex alongside the RQ2
   queue, or fold the brief into the RQ2 doc.
2. Decide whether to commit this branch's research artifacts.
3. If intraday volume ever becomes interesting again: the un-park gates are
   in `ideas-parking-lot.md` (paid feed + pre-registered mechanism first).
