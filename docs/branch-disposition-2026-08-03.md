# Branch disposition — 2026-08-03

**Decision authority:** owner-directed, this session. The owner approved the
cleanup, then reviewed the per-branch evidence and directed: *"if there already
in then delete them keep the 2 other ones for a future session to decide."*

**What this file is for.** The repo had accumulated 59 local branches and 9
worktrees with no recorded decision about any of them. "No decision" is itself
the defect: a branch nobody has ruled on looks identical to a branch holding
unshipped work. This file records the ruling for every branch so the state is
readable without re-deriving it.

## Result

| | before | after |
|---|---|---|
| local branches | 59 | 5 |
| worktrees | 9 | 3 |
| archive tags | 0 | 18 |

`main` advanced `1818277 → c7b21a9` (fast-forward, docs only: the frozen
worktree-location rule in `CLAUDE.md` + `AGENTS.md`).

## Nothing was lost

Every deleted branch tip is preserved as an annotated tag. To bring any of them
back exactly as it was:

```bash
git switch -c <any-name> archive/2026-08-03/<original-branch-name>
git tag -l 'archive/2026-08-03/*'      # list all 18
```

Tags are pushed to `origin`, so they survive loss of this machine.

## Deleted — verified already on main, or superseded, or dead by rule change

Evidence is a direct file-content comparison against `main`, not a branch-name
guess. Line counts are `wc -l` of the same path on each side.

| Branch | Evidence | Ruling |
|---|---|---|
| `codex/cache-schema-v2` | `data/cache_schema.py` main **345** vs branch **87** | integrated; main 4× further along |
| `codex/od1-v2-backfill` | `tools/thetadata_v2_backfill.py` main **1060** vs branch **475**; the approved capture completed (`reports/thetadata_v2/2026-08-02-od1-full-audit.md`); OD-4 disabled further acquisition | integrated + job finished |
| `feature/h7-real-entry-path-main` | `h7_paper_lifecycle.py` main **1907** vs branch **1428** | integrated via the reviewed one-door path |
| `luna/research-hardening-20260727` | `tools/research_refresh_guard.py` **byte-identical** (460 = 460); main ahead on `research_context_assemble.py` (413 vs 391) and `research_refresh.sh` (258 vs 251) | integrated |
| `feature/strategy-enhancement` | `docs/evidence-upgrade/decision-log.md` main **1048** vs branch **836** | main is ahead; merging would have regressed history |
| `feature/bs-attractiveness-descriptive` | H10a/H10b are present in `ledger/experiments.jsonl`; the one-off scripts were deliberately not retained | job finished |
| `ci/claude-pr-review` | main already has `id-token: write` **and** pins actions to exact SHAs (`actions/checkout@11d5960…`); branch floats `@v4`/`@v1` | superseded; merging would have regressed supply-chain safety |
| `data-layer` | `data/alphavantage.py`, `data/dolthub.py` never existed on main; Alpha Vantage was probe-confirmed to carry no options data on the free tier | dead end, 777 commits stale |
| `parking/market-data-bundle-2026-07-20` | `market_data/` never on main; Schwab shipped instead as `data/schwab_adapter.py` (454 lines, live); self-labeled "NOT for main"; OD-4 removed the purpose | superseded by a simpler design |
| `feature/h7c-report-gated-exit` | author's own commit message: "should not land on main without coverage proving it"; main enforces `H7C_CLOSE_BEFORE_EARNINGS` a tested way | superseded |
| `docs/replan-2026-07-22` | 0 commits ahead of main | contained in main |
| `feature/h7-real-entry-path` | 0 commits ahead of main | contained in main |
| `agent/h7-entry-authority-review` | `git cherry`: 0 unique commits | content on main as `9eac0f4` |
| `codex/main-closeout-20260802` | `git cherry`: 0 unique of 8 | contained in main |
| `root/cache-hardening-20260727` | `git cherry`: 0 unique of 4 | contained in main |
| `codex/reliability-profile-20260802` | `git cherry`: 0 unique | on main as `docs/reliability/`, `scripts/reliability_checklist.py` |
| `fix/dashboard-refresh-freshness` | `git cherry`: 0 unique | contained in main |
| `feature/h7-stage4-spec` | `git cherry`: 0 unique | contained in main |

Also deleted: 35 branches that `git branch --merged main` confirmed were fully
contained in `main` (including 9 stale `worktree-agent-*` scratch branches).
These carried no unique commits and were not tagged.

## KEPT — hold code that exists nowhere on main

Owner directed these stay for a future session. **Do not merge either as-is**:
both are hundreds of commits stale and target a retired path.

### `codex/h7-stage8-critical-20260717` (403 behind main)

