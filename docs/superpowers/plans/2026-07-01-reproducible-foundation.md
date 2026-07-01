# Reproducible Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the options-validator harness reproducibly runnable and under version control, with a single dependency source of truth, a documented test command, and the strategy configured to the one capital-honest setup ($14k sleeve, $2-wide) the eventual backtest should judge.

**Architecture:** Small, deterministic changes to config/docs plus repo bootstrapping. No strategy logic, no live data, no new runtime dependencies. All changes land in a single initial git commit because the repo is not yet under version control and the spec calls for one clean initial commit. Verification is via the existing `unittest` suite, the feasibility script's output, and `uv`'s lockfile check.

**Tech Stack:** Python 3.12, `uv` (pyproject + uv.lock), stdlib `unittest`, git.

---

## Context an implementing engineer needs

- **Run everything through `uv`.** The interpreter lives in `.venv` (Python 3.12.13). Use `uv run python ...`, not a bare `python`.
- **Tests are stdlib `unittest`, not pytest.** pytest is intentionally not a dependency. Run them with `uv run python -m unittest discover -s tests`.
- **`feasibility.py` reads `config.RISK_SLEEVE_CANDIDATES`** (a list), not `config.RISK_SLEEVE`. Its pure helpers `max_loss_per_spread(width, credit)` and `contracts_that_fit(risk_budget, max_loss)` are importable and side-effect-free.
- **The 30%-of-width credit is an assumption** (`ASSUMED_CREDIT_FRAC = 0.30` in `analysis/feasibility.py`). Every fit/no-fit conclusion is contingent on it until real ThetaData quotes replace it (Phase 1). The $2-wide fit is a **zero-slack threshold**, not robust.
- **Spec:** `docs/superpowers/specs/2026-07-01-reproducible-foundation-design.md`.

## File map

- Modify: `.gitignore` — add `.claude/` (local agent config/permissions must not be committed).
- Modify: `config.py` — `RISK_SLEEVE` 8_000→14_000, `A_SPREAD_WIDTH` 5→2, add 14_000 to `RISK_SLEEVE_CANDIDATES`, record reasoning in comments.
- Modify: `tests/test_core.py` — add a guard test locking the honest-config fit pattern.
- Modify: `README.md` — add the test command to Quickstart and a Tests row to the Status table.
- Modify: `AGENTS.md` — remove the leftover "weather forecasts" phrase (line ~83).
- Delete: `requirements.txt`.
- Delete: `.DS_Store` (on-disk; already gitignored).
- Create: git repository (`.git/`) + one initial commit.

---

## Task 1: Initialize git and verify .gitignore works

**Files:**
- Create: `.git/` (via `git init`)
- Modify: `.gitignore` (add `.claude/`)

This runs first so the `--ignored` sanity check can observe `.DS_Store` and `.claude/` **before** `.DS_Store` is removed in Task 5, and so `git add -A` in Task 6 cannot leak local agent config.

- [ ] **Step 1: Initialize the repository**

Run:
```bash
git init
```
Expected: `Initialized empty Git repository in /Users/carsynstephenson/Downloads/options-validator/.git/`

- [ ] **Step 2: Add `.claude/` to `.gitignore` (repo-safety: local agent config must never be committed)**

`.claude/settings.local.json` holds local tool-permission state and does not belong in the initial project commit. Append this block to `.gitignore` (after the existing `.env` block, before `.cache/`):

```gitignore

# Local Claude Code agent config / permissions -- never commit
.claude/
```

- [ ] **Step 3: Verify .gitignore ignores the generated/local artifacts (while .DS_Store still exists)**

Run:
```bash
git status --porcelain --ignored
```
Expected: lines prefixed with `!!` include `.venv/`, `.cache/`, `.DS_Store`, `.claude/`, and `__pycache__/` (a `__pycache__` dir may exist under the repo root and/or subpackages). These MUST appear as ignored (`!!`), confirming `.gitignore` works — not merely be absent. In particular `.claude/` MUST show as `!!`, not `??`. If any of `.venv/`, `.cache/`, `.DS_Store`, `.claude/` appears as untracked (`??`) instead of ignored (`!!`), stop and fix `.gitignore` before continuing.

