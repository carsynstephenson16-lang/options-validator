# Dual-path orchestration: H9 historical study + Stage-8 readiness (design)

**Date:** 2026-07-16. **Owner-approved approach A** (three parallel tracks,
gated merges) in the 2026-07-16 orchestration session. Companion spec:
`2026-07-16-h9-post-earnings-historical-study-DRAFT.md`.

## Goal

Begin verdict-bearing work immediately, so the 2026-07-29 ThetaData expiry
stops being the binding constraint, without weakening any registered gate.
Two owner-selected decisions shape everything:

1. **Data:** research provider alternatives BEFORE any renewal spend
   (owner choice 2026-07-16).
2. **Review model:** hybrid — in-session adversarial subagent review for
   build steps; the owner's external deep-research review reserved for the
   two irreversible gates (H9 registration freeze, Stage-8 activation).

## Roles

- **Orchestrator (this session):** writes specs and agent briefs, verifies
  every review finding against the code, reviews every diff before commit,
  drafts every ledger fact for owner approval. Does not delegate spec
  authorship.
- **Opus subagents:** provider research (Track 1), all adversarial reviews.
- **Sonnet subagents:** structured implementation + tests (census tool, H9
  runner glue, Stage-8 schema/guard).

**Hook disclosure:** subagents spawned from the orchestration session do not
inherit this repo's PreToolUse hooks. Mitigations: the H7 tombstone and all
refusal gates are in-code and fire regardless of caller; agents are
prohibited from writing `ledger/facts.log` directly (appends only via repo
tooling, owner-approved); the orchestrator reviews all diffs; no live-order
path exists in the repo.

## Track 1 — data continuity (Opus, research only)

Evaluate EOD option-chain providers against frozen requirements: real NBBO
at session close, full chains for the active universe, history availability,
monthly cost, integration effort, and what a provider switch means as a
disclosed amendment to the frozen cost model. Candidates: ThetaData renewal
(baseline), Polygon, ORATS, CBOE DataShop, dxFeed, marketdata.app.
Deliverable: a decision table; the owner picks. Also: verify the daily
preservation top-up stays green through 2026-07-29 (registered preservation
scope, `THETADATA_EXIT_DATE_UPDATE`). No subscription is purchased by any
agent under any circumstances.

## Track 2 — H9 registration and single run

Sequence: DRAFT spec (done, orchestrator-written) → owner types §5 values →
freeze + `H9_REGISTERED` (trial 11→12) → owner's external review clears the
freeze → Sonnet builds census + runner test-first (test matrix in spec §8) →
Opus adversarial review, orchestrator verifies → census → one run →
adjudication → `H9_RESULT`. Zero new data spend is a hard property. If the
census returns INSUFFICIENT_SAMPLE, that is the verdict and the track ends
honestly.

## Track 3 — Stage-8 build (build-only, inactive)

Disclosed deviation from the readiness packet's §5 ordering: implementation
of the `window_registration` schema + activation guard proceeds before the
owner's §3 window inputs, because those values are runtime inputs to the
registration event, not to the schema code. Recorded as an owner-authorized
ledger fact citing the owner's 2026-07-16 directive. Everything stays
inactive: real forward ledger `VALID EMPTY`, no scheduler, no real event.
Opening the window still requires ALL of: Track-1 provider decision; clean
bound commit; whole-universe gates green on the latest session; all seven §3
values typed by the owner; the owner's external review.

## Gates the owner personally holds

1. Provider choice (Track 1).
2. H9 §5 typed values.
3. External review #1 — H9 registration freeze.
4. External review #2 — Stage-8 activation.
5. Every ledger fact.

## Failure handling

Any agent finding that contradicts a ledger fact halts its track and
escalates. All builds test-first; full offline suite + ruff + pyright must
pass before the orchestrator accepts a diff. Reviews are adversarial by
brief ("show how this could be lying"). "No edge" and INSUFFICIENT_SAMPLE
are successful outcomes.
