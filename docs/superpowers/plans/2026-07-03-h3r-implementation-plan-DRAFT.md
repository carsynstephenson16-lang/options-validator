# H3R Implementation Plan (DRAFT — owner approval required before ANY step runs)

> **ARCHIVED (2026-07-03, later same day):** scope pivoted to 4-name research
> before approval; this plan never executed. Tasks 1 (P&L decomposition),
> 4 (underlying closes), 6 (feature frame + lagged provider), and 8 (strategy
> registry / un-hardcoded reveal path) remain directly reusable for the
> 4-name platform and are referenced by the pivot roadmap.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **OWNER GATE:** This plan is a DRAFT deliverable. No task below — including
> commits — executes until the owner approves (a) the pre-registration spec
> `docs/superpowers/specs/2026-07-03-h3r-preregistration-DRAFT.md`, (b) the
> close-series data source (Task 4), and (c) implementation itself. The plan
> deliberately ENDS before registration/backtest: those are owner-gated steps
> in the spec, not engineering tasks.

**Goal:** Everything H3R needs to be registerable — data, features, strategy,
harness generalization, gates — committed and green BEFORE registration, so
the source-hash freeze never bricks the reveal path.

**Architecture:** Direct underlying closes become a new blind-pull cache with
an OOS-gated loader. A deterministic feature frame (RV/SMA/ATM-IV/VRP
percentile) feeds a lag-enforcing provider injected through a new harness
`extra_parameters` passthrough into a `PutCreditSpread` subclass that adds a
signal gate, ATM delta band, credit floor, and DTE-only exits. The reveal
path resolves the strategy class from a `strategy_id` field on the
registration record instead of a hardcoded import.

**Tech Stack:** Python 3.12 / uv, pandas, unittest, existing Lumibot offline
harness. Run suite with `uv run python -m unittest discover -s tests`.

---

### Task 1: Per-trade P&L decomposition fields

**Files:**
- Modify: `strategies/put_credit_spread.py:274-293` (`_finalize_trade`)
- Test: `tests/test_trade_decomposition.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_trade_decomposition.py"""
import unittest
from datetime import date as Date

from strategies.base import round_trip_commission_per_spread
from strategies.put_credit_spread import PutCreditSpread, _OpenSpread


class FakeAsset:
    def __init__(self, strike):
        self.strike = strike


def make_strategy_with_pos():
    s = object.__new__(PutCreditSpread)
    s.closed_trades = []
    short, long_ = FakeAsset(400.0), FakeAsset(395.0)
    pos = _OpenSpread(
        symbol="SPY", expiration=Date(2020, 6, 19), short_asset=short,
        long_asset=long_, contracts=1, model_credit=2.20,
        entry_decision_date="2020-05-11", state="pending_exit",
        entry_credit=2.20, exit_reason="close_at_dte",
        exit_decision_date="2020-06-12")
    pos.exit_fills = {short: 1.10, long_: 0.30}
    s._spreads = {"SPY": pos}
    return s, pos


class DecompositionTests(unittest.TestCase):
    def test_decomposition_fields_present_and_consistent(self):
        s, pos = make_strategy_with_pos()
        s._finalize_trade("SPY", pos)
        t = s.closed_trades[0]
        comm = round_trip_commission_per_spread()
        self.assertEqual(t["entry_credit"], 2.20)
        self.assertEqual(t["exit_debit"], 0.80)          # 1.10 - 0.30
        self.assertEqual(t["contracts"], 1)
        self.assertEqual(t["width"], 5.0)
        self.assertAlmostEqual(t["gross_pnl"], (2.20 - 0.80) * 100.0)
        self.assertAlmostEqual(t["commissions"], comm)
        self.assertAlmostEqual(t["pnl"], t["gross_pnl"] - t["commissions"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_trade_decomposition -v`
Expected: FAIL with `KeyError: 'entry_credit'`

- [ ] **Step 3: Implement — extend `_finalize_trade` (additive keys only)**

In `strategies/put_credit_spread.py`, replace the `self.closed_trades.append({...})`
dict with:

```python
        gross_pnl = (pos.entry_credit - exit_debit) * 100.0 * n
        commissions = round_trip_commission_per_spread() * n
        self.closed_trades.append({
            "pnl": gross_pnl - commissions,
            "capital_at_risk": capital_at_risk_per_spread(width, pos.entry_credit) * n,
            "entry_date": pos.entry_decision_date,
            "symbol": symbol,
            "economic_max_loss":
                economic_max_loss_per_spread(width, pos.entry_credit) * n,
            "exit_reason": pos.exit_reason,
            "exit_date": pos.exit_decision_date,
            # decomposition (audit 2026-07-04): additive, ignored by scoreboard
            "entry_credit": pos.entry_credit,
            "exit_debit": exit_debit,
            "contracts": n,
            "width": width,
            "gross_pnl": gross_pnl,
            "commissions": commissions,
        })
```

(`pnl` arithmetic is unchanged: it was already `gross − commissions`.)

- [ ] **Step 4: Run the new test AND the full suite**

Run: `uv run python -m unittest tests.test_trade_decomposition -v && uv run python -m unittest discover -s tests`
Expected: all PASS (existing scoreboard tests must not care about extra keys)

- [ ] **Step 5: Commit**

```bash
git add strategies/put_credit_spread.py tests/test_trade_decomposition.py
git commit -m "feat(strategy): itemized per-trade P&L decomposition fields (H3R prereq)"
```

---

### Task 2: Credit-floor hook (pure function + base wiring)

**Files:**
- Modify: `strategies/base.py` (add function), `strategies/put_credit_spread.py:40-57,87-90`
- Test: `tests/test_credit_floor.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_credit_floor.py"""
import unittest

from strategies.base import passes_credit_floor


class CreditFloorTests(unittest.TestCase):
    def test_floor_zero_keeps_legacy_semantics(self):
        self.assertTrue(passes_credit_floor(0.01, 0.0))
        self.assertFalse(passes_credit_floor(0.0, 0.0))
        self.assertFalse(passes_credit_floor(-0.10, 0.0))

    def test_h3r_floor(self):
        self.assertTrue(passes_credit_floor(1.51, 1.50))
        self.assertFalse(passes_credit_floor(1.50, 1.50))
        self.assertFalse(passes_credit_floor(1.49, 1.50))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_credit_floor -v`
Expected: FAIL with `ImportError: cannot import name 'passes_credit_floor'`

- [ ] **Step 3: Implement**

Append to `strategies/base.py`:

```python
def passes_credit_floor(credit: float, floor: float) -> bool:
    """Entry credit must STRICTLY exceed the floor. floor=0.0 reproduces the
    legacy 'non-positive credit' skip exactly."""
    return credit > floor
```

In `strategies/put_credit_spread.py` `initialize()` add after `self.haircut = ...`:

```python
        self.credit_floor = 0.0            # subclasses may raise (e.g. H3R $1.50)
```

Replace the credit check in `_try_enter`:

