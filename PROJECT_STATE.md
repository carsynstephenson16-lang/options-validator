# PROJECT_STATE — options-validator (CANONICAL status + roadmap)

**As of:** 2026-07-31. **Checkout:** `sfix` @ `5626c3f`; `main` @ `ecdaeb9`
(ops worktree; incorporated into `sfix` by merge `9cf3ee4`). This file is the
ONE roadmap. Every plan in the supersession
table (§8) is retired as an active path; those files remain as history.
Update this file whenever a registration, verdict, branch reconciliation, or
data decision lands.

## 1. What still works (verified 2026-07-31)

- The append-only ledger records are intact on disk (H7 window: one
  registration event, 2026-07-20; `research.cli verify` was NOT re-run this
  session). Hooks block ledger hand-edits and live-order code.
- The v1 chain cache (31,367 parquet files, 2018-01-02 → 2026-07-27) reads
  offline; every existing result replays from it.
- The Schwab live-preview lane landed on `sfix` with tests and a verified
  2026-07-29/30 probe; it is read-only by construction.
- The 13:00 intraday recorder keeps accumulating display-only receipts.
- Test suite: 2,232 tests passed on `sfix` @ `5626c3f`; `ruff` and `pyright`
  are clean.

## 2. What is unsafe (do not build on it)

Of findings F1–F6 in
`reports/strategy-evaluations/12_review_of_the_two_landed_commits.md`, F3–F5
were fixed in `5626c3f`. The remaining blockers are: the $600 cap is not
enforceable under decision-day sizing with fill-day prices (F1); `entry_date`
changed to fill-day and feeds verdict cohorts without registration (F2); and
`BACKTEST_EXECUTION_CONVENTION` is unregistered (F6). **No new backtest,
promotion, or registration until P0 closes.**

## 3. What is blocked, and on what

- Correction-facts append: blocked on independent review + owner approval
  (draft: `13_correction_facts_draft.md`).
- Phase B / v2 rebuild of H6/H8: blocked on owner decision OD-1
  (`docs/provider-transition.md` §5) — and OD-1 expires at cancellation.
- H7 future sessions: blocked on OD-3 (old vs new window namespace).
- Evidence-upgrade program: paused at packet 5B; its blocker is that no
  automated review lane has ever run on this repo (PR #18 measured silent —
  `docs/evidence-upgrade/decision-log.md` D40). Owner console action required.
- Branch truth: `main` was merged into `sfix` at `9cf3ee4`; `sfix` contains
  `88ffbb6` and `ecdaeb9` and is pushed through `5626c3f`. No completed P0 fix
  is local-only.

## 4. Overbuilt or duplicated (consolidation targets, not deletions)

- Instruction sprawl: guardrails restated across `CLAUDE.md`, `.cursorrules`,
  `AGENTS.md`; `.cursorrules` is now the single authoritative copy
  (CLAUDE.md imports it; AGENTS.md mirrors it for Codex by design).
- Skills in three places: `.agents/skills/` (13, tracked), `.claude/skills/`
  (13: 12 symlinks into `.agents/skills/` + `research-refresh`; the
  `daily-ritual` symlink was missing and was added 2026-07-31),
  `ov/.claude/skills/` (9 duplicates in the distributable bundle).
- Root status files: `PROJECT_STATE.md` is canonical; the 26 root-dated notes
  are gitignored scratch by design.
- `block_live_trading.py` logic lives untracked in `.claude/hooks/` while the
  tracked, tested copy convention is `.agents/hooks/` (only the ledger guard
  is there).

## 5. Parked or archived

Parked (with a written spec or decision, revisit triggers stated in each):
daily-NAV drawdown (`docs/superpowers/specs/2026-07-30-daily-nav-drawdown.md`);
the 1pm-capture → 2pm-entry hypothesis (report 12 §4 — new registration
required, not an H7 retrofit); Session 4 feed-inclusion work (measured inert:
0 of 310 trades affected); index-chain funding; LSE feed (retired). Abandoned
if OD-1 declined: Phase B v2 backfill. Spent forever: H1/H2, H9, Card 3, QM
study, H7 historical diagnostic.

## 6. Roadmap

Every task is one focused session or less. **Completion proof** is what must
exist afterward. Do tasks in order within a priority; P0 before P1 before P2.

### P0 — correctness and governance gates (block all further research)

- **P0.1 COMPLETE — Reconcile branches.** `main` was merged into `sfix` at
  `9cf3ee4` and pushed. `sfix` contains `88ffbb6` and `ecdaeb9`; the full suite
  passed before the merge commit.
- **P0.2 COMPLETE — Fix the twin ratio + drawdown ordering.** `5626c3f`
  changed `return_on_economic_max_loss` to sum-over-sum and computes
  closed-trade drawdown in stable entry-date order. The 13.64% ratio and
  shuffled-order drawdown regressions failed before the fix and passed after;
  the full suite passed.
- **P0.3 Cap enforceability (owner decision OD-A + implementation).** Owner
  picks the F1 mechanism: (a) re-size at fill, (b) cancel if fill-day credit
  worse than a typed tolerance, (c) accept and disclose. Recommended default:
  (b) — fail-closed, uses only fill-time data at fill time, no look-ahead.
  Proof: a cap test where decision and fill quotes DIFFER (the existing suite
  holds them equal — `test_selector_credit_equals_engine_fill_credit_for_same_quotes`);
  measured worst-case breach across the dataset reported. Depends: P0.1.
