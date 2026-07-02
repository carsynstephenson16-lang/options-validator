# Pre-registration design decisions (2026-07-02)

**Status:** ALL decisions made and applied; no owner blockers remain (see
Addendum -- the sleeve blocker in section 6 was resolved by the owner the
same day, and section 5 was decided as option (a)).
**Context:** the scanner-vs-validator scope review (2026-07-02) concluded:
continue validation, no scanner. This doc records the $0 pre-subscription
decisions that must be clean BEFORE the first ThetaData dollar and BEFORE the
first hypothesis registers. Everything here was decided BLIND: no paid data,
no post-`IN_SAMPLE_END` market data fetched or opened.

## 0. New instrument-level evidence: analysis/power_check.py

A synthetic power/size study of the FROZEN verdict path (real
`metrics._build_week_cohorts` + `_ci_from_cohorts`, widest envelope, PASS iff
CI90 lower bound > 0; verdict gates replicated and test-pinned against
`scoreboard()`). It measures the instrument, not the strategy. Dependence is
calibrated and measured at ~1.5 effective bets across the 5 names, matching
config's concentration flag. Reproduce with `python analysis/power_check.py`
(explicit seeds; `--quick` for a smoke run).

Full-run results (2026-07-02, verbatim from `python analysis/power_check.py`):

```
measured fully-overlapping PnL correlation 0.607 -> ~1.46 effective bets across 5 names (config flags ~1.5)
PASS rule: widest-envelope 90% CI lower bound > 0 (metrics.py, frozen)

-- SIZE (false-PASS rate): true edge $0.00/trade, reps=120, n_boot=2000 --
IS 2018-2022           edge=$  0.00 | trades~ 297 losses~ 74 | PASS 11/120 =  9.2% [Wilson95  5.2%..15.7%]  NO-EDGE 86.7%  FAIL  4.2%  INSUFF 0.0% | med CI width $ 20.06
OOS 2023..2024-12-31   edge=$  0.00 | trades~ 119 losses~ 28 | PASS 13/120 = 10.8% [Wilson95  6.4%..17.7%]  NO-EDGE 84.2%  FAIL  5.0%  INSUFF 0.0% | med CI width $ 28.74
OOS 2023..2026-06-30   edge=$  0.00 | trades~ 207 losses~ 54 | PASS 7/120 =  5.8% [Wilson95  2.9%..11.6%]  NO-EDGE 87.5%  FAIL  6.7%  INSUFF 0.0% | med CI width $ 23.74

-- POWER: true edge $4.00/trade, reps=50, n_boot=1000 --
IS 2018-2022           edge=$  4.00 | PASS  5/50 = 10.0% [ 4.3%..21.4%]
OOS 2023..2024-12-31   edge=$  4.00 | PASS 10/50 = 20.0% [11.2%..33.0%]
OOS 2023..2026-06-30   edge=$  4.00 | PASS  7/50 = 14.0% [ 7.0%..26.2%]

-- POWER: true edge $10.00/trade, reps=50, n_boot=1000 --
IS 2018-2022           edge=$ 10.00 | PASS 25/50 = 50.0% [36.6%..63.4%]
OOS 2023..2024-12-31   edge=$ 10.00 | PASS 14/50 = 28.0% [17.5%..41.7%]
OOS 2023..2026-06-30   edge=$ 10.00 | PASS 19/50 = 38.0% [25.9%..51.8%]

-- POWER: true edge $20.00/trade, reps=50, n_boot=1000 --
IS 2018-2022           edge=$ 20.00 | PASS 47/50 = 94.0% [83.8%..97.9%]
OOS 2023..2024-12-31   edge=$ 20.00 | PASS 33/50 = 66.0% [52.2%..77.6%]
OOS 2023..2026-06-30   edge=$ 20.00 | PASS 43/50 = 86.0% [73.8%..93.0%]
```

Findings:

- SIZE: at true edge $0 the 90% CI **undercovers** in the short windows
  (IS 9.2%, OOS-2yr 10.8% false-PASS vs nominal ~5%) -- but the EXTENDED
  OOS window restores near-nominal size (5.8% [2.9-11.6]).
- POWER: a plausible $4/trade edge is not discriminable anywhere (PASS
  10-20%, barely above the false-PASS base). $10/trade: 50% IS, 28% OOS-2yr,
  38% OOS-extended. $20/trade: 94% / 66% / 86%.
