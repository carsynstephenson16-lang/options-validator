# M3 — Behavior Studies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three small, tested study modules that turn cached data into committed fact reports: (a) does high IV rank precede bigger realized moves, (b) what earnings do to IV and price, (c) what monthly covered calls on VST/AMZN would have earned vs buy-and-hold.

**Architecture:** Each study is a pure `compute_*` function (fixture-testable, returns DataFrames/dicts) plus a thin `main` that loads real data (features/closes/chains/earnings, `allow_oos=True` disclosed), writes `reports/YYYY-MM-DD-<study>.md`, and appends one facts.log headline. No study issues verdicts; wording in reports stays descriptive.

**Tech Stack:** Python 3.12 / uv, pandas, unittest. Suite: `uv run python -m unittest discover -s tests`.

**Depends on:** M1 (chains.py), M2 (underlying_closes, features incl. cached frames, earnings loader), earnings CSVs present, closes pulled.

**Shared conventions (all three tasks):** reports directory `reports/` is created if absent and reports ARE committed (they're the project's factual record); every report head-notes its data window and the disclosure line; costs use `config.SLIPPAGE_HAIRCUT` and `config.COMMISSION_PER_CONTRACT` — never literals.

---

### Task 1: Study A — IV rank vs subsequent realized moves

**Files:**
- Create: `options_researcher/studies/__init__.py` (empty), `options_researcher/studies/iv_vs_realized.py`
- Test: `tests/test_study_iv_vs_realized.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_study_iv_vs_realized.py"""
import unittest

import numpy as np
import pandas as pd

from options_researcher.studies.iv_vs_realized import compute_iv_vs_realized


def fixture_features():
    """400 bdays: first 200 calm (iv .20, tiny moves), last 200 wild
    (iv .60, big moves) -- high-rank days should show larger forward vol."""
    idx = pd.bdate_range("2020-01-02", periods=400).strftime("%Y-%m-%d")
    close = [100.0]
    rng = np.random.default_rng(7)
    for i in range(1, 400):
        step = 0.001 if i < 200 else 0.03
        close.append(close[-1] * (1 + rng.choice([-1, 1]) * step))
    f = pd.DataFrame(index=idx)
    f["close"] = close
    f["atm_iv"] = [0.20] * 200 + [0.60] * 200
    f["iv_rank"] = [0.10] * 200 + [0.90] * 200
    f["earnings_week"] = False
    return f


class StudyATests(unittest.TestCase):
    def test_high_rank_bucket_shows_higher_forward_vol(self):
        out = compute_iv_vs_realized(fixture_features(), horizon_bd=21)
        hi = out[out["bucket"] == "iv_rank>=0.70"]["fwd_rv_median"].iloc[0]
        lo = out[out["bucket"] == "iv_rank<=0.30"]["fwd_rv_median"].iloc[0]
        self.assertGreater(hi, lo)

    def test_buckets_report_counts_and_iv(self):
        out = compute_iv_vs_realized(fixture_features(), horizon_bd=21)
        self.assertEqual(set(out.columns),
                         {"bucket", "n_days", "iv_median", "fwd_rv_median",
                          "fwd_absmove_median_pct", "implied_move_median_pct"})
        self.assertTrue((out["n_days"] > 0).all())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_study_iv_vs_realized -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `options_researcher/studies/iv_vs_realized.py`**

```python
"""Study A: does a high IV rank actually precede larger realized moves?

Descriptive only. For days in each iv_rank bucket (>=0.70 vs <=0.30,
earnings weeks excluded to keep the comparison clean), measure the NEXT
`horizon_bd` business days: annualized realized vol and |total move|, and
compare with the move the option market implied (atm_iv * sqrt(h/252)).
An honest "no relationship" result is a fully successful outcome.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

HI, LO = 0.70, 0.30


def _forward_stats(close: pd.Series, horizon_bd: int):
    logret = np.log(close.astype(float)).diff()
    fwd_rv = (logret.rolling(horizon_bd).std(ddof=1) * np.sqrt(252.0)
              ).shift(-horizon_bd)
    fwd_move = (close.shift(-horizon_bd) / close - 1.0).abs()
    return fwd_rv, fwd_move


def compute_iv_vs_realized(features: pd.DataFrame, *,
                           horizon_bd: int = 21) -> pd.DataFrame:
    f = features[~features["earnings_week"].astype(bool)].copy()
    fwd_rv, fwd_move = _forward_stats(f["close"], horizon_bd)
    f["fwd_rv"], f["fwd_move"] = fwd_rv, fwd_move
    f = f.dropna(subset=["iv_rank", "atm_iv", "fwd_rv", "fwd_move"])

    rows = []
    for name, mask in (("iv_rank>=0.70", f["iv_rank"] >= HI),
                       ("iv_rank<=0.30", f["iv_rank"] <= LO)):
        g = f[mask]
        implied = g["atm_iv"] * np.sqrt(horizon_bd / 252.0)
        rows.append({
            "bucket": name,
            "n_days": int(len(g)),
            "iv_median": float(g["atm_iv"].median()),
            "fwd_rv_median": float(g["fwd_rv"].median()),
            "fwd_absmove_median_pct": float(100 * g["fwd_move"].median()),
            "implied_move_median_pct": float(100 * implied.median()),
        })
    return pd.DataFrame(rows)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_study_iv_vs_realized -v`
Expected: 2 tests PASS

- [ ] **Step 5: Add the report entrypoint (append to the same file)**

```python
def main():
    import os
    from datetime import date as _date

    import config
    from options_researcher.features import load_features
    from research.facts import append_fact

    os.makedirs("reports", exist_ok=True)
    today = _date.today().isoformat()
    lines = [f"# Study A — IV rank vs subsequent realized moves ({today})",
             "", "Descriptive; earnings weeks excluded; horizon 21 business "
             "days. Post-2022 data disclosed (facts.log PIVOT_4NAME_SCOPE).",
             ""]
    for symbol in config.UNIVERSE:
        table = compute_iv_vs_realized(load_features(symbol))
        lines += [f"## {symbol}", "", table.to_markdown(index=False), ""]
        hi = table.iloc[0]
        append_fact(
            f"STUDY_A {symbol}: iv_rank>=0.70 days n={hi['n_days']} "
            f"iv_med={hi['iv_median']:.3f} fwd_rv_med={hi['fwd_rv_median']:.3f}")
    path = f"reports/{today}-study-a-iv-vs-realized.md"
    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Full suite, then commit**

Run: `uv run python -m unittest discover -s tests`
Expected: all PASS

```bash
git add options_researcher/studies/ tests/test_study_iv_vs_realized.py
git commit -m "feat(studies): Study A -- IV rank vs subsequent realized moves

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Study B — earnings behavior (IV run-up, crush, move size)

**Files:**
- Create: `options_researcher/studies/earnings_behavior.py`
- Test: `tests/test_study_earnings.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_study_earnings.py"""
import unittest
from datetime import date

