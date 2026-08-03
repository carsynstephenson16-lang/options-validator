---
paths:
  - ".cache/**"
  - "data/**"
  - "market_data/**"
  - "options_researcher/live_quotes.py"
  - "options_researcher/intraday_capture.py"
  - "tools/cache_manifest.py"
---

# Data, cache, and provider rules

Canonical provider plan: `docs/provider-transition.md`.

- **v1 cache is immutable.** Never overwrite, migrate in place, or delete
  anything under `.cache/chains/`. A schema v2 lives only in a NEW side-by-side
  namespace; v1 files stay byte-identical and become display-only where v2 exists.
- **No provider endpoint call without owner approval.** Any ThetaData or Schwab
  request costs money, quota, or auth risk. Before proposing one, produce a
  written call-count estimate (precedent:
  `reports/strategy-evaluations/09_session5_refetch_gate.md`, 62,734 calls for
  a full refetch). Tests and backtests run offline against the local cache only.
- **Fail closed on missing data.** If a feature needs historical depth,
  timestamps, Greeks, or provenance the current provider or cache cannot supply,
  the feature STOPS with a clear blocker. Never silently substitute delayed,
  stale, or weaker data. The Schwab adapter's refusal of `isDelayed` chains is
  the model to follow.
- **Schwab is the live-preview lane only.** No Schwab response is written into
  `.cache/chains` or any blind-study cache. Schwab does not provide dated
  historical option chains, point-in-time open interest, or historical Greeks;
  do not design work that assumes it does. `live_quotes --probe` runs in the
  regular session ONLY and is required before the live lane turns on.
- **Provenance travels with data.** Every capture records source, retrieval
  time, and entitlement context. Data with unknown provenance cannot feed a
  gate or verdict.
- **Irreplaceable bytes must never live in one disposable place.** The cache is
  gitignored and acquisition is disabled, so every namespace in
  `data/irreplaceable_data_inventory.json` is unrecoverable if deleted. Run
  `uv run python tools/irreplaceable_data_guard.py verify` BEFORE removing any
  worktree, branch, or directory, and re-run `generate` after an approved
  capture. Incident 2026-08-03: the 1,536-partition future-ticker capture
  (3,072 provider calls, taken before cancellation) existed only inside a git
  worktree under `~/Downloads`; `tools/cache_manifest.py` covers only
  `.cache/chains`, so nothing would have flagged its loss. A worktree is a
  working copy, never a storage location.
