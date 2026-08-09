# Fable 5 skill & instruction-asset audit — options-validator

Date: 2026-08-08. Mode: `--apply` (default; no arguments supplied). Scope: active repository only (no `--include-personal`). Auditor: Claude Fable 5 orchestrating Sonnet subagents (inventory, doc refresh, body audit, 6 eval contexts, independent verifier).

## 1. Outcome summary

- **21 in-scope instruction assets audited; 20 clean, 1 defect found and fixed.**
- **2 files changed, 15 lines inserted, 0 lines deleted or reworded.** Both edits are additive fail-closed/maintainability improvements to the `independent-research-critic` asset pair. No guardrail wording was touched anywhere.
- **Eval: 6 fresh-context baseline/candidate runs.** Candidate deterministic and correct on both failure cases; byte-equivalent behavior on the normal path. Baseline confirmed non-deterministic (invented two *different* status strings for the same failure class across two runs).
- **Independent verifier: PASS on all 6 checks.** `git diff --check` clean; all frontmatter parse-valid before and after.
- **1 recommendation deliberately not applied** (see §8), 0 regressions, 0 pre-existing failures in scope.

## 2. Repository state

- Root: `/Users/carsynstephenson/options-validator`; branch `docs/cross-project-source-standard-2026-08-03`, in sync with origin; baseline = clean tree at `32afcc8cc6925ebaf810f916e9dc973a76192a14`.
- Claude Code 2.1.220; session model Fable 5 (`claude-fable-5`); subagent work on Sonnet.
- Worktrees present (none entered, none touched): `~/options-validator-ops` (main), `~/options-validator-research` (deploy/research), three under `.claude/worktrees/`.
- Hook registrations in `.claude/settings.local.json` (gitignored) verified to exactly match CLAUDE.md's "Hard enforcement" section: `block_live_trading.py` + `.agents/hooks/block_ledger_edits.py` (PreToolUse), `session_note_guard.py` (Stop).
- Plugins: skill-creator plugin skills are present in the environment but were not needed; evals were run as fresh-context A/B subagent comparisons (see §7).

## 3. Official source ledger (all accessed 2026-08-08, Anthropic-owned domains only)

