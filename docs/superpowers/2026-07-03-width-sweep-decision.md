# Width sweep decision — all widths FAIL in-sample; $5 least-bad (2026-07-03)

**Protocol:** exactly as frozen pre-run in
[specs/2026-07-03-h1-preregistration-scope-decision.md](specs/2026-07-03-h1-preregistration-scope-decision.md) §6:
arms $1/$5 on the H1 scope (SPY/QQQ, 2018-01-01..2022-12-31, everything else
identical), the $2 arm being H1's registered run itself; selection by highest
in-sample CI90 lower bound; challenger needs >= 10 losses and must strictly
beat $2's bound. Arms ran at committed config states (`6f87550` w=1, `ce5ab7c` w=5) and were
trial-logged; config restored to w=2 at `2b0d36a` (byte-identical to H1's
registered surface — H1 stays revealable).

## Results (in-sample, conservative frozen fill model)

| Width | Trades | Win rate | Losses | Expectancy/trade | CI90 | Verdict |
|---|---|---|---|---|---|---|
| $1 | 356 | 12.4% | 312 | −$185.17 | [−204.92, −164.12] | FAIL |
| $2 (H1) | 226 | 50.0% | 113 | −$102.79 | [−132.61, −74.46] | FAIL |
| $5 (H2) | 196 | 69.4% | 60 | −$39.07 | [−61.28, −18.08] | FAIL |

**Rule application:** $5 beats $2's CI_lo (−61.28 > −132.61) with 60 ≥ 10
losses → the challenger wins. Per the frozen rule it was registered as
**H2-pcs-spy-qqq-5wide-30delta-eod-v1** (ledger `77583ae1…`, trial 4) with its
honest FAIL. Trial accounting is deliberately conservative: the $5 backtest
counts twice (arm trial_intent + registration).

## The structural story (why wider = less bad, and why all fail)

Per-contract frictions (commissions $2.60 round trip, two crossed half-spreads
per round trip, 1% adverse haircut) are roughly FIXED while credit scales with
width. Measured conservative credits: ~$0.13 at $1 (stop threshold sits inside
day-one quote noise → 12% win rate), ~$0.29 at $2, ~$0.65-0.75 at $5. The
monotone improvement (−185 → −103 → −39 per trade) is the friction share
shrinking. Even at $5 — a single contract using most of the $600 cap — the
CI90 upper bound is −$18.08: **negative expectancy with 90% confidence at
every width in the menu**. The 2×credit stop measured against conservative
cost-to-close remains a large drag at all widths (H1 anatomy: every loss was a
stop; wins only profit-targets).

## Decision

- No width proceeds toward an OOS reveal. **Standing recommendation: spend no
  OOS look on H1 or H2** — in-sample already rejects both with the whole CI
  below zero, and the 3-look lifetime budget is precious.
- $2 remains the committed config default (H1's registered surface). H2's
  reveal, if the owner ever ordered one against recommendation, requires
  restoring the width-5 bytes recorded at its code_sha.
- The sweep menu [1, 2, 5] is exhausted. Any other width — or any change to
  exits, stops, credit floors, or fill assumptions — is a NEW hypothesis and a
  new trial; nothing gets retuned against these results.

## What this does NOT license

The "wider is better" gradient is an in-sample observation under the frozen
cost model. It does not justify registering ever-wider spreads chasing the
gradient (width is capped by the $600 sleeve rule — $5 already sizes to 1
contract), and it does not justify softening the fill model to rescue the
strategy: the conservative model is the point of the harness.
