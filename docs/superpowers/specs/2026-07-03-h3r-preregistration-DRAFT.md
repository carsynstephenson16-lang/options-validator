# H3R pre-registration — DRAFT (2026-07-03, NOT frozen, NOT registered)

> **ARCHIVED (2026-07-03, later same day):** the owner pivoted the project to
> a 4-name options research scope (VST/CEG/MSFT/AMZN) before this spec was
> approved. H3R was never registered and never run; no trial was spent. Kept
> because the methodology — Gate V (data validation), Gate P (power/
> eligibility before any trial), baseline/placebo/inverted attribution arms,
> and the PASS-vs-OOS-eligible separation — is reusable verbatim for future
> 4-name hypotheses.

**Status: awaiting owner approval. No backtest has run under this spec. No OOS
is touched (budget 0/3). On approval this document is committed verbatim and
becomes the frozen pre-registration; every parameter below is then immutable.
Supersedes `2026-07-03-h3-candidate-research-memo-DRAFT.md` (H3 v1).**

Responds to: external audit `2026-07-04-chatgpt-deep-research-h3-audit-report.md`.
Adopted from it: SPY-only primary; QQQ demoted to a separate non-verdict
robustness sleeve; locked close-series validation gate before any feature is
trusted; explicit per-trade P&L decomposition; quote-quality discipline;
prohibited-moves list. Deviations from it are listed in §9 with reasons.

---

## 1. Hypothesis (falsifiable)

> **H3R (`H3R-cvrp-spy-atm5w-noStop-eod-v2`):** On SPY, selling the ~0.50-delta
> put and buying the put exactly $5 lower on the nearest 30–45 DTE expiry,
> entered at day-t EOD **only when** (a) the day-(t−1) VRP signal —
> ATM implied vol minus 21-day realized vol — is at or above the 70th
> percentile of its trailing window, and (b) the day-(t−1) close is above its
> 200-day SMA, held with **no stop and no profit target** to a forced close at
> 7 DTE, has **positive expectancy per trade after the frozen conservative
> cost model** over in-sample 2018-01-01..2022-12-31.

Novelty disclosure (literature scout, 2026-07-03): no published study tests
this exact bundle (IV−RV tercile gate + SMA gate + ATM $5 vertical after
retail costs). Components have support (conditional VRP: Bakshi–Kapadia,
Goyal–Saretto, Realized-GARCH VRP; trend-in-crisis: Hurst–Ooi–Pedersen), but
H3R is registered as a **novel claim**, not a confirmatory replication.

## 2. Frozen rules

| Field | Frozen value |
|---|---|
| Primary universe | **SPY only** (`H3R_UNIVERSE = ["SPY"]`) |
| Robustness sleeve | QQQ, run only after the SPY verdict is ledgered; never feeds the verdict |
| Structure | Sell put nearest \|Δ\|=0.50 (accept band 0.40–0.60, else skip), buy put at short strike − $5 exactly (must exist, else skip) |
| Expiry | Nearest expiration with DTE in [30, 45] (existing `_pick_expiration` logic) |
| Entry timing | Decision at day-t EOD on day-t chain; orders fill t+1-or-later at conservative quotes (existing harness convention) |
| Signal features | All from day t−1 or earlier, served by a lag-enforcing provider (§4) |
| RV | √252 × stdev(ddof=1) of the last 21 daily log returns of the **direct** close series, ending at t−1 |
| ATM IV | From the t−1 cached chain: put nearest \|Δ\|=0.50 within [0.40, 0.60] on the nearest 30–45 DTE expiry; iv must be > 0, else signal undefined that day (fail closed) |
| VRP | ATM IV − RV (annualized vol points) |
| VRP gate | VRP(t−1) ≥ 70th percentile (inclusive rank) of its trailing window: last min(252, available) observations, minimum 126 required |
| Trend gate | close(t−1) > SMA200(t−1) of direct closes |
| Regime filter | The trend gate is the only regime filter; no VIX or external index data |
| Liquidity gates | Existing frozen gates, both legs at entry: OI ≥ 100; bid ≥ 0, ask > 0, ask ≥ bid (crossed/zero-quote rejection); (ask−bid)/mid ≤ 10% |
| Credit gate | Conservative entry credit (short bid − long ask, 1% haircut) ≥ **$1.50**, else skip |
| Exit | Forced close at DTE ≤ 7, conservative cost-to-close (short ask×1.01 − long bid×0.99). **No stop. No profit target.** |
| Assignment | Not simulated (harness limitation, disclosed); 7-DTE close mitigates pin risk; early-exercise-exposure days reported descriptively (§6.7) |
| Sizing | `size_defined_risk` unchanged: max contracts with economic max loss ≤ $600; ATM $5-wide ⇒ 1 contract (~$260–355 max loss) |
| Sleeve exposure | One SPY spread max ⇒ ≤ ~$600 ≈ 4.3% of the $14k sleeve at risk |
| Cost model | Frozen `conservative_bid_ask_plus_haircut_v1`: mid-or-worse via bid/ask crossing, $0.65/contract/leg/way, 1% adverse haircut |
| Windows | is_window 2018-01-01..2022-12-31; oos_window 2023-01-01..2026-06-30 (inherited; sealed); entry blackout: last `MAX_HOLD_DAYS = 46` days of each window |
| Sample floor | Verdict requires ≥ 10 losses and ≥ 3 entry-week cohorts (existing) |

