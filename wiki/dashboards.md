# Dashboards

Derived summary of `docs/dashboard-architecture.md` (2026-07-25 decision
record) — read that file for the full comparison table. See [[automation]]
for what rebuilds these, [[hypotheses]] for what data feeds each card.

## The four surfaces

| Surface | Command | Output | Refresh |
|---|---|---|---|
| Mission control | `python -m options_researcher.dashboard` | `.tmp/dashboard/index.html` | Rebuilt by the 09:09 ritual |
| Attractiveness / Top-3 | `python -m options_researcher.attractiveness_dashboard` | `.tmp/dashboard/attractiveness.html` (~500 KB) | Same. Layout redesigned 2026-09-07 (Brief 39, PR #159): lane-board / agreement table, `BOARD_LANES_ENABLED=True` by default (`config.py:941`); output path and bookmark unchanged |
| Live preview server | `python -m options_researcher.live_dashboard --serve` | `http://127.0.0.1:8642/` | Kept running by LaunchAgent `com.carsyn.options-validator.live-dashboard` (owner-installed, `KeepAlive`, healthy since 2026-08-26 — its `-15` last-exit in `launchctl list` is stale bookkeeping); base page is a snapshot, its LIVE panel polls `/live.json` every 30s |
| QM context module | (data provider, not a page) | — | Ritual refreshes its OHLCV cache |

All four are stdlib Python, zero web frameworks, zero new processes for the
static pages. As of 2026-07-25 both static builders write atomically
(temp file + `os.replace`) after rendering the whole page in memory, so a
failed build leaves the prior good page intact rather than a partial one;
per-symbol data failures render as explicit `blocked` records, never take
the page down.

## Bookmark story

Primary bookmark:
`file:///Users/carsynstephenson/options-validator-ops/.tmp/dashboard/attractiveness.html`
— refresh re-reads the file after each 09:09 ritual run; shows "Market
close <date>" / "Research updated <date>" chips, with an explicit stale
warning when research context lags behind the chain data.

Secondary bookmark: the same directory's `index.html` (mission control).
**Fixed 2026-09-04 (Brief 37 WP-A, PR #156):** its yellow "DATA AS-OF"
banner now shows the earliest last-cached-close date across
`config.UNIVERSE` (`dashboard.py:123-144`, `_default_data_as_of`). Before
that fix it was pinned to `config.BACKTEST_END` (2026-06-30) regardless of
real freshness — historical quirk, no longer live.

The live-preview server is kept up by its own LaunchAgent on the ops
checkout (install is an explicit owner step, not part of the 09:09
ritual); the live lane is still gated on a same-day market-hours schema
probe (`options_researcher.live_quotes --probe`), and it can never render
a FIRE signal in the preview lane — that stays owned by `entry_watch` on
completed-session closes (test-enforced).

## Why this architecture (decision record)

`docs/dashboard-architecture.md` compares four options and **keeps the
current static-pages-plus-ritual architecture**: zero new dependencies,
already wired into automation, fail-visible states already test-covered.
A one-page app (Streamlit/Dash) and a full tabbed app (FastAPI/React) were
both rejected — they'd add a framework/server dependency and a
deployment/secrets surface this offline-tested research repo deliberately
avoids, and neither moves a live hypothesis toward its verdict (the scope
guard in [[decisions]]). Richer dashboard ideas beyond this stay in
`ideas-parking-lot.md`.
