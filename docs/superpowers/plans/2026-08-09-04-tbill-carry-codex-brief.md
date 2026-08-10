# Codex brief 04 — EXP-TBILL: carry vs T-bill + assignment stub (2026-08-09)

1. **Title:** EXP-TBILL CSP/CC carry-vs-cash comparison with a fail-closed
   early-assignment stub.
2. **Executor:** gpt-5.6-sol, reasoning effort medium.
3. **Base commit:** `1866f59f5d9c976363315878072a1e17165a385a`.
4. **Dependencies:** none (Stage A; parallel-safe).
5. **Goal:** answer, per name, "does this cash-secured-put credit
   actually beat parking the collateral in T-bills?" using the repo's
   point-in-time Treasury curve; and represent early-assignment risk
   HONESTLY as data-blocked until an ex-dividend date calendar exists.
6. **Why selected:** Wave-2 consensus 78.5 (rescoped); survey rank 6 —
   its own "top of the unlock queue"; sole blocker (the two rates CSVs)
   measurably resolved 2026-08-04; OCC-official mechanics; the carry
   axis is untouched by every existing lane. Fourth-ranked below 80
   triggered the full-file fallback review; no pre-471 idea displaced it
   (selection report §7).
7. **Evidence:** survey rank 6 row (OCC Characteristics and Risks, June
   2024, Official-source; `oc = K*100*(e^(r*tau/365)-1)`); parking lot
   lines 916–920; `data/rates.py` fail-closed loaders (built, tested);
   selection report §6.4.
8. **Existing assets to reuse:** `data.rates.risk_free_rate(observation_date,
   expiration_date)` and its `MissingRateError`;
   `chains.nearest_monthly` + `atm_row` for the reference put; composite
   blocked-card pattern. (`data.rates.dividend_yield` is deliberately NOT
   used in v1 — the T-bill comparison needs no dividend input; a
   dividend-context line was cut in review because the fixed-key schema
   carries no field for it. Re-adding it is a future scope change.)
9. **Scope:** new module + new test file ONLY.
10. **Non-goals:** no config/dashboard edits (Stage B); no ex-div date
    fabrication or approximation (quarterly guessing is prohibited); no
    assignment probability model; no margin math; no CC lane beyond the
    dividend-yield read; no rates CSV refresh (owner data action).
11. **Files changed:** `options_researcher/exp_tbill_carry.py` (new),
    `tests/test_exp_tbill_carry.py` (new).
12. **Symbols reused:** as §8; pandas/numpy/math only.
13. **New interfaces:**
    `exp_tbill_carry(contract_row, spot: float, *, symbol: str, asof: str, expiration: str) -> dict`;
    `early_assignment_flag(*_args, **_kwargs) -> dict` (permanent stub);
    `build_exp_tbill_board(symbols, *, asof) -> list[dict]` (loads the
    as-of chain, picks the near-tenor 0.50Δ put via `atm_row`, calls the
    rates loaders, per-symbol blocked cards).
14. **Input schema:** one cached chain row (bid/ask/strike/expiration),
    ISO dates. Spot, when needed for display context, comes from EXACTLY
    `data.underlying_closes.load_closes(symbol, "2018-01-01",
    chain_session_date, allow_oos=True).iloc[-1]` — truncated to the
    CHAIN session actually used for the reference put (the
    attractiveness.py::main precedent), never to this module's `asof`
    parameter, so spot and quote always share one session date (named
    test below).
15. **Output schema (fixed keys):** `{"experiment_id": "EXP-TBILL",
    "state": "ABOVE_TBILL"|"BELOW_TBILL"|"DATA_BLOCKED", "data_blocked",
    "reason", "asof", "max_asof", "credit_mid": float|None,
    "collateral": float|None, "credit_annualized_yield": float|None,
    "tbill_annualized_yield": float|None, "carry_spread": float|None,
    "opportunity_cost": float|None, "rate_provenance": str|None,
    "assignment": {"state": "DATA_BLOCKED",
    "reason": "EX_DIV_DATE_UNAVAILABLE", "unlock": "owner-sourced forward
    ex-dividend date calendar"}, "caveat": str}`.
16. **Formula:** **Invalid-quote guard first (same rule as brief 03):**
    `bid <= 0`, crossed quotes (`ask < bid`), or `mid <= 0` on the
    reference put → DATA_BLOCKED with reason "invalid reference quote" —
    a degenerate mid must never feed the yield math. Then
    `credit_mid = (bid+ask)/2` (mid; the display copy notes
    real fills are mid-or-worse per repo cost rules); `collateral =
    strike*100`; `tau` = calendar days asof→expiration;
    `r = risk_free_rate(asof, expiration)` (continuous, interpolated);
    `opportunity_cost = collateral*(e^(r*tau/365) - 1)` (the OCC-official
    carry the cash would earn); `credit_annualized_yield =
    (credit_mid*100/collateral)*(365/tau)`; `tbill_annualized_yield =
    e^(r) - 1` expressed annualized from the same curve;
    `carry_spread = credit_annualized_yield − tbill_annualized_yield`;
    state by sign of `carry_spread`. No invented threshold anywhere.
