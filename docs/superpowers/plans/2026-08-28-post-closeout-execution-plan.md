# Post-Closeout Execution Plan — H7 packet repair, PR #94, briefs 32–35

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the four open items from the 2026-08-28 deferred-closeout: repair and
re-package the H7 bar-7 registration decision (PR #101 + riders #71/#102), land the
PR #94 quick win, execute briefs 32–35 (Codex primary, Claude-subagent fallback), and
record dispositions for the deliberate-later PR pile.

**Architecture:** This is PR/doc orchestration, not new feature design. Sonnet agents do
mechanical verification and small scouting; Opus agents do the packet repair, any brief
implementation fallback, and EVERY adversarial review (fresh reviewer each round —
2026-08-28 process lesson: three consecutive rounds each caught what the prior missed).
Owner-only actions (merges to main, the H7 ruling itself, frozen numbers) are marked
**OWNER** inline.

**Tech stack:** git worktrees under `.tmp/worktrees/`, `gh` CLI, offline unittest suite
(`uv run python -m unittest discover -s tests`; exit code is the verdict, never grep).

**Specs this plan argues from:**
- `reports/2026-08-28-deferred-closeout-rulings.md` (owner rulings + append-only correction)
- `docs/superpowers/plans/2026-08-28-{32,33,34,35}-*-codex-brief.md` — the four handed-off
  briefs. **The brief files remain the implementation source of truth**; this plan only
  sequences and assigns them.
- `reports/h7_forward_schwab/2026-08-15-registration-packet-bar7-draft.md` (only on branch
  `claude/h7-registration-packet-draft`, PR #101, worktree
  `.claude/worktrees/gracious-neumann-d938c9/.tmp/worktrees/h7-packet-draft` — KEEP-flagged,
  do not remove)

## Global constraints

- Research guardrails unchanged: validator only, no live orders, append-only ledger,
  offline tests, conservative-cost vocabulary discipline.
- All merges to main are **OWNER** actions. Exception already granted: the owner's
  2026-08-28 message states PR #94 "deserves landing".
- Every implementation PR is born-draft; the session un-drafts only after a fresh
  adversarial review passes (owner directive in the 2026-08-28 kickoff message).
- Never hand off after a review FAIL without a FRESH reviewer.
- Worktrees only under `.tmp/worktrees/<short-name>`. Before removing any worktree/branch:
  `uv run python tools/irreplaceable_data_guard.py verify` + ignored/untracked check.
- Branch hygiene: every branch that gains commits is pushed before session end.
- Suite verdicts by exit code; pipeline `cmd | tail` exit codes lie (use `set -o pipefail`
  or check `${PIPESTATUS}`).

---

## Phase 0 — Preconditions (mechanical)

### Task 0.1: Land PR #124 (carries briefs 32–35 + rulings report to main)

Briefs 32–35 and the rulings report exist ONLY on `claude/deferred-closeout-2026-08-28`.
Executors (Codex or subagents) need them reachable; main is the clean place.

- [ ] **Step 1:** Wait for CI: `gh pr checks 124` → Offline Quality Gates SUCCESS
      (Secret Scan already green; branch is 0 behind / 7 ahead of main, MERGEABLE).
- [ ] **Step 2:** Un-draft: `gh pr ready 124`.
- [ ] **Step 3 (OWNER):** Squash-merge #124.
- [ ] **Fallback if merge is deferred:** executors read briefs from
      `origin/claude/deferred-closeout-2026-08-28` and branch their work off `origin/main`
      anyway (briefs are inputs, not code dependencies).

### Task 0.2: Land PR #94 (daily-ritual plist — the quick win)

Verified 2026-08-28: tracked plist is **byte-identical** to the deployed
`~/Library/LaunchAgents/com.carsyn.options-validator.daily-ritual.plist` (MD5 match;
09:09 ET Mon–Fri; WorkingDirectory = ops checkout). CI green, `CLEAN` mergeable despite
being 34 commits behind (no path overlap). No rebase, no edits needed.

- [ ] **Step 1:** `gh pr ready 94`
- [ ] **Step 2 (OWNER-authorized 2026-08-28 kickoff message):** squash-merge #94.
- [ ] **Step 3:** Post-merge verification:
      `git fetch origin && git show origin/main:tools/launchagents/com.carsyn.options-validator.daily-ritual.plist | diff - ~/Library/LaunchAgents/com.carsyn.options-validator.daily-ritual.plist`
      → must be empty (tracked copy = live copy).

---

## Phase 1 — H7 packet repair (PR #101) — Opus implements, fresh Opus reviews

Work in the existing worktree
`.claude/worktrees/gracious-neumann-d938c9/.tmp/worktrees/h7-packet-draft`
(branch `claude/h7-registration-packet-draft`, currently head `d3e0a66`, 1 commit /
+290 lines off main). Single file:
`reports/h7_forward_schwab/2026-08-15-registration-packet-bar7-draft.md`.

### Task 1.1: Fix defect 1 — "all four" over five rows

- [ ] **Step 1:** At packet lines 21–22, replace:
      `Registration of the bar-7 window **cannot happen** until all four of these`
      with:
      `Registration of the bar-7 window **cannot happen** until all five of these`
      (Line 32 already says "all five rows" — the defect is line 21 alone.)

### Task 1.2: Refresh the entire §0 status table against current main

The table (lines 24–30) was drafted 2026-08-15 and is stale. Verified 2026-08-28:

- [ ] **Step 1:** Row 1 (Disposition B merged): `git merge-base --is-ancestor 54e9a00 origin/main`
      succeeds → flip to **MET**, cite commit `54e9a00`.
- [ ] **Step 2:** Row 4 (3a `invocation_source` landed): present on main in
      `options_researcher/schwab_chain_capture.py`, `data/ritual_authority.py` + tests
      → flip to **MET**. Recompute the S1 three-session start date the row derived from
      its absence.
- [ ] **Step 3:** Rows 2 (independent adversarial review of disposition B) and 3 (post-merge
      drill re-run GREEN): search `docs/superpowers/reviews/`, `reports/`, and session notes
      dated 2026-08-15..2026-08-28 for a review receipt / drill receipt newer than
      `reports/h7_forward_schwab/2026-08-14-backup-drill-failure-receipt.md`. If none found,
      they stay NOT MET — report honestly, do not infer.
- [ ] **Step 4:** Update the line-22 follow-on sentence ("None has cleared as of this
      drafting session.") to match the refreshed statuses, with a dated refresh note.

### Task 1.3: Add the quote-age row (defect 2) — as an obligation, NOT a sixth gate

Brief 32 rev 4 frames it precisely: the blocking gate + owner-typed threshold is a
requirement **created by** the registration event, not a precondition **of** it. Forcing
it into a "must read MET" row would misstate the ruling and could deadlock the packet.

- [ ] **Step 1:** Append row 6 to the §0 table:

      | 6 | **Quote-age gate commitment recorded in registration text** (not a registration blocker — a forward obligation created BY registering) | **Not a gate on this registration.** A descriptive daily quote-age sidecar report ships now (`options_researcher/schwab_quote_age_report.py`, brief 32 rev 4, HANDED OFF 2026-08-28; display-only, `"display_only": true` / `"verdict_eligible": false`, no threshold, no GO/NO_GO effect). Owner ruled 2026-08-28 ("Report now, gate later"): the BLOCKING gate + owner-typed threshold are a binding requirement of the H7 Schwab registration **arc**, triggered by the registration event itself — explicitly NOT satisfied by merging PR #71's caller of `h7_schwab_data_gate.evaluate()` (brief 32 round-3 finding F2). The registration `reason` text must record this commitment and cite the evidence: worst SELECTABLE quote age 0.61–10.38 min across 7 timestamped sessions (10-min block ⇒ 1/7 NO_GO; 15/20-min ⇒ 0/7; n=7, Reviewer-measured 2026-08-28, not owner-typed). | `docs/superpowers/plans/2026-08-28-32-schwab-quote-age-gate-codex-brief.md` ("Recorded for the H7 registration arc"); `reports/2026-08-28-deferred-closeout-rulings.md` ruling 1 + correction addendum |

- [ ] **Step 2:** Rework the closing line 32 to:
      `**Until rows 1–5 all read MET, this document is inert. Row 6 is not a registration gate; it records the obligation the registration event itself creates.**`

### Task 1.4: Label the branch-only evidence (provenance gap)

The packet's feasibility case (§2a, §3a, §3b, §5) cites `V0_BASELINE.json`,
`V14_REGISTERED_COHORT_9.json`, `V9_LANE_A_OR.json`, the 18-variant disclosure, and the
variant-menu doc — **none of which exist on main**; they live only on PR #102's branch.
Under the repo's claim-discipline rule that is a provenance-labeling gap.

- [ ] **Step 1:** If Task 2.1 (#102 merge) has completed: verify each cited path exists on
      `origin/main` (`git cat-file -e origin/main:reports/h7_forward_schwab/variant-receipts/comparable_70_common/V9_LANE_A_OR.json` etc.) and add a one-line note that the receipts landed.
- [ ] **Step 2:** If #102 has NOT merged yet: add to §0 (below the table) —
      `Evidence caveat: the variant receipts cited in §2a/§3a/§3b/§5 currently exist only on PR #102 (wt/brief09-variant-menu-0814, additive-only, conflict-free). Landing #102 before or alongside this ruling is a packet-integrity prerequisite; the numbers are otherwise branch-only evidence.`

### Task 1.5: Fresh adversarial review (Opus, new agent — not the implementer)

- [ ] **Step 1:** Dispatch a fresh Opus reviewer with the grilling posture: "show me how
      this packet could mislead the owner" — specifically checking: refreshed row statuses
      against actual main state, row-6 wording against brief 32 rev 4 and the rulings
      report, arithmetic of any recomputed S1 dates, and that no sentence implies merging
      #71 satisfies anything.
- [ ] **Step 2:** Apply fixes; if the review FAILs, next round gets another fresh reviewer.

### Task 1.6: Push + update PR #101 for the owner

- [ ] **Step 1:** Commit (message: `docs(h7): bar-7 packet — five-row count fix, §0 status refresh vs main, quote-age obligation row (rulings 2026-08-28)`), push.
- [ ] **Step 2:** Update PR #101 body: what changed, and the explicit owner-decision list
      (entry-rule variant choice, feasibility disposition, rows 2/3/5 clearance, quote-age
      commitment acknowledgment). PR stays draft — the ruling itself is **OWNER**.

---

## Phase 2 — The riders (#102 before the ruling, #71 after)

### Task 2.1: PR #102 — recommend landing BEFORE the H7 ruling

Additive-only (+9,149/−0, 43 files), `MERGEABLE`, zero content conflicts despite being 236
commits behind. It is the packet's evidence base (Task 1.4).

- [ ] **Step 1 (Sonnet):** Confirm nothing in it touches production/verdict paths:
      `git -C .tmp/worktrees/brief09-variant-menu diff origin/main...HEAD --name-only`
      → expect only `tools/h7_entry_variant_menu*.py`, `reports/h7_forward_schwab/**`
      (receipts + docs). Then confirm no production import:
      `git grep -l h7_entry_variant_menu -- 'options_researcher/'` on that branch → empty.
- [ ] **Step 2 (Opus, light review):** Sanity-pass the tool for guardrail compliance
      (cached-data-only, no network, display/measurement only, as-of stamping).
- [ ] **Step 3:** `gh pr ready 102`; **OWNER** merges.
- [ ] **Step 4:** After merge, re-run Task 1.4 Step 1 and re-diff #115 (Phase 4) — #115
      carries overlapping copies of the same tool + receipts from the 08-22 sweep.

### Task 2.2: PR #71 — HOLD until the owner rules

`CONFLICTING`: real conflicts in `docs/provider-transition.md` and
`options_researcher/h7_schwab_window_registration.py`; 10 of its 16 files have diverged on
main; its feasibility-stop logic predates the variant choice.

- [ ] **Step 1:** No rebase, no conflict resolution until the H7 ruling lands — rework
      before the ruling risks building against the wrong variant twice.
- [ ] **Step 2 (after ruling, Opus):** Rebase/rework per the chosen variant + disposition;
      full suite; fresh-Opus review; then un-draft for **OWNER** merge.
- [ ] **Standing note (brief 32 F2):** merging #71 never satisfies the quote-age gate
      obligation — the gate is a registration-arc work package with an owner-typed threshold.

---

## Phase 3 — Briefs 32–35 execution (Codex primary; Opus/Sonnet fallback)

**Verified 2026-08-28: Codex has NOT started any brief** — no branches, commits, or PRs
exist. Whoever goes first starts clean.

**Landing order (binding, from the briefs themselves):**
1. **35** first, then **33** (both touch `tests/test_daily_ritual_provenance.py`; C3).
2. **34** independent — any time, in parallel.
3. **32**: attempt WITHOUT the brief-33 accessor first (compute the selectable mask via
   its documented default inline in the new module — the brief's own fallback). Only if
   that proves infeasible, wait for 33's public accessor and land after it.

**Primary path:** Codex executes one brief per dispatch from the brief file verbatim.
**Fallback path (Codex usage exhausted):** the briefs were written to be executor-agnostic
— they carry exact seams, line numbers, test lists, and acceptance commands. No new plan
documents are needed; assign as follows:

| Brief | Implementer | Reviewer focus (fresh Opus) | Size | Branch |
|---|---|---|---|---|
| 35 pick-tracker round-5 (NEW-A/NEW-C/N3) | **Opus** (NEW-C dead-code proof + N3 partial-write pinning need reasoning; NEW-A is trivial) | RED/GREEN receipts for the mutation test; `-> bool` return path; immutable-history split untouched; `create=True` mock at `tests/test_pick_tracker.py:613` undisturbed | S-M | `claude/brief-35-pick-tracker-round5` |
| 33 closes provenance receipt | **Opus** | line-pin tripwire (`test_daily_ritual_provenance` passes UNMODIFIED); `.gitkeep` staged in same PR; `stored_file_sha256` labeling honesty; overwrite guard; superseded-not-mismatch semantics; PR-body source-hash disclosure | M-L | `claude/brief-33-closes-receipt` |
| 34 macOS CI job | **Sonnet** (single YAML job) | module list verified by actually running `PYTHONPATH=tests uv run python -m unittest <list>` locally on the Mac (exit 0) — never copied verbatim; `macos-14` pin + action SHAs; cost citation | S | `claude/brief-34-macos-ci` |
| 32 quote-age sidecar report | **Opus** | exact seam (`schwab_chain_capture.py:353→:354`, complete-path only); filename from `receipt_filename` stem (collision with PR #100 lanes); log prefix must not match the four pinned classifications; `display_only`/`verdict_eligible` pair verbatim; capture A/B byte-identity test; PR-body diagnostic-hash sentence | M | `claude/brief-32-quote-age-report` |

**Dispatch protocol (identical for Codex and fallback agents), per brief:**

- [ ] **Step 1:** Fresh worktree: `git worktree add .tmp/worktrees/brief<NN> -b <branch> origin/main`.
- [ ] **Step 2:** Executor reads the brief file + `reports/2026-08-28-deferred-closeout-rulings.md`; implements exactly within the brief's Scope IN/OUT.
- [ ] **Step 3:** Full offline suite by exit code + the brief's own named tests, including
      every RED/GREEN the brief demands (with the mutation shown in the PR body).
- [ ] **Step 4:** Commit per green unit; push branch.
- [ ] **Step 5:** Open **born-draft** PR; body carries the brief's required disclosures
      (32: diagnostic-hash consequence; 33: source-hash/v2 + validity-window; 34: final
      module list with per-module test/skip counts + macOS-minutes cost citation).
- [ ] **Step 6:** Fresh-Opus adversarial review per the table's focus column; FAIL → fix →
      ANOTHER fresh reviewer. PASS → session un-drafts the PR (owner kickoff directive);
      **OWNER** merges in the landing order above.

---

## Phase 4 — Deliberate-later pile: dispositions only (NO action this session)

All six are draft + `CONFLICTING`. Branches all exist locally and on origin — nothing at
prune risk. Recorded dispositions for a future session / owner call:

- **#103 A2 battery** (164 behind, ~5,000 lines + tests, has worktree
  `.tmp/worktrees/a2-outcome-battery`): rebase first, then its own dedicated review round.
  Too large to ride along — schedule as its own session.
- **#114 DSR specs** (289 behind but only 2 doc files / 163 lines): when the owner rules on
  the two instrument-only specs, re-apply the two files onto a fresh branch off main and
  close #114. No review round needed for a re-cherry-pick of docs.
- **#60 QM dashboard** (771 behind — most stale; `attractiveness_dashboard.py` rewritten
  since): close-with-rescue. Keep as reference only; any still-wanted logic gets rebuilt
  against current main, never rebased.
- **#61 branch-hygiene CLAUDE.md rule** (354 behind, single doc change): the rule already
  exists in the current global CLAUDE.md (Session hygiene #9, Carsyn-directed 2026-08-04).
  Verify, then close as redundant — no rescue needed.
- **#88 codex/handoff** (304 behind): unique value is the Schwab capture-failure hardening
  (`schwab_auth_failure.py`, `intraday_capture.py`) — ops-reliability relevant; extract
  that diff for its own review. Its VST analyst-review docs are byte-identical duplicates
  of #115's — **#115 owns the VST docs**.
- **#115 merge-sweep** (114 behind — freshest, highest H7 relevance): heavily overlaps
  PR #102 (same variant-menu tool + receipts). AFTER #102 lands, re-diff #115 against main;
  remaining unique content = plugin-program design specs, cohort-9 occupancy follow-up
  report, VST docs. Then a review round for what's left.

---

## Sequencing summary (what can run in parallel)

```
Phase 0 (0.1 #124, 0.2 #94)  ──►  immediately, in parallel
Phase 2.1 (#102 land)        ──►  immediately (evidence prerequisite for the ruling)
Phase 1 (packet repair)      ──►  now; Task 1.4 finalizes after 2.1
Phase 3 (briefs)             ──►  35 ∥ 34 first; 33 after 35; 32 after 33 (or parallel if inline mask works)
OWNER: H7 ruling             ──►  after Phase 1 + 2.1
Phase 2.2 (#71 rework)       ──►  only after the ruling
Phase 4                      ──►  later sessions
```

**Owner-action list produced by this plan:** merge #124, merge #94, merge #102, the H7
bar-7 ruling itself (via repaired PR #101 packet), merges of brief PRs 35/33/34/32 in
order, and (later) dispositions for #103/#114/#60/#61/#88/#115.