## 3. Two pre-registration gates (run BEFORE the hypothesis exists; can kill it free)

**Gate V — close-series validation (locked).** Direct SPY (and QQQ, for the
sleeve) daily closes are fetched blind for 2017-01-01..2026-06-30 from the
owner-approved source and cached; the loader refuses dates > IN_SAMPLE_END
without `allow_oos` (chain-cache discipline). Acceptance, frozen: (a) no
missing trading days vs the chain-cache calendar within 2017..2022; (b)
put-call-parity spot series built from cached chains (r=0, mid quotes,
nearest-band expiry, median across strikes) agrees with direct closes on log
returns: median |return difference| ≤ 5 bps and 99th percentile ≤ 50 bps over
2018..2022; (c) parity outlier days (e.g. dividend-adjusted-chain artifacts
like QQQ 2023-12-27) are enumerated and must be < 1% of days. Features use
**direct closes only**; parity is the cross-check. Gate V failure ⇒ stop,
report to owner; H3R is not registered.

**Gate P — power/eligibility (signal-only, no P&L).** After the spec freezes:
(a) `power_check`-style synthetic study of the verdict path under H3R's shape
(1 symbol, gated entry density, ~5-week holds, ATM win/loss mix grid) —
reports false-PASS and power; (b) eligibility count on in-sample features
only: number of signal-on days and greedy projected trade count (entry →
+35 calendar days). **No option P&L is computed.** Frozen floor: projected
trades ≥ 25, else H3R-as-specified is not registered (design infeasibility,
zero trials spent; any re-parameterized variant is a new hypothesis). Both
outputs go to facts.log (disclosed engineering look, signal-only).

## 4. Lag enforcement

The strategy never computes features. A provider built from the feature frame
serves, for decision date t, the most recent feature row with date < t. Unit
tests assert a signal flipping on at date d gates entries no earlier than the
next trading day. Structure selection and fills use the day-t chain and
t+1-or-later fills per the verified harness convention (selection is
execution mechanics; the go/no-go signal is strictly lagged).

## 5. Verdict criteria (primary run, frozen verbatim)

> The registered in-sample run's metrics.scoreboard verdict stands as
> reported: PASS iff the dependence-aware 90% CI (weekly entry-cohort block
> bootstrap + stationary cross-check, widest envelope) lower bound on
> expectancy per trade is > $0 after all modeled costs with ≥ 10 losses and
> ≥ 3 entry-week cohorts; FAIL iff the CI upper bound < $0; otherwise NO EDGE
> / INSUFFICIENT SAMPLE as reported. The first run's scoreboard is registered
> as H3R's is_result **whatever it shows**; declining to register after
> seeing it is ruled out now (no-discretion clause).

FAIL, NO EDGE, or INSUFFICIENT SAMPLE ⇒ H3R is dead: no OOS look, no
re-tuning, no width/delta/threshold/exit changes against the result. Any
variant is a new hypothesis with new gates and its own trials.

## 6. Pre-declared diagnostics (all trial-logged; none feed the verdict)

With no stop and no profit target, entry/exit **dates** are fill-independent,
so 6.4–6.5 are exact re-pricings of the recorded legs — no new backtests.

1. **Baseline attribution arm** (always-on provider; same structure,
   unconditional): run after the primary is ledgered. Purpose: does the
   signal, not the ATM/no-stop structure, carry the result?
2. **Placebo arm** (signal lagged 252 trading days): should look like
   baseline, not like primary.
3. **Inverted arm** (enter when VRP percentile ≤ 0.30, trend gate unchanged):
   should be no better than primary.
4. **Cost stress** (re-pricing): half-spread ×1.5; haircut 1%→2%; commission
   $0.65→$1.00/leg — each separately. Trades whose stressed entry credit
   falls below the $1.50 floor are reported both included and excluded.
