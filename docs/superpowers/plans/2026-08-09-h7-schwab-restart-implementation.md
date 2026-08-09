# H7 Schwab Restart Machinery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the offline-tested, fail-closed Schwab preclose-chain capture, manifest, registration, and feasibility machinery for the unregistered `h7-forward-schwab-v1` namespace without activating H7 or changing its decision rules.

**Architecture:** A new capture module consumes only the existing read-only Schwab option-chain endpoint, writes exact-session Parquets under `.cache/schwab_chains`, and binds every file into a per-session manifest plus immutable receipt. A Schwab-specific H7 gate validates that package before reusing the existing H7 row-integrity checks. A sibling registration builder freezes the unchanged scoring block, Schwab provenance, session convention, and a hash-bound feasibility receipt into a new empty ledger namespace; all real appends remain behind an uninvoked owner gate.

**Tech Stack:** Python 3.12, pandas/pyarrow, `unittest`, existing `schwab-py` adapter, repository canonical hashing/atomic-I/O helpers, zsh, macOS LaunchAgent templates.

## Global Constraints

- Never write to `ledger/h7_forward/events.jsonl` or `ledger/h7_forward/HEAD`.
- Never write a Schwab response under `.cache/chains/`.
- Keep `h7_active=False`, `exact_session_source_active=False`, and `THETADATA_ACQUISITION_DISABLED=True`.
- Use only offline synthetic fixtures in tests; no Schwab, ThetaData, or other network calls.
- The official session-chain convention is exactly `preclose_snapshot_v1`.
- The new namespace id is exactly `h7-forward-schwab-v1`; the cache path is exactly `.cache/schwab_chains`.
- Preserve `MIN_LOSSES_FOR_VERDICT=10` and every existing H7 strategy, cost, and scoring identity.
- Every numeric proposal in the owner packet is labeled `LLM/tool-computed`; no acceptance threshold or authority value is frozen here.
- Registration, OD-3 wording, starvation acceptance/redesign, authority flips, LaunchAgent loading, and merges remain owner-only.

---

### Task 1: Read-only full-chain adapter seam

**Files:**
- Modify: `data/schwab_adapter.py`
- Modify: `tests/test_schwab_adapter.py`

**Interfaces:**
- Consumes: existing `SchwabMarketData.api.get_option_chain()` and `_response_json()`.
- Produces: `SchwabMarketData.option_full_chain(symbol: str) -> pd.DataFrame` with the complete provider response normalized once.

- [ ] **Step 1: Write failing adapter tests.** Add a two-expiration synthetic response and assert one call to `get_option_chain`, both rights, both expirations, exact H7 columns, decimal IV, NaN preservation, SUCCESS/not-delayed/not-truncated enforcement, provider contract-count equality, and no account/order surface.
- [ ] **Step 2: Verify RED.** Run `uv run python -m unittest tests.test_schwab_adapter.SchwabMarketDataTests.test_full_chain_returns_every_expiration_with_h7_columns -v`; expect `AttributeError: 'SchwabMarketData' object has no attribute 'option_full_chain'`.
- [ ] **Step 3: Implement the minimal seam.** Extract the existing response normalization into `_parse_chain_payload(symbol, payload, expected_expiration=None)`, retain all current per-expiration checks, and add `option_full_chain()` using `contract_type=ALL`, `include_underlying_quote=False`, and the existing entitlement argument without `from_date`/`to_date`.
- [ ] **Step 4: Verify GREEN and compatibility.** Run `uv run python -m unittest tests.test_schwab_adapter -v`; require all tests to pass and `get_option_chain` to remain the only chain endpoint.
- [ ] **Step 5: Commit.** Commit only the adapter and adapter tests as `feat(schwab): expose read-only full option chain`.

### Task 2: Per-session manifest and verifier

**Files:**
- Create: `tools/schwab_chain_manifest.py`
- Create: `tests/test_schwab_chain_manifest.py`

**Interfaces:**
- Consumes: files named `{SYMBOL}_{YYYY-MM-DD}.parquet` and a capture receipt.
- Produces: `build_manifest(session, symbols, chain_dir) -> dict`, `write_manifest(manifest, path) -> Path`, and `verify_session(session, symbols, chain_dir, manifest_path, receipt_path) -> dict`.

