# Cross-session chain-consistency shadow flags — Codex brief

- **Date:** 2026-08-24
- **Author:** Claude Fable 5 orchestrating session
- **Executor:** Codex (default model, high reasoning)
- **Status:** rev 3 — two independent adversarial review rounds (Opus,
  2026-08-24). Round 1 PASS WITH FIXES (findings 1, 2, 4, 5, 6, 9, 10, 12,
  13 + minors 14–17, 20 applied in rev 2). Round 2 found rev 2's WP-0
  percentile threshold derivation self-fulfilling and corruption-blind
  (finding R1, BLOCKER) — replaced in this revision with corruption-target
  thresholds; R6–R8 and R13 also applied. Ready for hand-off; merge timing
  stays with the owner.
- **Provenance:** Repo-verified against local HEAD `24368f6` (branch
  `claude/codex-handoff-plan-2026-08-22`; five read-only agent audits +
  one adversarial review with live data measurements, 2026-08-24) unless
  labeled otherwise. Parent plan:
  `docs/plans/2026-08-24-options-validator-research-integration-plan.md` §6
  Phase 1 (WS-2), owner-approved to brief stage 2026-08-24 in-session.

## Why this exists (plain language)

The Schwab 15:45 preclose capture lane is now the repo's only source of new
options-chain data. Holes in it are permanent (2026-08-15/08-18 and 08-21 are
already unrecoverable), and a *corrupted* capture would be worse than a hole —
it would silently become load-bearing history. The existing audit stack is
strong **within** one session (crossed quotes, no-arb bounds, Greek/IV
plausibility, duplicates — `options_researcher/quote_integrity.py:92-137`,
`data/recent_topup.py:482-538` (`audit_chain`), `tools/h7_data_audit.py:271-543`;
all Repo-verified) but nothing anywhere compares one session's chain to the
previous session's. This brief adds day-over-day consistency **flags** —
shadow-mode data-quality observations, never directional signals, never gates.
Closes the WS-2 / Candidate-F-narrow finding of the 2026-08-24 plan.

## Hash-identity consequence of landing this brief (review finding 2 — read first)

Adding `data/chain_consistency.py` and `tools/chain_consistency_audit.py`
changes `diagnostic_source_hash` (`research/hashing.py:132` —
`DIAGNOSTIC_SOURCE_PATHS_V2` includes `data`, `tools`), and adding uppercase
constants to `config.py` changes `config_hash` (`research/hashing.py`,
all-uppercase-constants provenance hash). Five fail-closed H7 consumers
refuse on identity mismatch (`options_researcher/h7_watch.py:196-199`,
`h7_data_gate.py:748`, `h7_exit_session.py:247,267`, `tools/h7_data_audit.py:668`,
`research/diagnostics.py:156`). Therefore (all Repo-verified via review):

- The merge must land **outside the 07:10–15:45 ET operational window**, and
  the ops checkout must be synced to the new `origin/main` immediately after
  (the preclose wrapper refuses on HEAD-vs-origin/main mismatch — this exact
  failure mode caused the permanent 08-15→08-18 hole).
- Immediately after ops sync, run a fresh source-health → data-gate → watcher
  cycle so new receipts carry the new identity.
- The PR body must state that pre-existing sealed receipts will no longer
  re-verify at the new hash (expected, not a defect).

## Scope

**IN:** one new pure module `data/chain_consistency.py`; one new read-only CLI
`tools/chain_consistency_audit.py`; a frozen constants block in `config.py`;
receipts under `.tmp/chain_consistency/` by default; tests.

**OUT (binding):**
- No ledger/facts writes, no registration, no authority flips, no live-order
  paths, no changes to frozen values, no paper-book access.
- **No gating or refusal authority anywhere.** The capture wrapper's existing
  alignment guard remains the only mechanism that may refuse a capture. Flags
  are observations; nothing reads them to admit/deny/skip anything.
- **No legacy-cache mode.** Rev 1 proposed a `--root chains` backfill mode
  over `.cache/chains/`; review finding 1 (BLOCKER) established that
  `.cache/chains/` holds 15,766 files dated past `IN_SAMPLE_END = 2022-12-31`
  (`config.py:78`) — the sealed OOS holdout — and a naive parquet read
  bypasses the reveal gate. The mode is **deleted**, not clamped. This tool
  reads `.cache/schwab_chains/` only.
- **No changes to `tools/job_health_digest.py`** — that file is owned by brief
  21 rev 2's queued hardenings; wiring the digest to read these receipts is a
  later owner-sequenced step.
- No dashboard changes; no imports of this module from any
  `options_researcher/` scoring/rendering path.
