# Phase 1A — Research Integrity Foundation — Design Spec

**Date:** 2026-07-01
**Status:** Design (pre-implementation). Supersedes the orientation in
[handoff-2026-07-01-phase1a.md](../handoff-2026-07-01-phase1a.md) where they differ.
**Scope:** Build the enforcement substrate that must be true **before the first
real ThetaData backtest**, so run #1 records an honest result instead of a lie.
Not the broad learning layer (last), not the statistical gates (Phase 1B,
deferred). One narrow spec.

## Why this exists

The project's entire value is being a disciplined lie-detector: a "no edge after
costs" finding is a success. That only holds if the first real backtest is
recorded under conditions that prevent us from fooling ourselves — before any
result exists to be tempted by. The documented failure modes are not
hypothetical:

- **Honest self-deception (garden of forking paths).** Gelman & Loken show that
  a researcher making even a *single* data-dependent analysis choice inflates
  false positives without any conscious p-hacking
  ([forking paths](https://en.wikipedia.org/wiki/Forking_paths_problem)).
- **Backtest overfitting / holdout unreliability.** Bailey, Borwein, López de
  Prado & Zhu: standard holdouts are unreliable for investment backtests
  ([PBO](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253)).
- **Multiple testing.** Harvey, Liu & Zhu: with extensive data mining, ordinary
  significance thresholds are far too low
  ([NBER w20592](https://www.nber.org/papers/w20592)).
- **Calibration = overfitting.** Carr & López de Prado: calibrating a trading
  rule through historical simulation contributes to overfitting
  ([arXiv 1408.1159](https://arxiv.org/abs/1408.1159)).
- **Naive IID resampling is too optimistic for dependent series.** Dependent
  data needs dependence-aware resampling (Künsch 1989; Politis & Romano 1994
  stationary bootstrap; Politis & White 2004 automatic block length, **with the
  Patton–Politis–White 2009 correction** —
  [PDF](https://public.econ.duke.edu/~ap172/Patton_Politis_White_2009.pdf)).
- **Memory is not enforcement.** Claude Code docs: CLAUDE.md/memory is "context,
  not enforced configuration"; to block an action regardless of what the agent
  decides, use a hook. Anthropic's agent guidance: start simple, add complexity
  only when it demonstrably improves outcomes, and keep autonomous agents behind
  guardrails.

## Threat model: C (staged)

Defend against **honest future-me now**; design clean seams so hard
**autonomous-agent** enforcement can be bolted on later **without a rewrite**.
**No Claude Code hooks are built in Phase 1A** — there is no autonomous runner
yet, so building hooks now is infrastructure for a threat that does not exist.
The substrate is tamper-*evident* + git-anchored (sufficient for honest-me); a
tamper-*proof* external anchor / `PreToolUse` hook is a later, additive step.

## Organizing principle

Every integrity guarantee is enforced by **code**, never by a prose rule in
CLAUDE.md/memory. The guarantees live in the ledger, the integrity CLI, the
run-window gate, and `metrics.py` — each covered by a test. Because a future
hook matches on the **shell command**, the sensitive operations are exposed as
**distinct CLI subcommands** (the "seams"), so a hook can later allow an
in-sample run while blocking an OOS reveal or a ledger rewrite.

---

## Components

Six units. Units 1–5 are enforcement; unit 6 is non-enforcement support. Each is
independently testable on **synthetic trades**, so all of 1A can be built and
verified **before ThetaData is wired** (real reveals inject the real backtest
function later — see Unit 4).

### Unit 1 — Typed trade record

The pre-Phase-1A record fed to `metrics.scoreboard()` was only
`{pnl, capital_at_risk}`. That baseline could not support an IS/OOS split, cohort
bootstrap, or provenance hashing, so Phase 1A tightens the verdict-path trade
schema as follows.

- **Required** (substrate cannot run without these):
  - `pnl` — net of all costs (unchanged).
  - `capital_at_risk` — defined-risk broker margin `(width − credit) × 100`
    (unchanged; remains the denominator of return ratios).
  - `entry_date` — **the IS/OOS split and every cohort key on entry date**, not
    exit date. A trade belongs to the window in which the *decision* was made;
    keying on exit date would reintroduce look-ahead.
  - `symbol` — non-empty underlying ticker string required on verdict paths for
    auditability (verifying a weekly cohort actually spans multiple names, i.e.
    the ~1.5-independent-bets concentration claim) and to foreclose a "drop a
    field, get a tighter CI" escape hatch. Under weekly cohorting the cohort
    *key* is the ISO week, not the symbol, but symbol stays required so the
    cross-sectional structure is auditable and available for later diagnostics
    without a schema break.
- **Recommended** (cheap, high audit value; not blocking):
  - `exit_date`, `strategy_id`, `width`, `entry_credit`, `costs`,
    `economic_max_loss` (see Risk-basis section), `data_source_id`
    (provenance for the data-window hash).
- **Outcome classification:** verdict loss counts are derived from realized net
  `pnl` only: wins are `pnl > 0`, losses are `pnl < 0`, and flat trades are
  neither. If an extractor supplies `is_win`, it must agree with `pnl > 0`;
  contradictory flags are rejected rather than allowed to satisfy or evade the
  loss-count gate.
- **Fail loud, never silently fall back.** On any verdict-producing path
  (`scoreboard()`), a missing `entry_date` or `symbol` must **raise
  `ValueError`** — the same discipline `_validated_arrays` already applies to
  missing `pnl`/`capital_at_risk` ([metrics.py:26-53](../../../metrics.py#L26-L53)).
  A silent IID fallback with a log warning is exactly the quiet integrity hole
  this spec exists to close: it would let a too-tight CI produce a PASS whenever
  someone forgot to populate the dates. IID resampling survives **only** as an
  explicit, opt-in helper (`iid_expectancy_ci()`) used by the pedagogical demo,
  **never auto-invoked** by `scoreboard()`. The demo generates synthetic
  `entry_date`/`symbol` so it exercises the real cohort path; the IID helper
  exists solely to *illustrate* the under-coverage it causes.

### Unit 2 — Append-only, git-anchored ledger

- **Format:** JSONL, one record per line, **hash-chained** — each record carries
  `prev_hash` and `record_hash = H(prev_hash ‖ canonical(record_body))`. Chosen
  over SQLite because it is human-readable, diffable, and the chain *is* the
  tamper-evidence.
- **Anchoring (concrete mechanism):** the ledger is two tracked files —
  `ledger/experiments.jsonl` (the hash-chained records) and `ledger/HEAD` (a
  one-line file holding the current `record_hash`). Every append rewrites
  `ledger/HEAD`. `integrity verify --anchored` (a) recomputes the chain from
  `experiments.jsonl` and checks the last `record_hash` equals `ledger/HEAD`, and
  (b) requires **both files committed with a clean working tree** — an
  uncommitted edit is a tamper signal. Git tags are an optional later addition,
  not required now. **Honest limit stated in the spec:** a purely local chain is
  tamper-*evident*, not tamper-*proof* — a capable agent could recompute every
  hash and re-commit. Committing `HEAD` puts the head in git history (rewriting it
  leaves a trace); a real external/remote anchor is the deferred threat-B layer.
- **Record types and fields:** Phase 1A accepts only `trial_intent`, `run`, and
  `oos_reveal` records. A `trial_intent` record carries a `timestamp`, `reason`,
  cumulative `trial_count`, and optional `hypothesis_id`. A `run` record carries
  `run_id`, `timestamp`,
  `hypothesis_id`, pre-registered `decision_threshold`, `code_sha`,
  `config_hash`, `cost_model_hash`, `source_hash`, `data_window_hash`,
  `risk_basis` (see below), `is_window`, `is_result` (scoreboard dict),
  `oos_window`, `oos_result` (**null until reveal**), `trial_count`
  (cumulative), and `notes`. Verdicts live inside `is_result` / `oos_result`;
  there is no separate top-level verdict field. Phase-1B fields
  (`deflated_sharpe`, `pbo`) are **present but null/stubbed — never computed in
  1A**. Verification rejects unknown ledger record types and malformed window
  objects. An `oos_reveal` record carries a `timestamp`, matching
  `run_id`/`hypothesis_id`, `oos_result` (scoreboard dict), `trial_count`, and
  look-budget metadata. Timestamps are timezone-aware ISO timestamps, not free
  text. Phase 1A record schemas are closed: extra top-level fields are rejected
  so a manually edited ledger cannot smuggle ambiguous, unversioned semantics into
  an otherwise valid hash chain. Ledger verification also rejects untrimmed
  identity/audit strings such as `hypothesis_id`, `run_id`, `decision_threshold`,
  and trial-intent `reason`; canonicalization is not only a CLI convenience.
  `code_sha` must be a full Git object hash. Frozen `config_hash`,
  `cost_model_hash`, `source_hash`, and `data_window_hash` fields must be
  64-character lowercase SHA-256 hex digests, and the registered `is_window`
  must end strictly before `oos_window` begins.
- **Reveal records are append-only.** The pre-registration `run` record is never
  mutated. It keeps `oos_result: null`; a successful reveal appends a separate
  `oos_reveal` record with the same `run_id`/`hypothesis_id`, the `oos_result`,
  and look-budget metadata. This is what makes "write-once" compatible with an
  append-only ledger.

### Unit 3 — Integrity CLI (the hook seams)

Distinct subcommands so a future hook can gate them individually:

- `integrity register` — write a new hypothesis record: `hypothesis_id`,
  `decision_threshold`, `is_result`, and all hashes; `oos_result` null.
  Increments the trial counter. `hypothesis_id` is single-use: a duplicate
  registration is refused, because reusing an ID would make the write-once OOS
  rule ambiguous. `hypothesis_id` and `decision_threshold` are trimmed before
  hashing/storage and must be non-empty after trimming, so `"H1"` and `" H1 "`
  cannot become two different hypotheses. `is_result` must be a scoreboard
  object, `notes` must be text, optional `run_id` must be non-empty when supplied,
  and registration refuses a malformed `data_window`: both `is_window` and
  `oos_window` must be explicit objects with parsable `start`/`end` bounds.
- `integrity reveal-oos` — the only path that populates `oos_result`
  (see Unit 4).
- `integrity trial-log` — record an **intent-to-select** that was not a full run
  (an eyeballed delta, a discarded config, each width in a sweep). Increments
  the counter. `reason` and optional `hypothesis_id` are trimmed and must be
  non-empty when supplied.
- `integrity verify` — recompute the hash chain, check the git-anchored head and
  ancestry, report tamper/consistency status.

**Trial counter:** monotonic, stored *in* the chained ledger so it cannot be
reset without breaking the chain. It counts intent-to-select, not executed runs
(a width sweep of 3 counts as 3). It is *recorded* in 1A; the multiple-testing
deflation that *consumes* it is Phase 1B.

**Frozen source/config/cost surfaces.** `code_sha` is an audit field, not the
drift-enforcement field: ledger anchoring commits naturally change `HEAD` even
when strategy code is unchanged. Instead `source_hash` hashes the
verdict/backtest source-code execution surface (`pyproject.toml`, `uv.lock`,
`config.py`, `metrics.py`, and Python files under `analysis/`, `data/`,
`harness/`, `research/`, `strategies/`) while excluding ledger records, results,
caches, docs, and tests. Market-data content belongs in `data_window_hash` once
ThetaData is wired; it is not smuggled into the source-code hash. The dependency
files are included because changing numpy or another locked runtime dependency can
change the verdict machinery without a `.py` diff. `config_hash` hashes all
uppercase config constants. At `reveal-oos`, the current `source_hash`,
`config_hash`, and `cost_model_hash` must all match the registered values, or the
code refuses the reveal. This prevents a post-registration strategy, verdict,
dependency, or config change from leaking into the holdout while still allowing
ledger anchor commits. `register` also refuses if any file that would be hashed
is untracked or ignored, or if any tracked file in the source-hash surface is
dirty or deleted, because a preregistered hash of uncommitted source cannot be
recovered from git later. The registration may dirty the ledger files; the
research source surface must be committed-clean before that write happens.

**Frozen cost/fill params — one canonical hashable surface.** These constants are
scattered across files, so hashing "config.py lines" by string/line search would
be fragile and would silently miss the most p-hackable one: `ASSUMED_CREDIT_FRAC`
lives in [feasibility.py:25](../../../analysis/feasibility.py#L25), **not**
`config.py`. Instead a single `cost_model_snapshot() -> dict` gathers the frozen
set **explicitly**, canonical-serializes it (sorted keys), and hashes *that one
object* into `cost_model_hash`. Contents: `SLIPPAGE_HAIRCUT`, `MAX_SPREAD_PCT`,
`MIN_OPEN_INTEREST`, `HALF_SPREAD_COST`, `COMMISSION_PER_CONTRACT` (config.py);
`ASSUMED_CREDIT_FRAC` (feasibility.py); `FILL_MODEL_ID` — a new explicit version
string in config.py (the fill model is *logic*, not a number, so it is versioned
by an id that must be bumped if the fill logic changes); and the verdict-affecting
**estimator + policy constants** `BOOTSTRAP_BLOCK_EXPONENT`,
`BOOTSTRAP_BLOCK_CONSTANTS`, `COHORT_GRANULARITY` (Unit 5) and `OOS_LOOK_BUDGET`
(Unit 4) — so block length, cohort granularity, and look budget can't be quietly
retuned without invalidating the hypothesis. Because the drift refusal is keyed on
the hash of this one explicit object, it is **location-agnostic** and needs no
edit-blocking hook. Rule resolving the apparent contradiction with
[feasibility.py:9](../../../analysis/feasibility.py#L9) (which plans to replace
the assumed credit with measured data): **calibrate once on in-sample data, log
+ hash the value, then freeze for that hypothesis.** Measuring a credit from data
is a *fact* (allowed); nudging an assumption because it improves PnL is *tuning*
(banned). Changing a frozen param starts a **new** pre-registered hypothesis and
increments the counter — enforced by the hash mismatch between `register` and
`reveal-oos`.
- **Fill-model semantics:** when `HALF_SPREAD_COST` is true, entry credit crosses
  the bid/ask on both legs (short leg at bid, long leg at ask) and then applies
  `SLIPPAGE_HAIRCUT` adversely on top. A near-mid fill model is a different
  `FILL_MODEL_ID`, not the current conservative model.

### Unit 4 — RunWindow / OOS gate

- Enforce `config.IN_SAMPLE_END` ([config.py:51](../../../config.py#L51)):
  in-sample = entry ≤ 2022-12-31; out-of-sample = after. Currently used by **zero
  code** — this unit is where it becomes real.
- **OOS reveal *is* the first execution of the post-2022 window.** The OOS
  backtest is never run during exploration. `reveal-oos` refuses unless (a) a
  matching `register` exists with a decision threshold, (b) the global OOS
  **look budget** > 0, (c) `ledger/experiments.jsonl` and `ledger/HEAD` are
  **committed with a clean tree** — so the pre-registration is immutable in git
  history *before* anyone peeks at the holdout, and (d) the current `source_hash`,
  `config_hash`, and `cost_model_hash` match the registered values. It then runs
  the OOS backtest and validates every returned trade entry date against the
  registered `oos_window` (`start <= entry_date <= end`) as well as the global
  `IN_SAMPLE_END` boundary. Only then does it append an `oos_reveal` record with
  `oos_result` **write-once** and decrement the budget. A second reveal on the
  same hypothesis is refused.
- **Global look budget = 3** (`config.OOS_LOOK_BUDGET = 3`, hashed into the
  ledger). This is a global cap across the whole research program, not per
  hypothesis. Trader rationale: with 2023–2024 as the holdout and this universe
  behaving like ~one tech-beta factor, five looks is too generous — three buys
  exactly one primary reveal, one legitimate repair/retest, and one final "we are
  done touching this holdout" allowance. A single holdout leaks through the
  researcher; enforcing `IN_SAMPLE_END` makes the system *less unsafe*, not
  *safe* — the ledger + budget exist because the holdout alone is a **weak floor**
  (this is why PBO exists). CSCV/CPCV is the ideal but this sample is likely too
  thin to slice.
- **Testability before ThetaData:** `reveal-oos` takes an **injected run
  function**, so it is fully unit-testable now with a fake backtest and wired to
  the real Lumibot/ThetaData path later.
- **Non-verdict data probes stay in-sample.** Smoke tests and environment checks
  are allowed to verify connectivity, schema, and caching, but they must use
  dates on or before `IN_SAMPLE_END` unless they go through the OOS reveal gate.
  "Just printing a chain" after 2022 is still a holdout look.
- **Cached/fetched option chains are validated at the adapter boundary.** Cache
  keys must use a safe symbol and ISO date, and cached parquet must contain the
  required option-chain schema with finite numeric fields before any strategy or
  smoke path can consume it. Bad cache data is an integrity failure, not a
  downstream surprise.

### Unit 5 — Dependence-aware confidence interval

Replace the IID resample in `_expectancy_ci`
([metrics.py:65-73](../../../metrics.py#L65-L73)), which does
`rng.choice(pnls, replace=True).mean()` and assumes independent trades. They are
dependent on **two axes**: serial (losses cluster in vol regimes — 2018 Q4, 2020
Feb–Mar, 2022) and cross-sectional (`UNIVERSE` ≈ 1.5 independent bets; the five
names lose in the same week). IID underestimates variance → CI too tight →
**false PASS**.

- **Primary: block bootstrap over the time-ordered sequence of entry-*week*
  cohorts.** Group trades into cohorts by the **ISO week of `entry_date`**
  (`COHORT_GRANULARITY = "week"`, frozen/hashed); resample **contiguous blocks of
  weekly cohorts** over calendar time. Keeping a whole weekly cohort intact
  preserves cross-sectional correlation — the five names lose in the *same week*,
  and a 30–45 DTE spread holds multi-week overlapping exposure — so same-week
  co-movement is *always* grouped, not left to a lucky block draw. Blocking
  contiguous weekly cohorts preserves serial/regime clustering across weeks.
  Statistic per resample = total PnL / total trades. Weekly is the deliberate
  granularity: daily cohorts are too fine (same-week co-movement leaks unless the
  random block happens to span it), monthly too coarse. This method preserves
  **both** axes — cohort resampling alone does not (it treats cohorts as
  independent and breaks the serial axis), which is why the block sits on top.
- **Pinned block-length envelope (no quiet tuning knob).** Block length is
  itself verdict-affecting (it sets CI width), so it must be pre-registered and
  hashed, not chosen ad hoc. Fix `BOOTSTRAP_BLOCK_EXPONENT = 1/3` (the standard
  n^(1/3) blocking rate for variance/CI estimation) and
  `BOOTSTRAP_BLOCK_CONSTANTS = [0.5, 1, 2, 4]`; candidate lengths are
  `round(c · n_cohorts^(1/3))` for each `c`, deduped, clamped to
  `2 ≤ block_len ≤ n_cohorts − 1` (block 1 = IID; block ≥ n collapses the CI to a
  point). `n_cohorts` is the number of weekly cohorts. **Degenerate-sample guard:**
  if `n_cohorts < 3` the clamp range `2 ≤ L ≤ n_cohorts − 1` is empty — no valid
  block length exists — so no dependence-aware CI can be formed and `scoreboard()`
  returns **INSUFFICIENT SAMPLE / no verdict** (never PASS/FAIL), consistent with
  the loss-gated verdict floor: too few distinct entry weeks means there is
  nothing to block-resample honestly. Note the mechanics: under
  the **report-the-widest** rule a stray near-IID small block is already
  *dominated* (it yields the narrowest CI and cannot move the reported bounds), so
  the load-bearing part of this guard is the **upper** clamp; the lower clamp is
  defensive. Both constants are part of the cost-model snapshot (Unit 3), so they
  cannot be quietly retuned without invalidating the hypothesis. A **fixed
  pre-registered envelope is
  deliberately chosen over data-driven automatic selection** (e.g. Politis–White):
  automatic block-length selection is itself a data-dependent choice — another
  forking path — so pinning is the more integrity-honest option here.
- **Cross-check:** stationary bootstrap (Politis–Romano, random/geometric block
  length) over the **same** weekly-cohort sequence, sweeping the **same deduped,
  clamped block-length envelope** as the primary — each `L` in the envelope is
  used as the *mean* geometric block length (`p = 1/L`). **Report the widest CI
  across all `(method, block_len)` combinations** — the minimum lower bound and
  maximum upper bound over both methods and every `L` in the envelope. Reporting
  the widest, not an average, means no configuration can be selected because it
  flatters the result.
- **Honest expectation, stated in the spec:** with ~3 major independent regimes,
  the effective number of independent blocks is small, so the CI will be **wide
  and somewhat unstable**. That is correct behavior, not a defect; it reinforces
  the loss-gated verdict and the deferral of DSR/PBO.
- **TDD (no fake precision):** a synthetic autocorrelated + cross-correlated
  series where the IID CI demonstrably under-covers (excludes zero → false PASS)
  and the block/cohort method widens (includes zero → correctly refuses). Do
  **not** assert "IID-data ≈ IID-CI": the report-the-widest envelope is *honestly*
  wider than a single IID CI even on independent data, so that assertion forces
  fake precision. On independent data, assert only that the CI is finite, ordered
  (`lo < mean < hi`), and stable under the fixed seed. Avoid flaky Monte-Carlo
  pass/fail coverage thresholds in the unit suite; a coverage sweep can live as a
  separate non-asserting diagnostic script.

### Unit 6 — Facts log (support, non-enforcement)

A free-form, append-only descriptive log — ThetaData gaps, measured spreads,
commission drag, workflow notes — **clearly separate** from the immutable
hypothesis ledger and explicitly **not verdict-feeding**. This is the "learn
facts, not parameters" channel.

---

## Risk-basis amendment (finding #7)

Before the Codex post-review fix, `size_defined_risk`
([base.py](../../../strategies/base.py)) sized on **gross** payoff max loss
`(width − credit) × 100`, excluding commissions. OIC confirms that payoff
definition (max loss = high strike − low strike − net premium); commissions are
additional real cash loss. At the current **zero-slack** $2-wide config
([config.py:76-85](../../../config.py#L76-L85)), the $2.60 round-trip commission
pushes true economic risk to ~$142.60, above the $140 per-trade budget — which
**flips feasibility from 1 contract to 0**. Gross-only sizing therefore would let
the backtest trade a configuration that violates the stated "1% of sleeve" rule
on every $2-wide trade: certifying a strategy that could not actually be run.
This is a simulation-realism integrity concern, not later polish.

Resolution (two distinct concepts):

1. `capital_at_risk` = defined-risk broker margin. **Unchanged**; remains the
   headline return-ratio denominator (commissions are a PnL drag in the
   numerator, not collateral).
2. `economic_max_loss` = margin + round-trip commissions. The **sizing/budget-fit
   basis** — and the denominator of a **secondary** diagnostic.

- **Both ratios reported, verdict driven by neither.** The scoreboard keeps the
  headline return ratios (Sharpe/Sortino/capital-efficiency) on `capital_at_risk`
  and **adds `return_on_economic_max_loss` as a secondary diagnostic**. Margin
  return and economic-risk return answer different trading questions, so we report
  both — but the **verdict is driven by the PnL expectancy CI (Unit 5), not by any
  ratio**. If `economic_max_loss` is supplied for any trade, it must be supplied
  for every trade and must be at least `capital_at_risk`; otherwise the scoreboard
  refuses the malformed diagnostic instead of printing a flattering number.
  Sizing, however, must use `economic_max_loss`.
- **In Phase 1A (this spec):** the ledger **defines and hashes the `risk_basis`**
  used for a run, so every verdict is interpretable and reproducible.
  `risk_basis` is an enum: exactly `capital_at_risk` or `economic_max_loss`.
  Unknown values are refused at registration time.
- **Post-review implementation before the first real backtest:** `size_defined_risk`
  now gates on `economic_max_loss`, the feasibility report uses economic max loss
  as the budget-fit basis, and the strategy logs economic max loss when it skips or
  places a spread. Future ThetaData trade extraction must still record both
  `capital_at_risk` and `economic_max_loss` separately.

---

## Principles stated in the spec

- **Deterministic code owns the verdict.** Agents review evidence, explain
  failures, and propose next hypotheses; they never decide edge. (WAT: probabilistic
  orchestration, deterministic execution.)
- **DSR/PBO are Phase-1B warnings behind a minimum-N guard, never certifiers.**
  The sample (~1.5 independent bets, low-tens of losses) risks laundering a thin
  sample into false rigor. The real certifier is the loss-gated, dependence-aware
  CI.
- **Threat model C:** tamper-evident + git-anchored now; hooks / external anchor
  later; no hooks built in 1A.

## In scope

Units 1–6; the `risk_basis` definition + hashing (#7, ledger side); replacing the
IID bootstrap; enforcing `IN_SAMPLE_END`; the CLI seams. All testable on
synthetic trades.

## Out of scope

- Claude Code `PreToolUse` hooks (seams only; hooks are the later threat-B layer).
- Autonomous agent runner.
- Auto-tuning strategy parameters (delta/width/DTE/stops) **or** cost/fill
  assumptions to PnL.
- DSR / PBO / CSCV computation or gating (Phase 1B; fields stubbed only).
- ThetaData fetch and Lumibot strategy-adapter wiring (Phase-0 stubs stay stubs;
  the substrate injects a run function, it does not wire the engine).

## Testing strategy

Stdlib `unittest` (no pytest), TDD, run via
`uv run python -m unittest discover -s tests`. New coverage: hash-chain tamper
detection; `verify --anchored` catches a rewritten record, a `HEAD` mismatch, and
an **uncommitted/dirty tree**; `scoreboard()` **raises** on a missing
`entry_date`/`symbol` (no silent IID fallback); `reveal-oos` refused without a
prior `register`, refused when the look budget is exhausted, and refused when the
ledger tree is dirty/uncommitted; `oos_result` write-once; config/cost-hash
mismatch detected between `register` and `reveal-oos`; trial counter monotonic and
non-resettable; the reported CI is the **widest across the block-length envelope +
stationary cross-check**, and that CI widens vs the explicit IID helper on a
synthetic clustered series (IID under-covers). All existing tests stay green.

## Definition of done

The substrate is true before run #1: append-only git-anchored ledger;
pre-registration gate; write-once OOS with enforced `IN_SAMPLE_END` and a global
look budget; monotonic intent-to-select counter; frozen + hashed cost/fill params
and `risk_basis`; dependence-aware (block-over-cohort primary + stationary
cross-check) CI replacing the IID one — each enforced by code, each covered by a
test, all existing tests green, committed on a branch. Phase-1B stat fields are
stubbed, not computed. The `size_defined_risk` economic-max-loss sizing change is
implemented and covered before the first real backtest.

## Sequencing

(1) reproducible foundation [done] → (2) **this Phase 1A substrate** + economic-risk
sizing fix [done in Codex post-review patch] → (3) wire ThetaData → first backtest
**through the substrate** → (4) Phase 1B statistical gates → (5) broad
learning-layer spec last.