```python
        if not passes_credit_floor(credit, self.credit_floor):
            self.log_message(
                f"{symbol}: credit ${credit:.2f} <= floor ${self.credit_floor:.2f}, skip")
            return
```

and add `passes_credit_floor` to the `strategies.base` import list at the top.

- [ ] **Step 4: Run the tests**

Run: `uv run python -m unittest tests.test_credit_floor -v && uv run python -m unittest discover -s tests`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add strategies/base.py strategies/put_credit_spread.py tests/test_credit_floor.py
git commit -m "feat(strategy): credit-floor hook, legacy semantics preserved at floor=0"
```

---

### Task 3: Config block for H3R (frozen surface)

**Files:**
- Modify: `config.py` (append new section after the A_* block)
- Test: `tests/test_h3r_config.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_h3r_config.py"""
import unittest

import config


class H3RConfigTests(unittest.TestCase):
    def test_h3r_frozen_values(self):
        self.assertEqual(config.H3R_UNIVERSE, ["SPY"])
        self.assertEqual(config.H3R_SHORT_PUT_DELTA, 0.50)
        self.assertEqual(config.H3R_DELTA_BAND, (0.40, 0.60))
        self.assertEqual(config.H3R_SPREAD_WIDTH, 5)
        self.assertEqual(config.H3R_CREDIT_FLOOR, 1.50)
        self.assertEqual(config.H3R_RV_WINDOW, 21)
        self.assertEqual(config.H3R_SMA_WINDOW, 200)
        self.assertEqual(config.H3R_VRP_PCT_WINDOW, 252)
        self.assertEqual(config.H3R_VRP_PCT_MIN_OBS, 126)
        self.assertEqual(config.H3R_VRP_PCT_THRESHOLD, 0.70)

    def test_h1_surface_untouched(self):
        # guard: adding H3R must not disturb the registered H1/H2 surface
        self.assertEqual(config.A_SPREAD_WIDTH, 2)
        self.assertEqual(config.A_SHORT_PUT_DELTA, 0.30)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_h3r_config -v`
Expected: FAIL with `AttributeError: ... has no attribute 'H3R_UNIVERSE'`

- [ ] **Step 3: Implement — append to `config.py`**

```python
# ---------------------------------------------------------------------------
# STRATEGY H3R -- CONDITIONAL-VRP ATM PUT CREDIT SPREAD (SPY primary).
# DRAFT until the pre-registration doc is frozen; after H3R registers, this
# block is part of the hashed surface and immutable. QQQ is a separate
# NON-VERDICT robustness sleeve (spec §6.8), not part of H3R_UNIVERSE.
# ---------------------------------------------------------------------------
H3R_UNIVERSE          = ["SPY"]
H3R_SHORT_PUT_DELTA   = 0.50          # ATM; friction share ~6-10% of credit
H3R_DELTA_BAND        = (0.40, 0.60)  # outside band -> skip (fail closed)
H3R_SPREAD_WIDTH      = 5             # $5 grid exists on SPY throughout
H3R_CREDIT_FLOOR      = 1.50          # conservative credit must exceed this
H3R_RV_WINDOW         = 21            # trading days, ddof=1, close-to-close
H3R_SMA_WINDOW        = 200           # trend/crash gate
H3R_VRP_PCT_WINDOW    = 252           # trailing percentile window (cap)
H3R_VRP_PCT_MIN_OBS   = 126           # expanding window floor (keeps 2018Q4)
H3R_VRP_PCT_THRESHOLD = 0.70          # top-tercile gate, inclusive rank
```

- [ ] **Step 4: Run tests**

Run: `uv run python -m unittest tests.test_h3r_config -v && uv run python -m unittest discover -s tests`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_h3r_config.py
git commit -m "feat(config): H3R frozen parameter block (draft until prereg freeze)"
```

---

### Task 4: Direct underlying closes — blind-pull cache + OOS-gated loader

**Files:**
- Create: `data/underlying_closes.py`
- Test: `tests/test_underlying_closes.py` (create)

- [ ] **Step 1: VERIFY the installed ThetaData client's stock-EOD surface (read-only)**

Run: `uv run python -c "import thetadata, inspect; print([m for m in dir(thetadata.ThetaClient) if 'stock' in m.lower() or 'eod' in m.lower()])"`
Expected: a method list. Record the exact stock-EOD method name in the fetch
function's docstring. If NO stock endpoint exists on the installed client,
STOP — report to the owner (spec Gate V blocks; alternate source is an owner
decision). Do not guess an API.

- [ ] **Step 2: Write the failing test (storage + loader gate; no network)**

```python
"""tests/test_underlying_closes.py"""
import os
import tempfile
import unittest
from unittest import mock

import pandas as pd

import config
from data import underlying_closes
from data.thetadata_adapter import OOSDataTouchError


def synthetic_frame():
    return pd.DataFrame({
        "date": ["2022-12-29", "2022-12-30", "2023-01-03", "2022-12-28"],
        "close": [382.4, 380.1, 384.2, 383.0],
    })


class UnderlyingClosesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(underlying_closes, "CACHE_DIR", self.tmp.name)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        underlying_closes.store_closes("SPY", synthetic_frame())

    def test_store_sorts_and_dedupes(self):
        s = underlying_closes.load_closes("SPY", "2022-12-01", "2022-12-31")
        self.assertEqual(list(s.index), ["2022-12-28", "2022-12-29", "2022-12-30"])

    def test_loader_refuses_oos_by_default(self):
        with self.assertRaises(OOSDataTouchError):
            underlying_closes.load_closes("SPY", "2022-12-01", "2023-01-31")

    def test_loader_allows_oos_explicitly(self):
        s = underlying_closes.load_closes(
            "SPY", "2022-12-01", "2023-01-31", allow_oos=True)
        self.assertIn("2023-01-03", s.index)

    def test_in_sample_end_boundary_is_inclusive_and_free(self):
        s = underlying_closes.load_closes("SPY", "2022-12-01", config.IN_SAMPLE_END)
        self.assertEqual(len(s), 3)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_underlying_closes -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data.underlying_closes'`

- [ ] **Step 4: Implement `data/underlying_closes.py`**

```python
"""data/underlying_closes.py -- direct daily underlying closes (H3R Gate V).