17. **Causal timing:** `risk_free_rate` is already point-in-time gated by
    `known_as_of_utc`/`valid_through` inside `data/rates.py`; the chain
    row comes from the `<= asof` cached session. Nothing else is read.
    Two mechanical gotchas (audit B2/B4): every chain read MUST pass
    `allow_oos=True` (`composite_signals.py:682` precedent —
    `IN_SAMPLE_END=2022-12-31` makes the default raise
    `OOSDataTouchError` at 2026 sessions); and `risk_free_rate` performs
    an exact `type(x) is date` check, so ISO strings MUST be converted
    with `date.fromisoformat()` before every loader call.
18. **As-of rules:** `max_asof = min(chain session used, last rates
    observation date resolvable at asof)`; currently 2026-07-27. Stamp
    displayed; never borrows the closes-lane date.
19. **Missing data:** `MissingRateError` → DATA_BLOCKED with the
    loader's own message ("no Treasury curve known by valuation close");
    no valid reference put (absent, or failing the §16 invalid-quote
    guard) → DATA_BLOCKED.
20. **Stale data:** rates rows expire via `valid_through`; at asof past
    validity the loaders refuse and the card shows the refusal — this is
    the owner's cue to refresh the CSVs (owner action; never auto-fetch).
21. **Failure behavior:** blocked card on exception; never partial;
    the assignment sub-dict is ALWAYS the stub — there is no code path
    that emits an assignment verdict.
22. **Configuration:** near-tenor band `(15, 60)` DTE + 0.50Δ put
    (composite convention), via getattr defaults
    `EXP_TBILL_TENOR_DTE=(15,60)`, `EXP_TBILL_TARGET_DELTA=0.50`.
    Provenance comments as in the design spec. No thresholds exist.
23. **Owner-controlled values:** none now. Future: the ex-div calendar
    (owner-sourced data), rates CSV refresh (owner action), any
    promotion (feasibility gate).
24. **Security/provider:** offline; CSVs + cached chain only.
25. **Dashboard behavior (Stage B):** two-clause line, e.g. "Parking
    $18,400 in T-bills earns ~4.9%/yr; this put's credit adds ~2.1%/yr
    on top for taking assignment risk (mid quotes; real fills are mid or
    worse). Early-assignment risk: unknown — no ex-dividend-date data on
    disk yet." Rate provenance (treasury.gov capture) shown in the
    tooltip/details.
26. **Named tests:** `test_key_contract`,
    `test_occ_opportunity_cost_hand_computed` (fixture curve, hand
    value), `test_carry_spread_sign_states`,
    `test_missing_rate_blocked_via_loader`,
    `test_assignment_stub_always_blocked_red` (see §28),
    `test_no_reference_put_blocked`,
    `test_invalid_reference_quotes_blocked` (bid=0, crossed, mid<=0 →
    DATA_BLOCKED; mirrors brief 03's invalid-quote rule),
    `test_spot_session_matches_chain_session` (spot date == the chain
    session used, never the module asof),
    `test_mid_quote_used_not_bid_or_ask`,
    `test_no_lookahead_rates_gate` (asof after valid_through → blocked),
    `test_board_blocked_card`.
27. **Baseline tests:** untouched; full suite stays green.
28. **Red test first:** `test_assignment_stub_always_blocked_red` —
    property-style: for arbitrary inputs (including ones that look like a
    dividend capture setup) the flag returns the EX_DIV_DATE_UNAVAILABLE
    stub and NEVER a computed verdict. Fail first (module absent), then
    implement.
29. **Targeted verification:** `uv run python -m unittest tests.test_exp_tbill_carry`.
30. **Full verification:** full discovery, ruff on the two files,
    pyright, `git diff --check`.
31. **Acceptance criteria:** named tests green; hand-computed OCC fixture
    matches to 1e-6; on the real cache at asof=2026-07-27 the comparison
    renders for every board name whose reference put passes the
    invalid-quote guard, AND the cache-conditional test asserts loudly
    that at least one name is NOT DATA_BLOCKED (an all-blocked board —
    the signature of a missing `allow_oos=True` — must FAIL the test);
    stub red test green.
32. **Performance limits:** one chain session read + one CSV parse per
    board build; < 5s total; no persisted artifacts.
33. **Rollback:** delete the two files.
34. **Commit boundary:** one commit,
    `feat(exp): EXP-TBILL carry-vs-tbill display experiment (module + tests)`,
    branch `codex/attractive-exp-tbill-carry`.
35. **Stop conditions:** `data/rates.py` API signature drift (report,
    don't adapt); rates CSVs absent; any temptation to approximate an
    ex-div date (stop — it's prohibited); any network need.
36. **Unsupported assumptions:** none knowingly; the continuous-rate
    annualization convention is stated in the module docstring and
    display details.
37. **Remaining risks:** rates staleness beyond valid_through renders
    the lane blocked until the owner refreshes (honest but reduces
    visible coverage); mid-quote credit is optimistic by construction
    (disclosed in copy per repo cost discipline).
38. **Fable review checklist:** master checklist + verify the stub has
    no computed branch, the loaders' exceptions are surfaced verbatim,
    and the mid-or-worse disclosure appears in the copy.
