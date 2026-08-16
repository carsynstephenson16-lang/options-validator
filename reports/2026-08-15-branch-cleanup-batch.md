# Branch cleanup batch — 2026-08-15

**Session:** scheduled weekend-cleanup. **Authority:** the "available on
request" stale-branch cleanup from the 2026-08-14 decision package.

**Actions taken:** 21 **local** branches deleted. **No remote branch was
deleted** — see §3 for why, and for the ready-to-run command.

**Safety checks, both run and both clean:**

| Check | Result |
|---|---|
| `uv run python tools/irreplaceable_data_guard.py verify` (before) | `irreplaceable data: OK`, exit 0 |
| `uv run python tools/irreplaceable_data_guard.py verify` (after) | `irreplaceable data: OK`, exit 0 |
| `git status --short --ignored=matching --untracked-files=all` on all 33 worktrees | run; **one real finding — §4** |

Deletion criteria, all four required:

1. tip is an ancestor of `origin/main` (`git merge-base --is-ancestor`,
   re-checked per branch inside the deleting loop — not from a stale list);
2. no attached worktree;
3. not on the task's protected list;
4. not infrastructure (`main`, `deploy/research`).

---

## 1. Deleted (21 local branches)

Every commit on each remains reachable from `origin/main`, so this is
recoverable by name: `git branch <name> <sha>`.

| Branch | Tip |
|---|---|
| `claude/capitaliq-vst-source-package-603404` | `9640b92` |
| `claude/clever-perlman-4fe111` | `d6ed665` |
| `claude/drill-disposition-b-final` | `60a999c` |
| `claude/hungry-kapitsa-a8e755` | `1bddfa0` |
| `claude/ideas-parking-lot-review-762348` | `5942eb2` |
| `claude/options-indicators-optimization-7ef533` | `eda6618` |
| `claude/options-scanner-cache-update-e9202c` | `1530444` |
| `claude/options-validator-arch-review-a5a5bc` | `c875839` |
| `claude/ritual-data-phase-flip` | `f0be1a1` |
| `claude/ritual-switch-on-rev21` | `b6de7e4` |
| `claude/rq2-k3-and-dashboard-split` | `f230813` |
| `claude/rq2-k3-stale-docs` | `f1e7dec` |
| `claude/schwab-freshness` | `9562743` |
| `claude/tiktok-shop-phase-2-3-5ae3d2` | `ba1bda4` |
| `docs/cross-project-source-standard-2026-08-03` | `3d5266e` |
| `evidence/ops-august-2026-08-09` | `863175a` |
| `feat/h7-forward-schwab-v1` | `c1563ec` |
| `feat/source-standard-receipt-fields` | `1cad05c` |
| `port/qm-frozen-study-guard-v2` | `0f32c26` |
| `worktree-agent-a70f53271d3a0d28c` | `02593ea` |
| `wt/merge-train-0813` | `4c759ff` |

Local branch count: **58 → 37**.

Naming trap worth recording: the worktree directory
`.claude/worktrees/options-indicators-optimization-7ef533` has
`claude/options-validator-research-review-e27946` checked out, **not** the
similarly-named branch. The deleted `claude/options-indicators-optimization-7ef533`
had no worktree. Directory names are not branch names.

---

## 2. Kept, with reasons

**Protected by the task directive** (merged, but explicitly off-limits):
`claude/financial-analysis-skill-audit-3f5c84`, `codex/capitaliq-ownership-inputs`,
`codex/short-positioning-phases-1-4`, `codex/local-main-eea4700` (remote only).
Also named-but-unmerged, so protected twice over: `wt/brief09-variant-menu-0814`,
`codex/h7-schwab-recovery`, `codex/attractive-exp-wiring`,
`codex/options-validator-plugins-design`.

**Infrastructure — never delete:** `main`, `deploy/research` (LaunchAgent
checkout at `~/options-validator-research`).

**Attached worktree** — attachment is a preservation signal until classified
(PROJECT_STATE §3.1), so these were skipped even when merged: 16 branches
including all six `codex/attractive-exp-*` lanes, `claude/drill-disposition-b`,
`claude/serene-tereshkova-3f90be`, and both `wt/recovery-slice-*-0814` lanes.

**Ambiguous — listed, not deleted:**

