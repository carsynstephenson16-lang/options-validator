# Canonical chain-cache manifest reconciliation — 2026-08-01

## Verdict

The 33 top-level July 24/27 chain files are now bound into
`data/chain_cache_manifest.txt`. The cache files themselves were not rewritten
or deleted. The manifest grew from 31,333 to 31,366 entries and a fresh
`tools/cache_manifest.py verify` returned `verify: OK`.

## Provenance and byte checks

- The pre-reconciliation Q9 inventory identified exactly 33 top-level extras.
- All 33 had matching append-only acquisition facts: 18 also had attestations
  and 15 were fact-only.
- Immediately before and after manifest generation, every file's size and
  SHA-256 matched the hashes captured in the Q9 receipt.
- The tracked diff contains exactly 33 added manifest lines and no removed or
  modified manifest lines.

## Nested SPY classification

Two files use the `SPY` / `2022-12-30` key, but they are not duplicate bytes:

| Path | Rows | Size | SHA-256 | Classification |
| --- | ---: | ---: | --- | --- |
| `.cache/chains/SPY_2022-12-30.parquet` | 6,920 | 249,531 | `ea9882f89c29edf47e1534da43fb85aaf14f1884b2d3e07cb0ae1967346d46b3` | Canonical top-level chain |
| `.cache/chains/dolthub/SPY_2022-12-30.parquet` | 158 | 13,744 | `cd6f4f4333ef4d66cc4b1e10b917f7c36389785696c05f55b5aed3cd320d8f64` | Noncanonical nested alternate snapshot |

Both files have the same eleven-column v1 shape, but their contents and row
coverage differ. The nested file remains untouched for provenance. It is not
listed in the canonical top-level manifest and must not be selected by cache
consumers.

## Commands

```text
.venv/bin/python -m unittest discover -s tests -p 'test_cache_manifest.py'
# Ran 5 tests: OK

.venv/bin/python tools/cache_manifest.py generate
# wrote 31366 entries to data/chain_cache_manifest.txt

.venv/bin/python tools/cache_manifest.py verify
# verify: OK
```