BLIND-PULL POLICY (mirrors the chain cache): fetch writes the full configured
range to parquet WITHOUT displaying any value; load_closes() refuses rows
after config.IN_SAMPLE_END unless allow_oos=True. Features must be built from
THIS series (spec §2); parity-derived spots are a validation cross-check only
(analysis/validate_closes.py), never a feature source.
"""
from __future__ import annotations

import os

import pandas as pd

import config
from data.thetadata_adapter import OOSDataTouchError

CACHE_DIR = os.path.join(".cache", "underlying")


def _path(symbol: str) -> str:
    return os.path.join(CACHE_DIR, f"{symbol}.parquet")


def store_closes(symbol: str, frame: pd.DataFrame) -> str:
    """Persist ['date','close'] rows sorted+deduped. Used by the fetch and by
    tests with synthetic data. Returns the parquet path."""
    if list(frame.columns) != ["date", "close"]:
        raise ValueError(f"expected columns ['date','close'], got {list(frame.columns)}")
    out = (frame.assign(date=frame["date"].astype(str))
                .drop_duplicates(subset="date", keep="last")
                .sort_values("date")
                .reset_index(drop=True))
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _path(symbol)
    out.to_parquet(path, index=False)
    return path


def load_closes(symbol: str, start_iso: str, end_iso: str, *,
                allow_oos: bool = False) -> pd.Series:
    """Date-indexed close Series over [start_iso, end_iso]. Fail-closed OOS
    gate: any end beyond IN_SAMPLE_END requires allow_oos=True."""
    if not allow_oos and end_iso > config.IN_SAMPLE_END:
        raise OOSDataTouchError(
            f"load_closes({symbol}, end={end_iso}) exceeds IN_SAMPLE_END="
            f"{config.IN_SAMPLE_END} without allow_oos=True")
    df = pd.read_parquet(_path(symbol))
    s = df.set_index("date")["close"].sort_index()
    return s.loc[start_iso:end_iso]


def fetch_underlying_eod(symbol: str, start_iso: str, end_iso: str) -> str:
    """One-shot blind pull via the installed ThetaData client (method name
    verified in Task 4 Step 1 -- fill it in here when verified). Writes the
    cache and returns the path; NEVER prints a price."""
    raise NotImplementedError(
        "wire to the verified ThetaData stock-EOD endpoint; owner-gated pull")
```

Note: `fetch_underlying_eod` stays `NotImplementedError` until Step 1's
verified method name is known and the owner approves the pull; the loader,
storage, and every downstream task are fully testable without it.

- [ ] **Step 5: Run tests**

Run: `uv run python -m unittest tests.test_underlying_closes -v && uv run python -m unittest discover -s tests`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add data/underlying_closes.py tests/test_underlying_closes.py
git commit -m "feat(data): blind-pull underlying-close cache with OOS-gated loader (H3R Gate V prereq)"
```

---

### Task 5: Gate V — parity cross-check validator

**Files:**
- Create: `analysis/validate_closes.py`
- Test: `tests/test_validate_closes.py` (create)

- [ ] **Step 1: Write the failing test (synthetic chains with known parity spot)**

```python
"""tests/test_validate_closes.py"""
import unittest

import numpy as np
import pandas as pd

from analysis.validate_closes import compare_series, parity_spot_from_chain


def chain_with_spot(spot, expiration="2020-07-17"):
    strikes = [spot - 10, spot - 5, spot, spot + 5, spot + 10]
    rows = []
    for k in strikes:
        call_mid = max(spot - k, 0) + 2.0     # crude but parity-consistent
        put_mid = call_mid - (spot - k)       # C - P = S - K  (r=0, no divs)
        for right, mid in (("C", call_mid), ("P", put_mid)):
            rows.append({"expiration": expiration, "strike": float(k),
                         "right": right, "bid": mid - 0.05, "ask": mid + 0.05,
                         "open_interest": 1000, "iv": 0.2, "delta": 0.5,
                         "gamma": 0, "theta": 0, "vega": 0})
    return pd.DataFrame(rows)


class ParitySpotTests(unittest.TestCase):
    def test_recovers_known_spot(self):
        est = parity_spot_from_chain(chain_with_spot(300.0), "2020-06-15", (30, 45))
        self.assertAlmostEqual(est, 300.0, places=6)

    def test_compare_series_accepts_tight_noise(self):
        idx = [f"2022-01-{d:02d}" for d in range(3, 29)]
        direct = pd.Series(np.linspace(400, 410, len(idx)), index=idx)
        noisy = direct * (1 + np.random.default_rng(7).normal(0, 1e-5, len(idx)))
        report = compare_series(direct, pd.Series(noisy.values, index=idx))
        self.assertTrue(report["accepted"])
        self.assertLess(report["median_return_diff_bps"], 5.0)

    def test_compare_series_rejects_big_noise(self):
        idx = [f"2022-01-{d:02d}" for d in range(3, 29)]
        direct = pd.Series(np.linspace(400, 410, len(idx)), index=idx)
        bad = direct * (1 + np.random.default_rng(7).normal(0, 5e-3, len(idx)))
        report = compare_series(direct, pd.Series(bad.values, index=idx))
        self.assertFalse(report["accepted"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_validate_closes -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'analysis.validate_closes'`

- [ ] **Step 3: Implement `analysis/validate_closes.py`**

```python
"""analysis/validate_closes.py -- Gate V: validate direct closes vs parity.

