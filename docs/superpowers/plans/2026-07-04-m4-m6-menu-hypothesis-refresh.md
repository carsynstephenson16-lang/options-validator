# M4–M6 — Structure Menu, First Hypothesis Gate, Refresh — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. M4 is an orchestrator/analyst procedure (writing a decision document, not code); M5 is intentionally NOT planned here (owner-gated); M6 is code.

---

## M4 — Structure menu (procedure, runs after M3 reports are committed)

**Output:** `docs/superpowers/<today>-structure-menu.md` + owner decision.

- [ ] **Step 1: Assemble the inputs.** The committed M3 reports (Studies A,
  B, C), the two profiler tables (README "first profile" + monthlies
  findings), `analysis/feasibility.py` output, and the frozen cost model
  constants from `config.py`.
- [ ] **Step 2: Score each candidate structure per name.** Grid (structure ×
  name): monthly covered call 0.20/0.30/0.40Δ (VST, AMZN — against held
  shares); monthly put credit spread $5-wide 0.30-0.50Δ (MSFT, AMZN);
  monthly call debit spread (MSFT, AMZN); LEAPS-based covered-call
  substitute / PMCC (MSFT, CEG); earnings-aware variants (skip-earnings vs
  hold-through, using Study B numbers). For each cell report: measured
  typical credit/debit (from cached chains at the relevant delta), friction
  estimate (commissions + half-spreads + haircut, from config), friction
  share of premium, sleeve fit under the $600 economic-max-loss cap,
  scoreable-history length, and the failure mode that kills it.
- [ ] **Step 3: Explicit rejects.** Every cell that fails (friction share >
  ~25%, no sleeve fit, insufficient history) gets a one-line reject with
  its number — the menu must show the graveyard, not just survivors.
- [ ] **Step 4: Recommend exactly ONE first hypothesis** with a one-paragraph
  rationale tied to study numbers, plus the validation design it will
  declare (in-era backtest window + forward paper window ≥ 2 earnings
  cycles, per facts.log PIVOT_4NAME_SCOPE).
- [ ] **Step 5: STOP — owner picks or approves.** Nothing registers in M4.

## M5 — First registered hypothesis (GATED; planned only after the M4 pick)

Deliberately unplanned here: its plan is written AFTER the owner picks the
structure, in the H1/H3R pre-registration mold (frozen parameters →
registration → single run → honest record). Engineering already scoped for
that future plan (reusable from the archived H3R plan): strategy registry +
`strategy_id` on ledger records (un-hardcodes `_oos_backtest_trades`),
per-trade P&L decomposition fields, new strategy class in `strategies/`,
power/eligibility pre-check sized to the chosen structure. Writing that plan
before the pick would be the H1 mistake again (structure first, evidence
second).

## M6 — One-command refresh (code; buildable after M2)

**Goal:** `uv run python -m options_researcher.refresh` fetches missing
chain days + closes, rebuilds feature frames, reruns the three studies, and
prints a what-changed summary. Idempotent: skip-if-cached everywhere.

### Task 1: Refresh orchestrator with injectable steps

**Files:**
- Create: `options_researcher/refresh.py`
- Test: `tests/test_refresh.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_refresh.py"""
import unittest

from options_researcher.refresh import run_refresh


class RefreshTests(unittest.TestCase):
    def test_runs_steps_in_order_and_reports(self):
        calls = []
        summary = run_refresh(steps=[
            ("chains", lambda: calls.append("chains") or {"fetched": 3}),
            ("closes", lambda: calls.append("closes") or {"rows_added": 5}),
            ("features", lambda: calls.append("features") or {"symbols": 4}),
        ])
        self.assertEqual(calls, ["chains", "closes", "features"])
        self.assertEqual(summary["chains"], {"fetched": 3})
        self.assertEqual(summary["closes"], {"rows_added": 5})

    def test_step_failure_stops_and_is_reported_loudly(self):
        def boom():
            raise RuntimeError("fetch died")
        with self.assertRaises(RuntimeError):
            run_refresh(steps=[("chains", boom),
                               ("closes", lambda: {"rows_added": 0})])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest discover -s tests -p "test_refresh.py" -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `options_researcher/refresh.py`**

```python
"""options_researcher/refresh.py -- one-command data + research refresh.

Steps run IN ORDER and fail LOUDLY (a dead fetch must never let stale data
masquerade as fresh): 1) chains: cache_runner both windows for the universe
(skip-if-cached), 2) closes: fetch_underlying_eod per symbol from the last
cached date, 3) features: features.build_all(), 4) studies: the three
study mains. Each step returns a small dict merged into the printed
what-changed summary.
"""
from __future__ import annotations


def run_refresh(steps=None) -> dict:
    """Execute (name, fn) steps in order; return {name: result}. Injectable
    for tests; default_steps() wires the real pipeline."""
    summary: dict = {}
    for name, fn in (steps if steps is not None else default_steps()):
        print(f"refresh: {name} ...", flush=True)
        summary[name] = fn()
        print(f"refresh: {name} -> {summary[name]}", flush=True)
    return summary


def default_steps():
    import config
    from data import cache_runner
    from data.underlying_closes import fetch_underlying_eod
    from options_researcher import features
    from options_researcher.studies import (covered_call_income,
                                            earnings_behavior,
                                            iv_vs_realized)

    def chains():
        a = cache_runner.cache_in_sample()
        b = cache_runner.cache_oos_blind()
        return {"in_sample": a, "oos_blind": b}

    def closes():
        out = {}
        for symbol in config.UNIVERSE:
            out[symbol] = fetch_underlying_eod(symbol, "2017-01-01",
                                               config.BACKTEST_END)
        return out

    def feats():
        features.build_all()
        return {"symbols": len(config.UNIVERSE)}

    def studies():
        iv_vs_realized.main()
        earnings_behavior.main()
        covered_call_income.main()
        return {"studies": 3}

    return [("chains", chains), ("closes", closes),
            ("features", feats), ("studies", studies)]


if __name__ == "__main__":
    run_refresh()
```

- [ ] **Step 4: Run tests + full suite**

Run: `uv run python -m unittest discover -s tests -p "test_refresh.py" -v && uv run python -m unittest discover -s tests`
Expected: all PASS (default_steps is exercised only in real refreshes)

- [ ] **Step 5: Commit**

```bash
git add options_researcher/refresh.py tests/test_refresh.py
git commit -m "feat(researcher): one-command refresh orchestrator (fail-loud, injectable)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

### M6 notes

- `fetch_underlying_eod` re-pulls the full range in v1 (ThetaData EOD pulls
  are cheap and store_closes dedupes); incremental-from-last-date is a
  later optimization only if pulls get slow — YAGNI now.
- BACKTEST_END currently caps data at 2026-06-30; extending it is a config
  decision recorded like the last one (blind-extension note), not a silent
  edit inside refresh.

## Self-review notes

- M4 produces a decision document with a mandatory owner STOP; M5 stays
  unplanned by design (anti-H1 rule); M6's only code is a small, injectable
  orchestrator — the heavy lifting stays in the already-tested modules.
- Per-file unittest commands use the discover -p form (the dotted form
  doesn't work in this repo: tests/ has no __init__.py).
