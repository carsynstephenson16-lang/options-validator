# External quantitative sources

These Git sources are deliberately outside the root `options-validator`
dependency graph. The root project remains the source of truth for the local
Black-Scholes implementation, cached option data, research ledger, and
scanner behavior.

## Active isolated tools

```bash
uv run --project tools/bs_parity python tools/bs_parity/run.py
uv run --project tools/financepy_validation python tools/financepy_validation/run.py
```

The first command uses `vollib` only as an independent numerical comparator.
It must not be imported by production code or used to change the local
Black-Scholes conventions. The second command evaluates FinancePy's analytic
Black-Scholes engine against the local implementation in a separate
environment; it is not a runtime dependency or a strategy engine.

The FinancePy check uses a $0.0001 absolute price-drift gate. FinancePy is
expected to be numerically close rather than bit-identical; the observed
2026-07-18 run was 8 comparisons with a maximum drift of approximately
$0.0000132. This is a model-validation observation, not evidence that either
implementation is the canonical market-data or strategy model.

## Equity-research OpenBB boundary

Use the MIT-licensed `backends-for-openbb` repository as the adapter scaffold
for `equity-research`. OpenBB output is enrichment/discovery only. It must not
replace or overwrite:

- SEC filings or `tickers/*/filings/_companyfacts.json`;
- existing captured pages and their URL/access-time metadata;
- the repo's canonical `[SOURCED: ...]` citation trail; or
- deterministic valuation/model outputs.

OpenBB Platform itself is AGPL-3.0-only. Keep it in an
`equity-research`-owned optional environment, not in this repository's root
environment. Any future service or distribution that embeds or modifies the
AGPL platform needs a separate license review; this note is not legal advice.

The current `equity-research` checkout has unrelated uncommitted work, so this
repository records the exact adapter source and contract but does not mutate
that checkout as part of this change.

## Deferred and reference-only sources

- `ffn` is recorded for a later portfolio-performance reporting decision; it
  is not installed and cannot affect strategy verdicts.
- `pysabr`, `willowtree`, and `finoptions` are reference material only. They
  are not imported, installed, or used in the scanner/backtest path.

Exact repository URLs, revisions, licenses, and roles are in
`tools/third_party/repos.toml`.

The shared implementation sequence and Claude-ready handoff are in
`docs/superpowers/plans/2026-07-18-cross-repo-external-quant-integration-map.md`.

## FinancePy GPL boundary

FinancePy is GPL-3.0-or-later. It is fetched by the isolated validation
project only. No FinancePy code is copied into the root package, imported by
production modules, or linked into the root runtime. If validation tooling is
ever distributed together with this repository, re-check the GPL obligations
for that distribution, include the license/source notices required by the
license, and obtain legal review for any combined or hosted deployment.
