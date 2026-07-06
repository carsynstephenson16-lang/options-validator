# H1 pre-registration: scope, threshold, and sequencing (2026-07-03)

**Status:** FROZEN before any in-sample backtest has ever run (ledger: 0 records,
trial_count 0 at writing). This document is the pre-registration commitment for
hypothesis H1. Everything here was decided a priori — no PnL, scoreboard, or
per-symbol result from the cached 2018–2022 window had been computed when this
was committed (the only result values ever surfaced remain the two disclosed
engineering peeks in ledger/facts.log: SPIKE_OFFLINE_BACKTEST and HARNESS_SMOKE).

Decision authority: owner delegated the H1 scope decision (2026-07-03 session
brief); default recommendation from project memory adopted after independent
re-derivation below.

---

## 1. The decision

| Item | Frozen value |
|---|---|
| hypothesis_id | `H1-pcs-spy-qqq-2wide-30delta-eod-v1` |
| Registered scope | **SPY + QQQ only** (pooled scoreboard) |
| Strategy | Defined-risk put credit spread per committed config: sell ~0.30-delta put, buy $2 lower, 30–45 DTE band (nearest), 50% profit target, 2× credit stop, forced close at 7 DTE, EOD decision cadence, one spread per underlying |
| Width | **$2** (`A_SPREAD_WIDTH = 2`) — the candidate declared 2026-07-02 on cost-structure grounds, before any backtest |
| is_window | 2018-01-01 .. 2022-12-31 |
| oos_window | 2023-01-01 .. 2026-06-30 |
| risk_basis | `economic_max_loss` (sizing gates on margin + round-trip commissions; $600 hard cap per trade) |
| decision_threshold | See §3 verbatim string |
| Unregistered diagnostics | MSFT, AAPL, NVDA, VST, PLTR, AMZN, NOW — run individually in-sample, never pooled into any verdict (§6) |

The seven single names are excluded from the registered hypothesis and serve
only as post-registration robustness diagnostics.

## 2. Why SPY/QQQ (a priori case)

1. **Hindsight contamination of the 9-name universe.** The single names were
   chosen in 2026 with full knowledge of the 2023–2026 AI/growth boom — and the
   OOS window (2023-01 .. 2026-06) IS that boom. A 9-name OOS PASS would be
   uninterpretable: strategy edge and name-selection bias cannot be separated,
   because short-put PnL on names selected for having gone up is inflated by
   construction. SPY/QQQ are the default index underlyings any VRP study would
   have picked in 2017 — defensible without hindsight.
2. **Dependence, not diversification.** config.py itself flags the universe as
   ~one growth/AI cluster (~1.5 independent bets). Adding 7 correlated names
   multiplies trade count ~4–5× but adds few independent entry-week cohorts,
   so under the dependence-aware CI the power gain is small while the pooled
   point estimate gets dragged by the cluster — increasing false-PASS risk
   through exactly the undercoverage channel the 2026-07-02 power study
   measured.
3. **Capital realism.** Nine concurrent $600-cap positions ≈ $5,400 ≈ 38.6% of
   the $14k sleeve at simultaneous risk in one correlated cluster; two index
   positions ≈ $1,200 ≈ 8.6%. The registered hypothesis should be tradeable as
   registered.
4. **Mechanism match.** The volatility-risk-premium mechanism is documented on
   index options. Single-name short puts carry idiosyncratic earnings/gap risk
   — a genuinely different hypothesis that deserves its own registration if
   ever pursued.

**Why not SPY only:** QQQ is a priori defensible (broad, liquid, higher-IV
index), roughly doubles the loss sample feeding `MIN_LOSSES_FOR_VERDICT = 10`,
and probes a second index regime. The weekly-cohort bootstrap absorbs SPY–QQQ
same-week correlation by design.

**Sizing note (per-symbol, not per-cluster):** the $600 cap applies per trade;
with 2 registered names the worst simultaneous registered exposure is ~$1,200.

## 3. Decision threshold (verbatim, frozen)

