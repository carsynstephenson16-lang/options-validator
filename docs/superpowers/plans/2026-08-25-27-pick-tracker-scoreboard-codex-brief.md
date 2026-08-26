# Codex brief 27 — daily pick recorder + entry-window scoreboard, decision/fill split, registration-gated (rev 6)

**Date:** 2026-08-26 (rev 6, post-Briefs-26/25/28 interface rebase)
**Author:** Claude orchestrating session (Fable), 2026-08-25; current-main rebase by Codex, 2026-08-26
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** INDEPENDENT REVIEW PASS rev 6 — specification/review only; not authorized for implementation hand-off. Briefs 26, 25, and 28 are landed, this revision reconciles their current interfaces, and a fresh independent Terra review found no open Critical, Important, or Minor findings. The documentation PR remains draft; readiness, merge, implementation, deployment, registration, and scored writes each require their own later authority. Receipt: `reports/2026-08-26-brief-27-independent-review-receipt.md`.
**Duration honesty (rev-2 finding N-6):** the owner asked for "two months." Two months is the ENTRY window (proposed 42 sessions, owner-typed at registration). Positions entered late in the window then run out their mark schedules — a LEAPS pick entered on the final day reaches its longest registered mark ~126 sessions (≈6 months) later. The scoreboard reports progressively from week one; the FINAL settled answer for every lane arrives months after the entry window closes. Say this to the owner plainly; do not sell a 6-month tail as a 2-month study.
**Provenance:** Repo-verified against exact canonical `origin/main@1255d5a5cdf0cbb5336a92a5acb738f616cf7e92` unless labeled otherwise. That commit is PR #91's Brief 28 merge and contains landed Briefs 26, 25, and 28. The remaining order is this brief, then brief 30; neither may bypass its own fresh-base and authority gates.
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
   non-overlapping entry cohorts (A2-v1's own device, ledger seq 19); point
   summaries always render, while the primary contrast carries an exploratory
   dependence-aware bootstrap CI only after WP-D's minimum-cohort gate; the
   single primary contrast needs no
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
- WP-E: ritual hook + durability + owner-run ops handoff instructions.
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
- The worker ends at a green **draft PR**. It may not make the PR ready,
  merge, deploy, sync `~/options-validator-ops`, modify a ledger, type a
  registration, enable a flag, or flip authority. WP-E.3 is an owner-run
  handoff contract, not delegated execution.
- Do not add `reports/pick_tracker` to
  `tools/irreplaceable_data_guard.py:54-63` `DEFAULT_NAMESPACES`. Tracker
  reports are git-tracked, ritual-grown evidence, not a gitignored provider
  cache; an inventory floor here can false-alarm on a lagging main checkout
  and block repo-wide reconciliation. This rev-6 ruling removes the disputed
  rev-5 requirement rather than deferring it.

## State and authority gates (never collapse these)

1. **Specification review (this pass):** documentation rebase, current-interface
   verification, and independent review only. It creates no tracker output.
2. **Dry-run/build:** a later, separately authorized implementation may build
   code and may write only `reports/pick_tracker/dryrun/`. Passing tests or a
   dry-run does not establish readiness.
3. **Draft implementation PR:** visibility for review only; it must remain
   `isDraft=true` and carries no readiness or landing authority.
4. **Readiness:** a separate owner decision after implementation evidence and
   independent review. Readiness is not merge authority.
5. **Merge:** a separate explicit owner action. Merge is not deployment or ops
   synchronization.
6. **Deployment / ops synchronization:** a separate owner/operator action after
   the fresh health gates in WP-E.3; never performed by the implementation
   worker.
7. **Owner-typed registration:** a separate typed append after WP-F is complete.
   A spoken approval, merged implementation, enabled context lane, or dry-run
   artifact is not registration.
8. **Scored writes:** permitted only after the owner-typed registration exists
   and only from its first admissible session. Dry-run rows are permanently
   excluded; there is no historical tracker run or backfill.

## Design contract

**Sessions and identity.** `as_of` for every record is the ritual's
`$AS_OF` (`h7_watch.evaluation_session(...)` — `tools/daily_ritual.sh:119-120`;
rev-1 finding 25), never `RUN_DATE`. A session is usable only if
`schwab_chain_view.verified_sessions()` lists it
(`options_researcher/schwab_chain_view.py:170-195`); the receipt path is
derived as `reports/schwab_chains/<session>/preclose.json` (the module's
`REPORTS_DIR` convention, `options_researcher/schwab_chain_view.py:44`) and
the recorder computes and stamps its sha256 itself (the view API returns
sessions, not paths — rev-1 finding 25).

**Decision/fill split (mirrors registered seq 21; no same-capture shortcut).**
Decision session D is the verified board session on which the symbol/lane slot
enters the arm's top-N. The D capture supplies decision identity only and can
NEVER supply its fill, including on rerun. Derive the next two XNYS sessions
after D in order from the existing `data.cache_runner.trading_days` calendar
(`data/cache_runner.py:121-124`); do not use weekday arithmetic. Inspect D+1,
then D+2. The first of those sessions with a verified capture is the only fill
candidate. If neither is verified, close `CANCELLED_NO_FILL_DATA`. At that
first verified candidate, the exact evaluated contract must occur once with a
valid quote and required schema: absent contract →
`CANCELLED_CONTRACT_ABSENT`; duplicate/invalid row or quote →
`CANCELLED_FILL_SCHEMA_INVALID`; required position provenance changed →
`CANCELLED_COVERAGE_CHANGED`. Do not skip a bad/absent D+1 contract and hunt a
later price on D+2. A valid fill uses the conservative executable side at that
candidate capture (buy at ask / sell at bid), then applies
`SLIPPAGE_HAIRCUT` and one-leg `COMMISSION_PER_CONTRACT` from
`config.py:90-91`. The two-session search bound is LLM-proposed and remains
owner-typed only through WP-F. Every cancellation kind appears in scoreboard
counts — cancelled picks are themselves a finding about the pipeline.

**Evaluated leg and risk basis (Wave 0 full-PR audit):** the study measures the
incremental option recommendation, not mark-to-market P&L on an owner holding
that predates the pick. Every pick carries strict schema
`pick_position/v1` with exactly one evaluated option leg
`{symbol, right, strike, expiry, side, contracts: 1}`, `pnl_scope` exactly
`INCREMENTAL_OPTION_LEG_ONLY`, and lane-specific frozen coverage/risk basis:

| Lane | Evaluated leg | Required coverage context | Risk-basis denominator |
|---|---|---|---|
| `long_call`, `leaps` | long call | none | conservative entry debit at fill |
| `put` | short put | assignment-capital value from `top3_snapshot.policy`; `pick_position/v1` adds derivation `EVALUATED_STRIKE_X_100` and validates exact equality | assignment capital |
| `cc` | short call | 100-share holding identity, cost basis, and source-row hash | frozen 100-share cost basis |
| `pmcc` | short call | full held-LEAPS identity from `data/positions/positions.csv`: position id, symbol, right, strike, expiration, contracts, entry price, plus source-row hash | frozen LEAPS entry debit for one covering contract |

Freeze the denominator once, at fill, before any outcome is visible. For one
contract: long-call/LEAPS basis is the conservative evaluated-leg entry debit
including its entry commission; put basis is exactly the stamped policy
assignment capital (`evaluated strike × 100`, not reduced by premium); CC basis
is `100 ×` the source holding's frozen per-share cost basis; PMCC basis is
`100 ×` the covering LEAPS source row's frozen entry price for one contract.
All must be finite and positive. `evaluated_leg_pnl` includes only cash flows
and entry/exit costs of the evaluated option leg: long legs buy at the adverse
ask and close at the adverse bid; short legs sell at the adverse bid and close
at the adverse ask. It never includes pre-pick stock/LEAPS P&L.

The coverage leg is validity/provenance and normalization context only: do not
include its historical P&L in the pick outcome and do not charge a fictitious
new transaction cost for it. PMCC preview cards remain ineligible. If a lane's
required identity or finite positive basis is absent, inconsistent, or changes
before fill, cancel visibly as `CANCELLED_POSITION_SCHEMA_INVALID` or
`CANCELLED_COVERAGE_CHANGED`; never infer a leg, substitute current spot, or
emit partial P&L.

**Reuse, don't reimplement (rev-1 finding 3 minimal-fix):**
`options_researcher/h7_paper_lifecycle.py` already implements
decision-vs-fill value splits, slippage haircuts, and chain/closes identity
hashing (entry-intent payload at `:557-574`; fill enforcement and identities at
`:836-885,1076-1098`). Its public fill path is ledger/approval-bound and
exact-T+1-only, so the tracker must not call that stateful lifecycle path.
Reuse the already-public pure quote primitives it consumes:
`data.pandas_feed.quote_valid` (`data/pandas_feed.py:54-61`) and
`adverse_buy` / `adverse_sell` re-exported there from
`strategies/base.py:12-20`. Keep the lifecycle's synthetic-only/
real-store-refusal and authority guarantees intact; do not copy or extract a
second fill model.

**Scored arms.** `frozen_baseline` = `select_top_picks(data)` — the
fully-qualified list WITHOUT the CSP-watch admission
(`include_csp_watch=False`; WATCH cards are trades the repo says are not
capital-confirmed — rev-1 finding 21). The watch-inclusive variant is
recorded with an explicit `watch_included: true` flag, reported separately,
never in the primary contrast. `context_lane` = brief 25's ordering
(full watch-inclusive admissible pool, then `rank_context_lane`; current
interfaces at `attractiveness_dashboard.py:3944-4029` and
`options_researcher/context_lane.py:84-138`). Repo-verified current state:
`CONTEXT_LANE_ENABLED` is `True` on the provenance commit
(`config.py:867-870`), so the present build has both arms; remove every rev-5
claim that the context arm is awaiting a flip or that current runs are
one-arm. A future rollback to `False` remains loud: emit one `LANE_DISABLED`
state for that session and refuse the primary contrast rather than silently
shrinking the window. Flag enablement does not waive dry-run or registration
gates.

**Descriptive nominations.** For each authorized experiment lane
(`exp_beta_qqq`, `exp_tail_shape`, `exp_spread_stability`,
`exp_tbill_carry`, `exp_short_positioning` — module names Repo-verified),
the recorder stores the lane's per-symbol ordering over the SAME admissible
pool (shared vetoes: liquidity RED, skipped, non-rank-eligible) as a
nomination column, or `NOT_A_SELECTOR` where the lane has no natural
ordering. The recorder imports `exp_*` directly — it is its own module; the
AST boundary is file-scoped to `attractiveness_dashboard.py`
(`tests/test_experiments_baseline.py:91-93`). No P&L, no ranking, no winner
language for these columns; the
packet (WP-F) states that scoring any of them later requires its own
registration.

## Work packages

### WP-A — picks artifact from the dashboard build (rev-1 finding 23)

Current-main interface map (Repo-verified on the provenance commit):

- `render()` is a pure string-template interface with injected `event_view`
  (`options_researcher/attractiveness_dashboard.py:4609-4626`).
- `_original_hero_html` computes the visible watch-inclusive `py_picks` and
  the policy-qualified `qualified_picks` used for hero accounting at
  `:3681-3749` (calls at `:3691-3692`).
- `_context_lane_html` ranks the full watch-inclusive admissible pool and
  renders those exact `rows` at `:3944-4029`; `rank_context_lane` returns each
  row's exact `pick`, `candidate_id`, score, and context metadata
  (`options_researcher/context_lane.py:84-138`).
- `render()` also repeats the watch-inclusive selection for research and
  protected-card consumers at `:4627-4636`, and context diagnostics repeat it
  at `:4010`. These are consumers, not extra tracker arms.
- `pinned_picks` selects per symbol (`:562-580`) and `_pinned_html` renders
  those cards at `:4131-4172`; pins are explicitly not ranked and are NEVER a
  tracker arm. The lower QM and research views are also never arms.
- `_build_and_write` assembles data, constructs the immutable pre-render
  `EventView`, calls render, and writes HTML at `:4805-4857`. `EventView`
  recursively freezes its payload at `options_researcher/event_calendar.py:46-52,70-111`.

The rev-5 mutable-dict `selection_sink` proposal is retired because mutating a
caller-owned sink would make `render()` externally stateful and violate Brief
28's pure-render boundary. In rev 6, the **selection-sink contract** means the
returned `selection_snapshot` described below, never a mutable input argument.
Implement a pure internal result interface:

1. Add a frozen `DashboardRenderResult` (name may vary only if equally
   explicit) with `html: str` and a detached, canonical-JSON-ready
   `selection_snapshot`. A pure internal `_render_result(...)` computes each
   tracker selection ONCE, passes those same objects into the hero/context/
   diagnostics/research consumers, renders the HTML, and returns both values.
   It performs no file I/O and mutates neither `data`, cards, grades,
   `EventView`, ranking inputs, nor caller-owned containers.
2. Preserve public compatibility: `render(...) -> str` returns only
   `_render_result(...).html`. `_build_and_write` calls `_render_result` ONCE,
   not `render()` plus another selector, and persists the returned snapshot.
   Brief 28's `event_view` remains separately built before the render call and
   remains the same immutable injected object; event chips never enter the
   snapshot or selection.
3. Snapshot exactly these keys from the same values used to render:
   - `frozen_baseline`: policy-qualified `qualified_picks`. This is the
     primary scored arm and hero eligibility/accounting membership; when WATCH
     cards exist it is intentionally not identical to the visible hero-card
     list.
   - `frozen_baseline_watch_inclusive`: visible hero `py_picks`, explicitly
     `watch_included: true`, reported separately and never used by the primary
     contrast.
   - `context_lane`: the exact `rows` rendered by `_context_lane_html`, not a
     second `rank_context_lane` call. Preserve a loud `FAILED` or future
     `DISABLED` arm state instead of silently returning an empty list.
   Research protection, context diagnostics, pinned cards, and QM views reuse
   or consume these values where applicable but never create snapshot arms.
4. Persist `.tmp/dashboard/picks_snapshot.json`, schema
   `picks_snapshot/v1`, with ordered candidate lists, `candidate_id`, complete
   `pick_position/v1` evaluated-leg/coverage/risk-basis records, raw quote
   sides from the board capture, board `evaluation_date` and `data_as_of`,
   capture receipt path + sha256, source-row hashes, `config_hash`, and a
   `render_id`/`html_sha256` binding to the exact returned HTML bytes. Use
   temp-file + flush + fsync + `os.replace` for both files. The recorder
   verifies the current HTML hash before consuming the snapshot and refuses
   `SNAPSHOT_RENDER_MISMATCH`; this prevents a crash between two individually
   atomic replaces from pairing a new selection with an old page.
5. Extend holdings / held-LEAPS assembly only enough to preserve the required
   identities. Current PMCC assembly collapses each held LEAPS to
   `(strike, entry_price)` at `:1674-1680` and carries only strike/premium into
   the PMCC group at `:1930-1944`; that is insufficient. Preserve full source
   identity and fail closed until it is present. Do not change candidate
   grades, admission, ordering, shortlist width/membership, rendered sections,
   or `sections_json()` bytes.

NAMED TESTS: (1) one spy-count test proves each tracker arm is selected/ranked
once per `_render_result` call and the persisted candidate IDs equal that same
result; (2) visible hero candidate IDs equal
`frozen_baseline_watch_inclusive`; (3) rendered context candidate IDs equal
`context_lane`; (4) on a CSP-WATCH fixture `frozen_baseline` excludes the card
while `frozen_baseline_watch_inclusive` contains it; (5) pinned/QM/research
consumers never appear as arms; (6) populated immutable `EventView`, all
`grades`, all selection/ranking outputs, and `sections_json()` are byte-equal
before/after; (7) render performs no file I/O; (8) HTML/snapshot hash mismatch
fails closed. The primary contrast reads ONLY `frozen_baseline` (§Scored
arms). The dashboard imports no `exp_*`. Fixture `_build_and_write` calls may
write the `.tmp` snapshot, but pure `render()` fixture calls write nothing.

### WP-B — recorder (`options_researcher/pick_tracker.py`)

1. Consumes the picks artifact + `verified_sessions()`; refuses to record a
   session absent from the verified list (`SESSION_UNVERIFIED`, fail-closed).
2. Membership-entry events are keyed on **(arm, symbol, lane)** — a
   shortlist SLOT — NOT on `candidate_id` (2026-08-25 parameter audit,
   measured on the frozen cache 2026-05-01→2026-07-27: the winning
   expiry+strike changes on ~90% of consecutive session pairs, median
   candidate_id run length 1 session, ~38 candidate_id-keyed events per
   symbol-lane per 42 sessions — candidate_id keying would flood the study
   with re-struck near-duplicates of one economic bet, defeating the
   rev-2 fix for review finding 4). The slot opens ONCE, on the session
   its symbol-lane first enters the arm's top-N; the contract recorded is
   the one displayed on that opening session and it runs its own
   mark/settlement schedule. While the slot stays continuously in the
   top-N, a strike/expiry change is recorded as a `RESTRIKE` annotation on
   the open slot, never a new event. A new event opens only after the
   symbol-lane exits the top-N and later re-enters. The WP-F.4 projection
   must quote base rates under THIS keying.
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

1. Fill resolution per the Design contract's decision/fill split, including
   strict `pick_position/v1` and frozen-coverage validation before any P&L.
2. Daily marks for the single evaluated option leg against the newest verified
   capture, conservative close-out side (sells marked at ask to buy back, buys
   at bid). Missing name in a capture → `MARK_GAP` (never a stale carry —
   `.cursorrules` EOD-gap rule). Coverage context is revalidated for identity
   but never marked into the incremental pick P&L.
3. Mark/settlement schedule (rev-2 finding N-3; REVISED by the 2026-08-25
   parameter audit): ledger seq 19 registers mark points for exactly TWO
   lanes — "LEAPS marks are 21, 63, and 126 sessions; tactical call marks
   are 5, 10, and 20 sessions" (Repo-verified). For CSP it registers exit
   ARMS (strategy rules, no mark schedule); for CC/PMCC it registers
   accounting decompositions with NO horizons. LEAPS and tactical calls use
   the registered marks. CSP/CC/PMCC use an LLM-PROPOSED,
   elapsed-SESSION-denominated grid — **5 and 10 sessions, plus 21 sessions
   applied ONLY to entries whose DTE at fill exceeds 30 calendar days** —
   owner-typed via the WP-F packet; Codex must not freeze them in
   `config.py` as registered values. This grid is explicitly NOT seq 19's
   CSP "close at 21 DTE" exit arm: that is a remaining-tenor rule (like
   `config.py` H10_DTE_EXIT), not an elapsed clock, and conflating the two
   is the seq-30 IV-units defect pattern — the audit found the modal board
   pick (~11 DTE, ladder bucket 1 target 14 DTE / window 10-21 calendar
   days) can NEVER reach 21 elapsed sessions and is already past 21
   remaining DTE at entry. Every pick settles at the EARLIER of contract
   expiry (intrinsic at `data/underlying_closes.py` close) or its lane's
   longest applicable mark; an interior mark falling after expiry is
   recorded `MARK_AFTER_EXPIRY` and omitted, never carried — this applies
   to the registered tactical 10/20 marks too, which an ~11-DTE tactical
   pick also cannot reach. The scoreboard prints, per lane, the count of
   entries whose marks were unreachable, and a lane with zero entries over
   the window reports "no data", never a result — the audit's badge census
   (sell lanes carry 7 gradeable badges vs 3 on buy lanes; FOMC/VRP/
   earnings badges currently AMBER/UNKNOWN on most sell cards) means income
   lanes may rarely enter the shortlist at all. Charge entry and exit costs
   for the evaluated option leg only. Data-edge terminations labeled
   `terminal_conservative_mark` (seq 21 convention).
4. Outputs per pick: evaluated-leg P&L after costs and
   `return_on_risk_basis = evaluated_leg_pnl / frozen_risk_basis` at each mark
   point, max drawdown on that same normalized series, coverage-context status,
   and the plain-language outcome word ("gained/lost after costs" — vocabulary
   discipline; never "worked"/"proven"). Raw dollars remain available only
   within lane-level tables and are never pooled across structures.

### WP-D — scoreboard

1. Dated `reports/pick_tracker/<or dryrun/><date>/scoreboard.{md,json}`:
   per arm AND lane — entries, cancellations by kind, open/settled counts,
   raw evaluated-leg dollars, normalized `return_on_risk_basis`, and weekly
   non-overlapping cohort summaries. Never pool raw dollar P&L across lanes.
   The ONE primary contrast is context_lane minus frozen_baseline on normalized
   returns: within each weekly cohort compute each arm's mean separately by
   lane, compare only lanes represented in BOTH arms, then equal-weight those
   paired lane contrasts. Report unmatched-lane counts explicitly; do not
   impute them. Weekly entry cohorts do not make outcomes independent: mark
   windows overlap and symbols are correlated. Emit an explicitly
   **exploratory** moving-block bootstrap CI only with at least **8**
   chronological weekly paired-lane cohort contrasts, resampling consecutive
   two-week blocks to preserve short-range overlap dependence (threshold and
   block length LLM-proposed 2026-08-25). Before that, show point summaries
   plus `INSUFFICIENT_COHORTS`, never a CI or directional conclusion. Never
   call the cohorts or CI independent. Mandatory header block: "DESCRIPTIVE
   ONLY — NOT A TRADE RANKING; no verdict authority; dry-run rows are
   permanently excluded from any registered window; A2-v1 (ledger seq
   19/27) retains interpretive authority for board-level outcome questions;
   CONCENTRATION: picks are drawn from one 18-name AI-infrastructure board
   and are correlated — the effective sample is far smaller than the row
   count."
2. Dashboard: compact section "PICK TRACKER (descriptive)" via passive file
   read of the latest scoreboard JSON (experiments-shelf doctrine — no
   builder import). Absent scoreboard renders loudly as unbuilt.

### WP-E — ritual hook, durability, owner-run ops handoff (rev-1 finding 24)

1. Insert recorder+evaluator after the dashboard build
   (`tools/daily_ritual.sh:472`) and before the capture receipt (`:477`),
   each `|| note` fail-soft: a tracker failure must be INCAPABLE of changing
   the ritual's exit status or any lane's state (brief 14 WP-D hard-isolation
   wording).
2. Add `reports/pick_tracker` to `DATA_TIER_PATHS`
   (`tools/daily_ritual.sh:543-545`) so dry-run/scored evidence is included in
   the ritual's narrow durability commit. Do NOT edit
   `tools/irreplaceable_data_guard.py` or add this path to
   `DEFAULT_NAMESPACES` (`tools/irreplaceable_data_guard.py:54-63`); the
   disputed rev-5 guard addition is removed.
3. **Owner-run ops-sync handoff (explicit; worker MUST NOT execute):** the
   implementation draft PR includes a post-merge checklist for the owner or a
   separately authorized operator. Only after owner merge may that operator
   fast-forward `~/options-validator-ops` in the sanctioned window (after the
   15:50 capture completes, before the next 07:10 ritual — the capture wrapper
   refuses on HEAD-vs-origin/main drift, the cause of the permanent
   2026-08-15→08-18 hole). The checklist records
   `git -C ~/options-validator-ops rev-parse HEAD` before, requires an
   owner-run `merge --ff-only` per runbook
   `docs/superpowers/plans/2026-08-13-08-fork-healing-ops-sync-canary-runbook.md`,
   records HEAD after, and verifies the next ritual's log shows the tracker
   step.
   This documentation pass verified checkout alignment only, not live ritual
   health; synchronization to the provenance SHA is not health evidence. A
   fresh owner/operator check is a HARD PRECONDITION of deployment: the
   relevant repair must be present and ≥5 consecutive trading-session daily
   receipts must have committed cleanly, with any gap or failed commit
   resetting the streak (WP-F.4 binds registration to the same evidence).
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
   OWNER SELECTION 2026-08-25 (spoken in-session, then audited at the
   owner's direction "audit your proposals then go with what's best"): the
   owner approved the 42-session window, the income-lane mark proposal, and
   the pre-accept route, and delegated adoption of the audit's amendments.
   The audited final proposals are: window 42 sessions (unchanged; audit
   verdict — length was fine, the entry KEYING was the defect, fixed in
   WP-B.2); income-lane marks 5/10 sessions + conditional 21 (WP-C.3, the
   audited replacement for the defective flat 21); pre-accept per WP-F.4's
   audited clause below. These remain proposals until the owner TYPES them
   in the registration.
2. The packet quotes the feasibility gate's ban verbatim
   (`2026-07-24-registration-feasibility-gate.md:71-73`) and states the
   design's answer: two arms fixed in advance, one pre-registered contrast,
   experiment lanes descriptive-only — a pre-registered comparison, not a
   run-many-pick-best sweep. It also states: not loss-gated (the gate's own
   trigger at `:36-38` is "with a loss-gated verdict" — Repo-verified line
   numbers), no verdict authority, and any promotion use re-enters
   `.cursorrules:138-139` as a separate owner decision.
3. **Registration/flag ordering (rev-2 finding N-9; rebased):**
   `CONTEXT_LANE_ENABLED = True` is already Repo-verified on the provenance
   commit (`config.py:867-870`). The packet still binds the entry window's
   first admissible session to the LATER of the owner-typed registration append
   and the first session whose exact `origin/main` code has the flag true (the
   seq-26 clause-2 construction), so it cannot cover a self-selected pre-flag
   sub-window. If the flag is later rolled back before or during the window,
   record `LANE_DISABLED`, compute no primary contrast for that session, and
   follow the packet's pre-registered interruption rule; do not silently
   shrink or extend the window. The implementation worker may not change the
   flag.
4. **Entry-count AND cancellation-rate projection (rev-2 N-6; round-3
   NEW-4):** before the packet is presented for owner typing, compute:
   (a) a base-rate estimate of membership-entry events per arm per week. This
   documentation pass does not run a historical tracker or re-count live ops
   captures. At implementation/registration-readiness time, measure the then-
   current verified-capture density. If it is too thin for the entry-rate
   estimate, use the frozen ThetaData-cache board history only as a PROXY,
   labeled as such (proxy regime ≠ current regime; the label is mandatory);
   (b) the expected CANCELLATION rate under the decision/fill split at
   then-current real capture density, with every missing candidate session
   counted under the exact D+1/D+2 rule rather than bridged;
   (c) the minimum capture density the design needs (state it as
   sessions-with-verified-capture per week).
   The owner ruled the PRE-ACCEPT route 2026-08-25 — but ruled it EX ANTE,
   before (a)/(b)/(c) exist. Per the parameter audit, the packet's
   pre-acceptance clause is therefore incomplete until ALL THREE numbers —
   (a), (b), AND (c), not just "the computed numbers" loosely — are
   inserted and quoted verbatim (H10 precedent is pre-accept QUOTING the
   number). Guard against pre-accepting blind: if computed (b) exceeds 50%
   or (a) falls below one event per arm per week (slot keying, WP-B.2),
   the packet RETURNS to the owner for re-confirmation before typing —
   an advance pre-acceptance does not extend to numbers materially worse
   than the design assumed. The gate's stated failure mode — "a window
   that costs months and answers nothing" — is this design's risk, and
   the packet must face it with the numbers, not the not-loss-gated
   escape. **Hard precondition (upgraded from "should", round-3 NEW-4): a
   fresh owner/operator health check must show the relevant repair present and
   ≥5 consecutive committed trading-session daily receipts before registration
   is presented for owner typing; any gap or failed commit resets the streak.**
5. Until the owner-typed registration exists, the recorder REFUSES to write
   outside `dryrun/` (enforced in code + test, not by convention).

## Acceptance / verification

```bash
for test_file in test_pick_tracker.py test_attractiveness_dashboard.py test_context_lane.py test_event_awareness.py test_daily_ritual_provenance.py test_irreplaceable_data_guard.py; do
  uv run python -m unittest discover -s tests -p "$test_file" || exit 1
done
uv run python -m unittest discover -s tests
uv run ruff check .
uv run ruff format --check options_researcher/pick_tracker.py tests/test_pick_tracker.py
uv run pyright
bash -n tools/daily_ritual.sh
git diff --check
```
Every command must exit 0. The full unittest discovery is offline. The focused
guard test is regression evidence only: `DEFAULT_NAMESPACES` and the guard code
remain unchanged. Current main's pre-existing
`options_researcher/attractiveness_dashboard.py` and
`tests/test_attractiveness_dashboard.py` would be reformatted by Ruff; do not
create that broad unrelated diff. If implementation legitimately adds another
new Python file, append it to the new-file format command; do not substitute a
repo-wide or pre-existing-file format rewrite while baseline debt exists.
Named tests: unverified-session refusal; slot membership-entry once-only (one
symbol-lane present 10 straight sessions while candidate ids re-strike yields
ONE open event plus `RESTRIKE` annotations); slot exit then re-entry yields a
second event; idempotent re-append;
same-session different-hash fail-closed; decision/fill split (fixture where
D and D+1 quotes differ — D is never used and the recorded fill uses D+1's
WORSE side; a rerun on D cannot create a fill; a missing D+1 plus verified D+2
uses D+2; no verified D+1/D+2 yields `CANCELLED_NO_FILL_DATA`; an absent or
invalid exact contract at the first verified candidate cancels and never hunts
a later price; the drifted-quote rule of `.claude/rules/backtest-engine.md`);
MARK_GAP on missing name;
per-lane `pick_position/v1` schema and risk-basis construction; put assignment
capital must equal evaluated strike × 100 with derivation stamped; missing PMCC
long-leg expiry/right/position identity and missing CC basis each cancel
fail-closed; coverage P&L is excluded; raw dollars never pool across lanes;
paired-lane normalization; 7 weekly cohorts render `INSUFFICIENT_COHORTS`
while 8 enable the exploratory two-week moving-block bootstrap CI, whose test
proves resampled blocks retain adjacent cohort pairs; per-lane A2 mark schedule
applied; dry-run path enforcement (writing a
scored row without a registration receipt raises); ritual isolation
(recorder raising cannot change wrapper exit — shell-level pattern in
`tests/test_daily_ritual_provenance.py`); dashboard section absent-is-loud;
scoreboard header contains the concentration + A2-authority sentences.
The implementation ends at a green GitHub draft PR with `isDraft=true`; the
worker does not execute WP-E.3, type WP-F, make ready, merge, or deploy.

## Claim-discipline register

- No pick persistence / no RQ2-A2 code exists: Repo-verified
  @1255d5a5cdf0cbb5336a92a5acb738f616cf7e92 (grep
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
- Conservative-fill + cost standard: Repo-verified `.cursorrules`,
  `data/pandas_feed.py:8-20,38,54-61`, and `strategies/base.py:12-20`;
  `COMMISSION_PER_CONTRACT`, `SLIPPAGE_HAIRCUT` are at `config.py:90-91`.
- Current render/result boundary, exact hero/context consumers, pinned-card
  exclusion, immutable pre-render EventView, and `_build_and_write` call path:
  Repo-verified at the rev-6 WP-A citations on the provenance commit. The
  returned render-result design is LLM-proposed to satisfy the owner's explicit
  no-rerun and pure-render requirements; no current generalized selection sink
  exists.
- `CONTEXT_LANE_ENABLED` is true on current main: Repo-verified
  `config.py:867-870`.
- Current PMCC card enrichment retains only the held LEAPS strike and entry
  cost, while `data/positions/positions.csv` carries the full right/expiration/
  position identity: Repo-verified
  `attractiveness_dashboard.py:1674-1680,1930-1944` and
  `options_researcher/portfolio.py:24-27,38-74`; the Wave 0 reviewer
  correctly found the prior multi-leg P&L contract under-specified.
- `reports/pick_tracker` belongs in the future ritual durability allow-list
  (`tools/daily_ritual.sh:543-545`) but not the irreplaceable-data namespace
  list (`tools/irreplaceable_data_guard.py:54-63`): rev-6 specification ruling.
  No shell or guard file is changed by this documentation pass.
- Ops checkout alignment to the provenance commit: user-supplied and locally
  Git-verified in this pass. Live ritual health and the five-receipt streak:
  Unknown/not audited here; must be freshly verified at deployment and
  registration gates.
- 42-session entry window, 2-session fill bound, 5/10/+conditional-21
  income-lane marks, slot keying: LLM-proposed 2026-08-25, owner-approved
  in-session (spoken) with audit amendments owner-delegated ("go with
  what's best"); the owner types the registered numbers.
- Candidate churn measurement (winning expiry+strike changes ~90% of
  consecutive session pairs; median candidate_id run 1 session; ~38
  candidate_id events per symbol-lane per 42 sessions): Test-verified
  2026-08-25 on the frozen cache 2026-05-01→2026-07-27 (7 dense symbols;
  single-regime proxy caveat; parameter-audit receipt in the review
  receipt file).
- Incremental-option-leg P&L scope, lane-specific frozen risk bases,
  paired-lane equal weighting, the 8-cohort CI minimum, and two-week
  moving-block resampling: LLM-proposed 2026-08-25, descriptive-only, and
  required to reduce structure-size/lane-mix distortion while acknowledging
  overlapping outcomes and correlated names.
- Broker paper fills optimistic vs this repo's standard: Inference (no
  official source consulted); the against-Robinhood recommendation rests
  primarily on the Repo-verified validator-only guardrail.
