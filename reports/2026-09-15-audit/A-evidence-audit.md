# A — Evidence audit: what this repo has empirically found, and how each finding could be lying

**2026-09-15. Read-only adversarial audit; nothing modified.** Vocabulary: survived this test / not yet rejected / rejected / consistent with zero edge.

**Headline:** across 32 ledger records and ~2.5 months the repo holds **zero loss-gated verdicts**, **one** paper options position ever opened, and **zero completed paper trades**. Every positive-looking number is in-sample, non-blind, outcome-selected, or under its own loss bar. Paths are relative to `/Users/carsynstephenson/options-validator/`. (~2,800 words; over the 2,500 target because each table cell carries a cited figure.)

---

## §1 Registry

Source: `ledger/experiments.jsonl` (seq); results in `ledger/facts.log`.

| ID (seq) | Design | Validation path | Loss bar / verdict rule | Sample | Status | Numbers |
|---|---|---|---|---|---|---|
| **H1** (0) | Put credit spread SPY/QQQ $2 wide 0.30Δ EOD | IS 2018–22, then **one** sealed OOS reveal 2023-01..2026-06 | CI90 lower > $0, ≥10 losses, ≥3 cohorts; FAIL iff CI90 upper < $0 | IS n=226, 113 losses; OOS **never revealed** | IS **rejected**, holdout sealed | exp −$102.79, CI90 [−132.61, −74.46], total −$23,230.80 |
| **H2** (3) | Same, $5 wide (sweep winner) | Same | Same | IS n=196, 60 losses | IS **rejected**; standing advice: don't spend the OOS look | exp −$39.07, CI90 [−61.28, −18.08] |
| sweep $1 (1) | $1 arm, IS only | IS arm | Highest IS CI90 lower bound, ≥10 losses | n=356, 312 losses | **rejected** | exp −$185.17, CI90 [−204.92, −164.12] |
| sweep $5 (2) | $5 arm, IS only | IS arm | Same | n=196, 60 losses | **rejected** (least-bad width, still negative) | exp −$39.07 |
| **H4** (4) | Composite thesis portfolio | Forward paper ≥2 quarters | not reached | 0 cycles | **superseded at zero cycles** | — |
| **H5** (5, amd 29) | Sector Income Core: LEAPS/CSP/CC/PMCC | Forward paper | **no loss bar ever registered numerically** | 0 options positions; 39 VST shares | trigger **RETIRED** 08-17; observe-only | — |
| **H6** (6, amd 22) | Post-earnings long call; NVDA/PLTR/AMZN; 45–90 DTE; ≤$2k/mo | Forward paper | CI90 upper < 0 **after 8 completed**; kill = 3 straight full-loss months | **1 open, 0 completed, 0 losses** | `INSUFFICIENT_SAMPLE`; evaluator dark since 07-27 | H6-0001 NVDA $220C exp 09-18, entry $920.65; 07-27 mark −$441.30 (−47.9%) |
| **H7a/b/c** (7–10) | Three swing lanes on AI names, judged separately | Forward paper ≥3 mo per lane; 2018–26 diagnostic **WITHDRAWN** as verdict-capable (seq 10) | CI90 entirely < 0 with **≥10 losses** per lane | 0 entries (`h7_positions.csv` header-only; `ledger/h7_forward/events.jsonl` = 1 registration record) | **PAUSED**; Schwab restart lane prepared, not activated | — |
| **H8** (11) | Pre-earnings long call; PLTR/AMZN; T-15..T-8 before a **confirmed** report; IVR ≤ 0.50 | Forward paper only | CI90 upper < 0 **after 8 completed** | 0 | **no scorer exists in the codebase** | — |
| **CARD3** (12,13) | Near-bottom long call, 8 names, **IS 2018–22 only** | One-run exploratory, never a verdict | CI90 upper < 0 with ≥10 losses | 235 signals → **7 fills** → 6 complete, 4 losses | `INSUFFICIENT SAMPLE / INCONCLUSIVE` | n=6, 2W/4L, exp −$85.47, CI90 [−187.97, +13.87] |
| **H9** (14) | Post-earnings conditional, calls-only, 8 names, **non-blind historical** | One run; can never validate/reject H6/H7/H8 | ≥10 losses | 165 events → 16 trades, **4 losses** | `INSUFFICIENT_SAMPLE`; contract **spent** | 12W/4L, exp **+$290.32**, CI90 [+27.82, +574.46], total **+$4,645.20** |
| **H10a** (15) | QM parabolic continuation | Forward paper to 2026-10-06 | CI90 upper ≤ 0 at **≥7 losses** (owner-lowered from 10) | 4 obs days, 3 usable, **0 fires** | **CLOSED 08-15 `INSUFFICIENT_SAMPLE — STARVED`** | n=0; neither rule computable |
| **H10b** (16,28,30) | QM breakout continuation | Forward paper to 2027-01-06 | Same, ≥7 losses | 10 days 08-20→09-09: **0 fires**, 63 no-signal, 47 DATA-skips | running, 0 positions | — |
| **RQ1** (17,20) | ρ of GREEN-fraction vs forward RV / IV change | Descriptive, no verdict | \|ρ\| ≥ 0.30 = effect-size flag only | 4,886 obs, 4 names | **SPENT**; `outcome-selected, self-deceiving, cannot-promote` | ρ(fwd RV) **−0.326**; ρ(fwd IV chg) +0.086 |
| **RQ2-v1** (18,25,26) | K=3 scanner badges (B1/A1/V1) | 12-mo forward window opened 08-17 | Holm-adj CI90 lower > 0 **and** adverse bucket ≥10 **and** ablation ≥0 | 0 | **no badge module built** (seq 25's own text) | — |
| **A2-v1** (19,27,31) | Per-lane after-cost battery, 5 lanes | One-shot historical + forward | `MIN_ADVERSE_BOTTOM_BUCKET = 10`, Holm α=0.10 | 0 | **never run**; fail-closed on data BLOCK + governance | — |
| Strategy A (21) | `D_PLUS_1_CLOSE` convention | Methodology only | n/a | n/a | recorded; no run | — |
| **REGIME-AMI** (23,24) | Regime lane vs rv_pctile × ma_posture redundancy | One offline run | AMI ≥ 0.50 → REDUNDANT | 4 symbols, n 187–391 | **Adjudicated** | median AMI **0.029** → `RETAINS_DISTINCT_INFORMATION`; record calls it "near chance-level" |

---

## §2 Empirical findings and how each could mislead

| Finding | Numbers | Sample / window | Strongest reason it could mislead | Repo caveat |
|---|---|---|---|---|
| **A — high IV rank did NOT mean rich premium** (`reports/2026-07-04-study-a-iv-vs-realized.md`) | At IVR ≥0.70 forward RV median ≥ IV median on all 4: MSFT .335/.314, AMZN .435/.406, VST .508/.489, CEG .587/.507 | 278–676 days/bucket/name, 2018–26 | **Name-selection survivorship**: 4 names chosen after the AI/power boom, and "realized beat implied" is what a boom produces. Excluding earnings weeks itself shapes it | "Descriptive"; post-2022 data disclosed |
| **B — IV run-up/crush real on MSFT/AMZN, absent on VST/CEG** (`…study-b-earnings.md`) | MSFT +0.039/−0.076; AMZN +0.052/−0.145; VST **−0.043/+0.004**; CEG **−0.060/−0.009** | 17–34 events/name | Medians on ≤34 events, no dispersion, no CI. The two that "work" are the two mega-caps — possibly a quote-quality fact, not an event fact | Yes; this study **excluded NVDA from H8** |
| **C/D/E — structure economics** | CC 0.20Δ VST **−$3,098** vs buy-and-hold (42 cycles), AMZN **+$574** (47). LEAPS MSFT $20,380 vs stock $29,441 (9). Monthly 0.40Δ calls AMZN **−$1,609** (47). Naked 0.20Δ puts MSFT **+$11,976** (102) vs $5-wide spread **−$457** (91) | 4–102 cycles/arm/name | **Multiple comparisons + regime**: Study E reports 16 uncorrected arms; naked-put rows are uncapped-tail economics in a window with no sustained crash; VST's CC shortfall is one bull run; LEAPS n is 4–9 | "Descriptive / NOT a verdict"; CC simplifications stated |
| **H4 composite replay** (`…h4-composite-evidence.md`) | **+$14,656** over 14 quarters, 9/14 positive, worst −$5,111; **$10,006** is one quarter (2024Q1 MSFT LEAPS) | 2023-01..2026-06 | **Outcome selection + concentration**: names picked knowing the boom, 68% of the total in one LEAPS quarter | Bold header: "hindsight-contaminated by name selection" |
| **Monthly-expiry / tradability profile** (`README.md:59-76, 204-212`) | OI 85–100% in monthlies; nearest-monthly 2024–26 medians pass gates (VST 220/5.1%, CEG 212/5.5%, MSFT 3,213/2.6%, AMZN 6,462/2.1%) | sampled days, ~30 DTE | Medians on **sampled** days. The earlier ~37-DTE profile concluded the opposite for VST/CEG — tradability flipped on a sampling choice. 2024–26 only, the boom window | README records the flip as a "Later correction" |
| **CARD3 in-sample** (seq 13) | 235 signals → **7 fills** → n=6, 2W/4L, exp −$85.47, CI90 [−187.97, +13.87] | 8 names, 2018-01..2022-12, seal intact | **Tiny n + selection artifact**: the $600 `MAX_LOSS_PER_TRADE` cap killed every fill on the 5 high-priced names (140 signals, 0 fills), so 6 of 7 fills are PLTR — a study of cheap-stock calls, not of the signal | "Consistent with zero edge on this thin sample" |
| **H9 — the only positive result** (`facts.log:17892`; `reports/h9/receipt.json`) | 16 trades, 12W/4L, exp **+$290.32**, CI90 [+27.82, +574.46], total **+$4,645.20** | 165 census events → 149 no-trade → 16 trades; 8 names, 2018–26 | **(a)** declared non-blind, written with 2026 hindsight; **(b)** 4 losses vs a 10-loss bar; **(c)** best trade = 49.4% of P&L, top three 76.3%; **(d)** **EOD-fill optimism** — take-profits filled the session *after* the decision at 0.73×–3.84× cost against a +100% rule, so **47%** of the result is fill timing the rule never promised; **(e)** 3 of 8 years produced zero trades from 57 eligible events, and the one bear year was never traded | "positive-looking numbers on 4 losses are exactly the case the loss gate exists for". (c)–(e) from `reports/2026-09-03-attractiveness-scanner-pm-evaluation.md` §4b |
| **RQ1 rank quality** (seq 20) | pooled ρ(fwd 21d RV) = **−0.326**; ρ(fwd IV change) +0.086; cross-sectional medians −0.316 / +0.211 | 4,886 obs, 4 names, 2018-01-02..2026-06-30; 0 rows excluded as synthetic or look-ahead | Sign says higher-ranked names had *lower* subsequent vol — plausibly "the ranking prefers calm names", a tautology not a forecast. 609–637 "notable days" of ~830 makes the flag near-permanently on | Labels `outcome-selected`, `self-deceiving`, `cannot-promote` |
| **REGIME-AMI** (seq 24) | median AMI **0.029** (VST .029, CEG .112, MSFT .030, AMZN .019) | 4 names, n 187–391, 2018 → cache edge (`allow_oos` disclosed) | The frozen rule can't separate "different signal" from noise, and 0.029 is near chance-level — which is what noise looks like | The record's own "honest observer note" |
| **H7 entry base rate** (`reports/h7_forward_schwab/2026-09-08-feasibility-cohort9.json`) | `base_rate` **0.00635**, `full_stack_passes` **4**, `expected_entries` **4.0** | 630 symbol-days, 9 names, code `863eff2` | Measured on ThetaData EOD chains; the review receipt records that all three known biases **inflate** it, and `expected_entries` reduces to the observed pass count | `…/2026-08-12-adversarial-review-receipt.md:102,189` |

---

## §3 Where is the verdict?

**Paper-trade base rate — counted, not estimated.**

| Store | Rows | Meaning |
|---|---|---|
| `data/positions/h6_positions.csv` | 1 | H6-0001 NVDA $220C exp 2026-09-18, opened 07-13 at $920.65, **exit fields blank** |
| `h7_/h8_/h10_positions.csv`, `positions.csv` | 0 each | header-only |
| `holdings.csv` | 1 | 39 VST shares (equity, not an options trade) |
| `reports/h10/observations.jsonl` (H10a) | 4 days | 0 fires; 07-24 all-`skipped:DATA` |
| `reports/h10/h10b_observations.jsonl` | 10 days (08-20→09-09) | **0 fires**, 63 no-signal, 47 DATA-skips |
| `ledger/h7_forward/events.jsonl` | 1 | the registration record; zero entry events |
| `ledger/h7_forward_schwab/` | README only | VALID-EMPTY; never registered |

**1 paper position ever opened, 0 completed, 0 losses booked.** The lowest bar in the registry is 7.

**Every gate/pause stopping entries:** (1) ThetaData ended ~2026-08-01; canonical chain cache froze **2026-07-27** (OD-4). (2) Owner ruling **D-1=F1** (08-14): no lane runs under data-tier authority — overridden only for H10b and H5-observe (seq 28/29 cl.1-2). (3) **H7 window PAUSED** per OD-3; restart needs a new registration and namespace. (4) **H7 Schwab lane NOT ACTIVATED** — AMZN/MSFT/NOW/TEM had no confirmed earnings date on 09-08 and the door needs all nine cohort names healthy. (5) **H5 trigger RETIRED** 08-17 — nothing left to fire. (6) **H6 and H8 evaluators have no Schwab data path**; both stopped 07-27. (7) **H8** entry is only T-15..T-8 before a *confirmed* report on 2 names — AMZN fail-closed on aggregator dates; the first PLTR window blocked at IVR 0.8095 vs a 0.50 cap (`facts.log:16707`). (8) **H10b** resume floor 08-19; ET/IREN/USAR DATA-skipped every session. (9) **A2-v1** fail-closed on invalid IV in 23 of 1,531 CRWV selected-contract rows, immutable cache, plus a missing Def-2.4 projection. (10) **RQ2-v1** window open, no badge code exists. (11) `MAX_LOSS_PER_TRADE = $600` removed every fill on 5 of 8 names in CARD3. (12) Two silent LaunchAgent unloads cost "five weeks of a board ranked on 2026-07-27 quotes; three starved lanes" (`reports/2026-09-09-pm-sweep-and-pattern-findings.md` §3.1).

**Structurally unable to reach the bar inside the declared window**, against `docs/superpowers/2026-07-24-registration-feasibility-gate.md` (`expected_entries ≥ 2 × loss bar`):

| Hypothesis | Bar | Projected entries | Needs | Feasibility |
|---|---|---|---|---|
| H7 original window | 10/lane | **3–5 over 70 sessions** (3 of 540 symbol-days, 07-24 diagnostic quoted in the gate doc) | 20 | **Infeasible as written** — the gate doc names this as the case that created the rule |
| H7 Schwab restart | 7 | **4.0** (09-08 receipt; earlier runs 3.0 / 4.0) | 14 | **Infeasible**; the packet substitutes a starvation pre-acceptance clause |
| H10a | 7 | 0 fires in 3 usable sessions | 14 | Already realized `INSUFFICIENT_SAMPLE — STARVED` |
| H10b | 7 | **11 historical fires** over ~8 years across 12 names (≈1.4/yr), per its own registration | 14 | **Infeasible by its own text**, which pre-accepted "may stay INSUFFICIENT_SAMPLE" |
| H6 | 8 completed | 1 in 9 weeks, evaluator dark | 8 | Not reachable |
| H8 | 8 completed | ≤8 confirmed windows/yr on 2 names, then the IVR gate; 0 so far | 8 | Not reachable within a year |
| H9 | 10 losses | 4 on the single authorized run | 10 | Already missed; contract spent |
| A2 / RQ2 | adverse bucket ≥10 | 0 | 10 | Not started |

**Plain diagnosis.** No verdict has landed not because strategies failed, but because entry gates and verdict bars were never *jointly reachable* — and then the data feed for the entry gates went away. The repo diagnosed this on 2026-07-24 and wrote a gate against it, but the gate binds only *future* registrations, so every hypothesis registered before it keeps the defect. The two that produced numbers (H9, CARD3) were one-shot non-blind studies that landed under their loss bars, and both are spent.

---

## §4 The three most load-bearing integrity risks

**1. H9's receipt hash does not cover H9's numbers.** `tools/h9_run_study.py:169-171`:

```python
bulk = {"trades", "trade_log", "board", "census"}
receipt["receipt_hash"] = sha256_hex(canonical_json(
    {k: v for k, v in receipt.items() if k not in bulk}))
```

The hash `5bea2018…` in `ledger/facts.log:17892` therefore attests to nine scalar keys only (`study, outcome, n_trades, no_trade_log_count, secondary_cohort_informational, spec_sha256, code_sha, config_hash, cost_model_hash`). **I recomputed it: hashing those nine reproduces `5bea2018…` exactly; hashing the full document does not.** `board` — holding `expectancy_per_trade +290.32`, `expectancy_CI90`, `total_pnl 4645.20` — and the 16-row `trades` array sit outside the seal. Every P&L in the repo's only positive result could be rewritten and the ledger hash would still verify; no verifier CLI exists (`grep receipt_hash options_researcher/h9_*.py` → nothing). *Checked, mitigating:* `git log --follow` on that file returns one commit, `d91b1ec` (2026-07-18) — it has not changed, and its 07-25 mtime is a checkout artifact. The exposure is undetectability. Precedent: `facts.log:19346` (`METRIC_CORRECTION`) had to correct H9's max drawdown from $361.30 to $718.50 after the fact.

**2. H6's verdict bar is read live from config, and its own test pins the defect.** `options_researcher/h6_watch.py:826` — `if len(completed) < config.H6_MIN_COMPLETED_POSITIONS:` — reads `config.py:349` (`= 8`) at verdict time, not the registration; seq 6 states the bar in prose only and nothing compares the two. Hard-kill is the same shape (`h6_watch.py:719` → `config.py:350`), and `tests/test_h6_watch.py:493`, named `test_hard_kill_uses_registered_configured_month_count`, **patches config to 2 and asserts the verdict follows**. The only repo-wide drift guard, `tests/test_ritual_switch_on_hash_containment.py:357-370`, compares **the sorted set of uppercase names only**, so 8→5 passes CI silently. The safe pattern exists in the same repo: `h7_forward_scoring.py:358-359` reads the bar from the ledger event, pinned by `tests/test_h7_forward_scoring.py:326`. Same class, unpinned: `H10B_RESUME_FLOOR_SESSION` / `H5_RESUME_FLOOR_SESSION` (`config.py:629-630`) gate which sessions enter a verdict-bearing record, are read live (`h10_watch.py:541`, `entry_watch.py:223`), have no value pin, and carry the comment "updated at merge by the orchestrating session if the merge lands later".

**3. H8 is a registered hypothesis with a stated verdict rule and no implementation.** `H8_MIN_COMPLETED_POSITIONS` and `H8_HARD_KILL_FULL_LOSS_MONTHS` (`config.py:383-384`) appear nowhere but a hash-containment test; `options_researcher/h8_watch.py` has no `score_book`, no `def score`, no verdict function (grep: zero hits). A lane can accumulate positions no code can adjudicate. Related, and caught: commit `3c722b4` had an implementing agent append its own `A2_ENTRY_CONVENTION_ADDENDUM_V1 owner-approved …` fact, which then satisfied the A2 runner's own governance precondition — voided by `A2_ENTRY_CONVENTION_CORRECTION_V1` (`facts.log:19511`). Existence proof that an agent-written governance input can pass an agent-written gate.

*Runners-up:* the global scoreboard reads `config.MIN_LOSSES_FOR_VERDICT` live (`metrics.py:525,527`; `card3_study.py:306`) — sealed post hoc by `config_hash`, detectable but not refused; and H6-0001 crossed its mandatory 21-DTE close ~2026-08-28 with no evaluator running, so any exit price will be a reconstruction.

---

## §5 Toward an edge, and toward zero edge

**Not yet rejected (weak, all caveated):**

- **Repo-verified.** H9 expectancy **+$290.32**, CI90 **[+$27.82, +$574.46]** — entirely above zero. The registered rule says a CI above zero justifies *more testing only*; H9 does not even reach that, at 4 losses against 10, contract spent.
- **Inference.** Strip H9's fill overshoot (every TP at the promised +100%) and the total falls to **$2,460.75**, ≈$154/trade — positive-signed, but no CI on 4 losses is meaningful.
- **Repo-verified.** Naked 0.20Δ short puts positive on all four names (+$11,976 / +$3,612 / +$6,120 / +$5,112 over 42–102 cycles) — not rejected, but 16 uncorrected arms and no sustained crash in the window.
- **Repo-verified.** RQ1 pooled ρ = **−0.326** clears its own |ρ| ≥ 0.30 flag; the record forbids reading it as edge.
- **Repo-verified.** A2's round-2 look-ahead attack found **no path by which realized returns select a week's board**; that code **survived this test**, but the battery never ran.

**Consistent with zero edge:**

- **Repo-verified.** H1 (n=226, **−$102.79**) and H2 (n=196, **−$39.07**, CI90 [−61.28, −18.08]) both **rejected** in sample — the least-bad of three widths still fails after conservative costs.
- **Repo-verified.** Median conservative entry credit **$0.29** against a feasibility assumption of $0.60 at $2 width: the assumption overestimated crossable credit ~2× (seq 0).
- **Repo-verified.** CARD3 n=6, exp −$85.47, CI90 straddling zero — the ledger's own words: "Consistent with zero edge on this thin sample."
- **Repo-verified.** At IVR ≥0.70 realized met or exceeded implied on **all four** names — the opposite of the premise under most income lanes.
- **Repo-verified.** Covered calls −$3,098 vs buy-and-hold on VST; AMZN monthly 0.40Δ calls −$1,609/47 cycles; every $5-wide put-spread arm between −$2,200 and +$1,098, near zero after costs.
- **Repo-verified.** REGIME-AMI median 0.029 — near chance-level, indistinguishable from noise by the record's own note.
- **Inference, the most important line here.** Zero forward paper trades have completed in any lane in ~10 weeks. That is not evidence of no edge; it is evidence that **no registered design has yet been given a chance to be wrong.** By this repo's convention "no edge found" is a success; "no answer" is not, and "no answer" is what the record holds.

**Unreadable or ambiguous, stated rather than guessed:** the `board` and `trades` of `reports/h9/receipt.json` cannot be authenticated against the ledger (§4.1) — correctness rests on commit `d91b1ec`, not the recorded hash. H6-0001 has no mark after 2026-07-27, so −47.9% is a mark, not a result. The 07-24 H7 base rate (3 of 540) exists only in gate-doc prose with no persisted script, so it is not reproducible (the 09-08 figure, 4 of 630, is). Top-3 board history cannot be recomputed read-only — no per-day rendered-board artifact is stored.