- [ ] **Step 1: Write failing manifest tests.** Synthetic Parquets must prove exact file-set closure, SHA-256 and size binding, receipt/manifest session equality, exact universe equality, `preclose_snapshot_v1`, at least two distinct expirations per successful symbol, and receipt-to-file hash equality.
- [ ] **Step 2: Verify RED.** Run `uv run python -m unittest tests.test_schwab_chain_manifest -v`; expect an import failure for `tools.schwab_chain_manifest`.
- [ ] **Step 3: Implement deterministic manifest construction.** Emit schema `schwab-chain-manifest/v1`, sorted symbols/files, repo-relative paths, byte sizes, hashes, session, convention, provider `schwab`, and a canonical `manifest_hash` computed without the hash field.
- [ ] **Step 4: Implement fail-closed verification.** Refuse missing/prior-day files, extra or missing universe names, stale receipt dates, single-expiration files, receipt failures, manifest/receipt hash disagreement, and byte drift. Return verified bindings only after all names pass.
- [ ] **Step 5: Prove tamper refusal.** Run the focused tamper test after changing one fixture byte; require both the manifest verifier and its receipt-binding path to raise `SchwabChainManifestError`.
- [ ] **Step 6: Commit.** Commit as `feat(h7): add Schwab chain session manifest`.

### Task 3: Durable preclose capture

**Files:**
- Create: `options_researcher/schwab_chain_capture.py`
- Create: `tests/test_schwab_chain_capture.py`
- Modify: `data/irreplaceable_data_inventory.json`
- Modify: `tools/irreplaceable_data_guard.py`

**Interfaces:**
- Consumes: injected `SchwabMarketData`, `h7_scope.watch_universe()`, `option_full_chain()`, and Task 2 manifest functions.
- Produces: `capture(*, client, now_ny, chain_dir, reports_dir, force=False) -> tuple[int, dict]` and CLI `python -m options_researcher.schwab_chain_capture`.

- [ ] **Step 1: Write failing capture tests.** Cover exact 15-name scope, 15 distinct files, required H7 columns, explicit NaN for sparse required fields, per-name failure records, single-expiration refusal, write-once receipt conflicts, and a sentinel proving no default client is constructed on an invalid time or dry-run refusal path.
- [ ] **Step 2: Verify RED.** Run `uv run python -m unittest tests.test_schwab_chain_capture -v`; expect an import failure.
- [ ] **Step 3: Implement normalization and atomic writes.** Reindex to `expiration,strike,right,bid,ask,open_interest,iv,delta,gamma,theta,vega`, rename adapter `implied_vol` to `iv`, preserve NaN, require both rights and at least two expirations, and use `data.atomic_io.atomic_parquet_write`.
- [ ] **Step 4: Implement the receipt.** Write `reports/schwab_chains/{session}/preclose.json` with attempted universe, each status/row/expiration count/hash/size, `captured_at_et`, `captured_at_utc`, config hash, code SHA, provider identity, convention, manifest path/hash, and overall failure when any name fails.
- [ ] **Step 5: Keep failed packages non-authoritative.** Always write the failure receipt when capture begins, but do not report success and do not emit a passing manifest unless every official-scope name passes.
- [ ] **Step 6: Extend irreplaceable inventory coverage.** Add `.cache/schwab_chains` to `DEFAULT_NAMESPACES`; leave it recorded absent until actual canary bytes exist, and test that generated inventories include the namespace.
- [ ] **Step 7: Verify GREEN.** Run `uv run python -m unittest tests.test_schwab_chain_capture tests.test_schwab_chain_manifest tests.test_irreplaceable_data_guard -v`.
- [ ] **Step 8: Commit.** Commit as `feat(h7): capture durable Schwab preclose chains`.

### Task 4: Schwab package data gate

**Files:**
- Create: `options_researcher/h7_schwab_data_gate.py`
- Create: `tests/test_h7_schwab_data_gate.py`
- Modify: `options_researcher/h7_data_gate.py`
- Modify: `tests/test_h7_data_gate.py`

**Interfaces:**
- Consumes: Task 2 `verify_session()` and existing `h7_data_gate._evaluate()` with an injected receipt validator.
- Produces: `evaluate(requested_run_date, *, close_dir, chain_dir, manifest_path, receipt_path, scope=None) -> dict` with evidence mode `REAL-H7-SCHWAB-PRECLOSE-AUDIT`.

- [ ] **Step 1: Write four failing gate tests.** Missing exact-session file, stale receipt, 14/15 capture or one-expiration smuggling, and tampered Parquet must each return/refuse without any fallback to `.cache/intraday`, an earlier day, or a client constructor.
- [ ] **Step 2: Verify RED.** Run `uv run python -m unittest tests.test_h7_schwab_data_gate -v`; expect an import failure.
- [ ] **Step 3: Implement the validator adapter.** Verify the whole package once, then supply a per-symbol binding callable matching `_evaluate_chain`'s `(chain_dir, path, symbol, session, consumer_scope)` contract. The callable must return manifest/receipt hashes and refuse any mismatch.
- [ ] **Step 4: Reuse existing integrity checks without schema spoofing.** Call the existing pure evaluator through a provider-neutral seam; record Schwab provenance explicitly rather than classifying the files as ThetaData schema v2.
- [ ] **Step 5: Verify GREEN and zero calls.** Run `uv run python -m unittest tests.test_h7_schwab_data_gate tests.test_h7_data_gate tests.test_provider_disabled -v`; require the sentinel client construction count to remain zero.
- [ ] **Step 6: Commit.** Commit as `feat(h7): gate Schwab exact-session packages`.

