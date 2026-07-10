# H7 — swing options on volatile AI names (three lanes) — design

**Date:** 2026-07-09
**Status:** approved design, pending spec review; numbers NOT yet frozen
**Scope class:** NEW hypothesis track, authorized by owner scope override
(facts.log `SCOPE_OVERRIDE 2026-07-09`, owner decision "option C" overriding
the operating manual's no-new-builds-before-first-verdict standing rule).
H5 and H6 are unchanged and stay live. Multiple-testing note: H7 registers
as THREE lanes = three hypothesis versions in the denominator.

## Thesis (owner's, made falsifiable)

Volatile AI-infrastructure names (owner examples: CRWV, TEM, PLTR, NOW) swing
hard, and the owner wants to buy the recovery after a drawdown stabilizes, buy
the resolution of a quiet consolidation, and — when the options are objectively
rich — get paid for the same view with defined-risk short premium. The
falsifiable core: **after a mechanical drawdown-stabilization or
range-compression signal on a story name, forward moves net of realistic costs
exceed what the then-current option prices imply.** "No edge after costs" is a
success finding, per house rules.

Vocabulary discipline: this spec never says "safe" or "methodical gains."
Lane H7c is *defined-risk*, not safe: a high win rate on short spreads proves
nothing; the rare max losses decide the verdict (house verdict rule).

## What the 2026-07-09 feasibility profile measured (facts, cached chains)

| Name | Spot (parity) | 6-wk move | 6-wk RV | ATM-90d IV | ATM spread | Gate-passing calls 25–130 DTE |
|---|---|---|---|---|---|---|
| CRWV | 83.96 | −21% | 90% | 94% | 3.7% | 50 (3 expiries) |
| TEM  | 60.24 | +28% | 81% | 76% | **21.8%** | 19 |
| NOW  | 111.25 | +11% | 86% | 65% | 3.5% | 49 |
| SMCI | 26.35 | −29% | 134% | 97% | 6.4% | 46 |
| PLTR | 134.93 | −1.5% | 69% | 57% | 3.0% | 110 |
| NVDA | 198.03 | −8% | 41% | 43% | 0.9% | 161 |

- Every name's IV is at or below trailing realized — long premium is not
  currently marked up on trailing-RV terms (noisy measure; disclosed).
- TEM is watch-only until spreads tighten; HYLN excluded (≈128-row chain).
- ATM 90–100 DTE calls cost $1.6–1.7k on the liquid names; 0.60/0.25 debit
  spreads $1.1–1.4k → the $600 global per-trade cap cannot host this lane;
  H7 gets its own monthly sleeve (owner decision, this session).
- **Assumption to verify before any backtest:** parity-implied NOW at $111
  implies a ServiceNow split after 2026-01; confirm split history and that
  cached NOW chains are split-consistent across the full 2018+ range.

## Universe

- **Story-watchlist** (owner-curated; the discretionary "good story" axis is
  explicitly the owner's, never scored by the repo): initial list CRWV, TEM,
  PLTR, NOW, SMCI, NVDA. The four core names (VST, CEG, MSFT, AMZN) are
  eligible for H7a/H7b only; their income trades remain H5's book (H7c
  excluded on core names — no double-dipping one name in two hypotheses'
  short-premium lanes).
- Watchlist lives in `config.py` (`H7_WATCHLIST`); every add/remove is
  ledger-logged with a one-line reason.
- Daily intersection with mechanical gates on EVERY traded leg:
  `MIN_OPEN_INTEREST` ≥ 100, `MAX_SPREAD_PCT` ≤ 10%. A name failing gates
  shows as WATCH-ONLY, never tradeable.

## Entry lanes (separately frozen, separately judged)

All three share: signals computed from daily closes + cached chains only (no
look-ahead); no new entries within 5 sessions before a scheduled earnings
report (H6-consistent); at most ONE open H7 position per underlying across
all lanes. Measures, fixed here: "IV" = the ATM call IV at the expiration
nearest 90 DTE (±18 d), i.e. the profiler's definition; "trailing RV" =
annualized close-to-close realized vol over the last 21 trading days.
Signals are edge-triggered: H7a fires on the cross above the prior 20-day
high, once per drawdown episode (re-arms only after a new 20-day low).

- **H7a — drawdown + stabilization (long).** ALL of: drawdown from 52-wk high
  ≥ `H7A_DRAWDOWN_MIN`; first close above the trailing 20-day high
  (stabilization confirm); IV ≤ trailing RV × `H7_IV_PAR_K` (the structure
  table below switches call vs debit spread at `H7_IV_CHEAP_K`).
- **H7b — coil / range compression (long).** ALL of: (60-day high − low) /
  spot ≤ `H7B_RANGE_MAX`; 20-d realized vol ≤ 25th percentile of its own
  1-yr history (names with <1 yr listed: use available history, minimum 6
  months, else ineligible); same IV bound as H7a.
- **H7c — defined-risk premium selling (short, rich-IV branch).** ALL of:
  H7a's stabilization condition holds; IV(≈90d ATM) ≥ trailing 21-d RV ×
  `H7_IV_RICH_K`; structure is a bull put spread ONLY (short put ≈0.25–0.30Δ,
  long put `H7C_WIDTH` lower, 30–45 DTE). Short premium is NEVER held through
  an earnings report: positions close by the last session before a scheduled
  report regardless of P&L (asymmetric to the long lanes by design — long
  lanes may hold through, that's the catalyst thesis, disclosed).

The IV gate is the honest operationalization of "mispriced options": cheap →
buy (H7a/H7b), rich → sell defined-risk (H7c), in-between → no trade, logged.

## Structures & exits

| Condition | Structure | Exit rules |
|---|---|---|
| H7a/H7b, IV ≤ RV × `H7_IV_CHEAP_K` | single long call 0.55–0.70Δ, 60–120 DTE | +100% TP; close/roll at 30 DTE; stop on close below signal low (H7a) / range low (H7b) |
| H7a/H7b, RV × cheap_k < IV ≤ RV × `H7_IV_PAR_K` | call debit spread, long 0.60Δ / short 0.25Δ, same expiry | 75% of max value TP; close at 30 DTE; same stop |
| H7c, IV ≥ RV × `H7_IV_RICH_K` | bull put spread, short 0.25–0.30Δ, 30–45 DTE | TP at 50% of credit; stop at 2× credit or stabilization-low breach; hard close before earnings |

Max loss is always the debit (long lanes) or width − credit (H7c). No naked
short options — structurally impossible, consistent with repo policy.

## Sizing

`H7_MONTHLY_AT_RISK` — hard cap on total premium/max-loss at risk opened per
calendar month, all three lanes combined (H6 precedent: $2,000/mo; owner
types the H7 value at registration). Position count is whatever fits under
the cap. Sleeve accounting rolls up into `RISK_SLEEVE`; the global
`MAX_LOSS_PER_TRADE = 600` explicitly does NOT apply to H7 (owner decision,
this session — logged at registration).

## Verdict machinery (owner decision: all three streams in parallel)

Ordering rule that keeps this honest: **registration freezes all numbers
FIRST; the backtest and the watcher launch only after.**

1. **Forward paper window (verdict-bearing):** ≥ 3 months per lane, marks via
   the existing positions/portfolio/scoreboard path, expectancy after costs
   with bootstrap CI, verdict gates on `MIN_LOSSES_FOR_VERDICT` accumulated
   losses per lane — explicitly not on win rate.
2. **Backtest (parallel, non-gating, can kill but not bless):** the frozen
   rules run on the 7 fully-cached names (NOW, NVDA, PLTR, MSFT, AMZN, VST,
   CEG; 2018→2026-06). Disclosed bias: these names were picked knowing the
   AI boom; a positive result is necessary-context only. A lane whose
   backtest AND early forward window both look bad gets rejected early.
   CRWV/TEM/SMCI have no usable history (29 cached days) — forward-only.
3. **Watcher (instrument, not evidence):** daily H7 screen — signal state per
   name per lane, IV-vs-RV branch, structure menu with real costs, WATCH-ONLY
   flags — extending the `attractiveness`/`entry_watch` patterns. One new
   module (`options_researcher/h7_watch.py` + config + tests); no changes to
   H5/H6 code paths.

## Costs & data

- Fills: quote mid or worse + `SLIPPAGE_HAIRCUT` 1% + `COMMISSION_PER_CONTRACT`
  $0.65/leg each way; both legs gated and costed on spreads. EOD gaps: skip
  and log, never substitute intraday.
- **ThetaData subscription renewal past ~07-25 is REQUIRED** for the forward
  window and daily watch (also carries H5/H6 marks). Owner must explicitly
  confirm the spend — flagged as an open item below.
- Optional, separate owner decision: one-time SMCI history backfill
  (~2,100 trading days) to add a failed-recovery case to the backtest set.

## Proposed frozen parameters (LLM-asserted — owner types final values)

Per the operating manual, every number below is a proposal with reasoning;
none is frozen until the owner enters it in the registration entry. The same
applies to every numeric value in the lanes/structures/exits sections above
(delta bands, DTE bands, TP/stop levels, 20-day/60-day/52-wk lookbacks, the
5-session earnings buffer): all LLM-asserted proposals, frozen only at
registration.

| Parameter | Proposal | Reasoning (all Inference unless noted) |
|---|---|---|
| `H7A_DRAWDOWN_MIN` | 0.25 | Deep enough to mean a real cycle (CRWV −40%+ from high qualifies today); 15% would fire on routine noise for 80-RV names |
| `H7B_RANGE_MAX` | 0.15 | NVDA's current 15.4%/6-wk range is the live example of "quiet" among these names |
| `H7_IV_CHEAP_K` | 1.00 | "Not marked up" = IV at or below trailing realized; measured, not asserted (profile above) |
| `H7_IV_PAR_K` | 1.15 | Par band width ~1 vol-regime notch; beyond it, debit spreads stop compensating |
| `H7_IV_RICH_K` | 1.25 | Selling requires a real premium over realized, not statistical noise on a 21-d window |
| `H7C_WIDTH` | $10 (CRWV/NOW-priced), $5 (SMCI-priced) | Width ≈ 10% of spot keeps max loss ≈ sleeve-compatible |
| `H7_MONTHLY_AT_RISK` | $2,000 | H6 precedent (owner set it there) |
| Forward window length | 3 months minimum | Matches H5/H6 convention; shorter windows can't accumulate the loss count |
| `MIN_LOSSES_FOR_VERDICT` (per lane) | existing config value | Repo-verified house rule; not a new number |

## Open items (owner actions before registration)

1. Type the final values for every parameter above into the registration.
2. Confirm ThetaData renewal (spend) — without it there is no forward window.
3. Verify the NOW split assumption before the backtest runs.
4. Update the operating-manual standing line (owner edit, drafted in session).
5. Decide the optional SMCI backfill (separate approved pull).
