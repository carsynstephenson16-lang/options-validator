# M2 — Underlying Closes + Daily Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Direct daily stock closes (blind-pulled, OOS-gated) plus a per-name daily feature frame (close, realized vol, monthly ATM IV, IV rank, earnings-week flag) that every M3 study consumes.

**Architecture:** `data/underlying_closes.py` owns storage/loading/fetching of closes (adapted from the archived H3R plan — same OOS-gate discipline as the chain cache). `options_researcher/earnings.py` loads the curated, source-cited earnings CSVs and refuses malformed ones. `options_researcher/features.py` is pure computation over closes + chains (via M1's `chains.py`) + earnings dates; results cached to `.tmp/research/` (regenerable intermediates).

**Tech Stack:** Python 3.12 / uv, pandas, unittest, installed `thetadata` client (endpoint VERIFIED before use). Suite: `uv run python -m unittest discover -s tests`.

**Depends on:** M1 (`options_researcher/chains.py`) committed and green. Earnings CSVs in `data/earnings/{SYM}.csv` (compiled separately with source URLs; Task 3's loader is content-agnostic and tested on fixtures).

---

### Task 1: Close-series storage + OOS-gated loader

**Files:**
- Create: `data/underlying_closes.py`
- Test: `tests/test_underlying_closes.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_underlying_closes.py"""
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
        underlying_closes.store_closes("VST", synthetic_frame())

    def test_store_sorts_and_dedupes(self):
        s = underlying_closes.load_closes("VST", "2022-12-01", "2022-12-31")
        self.assertEqual(list(s.index),
                         ["2022-12-28", "2022-12-29", "2022-12-30"])

    def test_store_rejects_wrong_columns(self):
        with self.assertRaises(ValueError):
            underlying_closes.store_closes(
                "VST", pd.DataFrame({"day": ["2022-12-28"], "close": [1.0]}))

    def test_loader_refuses_post_insample_by_default(self):
        with self.assertRaises(OOSDataTouchError):
            underlying_closes.load_closes("VST", "2022-12-01", "2023-01-31")

    def test_loader_allows_explicit_oos(self):
        s = underlying_closes.load_closes(
            "VST", "2022-12-01", "2023-01-31", allow_oos=True)
        self.assertIn("2023-01-03", s.index)

    def test_boundary_inclusive_no_flag_needed(self):
        s = underlying_closes.load_closes("VST", "2022-12-01",
                                          config.IN_SAMPLE_END)
        self.assertEqual(len(s), 3)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_underlying_closes -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data.underlying_closes'`

- [ ] **Step 3: Implement `data/underlying_closes.py`**

```python
"""data/underlying_closes.py -- direct daily underlying closes.

BLIND-PULL POLICY (mirrors the chain cache): the fetch writes the full
configured range to parquet WITHOUT displaying any value; load_closes()
refuses rows after config.IN_SAMPLE_END unless allow_oos=True. Researcher
call sites pass allow_oos=True explicitly -- a disclosed post-2022 look
(ledger/facts.log PIVOT_4NAME_SCOPE). Features and covered-call studies use
THIS series; put-call-parity spots are never a feature source.
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
    """Persist ['date','close'] rows sorted+deduped; returns the path.
    Used by the fetch and by tests with synthetic data."""
    if list(frame.columns) != ["date", "close"]:
        raise ValueError(
            f"expected columns ['date','close'], got {list(frame.columns)}")
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
    """Date-indexed float close Series over [start_iso, end_iso].
    Fail-closed OOS gate on the END of the requested range."""
    if not allow_oos and end_iso > config.IN_SAMPLE_END:
        raise OOSDataTouchError(
            f"load_closes({symbol}, end={end_iso}) exceeds IN_SAMPLE_END="
            f"{config.IN_SAMPLE_END} without allow_oos=True")
    df = pd.read_parquet(_path(symbol))
    s = df.set_index("date")["close"].sort_index().astype(float)
    return s.loc[start_iso:end_iso]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_underlying_closes -v`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add data/underlying_closes.py tests/test_underlying_closes.py
git commit -m "feat(data): blind-pull underlying-close cache with OOS-gated loader

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: ThetaData stock-EOD fetch (endpoint VERIFIED first; pull is orchestrator-only)

**Files:**
- Modify: `data/underlying_closes.py` (append)
- Test: `tests/test_underlying_closes.py` (append)

- [ ] **Step 1: VERIFY the installed client's stock-EOD surface (read-only)**

Run: `uv run python -c "import thetadata; c=[m for m in dir(thetadata) if not m.startswith('_')]; print(c)"`
then: `uv run python -c "from thetadata import ThetaClient; print([m for m in dir(ThetaClient) if 'stk' in m.lower() or 'stock' in m.lower() or 'eod' in m.lower() or 'hist' in m.lower()])"`
Expected: a non-empty method list containing a stock/historical endpoint.
**If NO stock-history endpoint exists on the installed client: STOP.** Report
BLOCKED with the printed lists — do not guess an HTTP API, do not pip-install
anything.

- [ ] **Step 2: Write the failing test (fetch normalization only; NO network in tests)**

```python
class FetchNormalizationTests(unittest.TestCase):
    def test_rows_to_frame_normalizes(self):
        rows = [("2023-01-04", 385.12), ("2023-01-03", 384.20)]
        frame = underlying_closes.rows_to_frame(rows)
        self.assertEqual(list(frame.columns), ["date", "close"])
        self.assertEqual(list(frame["date"]), ["2023-01-04", "2023-01-03"])
        self.assertAlmostEqual(float(frame["close"].iloc[1]), 384.20)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_underlying_closes -v`
Expected: FAIL with `AttributeError: ... 'rows_to_frame'`

- [ ] **Step 4: Implement (append to data/underlying_closes.py)**

```python
def rows_to_frame(rows) -> pd.DataFrame:
    """Normalize (iso_date, close) pairs from any fetch path into the
    storage schema. Pure; unit-tested without network."""
    return pd.DataFrame(rows, columns=["date", "close"])


def fetch_underlying_eod(symbol: str, start_iso: str, end_iso: str) -> str:
    """One-shot BLIND pull of daily closes via the installed ThetaData
    client (endpoint verified in this plan's Task 2 Step 1 -- adapt ONLY the
    client-call lines below to the verified method name/signature; if the
    response shape differs from (date, close)-per-day, STOP and report).
    Writes the cache and returns the path; NEVER prints a price.

    ORCHESTRATOR-ONLY: implementer agents do not run this function; the
    controlling session runs the actual pull after code review.
    """
    from datetime import date as _date

    from data.thetadata_adapter import _client  # existing lazy client factory

    client = _client()
    resp = client.get_hist_stock(          # VERIFIED NAME GOES HERE
        req="EOD",
        root=symbol,
        date_range=(_date.fromisoformat(start_iso),
                    _date.fromisoformat(end_iso)),
    )
    rows = [(str(r.date), float(r.close)) for r in resp.itertuples()]
    return store_closes(symbol, rows_to_frame(rows))
```

Note: `data/thetadata_adapter.py` already owns lazy client construction —
import and reuse its factory (search for the existing helper; it is the
function the chain fetch path uses to build/authenticate the client). If the
factory's name differs from `_client`, use the actual name — but do NOT
build a second client path.

- [ ] **Step 5: Run tests + full suite**

Run: `uv run python -m unittest tests.test_underlying_closes -v && uv run python -m unittest discover -s tests`
Expected: all PASS (fetch function is present but never executed by tests)

- [ ] **Step 6: Commit**

```bash
git add data/underlying_closes.py tests/test_underlying_closes.py
git commit -m "feat(data): ThetaData stock-EOD fetch (verified endpoint; blind, orchestrator-run)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Earnings CSV loader (fail-loud validation)

**Files:**
- Create: `options_researcher/earnings.py`
- Test: `tests/test_earnings_loader.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_earnings_loader.py"""
import os
import tempfile
import unittest
from datetime import date
from unittest import mock

from options_researcher import earnings


GOOD = "date,when,source_url\n2024-02-01,amc,https://example.com/a\n2024-04-30,amc,https://example.com/b\n"


class EarningsLoaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.object(earnings, "EARNINGS_DIR", self.tmp.name)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, symbol, text):
        with open(os.path.join(self.tmp.name, f"{symbol}.csv"), "w") as f:
            f.write(text)

    def test_loads_sorted_dates(self):
        self.write("AMZN", GOOD)
        self.assertEqual(earnings.load_earnings("AMZN"),
                         [date(2024, 2, 1), date(2024, 4, 30)])

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            earnings.load_earnings("MSFT")

    def test_bad_header_raises(self):
        self.write("VST", "day,when,url\n2024-02-01,amc,https://x\n")
        with self.assertRaises(ValueError):
            earnings.load_earnings("VST")

    def test_unsorted_or_duplicate_dates_raise(self):
        self.write("CEG", "date,when,source_url\n2024-05-01,bmo,https://x\n2024-02-01,bmo,https://y\n")
        with self.assertRaises(ValueError):
            earnings.load_earnings("CEG")

    def test_missing_source_url_raises(self):
        self.write("VST", "date,when,source_url\n2024-02-01,amc,\n")
        with self.assertRaises(ValueError):
            earnings.load_earnings("VST")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_earnings_loader -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'options_researcher.earnings'`

- [ ] **Step 3: Implement `options_researcher/earnings.py`**

```python
"""options_researcher/earnings.py -- curated earnings-date loader.

CSVs live in data/earnings/{SYMBOL}.csv with columns date,when,source_url.
Every row was compiled with a citation (IR press release or SEC 8-K); this
loader REFUSES malformed files instead of silently coping -- a wrong or
missing earnings date corrupts every downstream study.
"""
from __future__ import annotations

import csv
import os
from datetime import date

EARNINGS_DIR = os.path.join("data", "earnings")
_REQUIRED = ["date", "when", "source_url"]
_WHEN = {"bmo", "amc", "unknown"}


def load_earnings(symbol: str) -> list[date]:
    """Strictly-increasing announcement dates for `symbol`. Raises
    FileNotFoundError (no file) or ValueError (malformed content)."""
    path = os.path.join(EARNINGS_DIR, f"{symbol}.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} missing -- compile it (with source URLs) before "
            "building features for {symbol}")
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != _REQUIRED:
            raise ValueError(
                f"{path}: header must be {_REQUIRED}, got {reader.fieldnames}")
        out: list[date] = []
        for i, row in enumerate(reader, start=2):
            if not row["source_url"].strip():
                raise ValueError(f"{path}:{i}: empty source_url")
            if row["when"] not in _WHEN:
                raise ValueError(f"{path}:{i}: when={row['when']!r} not in {_WHEN}")
            d = date.fromisoformat(row["date"])
            if out and d <= out[-1]:
                raise ValueError(f"{path}:{i}: dates not strictly increasing")
            out.append(d)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_earnings_loader -v`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add options_researcher/earnings.py tests/test_earnings_loader.py
git commit -m "feat(researcher): fail-loud earnings CSV loader

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Daily feature frame

**Files:**
- Create: `options_researcher/features.py`
- Test: `tests/test_features.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_features.py"""
import unittest
from datetime import date

import numpy as np
import pandas as pd

from options_researcher.features import build_daily_features


def chain_day(iv, expiration):
    return pd.DataFrame([{
        "expiration": expiration, "strike": 100.0, "right": "P",
        "bid": 2.0, "ask": 2.1, "open_interest": 500, "iv": iv,
        "delta": -0.50, "gamma": 0.0, "theta": 0.0, "vega": 0.0}])


def fixture(n_days=300, last_iv=0.90):
    days = pd.bdate_range("2019-01-02", periods=n_days)
    isos = days.strftime("%Y-%m-%d")
    closes = pd.Series(np.full(n_days, 100.0), index=isos)
    chains = {}
    for i, (ts, iso) in enumerate(zip(days, isos)):
        exp = (ts + pd.offsets.BDay(1)).to_period("M")  # unused helper var
        # nearest monthly ~35 calendar days out: use the 3rd Friday trick by
        # just offsetting 35 days -- tests only need SOME in-band expiration;
        # is_monthly is not consulted by atm_iv (nearest_monthly is), so give
        # a REAL 3rd-Friday date to stay honest:
        d = ts.date()
        month = d.month + (2 if d.day > 10 else 1)
        year = d.year + (1 if month > 12 else 0)
        month = month if month <= 12 else month - 12
        from options_researcher.chains import third_friday
        exp_date = third_friday(year, month)
        chains[iso] = chain_day(0.20 if i < n_days - 1 else last_iv,
                                exp_date.isoformat())
    return isos, closes, chains


class FeatureFrameTests(unittest.TestCase):
    def test_constant_closes_give_zero_rv(self):
        isos, closes, chains = fixture(60)
        f = build_daily_features("VST", isos[0], isos[-1],
                                 closes=closes, chains=chains, earnings=[])
        self.assertAlmostEqual(float(f["rv21"].iloc[-1]), 0.0)
        self.assertTrue(np.isnan(float(f["rv21"].iloc[5])))  # warmup NaN

    def test_iv_rank_high_on_spike_day_only_with_min_obs(self):
        isos, closes, chains = fixture(300, last_iv=0.90)
        f = build_daily_features("VST", isos[0], isos[-1],
                                 closes=closes, chains=chains, earnings=[])
        self.assertGreaterEqual(float(f["iv_rank"].iloc[-1]), 0.99)
        short = fixture(100, last_iv=0.90)
        f2 = build_daily_features("VST", short[0][0], short[0][-1],
                                  closes=short[1], chains=short[2], earnings=[])
        self.assertTrue(np.isnan(float(f2["iv_rank"].iloc[-1])))  # <126 obs

    def test_earnings_week_window(self):
        isos, closes, chains = fixture(60)
        e = [date.fromisoformat(isos[40])]
        f = build_daily_features("VST", isos[0], isos[-1],
                                 closes=closes, chains=chains, earnings=e)
        self.assertTrue(bool(f["earnings_week"].loc[isos[35]]))   # 5 bd before
        self.assertTrue(bool(f["earnings_week"].loc[isos[41]]))   # day after
        self.assertFalse(bool(f["earnings_week"].loc[isos[20]]))

    def test_missing_chain_day_gives_nan_iv_not_crash(self):
        isos, closes, chains = fixture(60)
        del chains[isos[30]]
        f = build_daily_features("VST", isos[0], isos[-1],
                                 closes=closes, chains=chains, earnings=[])
        self.assertNotIn(isos[30], f.index)  # day simply absent (fail closed)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_features -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'options_researcher.features'`

- [ ] **Step 3: Implement `options_researcher/features.py`**

```python
"""options_researcher/features.py -- per-name daily feature frame.

One row per cached chain day: close, rv21 (annualized 21-day realized vol,
ddof=1), atm_iv (0.50-delta put on the NEAREST MONTHLY expiration, 15-60
DTE), iv_minus_rv, iv_rank (inclusive-rank percentile of atm_iv over the
trailing <=252 finite obs; NaN until 126), monthly_dte, earnings_week
(True iff an announcement date e satisfies -7 <= (e - day).days <= 1 in
BUSINESS-day terms via the -5bd..+1bd convention below).

Fail-closed: a day with no cached chain simply has no row; a day with no
in-band monthly gets NaN atm_iv. No fallbacks, no interpolation.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from options_researcher.chains import atm_row, nearest_monthly

RV_WINDOW = 21
PCT_WINDOW = 252
PCT_MIN_OBS = 126
EARN_BD_BEFORE = 5   # flag starts 5 business days before the announcement
EARN_BD_AFTER = 1    # ...and covers the business day after it


def _earnings_flags(index_isos, earnings: list[date]) -> pd.Series:
    days = [date.fromisoformat(d) for d in index_isos]
    flags = []
    for d in days:
        hit = False
        for e in earnings:
            lo = np.busday_offset(e.isoformat(), -EARN_BD_BEFORE, roll="backward")
            hi = np.busday_offset(e.isoformat(), EARN_BD_AFTER, roll="forward")
            if lo <= np.datetime64(d) <= hi:
                hit = True
                break
        flags.append(hit)
    return pd.Series(flags, index=index_isos)


def build_daily_features(symbol: str, start_iso: str, end_iso: str, *,
                         closes: pd.Series,
                         chains: dict[str, pd.DataFrame],
                         earnings: list[date]) -> pd.DataFrame:
    closes = closes.sort_index().astype(float)
    logret = np.log(closes).diff()
    rv = logret.rolling(RV_WINDOW).std(ddof=1) * np.sqrt(252.0)

    days = sorted(d for d in chains if start_iso <= d <= end_iso)
    atm_iv, monthly_dte = [], []
    for d in days:
        today = date.fromisoformat(d)
        exp = nearest_monthly(chains[d], today)
        if exp is None:
            atm_iv.append(float("nan")); monthly_dte.append(float("nan"))
            continue
        row = atm_row(chains[d], exp)
        iv = float(row["iv"]) if row is not None else float("nan")
        atm_iv.append(iv if iv and iv > 0 else float("nan"))
        monthly_dte.append(float((exp - today).days))

    f = pd.DataFrame(index=pd.Index(days, name="date"))
    f["close"] = closes.reindex(days)
    f["rv21"] = rv.reindex(days)
    f["atm_iv"] = atm_iv
    f["iv_minus_rv"] = f["atm_iv"] - f["rv21"]
    f["monthly_dte"] = monthly_dte

    ranks, vals = [], []
    for v in f["atm_iv"]:
        vals.append(v)
        window = [x for x in vals[-PCT_WINDOW:] if np.isfinite(x)]
        if not np.isfinite(v) or len(window) < PCT_MIN_OBS:
            ranks.append(float("nan"))
        else:
            ranks.append(float(np.mean(np.asarray(window) <= v)))
    f["iv_rank"] = ranks
    f["earnings_week"] = _earnings_flags(list(f.index), earnings)
    return f
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_features -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add options_researcher/features.py tests/test_features.py
git commit -m "feat(researcher): daily feature frame -- rv21, monthly ATM IV, iv_rank, earnings weeks

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Feature cache + builder entrypoint

**Files:**
- Modify: `options_researcher/features.py` (append)
- Test: `tests/test_features.py` (append)

- [ ] **Step 1: Write the failing test (append)**

```python
import os
import tempfile
from unittest import mock

from options_researcher import features


class CacheRoundTripTests(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        isos, closes, chains = fixture(60)
        f = build_daily_features("VST", isos[0], isos[-1],
                                 closes=closes, chains=chains, earnings=[])
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(features, "FEATURES_DIR", tmp):
                path = features.save_features("VST", f)
                self.assertTrue(os.path.exists(path))
                back = features.load_features("VST")
        pd.testing.assert_frame_equal(back, f)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_features -v`
Expected: FAIL with `AttributeError ... 'save_features'`

- [ ] **Step 3: Implement (append to options_researcher/features.py)**

```python
import os

FEATURES_DIR = os.path.join(".tmp", "research")


def save_features(symbol: str, frame: pd.DataFrame) -> str:
    os.makedirs(FEATURES_DIR, exist_ok=True)
    path = os.path.join(FEATURES_DIR, f"{symbol}_features.parquet")
    frame.to_parquet(path)
    return path


def load_features(symbol: str) -> pd.DataFrame:
    return pd.read_parquet(
        os.path.join(FEATURES_DIR, f"{symbol}_features.parquet"))


def build_all(end_iso: str = None):
    """Build + cache feature frames for the whole universe. Post-2022 reads
    are explicit allow_oos=True (disclosed; facts.log PIVOT_4NAME_SCOPE)."""
    import config
    from data.underlying_closes import load_closes
    from options_researcher.chains import load_range
    from options_researcher.earnings import load_earnings

    end_iso = end_iso or config.BACKTEST_END
    for symbol in config.UNIVERSE:
        closes = load_closes(symbol, "2017-01-01", end_iso, allow_oos=True)
        chains = load_range(symbol, config.BACKTEST_START, end_iso,
                            allow_oos=True)
        earn = load_earnings(symbol)
        frame = build_daily_features(symbol, config.BACKTEST_START, end_iso,
                                     closes=closes, chains=chains,
                                     earnings=earn)
        path = save_features(symbol, frame)
        print(f"{symbol}: {len(frame)} rows -> {path}")


if __name__ == "__main__":
    build_all()
```

- [ ] **Step 4: Run tests + full suite**

Run: `uv run python -m unittest tests.test_features -v && uv run python -m unittest discover -s tests`
Expected: all PASS (build_all is not exercised by tests — it needs the real
closes cache, which the orchestrator pulls after review)

- [ ] **Step 5: Commit**

```bash
git add options_researcher/features.py tests/test_features.py
git commit -m "feat(researcher): feature cache + universe builder entrypoint

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Orchestrator-only follow-ups (NOT implementer steps)

1. Run the verified blind pull: MSFT/AMZN/VST 2017-01-01..2026-06-30, CEG
   2022-01-01..2026-06-30 (`fetch_underlying_eod` per symbol). Append a
   facts.log line with row counts per symbol (no values).
2. Drop the compiled `data/earnings/*.csv` in place (separate research
   agent, spot-audited), run `load_earnings` on all four, commit CSVs.
3. Run `uv run python -m options_researcher.features` (build_all), sanity-
   check row counts (~2,130 MSFT/AMZN/VST, ~1,100 CEG), commit nothing
   (.tmp is disposable).

## Self-review notes

- Task 2's client call is explicitly marked adapt-to-verified-name with a
  STOP rule; tests never touch the network; the pull is orchestrator-only.
- `earnings_week` window is defined once (−5bd..+1bd) in code + docstring.
- `iv_rank` inclusive-rank matches the H3R-era convention (min 126, cap 252).
- Fixture chains use REAL 3rd-Friday dates so `nearest_monthly` is honestly
  exercised, not bypassed.