- Evidence value: at $10/trade, a PASS on the extended window has a
  likelihood ratio vs the null of ~6.6 (38%/5.8%), against ~2.6 on the
  2-year window (28%/10.8%) -- the extension improves BOTH error rates.
- Consequence: for any true edge <= ~$10/trade the MODAL verdict is an honest
  "NO EDGE", and a PASS at plausible edge sizes is weak evidence on its own.
  This is what the experiment, at ~1.5 effective bets, can honestly resolve.

## 1. Scope (owner-approved)

Validator only. No scanner, no suggestor, no ranking engine, no order path.
Unchanged from README/.cursorrules/AGENTS.md.

## 2. OOS window: extended, decided blind (APPLIED)

`BACKTEST_END` moved `2024-12-31 -> 2026-06-30` (config.py, dated comment).

- Why: the 2-year OOS window is the study's weakest cell (lowest power, size
  inflation at ~100 cohorts). Extending to 2026-06-30 adds ~75% more OOS weeks
  -- the only free lever that improves power AND coverage simultaneously.
  CONFIRMED by the full artifact run (section 0): the extension restores
  near-nominal size (10.8% -> 5.8% false-PASS) and raises $10-edge power
  (28% -> 38%), improving the PASS likelihood ratio from ~2.6 to ~6.6.
- Why it is legitimate: nothing is registered yet; the window choice is a
  pre-registration design input. It was made from synthetic evidence only.
  Registration freezes it via `data_window_hash`; changing it afterwards
  starts a new hypothesis and spends budget accordingly.
- Honest caveat: the owner has lived through 2023-2026 markets. The harness
  guards DATA looks, not memories; that residual bias exists for any recent
  holdout and is smaller than the alternative (no usable OOS power at all).

## 3. Width sweep: in-sample only (APPLIED)

`A_SPREAD_WIDTH_SWEEP = [1, 2, 5]` is three hypotheses; `OOS_LOOK_BUDGET = 3`
is a LIFETIME cap. Phase 3 as previously written could exhaust the entire OOS
budget on width variants of one idea. Decision (config comment + README Phase
3 line): the sweep is judged in-sample only; exactly ONE pre-registered width
may ever reveal OOS.

## 4. OOS data plan: blind-cache during the paid month (DECIDED, spec-first)

Problem: the paid month caches 2018-2022 in-sample, but the eventual OOS
reveal needs 2023+ chains, and the adapter correctly refuses
post-`IN_SAMPLE_END` fetches (`OOSDataTouchError`). A second paid month at
reveal time would work but doubles the data cost.

Decision: implement a **blind-cache** mode before subscribing, test-first:

- Fetch-to-parquet for post-`IN_SAMPLE_END` dates WITHOUT surfacing values:
  the code path may report row counts and file hashes only -- never prices,
  greeks, or any aggregate of them.
- Every blind-cache invocation writes a `facts` ledger event (symbol, date
  range, row count, file hash) so the cache is auditable and cannot become a
  stealth look.
- READING those parquet files stays gated by the OOS reveal path
  (`allow_oos=True` via `reveal_oos()` only). Charge-on-touch is unchanged:
  the budgeted look happens at reveal, not at caching.
- IMPLEMENTED (2026-07-02): `data/thetadata_adapter.blind_cache_chain` +
  `tests/test_blind_cache.py` -- refuses in-sample dates; returns only
  `BLIND_CACHE_METADATA_KEYS` (symbol, date, rows, schema names, sha256,
  path, already_cached); appends a `BLIND_CACHE` facts event per invocation;
  an already-cached file is audited from parquet FILE METADATA only (value
  pages never materialized); tests pin that `get_eod_chain` still refuses
  the blind-cached date without the reveal gate and that the reveal seam
  reads the cache without a network touch.

## 5. Verdict CI size inflation: acknowledged, decision owner-facing

The measured ~10% false-PASS (vs nominal ~5%) is a property of the frozen CI
under realistic dependence at these sample sizes. Options, to be settled
BEFORE registration (they are verdict-affecting):

- (a) Keep CI90 and REPORT the measured operating characteristics in the
  registered record, so any future PASS is read against a ~10% false-PASS
  base rate. RECOMMENDED: it changes no frozen machinery and keeps the
  already-low power; honesty lives in the registered interpretation.
- (b) Widen the interval (e.g., 2.5/97.5 percentiles) to restore ~5% size at
  a further cost to power. Legitimate but likely leaves the experiment unable
  to certify anything plausible.

