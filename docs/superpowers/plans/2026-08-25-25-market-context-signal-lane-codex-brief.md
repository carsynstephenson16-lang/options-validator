# Codex brief 25 — daily market context that visibly contributes to a labeled second ranking lane (rev 5)

**Date:** 2026-08-26 (rev 5, train-order correction)
**Author:** Claude orchestrating session (Fable), 2026-08-25
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** REVIEW PASS rev 4 for Brief 25's substantive contract; rev 5 changes only the downstream train order and is pending PR #90's final correction review. Binding implementation order is 26 → 25 → 28 → 27 → 30; this status does not authorize merge, flag enablement, or deployment.
**Provenance:** Brief 25's substantive contract was repo-verified against commit `720a20e` on branch `claude/codex-handoff-plan-2026-08-22` unless labeled otherwise. The 2026-08-26 order-only addendum is repo-verified against post-Brief-25 `origin/main@8a6920a2449094f4e5db5ad6ff00741f2d388023`. Landing order is binding: **26 → 25 → 28 → 27 → 30** (Brief 28 consumes Brief 25's context-card surface before Brief 27, and Brief 30 remains last).
**Owner directive source:** Carsyn in-session 2026-08-25 ("market context i want that updated daily and actually contributing to the signals") — spoken, not owner-typed.

## Why this exists (plain language)

Two things frustrate the owner:

1. **The market context on the board is stale.** The "Market context
   (Backdrop)" section and company-research annotations come from the LLM
   research bundle keyed to board `data_as_of` 2026-07-27. The producer
   LaunchAgent is NOT disabled (rev-1 finding 1 corrected): it is enabled and
   has fired 13 times, but every recent run exits 3 `UPSTREAM_BLOCKED` because
   the 07:10 ops daily ritual's run-status is not `OK` when the producer
   checks at 07:40/08:10 (Repo-verified 2026-08-25: `launchctl print` shows
   `runs = 13, last exit code = 3`; logs
   `~/options-validator-research/.tmp/research_refresh/2026-08-25_081005.log`
   show `UPSTREAM_BLOCKED: ritual run status is not OK: 'RUNNING'`, and the
   2026-08-24 run saw a status stale from 08-21). The producer is failing
   CLOSED, correctly; the upstream ritual is the sick component, and its
   repair is a separate ops investigation (task chip spawned 2026-08-25) —
   NOT this brief's scope.
2. **The context that IS fresh contributes nothing.** The composite signal
   lane (trend / vol-premium / regime / options internals,
   `options_researcher/composite_signals.py`) recomputes at every dashboard
   build from cached data, but is isolated display context. Repo-verified:
   `.cursorrules:130-133` freezes the GREEN-fraction baseline while
   experiment flags are off, and RQ2-v1/A2-v1 (ledger seq 18/19/25/26/27)
   opened a forward window 2026-08-17 measuring exactly that frozen ranking.

The integrity-compatible way to make context "actually contribute" TODAY is a
**second, clearly labeled, flag-gated ranking lane** rendered beside the
frozen shortlist — never replacing it — whose pick quality brief 27 tracks
head-to-head against the frozen baseline. Promotion to default ranking stays
a separate owner decision behind `.cursorrules:138-139`. This brief amends no
registration.

## Scope

**IN**
- WP-A: shared display-rank module extraction (pure refactor, byte-identical
  ordering).
- WP-B: context-aware scorer module + config flag (default OFF).
- WP-C: dashboard rendering of the context lane beside the frozen shortlist.
- WP-D: honest research-staleness note (no launchctl claims, no re-enable
  instruction).
- WP-E: tests, acceptance metrics, failure behavior, rollback.

**OUT (hard stops)**
- No ledger writes, no registration, no amendment to RQ2-v1/A2-v1 or any
  registered hypothesis, no authority flips, no live-order paths.
- No semantic change to the frozen recipe: `select_top_picks`,
  `_admissible_pick_pool` vetoes, tie-breaks, one-pick-per-symbol, and the
  quality-key ORDERING stay behavior-identical (WP-A moves code; a named
  byte-behavior test proves ordering identity).
- No network providers, no yfinance, no new data acquisition (OD-4 stands).
- No changes to `tools/research_refresh.sh`, the runbook, any plist, or any
  LaunchAgent state.
- No import of `options_researcher.exp_*` into `attractiveness_dashboard.py`
  (AST boundary test `tests/test_experiments_baseline.py:92`).
- The ritual-health repair (why run-status is RUNNING/stale at 07:40) is a
  separate investigation — do not touch `tools/daily_ritual.sh`.
