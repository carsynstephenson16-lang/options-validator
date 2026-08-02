# Options Validator reliability profile integration plan

## Goal

Vendor the verified five-source reliability catalog and add a separate,
read-only advisory reporter for point-in-time data, cost/fill correctness,
reproducibility, experiment governance, and dependency debt. It must not change
research results, caches, ledgers, provider behavior, or activation state.

## Frozen inputs and baseline

- Standards commit: `d88dcdbbbc26d919d0b2a398400767278e08027d`.
- Catalog version: `1`.
- Catalog SHA-256: `22543bf44d3e5c690c22b3eea279c218a883032300e2a923b7e980295a94a379`.
- Repository integration base: `c00044fb6bf4448c2814d7c8cf9cf43baeedf1ea`.
- The first full pre-change run had 2 import subprocesses exceed their fixed
  60-second timeouts during a resource-contended run; both passed in isolation
  in 11.714 seconds. A sandboxed retry then proved that loopback sockets and
  SQLite writes require the native environment. The definitive isolated run,
  with only `LIVE_MARKET_DATA_PROVIDER=schwab` supplied from configuration,
  passed all 2,302 tests in 176.051 seconds.
- Runtime dependencies added: none.

## Files and method

- Add the pinned snapshot, lock, complete 120-item profile, structured test
  receipt, and usage notes under `docs/reliability/`.
- Add `scripts/reliability_checklist.py` and its behavioral tests without
  importing it from any research or production path.
- Validate digest, repository-relative paths, evidence hashes and symbols, Git
  ancestry, mapping completeness, and N/A expiry before reporting.
- Compute `STALE` rather than authoring it. Consolidate overlapping source items
  under one local control. Preserve native MLTS 0/1/2 category scoring.
- Apply the approved six-input marginal-value score only to declared gaps;
  equivalent evidence always forces `BUILD_NOTHING`.

## Initial mappings and priorities

Map only current sealed-window, source-hash, experiment-registration,
cost/fill-selection, and cache-manifest controls with file and test evidence.
Keep source-to-verdict lineage, dependency utility, simpler-baseline coverage,
and stale-monitoring consolidation as explicit candidate gaps.

## Authority boundary and rollback

The tool cannot reveal holdouts, modify canonical data, update a study, write a
ledger, change a verdict, enable a provider, or activate trading. Every
experiment and promotion remains owner-gated. Rollback removes only the new
files; no runtime path or dependency is changed.

Verification is the focused checklist suite, syntax/lint checks applicable to
the new files, a real no-write CLI run, and a complete uncontended root suite.
