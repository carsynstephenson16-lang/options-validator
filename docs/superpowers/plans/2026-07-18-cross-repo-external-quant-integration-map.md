# Cross-repo external quantitative-library integration map

**Audience:** Claude or any implementation agent working in either repository.

**Purpose:** apply the same library decisions consistently without creating a
shared runtime, cross-repo imports, or a second source of truth.

## 1. Non-negotiable architecture

```text
options-validator                         equity-research
-----------------                         ---------------
local Black-Scholes  <-> vollib           SEC filings + companyfacts + captures
                 \                            remain canonical
                  -> FinancePy                 |
                     validation only            +-> OpenBB adapter sidecar
                                                     (non-canonical enrichment)

No imports, shared configuration, or automatic data writes between repositories.
```

Each repository owns its code, environment, lockfile, tests, and artifacts.
The only shared item is this decision map and the pinned-upstream manifest at
`tools/third_party/repos.toml`.

## 2. Library ownership map

| Library | options-validator | equity-research | Hard boundary |
|---|---|---|---|
| `vollib` | Isolated Black-Scholes parity comparator only | None | Never import in production/scanner code. |
| FinancePy | Separate analytic-model validation environment only | None | GPL-3.0-or-later; do not copy or import it into the root runtime. |
| OpenBB Platform | None | Optional, isolated enrichment runtime only | AGPL-3.0-only; legal review before a distributed or hosted use. |
| `backends-for-openbb` | Reference only | MIT adapter scaffold | It may present enrichment; it never replaces citations or filings. |
| `ffn` | Deferred | Deferred | Add only after a portfolio-performance reporting spec is approved. |
| `pysabr`, `willowtree`, `finoptions` | Reference only | Reference only | No installation, imports, backtests, or verdict inputs. |

Use the immutable revisions already recorded in
`tools/third_party/repos.toml`. Do not substitute a PyPI release, floating
branch, or another fork without an explicit change record.

## 3. Implementation order

### Phase A — preserve the boundaries first

1. Check the target repository's worktree. Do not overwrite unrelated work.
2. Reconfirm its canonical data and model paths before adding an adapter.
3. Add any new dependency to a **separate optional environment**, never the
   root runtime dependency set by default.
4. Pin every Git source to a full commit SHA and commit that environment's
   lockfile.
5. Write an explicit `README` stating the role, license, source URL, and
   commands to run it.

### Phase B — options-validator (already implemented)

Keep the root `pyproject.toml` and `uv.lock` free of these libraries. The
only permitted executables are:

```bash
uv run --frozen --project tools/bs_parity python tools/bs_parity/run.py
uv run --frozen --project tools/financepy_validation python tools/financepy_validation/run.py
```

Required behavior:

- `vollib` compares only European Black-Scholes-Merton price vectors against
  `options_researcher.black_scholes`; it cannot replace that implementation.
- FinancePy compares only its analytical European model. It reports numerical
  drift, but cannot write a candidate, rank, backtest result, ledger record,
  or market-data artifact.
- Any future FinancePy experiment must remain under
  `tools/financepy_validation/`, use its own lockfile, and emit a clearly
  non-canonical validation report.
- No strategy, live-dashboard, cache, fill-model, or research-verdict code
  may import `vollib` or FinancePy.

Acceptance checks:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_black_scholes.py' -v
uv run --frozen --project tools/bs_parity python tools/bs_parity/run.py
uv run --frozen --project tools/financepy_validation python tools/financepy_validation/run.py
.venv/bin/ruff check tools/bs_parity tools/financepy_validation
```

### Phase C — equity-research OpenBB adapter

Work on a clean branch or worktree of `equity-research`. Do **not** add OpenBB
to `requirements.txt` or the default dependency list. Instead, create an
optional, explicitly named integration surface such as:

```text
integrations/openbb_adapter/
  README.md                 # license, setup, provenance, non-canonical status
  pyproject.toml            # isolated adapter/service environment
  app.py                    # adapter endpoints only
  schemas.py                # typed output envelope
  tests/
    test_contract.py
    test_provenance.py
    test_canonical_boundary.py
```

Start from the MIT `backends-for-openbb` scaffold. If the implementation also
installs or embeds the AGPL OpenBB Platform, record that separately in the
optional environment and complete a license review before distribution or
hosting.

The adapter must return a typed envelope equivalent to:

```json
{
  "canonical": false,
  "provider": "openbb",
  "retrieved_at": "2026-07-18T16:00:00Z",
  "as_of": "2026-07-18",
  "request": {"ticker": "EXAMPLE", "endpoint": "..."},
  "source_urls": ["https://..."],
  "data": {}
}
```

Rules for the adapter:

- Explicit request only; no background refresh, trade action, or mutation of
  research conclusions.
- Save raw OpenBB captures, when retained, under
  `tickers/<TICKER>/web/openbb/` with provider, original URL(s), retrieval
  time, and `canonical: false` metadata.
- It must never write to `tickers/<TICKER>/filings/`,
  `_companyfacts.json`, `tickers/<TICKER>/models/`, or an analysis file's
  `[SOURCED: ...]` record.
- Filing-grade actuals still come from SEC/EDGAR. Existing captures retain
  their current authority and provenance.
- Treat the adapter as analyst-context/UI material only. Any number needed in
  a memo must be independently rebound to the repository's existing canonical
  pipeline before citation.

Minimum tests:

1. A mocked adapter response has `canonical: false`, provider identity,
   timestamp, source URL, and as-of date.
2. The capture writer emits only to `tickers/<TICKER>/web/openbb/`.
3. A test proves it cannot write to `filings/`, `_companyfacts.json`,
   `models/`, `decisions.md`, or `data/calibration.md`.
4. A memo-validation fixture containing an OpenBB value without an SEC or
   existing canonical citation fails the existing citation rules.
5. No network call runs in the unit-test suite; provider calls are mocked.

### Phase D — deferred portfolio reporting

Do not install `ffn` yet. Revisit only after a short reporting specification
defines the portfolio input schema, return convention, cash-flow treatment,
benchmark, as-of timestamp, and whether the report is descriptive only. The
report must consume recorded position and mark data; it cannot calculate or
claim strategy edge.

## 4. Claude implementation prompt

> Implement only the work assigned to the repository you are currently in.
> Read the cross-repo external quantitative-library integration map first.
> Preserve the root dependency graph and canonical data/citation paths. Use
> full Git commit pins and a separate optional environment for any external
> tool. Do not add cross-repo imports, shared configuration, background
> fetches, trading behavior, or strategy/verdict inputs. For OpenBB, build a
> non-canonical enrichment adapter with typed provenance and tests proving it
> cannot write to SEC/companyfacts, models, analysis citations, decisions, or
> calibration. Run the acceptance checks and report any license or worktree
> blocker before proceeding.

## 5. Definition of done

- Each active library has one owner repository and a declared purpose.
- Every active Git dependency is full-SHA pinned and lockfile-backed.
- Root production dependencies remain unchanged.
- Numerical comparison output is diagnostic only and has no strategy side
  effects.
- OpenBB data is clearly non-canonical, provenance-bearing, and cannot replace
  SEC/companyfacts or captured-source evidence.
- Deferred/reference libraries have no import path or runtime effect.
