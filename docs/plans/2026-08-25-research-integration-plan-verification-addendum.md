# Verification Addendum — Research Integration Plan (2026-08-25)

**Target document:** `docs/plans/2026-08-24-options-validator-research-integration-plan.md`
(refreshed version, as committed by `4ba98e5` "wip(auto): daily rescue 2026-08-25").
**Verified against:** branch `claude/codex-handoff-plan-2026-08-22`, HEAD
`4ba98e5998345fac6fea9614b6d87ec3c1334ca3`, on 2026-08-25.
**Method:** four independent read-only audits — (1) code-evidence spot-check of every
Section-2 "Verified" row, (2) byte-level recount of every Section-8 data-inventory
figure, (3) repo-delta audit of everything landed after the plan's authorship, and
(4) an adversarial logic review ("show how this plan could be lying") including full
recomputation of the Section-4 scorecard arithmetic.
**Authority:** none. This addendum is review-only. It changes no production behavior,
consumes no OOS look, and proposes corrections for owner ratification. Supersede-
don't-rewrite: the 2026-08-24 document is left untouched; this addendum is the
correction layer.

**Ratification (2026-08-25):** the owner approved this addendum in-session
("approve", chat, 2026-08-25 ~10:56 EDT) and directed that it be merged to
`main` correctly. Scope of the approval as presented to the owner: (1) the §4
corrected decision table; (2) the Candidate-F amended terms — falsifiable
default-REMOVE acceptance criterion and an operator/cadence as a manual step in
the existing ritual (specific runbook wiring remains the next separately
authorized action, per the plan's own stop point); (3) landing the refreshed
plan + this addendum on `main` to supersede the stale copy (finding 10). The
[OWNER] markers below are retained to show what required ratification; each is
now RATIFIED per this note. No frozen numbers, registrations, or verdicts are
involved.

---

## 1. What verification CONFIRMED

The plan's factual spine is sound.

- **Code evidence: 13 of 14 spot-checked claims confirmed at file/symbol/line level;
  0 refuted; 2 partially supported on wording only** (errata in §3 below). Fill model
  (`strategies/base.py` `adverse_buy`/`adverse_sell`/`entry_credit_conservative`;
  `config.py` `SLIPPAGE_HAIRCUT = 0.01`, `FILL_MODEL_ID`), commissions
  (`COMMISSION_PER_CONTRACT = 0.65` wired through both engines), liquidity gates
  (`data/chain_policy.py:passes_liquidity`), OOS charge-on-touch
  (`OOSDataTouchError`, `research/experiments.py`), block bootstrap + purge/embargo
  walk-forward, enforced Holm correction, CSCV/PBO deliberate absence
  (`research/ledger.py` hard-null; `config.py` feasibility floors only),
  expiration-only settlement with a fail-closed `early_assignment_flag` stub,
  isolated QuantLib fixtures (zero runtime imports), existing surface features
  (`atm_iv`, `iv_minus_rv`, `term_slope`, `skew_25d`), annual-snapshot dividends with
  no point-in-time ex-div calendar — all as the plan states.
- **Data inventory: every Section-8 figure reproduced exactly** — 31,366 legacy chain
  files / 26 symbols / 2018-01-02..2026-07-27 (no timestamps, no sizes); Schwab 60
  files / 15 symbols / 4 capture dates / 143,738 rows with exactly 19,834 null
  `trade_timestamp` (no size columns); chains_v2 4,608 partitions / 18 symbols /
  256 sessions with sizes+timestamps and exactly 3 quarantined partitions
  (crossed markets, 2025-11-24); no broker execution/order/package/combo/net-quote
  data anywhere in the repo. Sole drift since 2026-08-24: +30 intraday snapshot
  files dated 2026-08-25 (956→986 files, 14→15 dates) — organic accumulation, not
  an inventory error. This addendum now serves as the independent reproduction
  record Section 8 lacked.
- **Scorecard arithmetic: all nine weighted totals recompute exactly** (max 52.5;
  A 37.5, B 28.5, C 31.0, D 31.5, E 29.0, F 43.0, G 24.0, H 39.0, I 32.5). All 90
  prose axis explanations match their table rows.
- **Safety posture: no passage weakens fail-closed behavior, touches locked OOS
  data, alters production rankings/verdicts/sizing/risk caps, or adds paid
  data/services.** Exclusions are explicit and repeated.
- **Nothing landed after 2026-08-24 invalidates any per-candidate verdict.** The
  plan had already absorbed the PR #72/#73/#74 merges (chain-consistency +
  SPREAD_BLOWOUT demotion + fill-adversity). The uncommitted
  `attractiveness_dashboard.py` work is unrelated owner-directed input-root
  plumbing (test suite green: 164 passed).

