# M1 — Research Core (chains.py) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One blessed module (`options_researcher/chains.py`) for monthly-expiration selection and ATM/liquidity helpers, with both profilers refactored onto it — no behavior change.

**Architecture:** Pure functions over the cached chain DataFrames (columns: expiration, strike, right, bid, ask, open_interest, iv, delta, gamma, theta, vega). Calendar math (3rd-Friday rule incl. holiday-Thursday) lives here and nowhere else. Liquidity gates come from the existing `data.thetadata_adapter.passes_liquidity` — never re-implemented.

**Tech Stack:** Python 3.12 / uv, pandas, unittest. Run suite: `uv run python -m unittest discover -s tests`.

---

### Task 1: Calendar functions (third_friday, is_monthly)

**Files:**
- Create: `options_researcher/chains.py`
- Test: `tests/test_chains_core.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_chains_core.py"""
import unittest
from datetime import date

from options_researcher.chains import is_monthly, third_friday


class CalendarTests(unittest.TestCase):
    def test_third_friday_known_months(self):
        self.assertEqual(third_friday(2026, 7), date(2026, 7, 17))
        self.assertEqual(third_friday(2024, 6), date(2024, 6, 21))
        self.assertEqual(third_friday(2025, 4), date(2025, 4, 18))

    def test_monthly_is_third_friday(self):
        self.assertTrue(is_monthly(date(2024, 6, 21)))
        self.assertFalse(is_monthly(date(2024, 6, 14)))   # ordinary weekly
        self.assertFalse(is_monthly(date(2024, 6, 28)))

    def test_holiday_thursday_counts_as_monthly(self):
        # 2025-04-18 is Good Friday; listed monthly expiration moves to
        # Thursday 2025-04-17. Both dates classify as monthly.
        self.assertTrue(is_monthly(date(2025, 4, 17)))
        self.assertTrue(is_monthly(date(2025, 4, 18)))
        # A Thursday NOT adjacent to the 3rd Friday is never monthly. (The
        # Thursday immediately BEFORE a 3rd Friday is always classified
        # monthly by design: listed options only expire on such Thursdays
        # via holiday shifts, so the predicate needs no holiday calendar.)
        self.assertFalse(is_monthly(date(2024, 6, 13)))   # Thu before 2nd Friday


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_chains_core -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'options_researcher.chains'`
(If `ImportError ... is not a package`: `options_researcher/` has no
`__init__.py` by design — create an EMPTY `options_researcher/__init__.py`
as part of Step 3; the standalone profiler scripts are unaffected.)

- [ ] **Step 3: Write minimal implementation**

```python
"""options_researcher/chains.py -- blessed monthly-expiration selection.

The monthlies finding (2026-07-04, committed): open interest on all four
universe names concentrates 85-100% in standard MONTHLY expirations, and
nearest-monthly liquidity passes the frozen gates. Every researcher module
selects expirations through THIS module; the 3rd-Friday calendar rule lives
here and nowhere else.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from data.pandas_feed import load_cached_chains
from data.thetadata_adapter import passes_liquidity


def third_friday(year: int, month: int) -> date:
    """The 3rd Friday of a month (always the 15th..21st)."""
    d = date(year, month, 15)
    while d.weekday() != 4:
        d += timedelta(days=1)
    return d


def is_monthly(exp: date) -> bool:
    """Standard listed monthly: the 3rd Friday, or the Thursday immediately
    before it (exchange-holiday Fridays, e.g. Good Friday, shift the listed
    expiration to Thursday). The Thursday case needs no holiday calendar:
    listed equity options never expire on that Thursday EXCEPT via the
    holiday shift, so the adjacency test alone is sufficient on real
    chain data."""
    tf = third_friday(exp.year, exp.month)
    return exp == tf or (exp.weekday() == 3 and exp + timedelta(days=1) == tf)
```

Also create an empty `options_researcher/__init__.py` (zero bytes) so the
package imports.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest tests.test_chains_core -v`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add options_researcher/chains.py options_researcher/__init__.py tests/test_chains_core.py
git commit -m "feat(researcher): chains.py calendar core -- 3rd-Friday monthly rule

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Selection helpers (puts_in_window, nearest_monthly, atm_row, liquid_strikes, load_range)

**Files:**
- Modify: `options_researcher/chains.py` (append)
- Test: `tests/test_chains_core.py` (append)

- [ ] **Step 1: Write the failing tests (append to tests/test_chains_core.py)**

```python
import pandas as pd
from unittest import mock

from options_researcher import chains
from options_researcher.chains import (
    atm_row, liquid_strikes, load_range, nearest_monthly, puts_in_window,
)