Frozen acceptance (prereg spec §3): median |daily log-return diff| <= 5 bps
AND 99th percentile <= 50 bps over the compared window AND parity-outlier
days < 1% of days. Features consume DIRECT closes; the parity series exists
only to catch a broken close series or broken chains (e.g. the QQQ
2023-12-27 dividend-adjusted-strike artifact) BEFORE any strategy result.
"""
from __future__ import annotations

from datetime import date as Date

import numpy as np
import pandas as pd

import config
from data import underlying_closes
from data.pandas_feed import load_cached_chains
from research.facts import append_fact

MEDIAN_BPS_MAX = 5.0
P99_BPS_MAX = 50.0
OUTLIER_DAY_FRAC_MAX = 0.01


def parity_spot_from_chain(chain: pd.DataFrame, today_iso: str,
                           band: tuple[int, int]) -> float:
    """Median over strikes of C_mid - P_mid + K on the nearest in-band
    expiry (r=0, no dividend PV -- fine for RETURN comparison). NaN when the
    day has no usable in-band expiry or no P/C strike overlap."""
    today = Date.fromisoformat(today_iso)
    lo, hi = band
    dtes = {e: (Date.fromisoformat(str(e)) - today).days
            for e in chain["expiration"].unique()}
    in_band = {e: d for e, d in dtes.items() if lo <= d <= hi}
    if not in_band:
        return float("nan")
    exp = min(in_band, key=lambda e: in_band[e])
    sub = chain[chain["expiration"] == exp]
    calls = sub[sub["right"] == "C"].set_index("strike")
    puts = sub[sub["right"] == "P"].set_index("strike")
    ks = calls.index.intersection(puts.index)
    if len(ks) == 0:
        return float("nan")
    c_mid = (calls.loc[ks, "bid"] + calls.loc[ks, "ask"]) / 2
    p_mid = (puts.loc[ks, "bid"] + puts.loc[ks, "ask"]) / 2
    return float((c_mid - p_mid + pd.Series(ks, index=ks)).median())


def compare_series(direct: pd.Series, parity: pd.Series) -> dict:
    """Log-return agreement stats on the common dates + frozen acceptance."""
    common = direct.index.intersection(parity.dropna().index)
    d = np.log(direct.loc[common].astype(float)).diff().dropna()
    p = np.log(parity.loc[common].astype(float)).diff().dropna()
    both = d.index.intersection(p.index)
    diff_bps = ((d.loc[both] - p.loc[both]).abs() * 1e4)
    median_bps = float(diff_bps.median())
    p99_bps = float(diff_bps.quantile(0.99))
    outlier_frac = float((diff_bps > P99_BPS_MAX).mean())
    accepted = (median_bps <= MEDIAN_BPS_MAX and p99_bps <= P99_BPS_MAX
                and outlier_frac <= OUTLIER_DAY_FRAC_MAX)
    return {"n_days": int(len(both)), "median_return_diff_bps": median_bps,
            "p99_return_diff_bps": p99_bps, "outlier_day_frac": outlier_frac,
            "accepted": bool(accepted)}


def run_gate_v(symbol: str, start_iso: str, end_iso: str) -> dict:
    """In-sample only by construction (loader gate). Appends the verdict to
    facts.log and returns the report."""
    direct = underlying_closes.load_closes(symbol, start_iso, end_iso)
    chains = load_cached_chains(symbol, start_iso, end_iso, allow_oos=False)
    parity = pd.Series({day: parity_spot_from_chain(chain, day, (20, 60))
                        for day, chain in chains.items()}).sort_index()
    report = compare_series(direct, parity)
    append_fact(
        f"H3R_GATE_V {symbol} {start_iso}..{end_iso} "
        f"n={report['n_days']} med={report['median_return_diff_bps']:.2f}bps "
        f"p99={report['p99_return_diff_bps']:.2f}bps "
        f"outliers={report['outlier_day_frac']:.4f} "
        f"accepted={report['accepted']}")
    return report


if __name__ == "__main__":
    print(run_gate_v("SPY", "2018-01-01", config.IN_SAMPLE_END))
```

- [ ] **Step 4: Run tests**

Run: `uv run python -m unittest tests.test_validate_closes -v && uv run python -m unittest discover -s tests`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add analysis/validate_closes.py tests/test_validate_closes.py
git commit -m "feat(analysis): Gate V close-series validator (parity cross-check, frozen acceptance)"
```

---

### Task 6: Feature frame + lag-enforcing provider

**Files:**
- Create: `data/features_vrp.py`
- Test: `tests/test_features_vrp.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_features_vrp.py"""
import unittest

import numpy as np
import pandas as pd

from data.features_vrp import build_features, make_feature_provider


def flat_chain(iv, expiration):
    return pd.DataFrame([{"expiration": expiration, "strike": 100.0,
                          "right": "P", "bid": 1.0, "ask": 1.1,
                          "open_interest": 500, "iv": iv, "delta": -0.50,
                          "gamma": 0, "theta": 0, "vega": 0}])


def build_fixture(n_days=300, iv_last=0.9):
    dates = pd.bdate_range("2019-01-02", periods=n_days).strftime("%Y-%m-%d")
    closes = pd.Series(np.full(n_days, 100.0), index=dates)
    # constant closes -> RV=0, SMA=100; IV spike on the LAST day only
    chains = {}
    for i, d in enumerate(dates):
        exp = (pd.Timestamp(d) + pd.Timedelta(days=35)).strftime("%Y-%m-%d")
        chains[d] = flat_chain(0.20 if i < n_days - 1 else iv_last, exp)
    return dates, closes, chains


class FeatureTests(unittest.TestCase):
    def test_signal_needs_min_obs(self):
        dates, closes, chains = build_fixture(n_days=100)
        f = build_features("SPY", dates[0], dates[-1], closes=closes, chains=chains)
        self.assertFalse(bool(f["signal_on"].any()))   # <126 obs: never on

    def test_spike_day_turns_signal_on_that_day_only(self):
        dates, closes, chains = build_fixture(n_days=300)
        f = build_features("SPY", dates[0], dates[-1], closes=closes, chains=chains)
        self.assertTrue(bool(f.loc[dates[-1], "signal_on"]))
        self.assertFalse(bool(f.loc[dates[-2], "signal_on"]))

    def test_provider_serves_strictly_lagged_row(self):
        dates, closes, chains = build_fixture(n_days=300)
        f = build_features("SPY", dates[0], dates[-1], closes=closes, chains=chains)
        provider = make_feature_provider(f)
        # decision ON the spike day sees the day-before row -> gate closed
        self.assertFalse(bool(provider("SPY", dates[-1])["signal_on"]))
        # decision the day AFTER the spike sees the spike row -> gate open
        next_day = (pd.Timestamp(dates[-1]) + pd.offsets.BDay(1)).strftime("%Y-%m-%d")
        self.assertTrue(bool(provider("SPY", next_day)["signal_on"]))

    def test_provider_modes(self):
        dates, closes, chains = build_fixture(n_days=300)
        f = build_features("SPY", dates[0], dates[-1], closes=closes, chains=chains)
        next_day = (pd.Timestamp(dates[-1]) + pd.offsets.BDay(1)).strftime("%Y-%m-%d")
        self.assertTrue(bool(
            make_feature_provider(f, mode="always_on")("SPY", dates[5])["signal_on"]))
        self.assertFalse(bool(
            make_feature_provider(f, mode="inverted")("SPY", next_day)["signal_on"]))
        lagged = make_feature_provider(f, mode="placebo_lag252")
        self.assertFalse(bool(lagged("SPY", next_day)["signal_on"]))

    def test_missing_iv_fails_closed(self):
        dates, closes, chains = build_fixture(n_days=300)
        chains[dates[-1]] = chains[dates[-1]].assign(iv=float("nan"))
        f = build_features("SPY", dates[0], dates[-1], closes=closes, chains=chains)
        self.assertFalse(bool(f.loc[dates[-1], "signal_on"]))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_features_vrp -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data.features_vrp'`

- [ ] **Step 3: Implement `data/features_vrp.py`**

