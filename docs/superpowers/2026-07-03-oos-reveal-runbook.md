# OOS reveal runbook — prepared and PAUSED at the owner's door (2026-07-03)

**OWNER DECISION 2026-07-03: reveal DECLINED ("no") — the holdout stays
sealed at 0/3.** This runbook remains the only sanctioned path should that
ever change.

**STANDING RECOMMENDATION: DO NOT REVEAL.** Both registered hypotheses failed
in-sample with their entire CI90 below zero (H1 $2-wide: −$102.79/trade
[−132.61, −74.46]; H2 $5-wide: −$39.07/trade [−61.28, −18.08]). An OOS look
would spend 1 of the 3 lifetime budget slots to confirm an already-rejected
strategy. The holdout's value is for a FUTURE hypothesis that first earns a
positive in-sample case. This runbook exists so the reveal, whenever the owner
orders one, is a single deliberate act with no improvisation.

## State at preparation time (verified 2026-07-03)

- H1 `H1-pcs-spy-qqq-2wide-30delta-eod-v1`: registered, revealable NOW —
  preflight ALL GATES PASS (hashes MATCH, budget 0/3, ledger anchored).
- H2 `H2-pcs-spy-qqq-5wide-30delta-eod-v1`: registered; revealing it would
  first require restoring the width-5 config bytes from its code_sha (a
  one-line commit) — its preflight will show config/source drift until then.
- Budget: **0 of 3 touched.** No oos_attempt records exist.
- Rehearsal: the reveal path is pinned end-to-end by
  tests/test_charge_on_touch.py (attempt-before-backtest ordering, crash
  persistence, budget-by-touch, write-once, registered-scope derivation) —
  rerun the suite on reveal day.

## Reveal-day procedure (owner has said GO for hypothesis X)

1. `uv run ruff check . && uv run pyright && uv run python -m unittest discover -s tests`
   — all green or STOP.
2. `uv run python tools/reveal_preflight.py <hypothesis_id>` — read-only; must
   print ALL GATES WOULD PASS or STOP (it never touches the holdout).
3. `uv run python -m research.cli reveal-oos --hypothesis-id <hypothesis_id>`
   — THE point of no return. Internally: gates → **oos_attempt appended
   (budget charged)** → offline OOS backtest over the registered scope/window
   from the local cache → scoreboard → oos_reveal appended.
4. Immediately: `git add ledger/ && git commit` (the attempt+reveal records),
   then `uv run python -m research.cli verify --anchored`.
5. Report the OOS scoreboard verdict VERBATIM (PASS / FAIL / NO EDGE /
   INSUFFICIENT SAMPLE), update project memory, and stop.

## Hard facts to hold in mind at the door

- **Charge-on-touch:** the budget slot is spent at step 3 the moment the
  attempt record lands — a crash mid-backtest still consumed the look
  (re-running the SAME hypothesis completes that look, never opens a new one).
- **Write-once:** a revealed hypothesis can never reveal again.
- **OOS entry blackout:** entries stop 2026-05-15 (46 days before window end).
- **Expected sample:** OOS is 3.5 years vs in-sample's 5; loss counts should
  clear the >= 10 gate at $2 width on historical density, but INSUFFICIENT
  SAMPLE is a possible honest outcome at $5 (60 losses in 5 IS years → ~40
  expected OOS).
- Any source/config edit after this preparation un-reveals the hypothesis
  until the exact registered bytes are restored (tools/ and docs/ are safely
  OFF the hash surface).