5. **Commission/fee sanity**: decomposition table per trade — gross credit,
   exit debit, commissions, half-spread cost, haircut cost (new fields, §8).
6. **Regime breakdown**: calendar years 2018–2022 + flagged sub-windows
   (2018Q4, 2020H1, 2022); descriptive.
7. **Early-exercise exposure**: count open-position days with short put ITM
   ≥ $2.50 and extrinsic < $0.05 at mid (descriptive; model limitation).
8. **QQQ robustness sleeve**: identical frozen rules, symbols=["QQQ"], run
   only after the SPY verdict is ledgered; descriptive.
9. **Liquidity stress** (only if primary PASS): OI ≥ 200 and spread ≤ 7%
   gates; a re-run (new trial, in-sample only).
10. **Threshold envelope** (only if primary PASS): 0.65 and 0.75 arms via
    config-committed states (width-sweep mechanics); two trials.

## 7. OOS-eligibility bar (frozen; distinct from PASS)

A PASS earns an owner conversation, never an automatic reveal. The standing
recommendation to spend an OOS look additionally requires ALL of:

- primary point expectancy > baseline arm point expectancy (attribution);
- primary − placebo point expectancy ≥ $10, and placebo does not PASS;
- inverted arm point expectancy < primary;
- point expectancy > 0 under each single-factor cost stress (6.4);
- point expectancy > 0 under liquidity stress (6.9);
- both envelope arms (6.10) have point expectancy > 0;
- no single calendar half-year contributes > 50% of the sum of positive
  trade P&L; total trades ≥ 25;
- Gate V still green (no data revisions).

Any miss ⇒ recorded as PASS-fragile; default recommendation: no reveal.

## 8. Required implementation before registration (source-freeze trap)

All of the following must be committed and green BEFORE H3R registers,
because the source hash freezes at registration: trade-record P&L
decomposition fields; credit-floor hook; `data/underlying_closes.py` (blind
fetch + OOS-gated loader); `analysis/validate_closes.py` (Gate V);
`data/features_vrp.py` (frame + lag-enforcing provider incl. always_on /
placebo / inverted modes); `strategies/conditional_vrp_spread.py`;
harness `extra_parameters` passthrough + strategy registry +
`strategy_id` in registration records + generalized `_oos_backtest_trades`
(today it hardcodes PutCreditSpread — H3R's reveal would be bricked);
`analysis/power_check_h3r.py`; `analysis/h3r_eligibility.py`. Full suite
green. See the implementation plan doc.

## 9. Deviations from the external audit, with reasons

1. **VRP percentile warmup min 126 (expanding to 252 cap), not a hard 252**:
   a hard 252 pushes first entries to ~2019-01 and silently deletes the
   Q4-2018 stress regime from in-sample; 126 keeps it. The 252-day window is
   still the steady-state. Decided a priori, before any run.
2. **SMA200/RV warmup solved with 2017 closes** (blind pull), so the trend
   gate is live from 2018-01-02 rather than ~2018-10.
3. **Assignment simulation**: not implemented (audit asks for "explicit
   handling"); we disclose the limitation, bound it with the defined-risk
   cap + 7-DTE close, and report exposure days (6.7). Full assignment
   modeling would be a new harness capability, out of scope for H3R.

## 10. What counts as a NEW hypothesis (vs licensed robustness)

Licensed, pre-declared, non-verdict: exactly the §6 list. Everything else is
a new hypothesis and a new registration — explicitly including any change to:
threshold value or percentile window; RV estimator or window; SMA length;
delta target/band; width; DTE band; exit DTE; stop/target policy; credit
floor; universe; cost model; fill model; liquidity gates; verdict machinery;
feature timing. Re-pooling SPY+QQQ after a SPY FAIL is prohibited. Removing
2020 or 2022 from in-sample is prohibited. Softening fills is prohibited.

## 11. Design-contamination disclosure

H3R was designed after seeing H1/H2's in-sample FAILs and the width-sweep
gradient. The design inputs were literature priors, friction arithmetic, and
the external audit — not scans of variant P&L (no H3R-shaped backtest has
ever run). Residual contamination risk is real, cannot be zeroed, and is why
the sealed holdout and the §7 bar exist. Honest prior: the conditioning must
be worth > ~$40/trade over the H2-measured unconditional 30Δ baseline just to
reach zero; P(in-sample PASS) is estimated at 20–35%. INSUFFICIENT SAMPLE is
a live outcome (Gate P exists to catch it before a trial is spent).