```python
"""data/features_vrp.py -- H3R feature frame + lag-enforcing provider.

The STRATEGY never computes features. build_features() produces one row per
chain day t (values AS OF t); make_feature_provider() serves, for a decision
date, the latest row STRICTLY BEFORE it -- the only place lag is enforced,
so it is tested in one place. Fail-closed: any NaN input => signal_on False.
"""
from __future__ import annotations

from datetime import date as Date

import numpy as np
import pandas as pd

import config


def atm_iv_from_chain(chain: pd.DataFrame, today_iso: str,
                      band=(30, 45),
                      target=None, accept=None) -> float:
    """IV of the put nearest |delta|=target within `accept` on the nearest
    in-band expiry; NaN when absent/invalid (fail closed)."""
    target = config.H3R_SHORT_PUT_DELTA if target is None else target
    accept = config.H3R_DELTA_BAND if accept is None else accept
    today = Date.fromisoformat(today_iso)
    puts = chain[chain["right"] == "P"]
    if puts.empty:
        return float("nan")
    dtes = {e: (Date.fromisoformat(str(e)) - today).days
            for e in puts["expiration"].unique()}
    lo, hi = band
    in_band = {e: d for e, d in dtes.items()
               if max(lo, config.DTE_MIN) <= d <= hi}
    if not in_band:
        return float("nan")
    exp = min(in_band, key=lambda e: in_band[e])
    sub = puts[puts["expiration"] == exp]
    row = sub.loc[(sub["delta"].abs() - target).abs().idxmin()]
    d = abs(float(row["delta"]))
    iv = float(row["iv"])
    if not (accept[0] <= d <= accept[1]) or not np.isfinite(iv) or iv <= 0:
        return float("nan")
    return iv


def build_features(symbol: str, start_iso: str, end_iso: str, *,
                   closes: pd.Series, chains: dict[str, pd.DataFrame],
                   rv_window=None, sma_window=None,
                   pct_window=None, pct_min_obs=None,
                   threshold=None) -> pd.DataFrame:
    """One row per chain day within [start_iso, end_iso]. `closes` may (and
    for SMA warmup should) start EARLIER than start_iso."""
    rv_window = config.H3R_RV_WINDOW if rv_window is None else rv_window
    sma_window = config.H3R_SMA_WINDOW if sma_window is None else sma_window
    pct_window = config.H3R_VRP_PCT_WINDOW if pct_window is None else pct_window
    pct_min_obs = config.H3R_VRP_PCT_MIN_OBS if pct_min_obs is None else pct_min_obs
    threshold = config.H3R_VRP_PCT_THRESHOLD if threshold is None else threshold

    closes = closes.sort_index().astype(float)
    logret = np.log(closes).diff()
    rv = logret.rolling(rv_window).std(ddof=1) * np.sqrt(252.0)
    sma = closes.rolling(sma_window, min_periods=1).mean()

    days = sorted(d for d in chains if start_iso <= d <= end_iso)
    atm = pd.Series({d: atm_iv_from_chain(chains[d], d) for d in days})

    frame = pd.DataFrame(index=pd.Index(days, name="date"))
    frame["close"] = closes.reindex(days)
    frame["rv"] = rv.reindex(days)
    frame["sma"] = sma.reindex(days)
    frame["atm_iv"] = atm
    frame["vrp"] = frame["atm_iv"] - frame["rv"]

    pcts, vals = [], []
    for v in frame["vrp"]:
        vals.append(v)
        window = [x for x in vals[-pct_window:] if np.isfinite(x)]
        if not np.isfinite(v) or len(window) < pct_min_obs:
            pcts.append(float("nan"))
        else:
            pcts.append(float(np.mean(np.asarray(window) <= v)))  # inclusive rank
    frame["vrp_pct"] = pcts

    frame["above_sma"] = frame["close"] > frame["sma"]
    finite = frame[["close", "rv", "sma", "atm_iv", "vrp", "vrp_pct"]].notna().all(axis=1)
    frame["signal_on"] = finite & frame["above_sma"] & (frame["vrp_pct"] >= threshold)
    return frame


def make_feature_provider(frame: pd.DataFrame, mode: str = "primary"):
    """(symbol, decision_iso) -> feature row for the latest date STRICTLY
    BEFORE decision_iso, or None. Modes (prereg spec §6): primary,
    always_on (baseline arm), inverted (VRP pct <= 1-threshold), and
    placebo_lag252 (signal shifted 252 rows into the future = decisions see
    year-old states)."""
    if mode not in {"primary", "always_on", "inverted", "placebo_lag252"}:
        raise ValueError(f"unknown provider mode {mode!r}")
    f = frame.copy()
    thr = config.H3R_VRP_PCT_THRESHOLD
    if mode == "always_on":
        f["signal_on"] = True
    elif mode == "inverted":
        finite = f[["vrp_pct"]].notna().all(axis=1)
        f["signal_on"] = finite & f["above_sma"] & (f["vrp_pct"] <= 1.0 - thr)
    elif mode == "placebo_lag252":
        f["signal_on"] = f["signal_on"].shift(252).fillna(False)

    dates = list(f.index)

    def provider(symbol: str, decision_iso: str):
        import bisect
        i = bisect.bisect_left(dates, decision_iso)
        return None if i == 0 else f.iloc[i - 1]

    return provider
```

- [ ] **Step 4: Run tests**

Run: `uv run python -m unittest tests.test_features_vrp -v && uv run python -m unittest discover -s tests`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add data/features_vrp.py tests/test_features_vrp.py
git commit -m "feat(data): VRP/SMA feature frame + strictly-lagged provider with arm modes"
```

---

### Task 7: `ConditionalVrpSpread` strategy

**Files:**
- Create: `strategies/conditional_vrp_spread.py`
- Test: `tests/test_conditional_vrp_spread.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_conditional_vrp_spread.py"""
import unittest
from datetime import date as Date

import pandas as pd

from strategies.conditional_vrp_spread import ConditionalVrpSpread
from strategies.put_credit_spread import _OpenSpread


class FakeAsset:
    def __init__(self, strike):
        self.strike = strike


def bare(signal_on, dte=None):
    s = object.__new__(ConditionalVrpSpread)
    s.log_message = lambda *a, **k: None
    s._today_iso = "2020-06-01"
    s._today = lambda: Date.fromisoformat(s._today_iso)
    row = pd.Series({"signal_on": signal_on})
    s._feature_provider = lambda sym, iso: row
    s.chain_calls = 0

    def chain_counter(sym=None):
        s.chain_calls += 1
        return None
    s._get_eod_chain = chain_counter
    s.close_dte = 7
    s.closed = []
    s._close = lambda sym, pos, reason: s.closed.append(reason)
    return s


class GateTests(unittest.TestCase):
    def test_signal_off_means_no_chain_fetch(self):
        s = bare(signal_on=False)
        s._try_enter("SPY")
        self.assertEqual(s.chain_calls, 0)

    def test_signal_on_proceeds_to_selection(self):
        s = bare(signal_on=True)
        s._try_enter("SPY")                    # base skips on chain None
        self.assertEqual(s.chain_calls, 1)

    def test_missing_provider_fails_loud(self):
        s = bare(signal_on=True)
        s._feature_provider = None
        with self.assertRaises(RuntimeError):
            s._try_enter("SPY")


class DeltaBandTests(unittest.TestCase):
    def test_out_of_band_delta_returns_none(self):
        s = object.__new__(ConditionalVrpSpread)
        s.delta_band = (0.40, 0.60)
        chain = pd.DataFrame([{"expiration": "2020-07-17", "strike": 300.0,
                               "right": "P", "delta": -0.30, "bid": 1, "ask": 1.1,
                               "open_interest": 500, "iv": 0.2,
                               "gamma": 0, "theta": 0, "vega": 0}])
        self.assertIsNone(s._strike_nearest_delta(chain, "2020-07-17", 0.50))


class ExitTests(unittest.TestCase):
    def make(self, dte):
        s = bare(signal_on=True)
        pos = _OpenSpread(symbol="SPY",
                          expiration=Date.fromisoformat(s._today_iso)
                          + pd.Timedelta(days=dte).to_pytimedelta(),
                          short_asset=FakeAsset(300.0), long_asset=FakeAsset(295.0),
                          contracts=1, model_credit=2.2,
                          entry_decision_date="2020-05-01", state="open",
                          entry_credit=2.2)
        s._spreads = {"SPY": pos}
        return s

    def test_no_exit_above_close_dte(self):
        s = self.make(dte=8)
        s._manage_exit("SPY")
        self.assertEqual(s.closed, [])

    def test_dte_exit_fires(self):
        s = self.make(dte=7)
        s._manage_exit("SPY")
        self.assertEqual(s.closed, ["close_at_dte"])

    def test_no_stop_no_target_marks_never_consulted(self):
        s = self.make(dte=20)
        s._spread_mark = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("mark must not be consulted"))
        s._manage_exit("SPY")                  # must not raise
        self.assertEqual(s.closed, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_conditional_vrp_spread -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `strategies/conditional_vrp_spread.py`**

```python
"""strategies/conditional_vrp_spread.py -- H3R: conditional-VRP ATM spread.

