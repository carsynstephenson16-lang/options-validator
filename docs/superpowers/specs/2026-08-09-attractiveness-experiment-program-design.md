# Attractiveness experiment program — design (2026-08-09)

Authorization: `.cursorrules` / `AGENTS.md` 2026-08-09 owner-directed
paragraph; record `reports/2026-08-09-attractiveness-experiment-authorization.md`.
Selection evidence: `reports/2026-08-09-parking-lot-471-selection-report.md`.
Status: SPECIFICATION ONLY — no experiment code exists yet; implementation
is Codex-only from the briefs in `docs/superpowers/plans/2026-08-09-*`.

## 1. Current architecture (what exists, verified)

- Baseline ranking: frozen GREEN-fraction recipe (RQ1) rendered by
  `options_researcher/attractiveness.py` +
  `attractiveness_dashboard.py` (3,051 lines; `render()` documents the
  page order; `assemble()` takes optional per-section inputs, e.g.
  `composite_signals=None`).
- Reference display-only lane: `options_researcher/composite_signals.py`
  — per-symbol angle functions returning fixed-key dicts
  (`state`, `data_blocked`, `reason`, payload), caller-truncates-to-asof
  causality, per-card `max_asof`, `DATA_BLOCKED` fail-visible states,
  frozen `COMPOSITE_*` constants with LLM-proposed provenance, its own
  test file including a no-look-ahead invariance test, and one dashboard
  section renderer. This program replicates that pattern; it does NOT use
  `options_researcher/robustness/` (reserved for registered verdict-bearing
  studies).
- Data surfaces: `.cache/chains` (EOD, frozen at 2026-07-27; per-contract
  bid/ask/OI/iv/delta/gamma/theta/vega), `.cache/underlying` closes via
  `data/underlying_closes.load_closes_adjusted` (through 2026-08-04; QQQ +
  SPY present), `data/rates.py` (`risk_free_rate`, `dividend_yield`,
  fail-closed, point-in-time-gated), `data/earnings/gating_v3.csv` (all 15
  board names, provenance-bearing), `.tmp/composite_cache/<SYM>.parquet`
  (derived ATM-IV history — read-only for this program; nobody writes to
  it except composite_signals).

## 2. Selected experiment lanes

| ID | module (new) | axis | data | max as-of source |
|---|---|---|---|---|
| EXP-BETA | `options_researcher/exp_beta_qqq.py` | factor exposure vs QQQ | closes | min(name, QQQ) closes — QQQ currently ends 2026-08-03, one session behind the names, so that caps the stamp |
| EXP-TAIL | `options_researcher/exp_tail_shape.py` | realized tail shape | closes | closes |
| EXP-SPREAD | `options_researcher/exp_spread_stability.py` | execution-cost dynamics | chains | chain edge (2026-07-27) |
| EXP-TBILL | `options_researcher/exp_tbill_carry.py` | carry + assignment mechanics | chains + `data/rates` | min(chain edge, rates validity) |

Each experiment: one module, one `EXP_<NAME>_*` config block, one test
file, one dashboard renderer + one `assemble()` keyword. No new
dependencies. No experiment imports another experiment.

## 3. Common contracts

1. **Pure-function angle:** `exp_<name>(...) -> dict` with the fixed key
   set `{"experiment_id", "state", "data_blocked", "reason", "asof",
   "max_asof", ...payload}`. Inputs are pre-truncated by the caller to
   `<= asof` (composite precedent); the function never reads the clock,
   the network, positions/ledger state, or any file outside its declared
   inputs. (EXP-BETA's originally-sketched position dollar-translation
   was cut in adversarial review — no experiment reads positions in v1.)
2. **Fail-visible:** every missing/thin/stale input maps to
   `state="DATA_BLOCKED"` with a machine reason constant AND a
   plain-language operator sentence. Never a silent substitute, never a
   neutral-looking default.
3. **Constants:** all in `config.py` as `EXP_<NAME>_<CONST>` with a
   comment carrying provenance ("LLM-proposed 2026-08-09,
   standard-from-literature / repo convention; display-only; not
   owner-ratified"). No per-name tuning. Reused repo conventions:
   window 252 / min-obs 126 mirror `COMPOSITE_PCTL_WINDOW/MIN_OBS`.
4. **Off by default — with an explicit no-auto-compute rule:**
   `EXPERIMENT_LANES_ENABLED: dict[str, bool]` in `config.py`, all four
   `False`. The dashboard CLI gains `--experiments` (enables all built
   lanes for that render only, no config change). `assemble()` receives
   experiment payloads as optional keyword args defaulting to `None` —
   **and, unlike the `composite_signals` keyword it otherwise mirrors,
   an experiment keyword left as `None` NEVER self-computes** (audit
   finding B1: `assemble()`'s composite branch auto-builds on `None`
   during real assembly with no flag gate; copying that literally would
   silently enable experiments in every production rebuild, e.g. the
   `daily_ritual.sh`/`research_refresh.sh` no-arg invocations). Only the
   CLI path constructs experiment payloads, and only when
   `--experiments` is passed or a lane's config flag is `True`.
5. **Baseline isolation:** with every flag off and no CLI flag, the
   rendered HTML must be byte-identical to pre-program output. This is a
   named test (see §7). Experiments never touch `attractiveness.py`
   ranking/grading functions, `top3_snapshot`, any `h5/h6/h7/h8/h10`
   module, any ledger, or the paper book.

## 4. Data flow

closes/chains/rates/gating_v3 → (caller truncates to asof) → experiment
module pure function → dict → `assemble(..., exp_beta=..., exp_tail=...,
exp_spread=..., exp_tbill=...)` → `render()` "Experiments — display-only"
section → static HTML. No experiment persists derived caches in v1
(recompute-per-render is cheap for all four; EXP-SPREAD reads a bounded
~25-chain-day window, not full history).

## 5. Dashboard design (contract)

One new top-level section, rendered only when at least one experiment
payload is present: **"Experiments — display-only (not part of Top-3
ranking)"**, containing:

1. A health strip: per experiment — name/ID, enabled state, data source,
   its own max as-of, coverage (n names rendered / n attempted), and
   failure reason when blocked. This is the required
   data-and-experiment-health + comparison view (all four lanes side by
   side; the baseline hero above is untouched and remains the comparison
   anchor).
2. Per-experiment blocks with one plain-language line per symbol,
   each carrying: the number(s), its own as-of stamp, the honesty caveat
   (what the line does NOT prove), and refusals rendered in words
   ("we don't have dividend-date data yet"), never bare enums.
3. A limitations footer naming: display-only; descriptive not
   predictive; chain lane frozen 2026-07-27 vs closes 2026-08-04;
   constants LLM-proposed and not owner-ratified; promotion gates.

Rules kept from the repo: never merged into Top-3 admission/ordering;
missing data never rendered as neutral; closes-based and chain-based
stamps never share one date; the intrinsic-only scenario ladder stays
model-free (no experiment renders inside it).

## 6. Experiment definitions (frozen at spec time)

### EXP-BETA (rolling beta to QQQ)
- Formula: on aligned daily log returns over trailing
  `EXP_BETA_WINDOW=252` sessions ending at asof: `beta = Cov(r_i,
  r_QQQ)/Var(r_QQQ)`; report `r_squared`; floor
  `EXP_BETA_MIN_OBS=126` paired observations else DATA_BLOCKED.
- Dollar-translation line: CUT from v1 (audit F4 — no frozen notional
  convention exists for the options position schema); beta + R² only.
- Displayed caveat (mandatory): betas drift toward 1 in selloffs; a
  calm-period beta understates crash co-movement.
- Diagnostics displayed: window beta vs `126`-session beta; if the two
  disagree in sign or by >0.5, add "unstable estimate" wording.
- Null usefulness: an unstable/low-R² result is itself the finding
  (idiosyncratic name) and is displayed as such.

### EXP-TAIL (realized tail shape)
- On trailing `EXP_TAIL_WINDOW=252` daily log returns ending at asof:
  sample skewness, excess kurtosis, and
  `jump_count = #{t in window: |r_t| > 3 * sigma_{t-1}}` where
  `sigma_{t-1}` is the trailing 252d std computed on data strictly
  before t (causal; fixes the self-referential-sigma defect found in
  review). NaN-gate: `EXP_TAIL_MIN_OBS=250`.
- Stability diagnostic: recompute at windows {189, 252, 378}; if the
  qualitative read (skew sign, kurtosis>1 flag) flips across windows,
  display "UNSTABLE across window choices" instead of a confident read.
- Copy pattern: "N moves bigger than 3× normal in the past year; recent
  surprises leaned down/up; history, not a forecast."

### EXP-SPREAD (spread stability)
- Contract series is ROLE-BASED: each session's near-tenor put row via
  `chains.nearest_monthly` (15–60 DTE expiration pick) then
  `chains.atm_row` (0.50Δ row within it) — composite precedent; never a
  fixed (strike, expiration) identity across rolls. All chain-history
  reads at the frozen edge pass `allow_oos=True`
  (`composite_signals.py:682` precedent; without it the
  `IN_SAMPLE_END=2022-12-31` holdout guard raises for every session).
- `ratio = rel_spread_today / median(rel_spread over the trailing
  EXP_SPREAD_BASELINE=20 sessions, strictly [t-20, t-1],
  excluding earnings-week sessions per gating_v3)`; `rel_spread =
  (ask-bid)/mid`. Today's own reading is never in its baseline. If today
  is an earnings week, the reading still renders, labeled as such.
- Floor: `EXP_SPREAD_MIN_BASELINE_OBS=10` valid baseline sessions else
  DATA_BLOCKED. Label `elevated` at `ratio >= EXP_SPREAD_ELEVATED=2.0`
  (LLM-proposed display label; the ratio itself is always printed).
- Earnings-data access is read-only `gating_v3.csv`; no H7 mutating API.

### EXP-TBILL (carry vs T-bill + assignment stub)
- For the CSP/CC reference contract at asof: annualized credit yield on
  collateral vs `data.rates.risk_free_rate(asof, expiration)`
  (opportunity cost `oc = K*100*(e^(r*tau/365)-1)`, OCC-official
  mechanics); states ABOVE_TBILL / BELOW_TBILL by sign — no invented
  threshold. `MissingRateError`/`MissingDividendYieldError` →
  DATA_BLOCKED with the loader's reason.
