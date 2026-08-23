# Finishing options-validator: the decision list (owner package)

- **Date:** 2026-08-22
- **Author:** Claude Fable 5 orchestrating session
- **Status:** DRAFT — pending independent adversarial review; decisions themselves are owner-only
- **Provenance:** Repo-verified against origin/main @accd165 unless labeled otherwise. This package proposes; you decide. Any number below that came from an LLM is labeled and must not be frozen as-is.

## The honest headline

The platform doesn't need more code to move — it needs your rulings. Every live hypothesis is either waiting on time (H6, H8, H10b need trades/sessions to accumulate) or waiting on one of the decisions below. "Finished" here means: every lane is either running toward its declared verdict or explicitly closed. A "no edge" outcome still counts as success.

## Recommended order (dependencies first)

**Round 1 — unblocks daily operation (15 minutes):**

1. **D6 — flip `exact_session_source_active`?** Plain English: a safety flag that says "I trust the price-date bookkeeping enough to let the H5-observe and H10b watchers actually run." The honesty bar you ratified is S1 (`reports/2026-08-14-switch-on-owner-decisions.md:40-55`), which has FOUR conditions: (1) three consecutive unattended sessions, (2) offline-verifying preclose receipts over the full registered watch universe, (3) no forced-capture marker, (4) LaunchAgent loaded with last exit 0. **There is also an OPEN sub-fork recorded at `:48-55` that MUST be resolved by you before any flip:** condition 3 needs either (3a) an `invocation_source` field in the receipt or (3b) dropping the condition. Note: 3a has since landed in code (`options_researcher/schwab_chain_capture.py:311` writes `invocation_source`), so 3a-by-default is available to ratify. **Measured streak as of 2026-08-22 (Repo-verified):** clean receipts exist for 08-19 and 08-20 (`ok`, force=False, `invocation_source=launchd`, 15 names); 08-18 and 08-21 have none — the streak is 2 and was broken on 08-21. **Recommendation: ratify 3a, then flip when the streak reaches 3 — don't flip today.**

2. **D3 — branch rulings.** **27 branches are unmerged into main (51 local total)** — the full per-branch table is appended at the end of this package; rule from it, not from memory. Buckets: (a) *merge-ready* — ONLY branches a report explicitly review-approved (correction from rev 1: PROJECT_STATE.md:97-104 is headed "awaiting review/owner decision" — it is NOT approval evidence, and `codex/capitaliq-ownership-inputs` / `codex/short-positioning-phases-1-4` from that list already merged in the 2026-08-13 train); (b) *delete after guard check* — only where a report explicitly approves deletion (note: `codex/attractive-exp-wiring` holds VST analyst-review specs per PROJECT_STATE.md:101 and is NOT a deletion candidate; five attractive-exp branches remain unmerged, not four); (c) *needs its own review first* — everything with "no report found" in the table, including `codex/h7-schwab-recovery` (PROJECT_STATE.md says explicitly it needs independent adversarial review) and `claude/merge-sweep-2026-08-22`.

**Round 2 — the H7 restart (the big one):**

3. **D1 — pick the H7 variant.** Plain English: H7 is the swing-trade experiment; the redesign found no entry rule that would historically have produced the 20 entries the feasibility gate demands in a normal window. Your options (full math in `reports/2026-08-14-owner-decision-package.md:91-112`, Decision 10): (a) variant V9 + a longer ~140-session window (you type the window); (b) normal window + pre-accept the starvation risk in writing (H10 precedent); (c) lower the loss bar (you type the number); (d) register nothing — keep capturing data only. **No recommendation between a/b/d — that's genuinely a risk-appetite call. I recommend against (c):** lowering the bar to fit the data is the pattern the gate exists to stop.
4. Then D-package Decisions 11 and 12 (registration authorization, `h7_active` flip) in their stated order — 12 is strictly last.

**Round 3 — research-lane hygiene (can wait, but each blocks one thing):**

