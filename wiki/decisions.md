# Standing decisions — index

Pointers only; each decision's real text lives in `ledger/facts.log`,
`config.py`, or a dated doc. See [[hypotheses]] for what these decisions
gate and [[automation]]/[[dashboards]] for what they run.

## Four-name pivot (2026-07-03)
Scoped the project to VST/CEG/MSFT/AMZN (`config.UNIVERSE`, `config.py:60`).
Consequence, decided the same day: 2023+ is no longer a credible blind
holdout for these four names — they were picked already knowing the AI
boom. `PIVOT_4NAME_SCOPE`, `ledger/facts.log:8590`. See [[data-layer]]
"Blind / in-sample split."

## H7 scope freeze — 15-name display scope, 9-name immutable entry cohort
The 15-name watch universe is `H7_WATCHLIST` (11 names) plus
`H7_CORE_LONG_ONLY` (4 names, `["VST","CEG","MSFT","AMZN"]`) minus
`H7_EXCLUDED` (`config.py:377-385, 643-645`);
`options_researcher/h7_scope.py:18-25` hard-raises unless the count is
exactly 15. Separately, the **9-name entry cohort is frozen for the life of
the live forward window**: `[AMD, AMZN, CEG, ET, MSFT, NOW, PLTR, TEM, VST]`,
set at Stage-8 activation (`ledger/h7_forward/events.jsonl` seq 0,
`window_registration`, 2026-07-20); 6 names excluded reason
`EARNINGS-UNKNOWN` (AVGO, CRWV, IREN, NVDA, SMCI, USAR — data-readiness
exclusion, not a performance signal). The historical (2018–2026) H7
diagnostic is separately, permanently withdrawn as verdict-capable evidence
(amendment v1.3, 2026-07-11) — see [[hypotheses]] H7.

## OI-change line — v1 shipped, v2 gated
`config.py:133-137`: `OI_CHANGE_MIN_BASE` / `OI_CHANGE_MAX_PRIOR_GAP_DAYS`
are **ACTIVE** — a display-only line on each attractiveness card noting how
open interest changed since the prior session; it never feeds a grade.
`OI_CHANGE_PCTL_WINDOW` / `OI_CHANGE_PCT_MIN_OBS` / `OI_CHANGE_NOTABLE_PCTL`
are frozen but **INACTIVE** — v2 (percentile/NOTABLE flagging) is gated on
a pre-registered calibration study,
`docs/superpowers/plans/2026-07-25-oi-v2-calibration-design.md`.

## RQ2 briefs — delegated values
`docs/superpowers/plans/2026-07-22-rq2-scanner-enrichment-briefs.md` specs
five candidate scanner badges (term-structure corner, skew, market-implied
expectations, VRP calibration, board concentration). Every `[OWNER]` blank
in the brief bodies was owner-delegated to Claude on 2026-07-24 ("i had you
type those in for me"); resolved numbers live in that doc's
"§ Delegated values (2026-07-24)" table, each labeled LLM-proposed and
scheduled for testing at implementation and re-confirmation at
registration — never silently frozen. Standing constraint on all of it:
addition-only — a new badge may never change an existing grade, gate, or
Top-3 rank.

## Readiness verdict — 2026-07-25
`docs/options-validator-readiness.md`: **READY WITH KNOWN LIMITATIONS** for
the scheduled Monday 2026-07-27 07:10 ritual run, verified against `main`
at commit 2864008 (1,996 tests green, ruff/pyright clean, CI green). Two
owner-side dependencies: machine awake at 07:10, and the remote ThetaData
service (MDDS) reachable — **no local terminal process required**
(correction that session; see [[data-layer]]). Non-blocking P1 backlog:
mission-control banner date pin, a stale plist comment, and an earnings
source refresh for 6 non-registered watchlist names. Companion docs:
`docs/monday-runbook.md`, `docs/dashboard-architecture.md`.

## Capital & risk ceiling
`config.RISK_SLEEVE = 14_000` and `config.MAX_LOSS_PER_TRADE = 600`
(`config.py:30,42`, owner decision 2026-07-02) bound every hypothesis above;
never sized against net worth. The legacy H1/H2 OOS holdout reveal was
separately declined by the owner (budget 0/3 spent,
`ledger/facts.log:8589`) and stays sealed.
