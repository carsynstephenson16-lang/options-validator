# Reproducible Foundation — Design Spec

**Date:** 2026-07-01
**Scope:** Close the remaining gaps so the options-validator harness is
reproducibly runnable and under version control, and set the strategy
configuration to the one honest, cost-aware setup the eventual backtest should
judge. Phase 0 only — no live data, no strategy logic.

## Context

An audit found the project was not reproducibly runnable and lacked version
control. A prior agent (Codex) then landed most of the fix, verified here:

- `uv` + `pyproject.toml` + `uv.lock`, Python pinned to **3.12**
  (`requires-python = ">=3.12,<3.13"`, `.venv` is 3.12.13).
- `.gitignore` covering `.DS_Store`, `__pycache__/`, `.venv/`, `.cache/`,
  `.env`, `results/*`.
- `metrics.py` hardened: `_validated_arrays` now raises `ValueError` on a
  missing, non-finite, or `<= 0` `capital_at_risk` (the audit's silent
  zero-return finding).
- `AGENTS.md` scope narrowed to the options harness (Kalshi/weather-bot
  language removed from the role description).
- `README.md` Quickstart switched to `uv sync` / `uv run`.
- `tests/test_core.py` added — 7 tests, all passing via `unittest`.

This spec covers only what remains.

## Goal

Make the harness reproducibly runnable end-to-end and version-controlled, with
a single dependency source of truth and a documented test command. Do **not**
touch the Phase-0 stubs (ThetaData fetch, Lumibot strategy calls, backtest
wrapper, smoke test).

## Changes

### 1. Delete `requirements.txt`
`pyproject.toml` + `uv.lock` are canonical. `requirements.txt` is now a stale
hand-maintained second source of truth (still lists `numpy>=1.26`,
`pandas>=2.0`, commented Lumibot/ThetaData) and invites drift.

- Grep live project files for any reference to `requirements.txt` before
  deleting; remove lingering mentions (README already dropped `pip install`).
  Exclude `docs/` from this grep — the spec/design docs legitimately name the
  file when describing its removal, so a repo-wide grep would contradict itself.
- Delete the file.

### 2. Document the test command in `README.md`
Tests exist and pass but are undocumented, and `pytest` is intentionally not a
dependency. Keep stdlib `unittest`.

- Add to Quickstart:
  ```bash
  uv run python -m unittest discover -s tests
  ```
- Add a "Tests" row to the Status table (`tests/test_core.py` | passing).

### 3. Initialize git + first commit
Version control is the load-bearing piece of "reproducibility" and is missing
(`git status` → `fatal: not a git repository`).

