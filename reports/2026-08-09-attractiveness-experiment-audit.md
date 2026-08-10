# Attractiveness experiment program — fresh-context audit record (2026-08-09)

Three fresh-context Claude Sonnet 5 auditors reviewed the finished
artifacts (selection report, authorization record, design spec, master
brief, four Codex briefs, parking-lot dispositions append, JSON/CSV
exports, rule-file edits). None had participated in Waves 1–2. Every
finding was independently verified by Fable against primary repo evidence
before a correction was applied; a fourth fresh-context verifier then
confirmed every correction. Verdicts are per-auditor; findings are listed
with their dispositions.

## Verdicts

| Auditor | Scope | Initial verdict | After corrections |
|---|---|---|---|
| A | Evidence and data integrity | REVISE (1 major, 2 minor) | corrections verified |
| B | Repo duplication and architecture | REVISE (1 critical, 2 major, 5 minor) | corrections verified |
| C | Quant design and Codex completeness | REVISE (2 critical, 5 major, 2 minor) | corrections verified |
| Focused re-verifier | All corrected locations | — | ALL CORRECTIONS VERIFIED, no new inconsistencies |

No critical or major finding remains open. Codex-readiness gate: PASS
(as a handoff; Codex itself is unavailable on this machine).

## Critical findings (all fixed)

1. **C-F1 (brief 02, self-contradiction):** §16's 126-obs causal-sigma
   floor vs §32's `rolling(252)` hint (pandas defaults min_periods to
   the window — a 2.4× swing in evaluable days on CRWV). FIX: §32 now
   mandates `rolling(252, min_periods=126)`; new named boundary test.
2. **C-F2 (brief 04, missing invalid-quote guard):** a zero-bid/crossed
   reference put would have fed a degenerate mid into the yield math.
   FIX: brief 03's invalid-quote rule replicated into §16/§19 + named test.
3. **B-B1 (master brief + spec, silent-enable hazard):** the cited
   "composite pattern" auto-computes on `None` during real assembly with
   NO flag gate; copying it would have enabled all four experiments in
   every no-arg production rebuild (`daily_ritual.sh`,
   `research_refresh.sh`) despite `EXPERIMENT_LANES_ENABLED` all-False.
   FIX: experiments must NEVER self-compute on None; only the CLI path
   builds payloads under `--experiments`/config flags; the baseline test
   suite now must exercise the real `main()` entry point with mocked
   `_gather_all` and assert the section is absent.

## Major findings (all fixed)

- **C-F3:** brief 04's spot source ("the chain-session close store the
  dashboard already uses") named a mechanism that doesn't exist. FIX:
  exact call pinned (`load_closes(..., chain_session_date,
  allow_oos=True).iloc[-1]`) + session-match test.
- **C-F4:** EXP-BETA's dollar-translation required an unfrozen notional
  convention (strike- vs entry- vs delta-based, multi-leg aggregation).
  FIX: CUT from v1 across brief 01 and the spec; no positions access at
  all in v1; future scope with its own reviewed convention.
- **C-F5:** no selection-effect/K-counting disclosure anywhere. FIX:
  added to spec §10 (binding on promotion) and selection report §10.
- **C-F6:** EXP-TAIL copy could render moments with false precision at
  n≈339. FIX: `n_obs` mandatory in rendered copy (and
  `baseline_sessions_used` for EXP-SPREAD).
- **C-F8:** brief 04 called `dividend_yield` with no schema field for
  the result. FIX: dividend read removed from v1 scope.
- **B-B2:** neither chain-reading brief mentioned `allow_oos=True`;
  `IN_SAMPLE_END=2022-12-31` means default reads raise
  `OOSDataTouchError` at every 2026 session, which the blocked-card
  wrapper would silently turn into an all-blocked board. FIX: mandated
  in briefs 03/04 (+ spec) with the `composite_signals.py:682` precedent
  cited, plus loud not-all-blocked acceptance assertions.
- **B-B3:** the "tiny gating_v3 reader" ignored that gating_v3 carries
  event classes, retractions, and supersession. FIX: exact filter
  specified (actual_quarterly_earnings, assertion, not-retracted,
  occurred_date vs expected_date) + fixture test.
- **A-01:** selection report claimed rates `valid_through ≤ 2026-09-13`;
  measured truth: Treasury curve maxes 2026-07-27 (co-terminous with the
  chain freeze); dividends expire per name 2026-07-31 → 2026-10-26. FIX:
  corrected in §9.

## Minor findings (all fixed or dispositioned)

- C-F7 rollback enumeration (flags dict + health strip) — fixed in spec §10.
- C-F9 Stage-B prompt file-scope + garbled checklist wording — fixed.
- B-B4 `type(x) is date` exact-type gotcha in rates loaders — noted in
  brief 04 §17 with `date.fromisoformat()` requirement.
- B-B5 three unrelated meanings of "skew" in the repo — disambiguating
  docstring note mandated in brief 02 §12.
- B-B7 getattr-fallback constants pattern adjudicated as acceptable for
  dead-until-wired display modules; config-vs-default drift test added
  to the Stage-B baseline suite.
- B-B8 spec wording (nearest_monthly + atm_row) — fixed.
- B-B6 relative-spread formula precedents in options_flow/audit tools —
  verified different domain, no action.
- A-02 QQQ/SPY closes end 2026-08-03 (one session behind the names) —
  spec/brief wording corrected; asymmetric-end-date test added.
- A-03 report table is a coarser rollup than the JSON `category` field —
  clarifying sentence added.

## Dispositions on auditor meta-notes

- Auditor A could not re-derive the Wave-2 numeric scores from the raw
  transcripts (unstructured logs). Disposition: the four transcripts are
  preserved under `.tmp/research/parking-lot-471/wave2_transcripts/`;
  scores in the scorecard are quoted verbatim from each reviewer's
  structured JSON; accepted as sourced, flagged here for transparency.
- Auditor C's duplicate-risk note (EXP-TBILL card must not be mistakable
  for a registered-hypothesis card) — folded into the Stage-B review
  focus: the experiments section header and per-line display-only labels
  are the required separation.

## Residual risks after audit

1. Codex is unavailable; nothing is implemented. The handoff is
   copy-ready but unexecuted, and Stage-A acceptance criteria that
   depend on the real cache have not been run.
2. Chain-lane experiments are capped at the frozen 2026-07-27 edge until
   a provider decision; the T-bill lane's Treasury curve expires at the
   same edge (owner refresh action).
3. Wave-2 strike-density spot-checks were VST-only (extrapolated,
   disclosed).
4. The session-start git snapshot anomaly (a prior session's identical
   rule edits that are no longer on disk) is disclosed in the selection
   report §9; if that state resurfaces, keep exactly one copy.
