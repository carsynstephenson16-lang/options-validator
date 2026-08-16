# Runbook 08 — Heal the main fork, sync ops, unblock the canary

**Date:** 2026-08-13 (rev 2, post adversarial review — 16 findings applied)
**Author:** Claude (orchestrating session, PM scope pass)
**Executor:** mixed — steps marked AGENT are agent-executable; every merge to
`origin/main` and every mutation of the production ops checkout requires the
owner's go-ahead first (one batched approval covering steps 2–4 is fine).
Codex (Sol, high) executes any step marked CODEX.
**Status:** rev 1 FAILED independent adversarial review (2026-08-13); rev 2
incorporates all findings. Re-review before execution.
**Evidence base:** 2026-08-13 read-only audits (automation diagnosis, branch
disposition, H7 gap map) + the adversarial review of rev 1, this session.

## The single sentence

`origin/main` (7fbe013) and local `main` (eea4700) forked on 2026-08-10; the
production ops checkout **is the worktree where `main` is checked out**
(`~/options-validator-ops/.git` → `gitdir: …/.git/worktrees/options-validator-ops`),
so the 15:45 ET Schwab chain pre-close wrapper refuses daily with "HEAD is not
aligned with origin/main" — healing the fork inside that worktree, with owner
approval, is what lets the first real canary capture happen.

## Preconditions (verified 2026-08-13)

- Schwab data lane recovered: intraday capture 15/15 healthy since 2026-08-12
  09:31 (Repo-verified receipts). Last success before the outage was
  2026-08-07 15:45; failures ran 2026-08-10 09:31 → 2026-08-11 15:45.
  Recovery is proven; that a manual reauth caused it is **Inference** — the
  failure signature (`ensure_active_token` OAuth error) is also consistent
  with a provider-side outage. Operational consequence either way: the token
  refreshes on use and expires after ~7 idle days; see step 6 precondition.
- `git merge-tree origin/main main` is conflict-free (single tree, no
  conflict markers).
- `codex/capitaliq-ownership-inputs` (c54c7c8): its three files shared with
  local main's unique commit eea4700 are blob-identical, and it adds
  `reports/capitaliq/vst_2026-08-10-source-index.md` + attractiveness
  dashboard wiring. Not an ancestry superset (merge-base is 1fe8169), but the
  three-way merge into origin/main is clean and loses nothing. eea4700 is
  durable on `origin/codex/local-main-eea4700`.
- No file overlap between c54c7c8 and the step-1 hardening files relative to
  the merge base — 1→3 ordering is safe.

## Already done this session (2026-08-13)

- `codex/pre-canary-capture-hardening` committed @401f78b after full offline
  suite exit 0 on that exact tree, and pushed. **Merge NOT done** — owner-gated
  below.
- `codex/h7-schwab-evidence-mode` (609d43a) and `codex/handoff` (2c8332a)
  pushed to origin (branch-hygiene backup; pushing is backup, not
  integration). These were the two branches whose content existed nowhere on
  origin.

## Ordered steps

1. **[FABLE REVIEW] Adversarial review of the pre-canary hardening commit
   (401f78b)** against the 2026-08-12 review items H1/H2/H3/M-c — reviewing
   the FULL 11-file diff, not only the four named items (the diff also adds
   `reports/schwab_chains` to the irreplaceable-data guard + inventory and
   adds the `SCHWAB_PACKAGE_INVALID` fail-closed NO_GO packaging to the
   Schwab data gate).
2. **[OWNER GO-AHEAD, then AGENT] Merge `codex/pre-canary-capture-hardening`
   to origin/main** (after step 1 passes). Suite gate applies at merge.
   Without this landed, real canary bytes would be captured WITHOUT the
   H1/H2/H3 protections.
3. **[OWNER GO-AHEAD, then AGENT] Merge `codex/capitaliq-ownership-inputs`
   (c54c7c8) to origin/main.** Mechanically clean, BUT `PROJECT_STATE.md`
   (2026-08-12 block) lists this branch as "awaiting review/owner decision" —
   so the owner's explicit go-ahead is required, not assumed. Suite after
   merge.