Ordering matters — the ignored-status check must run **while `.DS_Store` still
exists**, otherwise it can't confirm the file is ignored rather than merely
gone (see change #4):

- `git init`.
- Verify `.gitignore` works by inspecting `git status --porcelain --ignored`
  before staging: `.venv/`, `.cache/`, `__pycache__/`, `.DS_Store` must appear
  as **ignored** (`!!`), not merely absent.
- Do the trivia cleanup in change #4 now (after the ignored-status check).
- Stage source, config, tests, and docs (including this spec).
- Make the initial commit. Commit message ends with the required
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` trailer.
- Confirm `git status --porcelain --ignored` shows a clean tree with no ignored
  artifacts staged or tracked.

### 4. Trivia cleanup (bundled, low-risk)
Runs **after** the ignored-status sanity check in change #3, not before.
- Remove the leftover "weather forecasts" phrase at `AGENTS.md:83` so scope is
  fully options-only.
- `rm` the on-disk `.DS_Store` (already gitignored; keeps the tree clean).

### 5. Set the strategy configuration to the honest, cost-aware setup
Decided with the account owner, this sets *which* configuration the Phase-1
backtest will ultimately judge. It is a config-value change only — no strategy
logic, no live data.

Real risk-capital picture (owner-provided): $50k invested portfolio and up to
$40k Schwab margin are **excluded** — the portfolio must not sit behind option
trades ([config.py:16-19](../../../config.py#L16-L19)), and borrowed margin is
not "willing-to-lose" money. The genuine options sleeve is ~$14k ($4k cash +
~$10k active swing capital). An earlier "$58k sleeve for $5-wide" idea was
rejected as reverse-engineering the sleeve to fit the trade — the exact mistake
[feasibility.py:71](../../../analysis/feasibility.py#L71) warns against.

At a ~$14k sleeve with 1% risk ($140/trade), using the code's assumed 30%-of-
width credit: $5-wide (~$350 max loss) does **not** fit; $2-wide (~$140 max
loss) fits at 1 contract; $1-wide fits but is the most cost-punished. Verdict
sample size comes from 7 years × 5 names of history, not sleeve size, so
1 contract per trade is sufficient to reach `MIN_LOSSES_FOR_VERDICT`.

**$2-wide is a threshold fit, not a robust one.** The feasibility formula sizes
on *gross* max loss `(width − credit) × 100` only — it excludes the ~$2.60
round-trip commission and assumes the 30%-of-width credit holds. At $14k the
budget is exactly $140 and gross max loss is exactly $140: **zero slack.** A
thinner real credit or the commission drag pushes true all-in risk over budget.
So $2-wide is the best *candidate* to test, but it is a knife-edge fit under the
current simplified formula — not confirmed until real quote data measures the
conservative credit. The live data path must still **skip any trade whose actual
conservative credit does not fit the budget**, exactly as
[put_credit_spread.py:72-77](../../../strategies/put_credit_spread.py#L72-L77)
already does (`contracts < 1` → log and skip, never round up). Tightening the
feasibility formula to include commissions is a candidate Phase-1 follow-up, not
part of this spec.

Changes to `config.py`:
- `RISK_SLEEVE`: `8_000` → `14_000`.
- `A_SPREAD_WIDTH`: `5` → `2`.
- Update the surrounding comments to record this reasoning (honest sleeve, why
  $58k/margin/portfolio were excluded, why $2-wide) so the assumption lives next
  to the code that depends on it.
- Add `14_000` to `RISK_SLEEVE_CANDIDATES` (→ `[8_000, 14_000, 25_000,
  58_000]`) so the feasibility table actually displays the chosen honest
  sleeve. `feasibility.py` reads `RISK_SLEEVE_CANDIDATES`, not `RISK_SLEEVE`,
  so without this the $14k row would not appear.
- Leave `A_SPREAD_WIDTH_SWEEP` as-is: the sweep should still show the full
  trade-off, including that $5-wide does not fit — that visibility is the point.

The honest finding "$5-wide does not fit my real capital" is a valid, expected
outcome, not a failure to fix.

## Verification (evidence before claiming done)

- `uv sync --locked --check` → `Would make no changes` (lockfile current,
  environment reproducible; does not mutate).
- `uv run python analysis/feasibility.py` runs and, at the new $14k candidate
  sleeve, shows $2-wide fitting (1 contract, threshold) and $5-wide not fitting.
- `uv run python metrics.py` runs and prints the scoreboard demo.
- `uv run python -m unittest discover -s tests` → 7/7 pass.
- Grep of live project files (excluding `docs/`) returns no remaining
  `requirements.txt` reference; the file is gone.
- `git log --oneline` shows the initial commit.
- `git status --porcelain --ignored` confirms `.venv/`, `.cache/`,
  `__pycache__/` are ignored and none are staged/tracked; `.DS_Store` was
  observed as ignored (`!!`) before removal and no longer present after.

## Out of scope (stays Phase 0)

Note: config *values* (sleeve, width, candidates) are in scope per change #5;
strategy *logic* and *live data* are not.


- Wiring the ThetaData EOD chain fetch (`data/thetadata_adapter.py`
  `get_eod_chain` keeps raising `NotImplementedError`).
- Lumibot strategy calls (`strategies/put_credit_spread.py`).
- Backtest wrapper (`harness/run_backtest.py`).
- `smoke_test.py` passing — it correctly stays blocked on ThetaData.
