# Codex brief 25 — daily market context that visibly contributes to a labeled second ranking lane (rev 3)

**Date:** 2026-08-25 (rev 3, same day)
**Author:** Claude orchestrating session (Fable), 2026-08-25
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** READY FOR HAND-OFF — adversarial review round 3 verdict **PASS** (rounds 1-3 recorded in `reports/2026-08-25-briefs-25-27-adversarial-review-receipt.md`). Hand-off still waits on brief 26 landing first (binding order 26 → 25 → 27).
**Provenance:** Repo-verified against commit `720a20e` on branch `claude/codex-handoff-plan-2026-08-22` unless labeled otherwise. Landing order is binding: **brief 26 lands first, then this brief, then brief 27** (shared constants and heading strings flow 26 → 25 → 27).
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

1. Inputs: the assembled board sections AND the composite board object built
   during real assembly (`attractiveness_dashboard.py:1340` @720a20e:
   `if composite_signals is None and real_assembly:` — pass the built board
   in; never rebuild it per page).
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
     Stated plainly: the composite trend angle emits ONLY `UP`, `DOWN`, or
     DATA_BLOCKED (Repo-verified `composite_signals.py:164,166,89`; there is
     no neutral state, and `aligned_count` already zeroes non-UP/DOWN states
     at `:540`), so for EVERY lane the context term is nonzero only on `UP` —
     buy lanes because direction agrees, sell lanes because premium selling
     against a confirmed DOWN trend must not be promoted by "alignment". Do
     not write a branch for any other trend state; it would be dead code.
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
3. Fail-visible: a symbol whose composite card is DATA_BLOCKED renders in the
   lane with its blocked state and context_term reason; the lane never drops
   a name the frozen shortlist shows (`_blocked_html` ethos,
   `attractiveness_dashboard.py:3971` docstring @720a20e).
4. Test updates for flag-ON ordering are additive-only: new flag-ON test
   asserts the insertion point; the flag-OFF path leaves EVERY existing
   ordering test untouched (the full enumerated ordering-test list lives in
   brief 26 WP-E; this brief adds none of its own heading strings to the
   flag-OFF page).

### WP-D — honest research staleness note (rev-1 findings 1, 11, 29)

1. Freshness-strip research chip: add the causal sentence to its
   notice/tooltip: "Research refresh is currently blocked upstream: the
   morning data ritual has not been finishing cleanly, so the researcher
   refuses to run (fail-closed). See the ops ritual-health investigation."
   Plain English, no launchctl instructions, no dollar figures, no claim
   about the LaunchAgent being disabled.
2. Do NOT render budget numbers. (Rev-1 WP-C.2 hardcoded $8/$200 with a wrong
   citation and a false offline-impossibility claim — deleted. If the owner
   later wants spend surfaced, that is an owner decision with owner-typed
   figures.)
3. Research-bundle candidate-count cost note (rev-1 finding 29): moved OUT of
   a PR description into this brief as an explicit owner decision — see
   WP-E.4 D-2.

### WP-E — tests, acceptance, failure behavior, rollback (rev-1 findings 10, 26)

1. Flag-OFF byte-identity golden test (WP-C.1).
2. Flag-ON tests MUST inject a synthetic composite board with mixed
   `aligned_count`/grade/trend values and assert an ACTUAL order change vs
   the frozen lane, plus: vetoed (grade C) name never outranks its frozen
   position via context; DOWN-trend name gains 0 on a buy lane; blocked
   composite renders blocked. (Fixture builds never construct a real
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
   - **D-1:** when to flip `CONTEXT_LANE_ENABLED = True` (proposal: after
     brief 27's dry-run recorder is live, so the lane's picks are recorded
     from day one — but the flip itself is the owner's).
   - **D-2:** whether research bundles should annotate `PICK_TOP_N`+pinned
     candidates (≈66% more packets per run against the plist's
     $8.00/attempt, $200.00/month budgets —
     `tools/launchd/com.carsyn.options-validator.research-refresh.plist:24-27`,
     Repo-verified) or stay at 3+pinned.

## Acceptance / verification

```bash
uv run python -m unittest discover -s tests    # exit 0, offline
uv run ruff check . && uv run pyright          # exit 0
```
Plus WP-E.4's named metrics and the unmodified AST boundary test.

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
- Trend angle emits only UP/DOWN/DATA_BLOCKED: Repo-verified
  `composite_signals.py:164,166,89,540`.
- Lexicographic-over-weighted: Inference from composite-lane doctrine
  (`composite_signals.py:32,76,520`).
- context_term position, UP-only-for-all-lanes rule: LLM-proposed 2026-08-25,
  labeled in code; reviewable at promotion time.
