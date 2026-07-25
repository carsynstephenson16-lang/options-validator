# Monday runbook — 2026-07-27 scheduled run

Written 2026-07-25 (readiness review). Every command below was executed or
verified against the repo during that review; log/receipt paths are real paths
observed on disk. The automation executes from the **ops checkout**
`/Users/carsynstephenson/options-validator-ops` (branch-guarded to `main`),
not from the development checkout.

## What fires automatically (verified from loaded LaunchAgents)

| Time (ET, Mon–Fri) | Agent | What it does |
|---|---|---|
| 07:10 | `com.carsyn.options-validator.daily-ritual` | Full ritual: topup Friday closes → H7 source health → data gate → exit fill/monitor → h7_watch → entry preflight → h6/h5/h8/h10 watchers → QM OHLCV + feature rebuilds → both dashboards → capture receipt → evidence commit+push |
| 09:31, 09:35, 11:00, 13:00, 15:45 | `com.carsyn.options-validator.intraday-capture` | 15-name board snapshot receipts under `reports/intraday_capture/<date>/`; never commits (Monday's ritual sweeps Friday's receipts) |
| 08:07 Mon only | `com.carsyn.pick-dashboard` | **equity-research repo asset** (`~/equity-research/scripts/run_pick_dashboard.sh`) — not part of this repo's run |

The machine must be awake at 07:10; launchd does not run missed
StartCalendarInterval jobs at their scheduled fidelity on a sleeping laptop.

## Before 07:10 Monday (owner checklist)

1. **Nothing to start for data.** Correction (2026-07-25, late review): the
   active data path authenticates with `THETADATA_API_KEY` from `.env`
   directly against ThetaData's remote MDDS — **no local ThetaTerminal
   process, no port** (`tools/daily_ritual.sh:56-61`,
   `data/thetadata_adapter.py:137-149`; the 127.0.0.1:25503 entry in
   `.env.example` is the legacy path). The ritual preflights the key
   loudly. Friday's midday capture failure (all 15 names gRPC
   `StatusCode.UNAVAILABLE`) was a transient remote/network outage —
   midmorning and preclose the same day were 15/15 ok; such blips
   self-heal on later runs.
2. Machine awake / lid open before 07:10.
3. Internet reachable generally: the QM OHLCV refresh step pulls from
   Yahoo (not ThetaData) — if Yahoo is unreachable, H10 skips DATA for the
   day (fail-visible, recovered next run).
4. Nothing else — no manual data pulls, no code changes needed.

## Expected Monday outcome (evidence-based)

Friday's ritual ended `RITUAL STATUS: BROKEN` (exit 1) on two CRITICALs.
Both causes are fixed in the code the ops checkout now runs (`main` @ 2864008):

- **H7 preflight refusal** — cause was registered name NOW source-unhealthy.
  Under the ratified 45-calendar-day post-report grace (~30 trading
  sessions; merged Friday evening), source health re-run 2026-07-25 shows
  NOW `ok gate=CLEAR [GRACE]` and **all 9 registered entry names healthy**.
  Expect no preflight CRITICAL.
- **H10 "watcher skipped: DATA"** — cause was step ordering (h10_watch ran
  before the QM OHLCV refresh). Current script refreshes OHLCV at
  `tools/daily_ritual.sh:216` before h10_watch at `:311`. Expect clean H10
  reads.

Still expected and NOT a failure:
- `source health: exit 1 — per-name entry bans apply`: 6 non-registered
  names (CRWV, SMCI, NVDA, AVGO, IREN, USAR) have no gating assertions;
  they are entry-banned per-name, the board is not blocked. Optional owner
  fix at leisure: `uv run python tools/h7_refresh_earnings.py --help`.
- MSFT / AMZN / TEM `gate=BANNED`: earnings within the warn window
  (reports 07-29/07-30) — the registered earnings-proximity ban working.

## After the run — verification (all commands verified)

```bash
# 1. Exit codes of the agents (second column; 0 = clean)
launchctl list | grep options-validator

# 2. Ritual log (files are named <date>_<HHMM>.log in this directory)
ls /Users/carsynstephenson/options-validator-ops/.tmp/daily_ritual/
tail -40 "/Users/carsynstephenson/options-validator-ops/.tmp/daily_ritual/2026-07-27_0710.log"
# Look for: "RITUAL STATUS: OK" and the per-step summary block.

# 3. Dashboards (bookmark these two file:// paths)
open /Users/carsynstephenson/options-validator-ops/.tmp/dashboard/attractiveness.html
open /Users/carsynstephenson/options-validator-ops/.tmp/dashboard/index.html
# attractiveness.html header shows "Market close 2026-07-24" after a good run.
# KNOWN QUIRK: index.html's yellow banner is pinned to config.BACKTEST_END
# (2026-06-30) — read the header sub-line and H7 panel for freshness instead.

# 4. Read-only H7 door check (safe any time; writes nothing)
uv run python -m options_researcher.h7_entry_preflight

# 5. Intraday captures appearing through the day
ls /Users/carsynstephenson/options-validator-ops/reports/intraday_capture/2026-07-27/
```

## If the ritual reports CRITICAL

The ritual is fail-closed and honest: a CRITICAL line names the failing step
and the summary block at the log tail lists every step's status. Do not
paper over it — the per-step line tells you which receipt/log to read.
A manual catch-up re-run is an established pattern (a 2026-07-23 11:37
manual run exists in the log directory):

```bash
cd /Users/carsynstephenson/options-validator-ops && /bin/zsh tools/daily_ritual.sh
```

(The script itself enforces branch `main` and re-uses same-day receipts
rather than overwriting; data-gate receipts are immutable by design.)

## Rollback

- Code: `git -C /Users/carsynstephenson/options-validator-ops log --oneline -5`
  then `git revert <sha>` on `main` (never rewrite pushed history), push, and
  re-run the ritual. Dashboards fully regenerate on the next run.
- Data: receipts and the ledger are append-only/immutable; there is nothing
  to roll back there. Chain cache only ever adds missing days.
- Dashboards: HTML writes are atomic as of 2026-07-25 (tmp + `os.replace`);
  a crashed build leaves the previous page intact.

## Open owner decisions (not blocking Monday)

1. Second Friday probe receipt preserved at
   `…-ops/reports/live_probe/2026-07-24T1500Z-preserved.json`. Note: now
   that `reports/live_probe` is in the ritual's evidence allow-list,
   Monday's ritual will auto-commit it — delete it before Monday if you
   don't want it kept (default: it gets preserved as evidence).
2. Earnings-source refresh for the 6 non-registered unhealthy names.
3. Ten leftover `.claude/worktrees/` agent worktrees from Friday's waves —
   safe to prune whenever (`git worktree list` to review).
