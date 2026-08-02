# OD-1 schema-v2 full audit — 2026-08-02

## Verdict

**PASS WITH WARNINGS / DATA QUALITY ACCEPTABLE WITH QUARANTINES.** This is a
data-readiness result only. It is not a strategy result, an H7 restart, an edge
claim, or live-trading authority.

The full machine receipt is stored beside the ignored data at:

`/Users/carsynstephenson/options-validator/.cache/chains_v2/od1-2026-08-01/_meta/full_audit.json`

- Receipt SHA-256 identity: `c08106ba2cb5c540c8800925cf0f5511c99c733d944c2597de80f8b3ea77c7e3`
- Audit-source commit: `c6e83e70e60e4d0d05931007b2621455bf9ddd3d`
- Source identity: clean; 20 exact source hashes bound in the full receipt,
  including `data/atomic_io.py` and
  `options_researcher/h7_synthetic_proof.py`, two runtime dependencies omitted
  by the superseded receipt's source-identity closure
- Scope: 18 symbols × 256 XNYS sessions = 4,608 normalized partitions
- Raw provider frames bound: 9,216
- Normalized chain plus independent-close files bound: 4,626
- Effective blockers: 0
- Warnings: 10,394

The outer receipt hash, embedded base-audit receipt, normalized file-hash map,
and raw-file hash map were independently recomputed after the dependency
closure was repaired and the full audit rerun.

## Exact-byte quarantines

The bytes remain untouched. These whole daily partitions are excluded from
every verdict-bearing read by symbol, session, size, and SHA-256:

| Symbol | Session | Defect | SHA-256 |
| --- | --- | --- | --- |
| AMD | 2025-11-24 | 18 crossed markets | `3089e58c4f92…ace1` |
| AMZN | 2025-11-24 | 6 crossed markets | `e344c3fdf153…ff7b` |
| AVGO | 2025-11-24 | 12 crossed markets | `dc3872d2b2f4…f14f` |

Registry SHA-256: `e16a56104b0d8be08f8f73bb3140bc53f7241c01a07bf0feb7d2dc5cdc777be0`.

A post-integration smoke check accepted audited `NVDA 2026-07-31` with bound
partition SHA-256
`cf5829591821aeda50ff8f8df50989d25cb45a449071e64c7dd8eee51f8bfd78`.
The focused loader tests separately refuse a quarantined partition with
`is quarantined from verdict use`.

## Warning interpretation

- 4,608 check-10/11 warnings disclose bad IV/Greek values only on rows outside
  the exact H7 IV/contract-selection mask.
- 3,225 H7-admission warnings mean many symbol-days do not have five qualifying
  near-money contracts. The strategy must skip those days.
- 914 spread warnings and 4 zero-bid warnings are disclosed liquidity defects.
- 878 put-call-parity warnings are diagnostic only. The independent provider
  underlying close comparison passed; simplified parity omits rates, dividends,
  and American-exercise effects.
- 762 monthly-listing warnings describe strategy ineligibility or absent calendar
  monthlies, not proof of missing provider rows.

The audit therefore supports safe, receipt-bound offline reads of the
nonquarantined partitions. It does not show that any strategy has an advantage,
or even that H7 will produce enough entries for a verdict.
