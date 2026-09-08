# Codex brief 40 — H7 activation-day receipt chain: the missing Schwab data-gate command and the one-shot runbook

**Date:** 2026-09-08 (rev 1 — NOT yet adversarially reviewed; see Status)
**Author:** Claude (orchestrating session; receipt-regeneration attempt, 2026-09-08)
**Executor:** Codex (Sol, high reasoning — as briefs 07/37/38; owner may substitute at dispatch)
**Status:** DRAFT FOR REVIEW — the owner asked for the receipt regeneration to be
dispatched; this brief IS the dispatch, but per repo practice (briefs 36/38) it
must pass one independent adversarial review round before Codex starts. The
reviewer's receipt goes to `reports/2026-09-08-brief-40-adversarial-review-round1.md`.
Dispatch, landing and ops sync remain the owner's.
**Provenance:** file:line constraints are Repo-verified against `origin/main`
@ `863eff2` unless a sentence carries its own label. "Run-verified" facts were
executed 2026-09-08 in the ops execution checkout (`~/options-validator-ops`) or
the primary checkout on a clean tree at the same commit. Sentences labelled
**Inference** are the author's reading of the code, not a file fact.
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
   (`options_researcher/h7_schwab_window_registration.py:640` and `:699`). The
   only CLI, `python -m options_researcher.h7_data_gate` (`h7_data_gate.py:804-893`),
   evaluates the ThetaData store `.cache/chains` (edge 2026-07-27, frozen by
   OD-2/OD-4) in the legacy evidence mode. The Schwab evaluator
   `h7_schwab_data_gate.evaluate()` (`h7_schwab_data_gate.py:134-200`) has
   **no production caller** — `grep -rn h7_schwab_data_gate options_researcher/ tools/`
   finds only the quote-age gate importing two helpers (`h7_schwab_quote_age_gate.py:21-24`)
   and `h7_data_gate.py:522,601` importing the closure validator. The five
   remaining callers are tests.
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
   source-health / data-gate / watcher / backup receipts are an
   **activation-day** procedure, run after that morning's ritual and before the
   next, immediately followed by the owner's activation command.

What this brief delivers: (WP-A) the missing command; (WP-B) one shell entry
point that runs the whole activation-day chain in the ops checkout and prints
the exact owner command with every path filled in; (WP-C) a calendar refusal
in the pre-close capture, because the wrapper captured a full "ok" package on
Labor Day 2026-09-07 (market closed).

What this brief does NOT do: it does not register anything, does not touch
`data/ritual_authority.py`, does not weaken any validator to accept stale
receipts, does not build the quote-age *blocking* gate (Brief 36 WP-E Mode A
stands: display-only until an owner-typed absolute threshold exists), and
does not edit `data/earnings/*` (see Owner decision D-1).

## Repo-verified facts the executor must not contradict

