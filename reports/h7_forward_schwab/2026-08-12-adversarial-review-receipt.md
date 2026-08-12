# H7 Schwab lane — independent adversarial review (gate-packet prerequisite #4)

**Date:** 2026-08-12
**Reviewer:** Claude Opus, acting as an independent read-only adversarial reviewer. I am not one of the implementing sessions and have no prior stake in this code.
**Scope:** `feat/h7-forward-schwab-v1` as merged (`1866f59`) plus `2d68a8c`, `64635c2`, `6a38040`, `d77f995`, reviewed **at HEAD `57fcf90`** (== `origin/main`).
**Satisfies:** audit finding M5 (`reports/repo-audits/2026-08-11-three-day-state-audit.md`) and prerequisite #4 of 6 in `reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md`.
**Repo state:** `git status` clean before and after. I wrote nothing to the repository; all probes ran on synthetic data in scratch.
**Provenance note (added by the orchestrating session at commit time):** this file is the reviewer's final text committed verbatim; only this note was added.

## VERDICT: PASS WITH FIXES

**The merge stands — do not revert.** The lane is genuinely inert, its fail-closed machinery is real, and reverting would destroy the audit trail and the gate packet for no safety gain.

**Registration and the authority flip must NOT proceed** until B1–B4 below are closed. Three of the four are cheap; B4 is a disclosure the owner is entitled to before typing a starvation pre-acceptance.

---

## Blocking findings

### B1 — The one-door AST tripwire does not watch the new Schwab store

`tests/test_h7_one_door.py:108-113` — `_is_real_store_ref` matches only the identifier `REAL_FORWARD_STORE`. Consequently `_appends_to_real_store` (`:146-183`) is blind to a module that appends to `SCHWAB_FORWARD_STORE`, and `_real_store_constructor_functions` (`:86-105`) only flags functions that *also* call `Path`.

I reconstructed the evasions rather than assuming. Scratch probe results against the test's own scanner functions:

| Candidate second door | `_appends_to_real_store` | `_real_store_constructor_functions` |
|---|---|---|
| `append_event(e, base_dir=SCHWAB_FORWARD_STORE, expected_head=None)` | **False** | **[]** |
| `def f(base=SCHWAB_FORWARD_STORE): append_event(e, base_dir=base, ...)` | **False** | **[]** |
| `append_event(e, base_dir=Path("ledger/h7_forward_schwab"), ...)` | False | `['quietly_register']` (caught, incidentally) |
| *control:* `base_dir=REAL_FORWARD_STORE` | True | [] (caught, by design) |

The first two reach the real Schwab store and are invisible to both scanners. There is no runtime backstop: `h7_event_ledger.append_event` (`:356-400`) appends to whatever `base_dir` it is handed and has no store-identity guard, and the VALID-EMPTY re-verify that protects registration lives *inside* `register_window_real` (`h7_schwab_window_registration.py:392-396`) — a second door never calls it. A seq-0 registration created this way would bypass every owner gate: guard report, code identity, spec hash, gate recheck.

Present exposure is zero — `SCHWAB_FORWARD_STORE` is referenced only at `h7_schwab_window_registration.py:34` and `:297`, and `.agents/hooks/block_ledger_edits.py:31` does block agent *file* writes to `h7_forward_schwab/{events.jsonl,HEAD}` (33/33 tests green). But the tripwire whose job is to keep that exposure at zero is not watching this store. This matters most **after** registration, when the VALID-EMPTY backstop is gone and the AST scan is the only source-level guard left.

**Fix:** parameterize `_is_real_store_ref` over both store constants and assert the scan per namespace. Small change; restores the property the test's own docstring claims.

### B2 — The Schwab gate cannot produce the evidence the registration door demands, and the door cannot tell

Two independent hard refusals block a Schwab gate result from ever becoming a durable receipt:

- `h7_data_gate.py:589-590` — `build_receipt` raises unless `evidence_mode == "REAL-H7-FULL-AUDIT"`. The Schwab mode is `"REAL-H7-SCHWAB-PRECLOSE-AUDIT"` (`h7_schwab_data_gate.py:13`).
- `h7_data_gate.py:554` — `_validate_result_scope_closure` hardcodes `validate_v2_audit_receipt` (the ThetaData v2 validator), which no Schwab package can satisfy.

Meanwhile `build_window_registration_event` **requires** `data_gate_evidence_id` and `data_gate_receipt_hash` (`h7_schwab_window_registration.py:58-61`) and freezes them into the immutable payload (`:266-267`) — while checking nothing about their provenance, evidence mode, or session.