- The worker ends at a green **draft PR**. It may not make the PR ready,
  merge, deploy, sync an operational checkout, enable the context flag,
  modify a ledger, or flip authority. Owner instructions below describe
  owner-controlled follow-up state; they do not delegate those actions.

## Work packages

### WP-A — shared display-rank module (rev-1 finding 9)

1. New module `options_researcher/display_rank.py`. Move there: the BODY of
   `_display_quality_key` (`attractiveness_dashboard.py:610` @720a20e), its
   green-fraction computation, AND the `_BUY_LANES`/`_SELL_LANES` lane-set
   tuples (`:215-216`) that it and WP-B both need. The dashboard keeps thin
   delegating wrappers / re-exports so every existing call site and test is
   untouched. `context_lane.py` (WP-B) imports from `display_rank`, not from
   the dashboard — no import cycle.
2. Null semantics are the DASHBOARD's, not `rq1_runner`'s: empty/missing
   grades → `0.0` fraction exactly as `_display_quality_key` does today
   (Repo-verified difference: `rq1_runner.green_fraction` returns `None` on
   empty — do NOT couple to the study runner).
3. Named test: for a fixture card set covering every lane kind and an
   ungraded card, the moved function returns tuples equal element-for-element
   to the pre-move implementation (golden values captured in the test).

### WP-B — context-aware scorer (`options_researcher/context_lane.py`, flag OFF)

1. Inputs: the FULL `_admissible_pick_pool` from the assembled board sections
   AND the composite board object built during real assembly
   (`attractiveness_dashboard.py:1340` @720a20e:
   `if composite_signals is None and real_assembly:` — pass the built board
   in; never rebuild it per page). Score the full admissible pool, then take
   `PICK_TOP_N`; do not restrict scoring to the frozen shortlist. A context
   pick may therefore displace a frozen boundary pick, which is required for
   Brief 27's arm comparison to be non-vacuous.
2. Score tuple (lexicographic, never summed — composite-lane doctrine,
   `composite_signals.py:32,76,520` "never a weighted average"):
   `(-green_fraction, -context_term, -rank_leader, -tech_conf, tie, symbol, lane, strike)`
   — i.e. the FULL frozen determinism tail is preserved verbatim
   (rev-1 finding 8; frozen pool key built at
   `attractiveness_dashboard.py:349` inside `_admissible_pick_pool`).
   `context_term` (rev-1 finding 7 — must be direction-aware and
   veto-respecting):
   - 0 if the symbol's composite card is DATA_BLOCKED, absent, or its
     `confluence_grade` is "C" (an internals VETO caps the grade at C —
     Repo-verified `composite_signals.py:557-558`; a vetoed name must never
     gain rank from context);
   - else `aligned_count`, but ONLY when the trend angle's state is `UP`.
     The composite trend angle emits `UP`, `DOWN`, `MIXED`, or DATA_BLOCKED
     (Repo-verified `composite_signals.py:128-168`). For EVERY lane the
     context term is nonzero only on `UP` —
     buy lanes because direction agrees, sell lanes because premium selling
     against a confirmed DOWN trend must not be promoted by "alignment".
     `DOWN` and `MIXED` both produce 0 with reason `DIRECTION_MISMATCH`;
     DATA_BLOCKED produces 0 with reason `BLOCKED`.
   - The lane-direction sets `_BUY_LANES`/`_SELL_LANES` (defined at
     `attractiveness_dashboard.py:215-216`; used by the quality key at
     `:624-628`) move to `display_rank` in WP-A — import them from there.
   Label in the module docstring: the position of `context_term` (second) and
   the UP-only-for-all-lanes rule are LLM-proposed 2026-08-25.
3. Config: new block in `config.py`, SEPARATE from the 2026-08-09 experiment
   block (rev-1 finding 26 — that block instantiates a different owner
   authorization):
   ```
   # CONTEXT-AWARE SHORTLIST LANE — display-only second ranking lane.
   # Owner-directed in-session 2026-08-25 (spoken, not owner-typed).
   # Disabled by default; enabling is an owner decision (see brief 25 WP-E.4).
   CONTEXT_LANE_ENABLED: bool = False
   ```
   Slot count: consume `config.PICK_TOP_N` from brief 26 (landing-order
   dependency; no new count constant, no hardcoded 3 or 5).
4. Output rows carry: symbol, lane, `top3_snapshot.candidate_id`, full score
   tuple, the composite card's `max_asof`, board `data_as_of`, and the
   context_term with its reason ("VETOED", "DIRECTION_MISMATCH", "BLOCKED",
   or the aligned angles by name).

