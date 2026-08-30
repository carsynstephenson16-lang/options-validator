# Quantitative and strategy-validity audit

**Audit snapshot:** 2026-08-25, frozen `main` SHA `c9e74ccd05e4ecdd0de8de6f35bef714bc6f1771`.

**Scope:** Read-only review of canonical ledger/registration, code, test source, and reports. No backtest, robustness run, provider call, paper-book operation, ledger/receipt/cache mutation, or test execution occurred. Audit-specific preregistration/data-admission authority for a new run is absent. Protected preflight WIP was not changed; WIP absent from this frozen tree is not treated as evidence.

## Verdict

**Not ready for an affirmative strategy conclusion.** The only high-sample, verdict-shaped historical spread results are **rejected** after modeled costs: H1 ($2 SPY/QQQ PCS) and H2 ($5). Every relevant forward lane is **not yet rejected** or **consistent with zero edge** because it has no completed, loss-rich forward sample; none has survived a named forward statistical test. This conservative conclusion avoids false positives; it can only create a false negative by refusing to infer a benefit from sparse or starved data.

## Per-strategy evidence and verdicts

| Strategy/lane | Audit verdict | Evidence and limitation |
|---|---|---|
| H1 $2 SPY/QQQ EOD put-credit spread | **rejected** | **Verified:** `ledger/experiments.jsonl:1` records 226 trades, 113 losses, expectancy -$102.79/trade, CI90 [-$132.61, -$74.46], and a modeled-cost fail. It is in-sample only and no OOS look was spent. Two crisis exits exceeded defined-risk economics; excluding their $1,740 total overrun still leaves about -$95/trade in the same record. |
| H2 $5 SPY/QQQ EOD put-credit spread | **rejected** | **Verified:** `ledger/experiments.jsonl:4` has 196 trades, 60 losses, expectancy -$39.07/trade, CI90 [-$61.28, -$18.08]. The $1 width trial was also negative (`:2`). H2 was the predeclared least-bad width, but still negative. |
| H3R conditional VRP | **not yet rejected** | **Verified:** `README.md:57` calls it archived and un-run at the scope pivot. There is no evidence for or against it and no valid survivor claim. |
| H4 composite historical replay | **not yet rejected** | **Verified:** `reports/2026-07-04-h4-composite-evidence.md` reports +$14,656 over 14 quarters; `options_researcher/h4_backtest.py:1-12` labels it hindsight-contaminated evidence-only. It reads post-2022 (`:52-60`) and was superseded at zero cycles (ledger seq 5); its P&L is not verdict evidence. |
| H5 Sector Income Core | **not yet rejected** | **Verified:** ledger seq 5 registered H5 and seq 29 retires its entry trigger to observe mode; `README.md:250` confirms. A retired trigger cannot generate a strategy verdict; Schwab observations are descriptive. |
| H6 post-earnings long calls | **not yet rejected** | **Verified:** `README.md:335-340` records one open NVDA paper call and zero completions; `reports/h6_forward/2026-07-22.json` returns `INSUFFICIENT_SAMPLE` until eight completions. No completed-trade CI or independent-regime sample exists. |
| H7a/H7b/H7c swing lanes | **not yet rejected** | **Verified:** ledger seq 10 withdraws the historical diagnostic as verdict-capable; `README.md:374-420` makes forward paper the sole verdict path and says H7 is paused with no position/result. The historical diagnostic cannot bless a lane by design. |
| H8 pre-earnings long calls | **not yet rejected** | **Verified:** `README.md:341-361` reports a header-only book and zero completed positions. No sample, CI, or independent regime evidence exists. |
| CARD3 near-bottom long call | **consistent with zero edge** | **Verified:** ledger seq 13 records 6 completed trades, 4 losses, expectancy -$85.47 and CI90 [-$187.97, +$13.87]; one open in-sample trade was excluded rather than peeking past the seal. The 10-loss floor was not met; fills concentrated in PLTR/VST because other names exceeded the $600 cap. |
| H9 post-earnings conditional historical study | **consistent with zero edge** | **Verified:** `reports/h9/receipt.json` records 16 trades, 4 losses, and `INSUFFICIENT_SAMPLE`; `reports/h9/census.json` has 165 eligible events. A favorable point estimate does not clear the predeclared 10-loss floor. |
| H10a parabolic continuation | **not yet rejected** | **Verified:** `reports/h10/2026-08-15-h10a-closeout.md` and `ledger/facts.log` `H10A_RESULT` show 0 fires/trades/losses and `INSUFFICIENT_SAMPLE — STARVED`. No reject/continue CI is computable; retest needs a new registration and feasibility gate. |
| H10b breakout continuation | **not yet rejected** | **Verified:** ledger seq 16 registers it and seq 28 prospectively substitutes the Schwab source. `reports/h10/h10b_observations.jsonl` records zero fires/open positions. **Inferred:** its disclosed official-close-spot plus 15:45-preclose-chain timing can be less executable than a synchronized snapshot; it is not P&L evidence. |
| RQ1/RQ2/A2/regime/attractiveness research | **not yet rejected** as research questions; no strategy verdict | **Verified:** ledger seq 17–27 and `docs/robustness-experiments.md:1-8` make these descriptive/research-only and non-promoting. A2-related WIP named in preflight is protected and absent at this SHA: **Blocked** from this audit. |

## Simulation realism

### What is modeled (Verified)

