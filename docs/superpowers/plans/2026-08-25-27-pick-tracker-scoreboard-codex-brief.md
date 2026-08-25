# Codex brief 27 — daily pick recorder + entry-window scoreboard, decision/fill split, registration-gated (rev 4)

**Date:** 2026-08-25 (rev 4, same day)
**Author:** Claude orchestrating session (Fable), 2026-08-25
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** DRAFT rev 4 — adversarial review round 3 verdict PASS WITH FIXES (NEW-2 sink-key split, NEW-3 stale prose, NEW-4 density/cancellation projection + hard ops precondition — applied in this rev). Receipt: `reports/2026-08-25-briefs-25-27-adversarial-review-receipt.md`.
**Duration honesty (rev-2 finding N-6):** the owner asked for "two months." Two months is the ENTRY window (proposed 42 sessions, owner-typed at registration). Positions entered late in the window then run out their mark schedules — a LEAPS pick entered on the final day reaches its longest registered mark ~126 sessions (≈6 months) later. The scoreboard reports progressively from week one; the FINAL settled answer for every lane arrives months after the entry window closes. Say this to the owner plainly; do not sell a 6-month tail as a 2-month study.
**Provenance:** Repo-verified against commit `720a20e` on branch `claude/codex-handoff-plan-2026-08-22` unless labeled otherwise. Landing order is binding: **brief 26, then brief 25, then this brief.**
**Owner directive source:** Carsyn in-session 2026-08-25 ("each day the system should thoroughly run through each experiment and different standards and choose the top 5 for the day and track its picks for 2 months to see if it actually has been picking correctly") — spoken, not owner-typed.

## Why this exists (plain language)

