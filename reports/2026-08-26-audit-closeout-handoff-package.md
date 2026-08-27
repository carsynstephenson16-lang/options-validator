# Audit close-out — Codex hand-off package (2026-08-26 evening)

**Author:** Claude Fable 5 orchestrating session, branch
`claude/codex-handoff-plan-2026-08-22`
**Provenance:** Repo-verified against
`origin/main@4ab1a385c3ee6a5c97285f9bf0a341f5a69feac5` and the live machine,
2026-08-26 evening, unless labeled otherwise. Review evidence:
`reports/2026-08-26-briefs-24-29-31-adversarial-review-receipts.md`.

## What this is, in plain language

The owner asked for optimized Codex hand-offs that finish and close out the
audit work: the 2026-08-22 five-project lean-ops plan
(`docs/superpowers/plans/2026-08-22-19-lean-ops-codex-handoff-plan.md`) and
the 2026-08-25 repository-audit verification arc. This package is the single
place that says: what is already done, exactly what Codex should be handed
next (with the hand-off text ready to paste), what only the owner can do,
and what is deliberately parked awaiting an owner decision.

Every brief handed off below has passed a fresh independent adversarial
review this evening (each reviewer's job was to refute, not confirm; each
brief took one to three rounds and every finding was either fixed or
recorded). Every implementation PR Codex creates starts as a GitHub draft;
green checks are review evidence, never landing authority; merging,
deploying, and syncing the operational checkout stay with the owner.

## Scoreboard — the audit plan's options-validator rows

