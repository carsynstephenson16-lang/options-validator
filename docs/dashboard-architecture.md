# Dashboard architecture — decision record (2026-07-25 readiness review)

## Current UI (verified by inspection and execution)

Four surfaces, all stdlib-Python, zero web frameworks:

| Surface | Command | Output | Refresh model |
|---|---|---|---|
| Mission control | `uv run python -m options_researcher.dashboard` | `.tmp/dashboard/index.html` (static file) | Rebuilt by the 07:10 ritual; browser refresh re-reads the file |
| Attractiveness / Top-3 | `uv run python -m options_researcher.attractiveness_dashboard` | `.tmp/dashboard/attractiveness.html` (static, ~500 KB) | Same |
| Live preview server | `uv run python -m options_researcher.live_dashboard --serve` | `http://127.0.0.1:8642/` | Manual-only; base page is a startup snapshot, LIVE panel polls `/live.json` every 30 s |
| QM context module | (not a page — data provider for the attractiveness page) | — | Ritual refreshes its OHLCV cache |

Failure behavior (verified): both static builders render the entire page
in memory before writing, so a data failure leaves yesterday's page intact;
per-symbol failures render as explicit `blocked` records instead of taking
the page down; as of 2026-07-25 the final write is atomic (tmp +
`os.replace`). The live server degrades per-symbol to "unavailable" and can
never render FIRE in the preview lane (test-enforced).

## Options compared (against verified repo constraints)

| Option | Assessment |
|---|---|
| **Keep existing architecture + small fixes** | **CHOSEN.** Zero new dependencies, zero new processes to babysit, already wired into the ritual, fail-visible states already built and tested (1,996-test suite covers all surfaces). Monday risk ≈ zero. |
| One-page app (Streamlit/Dash) | Rejected for now: adds a framework dependency and a long-running server to a repo whose tests must stay offline; duplicates two working pages; fails the scope guard ("does this move a live hypothesis toward its verdict?" — no). Parking lot. |
| One app with tabs (FastAPI/React) | Rejected: highest effort, new deployment/secrets surface, no requirement demands interactivity beyond what static pages + the live server already give. Parking lot. |
| Multiple dashboards (status quo formalized) | This is the status quo; the two static pages + optional live server are intentionally separate concerns (recorded state vs. candidate scan vs. intraday preview). |

Framework comparison beyond this was not warranted: the repo constraint
(offline unittest suite, no server dependencies, ritual-driven regeneration,
research-integrity guardrails) eliminates hosted/server-first designs before
framework choice matters.

## Bookmark-and-refresh solution (smallest reliable for Monday)

**Bookmark:** `file:///Users/carsynstephenson/options-validator-ops/.tmp/dashboard/attractiveness.html`

- Browser refresh re-reads the file; after the 07:10 ritual the page shows
  the new session ("Market close <date>" + "Research updated <date>" chips,
  with an explicit stale warning when research context lags).
- A failed build leaves the previous good page in place (whole-render-then-
  atomic-write), so the bookmark never shows a partial page — at worst an
  honest yesterday page whose own dates say so.
- No server required, no login, no secrets in the payload (grep-verified).

Secondary bookmark: `.../.tmp/dashboard/index.html` (mission control).
Known quirk (P1): its yellow "DATA AS-OF" banner is pinned to
`config.BACKTEST_END` (2026-06-30) — see backlog.

Localhost vs hosted, stated plainly: the optional live view
(`http://127.0.0.1:8642/`) only resolves while a manually-started local
process runs; nothing in the automation starts it, by design (the live lane
is gated on a same-day market-hours schema probe). A hosted dashboard would
require deployment, auth, and secrets handling that this research repo
deliberately avoids — rejected without owner request.

## P1 improvements (documented, not done in the readiness window)

1. `dashboard.py::_default_data_as_of` pins the banner date to
   `config.BACKTEST_END` — change to the actual latest cached close
   (entry_watch already reads closes-to-today with `allow_oos=True`,
   so precedent exists) or relabel the banner. One-line fix + test pin
   review; touches OOS-seal-adjacent code, so it gets its own reviewed
   change, not a Saturday-night edit.
2. `ideas-parking-lot.md` holds the richer dashboard ideas; nothing here
   unparks them.
