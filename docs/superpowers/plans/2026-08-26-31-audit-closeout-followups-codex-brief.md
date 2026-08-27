# Codex brief 31 — audit close-out follow-ups (SEC-01 test pinning + job-health digest wiring)

- **Date:** 2026-08-26 (rev 2, same evening — round-1 independent adversarial review FAILED rev 1 with findings F1–F16; this revision answers all of them)
- **Author:** Claude Fable 5 orchestrating session (claude/codex-handoff-plan-2026-08-22)
- **Executor:** Codex (default model, medium reasoning — both WPs are small and mechanical)
- **Status:** round-2 (final) independent correction review **PASS**, 2026-08-26 evening; all residuals applied. **WP-A: READY FOR HAND-OFF now (separate PR). WP-B: OWNER-GATED — excluded from Codex scope until the owner rules (see WP-B preamble). Landing authority unchanged: draft PR, owner lands.** Receipt: `reports/2026-08-26-briefs-24-29-31-adversarial-review-receipts.md`.
- **Provenance:** Repo-verified against `origin/main@4ab1a385c3ee6a5c97285f9bf0a341f5a69feac5` unless labeled otherwise.

## Why this exists (plain language)

Two loose ends from the 2026-08-25 repository audit:

1. **SEC-01 follow-up (WP-A).** The SEC-01 fix (comment-triggered Claude
   review requires a trusted author association) landed via PR #82
   (`b51e24a`). Its merged body records, under "Known residual gaps
   (follow-up candidates, not blockers)", that the contract test pins the
   job's `if:` authorization string exactly but nothing pins the `on:`
   trigger set, the `permissions:` block, or the auth-gate step wiring.
   **Honest threat statement (corrected per review F1):** there is NO live
   exploit path today — the job gate keys off `github.event_name`
   (`.github/workflows/claude-review.yml:60-71`), so a newly added trigger
   such as `pull_request_target` would be skipped by the existing pinned
   condition. The value of WP-A is (a) catching an *availability*
   regression — e.g. a `pull_request` → `pull_request_target` swap silently
   disabling automatic review, (b) defense-in-depth if the condition test is
   ever relaxed, and (c) pinning the one genuinely unpinned
   security-relevant surface, the `permissions:` block
   (`claude-review.yml:37-45`, which includes `id-token: write` — a widening
   to e.g. `contents: write` would be a real escalation and no test would
   notice).