### Task 5: Separate preclose scheduling template

**Files:**
- Create: `tools/schwab_chain_capture.sh`
- Create: `tools/launchd/com.carsyn.options-validator.schwab-chain-preclose.plist`
- Create: `tests/test_schwab_chain_schedule.py`

**Interfaces:**
- Consumes: Task 3 CLI in `/Users/carsynstephenson/options-validator-ops` after owner merge.
- Produces: an independently scheduled weekday 15:45 ET invocation with separate stdout/stderr and no dependency on `tools/intraday_capture.sh`.

- [ ] **Step 1: Write failing schedule tests.** Parse the plist and assert label/path, weekday 15:45 entries, separate log names, and an argument list containing only the Schwab capture wrapper.
- [ ] **Step 2: Verify RED.** Run `uv run python -m unittest tests.test_schwab_chain_schedule -v`; expect missing template failure.
- [ ] **Step 3: Implement wrapper and plist.** The wrapper must enforce ops `main==origin/main`, `SCHWAB_TRADING_ENABLED` not truthy, explicit `LIVE_MARKET_DATA_PROVIDER=schwab`, and invoke only `uv run python -m options_researcher.schwab_chain_capture`.
- [ ] **Step 4: Validate without loading.** Run `plutil -lint tools/launchd/com.carsyn.options-validator.schwab-chain-preclose.plist` and the focused test. Do not copy or bootstrap the plist.
- [ ] **Step 5: Commit.** Commit as `ops(h7): add isolated Schwab preclose schedule`.

### Task 6: Schwab registration builder and empty namespace

**Files:**
- Create: `options_researcher/h7_schwab_window_registration.py`
- Create: `tests/test_h7_schwab_window_registration.py`
- Create: `ledger/h7_forward_schwab/README.md`
- Modify: `.agents/hooks/block_ledger_edits.py`
- Modify: `.agents/hooks/README.md`
- Modify: `tests/test_block_ledger_edits.py`

**Interfaces:**
- Consumes: unchanged H7 scoring identity, Task 4 evidence binding, Task 7 feasibility receipt, and generic `h7_event_ledger` with explicit `base_dir`.
- Produces: `build_window_registration_event(owner, evidence, feasibility, universe_manifest=None) -> dict` and synthetic-only `register_window(..., base_dir) -> AppendResult`.

- [ ] **Step 1: Record old-store hashes.** Run `shasum -a 256 ledger/h7_forward/events.jsonl ledger/h7_forward/HEAD` and save the output outside the repository for the before/after comparison.
- [ ] **Step 2: Write failing builder tests.** Refuse each missing owner field, short capture coverage, wrong convention, tampered feasibility payload/hash, non-empty target store, and changed frozen scoring identity; prove a synthetic first append verifies at seq 0.
- [ ] **Step 3: Verify RED.** Run `uv run python -m unittest tests.test_h7_schwab_window_registration -v`; expect an import failure.
- [ ] **Step 4: Implement exact owner/evidence fields.** Require authorization/start/count/acks plus `SCHWAB_CAPTURE_LANE_VERIFIED_THROUGH`, `SCHWAB_CONFIRMATION_EVIDENCE`, and `SESSION_CHAIN_CONVENTION=preclose_snapshot_v1`; bind provider, namespace, historical edge, manifest/receipt hashes, scope, source health, feasibility hash, window arithmetic, unchanged costs/config/scorer, and `min_losses_for_verdict: 10`.
- [ ] **Step 5: Add only an empty tracked store.** `ledger/h7_forward_schwab/README.md` documents VALID-EMPTY and the typed API. Do not create `events.jsonl` or `HEAD`.
- [ ] **Step 6: Extend hook coverage test-first.** Prove edits/removals/touches of `ledger/h7_forward_schwab/{events.jsonl,HEAD}` are blocked while its README remains editable, then minimally extend the regex and help text.
- [ ] **Step 7: Verify GREEN.** Run `uv run python -m unittest tests.test_h7_schwab_window_registration tests.test_h7_event_ledger tests.test_block_ledger_edits -v`.
- [ ] **Step 8: Commit.** Commit as `feat(h7): add Schwab registration namespace`.

