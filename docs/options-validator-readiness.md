# Options-validator readiness report — Monday 2026-07-27 run

Written 2026-07-25 by the readiness review session (lead reviewer + three
scoped inventory agents + one fresh-context final reviewer). Every claim
below is labeled; "Verified" means executed or read in this repo during the
review. Companion docs: `docs/monday-runbook.md`,
`docs/dashboard-architecture.md`.

## Verdict

**READY WITH KNOWN LIMITATIONS** — the scheduled Monday 07:10 ritual is
expected to run clean on current `main` (2864008), with two owner-side
dependencies (machine awake, ThetaData terminal running) and the known
limitations listed at the end.

## Verified project scope (one paragraph)

Research-only validator for four core AI-infrastructure names plus the H7
15-name watchlist; it never places orders (hook-enforced). Live registered
forward-paper hypotheses: H5 (income core), H6 (post-earnings long calls),
H7 (15-name swing board, forward window LIVE since 2026-07-20, scores
~2026-10-26), H8 (pre-earnings long calls), H10a/b (QM breakout/parabolic
recorders). H9 and RQ1 are spent one-run studies. "No edge after costs" is a
successful outcome. Sources: `README.md`, `CLAUDE.md`, `.cursorrules`,
`ledger/`, registered specs under `docs/superpowers/`.

## Baseline status (Verified by execution this session)

- Full suite on `main`@2864008: **1,996 tests, OK, exit 0** (`unittest`,
  offline). Ruff: clean. Pyright: 0 errors. Pre-commit: pass.
- GitHub CI on the same commit: **success** (ruff, pyright, unittest,
  gitleaks).
- `main` == `origin/main` == ops checkout (`~/options-validator-ops`).

## Current system map (condensed; Verified)

- **Data**: ThetaData terminal → `data/thetadata_adapter.py` → per-day
  parquet chain cache (`.cache/chains/`, shared by symlink with the ops
  checkout); `data/recent_topup.py` adds only missing XNYS trading days.
- **Automation**: two repo LaunchAgents (07:10 ritual; 5×/day intraday
  capture), both executing `tools/*.sh` from the ops checkout, branch-guarded
  to `main`; ritual commits an evidence allow-list and pushes to
  `origin/main`. (`com.carsyn.pick-dashboard` at Mon 08:07 belongs to
  equity-research, not this repo.)
- **Watchers/validators**: full inventory with entry points, hypothesis
  mapping, receipts, and test files captured in this review; every module
  has test coverage. Highlights: H7 operator chain (source health → data
  gate → exit fill/monitor → watcher → preflight) is fail-closed with
  immutable receipts; H5 entry_watch is the only surface allowed to FIRE;
  verdict layer (`metrics.py::scoreboard`) gates on losses
  (`MIN_LOSSES_FOR_VERDICT=10`; H10 uses its own 7).
- **Surfaces**: two ritual-rebuilt static HTML pages + one manual localhost
  live-preview server (see `docs/dashboard-architecture.md`).
- **Persistence**: ledger append-only with flock+fsync; gate receipts
  atomic (tmp+`os.replace`) and immutable; captures/receipts are dated
  add-only files; dashboard HTML atomic as of this review; chain cache
  add-only.
- **Secrets**: `.env` (gitignored) only; grep of rendered HTML, reports,
  and logs found no secret-shaped strings; CI runs gitleaks.

## The attractiveness system, explained

