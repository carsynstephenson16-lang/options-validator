---
name: executor-handback-verification
description: Use when an executor (Codex, a subagent, or a pasted report) hands work back claiming a fix round is done, tests pass, a review PASSED, or a PR is ready — before repeating any of those claims, merging, syncing the ops checkout, or writing a review verdict. The return leg of codex-brief-writing.
---

# Executor Hand-back Verification

An executor's report is a claim, not evidence. Four hand-backs between
2026-08-26 and 2026-09-08 asserted a review PASS or a green suite that no
committed artifact supported (PRs #93, #147, #156, #161); three were
provably false (#93, #147, #161). Every one was caught by hand; no tracked
skill, hook, or test enforced the rule. This is the written procedure.

## The hand-back receipt (fill every slot, in order)

Write this block at the top of the implementation-review receipt under
`reports/<date>-<brief>-implementation-review-round<N>.md`. A slot with no
value is a finding, not a blank.

1. **Head SHA verified:** `gh pr view <n> --json headRefOid` → SHA; the review
   is of this SHA only. A later push voids the receipt.
2. **Brief revision pinned:** the brief file's SHA on `main` at review time
   (`git log -1 --format=%h -- <brief path>`). If it moved since the round
   the executor fixed against, review conformance to the *new* revision and
   record the move — a fix round against a moved target is the executor's
   good-faith work, not a finding against them (2026-09-02, Brief 36).
3. **CI at that SHA:** `gh pr checks <n>` run by the reviewer; the run ID goes
   in the receipt. The PR body's "exit 0" is quoted only as the claim.
4. **Suite re-run by the reviewer** in a worktree under `.tmp/worktrees/`:
   `uv run python -m unittest discover -s tests` exit code, `ruff`, `pyright`.
5. **Every review artifact at that SHA is committed:** a review verdict with no
   committed receipt at this head is void. Any executor commit that deletes
   or rewrites a prior FAIL receipt (`git log --diff-filter=D --name-only`)
   is itself a blocker: evidence is superseded by a new dated file, never
   removed (2026-09-02, commit `36fa9ed`, recorded in
   `reports/2026-09-02-brief-36-implementation-review-round3.md:8-9`).
6. **Finding-by-finding closure:** each prior finding ID against the diff.
   Include at least one input the brief did not anticipate (dated-off-board
   inputs found the Brief 39 as-of bug after five rounds missed it). If the
   deadline leaves no time for this slot, the verdict is NOT READY — a
   capture missed because ops stayed on the previous main is recoverable;
   a defect merged under time pressure is not.
7. **Ops sync plan:** after merge, the repo's idiom
   (`docs/superpowers/plans/2026-08-13-08-fork-healing-ops-sync-canary-runbook.md:119`,
   `tools/ops_alignment_check.sh:49`):
   `git -C ~/options-validator-ops fetch -q origin main && git -C ~/options-validator-ops merge --ff-only origin/main`,
   then confirm `rev-parse HEAD` equals `origin/main` before 15:45 ET.
   Never `reset --hard` ops — it carries the ritual's own evidence commits
   (a "PUSH FAILED — ops HEAD is AHEAD" crit is the symptom).

## Out of scope

Merge timing, frozen numbers, registrations, verdicts, ledger writes:
owner-only. Green checks are review evidence, not landing authority.