- [ ] **Step 4: Do NOT commit yet**

The initial commit happens in Task 6 after all file changes are made. No commit in this task.

---

## Task 2: Set the honest strategy configuration (TDD)

**Files:**
- Modify: `config.py:21` (`RISK_SLEEVE`), `config.py:27` (`RISK_SLEEVE_CANDIDATES`), `config.py:64` (`A_SPREAD_WIDTH`)
- Test: `tests/test_core.py`

- [ ] **Step 1: Write the failing guard test**

Add this to the top imports of `tests/test_core.py` (the file already has `import config`):

```python
from analysis.feasibility import (
    ASSUMED_CREDIT_FRAC,
    contracts_that_fit,
    max_loss_per_spread,
)
```

Add this new test class at the end of `tests/test_core.py`, before the `if __name__ == "__main__":` block:

```python
class HonestSleeveConfigTests(unittest.TestCase):
    """Locks the decided CAPITAL-HONEST config: $14k sleeve, $2-wide.

    IMPORTANT: these assert GROSS feasibility only, under the current
    ASSUMED_CREDIT_FRAC. $2-wide is a ZERO-SLACK gross threshold, NOT a robust
    all-in fit: the sizing formula excludes commissions and assumes the 30%
    credit holds, so true all-in risk can exceed budget. Do not read a passing
    test here as "$2-wide is safe to trade." See spec
    2026-07-01-reproducible-foundation-design.md.
    """

    def _gross_max_loss(self, width):
        return max_loss_per_spread(width, ASSUMED_CREDIT_FRAC * width)

    def _contracts_for_width(self, width):
        budget = config.RISK_SLEEVE * config.RISK_PER_TRADE
        return contracts_that_fit(budget, self._gross_max_loss(width))

    def test_sleeve_is_capital_honest_fourteen_k(self):
        self.assertEqual(config.RISK_SLEEVE, 14_000)

    def test_configured_width_is_two(self):
        self.assertEqual(config.A_SPREAD_WIDTH, 2)

    def test_two_wide_is_a_zero_slack_gross_threshold_fit(self):
        # Per-trade budget exactly equals the $2-wide GROSS max loss: zero
        # slack. Commissions / worse real fills push true risk over budget.
        budget = config.RISK_SLEEVE * config.RISK_PER_TRADE
        self.assertEqual(self._gross_max_loss(2), budget)  # exact knife-edge
        self.assertEqual(self._contracts_for_width(2), 1)  # gross threshold fit

    def test_five_wide_does_not_fit_the_honest_sleeve(self):
        self.assertEqual(self._contracts_for_width(5), 0)

    def test_fourteen_k_is_a_feasibility_candidate(self):
        self.assertIn(14_000, config.RISK_SLEEVE_CANDIDATES)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
uv run python -m unittest tests.test_core.HonestSleeveConfigTests -v
```
Expected: FAIL. With the current config (`RISK_SLEEVE = 8_000`, `A_SPREAD_WIDTH = 5`, candidates without 14_000): `test_sleeve_is_capital_honest_fourteen_k`, `test_configured_width_is_two`, `test_two_wide_is_a_zero_slack_gross_threshold_fit` (at $8k the budget is $80, which is neither equal to the $140 gross max loss nor enough for 1 contract), and `test_fourteen_k_is_a_feasibility_candidate` fail. `test_five_wide_does_not_fit_the_honest_sleeve` happens to pass already (5-wide doesn't fit $8k either), which is fine.

- [ ] **Step 3: Update `config.py` — RISK_SLEEVE and its rationale**

Replace this block (currently around lines 15–27):

```python
# IMPORTANT (read before changing): "capital" in a backtest is a STUDY KNOB,
# not your bank balance. The honest way to size risk is to decide how much of
# YOUR money is the "options book" (the risk sleeve) and size 1% of THAT --
# not 1% of your whole net worth (which silently puts your stock portfolio
# behind every options trade) and not 1% of an arbitrary round number.
# Set RISK_SLEEVE to the dollars you are genuinely willing to lose here.
RISK_SLEEVE          = 8_000     # $ you are treating as the options book
RISK_PER_TRADE       = 0.01      # max fraction of RISK_SLEEVE at risk per trade
STARTING_CAPITAL     = 25_000    # account equity used by the backtest engine

# For the feasibility study we test sizing against several candidate sleeve
# sizes so you can SEE the trade-off rather than guess one.
RISK_SLEEVE_CANDIDATES = [8_000, 25_000, 58_000]
```

with:

```python
# IMPORTANT (read before changing): "capital" in a backtest is a STUDY KNOB,
# not your bank balance. The honest way to size risk is to decide how much of
# YOUR money is the "options book" (the risk sleeve) and size 1% of THAT --
# not 1% of your whole net worth (which silently puts your stock portfolio
# behind every options trade) and not 1% of an arbitrary round number.
# Set RISK_SLEEVE to the dollars you are genuinely willing to lose here.
#
# HONEST SLEEVE (2026-07-01 decision): the owner's ~$14k of genuine options
# risk capital = cash + active swing-trade capital. The $50k invested portfolio
# and up to $40k of Schwab margin are DELIBERATELY EXCLUDED: the portfolio must
# not sit behind option trades, and borrowed margin is not "willing-to-lose"
# money. An earlier "$58k sleeve so a $5-wide spread fits" idea was rejected as
# reverse-engineering the sleeve to fit the trade -- the exact mistake this file
# and analysis/feasibility.py warn against.
RISK_SLEEVE          = 14_000    # $ genuinely willing to lose (cash + swing)
RISK_PER_TRADE       = 0.01      # max fraction of RISK_SLEEVE at risk per trade
STARTING_CAPITAL     = 25_000    # account equity used by the backtest engine
                                 # (engine buying power; decoupled from the
                                 # risk sleeve above -- 1-contract spreads need
                                 # trivial buying power)

# For the feasibility study we test sizing against several candidate sleeve
# sizes so you can SEE the trade-off rather than guess one. 14_000 is the
# owner's real sleeve; the others bracket it so the trade-off stays visible.
RISK_SLEEVE_CANDIDATES = [8_000, 14_000, 25_000, 58_000]
```

- [ ] **Step 4: Update `config.py` — A_SPREAD_WIDTH and its rationale**

Replace this line (currently around line 64):

```python
A_SPREAD_WIDTH       = 5             # buy the put this many $ lower
```

with:

```python
# $2-wide is the CAPITAL-HONEST threshold candidate at the ~$14k sleeve -- NOT
# the "cost-efficient" width (narrower spreads are MORE commission/spread
# sensitive, not less). At 1% risk the per-trade budget is $140, which equals
# the $2-wide GROSS max loss exactly -- a ZERO-SLACK threshold (commissions and
# real-credit shortfalls are NOT in the feasibility formula, so true all-in risk
# can breach budget; the live data path must skip trades whose actual
# conservative credit does not fit). $5-wide does not fit this sleeve; $1-wide
# fits but is the most cost-punished. Not validated until real quotes replace
# ASSUMED_CREDIT_FRAC in feasibility.py.
A_SPREAD_WIDTH       = 2             # buy the put this many $ lower
```

- [ ] **Step 5: Run the guard test to verify it passes**

Run:
```bash
uv run python -m unittest tests.test_core.HonestSleeveConfigTests -v
```
Expected: PASS (5 tests OK).

- [ ] **Step 6: Run the full suite to confirm nothing else broke**

Run:
```bash
uv run python -m unittest discover -s tests -v
```
Expected: `OK`, 12 tests (the original 7 plus the 5 new). The original `test_defined_risk_sizing_never_rounds_up` still passes: it reads `config.RISK_SLEEVE` on both sides of its assertion, so the sleeve change does not break it.

- [ ] **Step 7: Confirm the feasibility table now shows the honest sleeve**

Run:
```bash
uv run python analysis/feasibility.py
```
Expected: a `sleeve $14,000` row appears under each width; for Width $2 it reads `1 contract(s) [FITS]`, and for Width $5 it reads `0 contract(s) [ZERO -- does not fit]`.

(No commit — Task 6 makes the single initial commit.)

---

## Task 3: Delete the stale requirements.txt

**Files:**
- Delete: `requirements.txt`

`pyproject.toml` + `uv.lock` are the single source of truth; `requirements.txt` is a hand-maintained second list that invites drift.

- [ ] **Step 1: Confirm no live project file still references requirements.txt (excluding docs)**

Run:
```bash
rg -n "requirements\.txt" --glob '!docs/**' --glob '!.venv/**' --glob '!.git/**' --glob '!.cache/**'
```
Expected: no output. (The README already dropped `pip install -r requirements.txt`. `docs/` is excluded on purpose — the spec and this plan legitimately name the file while describing its removal, so a repo-wide search would contradict itself.) If any non-docs match appears (e.g., in `README.md` or a `.py`), remove that reference before deleting the file.

- [ ] **Step 2: Delete the file**

Run:
```bash
rm requirements.txt
```
Expected: no output; `ls requirements.txt` then reports "No such file or directory".

(No commit yet.)

---

## Task 4: Document the test command in README

**Files:**
- Modify: `README.md` (Quickstart code block ~lines 29–33; Status table ~lines 12–21)

- [ ] **Step 1: Add the test command to the Quickstart block**

Replace this block:

```bash
uv sync
uv run python analysis/feasibility.py     # can a spread even fit your risk sleeve?
uv run python metrics.py                  # see the scoreboard on synthetic trades
```

with:

```bash
uv sync
uv run python analysis/feasibility.py     # can a spread even fit your risk sleeve?
uv run python metrics.py                  # see the scoreboard on synthetic trades
uv run python -m unittest discover -s tests   # run the test suite
```

- [ ] **Step 2: Add a Tests row to the Status table**

In the Status table, after the row:

```
| Smoke test | `smoke_test.py` | Phase 0 (needs ThetaData) |
```

add:

```
| Tests | `tests/test_core.py` | passing (`unittest`) |
```

- [ ] **Step 3: Verify the documented command actually works**

Run:
```bash
uv run python -m unittest discover -s tests
```
Expected: `OK` (12 tests). This confirms the README instruction is accurate.

(No commit yet.)

---

## Task 5: Scope trivia — remove "weather forecasts" and delete .DS_Store

**Files:**
- Modify: `AGENTS.md` (~line 83)
- Delete: `.DS_Store`

Runs AFTER Task 1's `--ignored` check, so `.DS_Store` was observed as ignored before removal.

- [ ] **Step 1: Remove the leftover cross-domain phrase in AGENTS.md**

Replace this line:

```
Do not hardcode current prices, weather forecasts, event probabilities, or market odds.
```

with:

```
Do not hardcode current prices, event probabilities, or market odds.
```

- [ ] **Step 2: Confirm no other Kalshi/weather references remain**

Run:
```bash
rg -ni "kalshi|weather" --glob '!docs/**' --glob '!.venv/**' --glob '!.git/**' --glob '!.cache/**'
```
Expected: no output. (If anything remains outside `docs/`, remove it.)

- [ ] **Step 3: Remove the on-disk .DS_Store**

Run:
```bash
rm -f .DS_Store
```
Expected: no output; the file is gone.

(No commit yet.)

---

## Task 6: Verify everything, then make the initial commit

**Files:**
- Create: initial git commit

- [ ] **Step 1: Full verification sweep**

Run each and confirm the expected result:

```bash
uv sync --locked --check
```
Expected: ends with `Would make no changes` (lockfile current; environment reproducible; not mutated).

```bash
uv run python analysis/feasibility.py
```
Expected: runs; `sleeve $14,000` row shows Width $2 `[FITS]` (1 contract), Width $5 `[ZERO -- does not fit]`.

```bash
uv run python metrics.py
```
Expected: prints the scoreboard demo ending in `VERDICT: INSUFFICIENT SAMPLE (6 losses; need >= 10)...`.

```bash
uv run python -m unittest discover -s tests
```
Expected: `OK` (12 tests).

```bash
rg -n "requirements\.txt" --glob '!docs/**' --glob '!.venv/**' --glob '!.git/**' --glob '!.cache/**'
```
Expected: no output (file gone, no live references).

- [ ] **Step 2: Stage everything (gitignore excludes venv/cache/pycache/DS_Store/.claude)**

Run:
```bash
git add -A
git status --porcelain --ignored
```
Expected: staged (`A `) entries include `config.py`, `metrics.py`, `README.md`, `AGENTS.md`, `.cursorrules`, `.gitignore`, `.python-version`, `pyproject.toml`, `uv.lock`, `smoke_test.py`, the `analysis/`, `data/`, `harness/`, `strategies/`, `tests/`, `results/.gitkeep`, and `docs/` trees. `requirements.txt`, `.DS_Store`, and anything under `.claude/` must NOT appear. Ignored (`!!`) entries (`.venv/`, `.cache/`, `__pycache__/`, `.claude/`) must NOT be staged.

- [ ] **Step 3: Audit the staged set before committing (first commit stages the whole world)**

Run:
```bash
git diff --cached --stat
git diff --cached --check
```
Expected: `--stat` lists only intended project files (source, config, tests, docs, lockfile, dotfiles above); confirm by eye that **no** `.claude/`, `settings.local.json`, `.env*`, secrets, `.venv/`, `.cache/`, or `__pycache__/` artifact appears. `--check` reports nothing (no whitespace errors / conflict markers). Explicit safety check — must return no output:
```bash
git diff --cached --name-only | rg -n "^\.claude/|settings\.local\.json|\.env|\.venv/|__pycache__/|\.cache/|\.DS_Store"
```
Expected: no output. If anything matches, unstage it (`git restore --staged <path>`) and add it to `.gitignore` before proceeding.

- [ ] **Step 4: Make the initial commit**

Run:
```bash
git commit -m "$(cat <<'EOF'
Initial commit: reproducible options-validator foundation

- uv/pyproject/uv.lock env pinned to Python 3.12; single dependency source
  of truth (requirements.txt removed).
- Honest strategy config: RISK_SLEEVE=14k, A_SPREAD_WIDTH=2 (zero-slack
  threshold fit; rationale in config.py), 14k added to feasibility candidates.
- Documented unittest command in README; scope narrowed to options-only.
- Guard tests lock the honest-config fit pattern.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```
Expected: a commit is created reporting the files added.

- [ ] **Step 5: Confirm a clean, correctly-tracked tree**

Run:
```bash
git log --oneline
git status --porcelain --ignored
```
Expected: `git log --oneline` shows exactly one commit. `git status --porcelain --ignored` shows a clean working tree — no staged/untracked source, only `!!` ignored entries (`.venv/`, `.cache/`, `__pycache__/`, `.claude/`). No `.DS_Store` anywhere; `requirements.txt` absent; nothing under `.claude/` tracked.

---

## Self-review notes (author)

- **Spec coverage:** Change #1 (delete requirements.txt) → Task 3. #2 (document unittest + status row) → Task 4. #3 (git init, ordered `--ignored` check, initial commit) → Tasks 1 & 6. #4 (weather-forecast phrase, `.DS_Store`) → Task 5. #5 (config values + reasoning + candidates) → Task 2. All spec verification bullets map to Task 6 Step 1 and Task 2 Step 7.
- **Ordering guarantee:** `git init`, `.claude/` gitignore, and the `--ignored` check (Task 1) precede `.DS_Store` removal (Task 5); commit (Task 6) is last.
- **Repo-safety:** `.claude/` (local agent permissions) is gitignored in Task 1 and Task 6 adds an explicit staged-set audit (`git diff --cached --stat`/`--check` + a name-only guard) so the first commit cannot leak local config, secrets, or cache artifacts.
- **Threshold-fit honesty** is carried into the `config.py` comment and the test (zero-slack exact-equality assertion + name `test_two_wide_is_a_zero_slack_gross_threshold_fit`), not just the spec. Wording is "capital-honest," not "cost-aware" (narrow spreads are more cost-sensitive).
- **Searches use `rg`** (repo preference), not `grep`.
- **No new runtime dependency** added; tests stay stdlib `unittest` (7 original → 12).
