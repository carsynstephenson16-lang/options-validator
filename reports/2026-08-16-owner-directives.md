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
Lane Board dashboard) merged 2026-08-15 22:23 ET (`mergedAt`
2026-08-16T02:23:23Z; corrected per review FX-E — the earlier "20:07" was a
CI-check completion time, not the merge) with all three CI checks green
(Offline Quality Gates, Claude PR Review, Secret Scan). No action taken
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

**Constraint (append-only ledger):** H10a's closure was ratified 2026-08-15
(owner selected "Write it today" in-session) and the `H10A_RESULT` fact was
appended 2026-08-16T23:36Z (PR #57) — two distinct dates, stated separately
per review FX-F; the fact's own text is internally dated 2026-08-15. Verdict:
INSUFFICIENT_SAMPLE — STARVED, 0 trades. A recorded adjudication cannot be un-recorded, and the repo
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

*(Section rewritten 2026-08-17/18 per confirmation-round NEW-7 — the original
rev-1 reading, "H5 alerts should become recordable paper positions," was
SUPERSEDED by the owner's Q4 answer below and is retained only in git
history.)*

The owner's ruling (Q4 + explicit option selection, recorded below): the
frozen H5 entry trigger is RETIRED and H5 becomes a daily OBSERVER on the
Schwab lane while it ramps — no fires, no paper entries, until the owner
types a new entry rule. `H5_AMENDMENT_V1` (rev 3 in
`reports/2026-08-16-h10b-h5-amendment-drafts.md`) records exactly that:
trigger retirement with a named supersession, observe mode, no recording
path enacted.

Cap facts, correctly attributed (review FX-B): the $10k/name and $16k total
thesis-bucket caps are `H4_THESIS_MAX_PREMIUM_PER_NAME`/`_TOTAL` — a SHARED
H4/H5 bucket, the $16k dated 2026-07-06, provenance advisory/un-chained per
its own config comment; not H5-specific owner-typed caps of 2026-07-04. The
income side (cash-secured puts / covered calls / PMCC) remains display-only
with **no owner-typed collateral cap in existence**; inventing one is
prohibited.

**Known unresolved tension, surfaced not solved:** the shared thesis-bucket
total cap ($16k) exceeds the whole-portfolio risk sleeve ($14k). This
predates today and is flagged for an owner decision; no number is changed
here.

## Owner confirmations required BEFORE any amendment append (review FX-G/FX-H)

The five directives above derive from one owner sentence; per the 2026-08-15
N-1 precedent, the interpretive choices are put back as explicit questions.
No amendment is appended until these are answered (each defaults to "the
drafted reading" only if the owner says so):

- **Q1 — H10a:** proceed with a NEW registration H10a-v2 (packet prepared;
  you type window + feasibility disposition), or did "reopen" mean something
  else (e.g. just resume watching without a verdict-bearing window)?
- **Q2 — D-1=F1 override for H10b (and H5's watch):** confirm the Schwab
  15:45 preclose lane counts as a qualifying exact-session source for these
  lanes' entry evaluation. (This reverses part of your 2026-08-14 F1 ruling;
  the drafted amendment confronts F1's rationale rather than ignoring it.)
- **Q3 — H5 AMZN destination:** AMZN is not an authorized LEAPS name; the
  draft routes an AMZN fire to a tactical call only ($600 cap). Confirm, or
  authorize AMZN LEAPS (that would be a new frozen decision — yours).
- **Q4 — H5 IVR dead period:** the frozen IVR<=0.5 trigger cannot compute on
  Schwab data until ~126 sessions accumulate (~6 months), so H5 cannot fire
  during that period under the drafted amendment. Accept the dead period, or
  change the trigger (owner-only either way).

## Owner answers — recorded 2026-08-17 (in-session)

The owner answered Q1–Q4 directly ("get rid of. the h5 frozen rule entry i
want to obsereve while its testing. proceed with fresh window. ya confirm
overrid. yes. no dont accept dead period", sic) and then selected among
explicit multiple-choice options (N-1 confirmation-loop precedent):

- **Q1 = PROCEED with H10a-v2** (fresh registration). Follow-up selections:
  window length = **same as v1, ~2.5 months** (end ≈ 2026-11-01, exact end
  date typed by the owner at ratification); feasibility disposition =
  **pre-accept starvation**, quoting the freshly computed receipt-bound
  number (measured on ThetaData history, labeled as such — H7 precedent) at
  registration time.
- **Q2 = CONFIRMED**: the Schwab 15:45 preclose lane is a qualifying
  exact-session source for H10b's and H5's watch lanes (partial reversal of
  the 2026-08-14 D-1=F1 ruling, owner-confirmed).
- **Q3 = YES**: an AMZN fire (under any future entry rule) routes to a
  tactical call only ($600 defined-risk cap); AMZN LEAPS remain
  unauthorized.
- **Q4 = DEAD PERIOD REJECTED, resolved by retiring the rule**: the frozen
  H5 entry trigger (H5_ENTRY_TRIGGER_PREREG 2026-07-07 + V2 amendment
  2026-07-15) is RETIRED. Explicit follow-up selection: "Retire rule;
  observe-only" — H5 records daily observations (prices, data availability,
  IV-history accumulation) while the Schwab lane ramps; **no fires and no
  paper entries until the owner types a new entry rule**. The retired rule
  stays on the record as history (append-only; named supersession).

## What remains owner-only after this session

1. Type/ratify the H10a-v2 registration (packet draft prepared; owner
   selections of 2026-08-17 recorded — ~2.5-month window, starvation
   pre-accepted pending the quoted feasibility number).
2. Type a collateral cap if the H5 income side should ever record positions.
3. Type any FUTURE H5 entry rule (the retired trigger is not coming back
   without a new owner-typed decision; AMZN routes tactical-only per Q3).
4. Resolve the $16k-vs-$14k cap tension.
5. Schwab re-auth before ~2026-08-19 00:56 ET token death.
