# Anti-stranding system

Purpose: guarantee that **no commit exists in only one place**, that **every
branch with work is visible as a PR**, and that finished worktrees disappear —
while every merge into main stays an owner decision (one tap on GitHub).

Built 2026-08-15 after an audit found 16 commits existing only on this laptop,
18 branches unmerged into main with just 2 open PRs, and that the remembered
weekly "branch-sweep" job had never actually been implemented.

## Layers (each catches what the previous one misses)

| Layer | What | Catches |
|---|---|---|
| L0 | Policy: docs/reports commit to `main` directly; branches only for code | ~half of strandings never happen |
| L1 | Global git `post-commit` hook → auto-push after every commit | Claude, Codex, AND manual commits |
| L2 | Claude `SessionEnd` + `WorktreeRemove` hooks → rescue-commit + push | dirty tree at walk-away |
| L3 | Daily 08:15 reconciler → push, PR (≤3/day), rescue, digest on Desktop | crashes, Codex sessions, everything else |
| L4 | Owner merges. Always. | — |

Hard rules baked into every script: never `--force`, never `git add` of
untracked files (repos are PUBLIC — a stray secret must never auto-publish),
never merge, never delete (worktree prune is opt-in via `PRUNE=1` and only for
provably merged + clean trees), ops/research checkouts and `main`/`deploy/*`
are never touched.

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

- Every merge into main (GitHub mobile app works).
- Anything touching `ledger/**`, frozen numbers, registrations, verdicts.
- Syncing `~/options-validator-ops` (it has its own 15:30 ET alignment gate).
- Deleting anything.
