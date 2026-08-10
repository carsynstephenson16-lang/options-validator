# Codex brief 03 — EXP-SPREAD: spread-stability annotation (2026-08-09)

1. **Title:** EXP-SPREAD "wide today vs always wide" display experiment.
2. **Executor:** gpt-5.6-sol, reasoning effort medium.
3. **Base commit:** `1866f59f5d9c976363315878072a1e17165a385a`.
4. **Dependencies:** none (Stage A; parallel-safe).
5. **Goal:** annotate the reference contract's relative spread at the
   as-of session against its own trailing baseline, so the operator can
   tell an unusually expensive-to-trade day from a name that is always
   wide. The existing liquidity gate is a static pass/fail; this is the
   missing dynamic view.
6. **Why selected:** Wave-2 consensus 81.3; the only execution-cost-
   dynamics candidate; data verified (≈25 consecutive chain sessions to
   the 2026-07-27 edge, plus years of history for test replay).
7. **Evidence:** survey rank 12 (George–Longstaff 1993); parking lot
   lines 895–896; selection report §6.3. Quant defects (contract
   identity across expiry rolls; baseline contamination) are closed by
   the §16 design, which is an acceptance criterion.
8. **Existing assets to reuse:** `options_researcher/chains.py`
   (`nearest_monthly`, `atm_row` with target delta), the chain-cache
   loading idiom used by `composite_signals` (bounded trailing window of
   chain files) — **every chain read MUST pass `allow_oos=True`
   (`composite_signals.py:682` precedent): `IN_SAMPLE_END=2022-12-31`
   means the default `allow_oos=False` raises `OOSDataTouchError` for
   every 2026 session, which the blocked-card wrapper would silently
   convert into an all-DATA_BLOCKED board** — plus
   `data/earnings/gating_v3.csv` read-only for earnings-week exclusion,
   and the composite blocked-card pattern.
9. **Scope:** new module + new test file ONLY.
10. **Non-goals:** no config/dashboard edits (Stage B); no liquidity-gate
    change; no H7 API use beyond read-only file access; no threshold
    that grades or orders anything; no persisted cache.
11. **Files changed:** `options_researcher/exp_spread_stability.py` (new),
    `tests/test_exp_spread_stability.py` (new).
12. **Symbols reused:** `chains.nearest_monthly`, `chains.atm_row`,
    pandas/numpy; a tiny local `gating_v3` CSV reader (read-only, no H7
    module import — isolation from the registered lane made concrete).
    **The local reader MUST apply this exact filter (audit B3 —
    gating_v3 is not a flat date list):** keep only rows with
    `event_class == "actual_quarterly_earnings"` and
    `record_type == "assertion"`; drop any assertion row that a later
    `record_type == "retraction"` row names in its `supersedes` column;
    the operative date is `occurred_date` when `status == "occurred"`,
    else `expected_date`. Named test required
    (`test_gating_v3_filter_semantics`) with fixture rows covering a
    business_update row (ignored), a retracted assertion (ignored), and
    an occurred vs estimated date pick.
13. **New interface:**
    `exp_spread_stability(chain_by_session: dict[str, pd.DataFrame], *, asof: str, earnings_weeks: set[str]) -> dict`
    plus `build_exp_spread_board(symbols, *, asof) -> list[dict]` (loads
    the trailing ≤ `EXP_SPREAD_LOOKBACK_SESSIONS=25` cached chain files
    per symbol up to `asof`, derives earnings-week session sets from
    gating_v3, per-symbol blocked cards).
14. **Input schema:** `chain_by_session` maps ISO session → that
    session's chain DataFrame (cached schema: expiration, strike, right,
    bid, ask, open_interest, iv, delta, ...), all sessions `<= asof`.
15. **Output schema (fixed keys):** `{"experiment_id": "EXP-SPREAD",
    "state": "OK"|"ELEVATED"|"DATA_BLOCKED", "data_blocked", "reason",
    "asof", "max_asof", "rel_spread_today": float|None,
    "baseline_median": float|None, "ratio": float|None,
    "baseline_sessions_used": int, "today_is_earnings_week": bool,
    "caveat": str}`.
