# Codex brief 34 — scoped macOS shell-contract CI job (TST-02)

**Date:** 2026-08-28
**Author:** Claude orchestrating session (Fable), deferred-closeout session
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** HANDED OFF TO CODEX (rev 2) — round-1 independent adversarial
review (Opus, 2026-08-28) verdict PASS WITH FIXES (4); all applied in this
rev; Fable sign-off recorded. Owner directive to proceed: 2026-08-28
in-session ("finish everything that's deferred").
**Provenance:** Repo-verified against origin/main @`704a138`. Finding
source: 2026-08-25 audit TST-02 (candidate registry). Motivating incident:
the macOS-only `/var` → `/private/var` test failure fixed by PR #78.
**Owner directive:** Carsyn in-session 2026-08-28 — ruled "macOS job only"
(repo-rag CI explicitly declined; do not add it).

## Why this exists (plain language)

The automation that actually runs on Carsyn's Mac (daily ritual, capture
wrappers, backups) is only ever CI-tested on Linux. `ci.yml` has two jobs —
`quality` (`:13`, `runs-on: ubuntu-latest` at `:15`) and `secrets`
(gitleaks, `:50`) — and the separate `claude-review.yml` workflow; nothing
anywhere runs on macOS (review fix 2 corrected rev 1's "single job" claim).
Mac-only path/symlink/zsh quirks ship untested — PR #78's `/private/var`
bug is the proof. This adds ONE scoped macOS job running the shell-contract
test modules.

## Design

New job `macos-shell-contracts` in `.github/workflows/ci.yml`:
- `runs-on: macos-14` (pin a numbered image, not `-latest`).
- Same checkout/uv/python setup steps as the existing job, action SHAs
  pinned identically to the current file's pins.
- Invocation (review fix 1 — MANDATED): several test modules do bare
  sibling imports (`tests/test_ritual_receipt.py:12-13` imports
  `test_entry_watch` etc.), so a plain `python -m unittest <module>` dies
  with `ModuleNotFoundError`. Use
  `PYTHONPATH=tests uv run python -m unittest <module list>` (reviewer-
  verified: 15 tests OK) — NOT bare module invocation.
- Module list (review fix 4): rev-1's list was both over-inclusive
  (`test_ritual_authority`, `test_ritual_status`,
  `test_ritual_switch_on_hash_containment`, `test_h7_backup` execute no
  shell — keep `test_h7_backup` anyway: it IS the PR-#78 macOS
  path-semantics regression) and under-inclusive. Concrete candidates that
  DO execute shell: `test_daily_ritual_provenance`,
  `test_shell_banner_guard`, `test_research_view_launchagents`,
  `test_anti_stranding_remote_owner`, `test_ops_alignment_check`,
  `test_research_display_refresh`, `test_research_refresh_guard`,
  `test_schwab_chain_schedule`, `test_job_health_digest_schedule`,
  `test_h7_daily_exit_order`, `test_entry_watch`, `test_h8_watch`,
  `test_intraday_capture`, `test_qm_dashboard`,
  `test_research_context_assemble`. Verify each at implementation time;
  state the final list in the PR body with per-module test + skip counts.
- Env parity (review fix 3 — decided): do NOT set
  `LIVE_MARKET_DATA_PROVIDER` (the existing job sets it at `ci.yml:39-40`;
  none of the candidate modules read it — the ones that care pin it
  themselves). No secrets, no provider env vars, same offline posture.
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
