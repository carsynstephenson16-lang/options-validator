# Owner package — verification of the 2026-08-25 Codex repository audit

**Date:** 2026-08-25 (evening session)
**Author:** Claude orchestrating session (Fable) — verification, judgment, and
hand-off packaging only; Codex performed the audit; subagents (1 Sonnet
fact-checker, 2 independent Opus adversarial reviewers) did the heavy checking.
**Audit under review:** branch `codex/options-validator-audit-20260825-1403`,
bundle now committed at `3e30d2e` (19 reports), candidate fix `8afb0eb`.

## The short version

Codex audited the whole repo and was unusually disciplined: it implemented
exactly ONE narrow change (a CI security fix) and deliberately held everything
else back as plan-only pending your authority. I verified its claims
adversarially before trusting any of them. Result: **the security fix is
confirmed and staged for your one-click landing (draft PR #82)**, the audit's
one High-severity data-safety finding is confirmed and turned into a
reviewed, ready Codex brief (**brief 29**), and the audit itself was caught in
two mistakes that are now corrected in the hand-offs. Nothing was merged,
activated, or mutated; every decision below is yours.

## What was verified, and how

### 1. The implemented fix (SEC-01) — CONFIRMED, staged as draft PR #82

Plain language: the GitHub workflow that runs Claude code review could be
triggered by ANYONE writing `@claude` in a PR comment; when the review token
is configured, that meant strangers could invoke the credentialed action. The
fix requires the commenter to actually belong to the repo (owner, org member,
or collaborator). Automatic review of normal PRs is unchanged.

Independent Opus attack on the commit: confirmed it gates the right field on
both comment paths, uses exact equality (no substring widening), leaves the
normal PR path alone, and uses no dangerous trigger types. The new contract
test was mutation-probed live: all three loosening attacks the audit claimed
it catches, it caught. Merge vs current main: conflict-free; full suite on
the branch: 3,231 tests with exactly one failure that is pre-existing,
unrelated, and already fixed on main (PR #78) — CI on PR #82 is the final
proof.

**Your action:** un-draft PR #82 to land it (automerge finishes the job when
checks are green). Known follow-up worth ~10 lines later: the contract test
does not yet pin the trigger types or the token gate itself — recorded in the
PR body.

### 2. The High-severity data finding (DATA-01) — CONFIRMED, now brief 29

Plain language: the repo keeps a safety list of data folders whose bytes can
never be re-downloaded; a guard tool checks it before anything is deleted.
The list predates the Schwab capture lane, so the guard currently gives ZERO
protection to `.cache/schwab_chains` — five sessions of captured option
chains including today's, gitignored, unrepurchasable. Deleting them all
would pass the guard today. I reproduced this directly, not just from the
audit's word.

The fix is packaged as **Codex brief 29**
(`docs/superpowers/plans/2026-08-25-29-schwab-inventory-binding-codex-brief.md`),
which went through a full independent Opus adversarial review (6 blocking +
8 advisory findings — all applied) plus my sign-off. The review materially
improved it; two corrections to the audit's own plan are worth knowing:

- The audit suggested deep content hashing for the Schwab folders. Rejected:
  those folders GROW every trading day, so content hashes would false-alarm;
  count/byte floors (what every other namespace uses) are correct.
- The review discovered the guard has a daily scheduled caller
  (`repo-reconcile`, ~8:15am): a guard failure halts branch backups, PRs and
  automerge for the whole repo that day. So the brief binds only the
  gitignored parquet, drops the git-tracked receipts folder from the guard
  (git + the ritual auto-commit already protect it, and a floor there would
  false-alarm most days), and requires the code change and the list refresh
  to land in one PR. Brief 27 carried the same latent mistake for its new
  `reports/pick_tracker` folder — its draft now has a coordination note
  dropping that part.

**Your action:** say "hand brief 29 to Codex" when you want it executed. It
lands via a draft PR whose data-list diff you review before un-drafting.

### 3. The other plan-only findings — all CONFIRMED, decisions yours

- **SEC-02 (push-hook ownership check is spoofable):** confirmed in the repo
  copies — and the fact-check found the DEPLOYED hooks on this machine are
  worse: no ownership check and no secret-scan at all. Recommendation: do
  NOT open a new workstream; the existing brief 24 (repo-reconcile redeploy)
  is the urgent path — deploying the repo copies is a strict improvement —
  and the strict URL-parser fix becomes a small follow-on after redeploy.
- **WIKI-01 (derived wiki is stale):** confirmed — the wiki froze 2026-07-25
  and still says the H5 trigger is armed, H10a is running, H7 is live, and
  ThetaData is subscribed through November; Schwab is never mentioned.
  Fixing it is docs work a Claude session can do directly, but rewriting
  current-status claims needs your explicit vault-update authority.
  **Decision:** authorize the wiki refresh, or leave it (it is derived
  memory, never source of truth).
- **DATA-02 (no per-quote age check in Schwab packages):** confirmed —
  package verification checks the capture receipt's time, not each quote row.
  ~3,300 sampled rows were >15 minutes old; none was selectable, so no
  current harm. A fix needs an owner-typed age threshold — no number is
  proposed here, per the frozen-numbers rule. **Decision:** whether/when to
  set one.
- **DATA-03 (closes refresh has no raw-response receipt):** confirmed — the
  chain-cache top-up path already hashes what it fetches, the closes path
  does not. A fix changes acquisition record-keeping and needs your
  authority. **Decision:** whether to commission a design.
- **CI ideas (macOS job, repo-rag job):** confirmed gaps, low urgency, both
  need policy/cost calls. Parked in the roadmap until you want them.
- **New observation from verification:** the ops checkout's untracked capture
  logs (`~/options-validator-ops/.tmp/schwab_chain_capture/`) are protected
  by nothing and listed nowhere. Probably fine to lose (the real receipts
  are tracked); flagging so the choice is deliberate.

### 4. Corrections of record (honesty section)

- The audit's final matrix attributed the one suite failure to host resource
  exhaustion; it was actually a real, deterministic macOS test bug — since
  fixed on main by PR #78. Mild, but worth noting the audit dismissed a real
  failure as environmental.
- My own mid-session claim that the suite "passed exit 0" was wrong — that
  was the exit code of a `tail` pipe, not the tests. The honest result (one
  pre-existing failure, fixed upstream) comes from the Opus reviewer's
  direct run and is what PR #82's body states.
- The audit's strategy-verdict matrix (H1/H2 rejected, H10a closed-starved,
  others not-yet-rejected/insufficient) matches the ledger's existing
  adjudications; it makes no new strategy claim and I checked it introduces
  none.

