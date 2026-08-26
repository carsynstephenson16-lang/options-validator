# Domain 3 — Data and Provenance Audit

**Scope:** frozen audit worktree at `c9e74ccd05e4ecdd0de8de6f35bef714bc6f1771`; static/read-only source, tracked evidence, and safe canonical-cache metadata inspection. No provider call, capture, cache/ledger/receipt mutation, or paper/live operation was performed. Protected-WIP overlaps are plan-only.

**Overall verdict:** **NOT READY for an unqualified data-provenance claim.** The repository has strong exact-byte and fail-closed controls for the canonical v1 cache, schema-v2 partitions, and Schwab package identity. Two currently live integrity/provenance gaps and one permanent v1 limitation remain. No strategy result is reinterpreted by this audit.

## Verified strengths

- **Verified — frozen v1 identity and retention intent.** `data/chain_cache_manifest.txt` has 31,366 entries; the supplied canonical `tools/cache_manifest.py verify` result was `OK`. The manifest verifies every top-level regular file by name, size, and SHA-256 (`tools/cache_manifest.py:31-38,58-74`); README explicitly describes the same frozen 31,366-file corpus (`README.md:49-50,134-141`). The stronger exit-audit parser separately recognizes the classified nested SPY alternate rather than treating it as canonical (`tools/thetadata_exit_audit.py:303-421`).
- **Verified — acquisition and exact-session fallbacks fail closed.** ThetaData acquisition has a non-overridable refusal (`data/provider_policy.py:1-26`), whereas cached reads remain available. The H7 gate never backfills or substitutes a date and gives missing/stale inputs named no-go codes (`options_researcher/h7_data_gate.py:1-24,116-165,212-355`). This is the correct response to the cacheless audit worktree's 31,366 missing files: **environmental/Blocked**, not evidence of cache loss.
- **Verified — v2 has materially stronger provenance.** The v2 receipt checks content-bound raw hashes, partition hashes, clean source closure, audit scope, consumer scope, and quarantine state (`data/cache_schema.py:113-261`; `tools/thetadata_v2_audit.py:177-223,357-435`). It is correctly isolated and not silently promoted (`docs/provider-transition.md:57-60,67-74`).
- **Verified — four Schwab exact-session packages are byte-consistent in the canonical cache.** Offline `verify_session` passed for all 15-name packages dated 2026-08-14, 08-19, 08-20, and 08-24, matching their tracked manifest/receipt hashes. The verifier enforces session, sorted universe, receipt timing, `force=false`, manifest/receipt bindings, file hash/size/row count, and at least two expirations (`tools/schwab_chain_manifest.py:139-247`). This confirms package identity only, not that all quotes are fresh or decision-ready.
- **Verified — raw/adjusted close semantics and same-day handling are explicit.** The closes store separates raw strike-aligned closes from split-continuous signal values (`data/underlying_closes.py:44-99`), drops same-day partial rows (`108-113`), and the guarded Yahoo refresh restores historical changes/deletions instead of silently accepting them (`data/recent_topup.py:107-237`).

## Findings

### D3-1 — High: the irreplaceable-data guard currently does not protect existing Schwab packages

**Verified.** `DEFAULT_NAMESPACES` correctly includes `.cache/schwab_chains` and `reports/schwab_chains` (`tools/irreplaceable_data_guard.py:51-63`), but the committed inventory records both as `present: false`, zero files, zero bytes (`data/irreplaceable_data_inventory.json:23-26,38-41`). `verify()` deliberately skips every namespace whose recorded `present` is false (`tools/irreplaceable_data_guard.py:147-150`). Therefore the supplied `irreplaceable_data_guard verify: OK` cannot detect deletion or shrinkage of the currently existing Schwab artifacts.

**Current evidence/counterevidence.** Canonical cache metadata showed 60 Schwab parquet files (four 15-name sessions), and this worktree contains eight corresponding tracked manifests/receipts. The four packages independently hash-verified as noted above, so this is not an observed loss. It is a retention-control blind spot: deleting the 60 files and receipts after this audit would still be invisible to the existing inventory record.

**Plan only.** After preserving the current ops bytes and under normal owner-approved artifact maintenance, regenerate the inventory from the canonical root (prefer `--deep` for the Schwab namespaces), review the tracked inventory diff, and add a regression fixture: a namespace recorded absent, then populated, then removed must fail verification. Do not regenerate during this audit.

### D3-2 — Moderate: Schwab package identity does not audit per-contract quote freshness

**Verified.** Capture persists `timestamp` and `trade_timestamp` (`options_researcher/schwab_chain_capture.py:48-85,175-198`), and the adapter obtains quote timestamps (`data/schwab_adapter.py:231-274`); however `verify_session()` validates receipt-level capture time but never reads/checks those columns (`tools/schwab_chain_manifest.py:60-77,139-247`). The H7 external-package path retains column/schema, nonfinite, duplicate, negative, crossed-market, and liquidity/Greek checks, but contains no timestamp-age or same-session quote check (`options_researcher/h7_data_gate.py:302-355,484-515`). Tests cover stale *receipt* time, not stale constituent quote time (`tests/test_schwab_chain_manifest.py:112-143`; `tests/test_h7_schwab_data_gate.py:288-298`).

**Verified local sample.** The four verified packages had respectively 1,207 / 701 / 748 / 638 rows whose quote timestamp was more than 15 minutes before the receipt capture time. The 2026-08-20 package has one SMCI quote timestamp from 2026-08-19. None of these rows met the current generic selectable liquidity/delta mask; thus **no current selectable-row impact was observed**. This is nevertheless an unimplemented required check #9 from the selected data-audit standard, not proof that a selectable quote was stale.