16. **Formula (mandated design, closes both review defects):**
    - **Role-based series:** for each session independently, the
      reference row = the near-tenor (nearest monthly expiration in the
      15–60 DTE band) put closest to 0.50 delta via `atm_row` — never a
      fixed (strike, expiration) identity carried across sessions.
    - `rel_spread = (ask - bid) / mid`, `mid = (ask + bid)/2`; rows with
      `bid <= 0`, crossed quotes (`ask < bid`), or `mid <= 0` are invalid
      → that session drops from the baseline (and today → DATA_BLOCKED).
    - **Baseline:** median of `rel_spread` over the trailing
      `EXP_SPREAD_BASELINE=20` sessions strictly BEFORE the as-of session
      ([t−20, t−1]; today's reading is never in its own baseline),
      excluding sessions inside an earnings week per gating_v3.
    - `ratio = rel_spread_today / baseline_median`. If today is an
      earnings week the reading still renders with
      `today_is_earnings_week=True` and copy noting it.
17. **Causal timing:** all inputs are cached sessions `<= asof`; the
    baseline is strictly historical by construction.
18. **As-of rules:** chain lane — `max_asof` = the newest chain session
    used (2026-07-27 at the current frozen edge). Must never display a
    closes-lane date.
19. **Missing data:** fewer than `EXP_SPREAD_MIN_BASELINE_OBS=10` valid
    baseline sessions → DATA_BLOCKED ("fewer than 10 usable baseline
    sessions"); no valid reference row today → DATA_BLOCKED; gating_v3
    unreadable → DATA_BLOCKED (never "assume no earnings").
20. **Stale data:** the frozen chain edge is disclosed by the stamp; no
    freshness pretense.
21. **Failure behavior:** blocked card on exception; never partial.
22. **Configuration (module defaults via getattr):**
    `EXP_SPREAD_BASELINE=20` (survey's own figure),
    `EXP_SPREAD_MIN_BASELINE_OBS=10`, `EXP_SPREAD_LOOKBACK_SESSIONS=25`,
    `EXP_SPREAD_ELEVATED=2.0` (display label only; the ratio is always
    printed), near-tenor band `(15, 60)` DTE + 0.50Δ put mirroring the
    composite near-tenor convention. Provenance comments as in the
    design spec.
23. **Owner-controlled values:** none now; any future gating use is
    owner-gated.
24. **Security/provider:** offline; bounded chain-file reads only.
25. **Dashboard behavior (Stage B):** one line that MUST state the
    baseline sample size, e.g. "This contract's spread at the 07-27
    close was 2.8× its usual level (median of 17 usable prior sessions)
    — trading would likely have cost more than typical. Descriptive, as
    of the frozen chain date; not a forecast." Rendering
    `baseline_sessions_used` is mandatory (false-precision guard). The word "today" must NOT appear
    while the chain lane is frozen. `state="ELEVATED"` iff
    `ratio >= EXP_SPREAD_ELEVATED`.
26. **Named tests:** `test_key_contract`,
    `test_gating_v3_filter_semantics` (see §12),
    `test_known_median_ratio` (synthetic 21-session fixture),
    `test_baseline_excludes_today_red` (see §28),
    `test_baseline_excludes_earnings_weeks`,
    `test_today_earnings_week_still_renders_labeled`,
    `test_invalid_quotes_dropped`, `test_min_baseline_blocked`,
    `test_role_based_reference_across_roll` (fixture spanning a monthly
    expiry roll: reference row re-resolves each session, no identity
    carry), `test_no_lookahead_invariance`, `test_board_blocked_card`.
27. **Baseline tests:** untouched; full suite stays green.
28. **Red test first:** `test_baseline_excludes_today_red` — fixture
    where including today in its own baseline changes the ratio
    materially; assert the [t−20, t−1] value. Fail first, then implement.
29. **Targeted verification:** `uv run python -m unittest tests.test_exp_spread_stability`.
30. **Full verification:** full discovery, ruff on the two files,
    pyright, `git diff --check`.
31. **Acceptance criteria:** named tests green; on the real cache at
    asof=2026-07-27 the board renders for every name with ≥10 valid
    baseline sessions, AND the cache-conditional test asserts loudly that
    at least one name is NOT DATA_BLOCKED (an all-blocked board — the
    signature of a missing `allow_oos=True` — must FAIL the test, not
    quietly pass); an
    additional cache-conditional replay over ≥60 historical sessions for
    one deep name (VST) completes without error and yields a finite
    ratio distribution (median logged, not asserted against a value).
32. **Performance limits:** ≤25 chain-file reads per symbol per call;
    whole board target < 20s on the local cache; no persisted artifacts.
33. **Rollback:** delete the two files.
34. **Commit boundary:** one commit,
    `feat(exp): EXP-SPREAD spread-stability display experiment (module + tests)`,
    branch `codex/attractive-exp-spread-stability`.
35. **Stop conditions:** chain schema missing bid/ask; `atm_row`
    signature drift; gating_v3 schema drift; any network need.
36. **Unsupported assumptions:** earnings-week definition = the
    calendar week (Mon–Fri) containing the asserted earnings date from
    gating_v3; stated in-module and in the display copy.
37. **Remaining risks:** role-based reference can jump strikes on big
    spot moves (by design; disclosed in module docstring); 07-28+ has no
    chain data until a provider decision (stamp discloses).
38. **Fable review checklist:** master checklist + verify no H7 module
    import, baseline window indices, and the absence of the word
    "today" in rendered copy for the frozen lane.
