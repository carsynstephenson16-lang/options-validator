# Codex brief 40 — H7 activation-day receipt chain: the missing Schwab data-gate command and the one-shot runbook

**Date:** 2026-09-08 (rev 2 — round-1 adversarial review FAIL, all 15 findings applied; see Status)
**Author:** Claude (orchestrating session; receipt-regeneration attempt, 2026-09-08)
**Executor:** Codex (Sol, high reasoning — as briefs 07/37/38; owner may substitute at dispatch)
**Status:** DRAFT — pending round-2 independent adversarial review before hand-off.
Round 1 (`reports/2026-09-08-brief-40-adversarial-review-round1.md`) returned
FAIL: two blockers (chain-dir shape; untracked receipts vs. the door's clean-tree
check), four HIGH, seven MEDIUM, one LOW. Every finding is applied in this
revision and cited inline as **R1-n**. Per repo practice (briefs 36/37/38) a
revision that closed a FAIL gets one more review round; its receipt goes to
`reports/2026-09-08-brief-40-adversarial-review-round2.md`. Dispatch, landing
and ops sync remain the owner's.
**Provenance:** file:line constraints are Repo-verified against `origin/main`
@ `863eff2` unless a sentence carries its own label. "Run-verified" facts were
executed 2026-09-08 in the ops execution checkout (`~/options-validator-ops`) or
the primary checkout on a clean tree at the same commit (by the author, and
independently by the round-1 reviewer). Sentences labelled **Inference** are
the author's reading of the code, not a file fact.
**Companion report:** `reports/2026-09-08-h7-receipt-regeneration-status.md`
(what was regenerated today, what could not be, with the evidence).

## Why this exists (plain language)