### WP-C — rendering

1. Flag OFF (default): rendered HTML byte-identical to pre-change output
   (named golden test; baseline-isolation byte-identity clause at
   `docs/superpowers/specs/2026-08-09-attractiveness-experiment-program-design.md:83`).
   NOTE (rev-1 finding 12): brief 26 lands first and re-goldens the page; this
   brief's golden is captured AFTER brief 26 is merged.
2. Flag ON: section "CONTEXT-AWARE SHORTLIST — EXPERIMENTAL" renders
   immediately after the frozen hero block (heading string owned by brief 26:
   "Rule-based top 5") and before "QM MOVEMENT LANE". `config.PICK_TOP_N`
   slots; each slot names the candidate and the aligned angles in words.
   Mandatory disclaimer, exact text (rev-1 finding 27; rev-2 finding N-12 —
   must be true on the day THIS brief lands, before brief 27 exists):
   "Experimental re-ordering by market context. The rule-based list above is
   the registered baseline. This lane is display-only and carries no verdict
   or trade authority; once the pick tracker is live its picks will be
   tracked descriptively against the baseline."
3. Fail-visible without falsifying membership: any selected context-lane name
   whose composite card is DATA_BLOCKED renders in its slot with blocked state
   and reason. Separately, a compact comparison-diagnostics row covers every
   frozen-shortlist name and shows its context reason, including
   `BLOCKED`, `VETOED`, `DIRECTION_MISMATCH`, or `DISPLACED`. Diagnostics do
   not consume the `PICK_TOP_N` context slots. The context shortlist may omit
   a frozen name only through the explicit full-pool ranking; no name or
   failure state silently disappears (`_blocked_html` ethos,
   `attractiveness_dashboard.py:3971` docstring @720a20e).
4. Test updates for flag-ON ordering are additive-only: new flag-ON test
   asserts the insertion point; the flag-OFF path leaves EVERY existing
   ordering test untouched (the full enumerated ordering-test list lives in
   brief 26 WP-E; this brief adds none of its own heading strings to the
   flag-OFF page).

### WP-D — honest research staleness note (rev-1 findings 1, 11, 29)

1. Freshness-strip research chip uses only the context bytes the board actually
   loaded; it does not inspect the producer's success-only slot receipt,
   mutable guard state, logs, or FINAL manifest. Brief 26's `_build_and_write`
   already captures `deployment_root` and the yielded `input_root`. While still
   inside `_input_root_cwd()`, load both the board and research context from
   that SAME resolved `input_root`; do not call `load_context()` later from the
   deployment root. Carry the parsed context, its warning, source path, and
   SHA-256 into `render()` as injected data.
2. Derive only these states: context is a mapping, annotation normalization
   succeeds, and context `as_of == board.data_as_of` → `EXACT`; valid context
   `as_of < board.data_as_of` → `STALE`; no context → `UNAVAILABLE`; unreadable,
   non-object, invalid/future as-of, hash drift after load, or failed annotation
   normalization → `INTEGRITY_FAILED`. Render date-neutral text, "Research
   context <status> — context as of <as-of or unavailable>; board as of
   <data_as_of>." These states describe loaded evidence only and never claim
   why a refresh did or did not run.
3. Named tests prove exact/stale/unavailable/integrity-failed states; context
   and board are loaded from the same injected input root even when deployment
   cwd differs; parsing and hashing use one byte snapshot, so a later file
   mutation cannot split the current build; mutable guard/log/final-manifest
   content cannot change the chip. This avoids the producer's PENDING →
   dashboard → FINAL cycle entirely.
4. Do NOT render budget numbers. (Rev-1 WP-C.2 hardcoded $8/$200 with a wrong
   citation and a false offline-impossibility claim — deleted. If the owner
   later wants spend surfaced, that is an owner decision with owner-typed
   figures.)
5. Research-bundle candidate-count cost note (rev-1 finding 29): moved OUT of
   a PR description into this brief as an explicit owner decision — see
   WP-E.4 D-2.

### WP-E — tests, acceptance, failure behavior, rollback (rev-1 findings 10, 26)

1. Flag-OFF byte-identity golden test (WP-C.1).
2. Flag-ON tests MUST inject a synthetic composite board with mixed
   `aligned_count`/grade/trend values and assert an ACTUAL order change vs
   the frozen lane from the full admissible pool, including displacement of a
   frozen boundary pick, plus: vetoed (grade C) name never gains rank from
   context; DOWN and MIXED trends each gain 0 with `DIRECTION_MISMATCH`; a
   selected blocked composite renders blocked; and every frozen name appears
   in comparison diagnostics even when displaced. (Fixture builds never
   construct a real
   composite board — `real_assembly` gating at `:1340` — so injection is the
   only non-vacuous path.)
