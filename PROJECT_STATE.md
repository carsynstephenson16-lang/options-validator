# PROJECT_STATE — options-validator

**As of:** 2026-07-23 (evening). **Branch:** `docs/replan-2026-07-22` @ `df2957e`.
Paste this file at the top of the next session instead of re-explaining.
Update it whenever a registration, verdict, or data decision lands.

## What this project is (one breath)

Research-only options validator. Never places orders. "No edge after costs"
is a success. Every verdict-bearing test is pre-registered on the hash-chained
ledger, frozen first, run once; verdicts gate on LOSSES. Codex implements from
briefs; Claude orchestrates; the owner types every frozen number.

## Live hypotheses and clocks

- **H7** forward window LIVE (seq-0, scores once ~2026-10-26); exit/scoring
  recorders being built (replan R1–R2). **H10a/b** registered (backstops
  2026-10-06 / 2027-01-06) — capture path being built (R3). **H5** triggers
  2/3 met, watch manual (R4 wires it). **H6/H8** sample-gated forward books.
- **RQ1** (seq 17): RUN 2026-07-23, one-run spent (result = ledger seq 20;
  receipt `reports/rq1/rq1-v1.json`). Pooled Spearman rho −0.326 vs forward
  21-session realized vol (notable, descriptive-only) and +0.086 vs forward
  IV change (not notable); 4,886 usable name-days, MSFT/AMZN/VST/CEG. NO
  VERDICT, no promotion. Residue EX3a open: causal-reconstruction property
  test was never built (2026-07-23 review) — verify-the-method only; never
  rerun the study.
- **RQ2-v1** (seq 18) + **A2-v1** (seq 19): owner-typed freezes 2026-07-23 —
  corner badge 75/25 earnings-GATED (near 15–45 / long 60–120 DTE); bounce
  lens −20% / mom>0 / RV≥70th with mandatory negative-priors text; five CSP
  exit arms incl. 50%-capture and 21-DTE; Holm α=0.10 (Romano–Wolf switch at
  K≈10–12); adverse gate 10; 12-month backstop. UNRUN; §13.1b pins closed
  2026-07-23 via ledger fact `RQ2_A2_PIN_ADDENDUM_V1` (10 sessions / terciles
  / one-sided / report strictly inside near-leg life).
- Spent forever: H1/H2, H9, Card 3, QM study. H7 historical diagnostic
  permanently withdrawn. Sealed SPY/QQQ holdout: reveal budget 0/3.

## The 12-month program (2026-07-23 → 2027-07-23)

Master doc: `docs/superpowers/plans/2026-07-23-twelve-month-scanner-research-program.md`
(26-row audit-resolution table, workstreams A–H, calendar, corrected math).
Detail: `...-workstreams-b-d-detail.md` (19 defined-risk opportunity cards +
earnings variance decomposition). Build order:
`docs/superpowers/plans/2026-07-23-codex-execution-queue.md` (EX0–EX10) —
**handed to Codex 2026-07-23.**

- EX1 wording-honesty fixes + EX2 recorders: no dependencies, in flight.
- EX3 RQ1 runner: build → adversarial review → run ONCE.
- EX4/EX5 badges, EX6 expectation lines, EX7 concentration panel:
  display-only, byte-identical-ordering test pins mandatory.
- EX8 A2 runner + RQ2 scoring: **unblocked 2026-07-23 — pin addendum typed
  (`RQ2_A2_PIN_ADDENDUM_V1`).**
- EX9 earnings-variance machinery: **CALENDAR-URGENT — August prints start
  ~2 weeks out; missed events are unrecoverable by construction.**

## Data state

- Chains: EOD ThetaData through 2026-07-21; 15-name universe (+legacy).
  **Subscription confirmed only to 2026-11-30 — extension decision ~10-01 is
  the program's existential risk.**
- NEW 2026-07-23, all loader-verified: `data/rates/treasury_cmt.csv`
  (forward-serving capture provenance; daily append step joins the ritual at
  R5); `data/rates/expected_dividends.csv` (15/15 SEC/IR-sourced; owner
  spot-check 6/6 MATCH — `reports/2026-07-23-dividend-payer-spot-check.md`;
  NVDA now $1.00/yr after a 25× raise); QQQ+SPY closes+OHLCV 2017→2026-07-22
  (sanctioned Yahoo path).
- Index option chains: NOT funded (owner decision 2026-07-23) — implied-vol
  dispersion parked; realized-vol/beta/concentration proceed on closes.
- Alpha Vantage full-history closes now paywalled — Yahoo path is the
  sanctioned fallback. The isolated LSE feed probe was retired 2026-07-23
  after its measured payload failed quote, liquidity, staleness, and
  point-in-time-history requirements; audit:
  `reports/2026-07-23-lse-feed-assessment.md`.

## Standing rules that bite

- Scanner GREEN recipe FROZEN for RQ1; all changes addition-only display
  badges; nothing new may grade, rank, or trigger without its registration.
- Ledger append-only via typed APIs; never hand-edit; K (versions tried) is
  the multiple-testing denominator and must be surfaced.
- Plain language to Carsyn always; label claims (Repo-verified / Official /
  Inference / Assumption); banned words: proven, confirmed, works, edge
  found, guaranteed.
- Concurrent sessions share this checkout — re-check `git log` before
  trusting a "clean" assumption.

## Next session, start here

1. Pin addendum is DONE (fact `RQ2_A2_PIN_ADDENDUM_V1`) — EX8 is unblocked;
   check Codex progress on EX4–EX9.
2. Check Codex progress against the EX queue acceptance criteria; review
   diffs adversarially (esp. the byte-identical ordering pins).
3. ThetaData extension decision countdown (~2026-10-01).
4. First weekly aggressive-vol report is due once EX-card builds land;
   August earnings capture (EX9) is the calendar-critical path.