PutCreditSpread with four frozen differences (prereg spec §2):
  1. entry requires the LAGGED signal row's signal_on (provider enforces t-1);
  2. short leg targets |delta|=0.50 and must land inside H3R_DELTA_BAND;
  3. conservative entry credit must exceed H3R_CREDIT_FLOOR;
  4. NO stop, NO profit target -- the only exit is the forced 7-DTE close.
Everything else (liquidity gates, sizing, fills, chunk plumbing,
decomposition) is inherited unchanged.
"""
from __future__ import annotations

import config
from strategies.put_credit_spread import PutCreditSpread


class ConditionalVrpSpread(PutCreditSpread):

    def initialize(self):
        super().initialize()
        self.delta = config.H3R_SHORT_PUT_DELTA
        self.delta_band = config.H3R_DELTA_BAND
        self.width = config.H3R_SPREAD_WIDTH
        self.credit_floor = config.H3R_CREDIT_FLOOR
        params = self.parameters or {}
        self._feature_provider = params.get("feature_provider")

    # ----- ENTRY GATE ------------------------------------------------------
    def _signal_on(self, symbol) -> bool:
        if self._feature_provider is None:
            raise RuntimeError(
                "no feature_provider wired -- the harness must inject the "
                "lagged feature provider (parameters['feature_provider'])")
        row = self._feature_provider(symbol, self._today().isoformat())
        return row is not None and bool(row["signal_on"])

    def _try_enter(self, symbol):
        if not self._signal_on(symbol):
            return                      # gate closed: no chain read, no log spam
        super()._try_enter(symbol)

    # ----- ATM BAND --------------------------------------------------------
    def _strike_nearest_delta(self, chain, exp, d):
        row = super()._strike_nearest_delta(chain, exp, d)
        if row is None:
            return None
        lo, hi = self.delta_band
        return row if lo <= abs(float(row["delta"])) <= hi else None

    # ----- EXITS: 7-DTE ONLY ------------------------------------------------
    def _manage_exit(self, symbol):
        pos = self._position(symbol)
        if self._dte(pos) <= self.close_dte:
            self._close(symbol, pos, reason="close_at_dte")
```

- [ ] **Step 4: Run tests**

Run: `uv run python -m unittest tests.test_conditional_vrp_spread -v && uv run python -m unittest discover -s tests`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add strategies/conditional_vrp_spread.py tests/test_conditional_vrp_spread.py
git commit -m "feat(strategy): ConditionalVrpSpread -- lagged signal gate, ATM band, no stop/target"
```

---

### Task 8: Harness passthrough + strategy registry + reveal generalization

**Files:**
- Modify: `harness/run_backtest.py` (`_run_chunk`, `run`, `_oos_backtest_trades`, new registry)
- Modify: `research/experiments.py` (`register` gains `strategy_id`), `research/ledger.py` (verifier accepts field)
- Test: `tests/test_strategy_registry.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_strategy_registry.py"""
import unittest

from harness.run_backtest import STRATEGY_REGISTRY, _resolve_strategy
from strategies.conditional_vrp_spread import ConditionalVrpSpread
from strategies.put_credit_spread import PutCreditSpread


class RegistryTests(unittest.TestCase):
    def test_legacy_default_resolves_put_credit_spread(self):
        self.assertIs(_resolve_strategy(None), PutCreditSpread)
        self.assertIs(_resolve_strategy("put_credit_spread"), PutCreditSpread)

    def test_h3r_resolves_conditional_vrp(self):
        self.assertIs(_resolve_strategy("conditional_vrp_spread"),
                      ConditionalVrpSpread)

    def test_unknown_id_fails_loud(self):
        with self.assertRaises(KeyError):
            _resolve_strategy("nope")

    def test_registry_ids_are_stable_strings(self):
        self.assertEqual(set(STRATEGY_REGISTRY),
                         {"put_credit_spread", "conditional_vrp_spread"})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_strategy_registry -v`
Expected: FAIL with `ImportError: cannot import name 'STRATEGY_REGISTRY'`

- [ ] **Step 3: Implement**

In `harness/run_backtest.py` add near the top:

```python
import importlib

# Registered-record strategy resolution. Records WITHOUT strategy_id are
# legacy (H1/H2) and mean put_credit_spread; the reveal path must never
# hardcode a class again (that would brick any new hypothesis's reveal).
STRATEGY_REGISTRY = {
    "put_credit_spread": "strategies.put_credit_spread:PutCreditSpread",
    "conditional_vrp_spread":
        "strategies.conditional_vrp_spread:ConditionalVrpSpread",
}


def _resolve_strategy(strategy_id):
    key = strategy_id or "put_credit_spread"
    mod_name, cls_name = STRATEGY_REGISTRY[key].split(":")
    return getattr(importlib.import_module(mod_name), cls_name)
```

Thread `extra_parameters` through: `_run_chunk(..., extra_parameters=None)`
merges `**(extra_parameters or {})` into the `parameters=` dict after
`"blocked_until": blocked_until,`; `run(...)` gains
`extra_parameters: dict | None = None` and passes it to every `_run_chunk`
call. In `_oos_backtest_trades`, replace the hardcoded import + call with:

```python
    record = runs[-1]
    window = record["oos_window"]
    strategy_cls = _resolve_strategy(record.get("strategy_id"))
    extra = _oos_extra_parameters(record)
    return run(strategy_cls, start=window["start"], end=window["end"],
               symbols=list(record["scope"]["symbols"]), allow_oos=True,
               extra_parameters=extra)