- `data/pandas_feed.py:8-26` widens buys up and sells down by the 1% frozen haircut, with adverse cent rounding; the raw mid is a mark, not a fill. `strategies/base.py:28-40,59-97` crosses bid/ask and charges round-trip per-leg commissions.
- `config.py:237-244` freezes D+1 close, fill-session dates, and terminal conservative marks. `strategies/put_credit_spread.py:261-347` freezes decision-day legs and revalidates the same legs/economics on the next session. Reviewed source tests `tests/test_causal_fill_convention.py:160-313` cover worse fill, cap resize/cancel, no future-delta admission, next-session exit, and terminal mark. They were not re-run.
- PCS selection requires both-leg OI/quote liquidity (`strategies/put_credit_spread.py:103-149`) and sizes with spread margin plus round-trip commission (`strategies/base.py:33-56`). H7 admission applies monthly, two-sided, OI and spread gates (`options_researcher/h7_signals.py:145-167`).
- H7 uses bounded `known_as_of`, next-session entry economics revalidation, and cancellation/retention instead of filling missing/crossed quotes (`strategies/h7_backtest.py:245-395,435-635`; reviewed `tests/test_h7_backtest_engine.py:119-164,302-319`).

### Material realism limits

1. **High — uncalibrated execution haircut.** **Verified:** `reports/fill_calibration/2026-08-24-fill-adversity-context.md` says no realized execution records exist, so the 1% haircut cannot be calibrated to actual fills. It identifies at least one out-of-scale bucket but explicitly calibrates nothing. **Inference:** profitability can be overstated or understated; forced short-premium exits are most vulnerable to overstatement.
2. **High — quote/OI liquidity is not capacity.** **Verified:** `config.py:90-92,122-125` contains commission, haircut, OI and spread gates; reviewed execution paths do not set daily-volume participation, quoted-size consumption, queue priority, or market impact. The calibration report says quoted size is one-lot plausibility, not fill evidence. **Inference:** scale and stressed exits can be less executable than modeled, biasing P&L upward.
3. **Medium — no complete assignment/exercise/broker-margin simulation.** PCS closes at 7 DTE (`config.py:166-168`), and H7 fails loudly for unresolved expiry exits (`strategies/h7_backtest.py:444-447,564-567`), but reviewed paths model option P&L rather than early assignment, exercise by exception, borrow, or broker-specific buying power. **Unknown:** full broker-level accounting for non-PCS forward books. The hidden direction for short puts/covered structures is adverse.
4. **Medium — $600 is entry-time economics, not realized-loss ceiling.** **Verified:** H1 documents two crisis exits beyond defined risk and one $604.80 entry-time economic max. This is conservative disclosure, but it means the cap must not be described as a guaranteed realized loss bound.

**Realism grade: C+ for historical simulation.** It is materially stronger than mid-price simulation, but realized-fill calibration, capacity/impact treatment, and assignment/broker accounting are required for a higher grade. This is not a live-system grade.

## Statistical validity, causality, and selection risk

- **Verified:** `metrics.py:497-536` uses weekly entry cohorts, a fixed bootstrap envelope, and refuses a verdict below 10 losses or three cohorts. It asks whether after-cost expectancy differs from zero, not whether a mechanism persists.
- **Verified:** `research/experiments.py:224-339` requires a registered/frozen config-cost-source surface, anchored clean ledger, charge-on-touch OOS budget, and partition checks. H1/H2 have `oos_result: null`; no OOS budget was silently spent.
- **Verified:** CSCV/PBO is not implemented: `config.py:211-225` makes it a future floor and `research/ledger.py:422-423` forces `pbo` null. This is disclosed but blocks treating selected positive historical results as robust to broad search.
- **Verified:** the ledger reaches trial count 32 (seq 31), including strategy trials, width arms, amendments, and descriptive studies. **Inference:** it is not one comparable parameter-grid denominator, but it proves any later positive selection needs its own complete search accounting rather than a naive CI.
- **Verified:** H1's SPY/QQQ scope acknowledges AI/power-name survivorship (`docs/superpowers/specs/2026-07-03-h1-preregistration-scope-decision.md:18-45`); H4 is hindsight-labeled; H7 historical evidence was withdrawn. No active conclusion can erase these limits.
- **Verified:** cached chains reject post-`IN_SAMPLE_END` reads unless explicitly authorized (`data/pandas_feed.py:100-130`), and CARD3 excludes its unresolved post-boundary trade. H4 explicitly opts into post-2022 data but remains evidence-only. **Unknown:** a fresh independent audit of all raw cache timestamps/corporate actions is out of this audit's authority.

## Required evidence before a lane could say it survived a named test

1. A ledger-bound prospective version fixing entry/exit, event, liquidity, cost, quantity, risk, and rejection rules; any altered number is a new version.
2. Enough completed forward observations to meet the registered loss and independent-regime requirements, with point-in-time receipts and no silent session substitution.
3. A separately reported execution-sensitivity analysis grounded in realized-fill evidence where possible; otherwise retain the C+ grade and adverse capacity/assignment caveats.
4. For a selected historical result, predeclared multiple-testing treatment. CSCV/PBO remains unavailable unless a valid future grid clears its floors; this report grants no authority to build or run it.

## Coverage, blockers, and final decision

**Coverage:** legacy PCS and H7 engines, H4/CARD3 historical studies, H1/H2/H4/H5/H6/H7/H8/H9/H10/RQ registry evidence, scoring/OOS code, causality tests by inspection, and fill-adversity context.

**Blocked:** audit-specific run authority; insufficient forward observations; paused H7; no realized fills; protected A2/WIP outside the frozen audit scope.

**Final decision: not ready** for promotion or a strategy-positive claim. Preserve the rejected, starved, and insufficient-sample records without reinterpretation.
