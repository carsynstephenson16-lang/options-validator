# QM signal research — owner gate handoff (2026-07-14)

**Status: implementation arc BUILT on `feature/qm-signal-research`; RUN-GATED.**
`qm_study` and `qm_watch` refuse (exit 2) until every `QM_*` value in
`config.py` is owner-typed and both `QM_SCOPE_OVERRIDE` and `QM_STUDY_PREREG`
facts exist in `ledger/facts.log`. Nothing in this document is a result; no
study has run. Every number below is **LLM-asserted** until the owner types it.

Spec: `docs/superpowers/specs/2026-07-14-qm-signal-research-design.md`
(signed-off commit `5bf97f2`, sha256
`eac27f5743267500ff59e01b75f33837c96bfdfd5fb32c1e0c06a824f537f1cb`).

## 1. What the 2026-07-14 research pass found (labels per claim discipline)

Full report retained in the session log; sources: qullamaggie.com (primary),
George & Hwang 2004 *JF*, Jegadeesh & Titman 1993 *JF*, VCP practitioner
writeups (secondary).

- **Parabolic gates as proposed are likely near-vacuous on this universe**
  (Inference). The 1.5×-20d-SMA close is not his rule (his 10/20-day MAs are
  the snapback *target* — Official-source) and is small-cap scale; his stated
  large-cap magnitude is "50–100%+ in a few days or weeks" (Official-source),
  so 1.00-in-40-sessions doubles the floor and slows the window. A signal
  that never fires produces no test.
- **Breakout port is magnitude-faithful but a looser superset** (Inference):
  no contraction/higher-lows test, and the prior-run rule tolerates slow
  grinds where he requires an episodic move. Disclosed in the study's
  caveats block; tightening is a spec-v2 candidate, not built.
- **Strongest support for the breakout leg** is the 52-week-high/momentum
  literature — real, small, weakest in large caps (Official-source).
  No peer-reviewed evidence located for fading large-cap parabolas
  (Inference from absence).
- **Dominant hazard: hindsight universe selection.** The 12 names were picked
  knowing the AI boom; raw post-fire drift would mostly measure the
  universe's tailwind. Defense already in the spec: every fire statistic is
  read only against the same-name unconditional baseline.

## 2. Owner actions, in order (spec §7)

1. **Type every `QM_*` value into `config.py`** (end of file; all currently
   `None` on purpose). Decision table in §3.
2. **Append the `QM_SCOPE_OVERRIDE` fact** — draft in §4. (If the agent
   already appended it during the build session per the approved plan, skip.)
3. **Append the `QM_STUDY_PREREG` fact** — draft in §5, with the values you
   actually typed.
4. **Run order:** `uv run python -m options_researcher.qm_study --counts-only`
   first. If a setup's total fire count is below your feasibility floor, that
   setup is *untestable-as-specified* — a valid, reportable finding; any
   recalibration is a logged v2 decided on counts alone (counts contain no
   outcome information). Otherwise: one full `qm_study` run per the one-run
   contract, then `qm_watch` joins the daily ritual (alert-only).

## 3. Value decision table (ALL LLM-asserted; owner types her own numbers)

| Constant | Spec §6 proposal | Research note (2026-07-14) | Alternate |
|---|---|---|---|
| `QM_RUN_LOOKBACK` | 60 | "1–3 months" faithful | — |
| `QM_RUN_MIN_PCT` | 0.30 | his stated lower bound | — |
| `QM_BASE_MIN_DAYS` / `QM_BASE_MAX_DAYS` | 10 / 40 | "2 wk–2 mo" faithful | — |
| `QM_BASE_MAX_DEPTH` | 0.25 | flat cap is looser than his "tight/tightening" | 0.20 if you want tighter |
| `QM_BASE_SMA` | 20 | he surfs the 10 *and* 20 | 10 for the tighter line |
| `QM_VOL_DRYUP_RATIO` | 0.65 | unanchored (he gives no number) | — |
| `QM_PARA_LOOKBACK` | 40 | his large-cap window is "days to weeks" (faster) | 20 |
| `QM_PARA_MIN_PCT` | 1.00 | his large-cap floor is 0.50 | 0.50 |
| `QM_PARA_GREEN_DAYS` | 3 | faithful lower edge | — |
| `QM_PARA_EXT_PCT` | 0.50 | **small-cap scale; may never fire on mega caps** | 0.10–0.15 |
| `QM_PARA_SMA` | 20 | reference MA is invented (his MAs are the target) | — |
| `QM_HORIZONS` | (5, 10, 20) | pre-declared; freeze once | — |
| `QM_TRADABILITY_DTE` | (30, 60) | monthly band the repo targets | — |
| `QM_NTM_BAND` | 0.10 | spec gap found at build time ("near-ATM" had no number); mirrors H7's definition, frozen independently | — |