| # | Fact | Where |
|---|---|---|
| F1 | Activation CLI takes `--source-health-receipt`, `--data-gate-receipt`, `--backup-restore-receipt`, `--completed-session`, `--activation-spec`, `--owner-typed-spec-sha256`, `--included-symbols`, `--evidence`, plus owner-typed fields at use time | `tools/h7_schwab_manual_activate.py:343-351` |
| F2 | Receipt chain check: `source.receipt_hash == data.source_health_receipt_hash`, data receipt's `source_health_receipt_path` must be the same file, data receipt revalidated by `h7_data_gate.validate_durable_receipt` | `tools/h7_schwab_manual_activate.py:120-158` |
| F3 | Backup receipt: `receipt_type == "backup_restore"`, `scope == scope_identity()`, `completed_session` equal to the CLI arg, `verification.ok is True` | `tools/h7_schwab_manual_activate.py:108-117` |
| F4 | Door rechecks source-health all-healthy and data-gate GO at append time and requires a clean tree at HEAD | `h7_schwab_window_registration.py:904-975` |
| F5 | Trim mode: full 15-name receipts, every INCLUDED name healthy (source) and per-symbol GO (data gate); excluded names may be NO_GO | `options_researcher/h7_activation_guard.py:109-240`; spec `docs/superpowers/specs/2026-09-02-h7-schwab-activation-spec.md` |
| F6 | Durable data-gate receipt = `h7_data_gate.build_receipt(result, source_health_receipt=…, source_health_receipt_path=…)` then `research.receipts.write_immutable_receipt(receipt, path)`; the ritual's expected path is `reports/h7_data_gate/<scope_id>/receipts/<session>.json` | `h7_data_gate.py:610-668`, `:879-887`; `research/receipts.py:94`; `tools/daily_ritual.sh:157` |
| F7 | Schwab evaluation: `h7_schwab_data_gate.evaluate(requested_run_date, close_dir=, chain_dir=, manifest_path=, receipt_path=, scope=None, symbols=None)`; chain dir is `.cache/schwab_chains/<session>/`, manifest+capture receipt under `reports/schwab_chains/<session>/{manifest.json,preclose.json}` | `h7_schwab_data_gate.py:134-200`; `h7_schwab_window_registration.py:35-37` (`CACHE_NAMESPACE`, `SESSION_CHAIN_CONVENTION`) |
| F8 | Watcher requires `--data-gate-receipt`; validates scope, session, per-included GO, and the source-health link; it does not inspect `evidence_mode` | `options_researcher/h7_watch.py:150-186`, `:422-470` |
| F9 | Source-health CLI writes its receipt unconditionally to `reports/h7_receipts/<scope_id>/source_health/<session>.json`; `--write-receipt` overrides the path | `options_researcher/h7_source_health.py:197-293` (Run-verified: the 2026-09-08 dry run wrote `…/2026-09-04.json`) |
| F10 | Backup/restore tool needs `RESTIC_REPOSITORY` and `RESTIC_PASSWORD_FILE`/`_COMMAND` in the environment; it does not load `.env` itself | `tools/h7_forward_backup.py:141-147`; no `dotenv` import (grep) |
| F11 | `evaluation_session()` uses the XNYS calendar; 2026-09-07 (Labor Day) is never an evaluation session; the newest verified pre-close package is 2026-09-03; 2026-09-04 was refused pre-auth ("could not refresh origin/main") | `options_researcher/h7_watch.py:236`; `reports/schwab_chains/`; `.tmp/schwab_chain_capture/2026-09-04_1545.log` (ops) |
| F12 | The pre-close capture has **no exchange-calendar check**: `grep -n -i 'calendar\|holiday\|trading_days' options_researcher/schwab_chain_capture.py tools/schwab_chain_capture.sh` returns nothing; the plist fires Weekday 1–5 | Run-verified; `~/Library/LaunchAgents/com.carsyn.options-validator.schwab-chain-preclose.plist` |
| F13 | Quote-age gate is callable, unwired, Mode A (no absolute threshold ⇒ `AWAITING_OWNER_THRESHOLD`, bans nothing) | `options_researcher/h7_schwab_quote_age_gate.py:1-8`, `:157-175` |
| F14 | Editing anything inside `FEASIBILITY_SOURCE_PATHS` / the transitive closure invalidates the feasibility receipt regenerated today (`reports/h7_forward_schwab/2026-09-08-feasibility-cohort9.json`, code `863eff2`) | `h7_schwab_window_registration.py:38-60`, `:160-175` |

F14 is the trap for this brief: **WP-A must not import into, or edit, any
module inside the feasibility closure.** The new command lives in `tools/`
and imports `options_researcher.h7_schwab_data_gate`, `h7_data_gate`,
`h7_source_health`, `research.receipts` — check `feasibility_source_closure()`
before adding an import; if a needed module is inside the closure, the receipt
must simply be regenerated on activation day too (WP-B step 0 does that), and
the brief's acceptance says so out loud rather than hiding it.

## Work packages

### WP-A — `tools/h7_schwab_data_gate_receipt.py`: produce the durable Schwab data-gate receipt

One operator command, run from the checkout root that holds the caches:

```bash
uv run python tools/h7_schwab_data_gate_receipt.py \
  --as-of YYYY-MM-DD \
  --source-health-receipt reports/h7_receipts/h7-forward-15-v1/source_health/<session>.json \
  [--chain-root .cache/schwab_chains] [--reports-root reports/schwab_chains] \
  [--close-dir .cache/underlying] \
  [--write-receipt reports/h7_data_gate/h7-forward-15-v1/receipts/<session>.json]
```

Behaviour:

1. Resolve `session = evaluation_session(as_of)` (F11). Refuse (exit 2, no
   artifact) if `session` is not an XNYS trading day (belt-and-braces with WP-C).