- Early-assignment flag: returns `state="DATA_BLOCKED",
  reason="EX_DIV_DATE_UNAVAILABLE"` unconditionally (no forward ex-div
  date calendar exists on disk). This is a documented permanent stub
  with a red test proving it never fabricates a date; it activates only
  after an owner-sourced calendar lands (owner data action).

## 7. Testing strategy

Per experiment (own `tests/test_exp_<name>.py`, offline, unittest):
key-contract test; synthetic-known-answer test (β of QQQ vs itself ≈ 1,
constructed skew/kurtosis, known-median ratio window, hand-computed OCC
oc); DATA_BLOCKED tests for every declared refusal; a no-look-ahead
invariance test (full-vs-truncated input equality — the composite
pattern); and the experiment's specific red test named in its brief.
Program-level: `tests/test_experiments_baseline.py` asserts (a)
`assemble()`/`render()` with no experiment payloads produce byte-identical
HTML to the pre-program call signature, (b) config flags default off,
(c) **the real production entry point stays clean**: mock `_gather_all`
(repo precedent: `tests/test_attractiveness_dashboard.py:1696`), call
`main()` with no arguments, and assert the Experiments section is ABSENT
— an injected-fixture `assemble()` test alone cannot catch an
auto-compute branch that only fires during real assembly (audit B1), and
(d) each `config.EXP_*` value equals its module's frozen default
(drift guard, audit B7).
Dashboard smoke tests live in each experiment's own test file (composite
precedent), NOT in `test_attractiveness_dashboard.py`.

## 8. Dependency graph and sequencing

- Stage A (parallel, zero shared files): four module+config-constants-
  in-brief+test tasks. Modules and test files are disjoint.
- Stage B (single sequential fan-in task): append the four config blocks
  + the flags dict, add the dashboard section renderer, wire
  `assemble()`/`render()` + CLI flag. `config.py` and
  `attractiveness_dashboard.py` are the two unavoidable shared files —
  they are touched ONLY in Stage B.
- Stage C: final verification + dashboard build + visual inspection.
No new registry/framework: the composite pattern replicated per
experiment is the smallest architecture that satisfies isolation
(engineering review, Wave 2; a typed harness was evaluated and declined).

## 9. Non-goals

No ranking/grading/ordering influence; no composite score across
experiments (isolated evaluation first; any combination is a future
ablation study); no RQ2 badge work (registered surface); no OI-v2, no
skew-steepness (owner-gated); no new dependencies; no provider calls; no
persisted experiment caches in v1; no typed-Card refactor (its 2026-08-08
trigger fires with this program — noted for the owner, deliberately not
performed here to keep diffs isolated and reviewable).

## 10. Rollback and promotion

Rollback per experiment: delete its module, test file, its `EXP_<NAME>_*`
config block AND its entry in `EXPERIMENT_LANES_ENABLED`, its
`assemble()` keyword + render call, and its row source in the
experiments health strip; the baseline test proves the remainder
unchanged. No persisted state exists to clean (v1).
Promotion of ANY experiment beyond display requires: a separate owner
decision; the 2026-07-24 registration feasibility gate where loss-gated;
owner-typed (or properly delegated) constants replacing the LLM-proposed
display conventions; and its own registered evaluation design. Until
then every rendered line stays labeled display-only.
**Selection-effect disclosure (binding on promotion):** these four lanes
were selected from 9 Wave-2-scored candidates out of a 48-idea inventory;
any future registration built on an experiment's numbers must disclose
that selection history in its multiple-testing accounting (K-counting),
alongside the RQ2-v1 K=2-vs-K=3 discrepancy (resolved 2026-08-10: the owner
ruled K=3; ledger seq 25 `RQ2_AMENDMENT_V1_1` records the amendment — see the
addenda in both 2026-08-09 selection/authorization reports).

## 11. Acceptance metrics (named per lane)

- EXP-BETA: renders for ≥12/15 board names at closes as-of; QQQ-self-test
  β≈1±0.01; synthetic 2× series β≈2±0.05; both-window diagnostic present.
  (No dollar line in v1.)
- EXP-TAIL: renders for all names with ≥250 closes; synthetic moments
  recovered within tolerance; causal-sigma red test (appending a future
  jump must not change earlier jump counts).
- EXP-SPREAD: renders for names with ≥10 valid baseline sessions at the
  chain edge; baseline provably excludes today and earnings weeks (tests);
  replay over ≥60 historical sessions produces a ratio distribution
  summary in the test fixture without errors.
- EXP-TBILL: comparison renders for all names where rates+dividends
  resolve at the chain-edge asof; OCC formula spot-check matches a
  hand-computed fixture; assignment stub returns EX_DIV_DATE_UNAVAILABLE
  for every input (red test).
- Program: baseline byte-identity test green; full suite, ruff, pyright
  green; dashboard builds and the Experiments section renders real
  cached data (no mocks) when enabled.
