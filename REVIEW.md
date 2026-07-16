# Code Review Charter — Options Validator

Instructions for the automated PR reviewer (Claude). This is a **strict, token-economical**
review. Deploy focused sub-checks against these rules, then **verify each finding before
posting** — do not report anything you have not confirmed against the diff.

## Operating rules (token discipline)

1. **Review only what changed.** Read the diff and the minimum surrounding context. Do not
   re-read the whole repo or unchanged files.
2. **Scope by file type:**
   - **Review closely:** the research/backtest Python (`harness/**`, `analysis/**`,
     `config.py`, and any other executable code) and `.github/workflows/**`.
   - **Skim only:** dated journals (`2026-*.md`), `docs/**`, `.canvas`/`Untitled*` notes, and
     generated/output data under `data/**`. Do not nitpick their prose or numbers.
   - **Never** flag generated/cached artifacts (`__pycache__`, output data).
3. **Deploy focused sub-checks, then review their work.** Split the code diff into a few narrow
   checks (correctness, methodology-validity, regression-risk). Run each under these rules, then
   **verify** every candidate finding: locate the exact line, state a concrete
   input→wrong-result scenario, and drop it if you cannot. Unverifiable findings are not reported.
4. **Signal over volume.** Report only **confirmed, actionable** issues at **high or medium**
   severity. No style nits, no praise, no summaries. Clean diff → say so in one line and stop.

## What to flag (in priority order)

1. **Backtest / research validity** — look-ahead bias, survivorship bias, using data unavailable
   at decision time, in-sample leakage into an out-of-sample window, mismatched timestamps, or
   any change that would make a validation result overstate edge. This is the highest-severity
   class for a validator whose whole job is an honest verdict.
2. **Correctness** — logic errors, wrong sign/units (Greeks, P&L, contracts vs shares ×100),
   wrong statistical test or degrees of freedom, mis-parsed option chains, edge cases that crash
   (empty data, None, missing expiry/strike).
3. **Loss-gate / ledger integrity** — code that could let a trial bypass its loss gate, or record
   a ledger/paper-window result inconsistently with what the harness actually computed.
4. **Security** — committed secrets/API keys, unsafe request handling, credentials in logs.
5. **Regression risk** — changes that could break existing behavior the tests don't cover; note
   the missing test rather than demanding one.

## Output format

- One short paragraph max of context, only if needed to frame findings.
- Then a list; each finding: `file:line — <one-sentence defect> — <concrete failure scenario>`
  and a minimal suggested fix. Rank most-severe first.
- End with an explicit verdict: **request changes**, **comment**, or **approve** (clean diff).

Keep the whole review tight. A correct, 3-finding review beats an exhaustive one.