4. **[OWNER GO-AHEAD, then AGENT] Heal the fork inside the ops worktree.**
   `main` is checked out ONLY in `~/options-validator-ops`; it cannot be
   moved from anywhere else (`git branch -f main …` refuses). This step and
   "sync ops" are the SAME operation:
   1. Preserve untracked receipts first: record
      `git -C ~/options-validator-ops status --short --ignored=matching --untracked-files=all`,
      then copy `reports/intraday_capture/2026-08-12`, `…/2026-08-13`, and
      `reports/live_probe/2026-08-12.json` to a location outside the worktree.
      (Verified: origin/main tracks none of these paths, so the merge cannot
      clobber them — this is belt-and-suspenders, not a known hazard. Note
      the irreplaceable-data guard does NOT cover these; do not cite a guard
      pass as protection for them.)
   2. `git -C ~/options-validator-ops merge --no-edit origin/main`
      (a merge commit; `--ff-only` is impossible while eea4700 is unmerged).
   3. `git -C ~/options-validator-ops push origin main`.
   4. Confirm: `git -C ~/options-validator-ops rev-parse HEAD` equals
      `git -C ~/options-validator-ops rev-parse origin/main`.
5. **[AGENT] Restart the live-dashboard LaunchAgent** so it stops serving
   27-July code (no-op benefit unless step 4 completed):
   `launchctl kickstart -k gui/$UID/com.carsyn.options-validator.live-dashboard`.
6. **[VERIFY] Canary window discipline.** The 15:45 wrapper compares HEAD to
   its LAST-FETCHED `origin/main` — `tools/schwab_chain_capture.sh` does not
   fetch, and the only fetch in the stack (daily ritual) is authority-blocked.
   Therefore: **freeze origin/main between step 4 and the canary** (no merges),
   or re-run step 4 the morning of the canary. Precondition the same morning:
   confirm the 09:31 intraday capture returned 15/15 before relying on the
   15:45 canary. Follow-up for brief 07 scope: add `git fetch -q origin main`
   before the comparison in the wrapper.
7. **[VERIFY] Next trading session 15:45 ET:** wrapper alignment gate passes →
   first real canary attempt (target 15/15 names, manifest verifies offline).
   Check ops `.tmp/schwab_chain_capture/<date>_1545.log` and
   `reports/schwab_chains/`. If partial: hardening guarantees fail-closed
   evidence; diagnose from the receipt, do not force. `force=True` captures
   are refused as gate evidence by design.
8. **[AGENT] Backup/restore drill with REAL canary bytes** (synthetic bytes
   explicitly don't count — docs/h7-forward-operations.md): run
   `tools/h7_forward_backup.py backup` then `restore-check` with
   `--completed-session <canary session>` (the tool takes a snapshot +
   completed session, not paths); record the receipt.
9. **[AGENT] Fast-forward the research worktree**
   (`~/options-validator-research`, branch `deploy/research`, clean, 72+
   behind) to the healed origin/main. `tools/research_refresh.sh` is tracked
   on both refs; the LaunchAgent path survives.
9a. **[AGENT, EVERY MERGE — rule R1, brief 11 §9.1]** *Any* merge to
    `origin/main`, by any session, agent, or the owner, is not complete until
    **both** production checkouts are fast-forwarded. Step 9 does this once for
    the research worktree; R1 generalizes it to every merge and both checkouts:

    ```bash
    git -C ~/options-validator-ops fetch -q origin main && git -C ~/options-validator-ops merge --ff-only origin/main
    git -C ~/options-validator-research fetch -q origin main && git -C ~/options-validator-research merge --ff-only origin/main
    git -C ~/options-validator-ops rev-parse HEAD          # must equal origin/main
    git -C ~/options-validator-research rev-parse HEAD     # must equal origin/main
    ```

    If `--ff-only` refuses, **STOP** — ops has local commits (the ritual's
    evidence commit whose push failed; brief 11 §9.2). Do not merge or reset;
    diagnose first.
9b. **[OPERATOR — rule R2, pre-canary self-check, brief 11 §9.1]** On every
    trading day, confirm before 15:45 ET that after a fetch
    `git -C ~/options-validator-ops rev-parse HEAD` equals
    `git -C ~/options-validator-ops rev-parse origin/main`. The 15:45 wrapper
    fetches and then refuses on a **behind**-divergence, and a refusal at 15:45
    loses that session's chains permanently. (Since owner decision D-3, an
    **ahead**-divergence consisting only of evidence-path commits is tolerated
    by the wrapper — `tools/schwab_chain_capture.sh`; a code commit or being
    behind still refuses.)

    > **R2 is currently unenforced and has already failed once.** On
    > 2026-08-14 PR #36 merged at 10:28:03 ET and ops was realigned at
    > 14:28:10 ET — four hours behind, undetected. Whether R2 becomes a
    > mechanism (a scheduled pre-15:45 alignment check, which needs a NEW plist
    > and therefore an owner `launchctl bootstrap`) or stays a documented
    > habit, or the risk is explicitly accepted, is **owner decision D-6 —
    > PENDING** (brief 11 §12). This step is the D-6b minimum in the meantime.