The daily shortlist is computed at render time and thrown away — nothing
records what the board picked or how those picks did (Repo-verified:
`select_top_picks` persists nothing; `reports/rq2/` and `reports/a2/` do not
exist; ledger seq 25's own text says no RQ2 badge module was ever built).
The owner wants a daily record of the top picks under each selection standard
and a two-month answer to "has it actually been picking correctly."

Rev 1 of this brief failed adversarial review on four blockers. Rev 2's
design answers each one head-on:

1. **Causality (rev-1 finding 3):** rev 1 recorded entry marks from the same
   15:45 capture that produced the pick — decision quote == fill quote, the
   exact defect `.claude/rules/backtest-engine.md` warns about, and an
   inversion of registered seq 21 (`D_PLUS_1_CLOSE`; entry_date = fill
   session, decision date kept separately). Rev 2 uses a **decision/fill
   split**: decision on session D's verified board; fill at session D+1's
   verified 15:45 capture, conservative side.
2. **The multi-arm ban (rev-1 finding 5):** the feasibility-gate doc this
   brief cites also says, verbatim: "Not a data-mining license … Running the
   check on many candidate designs and picking the best is exactly the
   overfitting this repo exists to prevent, and remains banned"
   (`docs/superpowers/2026-07-24-registration-feasibility-gate.md:71-73`,
   Repo-verified). A seven-arm forward horse race with a declared winner is
   that thing. Rev 2 therefore scores exactly **two pre-registered arms** —
   `frozen_baseline` and `context_lane` (brief 25) — with ONE pre-registered
   primary contrast. The experiment lanes are recorded as descriptive
   nomination columns only: no P&L is computed for them, no winner language
   exists for them, and any future scoring of an experiment lane requires
   its own registration.
3. **Statistics (rev-1 finding 4):** naive daily re-recording counts one
   move many times. Rev 2 records a pick ONCE, at the session it ENTERS a
   lane's top-N (membership-entry event); aggregates use weekly
   non-overlapping cohorts (A2-v1's own device, ledger seq 19); every
   summary carries a bootstrap CI; the single primary contrast needs no
   multiplicity correction, and the mandatory concentration disclosure
   states that picks from an 18-name AI-infrastructure board are correlated
   and the effective sample is far smaller than the row count.
4. **Collision with A2-v1 (rev-1 finding 6):** A2-v1 (seq 19/27) is an OPEN
   registered outcome battery on the same board (12-month window since
   2026-08-17). Rev 2 (a) hard-gates all scored output on an owner-typed
   registration — until then every row goes to
   `reports/pick_tracker/dryrun/` and is permanently excluded from any
   scored window; (b) uses seq 19's registered mark points where they exist
   (LEAPS, tactical calls) and routes the unregistered CSP/CC/PMCC mark
   points to the owner for typing (WP-C.3; round-3 finding NEW-3 removed the
   earlier overclaim that the whole schedule was registered); (c) states in
   every report header that A2-v1 retains interpretive authority for
   board-level questions and this tracker answers only the shortlist-level
   question.

**On Robinhood (the owner's question):** no broker connection, paper or
otherwise. The repo is a validator (never connects to a brokerage order
endpoint — `.cursorrules` Scope; hard-enforced by hooks). Broker paper desks
also fill optimistically; this repo's registered standard is worse-side +
haircut + commissions, which produces harsher, more trustworthy numbers.
This tracker IS the paper-trading answer.

## Scope

**IN**
- WP-A: picks artifact written by the dashboard build.
- WP-B: recorder (membership-entry events, decision/fill split, dry-run by
  default).
- WP-C: evaluator (A2-schedule marks, conservative sides, costs).
- WP-D: scoreboard report + dashboard section.
- WP-E: ritual hook + ops sync + durability.
- WP-F: pre-registration packet DRAFT (hard precondition for any scored row).

**OUT (hard stops)**
- No ledger append — WP-F is a draft file; the owner types the registration
  later through the typed API path. Before that: dry-run output only.
- No live-order paths, no brokerage connection of any kind (including
  paper), no network providers, no new accounts.
- No mutation of any registered book (`data/positions/*`), no H-lane
  changes, no touch of RQ2/A2 machinery.
- No P&L computation, ranking, or winner language for experiment-lane
  nominations (descriptive columns only).
- The tracker has zero authority: descriptive, stamped non-verdict-bearing,
  cannot gate, size, or trigger anything.

## Design contract

**Sessions and identity.** `as_of` for every record is the ritual's
`$AS_OF` (`h7_watch.evaluation_session(...)` — `tools/daily_ritual.sh:119-120`;
rev-1 finding 25), never `RUN_DATE`. A session is usable only if
`schwab_chain_view.verified_sessions()` lists it; the receipt path is
derived as `reports/schwab_chains/<session>/preclose.json` (the module's
`REPORTS_DIR` convention, `options_researcher/schwab_chain_view.py:44`) and
the recorder computes and stamps its sha256 itself (the view API returns
sessions, not paths — rev-1 finding 25).

**Decision/fill split (mirrors registered seq 21).** Decision session D:
the pick enters a lane's top-N on D's board. Fill session: the NEXT session
with a verified capture containing the contract. Entry mark = conservative
executable side at that fill capture (buy at ask / sell at bid) plus
`SLIPPAGE_HAIRCUT`, plus `COMMISSION_PER_CONTRACT` per leg — all existing
`config.py` constants, no new numbers. If no verified capture exists within
2 sessions after D, the record closes as `CANCELLED_NO_FILL_DATA` (never a
silent fill; 2-session bound is LLM-proposed). If the contract is absent
from the fill capture, `CANCELLED_CONTRACT_ABSENT`. Both cancellation kinds
appear in the scoreboard's counts — cancelled picks are themselves a
finding about the pipeline.

**Reuse, don't reimplement (rev-1 finding 3 minimal-fix):**
`options_researcher/h7_paper_lifecycle.py` already implements
decision-vs-fill value splits, slippage haircuts, and chain/closes identity
hashing (see its entry-intent → fill machinery around `:568-574` and
`:1087-1098`). Reuse its helpers where importable without touching its
synthetic-only/real-store-refusal guarantees; if a helper is not cleanly
importable, factor it into a shared module rather than copying logic.

**Scored arms.** `frozen_baseline` = `select_top_picks(data)` — the
fully-qualified list WITHOUT the CSP-watch admission
(`include_csp_watch=False`; WATCH cards are trades the repo says are not
capital-confirmed — rev-1 finding 21). The watch-inclusive variant is
recorded with an explicit `watch_included: true` flag, reported separately,
never in the primary contrast. `context_lane` = brief 25's ordering
(recorded only when `CONTEXT_LANE_ENABLED`; when off, one `LANE_DISABLED`
row per session — loud, not skipped). Owner decision D-1 in brief 25 governs
when the flag flips; until then the tracker honestly records a one-arm
dry-run.

**Descriptive nominations.** For each authorized experiment lane
(`exp_beta_qqq`, `exp_tail_shape`, `exp_spread_stability`,
`exp_tbill_carry`, `exp_short_positioning` — module names Repo-verified),
the recorder stores the lane's per-symbol ordering over the SAME admissible
pool (shared vetoes: liquidity RED, skipped, non-rank-eligible) as a
nomination column, or `NOT_A_SELECTOR` where the lane has no natural
ordering. The recorder imports `exp_*` directly — it is its own module; the
AST boundary is file-scoped to `attractiveness_dashboard.py`
(`tests/test_experiments_baseline.py:92-93` — rev-2 finding N-10 corrected
the line). No P&L, no ranking, no winner language for these columns; the
packet (WP-F) states that scoring any of them later requires its own
registration.

## Work packages

### WP-A — picks artifact from the dashboard build (rev-1 finding 23)

The rev-1 premise "same in-process data" was impossible from a shell step,
and rev 2's "after selection, before render" was impossible too:
`_build_and_write` (`attractiveness_dashboard.py:4146-4163` @720a20e) calls
`assemble()` then `render()`, and ALL selection happens INSIDE `render()`
(`select_top_picks` at `:3245-3246`). A third independent selection call
could silently diverge from the rendered page — the rev-1 defect again
(rev-2 finding N-8). Fix: `render()` gains an optional `selection_sink`
parameter (a dict it fills with exactly the per-arm pick objects it
renders); `_build_and_write` passes the sink and persists its contents to
`.tmp/dashboard/picks_snapshot.json` — schema `picks_snapshot/v1`, per-arm
ordered candidate lists with `candidate_id`, contract identity (symbol,
lane kind, strike, expiry, right), quote sides from the board's capture,
board `data_as_of`, capture receipt path + sha256, and `config_hash`
surface. Atomic write. Arm-to-call mapping is explicit (round-3 finding
NEW-2 — the board makes THREE `select_top_picks` calls that differ):
- sink key `frozen_baseline` ← the policy-qualified call
  `select_top_picks(data)` at `attractiveness_dashboard.py:3246`;
- sink key `frozen_baseline_watch_inclusive` ← the hero-block call
  `select_top_picks(data, include_csp_watch=True)` at `:3245`;
- the research-bundle call at `:4029` is not a new arm — note in code that
  it remains a separate consumer.
NAMED TESTS: (1) the `frozen_baseline_watch_inclusive` key equals the hero
block's rendered candidate_ids on the same build; (2) on a fixture with a
CSP WATCH card present, `frozen_baseline` excludes it while
`…_watch_inclusive` contains it. The primary contrast reads ONLY
`frozen_baseline` (§Scored arms). The dashboard imports nothing new (frozen
+ context arms only — no `exp_*`). Fixture builds write it too (harmless,
path is `.tmp`).

### WP-B — recorder (`options_researcher/pick_tracker.py`)

1. Consumes the picks artifact + `verified_sessions()`; refuses to record a
   session absent from the verified list (`SESSION_UNVERIFIED`, fail-closed).
2. Membership-entry events: a (arm, candidate_id) pair opens ONCE — on the
   session it first appears in that arm's top-N — and is not re-recorded
   while continuously present; re-entry after an exit opens a new event.
3. Append-only JSONL under `reports/pick_tracker/dryrun/` (until WP-F's
   registration flips the path), fcntl-locked, idempotent: same
   (session, arm, content-hash) re-append is a no-op; same-session
   different-hash fails closed — copy `h10_observe.py:1-7` discipline
   (Repo-verified pattern).
4. Every line stamps: `as_of`, receipt path + sha256, artifact schema
   version, recorder version, `config_hash`, and
   `"authority": "NONE — descriptive tracking, dry-run"`.
5. Nomination columns (Design contract) recorded in the same line, flagged
   `descriptive_only: true`.

### WP-C — evaluator

1. Fill resolution per the Design contract's decision/fill split.
2. Daily marks for open scored picks against the newest verified capture,
   conservative close-out side (sells marked at ask to buy back, buys at
   bid). Missing name in a capture → `MARK_GAP` (never a stale carry —
   `.cursorrules` EOD-gap rule).
3. Mark/settlement schedule (rev-2 finding N-3 — honesty about what seq 19
   actually registers): ledger seq 19 registers mark points for exactly TWO
   lanes — "LEAPS marks are 21, 63, and 126 sessions; tactical call marks
   are 5, 10, and 20 sessions" (Repo-verified). For CSP it registers exit
   ARMS (strategy rules, no mark schedule); for CC/PMCC it registers
   accounting decompositions with NO horizons. Therefore: LEAPS and tactical
   calls use the registered 21/63/126 and 5/10/20 marks; CSP/CC/PMCC mark
   points are LLM-PROPOSED here (proposal: 5/10/21 sessions, mirroring the
   tactical grid plus the 21-DTE convention) and are moved into the WP-F
   packet for the OWNER to type at registration — Codex must not freeze
   them in `config.py` as registered values. A pick's terminal settlement is
   the earlier of contract expiry (intrinsic at `data/underlying_closes.py`
   close) or its lane's longest mark point — no single 42-session close-out
   across all lanes (rev-1 finding 22). Both legs' costs each way. Data-edge
   terminations labeled `terminal_conservative_mark` (seq 21 convention).
4. Outputs per pick: P&L after costs at each mark point, max drawdown while
   open, and the plain-language outcome word ("gained/lost after costs" —
   vocabulary discipline; never "worked"/"proven").

### WP-D — scoreboard

1. Dated `reports/pick_tracker/<or dryrun/><date>/scoreboard.{md,json}`:
   per arm — entries, cancellations by kind, open/settled counts, per-cohort
   (weekly, non-overlapping) after-cost P&L series with a bootstrap CI, and
   the ONE primary contrast: context_lane minus frozen_baseline per-cohort
   mean after-cost P&L, bootstrap CI. Mandatory header block: "DESCRIPTIVE
   ONLY — NOT A TRADE RANKING; no verdict authority; dry-run rows are
   permanently excluded from any registered window; A2-v1 (ledger seq
   19/27) retains interpretive authority for board-level outcome questions;
   CONCENTRATION: picks are drawn from one 18-name AI-infrastructure board
   and are correlated — the effective sample is far smaller than the row
   count."
2. Dashboard: compact section "PICK TRACKER (descriptive)" via passive file
   read of the latest scoreboard JSON (experiments-shelf doctrine — no
   builder import). Absent scoreboard renders loudly as unbuilt.

### WP-E — ritual hook, ops sync, durability (rev-1 finding 24)

1. Insert recorder+evaluator after the dashboard build
   (`tools/daily_ritual.sh:472`) and before the capture receipt (`:477`),
   each `|| note` fail-soft: a tracker failure must be INCAPABLE of changing
   the ritual's exit status or any lane's state (brief 14 WP-D hard-isolation
   wording).
2. Add `reports/pick_tracker` to `DATA_TIER_PATHS`
   (`tools/daily_ritual.sh:535-536`) and to
   `tools/irreplaceable_data_guard.py` namespaces.
3. **Ops-sync work package (explicit):** after merge to origin/main, fast-
   forward `~/options-validator-ops` in the sanctioned window (after the
   15:50 capture completes, before the next 07:10 ritual — the capture
   wrapper refuses on HEAD-vs-origin/main drift, the cause of the permanent
   2026-08-15→08-18 hole). Steps: record
   `git -C ~/options-validator-ops rev-parse HEAD` before, `merge --ff-only`
   per runbook
   `docs/superpowers/plans/2026-08-13-08-fork-healing-ops-sync-canary-runbook.md`,
   record HEAD after, and verify next ritual's log shows the tracker step.
   NOTE (Repo-verified 2026-08-25): the ops ritual is currently unhealthy
   (receipts uncommitted since 08-20; run-status stale/RUNNING at
   07:40-08:10). The separate ops-health investigation (task chip
   2026-08-25) is a HARD PRECONDITION of this brief's deploy step (round-3
   finding NEW-4 upgraded it from "should"): do not deploy the ritual hook
   until the repair has landed and ≥5 consecutive daily receipts have
   committed cleanly (WP-F.4 binds the registration to the same evidence).
   The recorder itself degrades cleanly (SESSION_UNVERIFIED) if captures
   are missing — dry-run development and tests are NOT blocked.

### WP-F — pre-registration packet (hard precondition for scored rows)

1. `docs/superpowers/plans/2026-08-25-pick-tracker-registration-packet-DRAFT.md`
   modeled on the H10a-v2 packet shape
   (`docs/superpowers/plans/2026-08-16-h10a-v2-reregistration-packet-DRAFT.md`):
   study question; the two scored arms; membership-entry event definition;
   decision/fill convention (citing seq 21); mark points (registered
   LEAPS/tactical values + owner-typed CSP/CC/PMCC per WP-C.3); weekly
   cohorts; bootstrap-CI reporting; the single primary contrast; entry
   window length (owner types the number — proposal 42 trading sessions ≈ 2
   calendar months of ENTRIES, positions then run out their mark schedule;
   LLM-proposed, provenance table); dry-run exclusion; no-extension clause;
   owner-typed wording block with blanks.
2. The packet quotes the feasibility gate's ban verbatim
   (`2026-07-24-registration-feasibility-gate.md:71-73`) and states the
   design's answer: two arms fixed in advance, one pre-registered contrast,
   experiment lanes descriptive-only — a pre-registered comparison, not a
   run-many-pick-best sweep. It also states: not loss-gated (the gate's own
   trigger at `:36-38` is "with a loss-gated verdict" — Repo-verified line
   numbers), no verdict authority, and any promotion use re-enters
   `.cursorrules:138-139` as a separate owner decision.
3. **Registration/flip ordering (rev-2 finding N-9):** flipping
   `CONTEXT_LANE_ENABLED = True` (brief 25 owner decision D-1) is a HARD
   precondition of the registration — the packet's wording block states
   that the entry window's first admissible session is the LATER of the
   registration append and the flip (the seq-26 clause-2 construction), so
   the contrast can neither open with a permanently empty arm nor cover a
   self-selected sub-window.
4. **Entry-count AND cancellation-rate projection (rev-2 N-6; round-3
   NEW-4):** before the packet is presented for owner typing, compute:
   (a) a base-rate estimate of membership-entry events per arm per week —
   verified-capture history is FAR too thin to use (Repo-verified 2026-08-25:
   `verified_sessions()` returns 2 sessions in the repo checkout
   [08-14, 08-19]; the ops working tree holds 4 receipt dirs
   [08-14, 08-19, 08-20, 08-24], two uncommitted), so the projection uses
   the frozen ThetaData-cache board history as a PROXY, labeled as such
   (proxy regime ≠ current regime; the label is mandatory);
   (b) the expected CANCELLATION rate under the decision/fill split at
   recent real capture density — the actual gaps (08-14→08-19 is 3
   sessions; 08-21/08-22 missing between 08-20 and 08-24) mean that at
   recent density MOST decisions would cancel rather than fill, making
   cancellations the study's dominant output;
   (c) the minimum capture density the design needs (state it as
   sessions-with-verified-capture per week).
   The packet must either state minimums the owner accepts or carry an
   explicit sparsity pre-acceptance clause quoting the computed numbers
   (H10 precedent) — silence is not an option. The gate's stated failure
   mode — "a window that costs months and answers nothing" — is this
   design's risk, and the packet must face it with the numbers, not the
   not-loss-gated escape. **Hard precondition (upgraded from "should",
   round-3 NEW-4): the ops-health repair (task chip 2026-08-25 — receipts
   uncommitted, ritual status stale/RUNNING) must land and show ≥5
   consecutive committed daily receipts before the registration is
   presented for owner typing.**
5. Until the owner-typed registration exists, the recorder REFUSES to write
   outside `dryrun/` (enforced in code + test, not by convention).

## Acceptance / verification

```bash
uv run python -m unittest discover -s tests    # exit 0, offline
uv run ruff check . && uv run pyright          # exit 0
```
Named tests: unverified-session refusal; membership-entry once-only (a pick
present 10 straight sessions yields ONE open event); idempotent re-append;
same-session different-hash fail-closed; decision/fill split (fixture where
D and D+1 quotes differ — the recorded fill uses D+1's WORSE side; the
drifted-quote rule of `.claude/rules/backtest-engine.md`);
`CANCELLED_NO_FILL_DATA` on missing next capture; MARK_GAP on missing name;
per-lane A2 mark schedule applied; dry-run path enforcement (writing a
scored row without a registration receipt raises); ritual isolation
(recorder raising cannot change wrapper exit — shell-level pattern in
`tests/test_daily_ritual_provenance.py`); dashboard section absent-is-loud;
scoreboard header contains the concentration + A2-authority sentences.

## Claim-discipline register

- No pick persistence / no RQ2-A2 code exists: Repo-verified @720a20e (grep
  + ledger seq 25 self-statement; `reports/rq2/`, `reports/a2/` absent).
- Feasibility gate trigger (`:36-38`) and data-mining ban (`:71-73`):
  Repo-verified, quoted.
- Seq 21 decision/fill convention; LEAPS 21/63/126 and tactical 5/10/20
  marks (seq 19); weekly non-overlapping cohorts (seq 19): Repo-verified in
  `ledger/experiments.jsonl`. CSP/CC/PMCC mark points: NOT registered
  anywhere — LLM-proposed here, owner-typed at registration (rev-2 finding
  N-3).
- `h10_observe` append discipline; `h7_paper_lifecycle` decision/fill
  machinery: Repo-verified modules.
- Conservative-fill + cost standard: Repo-verified `.cursorrules`;
  `COMMISSION_PER_CONTRACT`, `SLIPPAGE_HAIRCUT` exist in `config.py`.
- Ops ritual currently unhealthy: Repo-verified 2026-08-25 (untracked
  receipts 08-20/08-24 in ops; producer logs showing stale/RUNNING status).
- 42-session entry window, 2-session fill bound: LLM-proposed 2026-08-25;
  the owner types the registered numbers.
- Broker paper fills optimistic vs this repo's standard: Inference (no
  official source consulted); the against-Robinhood recommendation rests
  primarily on the Repo-verified validator-only guardrail.
