# Codex brief 02 — EXP-TAIL: realized tail-shape line (2026-08-09)

1. **Title:** EXP-TAIL rolling realized tail-shape display experiment.
2. **Executor:** gpt-5.6-sol, reasoning effort medium.
3. **Base commit:** `1866f59f5d9c976363315878072a1e17165a385a`.
4. **Dependencies:** none (Stage A; parallel-safe).
5. **Goal:** a display-only line describing the SHAPE of each name's
   realized return history — skewness, excess kurtosis, and a causal
   jump count — so the operator sees "this name jumps" where the cushion
   metric only shows level.
6. **Why selected:** Wave-2 consensus 84.5; survey's own "strongest of
   the parked set" (rank 7); tail shape is exactly where loss-gated
   verdicts say the information lives; closes-only, freshest data lane.
7. **Evidence:** survey rank 7 row (standard short-vol tail literature);
   parking lot lines 886–887; selection report §6.2. Quant review defect
   (self-referential sigma) fixed by design in §16.
8. **Existing assets to reuse:** `data/underlying_closes.load_closes_adjusted`;
   composite fixed-key dict + blocked-card pattern.
9. **Scope:** new module + new test file ONLY.
10. **Non-goals:** no config.py/dashboard edits (Stage B); no CVaR (rejected
    overlap, C6); no grading; no persisted cache; no intraday anything.
11. **Files changed:** `options_researcher/exp_tail_shape.py` (new),
    `tests/test_exp_tail_shape.py` (new).
12. **Symbols reused:** `load_closes_adjusted`, numpy/pandas. Module
    docstring MUST note (audit B5): this module's skew/kurtosis are
    bias-corrected sample moments with EXCESS kurtosis (pandas
    convention), a deliberately different convention from
    `metrics.sample_moments` (population moments, RAW kurtosis, strategy
    PnL domain) and unrelated to `composite_signals`' implied-vol
    "skew_25d" — three different things share the word "skew".
13. **New interface:**
    `exp_tail_shape(closes: pd.Series, *, asof: str) -> dict` and
    `build_exp_tail_board(symbols, *, asof) -> list[dict]` (loads,
    truncates to `<= asof`, per-symbol blocked cards on exception).
14. **Input schema:** date-indexed close Series truncated to `<= asof`.
15. **Output schema (fixed keys):** `{"experiment_id": "EXP-TAIL",
    "state": "OK"|"UNSTABLE"|"DATA_BLOCKED", "data_blocked", "reason",
    "asof", "max_asof", "skew": float|None, "excess_kurtosis": float|None,
    "jump_count": int|None, "jump_rate": float|None, "window": int,
    "n_obs": int, "window_agreement": bool|None, "caveat": str}`.
16. **Formula:** daily log returns `r_t`. Over the trailing
    `EXP_TAIL_WINDOW=252` returns ending at `max_asof`: sample skewness
    and excess kurtosis (pandas `.skew()`/`.kurt()`, bias-corrected).
    **Causal jump rule:** `jump_count = #{t in window: |r_t| >
    3 * sigma_before(t)}` where `sigma_before(t)` = std (ddof=1) of the
    252 returns strictly BEFORE t (min 126 to evaluate a day; days with
    insufficient prior history are excluded from both numerator and
    denominator; `jump_rate = jump_count / evaluable_days`). The sigma
    judging a day never includes that day or any later day — this is the
    mandated fix for the survey formula's self-referential sigma.
17. **Causal timing:** board builder truncates to `<= asof`; the causal
    sigma rule additionally guarantees within-window causality.
18. **As-of rules:** closes lane; `max_asof` = last close ≤ asof
    (currently 2026-08-04); never shares a stamp with chain-based lanes.
19. **Missing data:** `n_obs < EXP_TAIL_MIN_OBS=250` → DATA_BLOCKED
    ("fewer than 250 usable sessions"); zero evaluable jump days →
    jump fields None with reason noted, moments still shown.
