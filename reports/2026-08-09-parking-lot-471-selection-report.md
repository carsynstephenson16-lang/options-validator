# Parking-lot line-471 adjudication and experiment-portfolio selection (2026-08-09)

**Orchestrator:** Claude Fable 5. **Research workers:** Claude Sonnet 5 (six
Wave-1 agents, four Wave-2 specialist reviewers, three Wave-3 fresh-context
auditors). **Implementation:** Codex (gpt-5.6-sol, medium reasoning) from the
briefs under `docs/superpowers/plans/` — no strategy code was written by
Claude sessions, per the standing division of labor.

## 1. Source boundary and baseline

- Source file: `ideas-parking-lot.md`, sha256
  `528c821c159ffec6ed7f7260f60e53b0ab795217219d98b2e92455df6d1703c7`,
  1,204 lines, captured before any edit.
- Physical boundary: line 471 (falls mid-table inside the section
  "## UNH / CRWD / ZS / NBIS — measured chains + H7 story scan", whose
  heading is line 418; that section is included in full and flagged as
  starting pre-boundary).
- Repo baseline: worktree branch `claude/ideas-parking-lot-review-762348`,
  HEAD `1866f59f5d9c976363315878072a1e17165a385a`, clean tree. Full offline
  unittest suite exit 0; `ruff check .` clean; `pyright` 0 errors;
  `git diff --check` clean; `uv run python -m options_researcher.attractiveness_dashboard`
  builds `.tmp/dashboard/attractiveness.html` (631,807 bytes) with all
  expected sections.
- Codex execution surface: NOT available on this machine (`which codex` →
  not found). Everything below is therefore research + specification +
  copy-ready handoff; **no experiment code is implemented**.

## 2. Coverage of line 471 → EOF (zero unclassified)

17 level-2 blocks intersect [471, 1204] (six consecutive `##` headings at
lines 741–871 are one pasted external study design and are counted as one
block). Normalized inventory: **48 distinct ideas** (12 in lines 418–740,
14 survey-parked bullets in 741–964 plus 1 external-study block, 21 in
965–1204). Classification counts:

| classification | count |
|---|---|
| scoring candidates for this program | 9 |
| rejected / do-not-build (incl. explicit reject lists) | 12 |
| owner-action (owner decision/registration/data-sourcing required first) | 6 |
| already implemented (OI v1, Wasserstein/REGIME-AMI, PyArrow, 25Δ risk-reversal†) | 4 |
| shared infrastructure / research-only / partial implementation | 8 |
| maintenance cleanup | 5 |
| data-blocked | 2 |
| duplicate / superseded by registered or planned surface | 2 |
| unclassified | **0** |

† The 25Δ risk-reversal line (parked 2026-07-22, survey rank 19) was
quietly implemented 2026-08-04 inside `composite_signals.internals_angle`
(`skew_25d` + `skew_pctl` + `steep_skew`) under the composite-lane
authorization, without an un-park entry. Recorded as a dispositions
correction in the parking lot's 2026-08-09 dispositions section.

Full machine-readable inventory: `reports/2026-08-09-parking-lot-471-idea-ledger.json`.
(The table above is a coarser narrative rollup of the JSON's finer
`category` field — e.g. non-candidate experiment-category ideas whose own
gates make them owner-gated or duplicative are rolled into those buckets,
and the one "implementation-ready refactor" is rolled into owner-action —
it is not a literal `groupby(category)`; both tallies sum to 48.)
Working store: SQLite (`.tmp/research/parking-lot-471/ledger.sqlite`) —
chosen because 48 normalized ideas exceeds the 30-idea JSONL threshold;
Fable was the only writer; agents returned JSON.

## 3. Stale claims corrected by measurement (Wave 1)

1. "No QQQ/SPY closes exist" (parking lot line 901; survey) — FALSE now:
   `QQQ.parquet`/`SPY.parquet` exist, 2,408 rows each, 2017-01-03 →
   2026-08-03.
2. "`data/rates/` does not exist" (line 919) — FALSE now: treasury CMT
   (official Treasury source, 140 observation dates) + expected dividends
   (all 15 board names) exist since 2026-08-04; both resolve through the
   fail-closed `data/rates.py` loaders at observation date 2026-07-27.