| Item | Status |
|---|---|
| Brief 20 — backup allow-list from guard namespaces | **DONE** (PRs #66/#76/#78 merged). Record corrected in the brief's 2026-08-26 addendum: PR #66's body wrongly claimed `record-invalidation` covers directory receipts — it does not. Open leftover: the restic drill against the widened ~2.1 GB payload has not run (owner action A5). |
| Brief 21 — job-health digest tool | **DONE** (PR #67 v1 + PR #81 full hardening, merged). Open leftover: nothing ever runs it — wiring specified in brief 31 WP-B, owner-gated. |
| Brief 24 — reconciler redeploy arc | WP-A digest-publish fix **LANDED** (PR #75). WP-B owner redeploy **NOT RUN** — the single most urgent owner action (A1). New rev-4 WP-C (SEC-02 strict remote-owner verifier) + WP-D (every reconciler PR starts draft) **review-PASSED, ready for Codex** as a prepared draft. |
| Brief 25 — context lane | **DONE** (PR #86; flag ON under owner override). |
| Brief 26 — board declutter / Top-5 | **DONE** (PR #85). |
| Brief 27 — pick tracker | Spec PASS (rev 6, PR #92); implementation on **draft PR #93** (checks green, PR-body review PASS). Next gate is the owner's readiness decision (A6); registration/scored writes remain separate owner gates. |
| Brief 28 — event awareness | **DONE** (PR #91). |
| Brief 29 — Schwab cache inventory binding (DATA-01) | Rev 5 **review-PASSED tonight, READY FOR HAND-OFF** (was BLOCKED since the failed rev-2 review). |
| Brief 30 — midday chain refresh | Was already READY FOR HAND-OFF (PASS on `572cabc`) but never dispatched. **Hand off WP-A now**; staged WP-A → one green 15:45 ops cycle → remainder; lands after brief 27. One carried constraint from tonight's brief-29 review binds its future regeneration step (in the receipt). |
| Brief 31 — SEC-01 test pinning + digest wiring (NEW tonight) | **Review-PASSED. WP-A ready for Codex now; WP-B owner-gated** (D1). |
| SEC-01 base fix | **DONE** (PR #82 merged, owner-sanctioned). |
| Wiki refresh | **DONE** (2026-08-26 morning, owner-authorized). |

## Codex hand-off queue (paste-ready)

Recommended dispatch order: 29 → 24(WP-C/D) → 31(WP-A) → 30(WP-A). They
touch disjoint files, so they may also run in parallel.

**1. Brief 29 (DATA-01 — protect the Schwab chain cache):**
> Implement docs/superpowers/plans/2026-08-25-29-schwab-inventory-binding-codex-brief.md (rev 5, READY FOR HAND-OFF) exactly as written. TDD: demonstrate every WP-C RED first. WP-A/B/C/D land in ONE PR (atomicity is binding). Work in .tmp/worktrees/data01-inventory-binding off the pinned origin/main SHA; obey the quiesce window, sentinels, and machine-checkable delta. Create the PR with gh pr create --draft, prove isDraft=true, and STOP — no make-ready, no merge, no deploy, no ops sync.

**2. Brief 24 WP-C/WP-D (harden the daily reconciler):**
> Implement the Rev 4 section (WP-C + WP-D) of docs/superpowers/plans/2026-08-24-24-repo-reconcile-redeploy-codex-brief.md exactly as written: the strict all-push-destinations GitHub-owner verifier shared by all four anti-stranding scripts, and unconditional --draft on every reconciler-created PR. Tests RED first; stub git/gh executables assert no push/create/merge path ever runs in tests. Create ONE draft PR, prove isDraft=true, and STOP — it must not be made ready until the owner confirms the WP-B redeploy ran.

**3. Brief 31 WP-A (pin the review workflow's contract):**
> Implement WP-A ONLY of docs/superpowers/plans/2026-08-26-31-audit-closeout-followups-codex-brief.md (WP-B is owner-gated — do not touch it). Tests only; comment-tolerant normalized matching; mutation-prove each assertion including the comment-only negative control; RED first. Draft PR, prove isDraft=true, STOP.

**4. Brief 30 WP-A (parameterize the capture core):**
> Implement WP-A ONLY of docs/superpowers/plans/2026-08-25-30-midday-chain-refresh-codex-brief.md (READY FOR HAND-OFF; staged rollout is binding: WP-A alone, then one green 15:45 ops cycle before any further WP). Byte-identical defaults are the acceptance bar. Draft PR, prove isDraft=true, STOP.

**Cross-repo (the audit plan's other legs; briefs already exist, hand off from those repos):**
- Kalshi: `~/Claude.prod/claude/docs/briefs/2026-08-22-alert-renotify-and-log-rotation-codex-brief.md` — WP-A/B/C are Codex-ready; WP-0 stays owner-gated (deferred-actions item 8 is still unruled). NOTE: the brief file is UNTRACKED and the repo's "origin" is a local path — commit the brief and give the repo a real GitHub remote first (owner action A8).
- Equity-research: `docs/briefs/2026-08-22-repo-rag-repair-codex-brief.md` on branch `claude/repo-rag-repair-brief-2026-08-22` (pushed, unmerged). The repo-rag index has now failed 8 consecutive scheduled runs on the same policy-hash mismatch; the one-shot `python -m repo_rag health --rebuild` (owner/Claude, item A9) is independent of the brief and would stop the bleeding immediately.

## Owner actions (ordered; nothing here is delegable)

- **A1 (urgent).** Run brief 24 WP-B: `cd ~/options-validator && git pull && zsh tools/anti-stranding/install.sh`, then `launchctl kickstart -k gui/$(id -u)/com.carsyn.repo-reconcile`, then the two verification lines in the brief. Until this runs, the daily 08:15 job is the Aug-15 orphan script: no ownership gate, no secret scan, and an automerge loop missing four guards that the repo copy has (it auto-merged a `.github/` workflow change this morning — that landing happened to be owner-sanctioned, but nothing checked).
- **A2.** Convert the six non-draft open worker PRs to drafts (this session was permission-blocked from doing it): `for n in 60 61 71 87 88 89; do gh pr ready $n --undo; done`. Three of them (#87/#88/#89) were created non-draft by the reconciler TODAY; with automerge armed, any that goes green lands unreviewed. Then disposition each (review/close).
- **A3.** After each Codex draft PR above goes green + review-clean: make ready / land (your call, per PR).
- **A4.** After brief 24 WP-C/WP-D land: run the SECOND redeploy (same WP-B block) — until then the new code changes nothing live. Also rule on the prepare-early clause if you object (it is labeled Agent-proposed, owner-may-veto).
- **A5.** Run one restic backup + restore-check against the widened payload (~2.1 GB; brief 20's drill leftover).
- **A6.** Brief 27 readiness decision on draft PR #93 (pick tracker). Note its spec's own gates: deployment needs the ritual repair + 5 consecutive clean daily receipts; registration is owner-typed later.
- **A7.** Land/close the two small docs PRs: #94 (daily-ritual plist tracking, this session) and the docs PR this session opens for the brief revisions.
- **A8.** Kalshi repo: create a GitHub remote and push (both checkouts are laptop-only; "origin" is a local folder — one disk failure loses everything). Also: `launchctl load ~/Library/LaunchAgents/com.kalshi.weatherbot.orderbook_recorder.plist` (still unloaded; note the plist filename uses an underscore while its internal label uses a hyphen), and two kalshi jobs (`alerts`, `daily-report`) show last-exit 1 — worth a look.
- **A9.** Equity-research one-shots from the audit plan, still not done: `python -m repo_rag health --rebuild` (8 failures and counting) and `git config core.hooksPath scripts/hooks` (blocked note: `scripts/hooks/` still lacks the pre-commit counterpart the brief flagged — check that first).
- **A10.** TikTok repo still has NO git remote (15 branches laptop-only, plus untracked production plans). Routing row #1 of the audit plan; owner call on where it lives.

## Decision menu (parked by your own "nothing commissioned" ruling — say the word and a brief gets drafted)

- **D1.** Brief 31 WP-B: approve the build(Codex)/install(owner) split for the job-health digest schedule (brief 21 assigned wiring to you). One yes unlocks a review-passed spec.
- **D2.** DATA-02 (quote-age gate): needs an owner-typed age threshold — cannot be delegated. Mechanism can be built inert-until-typed if you want it.
- **D3.** DATA-03 (close-refresh provenance receipts): commission a design, or leave.
- **D4.** TST-02/TST-03 (macOS CI runner; repo-rag CI): policy/cost calls.
- **D5.** Ops capture logs (`~/options-validator-ops/.tmp/schwab_chain_capture/`): unprotected by design today — bless that or ask for coverage.
- **D6.** Backup-inventory invalidation semantics (brief 20's declared follow-up): commission or leave.
- **D7.** Kalshi WP-0 (halt-alert re-notify) vs deferred-actions item 8: rule it.
- **D8.** Claude.prod origin: give it a GitHub remote or accept inventory-only after redeploy.

## Open-PR inventory (all owner-disposition)

#93 brief-27 implementation (DRAFT, green, awaiting A6) · #94 daily-ritual
plist (DRAFT, this session) · #89 h7 evidence-mode fix, #88 codex/handoff,
#87 plugins design (all created non-draft by the reconciler 2026-08-26 —
A2) · #71 h7 schwab recovery · #61 branch-hygiene docs · #60 qm dashboard
integration (stale Codex WIP).

## What this session changed (docs only; suite exit 0 verified before commit)

Brief 29 → rev 5 READY FOR HAND-OFF; brief 24 → rev 4 with WP-C/WP-D
review-passed; brief 31 created (rev 2, WP-A ready); briefs 20/21 status
addenda + PR-#66 record correction; registry rows 28-31 reconciled; this
package + the combined review receipt; PROJECT_STATE status refresh. No
code, no ledger, no config, no authority, no frozen values.

## Update 2026-08-27 morning (post-Codex-execution; Repo-verified against remote main `5b1ed04` + live machine)

**Executed by Codex overnight:** all five dispatches implemented as separate
draft PRs — #96 (brief 29), #97 (brief 24 WP-C/D), #98 (brief 31 WP-A), #99
(brief 31 WP-B — built under the owner's "execute the plan then" wording,
recorded in its PR body; D1 confirmation still requested below), #100
(brief 30 WP-A, correctly self-held pending the brief-27 lane). A2 executed
for #60/#61/#71/#88/#89 (now drafts); #87 could not be converted — it had
already automerged at 08:48 under the OLD deployed script (four Aug-11
docs-only plugin-design specs; owner post-hoc review). A1 partially done:
`~/bin/repo-reconcile` now byte-equals main (`40a13c8`), `gh-login` cached,
canonical digest fresh — so **the guard now runs daily in the reconciler**,
and the governed-path automerge guard is live (verified: it is what blocked
kalshi #18/#19 from being merge-eligible).

**Corrections to this package:**
- A8 was partly wrong: `~/Claude` DOES have a GitHub origin
  (kalshi-weather-bot); only `~/Claude.prod` is local-pathed (that is D8).
  The reconciler's 09:09 kickstart created kalshi PRs #17 (draft),
  #18/#19 (non-draft) from stranded branches — #19 is a ~90-commit
  accumulated branch whose title reflects only its tip commit.
- New reconciler-created non-draft PRs #101/#102/#103 (H7 packet draft /
  brief09 variant menu / A2 outcome battery). #101 and #102 touch only
  `reports/`+`tools/` paths NOT covered by the governed-path guard —
  automerge-eligible if their checks go green. Draft conversion routed to
  Codex (this session remains permission-blocked on PR state changes).

**A1 residual, precisely:** the launchd exit-1 is the new script's designed
loud failure — the Desktop copy `mv` is TCC-denied, the canonical digest
succeeds, and the script has NO supported disable for the Desktop step
(`${DIGEST_DESKTOP:-…}` treats empty as unset). Closing A1 = owner TCC
decision: grant Full Disk Access to the LaunchAgent's interpreter, or
redirect `DIGEST_DESKTOP` to a non-TCC path via the plist (a small spec'd
change if chosen). The full installer (post-commit hook with the ownership
gate + nohup fix, session-rescue, worktree-guard) remains the owner-run
WP-B step — Codex correctly refused to run it.

## Update 2026-08-27 midday — #93 review resolved; Codex round-3 queue

**PR #93 (pick tracker) is NOT READY — artifact-backed.** The
audit-closeout session's independent bounded review (recorded in
`.superpowers/sdd/2026-08-26-audit-closeout-handoff-package/progress.md`
and `closeout-execution-report.md`, 2026-08-26 23:32 → 02:05 EDT) reviewed
#93's exact, still-current head `5877939` and returned **FAIL / NOT
READY**. P1: snapshot validation accepts source-row/render divergence; the
mutable current portfolio can retroactively rewrite historical CC/PMCC
outcomes; daily marking is absent and drawdown ignores the zero-return
entry point. P2: FAILED/DISABLED arms synthesize exits/re-entries; WP-D
reports omit required cohort/cancellation/scoreboard content. By contrast,
#93's own body line "independent read-only full-diff review after bounded
corrections: PASS" has NO corroborating artifact anywhere (no receipt file,
no GitHub review, no worktree record) — an uncorroborated self-report. The
only Brief-27 PASS receipt in `reports/` reviewed the SPEC rebase (PR #92),
not the implementation. Owner A6 answer: hold readiness until the fix round
below completes.

**State at this update:** #96/#97/#98/#99 are READY with all checks green
(review-check "failures" were concurrency-cancelled runs, re-run to pass);
they land at the next 08:15 automerge. A1 fully closed (FDA granted and
live-verified; Desktop digest delivery restored; redirect reverted).
Every other open PR is a draft, including the day's reconciler re-PRs of
squash-merged branches (#104–#110 — see churn note below).

### Codex round-3 dispatch (paste-ready)

> 1. **#93 fix round (Brief 27 implementation).** The governing findings
> are the audit-closeout controller review at
> `.superpowers/sdd/2026-08-26-audit-closeout-handoff-package/progress.md`
> ("A6 independent bounded review: FAIL / NOT READY at head 5877939") —
> close those exact P1/P2 findings, TDD (RED first per finding where
> testable): (P1) snapshot validation must fail closed on any
> source-row/render divergence; historical CC/PMCC outcomes must be
> immutable once recorded (no retroactive rewrite path from the mutable
> portfolio — prove with a test that mutates the portfolio and asserts
> recorded history is byte-stable); implement daily marking and make
> drawdown include the zero-return entry point; (P2) FAILED/DISABLED arms
> must never synthesize exits/re-entries; WP-D reports must carry the
> cohort/cancellation/scoreboard content the spec requires. Then obtain a
> FRESH independent review of the full diff and COMMIT its receipt under
> `reports/` — a PASS claim without a committed receipt artifact is void
> (that is exactly what round 2 caught). Correct #93's PR body: replace
> the uncorroborated PASS line with the receipt reference. Keep draft;
> readiness is the owner's A6 decision.
> 2. **After the 08:15 automerge:** verify #96/#97/#98/#99 all merged;
> report each merge SHA. If any failed to merge, report why and stop —
> do not retry merges yourself.
> 3. **#100 (Brief 30 WP-A) hold update:** its dependency is now "#93 fix
> round passes independent review + owner A6 + WP-A lands + one green
> 15:45 ops cycle with committed receipt". Update #100's body to that
> current chain. No other action.
> 4. Report back: fix-round evidence (RED logs, suite exit codes), the
> committed receipt path, the #93 body diff, merge confirmations, and
> isDraft states for everything you touched.

### Owner/orchestrator notes for next session

- After #97 merges: run the SECOND redeploy (installer + kickstart) so the
  strict owner-verifier and default-draft reconciler go live; verify
  `diff` equality per the brief.
- Reconciler churn: it re-PRs SQUASH-merged branches daily (ancestry check
  cannot see squashed content; #104–#110 today). WP-D landing makes future
  ones drafts (harmless). Durable fix options for the owner: delete merged
  branches (guard-verified list on request) or commission a small brief-24
  -arc follow-up (skip branches whose PR history shows a MERGED PR).
- Schwab token re-auth due ~2026-08-30 (weekend).

## Update 2026-08-27 late morning — lid-aware schedule retime (owner-directed)

The owner's laptop lid is shut 07:10–09:00 every morning; all scheduled jobs
were moved out of the 06:55–09:05 window (owner-directed 2026-08-27; note
launchd replays missed calendar jobs on wake, so nothing was ever lost —
this makes timing deterministic instead of a lid-open pile-up). New times:
repo-reconcile 08:15→**09:20**; research-display-refresh 07:30→**09:50**;
research-refresh 07:40/08:10→**10:00/10:30** (this also FIXES the standing
UPSTREAM_BLOCKED failure — the producer was still keyed to the retired
07:10 ritual and now runs after the 09:09 ritual completes); OV
repo-rag-health Sun/Wed 07:00→**09:40**; pick-dashboard Mon 08:07→**09:25**;
kalshi alerts dropped its 09:00 slot (first now 09:15); kalshi
weekly-calibration Sun 08:00→**09:40**; equity-research repo-rag-agent
Mon/Thu and repo-rag-health Sun/Wed 07:00→**09:40/09:45**. Daily ritual
stays 09:09 (already owner-retimed for the same reason). All nine agents
bootout/bootstrap-reloaded and verified. OV tracked plists updated in the
same commit as this note; **follow-up for the kalshi and equity-research
repos:** their tracked plist sources still show the old times (installed
copies changed only — editing those checkouts would have dirtied branches
that other automation auto-commits); sync them in each repo's next session.
Downstream doc note: every "~08:15 reconcile" reference now means 09:20.
