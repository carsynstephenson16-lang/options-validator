# H7 amendment — inferred post-report grace (owner-typed 2026-07-24)

**Status: INACTIVE until owner ratifies and the owner-run ledger
registration is appended; merging this branch is the ratification act.**
Nothing in this branch writes to `ledger/facts.log` — that append is an
owner action, deliberately left undone here (a guard hook also enforces
that no session but the owner's own writes the ledger).

## Trigger

ServiceNow (NOW) reported Q2 2026 earnings on 2026-07-22. By 2026-07-24 its
`h7_source_health` row read `NOW: UNHEALTHY [MISSING] gate=UNKNOWN ...
next report unknown: no live future assertion and no proven report within
the grace window`, and `h7_entry_preflight` printed `REAL ENTRY PATH WOULD
REFUSE: ['NOW']`. NOW is one of the 9 registered entry-cohort names of the
live forward window `h7-forward-15-v1` (`AMD, AMZN, CEG, ET, MSFT, NOW,
PLTR, TEM, VST` — the other 6 watched names are EARNINGS-UNKNOWN-excluded
from the cohort at registration and are a separate, unrelated concern). The
real-entry door in `options_researcher/h7_session.py` (`open_real_session`,
`unhealthy = sorted(name for name in entry_names if
symbols[name].get("healthy") is not True)`, historically ~lines 137–144)
refuses the door for the **whole cohort** the moment any one registered
name is unhealthy — so the entire live window was blocked over NOW simply
having reported, two days prior.

## Why the existing grace mechanism did not cover this

The gate (`options_researcher/h7_earnings.py::earnings_gate`) already had a
post-report grace concept, `H7_EARNINGS_POST_REPORT_GRACE_D = 45`, owner-
ratified 2026-07-10 (`H7_OWNER_DECISIONS_7B01`). But that grace only starts
from a **PROVEN** `status="occurred"` gating-store record — a distinct,
separately-sourced-and-promoted assertion that the report actually
happened (typically an 8-K or IR confirmation, added by hand via
`tools/h7_refresh_earnings.py`). NOW's newest gating assertion
(`data/earnings/gating_v3.csv`, record `G0009`) is a `status="confirmed"`
schedule for `2026-07-22` — the report date was known in advance, but
nobody has yet promoted a distinct occurred record proving it happened.
That promotion work routinely lags the report by days: exactly what
happened here. The pre-amendment rule was deliberate ("Day grace+1 without
a valid future assertion = EARNINGS-UNKNOWN" — config.py comment on
`H7_EARNINGS_POST_REPORT_GRACE_D`) but had the side effect of gating real
entries on unrelated clerical lag, not on any actual uncertainty about
whether NOW reported.

## Owner-typed parameter

Owner message, 2026-07-24, verbatim intent: *"if a company reports
earnings wait 1.5 months to get the new earnings date so the company has
time."* Entered as `config.H7_POST_REPORT_GRACE_DAYS = 45` (1.5 months =
45 calendar days) — a distinct constant from `H7_EARNINGS_POST_REPORT_GRACE_D`
(also 45, coincidentally the same number, but a different owner decision on
a different date governing a different, PROVEN grace path; the two are not
merged so either can be retyped independently in the future without
ambiguity about which decision moved).

## What changes

A symbol now also qualifies for **CLEAR** when:

1. its newest **CONFIRMED** (never merely estimated) gating-store report
   assertion is for a date now in the past,
2. no newer confirmed or estimated **future** report date exists for it,
   and
3. `evaluation_session − past_report_date <= 45` calendar days.

This is an **Inference**, not a Test-verified or Official-source fact:
*US quarterly reporters cannot plausibly report again within 45 days of a
report, so "no imminent earnings" is inferable without a confirmed next
date.* It is explicitly weaker evidence than the existing proven-occurred
grace and is never displayed as an ordinary confirmed-date CLEAR.

### Decision points that change behavior

All of these share one primitive
(`options_researcher/h7_earnings.py::earnings_gate`), so the fix was made
once, at that layer, and every consumer inherits it — this was verified by
reading each consumer before editing, not assumed:

