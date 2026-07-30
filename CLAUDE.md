# options-validator — Claude Code instructions

Research platform anchored to four AI-infrastructure core names (VST, CEG,
MSFT, AMZN), plus the owner-authorized H7 story-name watchlist. **Research
only — this is NOT a live bot and places no orders.**
A "no edge after costs" finding is a success, not a failure to fix. Mission,
current status, and the phase roadmap live in `README.md`. **Scope loosened
2026-07-22 (owner-directed):** the blanket "no scanner/suggestor/optimizer
unless on the phase plan" restriction is retired; the binding limit is now
`.cursorrules`' Scope guard test — "does this move a live hypothesis toward
its verdict?" — plus the absolute rule that this is never a live-order bot.

## Non-negotiable research guardrails

@.cursorrules

The import above is the authoritative wording.

`AGENTS.md` is the Codex-facing twin of these rules. When a guardrail
changes, update `.cursorrules` and `AGENTS.md` together so they don't drift.

## Division of labor (owner directive 2026-07-22)

Claude Code sessions ORCHESTRATE: research, specs, Codex briefs, review,
verification, and owner decision packages. Codex implements code from the
briefs. The owner types every frozen number and new registration.
*Amended 2026-07-25 (owner-directed):* **amendments to already-registered
specs are no longer an owner act** — the implementing agent may draft and
record them (ledger fact + spec doc) once the amendment text has passed an
independent adversarial review and Fable's sign-off, and every recorded
amendment carries the provenance label "owner-delegated standing
2026-07-25". New hypothesis registrations, frozen numbers, and verdict
ratifications remain owner-typed. The owner retains veto: a vetoed
amendment is corrected by a further append-only amendment, never by
rewriting.
Delegate heavy reading and routine lifting to subagents (Sonnet for research
and scouting, Opus for adversarial review); reserve the main session for
judgment, synthesis, and integrity checks. Claude writes code directly only
for docs, briefs, and trivial mechanical fixes — not strategy or ledger code.

## Commands (verified 2026-07-06; suite now runs minutes, not ~6 s)

```bash
uv sync --frozen                                 # Python 3.12; uv.lock is source of truth
uv run python -m unittest discover -s tests      # full suite (offline); exit code is the verdict
uv run python tools/score_backtest.py --symbols MSFT,AMZN --json
uv run python options_researcher/profile_tradability.py
uv run python analysis/feasibility.py
uv run python -m options_researcher.attractiveness
uv run python -m options_researcher.entry_watch  # WAIT/FIRE vs frozen entry triggers
uv run python -m options_researcher.h7_watch  # session-aligned H7 watcher; alerts only
uv run python -m options_researcher.h7_source_health  # earnings provenance health; exit 1 = refresh needed
uv run python -m options_researcher.h7_data_gate --source-health-receipt <path>  # Stage 2 whole-universe data gate (read-only, BUILD-ONLY); --source-health-receipt is REQUIRED (a receipt written without it is immutable and permanently revokes that session's real-entry authority); operator order (amendment v1.4, 2026-07-14): run+record source health -> data gate must be exit 0 -> watcher; source-unhealthy names are entry-banned per-name by the watcher's fail-closed gate (they no longer block the whole board); a data-gate NO_GO still blocks the run
uv run python -m options_researcher.h7_entry_preflight  # read-only daily proof the real entry path would open (exit 1 = it would refuse); writes nothing
uv run python -m options_researcher.h7_event_ledger verify  # Stage 3 forward-event ledger verifier (BUILD-ONLY, INACTIVE); NEVER hand-edit ledger/h7_forward/{events.jsonl,HEAD} -- append only via the typed Python API; a hand edit breaks the hash chain and verify refuses
uv run python tools/h7_refresh_earnings.py --help  # owner-run append-raw/promote refresher
uv run python -m options_researcher.portfolio    # mark the H5 paper book
uv run python -m options_researcher.dashboard    # writes .tmp/dashboard/index.html
uv run python -m options_researcher.live_dashboard --serve  # 127.0.0.1 live-preview server (two lanes: OFFICIAL H5 vs LIVE PREVIEW; FIRE stays with entry_watch)
uv run python -m options_researcher.live_quotes --probe  # one-shot live schema probe (regular session ONLY; required before the live lane turns on)
uv run python -m options_researcher.attractiveness_dashboard  # writes .tmp/dashboard/attractiveness.html
uv run python -m tools.research_context_assemble --verify  # research-context freshness check; tools/research_refresh.sh runs the scheduled LLM refresh (kill-switch: .research-refresh-off)
uv run python -m options_researcher.robustness --help  # registered research-only walk-forward/null/stability experiments
```

Tests are `unittest` (not pytest) and must stay runnable offline against the
local parquet cache — no network, no paid API calls. Anything that would hit
the ThetaData terminal or subscription needs owner sign-off first.

## Layout

- `ledger/` — append-only research ledger (`facts.log`, trials). Never rewrite or delete entries.
- `data/` — parquet chain cache; `data/positions/positions.csv` and `data/positions/holdings.csv` drive the paper book.
- `reports/`, `docs/superpowers/` — dated findings, frozen specs, and pre-registrations.

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
- **Registration feasibility gate (2026-07-24):** before registering any
  loss-gated hypothesis or forward window, compute the historical base rate
  of the full entry stack and project expected entries over the window;
  refuse registration unless expected entries ≥ 2× the loss bar, or the
  registration explicitly pre-accepts the starvation risk with the computed
  number quoted (H10 precedent). See
  `docs/superpowers/2026-07-24-registration-feasibility-gate.md`.

## Optional public-web research fetchers

`.cursorrules` (imported above) carries the binding rules: manual research
utilities only, never from tests or a trigger path, never to bypass source
terms, and they cannot change a hypothesis verdict.

For *which* fetcher to reach for once a URL is known — including the measured
SEC EDGAR 403 gotcha and the Crawl4AI content-loss trap — use the
`web-fetch-order` skill.

## Conventions and pitfalls

- Verify Lumibot/ThetaData call signatures against the installed packages;
  do not trust remembered APIs. If a capability is missing, stop and report.
- `.claude/` is intentionally gitignored (local-only settings); this file is
  the tracked Claude entry point.
- Root-level dated notes (`/2026-*.md`, `Untitled*.md`) are gitignored
  Obsidian scratch — never commit them.
- Secrets live in `.env` (gitignored; `.env.example` is the template).

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

## Project boundary (always on)

This repo is a validator. It never places orders, never connects to a live
brokerage endpoint, never disables paper mode. A hook enforces this; do not
attempt to work around the hook, and treat a hook block as correct by default.

## Scope guard (always on)

`.cursorrules` (imported above) carries the scope-guard test verbatim. The one
thing it does not say: parked ideas are not rejected ideas; they're just not now.