So the gate packet's "machinery ready; Monday receipt absent" is not accurate: there is no code path that converts a verified Schwab package into the receipt the door asks for. Worse, the door would accept a **ThetaData-derived** gate receipt hash alongside `provider: schwab` and `cache_namespace: .cache/schwab_chains/`, and the resulting append-only event would read to any future auditor as *"the Schwab package passed the gate."* That is the single clearest way this lane could lie, and it is a gap in validation, not an exploit anyone has attempted.

**Fix (either):** extend `build_receipt` to accept the Schwab evidence mode with a Schwab-specific scope-closure recompute; or add a `data_gate_evidence_mode` field to `EVIDENCE_FIELDS` and assert it equals `h7_schwab_data_gate.EVIDENCE_MODE`. Do not ship the registration until one exists.

### B3 — `d77f995` removed the only code binding on the feasibility receipt and did not replace it

The commit (mislabeled `docs(h7)` — audit M6) deleted:

```python
if feasibility["code_sha"] != evidence["code_commit"]:
    raise RegistrationInputError("feasibility code_sha disagrees with registration code_commit")
```

**The removal was justified.** Because `register_window_real` separately pins `evidence["code_commit"] == HEAD` with a clean tree (`:354-360`), the deleted check demanded the feasibility receipt be computed at the exact registration HEAD — unsatisfiable once the gate packet, the one-door test, and the merge landed on top of measurement commit `3729049`. Restoring it is the wrong fix.

**But nothing replaced it, and a satisfiable replacement was sitting in the receipt.** After the removal, `_validate_feasibility` (`:107-133`) proves only that the receipt is internally intact and arithmetically self-consistent. It does not bind the measurement to the code or the frozen parameters that produced it:

- `config_hash` **is** in the receipt (`2026-08-09-feasibility.json:4`) but is absent from `FEASIBILITY_FIELDS` (`:71-85`) and never compared to the registration's own `config_hash()` (`:246`).
- `stack_version` is a hand-written string constant (`tools/h7_schwab_feasibility.py:34`), not derived from code — it does not change when the entry stack changes.
- `universe` **is** in the receipt (`:39-55`) but only its **cardinality** is checked: `int(feasibility["universe_size"]) != len(manifest["included"])` (`:197`) compares counts, not names.

The attack this enables: change `h7_watch.assemble_name` or `h7_board.resolve_board` after the measurement, and the registration still binds the old 3/1050 as if it described the stack being frozen. Nothing re-derives the base rate.

**Fix:** add `config_hash` to `FEASIBILITY_FIELDS` and assert `feasibility["config_hash"] == config_hash()`; assert `feasibility["universe"] == manifest["included"]`. Both are satisfiable today and catch the case that matters.

### B4 — The feasibility number was measured on a different data source than the window will use

The owner is being asked to type either a redesign or a starvation pre-acceptance quoting `3/1050`. Before doing so they should know the measurement is not of the stack that will run:

| | Measured (feasibility) | Will run (window) |
|---|---|---|
| Provider | ThetaData | Schwab |
| Cache | `.cache/chains` (`tools/h7_schwab_feasibility.py:35,157`) | `.cache/schwab_chains` |
| Snapshot instant | EOD (16:00) | 15:45 ET preclose |
| IV / Greeks | ThetaData model (carries `iv_error`) | Schwab's `volatility` + greeks |

Separately, the intended design pairs a **15:45 chain with a 16:00 underlying close** — `h7_watch.py:533` derives `raw_spot` from `closes.iloc[-1]`. A 15-minute basis mismatch between the options surface and the spot used for moneyness, delta selection and IV rank. That is a defensible modeling choice, but it is undocumented and it is not what the feasibility measurement did.

Three further biases, all pointing the same direction — the estimate is an **upper bound**:

1. The feasibility path never runs the data gate; sessions that would be whole-universe `NO_GO` (zero real entries) still contribute passes.
2. Portfolio state resets every session — `open_positions=()`, `open_h7c=0`, `month_spent=0.0`, full sleeve (`tools/h7_schwab_feasibility.py:170-173,195-200`). Real position-holding blocks re-entry and depletes the sleeve. `resolve_board` (`h7_board.py:69-87`) is therefore at its most permissive.
3. `common_cached_sessions` (`:117-133`) selects only sessions where **all 15** names have cached data, i.e. the data-complete days.