> H1 passes only if the write-once OOS reveal's metrics.scoreboard verdict is
> PASS: the dependence-aware 90% CI (weekly entry-cohort block bootstrap +
> stationary cross-check over the frozen block-length envelope, widest bounds)
> lower bound on expectancy per trade is > $0 after all modeled costs, with
> >= 10 losses and >= 3 entry-week cohorts in the OOS trades. FAIL iff the CI
> upper bound < $0. Otherwise the scoreboard's NO EDGE / INSUFFICIENT SAMPLE
> verdict stands as reported. One reveal, no re-runs, no parameter changes;
> the in-sample result is evidence for proceeding, never the verdict.

**No-discretion clause:** the first in-sample run's scoreboard is registered as
H1's is_result *whatever it shows* (PASS / FAIL / NO EDGE / INSUFFICIENT
SAMPLE). Declining to register after seeing the result would itself be a
selection event and is ruled out here, in advance.

## 4. Sequencing correction (source-freeze trap)

`research.experiments.reveal_oos()` refuses when `source_hash` drifts from the
registered value, and the hash surface covers `config.py`, `metrics.py`,
`analysis/`, `data/`, `harness/`, `research/`, `strategies/`, `pyproject.toml`,
`uv.lock`. Therefore **all code the reveal path needs must be final before H1
registers** — implementing charge-on-touch OOS logging after registration would
permanently brick H1's reveal (or force a throwaway H2 re-registration).

Revised order (supersedes the default ladder's 2→4 ordering):

1. Commit this decision doc.
2. Implement charge-on-touch OOS logging + reveal wiring, TDD (§5). Full suite
   green. Commit.
3. Run the first in-sample backtest (SPY/QQQ, $2, 2018-01-01..2022-12-31).
   Report the scoreboard honestly.
4. Register H1 on a clean tree; commit ledger files.
5. In-sample width sweep (§6). If it overturns $2, register the successor
   hypothesis at the chosen width (new hypothesis; H1 stays on the ledger,
   never revealed).
6. Single-name diagnostics (§6).
7. Prepare the reveal end-to-end; stop at the owner's door.

After step 4, the source surface is code-frozen for H1: any edit under the
hashed paths un-reveals H1 until the exact registered bytes are restored.

## 5. Charge-on-touch OOS logging (spec for the TDD step)

Policy (decided 2026-07-03, recorded in project memory): gate failures before
the backtest are free; once the holdout data is about to be touched, an
auditable, budget-consuming event is written *first*.

- New ledger entry_type **`oos_attempt`**, appended by `reveal_oos()` after all
  gates pass (including the anchored/clean check) and **before `run_fn()`
  executes**. Fields: timestamp, hypothesis_id, run_id, budget_used,
  budget_total.
- **Budget counts touched hypotheses, not successful reveals:** the budget
  check refuses a hypothesis not already touched when the count of distinct
  touched hypotheses (union of oos_attempt + oos_reveal hypothesis_ids) has
  reached `OOS_LOOK_BUDGET`. A crashed attempt burns the slot for that
  hypothesis (the data was touched); re-attempting the *same* hypothesis after
  an infrastructure failure does not burn a second slot (it completes the same
  look). Write-once on successful reveal is unchanged.
- Semantic verifier: oos_attempt must reference a registered run (matching
  run_id); an oos_reveal requires a prior oos_attempt for the same hypothesis;
  budget_used on any OOS record = distinct touched hypotheses up to and
  including it; budget_total constant and >= budget_used.
- **Run records gain a required `scope` field** `{"symbols": [...]}` (ledger is
  empty; no migration). `register()` requires it; the verifier validates it
  (non-empty list of non-empty upper-case strings).
- `_oos_backtest_trades(record)` unseals: reads the registered record's scope
  symbols + oos_window and calls
  `run(PutCreditSpread, start=oos_window.start, end=oos_window.end,
  symbols=scope, allow_oos=True)`.
  `reveal_out_of_sample(hypothesis_id)` builds that closure from the ledger.
- **Rehearsal requirement:** the test suite must exercise the full reveal path
  (attempt record → injected run_fn → reveal record, budget accounting,
  crash-between-attempt-and-reveal) against a temporary ledger and fake
  holdout trades. A real reveal is refused mechanics-wise until these tests
  exist and pass. (Memory's "mandatory dry-run rehearsal" — implemented as
  pinned tests, rerun on the reveal day.)
- Known limit (Phase 1A threat model, unchanged): the attempt record lands
  uncommitted on disk; an adversarial writer could `git checkout` it away
  before committing. Honest-single-writer is the documented boundary; hook
  enforcement is a later phase. The reveal SOP says: commit ledger immediately
  after the reveal returns.

## 6. Pre-declared follow-up protocols (frozen before any results)

**Width sweep (in-sample only, judged before any OOS look):**
- Arms: $1 and $5 (the $2 arm is H1's registered in-sample run itself — it is
  not rerun). Same scope (SPY/QQQ), same is_window, same everything but width.
- Mechanics: edit `A_SPREAD_WIDTH` in config.py, commit, run, record; restore
  `A_SPREAD_WIDTH = 2`, commit. Each arm is logged to the ledger as a
  `trial_intent` whose reason embeds the arm's scoreboard summary (expectancy,
  CI90, n_trades, n_losses, verdict); full scoreboards go in the width-decision
  doc. Arms are never registered as reveal-eligible runs.
