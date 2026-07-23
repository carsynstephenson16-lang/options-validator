# H11 drawdown-reversal — parameter PROPOSALS (owner types the frozen values)

**Status: PROPOSAL ONLY. Nothing here is registered. Every number below is
LLM-asserted and must be owner-typed into the ledger registration to become
real.** Registration follows the H10 pattern (`ledger/experiments.jsonl`
seq 15/16 as the template).

## Declared priors (MUST appear verbatim in the registration)

1. **Card 3** (seq 12-13, 2026-07-18): the same mechanical idea (≥30% off
   52-week high, near 60-day low, reversal tick, long calls) produced 6
   completed trades, expectancy **−$85.47/trade**, CI90 [−$187.97, +$13.87],
   INSUFFICIENT_SAMPLE. One-run contract spent; H11 is a forward-paper
   re-test, not a rerun.
2. **QM parabolic-fade REJECTED** (2026-07-14): violent moves in this
   universe's history tended to continue, not revert.
3. **Outcome-informed origin, disclosed:** this registration was prompted by
   observing CRWV's 2026-07 drawdown-and-bounce (close low $73.21 on 07-17 →
   ~$84 on 07-22) — a hindsight-selected example. That is exactly the bias a
   forward window exists to neutralize.

## Proposed design (each row = owner decision)

| Parameter | Proposal | Reasoning |
|---|---|---|
| Universe | `H7_WATCHLIST` names that are source-healthy at entry (per-name fail-closed, same rule as H7) | CRWV/IREN join automatically when the N1a earnings-source fix lands; no hand-picked list |
| Overlap rule | Skip entry if the same name has an open H7 real position | Keeps the two books' verdicts independent |
| Drawdown trigger | Close ≥30% below 52-week high AND ≥20% below its own 20-session high | 30% matches Card 3 (comparability); the 20-session leg makes it a *recent, violent* drop, not an old bear market |
| Reversal confirmation | Close above the prior 5-session high | Mechanical, EOD-computable, no discretion |
| Falling-knife guard | No new 20-session low in the last 3 sessions | Card 3 convention |
| Structure | Call debit spread, long ≈0.55Δ / short ≈0.30Δ, 45–75 DTE | Post-crash IV is usually rich; a spread blunts paying peak IV for calls. OWNER FORK: plain long call (Card 3 comparability) vs spread (cost honesty) — pick one |
| Liquidity | Both legs pass frozen `MIN_OPEN_INTEREST` + `MAX_SPREAD_PCT` | Existing house gates, unchanged |
| Earnings rule | Skip entry if a confirmed earnings date falls inside the max holding window; unconfirmed date = entry ban (fail-closed) | H10 convention; note CRWV reports 2026-08-18 |
| Fills/costs | Mid-or-worse + `SLIPPAGE_HAIRCUT` + `COMMISSION_PER_CONTRACT`, both legs | House rule |
| Per-trade cap | Net debit ≤ $600 | House `MAX_LOSS_PER_TRADE` convention |
| Monthly sleeve | Own cap, proposal $1,500/month premium at risk (NOT shared with H6+H8's $2k or H10's $2k) | Total live paper sleeves stay bounded; owner sizes this |
| Exits (first hit wins) | +100% on net debit → close; 25 sessions elapsed → close; 21 DTE → close | H10 template, slightly longer time stop for a swing thesis |
| Verdict gate | ≥7 losses (H10-precedent owner override of 10; weaker verdict disclosed) OR calendar backstop, proposal 2027-01-30; bootstrap CI90 on after-cost expectancy/trade; reject if CI upper ≤ 0 | Loss-gated per `.cursorrules`; backstop prevents a zombie window |
| Capture | `h11_watch` + receipts + observations, cloned from the Task-2/3 H10 pattern; book file `data/positions/h11_positions.csv` (standard 12-column header); no backfill; only post-registration observations count | Recorder exists BEFORE the clock starts — the H10 mistake is not repeated |

## Known conflicts to resolve before registering

- **Data horizon:** ThetaData EOD coverage is confirmed through 2026-11-30. A
  2027-01-30 backstop (and any position opened after ~mid-December) requires
  the ThetaData extension decision first, or an earlier backstop (e.g.
  2026-11-21) that fits paid coverage.
- **Registration order:** per the replan spec, H11 registers only after
  Track A recorders are merged (recorder-before-clock rule).
- **N1a dependency:** without the CRWV/IREN earnings-source fix, both names
  stay entry-banned under the proposed fail-closed earnings rule — the play
  the owner most wants would be excluded at launch.