## 2. Findings requiring correction (adversarial review)

Ordered most severe first. Dispositions marked **[OWNER]** need Carsyn's
ratification; the rest are editorial and can be applied by the next authorized
doc session.

1. **The scorecard is decorative (HIGH).** All nine decisions are actually produced
   by three gates that are not scored axes: *already built?* → RESEARCH ONLY;
   *required data or exposure absent?* → PARK; *duplicates an existing system / no
   consumer?* → REJECT. The score inverts the decisions in places (REJECTed I at
   32.5 outscores RESEARCH-ONLY D at 31.5 and two PARKs). **Disposition:** state
   the three gates explicitly as the decision rule; demote the score to context.
   Do not re-tune weights to rationalize the outcomes post hoc.
2. **Candidate G self-contradiction (HIGH).** §8/§10.3/§11.5 treat G as PARK
   (reconsiderable when preregistered sample power exists); §1.4/§12 say REJECT,
   and §10.8's parking-trigger list omits G, closing its reopening path.
   **Disposition [OWNER]:** proposed PARK with explicit trigger — *a predictive
   model consumer exists AND a preregistered sample-power criterion is met*.
   "REJECT as a new system today" remains true; PARK records the reopening
   condition three sections already assume.
3. **F's benefit score presupposes its own review's answer (HIGH).** Benefit 4/5
   (the largest single term in the top score) for a tool whose §2 gap column says
   "utility/actionability is not yet established" and whose Phase-2 goal is to
   establish exactly that. Honest benefit is 2–3 pending review, putting F at
   35.0–39.0 — no longer materially above PARKed H. **Disposition:** re-mark
   benefit "2–3 (pending review)". The observation-review recommendation itself
   still stands — it is justified by the gates (built, data arriving, reversible),
   not by the score.
4. **`BLOCKED BY DATA` dropped from the decision table (HIGH).** The handoff's
   required vocabulary; §8 uses it verbatim for A ("Blocked by missing data;
   cannot calibrate fills") and B ("Blocked by missing data and exposure"), yet
   §12 labels them RESEARCH ONLY and PARK. Corrected table in §4 below **[OWNER]**.
5. **"Verified — strong" fuses evidence with judgment (HIGH).** "Verified" is
   defined as an inspection claim; eleven §2 rows weld an unverifiable quality
   adjective onto it (including "strong convention" for an admittedly uncalibrated
   haircut). **Disposition:** split into two columns — evidence status
   (Verified/Inferred/Unknown) and quality judgment (explicitly labeled analyst
   judgment).
6. **F's acceptance criterion cannot fail (MED-HIGH).** §6 Phase 2.6 is satisfied
   by filing any decision; §7's penalty branch ("remove *or keep it manual*")
   includes the status quo; only §10.6 is falsifiable. **Disposition [OWNER]:**
   adopt the §10.6 form as the acceptance criterion — *if no flag causes a
   documented data action over the review horizon, the default outcome is REMOVE*;
   KEEP-MANUAL requires an explicit owner override with recorded reason.
7. **F's data precondition is at ~13% and unowned (MED-HIGH).** 4 Schwab capture
   dates exist against the ~30-session horizon; §8's own freshest fact (2026-08-24:
   all 15 raw closes missing) is a direct risk to accumulation and is never
   connected to F; and no one is assigned to run
   `tools/chain_consistency_audit.py` per capture pair, so the receipts the review
   depends on will not accumulate by themselves. **Disposition [OWNER]:** assign an
   operator and cadence (e.g., a manual step in the existing daily/weekly ritual —
   scheduler wiring stays excluded during the observation phase) and state the
   horizon in wall-clock terms, not only sessions.