import pandas as pd

from options_researcher.studies.earnings_behavior import compute_earnings_behavior


def fixture():
    idx = pd.bdate_range("2024-01-02", periods=40).strftime("%Y-%m-%d")
    f = pd.DataFrame(index=idx)
    f["close"] = 100.0
    f["atm_iv"] = 0.30
    # earnings on day 20: IV ramps into it, crushes after; price gaps 5%
    f.iloc[10:20, f.columns.get_loc("atm_iv")] = [0.32 + i * 0.01 for i in range(10)]
    f.iloc[20, f.columns.get_loc("atm_iv")] = 0.25          # post-crush
    f.iloc[20:, f.columns.get_loc("close")] = 105.0
    e = [date.fromisoformat(idx[19])]                        # amc on day 19
    return f, e


class StudyBTests(unittest.TestCase):
    def test_measures_runup_crush_and_move(self):
        f, e = fixture()
        out = compute_earnings_behavior(f, e)
        self.assertEqual(len(out), 1)
        row = out.iloc[0]
        self.assertGreater(row["iv_runup"], 0.05)            # ramped ~.09
        self.assertLess(row["iv_crush"], -0.10)              # .41 -> .25
        self.assertAlmostEqual(row["abs_move_pct"], 5.0, places=1)

    def test_skips_events_without_data_margin(self):
        f, _ = fixture()
        out = compute_earnings_behavior(f, [date(2030, 1, 15)])
        self.assertEqual(len(out), 0)                        # off the frame
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_study_earnings -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `options_researcher/studies/earnings_behavior.py`**

