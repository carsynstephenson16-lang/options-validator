# Codex brief 01 — EXP-BETA: beta-to-QQQ translation line (2026-08-09)

1. **Title:** EXP-BETA rolling beta-to-QQQ display experiment.
2. **Executor:** gpt-5.6-sol, reasoning effort medium.
3. **Base commit:** `1866f59f5d9c976363315878072a1e17165a385a`.
4. **Dependencies:** none (Stage A; parallel-safe). Stage-B wiring brief
   consumes this module later.
5. **Goal:** a pure, display-only function that states how much of a board
   name's daily movement behaves like QQQ (beta + R² + stability
   diagnostic), with honest refusals and its own as-of stamp.
   (A position dollar-translation line was CUT from v1 in adversarial
   review: deriving a scalar notional from the options position schema
   requires an aggregation/delta-adjustment convention nobody has frozen;
   inventing one violates the no-unresolved-choices rule. Future scope,
   with its own reviewed convention.)
6. **Why selected:** Wave-2 consensus 86.3 (top of 9); the only candidate
   on the factor-exposure axis — the standing "whole book is ONE AI
   factor" concern; former NEEDS-DATA blocker measurably resolved
   (QQQ.parquet 2,408 rows, 2017-01-03→2026-08-03).
7. **Evidence:** survey rank 15 (`reports/2026-07-22-scanner-quant-methods-survey.md`,
   Sharpe 1964 CAPM beta, Official/literature-standard); parking lot lines
   901–903; selection report §6.1.
8. **Existing assets to reuse:** `data/underlying_closes.load_closes_adjusted`
   (symbol + "QQQ"); the fixed-key dict + `_blocked_*` constructor pattern
   from `options_researcher/composite_signals.py`. No positions access in
   v1 (see §5).
9. **Scope:** new module + new test file ONLY.
10. **Non-goals:** no config.py edit (Stage B), no dashboard edit, no
    ranking influence, no SPY variant, no persisted cache, no crash-beta
    modeling (caveat text only), no positions access at all in v1 (the
    dollar-translation line is deferred until a notional convention is
    frozen and reviewed).
11. **Files changed:** `options_researcher/exp_beta_qqq.py` (new),
    `tests/test_exp_beta_qqq.py` (new). Nothing else.
12. **Symbols reused:** `load_closes_adjusted`, `numpy`/`pandas` only.
13. **New interface:**
    `exp_beta_qqq(closes: pd.Series, bench_closes: pd.Series, *, asof: str) -> dict`
    and `build_exp_beta_board(symbols: list[str], *, asof: str) -> list[dict]`
    (loads + truncates closes to `<= asof` for each symbol and QQQ;
    per-symbol try/except → blocked card, composite pattern).
14. **Input schema:** `closes`/`bench_closes` = date-indexed float Series
    already truncated to `<= asof` by the caller inside this module's
    board builder; `asof` = ISO date string.
15. **Output schema (fixed keys):** `{"experiment_id": "EXP-BETA",
    "state": "OK"|"UNSTABLE"|"DATA_BLOCKED", "data_blocked": bool,
    "reason": str|None, "asof": str, "max_asof": str (last session actually
    used, min of the two series), "beta": float|None, "r_squared":
    float|None, "beta_half_window": float|None, "n_obs": int,
    "caveat": str}`.
16. **Formula:** daily log returns; align on common dates; over the
    trailing `EXP_BETA_WINDOW=252` sessions ending at `max_asof`:
    `beta = Cov(r_i, r_qqq) / Var(r_qqq)` (sample, ddof=1);
    `r_squared = corr(r_i, r_qqq)**2`; `beta_half_window` = same formula
    over the trailing 126 sessions.
17. **Causal timing:** the board builder truncates both series to
    `<= asof` BEFORE computing; the pure function never sees later rows.
18. **As-of rules:** `max_asof` = the LAST COMMON session of the two
    series (i.e. the min of their end dates). This asymmetry is real
    today: board-name closes end 2026-08-04 but QQQ ends 2026-08-03, so
    the honest stamp is 2026-08-03. Closes lane, independent of the
    frozen chain lane — never share a stamp with chain-based lanes.