8. **Weighting rationale misstates its own weights (MED).** "Benefit, available
   evidence, and false-confidence safety dominate" — evidence carries weight 1.0;
   the actual dominant trio is benefit 2.0, data availability 1.5, FC-safety 1.5.
   Data availability at 1.5 is precisely what inflates the do-nothing candidates.
   The evidence axis also silently measures "how well-documented is the status"
   rather than "how strong is the case" (B scores evidence 5 for well-documented
   impossibility). **Disposition:** correct the sentence; disclose the evidence-
   axis semantics.
9. **C's conceded gap has no owner (MED).** The plan admits human-cost/maintenance
   fields are not uniformly captured and says they "belong in the next
   experiment's review template" — but no phase or ordering item carries that
   action. **Disposition:** carry it explicitly: *next registered experiment's
   review template adds complexity/data/maintenance-cost and removal-criteria
   fields.* REJECT-as-new-system stands.
10. **Governance inversion on the durable artifact (MED).** `main` carries the
    ORIGINAL plan (`3f5dccf`, header "APPROVED TO BRIEF STAGE (owner, in-session
    2026-08-24)"), whose §3-catalogued-stale recommendations a fresh clone would
    read as current; the corrected refresh lives only on this branch, where the
    daily auto-rescue (`4ba98e5`) committed it against its own "intentionally
    uncommitted" text. **Disposition [OWNER]:** decide whether to land the
    refreshed plan + this addendum on `main` (supersede-don't-rewrite: keep
    `3f5dccf`'s version in history, add a superseded banner or rely on the
    refresh) so the canonical checkout stops advertising completed work as open.
11. **Authority-boundary wording (LOW-MED).** §1 scopes the no-wiring rule "during
    this phase"; §10.7 is unconditional. **Disposition:** §1 should read "until a
    separately approved integration design," matching §10.
12. **OOS post-cutoff inspection is guarded by labeling discipline, not code
    (LOW-MED, note only).** §7 permits descriptive data-quality review of
    post-cutoff snapshots without spending a look. Probably fine for pure QA;
    flagged for explicit owner acknowledgement since the F review is a human
    looking at post-cutoff captures.

## 3. Citation errata (evidence audit)

1. **DSR/PSR symbol names.** `metrics.py` defines `psr` (line 446) and `dsr`
   (line 487) — not `probabilistic_sharpe_ratio`/`deflated_sharpe_ratio` as the §2
   table writes. Capability, Bailey/López de Prado citations, and
   `tests/test_deflated_sharpe.py` are all real; the names are wrong.
2. **"Prove baseline bytes invariant" conflates two test files.**
   `tests/test_experiments_baseline.py` proves import-boundary isolation and
   config-default parity (its output check is a marker string, not a byte diff);
   the actual byte-invariance assertions live in
   `tests/test_attractiveness_dashboard.py` and prove a different property
   (mechanical selection invariance under tracker/movement inputs), not
   experiments-vs-no-experiments output identity. No test currently diffs
   dashboard bytes with-vs-without experiments enabled.
3. **Chain-consistency branch scope.** `data/chain_consistency.py`,
   `tools/chain_consistency_audit.py`, and `tests/test_chain_consistency.py` exist
   on `main` only — absent from this working branch. The plan's row does say
   "Verified on `main`"; readers spot-checking the active checkout will not find
   the files. (Confirmed on `main`: only importer is the tool's own CLI — the
   no-production-caller claim holds.)

## 4. Corrected Final Decision Table (RATIFIED — owner approval in chat, 2026-08-25)

Uses the handoff's full required vocabulary. Changes from 2026-08-24 in **bold**.