20. **Stale data:** disclosed via the stamp only (closes are freshest).
21. **Failure behavior:** blocked card on any exception; never partial.
22. **Configuration:** module defaults via `getattr(config, ...)`:
    `EXP_TAIL_WINDOW=252`, `EXP_TAIL_MIN_OBS=250` (survey's own NaN-gate
    figure), `EXP_TAIL_JUMP_SIGMA=3.0` (standard convention),
    `EXP_TAIL_ALT_WINDOWS=(189, 378)`. Provenance comment on each:
    "LLM-proposed 2026-08-09; survey rank-7 convention; display-only;
    not owner-ratified."
23. **Owner-controlled values:** none now; promotion is a future gate.
24. **Security/provider:** offline; one parquet series per name.
25. **Dashboard behavior (Stage B consumes):** one plain sentence that
    MUST state the sample size, e.g. "4 surprise moves bigger than 3×
    normal in the past year (based on 339 sessions); recent surprises
    leaned down; fatter-tailed than a normal bell curve — history, not a
    forecast." Rendering `n_obs` in the copy is mandatory, not optional
    (false-precision guard at low n). **Stability diagnostic:** recompute skew
    sign and kurtosis>1 flag at windows {189, 252, 378}; if any flips,
    `state="UNSTABLE"`, `window_agreement=False`, and the copy says
    "UNSTABLE across window choices" instead of a confident read.
    `caveat` fixed string: "Describes past return shape only; not a
    forecast; a calm year hides tail risk."
26. **Named tests:** `test_key_contract`,
    `test_synthetic_negative_skew_recovered`,
    `test_synthetic_kurtosis_recovered`,
    `test_jump_count_engineered_jumps`,
    `test_causal_sigma_red` (see §28),
    `test_causal_sigma_min_periods_boundary` (a day with exactly 126–251
    prior observations IS evaluable; a day with 125 is NOT — pins the
    min_periods=126 requirement in §32),
    `test_min_obs_blocked`, `test_window_agreement_flag`,
    `test_no_lookahead_invariance`, `test_board_blocked_card`.
27. **Baseline tests:** untouched; full suite stays green.
28. **Red test first:** `test_causal_sigma_red` — construct a series
    where an in-window sigma WOULD absorb a large late move (classifying
    an early move differently than the causal rule does); assert the
    causal classification. Write against the unbuilt module, show it
    fail, then implement.
29. **Targeted verification:** `uv run python -m unittest tests.test_exp_tail_shape`.
30. **Full verification:** full unittest discovery, ruff on the two
    files, pyright, `git diff --check`.
31. **Acceptance criteria:** named tests green; synthetic moments within
    tolerance (skew ±0.1, kurtosis ±0.3 at n=5,000); engineered-jump
    count exact; all 15 board names render on the real cache
    (cache-conditional test; every name has ≥339 closes ≥ min 250 —
    CRWV thinnest at 339); UNSTABLE path exercised.
32. **Performance limits:** in-memory pandas; the causal-sigma rolling
    std is one `shift(1).rolling(252, min_periods=126).std()` pass
    (min_periods=126 is REQUIRED — pandas defaults min_periods to the
    window, which would contradict §16's 126-obs floor) — board < 2s.
33. **Rollback:** delete the two files.
34. **Commit boundary:** one commit,
    `feat(exp): EXP-TAIL realized tail-shape display experiment (module + tests)`,
    branch `codex/attractive-exp-tail-shape`.
35. **Stop conditions:** closes loader signature drift; any network need.
36. **Unsupported assumptions:** none knowingly; pandas skew/kurt
    bias-correction semantics asserted in a fixture test rather than
    assumed.
37. **Remaining risks:** moment noise at n≈339 for the youngest names
    (disclosed via n_obs display + UNSTABLE diagnostic); cross-name
    correlated tails on shock days mean 15 lines are not 15 independent
    facts (caveat covers).
38. **Fable review checklist:** master checklist + verify the causal
    sigma uses `shift(1)` (or equivalent) and that no in-window sigma
    path survives anywhere.
