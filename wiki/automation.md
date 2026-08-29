# Automation

Derived map of what runs unattended. Canonical source is the scripts and
LaunchAgent plists themselves — see `docs/monday-runbook.md` for the fullest
verified account. Cross-refs: [[data-layer]] for what gets refreshed,
[[hypotheses]] for who consumes each step, [[dashboards]] for the pages this
rebuilds.

## The daily ritual (07:10 ET, weekdays)
LaunchAgent `com.carsyn.options-validator.daily-ritual` runs
`tools/daily_ritual.sh` from the **ops checkout**
(`~/options-validator-ops`), never the dev checkout. Frozen step order
(`tools/daily_ritual.sh:1-14` header comment, amendment v1.4 + the
2026-07-24 `H10_RITUAL_ORDER_FIX`):

1. Recent-day top-up (`data/recent_topup.py`) → closes refresh.
2. H7 source health (per-name, never blocks the board).
3. H7 data gate — **hard gate**: NO_GO blocks every watcher below, no
   override (`tools/daily_ritual.sh:117-152`).
4. H7 real-paper exit fill/monitor.
5. QM OHLCV refresh, then attractiveness feature rebuild (moved ahead of
   the watchers that consume them on 2026-07-24 — running consumers before
   their own data refresh had been producing false stale/DATA skips).
6. `h7_watch` → `h6_features` → `h6_watch` → H5 `entry_watch` → `h8_watch` →
   `h10_watch`/`h10_observe`.
7. Both dashboards rebuilt ([[dashboards]]).
8. Durability: commits an evidence allow-list, pushes to `origin/main`,
   takes a restic snapshot (`tools/daily_ritual.sh:335-380`).

**Fail-closed semantics**: a branch guard refuses to run at all if the ops
checkout isn't on `main` (`tools/daily_ritual.sh` — added after a 2026-07-20
incident where a concurrent agent left a checkout on a feature branch).
(As of 2026-08-26 the ThetaData key check described here is historical —
ThetaData acquisition is disabled, see [[data-layer]]; the ritual's data
tier now revolves around cached reads plus the Schwab lane, and its Step 8
durability allow-list includes `reports/schwab_chains` since PR #76.)
The data gate NO_GO blocks the whole watcher chain; source
health never blocks the board, only per-name entry bans. Every step logs a
`note`/`crit` line to `.tmp/daily_ritual/<date>_<time>.log`, and the run ends
with an explicit `RITUAL STATUS: OK` or `BROKEN` summary
(`docs/monday-runbook.md`).

## Intraday capture (5×/day)
LaunchAgent `com.carsyn.options-validator.intraday-capture` fires at 09:31,
09:35, 11:00, 13:00, 15:45 ET, writing a 15-name board snapshot receipt under
`reports/intraday_capture/<date>/`. It never commits — the next morning's
07:10 ritual sweeps the prior day's receipts into its evidence commit.
(As of 2026-08-26 the 15:45 slot is also when the Schwab preclose chain
capture writes its exact-session packages — see [[data-layer]]; a 15:30
alignment-check LaunchAgent warns if the ops checkout is behind
`origin/main`, the condition that makes the capture wrapper refuse.)

## Repo-RAG health agent (installed 2026-07-25)
LaunchAgent `com.carsyn.options-validator.repo-rag-health.plist` runs
`scripts/run_repo_rag_health.sh`, which calls `python3 -m repo_rag health`
inside `tools/repo_rag/`, logging to `tools/repo_rag/logs/`. Explicitly
advisory-only: the script's own header states it cannot modify H7 state,
ledgers, positions, hypotheses, or any execution/order path. Merged to main
alongside the H7 entry-path corrections, 2026-07-22
(`ledger/facts.log:17973`).

## Why the ops checkout, and why the branch guard
`tools/daily_ritual.sh` derives its own repo root from its own file location
rather than a hardcoded path, specifically so the unattended job can live in
a dedicated ops worktree (`~/options-validator-ops`) separate from whatever
branch active development sessions are using. The branch guard
(`RITUAL_BRANCH != main` → refuse) is the backstop: it turns "wrong branch"
into a loud, logged refusal instead of silently running unreviewed code
against the real, live H7 forward ledger. `docs/options-validator-readiness.md`
verifies `main == origin/main == ops checkout` as a standing release gate.