**Plan only.** Define the owner-approved age policy for the declared H7 selection path; then reject a prior-session timestamp and BLOCK/WARN stale rows if they are selectable, preserving the current receipt/manifest checks. Add synthetic tests for same-session-old and prior-session selectable quotes. Do not infer a threshold from this audit.

### D3-3 — Moderate: current close coverage makes the 2026-08-24 Schwab package fail closed for H7, and close provenance remains weak

**Verified.** Safe canonical-cache metadata inspection found 25 underlying-close files, each deduplicated, with latest date 2026-08-21. Thus an H7 evaluation requiring the 2026-08-24 exact session would produce `CLOSE_STALE`/`CLOSE_SESSION_MISSING` rather than a GO (`options_researcher/h7_data_gate.py:116-165`); it must not be treated as a ready gate solely because the 08-24 Schwab package verifies. The provider-transition policy explicitly requires a same-instant spot for a fresh preclose section, otherwise a named reason/frozen-cache path applies (`docs/provider-transition.md:123-147`).

**Verified provenance limitation.** `store_closes()` replaces a whole symbol file after sorting/deduplicating dates (`data/underlying_closes.py:28-41`); the routine stores neither source, retrieval timestamp, response hash, nor per-file content binding. The owner-authorized guarded refresh records one descriptive aggregate `DATA_PULL` fact (`data/recent_topup.py:84-104,107-122,225-237`). It catches retroactive changes and missing historical dates, but does not create an append-only hash-bound provenance record for the new tail. Exact H7 evaluation hashes the close file at read time, which detects later mutation during a receipt flow, but does not establish acquisition provenance.

**Plan only.** Keep the existing restoration guard, but make a future close-refresh record bind provider identity, retrieval time/timezone, requested range, raw response or durable raw hash, transformed close-file hash, and per-symbol max session. Require that binding wherever a close is decision-bearing. Refreshing the 08-24 close is an external provider operation and outside this audit's authority.

### D3-4 — Capability limitation: canonical v1 historical chains are byte-bound but permanently provenance-poor

**Verified.** v1 comprises only the eleven legacy fields (`data/cache_schema.py:43-77`) and is classified display-only when v2 provenance fields are absent (`data/cache_schema.py:315-337`). The provider-transition document expressly states that v1 discards provider provenance permanently and that v2 is the only future-gate remedy (`docs/provider-transition.md:57-65`). The top-level v1 manifest proves byte identity, not provider response identity, retrieval timestamp, entitlement, raw inputs, per-row quote timestamp, or independent-source parity.

**Counterevidence / containment.** This is deliberately contained for H7: a legacy v1 partition produces `CHAIN_SCHEMA_V1_DISPLAY_ONLY` (`options_researcher/h7_data_gate.py:256-301`). The exit audit supplies a fuller fourteen-check mechanism for selected forward/v2 windows, including duplicate, sign, crossed-market, IV/Greek, expiration, and parity checks (`tools/thetadata_exit_audit.py:1204-1499`), but its presence does not retroactively add raw provenance to every v1 byte.

**Ready decision for this point:** retain the v1 corpus as reproducible historical/display evidence only; do not represent a v1-only result as independently source-provenanced or eligible for a new verdict gate.

## Coverage and limits

| Area | Status | Evidence / limit |
|---|---|---|
| Schema, units, symbols | **Verified (v1/v2/Schwab contracts)** | Required chain fields, strict ISO expirations, `P/C`, numeric/nonfinite checks; v1 lacks provider timestamps/metadata. |
| Retrieval/as-of/timezone | **Partial / Blocked** | Schwab receipt time is offset-aware and preclose-bound; per-contract quote freshness is not enforced. No provider call was authorized. |
| Missingness, duplicates, outliers | **Partial** | Static code + local timestamp summary; no exhaustive 31,366-file row scan was run in this frozen worktree. |
| Manifests/cache anchoring | **Partial** | v1 supplied verification passed; all four local Schwab packages verified; D3-1 means Schwab retention is not presently inventory-bound. |
| Raw vs transformed | **Partial** | v2 raw artifacts are hash-bound; v1 and current Yahoo closes do not preserve a comparable raw-response binding. |
| Lookahead/leakage | **Verified control / not empirically re-run** | OOS reveal gates, exact-session/no-fallback gate, and actual XNYS close cutoff exist (`data/cache_runner.py:121-141`; `data/thetadata_adapter.py:27-33`). |
| Second-source comparison | **Partial** | v2 audit can compare provider spot to independent close; v1 provenance limitation and Schwab H7 path do not establish an independent current cross-check. |

## Validation performed

- Read-only static inspection of provider policy, cache schema/provenance, manifests, H7 data gates, Schwab capture/manifest code, close refresh code, and relevant offline tests.
- Safe local metadata scan of canonical `.cache/underlying` and `.cache/schwab_chains`; no market values printed or changed.
- Offline byte verification of the four 15-name Schwab session packages; no client construction, provider request, or artifact write was intended or performed.
- No test suite was run: this is a report-only audit, and runtime test execution would not improve the stated frozen-cache provenance evidence.

## Final decision

**Not ready** for blanket data-provenance readiness. The immediate plan-only priorities are: (1) inventory-bind the existing Schwab bytes/receipts, (2) add per-contract timestamp staleness enforcement to the exact-session gate, and (3) establish append-only hash-bound close-refresh provenance before a close-dependent path is treated as current. Existing fail-closed behavior correctly prevents the stale-close case from becoming a GO.
