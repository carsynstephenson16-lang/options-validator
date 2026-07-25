# RQ2 scanner-enrichment briefs — top-5 additions, validation protocol, owner blanks

**Date:** 2026-07-22. **Status:** DRAFT briefs for Codex execution; owner types every
frozen number; nothing here is registered yet. Companion to
`reports/2026-07-22-scanner-quant-methods-survey.md` (ranked survey and evidence).

**2026-07-24 update (owner-directed):** the owner delegated every `[OWNER]` blank
below to Claude this date ("i had you type those in for me"). The resolved values
live in the **§ Delegated values (2026-07-24)** table at the end of this doc. Every
value is **LLM-proposed under owner delegation** — per the standing provenance rule
they are tested at implementation time and re-confirmed at registration time, never
silently frozen. The `[OWNER …]` markers in the brief bodies are left in place so
the delegation is visible, not overwritten.

**Standing constraints binding every brief below (from the owner-approved replan,
`docs/superpowers/specs/2026-07-22-project-replan-design.md`):**
1. **Ordering:** Phase 1 recorders (R1–R5) come first. These briefs are Phase-3 work
   (N2/N3) and queue behind them unless the owner explicitly reprioritizes.
2. **Addition-only:** the current GREEN recipe, thresholds, gates, and Top-3 ordering
   are FROZEN for RQ1's sake. Every feature here is a new display badge/line/panel.
   No new feature may change any grade, gate, rank, or trigger.
3. **Fail-closed:** missing input → honest gap ("no data"), never a fabricated value,
   never a silently-skipped badge that looks GREEN.