- Do **not** import `data.cache_runner` (it pulls grpc + the ThetaData
  adapter at module level — brief 21's verbatim prohibition, Repo-verified).
- No network (OD-4, `.cursorrules:93,113,128`); no writes outside
  `.tmp/` (and the opt-in reports dir, WP-C); no `.cache` byte touched.
- Not a scheduler; no LaunchAgent changes. Flags are never signals: no
  directional language anywhere in output.

## Work packages

**WP-0 — Threshold selection by corruption target (do this FIRST; review
rounds 1 + 2 — read the history, it is load-bearing).**
Round-1 review measured rev 1's hand-picked `IV_JUMP = 0.15` flooding (2.7%
of yesterday-admitted contracts on the clean 08-19→08-20 pair; 9.2% of the
full chain). Rev 2 replaced it with "freeze at p99.5 of the measured clean
distribution" — round-2 review proved that **worse** (finding R1, BLOCKER):
the derived value comes out ≈1.15, which (a) misses a realistic corruption —
an IV doubling at the review-measured median admitted IV ≈0.43 gives
|Δiv| ≈ 0.43, well under 1.15 — and (b) still flags ~0.5% of every clean
session **by definition** (a percentile of clean data is not a falsifiable
prediction about clean data). Binding replacement — thresholds are set by
the smallest corruption the flag must CATCH, never by the clean
distribution:

- `IV_JUMP` and `DELTA_JUMP` evaluate **only contracts that passed
  `data.chain_policy.passes_liquidity` yesterday** (aligning them with
  `STRIKE_VANISHED`/`SPREAD_BLOWOUT`; junk deep-ITM/far-OTM rows — Schwab
  `iv` max observed 26.46 — drive the unstable tail).
- `CONSISTENCY_IV_JUMP_ABS = 0.40` — Assumption (corruption target): must
  catch an IV doubling at the median admitted IV (review-measured ≈0.43);
  set just below it.
- `CONSISTENCY_DELTA_JUMP_ABS = 0.30` — Assumption (corruption target): must
  catch delta sign flips and gross greek corruption. Round 1's observation
  that this "fired once in 24,850 pairs" is the **desired** behavior for a
  corruption flag (near-zero clean rate), not a defect — that framing only
  looked wrong under the abandoned percentile logic.
- **Measurement duty (not fitting):** measure each flag's clean-pair rate at
  these frozen values on **adjacent-session pairs only** — the same
  `calendar_sessions` adjacency test `GAP_SESSION` uses; the 08-14→08-19
  gap pair is excluded from measurement (identifying it is `GAP_SESSION`'s
  job, not a fitting input). Evaluate on yesterday-admitted contracts under
  the small-move condition. Record the per-pair table in the PR body and in
  the `config.py` provenance comment.
- **Pre-declared kill criterion (falsifiable):** if `IV_JUMP`'s measured
  clean-pair rate exceeds **1% of evaluated contracts** at 0.40, the honest
  conclusion is that |Δiv| on this data is too unstable to serve as a
  corruption signal — **drop the flag in the same PR with the measurement
  recorded**; do not widen the threshold. Same rule for `DELTA_JUMP`
  (expected ≈0). After freezing, thresholds may not be adjusted in response
  to later flag volume without a recorded decision (removal is the
  sanctioned response to noise — see Acceptance).

