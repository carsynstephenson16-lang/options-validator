---
name: verdict-interpreter
description: Translate backtest statistics into plain English with honest uncertainty. Use whenever presenting or discussing backtest results, bootstrap output, confidence intervals, p-values, Sharpe ratios, win rates, drawdowns, or a PASS/FAIL verdict from the validation harness. Use BEFORE showing raw numbers.
---

# Verdict Interpreter

The validator produces statistical output (stationary bootstrap, confidence intervals, verdicts). Carsyn is building this system while learning the statistics behind it. A number she can't interpret is worse than no number — it creates false confidence.

## Rules

1. Before showing any statistic, state in one sentence what question it answers. Example: "The bootstrap CI answers: if luck had gone differently, what range of results was plausible?"
2. Translate every verdict into a decision-relevant sentence:
   - Not "Sharpe 1.4, CI [0.2, 2.1]" but "The strategy made money in this sample, but the plausible range includes 'barely better than nothing' — this result does not yet distinguish skill from luck."
3. Always state the sample size in trades and in independent-ish market regimes, and say whether it's enough. Fewer than ~100 trades or fewer than 2 distinct regimes = say explicitly the verdict is weak.
4. Never use these words about a backtest result: "proven," "confirmed," "edge found," "works." Allowed vocabulary: "survived this test," "not yet rejected," "rejected," "consistent with zero edge."
5. If a result looks good, your NEXT sentence must be the most likely boring explanation (small sample, one favorable regime, costs underestimated, multiple testing).
6. Distinguish the two failure directions every time:
   - False positive: believing a dead strategy works (costs real money later).
   - False negative: killing a live strategy (costs opportunity). State which error this verdict risks more.

## Output format

**What we tested:** one sentence.

**What the numbers say:** plain English, no raw stats yet.

**The raw stats:** now the table/numbers, each with a one-line "this answers..." label.

**How much to trust it:** sample size, regimes covered, biggest caveat.

**What this verdict does NOT mean:** one or two lines.

**Decision:** what the pre-registered criteria say to do next (not what feels right).