3. Wasserstein entry (line 1113) says "Awaiting one run" — stale: the
   REGIME-AMI-v1 run completed 2026-08-03 (receipt
   `reports/regime/2026-08-03-regime-ami-v1-receipt.md`, decision
   RETAINS_DISTINCT_INFORMATION, median AMI 0.0295 vs 0.50 threshold) and
   the regime module is wired into the shipped composite lane.
4. `wiki/decisions.md` lists a "skew" badge among the five RQ2 briefs —
   wrong; the five are B1/A1/C1/N3-1/V1 (bounce lens, not skew).
5. Drift finding: of the 2026-07-23 "salvaged, not parked" Integrity
   Hardening Batch v1, only `block_live_trading` exists; the
   hook-registration doctor, frozen-values drift check, parking-lot
   section-preservation check, and robustness netguard were never built.

## 4. Registry facts that bound the selection

- `ledger/experiments.jsonl` seq 18 (**RQ2-v1**): K=2 frozen badges —
  Badge B (term-structure/VRP corner) and Badge A (bounce lens); forward
  window opens 2026-09-01; **badge modules not built**. Nothing in this
  program may build, alter, or duplicate them.
- seq 19 (**A2-v1**): after-cost outcome battery on the frozen
  GREEN-fraction ranking; not built; untouched here.
- **Discrepancy surfaced for the owner (not resolved):** the RQ2 briefs
  doc's delegated-values table says K=3 including V1 (VRP calibration);
  the chained registration says K=2 and omits V1. Owner adjudication
  needed before anyone treats V1 as registered.
- The frozen GREEN-fraction recipe (RQ1) is this program's baseline lane
  and is untouched while experiment flags are off.
- EOD chain cache is permanently frozen at 2026-07-27 (OD-2/OD-4);
  closes reach 2026-08-04. Every experiment stamps its own honest max
  as-of; chain-based and closes-based experiments differ by a week and
  must not share one stamp.

## 5. Scoring (Wave 2: four independent Sonnet reviewers)

Four reviewers (quantitative methods, engineering/architecture,
dashboard/operator value, portfolio composition) scored all nine viable
candidates against the frozen rubric (sturdy ≥75, preferred ≥80).
Full per-component detail: `reports/2026-08-09-parking-lot-471-scorecard.csv`
and the Wave-2 transcripts under `.tmp/research/parking-lot-471/`.

| cand | idea (survey rank) | quant | eng | dash | port | mean | outcome |
|---|---|---|---|---|---|---|---|
| C4 | Beta-to-QQQ translation line (15) | 87 | 84 | 88 | 86 | **86.3** | SELECTED #1 |
| C1 | Tail-shape line (7) | 77 | 85 | 86 | 90 | **84.5** | SELECTED #2 |
| C3 | Spread-stability annotation (12) | 71 | 87 | 88 | 79 | **81.3** | SELECTED #3 |
| C2 | T-bill carry + assignment stub (6) | 77 | 69 | 79 | 89 | **78.5** | SELECTED #4 |
| C7 | Taylor 1-day attribution (13) | 71 | 76 | 77 | 77 | 75.3 | close finalist — not selected |
| C5 | Vol-of-vol (8) | 73 | 77 | 69 | 77 | 74.0 | close finalist — not selected |
| C9 | Rank-stability replay (11 re-scoped) | 74 | 61 | 67 | 79 | 70.3 | close finalist — not selected |
| C6 | CVaR 5% CSP lane (16) | 36 | 73 | 68 | 62 | 59.8 | rejected |
| C8 | OU half-life of IV (14) | 33 | 41 | 39 | 58 | 42.8 | rejected |

Disagreements were reconciled on evidence, not votes:

- **C3 (quant 71 vs eng/dash 87/88):** quant's two defects — contract
  identity across expiry rolls and same-day baseline contamination — have
  concrete fixes (role-based near-tenor 0.50Δ series matching the
  composite precedent; baseline strictly [t−20, t−1]). Both fixes are
  mandated in the brief as acceptance criteria, which resolves the
  objection by construction.
