# Q9 blocked-receipt supersession

The two 2026-08-01 Q9 receipts are retained as honest pre-reconciliation
history. They were generated while the source tree was dirty and the 33 July
24/27 cache files were outside the manifest, so they must not be used as the
current readiness result.

They are superseded by the committed 2026-08-02 receipts:

- `reports/thetadata_exit/2026-08-02-q9-offline-intelligence.json` — EOD
  offline readiness passes with no blockers.
- `reports/options_flow/2026-08-02-q9-flow-readiness.json` — options flow
  remains `NOT AUDITED / DATA-GATED` because no real dataset exists.

No market-data file was changed or removed during either audit.
