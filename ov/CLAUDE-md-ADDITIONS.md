# Paste this section into your existing CLAUDE.md

(Do not replace your CLAUDE.md — append this. These are always-on rules, which is why they live here instead of in a skill: a skill triggers on specific tasks, but these apply to every single response.)

---

## Claim discipline (always on)

Every important factual claim about options mechanics, broker behavior, margin, assignment, fees, or data gets one of these labels:

- **Repo-verified** — I read it in this repo's code/tests
- **Test-verified** — a test in this repo proves it
- **Official-source** — OCC, Cboe, FINRA, SEC, exchange, or broker documentation (link it)
- **Inference** — I reasoned to it; here's the reasoning
- **Assumption** — unverified; treat as possibly wrong

Never cite blogs, Reddit, YouTube, or forums for assignment, margin, fills, or fees when an official source exists. If sources conflict, say so instead of picking one silently.

## Vocabulary discipline (always on)

Banned words about backtest results: "proven," "confirmed," "edge found," "works," "guaranteed."
Allowed: "survived this test," "not yet rejected," "rejected," "consistent with zero edge."

## Project boundary (always on)

This repo is a validator. It never places orders, never connects to a live brokerage endpoint, never disables paper mode. A hook enforces this; do not attempt to work around the hook, and treat a hook block as correct by default.

## Scope guard (always on)

Current phase: Phase 0 — get one strategy to one honest verdict. Before adding any new capability, ticker, strategy, or tool, answer in one sentence: "Does this move the current phase to a verdict?" If no, write the idea into `ideas-parking-lot.md` and continue the phase. Parked ideas are not rejected ideas; they're just not now.
