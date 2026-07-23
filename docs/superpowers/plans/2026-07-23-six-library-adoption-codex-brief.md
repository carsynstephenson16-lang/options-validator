# Six-Library Adoption Evaluation — Codex Brief (2026-07-23)

> **For agentic workers:** This brief's verdict is **NO INSTALLATION WORK
> TODAY**. There are zero execution tasks in the "do now" state. The
> conditional tasks in §4 are pre-written so they can be executed the day
> their trigger fires — do NOT execute them speculatively. If you were
> dispatched to "install the six libraries," stop and report back citing
> this brief.

**Goal:** Adjudicate an external recommendation to add QuantLib, SciPy,
PyArrow, Polars, Numba, and CVXPY (keeping Lumibot as the engine, vectorbt
as a cross-check, skipping Backtrader/Zipline), against the repo's scope
guard and engineering rules.

**Method:** Three parallel research agents on 2026-07-23 — (1) full repo
dependency-tree + usage audit (`uv tree`, grep of every source dir, reads of
`metrics.py`, `options_researcher/black_scholes.py`,
`options_researcher/robustness/`, `config.py`); (2) external research on
QuantLib/Numba/CVXPY (PyPI status, wheels, adversarial fit); (3) external
research on SciPy/Polars/PyArrow (same). Adversarial framing per the
operating manual ("show me how this could be lying," argue the skip case
first).

**Verdict: 0 of 6 pass the scope-guard sentence today.** One is already a
direct dependency (PyArrow), two are already installed transitively with
zero repo imports (SciPy, Polars), three are absent with no code shape
needing them (QuantLib, Numba, CVXPY). All parked in
`ideas-parking-lot.md` ("Six-library adoption proposal, parked 2026-07-23")
with per-library un-park gates.

---

## 1. Ground truth (Repo-verified, 2026-07-23)

From `uv tree` over the resolved lockfile (327 packages) and source grep:

| Library  | In env today?                                   | Repo imports?                       |
|----------|--------------------------------------------------|-------------------------------------|
| PyArrow  | Direct dep `pyarrow>=14,<22`, installed 21.0.0   | Yes — 4 files (parquet/provenance)  |
| SciPy    | Transitive, 1.18.0 (lumibot → quantstats-lumi)   | **None**                            |
| Polars   | Transitive, 1.42.1 (lumibot AND thetadata)       | **None**                            |
| QuantLib | Absent                                           | None                                |
| Numba    | Absent                                           | None                                |
| CVXPY    | Absent                                           | None                                |

Lumibot 4.5.63 unconditionally requires `polars>=1.32.3`, `scipy>=1.14.0`,
`pyarrow>=15.0.0` — so SciPy and Polars sit on disk regardless of anything
this repo declares.

## 2. Why each fails the scope guard today

- **PyArrow:** the recommendation is already satisfied — it has backed the
  ~18k-file parquet chain cache since the initial commit. No live
  hypothesis is blocked. (Sub-finding: the `<22` cap is stale vs PyPI
  25.0.0, released 2026-07-10; nothing needs ≥22, so no bump now.)
- **SciPy:** the repo hand-rolls its statistics **on purpose, three times,
  recently**: `metrics.py`'s verdict CI is a weekly-block + Politis-Romano
  stationary bootstrap (dependence-aware); `scipy.stats.bootstrap` is
  IID-only — close to useless for the headline statistic.
  `robustness/statistics.py`'s `CircularBlockPermutation` has no scipy
  equivalent (`permutation_test` lacks block modes), and Holm step-down
  lives in statsmodels, not scipy. `rq1_runner.py` used
  `pandas.rank().corr()` over `scipy.stats.spearmanr` with scipy already on
  disk. Adding a direct pin with zero imports is a dead declaration.
- **Polars:** EOD chains for 4–15 names are pandas-sized; the suite already
  runs in minutes; Lumibot/ThetaData boundaries speak pandas. A second
  dataframe idiom in a beginner-Python-owned codebase is a real cost with
  no measured benefit.
- **QuantLib (PyPI `QuantLib` 1.43, 2026-07-14 — NOT the stale
  `QuantLib-Python` 2020 stub):** healthy, cp39-abi3 wheels for macOS
  arm64+x86_64, ~16 MB, no numpy conflicts. But
  `options_researcher/black_scholes.py` (frozen 2026-07-17) is deliberately
  dependency-free, tested, and covers what the live hypotheses score on.
  SWIG bindings are non-idiomatic; official Python docs are thin.