2. **Job-health digest wiring (WP-B).** The digest tool (brief 21) is fully
   implemented and hardened (PRs #67 + #81, both merged), but nothing
   invokes it: no plist, no wrapper, no ritual step references
   `tools/job_health_digest.py`, and `.tmp/job_health/` exists in no
   checkout. **Authority statement (corrected per review F4):** brief 21
   declared invocation wiring "a follow-up owner step"
   (`docs/superpowers/plans/2026-08-22-21-job-health-digest-codex-brief.md:17`,
   as merged on main). WP-B proposes splitting that step into build (Codex)
   + install (owner). That reassignment, and the creation of an additional
   scheduled job (the TENTH options-validator LaunchAgent on the live
   machine — nine tracked plists across the repo (six in
   `tools/launchagents/` plus research-refresh, repo-rag-health, and
   repo-reconcile elsewhere) and nine options-validator agents installed
   today; correction-round N3), require an explicit owner yes/no; this brief surfaces the question
   and does not decide it. Until the owner says yes, WP-B is not
   hand-off-able.

Neither WP touches strategy, ledger, gates, authority, or any frozen value.

## Verified current state

- `.github/workflows/claude-review.yml:22-35` declares exactly three
  triggers: `pull_request` `types: [opened, synchronize, reopened,
  ready_for_review]` (:28), `issue_comment` `types: [created]` (:30),
  `pull_request_review_comment` `types: [created]` (:35). Repo-verified.
- The job-level `if:` matches only the three event names
  (`claude-review.yml:60-71`); the auth-check step `Check Claude
  authentication` is at :83-94 and exactly two steps carry
  `if: steps.auth.outputs.enabled == 'true'` guards (:105, :119); the
  workflow's own comment (:12-13) documents the auth gate as an
  availability control, not token protection. Repo-verified.
- `tests/test_claude_review_workflow.py` pins `EXPECTED_REVIEW_CONDITION`
  (:8) via exact-string match (:56) and mutation-proves its helper (:34); it
  reads only the `if: >` block (:59-63) — not `on:`, not `permissions:`, not
  any step. Repo-verified.
- PyYAML 6.0.3 IS present in the locked env (`uv.lock`, transitive via the
  `pre-commit` dev group) — but it is not a declared project dependency and
  no repo code imports `yaml` today. Repo-verified. **Decision (review
  F8):** WP-A uses anchored block matching (comment-tolerant, normalized —
  see the WP-A preamble) in the existing test's style; no yaml import, no
  dependency change.
- `tools/job_health_digest.py` CLI: `--as-of` is REQUIRED
  (`:785`, `date.fromisoformat`); `--root`, `--research-root` (default
  `~/options-validator-research`), `--out-dir` (default
  `<cwd>/.tmp/job_health`, :800); out-dir containment rejects an out-dir
  inside a *different* checkout's read root (:746-759); `main()` returns 0
  for every health outcome — "10 PROBLEMS" still exits 0 (:783-806, and the
  merged PR #81 acceptance run). Repo-verified.
- Scheduled-job conventions: all six plists in `tools/launchagents/` set
  `WorkingDirectory: /Users/carsynstephenson/options-validator-ops` and
  invoke the ops copy of their wrapper; wrappers hardcode
  `UV="$HOME/.local/bin/uv"` and export a minimal-safe PATH
  (`tools/schwab_chain_capture.sh:20-24`); the testable-wrapper seam
  precedent is `tools/research_display_refresh.sh:10`
  (`PYTHON_BIN="${RESEARCH_DISPLAY_PYTHON:-...}"`) exercised with fake
  executables by `tests/test_research_display_refresh.py`; the plist-shape
  test precedent is `tests/test_schwab_chain_schedule.py:56-79`
  (`plistlib`-based) and the notification convention is a `CRITICAL:` log
  line + `2>/dev/null`-guarded `osascript`
  (`tests/test_schwab_chain_schedule.py:202-219`). Repo-verified.
- `tools/launchagents/com.carsyn.options-validator.intraday-capture.plist`
  does NOT parse with `plistlib` (XML-invalid `--` inside a comment) —
  do not model the new plist's comments on it (review F11); model on the
  preclose plist.
- The digest consumes the invocation DATE (`datetime.now(_NY_TZ).date()`,
  `:575-602,665`) for the research-freshness check, so the run must happen
  on the same New York calendar date as `--as-of`; no frozen value or
  verdict consumes the clock time. Repo-verified.

## Scope

IN:
- WP-A: tests only — pin the `on:` trigger set, the `permissions:` block,
  and the two named auth-gated steps of `.github/workflows/claude-review.yml`.
- WP-B (owner-gated): a wrapper script + LaunchAgent plist + README section
  + tests for a daily digest run, build only.

OUT — hard stops:
- No change to `.github/workflows/claude-review.yml` itself (WP-A is
  test-side only; if a test reveals the workflow is wrong, STOP and report).
- No change to `pyproject.toml`, `uv.lock`, or the dependency set (review
  F8).
- No change to `tools/job_health_digest.py` behavior.
- No `launchctl` invocation, no install, no writes to
  `~/Library/LaunchAgents`, and no mutation of any ops-checkout git state,
  tracked file, receipt, or ledger. The permitted production writes are the
  digest job's own untracked output AND the wrapper's sibling-convention
  run log, BOTH under the ops checkout's untracked `.tmp/` (correction-round
  N2; see WP-B.1 rationale) — and only when the job the OWNER installs
  runs; nothing in Codex's work or tests writes to any real ops checkout.
- No alerting integration beyond the sibling-convention notification line
  specified in WP-B.4 (Telegram/email remain deferred per brief 21).
- No ledger writes, registrations, authority flips, frozen values,
  live-order paths, provider calls, or network access in tests.

## Work packages

### WP-A — pin the review workflow's trigger, permissions, and auth-gate surface

Extend `tests/test_claude_review_workflow.py`, keeping the existing file's
style: anchored block matching against the workflow text, with each new
check written as a pure function of the workflow string (or an object
parsed from it) so it can be mutation-proved on modified copies in-memory —
no yaml import, no temp files under `.github/` (review F8, F14).
**Comment tolerance (correction-round N1):** both target blocks contain
YAML comment lines (`on:` carries seven, `permissions:` four), so every new
check must strip comment lines and blank lines and collapse whitespace
BEFORE comparing — pinning the semantic content (the trigger→types mapping
and the permission→level mapping), the same normalization idea the existing
test applies at :26. A comment-only edit must NOT fail any new check, and
WP-A.4 proves that with a negative control.

1. Assert the `on:` block is EXACTLY the three triggers with exactly the
   current type lists — no extra trigger of any kind, explicitly including
   `pull_request_target`, `workflow_run`, and `schedule`. This is a
   deliberate exact-contract pin in the `EXPECTED_REVIEW_CONDITION` style: a
   legitimate future trigger change must consciously update the test.
2. Assert the `permissions:` block is EXACTLY its current content
   (`claude-review.yml:37-45`) — a widening (e.g. `contents: write`) must
   fail the test (review F15).
3. Assert auth-gate wiring by EXACT STEP IDENTITY (review F7 — an allowlist,
   not a blanket "every step is guarded" rule, which would false-alarm on
   benign setup steps): the `Check Claude authentication` step exists, and
   the two steps `Load review charter from the base branch` and the
   `anthropics/claude-code-action` step each carry
   `if: steps.auth.outputs.enabled == 'true'` verbatim.
4. Mutation-prove each new assertion the way :34 does, on in-memory modified
   copies: add `pull_request_target:`; widen a permission; strip a step
   guard — each must make the corresponding check fail. Plus the NEGATIVE
   control (correction-round N1): edit only a comment line inside the `on:`
   or `permissions:` block — no check may fail.

WP-A may be handed off, implemented, and reviewed independently of
WP-B's owner gate (review F10; landing authority unchanged).

### WP-B — schedule the job-health digest (build, don't install) — OWNER-GATED

**Gate:** brief 21 assigned invocation wiring to the owner. Codex may start
WP-B only after the owner explicitly approves this build/install split and
the creation of the additional scheduled job. Record the owner's wording in the
implementation PR body.

1. **Placement (review F3, decided):** follow the six-plist convention —
   `WorkingDirectory` is the ops checkout, the plist invokes the ops copy of
   the wrapper, `--root` is the ops checkout, and `--out-dir` is the ops
   checkout's own `.tmp/job_health` (the tool's default when cwd == root).
   Rationale, stated so no one relitigates it silently: `.tmp/*` is
   untracked scratch, deliberately excluded from backup
   (`tools/h7_forward_backup.py:74`) and from every receipt surface; the
   digest writing its own report there mutates no git state, receipt, or
   ledger. Brief 21's "writing anything there is a failure" bound its
   *acceptance run* (a read-only test), not the owner-installed production
   job. The OUT list above encodes exactly this boundary.
