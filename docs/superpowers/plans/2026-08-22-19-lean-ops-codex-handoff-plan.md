# Lean-ops program — master hand-off & coordination plan

- **Date:** 2026-08-22
- **Author:** Claude Fable 5 orchestrating session (five-project audit, same day)
- **Status:** DRAFT — pending independent adversarial review before hand-off
- **Provenance:** Repo-verified against origin/main @accd165bd2a7aeacf8ff6f1630d0b3b815b39703 unless labeled otherwise. Kalshi facts verified against ~/Claude.prod/claude @957d283d; equity-research facts against @b1cf011.

## Why this exists (plain language)

The 2026-08-22 five-project audit (options-validator, equity-research, sunwest-lead-engine, tik tok shop, kalshi bot) found: (1) laptop-only commits in three repos, (2) an incomplete backup allow-list covering only part of the guard-protected irreplaceable cache, (3) two silently failing equity-research scheduled jobs (one burning ~$2/week), (4) a Kalshi alert channel that has been muted for 104 days by its own dedup cap, and (5) ~30 GB of safely reclaimable disk on a 92%-full drive. n8n was evaluated and rejected (launchd replays missed jobs on wake; the observed failures are ones n8n retries would not fix; visibility is solved by a $0 receipt-reading digest).

This plan routes every remediation to the right executor. **Codex gets only tightly-scoped coding work with its own brief. Everything requiring judgment, authority, or destruction stays with the owner or the orchestrating Claude session.**

## Routing table (the whole program at a glance)

| # | Work | Executor | Where | Order gate |
|---|---|---|---|---|
| 1 | Push laptop-only branches (OV: `rescue/detached-fca78a0` — the only unpushed OV branch as of 2026-08-22; `claude/merge-sweep-2026-08-22` verified already pushed; kalshi: both checkouts to GitHub; tik tok: create remote + push; equity-research: 15 no-upstream branches) | Owner or Claude session (mechanical git, no code) | per-repo | FIRST — before any deletion anywhere |
| 2 | Extend backup allow-list to all guard namespaces + drill | **Codex** | brief 20 (this repo) | before any pruning of OV data |
| 3 | Off-machine backup destination (drive/cloud) + run backup | Owner (spend/hardware decision) + Claude session | — | after #2 merges |
| 4 | Job-health digest tool (receipt readers, not exit codes) | **Codex** | brief 21 (this repo) | independent |
| 5a | Kalshi halt-alert long-tail re-notify | Owner ruling FIRST (`~/Claude.prod/docs/deferred-actions.md` item 8 pre-registers this with an unfired trigger; doctrine wins) → then Codex | WP-0 of the kalshi brief | owner-gated |
| 5b | Kalshi log growth control (rotation + reader-safety) | **Codex** | brief in ~/Claude.prod/claude/docs/briefs/ | independent |
| 6 | equity-research repo-rag repair (agent knobs, cross-run budget guard, hooksPath) | **Codex** | brief in ~/equity-research/docs/briefs/ | independent |
| 7 | equity-research one-shot: run `python -m repo_rag health --rebuild` once; `git config core.hooksPath scripts/hooks` | Owner or Claude session (one-liners, not code) | — | anytime |
| 8 | Reload kalshi orderbook recorder: `launchctl load ~/Library/LaunchAgents/com.kalshi.weatherbot.orderbook_recorder.plist` | Owner | — | anytime |
| 9 | Pruning pass (worktree `.venv`s ~22 GB, `uv cache prune` ~8 GB, edgar `*/cache/` ~3.4 GB, kalshi dup DBs ~2.7 GB) | Claude session with owner present (destructive; guard verify + `git status --ignored` per target; NEVER whole worktrees) | — | ONLY after #1–#3 |
| 10 | Kalshi paper_trades.db retention design | Claude session study first (map read-ranges in `risk/calibration_circuit.py`, `engine/calibration.py`) — NOT Codex until a spec exists | — | after study |
| 11 | tik tok: reconcile PROJECT_STATE.md + spend ledger, commit untracked production scripts | Claude session (judgment + provenance) | — | after its push in #1 |
| 12 | Finishing options-validator = the ten owner decisions inventoried in the package (IDs are the package's own audit numbering; its D7 was a duplicate of D4 and is merged into it) | **Owner**, guided | `reports/2026-08-22-owner-decision-package-finishing-ov.md` | see package |

## Explicitly NOT delegated to Codex

- Any deletion, `git worktree remove`, branch deletion, or retention enforcement.
- Any ledger write, registration, authority flip, frozen value, or merge decision.
- The paper_trades.db archival (no spec yet; the three biggest tables feed the halt/Brier/CLV computation — Repo-verified: `risk/calibration_circuit.py`, `engine/calibration.py`, CLV columns per ~/Claude.prod/CLAUDE.md:216).
- tik tok repo changes (iCloud-evicted files; no remote; supervised-run doctrine).

## Standing verification rule for the pruning pass (#9)

Per target, in order: `uv run python tools/irreplaceable_data_guard.py verify` (exit 0 baseline) → `git -C <target> status --short --ignored=matching --untracked-files=all` (empty of surprises) → delete → guard verify again and compare. `.venv` directories inside worktrees are the only wholesale-deletable payload; the worktrees themselves stay.