Assumption 2 is disclosed in the receipt's `portfolio_state_assumption`; 1 and 3 are not, and the *direction* of the bias is stated nowhere.

**This strengthens rather than weakens the starvation conclusion, and the owner should be told so plainly.** I verified the arithmetic independently:

- Receipt hash recomputes to `8b567a5e…ff625c` — **matches** the embedded hash and the gate packet. Receipt is intact.
- `3/1050 = 0.002857142857142857` ✓; `expected_entries = 3.0` ✓; `symbol_days = 70 × 15` ✓; `error_count = 0` (clean denominator, no unavailable symbol-days padding it).
- Against the 2026-07-24 gate: `MIN_LOSSES_FOR_VERDICT = 10` → bar = 20 expected entries. **3.0 vs 20 is a 6.67× shortfall.** At this base rate the bar needs ≈ **467 decision sessions (~22 months)**, not 70.
- Exact Clopper-Pearson 95% CI on 3/1050 → `[0.00059, 0.00833]` → **[0.62, 8.74] expected entries.** The entire interval sits below the bar. The starvation conclusion is robust to sampling uncertainty — there is no "is 3 close enough to 20" debate to have.
- The 3 passes cluster on two sessions (2026-07-13 NOW; 2026-07-16 MSFT + PLTR). 68 of 70 sessions produced zero. The effective independent-observation count is two, so any extrapolation is weaker than 3/1050 makes it look.

One presentation point: because `window_sessions == lookback_sessions == 70` over the same universe, `expected_entries` reduces to exactly `full_stack_passes`. **"3.0 expected entries" is a restatement of "we observed 3," not an independent projection.** Honest arithmetic; the word "expected" implies a model that is not there.

---

## High-severity findings (non-blocking for merge; close before the Monday canary)

### H1 — The one claim nothing verifies is the capture time

`verify_session` (`tools/schwab_chain_manifest.py:116-221`) independently recomputes bytes, sizes, row counts, expiration counts and the manifest hash — and reads **zero** timing fields. It never inspects `captured_at_et`, `captured_at_utc`, `force`, `scheduled_session_tag`, `timing_validation`, `provider`, `config_hash` or `code_sha`.

Meanwhile `--force` (`schwab_chain_capture.py:245-249`) bypasses the preclose tolerance entirely — `validate_session_tag` returns `True` immediately on `force` (`options_researcher/intraday_capture.py:199-200`) — leaving only `in_regular_session` (09:30–16:00, `live_quotes.py:89-91`).

Probe confirmed: a package stamped `captured_at_et = 09:31`, `force: true`, `session_chain_convention: preclose_snapshot_v1` **verifies identically to a genuine 15:45 capture.** The convention label is self-asserted by the capture, never checked against the clock. For H7 this would pair a morning options surface with a 16:00 close — non-simultaneous inputs producing spurious moneyness and delta, with a receipt that still says "preclose."

*Credit where due:* the gate packet's "minimum 2 expirations" defense **is** enforced at verify time (`:194-197`), recomputed from the parquet — my forged single-expiration package was refused even after rewriting manifest and receipt consistently. But 2+ expirations does not distinguish 09:31 from 15:45.

**Fix:** have `verify_session` parse `captured_at_et`, require it within the preclose tolerance, and require `force` false. Or refuse to build a manifest at all when `force` is set.

### H2 — Normalization permanently discards fields that cannot be recovered

`_normalize` (`schwab_chain_capture.py:56-68, 97-100`) keeps 11 columns. The adapter has already parsed `contract_symbol`, `multiplier`, `non_standard`, `mini`, `timestamp`, `trade_timestamp` (`schwab_adapter.py:237-268`) — all dropped before the parquet is written.

Probe result: a chain containing a standard **and** an adjusted/mini contract at the same `(expiration, strike, right)` — routine after a corporate action, and this universe carries several high-corporate-action names — verifies fine at the manifest layer, then produces `CHAIN_DUPLICATE_CONTRACT` at the gate (`duplicate_contract_count = 2`) → per-symbol `NO_GO` → whole-universe `NO_GO`. Because `_write_parquet_once` (`:117-134`) refuses any overwrite on hash mismatch, **that session is permanently lost**; there is no remediation path. This compounds audit finding M7's "same-day retry is unsalvageable."