- **`options_researcher/h7_earnings.py::earnings_gate`** — the shared gate
  primitive. Gains the inferred-grace branch (new
  `GATE_REASON_POST_REPORT_GRACE_INFERRED` reason string, distinct from the
  existing "next report known or realized report within grace" success
  reason, so the CLI/receipts/logs can always tell which kind of CLEAR
  fired).
- **`options_researcher/h7_source_health.py::symbol_health`** — the
  observability layer used by the CLI board and every receipt. Gains a
  distinct `coverage="post_report_grace"` (separate from the existing
  proven-occurred `coverage="grace"`), a new `FLAG_GRACE = "GRACE"` board
  flag, and a `grace_started` field so the printed board line reads e.g.
  `NOW: ok gate=CLEAR [MISSING,GRACE] next report UNKNOWN, INFERRED GRACE
  ends 2026-09-05 (elapsed 2d, 30 sessions left) | newest: ...` — never
  confusable with a plain confirmed-date CLEAR line. `healthy` is still
  `gate != UNKNOWN and FLAG_STALE not in flags`, so a name whose inferred
  grace is about to lapse (few sessions of runway left) still shows
  UNHEALTHY with the existing STALE warning, same as the proven path.
- **`options_researcher/h7_session.py::open_real_session` /
  `record_session_evidence`** — the real-entry door. Reads only the
  source-health receipt's per-symbol `healthy`/`gate` booleans; it does not
  re-derive earnings state. It inherits the fix automatically once the
  receipt reflects the new gate/health output — no door code changed.
- **`options_researcher/h7_watch.py::assemble_name`** — the daily lane
  watcher. Calls `earnings_gate` directly (not through `symbol_health`), so
  it was checked explicitly for independent re-derivation that could
  disagree with source health. It does not re-derive: `banned = gate !=
  GATE_CLEAR` uses the same shared gate value, so a GRACE name is treated
  as earnings-known and reaches the ordinary lane_a/b/c admission logic
  (armed/route/budget/basket checks) instead of short-circuiting to
  `EARNINGS-UNKNOWN`. Verified with a lane-level test
  (`tests/test_h7_watch.py::test_confirmed_past_within_post_report_grace_is_entry_eligible`)
  that a NOW-shaped fixture reaches `ENTRY-OK`, not `EARNINGS-UNKNOWN`.
- **`options_researcher/h7_data_gate.py`** — checked and found NOT to
  consume per-symbol `healthy`/`gate` at all. It binds to the source-health
  receipt (matching `evaluation_session`, `scope_hash`, and citing its
  `receipt_hash`) but its own `whole_universe_verdict` GO/NO_GO is a data-
  completeness check (chain/closes coverage), independent of earnings
  provenance. Unaffected by this amendment; listed here to show it was
  checked, not assumed.
- **`options_researcher/h7_entry_preflight.py`** — read-only proof that
  chains the same receipts; inherits automatically, no code change.
- **`options_researcher/h7_synthetic_proof.py`, `h10_watch.py`,
  `tools/thetadata_cutoff_preflight.py`** — all call `symbol_health`
  directly and only read `.healthy`; inherit automatically.

## What does NOT change

- **Registered cohort membership.** The 9 included / 6 excluded
  (EARNINGS-UNKNOWN at registration) names of `h7-forward-15-v1` are frozen
  at activation (`h7_cohort.py::load_registered_cohort`) and are
  independent of source health. Grace can make an *included* name's health
  CLEAR again; it can never re-admit one of the 6 excluded names into the
  cohort — that membership is a separate, immutable registration fact this
  amendment does not touch.
- **Names with no gating assertion at all** (e.g. CRWV, `"NO GATING
  ASSERTIONS"`) get no grace of any kind — there is no confirmed past date
  to infer from. They stay UNHEALTHY exactly as before
  (`tests/test_h7_earnings.py::test_no_past_report_at_all_gets_no_inferred_grace`,
  `tests/test_h7_source_health.py::test_no_past_report_at_all_gets_no_grace`).
- **Expired ESTIMATES.** Only a `status="confirmed"` past date qualifies,
  matching the existing "expired estimates never start grace" owner rule
  from 7b-0.1 unchanged
  (`tests/test_h7_earnings.py::test_expired_estimate_does_not_start_grace`,
  new `test_estimated_past_date_gets_no_inferred_grace` in
  `test_h7_source_health.py`).