2. **Wrapper `tools/job_health_digest.sh`** (zsh, matching sibling wrappers):
   - Derive the repo root and cd there, per the sibling convention
     (`REPO="${0:A:h:h}"; cd "$REPO"` — `tools/schwab_chain_capture.sh:21-23`;
     required: `python -m tools.job_health_digest` imports `config` and the
     `tools` package from cwd; correction-round N4 — `$REPO` is the variable
     used throughout below).
   - Keep a sibling-style run log under `$REPO/.tmp/job_health_digest/`
     (`exec > "$LOG" 2>&1` pattern, `tools/schwab_chain_capture.sh:25-29`;
     permitted by the OUT list per correction-round N2).
   - Hardcode `UV="$HOME/.local/bin/uv"` and export the minimal-safe PATH
     per `tools/schwab_chain_capture.sh:20-24` (launchd supplies a minimal
     PATH; bare `uv` will not resolve).
   - Provide the testable seam per `tools/research_display_refresh.sh:10`:
     `UV_BIN="${JOB_HEALTH_UV:-$HOME/.local/bin/uv}"` (or equivalent) so
     tests can substitute a fake executable (review F5).
   - Full argv (review F2): derive the session date as
     `AS_OF="$(TZ=America/New_York date +%Y-%m-%d)"` (same pattern as
     `tools/research_display_refresh.sh:12`), then run
     `"$UV_BIN" run python -m tools.job_health_digest --as-of "$AS_OF"
     --root "$REPO" --out-dir "$REPO/.tmp/job_health"`. `--research-root`
     is NOT passed — the tool's default (`~/options-validator-research`) is
     the live layout. On an exchange holiday the tool emits `NO_SESSION`
     rows and exits 0 — that is a normal run, not a failure.
   - Exit-code discipline: propagate the tool's exit code; any nonzero exit
     logs a `CRITICAL:` line. (Known limitation, stated honestly per review
     F6: the tool returns 0 even with problems — the surfacing below, not
     the exit code, is what restores visibility.)