def _oos_extra_parameters(record) -> dict | None:
    """Per-strategy OOS wiring. conditional_vrp_spread needs the lagged
    feature provider built over [oos_start - warmup, oos_end] with
    allow_oos=True (warmup rows come from in-sample data -- not holdout)."""
    if record.get("strategy_id") != "conditional_vrp_spread":
        return None
    from datetime import date as Date, timedelta

    import config
    from data import underlying_closes
    from data.features_vrp import build_features, make_feature_provider
    from data.pandas_feed import load_cached_chains

    window = record["oos_window"]
    symbol = record["scope"]["symbols"][0]
    warmup_start = (Date.fromisoformat(window["start"])
                    - timedelta(days=600)).isoformat()   # 252 obs + slack
    closes = underlying_closes.load_closes(
        symbol, warmup_start, window["end"], allow_oos=True)
    chains = load_cached_chains(symbol, warmup_start, window["end"],
                                allow_oos=True)
    frame = build_features(symbol, warmup_start, window["end"],
                           closes=closes, chains=chains)
    return {"feature_provider": make_feature_provider(frame)}
```

In `research/experiments.py`, `register(...)` gains keyword
`strategy_id: str = "put_credit_spread"` stored on the record; in
`research/ledger.py` the run-record verifier accepts an optional
`strategy_id` that, when present, must be a key of a frozen allowed set
(mirror `STRATEGY_REGISTRY` keys as a module constant to avoid a
research→harness import).

- [ ] **Step 4: Run tests**

Run: `uv run python -m unittest tests.test_strategy_registry -v && uv run python -m unittest discover -s tests`
Expected: all PASS (charge-on-touch tests must still pass with legacy records)

- [ ] **Step 5: Commit**

```bash
git add harness/run_backtest.py research/experiments.py research/ledger.py tests/test_strategy_registry.py
git commit -m "feat(harness): strategy registry + extra_parameters passthrough; reveal path un-hardcoded"
```

---

### Task 9: H3R-shaped power study (synthetic; Gate P part a)

**Files:**
- Create: `analysis/power_check_h3r.py`
- Test: `tests/test_power_check_h3r.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_power_check_h3r.py"""
import unittest

from analysis.power_check_h3r import simulate_gated_trades


class SimTests(unittest.TestCase):
    def test_density_controls_trade_count(self):
        import numpy as np
        rng = np.random.default_rng(0)
        lo = simulate_gated_trades(260, 0.05, 0.0, rng)[1]
        rng = np.random.default_rng(0)
        hi = simulate_gated_trades(260, 0.50, 0.0, rng)[1]
        self.assertLess(len(lo), len(hi))

    def test_zero_density_zero_trades(self):
        import numpy as np
        entries, pnls = simulate_gated_trades(
            260, 0.0, 0.0, np.random.default_rng(1))
        self.assertEqual(pnls, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_power_check_h3r -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `analysis/power_check_h3r.py`**

```python
"""analysis/power_check_h3r.py -- Gate P (a): verdict-path power under the
H3R shape. SYNTHETIC: 1 symbol, signal-gated entry weeks (density param),
4-5 week holds, ATM win/loss mix. Reuses the frozen CI machinery + the
scoreboard-mirroring classify() from power_check (kept honest by its tests).

ASSUMPTIONS (documented, not config): ATM $5-wide, credit ~0.45W; win mean
+0.25W sd 0.12W (7-DTE close captures part of credit); loss mean -0.28W sd
0.15W (defined-risk cap at -(W-credit)=-0.55W enforced); P_LOSS grid
{0.35, 0.45, 0.55}. Edges tested: $0 (size) / $10 / $25 / $40 per trade.

Run:  uv run python analysis/power_check_h3r.py --quick
      uv run python analysis/power_check_h3r.py --density 0.12   # post-Gate-P
"""
import os
import sys
from datetime import date, timedelta

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from analysis.power_check import classify, wilson  # noqa: E402
from metrics import _build_week_cohorts, _ci_from_cohorts  # noqa: E402

W = config.H3R_SPREAD_WIDTH * 100.0
WIN_MEAN, WIN_SD = 0.25, 0.12
LOSS_MEAN, LOSS_SD = -0.28, 0.15
CAP = -0.55                       # -(W - credit): defined-risk floor
HOLD_CHOICES, HOLD_PROBS = np.array([4, 5]), np.array([0.5, 0.5])
P_LOSS_GRID = (0.35, 0.45, 0.55)
EDGES = (0.0, 10.0, 25.0, 40.0)   # dollars per trade
START = date.fromisoformat(config.BACKTEST_START)
N_WEEKS = (date.fromisoformat(config.IN_SAMPLE_END) - START).days // 7


def simulate_gated_trades(n_weeks, density, edge_dollars, rng, p_loss=0.45):
    """One history: each week is signal-on w.p. `density`; one open trade
    max; PnL in dollars. Returns (entry_dates_iso, pnls)."""
    entries, pnls = [], []
    week = 0
    base = (1 - p_loss) * WIN_MEAN + p_loss * LOSS_MEAN
    while week < n_weeks:
        if rng.random() < density:
            hold = int(rng.choice(HOLD_CHOICES, p=HOLD_PROBS))
            if rng.random() < p_loss:
                x = max(LOSS_MEAN + LOSS_SD * rng.standard_normal(), CAP)
            else:
                x = WIN_MEAN + WIN_SD * rng.standard_normal()
            pnls.append((x - base) * W + edge_dollars)
            entries.append((START + timedelta(weeks=week)).isoformat())
            week += hold + 1
        else:
            week += 1
    return entries, pnls


def run(density, quick=False):
    reps, n_boot = (8, 100) if quick else (200, 2000)
    print(f"H3R power study: density={density:.2f} weeks={N_WEEKS} reps={reps}")
    for p_loss in P_LOSS_GRID:
        for edge in EDGES:
            counts = {"PASS": 0, "FAIL": 0, "NO-EDGE": 0, "INSUFF": 0}
            n_tr = []
            for r in range(reps):
                rng = np.random.default_rng([42, int(p_loss * 100),
                                             int(edge), r])
                entries, pnls = simulate_gated_trades(
                    N_WEEKS, density, edge, rng, p_loss)
                n_losses = int((np.asarray(pnls) < 0).sum()) if pnls else 0
                cohorts = _build_week_cohorts(entries, pnls)
                if classify(n_losses, len(cohorts), 0.0, 0.0) == "INSUFF":
                    counts["INSUFF"] += 1
                    continue
                lo, hi = _ci_from_cohorts(cohorts, len(pnls), n_boot, 5, 95,
                                          seed=1_000_000 + r)
                counts[classify(n_losses, len(cohorts), lo, hi)] += 1
                n_tr.append(len(pnls))
            med = int(np.median(n_tr)) if n_tr else 0
            w_lo, w_hi = wilson(counts["PASS"], reps)
            print(f"p_loss={p_loss:.2f} edge=${edge:5.1f} trades~{med:3d} | "
                  f"PASS {counts['PASS'] / reps:5.1%} "
                  f"[{w_lo:.1%}..{w_hi:.1%}] NO-EDGE "
                  f"{counts['NO-EDGE'] / reps:5.1%} FAIL "
                  f"{counts['FAIL'] / reps:5.1%} INSUFF "
                  f"{counts['INSUFF'] / reps:5.1%}")


if __name__ == "__main__":
    args = sys.argv[1:]
    dens = 0.12
    if "--density" in args:
        dens = float(args[args.index("--density") + 1])
    run(dens, quick="--quick" in args)
```

Note: `power_check.py`'s `classify` and `wilson` must be importable; if
`classify` is module-private there, re-export it — do NOT duplicate the
verdict mirror (it is kept honest by `tests/test_power_check.py`).

- [ ] **Step 4: Run tests + a quick smoke**

Run: `uv run python -m unittest tests.test_power_check_h3r -v && uv run python analysis/power_check_h3r.py --quick`
Expected: tests PASS; smoke prints a grid without exceptions

- [ ] **Step 5: Commit**

```bash
git add analysis/power_check_h3r.py tests/test_power_check_h3r.py
git commit -m "feat(analysis): H3R-shaped synthetic power study (Gate P part a)"
```

---

### Task 10: Eligibility counter (signal-only; Gate P part b)

**Files:**
- Create: `analysis/h3r_eligibility.py`
- Test: `tests/test_h3r_eligibility.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_h3r_eligibility.py"""
import unittest

