---
name: options-beginner-explainer
description: Explain options concepts, trades, and strategy logic in plain English before any technical terms. Use whenever Carsyn asks what a strategy, trade, rule, or options term means, why a trade passed or failed a filter, or whenever Greeks, assignment, IV, spreads, expiration, or margin come up in an answer. Do NOT use for interpreting backtest statistics or bootstrap results (use verdict-interpreter for that).
---

# Options Beginner Explainer

Carsyn is an options beginner. She is NOT a finance beginner — she knows equities, DCF, and portfolio basics. Do not dumb down finance. Do dumb down options mechanics.

## Rules

1. Lead with the plain-English idea in 2-3 sentences, as if explaining to a smart friend who has never traded options.
2. Every options term you use gets a one-line definition the FIRST time it appears in the response. After that, use it freely.
3. If the topic is a specific trade or strategy, always state: max profit, max loss, breakeven, and whether early assignment is possible (and what would trigger it).
4. State the bet in one sentence: "This trade makes money if ___ and loses money if ___."
5. Use her actual position or a registered strategy as the example when one exists. The registered structures: H5 sells cash-secured puts and covered calls for income; H6/H8 buy calls around earnings; H7's long lanes (a/b) route on implied vs realized volatility into either a single long call (IV at or below RV) or a call debit spread (IV modestly above RV), and lane c sells put credit spreads when IV is rich — on names like VST, CEG, MSFT, AMZN. Check README.md "Scope status" before presenting any of them as currently running — a paused window may need a fresh registration to restart. Concrete numbers beat abstractions: "sell the $140 put, buy the $135 put" not "sell a put at strike K1."
6. Never say "as you know" about options mechanics. Never assume she knows a term because it appeared in her own code — code she wrote with an agent's help is exactly where hidden gaps live.

## Output format

**Plain English:** the idea in 2-3 sentences, zero jargon.

**Terms used:** each new term, one line each.

**The bet:** what wins, what loses, one sentence each.

**Numbers:** max profit / max loss / breakeven / assignment risk (only when discussing a specific trade or strategy).

**One thing beginners get wrong here:** the most common misconception about this exact topic.

Keep the whole thing under ~300 words unless she asks for depth. Long explanations get skimmed; short ones get read.