**Plain English (owner-facing).** Every morning the scanner looks at each
name on the board and asks: if you sold a put today (a promise to buy the
stock at a lower price, and you're paid up front for making that promise),
or sold a covered call against shares you own, or bought a LEAPS (a very
long-dated call option), how does today's pricing look? Each candidate
contract gets simple GREEN/AMBER/RED badges on frozen yardsticks: how much
income per unit of capital, how much cushion before the promise starts
losing, whether the contract trades enough to get out at a fair price
(liquidity), and whether options are expensive or cheap versus their own
past year (IV rank — implied volatility rank). A Top-3 strip picks the
day's best-graded candidates. It is a describing tool, not a predicting
tool: nothing in it forecasts, and nothing in it places orders. Since
2026-07-25 each card also carries a neutral line showing how the contract's
open interest (the count of contracts outstanding) changed since the prior
session — context only, never a grade.

**Technical.** Card builders per role
(`options_researcher/attractiveness.py:142-401`) select contracts by delta
distance from frozen targets (`H5_INCOME_DELTA=0.20` etc.), grade via
`grade()` (:26) against frozen `H5_*` config thresholds, rank inside
`ladder_cards` (:69) / `rank_cards` (:50) on `annualized_yield` (sell
lanes) or `breakeven_move` (long lanes). The dashboard's Top-3
(`attractiveness_dashboard.py::select_top_picks` :330) draws from an
admissibility pool (liquidity-RED hard veto, policy/snapshot eligibility)
with display-only weights. Earnings-cycle badges come from the v3
point-in-time store; missing data renders explicit `blocked` records or
UNKNOWN badges, never silent fills. OI-change line: computed post-ranking
(`oi_change.py`), board-invariance test-pinned. Tests:
`test_attractiveness*.py`, `test_oi_change_line.py`, and the dashboard
suites. Unverified by design: any claim that grades predict returns (RQ1's
one-run descriptive study explicitly returned "NO VERDICT").

## Monday-run analysis (the heart of this review)

Friday 07:10's ritual ended `RITUAL STATUS: BROKEN` (exit 1). Root causes,
both **Verified** from logs/receipts and both **cured in the code Monday
runs** (Friday-evening integration wave + this weekend's merges):

1. H7 preflight refused: registered name NOW was source-unhealthy.
   Post-grace re-run (2026-07-25): NOW `ok gate=CLEAR [GRACE]`; all 9
   registered entry names healthy.
2. H10 skipped all names on DATA: old step order ran `h10_watch` before the
   QM OHLCV refresh; current script refreshes first
   (`tools/daily_ritual.sh:216` vs `:311`).

Expected Monday summary therefore: topup OK → source health exit 1 (6
non-registered names unhealthy — by-design per-name bans, not a failure) →
gate GO → watchers clean → dashboards rebuilt → receipt written → evidence
pushed → `RITUAL STATUS: OK`.

## Work completed in this review

- P0: atomic HTML writes for both dashboards (gate: partial writes);
  `reports/live_probe` added to the ritual's evidence allow-list (probe
  receipts were never auto-committed); `.env.example` now documents the
  restic keys the ritual reads. All verified by tests/lint/smoke.
- Docs: this report, `docs/monday-runbook.md`,
  `docs/dashboard-architecture.md`.
- Earlier same review-session (already merged + CI green): OI-change line
  v1 (owner-ratified), `.research/` decision workflow artifacts.

## Backlog

**P0 (none remaining).**

**P1:** mission-control banner date pinned to `config.BACKTEST_END`
(2026-06-30) — misleading freshness cue on `index.html`
(`dashboard.py::_default_data_as_of`; fix spec in
`docs/dashboard-architecture.md`); stale "TEMPLATE ONLY" comment inside the
deployed intraday-capture plist; earnings-source refresh for CRWV, SMCI,
NVDA, AVGO, IREN, USAR (`tools/h7_refresh_earnings.py`, owner-run).

**Parking lot:** ten stale `.claude/worktrees/` from Friday's waves;
dashboard framework upgrades (rejected under the scope guard); OI-change v2
percentile/NOTABLE (gated on its pre-registered calibration study);
`reports/attractiveness_context` refresh cadence (manual research artifact,
currently 2026-07-15, dashboard already warns when stale).

## Risks and limitations

1. **Machine asleep at 07:10** → launchd misses the window; recovery is the
   documented manual re-run.
2. **ThetaData remote outage** → topup/captures fail with gRPC UNAVAILABLE
   (observed Friday midday, recovered same day); fail-soft/fail-visible.
   Correction 2026-07-25: the active adapter path is keyed HTTP against
   the remote MDDS — no local terminal process is required
   (`daily_ritual.sh:56-61`). Subscription confirmed through 2026-11-30
   (ledger fact THETADATA_RENEWAL_EXECUTED).
3. **H7 earnings bans around 07-29/07-30**: MSFT/AMZN/TEM are gate=BANNED
   (earnings proximity) — correct registered behavior, expect fewer
   entry-eligible names next week.
4. Monday's clean-run expectation is inference from verified fixes, not a
   completed Monday run; the first true proof is Monday's log.
5. `index.html` banner quirk (P1 above) can mislead a glance at freshness.

## Final verdict

**READY WITH KNOWN LIMITATIONS** — all release gates that can be satisfied
before the run itself are satisfied and evidenced; the remaining gates
(actual scheduled end-to-end completion) are structurally expected to pass
and will be proven by Monday's own receipts.