3. Scorer unit tests: lexicographic dominance of green_fraction over
   context_term; full tie-tail determinism (two permutations of input order
   produce identical output order).
4. Named acceptance metrics (required by the experiment-constraint pattern
   `.cursorrules:133-135`): (a) flag-OFF golden byte-identity PASS; (b)
   flag-ON injected-fixture reorder test PASS; (c) full suite + ruff +
   pyright exit 0. Failure behavior: any exception inside context-lane
   scoring renders the section as "CONTEXT LANE FAILED — <error class>"
   (loud), never a silent fallback to frozen-only. Rollback: set
   `CONTEXT_LANE_ENABLED = False` (restores byte-identical page); full
   removal = delete `context_lane.py`, the render branch, and the config
   block — no other surface touches them.
5. Owner decisions this brief surfaces (Codex does NOT act on these):
   - **D-1 — RULED (owner-directed in-session 2026-08-25, spoken: "switch
     context lane"):** the owner intends the lane to be enabled after the
     feature lands. The implementation worker nevertheless keeps
     `CONTEXT_LANE_ENABLED = False` throughout its draft PR, preserving the
     flag-OFF golden and rollback path, and stops. A separate owner-controlled
     follow-up, after merge and with explicit landing authority, may set it to
     `True` with the comment "owner-directed in-session 2026-08-25 (spoken,
     not owner-typed)". Brief 27 WP-F.3 is NOT satisfied until that owner
     action is present on `origin/main`; an intention to flip is not a flip.
   - **D-2 — RULED (owner-directed in-session 2026-08-25, spoken:
     "annotate all 5 picks"):** research bundles annotate
     `PICK_TOP_N`+pinned. The 2026-08-25 parameter audit confirmed this is
     the no-edit path — the research tool inherits the selector default and
     no verifier pins a count (`tools/research_context_assemble.py:66,68`;
     `attractiveness_research_v2.required_symbols` derives the set). One
     audited line for the runbook/packet: the annotated-candidate count is
     DERIVED from the live board, never pinned in the research path; if the
     derived required-symbol set cannot be covered within the per-attempt
     budget
     (`tools/launchd/com.carsyn.options-validator.research-refresh.plist:24-27`;
     the job runs on the owner's Claude Max login, so the practical constraint
     is plan usage, not dollars), the run fails closed and reports the
     shortfall — it never annotates a subset silently.

## Acceptance / verification

```bash
uv run python -m unittest discover -s tests    # exit 0, offline
uv run ruff check .                            # exit 0
uv run ruff format --check options_researcher/display_rank.py options_researcher/context_lane.py
uv run pyright                                 # exit 0
```
Plus WP-E.4's named metrics and the unmodified AST boundary test.
The hand-off artifact is a GitHub draft PR with `isDraft=true`; green checks
do not authorize readiness, merge, enablement, or deployment.

## Claim-discipline register

- Producer LaunchAgent enabled, 13 runs, last exit 3, UPSTREAM_BLOCKED cause:
  Repo-verified live 2026-08-25 (`launchctl print` + producer logs quoted
  above). The runbook's "intentionally left disabled and unloaded" line
  (`docs/research-context-refresh-runbook.md:57`) is STALE against the live
  system — flagged, not resolved, here.
- Frozen-baseline and promotion clauses: Repo-verified `.cursorrules:130-139`.
- RQ2/A2 forward window open since 2026-08-17: Repo-verified ledger seq 26/27.
- Composite build gating and veto semantics: Repo-verified
  `attractiveness_dashboard.py:1340`, `composite_signals.py:557-558` @720a20e.
- Direction mapping reuse: Repo-verified — `_BUY_LANES`/`_SELL_LANES`
  defined at `attractiveness_dashboard.py:215-216`, used by the quality key
  at `:624-628` @720a20e.
- Trend angle emits UP/DOWN/MIXED/DATA_BLOCKED: Repo-verified
  `composite_signals.py:128-168`; DOWN/MIXED receive zero context credit by
  this brief's LLM-proposed rule.
- Lexicographic-over-weighted: Inference from composite-lane doctrine
  (`composite_signals.py:32,76,520`).
- context_term position, UP-only-for-all-lanes rule: LLM-proposed 2026-08-25,
  labeled in code; reviewable at promotion time.