Brief 36 built the door that registers the first H7 Schwab forward window
(PR #147, merged 2026-09-03). Its own ordering rule (`…-36-…-codex-brief.md:74-83`)
says: land the door, then **regenerate the qualifying receipts at the new
config**, then the owner runs the activation CLI. The README, PROJECT_STATE and
the 2026-09-02 close-out all repeat that as the next step.

Today's attempt to do step 2 found that it cannot be done with what is on
`main`:

1. **There is no command that writes the Schwab-mode data-gate receipt the door
   requires.** The door insists on `evidence_mode == "REAL-H7-SCHWAB-PRECLOSE-AUDIT"`
   (`options_researcher/h7_schwab_window_registration.py:640` and `:699`; the
   constant is set once at `h7_schwab_data_gate.py:15`). The only CLI,
   `python -m options_researcher.h7_data_gate` (`h7_data_gate.py:804-897`),
   evaluates the ThetaData store `.cache/chains` (edge 2026-07-27, frozen by
   OD-2/OD-4) in the legacy evidence mode. The Schwab evaluator
   `h7_schwab_data_gate.evaluate()` (`h7_schwab_data_gate.py:134-200`) has
   **no production caller** — the non-test references are the registration
   module's constant/closure list, the quote-age gate's helper import
   (`h7_schwab_quote_age_gate.py:21`), `h7_data_gate.py:522,527,601,604`, and a
   docstring in `tools/h7_schwab_manual_activate.py:40`. Five test modules call it.
2. **The daily ritual's own source-health → data-gate chain is fenced off until
   after registration.** `tools/daily_ritual.sh:154-200` runs only when
   `data.ritual_authority require-full` exits 0, and that requires
   `h7_active=True` (`data/ritual_authority.py:39,82-83`). Before registration
   `h7_active` is False by construction. Run-verified 2026-09-08 09:09 log:
   `H7 lanes: PAUSED — full ritual authority not granted`.
3. **The data-gate receipt lives one day.** `h7_data_gate.validate_durable_receipt`
   (`h7_data_gate.py:670-751`) re-hashes every `close:<SYM>` input
   (`research/receipts.py:45-54`); those are `.cache/underlying/<SYM>.parquet`,
   refreshed by the ritual every trading morning (`DATA_PULL` facts, 09-08
   log line "underlying closes: guarded refresh ran"). A receipt made today
   fails `data-gate receipt input files changed` tomorrow. So the
   source-health / data-gate / backup receipts are an **activation-day**
   procedure, run after that morning's ritual and before the next, immediately
   followed by the owner's activation command.
4. **(R1-2) Every receipt the procedure writes dirties the tree the door
   demands clean.** `tools/h7_schwab_manual_activate.py:66-72` and
   `h7_activation_guard.py:84-90` both run `git status --porcelain` with no
   `--untracked-files=no`, so a fresh receipt (`??`) alone refuses activation.
   The procedure therefore ends with an evidence commit, exactly as the ritual's
   Step 8 and the capture wrapper's "evidence-only ahead" rule already allow.

What this brief delivers: (WP-A) the missing command; (WP-B) one shell entry
point that runs the whole activation-day chain in the ops checkout, commits the
evidence, and prints the owner command with every machine-derivable value
filled in; (WP-C) a calendar refusal in the pre-close capture, because the
wrapper captured a full "ok" package on Labor Day 2026-09-07 (market closed).

## Scope

**IN**

- WP-A: new `tools/h7_schwab_data_gate_receipt.py` + `tests/test_h7_schwab_data_gate_receipt.py`.
- WP-A (small, named edits): `tools/h7_forward_backup.py` — add the new
  namespace `reports/h7_data_gate_schwab` to `BACKUP_PATHS` (`:61-72`) and to the
  restore-check receipt scan (`:361-364`), with a test.
- WP-B: new `tools/h7_activation_day.sh` + shell test in
  `tests/test_h7_activation_day.py`; `docs/h7-forward-operations.md` new heading
  "Activation day (Schwab)".
- WP-B (small, named edits): `tools/schwab_chain_capture.sh:65-70` and
  `tools/schwab_chain_intraday_capture.sh:73-78` — add `reports/h7_data_gate_schwab`
  and `reports/h7_forward_schwab` to `EVIDENCE_ALLOW` (both lists must stay
  identical; there is a test that pins the intraday one — find and extend it).
- WP-C: `options_researcher/schwab_chain_capture.py` trading-calendar refusal +
  cases in `tests/test_schwab_chain_capture.py`; defensive mirror in
  `tools/schwab_chain_capture.sh` before auth.

**OUT** (an edit here is a review FAIL, not a judgment call)

- No registration, no ledger write (`ledger/*`), no `data/earnings/*` row, no
  cache write, no network call, no live-order path.
- No edit to `data/ritual_authority.py` (owner decision D-2).
- No edit to any validator's acceptance logic: `h7_data_gate.validate_durable_receipt`,
  `h7_schwab_data_gate.*`, `research/receipts.py`, `h7_activation_guard.py`,
  `h7_schwab_window_registration.py`, `tools/h7_schwab_manual_activate.py`.
- No edit to any file in `FEASIBILITY_SOURCE_PATHS` (50 entries; run
  `feasibility_source_closure()` first and list it in the PR body). **This
  includes `options_researcher/h7_watch.py`** (R1-4) — the watcher is not
  touched by this brief.
- No quote-age *blocking* gate (Brief 36 WP-E Mode A stands until an
  owner-typed absolute threshold exists).
- The script never invokes `tools/h7_schwab_manual_activate.py`, never pushes,
  never syncs a checkout, never edits the 2026-09-07 package.

## Repo-verified facts the executor must not contradict

| # | Fact | Where |
|---|---|---|
| F1 | Activation CLI takes `--source-health-receipt`, `--data-gate-receipt`, `--backup-restore-receipt`, `--completed-session`, `--activation-spec`, `--owner-typed-spec-sha256`, `--included-symbols`, `--evidence`, plus owner-typed fields at use time. The receipt paths are arguments; the door assumes no location | `tools/h7_schwab_manual_activate.py:343-351` |
| F2 | Receipt chain check: `source.receipt_hash == data.source_health_receipt_hash`, data receipt's `source_health_receipt_path` must be the same file, data receipt revalidated by `h7_data_gate.validate_durable_receipt` | `tools/h7_schwab_manual_activate.py:120-147` |
| F3 | Backup receipt: `receipt_type == "backup_restore"`, `scope == scope_identity()`, `completed_session` equal to the CLI arg, `verification.ok is True` | `tools/h7_schwab_manual_activate.py:108-117` |
| F4 | Door rechecks source-health all-healthy and data-gate GO at append time and requires `git status --porcelain` to be EMPTY **including untracked files** (`??` counts); the guard has an identical independent check. (R1-2) | `tools/h7_schwab_manual_activate.py:66-72`; `h7_schwab_window_registration.py:904-975` (`:936-938` "working tree is dirty at append time"); `h7_activation_guard.py:84-90,283` |
| F5 | Trim mode: full 15-name receipts, every INCLUDED name healthy (source) and per-symbol GO (data gate); excluded names may be NO_GO; the included-subset verdict is computed at `h7_activation_guard.py:176-180`; the door mirrors it at `h7_schwab_window_registration.py:662-677`; the cohort is read from `load_registered_cohort()` (Run-verified: included = AMD AMZN CEG ET MSFT NOW PLTR TEM VST; excluded = AVGO CRWV IREN NVDA SMCI USAR) | `options_researcher/h7_activation_guard.py:106-240`; spec `docs/superpowers/specs/2026-09-02-h7-schwab-activation-spec.md` |
| F6 | Durable data-gate receipt = `h7_data_gate.build_receipt(result, source_health_receipt=…, source_health_receipt_path=…)` then `research.receipts.write_immutable_receipt(receipt, path)`. `build_receipt` accepts the Schwab result: `_validate_result_scope_closure` branches on `evidence_mode == h7_schwab_data_gate.EVIDENCE_MODE` (`:600-606`) and injects `schwab_manifest_hash` / `schwab_capture_receipt_hash`. `write_artifact(result, *, reports_dir=…)` writes `<reports_dir>/<scope_id>/<session>.json` and raises `FileExistsError` on differing content. The ritual's LEGACY receipt path is `reports/h7_data_gate/<scope_id>/receipts/<session>.json` — **WP-A does not use it** (R1-5) | `h7_data_gate.py:600-668`, `:761-785`; `research/receipts.py:57-66,94`; `tools/daily_ritual.sh:157,186-195` |
| F7 | Schwab evaluation: `h7_schwab_data_gate.evaluate(requested_run_date, *, close_dir, chain_dir, manifest_path, receipt_path, scope=None, symbols=None)`; `scope=None, symbols=None` yields the full 15-name `scope_identity()` universe (`:151-153`). **The chain cache is FLAT: `chain_dir` is `.cache/schwab_chains/` itself; the manifest's per-file `path` (e.g. `AMD_2026-09-03.parquet`) is relative to it. There is no per-session subdirectory.** Manifest + capture receipt are session-partitioned: `reports/schwab_chains/<session>/{manifest.json,preclose.json}`. Run-verified: flat dir → `2026-09-03 GO 15 EXACT_SESSION_GO`; `<root>/<session>` → `NO_GO 0 SCHWAB_PACKAGE_INVALID`. (R1-1) | `h7_schwab_data_gate.py:134-200`; `h7_schwab_window_registration.py:38-39` (`CACHE_NAMESPACE = ".cache/schwab_chains/"` is a namespace string, `SESSION_CHAIN_CONVENTION` names the snapshot) |
| F8 | The watcher (`h7_watch`) recomputes every GO symbol's chain binding with the ThetaData v2 convention `validate_v2_audit_receipt(<cache_dir>/_meta/full_audit.json)`; Run-verified against the Schwab path it refuses (`FileNotFoundError` at `.cache/schwab_chains/_meta/full_audit.json`). **It cannot consume a Schwab data-gate receipt today**, and it sits inside the feasibility closure. (R1-4) | `options_researcher/h7_watch.py:111-121`; `data/cache_schema.py:125-127` |
| F9 | Source-health CLI writes its receipt unconditionally to `reports/h7_receipts/<scope_id>/source_health/<evaluation_session>.json`; `--write-receipt` overrides the path; prints `receipt=<path>`; **exits 1 whenever ANY of the 15 is unhealthy** (`:290-295`) — the six excluded names are permanently `EARNINGS-UNKNOWN`, so exit 1 is the steady state and the ritual treats it as non-fatal (`daily_ritual.sh:164-167`). Without `--as-of` the receipt's `evaluation_session` becomes the run date (`:238`) and the data gate rejects it ("source-health receipt session does not match gate", `h7_data_gate.py:631`). (R1-8) | `options_researcher/h7_source_health.py:197-295` |
| F10 | Backup/restore tool needs `RESTIC_REPOSITORY` and `RESTIC_PASSWORD_FILE`/`_COMMAND` in the environment; it does not load `.env` itself. `BACKUP_PATHS` is an explicit allow-list (`reports/h7_data_gate`, `reports/h7_receipts`, `reports/h7_forward_schwab`, …) and the restore-check scans `reports/h7_receipts/**/*.json` + `reports/h7_data_gate/*/receipts/*.json`; **a new namespace is invisible to both until added** (R1-5). Subcommands: `backup --completed-session`, `restore-check --backup-receipt --completed-session` | `tools/h7_forward_backup.py:61-72,141-148,361-364,552-559`; `docs/h7-forward-operations.md:36-50` |
| F11 | `evaluation_session(d)` = last completed XNYS session strictly before `d`, selected from `trading_days(...)` so it is a trading day by construction; `evaluation_session(2026-09-08) = 2026-09-04`; 2026-09-07 (Labor Day) is never a session (`trading_days('2026-09-07','2026-09-07') == []`); the newest verified pre-close package is 2026-09-03; 2026-09-04 was refused pre-auth ("could not refresh origin/main"). **So an activation day D needs a verified package for D−1, and 2026-09-08 has none.** (R1-6) | `options_researcher/h7_watch.py:236-246`; `data/cache_runner.py:121-124`; `reports/schwab_chains/`; ops `.tmp/schwab_chain_capture/2026-09-04_1545.log` |
| F12 | The pre-close capture has **no exchange-calendar check** (`grep -n -i 'calendar\|holiday\|trading_days'` over `schwab_chain_capture.py` and `tools/schwab_chain_capture.sh` returns nothing); the plist fires Weekday 1–5 at 15:45. The session is derived from `now_ny` at `:399`, AFTER `_default_client()` at `:397`; there is no `--session` argument; refusals print free text `schwab_chain_capture refused: <reason>` (`:390`); the wrapper composes the alert `CRITICAL: SCHWAB CHAIN REFUSED …` by grepping `^schwab_chain_capture refused:` (`tools/schwab_chain_capture.sh:150`); the first-write-wins slot is `_write_parquet_once` (`:322,340`, comment `:71`). (R1-9, R1-10) | Run-verified; `~/Library/LaunchAgents/com.carsyn.options-validator.schwab-chain-preclose.plist` |
| F13 | Quote-age gate is callable, unwired, Mode A (no absolute threshold ⇒ `AWAITING_OWNER_THRESHOLD`, bans nothing). **Its input must be a BUILT receipt** (`receipt_type == "data_gate"` and `evidence_mode == EVIDENCE_MODE`, else `QUOTE_AGE_EVIDENCE_INVALID`, `:183-195`); `included_symbols` must be a subset of the universe (`:196-203`). (R1-3) | `options_researcher/h7_schwab_quote_age_gate.py:1-8`, `:56-59`, `:157-203` |
| F14 | `feasibility_source_closure(REPO_ROOT) == FEASIBILITY_SOURCE_PATHS` (50 paths); the door compares `source_hash(paths=FEASIBILITY_SOURCE_PATHS)` (`:353`). **Only an EDIT to one of those 50 files invalidates the feasibility receipt**; adding a new `tools/` module the feasibility entry does not import does not; the measurement reads the frozen `.cache/chains` and is time-invariant. Inside the closure and relevant here: `h7_schwab_data_gate.py`, `h7_data_gate.py`, `research/receipts.py` (WP-A imports them — importing is safe, editing is not), `h7_watch.py` (untouched). Outside: `tools/h7_forward_backup.py`, both capture wrappers, `schwab_chain_capture.py`, `h7_source_health.py`, `h7_activation_guard.py`, `h7_schwab_manual_activate.py` (Run-verified). (R1-7) | `h7_schwab_window_registration.py:38-60`, `:160-175`, `:353` |
| F15 | Capture-wrapper alignment guard: branch must be `main`; `origin/main` fetched with a bounded timeout; HEAD may be AHEAD of `origin/main` **only by commits whose changed paths all fall under `EVIDENCE_ALLOW`** (`ledger/facts.log ledger/h7_forward ledger/h7_forward_schwab reports/h7_receipts reports/h7_data_gate reports/h5 reports/h6_forward reports/h8_forward reports/h10 reports/ritual reports/intraday_capture reports/live_probe reports/cache_runs reports/schwab_chains reports/schwab_chains_intraday`); `reports/h7_forward_schwab` is NOT in it today. The ritual's Step 8 stages `DATA_TIER_PATHS` (`daily_ritual.sh:562-563`) every day and `FULL_TIER_PATHS` (`:570-572`) only under full authority, then commits — never pushes. (R1-2, R1-12) | `tools/schwab_chain_capture.sh:36-52,65-104,150`; `tools/schwab_chain_intraday_capture.sh:73-78`; `tools/daily_ritual.sh:562-598` |

## Work packages

### WP-A — `tools/h7_schwab_data_gate_receipt.py`: produce the durable Schwab data-gate receipt

One operator command, run from the checkout root that holds the caches:

```bash
uv run python tools/h7_schwab_data_gate_receipt.py \
  --as-of YYYY-MM-DD \
  --source-health-receipt reports/h7_receipts/h7-forward-15-v1/source_health/<session>.json \
  [--chain-dir .cache/schwab_chains] [--reports-root reports/schwab_chains] \
  [--close-dir .cache/underlying] \
  [--output-root reports/h7_data_gate_schwab]
```

Behaviour:

1. Resolve `session = evaluation_session(as_of)` (F11). It is a trading day by
   construction; assert it, do not document an exit path for it (R1-15).
   Refuse (exit 2, no artifact) with `NO_PACKAGE_FOR_SESSION` if
   `<reports-root>/<session>/manifest.json` or `preclose.json` is absent.
2. Load the source-health receipt with `load_receipt(…, expected_type="source_health")`;
   refuse (exit 2) if its `evaluation_session != session` or its
   `scope != scope_identity()` (the data gate would otherwise write a receipt
   the door rejects at F2).
3. Call `h7_schwab_data_gate.evaluate(as_of, close_dir=<close-dir>, chain_dir=<chain-dir>, manifest_path=<reports-root>/<session>/manifest.json, receipt_path=<reports-root>/<session>/preclose.json)` (F7 — **flat chain dir, never `<chain-dir>/<session>`**, R1-1). Whole-universe: never pass `scope=` or `symbols=` (F5).
4. If the result is the package-invalid shape (`audit_receipt.valid is False`,
   `_package_no_go`), print the error and exit 2 without writing. Reason
   (R1-15): `build_receipt` cannot build it — `validate_receipt_scope_closure`
   raises `data-gate result lacks a verified Schwab package`
   (`h7_schwab_data_gate.py:44-51,104-108`); this is not a policy choice.
5. `receipt = build_receipt(result, source_health_receipt=…, source_health_receipt_path=…)` (F6) — build BEFORE the quote-age step (R1-3).
6. `evaluate_schwab_quote_age(data_gate_receipt=receipt, included_symbols=load_registered_cohort().included)` (F13) and PRINT its verdict per name. Mode A is display only and must not alter the receipt; in Mode B (an owner-typed absolute constant exists) an over-threshold included name is reported and the tool exits 1 — it still writes the receipt unchanged, because the arming gate is a post-registration obligation, not a registration input (spec §"Quote-age obligation").
7. Write to the Schwab namespace (R1-5): `write_artifact(result, reports_dir=<output-root>)` → `<output-root>/<scope_id>/<session>.json`, and `write_immutable_receipt(receipt, <output-root>/<scope_id>/receipts/<session>.json)`. **Never** `reports/h7_data_gate/…`: that path is the legacy lane's, `write_artifact` would `FileExistsError` against a legacy artifact of the same session, and `daily_ritual.sh:188-195` would silently adopt a Schwab receipt as the legacy verdict.
8. Print `immutable receipt <path>` on its own line (the ritual's sentinel, `daily_ritual.sh:186`), the per-name verdicts, `whole_universe_verdict`, and the included-subset verdict computed the way the guard does (`h7_activation_guard.py:176-180`), with the cohort from `load_registered_cohort()` — never a hard-coded list (R1-14).
9. Exit code per owner decision **D-5** (default below): 0 when every INCLUDED name is GO; 1 when any included name is NO_GO (excluded NO_GO alone does not fail); 2 on invalid invocation / no package / unverifiable package / unlinked source receipt. Never write on exit 2. Print both verdicts so the divergence from the legacy CLI's whole-universe rule (`h7_data_gate.py:893`) is visible on every run.
10. **No network. No cache write. No ledger write. No `data/` write. No tree-hygiene check here** — the door already refuses a dirty tree (F4), and the untracked receipt this tool writes is committed by WP-B.
11. Backup coverage (R1-5): add `Path("reports/h7_data_gate_schwab")` to `BACKUP_PATHS` (`tools/h7_forward_backup.py:61-72`) and extend the restore-check scan (`:361-364`) with `reports/h7_data_gate_schwab/*/receipts/*.json`. `tools/h7_forward_backup.py` is outside the closure (F14).

Acceptance tests (`tests/test_h7_schwab_data_gate_receipt.py`), reusing the
persistent real-package fixture from `tests/test_h7_schwab_window_registration.py`
(`_verified_data_gate_receipt()` begins at `:96`; note the fixture builds a flat
chain dir — mirror it, R1-1):

- happy path: writes a receipt that `h7_data_gate.validate_durable_receipt` accepts, whose `evidence_mode` is `REAL-H7-SCHWAB-PRECLOSE-AUDIT`, linked to the given source receipt; `tools.h7_schwab_manual_activate._validate_receipt_chain` accepts the pair together with a fixture backup receipt; artifact and receipt land under `reports/h7_data_gate_schwab/<scope_id>/…` and nothing is written under `reports/h7_data_gate/`;
- refuses (exit 2, nothing written) when the source receipt's session or scope mismatches; when no package exists for the session (`NO_PACKAGE_FOR_SESSION`);
- refuses (exit 2, nothing written) on a tampered manifest / missing parquet (`SchwabChainManifestError` path);
- exit 1 when an included name is NO_GO while an excluded name's NO_GO alone still exits 0; the cohort in the test comes from a fixture `load_registered_cohort` patch, not a literal;
- quote-age: a test that passes the RAW result to `evaluate_schwab_quote_age` and asserts `QUOTE_AGE_EVIDENCE_INVALID` (documents R1-3), then the built-receipt path asserts Mode A output present and non-blocking; Mode B (fixture config constant) reports over-threshold and exits 1 with the written receipt bytes unchanged;
- `--as-of 2026-09-08 ⇒ session 2026-09-04` (the "strictly before" rule on a trading-day `as_of`, R1-15);
- backup: a restore-check over a temp tree containing only a `reports/h7_data_gate_schwab/<scope>/receipts/<s>.json` receipt counts it (`data_gates >= 1`).

### WP-B — `tools/h7_activation_day.sh`: the one-shot chain, ops checkout only

Zsh (the repo's wrappers are zsh; see `daily_ritual.sh` shebang), lives in
`tools/`, mirrors the alignment guard of `tools/schwab_chain_capture.sh` (F15).

0. **Preconditions — nothing is written until all pass** (each a refusal with a one-line reason):
   - repo root resolved from the script's own path (`$0`), like the wrappers;
     any other checkout requires `--allow-checkout <path>` (R1-12; no plist parsing);
   - branch is `main`; `origin/main` fetched with the wrapper's bounded timeout;
     HEAD equals `origin/main` OR is ahead only by evidence-only commits per the
     wrapper's own `alignment_divergence_is_evidence_only` rule (copy the
     function; do not loosen it). Evaluated ONCE, here, before any artifact
     (R1-12) — the evidence commit in step 5 will move HEAD ahead afterwards by
     design;
   - `git status --porcelain` EMPTY **including untracked** — byte-identical to
     `_code_state()` (F4, R1-2). If dirty, print the paths and the exact
     remedy: if every path is under the ritual's `DATA_TIER_PATHS` (F15), offer
     `--stage-routine-evidence` which stages exactly those paths and commits
     with the ritual's data-tier message prefix; anything else is an owner
     problem and the script stops;
   - `session = evaluation_session(today)`; refuse `NO_PACKAGE_FOR_SESSION` if
     `reports/schwab_chains/<session>/{manifest.json,preclose.json}` are absent
     (F11, R1-6) — this is the check that would have stopped 2026-09-08 before
     writing anything;
   - Schwab token-age check (`options_researcher.schwab_token_age`) not `EXPIRED`;
   - `.env` sourced for the two `RESTIC_*` names only (F10); never echo values.
   - Feasibility receipt (R1-7): compute `source_hash(paths=FEASIBILITY_SOURCE_PATHS)`
     at HEAD; if it equals the `code_sha`/source-hash recorded in the newest
     `reports/h7_forward_schwab/*-feasibility-cohort9.json`, reuse that file;
     otherwise regenerate with
     `tools/h7_schwab_feasibility.py --symbols <load_registered_cohort().included> --output reports/h7_forward_schwab/<date>-feasibility-cohort9.json`
     and include it in the step-5 commit.
1. `python -m options_researcher.h7_source_health --as-of <today>` (F9; `--as-of`
   mandatory, R1-8). Parse `receipt=`. **Ignore the exit code.** Read the
   receipt; if any name in `load_registered_cohort().included` has
   `symbols[<sym>].healthy == false`: print the names and the
   `tools/h7_refresh_earnings.py` usage, and STOP (exit 1). The chain must not
   continue to produce a data-gate receipt the door will refuse. (The
   source-health receipt just written is immutable and stays; it is committed
   by a `--commit-partial` flag only if the owner asks, default no.)
2. WP-A with that source receipt. Stop on non-zero.
3. *(Dropped — R1-4.)* The watcher is not run: it cannot validate Schwab
   evidence (F8) and is inside the closure. The script prints one line saying
   so and pointing at owner item D-6.
4. `tools/h7_forward_backup.py backup --completed-session <session>` then
   `restore-check --backup-receipt <path> --completed-session <session>`
   (F10). Stop unless `verification.ok`. Backup runs AFTER the receipts exist
   because `BACKUP_PATHS` and the restore-check scan include them.
5. **Evidence commit (R1-2).** Exactly one `git add` loop over an allow-list
   consisting of: the source-health receipt path, the WP-A artifact + receipt
   paths, the backup + restore-check receipt paths, the feasibility receipt if
   regenerated, and the step-6 index — each `git add` checked for non-zero exit
   OR non-empty stderr (Brief 38 R1-1 precedent), then one
   `git commit -m "evidence(h7): activation-day receipts <session>"`. Never
   push; print `git -C <repo> push origin main` as the realign command the
   wrapper itself prints (F15). All committed paths fall under `EVIDENCE_ALLOW`
   after this brief's wrapper edits (Scope IN) — assert that in the shell test.
6. Print, verbatim, the activation command with `--source-health-receipt`,
   `--data-gate-receipt`, `--backup-restore-receipt`, `--completed-session`,
   `--activation-spec`, `--included-symbols <cohort>` and `--evidence <template>`
   filled in, and `<OWNER TYPES>` for `--owner-typed-spec-sha256` and every
   owner field. Print `shasum -a 256 docs/superpowers/specs/2026-09-02-h7-schwab-activation-spec.md`
   so the owner can compare what they reviewed — the owner still types it.
   **Evidence template (R1-11):** write
   `.tmp/h7_activation_day/<date>-evidence.template.json` with every
   `EVIDENCE_FIELDS` key (`h7_schwab_window_registration.py:227-245`): the
   machine-derivable ones filled (`feasibility_receipt` = the receipt object,
   `feasibility_receipt_hash`, `code_commit` = HEAD after step 5,
   `last_historical_manifest_receipt_hash` from `reports/schwab_chains/<session>/manifest.json`,
   the source/data fields `_assemble_evidence` fills at `h7_schwab_manual_activate.py:150-163`),
   the rest as `"<OWNER TYPES>"`. Print, on its own line: `EVIDENCE TEMPLATE IS
   INCOMPLETE — complete every <OWNER TYPES> field before use`. The script
   **never** invokes `tools/h7_schwab_manual_activate.py`.
7. Write a plain-text run log to `.tmp/h7_activation_day/<date>_<HHMM>.log` and
   a JSON index of receipt paths + hashes to
   `reports/h7_forward_schwab/<date>-activation-day-receipts.json` (not
   immutable; an index, not evidence; committed in step 5).

Acceptance: a shell test in `tests/test_h7_activation_day.py` modelled on the
zsh harness in `tests/test_daily_ritual_provenance.py` (Brief 38 — `zsh =
shutil.which("zsh")` + `skipTest`; hermetic git env: `GIT_CONFIG_GLOBAL`/
`GIT_CONFIG_SYSTEM`=devnull, `HOME`=tmpdir, repo-local identity,
`core.hooksPath=`; R1-15 — there is no `tests/test_daily_ritual_staging.py`).
Python entry points are stubbed by prepending a fake `uv` to `PATH` that
dispatches on the module/tool name and writes fixture receipts. Assert:
refusal on untracked file / HEAD behind origin / non-evidence divergence /
expired token / missing package, each BEFORE any file is written; stop after
step 1 when a cohort name is unhealthy regardless of the tool's exit code;
correct ordering; exactly one `git add` site and one `git commit` site (the
provenance test's mutation-verb regexes, `tests/test_daily_ritual_provenance.py`,
run against this script); no `push`; the printed activation command contains
no owner value; every committed path matches the (edited) `EVIDENCE_ALLOW`.
Document the procedure in `docs/h7-forward-operations.md` under "Activation
day (Schwab)", including the D−1 package requirement and the realign push.

### WP-C — Pre-close capture refuses non-trading days

`options_researcher/schwab_chain_capture.py`: derive `session` from `now_ny`
**before** `_default_client()` is constructed (today `:399` follows `:397`,
F12; precedent `tests/test_schwab_chain_capture.py:216
test_invalid_session_refuses_before_default_client_construction`). If
`data.cache_runner.trading_days(session, session)` is empty, print exactly
`schwab_chain_capture refused: NOT_A_TRADING_SESSION <session>` at line start
and return 1 (R1-9 — the wrapper's `CRITICAL: SCHWAB CHAIN REFUSED …` alert is
composed from that prefix at `tools/schwab_chain_capture.sh:150`; do not invent
a new top-level string). Write no manifest / receipt / fact; the first-write-wins
slot `_write_parquet_once` is never reached (R1-10). Keep the existing timing
tolerance untouched. Mirror the check defensively in `tools/schwab_chain_capture.sh`
before it touches auth, with the same output line. Add Labor Day (2026-09-07)
and Good Friday cases to `tests/test_schwab_chain_capture.py` (one file, not a
family), mirroring the named precedent test. The 2026-09-07 package already on
disk (tracked in `863eff2`) is NOT deleted or edited; WP-C's PR body must
state that `evaluation_session()` never selects it (F11) and that it is inert
for H7.

## Owner decisions (not for Codex)

- **D-1 (blocking, and not a code task): the earnings gating store.**
  Run-verified 2026-09-08: 7 of 15 names healthy; cohort names **AMZN, MSFT,
  NOW, TEM are UNHEALTHY** (inferred 45-day post-report grace within 5
  sessions of expiring or expired); AMD, ET, CEG, VST, PLTR go stale between
  2026-09-17 and 2026-09-21. The door requires all nine healthy on the same
  session (F5). Fix = one confirmed next-report assertion per name via
  `tools/h7_refresh_earnings.py append-raw … && promote …` from a company
  IR/PR or SEC source (owner-provided evidence by design). Inference: the
  nine report late Oct / early Nov; dates are usually announced 3–5 weeks
  ahead, so the earliest realistic activation window is **early-to-mid
  October 2026**, after the last of the nine announces. Decide whether an
  agent may gather the URLs and draft the `append-raw` lines for you to run.
- **D-2: the ritual fence.** Brief 11 §6.2 fences source health + data gate
  behind `h7_active`. After WP-B exists this is tolerable (activation day
  produces them by hand). Alternative: let region A run under data-tier
  authority once `exact_session_source_active` is true, so receipts exist
  every day. That is a governance change to `data/ritual_authority.py`; it
  is NOT in this brief.
- **D-3: the 2026-09-07 holiday package.** Leave the bytes (append-only), or
  record a one-line fact classifying it `NON_SESSION_CAPTURE`. Either is fine;
  WP-C prevents a repeat.
- **D-4 (unchanged from the 09-02 close-out §5.1): research-refresh keying.**
- **D-5 (R1-14): what exit 0 means for the Schwab data-gate command.** The
  legacy CLI exits 0 only on a whole-universe GO (`h7_data_gate.py:893`). The
  activation door only needs the INCLUDED nine GO (F5). Recommended default,
  written into WP-A.9: exit 0 = included-nine GO, with the whole-universe
  verdict printed beside it every run. Alternative: keep the legacy rule, in
  which case the six excluded `EARNINGS-UNKNOWN` names make exit 0 impossible
  and WP-B must ignore the exit code the way it ignores source-health's. Veto
  by amendment; Codex builds the default unless told otherwise at dispatch.
- **D-6 (R1-4): the post-activation daily procedure has a hole.** Once the
  window is live, the ritual's full-tier chain runs the LEGACY data gate
  against the frozen ThetaData cache (starved) and a watcher that cannot bind
  Schwab evidence (F8). Closing it means a Schwab-aware watcher binding —
  `h7_watch.py` is inside the feasibility closure, so that brief invalidates
  the feasibility receipt and needs its own regeneration. Decide whether that
  brief is written before or after activation. Not in this brief.

## Dispatch prompt (paste to Codex after the round-2 review passes)

> You are executing Codex brief 40 in `~/options-validator`:
> `docs/superpowers/plans/2026-09-08-40-h7-activation-day-receipt-chain-codex-brief.md`
> (rev 2). Read it fully, then `reports/2026-09-08-h7-receipt-regeneration-status.md`
> and both adversarial-review receipts (`reports/2026-09-08-brief-40-adversarial-review-round{1,2}.md`);
> every `R1-n` tag in the brief is a finding you must close as written, not
> reinterpret. Work on a new branch `codex/brief-40-activation-day-chain` from
> `origin/main`, in a worktree under `.tmp/worktrees/brief40` (owner rule
> 2026-08-03). Implement WP-A, WP-B, WP-C with TDD, inside the brief's Scope IN
> list only; the Scope OUT list is binding — in particular do not edit
> `data/ritual_authority.py`, any validator's acceptance logic, `data/earnings/*`,
> `ledger/*`, `options_researcher/h7_watch.py`, or any module inside
> `feasibility_source_closure()` (run it first and list the 50 paths in the PR
> body). The chain cache is FLAT (F7). Gates before the draft PR:
> `uv run python -m unittest discover -s tests` exit 0; `uv run ruff check .`
> exit 0; `uv run pyright` exit 0; `ruff format --check` on files you touched.
> Open the PR as a DRAFT; the body must carry the closure listing, the exact
> commands you ran, the D-5 default you built, and the statement that no
> receipt, cache, ledger or earnings row was written. Do not merge, do not sync
> the ops checkout, do not run anything in `~/options-validator-ops`.

## Gates (final)

```bash
uv run python -m unittest discover -s tests   # exit 0
uv run ruff check .                            # exit 0
uv run ruff format --check <files touched>     # exit 0
uv run pyright                                 # exit 0
```