- **Selection rule (frozen now):** carry forward the width with the highest
  in-sample CI90 *lower bound*. A challenger must (a) strictly exceed the $2
  candidate's CI90 lower bound, and (b) itself have >= 10 in-sample losses;
  otherwise $2 stands. Ties or insufficient samples resolve to $2. If a
  challenger wins, register it as a new hypothesis (e.g.
  `H2-pcs-spy-qqq-<w>wide-...`); H1 remains on the ledger, never revealed —
  the trial counter records everything.

**Single-name diagnostics (unregistered, non-verdict-feeding):**
- Per-symbol in-sample runs of the same strategy on each of the 7 names,
  reported as descriptive facts (per-symbol scoreboards in a diagnostics doc;
  summary lines in facts.log). No pooling into any verdict, no scope changes to
  any registered hypothesis based on them, no width/parameter tuning from them.
  Purpose: characterize concentration/robustness ("learn facts, not
  parameters").

## 7. Registration payload (to be executed at step 4)

```python
research.experiments.register(
    "H1-pcs-spy-qqq-2wide-30delta-eod-v1",
    decision_threshold=<§3 string>,
    is_result=<scoreboard of the §4-step-3 run>,
    data_window={"is_window": {"start": "2018-01-01", "end": "2022-12-31"},
                 "oos_window": {"start": "2023-01-01", "end": "2026-06-30"}},
    scope={"symbols": ["SPY", "QQQ"]},
    risk_basis="economic_max_loss",
    notes=<caveats: this doc's path; 46-day entry blackouts (below);
           power-study undercoverage caveat; EOD-managed only>,
)
```

**Caveats frozen into the registration notes:**
- **Entry blackouts:** the final `MAX_HOLD_DAYS = 46` days of each window admit
  no entries (holdout protection): in-sample entries stop 2022-11-15, OOS
  entries stop 2026-05-15. Positions always exit inside their own window.
- **CI size caveat:** the 2026-07-02 synthetic power/size study measured the
  verdict path at ~5.8% false-PASS at $0 true edge (after the blind OOS
  extension) and modest power at plausible edges ($10/trade ≈ 38% OOS PASS) —
  a PASS is evidence, not proof; NO EDGE at small true edges is the modal
  outcome and a fully successful result.
- **EOD-managed only:** the harness validates EOD management; intraday
  management would be new data and a new hypothesis.
- **Insufficient-sample branch:** if the registered IS result is INSUFFICIENT
  SAMPLE, H1 stays registered as-is (honest record); any wider-scope successor
  is a new hypothesis and must not be scope-shopped against results.

## 8. What was NOT decided from data

No in-sample aggregate has ever been computed when this doc was committed. The
inputs to this decision were: config.py's committed concentration flag, the
2026-07-02 synthetic power/size study (no market data), cache completeness
facts, capital facts from the owner, and the VRP literature's index-option
focus. The two engineering peeks (one spike trade's PnL; a 3-trade smoke count)
are disclosed in facts.log and did not inform scope.