Also pre-declare inside the prereg fact (not config): the **feasibility
floor** — proposed 10 deduped fires per setup across the universe (below it:
untestable-as-specified) — and the **pre-registered readings** of the one full
run, e.g.: median forward excess return vs baseline ≤ 0 at every horizon →
"consistent with zero signal value, no H8 arc"; median excess > 0 at ≥ 2
horizons AND fire-session tradability ≥ 60% → "justifies drafting an H8
pre-registration as a separate future arc". Proposals only; owner words them.

## 4. Draft `QM_SCOPE_OVERRIDE` fact (template: H7 SCOPE_OVERRIDE 2026-07-09)

> QM_SCOPE_OVERRIDE 2026-07-14: owner decision (chat sessions 2026-07-13/14)
> -- standing verdict-first rule consciously overridden for a SIGNAL-RESEARCH
> build only: mechanical EOD port of the two computable QM setups (Breakout,
> Parabolic) over the existing 12-name watch universe. Authorization covers:
> daily OHLCV cache from the already-trusted free Yahoo endpoint, signal
> functions, a read-only stdout-only daily watch, and a one-shot
> pre-registered event study (counts-only feasibility stage first).
> NOT covered: any hypothesis/book/verdict registration, any execution or
> stop/trail layer, Episodic Pivot, shorting, universe expansion, threshold
> sweeps, TradingView, new data spend, any live-order path (never). Spec
> docs/superpowers/specs/2026-07-14-qm-signal-research-design.md sha256
> eac27f5743267500ff59e01b75f33837c96bfdfd5fb32c1e0c06a824f537f1cb.

## 5. Draft `QM_STUDY_PREREG` fact (owner fills the bracketed values SHE typed)

> QM_STUDY_PREREG 2026-07-14: spec sha256 eac27f57...f1cb at commit 5bf97f2.
> Owner-typed values: QM_RUN_LOOKBACK=[..] QM_RUN_MIN_PCT=[..]
> QM_BASE_MIN_DAYS=[..] QM_BASE_MAX_DAYS=[..] QM_BASE_MAX_DEPTH=[..]
> QM_BASE_SMA=[..] QM_VOL_DRYUP_RATIO=[..] QM_PARA_LOOKBACK=[..]
> QM_PARA_MIN_PCT=[..] QM_PARA_GREEN_DAYS=[..] QM_PARA_EXT_PCT=[..]
> QM_PARA_SMA=[..] QM_HORIZONS=[..] QM_TRADABILITY_DTE=[..] QM_NTM_BAND=[..].
> Horizons frozen. Stage 1 = counts-only feasibility: a setup with fewer than
> [floor] deduped fires across the universe is untestable-as-specified;
> recalibration on counts alone is a logged QM_STUDY_PREREG_V2, never a
> post-outcome retune. Stage 2 = ONE full study run per data vintage; re-runs
> on new data are new dated reports, never threshold retunes without a new
> fact. Pre-registered readings: [reject wording] / [justifies-next-arc
> wording]. Universe = h7_scope.watch_universe() at run time; thin history
> reads as thin.

## 6. Build inventory (for the independent pre-merge review)

- `data/underlying_ohlcv.py` + tests — blind Yahoo OHLCV cache, raw +
  split-adjusted (volume inverse), OOS-gated.
- `options_researcher/qm_signals.py` + tests — pure §3 signals, dedupe,
  no-look-ahead property tested, `qm_params()` / `qm_prereg_gate()` refusals.
- `options_researcher/qm_study.py` + tests — gated one-shot event study,
  counts-only stage, baselines mandatory, tradability with no-chain
  disclosure, caveats block.
- `options_researcher/qm_watch.py` + tests — gated read-only daily cards,
  fail-closed per name, UNVALIDATED banner, stdout only.
- Branch merges only after independent review + owner say-so (spec §7.4).
