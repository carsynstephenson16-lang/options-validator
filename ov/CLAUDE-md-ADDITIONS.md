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

The live scope gate is README.md "Scope status": H5, H6, H7, and H8 are registered forward-paper hypotheses; task sequencing lives in `PROJECT_STATE.md` (the canonical roadmap — its P0 gate binds), and H7's historical diagnostic is permanently retired. Before adding a new capability, ticker, strategy, or tool, answer: "Does this move one of the live hypotheses toward its declared verdict?" If no, write it into `ideas-parking-lot.md` and continue.
