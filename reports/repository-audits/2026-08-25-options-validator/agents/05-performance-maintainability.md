# Domain 5 — Performance and maintainability audit

**Audit basis:** frozen `c9e74ccd05e4ecdd0de8de6f35bef714bc6f1771`; static,
read-only review only. No provider, network, live/paper, cache, ledger,
receipt, source, or test operation was performed. The only audit write is this
report.

## Verdict

**NOT READY for an unscoped performance or cleanup change.** There is verified
avoidable repeated parquet I/O in the display assembler, duplicated H6/H8
helper implementations, and two verification surfaces absent from root CI.
Their runtime impact is **inferred**, not measured; correctness-sensitive or
protected-path changes remain plan-only.

## Evidence and coverage

- **Verified:** the worktree HEAD is the requested frozen SHA. The preflight
  report marks `options_researcher/attractiveness_dashboard.py`,
  `options_researcher/h6_watch.py`, and the operational workflow sources as
  protected WIP (`00-preflight-and-wip.md:124-157`).
- **Verified static size:** AST parsing counted 4,173 lines, 111 functions,
  a 245-line largest function, and a 32-parameter largest signature in
  `options_researcher/attractiveness_dashboard.py`; it is the largest reviewed
  Python module. Other large authority-bearing modules include
  `h7_real_scoring.py` (2,029 lines) and `h7_paper_lifecycle.py` (1,908).
  Size is a prioritization signal, not a defect by itself.
- **Verified static I/O paths:** reviewed
  `data/underlying_closes.py:44-91`,
  `options_researcher/attractiveness_dashboard.py:1364-1557`, and
  `:1106-1149`; all three paths are necessary to establish the repeated-read
  finding below.
- **Verified tooling:** root CI runs lock sync, Ruff lint, Pyright, root unit
  coverage, and QuantLib validation, but omits `ruff format --check` and any
  `tools/repo_rag` command (`.github/workflows/ci.yml:13-48`). The latter is a
  separate tracked Python project with 11 `test_*.py` files and documented test
  command (`tools/repo_rag/pyproject.toml:1-16`,
  `tools/repo_rag/README.md:118-120`).
- **Counterevidence:** the dashboard intentionally makes only standard-library
  imports at module import time (`attractiveness_dashboard.py:27-47`) and
  defers pandas/project imports to real assembly (`:1364-1402`), so this audit
  does **not** establish an import-time performance problem. Root CI is also a
  meaningful locked, offline quality gate; its omissions do not show a current
  product failure.
- **Not performed / Unknown:** no cache-size-dependent dashboard timing,
  profiler, memory measurement, full-suite run, or CI execution. A timing run
  would require a defined cache snapshot and a declared no-write harness;
  absent that, milliseconds, memory, and user impact are **UNKNOWN**.

## Findings

### PM-01 — One dashboard assembly rereads each regular close parquet

**Status:** **VERIFIED mechanics; INFERRED runtime cost; no demonstrated
latency defect.**

For every non-Schwab symbol, `_gather_symbol()` first calls `load_closes()`
then `load_closes_adjusted()` (`attractiveness_dashboard.py:1538-1541`).
`load_closes_adjusted()` delegates back to `load_closes()`
(`data/underlying_closes.py:86-91`), and `load_closes()` always calls
`pd.read_parquet()` (`:44-60`). Later in the same real assembly,
`_underlying_closes_store_freshness()` opens each configured close parquet
again to derive its maximum session (`attractiveness_dashboard.py:1106-1149`).
Thus a normal cached candidate section causes three full reads of that symbol's
underlying-close parquet: raw, adjusted-from-a-second-raw, and freshness.

This is not an accusation that the distinct semantics are wrong: raw closes
are deliberately used for strike/spot arithmetic and adjusted closes for
technicals (`data/underlying_closes.py:44-91`). Nor did this audit establish
that parquet reads dominate wall time. It is, however, a directly observable
same-input reparse inside a single, deterministic display build.

**Smallest safe candidate:** introduce an assembly-scoped, injected
close-frame loader that reads each immutable source frame once, produces raw
and adjusted series from it, and derives the freshness maximum from that same
validated frame. Keep `data.underlying_closes.load_closes*` public contracts
unchanged. Add parity tests for raw/adjusted ranges, OOS refusal, malformed
stores, missing symbols, and byte-for-byte identical rendered payloads before
comparing measured cold/warm timings on a declared cache snapshot.

**Eligibility:** **PLAN-ONLY / BLOCKED.** The affected dashboard is protected
WIP. The proposal must not turn cache reads into a silent stale-data fallback
or change raw-versus-adjusted provenance.

### PM-02 — H6/H8 contain exact or near-exact maintenance copies

**Status:** **VERIFIED duplication; INFERRED divergence risk; no behavioral
defect established.**