## What was deliberately NOT done

No merge, no un-draft, no ledger append, no cache/data mutation, no wiki
edit, no provider call, no threshold invented, no change to any registered
hypothesis, no new workstream beyond the one reviewed brief. The audit
worktree stays in place until PR #82 lands (its branch now carries the
bundle, so nothing is stranded).

## Your decision list, smallest first

1. Un-draft **PR #82** (SEC-01 fix + audit bundle) — or comment for changes.
2. Say the word to hand **brief 29** to Codex (DATA-01 guard fix).
3. Wiki refresh: yes/no (grants vault-update authority for one reconciliation
   pass).
4. SEC-02 routing: confirm fold-into-brief-24 sequencing (recommended), or
   ask for a standalone brief.
5. DATA-02 quote-age threshold and DATA-03 close-receipt design: commission
   or defer (both fine to defer; nothing is currently selectable-stale).

---

## Addendum — owner rulings received 2026-08-26 (in-session, ~00:42 ET)

1. **Brief 29 → Codex: GO.** Status flipped to HANDED OFF.
2. **No new workstreams** — standing constraint for this arc.
3. **Wiki refresh: AUTHORIZED** — executed same session (see
   `wiki/log.md` 2026-08-26 lint entry). Future automation of the refresh:
   PARKED per ruling 2 (`ideas-parking-lot.md`, dated 2026-08-26 entry).
4. **PR #82: un-drafted per owner decision.** All checks green (quality
   gates, secret scan, review). The direct merge attempt was blocked by the
   session's permission layer; landing completes via the standing automerge
   (~8:15 daily). ACTION REMINDER: after it merges, sync ops before 15:45 —
   `git -C ~/options-validator-ops pull --ff-only` (the 15:30
   alignment-check LaunchAgent also warns).
5. **SEC-02 fold-into-brief-24 sequencing: CONFIRMED.** Ruling recorded in
   `docs/superpowers/plans/2026-08-24-24-repo-reconcile-redeploy-codex-brief.md`
   (appended section, 2026-08-26). No standalone SEC-02 brief.
6. **DATA-02 / DATA-03 / CI jobs (macOS, repo-rag) / ops capture logs:**
   owner asked for plain-language explanations before deciding — provided
   in-session 2026-08-26; decisions remain open, nothing commissioned.

## Merge-time correction (2026-08-26 ~09:05 ET, PR #90 conflict resolution)

Addendum item 1 is SUPERSEDED: after the hand-off status was recorded, a
second independent review (landed on main;
`reports/2026-08-26-brief-29-independent-review-receipt.md`) **FAILED brief
29 rev 2** with 8 blockers — most materially that `reports/schwab_chains`
removal breaks existing guard tests and `h7_forward_backup` (a
DEFAULT_NAMESPACES consumer the round-1 review did not check), and that the
canonical brief 27 rev 5 still carries the disputed guard addition. Main's
blocked-draft version of brief 29 is kept per the fail-closed rule (review
kills must not regress); the HANDED OFF status is void. **Owner decision
reopened:** brief 29 needs a rev 3 against current main answering the
blockers, plus a fresh independent written PASS, before any hand-off. The
underlying DATA-01 gap (unprotected `.cache/schwab_chains` parquet) remains
real and unprotected in the meantime.