- **P0.4 COMPLETE — Last-session exit crash (F3).** `5626c3f` closes a
  final-session trigger descriptively at the same session's conservative
  executable mark and records `exit_execution=terminal_conservative_mark`;
  ordinary exits remain next-session engine fills. The Dec. 30 year-boundary
  regression failed before the fix and passed after; the full suite passed.
- **P0.5 Register the execution convention + entry_date semantics (owner
  types).** Owner registers D+1-close (F6) and the `entry_date` = fill-day
  redefinition (F2), or reverts the field to decision-day. Recommended:
  keep fill-day, register it, and keep `entry_decision_date` alongside.
  Proof: chained-ledger registration entry; config comment cites it.
  Depends: P0.1.
- **P0.6 Correction facts append (owner-gated).** Independent adversarial
  review of `13_correction_facts_draft.md`, decide fix-first-or-not
  (recommended: land P0.2 first so the fact says "fixed in <sha>"), confirm
  the ledger hook accepts the prefix, owner approves, append via typed API.
  Proof: fact visible at the end of `facts.log`; hook did not block; wording
  matches the reviewed text. Depends: P0.2 recommended.

### P1 — provider transition and data continuity

- **P1.1 Owner decides OD-1, OD-2, OD-4** (`docs/provider-transition.md` §5)
  — these expire at cancellation. Proof: decisions recorded as facts.
- **P1.2 Execute any approved final pulls** (per-pull approval, written call
  count, manifest + `DATA_PULL` fact). Proof: facts + regenerated manifest.
- **P1.3 Fail-closed wiring check.** Verify every watch/feature refuses as-of
  dates beyond cache coverage instead of substituting; add the missing
  refusals. Proof: targeted tests. Depends: P0.1.
- **P1.4 Post-cancel cleanup.** Remove/flag dead ThetaData terminal config so
  no path can attempt a call. Proof: grep-clean + suite green.

### P2 — validated feature work (only after P0 and P1)

- **P2.1 H7 governance (OD-3)** — new namespace registration or continuation;
  owner-typed. **P2.2 Phase B v2 gate merge + H6/H8 artifact rebuilds from v2
  only** (exists only if OD-1 approved; includes the direct-v2 bypass checks
  in `h6_features/h6_watch/h8_watch/h7_exit_session` named by the handoff —
  re-verify that list against code first). **P2.3 Session 7 same-bar
  atomicity check** (report 10 D7a option b; keeps conservative fills;
  SMART_LIMIT rejected). **P2.4 Evidence-upgrade resume** once the review
  lane demonstrably posts on a PR.

### P3 — parked and optional

NAV-drawdown build (spec exists); 1pm-entry hypothesis registration (needs
captured history + feasibility gate); Session 4 broader feed-inclusion work;
skills consolidation into `.claude/skills/` (verify with `/context`);
`block_live_trading` hook logic moved to tracked `.agents/hooks/` with tests;
`ov/` bundle dedup; archive sweep of superseded plan docs.

## 7. Stop condition

Stop and convene the owner immediately if any P0 work shows a **registered
verdict would change** (H1/H2/H9 or any live book), if a ledger verify fails,
or if any task would require touching v1 cache bytes or a one-run record.

## 8. Supersession table (retired as active plans; kept as history)

| Retired plan | Where its live content went |
|---|---|
| `docs/superpowers/plans/2026-07-23-twelve-month-scanner-research-program.md` and `docs/superpowers/plans/2026-07-23-codex-execution-queue.md` (EX0–EX10) | Paused wholesale; nothing from it may run until P0 closes. Surviving items re-enter via this roadmap only. |
| `README.md` "Current status" table + phase-roadmap function | Sequencing and status live HERE; README's stale figures (cache edge "2026-06-30", "suite green") should be corrected at the next landing. README "Scope status" keeps one job: the registry of which hypotheses are live. |
| `docs/superpowers/plans/2026-07-11-h7-forward-roadmap.md` (the "active build arc" `.cursorrules` used to cite) | H7 work re-enters via P2.1/OD-3 only; `.cursorrules`/`AGENTS.md` scope-guard wording updated 2026-07-31 to point here |
| `docs/superpowers/plans/2026-07-28-thetadata-options-flow-intelligence-plan.md` | Built on ThetaData; parked pending OD-1/OD-4 (`docs/provider-transition.md`) |
| `docs/superpowers/2026-07-07-thetadata-cancel-checklist.md` and `THETADATA_EXIT_PLAN` references | `docs/provider-transition.md` |
| `docs/codex-implementation-plan.md`, `docs/options-validator-readiness.md` | Historical; superseded by this file |
| Old `PROJECT_STATE.md` (2026-07-23 snapshot) | Rewritten as this file; its data-state facts carried into §1/§3 and `docs/provider-transition.md` |
| `docs/evidence-upgrade/*` as an active queue | Paused at packet 5B → P2.4 |
| Handoff prompts / session reports 08–13 | Evidence record, not plans; indexed in `reports/strategy-evaluations/14_governance_rebuild_2026-07-31.md` |

## 9. Owner-only decisions, in one place

OD-A cap mechanism (P0.3, default b); OD-B entry_date + D+1 registration
(P0.5, default keep-and-register); OD-C correction-facts approval (P0.6,
default fix-first then append); OD-1 v2 backfill before cancel (default:
authorize only if Phase B wanted within ~6 months); OD-2 final EOD top-up
(default: yes); OD-3 H7 namespace (default: new namespace); OD-4 record the
real cancel date; OD-D evidence-upgrade review lane (enable managed Code
Review for this repo, or restore the deleted workflow with a fresh token).