It fails closed rather than lying — the right direction — but the discarded columns are exactly what you would need to *filter* the duplicates instead of losing the session, and to detect per-contract quote staleness (`isDelayed` is a whole-chain flag only). The bytes are gitignored and unrepurchasable. **This is cheap now and impossible later — fix before the first capture runs.**

### H3 — The package proves drift, not authenticity; the gate packet says "bind"

I attempted six tamper paths against `verify_session` on synthetic data:

| Attack | Result |
|---|---|
| Mutate parquet only | REFUSED — `hash mismatch for AAA` |
| Mutate parquet + rebuild manifest | REFUSED — `receipt manifest hash does not match` |
| Inflate manifest `row_count` + re-seal manifest hash | REFUSED — `receipt manifest hash does not match` |
| Delete one symbol's parquet | REFUSED — `exact-session file universe mismatch` |
| Full forge, single expiration | REFUSED — `expiration count is 1 for AAA` |
| **Full forge: parquet + manifest + receipt, all consistent** | **ACCEPTED** |

The triple-binding is genuinely strong against partial tampering. But the package is self-attesting with no external anchor, so anyone who can write all three files can forge it. After registration the ledger's `last_historical_manifest_receipt_hash` closes this. **Before registration — including for the Monday canary — nothing does.**

The gate packet's "Manifest + capture receipts bind exact session and every Parquet byte" should read **"detect post-capture drift."** Cheap hardening: append the manifest hash and receipt hash to `ledger/facts.log` (append-only, flock-protected, already in the restic allow-list) at capture time.

---

## Medium findings (non-blocking)

**M-a — Partial-universe acceptance is reachable, and the guard against it never runs for this lane.** `h7_schwab_data_gate.evaluate(..., symbols=["VST"])` produces `whole_universe_verdict: "GO"` over a one-name "universe" (`h7_data_gate.py:390-393, 425-431`). The whole-15 enforcement (`_validate_result_scope_closure`) is called *only* from `build_receipt`, which refuses Schwab results outright (B2). Harmless today — no CLI, no callers. Related: `h7_schwab_data_gate.evaluate` has no default paths; `chain_dir`, `manifest_path` and `receipt_path` are all caller-supplied, so there is no canonical "the" package.

**M-b — The guarded door delegates its two most important checks to callables that do not exist yet.** `register_window_real` takes `code_state` and `recheck_gates` as injected parameters (`:329-330`, used at `:354`, `:383`). Its guarantees are only as strong as a caller nobody has written or reviewed. The legacy lane has `tools/h7_manual_activate.py` as the model; the Schwab lane has no equivalent, and the one-door test's CLI assertions (`tests/test_h7_one_door.py:233-240`) cover only the legacy CLI. Write and review the Schwab CLI as part of the registration package, not after.

**M-c — Evidence-persistence gaps for the new lane.** `tools/daily_ritual.sh:385-388`'s git-add allow-list omits `ledger/h7_forward_schwab` and `reports/schwab_chains` — so once the namespace activates, the ritual would silently never commit the new store's events or the capture receipts. Restic coverage is correct (`tools/h7_forward_backup.py:36-51` includes `.cache/schwab_chains`, `reports/schwab_chains`, `reports/h7_forward_schwab`, `ledger/h7_forward_schwab`), and `.cache/schwab_chains` is registered in the irreplaceable-data guard (`tools/irreplaceable_data_guard.py:59`; inventory correctly shows `present: false`, 0 files). But `reports/schwab_chains` — the receipts *without which the parquet is inadmissible* — sits outside the guard's namespace list, so its loss would be invisible: the same blind spot as audit finding M4. `.tmp/schwab_chain_capture/*.log` is excluded by restic's `.tmp/*` pattern.

**M-d — The feasibility receipt records the numerator but not the funnel.** `summarize_counts` (`tools/h7_schwab_feasibility.py:47-102`) stores `passing_symbol_days` only. Nothing records how many candidates were `ENTRY-OK` before `resolve_board`, or board rejections by reason. The owner cannot tell from the receipt whether the signal fired 3 times or 300 times with 297 board rejections — which is exactly the fact that should drive a redesign decision. (Structurally the board is at its most permissive here, so the starvation is almost certainly in the signal; but the receipt does not prove it.) Recommend adding per-stage funnel counts before the owner is asked to choose.

**M-e — `_code_sha()` does not check for a dirty tree** in either the capture (`schwab_chain_capture.py:81-88`) or the feasibility tool (`:213-219`), so a receipt can claim a clean commit identity while the working tree differs. `register_window_real` does check `tree_clean` at append time — but the feasibility receipt is written long before.

