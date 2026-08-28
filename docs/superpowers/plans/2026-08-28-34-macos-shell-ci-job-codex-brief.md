# Codex brief 34 — scoped macOS shell-contract CI job (TST-02)

**Date:** 2026-08-28
**Author:** Claude orchestrating session (Fable), deferred-closeout session
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** DRAFT — pending independent adversarial review before hand-off
**Provenance:** Repo-verified against origin/main @`704a138`. Finding
source: 2026-08-25 audit TST-02 (candidate registry). Motivating incident:
the macOS-only `/var` → `/private/var` test failure fixed by PR #78.
**Owner directive:** Carsyn in-session 2026-08-28 — ruled "macOS job only"
(repo-rag CI explicitly declined; do not add it).

## Why this exists (plain language)

The automation that actually runs on Carsyn's Mac (daily ritual, capture
wrappers, backups) is only ever CI-tested on Linux (`ci.yml:15`
`runs-on: ubuntu-latest`, single job). Mac-only path/symlink/zsh quirks
ship untested — PR #78's `/private/var` bug is the proof. This adds ONE
scoped macOS job running only the shell-contract test modules.

## Design

New job `macos-shell-contracts` in `.github/workflows/ci.yml`:
- `runs-on: macos-14` (pin a numbered image, not `-latest`).
- Same checkout/uv/python setup steps as the existing job, action SHAs
  pinned identically to the current file's pins.
- Runs ONLY the shell/ops contract modules, by explicit module list (not
  discovery), e.g.: `test_daily_ritual_provenance`, `test_ritual_authority`,
  `test_ritual_receipt`, `test_ritual_status`,
  `test_ritual_switch_on_hash_containment`, `test_shell_banner_guard`,
  `test_research_view_launchagents`, `test_h7_backup` — VERIFY this list
  against the installed tree at implementation time and include any other
  module whose tests execute `zsh`/shell wrappers; state the final list in
  the PR body with a per-module test count and skip count.
- Offline discipline: same no-network posture as the suite's contract;
  no secrets added to the job; no provider env vars.
- Cost note for the PR body: macOS minutes bill ~10× Linux
  (Official-source: GitHub Actions billing docs — cite the current page);
  the scoped list keeps the job to a few minutes.

## Scope

**IN:** the one job + PR-body documentation.
**OUT (hard stops):** no repo-rag CI job (owner-declined 2026-08-28); no
change to the existing Ubuntu job, its coverage run, or required-check
configuration beyond the new job's presence; no new secrets; no
`macos-latest` floating tag; no test-file edits (if a module fails on
macOS, STOP and report — that is the job doing its work, not a thing to
paper over in this brief).

## Acceptance

- CI green on the PR with the new job visible, running the stated module
  list, exit 0.
- `uv run python -m unittest <module list>` exit 0 locally on this Mac
  (pre-flight before pushing).
- Born-draft PR; owner un-drafts.
