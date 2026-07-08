# Options Validator Project State and NotebookLM Brief - 2026-07-03

Tags: #options-validator #project-state #notebooklm #research-integrity

## Purpose

This note updates the Obsidian vault with the current state of the project and
packages the evidence for NotebookLM-style review. It is deliberately
evidence-bound: no invented market facts, no live-trading recommendation, and no
post-hoc strategy rescue.

## Bottom Line

The current Strategy A put credit spread did not work after realistic costs.
That is not a project failure. It is the harness doing its job: reject a weak
strategy in-sample before spending a scarce out-of-sample look or risking real
money.

Standing recommendation: do not reveal H1 or H2 OOS. The holdout budget remains
valuable only if saved for a future hypothesis that first earns a positive,
pre-registered in-sample case.

## Registered Hypotheses

| Hypothesis | Width | Scope | IS trades | IS losses | Expectancy/trade | CI90 | Verdict | OOS state |
|---|---:|---|---:|---:|---:|---|---|---|
| H1-pcs-spy-qqq-2wide-30delta-eod-v1 | $2 | SPY/QQQ | 226 | 113 | -$102.79 | [-$132.61, -$74.46] | FAIL | Unrevealed |
| H2-pcs-spy-qqq-5wide-30delta-eod-v1 | $5 | SPY/QQQ | 196 | 60 | -$39.07 | [-$61.28, -$18.08] | FAIL | Unrevealed |

H1 remains revealable from the current committed $2 configuration. H2 is
registered but would require restoring the exact width-5 config bytes from its
registered code SHA before any reveal preflight could pass. Both should remain
unrevealed unless the owner deliberately overrules the standing recommendation.

## Width Sweep Result

| Width | Trades | Win rate | Losses | Expectancy/trade | CI90 | Verdict |
|---:|---:|---:|---:|---:|---|---|
| $1 | 356 | 12.4% | 312 | -$185.17 | [-$204.92, -$164.12] | FAIL |
| $2 | 226 | 50.0% | 113 | -$102.79 | [-$132.61, -$74.46] | FAIL |
| $5 | 196 | 69.4% | 60 | -$39.07 | [-$61.28, -$18.08] | FAIL |

The sweep says "wider is less bad," not "wider works." The best tested arm
still has a negative upper confidence bound. Spending an OOS look now would
mostly confirm a result the in-sample evidence has already rejected.

## Single-Name Diagnostics

The unregistered single-name diagnostics did not uncover a hidden edge:

| Symbol | Outcome |
|---|---|
| MSFT | FAIL |
| AAPL | FAIL |
| NVDA | Insufficient sample: 4 trades, 1 loss |
| VST | Zero trades |
| PLTR | FAIL |
| AMZN | FAIL |
| NOW | Zero trades |

The practical 9-name universe was not operationally real at $2 width. Strike
spacing, open interest, quote width, and listing-window effects left SPY/QQQ as
the only robust registered scope. The diagnostics are descriptive only and must
not feed a verdict, scope change, or parameter retune.

## Why The Strategy Failed

- Per-contract frictions are roughly fixed while credit scales with spread
  width. Narrow spreads are crushed by commissions, crossed spreads, and the
  slippage haircut.
- The conservative model measured real credits well below the earlier
  feasibility assumption. H1's median conservative entry credit was about
  $0.29 on a $2-wide spread, while feasibility had assumed $0.60.
- The 2x-credit stop measured against conservative cost-to-close was a major
  drag. H1's loss anatomy was dominated by stops, while wins were profit-target
  exits.
- Some stress exits crossed crisis-blown quotes and exceeded entry-time
  defined-risk estimates. The run captured this honestly rather than hiding it.
- Single names added sparse, regime-biased fragments rather than clean
  diversification.

## What Is Working

The research harness is useful even though this strategy failed:

- Python 3.12 and `uv` environment are pinned.
- Offline chain cache and Pandas/Lumibot backtesting path are wired.
- Conservative bid/ask-plus-haircut fill path is implemented.
- Strategy closed trades are extracted from engine fills.
- In-sample versus OOS windows are enforced.
- Pre-registration, source/config/cost hashing, and append-only ledger exist.
- Dependence-aware weekly-cohort CI replaced the old IID bootstrap.
- Charge-on-touch OOS logging and reveal preflight/runbook exist.
- Ledger verification passed on 2026-07-03 with `ledger OK`.

This project should still be treated as a validation harness, not a live scanner
or trading bot.

## Current Decision

Do not reveal H1 or H2 OOS.

Do not use the width gradient to chase wider spreads. $5 is already the least
bad tested width and still failed with a negative CI90 upper bound. Do not
soften fills, relax liquidity, broaden scope, or adjust stops to rescue this
result.

Any future strategy work must start as a new pre-registered hypothesis with a
mechanism-level change. A new hypothesis should be distinct enough that it is
not just parameter shopping around a failed record.

## NotebookLM Role

There is no direct NotebookLM connector available in this Codex session. The
best available involvement is to prepare this note as a source packet that can
be uploaded to NotebookLM alongside the project evidence below.

NotebookLM may be useful for:

- Producing an outside synthesis of why H1/H2 failed.
- Finding contradictions or stale docs in the project narrative.
- Separating genuine future hypotheses from post-hoc retuning.
- Turning the evidence into a concise owner-facing decision memo.

NotebookLM must not be used for:

- Changing a verdict.
- Deciding to spend an OOS look.
- Inventing missing data or current market facts.
- Recommending live trading.
- Retuning parameters against the failed results.

## NotebookLM Source Set

Upload or attach these files as sources:

- `README.md`
- `AGENTS.md`
- `config.py`
- `ledger/experiments.jsonl`
- `docs/superpowers/specs/2026-07-03-h1-preregistration-scope-decision.md`
- `docs/superpowers/2026-07-03-width-sweep-decision.md`
- `docs/superpowers/2026-07-03-single-name-diagnostics.md`
- `docs/superpowers/2026-07-03-offline-pandas-backtesting-spike.md`
- `docs/superpowers/2026-07-03-oos-reveal-runbook.md`
- This file: `docs/superpowers/2026-07-03-project-state-notebooklm-brief.md`

Optional source if token budget allows:

- `metrics.py`
- `harness/run_backtest.py`
- `strategies/put_credit_spread.py`
- `data/pandas_feed.py`

## NotebookLM Prompt Pack

Use these questions:

1. Summarize the project state in one page for the owner. Emphasize whether the
   strategy worked, whether OOS should be revealed, and what remains valuable.
2. Identify any contradictions between the README, ledger, and 2026-07-03
   superpowers docs. Which docs look stale?
3. Explain why $5-wide was least bad but still not investable evidence.
4. List the strongest reasons not to spend an OOS look on H1 or H2.
5. Propose criteria that would make a future hypothesis genuinely new rather
   than parameter retuning of a failed strategy.
6. Identify any project risks that are operational or data-quality issues rather
   than strategy-edge issues.

## Source Links

- [[2026-07-03]]
- [[2026-07-03-width-sweep-decision]]
- [[2026-07-03-single-name-diagnostics]]
- [[2026-07-03-offline-pandas-backtesting-spike]]
- [[2026-07-03-oos-reveal-runbook]]
- [[specs/2026-07-03-h1-preregistration-scope-decision]]