- **C2 (eng 69):** engineering's discount priced the dead half (the
  ex-div-date flag). The selection rescopes C2: the T-bill collateral
  comparison is the evaluable core; the early-assignment flag ships as a
  permanent fail-closed `EX_DIV_DATE_UNAVAILABLE` state with the owner
  data-unlock surfaced. On the rescoped shape, three of four reviewers
  score ≥77.
- **C9 (port 79 vs others):** engineering's hidden-state-leak analysis
  (a naive replay of `assemble()` reads today's positions/ledger state)
  and the 600–820 LOC estimate are verified concrete risks the portfolio
  reviewer had not priced. Consensus below bar; not selected.

## 6. Selected portfolio (4)

Count rationale: exactly four candidates clear every sturdy gate. The
fifth-best (C7 at 75.3) clears the raw number but fails "never pad": all
four reviewers scored its scanner decision value 6–8/20 (it explains
yesterday, it doesn't inform today). C5 and C9 sit below 75. So the
default count of four stands; no fifth is taken.

1. **EXP-BETA — Beta-to-QQQ translation line** (86.3, survey rank 15).
   Rolling 252-session beta (Cov/Var) of each name vs QQQ with R²,
   126-obs floor, and a dollar-translation line for open positions.
   Selected because it is the only candidate on the factor-exposure axis —
   the standing "the whole book is ONE AI factor" concern — and its only
   historical blocker (no QQQ closes) is measurably gone.
2. **EXP-TAIL — Tail-shape line** (84.5, rank 7, "strongest of the parked
   set"). Rolling 252d realized skewness, excess kurtosis, jump-count with
   a causal jump sigma (trailing σ up to t−1 — fixes the survey formula's
   self-referential sigma) and a ≥250-obs NaN gate. Selected because tail
   shape is exactly where loss-gated verdicts say the information lives,
   and nothing on the board shows it (cushion is level-only).
3. **EXP-SPREAD — Spread-stability annotation** (81.3, rank 12). Today's
   relative spread of the role-based near-tenor 0.50Δ contract vs its own
   trailing [t−20, t−1] median, earnings weeks excluded from the baseline.
   Selected as the only execution-cost-dynamics candidate: the existing
   liquidity gate is a static pass/fail; "wide today vs always wide" is
   the missing operator fact at entry time.
4. **EXP-TBILL — CSP/CC carry vs T-bill + assignment-mechanics stub**
   (78.5, rank 6 — the survey's own "top of the unlock queue"). Annualized
   credit yield vs Treasury collateral yield from the fail-closed
   `data/rates.py` loaders (OCC-official mechanics); the early-assignment
   flag renders an honest permanent `EX_DIV_DATE_UNAVAILABLE` refusal
   until the owner sources a forward ex-dividend date calendar.

Axis coverage: factor exposure / realized-tail shape / execution cost /
carry-and-mechanics — four distinct information sources; none re-tiles the
composite board's four angles (trend, vol-premium level, regime,
OI-skew-liquidity internals) and none touches RQ2-v1's two frozen badges.

## 7. Full-document fallback (triggered, resolved: no displacement)

Trigger: the fourth-ranked selection scores 78.5 < 80. The entire file
(lines 1–470) was therefore reviewed against the same rules. Result: every
pre-471 idea is already promoted (event-edge), already registered or
planned surface (term-structure → RQ2 Badge B seq 18; market-implied
probability readout → N3-1 brief), data-blocked (VIXEQ badges — no
index-vol feed), owner-gated (drawdown-reversal entry, non-AI names,
bridge plugs, TradingView), measured-rejected (IBEX, microcaps), or done
(AVGO SPLITS). No pre-471 idea displaces C2; **no fallback selection was
made** and the portfolio remains all post-line-471.

## 8. Rejected close finalists (why not)

- **C7 Taylor attribution:** unanimous lowest decision value (6–8/20);
  educational, not decision-bearing; cheapest future add if wanted after
  the deferred typed-Card refactor.
- **C5 Vol-of-vol:** adjacent to composite Angle 2 (same `atm_iv_near`
  series, level vs instability); dashboard reviewer judged the
  beginner-confusion cost real; quant found the survey's Goyal–Saretto
  citation does not match the stdev(Δatm_iv) formula (their construct is
  (IV−RV)/RV) — the citation must be re-verified before any future build.
  Natural future shape: an explicit level-vs-instability combination study
  against Angle 2.
- **C9 Rank-stability replay:** honest re-scope of an infeasible parked
  idea (zero days of persisted board history), but the safe design is the
  program's largest build with a hidden-state-leak red test and permanent
  mislabeling risk ("reads like a track record"). The forward append-only
  daily board log may be proposed separately later; it accumulates value
  regardless.

## 9. Conflicts and open items surfaced to the owner

1. RQ2-v1 K=2 (ledger) vs K=3 (briefs doc) — owner adjudication needed.
2. Session-start anomaly: the harness snapshot at session start showed
   `M .cursorrules`, `M AGENTS.md`, and an untracked
   `reports/2026-08-09-attractiveness-experiment-authorization.md` (a
   prior/concurrent session apparently began this same program), but at
   measurement time neither the main checkout nor this worktree carried
   those changes. The only live copies are this branch's. If a stash or
   concurrent session resurfaces the earlier copies, keep exactly one.
3. 4/5 "salvaged" integrity-hardening items never built (§3.5).
4. `wiki/decisions.md` "skew badge" claim is wrong (§3.4); wiki fix
   deferred to a follow-up rather than half-following the vault procedure
   mid-program.
5. Rates staleness (measured, corrected in audit): the Treasury CMT
   curve's `valid_through` maxes at 2026-07-27 — co-terminous with the
   chain freeze, so the T-bill experiment resolves exactly at the frozen
   edge and fail-closes after it. Dividend rows expire per name between
   2026-07-31 (ET) and 2026-10-26 (9 names); ET/CEG/VST/NVDA/AVGO/MSFT
   expire soonest. Refreshing the two CSVs is an owner data action
   (provider policy applies).

## 10. Limitations

- Chain-based experiments (EXP-SPREAD, half of EXP-TBILL) are capped at
  the frozen 2026-07-27 chain edge until a future provider decision;
  closes-based experiments (EXP-BETA, EXP-TAIL) reach 2026-08-04.
- All display constants are LLM-proposed conventions with provenance
  labels; none is owner-ratified; promotion into any grading/ranking
  requires the 2026-07-24 feasibility gate and an owner decision.
- Wave-2 strike-density spot-checks (wings, strips) were on VST only and
  extrapolated to the board (same EOD builder); flagged, not hidden.
- Selection effect (K-counting): the four selections were chosen from 9
  scored candidates out of a 48-idea inventory. Any future registered
  study built on their numbers must disclose that selection history in
  its multiple-testing accounting (also recorded in the design spec §10).
- Nothing in this report claims any selected experiment has an edge,
  predicts returns, or grades candidates. All four are descriptive.

## Addendum 2026-08-10 — K discrepancy resolved; seq-18 date attribution corrected

*Appended 2026-08-10; the original text above is unchanged (dated report,
append-only).*

- **K discrepancy RESOLVED** (§4 bullet and open item §9.1): ledger seq 25
  (`RQ2_AMENDMENT_V1_1`, 2026-08-10, owner-directed) adjudicates RQ2-v1 to
  **K=3 candidate badges — B1, A1, V1** — with V1 registered as
  **membership-only** (its candidate statistic is NOT pinned; the RQ2 runner
  must refuse any V1 comparison until a further pre-result append-only
  amendment pins it). Read seq 25 in `ledger/experiments.jsonl` before
  treating V1 as anything more than a registered member.
- **Attribution correction.** §4 attributes "forward window opens 2026-09-01"
  to ledger seq 18, but seq 18 contains no start date. That date comes from
  the LLM-proposed delegated-values table in
  `docs/superpowers/plans/2026-07-22-rq2-scanner-enrichment-briefs.md`
  ("RQ2 forward window | Start 2026-09-01; backstop 2027-09-01"), not from the
  chained registration.