10. **[BLOCKED until `codex/h7-schwab-recovery` passes its own independent
    adversarial review and merges] Owner decision packet re-presentation.**
    The B3-compliant 2026-08-11 feasibility receipt (4/1050, expected entries
    4.0) exists ONLY on that unreviewed branch — it must not be put in front
    of the owner as "the" number until the branch survives review. Any
    presentation of it MUST carry the B4 caveat: measured on ThetaData EOD
    chains, not Schwab 15:45 pre-close data, and every known simplification
    inflates it. With that caveat, the owner decides: starvation redesign vs
    pre-accept; OD-3 namespace wording; registration authorization; authority
    flip (strictly last). None of these are agent calls.

## Deliberately NOT in this runbook

- Merging `codex/h7-schwab-recovery` (needs its own independent adversarial
  review first — PROJECT_STATE 2026-08-12; conflicts with the evidence-mode
  branch on `h7_schwab_window_registration.py`; land evidence-mode first via
  brief 07, then review recovery against the new base).
- Merging `codex/short-positioning-phases-1-4` (adds a FINRA short-interest
  provider — new-provider policy check against
  `.claude/rules/data-and-providers.md` / OD-4 posture is an owner read).
- Merging `codex/handoff` (2c8332a — pushed for durability this session).
  It overlaps origin/main's already-landed expired-auth fixes (M1); needs a
  reconcile-and-diff pass; treat as possible duplicate, not a blind merge.
- Deleting the four stale `codex/attractive-exp-*` branches (content already
  on origin/main) — deletion is an owner-approved cleanup batch; run the
  irreplaceable-data guard + the untracked/ignored-files check on each
  worktree first, per the worktree rule.
- ~~Any change to `data/ritual_authority.py` — that flip is the owner's, last,
  after registration.~~ **SUPERSEDED, owner-directed 2026-08-14** (owner wording
  in session: "I want to switch it back on"). See
  `docs/superpowers/plans/2026-08-14-11-ritual-switch-on-rev2-spec.md` §1.2.
  The supersession is **partial and named**: the owner directed that the
  **non-verdict-bearing data/display phase** may be switched on before
  registration, which is what the new `ritual_data_phase_active` flag
  authorizes. `h7_active` and `exact_session_source_active` remain
  registration-day-only and owner-only, and are untouched by brief 11 — the
  latter now has an explicit honesty bar (spec §7, bar S1, ratified by owner
  decision D-4 with sub-fork 3a/3b still open).

## Failure stops

Any suite failure, guard failure, merge conflict, or receipt that doesn't
verify STOPS the runbook at that step. No step may be worked around; a
refusal by a wrapper or hook is correct by default.