**WP-A — Pure comparison module `data/chain_consistency.py`.**
No file/network I/O in this module (mirror `data/chain_policy.py`'s shape).
The exchange calendar is **constructed by the CLI, not this module**, and
passed in via `calendar_sessions` (review finding 5). Public surface:

```python
def audit_pair(prev_chain, cur_chain, prev_close, cur_close,
               *, prev_session, cur_session, calendar_sessions) -> ConsistencyReport
```

`ConsistencyReport` is a frozen dataclass: per-flag lists of affected
contracts (bounded per flag by `CONSISTENCY_MAX_EXAMPLES`), per-flag counts,
an overall `status` chosen by fixed precedence (worst wins; precedence style
mirrors `options_researcher/oi_change.py:80-106`), and the max as-of session
of every input. Flags, in precedence order:

1. `GAP_SESSION` — `prev_session` is not the immediately preceding trading
   session per `calendar_sessions`. A gap is reported, never "repaired".
2. `EXPIRY_VANISHED` — an expiration present yesterday with ≥1
   yesterday-admitted contract is absent today although its expiration date
   is ≥ `cur_session`.
3. `STRIKE_VANISHED` — same test at (expiration, strike, right) granularity,
   restricted to yesterday-admitted contracts.
4. `IV_JUMP` — |Δiv| on a yesterday-admitted contract exceeds
   `CONSISTENCY_IV_JUMP_ABS` while the underlying's absolute return is below
   `CONSISTENCY_UNDERLYING_SMALL_MOVE`.
5. `DELTA_JUMP` — |Δdelta| on a yesterday-admitted, unexpired contract
   exceeds `CONSISTENCY_DELTA_JUMP_ABS` under the same condition.
6. `SPREAD_BLOWOUT` — a yesterday-admitted contract whose spread fraction
   `(ask-bid)/mid` at least doubles (`CONSISTENCY_SPREAD_BLOWOUT_MIN_RATIO`)
   AND exceeds `config.MAX_SPREAD_PCT` (`config.py:125`; reference, do not
   restate).
7. `OK`.

Rules: match on (expiration, strike, right); contracts absent *yesterday* are
new listings, never flagged; expired contracts excluded. Admission uses
`data.chain_policy.passes_liquidity` (`data/chain_policy.py:48-57`;
Repo-verified — note line range corrected from rev 1; the vectorized
equivalent `_liquid_mask` at `data/recent_topup.py:469-480` implements the
same predicate frame-wise and may be referenced for bulk work). Input schemas
(Repo-verified, all three enumerated per review finding 20):

- legacy `.cache/chains`: `expiration, strike, right, bid, ask,
  open_interest, iv, delta, gamma, theta, vega` (NOT an input to this tool —
  listed only so `NOT_EVALUABLE` logic is written against explicit schemas);
- `.cache/schwab_chains`: the above plus `contract_symbol, multiplier,
  non_standard, mini, timestamp, trade_timestamp`;
- `.cache/chains_v2`: the legacy set plus `timestamp, bid_size,
  bid_condition, ask_size, ask_condition, iv_error, underlying_timestamp,
  underlying_price, thetadata_client_version` (also not an input here).

A column required by a flag but missing from an input → that flag reports
`NOT_EVALUABLE` for the pair, never a silent skip (fail-visible).

**Explicitly out of WP-A:** open-interest deltas — the OI Δ1d context line
owns that surface (`options_researcher/oi_change.py`, shipped `b78d1c7`; the
previously circulated hash `2864008` is wrong).

**WP-B — Constants block in `config.py`.**
Follow the experiment-lane provenance style (`config.py:838-842`). Label:
`Chain-consistency shadow flags 2026-08-24; jump thresholds are
corruption-target Assumptions per brief 22 WP-0 (set by the smallest
corruption the flag must catch; clean-pair rates measured and recorded in
the PR), LLM-proposed, not owner-typed; display-only — bind no hypothesis,
verdict, gate, or trigger.` Constants: `CONSISTENCY_IV_JUMP_ABS = 0.40`,
`CONSISTENCY_DELTA_JUMP_ABS = 0.30` (WP-0 rationale),
`CONSISTENCY_UNDERLYING_SMALL_MOVE = 0.01` (Assumption: conditioning
threshold for "underlying near-flat"),
`CONSISTENCY_SPREAD_BLOWOUT_MIN_RATIO = 2.0` (Assumption),
`CONSISTENCY_MAX_EXAMPLES = 20` (ergonomics).

**WP-C — CLI `tools/chain_consistency_audit.py`.**
Read-only. Calendar: call `mcal.get_calendar("XNYS")` directly
(`pandas-market-calendars` 5.4.0 is already locked; review finding 5) — do
not import `data.cache_runner`. Underlying closes: use
`data.underlying_closes.load_closes(symbol, start, end, allow_oos=True)` —
**raw** closes (correct for strike/spot math per
`data/underlying_closes.py:48-52`). Note (review finding 4, binding wording):
`allow_oos=True` here is the closes cache's soft in-sample gate
(`data/underlying_closes.py:44-55` raises `OOSDataTouchError` for any
end date past 2022-12-31 without it); it is NOT the ledger reveal path
(`research/experiments.reveal_oos`) and charges nothing against the 0/3
reveal budget — no `reveal_oos` call occurs anywhere in this tool.

Modes:
- default: for each symbol in `.cache/schwab_chains/`, audit the **most
  recent available pair** — NOT "most recent consecutive" (review finding 10:
  a consecutive-only default can never fire `GAP_SESSION`, and the one real
  current gap, 08-14→08-19, is exactly what it would exclude). A symbol with
  fewer than 2 sessions reports `INSUFFICIENT_HISTORY` for that symbol.
- `--pair PREV CUR`: audit an explicit session pair.

Output: one JSON receipt per run, default under `.tmp/chain_consistency/`
(review finding 12; brief-21 precedent — `.gitignore` covers `.tmp/` only);
`--out-dir reports/chain_consistency/` is opt-in for a deliberately committed
artifact. Receipts use `research/receipts.py` (`make_receipt` /
`write_immutable_receipt`; Repo-verified). Two receipt facts the executor
must handle (review findings 14, 15):
- Receipts are content-addressed and carry **no wall-clock field**
  (`make_receipt` docstring, `research/receipts.py:58` — "no wall-clock
  field is inferred"); do not add one. Determinism is therefore
  unconditional: same inputs → identical payload.
- The module hardcodes `"receipt_schema": "h7-receipt/v1"` (`:60`) and
  "H7"-worded error strings (`:86`, `:98`) — a known misnomer for non-H7
  artifacts. The payload must carry `receipt_type:
  "chain_consistency_audit"`, and tests must load with an expected-type
  check.
- `write_immutable_receipt` raises `FileExistsError` on non-identical
  rewrite (`research/receipts.py:109,137`): a re-run of the same session after
  any code/threshold change must therefore write under a new filename (embed
  a short payload-hash prefix in the name); tests always write to a
  `TemporaryDirectory`.

Receipt content: per-symbol pair audited, per-flag counts + bounded
examples, `NOT_EVALUABLE`/`INSUFFICIENT_HISTORY` markers, max as-of session,
constants used (with their WP-0 derivation values), and the git SHA of the
producing code. Exit code: `0` when the audit ran to completion regardless of
flags (receipts, not exit codes, carry health truth — brief 21's rationale);
non-zero only on tool failure.

**WP-D — Tests (offline, `unittest`, no network).**
1. One fixture pair per flag, red→green.
2. Injected-corruption battery: corrupt one field per case (IV spike, delta
   flip, vanished strike, doubled spread) on a real-shaped fixture; assert
   exactly the intended flag fires.
3. Precedence (worst-wins) test.
4. `NOT_EVALUABLE` on a missing column is visible in the receipt (both
   directions: present → evaluated; absent → labeled).
5. Determinism: same inputs → byte-identical receipt payload, unconditional
   (no wall-clock field exists).
6. New-listing non-flag; expired-contract exclusion.
7. **Behavioral no-network test** (review finding 9 — rev 1's import-graph
   assertion was vacuous because `data/underlying_closes.py:19` imports
   `data.thetadata_adapter` at module level): deny sockets at the socket
   layer for a full CLI run over fixtures and assert zero attempts; plus
   `unittest.mock` call-count assertions of zero on `fetch_underlying_eod*`,
   `get_eod_chain`, and `blind_cache_chain`.
8. No `research.experiments` import (review finding 4).
9. Default pair selection over a fixture with a session hole yields
   `GAP_SESSION`; a one-session symbol yields `INSUFFICIENT_HISTORY`.
10. CLI exit-code semantics (0 with flags present; non-zero on unreadable
    input). All receipt-writing tests use `TemporaryDirectory`.

## Acceptance / verification

Exit codes define done:

```
uv run python -m unittest discover -s tests
uv run ruff check .
uv run pyright
```

Plus (review finding 13, mandatory):
- **False-positive review section in the PR body:** per-flag hit counts
  across EVERY available Schwab pair, with each name's underlying return for
  the pair. Whatever it shows is the honest result — a flagged real pair is a
  finding, not a test failure.
- **Measured clean-pair rates (review finding R13 — replaces rev 2's
  circular "≈0.5% ceiling"):** report each flag's measured rate at the WP-0
  corruption-target thresholds on every adjacent clean pair. Expected: ≈0
  for structural flags and `DELTA_JUMP`; below the 1% kill criterion for
  `IV_JUMP`. Exceeding the kill criterion drops the flag per WP-0 — never
  widens the threshold.
- **Removal criterion and rollback path, stated in the PR:** if flags become
  noise nobody reads, the sanctioned response is removal, not
  tuning-to-silence (parent plan §10 item 6). Rollback = delete the two new
  files, revert the `config.py` block, ops-sync, and run a fresh
  source-health → data-gate cycle to restore hash identity.
- PR body states the hash-identity consequence (section above) and includes
  grep evidence that no production module imports the new code.

Merge timing stays with the owner (standing policy).

## Post-implementation addendum — SPREAD_BLOWOUT disposition (owner-ruled 2026-08-24)

Implemented as PR #72 (merged `aed7af0`; fix round `7a97e82` applied all
independent-review findings). WP-0's kill criterion fired for real: IV_JUMP
measured 1.5213% (131/8,611) > 1% on the only adjacent clean pair and was
removed, not widened. SPREAD_BLOWOUT measured 2.2124% (256/11,571) and
saturated the headline `status` (15/15 symbols on a clean day).

**Owner disposition A (in-session, 2026-08-24, wording "go with option A"):**
SPREAD_BLOWOUT stays computed, counted, and receipted, but is demoted from
the worst-wins headline status (`data.chain_consistency.HEADLINE_DEMOTED_FLAGS`);
receipts carry a `headline_demoted_flags` marker. Threshold unchanged —
widening remains forbidden. **Pre-declared review:** if no SPREAD_BLOWOUT
observation has been acted on after ~30 captured sessions, remove the flag
per parent plan §10 item 6 rather than tune it.