```python
"""Study B: what earnings actually do to these names' options.

Per announcement e (using feature-frame rows, which are trading days):
  iv_runup  = atm_iv(last day <= e) - atm_iv(10 trading rows earlier)
  iv_crush  = atm_iv(first day > e) - atm_iv(last day <= e)
  abs_move_pct = |close(first day > e) / close(last day < e-window) - 1|
      measured close(day before announcement day) -> close(day after), so
      amc and bmo releases are both bracketed.
Events without a full bracket in the frame are SKIPPED (fail closed).
"""
from __future__ import annotations

from datetime import date

import pandas as pd


def compute_earnings_behavior(features: pd.DataFrame,
                              earnings: list[date]) -> pd.DataFrame:
    idx = list(features.index)
    rows = []
    for e in earnings:
        iso = e.isoformat()
        at_or_before = [i for i, d in enumerate(idx) if d <= iso]
        after = [i for i, d in enumerate(idx) if d > iso]
        if not at_or_before or not after or at_or_before[-1] < 10:
            continue
        i0, i1 = at_or_before[-1], after[0]
        iv = features["atm_iv"]
        close = features["close"]
        if pd.isna(iv.iloc[i0]) or pd.isna(iv.iloc[i1]) or pd.isna(iv.iloc[i0 - 10]):
            continue
        rows.append({
            "earnings_date": iso,
            "iv_runup": float(iv.iloc[i0] - iv.iloc[i0 - 10]),
            "iv_crush": float(iv.iloc[i1] - iv.iloc[i0]),
            "abs_move_pct": float(100 * abs(close.iloc[i1] / close.iloc[i0 - 1] - 1)),
        })
    return pd.DataFrame(rows,
                        columns=["earnings_date", "iv_runup", "iv_crush",
                                 "abs_move_pct"])


def main():
    import os
    from datetime import date as _date

    import config
    from options_researcher.earnings import load_earnings
    from options_researcher.features import load_features
    from research.facts import append_fact

    os.makedirs("reports", exist_ok=True)
    today = _date.today().isoformat()
    lines = [f"# Study B — earnings behavior ({today})", "",
             "Descriptive. Post-2022 data disclosed (facts.log "
             "PIVOT_4NAME_SCOPE).", ""]
    for symbol in config.UNIVERSE:
        table = compute_earnings_behavior(load_features(symbol),
                                          load_earnings(symbol))
        med = table[["iv_runup", "iv_crush", "abs_move_pct"]].median()
        lines += [f"## {symbol} — {len(table)} events", "",
                  f"Medians: run-up {med['iv_runup']:+.3f}, crush "
                  f"{med['iv_crush']:+.3f}, |move| {med['abs_move_pct']:.2f}%",
                  "", table.to_markdown(index=False), ""]
        append_fact(f"STUDY_B {symbol}: n={len(table)} "
                    f"runup_med={med['iv_runup']:+.3f} "
                    f"crush_med={med['iv_crush']:+.3f} "
                    f"absmove_med={med['abs_move_pct']:.2f}%")
    path = f"reports/{today}-study-b-earnings.md"
    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests, full suite, commit**

Run: `uv run python -m unittest tests.test_study_earnings -v && uv run python -m unittest discover -s tests`
Expected: all PASS

```bash
git add options_researcher/studies/earnings_behavior.py tests/test_study_earnings.py
git commit -m "feat(studies): Study B -- earnings IV run-up/crush and move size

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Study C — covered-call income on VST/AMZN vs buy-and-hold