`origin/port/qm-frozen-study-guard` @ `9c99586` — **memory records this as
"deletable"; that is wrong.** It is *not* an ancestor of `origin/main` and
carries **2 unique commits**:

- `9c99586` fix(qm): bind context to mechanical shortlist
- `daf7509` fix(dashboard): preserve descriptive QM fail-closed cues

Its work is plausibly superseded by `port/qm-frozen-study-guard-v2` (merged via
PR #28) and/or `codex/qm-dashboard-integration-20260717` (whose tip commit has
an identical subject line), but "plausibly superseded" is not "merged."
Deleting it would drop two commits that exist nowhere else. **Kept.** Resolving
this needs a content diff against v2, which is its own task.

---

## 3. Remote: inventoried, not deleted

19 remote branches meet the same criteria. **They were not deleted**, for two
reasons:

1. Deleting a remote ref is outward-facing and not reversible from this side.
2. The standing branch-hygiene rule is explicit that pushing is *backup*, and
   that "**merge and delete decisions stay Carsyn's**." Local deletion is
   internal housekeeping; removing origin refs is the decision that rule
   reserves. A scheduled unattended session is the wrong place to take it,
   especially mid-canary.

By reachability the deletion is safe — every commit is in `main`. Ready to run
when you want it:

```bash
git push origin --delete claude/ai-engineering-portfolio-project-a08276 claude/drill-disposition-b-final claude/ideas-parking-lot-review-762348 claude/options-scanner-cache-update-e9202c claude/options-validator-audit-cleanup-h6svzl claude/options-validator-audit-izf37s claude/ritual-data-phase-flip claude/ritual-switch-on-rev21 claude/rq2-k3-and-dashboard-split claude/rq2-k3-stale-docs claude/schwab-freshness docs/cross-project-source-standard-2026-08-03 evidence/ops-august-2026-08-09 feat/h7-forward-schwab-v1 feat/source-standard-receipt-fields fix/data-guard-worktree-cwd port/qm-frozen-study-guard-v2 sfix wt/merge-train-0813
```

**Two entries in that list deserve a second look before you run it:**

- **`sfix`** — merged and safe by reachability, but PROJECT_STATE cites it by
  name as the audited branch ("Checkout audited: … branch `sfix`, HEAD
  `217a4c5e…`"). The SHAs stay reachable, but the name stops resolving. Drop it
  from the command if you'd rather keep the pointer alive.
- **`claude/drill-disposition-b-final`** — merged **today** (PR #46). Nothing
  wrong with deleting it; just recent enough to be worth noticing.

---

## 4. Finding: two draft specs live only in one worktree

Turned up by the mandatory untracked-data scan, in
`.claude/worktrees/options-indicators-optimization-7ef533` (branch
`claude/options-validator-research-review-e27946`):

| File | Status | Size |
|---|---|---|
| `docs/superpowers/specs/2026-08-13-dsr-ledger-mode-provenance-draft-spec.md` | **in no commit on any ref** — `git log --all -- <path>` returns nothing | 8,992 B |
| `docs/superpowers/specs/2026-08-13-robustness-gate-surfacing-draft-spec.md` | on `main`, but the worktree copy **differs** | 11,494 B |

These match the two verifier-approved INSTRUMENT-ONLY draft specs awaiting an
owner decision. **This is the 2026-08-03 od1-v2 pattern exactly**: content that
exists only inside a worktree, invisible to every test, manifest, and backup
allow-list. The DSR spec in particular would be gone if that worktree were
removed with `rm -rf` instead of `git worktree remove`.

**Not acted on, deliberately.** That worktree belongs to another session's
in-flight work, and committing someone else's unreviewed draft spec — or
overwriting the `main` copy of the robustness one — is not this session's call.
Flagged for the owner:

1. `git -C <worktree> add` + commit both files onto their branch and push, or
2. decide the DSR draft is superseded and say so in writing.

Either way, **do not remove that worktree until one of those happens.**

All other worktrees showed only routine ignored paths (`.cache`,
`.claude/hooks`, `.claude/settings.local.json`, `.hypothesis`, `.lumibot`,
`.remember`) — nothing irreplaceable.

The one other untracked item of substance is
`~/options-validator-ops/reports/h7_receipts/backup/2026-08-14.json`, which is
the subject of `reports/2026-08-15-evidence-receipt-durability-proposal.md`.