def fixture_chain():
    """Two expirations: weekly 2024-06-14 (thin) and monthly 2024-06-21."""
    rows = []
    for exp, oi, delta in (
        ("2024-06-14", 10, -0.48),
        ("2024-06-21", 150, -0.48),
        ("2024-06-21", 200, -0.60),
        ("2024-06-21", 50, -0.30),
    ):
        rows.append({"expiration": exp, "strike": 100.0 - 100 * delta,
                     "right": "P", "bid": 2.00, "ask": 2.10,
                     "open_interest": oi, "iv": 0.30, "delta": delta,
                     "gamma": 0.0, "theta": 0.0, "vega": 0.0})
    rows.append({"expiration": "2024-06-21", "strike": 90.0, "right": "P",
                 "bid": 1.00, "ask": 0.90,       # crossed -> never liquid
                 "open_interest": 500, "iv": 0.30, "delta": -0.20,
                 "gamma": 0.0, "theta": 0.0, "vega": 0.0})
    rows.append({"expiration": "2024-06-21", "strike": 130.0, "right": "C",
                 "bid": 2.00, "ask": 2.10, "open_interest": 300, "iv": 0.30,
                 "delta": 0.48, "gamma": 0.0, "theta": 0.0, "vega": 0.0})
    return pd.DataFrame(rows)


class SelectionTests(unittest.TestCase):
    TODAY = date(2024, 5, 24)

    def test_puts_in_window_filters_right_quotes_and_dte(self):
        win = puts_in_window(fixture_chain(), self.TODAY, 15, 60)
        self.assertTrue((win["right"] == "P").all())
        self.assertNotIn(90.0, win["strike"].values)      # crossed quote out
        self.assertTrue(win["dte"].between(15, 60).all())

    def test_nearest_monthly_skips_weekly(self):
        exp = nearest_monthly(fixture_chain(), self.TODAY)
        self.assertEqual(exp, date(2024, 6, 21))

    def test_nearest_monthly_none_when_no_monthly_in_band(self):
        chain = fixture_chain()
        weekly_only = chain[chain["expiration"] == "2024-06-14"]
        self.assertIsNone(nearest_monthly(weekly_only, self.TODAY))

    def test_atm_row_picks_nearest_abs_delta_for_right(self):
        row = atm_row(fixture_chain(), date(2024, 6, 21))
        self.assertAlmostEqual(float(row["delta"]), -0.48)
        call = atm_row(fixture_chain(), date(2024, 6, 21), right="C")
        self.assertAlmostEqual(float(call["delta"]), 0.48)

    def test_atm_row_none_for_missing_expiration(self):
        self.assertIsNone(atm_row(fixture_chain(), date(2024, 7, 19)))

    def test_liquid_strikes_uses_frozen_gates(self):
        # puts on 2024-06-21: OI 150 ok, 200 ok, 50 below floor, crossed out
        self.assertEqual(liquid_strikes(fixture_chain(), date(2024, 6, 21)), 2)

    def test_load_range_passes_allow_oos_through(self):
        with mock.patch.object(chains, "load_cached_chains",
                               return_value={}) as m:
            load_range("VST", "2024-01-01", "2024-02-01", allow_oos=True)
        m.assert_called_once_with("VST", "2024-01-01", "2024-02-01",
                                  allow_oos=True)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest tests.test_chains_core -v`
Expected: FAIL with `ImportError: cannot import name 'atm_row'`

- [ ] **Step 3: Implement (append to options_researcher/chains.py)**

```python
def load_range(symbol: str, start_iso: str, end_iso: str, *,
               allow_oos: bool = False) -> dict[str, pd.DataFrame]:
    """Cached chains keyed by ISO day. Thin delegation -- the OOS gate stays
    in the data layer. Researcher call sites pass allow_oos=True explicitly
    (disclosed post-2022 look, facts.log PIVOT_4NAME_SCOPE)."""
    return load_cached_chains(symbol, start_iso, end_iso, allow_oos=allow_oos)


def puts_in_window(chain: pd.DataFrame, today: date,
                   min_dte: int, max_dte: int) -> pd.DataFrame:
    """Puts with sane quotes (bid>0, ask>=bid) whose DTE lies in the band.
    Adds exp_date (datetime.date) and dte (int) columns."""
    puts = chain[(chain["right"] == "P") & (chain["bid"] > 0)
                 & (chain["ask"] >= chain["bid"])].copy()
    if puts.empty:
        return puts.assign(exp_date=pd.Series(dtype=object),
                           dte=pd.Series(dtype=int))
    puts["exp_date"] = pd.to_datetime(puts["expiration"]).dt.date
    puts["dte"] = puts["exp_date"].map(lambda e: (e - today).days)
    return puts[(puts["dte"] >= min_dte) & (puts["dte"] <= max_dte)]


def nearest_monthly(chain: pd.DataFrame, today: date, *,
                    min_dte: int = 15, max_dte: int = 60):
    """Earliest MONTHLY expiration inside the DTE band, or None."""
    win = puts_in_window(chain, today, min_dte, max_dte)
    monthlies = sorted(e for e in win["exp_date"].unique() if is_monthly(e))
    return monthlies[0] if monthlies else None


def atm_row(chain: pd.DataFrame, expiration: date, *,
            right: str = "P", target_delta: float = 0.50):
    """Row of `right` on `expiration` with |delta| nearest target, or None."""
    exp_dates = pd.to_datetime(chain["expiration"]).dt.date
    sub = chain[(chain["right"] == right) & (exp_dates == expiration)
                & (chain["bid"] > 0) & (chain["ask"] >= chain["bid"])]
    if sub.empty:
        return None
    return sub.loc[(sub["delta"].abs() - target_delta).abs().idxmin()]


