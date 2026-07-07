# Options-Validator Skill Pack — Install Guide

## How to install (5 minutes)

1. Unzip this into the ROOT of your `options-validator` repo. It only adds files inside `.claude/` plus this readme and `CLAUDE-md-ADDITIONS.md`. Nothing overwrites your code.
   - One exception: if you already have a `.claude/settings.json`, don't overwrite it — open both files and copy the `"hooks"` block from mine into yours.
2. Open `CLAUDE-md-ADDITIONS.md`, copy everything below the line, paste it at the bottom of your existing `CLAUDE.md`. Then delete `CLAUDE-md-ADDITIONS.md`.
3. Verify the hook works. From the repo root run:
   ```
   printf '%s' '{"tool_input":{"command":"api.submit_order(qty=1)"}}' | python3 .claude/hooks/block_live_trading.py; echo "exit=$?"
   ```
   You should see a BLOCKED message and `exit=2`. Then run it with a harmless command and confirm `exit=0`.
4. Restart Claude Code in the repo. Type `/hooks` to confirm the PreToolUse hook is registered. The skills load automatically from `.claude/skills/`.
5. Commit everything, including `.claude/`, so the guardrails are versioned with the code they guard.

If you also use Codex: copy `.claude/skills/` to `.agents/skills/` (same files, second location). The hook is Claude Code-only — Codex won't enforce it, which is a reason to prefer Claude Code for sessions that write code.

## What's in the pack (7 skills + 1 hook)

| File | Job | One-line reason it exists |
|---|---|---|
| `options-beginner-explainer` | Plain-English options concepts | You can't validate what you can't explain |
| `verdict-interpreter` | Plain-English statistics | Your Phase 1A bootstrap will print numbers you can't yet read — this is the highest-value skill in the pack for you specifically |
| `options-data-audit` | Data quality gate | Bad ThetaData rows = confident garbage |
| `backtest-realism-audit` | Simulation mechanics only | Fantasy fills are how backtests lie |
| `results-red-team` | Statistical validity only | Finds the boring explanation before you believe the exciting one |
| `ledger-discipline` | Prereg + logging enforcement | Makes the agent enforce the hash-chain system you already designed |
| `session-synthesis` | Human Obsidian notes | Decisions and reasons, 250-word cap, rejected ideas required |
| `hooks/block_live_trading.py` | Blocks order-placement code | Deterministic — the agent can't talk its way past it. Fail-closed and tested (8 tests) |
| `repo-health-review` | Read-only improvement proposals | The safe version of your "self-improving agent" idea — see below |

## What I changed from ChatGPT's list, and why

**Cut `source-quality-gate` as a skill → moved into CLAUDE.md.** Its rules (label every claim, no blogs for margin/assignment facts) apply to *every* response, and skills are for *task-triggered* procedures. An always-on rule in a skill either fires constantly (context bloat) or gets missed. Same rules, right layer.

**Cut `strategy-preregistration` as a standalone skill → absorbed into `ledger-discipline`.** Your repo already has a pre-registration gate *in code*. A skill that defines its own separate prereg template creates two sources of truth, and they will drift. The replacement skill enforces the system you built instead of duplicating it, and adds the piece ChatGPT missed: counting hypothesis versions, which is the multiple-testing denominator the red team needs.

**Split the overlap between `backtest-realism-audit` and `results-red-team`.** ChatGPT's versions both covered overfitting, lookahead, and out-of-sample — about 40% overlap. Overlapping skills give you the same critique twice and each one shallower. Now: realism-audit = "could a real account trade this way?" (fills, costs, margin, assignment). Red-team = "do the statistics support the conclusion?" (multiple testing, sample size, regime luck, benchmarks). Each explicitly refuses the other's territory.

**Rewrote `obsidian-capture` → `session-synthesis`.** Yours was the right instinct. Changes: hard 250-word cap (an uncapped template becomes a log dump), every decision must carry its *reason* in plain English, rejected ideas are mandatory content, and there's an explicit anti-pattern list including "optimistic tone drift." The note is for Future Carsyn who remembers nothing — reasons are the only thing she can't regenerate from the repo.

**Added `verdict-interpreter` (not on ChatGPT's list).** The beginner-explainer covers options mechanics, but your actual comprehension gap in Phase 1A is *statistics*: what a bootstrap CI means, why 40 overlapping trades aren't 40 observations, what a verdict does and doesn't license. This skill bans the words "proven" and "works" and forces every good-looking result to be followed by its most boring alternative explanation.

## Your two ideas — straight answers

**Weekly researcher for CEG/VST/MSFT/AMZN news, financials, price moves: NO for this repo, and here's the reasoning.** Your strategy is *systematic* — entries come from delta, DTE, and credit rules, not from narratives. Weekly news analysis feeds zero inputs to those rules. What it *would* do is create a steady drip of stories ("VST dropped on the earnings call...") that tempt you to override the system, which is exactly the discretionary contamination the whole validator exists to prevent. The legitimate 10% of the idea — earnings dates and events matter for assignment risk and gap risk — is now handled where it belongs: the prereg checklist requires an explicit earnings-handling rule, and the realism audit checks it. Narrative research on these companies is real work, but it's `equity-research` repo work. Keeping the two repos separate isn't bureaucracy; it's keeping the discretionary brain and the systematic brain from voting in each other's elections.

**Agent that improves the project automatically: HARD NO, and this one matters.** Your repo's entire value proposition is an append-only ledger, frozen parameters, and pre-registration — i.e., *nothing changes without a logged human decision.* An agent that autonomously "improves" the project is the exact threat model that design defends against. Concretely: an auto-improver that touches strategy code is automated p-hacking; one that touches validation code silently changes what every past PASS/FAIL meant; and either way the ledger's guarantee ("this result came from this frozen config") is broken. The version of the idea that survives is `repo-health-review`: run it *when you ask*, it reads everything, changes nothing, and hands you a prioritized proposal list — including whether your guardrails themselves have tests, which right now is the most likely gap. You stay the only one who commits changes.

## The one thing to actually do next

None of this pack finds you an edge — you said the project "does not provide any edge," and skills won't change that, because skills change *process*, not *alpha*. What they change is whether you can trust a verdict when you get one. So the priority stays what it was: finish Phase 0, run the pre-registered backtest, get one honest verdict — probably "rejected" or "consistent with zero edge," and that's a successful outcome, because the system worked. Install the pack, then go run the test.