- **Pre-report BANNED windows.** `_ban_windows`/`entries_banned` are
  untouched; a report date still bans entries for
  `H7_EARNINGS_BAN_SESSIONS` sessions before it through the report day.
  Grace only ever applies strictly *after* a report date, and the ban
  window for a confirmed date ends at that date, so the two never overlap.
- **The proven occurred-based grace** (`H7_EARNINGS_POST_REPORT_GRACE_D`,
  `coverage="grace"`). Unaffected: still requires a distinct occurred
  record, still wins over the inferred path when both would apply (the
  gate checks `occurred_recent` before `inferred_grace`).
- **Receipt immutability.** No existing receipt under `reports/h7_receipts/`
  is touched. New receipts (post-merge, post-ratification) will embed the
  new `config_hash` automatically — the receipt chain re-keys next session
  by design, same as every prior config change.
- **Receipt schema backward compatibility.** `symbol_health()` gained one
  new field (`grace_started`) and one new flag value (`GRACE`); nothing was
  removed or renamed. Every existing reader of a source-health receipt
  (`h7_session.py::_source_symbol_map`, `h7_paper_lifecycle.py`,
  `h7_exit_session.py`, `h7_real_scoring.py`, `h7_activation_guard.py`)
  reads fields via `.get()`/direct key access on `healthy`/`gate`/`flags`
  and does not assume a closed key set, so old receipts (which lack
  `grace_started`) remain loadable and old code remains correct against
  new receipts.
- **Vocabulary/claim discipline.** The inferred-grace CLEAR is labeled
  Inference in its gate reason string, its config comment, and this
  document; it is never described as "proven," "confirmed earnings," or
  similar in code comments or board output.

## Verification

- `uv run python -m unittest discover -s tests` — 1788 tests, exit 0.
- `uv run ruff check .` — all checks passed.
- `uv run pyright` — 0 errors, 0 warnings, 0 informations.
- Manual check against the live gating store
  (`data/earnings/gating_v3.csv`, unmodified): with the fix, `NOW` on
  `2026-07-24` evaluates to `gate=CLEAR coverage=post_report_grace
  healthy=True flags=[MISSING, GRACE] grace_started=2026-07-22
  grace_end=2026-09-05 grace_sessions_left=30`; day 45 (`2026-09-05`) is
  still `CLEAR`; day 46 (`2026-09-06`) reverts to `UNKNOWN`, matching the
  frozen boundary contract. `CRWV` (no gating assertions) remains `UNKNOWN`
  with no grace.
- New/updated tests: `tests/test_h7_earnings.py` (inferred-grace CLEAR,
  post-grace-expiry UNKNOWN, day-45/46 boundary, no-past-report exclusion,
  future-date precedence), `tests/test_h7_earnings_causal.py` (checklist
  item 4, amended per H7_OWNER_DECISIONS_7B01 supersession, plus new item
  4b for the still-eventually-expires case), `tests/test_h7_source_health.py`
  (board coverage/flag/`healthy` semantics including the STALE-at-day-45
  edge), `tests/test_h7_watch.py` (lane state no longer independently
  disagrees), `tests/test_h7_session_real_path.py`
  (`test_grace_name_in_cohort_no_longer_refuses_the_door`: builds a
  source-health receipt from the real `evaluate_health()` over a
  NOW-shaped fixture and confirms `open_real_session` no longer raises).

## Ledger (owner action, not taken by this branch)

To ratify: append an `H7_AMENDMENT_POST_REPORT_GRACE` fact to
`ledger/facts.log` citing this document's SHA-256, in the same spirit as
`H7_AMENDMENT_V1_4` (`docs/superpowers/plans/2026-07-14-h7-amendment-v1.4-per-name-source-health.md`).
Update `CLAUDE.md` / `README.md` "Scope status" / `AGENTS.md` if they
restate the post-report grace rule verbatim elsewhere. Until that append
happens, this amendment is inactive — the code change ships on this branch
so it is ready to activate the moment the owner ratifies, but per repo
convention (`.cursorrules`, ledger-discipline) a parameter/rule change is
not "live" until it is in the ledger.