3. **Plist**
   `tools/launchagents/com.carsyn.options-validator.job-health-digest.plist`:
   weekdays 16:30 ET (LLM-proposed operational constant, labeled as such;
   the owner may change it at install; per review F13, no frozen value or
   verdict consumes the clock time, and the run must stay on the same NY
   calendar date as `--as-of`, which any daytime hour satisfies). The plist
   MUST round-trip through `plistlib.loads` — model comments on the
   preclose plist, NOT the XML-invalid intraday one (review F11).
4. **Surfacing (review F6 — without this the deliverable relocates the
   silence instead of ending it):** after a successful digest run, the
   wrapper parses the digest's own headline (`ALL OK` / `N PROBLEMS`,
   `tools/job_health_digest.py:688-689`). On `N PROBLEMS` (or any nonzero
   tool exit): emit a `CRITICAL:` log line AND a `2>/dev/null`-guarded
   `osascript` notification, following the pinned sibling convention
   (`tests/test_schwab_chain_schedule.py:202-219`). On `ALL OK`: log one
   ordinary line. No other alerting.
5. **README:** add a per-job `##` SECTION (not a table row — review F12) to
   `tools/launchagents/README.md` with Install / Verify / Uninstall blocks
   in the existing format, stating plainly that installing is an owner
   action.
6. **Tests** (offline, zsh-gated, fake executables via the WP-B.2 seam):
   the wrapper passes exactly the argv above (assert `--as-of` present and
   NY-date-shaped), propagates a nonzero tool exit, emits the CRITICAL +
   notification path on a fake "2 PROBLEMS" headline and the quiet path on
   "ALL OK", and writes nothing outside the fixture checkout's untracked
   `.tmp/` (the digest output dir and the run-log dir are both inside it —
   correction-round N2). Plus a `plistlib` shape test per
   `tests/test_schwab_chain_schedule.py:56-79`.

### Acceptance / verification

```bash
uv run python -m unittest discover -s tests   # full suite; exit code is the verdict
uv run ruff check .
uv run pyright
zsh -n tools/job_health_digest.sh             # WP-B only
git diff --check
```

- WP-A: RED demonstrated first — each new assertion shown failing against a
  counterexample-mutated in-memory copy (recorded in the PR body), then
  green against the real workflow.
- WP-B: wrapper/plist tests green; no test performs network access or
  touches any real ops checkout.
- Each WP's implementation PR is created with `gh pr create --draft`, proven
  `isDraft=true` via `gh pr view --json isDraft`, and STOPS there: no
  make-ready, no merge, no install, no ops sync. WP-A and WP-B ship as
  SEPARATE PRs so the owner-gated half never holds the unblocked half
  hostage (review F10).

## Owner actions this brief surfaces, not performs

1. Rule on WP-B: approve or decline the build(Codex)/install(owner) split of
   brief 21's owner step. WP-B stays out of Codex scope until this ruling.
2. If WP-B is approved and lands: run the README install section on the live
   machine.
3. Later, separately: the deferred alerting decision from brief 21
   (Telegram/email); WP-B.4's notification line is the only surfacing in
   scope here.
