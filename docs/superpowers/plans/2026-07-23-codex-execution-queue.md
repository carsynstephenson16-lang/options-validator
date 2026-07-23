# Codex execution queue — post-registration build order (2026-07-23)

**Authority:** replan (owner-approved 2026-07-22, Codex implements from
briefs); RQ2-v1 = ledger seq 18; A2-v1 = ledger seq 19; RQ1 = seq 17 (N4
resolved to (a)). Program frame:
`docs/superpowers/plans/2026-07-23-twelve-month-scanner-research-program.md`;
detailed specs in `2026-07-22-rq2-scanner-enrichment-briefs.md` and
`2026-07-23-workstreams-b-d-detail.md`.

**Global rules for every item (non-negotiable):**
- Test-first, offline unittest against the local cache; ruff + pyright clean;
  every constant into `config.py`; no network in tests.
- The frozen GREEN recipe, H5 thresholds, Top-3 ordering, and every registered
  H-lane surface are UNTOUCHABLE. Each display build ships a test pinning
  board grades and ordering byte-identical with the new feature present vs
  absent.
- Fail-closed everywhere: missing input → honest gap, never a fabricated
  value, never silent GREEN. Ledger files are append-only via typed APIs.
- This platform never places orders. Nothing here creates a trigger.
- Every study runner is built, adversarially reviewed, and only then RUN ONCE
  per its registration; results append to the ledger before discussion.

## Execution status — 2026-07-23

- **EX0 — DONE (2026-07-23):** the four pin addendum values are typed as
  ledger fact `RQ2_A2_PIN_ADDENDUM_V1`; EX8 is unblocked (runners must cite
  the fact and refuse without it).
- **EX1 — DONE:** honesty wording and the 252-vs-365 disclosure are shipped
  and test-pinned; card ordering and grades were not changed.
- **EX2 — VERIFIED:** the existing R1–R5 Phase-1 recorder path continues per
  the replan; focused H10, capture-receipt, H7-exit, ritual syntax, and diff
  checks pass. No activation or trigger surface was added.
- **EX3 — DONE:** the RQ1 runner was adversarially reviewed before its single
  run. The receipt is `reports/rq1/rq1-v1.json`; the typed retrospective
  result is ledger seq 20. The report is descriptive-only and cannot promote
  a badge. Its disclosed usable scope is 4,886 name-days across MSFT, AMZN,
  VST, and CEG.
- **EX4–EX8 — QUEUED:** EX4 starts with the partial-branch reconciliation;
  EX8 is unblocked by EX0.
- **EX9 — NEXT URGENT:** earnings-variance machinery remains calendar-urgent
  ahead of the August prints and is the next queue jump if capacity changes.
- **EX10 — LATER:** waits behind the recorders and EX3–EX9 movement.

The one-run RQ1 boundary is spent: do not rerun it, alter its recipe, or
interpret its descriptive rho values as a verdict.

---

## EX0 — DONE 2026-07-23: owner pin addendum (typed on owner directive)

Four unfrozen blanks in seq 18–19 (program doc §13.1b): fixed-horizon arm
length; bucket split; Holm sidedness; Badge B "applicable event window."
Owner types a short addendum fact; RQ2/A2 runners (EX6/EX7) must refuse to
run without it. EX1–EX5 are NOT blocked by this.

Closed 2026-07-23 by ledger fact `RQ2_A2_PIN_ADDENDUM_V1` (owner-directed
entry; validation in `reports/2026-07-23-pin-addendum-validation.md`).

## EX1 — H1 honesty bundle (owner-prioritized; no dependencies)

Append "(simple, not compounded)" to every `annualized_yield` render in
`options_researcher/attractiveness.py` verdict strings; add the one-line
252-vs-365 day-count disclosure to the dashboard footer; optional round-trip
cost line labeled "early-close scenario, not the base case."
**Acceptance:** strings test-pinned; card ordering and grades byte-identical;
suite green.

## EX2 — Phase-1 recorders R1–R5 (continue per the replan briefs)

