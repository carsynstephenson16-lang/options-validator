# options-validator — Claude Code instructions

Research platform anchored to four AI-infrastructure core names (VST, CEG,
MSFT, AMZN), plus the owner-authorized H7 story-name watchlist. **Research
only — this is NOT a live bot and places no orders.**
A "no edge after costs" finding is a success, not a failure to fix. Mission,
current status, and the phase roadmap live in `README.md`; treat the README
roadmap as the scope gate — no scanner, suggestor, or optimizer beyond it.

## Non-negotiable research guardrails

@.cursorrules

The import above is the authoritative wording. Headlines: no look-ahead;
fills at quote mid or worse plus slippage haircut; commissions plus
half-spread on both legs; liquidity gates on both legs; verdicts gate on
LOSSES (not trades or win rate); every strategy number comes from
`config.py`; skip-and-log data gaps instead of papering over them.

`AGENTS.md` is the Codex-facing twin of these rules. When a guardrail
changes, update `.cursorrules` and `AGENTS.md` together so they don't drift.

## Commands (verified 2026-07-06)

```bash
uv sync --frozen                                 # Python 3.12; uv.lock is source of truth
uv run python -m unittest discover -s tests      # full suite (~6 s, offline); exit code is the verdict
uv run ruff check .                              # lint (CI-enforced)
uv run pyright                                   # types; only pyrightconfig.json "include" paths
uv run pre-commit run --all-files                # ruff --fix, pyright, hygiene hooks
uv run python tools/score_backtest.py --symbols MSFT,AMZN --json
uv run python options_researcher/profile_tradability.py
uv run python analysis/feasibility.py
uv run python -m options_researcher.attractiveness
uv run python -m options_researcher.entry_watch  # WAIT/FIRE vs frozen entry triggers
uv run python -m options_researcher.h7_watch  # session-aligned H7 watcher; alerts only
uv run python -m options_researcher.h7_source_health  # earnings provenance health; exit 1 = refresh needed
uv run python -m options_researcher.h7_data_gate  # Stage 2 whole-universe data gate (read-only, BUILD-ONLY); operator order (amendment v1.4, 2026-07-14): run+record source health -> data gate must be exit 0 -> watcher; source-unhealthy names are entry-banned per-name by the watcher's fail-closed gate (they no longer block the whole board); a data-gate NO_GO still blocks the run
uv run python -m options_researcher.h7_event_ledger verify  # Stage 3 forward-event ledger verifier (BUILD-ONLY, INACTIVE); NEVER hand-edit ledger/h7_forward/{events.jsonl,HEAD} -- append only via the typed Python API; a hand edit breaks the hash chain and verify refuses
uv run python tools/h7_refresh_earnings.py --help  # owner-run append-raw/promote refresher
uv run python -m options_researcher.portfolio    # mark the H5 paper book
uv run python -m options_researcher.dashboard    # writes .tmp/dashboard/index.html
uv run python -m options_researcher.attractiveness_dashboard  # writes .tmp/dashboard/attractiveness.html
```

Tests are `unittest` (not pytest) and must stay runnable offline against the
local parquet cache — no network, no paid API calls. Anything that would hit
the ThetaData terminal or subscription needs owner sign-off first.

## Layout

- `config.py` — every strategy/risk number (UNIVERSE, sleeve, gates). No magic numbers elsewhere.
- `options_researcher/` — research layer: profiling, studies, attractiveness, portfolio, dashboard.
- `harness/`, `strategies/`, `tools/` — offline Lumibot backtest path and scoreboard CLI.
- `analysis/`, `metrics.py` — feasibility and shared metrics.
- `ledger/` — append-only research ledger (`facts.log`, trials). Never rewrite or delete entries.
- `data/` — parquet chain cache; `data/positions/positions.csv` and `data/positions/holdings.csv` drive the paper book.
- `reports/`, `docs/superpowers/` — dated findings, frozen specs, and pre-registrations.
- `tests/` — unittest suite. `.tmp/`, `results/`, `.cache/` are disposable and gitignored.

## Research integrity

- Hypotheses are **pre-registered in the ledger before results exist**:
  parameters frozen first, run once, result recorded whatever it shows.
- The legacy holdout is sealed (OOS reveal budget 0/3 spent). Never read past
  `IN_SAMPLE_END` without the reveal gate.
- 2023+ is not a credible blind holdout for these four names (they were
  picked knowing the AI boom); new hypotheses pre-declare their own
  validation design, e.g. a forward paper-trading window.
- Live hypothesis: H5 Sector Income Core (ledger trial 6), passive forward
  window — see README "Scope status".

## Conventions and pitfalls

- Ruff: double quotes, 100 cols, py312, rules E4/E7/E9/F/I (`pyproject.toml`).
- Verify Lumibot/ThetaData call signatures against the installed packages;
  do not trust remembered APIs. If a capability is missing, stop and report.
- ThetaData EOD marks can be missing even when intraday quotes exist — skip
  the day and log it rather than substituting an intraday snapshot.
- `.claude/` is intentionally gitignored (local-only settings); this file is
  the tracked Claude entry point.
- Root-level dated notes (`/2026-*.md`, `Untitled*.md`) are gitignored
  Obsidian scratch — never commit them.
- Secrets live in `.env` (gitignored; `.env.example` is the template).
- CI (`.github/workflows/ci.yml`) runs ruff, pyright, unittest, and gitleaks
  on PRs and on pushes to `main` and `phase-1a-research-integrity`.

## Obsidian LLM Wiki

This repo is an Obsidian vault. The maintained wiki layer is `wiki/`, with
immutable raw source material under `wiki/raw/`. Read `wiki/index.md` before
wiki-oriented work, and append every ingest, filed query result, or lint pass
to `wiki/log.md`.

The wiki is derived operator memory, not the source of truth. For strategy
verdicts, market data, configuration, and reproducibility, defer to `ledger/`,
`data/`, `reports/`, `docs/superpowers/`, tests, and committed source files.
If the wiki conflicts with canonical evidence, correct the wiki.

## Claim discipline (always on)

Every important factual claim about options mechanics, broker behavior,
margin, assignment, fees, or data gets one of these labels:

- **Repo-verified** — I read it in this repo's code/tests
- **Test-verified** — a test in this repo proves it
- **Official-source** — OCC, Cboe, FINRA, SEC, exchange, or broker documentation (link it)
- **Inference** — I reasoned to it; here's the reasoning
- **Assumption** — unverified; treat as possibly wrong

Never cite blogs, Reddit, YouTube, or forums for assignment, margin, fills, or
fees when an official source exists. If sources conflict, say so instead of
picking one silently.

## Vocabulary discipline (always on)

Banned words about backtest results: "proven," "confirmed," "edge found,"
"works," "guaranteed."

Allowed: "survived this test," "not yet rejected," "rejected," "consistent
with zero edge."

## Project boundary (always on)

This repo is a validator. It never places orders, never connects to a live
brokerage endpoint, never disables paper mode. A hook enforces this; do not
attempt to work around the hook, and treat a hook block as correct by default.

## Scope guard (always on)

The live scope gate is README.md "Scope status": H5, H6, H7, and H8 are registered
forward-paper hypotheses; H7's dependency-ordered roadmap is the active build
arc, with its historical diagnostic permanently retired. Before adding any new
capability, ticker, strategy, or tool, answer in one sentence: "Does this move
one of the live hypotheses toward its declared verdict?" If no, write the idea
into `ideas-parking-lot.md` and continue. Parked ideas are not rejected ideas;
they're just not now.