**Files:**
- Create: `options_researcher/studies/covered_call_income.py`
- Test: `tests/test_study_covered_call.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_study_covered_call.py"""
import unittest

import pandas as pd

import config
from options_researcher.studies.covered_call_income import compute_cc_cycles


def chain(iso_exp, strike, delta, bid):
    return pd.DataFrame([{"expiration": iso_exp, "strike": strike,
                          "right": "C", "bid": bid, "ask": bid + 0.10,
                          "open_interest": 500, "iv": 0.40, "delta": delta,
                          "gamma": 0.0, "theta": 0.0, "vega": 0.0}])


class CoveredCallTests(unittest.TestCase):
    def test_two_cycles_one_assignment(self):
        # Cycle 1: roll 2024-05-17, expiry 2024-06-21 (real 3rd Fridays).
        # Sell 0.30d call K=110 for bid 2.00; close at expiry 105 -> keep
        # premium, not assigned. Cycle 2: roll 2024-06-21, expiry 2024-07-19,
        # K=112, bid 2.00; close 120 -> assigned at 112.
        closes = pd.Series({"2024-05-17": 100.0, "2024-06-21": 105.0,
                            "2024-07-19": 120.0})
        chains = {"2024-05-17": chain("2024-06-21", 110.0, 0.30, 2.00),
                  "2024-06-21": chain("2024-07-19", 112.0, 0.30, 2.00)}
        out = compute_cc_cycles("VST", closes, chains, target_delta=0.30)
        self.assertEqual(len(out), 2)
        c1, c2 = out.iloc[0], out.iloc[1]

        haircut, comm = config.SLIPPAGE_HAIRCUT, config.COMMISSION_PER_CONTRACT
        credit = 2.00 * (1 - haircut) * 100 - comm
        self.assertFalse(bool(c1["assigned"]))
        self.assertAlmostEqual(c1["cc_pnl"], (105 - 100) * 100 + credit, places=2)
        self.assertAlmostEqual(c1["bh_pnl"], 500.0, places=2)
        self.assertTrue(bool(c2["assigned"]))
        # assigned: stock sold at 112, upside above capped
        self.assertAlmostEqual(c2["cc_pnl"], (112 - 105) * 100 + credit, places=2)
        self.assertAlmostEqual(c2["bh_pnl"], (120 - 105) * 100, places=2)
        self.assertLess(c2["cc_pnl"], c2["bh_pnl"])   # capped upside, stated

    def test_skips_cycle_when_no_delta_band_call(self):
        closes = pd.Series({"2024-05-17": 100.0, "2024-06-21": 105.0})
        chains = {"2024-05-17": chain("2024-06-21", 110.0, 0.05, 2.00)}
        out = compute_cc_cycles("VST", closes, chains, target_delta=0.30)
        self.assertEqual(len(out), 0)                 # fail closed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_study_covered_call -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `options_researcher/studies/covered_call_income.py`**

```python
"""Study C: monthly covered calls on the owner's share names (VST, AMZN)
vs buy-and-hold. DESCRIPTIVE INCOME TABLE, not a verdict.

Cycle definition: roll day r = a monthly expiration present in the cache
(or the first cached day for the opening cycle); at r, sell 1 call per 100
shares at the strike whose delta is nearest `target_delta` (accepted band
target +/- 0.15, else the cycle is SKIPPED -- fail closed) on the nearest
monthly expiration e; credit = bid*(1-haircut)*100 - commission (one leg,
one way; expiring options aren't closed). At e: assigned iff close(e) > K
(shares notionally sold at K and re-bought at close(e) frictionlessly --
stated simplification); cc_pnl = (min(close(e),K) - close(r))*100 + credit;
bh_pnl = (close(e) - close(r))*100. Dividends ignored on BOTH sides
(stated; slightly flatters neither leg's comparison).

The benchmark is buy-and-hold on the same shares: premium income's cost is
capped upside, and every report says so.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

import config
from options_researcher.chains import atm_row, nearest_monthly

DELTA_BAND = 0.15


def compute_cc_cycles(symbol: str, closes: pd.Series,
                      chains: dict[str, pd.DataFrame], *,
                      target_delta: float = 0.30) -> pd.DataFrame:
    rows = []
    days = sorted(chains)
    r = days[0]
    while True:
        today = date.fromisoformat(r)
        exp = nearest_monthly(chains[r], today) if r in chains else None
        if exp is None:
            break
        call = atm_row(chains[r], exp, right="C", target_delta=target_delta)
        e_iso = exp.isoformat()
        if e_iso not in closes.index or r not in closes.index:
            break
        if call is not None and abs(abs(float(call["delta"])) - target_delta) <= DELTA_BAND:
            k = float(call["strike"])
            credit = (float(call["bid"]) * (1 - config.SLIPPAGE_HAIRCUT) * 100
                      - config.COMMISSION_PER_CONTRACT)
            c_r, c_e = float(closes[r]), float(closes[e_iso])
            assigned = c_e > k
            rows.append({
                "roll_date": r, "expiry": e_iso, "strike": k,
                "delta": float(call["delta"]), "credit": credit,
                "assigned": assigned,
                "cc_pnl": (min(c_e, k) - c_r) * 100 + credit,
                "bh_pnl": (c_e - c_r) * 100,
            })
        nxt = [d for d in days if d >= e_iso]
        if not nxt or nxt[0] == r:
            break
        r = nxt[0]
    return pd.DataFrame(rows, columns=["roll_date", "expiry", "strike",
                                       "delta", "credit", "assigned",
                                       "cc_pnl", "bh_pnl"])


def main():
    import os
    from datetime import date as _date

    from data.underlying_closes import load_closes
    from options_researcher.chains import load_range
    from research.facts import append_fact

    os.makedirs("reports", exist_ok=True)
    today = _date.today().isoformat()
    eras = {"VST": "2023-01-01", "AMZN": "2018-01-02"}
    lines = [f"# Study C — monthly covered-call income vs buy-and-hold ({today})",
             "", "Descriptive income table, NOT a verdict. Benchmark is "
             "buy-and-hold on the same shares: premium's cost is capped "
             "upside. Frictionless share re-buy after assignment and no "
             "dividends on either side are stated simplifications. "
             "Post-2022 data disclosed (facts.log PIVOT_4NAME_SCOPE).", ""]
    for symbol, start in eras.items():
        closes = load_closes(symbol, start, config.BACKTEST_END,
                             allow_oos=True)
        chains = load_range(symbol, start, config.BACKTEST_END,
                            allow_oos=True)
        lines.append(f"## {symbol} (from {start})\n")
        for delta in (0.20, 0.30, 0.40):
            t = compute_cc_cycles(symbol, closes, chains, target_delta=delta)
            if t.empty:
                lines.append(f"- {delta:.2f}Δ: no scoreable cycles\n")
                continue
            cc, bh = t["cc_pnl"].sum(), t["bh_pnl"].sum()
            lines += [f"### target delta {delta:.2f} — {len(t)} cycles, "
                      f"{int(t['assigned'].sum())} assigned",
                      f"- premium collected: ${t['credit'].sum():,.0f}; "
                      f"CC total: ${cc:,.0f}; buy-and-hold: ${bh:,.0f}; "
                      f"difference: ${cc - bh:,.0f}",
                      f"- worst cycle (CC): ${t['cc_pnl'].min():,.0f}", ""]
            append_fact(f"STUDY_C {symbol} d={delta:.2f}: cycles={len(t)} "
                        f"assigned={int(t['assigned'].sum())} "
                        f"cc_total={cc:,.0f} bh_total={bh:,.0f}")
    path = f"reports/{today}-study-c-covered-calls.md"
    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests, full suite, commit**

Run: `uv run python -m unittest tests.test_study_covered_call -v && uv run python -m unittest discover -s tests`
Expected: all PASS

```bash
git add options_researcher/studies/covered_call_income.py tests/test_study_covered_call.py
git commit -m "feat(studies): Study C -- covered-call cycles vs buy-and-hold (descriptive)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Orchestrator-only follow-ups

Run the three `main()`s once data prerequisites exist, sanity-check the
tables against the committed profiler numbers, commit `reports/*.md` +
facts.log together as the M3 milestone commit.

## Self-review notes

- All three `compute_*` functions are pure and fixture-tested with golden
  numbers; `main()`s only orchestrate IO.
- Study C charges haircut + commission from config (never literals), skips
  cycles fail-closed when no call sits in the delta band, and every report
  restates the buy-and-hold benchmark caveat.
- Study A excludes earnings weeks so Study B owns that variance.
