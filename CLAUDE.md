# options-validator — Claude Code instructions

Research platform anchored to four AI-infrastructure core names (VST, CEG,
MSFT, AMZN), plus the owner-authorized H7 story-name watchlist. **Research
only — this is NOT a live bot and places no orders.** A "no edge after costs"
finding is a success, not a failure to fix. The older blanket no-scanner
restriction was retired 2026-07-22 (owner-directed) — do not re-apply it; the
current scope wording is the `.cursorrules` Scope guard together with its
2026-08-03 amendment that retired the pre-verdict ship-blocker.

## Non-negotiable research guardrails

@.cursorrules

The import above is the authoritative wording (hard guardrails, engineering
rules, verdict rule, feasibility gate, claim discipline, vocabulary
discipline, web-fetcher limits, draft-PR authority hold, catalyst-calendar
rule, scope guard and its owner-directed amendments). If sources conflict, say
so instead of picking one silently. `AGENTS.md` is the Codex-facing twin: when
a guardrail changes, update `.cursorrules` and `AGENTS.md` in the same commit
so they cannot drift.

## Start here (single-source index)

Live state is never restated in this file — a copy here goes stale silently.

- **Status, live blockers, next task:** `PROJECT_STATE.md` (canonical head;
  the older plans it lists are superseded; its dated status-refresh log lives
  under `docs/status-history/`). PROJECT_STATE.md governs sequencing; its
  live blockers and standing gates bind and outrank any doc that implies
  building now.
- **Which hypotheses are registered:** `README.md` "Scope status" is the
  registry; `ledger/experiments.jsonl` is the source of truth behind it.
- **Provider transition (ThetaData exit, Schwab lane):** `docs/provider-transition.md`.
- **H7 day-to-day operations:** `docs/h7-forward-operations.md`.
- **Ops checkouts + scheduled jobs (post-merge sync, LaunchAgent install/debug):**
  `tools/launchagents/README.md` and
  `docs/superpowers/plans/2026-08-13-08-fork-healing-ops-sync-canary-runbook.md`.
- **Engine-defect history:** `reports/strategy-evaluations/12_review_of_the_two_landed_commits.md`.
- **Parked ideas:** `ideas-parking-lot.md` — parked is not rejected; it's just not now.
- **Path-scoped rules** load automatically from `.claude/rules/` (ledger,
  data/providers, backtest engine).
- **Procedures (skills):** `.agents/skills/<name>/SKILL.md` (tracked,
  symlinked into `.claude/skills/`); `ls .agents/skills` is the current list —
  read the SKILL.md before performing one. `session-synthesis` writes the
  end-of-session note the Stop hook checks for. `.claude/skills/research-refresh`
  is the scheduled research-context refresh.

## Division of labor (owner directive 2026-07-22)

Claude sessions ORCHESTRATE: research, specs, Codex briefs, review,
verification, owner decision packages. Codex implements from briefs. The owner
types every frozen number, new registration, and verdict ratification.
*Amendment delegation (owner-directed 2026-07-25):* amendments to
already-registered specs may be drafted and recorded by the implementing agent
only after independent adversarial review and Fable's sign-off, and must carry
the provenance label "owner-delegated standing 2026-07-25". The owner retains
veto; a vetoed amendment is corrected by a further append-only amendment.
Delegate heavy reading and routine lifting to subagents (Sonnet for research
and scouting, Opus for adversarial review); reserve the main session for
judgment, synthesis, and integrity checks. Claude writes code directly only
for docs, briefs, and trivial mechanical fixes — not strategy or ledger code.

## Commands

```bash
uv sync --frozen                                 # Python 3.12; uv.lock is source of truth
uv run python -m unittest discover -s tests      # full suite, OFFLINE (~10 min); exit code is the verdict
PYTHONPATH=tests uv run python -m unittest <module> [<module> ...]  # fast loop: named modules (no tests/__init__.py)
uv run ruff check . && uv run ruff format --check . && uv run pyright   # lint + format + types (CI enforces ruff check; format-check is the pre-PR habit)
uv run python tools/irreplaceable_data_guard.py verify  # REQUIRED before deleting any worktree/branch/dir; anchors on the MAIN checkout from any cwd
uv run python -m options_researcher.h7_source_health   # exit 1 = refresh needed
uv run python -m options_researcher.h7_data_gate --source-health-receipt <path>
uv run python -m options_researcher.h7_entry_preflight  # read-only; writes nothing
tools/h7_activation_day.sh                       # one-shot activation-day receipt chain (ops checkout)
uv run python -m options_researcher.schwab_token_age    # offline: hours left on the 7-day Schwab refresh token
uv run python -m options_researcher.dashboard    # writes .tmp/dashboard/index.html
uv run python -m options_researcher.live_dashboard --serve  # display-only live lane
uv run python -m options_researcher.live_quotes --probe  # regular-session schema probe
uv run python -m options_researcher.attractiveness_dashboard
uv run python -m tools.research_context_assemble --verify
uv run python -m options_researcher.robustness --help
```

