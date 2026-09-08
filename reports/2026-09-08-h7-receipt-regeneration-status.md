# H7 Schwab receipt regeneration — what was regenerated, what is blocked, and why

**Date:** 2026-09-08 (morning, after the 09:09 ritual and before the 15:45 capture)
**Owner directive:** in-session 2026-09-08 — *follow through on all open items;
dispatch the receipt regeneration* (the step the README, PROJECT_STATE, and the
2026-09-02 close-out all name as next after Brief 36 landed).
**Branch:** `claude/h7-receipt-regeneration-2026-09-08` (from `origin/main` @ `863eff2`)
**Status:** partial by necessity — one of the four receipts is regenerated, one
is a dated health check that records a blocker, two cannot be produced on
`main` today. Nothing here is a registration, a verdict, or a frozen number.
No ledger was written. Provenance labels: **Repo-verified** = read from the
file at the cited line on `origin/main` @ `863eff2`; **Run-verified** = the
command was executed today in the checkout named; **Inference** = the author's
reading.

---

## The short version (plain language)

The activation door built by Brief 36 (PR #147, merged 2026-09-03) demands four
fresh pieces of evidence before the owner can register the H7 Schwab window:

| # | Evidence | State today | Why |
|---|---|---|---|
| 1 | Cohort-9 feasibility receipt at the post-merge config | **REGENERATED** — `reports/h7_forward_schwab/2026-09-08-feasibility-cohort9.json` | Read-only measurement over the frozen chain cache; re-measured identical to the packet (3 occupancy-constrained, 4.0 unconstrained). |
| 2 | Source-health receipt (earnings provenance, all 15 names) | **PRODUCED, and it says NOT READY** — `reports/h7_receipts/h7-forward-15-v1/source_health/2026-09-04.json` | 7 of 15 names healthy. Four of the nine cohort names (AMZN, MSFT, NOW, TEM) are unhealthy because their next earnings date is not yet in the gating store and the inferred post-report grace has run out. This is a data-maintenance blocker, not a code defect. |
| 3 | Schwab-mode data-gate receipt for one completed session | **CANNOT BE PRODUCED ON `main`** | No operator command writes it. The existing data-gate command reads the frozen ThetaData cache (edge 2026-07-27) and reports starved. The Schwab evaluator exists as a library function with test-only callers. |
| 4 | Backup + restore-check receipt for the same completed session | **NOT RUN** | Pointless without #3: the door binds all three to one `completed_session`, and the data-gate receipt hashes close-price files that the ritual refreshes every morning, so #2–#4 must be produced on activation day itself. |

So "regenerate the receipts" is not a one-time chore that this session could
finish. It is an **activation-day procedure** that needs one missing command.
Brief 40 (`docs/superpowers/plans/2026-09-08-40-h7-activation-day-receipt-chain-codex-brief.md`)
specifies that command and the one-shot runbook around it, and is the dispatch.

---

## 1. Feasibility receipt — regenerated (Run-verified)

Command, run in `~/options-validator` on `origin/main` @ `863eff2` with a clean
tree (the tool records `code_sha`):

```bash
uv run python tools/h7_schwab_feasibility.py \
  --symbols AMD AMZN CEG ET MSFT NOW PLTR TEM VST \
  --output reports/h7_forward_schwab/2026-09-08-feasibility-cohort9.json
```

Tool output: `passes=4/630 base_rate=0.006349206349 expected_entries=4.000000`
and `NO PASS/FAIL DECISION EMITTED; OWNER DECIDES`.

| Field | 2026-08-29 rerun (`V14_REGISTERED_COHORT_9.json`, code `86e8ba6`) | This receipt (code `863eff2`) |
|---|---|---|
| unconstrained expected entries | 4.0 | 4.0 |
| occupancy-constrained (42-session lockout) | 3 | 3 |
| symbol-days | 630 (9 × 70) | 630 |
| config hash | `b86b3188…` | `52501dcb…` (moved by PRs #147, #150, #159 — expected) |

The occupancy-constrained figure of **3** is the quantity the owner's
starvation pre-acceptance priced (packet §4; Brief 36 rev-2 N3). It is
unchanged. The chain cache gained no session for any scope name since
2026-07-27, so nothing else could have moved.

The receipt carries `input_files` hashes and the transitive source closure
(`FEASIBILITY_SOURCE_PATHS`), so **any later merge that touches config.py or
the closure invalidates it again** (Brief 36 round-3 F6, deliberate). It is
valid at `863eff2`.

`tests.test_h7_schwab_feasibility`: 9 tests, OK (Run-verified).

## 2. Source health — produced; records a blocker (Run-verified)

Command, run in the ops checkout `~/options-validator-ops` (same commit
`863eff2`; the tool reads `data/earnings/gating_v3.csv`, which is tracked and
identical in both checkouts):

```bash
uv run python -m options_researcher.h7_source_health --as-of 2026-09-08
```

The tool writes its receipt unconditionally to
`reports/h7_receipts/h7-forward-15-v1/source_health/<evaluation-session>.json`
(`options_researcher/h7_source_health.py:197-293`, Repo-verified). The file
was **moved** (same bytes) from the ops checkout into this branch so the ops
checkout carries no untracked receipt that a later `git pull` would collide
with. Evaluation session `2026-09-04` (last completed XNYS session before
09-08; 09-07 was Labor Day).

Result: `summary: 7/15 healthy; exit 1`. Per name (healthy ⇒ eligible):

| Name | In cohort-9? | Health | Reason (from the tool) |
|---|---|---|---|
| AMD | yes | ok | inferred grace ends 2026-09-18 (9 sessions left) |
| AMZN | yes | **UNHEALTHY** | STALE — inferred grace ends 2026-09-13, 4 sessions left (≤ warn 5) |
| CEG | yes | ok | grace ends 2026-09-20 |
| ET | yes | ok | grace ends 2026-09-18 |
| MSFT | yes | **UNHEALTHY** | STALE — grace ends 2026-09-12, 4 sessions left |
| NOW | yes | **UNHEALTHY** | STALE — grace ended 2026-09-05, 0 sessions left |
| PLTR | yes | ok | grace ends 2026-09-17 |
| TEM | yes | **UNHEALTHY** | STALE — grace ends 2026-09-13, 4 sessions left |
| VST | yes | ok | grace ends 2026-09-21 |
| AVGO, CRWV, IREN, USAR | no (excluded) | UNHEALTHY | next report UNKNOWN, no grace (since 08-21 receipt) |
| NVDA, SMCI | no | ok | grace ends 2026-10-10 / 2026-09-25 |

Mechanism (Repo-verified, `h7_source_health.py:73-166` and `config.py:520,536,576`):
a name with no *live future* confirmed earnings assertion is carried on an
inferred 45-day post-report grace; once fewer than
`H7_SOURCE_HEALTH_WARN_SESSIONS = 5` sessions of grace remain it is flagged
STALE and `healthy` becomes false. The activation guard in trim mode requires
**every included name** healthy in the receipt
(`options_researcher/h7_activation_guard.py:216-240`) and the door rechecks
`source_health_all_healthy` at append time
(`h7_schwab_window_registration.py:967-968`).

**What fixes it:** one confirmed next-report assertion per cohort name,
appended through `tools/h7_refresh_earnings.py append-raw … && promote …`
with a company IR/PR (or SEC) source URL and a `--known-as-of` timestamp. That
is owner-in-the-loop by design (the tool's own docstring: *"from owner-provided
evidence (no network, no crawler)"*). Timing reality (Inference): these nine
names report late October / early November; companies typically announce the
date three to five weeks ahead, so the store will most likely fill during the
last week of September and first half of October. **Until all nine are
confirmed on the same session, the door cannot open.** The other five cohort
names go STALE between 2026-09-17 and 2026-09-21, so by late September the
whole cohort will read unhealthy until the dates land.

No `data/earnings/*` file was modified by this session.

## 3. Schwab data-gate receipt — no producer on `main` (Repo-verified)

What the door needs: a durable `data_gate` receipt whose `evidence_mode` is
`REAL-H7-SCHWAB-PRECLOSE-AUDIT` (`h7_schwab_window_registration.py:640,699`),
linked to the source-health receipt of the same session, covering all 15 names,
per-symbol GO for the nine included (`h7_activation_guard.py:180-186`; spec
`docs/superpowers/specs/2026-09-02-h7-schwab-activation-spec.md`).

What exists:

- `python -m options_researcher.h7_data_gate` (`h7_data_gate.py:804-893`) runs
  the ThetaData path against `.cache/chains`, whose edge is 2026-07-27. The
  09-08 ritual log states it plainly: *"chain-dependent lanes are STARVED: no
  exact-session chain for 2026-09-04 (cache frozen at 2026-07-27; OD-2/OD-4
  forbid refill)"*. Its receipts would carry the wrong evidence mode anyway.
- `h7_schwab_data_gate.evaluate()` (`h7_schwab_data_gate.py:134-200`) verifies
  the manifest-bound Schwab package and runs the full H7 row checks in the
  Schwab evidence mode — but its only callers are five test modules
  (`grep -rn h7_schwab_data_gate` over `options_researcher/ tools/`: the quote-age
  gate imports two helpers; nothing calls `evaluate`).
- The ritual's own source-health → data-gate chain
  (`tools/daily_ritual.sh:154-200`) is fenced behind
  `data.ritual_authority require-full`, which fails while `h7_active=False`
  (`data/ritual_authority.py:39,82-83`) — the exact state before registration.
  The 09-08 log: *"H7 lanes: PAUSED — full ritual authority not granted"*.

Brief 36 anticipated this ("fresh source-health and data-gate receipts in the
operator flow", `…-36-…-codex-brief.md:82`) but shipped no operator flow for the
Schwab gate; its WP-E explicitly left the quote-age gate "intentionally unwired
to production". Brief 40 closes the gap.

Which session it will bind to: the newest verified pre-close package is
**2026-09-03** (15/15, launchd). 2026-09-04's capture was refused before auth —
`.tmp/schwab_chain_capture/2026-09-04_1545.log`: *"wrapper REFUSED: could not
refresh origin/main"* — a permanent gap by design. **2026-09-07 (Labor Day,
market closed) has a 15/15 "ok" package** captured at 15:45:14 ET on a closed
market; the capture wrapper checks pre-close timing but no exchange calendar
(`grep -n calendar|holiday|trading_days options_researcher/schwab_chain_capture.py`
returns nothing; plist fires Mon–Fri). `evaluation_session()` uses the XNYS
calendar and will never select 09-07, so the package is inert for H7 — but it
is a stale-quote snapshot labelled as a session, and Brief 40 WP-C adds the
missing calendar refusal.

## 4. Backup + restore-check — deferred to activation day (Repo-verified)

`tools/h7_schwab_manual_activate.py:108-117` requires a `backup_restore`
receipt whose `completed_session` equals the `--completed-session` argument
and whose `verification.ok` is true. `tools/h7_forward_backup.py backup` /
`restore-check` need `RESTIC_REPOSITORY` + `RESTIC_PASSWORD_FILE`, which are
set in the ops checkout's `.env` (names verified, values not read); restic
0.19.1 is installed. The 2026-08-20 drill (`reports/h7_receipts/backup_restore/2026-08-20.json`)
is the template. It is a ~5-minute step and belongs in the activation-day
runbook, not in a standalone PR — running it now for session 2026-09-03 would
produce a receipt that the data-gate step, once it exists, must match to the
day; there is no benefit to taking the snapshot early.

## 5. Why the chain is a same-day procedure (Repo-verified)

`h7_data_gate.validate_durable_receipt` (`h7_data_gate.py:670-751`) re-hashes
every `close:<SYM>` and `chain:<SYM>` input file
(`research/receipts.py:45-54`). The close files are
`.cache/underlying/<SYM>.parquet`, and the 09:09 ritual refreshes them every
trading day ("underlying closes: guarded refresh ran", facts.log
`DATA_PULL 2026-09-08`). A data-gate receipt therefore fails
`data-gate receipt input files changed` the next morning. Consequently the
qualifying receipts 2–4 must be produced **after that morning's ritual and
before the next one**, on the day the owner runs the activation CLI — which is
why the daily ritual was designed to chain them and why Brief 40 packages
them as one command.

## 6. Other open items touched today

- **PR #159 post-landing conflict warning:** the first ritual after the board
  redesign ran 2026-09-08 09:09; `IMMUTABLE_HISTORY_CONFLICT` count in its log
  = 0. Nothing to resolve.
- **Leftover worktrees from the 09-02 close-out** (`.tmp/worktrees/a2-governance-facts`,
  `.claude/worktrees/gracious-neumann-d938c9`): no longer exist
  (`git worktree list` shows only ops, research, and `.tmp/worktrees/brief39`).
  Already cleaned. The one remaining candidate is `.tmp/worktrees/brief39`
  (branch `codex/brief39-board-redesign`, landed via PR #159 squash) plus
  branch `claude/board-redesign-spec-2026-09-06` — owner per-target yes required
  before removal (deletion checklist).
- **Schwab token:** `SCHWAB TOKEN EXPIRES IN 23.9h (2026-09-09 13:22 UTC)`
  (Run-verified via `schwab_token_age.token_expiry_status`). Owner-only re-auth;
  if missed, 09-09's 10:00/13:00/15:45 pulls fail permanently.
- **Loss-bar source audit** (close-out §5 item 2): dispatched as a read-only
  audit; its report lands beside this one as
  `reports/2026-09-08-loss-bar-source-audit.md`.
- **Research-refresh keying** (close-out §5 item 1) and the **Pioneer updater
  zombie leak** (§5 item 6): owner decisions; unchanged.

## 7. Files in this change

| Path | What |
|---|---|
| `reports/h7_forward_schwab/2026-09-08-feasibility-cohort9.json` | new receipt (tool-written, immutable) |
| `reports/h7_receipts/h7-forward-15-v1/source_health/2026-09-04.json` | new receipt (tool-written, immutable; moved from ops checkout) |
| `reports/2026-09-08-h7-receipt-regeneration-status.md` | this report |
| `docs/superpowers/plans/2026-09-08-40-h7-activation-day-receipt-chain-codex-brief.md` | Brief 40 — the dispatch |
| `PROJECT_STATE.md` | status refresh 2026-09-08 |

No code, config, ledger, cache, or `data/earnings/*` change.