19. **Missing data:** <`EXP_BETA_MIN_OBS=126` paired obs →
    DATA_BLOCKED/"insufficient overlapping history (<126 sessions)";
    zero-variance benchmark window → DATA_BLOCKED/"degenerate benchmark
    variance"; no QQQ series → DATA_BLOCKED.
20. **Stale data:** none beyond as-of stamping (closes are the freshest
    lane); the stamp itself is the staleness disclosure.
21. **Failure behavior:** any exception in the board builder → blocked
    card with the exception class in `reason`; never a partial dict.
22. **Configuration:** module-level frozen defaults
    `EXP_BETA_WINDOW=252`, `EXP_BETA_HALF_WINDOW=126`,
    `EXP_BETA_MIN_OBS=126`, `EXP_BETA_UNSTABLE_DELTA=0.5`, each read via
    `getattr(config, name, default)` so Stage B can move them into
    config.py without editing this module. Comment on each: "LLM-proposed
    2026-08-09; repo convention (COMPOSITE_PCTL_WINDOW/MIN_OBS analog);
    display-only; not owner-ratified."
23. **Owner-controlled values:** none now; promotion into any
    grading/ranking is a future owner gate (feasibility gate 2026-07-24).
24. **Security/provider constraints:** offline only; reads two parquet
    close series; nothing else.
25. **Dashboard behavior:** handled in Stage B; this module only supplies
    the dict, including the mandatory `caveat`:
    "Betas drift toward 1 in sharp selloffs; a calm-period beta
    understates crash co-movement. Descriptive history, not a forecast."
    `state="UNSTABLE"` when sign(beta) != sign(beta_half_window) or
    |beta - beta_half_window| > EXP_BETA_UNSTABLE_DELTA.
26. **Named tests:** `test_key_contract`, `test_qqq_vs_itself_beta_one`,
    `test_synthetic_double_beta`, `test_insufficient_overlap_blocked`,
    `test_degenerate_bench_blocked`, `test_unstable_flag`,
    `test_no_lookahead_invariance`,
    `test_max_asof_min_of_asymmetric_end_dates` (bench series ending one
    session before the name series → max_asof = the earlier date; this
    is the cache's actual current state),
    `test_board_builder_blocked_card_on_exception`.
27. **Baseline tests:** none touched (module is unreferenced until
    Stage B; full suite must stay green).
28. **Red test first:** `test_qqq_vs_itself_beta_one` — write it against
    the not-yet-existing module, show ImportError/failure, then implement.
29. **Targeted verification:** `uv run python -m unittest tests.test_exp_beta_qqq`.
30. **Full verification:** `uv run python -m unittest discover -s tests`,
    `uv run ruff check options_researcher/exp_beta_qqq.py tests/test_exp_beta_qqq.py`,
    `uv run pyright`, `git diff --check`.
31. **Acceptance criteria:** all named tests green; β(QQQ,QQQ)=1±0.01;
    synthetic 2× series → β=2±0.05; board builder renders ≥12/15 board
    names on the real cache (asserted in a cache-conditional test that
    skips cleanly if the cache is absent); no-look-ahead invariance holds.
32. **Performance limits:** pure in-memory pandas on two Series; whole
    board < 2s on the cached data; no persisted artifacts.
33. **Rollback:** delete the two files; nothing else references them.
34. **Commit boundary:** one commit, message
    `feat(exp): EXP-BETA beta-to-QQQ display experiment (module + tests)`,
    Co-Authored-By per repo convention, branch `codex/attractive-exp-beta-qqq`.
35. **Stop conditions:** QQQ.parquet absent; closes loader signature
    differs from brief (report, don't adapt silently); any needed
    network access.
36. **Unsupported assumptions:** none knowingly.
37. **Remaining risks:** small-sample beta noise on CRWV/USAR/TEM (min
    floor mitigates; UNSTABLE state discloses); calm-period understatement
    (mandatory caveat).
38. **Fable review checklist:** master brief §review checklist applies;
    additionally verify the caveat string is present verbatim in the
    output dict and that the module contains NO positions access (cut
    in review).