| Candidate | 2026-08-24 | Proposed 2026-08-25 | Reason |
|---|---|---|---|
| A1 — fill-adversity context study (complete) | RESEARCH ONLY | RESEARCH ONLY | Done, merged (PR #74); descriptive only |
| A2 — fill/haircut calibration | (collapsed into A) | **BLOCKED BY DATA** | §8's own words; no broker executions/package fills exist |
| B — early-assignment scenarios | PARK | **BLOCKED BY DATA** | §8's own words; no ex-div event history, no assignment observations, no current short/multi-leg exposure |
| C — marginal-value experiment gate | REJECT | REJECT **+ carried action item** | Duplicates ExperimentSpec/ledger/OOS controls as a system; human-cost fields go into the next experiment's review template |
| D — simple surface features | RESEARCH ONLY | RESEARCH ONLY | Already exists display-only; no new model |
| E — era/regime stability | PARK | PARK | Outcome cohorts too sparse; trigger = preregistered sample power |
| F — chain-consistency observation review | RESEARCH ONLY | RESEARCH ONLY **(amended terms)** | Falsifiable default-REMOVE acceptance; assigned operator/cadence; honest benefit 2–3 pending review; wall-clock horizon disclosed (~13% of data precondition today) |
| G — feature grouping / ablation | REJECT (contradicted by 3 sections) | **PARK** | Resolves the internal contradiction; trigger = predictive consumer exists AND preregistered sample power |
| H — deterministic stress tests | PARK | PARK | Trigger = named exposed short/multi-leg position + concrete risk question |
| I — external framework lessons | REJECT | REJECT | Lessons/fixtures already absorbed; no migration case |

`PROCEED TO DESIGN`: still assigned to no candidate — correct, since nothing is
recommended for implementation now.

## 5. Repo-state notes for the next session

- **Pushed as backup (this session):** the branch's 5 unpushed commits
  (`720a20e`, `4ba98e5`, `77af463`, `1476a6f`, `615b958`) — backup only per the
  2026-08-04 universal branch-hygiene rule; no merge/PR implied.
- **Concurrent activity during this verification:** the dashboard input-root
  work (audited above as uncommitted WIP, tests green 164-passed) was committed
  mid-session by a parallel session as `720a20e` "fix(dashboard): default board
  input root to ops checkout" (2026-08-25 10:13). Unrelated to candidates A–I.
- **Untracked draft docs, untouched by this session:** briefs 25/26/27
  (`docs/superpowers/plans/2026-08-25-25/-26/-27-*`) — new scope outside A–I,
  authored by parallel sessions.
- **PROJECT_STATE.md / README "Scope status" lag:** neither reflects the PR
  #72/#73/#74 merges, the plan refresh, or briefs 24–26 (latest entries
  2026-08-23).
- **Brief 24 (infra, unrelated to A–I):** deployed `~/bin/repo-reconcile` is a
  hand-modified variant missing the ownership + gitleaks gates in `main`'s
  tracked copy; its Desktop digest publish has failed silently (TCC) for ~11
  days; fix branch `codex/repo-reconcile-publish` (`d08cadc`) exists, unmerged.
- **H7:** still PREPARED / NOT REGISTERED / NOT ACTIVATED; frozen numbers await
  owner entry at registration. Unaffected by any of the above.
- **Commit status (updated on ratification):** originally left uncommitted
  pending owner review; on the owner's 2026-08-25 approval this addendum is
  committed and merged to `main` together with the refreshed plan, resolving
  finding 10 (the stale-copy governance inversion).

## 6. Provenance

Produced 2026-08-25 by a four-auditor verification pass (three independent
inspection agents + one adversarial reviewer) orchestrated in a read-only
session. All file/line citations were mechanically inspected; all Section-8
counts were re-measured from bytes on disk; scorecard totals were recomputed
independently. Proposed decisions in §4 and dispositions marked [OWNER] are
LLM-proposed and carry no authority until Carsyn ratifies them.
