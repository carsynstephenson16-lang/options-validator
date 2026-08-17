# Owner directives — 2026-08-16 (in-session, evening)

**Provenance:** owner-directed in-session 2026-08-16. Owner wording (verbatim,
sic): "check out pr 51 merge and teh briefs review and sign off use sonnet and
opus agemts. also reopen h10a and 10b as well as h5 dont have it as alert only
watchlsit". Drafting and recording of the resulting amendments follows the
owner-delegated standing 2026-07-25 (independent adversarial review + Fable
sign-off required before any append). This report is the dated
source-of-record for these directives, per the 2026-08-14/15 decision-report
precedent.

## Directive 1 — PR #51 merge

**Status: already satisfied before this session acted.** PR #51 (Brief 13,
Lane Board dashboard) merged 2026-08-15 20:07 ET with all three CI checks
green (Offline Quality Gates, Claude PR Review, Secret Scan). No action taken
here beyond verification. The ops checkout was verified in this session to sit
exactly at `origin/main` (`f1fd4bd`), so the preclose alignment guard is
satisfied for Monday 2026-08-17.

## Directive 2 — briefs 14–16 review and sign-off (Sonnet + Opus agents)

Briefs 14–16 and the RQ2/A2 amendment drafts landed in PR #52 with a two-round
adversarial review receipt
(`reports/2026-08-15-monday-ship-adversarial-review-receipt.md`) and ledger
appends seq 26–27. Per this directive, an independent Opus-model verification
review was run 2026-08-16 re-checking blockers B-1..B-5, a sample of fixes
F-1..F-19, binding-values consistency against ledger seq 26/27, and the hash
chain. Its verdict and the resulting Fable sign-off are recorded in
`reports/2026-08-16-briefs-14-16-fable-signoff.md`.

## Directive 3 — reopen H10a

**Constraint (append-only ledger):** H10a's closure was ratified and recorded
2026-08-16 (facts.log `H10A_RESULT`, PR #57): verdict INSUFFICIENT_SAMPLE —
STARVED, 0 trades. A recorded adjudication cannot be un-recorded, and the repo
precedent for a restarted trial after adjudication is the H7 rule: **restart
requires a new registration and a new namespace** (OD-3 precedent). The
recorded H10A_RESULT stands as history and is not contradicted by reopening.

**Action:** a re-registration packet draft for **H10a-v2** is prepared at
`docs/superpowers/plans/2026-08-16-h10a-v2-reregistration-packet-DRAFT.md`.
Registration itself remains owner-typed (new registrations were never
delegated), and must pass the 2026-07-24 feasibility gate or carry an explicit
owner starvation pre-acceptance (the H7 V0 precedent, owner-ruled 2026-08-16,
is the template). Nothing is registered by this session.

## Directive 4 — reopen H10b

H10b (seq 16) was never closed; its registration stands. What "reopen" means
operationally: resume daily observation, which is currently impossible
because (a) the 2026-08-14 owner ruling D-1=F1 paused all hypothesis lanes
behind the H7 data gate, and (b) the watcher reads the frozen ThetaData chain
cache, which ended 2026-07-27. This directive is recorded as the owner
overriding D-1=F1 **for H10b specifically**. A pre-result amendment draft
(H10B_AMENDMENT_V1_1: data-source substitution to the Schwab 15:45 preclose
chain captures + observation resumption) is at
`reports/2026-08-16-h10b-h5-amendment-drafts.md`. H10b has zero results, so
this is a pre-result amendment and is delegable after adversarial review +
Fable sign-off. Actual resumption additionally requires implementation
(watcher re-pointing + ritual gating), which goes to Codex as a brief; until
that lands, H10b remains observation-paused in fact even once amended in form.

## Directive 5 — H5 no longer alert-only

H5's alert-only character is part of its registered design (2026-07-04) and
its watcher is read-only by construction. The directive is read as: H5 alerts
should become recordable paper positions, not just terminal messages. Honest
split, because the registration froze caps for only part of H5:

- **Defined-risk side (LEAPS core + tactical calls):** frozen caps exist
  (owner-typed 2026-07-04: $10k/name, $16k LEAPS total; $600 defined-risk per
  tactical trade). A pre-result amendment (H5_AMENDMENT_V1: paper-position
  recording path for these structures) is drafted in
  `reports/2026-08-16-h10b-h5-amendment-drafts.md` and is delegable.
- **Income side (cash-secured puts / covered calls / PMCC):** collateral-scale
  risk with **no owner-typed cap in existence** (the $600 cap structurally
  does not apply; see config.py CSP collateral note and the 2026-07-23
  program's cap-class distinction). Inventing that cap is prohibited
  (owner-typed numbers only), so the income side **stays alert-only until the
  owner types a collateral cap**. The amendment draft states this boundary
  explicitly.

**Known unresolved tension, surfaced not solved:** H5's frozen LEAPS total cap
($16k) exceeds the whole-portfolio risk sleeve ($14k). This predates today and
is flagged for an owner decision; no number is changed here.

## What remains owner-only after this session

1. Type/ratify the H10a-v2 registration (packet draft prepared).
2. Type a collateral cap if the H5 income side should ever record positions.
3. Resolve the $16k-vs-$14k cap tension.
4. Weekend Schwab re-auth before ~2026-08-19 00:56 ET token death.