5. **D4 — badge blockers BL-1/BL-2.** BL-1: badge B1 wants a year of IV history the Schwab lane doesn't have; splicing old ThetaData onto it was ruled fabrication. Options: record "unavailable by construction" and drop B1, or defer. BL-2: the capture universe is 15 names, the registered board is 18. Options: authorize capturing the 3 missing names, or amend to accept 15/18. Context: `docs/superpowers/plans/2026-08-15-14-rq2-badge-build-codex-brief.md:6-17` — brief 14 cannot go to Codex until you rule. **Recommendation: BL-1 drop-with-record; BL-2 authorize the 3 names (small, non-destructive).** Both LLM-proposed — veto freely.
6. **D2 — pin V1's statistic** (RQ2 volatility badge): one pre-result amendment naming the statistic before any comparison runs. The runner refuses until then (README.md:274-277). Needs you because pre-result pins are owner-typed.
7. **D5 — H10a-v2:** the draft packet (`docs/superpowers/plans/2026-08-16-h10a-v2-reregistration-packet-DRAFT.md`) shows starvation pre-accept selected 2026-08-17, but the file is still marked DRAFT — either ratify it (you type the feasibility number it quotes) or park it explicitly.

**Round 4 — housekeeping rulings (no urgency):** D9 (external review lane — needs console setup only you can do), D10 (prospective H6 amendment — default: leave unchanged), D11 (plans-archive convention). **D8 (the closes/exact-session source cadence, brief 18) is already answered 2026-08-20 (Decision 1 = A, Decision 2 = yes) — listed only so nobody re-opens it.**

**Numbering note:** D-IDs are this package's own audit sequence (2026-08-22), not a pre-existing registry. The original inventory's D7 was a duplicate of D4 (badge rulings) and is merged into it — that's why the list runs D1–D6, D8–D11.

## What I need from you, in one sitting

Reply with rulings in this shape and I'll route each to its executor (typed ledger API where required, Codex brief where it's code, nothing frozen without your keystrokes):

```
D6: sub-fork = 3a / 3b; then flip-at-streak-3 / hold
D3: rule per bucket from the appended table; exceptions: <names>
D1: a / b / c / d  (+ your typed window length or bar if a or c)
D4: BL-1 <ruling>; BL-2 <ruling>
D2: V1 statistic = <your choice, or "propose a menu">
D5: ratify / park
D9, D10, D11: <ruling or "later">
```

## Appendix — D3 branch-ruling table (Repo-verified 2026-08-22)

`git branch --no-merged main` = **27 branches; 51 local total.** All pushed and matching origin EXCEPT `rescue/detached-fca78a0` (laptop-only, confirmed 3× via `git ls-remote`). Summary: **0 merge-ready** (nothing carries explicit review approval at its current tip), **4 deletion-approved but worktree-blocked** (the `codex/attractive-exp-{beta-qqq,spread-stability,tail-shape,tbill-carry}` lanes — owner-approved deletion per PROJECT_STATE.md:130, but each is checked out in a `.tmp/worktrees/` worktree that must be guard-checked and removed first), **14 need their own review**, **13 worktree/WIP**. Notable rows:

| Branch | Ahead | Status |
|---|---|---|
| `rescue/detached-fca78a0` | 1 | **NOT PUSHED — push first, before anything else** (holds the 2026-08-19 rescued draft specs) |
| `claude/merge-sweep-2026-08-22` | 15 | pushed; needs review (this week's sweep output) |
| `codex/a2-outcome-battery` | 33 | pushed; in worktree; needs review — the biggest unreviewed pile |
| `codex/pre-canary-capture-hardening` | 5 | tip is 5 commits PAST what the 08-13 merge train landed — reviewed-then-grew; needs re-review |
| `claude/monday-ship-2026-08-15` | 7 | round-2 review passed an earlier commit; tip is an unreviewed auto-rescue commit |
| `codex/attractive-exp-wiring` | 2 | NOT a deletion candidate (VST analyst-review specs, PROJECT_STATE.md:101) |
| `codex/h7-schwab-recovery` | 7 | PROJECT_STATE.md:97-99: needs independent adversarial review before merge |
| `codex/handoff` | 3 | overlaps already-landed M1 fixes; reconcile-and-diff, not blind merge |
| `codex/qm-dashboard-integration-20260717` | 5 | "KEEP, harvest-only" per 2026-08-04 decision; plausibly superseded, unmerged |

Full 27-row table with per-branch evidence citations available on request; the buckets above are the synthesis. A recurring pattern worth a standing rule: **three branches were reviewed at one commit and then grew unreviewed tips** (auto-rescue commits landing on reviewed branches) — the daily rescue job is quietly invalidating review receipts. Consider ruling that auto-rescue commits go to dedicated `rescue/` branches, never onto reviewed ones.