`options_researcher/h7_event_ledger.py` on this branch is 1088 lines vs main's
475, and **main has zero functions the branch lacks**. Sixteen validation
functions were confirmed absent from all of `options_researcher/` and `tools/`
on main:

```
_validate_window_registration_payload   _validate_window_registration_position
_validate_registration_timing           _validate_registration_timestamp
_validate_evidence_reference            _validate_input_references
window_registration_universe_hash       require_synthetic_store
_canonical_data_gate_input_paths        _latest_completed_xnys_session
_is_checkout_forward_store              _parse_session_date
_require_exact_object                   _require_nonempty_string
_require_sha                            _add_months
```

These check that an H7 window registration is well-formed *before* it is
written to the permanent record. **Caveat:** they guard the **old** H7
registration path. Per `reports/h7_forward/2026-08-02-restart-decision.md`, H7
may only restart under a **new registration and a new namespace** — so this is a
source to harvest ideas and test cases from, not code to merge.

### `codex/qm-dashboard-integration-20260717` (403 behind main)

Two fail-closed guards absent from main: `_frozen_symbol_or_block` and
`_not_in_frozen_study` — they refuse to display a symbol that was not part of
the frozen study. Small, but the intent is the kind of thing this repo wants.
Harvest the idea; do not merge the branch.

## Worktrees

Six `.tmp/worktrees/*` checkouts were removed. Before each removal, per the
worktree rule frozen in `CLAUDE.md`, both checks were run and recorded:

- `uv run python tools/irreplaceable_data_guard.py verify` → `irreplaceable data: OK`
- `git -C <path> status --short --ignored=matching --untracked-files=all`

Every removed worktree held only reproducible artifacts (`.venv/`,
`__pycache__/`, lint caches) and an **empty** `.cache/` (0 bytes, 0 parquet
outside `.venv`). The only parquet files present anywhere under
`.tmp/worktrees/` were 20 pyarrow **library test fixtures** inside `.venv`
(100 KB total, restored by `uv sync`).

> A note on method, because it is the whole lesson of the 2026-08-03 od1-v2
> incident: measuring `.cache/` alone is **not** sufficient. The first audit
> pass reported "0 bytes at risk" from a `.cache`-only measurement while 20
> parquet files sat elsewhere in those same directories. They turned out to be
> harmless test fixtures, but the method would not have caught real data.
> Always sweep the whole worktree for data extensions, then classify.

Remaining worktrees — all three are load-bearing, none may be removed:

| Path | Branch | Why it exists |
|---|---|---|
| `/Users/carsynstephenson/options-validator` | `chore/branch-consolidation-2026-08-03` | primary checkout |
| `/Users/carsynstephenson/options-validator-ops` | `main` | `WorkingDirectory` for the `daily-ritual` and `live-dashboard` LaunchAgents |
| `/Users/carsynstephenson/options-validator-research` | `deploy/research` | sole on-disk home of `tools/research_refresh.sh` for the `research-refresh` LaunchAgent |

## Standing rule going forward

A branch with no recorded decision is a defect, not a neutral state. When work
finishes, it gets one of three rulings the same day — **merge**, **archive-tag
and delete**, or **an entry in this file naming what must happen next and who
decides**. Delete only after both the guard and the `--ignored` sweep are run
and their output recorded.

Remote branches on `origin` were **not** deleted in this pass; only local
branches were pruned. Cleaning up `origin` is a separate, explicitly
owner-gated decision.

## Addendum — origin cleanup EXECUTED 2026-08-04

The owner delegated resolution of the origin branch list in-session on
2026-08-03 ("complete all tasks 1–5 … decide what needs to be done"). Executed
2026-08-04 from the primary checkout after `irreplaceable_data_guard.py verify`
returned OK (run from the main checkout — the guard false-alarms from
worktrees, which have no `.cache/`):

- Verified per-branch before deletion: 19 of the 24 stale origin branches had
  tips reachable from `origin/main` (fully merged — zero commits at risk); the
  other 5 (`agent/h7-entry-authority-review`, `ci/claude-pr-review`,
  `feature/h7-real-entry-path-main`, `feature/h7-stage4-spec`,
  `parking/market-data-bundle-2026-07-20`) were each present in the local
  repository AND pinned by an `archive/2026-08-03/*` tag already pushed to
  origin, so their commits remain fetchable server-side via tags.
- Zero open PRs at execution time (`gh pr list --state open` empty).
- Deleted all 24; `origin` now holds exactly `main` and `sfix`.
- The two KEPT local branches (`codex/h7-stage8-critical-20260717`,
  `codex/qm-dashboard-integration-20260717`) remain harvest-only per the
  ruling above; the qm branch's fail-closed display-guard concepts were
  harvested into the composite-signal lane design
  (`reports/2026-08-04-composite-signal-lane-decision.md`).