4. **Display labels:** every model-derived number carries its label ("market-priced,
   not a forecast" / "measured over N past cycles" / "simple, not compounded").
5. **Tests:** unittest, offline against the local cache; no network in tests; ruff +
   pyright clean; every new constant lives in `config.py`.
6. **No RQ1 code** until the owner's N4 choice (replan §5).

---

## Brief B1 — Badge B: earnings-conditioned term-structure corner

**Scope guard:** moves RQ1/RQ2 (live registered + planned registration) toward their
verdicts by building the registered-candidate badge the replan names.

**Objective.** A per-name, per-day term-structure column and a "corner" badge:
- `ts_slope = atm_iv_near − atm_iv_long` (near = 15–45 DTE band, long = [OWNER:
  either BS-spec-§6's 60–120 or `H7_IV_TENOR_DTE_BAND` (72,108) — pick ONE and record
  why]; ATM selection identical to the existing nearest-strike put convention).
- `ts_pctl` = causal percentile of `ts_slope` over trailing 252 obs, min 60 obs
  (BS spec §6 conventions: lookahead-excluded rows labeled and excluded).
- `earnings_tag`: the slope renders with its earnings context (report inside the near
  window: "event-priced"; else "no earnings in window"; unknown → UNKNOWN). The
  PARKED prior verdict stands: an un-conditioned richness *ranking* is forbidden;
  the tag is what keeps this badge legitimate.
- `corner` = (ts_pctl ≥ [OWNER, draft 0.80]) AND (vrp_pctl ≤ [OWNER, draft 0.20])
  where `vrp_pctl` is the causal percentile of existing `iv_minus_rv`. Display-only.
- **Owner choice — tag vs gate (verifier-flagged distinction):** as drafted the
  corner flag can fire with no earnings in the near window and the earnings context
  appears only as a tag. [OWNER picks: (i) tag-only as drafted, or (ii) the corner
  flag itself requires a confirmed report inside the near window]. The parked prior
  verdict ("un-conditioned term-structure RANKING is forbidden") is honored either
  way because this badge never ranks; the choice is about display honesty.

**Existing assets:** partial column work exists on branch
`feature/bs-attractiveness-descriptive` (unmerged); `h7_signals.atm_iv_90d()` is the
long-tenor pattern; `features.py` holds the near-tenor `atm_iv`. First step is a
reconcile-and-merge review of that branch, not a rewrite.

**Files:** `options_researcher/features.py` (new columns), dashboard render,
`config.py` (TS_* constants), tests `tests/test_ts_corner_badge.py`.

**Tests/acceptance:** causal-percentile property test (shifting later data never
changes an earlier value); min-obs refusal; UNKNOWN earnings → UNKNOWN tag, never
GREEN; a name with no in-band long expiry → honest gap; frozen-recipe untouched
(board ordering byte-identical with badges hidden).

**Out of scope:** any use in ranking (that is RQ2's decision), any trigger, any
backtest.

## Brief A1 — Badge A: bounce lens

**Scope guard:** replan-named badge; feeds H11's registered form with a mechanical,
non-discretionary scanner surface.

**Objective.** `bounce_armed` per name from EXISTING fields only:
`dist_52w_high ≤ −[OWNER]%` AND `mom_1m ≥ [OWNER]%` AND `rv21` percentile ≥ [OWNER]
(exact combination is the owner's call; this brief proposes the three-condition AND
as the draft). Rendered as a badge on long-lane cards plus a board-strip list of
armed names.

**Mandatory honesty line on the badge itself** (replan §2.2): "Priors lean negative:
Card 3 measured −$85.47/trade (INSUFFICIENT_SAMPLE, 6 trades); the QM parabolic study
found violent up-moves continued, not snapped back. This badge describes a setup; it
does not predict a bounce."

**Files:** `options_researcher/technicals.py` or a new `bounce_lens.py`, dashboard,
`config.py` (BOUNCE_* constants, owner-typed), tests.

**Tests/acceptance:** SPAC entity floors respected for USAR/IREN (52-week references
never cross the listing boundary — reuse `H7_SIGNAL_CLOSES_START` handling);
NaN-gating on short history; priors line always renders with the badge; frozen
recipe untouched.

## Brief C1 — Board concentration & clustering panel

**Scope guard:** makes the standing "one AI factor" risk visible on the surface the
owner actually reads; display-only.

**Objective.** One dashboard header panel, four lines:
1. `ρ̄` = mean pairwise Pearson correlation of daily log returns, trailing
   [OWNER, draft 63] sessions, plus `n_eff = N/(1+(N−1)ρ̄)` — "today's board ≈ X
   effective independent bets" (formula precedent: `analysis/power_check.py`).
2. Earnings clustering: "k of today's GREEN cards report within [OWNER, draft 5]
   sessions of each other" — rollup of per-card earnings fields already computed;
   UNKNOWN names listed separately, never counted as clear.
3. Combined-max-loss bracket: Σ of admissible GREEN cards' own max-loss vs
   `RISK_SLEEVE`, shown as a RANGE with the n_eff translation and an explicit
   "hypothetical if you took them all — not advice, not a book" label.
4. Worst-observed-day replay: the dated worst mean-return day in the cached panel
   applied to today's cards' notionals ("on 2025-XX-XX these names averaged −X%;
   applied to today's cards that's ≈ −$Y"). Labeled "worst OBSERVED, not worst
   possible"; no IV response modeled (stated on the line).

**Files:** new `options_researcher/board_risk.py`, dashboard, `config.py`
(BOARD_CORR_WINDOW etc.), tests.

**Tests/acceptance:** panel never appears in per-card grades or ordering (test pins
byte-identical Top-3 with the panel disabled); short-history names drop out of ρ̄
with disclosure ("computed over 12 of 15 names"); no allocation phrasing anywhere
(test greps rendered text for banned suggestor patterns).

## Brief N3-1 — Market-implied expectations lines

**Scope guard:** replan item N3 (owner-promoted from the parking lot); its parked
gate ("display-only, never grades/ranks/triggers, owner nod + one-page spec") is
honored — this brief IS the one-page spec for the owner to nod at.

**Objective.** Three lines from existing per-contract fields:
1. Expected move: "the market prices roughly ±X% by {expiry} (1 standard deviation,
   about 2 in 3 odds — not a forecast)": `iv·√(dte/365)`.
2. Short-put/ASSIGNMENT_WATCH: "market-implied odds of finishing below ${K}: ~Y%
   (risk-neutral, tends to overstate real-world downside odds)": `N(−d2)` using the
   merged `black_scholes.py` d2; inputs r, q from `data/rates.py` once CSVs exist —
   until then compute with [OWNER choice: r=0 disclosed as approximation, or wait
   for the CSV unlock]. Fail-closed is the default recommendation: wait.
3. Touch probability on ASSIGNMENT_WATCH: "odds of touching ${K} at some point
   before expiry are roughly double the finish-below odds" — the reflection-principle
   approximation, with the exact barrier formula (drift-corrected) used in code and
   the "roughly double" only as prose.

**Files:** `options_researcher/attractiveness.py` card prose (additive lines only),
`portfolio.py` ASSIGNMENT_WATCH extension, tests.

**Tests/acceptance:** label text is test-pinned (the strings "not a forecast" and
"risk-neutral" must appear on every render); no probability ever enters a grade,
rank, or trigger (pin test); d2 math cross-checked against `black_scholes.py` unit
tests; missing IV/rate → line absent with honest gap, never a guessed number.

## Brief V1 — VRP-done-properly calibration pair

**Scope guard:** upgrades the scanner's core seller-honesty axis with measured
history; the current proxy's own docstring concedes the gap.

**Objective.** Two strictly-causal per-name lines on seller cards:
1. Tenor-matched VRP history: for past completed cycles at the card's DTE bucket,
   `IV_entry(τ) − realized vol over [entry, entry+τ]`; render "over the last N
   completed {τ}-day cycles this name's implied ran X pts above/below what was then
   realized (N=…)". Excludes the open cycle by construction; earnings-window cycles
   reported separately from clean cycles.
2. Earnings-crush history: median and IQR of
   `(atm_iv[t−1] − atm_iv[t+1])/atm_iv[t−1]` across that name's PAST reports from
   the point-in-time earnings store; "median front-month IV drop across last N
   reports: X% (N=…)".

**Files:** `options_researcher/features.py` (batch walk-forward builder; store in
the attractiveness feature dir with its own columns), card prose, `config.py`
(VRP_CAL_* window constants, owner-typed), tests.

**Tests/acceptance:** causality property test (truncating the cache at day D and
rebuilding reproduces the day-D values exactly — no future rows leak); N always
rendered; names with <[OWNER, draft 6] completed cycles refuse with "insufficient
history"; UNKNOWN earnings dates excluded, not guessed; frozen recipe untouched —
board grades and Top-3 ordering byte-identical with the new columns present vs
absent (same pin as B1/A1/C1/N3-1).

## Brief H1 — cost/annualization honesty bundle (hygiene; no RQ2, ship anytime)

Trivial, wording-only, no registration needed: append "(simple, not compounded)" to
every `annualized_yield` render; add the one-line 252-vs-365 day-count disclosure to
the dashboard footer; optional round-trip cost line "entry + modeled exit at today's
spread ≈ X% of this credit (early-close scenario, not the base case)". Test-pin the
strings. This is the one brief small enough to ship during Phase 1 without competing
with recorder work.

## Data-unlock actions (owner-run, unblocks ranks 6 and 15)

1. `data/rates/treasury_cmt.csv` — source: the treasury.gov daily par-yield URL
   already frozen in `config.BS_TREASURY_SOURCE_URL`; schema and staleness rules are
   already enforced by `data/rates.py` (fail-closed). Owner runs the sanctioned
   Trafilatura flow or manual download; retain capture time + URL.
2. `data/rates/expected_dividends.csv` — issuer-IR sourced expected dividends for the
   names that pay (VST, CEG, MSFT, ET, AVGO at least — verify each on its IR page);
   schema per `data/rates.py::DIVIDEND_FIELDS`. Unlocks the OCC-grounded
   early-assignment flag (survey rank 6) — the highest-value blocked item.
3. QQQ (and SPY) daily closes through the existing sanctioned closes pipeline —
   unlocks the beta-translation line (rank 15) and an index-relative regime line.

## RQ2 pre-registration skeleton (owner types every [OWNER])

```
# RQ2 — scanner enrichment ranking-quality registration
Study id:                      RQ2-v1        seq: ___ (experiments.jsonl)
Candidate badges (K = ___):    [OWNER — exact frozen definitions of each]
Cumulative attempts counter:   [OWNER — per ledger-discipline rule 8, includes
                                every discarded variant tried while designing]
Universe:                      config.ATTRACTIVENESS_UNIVERSE (15) — confirm
Card roles in scope:           [OWNER]
Baseline ranking:              GREEN-fraction ordering, commit [HASH], frozen
Candidate ranking rule:        [OWNER — how a badge would reorder, if promoted]
Label exit convention/role:    [OWNER — REQUIRED: no frozen exit exists today for
                                put/CC/PMCC income cards; hold-to-expiry proposed]
Fill/cost model:               frozen repo surfaces (adverse fills + SLIPPAGE_HAIRCUT
                                + COMMISSION_PER_CONTRACT + liquidity gates at entry
                                AND resolution) — unchanged
Historical pass:               Card-3-class EXPLORATORY IN-SAMPLE only, never a
                                verdict; used to (a) leak-test the pipeline,
                                (b) measure sigma for the power math, (c) allow
                                early outright rejection only
Forward window:                start [OWNER date]; calendar backstop [OWNER date,
                                ≥12 months recommended]
Primary metric:                top-minus-bottom bucket forward cost-adjusted
                                return-on-risk spread; bucket split [OWNER]
Adverse-count gate:            MIN_ADVERSE_BOTTOM_BUCKET = [OWNER, proposed 10]
Bootstrap:                     BOOTSTRAP_SAMPLES=5000, Politis-White blocks,
                                weekly cohorts — unchanged repo constants
Multiple testing:              Holm step-down, alpha = [OWNER, proposed 0.10],
                                across K; upgrade to White/SPA if cumulative
                                attempts exceed ~8-10
Secondary (never gates):       Spearman rank-IC, |rho|>=0.30 notable (RQ1 pattern)
Rejection:                     Holm-adjusted CI90 upper bound <= 0
Promotion:                     Holm-adjusted CI90 lower bound > 0 AND adverse gate
                                met AND ablation spread (baseline+X vs baseline)
                                not negative at CI90
Insufficient sample:           otherwise — an accepted outcome (H9/H10b precedent)
Regime slices (descriptive):   rv21 terciles; earnings-week flag — never gate
```

## Owner decision checklist (blocking order)

1. **N4** — RQ1 disposition. Recommended: (a) pre-badge GREEN-fraction.
2. **Exit convention** for income-card labels (the RQ2 skeleton's one hard gap).
3. **RQ2 blanks** — corner/bounce thresholds, bucket split, adverse count, α,
   window dates.
4. **Data unlocks** — two CSVs + QQQ/SPY closes approval.
5. **Priority** — confirm these queue behind Phase-1 recorders (default), or
   explicitly pull Brief H1 forward (safe: wording-only).
```

## § Delegated values (2026-07-24) — owner-delegated, LLM-proposed

Owner delegation recorded 2026-07-24 ("i had you type those in for me"). Every value
below is **LLM-proposed**: tested at implementation, re-confirmed at the RQ2
registration act, never silently frozen. Where the 2026-07-23 twelve-month program
already carried an owner-forwarded value, that value is kept unchanged and marked.

| Blank | Value | Reasoning |
|---|---|---|
| B1 long-tenor band | `H7_IV_TENOR_DTE_BAND` (72,108) | Reuses an existing frozen constant and the `atm_iv_90d()` code path; one tenor convention repo-wide, not two; matches the IV90 already rendered on watcher lines |
| B1 `ts_pctl` corner cut | ≥ 0.80 (draft kept) | Extreme-quintile cut; display-only badge, symmetric with the vrp cut |
| B1 `vrp_pctl` corner cut | ≤ 0.20 (draft kept) | Symmetric quintile |
| B1 tag-vs-gate | **(ii) event-gated flag** | The badge is *named* earnings-conditioned; a no-event fire under that name misleads even with a tag. No information is lost — `ts_slope`/`ts_pctl` columns still render for every name; only the corner FLAG requires a confirmed report inside the near window. Fail-closed spirit |
| A1 `dist_52w_high` | ≤ −20% | Correction-grade drawdown; deliberately DISTINCT from H7 lane A's frozen 25% so badge ≠ lane, and it arms ahead of the lane, giving observational lead time |
| A1 `mom_1m` | ≥ +5% | Modest reclaim evidence on names whose monthly vol runs 10–20%; higher would make the badge a momentum-chaser rather than a bounce lens |
| A1 `rv21` percentile | ≥ 0.60 | Flags bounce setups only in vol expansion; keeps the badge quiet in sleepy drifts |
| C1 ρ̄ window | 63 sessions (draft kept) | One trading quarter; matches `analysis/power_check.py` precedent |
| C1 clustering window | 5 sessions (draft kept) | One trading week |
| N3-1 rate choice | **Moot — use the live curve** | `data/rates/treasury_cmt.csv` went LIVE 2026-07-23; the r=0 approximation question no longer exists. Fail-closed on staleness per `data/rates.py` |
| V1 min completed cycles | 6 (draft kept) | Below ~6 non-overlapping cycles a median/IQR is noise, not history |
| RQ2 K (candidate badges) | **3** — B1 corner, A1 bounce, V1 VRP-cal | C1 is a panel and N3-1 is prose; neither ranks, so neither is a ranking candidate |
| RQ2 attempts counter | Start at **3**, with the survey screen footnoted | The 20-method survey was a prior-based literature screen, not fitted to our cache — that distinction is what keeps Holm-across-3 defensible. Any cache-tuned design variant increments the counter; past ~8–10, upgrade to White/SPA per this brief's own rule |
| RQ2 card roles in scope | Income seller cards (short put / covered call) + long-call cards | The two families the board actually renders |
| RQ2 ranking rule (if promoted) | Lexicographic tiebreak within equal GREEN-fraction | Least-disruptive promotion; a badge never overrides GREEN-fraction itself |
| RQ2 exit convention | Hold-to-expiry | The brief's own proposal; consistent with the owner-forwarded Part-II working values (2026-07-23 program) |
| RQ2 forward window | Start 2026-09-01; backstop 2027-09-01 | Post-Phase-1-recorders realistic ship date; 12-month backstop per this brief's recommendation |
| RQ2 bucket split | Terciles (top 5 vs bottom 5 of 15) | Quintiles are 3-name buckets at N=15 — too thin for a spread metric |
| RQ2 MIN_ADVERSE_BOTTOM_BUCKET | 10 (owner-forwarded 2026-07-23, unchanged) | — |
| RQ2 Holm α | 0.10 (owner-forwarded 2026-07-23, unchanged) | — |

**Feasibility-gate note (2026-07-24 process rule):** the RQ2 registration must quote
its projected adverse-count reachability (bottom-bucket cards accrue daily, so the
10-adverse bar projects reachable within weeks — compute and state the number at
registration time per `docs/superpowers/2026-07-24-registration-feasibility-gate.md`).