2. Load the source-health receipt with `load_receipt(…, expected_type="source_health")`;
   refuse if its `evaluation_session != session` or its `scope != scope_identity()`
   (the data gate would otherwise write a receipt the door rejects at F2).
3. Call `h7_schwab_data_gate.evaluate(as_of, close_dir=…, chain_dir=<chain-root>/<session>, manifest_path=<reports-root>/<session>/manifest.json, receipt_path=<reports-root>/<session>/preclose.json)` (F7). Whole-universe scope, never `symbols=`: the door demands 15-name evidence (F5).
4. Call `h7_schwab_quote_age_gate.evaluate_schwab_quote_age(data_gate_receipt=<result>, included_symbols=<all 15>)` (F13) and PRINT its verdict per name. In Mode A this is display only and must not alter the gate result; in Mode B (an owner-typed absolute constant exists) an over-threshold name is reported and the tool exits 1 — it still does not edit the receipt, because the arming gate is a post-registration obligation, not a registration input (spec §"Quote-age obligation").
5. `build_receipt(result, source_health_receipt=…, source_health_receipt_path=…)` then `write_immutable_receipt` to the ritual's expected path (F6) unless `--write-receipt` says otherwise. Also `write_artifact(result, reports_dir=…)` exactly as the legacy CLI does (`h7_data_gate.py:880`), so the human-readable artifact and the immutable receipt sit where the ritual and dashboard already look.
6. Print `immutable receipt <path>` on its own line — the same sentinel the ritual greps (`daily_ritual.sh:187`) — plus the per-name verdicts, `whole_universe_verdict`, and the included-nine subset verdict computed the way the guard does (`h7_activation_guard.py:180-186`).
7. Exit 0 on GO for all included names; 1 on any included NO_GO; 2 on invalid invocation / unverifiable package / unlinked source receipt. Never write on exit 2.
8. **No network. No cache write. No ledger write. No `data/` write.** The tool must refuse to run if `git status --porcelain` is non-empty for tracked files? — NO: do not add that check here; the DOOR already refuses a dirty tree (F4), and an untracked receipt written by this very tool would trip a naive check. Leave tree hygiene to WP-B.

Acceptance tests (`tests/test_h7_schwab_data_gate_receipt.py`), reusing the
persistent real-package fixture pattern from `tests/test_h7_schwab_window_registration.py:87-140`:

- happy path: writes a receipt that `h7_data_gate.validate_durable_receipt` accepts, whose `evidence_mode` is `REAL-H7-SCHWAB-PRECLOSE-AUDIT`, linked to the given source receipt; `tools/h7_schwab_manual_activate._validate_receipt_chain` accepts the pair together with a fixture backup receipt;
- refuses (exit 2, nothing written) when the source receipt's session or scope mismatches;
- refuses (exit 2) on a tampered manifest / missing parquet (`SchwabChainManifestError` path ⇒ `_package_no_go` is NOT written as a receipt — an all-NO_GO package receipt has no use and would be immutable);
- exit 1 when an included name is NO_GO while an excluded name's NO_GO alone still exits 0;
- Mode A quote-age output present and non-blocking; Mode B (fixture config constant) reports over-threshold and exits 1 without changing the written receipt bytes;
- non-trading `--as-of` resolution (e.g. `--as-of 2026-09-08` ⇒ session 2026-09-04) is exercised; a session with no package refuses.

### WP-B — `tools/h7_activation_day.sh`: the one-shot chain, ops checkout only