def liquid_strikes(chain: pd.DataFrame, expiration: date, *,
                   right: str = "P") -> int:
    """Rows of `right` on `expiration` passing the FROZEN liquidity gates
    (data.thetadata_adapter.passes_liquidity: OI floor, quote sanity,
    max spread). Never re-implements the gates."""
    exp_dates = pd.to_datetime(chain["expiration"]).dt.date
    sub = chain[(chain["right"] == right) & (exp_dates == expiration)]
    return int(sum(passes_liquidity(r.open_interest, r.bid, r.ask)
                   for r in sub.itertuples()))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_chains_core -v`
Expected: 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add options_researcher/chains.py tests/test_chains_core.py
git commit -m "feat(researcher): monthly/ATM/liquidity selection helpers on frozen gates

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Refactor profile_monthlies.py onto chains.py (no behavior change)

**Files:**
- Modify: `options_researcher/profile_monthlies.py`
- Baseline artifacts: `.tmp/m1_monthlies_before.txt`, `.tmp/m1_monthlies_after.txt`

- [ ] **Step 1: Capture the pre-refactor output (golden baseline)**

Run: `mkdir -p .tmp && uv run python options_researcher/profile_monthlies.py 2>/dev/null > .tmp/m1_monthlies_before.txt && wc -l .tmp/m1_monthlies_before.txt`
Expected: ~60 lines, no errors

- [ ] **Step 2: Refactor — delete the local copies, import from chains**

In `options_researcher/profile_monthlies.py`:
1. Delete the local `third_friday` and `is_monthly` function definitions.
2. Replace the import block additions with:

```python
from options_researcher.chains import is_monthly, third_friday  # noqa: F401
```

3. Everything else stays byte-identical (the OI_FLOOR/SPREAD_MAX display
   constants and day_stats logic are untouched in this task).

- [ ] **Step 3: Diff against the baseline**

Run: `uv run python options_researcher/profile_monthlies.py 2>/dev/null > .tmp/m1_monthlies_after.txt && diff .tmp/m1_monthlies_before.txt .tmp/m1_monthlies_after.txt && echo IDENTICAL`
Expected: `IDENTICAL` (empty diff)

- [ ] **Step 4: Run the full suite**

Run: `uv run python -m unittest discover -s tests`
Expected: all tests PASS (256 + the new chains tests)

- [ ] **Step 5: Commit**

```bash
git add options_researcher/profile_monthlies.py
git commit -m "refactor(researcher): profile_monthlies uses chains.py calendar (output identical)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Refactor profile_tradability.py onto chains.py (no behavior change)

**Files:**
- Modify: `options_researcher/profile_tradability.py`
- Baseline artifacts: `.tmp/m1_trad_before.txt`, `.tmp/m1_trad_after.txt`

- [ ] **Step 1: Capture the pre-refactor output**

Run: `uv run python options_researcher/profile_tradability.py 2>/dev/null > .tmp/m1_trad_before.txt && wc -l .tmp/m1_trad_before.txt`
Expected: ~70 lines, no errors

- [ ] **Step 2: Refactor the per-day put filtering to puts_in_window**

`profile_tradability.py` filters puts with `bid > 0` / `ask >= bid` and a
25–60 DTE window inline (see its day-loop). Replace that inline filtering
with:

```python
from datetime import date as _date

from options_researcher.chains import puts_in_window
```

and inside the day loop, where the script currently builds the
filtered/windowed put frame from `df`, use:

```python
        win = puts_in_window(df, _date.fromisoformat(date_str), 25, 60)
```

then keep the script's existing nearest-to-37-DTE expiry selection and all
downstream stats EXACTLY as they are (this profiler intentionally samples
nearest-37-DTE, NOT nearest-monthly — it is the weekly-fragmentation
detector; do not "fix" it to monthlies).

- [ ] **Step 3: Diff against the baseline**

Run: `uv run python options_researcher/profile_tradability.py 2>/dev/null > .tmp/m1_trad_after.txt && diff .tmp/m1_trad_before.txt .tmp/m1_trad_after.txt && echo IDENTICAL`
Expected: `IDENTICAL`. If the diff is non-empty, the refactor changed
behavior — STOP and reconcile before committing (the committed README
findings cite these numbers).

- [ ] **Step 4: Run the full suite**

Run: `uv run python -m unittest discover -s tests`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add options_researcher/profile_tradability.py
git commit -m "refactor(researcher): profile_tradability uses chains.puts_in_window (output identical)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Self-review notes

- Spec coverage: M1 = chains.py (T1–T2) + both profiler refactors (T3–T4). ✓
- The two profilers keep different expiry selection ON PURPOSE (nearest-37
  vs monthly); T4 Step 2 warns the engineer off "fixing" it.
- `liquid_strikes` reuses `passes_liquidity` — the frozen gates are never
  duplicated (house rule).
- Baselines use committed cache data; IDENTICAL diffs are the no-behavior-
  change proof the README numbers depend on.