Static AST-body comparison finds five functions identical between
`options_researcher/h6_watch.py` and `options_researcher/h8_watch.py`:
`_validated_chain` (15 lines each), `_require_session` (4), `_feature_iv_rank`
(17/15), `_json_default` (4), and `_json_safe` (2). `choose_contract` is
57/58 lines with a 0.995 AST sequence similarity, and `validate_book` is
139/113 lines with 0.926 similarity. Both modules also independently read
parquet chains and serialize JSON (`h6_watch.py:175-189,880,894-895,992-1015`;
`h8_watch.py:136-150,742,756-757,820-845`).

The overlap is a maintenance surface: a schema or normalization repair can
land in one watcher but not the other. It is **not** proof that a current
drift exists; the non-identical entry/exit and book-policy paths plausibly
encode distinct registered contracts, and `h8_watch.py` explicitly reuses
some H6 book definitions (`h8_watch.py:36-37`).

**Smallest safe candidate:** characterize the currently identical pure helper
behavior with shared parameterized tests first. Only then consider extracting
the exact chain-validation/JSON-normalization subset into a side-effect-free,
policy-neutral utility. Leave entry rules, exit rules, book layout, receipts,
and config reads in their existing modules. Require differential tests against
both existing APIs before and after extraction.

**Eligibility:** **PLAN-ONLY / BLOCKED.** `h6_watch.py` is protected WIP, and
these watchers are research/forward-paper boundaries. No consolidation is
authorized by this audit and none should alter a frozen hypothesis contract.

### PM-03 — Root CI misses format validation and the isolated repo-rag suite

**Status:** **VERIFIED workflow coverage gap; impact INFERRED.**

The project declares Ruff formatting (`pyproject.toml:48-50`) and local
pre-commit runs `uv run ruff check --fix` plus Pyright
(`.pre-commit-config.yaml:1-17`). CI runs only `uv run ruff check .`, not
`uv run ruff format --check .` (`.github/workflows/ci.yml:33-42`). Therefore a
format-only deviation can pass CI if the contributor did not run hooks.

`tools/repo_rag` is more than an untracked experiment: it has its own
`pyproject.toml`, 11 tracked test modules, a launchd wrapper, and a documented
test invocation (`tools/repo_rag/pyproject.toml:1-16`,
`tools/repo_rag/README.md:111-120`, `scripts/run_repo_rag_health.sh:1-17`).
The root CI workflow neither changes into that project nor invokes its suite.
This does not prove repo-rag is broken, only that its tests are not part of
the main PR gate.

**Smallest safe candidate:** add an offline CI step for `uv run ruff format
--check .`; add a separate repo-rag job that uses its declared interpreter,
runs `python -m unittest discover -s tests` from `tools/repo_rag`, and writes
only temporary test artifacts. First validate that job on a no-provider,
no-index fixture path. Keep the existing root quality job unchanged.

**Eligibility:** **IMPLEMENTATION-ELIGIBLE after explicit owner approval.**
The affected CI/configuration files are not named protected WIP, the proposal
does not change research, provider, or operational behavior, and it has a
clear rollback (remove the new isolated job/step). It still requires a fresh
CI run before being represented as passing.

### PM-04 — Performance claims currently have no committed measurement contract

**Status:** **VERIFIED absence in reviewed tooling; UNKNOWN product impact.**

The reviewed root developer surfaces define correctness checks (lock sync,
lint, type checking, coverage, unit tests) but no dashboard/runtime benchmark,
latency budget, cache-snapshot manifest, or profiler fixture
(`pyproject.toml:1-80`, `.github/workflows/ci.yml:1-71`, README quickstart
`README.md:80-105`). The repository documents correctness and data provenance
well; those are not substitutes for a reproducible performance baseline.

**Smallest safe candidate:** do not add a mandatory performance threshold.
Instead add an opt-in, offline benchmark harness with a fixed synthetic
fixture and JSON output containing Python/OS/package versions, input rows,
wall-clock distribution, and peak-memory method. It must read no real cache,
construct no provider, write only `.tmp`, and start as a manually invoked
diagnostic until repeated measurements establish variance. That would make a
future PM-01 change measurable without treating one developer laptop result as
a regression gate.

**Eligibility:** **DESIGN-READY, implementation needs separate approval.**
No root-path overlap was identified, but adding a benchmark and fixture is
new tooling rather than a repair; it should not be smuggled into an unrelated
performance refactor.

## Priority and final decision

1. **PM-03:** inexpensive, isolated CI coverage with clear failure signal and
   rollback; implementation-eligible only after approval.
2. **PM-01:** highest directly verified avoidable I/O, but measure after
   parity design and protected-WIP clearance.
3. **PM-02:** reduce future watcher drift only through a deliberately tiny,
   policy-neutral shared seam; do not merge the watcher modules.

**Final ready decision:** **NOT READY** for source, cache, watcher, or
operational changes from this audit. One CI-only proposal is implementation-
eligible with approval; all other candidates are evidence-backed plans. No
strategy, parameter, provider, paper-book, ledger, receipt, or live behavior
change is supported.