Zsh (the repo's wrappers are zsh; see `daily_ritual.sh` shebang), lives in
`tools/`, mirrors the alignment guard of `tools/schwab_chain_capture.sh`:

0. Preconditions, each a refusal with a one-line reason: cwd is the ops
   checkout (`$PWD` equals the resolved `WorkingDirectory` of the pre-close plist,
   or `--allow-checkout <path>` given); `HEAD == origin/main` after `git fetch`;
   `git status --porcelain` empty for tracked files; the Schwab token-age check
   (`options_researcher.schwab_token_age`) is not `EXPIRED`; `.env` sourced for
   the two `RESTIC_*` names only (F10) — never echo values.
   Then **regenerate the cohort-9 feasibility receipt** at this HEAD
   (`tools/h7_schwab_feasibility.py --symbols <nine> --output reports/h7_forward_schwab/<date>-feasibility-cohort9.json`)
   because F14 makes any code landing since 2026-09-08 invalidate today's.
1. `python -m options_researcher.h7_source_health --as-of <today>` (F9).
   Parse `receipt=`. If any of the nine included names is unhealthy: print the
   names and the `h7_refresh_earnings.py` usage, and STOP (exit 1). The chain
   must not continue to produce a data-gate receipt that the door will refuse.
2. WP-A with that source receipt. Stop on non-zero.
3. `python -m options_researcher.h7_watch --data-gate-receipt <path>` (F8) —
   alerts only; record exit code, do not stop on it (the watcher refusing is
   information for the owner).
4. `tools/h7_forward_backup.py backup --completed-session <session>` then
   `restore-check --backup-receipt <path> --completed-session <session>`
   (docs/h7-forward-operations.md:37-50). Stop unless `verification.ok`.
5. Print, verbatim and copy-pasteable, the activation command with every
   `--…-receipt`, `--completed-session`, `--activation-spec` and
   `--included-symbols AMD AMZN CEG ET MSFT NOW PLTR TEM VST` filled in, and
   placeholders `<OWNER TYPES>` for `--owner-typed-spec-sha256` and every
   owner field. Print `sha256sum docs/superpowers/specs/2026-09-02-h7-schwab-activation-spec.md`
   so the owner can compare what they reviewed — but the owner still types it.
   **The script never invokes `tools/h7_schwab_manual_activate.py`.**
6. Write a plain-text run log to `.tmp/h7_activation_day/<date>_<HHMM>.log` and
   a JSON summary of receipt paths + hashes to
   `reports/h7_forward_schwab/<date>-activation-day-receipts.json` (not
   immutable; it is an index, not evidence).

Acceptance: a shell test in the style of `tests/test_daily_ritual_staging.py`
(Brief 38) that runs the script against a temp repo with stubbed python
entry points and asserts: refusal on dirty tree / HEAD drift / expired token;
stop after step 1 when a cohort name is unhealthy; correct ordering; the
printed activation command contains no owner value; no `git add`/`commit`
inside the script. Document the procedure in `docs/h7-forward-operations.md`
under a new heading "Activation day (Schwab)".

### WP-C — Pre-close capture refuses non-trading days

`options_researcher/schwab_chain_capture.py` (and, defensively, the wrapper
`tools/schwab_chain_capture.sh` before it touches auth): if the target session
is not in `data.cache_runner.trading_days(session, session)` (F12), classify
as `SCHWAB CHAIN REFUSED` with reason `NOT_A_TRADING_SESSION`, exit non-zero,
write no manifest / receipt / fact, and do not consume the first-write-wins
slot. Keep the existing timing tolerance untouched. Extend the failure
taxonomy test (`tests/test_schwab_chain_capture*.py`) with a Labor Day case
and a Good Friday case. The 2026-09-07 package already on disk is NOT deleted
or edited (append-only evidence); WP-C's PR body must state that
`evaluation_session()` never selects it (F11) and that it is inert for H7.

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

## Dispatch prompt (paste to Codex after the review round passes)

> You are executing Codex brief 40 in `~/options-validator`:
> `docs/superpowers/plans/2026-09-08-40-h7-activation-day-receipt-chain-codex-brief.md`.
> Read it fully, then `reports/2026-09-08-h7-receipt-regeneration-status.md`
> and the adversarial-review receipt it names. Work on a new branch
> `codex/brief-40-activation-day-chain` from `origin/main`, in a worktree under
> `.tmp/worktrees/brief40` (owner rule 2026-08-03). Implement WP-A, WP-B, WP-C
> with TDD; do not touch `data/ritual_authority.py`, any validator's acceptance
> logic, `data/earnings/*`, `ledger/*`, or any module inside
> `feasibility_source_closure()` (run it first and list the closure in the PR
> body). Gates before the draft PR: `uv run python -m unittest discover -s tests`
> exit 0; `uv run ruff check .` exit 0; `uv run pyright` exit 0; `ruff format --check`
> on files you touched. Open the PR as a DRAFT; the body must carry the F14
> closure listing, the exact commands you ran, and the statement that no
> receipt, cache, ledger or earnings row was written. Do not merge, do not sync
> the ops checkout, do not run anything in `~/options-validator-ops`.

## Gates (final)

```bash
uv run python -m unittest discover -s tests   # exit 0
uv run ruff check .                            # exit 0
uv run ruff format --check <files touched>     # exit 0
uv run pyright                                 # exit 0
```