import pandas as pd

from analysis.h3r_eligibility import project_trades


class ProjectionTests(unittest.TestCase):
    def test_greedy_projection_respects_hold(self):
        dates = pd.bdate_range("2020-01-01", periods=80).strftime("%Y-%m-%d")
        frame = pd.DataFrame({"signal_on": [True] * 80}, index=dates)
        n = project_trades(frame, hold_calendar_days=35)
        self.assertEqual(n, 4)   # ~80 bdays = ~112 cal days -> 4 entries

    def test_no_signal_no_trades(self):
        dates = pd.bdate_range("2020-01-01", periods=80).strftime("%Y-%m-%d")
        frame = pd.DataFrame({"signal_on": [False] * 80}, index=dates)
        self.assertEqual(project_trades(frame), 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_h3r_eligibility -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `analysis/h3r_eligibility.py`**

```python
"""analysis/h3r_eligibility.py -- Gate P (b): signal-only eligibility count.

Computes NO option P&L (imports nothing from strategies/ or harness fill
paths -- the test suite enforces the import surface). Output: signal-day
count and a greedy projected trade count; frozen registration floor is
projected_trades >= 25 (prereg spec §3). Results go to facts.log as a
disclosed, signal-only engineering look.
"""
from __future__ import annotations

from datetime import date as Date, timedelta

import pandas as pd

import config
from data import underlying_closes
from data.features_vrp import build_features
from data.pandas_feed import load_cached_chains
from research.facts import append_fact

FLOOR = 25
HOLD_CALENDAR_DAYS = 35     # entry ~38 DTE -> exit at 7 DTE


def project_trades(frame: pd.DataFrame, hold_calendar_days=HOLD_CALENDAR_DAYS) -> int:
    """Greedy: walk days; a signal-on day starts a trade and blocks entries
    for hold_calendar_days. Mirrors one-spread-per-underlying, decision t
    fills t+1 -- close enough for a FEASIBILITY count, not a P&L."""
    n, blocked_until = 0, None
    for d in frame.index:
        if blocked_until is not None and d <= blocked_until:
            continue
        if bool(frame.loc[d, "signal_on"]):
            n += 1
            blocked_until = (Date.fromisoformat(d)
                             + timedelta(days=hold_calendar_days)).isoformat()
    return n


def run_gate_p(symbol="SPY") -> dict:
    start, end = config.BACKTEST_START, config.IN_SAMPLE_END
    closes = underlying_closes.load_closes("SPY", "2017-01-01", end)
    chains = load_cached_chains(symbol, start, end, allow_oos=False)
    frame = build_features(symbol, start, end, closes=closes, chains=chains)
    signal_days = int(frame["signal_on"].sum())
    projected = project_trades(frame)
    verdict = "REGISTERABLE" if projected >= FLOOR else "INFEASIBLE_AS_SPECIFIED"
    append_fact(f"H3R_GATE_P {symbol} {start}..{end} signal_days={signal_days} "
                f"projected_trades={projected} floor={FLOOR} verdict={verdict}")
    return {"signal_days": signal_days, "projected_trades": projected,
            "verdict": verdict}


if __name__ == "__main__":
    print(run_gate_p())
```

- [ ] **Step 4: Run tests**

Run: `uv run python -m unittest tests.test_h3r_eligibility -v && uv run python -m unittest discover -s tests`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add analysis/h3r_eligibility.py tests/test_h3r_eligibility.py
git commit -m "feat(analysis): Gate P signal-only eligibility counter with frozen floor"
```

---

### Task 11: Freeze + stop at the owner's door

**Files:**
- Modify: `docs/superpowers/specs/2026-07-03-h3r-preregistration-DRAFT.md` (drop DRAFT status on owner approval)
- No other code.

- [ ] **Step 1: Full suite green**

Run: `uv run python -m unittest discover -s tests`
Expected: all PASS, zero skips related to new modules

- [ ] **Step 2: Owner executes the data pull decision (outside this plan)**

`fetch_underlying_eod` is wired and run ONLY after the owner approves the
source (spec §3 Gate V). Blind pull 2017-01-01..2026-06-30 for SPY and QQQ;
no value displayed; commit the cache manifest note to facts.log.

- [ ] **Step 3: Run Gate V, then Gate P; record facts; STOP**

Run: `uv run python analysis/validate_closes.py && uv run python analysis/h3r_eligibility.py && uv run python analysis/power_check_h3r.py --density <measured>`
Expected: facts.log gains H3R_GATE_V and H3R_GATE_P lines. **Registration,
the in-sample run, and every §6 arm are OWNER-GATED actions defined in the
prereg spec — they are not tasks in this plan.**

- [ ] **Step 4: Commit docs**

```bash
git add docs/superpowers/specs/2026-07-03-h3r-preregistration-DRAFT.md docs/superpowers/plans/2026-07-03-h3r-implementation-plan-DRAFT.md ledger/facts.log
git commit -m "docs(h3r): freeze pre-registration after gates; stop at owner's door"
```

---

## Self-review notes

- Spec §8 items ↔ tasks: decomposition (T1), credit floor (T2), config (T3),
  closes (T4), Gate V (T5), features+provider (T6), strategy (T7),
  registry/passthrough/reveal (T8), power (T9), eligibility (T10). Covered.
- `_resolve_strategy(None)` legacy default matches ledger records that lack
  `strategy_id` (H1/H2) — charge-on-touch tests guard this (T8 Step 4).
- Type consistency: provider signature `(symbol, decision_iso) -> row|None`
  used identically in T6, T7, T8; `signal_on` column name identical in T6,
  T7, T10.
- Known open point (not a placeholder, an owner gate): the exact ThetaData
  stock-EOD method name (T4 Step 1 verifies against the installed client and
  stops if absent).
