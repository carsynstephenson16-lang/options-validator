# Phase 0 — Repository safety and baseline

- **Research cutoff / run date:** 2026-07-24
- **Operator:** Claude Code session (Lead Research and Implementation Manager workflow)
- **Working branch:** `feature/strategy-enhancement`, created 2026-07-24 from
  `docs/replan-2026-07-22` @ `eb927c8` (which already contains a merge of `main`).
  Branch creation via `git switch -c` — working tree untouched.

## Pre-existing uncommitted work (NOT touched by this workstream)

Recorded from `git status --short --branch` before branch creation:

```
## docs/replan-2026-07-22...origin/docs/replan-2026-07-22 [ahead 9]
 M docs/superpowers/plans/2026-07-22-rq2-scanner-enrichment-briefs.md
?? reports/live_probe/
```

Classification: **UNRELATED PRE-EXISTING, non-blocking.** Both items belong to
other in-flight workstreams (RQ2 briefs doc edits; live-probe reports). This
workstream writes only under `.research/` (and, only if the decision gate
approves, focused code + tests). Neither item is overwritten, staged, stashed,
or reset.

Known hazard (recorded, accepted): the owner sometimes runs multiple sessions
in this one shared checkout. Branch creation from current HEAD changes no
files, but any concurrent session committing during this window would commit
onto `feature/strategy-enhancement`. Mitigation: this workstream makes no
commits (project rule: no commit/push/merge unless explicitly instructed).

## Canonical verification commands (source: CLAUDE.md + .github/workflows/ci.yml)

CI runs exactly: `uv sync --all-groups --frozen`, `uv run ruff check .`,
`uv run pyright`, `uv run python -m unittest discover -s tests`, plus gitleaks.
There is no separate format-check step in CI (ruff lint only; pre-commit adds
`ruff --fix` + hygiene hooks locally).

## Baseline results (before any changes)

| Command | Exit code | Result |
|---|---|---|
| `uv run ruff check .` | 0 | "All checks passed!" |
| `uv run pyright` | 0 | 0 errors, 0 warnings, 0 informations |
| `uv run python -m unittest discover -s tests` | 0 | `Ran 1774 tests in 214.153s` / `OK` — 1774 passed, 0 failed, 0 skipped reported |

Baseline classification: **fully green — no BLOCKING, no RELATED NON-BLOCKING,
no UNRELATED PRE-EXISTING failures.** Any post-implementation failure on these
same three commands would therefore be caused by this workstream's changes.

Note on capture rigor: the suite was run twice. The first run piped through
`tail`, which reported the pipe's exit rather than unittest's; it was re-run
with direct redirection and exit-code capture (`UNITTEST_EXIT=0`). The counts
above come from the second, correctly-captured run.

## Subagent configuration limitation (per workflow §subagent_configuration)

This VS Code extension session's Agent tool does **not** expose hard per-agent
`maxTurns`, `tools` allowlists, `disallowedTools`, or `permissionMode`
configuration at dispatch time, and no suitable pre-existing bounded research
agents exist in `.claude/agents/` (only generic types: claude,
general-purpose, Explore, Plan, plus unrelated specialists). Per the workflow,
I am therefore using **explicit completion rules in each subagent prompt**
(single output file, minimum tools named, explicit tool prohibitions, stop
condition) instead of hard config, and recording that limitation here. No
permanent subagent definitions are being created.

## Repo-context constraints binding on this workstream

- Validator only; never places orders; free-data rule for any NEW data source
  (existing paid ThetaData subscription is already owned and in-stack, but the
  task's business context requires new inputs to be free for live use).
- Scope guard (.cursorrules): any new capability must move a live hypothesis
  toward its verdict; rejected candidates go to `ideas-parking-lot.md`.
- Claim discipline labels and vocabulary discipline apply to all research files.
- Known entitlement fact (memory, 2026-07-24 session): the live scanner runs 5
  snaps/day on ThetaData; stock/greeks endpoints NOT entitled — spot comes from
  options parity. Any intraday *stock volume* requirement is therefore a NEW
  data dependency, not a covered one. To be verified by the licensing
  researcher, not assumed.