**M-f — No quote-sanity validation in `_normalize`.** An all-zero or all-NaN bid/ask chain passes capture. The gate's nonfinite / negative / crossed checks and `audit_chain`'s IV-and-greek block catch most of it downstream; an all-zero-bid chain would still pass everything. Low severity.

---

## Attacks I attempted that did NOT hold

Stated explicitly so the owner can see where the lane is actually sound.

- **Look-ahead via session derivation** — clean. `evaluation_session` (`h7_watch.py:236-246`) returns the latest completed XNYS session *strictly before* the run date and never evaluates the run date itself. `session_close_utc` (`data/cache_runner.py:128-141`) uses the real XNYS close including early closes, not 23:59:59Z.
- **Look-ahead via split adjustment** — no material leak. `adjustment_factor` (`data/underlying_closes.py:62-70`) multiplies ratios of splits *after* the session to recover the raw price. Returns and realized vol are scale-invariant, and spot is converted back to raw, so reconstructing with today's splits table does not leak future information into the decision.
- **OOS holdout breach via `allow_oos=True`** — not a breach. It matches the established forward-lane convention (`h7_watch.py:518,521`; `h10_watch`, `qm_watch`, `qm_study` all do the same). Not a legacy-holdout read.
- **Hidden prior-day / intraday fallback in the gate** — none. `_evaluate_chain` (`h7_data_gate.py:213-246`) reads only the exact-session path; `newest_date_at_or_before_session` is recorded solely to raise `CHAIN_STALE` and is never substituted.
- **Old-ledger mutation** — none. The new lane never names `ledger/h7_forward` or `ledger/experiments.jsonl`; its imports from `h7_window_registration` are pure functions. `register_window_real`'s VALID-EMPTY re-verify would refuse the old store. Verified unchanged: `VALID records=1 head=a1ea228c2abb`.
- **Trading activation by env var** — `SCHWAB_TRADING_ENABLED` is a **refusal, not a switch**: a truthy value *raises* (`schwab_adapter.py:58-61`). Env can break the adapter, never enable trading. `READ_ONLY_METHODS` (`data/schwab_credentials.py:26-45`) contains only GET market-data endpoints; `__getattr__` raises `AttributeError` for anything else — no order, account, position or transaction surface exists to reach.
- **Authority activation** — flags are `False` at HEAD; `evaluate_full_ritual()` returns `ready=False` with all three blockers; `tools/daily_ritual.sh:47-54` hard-gates on `require-full` *before* any stateful surface and exits non-zero today; the PREPARED patch is unapplied and `data/ritual_authority.py` is untouched.
- **Partial-universe capture in production** — the wrapper passes no universe override; `capture()` defaults to `watch_universe()` (15). The 1-name captures in the log are test fixtures.
- **Wrapper and plist** — correct. Template only, `RunAtLoad=false`, `branch == main == origin/main` fail-closed, explicit `LIVE_MARKET_DATA_PROVIDER=schwab`, `SCHWAB_TRADING_ENABLED=false`, no `--force`.
- **New-namespace ledger state** — `VALID EMPTY`, exit 0.

---

## Recommendation to the owner

**On the merge:** it **stands**. Do not revert `1866f59`. The code is inert by construction — empty ledger namespace, authority flags false, zero callers on `register_window_real`, no order surface, a template-only plist. The failures I found are missing validations and overstated documentation, not live exposure, and every one is fixable in place.

**On registration and the authority flip:** **do not proceed** until B1–B4 are closed. Specifically, before you type OD-3 or the starvation decision:

1. **B1** — extend the one-door AST scan to cover `SCHWAB_FORWARD_STORE`. *(small)*
2. **B2** — give the Schwab lane a real receipt path, or bind and check `data_gate_evidence_mode` in the registration event. Until then, the door can only be satisfied with evidence from the wrong provider, and would record it as if it were Schwab's. *(design decision needed)*
3. **B3** — bind `config_hash` and `universe` in `_validate_feasibility`. `d77f995`'s removal was correct; the replacement is missing. *(small)*
4. **B4** — amend the gate packet to disclose that 3/1050 was measured on ThetaData EOD chains, that all three known biases inflate it, that `expected_entries` equals the observed count by construction, and that the 95% CI is **[0.62, 8.74] against a bar of 20**. *(documentation)*