Owned by the replan (R1 H7 exit/scoring → R2 real capture → R3 H10 capture →
R4 H5 entry_watch in ritual → R5 capture receipt). Not respecified here; this
queue slots BEHIND them for anything they contend with. Two additions when R5
lands: (a) daily Treasury-curve append step (fetch per the sourced-capture
convention in `data/rates/treasury_cmt.csv`; on fetch failure the rate-based
lines go absent — no stale reuse beyond each row's valid_through); (b) the
research-capture appendix line (B-card fires/refusals, label resolutions).

## EX3 — RQ1 runner (ledger seq 17; one-run contract)

Reconstruct daily GREEN-fraction boards point-in-time from the PRE-BADGE
recipe at the freeze commit; Spearman rho of board rank vs forward 21-session
realized vol, and separately vs forward IV change; |rho| >= 0.30 flagged
notable; synthetic and lookahead-contaminated rows excluded per the
registration. Output: one receipt-bound report; append the result record.
**Acceptance:** causal-reconstruction property test (truncated cache
reproduces day-D board exactly); one-run gate refuses a second run;
adversarial review recorded BEFORE the run.

## EX4 — Badge B: term-structure corner (seq 18)

First reconcile/merge review of `feature/bs-attractiveness-descriptive`
(partial §6 column exists there). Build: long-tenor ATM IV at 60–120 DTE
(registered band — parameterize `atm_iv_90d`'s pattern, do not repoint
`H7_IV_TENOR_DTE_BAND`, which belongs to H7); `ts_slope = atm_iv(15–45) −
atm_iv(60–120)`; causal 252-obs percentile (min 60); `vrp_pctl` = causal
percentile of existing `iv_minus_rv`; corner = ts_pctl >= 0.75 AND vrp_pctl
<= 0.25, displayed ONLY when the earnings gate confirms a report in the
applicable event window (EX0 pin iv), sourced via `h7_earnings` — UNKNOWN
refuses.
**Acceptance:** shifting later data never changes earlier percentiles;
UNKNOWN → no badge (never GREEN); ordering byte-identical; constants in
`config.py` cite seq 18.

## EX5 — Badge A: bounce lens (seq 18)

`bounce_armed = (dist_52w_high <= −0.20) AND (mom_1m > 0) AND (rv21 pctl >=
0.70)` from existing `technicals.py`/feature fields; rv21 percentile computed
causally against the name's own trailing history (window constant in config).
MANDATORY card text (registered): negative priors printed verbatim — Card 3
−$85.47/trade INSUFFICIENT_SAMPLE; QM parabolic continuation; "describes a
setup; does not predict a bounce."
**Acceptance:** USAR/IREN entity floors respected (no 52-week reference
across the listing boundary); NaN-gates on short history; priors text
test-pinned; ordering byte-identical. Disclosure line in the brief: the
badge's −20% arm differs from H7a's registered 25% arming threshold — two
surfaces, never conflated.

## EX6 — N3 market-implied expectations lines

(a) Straddle-quoted expected move (no dependencies): nearest-monthly ATM
straddle mid, labeled "straddle-implied expected absolute move — not a
forecast"; fallback `0.8·S·IV·√(τ/365)` labeled; separate 1-SD band line.
(b) Rate-dependent lines (rates + dividends now sourced and spot-checked):
`N(−d2)` finish-below odds and drifted touch probability
(Reiner–Rubinstein, ν=r−q−σ²/2) on short-put/ASSIGNMENT_WATCH surfaces;
permanent "risk-neutral, tends to overstate real-world downside odds" label;
EOD-monitoring downward bias noted in the doc, not the card.
**Acceptance:** label strings test-pinned; refusal when curve/dividend row
stale (loader fail-closed is the mechanism); no probability enters any grade,
rank, or trigger (pin test); d2/touch math unit-tested against
`black_scholes.py` conventions.

## EX7 — Concentration & clustering panel (Workstream G)

Board header panel: mean pairwise 63d correlation + n_eff; lambda1-share vs
Marchenko–Pastur null; earnings-cluster count (UNKNOWN names listed, never
counted clear); combined-max-loss bracket vs `RISK_SLEEVE` labeled
hypothetical; worst observed 1-day and 5-day replay (dated, "worst OBSERVED");
beta-to-QQQ and delta-adjusted index exposure lines (closes cached).
**Acceptance:** panel absent from all per-card grades/ordering (pin);
short-history dropouts disclosed ("computed over N of 15 names"); banned
suggestor phrasing grep-tested.

## EX8 — A2 runner (seq 19; blocked on EX0)

Label construction per the five lanes exactly as registered (five CSP arms;
roll = close + open; CC four-way accounting; PMCC committed-capital
denominator + chain-linked TWR, empty lane = "no data"; LEAPS 21/63/126;
tactical 5/10/20 with six-term attribution). Entries at T+1 close; frozen
cost surfaces; liquidity at entry AND resolution; ±50% cost stress arms.
Historical pass runs ONCE as Card-3-class exploratory (also yields the
measured sigma for power context); forward capture wires into the ritual
after R5.
**Acceptance:** causality property tests; non-overlapping cohort assignment
verified; staggered view never feeds the inference stats (structural
separation, tested); one-run gate on the historical pass.

## EX9 — Workstream D earnings decomposition (CALENDAR-URGENT)

Build per the companion spec §1–§6. Priority rationale: the August earnings
season starts in ~2 weeks; every un-captured print is lost forever (no
backfill by construction). Sequence: per-name expiration-density pre-check →
event-record schema + extraction (T1/T2 bracketing, clean-T3 diffusive,
fallback labeled) → bid/ask banding (rates+dividends live for forward
events; historical events labeled assumption_flat_rate) → T-window snapshot
capture into the ritual. Descriptive-only; registration of its written study
follows as its brief matures (owner types).
**Acceptance:** refusal conditions all tested (no bracketing pair; gate not
CLEAR/occurred; crossed/zero-bid; tau1 < 2 sessions); records carry
provenance (gate record ids, manifest hashes); no verdict output anywhere.

## EX10 — Workstreams C and E runners (after recorders)

C: three named variance measures, continuous-first descriptive tables
(registration before the historical one-run). E: model×horizon forecast
comparison per the program §8 matrix (QLIKE primary). Both briefs mature
after EX3–EX9 are moving; owner types their registrations.

---

**Standing risks for the whole queue:** ThetaData expires 2026-11-30
(owner decision ~10-01) — EX9's value collapses without it; `test_lse_feed.py`
is pre-existing untracked scratch, not part of this program (owner
housekeeping); Alpha Vantage full-history is paywalled — Yahoo path is the
sanctioned closes fallback.
