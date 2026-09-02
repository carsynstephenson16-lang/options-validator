# PR #71 Unfreeze + PR #115 Close-out Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Tasks 4–5 are owner-gated — do not execute them without the owner's typed approval.
>
> Revision 2, 2026-08-30: rewritten after Opus adversarial review (verdict FAIL, 3 blockers + 5 majors — all findings applied; review preserved in the session transcript and summarized per-task below).

**Goal:** Retire the two stale August branches honestly (PR #115 merge-sweep: nothing unique; PR #71 h7-schwab-recovery: unmergeable) while preserving #71's branch-only evidence, extracting its still-valuable ideas into a fresh, correctly-framed Codex brief, and fixing a durability-evidence coercion defect that is live on main — sequenced around the owner gates that actually bind.

**Architecture:** Two lanes. Lane A (agent-executable now): preserve #71's branch-only artifacts, author Brief 36 against main @ `85eb07a`, Opus-review it, push everything on a NEW branch as a DRAFT PR (never this session's branch — its merged PR #124 makes any push automerge-bait). Lane B (owner-gated): a single decision menu covering the #101 row-6 go, the PR closes themselves (closes here have always been owner-directed acts), the post-registration quote-age threshold, and branch/worktree deletes. Registration does NOT wait on the quote-age threshold — the packet defines that obligation as created BY registering, not gating it.

**Tech Stack:** git/gh (close-out), markdown (brief + decision menu), Python 3.12 + unittest (Codex-side, per brief).

**Spec:** Findings embedded in §"Evidence base" below (two Sonnet scout re-diffs + one Opus adversarial verification pass, 2026-08-30; every claim re-derivable from the cited commands). Governing docs: `reports/h7_forward_schwab/2026-08-15-registration-packet-bar7-draft.md` (PR #101 branch), `reports/2026-08-14-owner-answers-decision-menu.md` (loss-bar-7 ruling), `reports/2026-08-15-owner-rulings.md` (ruling 10: V0 selection + starvation pre-acceptance), `reports/2026-08-28-deferred-closeout-rulings.md:66` (quote-age evidence).

## Global Constraints

- Validator only; no live orders; ledger writes only via typed APIs (never hand-edit `ledger/h7_forward/*`).
- Every owner-typed number stays owner-typed: the H7-Schwab loss bar is **7** (owner ruling 2026-08-14), NOT `config.MIN_LOSSES_FOR_VERDICT` (10); the quote-age threshold does not exist until the owner types it; the starvation pre-acceptance is the owner's ruling-10 text, quoted, never paraphrased into oblivion.
- Row 7 obligation (verbatim constraint from packet): the blocking quote-age gate + owner-typed threshold are "explicitly NOT satisfied by merging PR #71's caller of `h7_schwab_data_gate.evaluate()`" (brief 32 round-3 finding F2) — and row 7 is "Not a gate on this registration", a forward obligation created by the registration event.
- Before removing ANY worktree/branch/dir: `uv run python tools/irreplaceable_data_guard.py verify` AND `git -C <path> status --short --ignored=matching --untracked-files=all` (od1-v2 incident, 2026-08-03). `.tmp/worktrees/h7-schwab-recovery` EXISTS, holds 15 review-trail artifacts (~288K; 14 gitignored + 1 committed only at .superpowers/sdd/) that exist nowhere else; its `.cache`/`.tmp` are 0B (no provider-data exposure — the loss risk is documentary, and Task 1 removes it).
- PR closes, branch deletes, and worktree removals are all owner-approved acts in this repo (precedent: every prior close was owner-directed — "close 60/61" 2026-08-29, the 2026-08-28 sweep ruling). This plan drafts the close comments; the owner approves before any `gh pr close` runs.
- Push Lane-A work to a NEW branch (`claude/pr71-unfreeze-plan-2026-08-30`) and open the PR as DRAFT. Never push to `claude/deferred-closeout-2026-08-28`: its PR #124 is merged and the daily reconciler (automerge flag = 1) would open and auto-land a fresh PR unreviewed.
- Suite stays green offline: `uv run python -m unittest discover -s tests` exit 0; `ruff check .`; `pyright`.
- Do not touch the open lanes owned by other sessions: PR #101 (branch `claude/h7-registration-packet-draft` — read-only; it lives in the nested worktree under `.claude/worktrees/gracious-neumann-d938c9`), PR #136, #135, #127, #125, #103, and the A2 lane worktree `.tmp/worktrees/a2-outcome-battery`.

## Evidence base (scout findings 2026-08-30, corrected by Opus verification pass)

**PR #115 (`claude/merge-sweep-2026-08-22`, merge-base `accd165b` 2026-08-21, 124 commits behind / 15 ahead):** 50 files changed vs main (+11596/−362); every substantive file is byte-identical to main at the same path (landed via PR #70 `06cddea`, PR #87 `02e5d60`, PR #102 `7ddc2ef`). The only two differing files are regressions: `PROJECT_STATE.md` is a stale 08-21 snapshot, and `reports/h7_forward_schwab/2026-08-15-v9-cohort9-occupancy-followup.md` carries a "3 of 9" arithmetic error main already fixed to "4 of 9" (four names are listed). No `ledger/`, hypothesis-code, or frozen-config content; no worktree. **Salvage candidates: none. Independently re-verified by the Opus pass.**

**PR #71 (`codex/h7-schwab-recovery`, tip `06ecf75` 2026-08-11, merge-base `f9aad05`; 16 files, +1557/−95):** real conflicts in **4 files / 11 conflict blocks** (measured: `git merge-tree --write-tree --name-only origin/main origin/codex/h7-schwab-recovery` → `h7_schwab_window_registration.py` ×3, `2026-08-09-owner-gate-packet.md` ×3, `test_h7_backup.py` ×2, `test_h7_schwab_window_registration.py` ×3). Classification:

- *Redundant (already on main byte-identical):* `data/earnings/assertions_v2.csv`, `data/earnings/gating_v3.csv`, `reports/h7_forward_schwab/2026-08-11-primary-earnings-evidence.md`.
- *Superseded (main's reviewed versions win):* `tools/h7_forward_backup.py`, `tests/test_h7_backup.py`, `tests/test_h7_one_door.py` (disposition-B chain `97fda34`/`54e9a00`/`60a999c`/`79c6eea`, `85e72a8`).
- *Stale bar reference, measurement still standing:* `docs/provider-transition.md` + `reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md` edits cite the retired 20-entry bar, but their underlying measurement (4.0 projected entries over 70 sessions) was independently re-measured at 4.00 on main (packet row 5: "the 14-entry shortfall is confirmed, not narrowed"). The shortfall finding stands at bar-7 too; registration proceeds only on the owner's explicit ruling-10 starvation pre-acceptance. These edits are dropped because main's packet supersedes them as the live record, NOT because their conclusion was overturned.
- **Preserve (branch-only, would be destroyed by branch delete):** `reports/h7_forward_schwab/2026-08-11-feasibility-primary-earnings.json` — a fully input-bound feasibility receipt (`expected_entries: 4.0`, `config_hash`, `code_sha 97a3e58`, sha256 of each input CSV, `error_count: 0`, 1050 symbol-days), the measurement provenance behind the number packet row 5 re-derives and the worked example WP-1 is modelled on; `reports/h7_forward_schwab/2026-08-11-v2-arming-bottleneck-design.md`; `docs/superpowers/sdd/h7-schwab-recovery-plan/task-2-report.md`. Plus 14 gitignored review-trail artifacts (briefs/reports/reviews/diffs under `.superpowers/sdd/h7-schwab-recovery-plan/` in the worktree) that exist on no branch at all.
- *Salvage as ideas into Brief 36:* the `_validate_feasibility` input-binding rigor in `options_researcher/h7_schwab_window_registration.py` (config_hash/error_count/canonical-universe binding), and the *concept* of `tools/h7_schwab_manual_activate.py` (owner-confirmed CLI wrapping `register_window_real`) + tests.
- **Do NOT port (guardrail-loosening):** `options_researcher/h7_activation_guard.py`'s `owner_fields` caller parameter. Main's `OWNER_FIELDS` check at `h7_activation_guard.py:197` is the SOLE owner-input backstop; the parameter lets any caller pass `owner_fields=()` and blank every owner field vacuously. If per-scope field sets are ever needed: module-level frozen mapping keyed by scope id, plus a red-green test proving a narrowed set is refused.
- *Open defects:* **P1** (Codex-bot, 2026-08-24): `_validate_feasibility` never rehashes measurement inputs — a stale qualifying receipt could register against changed data. **P2 (corrected attribution):** the bot anchored at `tools/h7_schwab_manual_activate.py:298` but the actual coercion is in the BUILDERS, and it is **live on main in two modules**: `options_researcher/h7_schwab_window_registration.py:391` and `options_researcher/h7_window_registration.py:243` both record `"darwin_durability_verified": bool(evidence[...])` with only a presence check upstream, so the string `"false"` records as `true`. `h7_window_registration.py` is the door that produced the live seq-0 H7 registration. Closing #71 fixes nothing here — main needs the fix (WP-4).
- *Owner-number defect:* hardcoded `minimum = 2 * config.MIN_LOSSES_FOR_VERDICT` (=20). Note the corrected framing: the measured 4.00 fails the owner-ruled bar (2×7=14) as well — the registration survives on ruling-10's pre-acceptance, not on any bar being met. The defect is that the bar is config-derived instead of owner-typed, not that it refuses too much.
- **Verdict: rewrite via fresh brief; do not rebase or merge** (18 days of superseding reviewed work on main's side of all 4 conflicts).

---

### Task 1: Preserve #71's branch-only evidence (agent-executable now)

**Files:**
- Create on new branch `claude/pr71-unfreeze-plan-2026-08-30`:
  - `reports/h7_forward_schwab/2026-08-11-feasibility-primary-earnings.json` (from `origin/codex/h7-schwab-recovery`)
  - `reports/h7_forward_schwab/2026-08-11-v2-arming-bottleneck-design.md` (same)
  - `docs/superpowers/sdd/h7-schwab-recovery-plan/` ← copy of the 15 review-trail artifacts (14 gitignored + task-2-report.md) from `.tmp/worktrees/h7-schwab-recovery/.superpowers/sdd/h7-schwab-recovery-plan/` (briefs, reports, reviews, progress.md, review diffs). Note: the branch's one COMMITTED sdd file lives at `.superpowers/sdd/h7-schwab-recovery-plan/task-2-report.md` (hidden root dir, not `docs/`) and was verified byte-identical to the worktree copy at execution time, so the trail copy covers it.
  - This plan file.

**Interfaces:**
- Produces: a draft PR carrying every artifact whose only copy is on the #71 branch or in its worktree, so the later delete decision destroys nothing.

- [ ] **Step 1: Create the branch from main**

```bash
git fetch origin && git switch -c claude/pr71-unfreeze-plan-2026-08-30 origin/main
```

- [ ] **Step 2: Extract the three committed branch-only files**

```bash
git show origin/codex/h7-schwab-recovery:reports/h7_forward_schwab/2026-08-11-feasibility-primary-earnings.json > reports/h7_forward_schwab/2026-08-11-feasibility-primary-earnings.json
git show origin/codex/h7-schwab-recovery:reports/h7_forward_schwab/2026-08-11-v2-arming-bottleneck-design.md > reports/h7_forward_schwab/2026-08-11-v2-arming-bottleneck-design.md
mkdir -p docs/superpowers/sdd/h7-schwab-recovery-plan
# committed task-2-report.md is at .superpowers/sdd/... on the branch; verify it matches the worktree copy:
git show origin/codex/h7-schwab-recovery:.superpowers/sdd/h7-schwab-recovery-plan/task-2-report.md | diff - .tmp/worktrees/h7-schwab-recovery/.superpowers/sdd/h7-schwab-recovery-plan/task-2-report.md
```

- [ ] **Step 3: Copy the worktree's gitignored review trail** (read-only source; do not modify the worktree)

```bash
cp -n .tmp/worktrees/h7-schwab-recovery/.superpowers/sdd/h7-schwab-recovery-plan/* docs/superpowers/sdd/h7-schwab-recovery-plan/
```

- [ ] **Step 4: Verify nothing branch-only remains** — re-run the classifier: every file in `git diff --name-only origin/main...origin/codex/h7-schwab-recovery` must now be on main, superseded-by-main, or present on this branch. Expected: zero unclassified.

- [ ] **Step 5: Suite + lint still green** (docs-only change, but run anyway)

Run: `uv run python -m unittest discover -s tests; uv run ruff check .`
Expected: exit 0 both.

- [ ] **Step 6: Commit, push, open DRAFT PR**

```bash
git add reports/h7_forward_schwab/2026-08-11-* docs/superpowers/sdd/h7-schwab-recovery-plan docs/superpowers/plans/2026-08-30-pr71-unfreeze-pr115-closeout.md
git commit -m "docs(h7): preserve PR #71 branch-only evidence + unfreeze/close-out plan (rev 2, Opus-reviewed)"
git push -u origin claude/pr71-unfreeze-plan-2026-08-30
gh pr create --draft --title "docs(h7): PR #71 unfreeze plan + branch-only evidence preservation" --body "Rev-2 plan (Opus adversarial review applied: FAIL verdict, 3 blockers fixed) + the three committed branch-only files and 16 worktree-only review artifacts from codex/h7-schwab-recovery, preserved ahead of any owner delete decision. DRAFT: owner decisions in the plan's Task 4 menu remain open."
```

### Task 2: Author Codex Brief 36 — H7 Schwab activation door, rebuilt on main

**Files:**
- Create: `docs/superpowers/specs/2026-08-30-brief-36-h7-schwab-activation-door.md` (via the `codex-brief-writing` skill — read its SKILL.md first). Same branch as Task 1.

**Interfaces:**
- Consumes: Evidence base classifications; main @ `85eb07a` file shapes (`options_researcher/h7_schwab_window_registration.py` incl. `_validate_data_gate_receipt`, `options_researcher/h7_window_registration.py`, `options_researcher/schwab_quote_age_report.py` from PR #131); the preserved feasibility receipt (WP-1's worked example of input binding).
- Produces: a brief Codex implements on a fresh branch; its activation-CLI merge is blocked until the owner's row-6 go (state this in the brief's activation-gate section); WP-4 is mergeable independently (it fixes a live defect).

- [ ] **Step 1: Draft the brief with these six work packages, each with named acceptance tests:**
  1. **WP-1 validator input binding:** re-target #71's `_validate_feasibility` binding ideas at main's current validator; ADD measurement-input rehashing (earnings CSV + chain cache + underlying cache content hashes recorded in the receipt and re-verified at registration time) — closes P1. The preserved `2026-08-11-feasibility-primary-earnings.json` (which already carries per-input sha256es) is the reference shape.
  2. **WP-2 feasibility gate in its owner-ruled form:** the validator must enforce the 2026-07-24 registration feasibility gate as `.cursorrules` states it: `expected_entries >= 2 × <owner-typed loss bar>` **OR** a present, non-empty, owner-typed starvation pre-acceptance field that quotes the computed `expected_entries` (H10 precedent; ruling 10 is the live instance). No config-derived bar (`MIN_LOSSES_FOR_VERDICT` must not appear in the gate); no presence-only check — a blank pre-acceptance with a failing bar must refuse.
  3. **WP-3 activation CLI rebuild:** `tools/h7_schwab_manual_activate.py` re-scoped to the V0/bar-7 evidence shape; owner types the confirmation string at use time; independent adversarial review required before merge (sole caller of the real append door `register_window_real`).
  4. **WP-4 durability-evidence coercion fix ON MAIN (live defect):** in BOTH `options_researcher/h7_schwab_window_registration.py:391` and `options_researcher/h7_window_registration.py:243`, replace `bool(evidence["darwin_durability_verified"])` with a strict `is True` check plus a `_require`-level type assertion; regression tests for `"false"`, `"true"`, `0`, `1`, `None` (only JSON `true` passes). Mergeable ahead of everything else.
  5. **WP-5 quote-age blocking gate (build-behind-missing-threshold):** implement the gate structure reading an owner-typed config entry that DOES NOT EXIST YET; the gate must fail-closed (refuse to arm) while the threshold is absent; no default value anywhere. Cite row 7 verbatim: a caller of `h7_schwab_data_gate.evaluate()` does not satisfy the obligation. This is a post-registration obligation — it does not gate the row-6 registration.
  6. **WP-6 tests:** rewrite the `tests/test_h7_schwab_window_registration.py` deltas against main's current file; new tests for WP-1..WP-5; offline only; the `owner_fields`-narrowing refusal test if (and only if) a scoped-fields mechanism is introduced.

- [ ] **Step 2: Require in the brief:** independent adversarial review before merge, full suite + ruff + pyright as the acceptance gate, and the explicit statement that merging this brief does not register anything — registration remains the owner-confirmed CLI act after the row-6 go.

- [ ] **Step 3: Commit the brief and push** (same draft-PR branch).

### Task 3: Opus adversarial review of the brief before hand-off

- [ ] **Step 1:** Dispatch an Opus subagent framed "show me how this brief could be lying" — specifically: does any WP smuggle in an invented number, weaken a guardrail (the `owner_fields` lesson), touch the ledger outside the typed API, claim row-7 satisfaction, or let WP-3 merge without the row-6 gate?
- [ ] **Step 2:** Apply fixes; re-review only if a finding was structural. Commit to the same draft PR.

### Task 4: Owner decision menu (Claude proposes, owner types/approves — nothing here is agent-executed)

Numbers below are labeled **LLM-transcribed from Reviewer-measured evidence, not owner-typed**.

- [ ] **Step 1: Present the open owner items in order:**

| # | Decision | Evidence on file | What it unblocks / destroys |
|---|---|---|---|
| 1 | **#101 row 6 — final go** on registering the bar-7 V0 forward window (+ OD-3 namespace line). Independent of item 3 — the quote-age threshold does NOT gate this (packet row 7: "Not a gate on this registration"). | Packet §0 rows 1–5 MET/cleared; ruling 10 (V0 + starvation pre-acceptance) stands | Registration event → Brief 36's activation CLI usable; row-7 obligation clock starts |
| 2 | **Approve the two PR closes** (#115, #71) with the corrected comments in Task 5 (4-files/11-blocks count; stale-bar-not-overturned wording; no "P2 fixed" claim until WP-4 lands) | Evidence base above; every prior close in this repo was owner-directed | Task 5 executes |
| 3 | **Quote-age threshold** (minutes) for the blocking gate — a post-registration obligation | Worst SELECTABLE quote age 0.61–10.38 min over 7 sessions; 10-min block ⇒ 1/7 NO_GO; 15 or 20-min ⇒ 0/7 (Reviewer-measured 2026-08-28, `reports/2026-08-28-deferred-closeout-rulings.md:66`) | WP-5's gate arms |
| 4 | **Branch/worktree deletes:** `claude/merge-sweep-2026-08-22` (destroys nothing — all content on main), `codex/h7-schwab-recovery` + `.tmp/worktrees/h7-schwab-recovery` (destroys nothing ONLY after Task 1's preservation PR merges — before that, destroys the sole copies of the feasibility receipt and 15 review-trail artifacts) | Task 1 draft PR; data-guard output | Cleanup only |

- [ ] **Step 2:** Record whatever the owner types via the standard append-only paths (registration via typed API only; threshold into `config.py` with owner-typed provenance).

### Task 5: Execute the approved closes (only after Task 4 item 2)

- [ ] **Step 1: Re-verify both diffs are still as measured** (guard against late pushes)

```bash
git fetch origin && git diff origin/main...origin/claude/merge-sweep-2026-08-22 --stat | tail -1
git merge-tree --write-tree --name-only origin/main origin/codex/h7-schwab-recovery | tail -5
```
Expected: 50 files +11596/−362; 4 conflicted files. If different, STOP and re-scout.

- [ ] **Step 2: Data-guard before touching #71's worktree-adjacent branch**

```bash
uv run python tools/irreplaceable_data_guard.py verify
git -C .tmp/worktrees/h7-schwab-recovery status --short --ignored=matching --untracked-files=all
```
Expected: guard exit 0; the 14 ignored sdd artifacts listed (already preserved by Task 1 — cross-check names match).

- [ ] **Step 3: Post the close comments and close**

```bash
gh pr comment 115 --body "Re-diff 2026-08-30 (merge-base accd165b, 124 commits behind main): all 50 changed files are byte-identical to main at the same path (landed via PR #70, #87, #102) except two stale regressions (PROJECT_STATE.md 08-21 snapshot; a '3 of 9' arithmetic error main fixed to '4 of 9'). Nothing unique to salvage. Closed per owner approval (plan: docs/superpowers/plans/2026-08-30-pr71-unfreeze-pr115-closeout.md). Branch retained pending the owner's delete decision."
gh pr close 115
gh pr comment 71 --body "Superseded 2026-08-30 (owner-approved close; plan: docs/superpowers/plans/2026-08-30-pr71-unfreeze-pr115-closeout.md). Measured: 18 days behind main; 4 files / 11 conflict blocks (git merge-tree). Backup/one-door deltas superseded by the reviewed disposition-B chain; earnings CSVs already on main byte-identical; the provider-transition/gate-packet edits carry a stale 20-entry bar reference but their 4.0-entry shortfall measurement was re-confirmed on main at bar-7 (registration proceeds on ruling-10's starvation pre-acceptance, not on the bar being met). Branch-only evidence preserved via PR <Task-1 PR#>. Salvage carried into Brief 36: validator input-binding (P1), rebuilt activation CLI, feasibility gate in owner-ruled form. NOT ported: h7_activation_guard owner_fields param (guardrail-loosening). The durability bool-coercion defect (bot P2, misanchored) lives in the builders ON MAIN and is Brief 36 WP-4 — closing this PR does not resolve it. Branch + worktree retained pending owner delete decision."
gh pr close 71
```

- [ ] **Step 4:** Update the session note / handoff: #115 re-diff done, #71 disposition recorded, Brief 36 in flight.

## Sequencing

```
Task 1 (preserve + draft PR) ─→ Task 2 (Brief 36) ─→ Task 3 (Opus review) ─→ Codex implements
                                                                               WP-4 (main fix): mergeable now
                                                                               WP-1/2/6: mergeable after review
                                                                               WP-3 (CLI): merge blocked ──┐
Owner item 1 (row-6 go + OD-3) ────────────────────────────→ registration ─────────────────────────────────┤
Owner item 3 (quote-age threshold — post-registration) ────────────────→ WP-5 gate arms                    │
Owner item 2 (approve closes) ─→ Task 5 (execute closes)                                                   │
Owner item 4 (deletes — only after Task 1 PR merges)                                        activation live┘
```

Tasks 1–3 need no owner input and can run today. Registration waits only on owner item 1. Nothing registers, arms, or merges into the ledger path without the owner's typed input at its own gate.