- **Numba (0.66.0, 2026-07-01):** zero Monte Carlo / profiled hot loops in
  the codebase (grep-confirmed); JIT first-call compile cost taxes the
  fast-offline-suite requirement; pins numpy `<2.5` (repo allows `<3`);
  **no macOS x86_64 wheels exist at all** (llvmlite is arm64-only on mac).
- **CVXPY (1.9.2, 2026-06-22):** mandatory dep tree pulls osqp, clarabel,
  scs, highspy, qdldl — 5+ compiled solvers. The repo has no optimization
  problem: sizing is hard dollar caps and integer slots in `config.py`, and
  `tools/h7_adjudicate.py` declares portfolio caps out of simulation scope
  (v1.2(6)). Licensing is clean (Clarabel Apache-2.0) — irrelevant, since
  there's nothing to solve.
- **vectorbt (from the same external recommendation):** not evaluated for
  install — a second backtest engine "for cross-checks" collides with the
  standing rule that Lumibot is the one engine and we don't build parallel
  backtest infrastructure. Parked alongside the six. Backtrader/Zipline:
  the recommendation itself said skip; concur.

## 3. Codex tasks — do now

**None.** No `pyproject.toml` change, no `uv add`, no code change. This
brief plus the parking-lot entry are the complete deliverable.

## 4. Conditional tasks (pre-written; execute ONLY when the trigger fires)

### Task C1 — Promote SciPy to a direct dep (trigger: first real repo `import scipy`)

The likeliest first import is swapping the hand-rolled IV root-finder for
brentq. When (and only when) a registered need makes that swap worthwhile:

**Files:**
- Modify: `pyproject.toml` (dependencies list)
- Modify: `options_researcher/black_scholes.py` (`implied_vol`)
- Test: existing `tests/` coverage of `implied_vol` must stay green unchanged

Steps:
1. `uv add "scipy>=1.14,<2"` (matches Lumibot's floor; lockfile will not
   change materially since scipy 1.18.0 is already resolved).
2. In `implied_vol`, replace the Newton+bisection hybrid with
   `scipy.optimize.brentq` over the existing frozen bracket `[0.01, 5.0]`,
   keeping the existing pre-check that price lies within
   `[f(low), f(high)]`. Note this touches a FROZEN module
   (2026-07-17 spec) — owner sign-off required before the edit, and the
   module docstring's "no third-party dependencies" line must be amended in
   the same commit.
3. `uv run python -m unittest discover -s tests` — exit 0 required; IV
   round-trip tests must pass with no tolerance loosening.
4. Commit pyproject + lockfile + module together.

### Task C2 — PyArrow cap bump (trigger: any dependency or feature requiring pyarrow ≥22)

1. Change `pyarrow>=14,<22` → `pyarrow>=14,<26` in `pyproject.toml`.
2. `uv sync --frozen` fails → `uv lock` → full test suite → commit.

### Task C3 — QuantLib (trigger: registered hypothesis needing American-exercise Greeks)

Requires a new registered hypothesis first; then: `uv add quantlib` (PyPI
name `QuantLib`, ≥1.43), use its binomial/finite-difference American
engines ONLY as a verification cross-check against
`options_researcher/black_scholes.py` outputs — never as a replacement for
the frozen module without a spec amendment.

### Tasks with no pre-written steps (re-evaluate from scratch if triggered)

- **Polars** — trigger: profiled pandas wall-clock bottleneck inside a
  robustness-layer loop reprocessing full chains.
- **Numba** — trigger: a specific profiled loop measured as the bottleneck
  AND shown to resist numpy vectorization.
- **CVXPY** — trigger: pre-registered hypothesis requiring joint cross-name
  correlation-aware sizing.

## 5. Provenance

- Source recommendation: external (LLM-asserted, pasted by owner
  2026-07-23) — treated as a hypothesis to test, not a directive.
- PyPI facts (versions, dates, wheels, requires-dist): Official-source,
  fetched 2026-07-23.
- Dependency tree and code-usage claims: Repo-verified via `uv tree`,
  `uv.lock`, and direct file reads on 2026-07-23.
- scipy.stats limitations (IID-only bootstrap, no block permutation):
  Official-source, docs.scipy.org, fetched 2026-07-23.