### Task 7: Fresh full-stack feasibility receipt

**Files:**
- Create: `tools/h7_schwab_feasibility.py`
- Create: `tests/test_h7_schwab_feasibility.py`
- Create at runtime: `reports/h7_forward_schwab/2026-08-09-feasibility.json`

**Interfaces:**
- Consumes: cached history only, official H7 scope, and the existing frozen entry-stack functions.
- Produces: `compute(*, lookback_start, lookback_end, window_sessions, chain_dir, close_dir) -> dict` and a canonical receipt with `receipt_hash`.

- [ ] **Step 1: Write failing arithmetic and no-network tests.** Hand-derived fixture counts must assert `base_rate=passes/symbol_days` and `expected_entries=base_rate*window_sessions*universe_size`; a sentinel must fail if any provider/client constructor runs.
- [ ] **Step 2: Verify RED.** Run `uv run python -m unittest tests.test_h7_schwab_feasibility -v`; expect an import failure.
- [ ] **Step 3: Implement one declared stack.** Reuse the existing H7 arming, earnings/eligibility, liquidity, routing, and cap predicates without searching alternate parameters. Count every symbol-session denominator and complete-stack pass.
- [ ] **Step 4: Emit provenance, not a decision.** Record lookback, sessions, symbols, pass count, denominator, base rate, declared window sessions, expected entries, stack/version hashes, code SHA, cache max-as-of, `min_losses_for_verdict=10`, and label `LLM/tool-computed`; include no pass/fail or starvation acceptance field.
- [ ] **Step 5: Run the cached computation once.** Write the permanent receipt under `reports/h7_forward_schwab/`, then independently recompute its arithmetic from recorded counts.
- [ ] **Step 6: Commit.** Commit tool, tests, and receipt as `analysis(h7): measure Schwab-window feasibility`.

### Task 8: Verification, owner packet, and reversible authority patch

**Files:**
- Create: `reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md`
- Create: `reports/h7_forward_schwab/2026-08-09-session-note.md`
- Create outside Git: `/private/tmp/h7-forward-schwab-authority-flip.patch`

**Interfaces:**
- Consumes: all prior task evidence and Task 7 computed number.
- Produces: a DRAFT packet, session note, and uncommitted patch; no registration or activation.

- [ ] **Step 1: Verify old-store immutability.** Re-run SHA-256 and `uv run python -m options_researcher.h7_event_ledger verify`; require byte-identical hashes and `VALID records=1`.
- [ ] **Step 2: Run complete validation.** Run frozen sync, full unittest discovery, Ruff, Pyright, irreplaceable-data guard, plist lint, focused sentinel dry-run refusal, and Schwab manifest tamper verification.
- [ ] **Step 3: Perform backup/restore only when real canary bytes exist.** If `.cache/schwab_chains` has no verified live session, record `BLOCKED_PENDING_MONDAY_CANARY` rather than manufacturing data. Once present, snapshot `.cache/schwab_chains` plus `ledger/h7_forward_schwab`, restore to a fresh `mktemp -d`, and byte-compare.
- [ ] **Step 4: Draft the owner packet.** Label it DRAFT; fill the namespace and computed feasibility number, show an untyped OD-3 template, and leave the operative starvation choice explicitly owner-only.
- [ ] **Step 5: Prepare but do not apply the patch.** Copy the two tracked files into a fresh `/private/tmp` directory, edit only those temporary copies, and generate a no-index patch saved as `/private/tmp/h7-forward-schwab-authority-flip.patch`. Never modify the working-tree copies. The patch remains unusable until owner authorization after the Monday canary and registration.
- [ ] **Step 6: Commit and push.** Commit only code/tests/docs/receipts on `feat/h7-forward-schwab-v1`, push the branch, and do not merge.
- [ ] **Step 7: Request independent adversarial review externally.** Hand the pushed SHA to the orchestrating Claude session with the prompt `show me how this could be lying`; record `PENDING_EXTERNAL_REVIEW` until its evidence is returned.

## Self-review result

- Spec coverage: WP3 capture/gate/scheduling, WP4 registration/feasibility/old-store proof, and WP5 packet/backup/review are mapped to Tasks 1-8.
- Boundary coverage: no task invokes a provider, registers a window, flips authority, loads a LaunchAgent, edits the old store, or merges.
- Type consistency: manifest and receipt hashes flow Task 2 -> Task 4 -> Task 6; feasibility receipt/hash flows Task 7 -> Task 6/8.
- Monday dependency: backup/restore of real Schwab bytes and external adversarial review are explicitly reported as pending rather than fabricated on Sunday.