## 6. OPEN BLOCKER (owner input required): risk sleeve

`config.RISK_SLEEVE = 14_000` (2026-07-01 decision comment: cash + active
swing capital, portfolio and margin deliberately excluded) vs project memory
flagging ~$7k liquid. These may be consistent (cash + swing) or the sleeve
may have drifted. The zero-slack feasibility math ($140 budget vs $140 gross
max loss at $2-wide) flips if the sleeve halves. **No hypothesis registers
until the owner states the number.** Question for the owner: "What is the
dollar amount you are genuinely willing to lose in this options book today --
is $14,000 (cash + swing) still true, or is ~$7,000 the honest figure?"

## Sequencing after the blocker clears

1. Owner confirms sleeve -> update `RISK_SLEEVE` if needed (+ re-run
   `analysis/feasibility.py`).
2. Owner picks 5(a) or 5(b).
3. Implement + test the blind-cache mode (section 4).
4. Resolve ThetaData auth Path A/B -> subscribe Options Standard ->
   smoke test `2022-12-30` -> cache in-sample AND blind-cache OOS ->
   first pre-registered backtest through the integrity substrate.

---

## ADDENDUM (later 2026-07-02): risk-cap decision + blocker resolutions

**Owner inputs (settled):** the sleeve is truly $14,000, and per-trade max
loss is capped at $600 (initially stated as $500 earlier the same day; the
owner raised it to $600 before this checkpoint was committed). The old
"1% of sleeve" rule is retired.

### A1. Risk representation (decided): explicit dollar cap

`MAX_LOSS_PER_TRADE = 600` is the PRIMARY risk knob (config.py), consumed by
`strategies/base.risk_budget()` -- the single sizing seam. `RISK_PER_TRADE`
and `RISK_SLEEVE_CANDIDATES` are retired (the candidates sweep existed to
display the 1%-rule trade-off). Rationale: the owner's decision IS a dollar
figure; a derived fraction (0.0357...) would hide it behind a magic number.

Material consequence, stated plainly: under the 1% rule the harness could not
trade AT ALL at assumed credits -- the $140 budget sat below the $2-wide
$142.60 ECONOMIC max loss and `size_defined_risk` correctly returned 0
contracts. The $600 cap makes every sweep width feasible ($1-wide: 8
contracts, $2-wide: 4, $5-wide: 1). Feasibility no longer forces the width;
the IN-SAMPLE sweep decides it. Feasibility != validation: costs, fills,
liquidity, and the verdict machinery are untouched.

### A2. Portfolio concentration (documented, test-pinned)

The cap is PER TRADE. Five concurrent positions x $600 = $3,000 =~ 21.4% of
the sleeve at simultaneous risk in a ~1.5-effective-bet universe -- in a tech
drawdown these lose together. `analysis/feasibility.py` prints this view;
`tests/test_core.py::HonestRiskCapConfigTests` pins the numbers.

### A3. Power/size study is sizing-invariant (no re-run needed)

Contract count multiplies a trade's edge AND its dispersion by the same
factor, so the CI-on-mean verdict and the study's PASS rates are unchanged;
only dollar labels scale (a "$4/trade" edge per 1-contract-W is $16/trade at
4 contracts; edge as a FRACTION of deployed risk is what the study varies).
The section-0 results stand as recorded.

### A4. Section 5 decided: option (a)

Keep CI90 unchanged; the registered record MUST cite the measured operating
characteristics (false-PASS ~5.8% on the extended OOS window, ~9-11% on the
short windows; power table in section 0) so any future PASS is read against
its real base rate. Rationale: (b) widening percentiles would spend the
already-scarce power to buy size the extended window has largely restored.

### A5. Scanner: remains deferred (re-affirmed)

The $600 cap changes feasibility, not evidence: still zero backtests, still
no validated edge model for any ranking to stand on. Validator-first
continues; the scanner stays a post-validation project per README.

### A6. Gate coherence under the cap (checked)

Verdict gates (MIN_LOSSES, cohorts, dependence-aware CI) are per-trade and
scale-invariant; OOS look budget, width-sweep-in-sample-only, and the
blind-cache plan are orthogonal to sizing. All remain as decided above.

**Next step:** implement the blind-cache mode test-first (section 4), then
resolve auth Path A/B. The subscription itself stays a pause point (money).