H7 safety clauses that are easy to forget: `--source-health-receipt` is
REQUIRED on the data gate (a receipt written without it is immutable and
permanently revokes that session's real-entry authority); operator order is
source health → data gate exit 0 → watcher; source-unhealthy names are
entry-banned per-name by the watcher's fail-closed gate (they no longer block
the whole board) but a data-gate NO_GO still blocks the run (amendment v1.4,
2026-07-14); NEVER hand-edit `ledger/h7_forward/*` (append only via the typed
API). The daily procedure is the `daily-ritual` skill.

Tests are `unittest` (not pytest) and must stay runnable offline against the
local parquet cache — no network, no paid API calls. Anything that would hit a
provider endpoint needs owner sign-off first (see `.claude/rules/data-and-providers.md`).

## Layout

- `ledger/` — append-only research ledger. Never rewrite or delete entries.
- `data/`, `.cache/chains/` — parquet chain cache (v1, immutable); `data/positions/` drives the paper book.
- `reports/`, `docs/superpowers/` — dated findings, frozen specs, pre-registrations.

## Research integrity (always on)

- Hypotheses are pre-registered in the ledger before results exist: parameters
  frozen first, run once, result recorded whatever it shows.
- The legacy holdout is sealed (OOS reveal budget 0/3 spent). Never read past
  `IN_SAMPLE_END` without the reveal gate. 2023+ is not a credible blind
  holdout for these names; new hypotheses pre-declare their own validation design.

## Hard enforcement (hooks — treat a block as correct)

- `block_live_trading` (PreToolUse): no live order paths; validator only.
- `block_ledger_edits` (PreToolUse): ledger writes only via typed APIs.
- `session_note_guard` (Stop): work days need a session note (`session-synthesis`).
Hook bodies are tracked in `.agents/hooks/` (see its README); registration is
local in `.claude/settings.local.json` (gitignored by policy). Do not work
around a hook; a block is correct by default. This repo is a validator: it
never places orders, never connects to a live brokerage endpoint, and never
disables paper mode.

## Worktree location rule (owner-directed 2026-08-03)

Worktrees live under `.tmp/worktrees/<short-name>` and **nowhere else** — never
in `/tmp` or `/private/tmp` (macOS purges it), never in `~/Downloads`, never as
a bare sibling directory — so `git worktree list` from this repo stays the
single honest inventory.

Two sanctioned exceptions, both load-bearing for scheduled jobs — **do not
remove or relocate them**: `~/options-validator-ops` (production execution dir
for the `daily-ritual`, capture, and `live-dashboard` LaunchAgents; its `.cache`
is a symlink to this repo's and its `.tmp/` holds live receipts not mirrored
here) and `~/options-validator-research` (sole on-disk location of
`tools/research_refresh.sh` for the `research-refresh` LaunchAgent).

To move a misplaced worktree use `git worktree move` (preserves the branch and
its commits); never `rm -rf` a worktree. Before removing any worktree, branch,
or directory, run `uv run python tools/irreplaceable_data_guard.py verify` AND
check the target for untracked/gitignored data with
`git -C <path> status --short --ignored=matching --untracked-files=all` — the
2026-08-03 od1-v2 incident lost 110 MB of unrepurchasable provider data that
lived only in a worktree and was invisible to every test and manifest.
Since 2026-08-09 the guard anchors on the main checkout from any cwd (running
it from a worktree used to false-report the whole cache as lost); its
`LOCATION ERROR` exit (code 2) means "wrong place", never data loss.

## Conventions

- Root dated notes (`/2026-*.md`, `Untitled*`) are gitignored Obsidian scratch — never commit them.
- Secrets live in `.env` / macOS Keychain (`.env.example` is the template).
- `.claude/rules/` and `.claude/skills/` are tracked and committed (un-ignored
  2026-07-31); the rest of `.claude/` stays local-only.
- `wiki/` is derived operator memory, never source of truth (`wiki/CLAUDE.md`).
