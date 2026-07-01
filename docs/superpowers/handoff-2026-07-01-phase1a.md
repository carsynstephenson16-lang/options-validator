# Handoff — Phase 1A: Research Integrity Foundation

> Paste the fenced block below as the opening message of a NEW session. It is
> self-contained: a fresh Claude has no memory of prior sessions. Everything
> else in this repo is the source of truth; this doc just orients the next run.

---

```markdown
You are a quantitative systems engineer working in the WAT framework
(Workflows/Agents/Tools) on an options-strategy VALIDATION HARNESS. You have no
memory of prior sessions; everything you need is below or in the repo.

# Project in one paragraph
The repo answers ONE question: does a defined-risk options strategy have
POSITIVE EXPECTANCY AFTER REALISTIC COSTS across 2018/2020/2022 regimes? It is
NOT a live bot and places no orders. A "no edge after costs" result is a
SUCCESS. The project's entire value is being a disciplined lie-detector, so
statistical honesty outranks getting a PASS.

# Environment (do this exactly)
- Repo root: /Users/carsynstephenson/Downloads/options-validator
- It IS a git repo (initial commit 1d7e47e). Work on a branch; commit only when asked.
- Python 3.12 via uv. Run code as:  uv run python <script>
- Tests are stdlib unittest, NOT pytest:  uv run python -m unittest discover -s tests
- Use `rg` for searches, not grep.

# Read these before doing anything (current source of truth)
- /Users/carsynstephenson/Downloads/CLAUDE.md   (WAT framework rules)
- README.md          (phase plan; what runs today)
- .cursorrules       (HARD guardrails: no look-ahead; conservative fills; costs
                     on BOTH legs; liquidity filters; don't build a custom engine
                     — use Lumibot; verdict gates on LOSSES, not trades)
- AGENTS.md          (engineering + quant/data rules)
- config.py          (all params; note IN_SAMPLE_END, RISK_SLEEVE=14000,
                     A_SPREAD_WIDTH=2, UNIVERSE, STARTING_CAPITAL≠sleeve)
- metrics.py         (the SCOREBOARD — holds the IID-bootstrap bug below)
- harness/run_backtest.py            (Phase-0 stub; the substrate wires in here)
- analysis/feasibility.py, strategies/base.py, strategies/put_credit_spread.py,
  data/thetadata_adapter.py          (trade structure & why trades correlate)
- docs/superpowers/specs/2026-07-01-reproducible-foundation-design.md
- docs/superpowers/plans/2026-07-01-reproducible-foundation.md
- Memory (persists across sessions; VERIFY any file/line it cites still exists):
  /Users/carsynstephenson/.claude/projects/-Users-carsynstephenson-Downloads-options-validator/memory/MEMORY.md
  + learning-layer-direction.md and phase-1a-research-integrity.md in that folder.

# State: already done (do NOT redo)
Reproducible foundation is complete and committed: uv/pyproject/uv.lock pinned
to 3.12; requirements.txt removed; RISK_SLEEVE=14000 and A_SPREAD_WIDTH=2 set as
the CAPITAL-HONEST, zero-slack threshold config (rationale in config.py);
.claude/ gitignored; README documents the test command; 12 unittest tests pass;
scope narrowed to options-only.

# Your task: design + build PHASE 1A — Research Integrity Foundation
This is ONE narrow spec (research-integrity-foundation-design.md), written and
built BEFORE any ThetaData wiring or backtest. It is the ENFORCEMENT SUBSTRATE
that must be true before run #1, or run #1 records a lie and every later
"learning" step learns from contaminated output. It is NOT the broad learning
layer (that comes last) and it is NOT the statistical gates (Phase 1B, deferred).

ORGANIZING PRINCIPLE (non-negotiable): every integrity guarantee must be CODE or
a HOOK, never a CLAUDE.md/memory rule. Memory/docs are "context, not enforced
configuration." To block an action regardless of what the agent decides, use a
PreToolUse hook. The guarantees live in harness/run_backtest.py + metrics.py +
hooks, not in prose.

Phase 1A components (enforcement substrate only):
1. Append-only, tamper-evident experiment ledger. Log run #1 as it happens
   (don't reconstruct). Per run: hypothesis ID, pre-registered decision
   threshold, code SHA + config hash + cost-model hash + DATA-WINDOW hash,
   in-sample result, out-of-sample result (write-once, timestamped), cumulative
   trial count, verdict. Stub the Phase-1B fields (DSR/PBO) — don't compute them.
2. Pre-registered hypothesis + threshold gate: the hypothesis and its pass
   threshold must be written BEFORE the OOS result field can be populated.
3. Write-once OOS + enforced IN_SAMPLE_END. CONFIRMED: config.IN_SAMPLE_END
   exists but is used by ZERO code today — the split is currently aspirational.
   Enforce IS ≤ 2022-12-31 vs OOS after; OOS window touched ONCE per hypothesis;
   a finite, logged GLOBAL OOS look budget (holdout leaks through the researcher,
   so after ~3–5 hypotheses the window is spent).
4. Trial COUNTER incrementing on INTENT-TO-SELECT (eyeballed configs, discarded
   runs, a width sweep of 3 = 3). Monotonic across the whole program; never
   reset by renaming a failed test as a "new hypothesis."
5. Frozen cost/fill params: SLIPPAGE_HAIRCUT, ASSUMED_CREDIT_FRAC,
   MAX_SPREAD_PCT, MIN_OPEN_INTEREST, fill model. Calibrate on in-sample only,
   then FREEZE (hash them into the ledger) before OOS. These are MORE p-hackable
   than delta/width.
6. Replace the IID bootstrap in metrics.py. _expectancy_ci() (~lines 65-73) does
   rng.choice(pnls, size=len(pnls), replace=True).mean() — an IID resample that
   assumes trades are independent. They are NOT, on TWO axes:
     - Serial: losses cluster in vol regimes (2018 Q4, 2020 Feb–Mar, 2022).
     - Cross-sectional: UNIVERSE = SPY/QQQ/AAPL/MSFT/NVDA ≈ 1.5 independent bets
       (config flags this); the 5 names lose in the same week.
   Effect: variance underestimated → 90% CI too tight → FALSE PASS at the
   loss-gated verdict. FIX: prefer the stationary bootstrap (Politis–Romano) and
   resample by ENTRY-DATE COHORT so BOTH clustering axes survive. A plain
   time-block bootstrap still overstates confidence on the cross-sectional axis —
   cohort resampling is required, not optional. TDD it: a synthetic
   autocorrelated / cross-correlated series where the IID CI under-covers and the
   new method widens appropriately.

# Phase 1B (DEFERRED — do NOT build in 1A)
Deflated Sharpe Ratio, PBO/CSCV, multiple-testing deflation that CONSUMES the
trial counter. At 1A there are ZERO runs, so computing these now is infra for
data you don't have. Stub the ledger fields in 1A; compute in 1B once N runs
exist. And note in the spec: DSR/PBO are WARNINGS behind a min-N guard, never the
certifier — this sample (~1.5 independent bets, low-tens of losses) is likely too
thin to slice, risking laundering a thin sample into false rigor. The real
certifier stays the loss-gated, dependence-aware CI (component 6).

# Two refinements to state explicitly in the spec
1. A single holdout is a WEAK FLOOR, not a guarantee — the PBO paper exists
   because holdouts are unreliable. Enforcing IN_SAMPLE_END makes the system
   "less unsafe," not safe; the ledger + look-budget exist precisely because the
   holdout alone is weak. CSCV/CPCV is the ideal but this sample may be too thin.
2. Bootstrap dependence is 2-D (serial AND cross-sectional) — see component 6.

# Decisions already made — DO NOT relitigate (from memory)
- "Learning" = research memory + overfitting-aware verdicts + agent/workflow
  learning. PARAMETER AUTO-TUNING IS BANNED, and the ban is WIDENED to cost/fill
  params (component 5). Calibrate in-sample only, then freeze before OOS.
- Trial count = intent-to-select, monotonic, non-resettable.
- Don't touch the Phase-0 STUBS (ThetaData fetch, Lumibot strategy adapters)
  unless the task is explicitly to wire them. 1A adds the ledger/OOS/counter
  substrate + fixes metrics.py; it does NOT wire ThetaData.
- Sequence: (1) reproducible-foundation [done] → (2) THIS Phase-1A spec →
  (3) wire ThetaData + first backtest THROUGH the substrate → (4) Phase 1B stats
  → (5) broad learning-layer spec last.

# Process (non-negotiable)
1. Design + creative work → use the superpowers brainstorming skill FIRST. Do
   not write code until the Phase-1A design is approved. Ask clarifying
   questions ONE at a time.
2. Then writing-plans → executing-plans (or subagent-driven-development). TDD:
   failing test first, minimal impl, verify with real command output, commit.
3. Make no "it passes"/"it's fixed" claim without showing the command output.
4. Work on a branch; commit only when the user asks.

# Definition of done for Phase 1A
The enforcement substrate is true BEFORE run #1: an append-only ledger; a
pre-registration gate; write-once OOS with an enforced IN_SAMPLE_END and a global
look budget; a monotonic intent-to-select counter; frozen+hashed cost/fill
params; and a dependence-aware (stationary + entry-date-cohort) bootstrap
replacing the IID one — each enforced by CODE or a HOOK, each covered by a test,
all 12+ existing tests still green, committed on a branch. Phase-1B stat fields
are stubbed, not computed.

# Sources (verified accurate)
Anthropic "Building effective agents"; Claude Code memory docs (memory ≠
enforcement → use PreToolUse hooks); Bailey/Borwein/López de Prado/Zhu PBO
(holdout unreliable → CSCV); Harvey/Liu/Zhu (t>3 multiple-testing hurdle); Carr &
López de Prado (calibrating rules via backtest = overfitting); block-bootstrap
for dependent data (Künsch 1989; Politis–Romano 1994).

Start by: reading the files above, then invoking the brainstorming skill to
design the Phase-1A Research Integrity Foundation. Ask me clarifying questions
one at a time.
```
