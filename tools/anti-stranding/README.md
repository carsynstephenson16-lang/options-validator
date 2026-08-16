# Anti-stranding system

Purpose: guarantee that **no commit exists in only one place**, that **every
branch with work is visible as a PR**, and that finished worktrees disappear —
while merges into main are automatic ONLY for the owner's own green-CI PRs
that touch no owner-governed path (everything else still lands on the owner).

Built 2026-08-15 after an audit found 16 commits existing only on this laptop,
18 branches unmerged into main with just 2 open PRs, and that the remembered
weekly "branch-sweep" job had never actually been implemented.

## Layers (each catches what the previous one misses)

| Layer | What | Catches |
|---|---|---|
| L0 | Policy: docs/reports commit to `main` directly; branches only for code | ~half of strandings never happen |
| L1 | Global git `post-commit` hook → auto-push after every commit | Claude, Codex, AND manual commits |
| L2 | Claude `SessionEnd` + `WorktreeRemove` hooks → rescue-commit + push | dirty tree at walk-away |
| L3 | Daily 08:15 reconciler → push, PR (≤3/day), rescue, auto-merge green PRs, digest | crashes, Codex sessions, everything else |
| L4 | Owner handles diverged branches, ledger forks, ops sync | — |

**Merge policy (owner-directed 2026-08-15, in-session wording: "i want the
merge to be an automatic decision i dont care"):** the reconciler merges an
open PR only when ALL of these hold — it is the owner's own PR (`--author
@me`) targeting `main` in a repo the owner owns; it is not a draft; every
check on the exact head commit is green (merge pinned to that SHA via
`--match-head-commit`); a PR with zero checks is reported, never merged; and
the diff touches no owner-governed path (`ledger/`, `config.py`,
`docs/superpowers/`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.github/` —
those escalate to the digest for the owner). NOTE: claude-review currently
reports green even when it skips itself (no `CLAUDE_CODE_OAUTH_TOKEN` in CI),
so it is NOT counted as a review guarantee — CI (ruff, pyright, unittest,
gitleaks) is the gate. No merges 15:00–16:30 ET weekdays (ops pre-capture
window), re-checked per PR. The switch is the owner-created flag file
`~/.config/repo-reconcile/automerge` (install.sh sets it to 1 unless the
owner previously opted out; `echo 0 >` reverts). This supersedes the earlier
"L4 owner merges always" design for routine PRs; owner-governed paths,
diverged branches, and ledger forks still land on the owner.

Hard rules baked into every script: never `--force`, never `git add` of
untracked files (repos are PUBLIC — a stray secret must never auto-publish),
never delete (worktree prune is opt-in via `PRUNE=1` and only for provably
merged + clean trees), ops/research checkouts and `main`/`deploy/*` are never
touched, and every side-effect loop (push, PR create, merge) acts only in
repos whose origin belongs to the owner's GitHub account — a cloned upstream
repo (e.g. `~/codex-plugin-cc` → `openai/codex-plugin-cc`) is inventory-only.

## Install (owner-run)

```bash
zsh tools/anti-stranding/install.sh
```

Then test the reconciler harmlessly:

```bash
DRY_RUN=1 ~/bin/repo-reconcile && open ~/Desktop/repo-digest.md
```

## L2 Claude hooks — manual paste (deliberately not automated)

Per the 2026-07-15 hook-lockout lesson (register hooks LAST, after scripts are
tested), merge this into the `"hooks"` object of `.claude/settings.local.json`
in each repo where Claude works, keeping existing entries:

```json
"SessionEnd": [{"hooks": [{"type": "command",
  "command": "zsh \"$HOME/bin/claude-session-rescue.sh\"", "timeout": 60}]}],
"WorktreeRemove": [{"hooks": [{"type": "command",
  "command": "zsh \"$HOME/bin/worktree-remove-guard.sh\"", "timeout": 20}]}]
```

## Uninstall

```bash
git config --global --unset core.hooksPath
launchctl bootout gui/$(id -u)/com.carsyn.repo-reconcile
rm -f ~/Library/LaunchAgents/com.carsyn.repo-reconcile.plist
```

## L0 policy (proposed doctrine amendment — owner ratifies)

Sessions write `reports/**`, `docs/**`, session notes, and parking-lot edits
as commits **directly on `main`** (pushed immediately); branches are used only
for changes touching `options_researcher/`, `tools/`, `config.py`, `data/`,
`ledger/`, `.github/`, or doctrine files. Rationale: 7 of the 13 stranded
branches found on 2026-08-15 contained no code at all. Not yet in force —
requires the owner to amend CLAUDE.md/AGENTS.md (they must not drift apart).

## What stays manual, permanently

- Merging anything that touches `ledger/**`, `config.py`, registrations,
  verdicts, doctrine files, or CI config (auto-merge excludes these paths).
- Syncing `~/options-validator-ops` (it has its own 15:30 ET alignment gate).
- Deleting anything.