| Page | Domain | Key rules extracted |
|---|---|---|
| Prompting best practices | platform.claude.com (redirect from docs.claude.com), `/docs/en/build-with-claude/prompt-engineering/claude-4-best-practices` | Clear-and-direct golden rule; long inputs before query; prefill deprecated on 4.6+; fixed thinking budgets deprecated on 4.7+ |
| Prompting Claude Fable 5 | platform.claude.com `/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5` | `reasoning_extraction` refusal category (never ask for visible reasoning transcription); older skills often over-prescriptive for Fable 5; ground progress claims in tool results; thinking always on, `effort` is the control |
| Extend Claude with skills | code.claude.com `/docs/en/skills` | Valid frontmatter field set (20 fields); combined `description`+`when_to_use` truncated at 1,536 chars in listing; SKILL.md under 500 lines; skill content persists in context; `disable-model-invocation` also blocks scheduled-task auto-fire (v2.1.196+) |
| Skill authoring best practices | platform.claude.com `/docs/en/agents-and-tools/agent-skills/best-practices` | Portable spec hard limits: `name` ≤64 chars lowercase-hyphen, `description` ≤1,024 chars, third person; only 6 fields valid outside Claude Code; references one level deep |
| How Claude remembers your project | code.claude.com `/docs/en/memory` | CLAUDE.md target under 200 lines; `@` imports load at launch (don't reduce context); path-scoped `.claude/rules` with `paths:` load lazily; Claude Code reads CLAUDE.md not AGENTS.md |
| Create custom subagents | code.claude.com `/docs/en/sub-agents` | Valid agent frontmatter; `model:` values incl. `fable`; background-by-default since v2.1.198 |
| Hooks reference | code.claude.com `/docs/en/hooks` | Exit 0/2/other semantics; per-event blocking table; matcher regex rules |
| Model configuration | code.claude.com `/docs/en/model-config` | Current aliases (`fable`, `best`, `opus`, `sonnet`, `haiku`, …); effort tiers; Fable 5 requires explicit selection |
| Run prompts on a schedule | code.claude.com `/docs/en/scheduled-tasks` | Routines / Desktop tasks / `/loop`; a bare OS LaunchAgent invoking the CLI is neither endorsed nor rejected (UNVERIFIED beyond the doc's literal text) |

Unverified items: none load-bearing. The only rule marked inference was the synthesis distinguishing the 1,024-char portable hard limit from the 1,536-char Claude Code display truncation.

## 4. Inventory (complete)

**Skills — `.agents/skills/*/SKILL.md`, all tracked, all symlinked from `.claude/skills/`, no supporting files, all frontmatter `name`+`description` unless noted:**

| Skill | Lines | Desc chars | Trigger | Risk | Action |
|---|---|---|---|---|---|
| backtest-realism-audit | 40 | 346 | model | med | unchanged |
| daily-ritual (`disable-model-invocation: true`) | 95 | 128 | user-only | high | unchanged |
| grilling | 11 | 493 | model | low | unchanged |
| independent-research-critic | 136→146 | 233 | model | med | **changed** |
| ledger-discipline | 26 | 297 | model | high | unchanged |
| obsidian-vault | 75 | 200 | model | low | unchanged |
| options-beginner-explainer | 32 | 408 | model | low | unchanged |
| options-data-audit | 45 | 310 | model | med | unchanged |
| repo-health-review | 28 | 532 | model (self-gated to on-request) | low | unchanged |
| results-red-team | 38 | 573 | model | med | unchanged |
| session-synthesis | 42 | 240 | user + Stop-hook-adjacent | low-med | unchanged |
| verdict-interpreter | 35 | 300 | model | low-med | unchanged |
| web-fetch-order | 58 | 389 | model | med | unchanged |

**Other assets:**

| Asset | Runtime | Risk | Action |
|---|---|---|---|
| `.claude/skills/research-refresh/SKILL.md` (tracked real dir, sole non-symlink; scheduled via LaunchAgent → `claude -p "/research-refresh"`) | skill, scheduled | high | unchanged (recommendation §8) |
| `.claude/rules/backtest-engine.md`, `data-and-providers.md`, `ledger.md` (path-scoped via `paths:`) | rules | med/high | unchanged |
| `CLAUDE.md` (147 lines), `AGENTS.md` (290), `.cursorrules` (98), `REVIEW.md` (46), `wiki/CLAUDE.md` (11) | claude-md / agents-md / shared | high | unchanged |
| `.agents/hooks/README.md` + `block_ledger_edits.py` (docstring cross-checked vs README: consistent) | hook | high | unchanged |
| `.agents/rules/independent-research-critic.md` (Codex-facing, surfaced by content search — previously invisible to the CLAUDE.md chain) | other-agent rule | med | **changed** |
| `.github/workflows/claude-review.yml` (embeds live REVIEW.md-driven review prompt, `--model sonnet` deliberate) | CI prompt | med | unchanged |
| `.serena/project.yml` (gitignored, local-only Serena config with `initial_prompt`) | other | low | unchanged, noted |

Excluded as non-assets: dated plan/handoff docs under `docs/superpowers/plans/` (one-shot briefs), `ci.yml` (no agent instructions), root dated Obsidian notes.

**Reference validation:** every file, command, module, and path referenced by every asset was checked on disk — **zero broken references**. All 12 `uv run` commands in CLAUDE.md resolve to existing modules. The only missing target, `reports/attractiveness_research/`, is the expected-but-never-produced output tree of the blocked research-refresh pipeline (environmental, not a doc defect — it is what motivated the one applied fix).

**Twin-drift checks:** CLAUDE.md vs AGENTS.md vs `.cursorrules` guardrail text — verbatim-consistent, no drift. `wiki/CLAUDE.md` vs obsidian-vault skill — consistent (near-verbatim subset, noted as future drift surface). Hook README vs script docstring vs settings registration — consistent.

## 5. Findings by severity

1. **Medium — fixed.** `independent-research-critic/SKILL.md` had no defined output when `reports/attractiveness_research/` (or any `manifest.json`) is absent — a state that is *currently live* on this checkout. Its two defined terminal outputs (`HARD_CONTRADICTION`, `[NO_NEW_INPUT]`) both presuppose a located manifest. Eval confirmed agents improvise non-deterministically in that state (two runs produced two different invented status strings), in a skill whose outputs feed receipt comparison.
2. **Low — fixed.** `.agents/skills/independent-research-critic/SKILL.md` and `.agents/rules/independent-research-critic.md` encode the same guardrails (run_id/SHA binding, no-mtime, PJM_BRA_NEXT, read-only) with no cross-link in either direction — an edit-one-miss-the-other drift risk, aggravated by the rules file being invisible to the CLAUDE.md/`.cursorrules` chain.
3. **Low — recommendation only.** `research-refresh` is model-invocable (no `disable-model-invocation`) despite being a high-risk scheduled pipeline; see §8.
4. **Informational.** AGENTS.md "Preferred Codex Session Configuration" pins Codex-side model names (GPT-5.6 xhigh/high, Terra medium) — unverifiable from Anthropic docs, out of this audit's jurisdiction, left for owner awareness.
5. **Informational.** `claude-review.yml` is gated on the `CLAUDE_CODE_OAUTH_TOKEN` repo secret, whose presence cannot be confirmed from the filesystem; REVIEW.md may be governing a bot that isn't currently firing.
6. **Clean sweep results:** zero hits repo-wide (in-scope set) for reasoning-transcription instructions (Fable 5 `reasoning_extraction` risk), prefill patterns, fixed-thinking-budget language, deprecated model names, retired-rule references (pre-verdict ship-blocker, blanket no-scanner), or unsupported frontmatter. All descriptions third-person, under the 1,024-char portable limit, matching their directory names.

## 6. Changes applied (exact reasons)

1. `.agents/skills/independent-research-critic/SKILL.md` — inserted 5 lines in §1 step 3: on missing tree/manifest, return exactly `[NO_INPUT] No finalized attractiveness_research manifest exists to audit.` and stop; never audit `manifest.pending.json` in its place. Reason: finding #1; pattern matches the skill's existing machine-checkable sentinels.
2. Same file — appended 6-line "Maintenance" section pointing to the condensed Codex twin, worded to match the repo's existing CLAUDE.md/AGENTS.md twin convention. Reason: finding #2.
3. `.agents/rules/independent-research-critic.md` — appended 4-line source-of-truth pointer back to the SKILL.md. Reason: finding #2.

## 7. Evaluation results (baseline vs candidate, fresh contexts)

Design: executing the skill for real would require fabricating research manifests inside the real `reports/` tree (state pollution this repo forbids), so evals were behavioral: six fresh Sonnet contexts, each given one unlabeled version (neutral filenames `skill_A`/`skill_B`, no version knowledge, no repo access) plus fully specified filesystem facts, asked for steps and exact final output.

| Case | Baseline (HEAD) | Candidate (edited) | Verdict |
|---|---|---|---|
| Missing tree (edge, live on this checkout) | Explicitly reported "skill defines no output"; improvised multi-paragraph `NO_INPUT_FOUND` message | Exact `[NO_INPUT]` sentinel, stopped at step 3, never consulted receipts | candidate |
| Pending-manifest-only (trap) | Improvised a *different* sentinel `[NO_VALID_INPUT]` + prose | Same exact `[NO_INPUT]` sentinel; refused pending manifest | candidate |
| Normal FINAL manifest + non-matching prior receipt | Full audit: all §1 gates PASS, duplicate gate correctly not triggered, exact §6 headers | Identical behavior, identical headers | tie (required) |

Critical assertions: candidate deterministic on both failure paths (2/2 exact-string match); zero happy-path deviation; trigger behavior unchanged by construction (frontmatter untouched, confirmed in diff). Token/time metrics: not reported per-case (harness exposes only aggregate subagent totals). **Change accepted.** Temporary eval files under `/tmp` were removed after use; no durable eval fixtures kept (the scenarios are documented here and cheap to reconstruct).

## 8. Rejected / not-applied proposals

1. **`disable-model-invocation: true` on `research-refresh`** — safety tightening consistent with its sibling `daily-ritual`, and current docs (v2.1.196 note) plus the invocation path (`tools/research_refresh.sh` runs `claude -p "/research-refresh"`, a user-style prompt invocation, not a Claude Code scheduled task) suggest the LaunchAgent path would keep working. NOT APPLIED because that suggestion cannot be tested without executing the unattended production pipeline (network + provider spend + FINAL-artifact publication — all forbidden here), and a wrong guess kills a scheduled job silently. **Recommended for the owner**: add the field, then watch the next LaunchAgent run's log to confirm the refresh still fires.
2. **R2 (over-prescription) candidates** — daily-ritual's repeated "Never" rules, options-beginner-explainer's rigid template, research-refresh's schemas: all judged deliberate (side-effect guardrails, owner-mandated accessibility contract, JSON-schema precision), not weak-model workarounds. Left alone; style preference alone is insufficient evidence.

## 9. Unchanged assets

The 18 assets not named in §6, for the reasons in §4/§5: body audit returned "clean" on every rule (R1–R7) for all of them, and the guardrail-bearing files (CLAUDE.md, AGENTS.md, `.cursorrules`, daily-ritual, ledger-discipline, rules/, hooks README, REVIEW.md) additionally fall under the touch-only-with-strong-evidence bar, which nothing met.

## 10. Protected-boundary checks

- Diff is 100% additive (15+/0−); verifier confirmed the read-only mandate, HARD_CONTRADICTION lineage rule, `[NO_NEW_INPUT]` duplicate gate, mtime prohibition, PJM_BRA_NEXT requirement, never-recommend-trades rules, and all frontmatter are untouched.
- No H5–H10 spec, gate ordering, `--as-of` handling, NO_GO semantics, entry-ban logic, or execution-authority boundary appears anywhere in the diff. No ledger path, hook script, settings file, or code file touched. No ThetaData/live/provider call made; no install, commit, push, branch, stash, reset, or history rewrite; no worktree entered.
- The one behavioral change *strengthens* fail-closed behavior (defined refusal replaces improvisation).

## 11. Validation commands and outputs

- Frontmatter/JSON validation (PyYAML from the existing venv, no installs): all 14 SKILL.md + 3 rules files parse; only valid fields; names match dirs; max description 573 ≤ 1,024 → `ALL PARSE-VALID`; `settings.local.json` → `valid JSON`. Re-run post-edit via verifier item C: PASS (146 lines, frontmatter unchanged).
- `git diff --check` → clean (no whitespace errors).
- `git diff --stat` → exactly 2 files, 15 insertions, 0 deletions.
- Symlink integrity: `.claude/skills/independent-research-critic` → resolves to edited file, content IDENTICAL (verifier item D).
- Repo test suite: no test references any in-scope markdown asset (`grep -rl` over `tests/` → empty), so no suite run was required by this change class; no pre-existing failures observed or introduced in scope.
- Fresh verifier subagent: PASS on all items A–F (file scope, additivity, parse/placement, symlink, safety sweep, cross-consistency).

## 12. Remaining risks / blocked items

- `research-refresh` model-invocability recommendation (§8.1) awaits an owner decision + one observed scheduled run.
- `reports/attractiveness_research/` remains unpopulated until the owner completes the launchctl bootstrap (pre-existing, tracked in memory/PROJECT_STATE lineage) — the new `[NO_INPUT]` path covers the interim honestly.
- `CLAUDE_CODE_OAUTH_TOKEN` secret presence (PR-review bot liveness) is unverifiable from the filesystem.
- This branch (`docs/cross-project-source-standard-2026-08-03`) now carries uncommitted changes; commit/merge timing stays with the owner per repo policy. Per the universal branch-hygiene rule, any commit made from this session should be pushed to origin before the session ends.