Then, before the Monday canary: H1 (verify the capture time), H2 (stop discarding `contract_symbol` / `multiplier` / `non_standard` / `mini` / `timestamp` — unrecoverable once captures begin), H3 (anchor the manifest hash in `facts.log`), and M-c (add the two new paths to the ritual's git-add allow-list).

**On the substance, separate from the code:** the honest reading of the feasibility work is that **a 70-session, 15-name window cannot reach a verdict on this entry stack.** It projects 3 entries against a 10-loss bar; the entire 95% confidence interval falls below the 2026-07-24 gate's 20-entry threshold; and reaching that bar at the measured base rate needs roughly 467 decision sessions. Every simplification in the measurement made the number *more* optimistic, not less. That is a clean, useful, negative result — a success under this repo's own standard, not a failure to fix — and it means the real decision in front of you is a redesign (or a different hypothesis), not a starvation pre-acceptance. The tool was right to emit no verdict; the numbers it produced survive independent recomputation.

**Vocabulary note per `.cursorrules`:** nothing here is "proven" or "confirmed." The lane **survived** the tamper, fallback, look-ahead, activation and old-ledger attacks I ran; it **did not survive** the second-door, receipt-provenance, feasibility-binding and capture-time attacks.

---

## Commands run

```
git log --oneline -25 / --all / 1866f59^..1866f59 --format="%H %P"
git status --short ; git rev-parse HEAD ; git rev-parse origin/main
git show d77f995 --stat ; git show d77f995 -- <registration + test files>
git show --stat 1866f59 ; git diff --stat 1866f59^1 1866f59
git check-ignore -v reports/schwab_chains .cache/schwab_chains reports/h7_forward_schwab ledger/h7_forward_schwab
wc -l <core surfaces> ; ls -la ledger/ ledger/h7_forward/ ledger/h7_forward_schwab/
grep/sed reads of: data/schwab_adapter.py, data/schwab_credentials.py,
  options_researcher/schwab_chain_capture.py, tools/schwab_chain_manifest.py,
  options_researcher/h7_schwab_data_gate.py, options_researcher/h7_data_gate.py,
  options_researcher/h7_schwab_window_registration.py, options_researcher/h7_window_registration.py,
  options_researcher/h7_event_ledger.py, options_researcher/h7_watch.py, options_researcher/h7_board.py,
  options_researcher/intraday_capture.py, options_researcher/live_quotes.py,
  tools/h7_schwab_feasibility.py, tools/h7_forward_backup.py, tools/irreplaceable_data_guard.py,
  tools/daily_ritual.sh, tools/schwab_chain_capture.sh, tools/launchagents/*.plist,
  data/ritual_authority.py, data/cache_schema.py, data/thetadata_adapter.py,
  data/underlying_closes.py, data/cache_runner.py, data/recent_topup.py,
  research/receipts.py, .agents/hooks/block_ledger_edits.py, tests/test_h7_one_door.py

uv run python -m options_researcher.h7_event_ledger verify --base-dir ledger/h7_forward_schwab   -> VALID EMPTY (exit 0)
uv run python -m options_researcher.h7_event_ledger verify                                        -> VALID records=1 head=a1ea228c2abb (exit 0)

LIVE_MARKET_DATA_PROVIDER=schwab uv run python -m unittest discover -s tests -p "<pattern>"  for:
  test_h7_schwab*.py, test_schwab*.py (32), test_h7_one_door.py, test_h7_data_gate.py,
  test_ritual_authority.py (4), test_block_ledger_edits.py (33), test_h7_backup.py (4),
  test_provider_disabled.py (14), test_h7_window_registration.py, test_shell_banner_guard.py (3),
  test_irreplaceable_data_guard.py (18)                                    -> all OK

uv run ruff check .                                                        -> All checks passed
uv run python -c "<recompute feasibility receipt hash + arithmetic + gate bar>"
uv run python -c "<Clopper-Pearson 95% CI on 3/1050>"
uv run python -c "<print ritual authority flags and readiness>"
uv run python -c "<dump irreplaceable_data_inventory namespaces>"

Scratch probes (synthetic data only, outside the repo):
  evasion_probe.py     - one-door AST scanners vs 3 Schwab-store evasions + old-store control
  drift_probe.py       - 6 tamper paths against schwab_chain_manifest.verify_session
  timing_dup_probe.py  - forced morning capture accepted; duplicate-contract collision path
```

Nothing in the repository was created, modified, or deleted by the reviewer; no receipt-writing CLI, provider-adjacent command, or git state change was run.
