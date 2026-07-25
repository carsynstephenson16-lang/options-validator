# Dashboards

Derived summary of `docs/dashboard-architecture.md` (2026-07-25 decision
record) — read that file for the full comparison table. See [[automation]]
for what rebuilds these, [[hypotheses]] for what data feeds each card.

## The four surfaces

| Surface | Command | Output | Refresh |
|---|---|---|---|
| Mission control | `python -m options_researcher.dashboard` | `.tmp/dashboard/index.html` | Rebuilt by the 07:10 ritual |
| Attractiveness / Top-3 | `python -m options_researcher.attractiveness_dashboard` | `.tmp/dashboard/attractiveness.html` (~500 KB) | Same |
| Live preview server | `python -m options_researcher.live_dashboard --serve` | `http://127.0.0.1:8642/` | Manual-only; base page is a snapshot, its LIVE panel polls `/live.json` every 30s |
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
— refresh re-reads the file after each 07:10 ritual run; shows "Market
close <date>" / "Research updated <date>" chips, with an explicit stale
warning when research context lags behind the chain data.

Secondary bookmark: the same directory's `index.html` (mission control).
**Known quirk (P1, not yet fixed):** its yellow "DATA AS-OF" banner is
pinned to `config.BACKTEST_END` (2026-06-30) rather than the actual latest
close — read the header sub-line and the H7 panel for real freshness
instead (`dashboard.py::_default_data_as_of`).

The live-preview server only resolves while manually started; nothing in
the automation starts it (the live lane is itself gated on a same-day
market-hours schema probe, `options_researcher.live_quotes --probe`), and it
can never render a FIRE signal in the preview lane — that stays owned by
`entry_watch` on completed-session closes (test-enforced).

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
