# H9 Post-Earnings Conditional Historical Study — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the census tool, event/trigger/lifecycle runner, and adjudication for the H9 written study per `docs/superpowers/specs/2026-07-16-h9-post-earnings-historical-study-DRAFT.md`, so that after the owner's external review clears the freeze, exactly one registered run can execute.

**Architecture:** Three new focused modules (`h9_events` timing, `h9_census` counts-only data sufficiency, `h9_study` trigger + lifecycle + adjudication) plus a gated CLI (`tools/h9_run_study.py`). Everything composes existing frozen machinery: `trading_days`/`session_close_utc` (calendar), `load_raw_assertions` (SEC occurred archive; acceptance timestamp = `known_as_of_utc`), `get_eod_chain`/`passes_liquidity` (chains), `load_closes_adjusted` (reaction R), `adverse_buy`/`adverse_sell` + `COMMISSION_PER_CONTRACT` (fill model), `metrics.scoreboard` (CI90 verdict), `research.hashing` (receipt). The census is structurally unable to return P&L. The prereg gate refuses before touching data unless `H9_REGISTERED` exists in facts.log.

**Tech Stack:** Python 3.12, pandas, unittest, existing repo modules only (no new dependencies).

**HARD GATES (do not violate):**
- Tasks 1–6 build and test on synthetic fixtures only. NO real chain data is read by any test.
- Task 7 (registration) and Task 8 (the one real run) are **OWNER-GATED**: execute only after the owner confirms the external review PASS in chat. The orchestrator will hold these.
- The tombstoned H7 historical diagnostic is untouched: nothing here imports or calls `tools/h7_run_diagnostic`, `record_diagnostic_attempt`, `authorize_oos_run`, or `run_lane`.

---

### Task 1: H9 config block

**Files:**
- Modify: `config.py` (append after the H8 block, ~line 283)
- Test: `tests/test_h9_config.py`

- [ ] **Step 1: Write the failing test**

```python
"""H9 config block — approved values per spec 2026-07-16 (a78b4db)."""
import unittest

import config


class H9ConfigTests(unittest.TestCase):
    def test_owner_approved_values(self):
        self.assertEqual(config.H9_REACTION_MIN, 0.02)
        self.assertEqual(config.H9_NEXT_REPORT_EXIT_SESSIONS, 2)
        self.assertEqual(config.H9_MIN_ELIGIBLE_EVENTS, 60)
        self.assertEqual(config.H9_PREMIUM_CAP_DOLLARS, 600)
        self.assertEqual(config.H9_SECONDARY_COHORT, ("NOW", "MSFT", "VST", "CEG"))

    def test_universe_is_the_eight_archive_names(self):
        self.assertEqual(config.H9_NAMES, config.H7_BACKTEST_SYMBOLS)
        self.assertEqual(len(config.H9_NAMES), 8)

    def test_window_matches_frozen_h7_window(self):
        self.assertEqual(config.H9_WINDOW, (config.H7_BACKTEST_START, config.H7_BACKTEST_END))

    def test_inherited_h6_construction_unchanged(self):
        # H9 inherits these; if H6 values ever change, the H9 spec freeze is violated.
        self.assertEqual(config.H6_DTE_BAND, (45, 90))
        self.assertEqual(config.H6_DELTA_BAND, (0.30, 0.50))
        self.assertEqual(config.H6_TAKE_PROFIT_PCT, 1.00)
        self.assertEqual(config.H6_CLOSE_AT_DTE, 21)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_h9_config.py -q`
Expected: FAIL with `AttributeError: module 'config' has no attribute 'H9_REACTION_MIN'`

- [ ] **Step 3: Add the config block**

Append to `config.py` after the H8 block, matching the repo's banner style:

```python
# ---------------------------------------------------------------------------
# H9 -- post-earnings conditional HISTORICAL WRITTEN STUDY (spec
# docs/superpowers/specs/2026-07-16-h9-post-earnings-historical-study-DRAFT.md,
# owner-approved values 2026-07-16, entry mechanics disclosed in spec §5).
# One-run contract; kill-not-bless; NEVER a trading lane. Registration gated
# on the owner's external review (H9_REGISTERED fact required by the CLI gate).
# Construction is inherited from H6 (DTE/delta bands, TP, DTE-close); costs
# from the frozen repo cost model. Does NOT reopen the tombstoned H7
# historical diagnostic.
# ---------------------------------------------------------------------------
H9_NAMES = H7_BACKTEST_SYMBOLS          # the 8 audited archive names
H9_WINDOW = (H7_BACKTEST_START, H7_BACKTEST_END)
H9_REACTION_MIN = 0.02                  # owner-approved 2026-07-16
H9_NEXT_REPORT_EXIT_SESSIONS = 2        # owner-approved 2026-07-16
H9_MIN_ELIGIBLE_EVENTS = 60             # owner-approved 2026-07-16 (census floor)
H9_PREMIUM_CAP_DOLLARS = 600            # owner-approved: global MAX_LOSS_PER_TRADE binds
H9_SECONDARY_COHORT = ("NOW", "MSFT", "VST", "CEG")  # E1-uncontaminated, informational only
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_h9_config.py -q`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_h9_config.py
git commit -m "feat(h9): config block with owner-approved study values"
```

---

### Task 2: Event timing — `h9_events.py`

**Files:**
- Create: `options_researcher/h9_events.py`
- Test: `tests/test_h9_events.py`

Timing rules from spec §2: T_pre = last session whose close is **strictly before** the 8-K acceptance; T_dec = first session whose close is **strictly after**; T_entry = next session after T_dec. Dedupe = earliest acceptance per (symbol, occurred_date). No helper exists for "session whose close is strictly after X" — compose from `trading_days` + `session_close_utc`.

- [ ] **Step 1: Write the failing tests**

```python
"""H9 event timing — strict-inequality causality per spec §2 / owner rule 1."""
import unittest
from datetime import date, datetime, timezone

from options_researcher import h9_events as ev


def raw(symbol, occurred, accepted_iso, record_id="A0001", status="occurred"):
    return {
        "record_id": record_id,
        "symbol": symbol,
        "event_id": f"{symbol}-{occurred}",
        "status": status,
        "occurred_date": date.fromisoformat(occurred),
        "expected_date": None,
        "known_as_of_utc": datetime.fromisoformat(accepted_iso),
        "supersedes": "",
    }


class TimingTests(unittest.TestCase):
    # 2026-07-01 (Wed), 07-02 (Thu) are XNYS sessions; 07-03 observed holiday;
    # 07-06 (Mon) next session. Regular close 20:00 UTC (EDT).

    def test_amc_filing_decides_next_session(self):
        # accepted after Wednesday's close -> T_dec is Thursday, entry Monday
        e = ev.resolve_timing("MSFT", datetime(2026, 7, 1, 20, 3, 31, tzinfo=timezone.utc),
                              start_iso="2026-06-24", end_iso="2026-07-10")
        self.assertEqual(e, ("2026-07-01", "2026-07-02", "2026-07-06"))

    def test_bmo_filing_decides_same_session(self):
        # accepted 12:00 UTC (before close) -> T_dec is that same day
        e = ev.resolve_timing("MSFT", datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
                              start_iso="2026-06-24", end_iso="2026-07-10")
        self.assertEqual(e, ("2026-06-30", "2026-07-01", "2026-07-02"))

    def test_acceptance_exactly_at_close_is_after(self):
        # strict inequality: close(T) is NOT strictly after ts==close(T)
        from data.cache_runner import session_close_utc
        close = session_close_utc("2026-07-01")
        e = ev.resolve_timing("MSFT", close, start_iso="2026-06-24", end_iso="2026-07-10")
        self.assertEqual(e[0], "2026-06-30")  # t_pre must be STRICTLY before
        self.assertEqual(e[1], "2026-07-02")  # decision rolls to the next session

    def test_holiday_gap_entry(self):
        # accepted after Thursday 07-02 close -> T_dec Monday 07-06, entry Tuesday 07-07
        e = ev.resolve_timing("MSFT", datetime(2026, 7, 2, 21, 0, tzinfo=timezone.utc),
                              start_iso="2026-06-24", end_iso="2026-07-10")
        self.assertEqual(e, ("2026-07-02", "2026-07-06", "2026-07-07"))

    def test_window_edge_returns_none(self):
        e = ev.resolve_timing("MSFT", datetime(2026, 7, 9, 21, 0, tzinfo=timezone.utc),
                              start_iso="2026-06-24", end_iso="2026-07-10")
        self.assertIsNone(e[2])  # no entry session inside the window


class DedupeTests(unittest.TestCase):
    def test_earliest_acceptance_wins_and_amendment_ignored(self):
        rows = [
            raw("MSFT", "2026-04-29", "2026-04-29T20:03:31+00:00", "A0001"),
            raw("MSFT", "2026-04-29", "2026-05-02T10:00:00+00:00", "A0002"),  # 8-K/A later
        ]
        events = ev.derive_events(rows, symbols=("MSFT",))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].accepted_utc.isoformat(), "2026-04-29T20:03:31+00:00")

    def test_non_occurred_rows_excluded(self):
        rows = [raw("MSFT", "2026-04-29", "2026-04-29T20:03:31+00:00", status="confirmed")]
        self.assertEqual(ev.derive_events(rows, symbols=("MSFT",)), [])

    def test_symbols_outside_universe_excluded(self):
        rows = [raw("TSLA", "2026-04-29", "2026-04-29T20:03:31+00:00")]
        self.assertEqual(ev.derive_events(rows, symbols=("MSFT",)), [])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_h9_events.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'options_researcher.h9_events'`

- [ ] **Step 3: Implement `options_researcher/h9_events.py`**

```python
"""H9 event derivation — verified occurred reports -> causal session timing.

Spec: docs/superpowers/specs/2026-07-16-h9-post-earnings-historical-study-DRAFT.md §2.
The acceptance timestamp is the raw store's known_as_of_utc (8-K Item 2.02
acceptanceDateTime). Strict inequalities everywhere: a filing accepted exactly
at a session close belongs to the NEXT session's information set.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from data.cache_runner import session_close_utc, trading_days


@dataclass(frozen=True)
class H9Event:
    symbol: str
    occurred_date: date
    accepted_utc: datetime
    t_pre: str | None = None
    t_dec: str | None = None
    t_entry: str | None = None
    exclusion: str | None = None  # reason code once census runs


def resolve_timing(symbol: str, accepted_utc: datetime, *, start_iso: str,
                   end_iso: str) -> tuple[str | None, str | None, str | None]:
    """(t_pre, t_dec, t_entry) ISO dates inside [start_iso, end_iso], else None slots."""
    days = trading_days(start_iso, end_iso)
    t_pre = None
    t_dec = None
    for d in days:
        close = session_close_utc(d)
        if close < accepted_utc:
            t_pre = d
        elif close > accepted_utc:
            t_dec = d
            break
        # close == accepted_utc: not strictly before (so NOT t_pre) and not
        # strictly after (so NOT t_dec) — skip; t_pre stays the prior session
        # and t_dec resolves at the next iteration's close
    if t_dec is None:
        return (t_pre, None, None)
    later = [d for d in days if d > t_dec]
    t_entry = later[0] if later else None
    return (t_pre, t_dec, t_entry)


def derive_events(raw_rows: list[dict], *, symbols: tuple[str, ...],
                  start_iso: str | None = None, end_iso: str | None = None) -> list[H9Event]:
    """Occurred rows -> deduped H9Event list (earliest acceptance per report date)."""
    import config
    start_iso = start_iso or config.H9_WINDOW[0]
    end_iso = end_iso or config.H9_WINDOW[1]
    best: dict[tuple[str, date], dict] = {}
    for row in raw_rows:
        if row.get("status") != "occurred" or row["symbol"] not in symbols:
            continue
        if row.get("occurred_date") is None or row.get("known_as_of_utc") is None:
            continue
        key = (row["symbol"], row["occurred_date"])
        if key not in best or row["known_as_of_utc"] < best[key]["known_as_of_utc"]:
            best[key] = row
    events = []
    for (symbol, occurred), row in sorted(best.items()):
        t_pre, t_dec, t_entry = resolve_timing(
            symbol, row["known_as_of_utc"], start_iso=start_iso, end_iso=end_iso)
        events.append(H9Event(symbol=symbol, occurred_date=occurred,
                              accepted_utc=row["known_as_of_utc"],
                              t_pre=t_pre, t_dec=t_dec, t_entry=t_entry))
    return events
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_h9_events.py -q`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add options_researcher/h9_events.py tests/test_h9_events.py
git commit -m "feat(h9): causal event timing with strict-inequality acceptance cutoffs"
```

---

### Task 3: Counts-only census — `h9_census.py`

**Files:**
- Create: `options_researcher/h9_census.py`
- Test: `tests/test_h9_census.py`

Spec §6: the census inspects ONLY data sufficiency; it is structurally unable to return returns/P&L. It reads the T_entry chain solely to test contract existence + liquidity; exit-window coverage is a **file-presence** check (flat cache layout `.cache/chains/<SYMBOL>_<DATE>.parquet`), never a read.

- [ ] **Step 1: Write the failing tests**

```python
"""H9 census — counts and data sufficiency only; structurally no P&L."""
import inspect
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

import pandas as pd

from options_researcher import h9_census as cz
from options_researcher.h9_events import H9Event


def entry_chain(rows):
    cols = ["expiration", "strike", "right", "bid", "ask", "open_interest",
            "iv", "delta", "gamma", "theta", "vega"]
    data = [
        {"expiration": e, "strike": k, "right": r, "bid": b, "ask": a,
         "open_interest": oi, "iv": 0.5, "delta": d, "gamma": 0.0,
         "theta": 0.0, "vega": 0.0}
        for (e, k, r, b, a, oi, d) in rows
    ]
    return pd.DataFrame(data, columns=cols)


def event(symbol="MSFT", occurred="2026-04-29", t_pre="2026-04-29",
          t_dec="2026-04-30", t_entry="2026-05-01"):
    return H9Event(symbol=symbol, occurred_date=date.fromisoformat(occurred),
                   accepted_utc=datetime(2026, 4, 29, 20, 3, tzinfo=timezone.utc),
                   t_pre=t_pre, t_dec=t_dec, t_entry=t_entry)


GOOD_ROW = ("2026-06-19", 400.0, "C", 9.8, 10.0, 500, 0.40)  # monthly, in-band


class CensusStructureTests(unittest.TestCase):
    def test_census_result_has_no_price_or_pnl_fields(self):
        fields = set(cz.CensusResult.__dataclass_fields__)
        self.assertFalse(fields & {"pnl", "returns", "prices", "marks", "proceeds"})

    def test_census_module_never_imports_exit_pricing(self):
        src = inspect.getsource(cz)
        self.assertNotIn("adverse_sell", src)
        self.assertNotIn("scoreboard", src)


class CensusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.chain_dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def touch_chain(self, symbol, iso):
        (self.chain_dir / f"{symbol}_{iso}.parquet").touch()

    def test_missing_entry_chain_excluded(self):
        closes = pd.Series({"2026-04-29": 100.0, "2026-04-30": 103.0})
        with mock.patch.object(cz, "_entry_chain", side_effect=FileNotFoundError):
            with mock.patch.object(cz, "_closes", return_value=closes):
                res = cz.run_census([event()], chain_dir=self.chain_dir)
        self.assertEqual(res.reasons.get("missing_entry_chain"), 1)
        self.assertEqual(res.eligible_count, 0)

    def test_window_edge_excluded(self):
        e = event(t_entry=None)
        res = cz.run_census([e], chain_dir=self.chain_dir)
        self.assertEqual(res.reasons.get("window_edge"), 1)

    def test_eligible_event_counted_with_manifest(self):
        closes = pd.Series({"2026-04-29": 100.0, "2026-04-30": 103.0})
        self.touch_chain("MSFT", "2026-05-01")
        with mock.patch.object(cz, "_entry_chain",
                               return_value=entry_chain([GOOD_ROW])):
            with mock.patch.object(cz, "_closes", return_value=closes):
                res = cz.run_census([event()], chain_dir=self.chain_dir)
        self.assertEqual(res.eligible_count, 1)
        self.assertEqual(res.per_symbol["MSFT"]["eligible"], 1)
        self.assertTrue(res.floor_met is False)  # 1 < H9_MIN_ELIGIBLE_EVENTS

    def test_no_contract_in_bands_excluded(self):
        closes = pd.Series({"2026-04-29": 100.0, "2026-04-30": 103.0})
        bad = ("2026-06-19", 400.0, "C", 9.8, 10.0, 500, 0.10)  # delta below band
        with mock.patch.object(cz, "_entry_chain", return_value=entry_chain([bad])):
            with mock.patch.object(cz, "_closes", return_value=closes):
                res = cz.run_census([event()], chain_dir=self.chain_dir)
        self.assertEqual(res.reasons.get("no_contract_in_bands"), 1)

    def test_exit_window_gaps_are_warn_not_exclusion(self):
        closes = pd.Series({"2026-04-29": 100.0, "2026-04-30": 103.0})
        # entry chain exists but no exit-window files touched -> warn count > 0
        with mock.patch.object(cz, "_entry_chain",
                               return_value=entry_chain([GOOD_ROW])):
            with mock.patch.object(cz, "_closes", return_value=closes):
                res = cz.run_census([event()], chain_dir=self.chain_dir)
        self.assertEqual(res.eligible_count, 1)
        self.assertGreater(res.exit_window_gap_days, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_h9_census.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'options_researcher.h9_census'`

- [ ] **Step 3: Implement `options_researcher/h9_census.py`**

```python
"""H9 eligibility census — counts and data sufficiency ONLY (spec §6).

Charter: this module may read the T_entry chain solely to test contract
existence and liquidity, and may test exit-window coverage only by file
PRESENCE. It never prices an exit, never computes a return, and never
imports exit-side fill helpers. That restriction is enforced by tests.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

import config
from data.cache_runner import trading_days
from data.thetadata_adapter import get_eod_chain, passes_liquidity
from data.underlying_closes import load_closes_adjusted
from options_researcher.chains import is_monthly
from options_researcher.h9_events import H9Event
from research.hashing import sha256_file

REASONS = ("window_edge", "registry_excluded", "missing_closes",
           "missing_entry_chain", "no_contract_in_bands", "entry_liquidity_fail",
           "no_acceptance_ts")


@dataclass
class CensusResult:
    eligible_count: int
    per_symbol: dict
    reasons: Counter
    exit_window_gap_days: int
    manifest: list = field(default_factory=list)  # (path, sha256) of files read
    floor_met: bool = False
    eligible_events: list = field(default_factory=list)


def _entry_chain(symbol: str, iso: str) -> pd.DataFrame:
    return get_eod_chain(symbol, iso, allow_oos=True)


def _closes(symbol: str, start_iso: str, end_iso: str) -> pd.Series:
    return load_closes_adjusted(symbol, start_iso, end_iso, allow_oos=True)


def _dte(entry_iso: str, expiration) -> int:
    exp = expiration if isinstance(expiration, date) else date.fromisoformat(str(expiration)[:10])
    return (exp - date.fromisoformat(entry_iso)).days


def _has_admissible_contract(chain: pd.DataFrame, entry_iso: str) -> tuple[bool, str]:
    calls = chain[chain["right"] == "C"]
    lo_d, hi_d = config.H6_DELTA_BAND
    lo_t, hi_t = config.H6_DTE_BAND
    in_band = calls[
        (calls["delta"] >= lo_d) & (calls["delta"] <= hi_d)
        & (calls["expiration"].map(lambda e: lo_t <= _dte(entry_iso, e) <= hi_t))
        & (calls["expiration"].map(lambda e: is_monthly(
            e if isinstance(e, date) else date.fromisoformat(str(e)[:10]))))
    ]
    if in_band.empty:
        return False, "no_contract_in_bands"
    liquid = in_band[in_band.apply(
        lambda r: passes_liquidity(r["open_interest"], r["bid"], r["ask"]), axis=1)]
    if liquid.empty:
        return False, "entry_liquidity_fail"
    return True, ""


def _max_exit_horizon(entry_iso: str) -> str:
    # widest possible hold: entry DTE up to H6_DTE_BAND[1] days to expiry
    days = trading_days(entry_iso, config.H9_WINDOW[1])
    horizon = min(len(days) - 1, config.H6_DTE_BAND[1])
    return days[horizon] if days else entry_iso


def run_census(events: list[H9Event], *, chain_dir: Path,
               floor: int | None = None) -> CensusResult:
    floor = config.H9_MIN_ELIGIBLE_EVENTS if floor is None else floor
    reasons: Counter = Counter()
    per_symbol: dict = {}
    manifest: list = []
    eligible: list = []
    gap_days = 0
    for e in events:
        stats = per_symbol.setdefault(e.symbol, {"eligible": 0, "excluded": 0})
        if e.t_entry is None or e.t_dec is None or e.t_pre is None:
            reasons["window_edge"] += 1
            stats["excluded"] += 1
            continue
        try:
            closes = _closes(e.symbol, e.t_pre, e.t_dec)
        except Exception:
            closes = pd.Series(dtype=float)
        if e.t_pre not in closes.index or e.t_dec not in closes.index:
            reasons["missing_closes"] += 1
            stats["excluded"] += 1
            continue
        try:
            chain = _entry_chain(e.symbol, e.t_entry)
        except Exception:
            reasons["missing_entry_chain"] += 1
            stats["excluded"] += 1
            continue
        entry_path = chain_dir / f"{e.symbol}_{e.t_entry}.parquet"
        if entry_path.exists():
            manifest.append((str(entry_path), sha256_file(entry_path)))
        ok, reason = _has_admissible_contract(chain, e.t_entry)
        if not ok:
            reasons[reason] += 1
            stats["excluded"] += 1
            continue
        # exit-window coverage: PRESENCE only, never read
        for d in trading_days(e.t_entry, _max_exit_horizon(e.t_entry)):
            if not (chain_dir / f"{e.symbol}_{d}.parquet").exists():
                gap_days += 1
        stats["eligible"] += 1
        eligible.append(e)
    res = CensusResult(eligible_count=len(eligible), per_symbol=per_symbol,
                       reasons=reasons, exit_window_gap_days=gap_days,
                       manifest=manifest, eligible_events=eligible)
    res.floor_met = res.eligible_count >= floor
    return res
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_h9_census.py -q`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add options_researcher/h9_census.py tests/test_h9_census.py
git commit -m "feat(h9): counts-only eligibility census, structurally P&L-free"
```

---

### Task 4: Trigger + lifecycle + adjudication — `h9_study.py`

**Files:**
- Create: `options_researcher/h9_study.py`
- Test: `tests/test_h9_study.py`

Spec §3: R from adjusted closes; calls only when `R >= H9_REACTION_MIN`; contract = highest-delta monthly call in bands, entry cost = `adverse_buy(ask)*100 + COMMISSION_PER_CONTRACT`, cap `H9_PREMIUM_CAP_DOLLARS`; exits priority pre-next-report > 21-DTE > +100% TP, decisions at close, fills next session (`adverse_sell(bid)*100 − COMMISSION_PER_CONTRACT`), missing exit chain = visible gap + first later valid session. Mark convention mirrors `h6_watch.evaluate_exit` exactly (proceeds vs `entry_cost * (1 + TP)`).

- [ ] **Step 1: Write the failing tests**

```python
"""H9 trigger + lifecycle on injected fixtures. No real data."""
import unittest
from datetime import date, datetime, timezone
from unittest import mock

import pandas as pd

import config
from options_researcher import h9_study as st
from options_researcher.h9_events import H9Event


def chain(rows):
    cols = ["expiration", "strike", "right", "bid", "ask", "open_interest",
            "iv", "delta", "gamma", "theta", "vega"]
    return pd.DataFrame(
        [{"expiration": e, "strike": k, "right": r, "bid": b, "ask": a,
          "open_interest": oi, "iv": 0.5, "delta": d, "gamma": 0.0,
          "theta": 0.0, "vega": 0.0} for (e, k, r, b, a, oi, d) in rows],
        columns=cols)


def ev(t_pre="2026-04-29", t_dec="2026-04-30", t_entry="2026-05-01"):
    return H9Event(symbol="MSFT", occurred_date=date(2026, 4, 29),
                   accepted_utc=datetime(2026, 4, 29, 20, 3, tzinfo=timezone.utc),
                   t_pre=t_pre, t_dec=t_dec, t_entry=t_entry)


ENTRY = ("2026-06-19", 400.0, "C", 9.8, 10.0, 500, 0.40)  # monthly


class TriggerTests(unittest.TestCase):
    def test_reaction_below_min_is_no_trade(self):
        closes = pd.Series({"2026-04-29": 100.0, "2026-04-30": 101.0})  # +1% < 2%
        self.assertEqual(st.trigger(ev(), closes), "reaction_below_min")

    def test_negative_reaction_is_no_trade(self):
        closes = pd.Series({"2026-04-29": 100.0, "2026-04-30": 95.0})
        self.assertEqual(st.trigger(ev(), closes), "reaction_below_min")

    def test_positive_reaction_triggers_call(self):
        closes = pd.Series({"2026-04-29": 100.0, "2026-04-30": 103.0})
        self.assertEqual(st.trigger(ev(), closes), "call")


class SelectionTests(unittest.TestCase):
    def test_highest_delta_in_band_wins(self):
        rows = [ENTRY, ("2026-06-19", 390.0, "C", 12.0, 12.4, 500, 0.48),
                ("2026-06-19", 380.0, "C", 15.0, 15.5, 500, 0.55)]  # out of band
        pick = st.select_contract(chain(rows), "2026-05-01")
        self.assertEqual(pick["delta"], 0.48)

    def test_premium_cap_binds(self):
        # adverse_buy(10.0)=10.10 -> $1010.65 > $600 cap -> cancel
        pick = st.select_contract(chain([ENTRY]), "2026-05-01")
        self.assertIsNone(st.entry_cost_if_within_cap(pick))
        cheap = ("2026-06-19", 430.0, "C", 4.8, 5.0, 500, 0.32)
        pick2 = st.select_contract(chain([cheap, ENTRY]), "2026-05-01")
        # highest-delta preference would pick 0.40 but it breaches the cap ->
        # selection is band-first; cap check is a cancel, not a re-pick
        self.assertEqual(pick2["delta"], 0.40)
        self.assertIsNone(st.entry_cost_if_within_cap(pick2))


class LifecycleTests(unittest.TestCase):
    def _provider(self, marks):
        # marks: {iso: (bid, ask)} for the held contract
        def get(symbol, iso):
            if iso not in marks:
                raise FileNotFoundError(iso)
            b, a = marks[iso]
            return chain([("2026-06-19", 430.0, "C", b, a, 500, 0.32)])
        return get

    def test_take_profit_decided_then_filled_next_session(self):
        marks = {"2026-05-01": (4.8, 5.0),   # entry: cost 505.65
                 "2026-05-04": (11.0, 11.2), # proceeds 1088.35 >= 2x cost -> TP decision
                 "2026-05-05": (10.0, 10.2)} # fill next session at adverse_sell(10.0)
        trade = st.simulate_trade(ev(), self._provider(marks),
                                  next_report_iso=None)
        self.assertEqual(trade["exit_reason"], "take_profit")
        self.assertEqual(trade["exit_fill_session"], "2026-05-05")
        self.assertAlmostEqual(trade["pnl"],
                               (10.0 * 0.99 * 100 - 0.65) - (5.0 * 1.01 * 100 + 0.65),
                               delta=1.5)  # penny rounding tolerance

    def test_missing_exit_chain_visible_gap_then_next_valid(self):
        marks = {"2026-05-01": (4.8, 5.0),
                 "2026-05-04": (11.0, 11.2),
                 # 05-05 missing -> gap; fill 05-06
                 "2026-05-06": (9.5, 9.7)}
        trade = st.simulate_trade(ev(), self._provider(marks), next_report_iso=None)
        self.assertEqual(trade["exit_fill_session"], "2026-05-06")
        self.assertIn("2026-05-05", trade["gaps"])

    def test_pre_next_report_exit_outranks_tp(self):
        marks = {"2026-05-01": (4.8, 5.0),
                 "2026-05-04": (11.0, 11.2),
                 "2026-05-05": (11.0, 11.2)}
        # next report 2026-05-06 -> exit decision at 2 sessions before = 05-04
        trade = st.simulate_trade(ev(), self._provider(marks),
                                  next_report_iso="2026-05-06")
        self.assertEqual(trade["exit_reason"], "pre_next_report")


class AdjudicationTests(unittest.TestCase):
    def test_vocabulary_mapping(self):
        self.assertEqual(st.map_verdict({"verdict": "FAIL (CI90 upper < 0)"}),
                         "REJECTED")
        self.assertEqual(st.map_verdict({"verdict": "INSUFFICIENT SAMPLE (n_loss=3)"}),
                         "INSUFFICIENT_SAMPLE")
        self.assertEqual(st.map_verdict({"verdict": "NO EDGE"}),
                         "NOT_REJECTED_FOR_THIS_NARROW_HISTORICAL_TEST")
        self.assertEqual(st.map_verdict({"verdict": "PASS (CI90 lower > 0)"}),
                         "NOT_REJECTED_FOR_THIS_NARROW_HISTORICAL_TEST")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_h9_study.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'options_researcher.h9_study'`

- [ ] **Step 3: Implement `options_researcher/h9_study.py`**

```python
"""H9 written study — trigger, lifecycle, adjudication (spec §3, §7).

Mark convention mirrors h6_watch.evaluate_exit exactly: proceeds =
adverse_sell(bid)*100*contracts - COMMISSION_PER_CONTRACT*contracts, compared
to entry_cost*(1+TP). Decisions at session close; fills at the NEXT session's
close (T->T+1). Exit priority (spec §3): pre_next_report > dte_close >
take_profit. One contract per event. NO trading path exists here.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

import config
import metrics
from data.cache_runner import trading_days
from data.pandas_feed import adverse_buy, adverse_sell, quote_valid
from data.thetadata_adapter import passes_liquidity
from options_researcher.chains import is_monthly
from options_researcher.h9_events import H9Event

VOCAB = ("REJECTED", "INSUFFICIENT_SAMPLE",
         "NOT_REJECTED_FOR_THIS_NARROW_HISTORICAL_TEST")


def trigger(event: H9Event, closes: pd.Series) -> str:
    r = closes[event.t_dec] / closes[event.t_pre] - 1.0
    return "call" if r >= config.H9_REACTION_MIN else "reaction_below_min"


def _exp_date(e) -> date:
    return e if isinstance(e, date) else date.fromisoformat(str(e)[:10])


def _dte(iso: str, expiration) -> int:
    return (_exp_date(expiration) - date.fromisoformat(iso)).days


def select_contract(chain: pd.DataFrame, entry_iso: str) -> pd.Series | None:
    calls = chain[chain["right"] == "C"]
    lo_d, hi_d = config.H6_DELTA_BAND
    lo_t, hi_t = config.H6_DTE_BAND
    band = calls[
        (calls["delta"] >= lo_d) & (calls["delta"] <= hi_d)
        & (calls["expiration"].map(lambda e: lo_t <= _dte(entry_iso, e) <= hi_t))
        & (calls["expiration"].map(lambda e: is_monthly(_exp_date(e))))
    ]
    band = band[band.apply(lambda r: quote_valid(r["bid"], r["ask"])
                           and passes_liquidity(r["open_interest"], r["bid"], r["ask"]),
                           axis=1)]
    if band.empty:
        return None
    return band.sort_values("delta", ascending=False).iloc[0]


def entry_cost_if_within_cap(row: pd.Series | None) -> float | None:
    if row is None:
        return None
    cost = round(adverse_buy(row["ask"]) * 100.0 + config.COMMISSION_PER_CONTRACT, 2)
    return cost if cost <= config.H9_PREMIUM_CAP_DOLLARS else None


def _proceeds(bid: float) -> float:
    return round(adverse_sell(bid) * 100.0 - config.COMMISSION_PER_CONTRACT, 2)


def simulate_trade(event: H9Event, chain_provider, *, next_report_iso: str | None) -> dict | None:
    """One event -> one trade dict or None (no trade / cancel). chain_provider(symbol, iso)."""
    entry_chain = chain_provider(event.symbol, event.t_entry)
    row = select_contract(entry_chain, event.t_entry)
    cost = entry_cost_if_within_cap(row)
    if cost is None:
        return None
    expiration, strike = _exp_date(row["expiration"]), float(row["strike"])
    pre_report_cutoff = None
    if next_report_iso:
        pre = trading_days(event.t_entry, next_report_iso)
        k = config.H9_NEXT_REPORT_EXIT_SESSIONS
        pre_report_cutoff = pre[-(k + 1)] if len(pre) > k else event.t_entry
    sessions = trading_days(event.t_entry, config.H9_WINDOW[1])[1:]
    decision, gaps = None, []
    for s in sessions:
        if _dte(s, expiration) < 0:
            break
        try:
            ch = chain_provider(event.symbol, s)
        except FileNotFoundError:
            gaps.append(s)
            continue
        m = ch[(ch["right"] == "C") & (ch["strike"] == strike)
               & (ch["expiration"].map(_exp_date) == expiration)]
        if m.empty or not quote_valid(m.iloc[0]["bid"], m.iloc[0]["ask"]):
            gaps.append(s)
            continue
        bid = float(m.iloc[0]["bid"])
        if pre_report_cutoff and s >= pre_report_cutoff:
            decision = (s, "pre_next_report")
        elif _dte(s, expiration) <= config.H6_CLOSE_AT_DTE:
            decision = (s, "dte_close")
        elif _proceeds(bid) >= cost * (1.0 + config.H6_TAKE_PROFIT_PCT):
            decision = (s, "take_profit")
        if decision:
            break
    if decision is None:
        return {"symbol": event.symbol, "entry_date": event.t_entry, "pnl": None,
                "capital_at_risk": cost, "exit_reason": "unresolved_data_gap",
                "gaps": gaps, "exit_fill_session": None}
    dec_session, reason = decision
    for s in trading_days(dec_session, config.H9_WINDOW[1])[1:]:
        try:
            ch = chain_provider(event.symbol, s)
        except FileNotFoundError:
            gaps.append(s)
            continue
        m = ch[(ch["right"] == "C") & (ch["strike"] == strike)
               & (ch["expiration"].map(_exp_date) == expiration)]
        if m.empty or not quote_valid(m.iloc[0]["bid"], m.iloc[0]["ask"]):
            gaps.append(s)
            continue
        proceeds = _proceeds(float(m.iloc[0]["bid"]))
        return {"symbol": event.symbol, "entry_date": event.t_entry,
                "pnl": round(proceeds - cost, 2), "capital_at_risk": cost,
                "exit_reason": reason, "exit_fill_session": s, "gaps": gaps}
    return {"symbol": event.symbol, "entry_date": event.t_entry, "pnl": None,
            "capital_at_risk": cost, "exit_reason": "unresolved_data_gap",
            "gaps": gaps, "exit_fill_session": None}


def map_verdict(board: dict) -> str:
    v = board["verdict"]
    if v.startswith("FAIL"):
        return "REJECTED"
    if v.startswith("INSUFFICIENT"):
        return "INSUFFICIENT_SAMPLE"
    return "NOT_REJECTED_FOR_THIS_NARROW_HISTORICAL_TEST"


def adjudicate(trades: list[dict]) -> dict:
    complete = [t for t in trades if t["pnl"] is not None]
    board = metrics.scoreboard(complete, label="H9")
    board["h9_outcome"] = map_verdict(board)
    board["unresolved_data_gap_trades"] = len(trades) - len(complete)
    return board
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_h9_study.py -q`
Expected: PASS (10 tests)

- [ ] **Step 5: Run the full offline suite + linters**

Run: `uv run pytest -q && uv run ruff check . && uv run pyright`
Expected: all green (baseline 1,220+ tests still passing)

- [ ] **Step 6: Commit**

```bash
git add options_researcher/h9_study.py tests/test_h9_study.py
git commit -m "feat(h9): trigger, T->T+1 lifecycle with deterministic exit priority, adjudication"
```

---

### Task 5: Spec §8 edge-case test matrix

**Files:**
- Test: `tests/test_h9_edge_matrix.py`

The 11-item matrix from spec §8. Items 1–3, 5, 6, 8, 10, 11 are already covered by Tasks 2–4 tests; this task adds the remaining ones as explicit named tests so the matrix is auditable one-to-one.

- [ ] **Step 1: Write the failing tests**

```python
"""Spec §8 adversarial matrix — items not already covered by module tests.

Matrix map (spec item -> test):
 1 AMC filing            -> test_h9_events.TimingTests.test_amc_filing_decides_next_session
 2 BMO filing            -> test_h9_events.TimingTests.test_bmo_filing_decides_same_session
 3 boundary timestamp    -> test_h9_events.TimingTests.test_acceptance_exactly_at_close_is_after
 4 duplicate/amended 8-K -> HERE: immutable T_accept under 8-K/A
 5 missing entry chain   -> test_h9_census.CensusTests.test_missing_entry_chain_excluded
 6 missing exit chain    -> test_h9_study.LifecycleTests.test_missing_exit_chain_...
 7 split inside hold     -> HERE: strike/marks read from as-traded chain rows (raw),
                            reaction R from adjusted closes — assert both sources used
 8 holiday next session  -> test_h9_events.TimingTests.test_holiday_gap_entry
 9 registry exclusions   -> HERE: registry-window events reason-coded
10 next report < DTE     -> test_h9_study.LifecycleTests.test_pre_next_report_exit_outranks_tp
11 census cannot price   -> test_h9_census.CensusStructureTests (both tests)
"""
import unittest
from datetime import date, datetime, timezone

from options_researcher import h9_events as ev
from options_researcher import h9_study as st


class Item4AmendedFilingTests(unittest.TestCase):
    def test_8ka_amendment_never_moves_t_accept(self):
        rows = [
            {"record_id": "A1", "symbol": "SMCI", "event_id": "SMCI-2024Q2",
             "status": "occurred", "occurred_date": date(2024, 8, 6),
             "expected_date": None,
             "known_as_of_utc": datetime(2024, 8, 6, 20, 5, tzinfo=timezone.utc),
             "supersedes": ""},
            {"record_id": "A2", "symbol": "SMCI", "event_id": "SMCI-2024Q2-A",
             "status": "occurred", "occurred_date": date(2024, 8, 6),
             "expected_date": None,
             "known_as_of_utc": datetime(2024, 9, 3, 14, 0, tzinfo=timezone.utc),
             "supersedes": ""},
        ]
        events = ev.derive_events(rows, symbols=("SMCI",))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].accepted_utc,
                         datetime(2024, 8, 6, 20, 5, tzinfo=timezone.utc))


class Item7SplitDisciplineTests(unittest.TestCase):
    def test_reaction_uses_adjusted_and_contracts_use_raw(self):
        # structural assertion: trigger() consumes the adjusted series the
        # runner loads via load_closes_adjusted; contract math never touches it
        import inspect
        runner_src = inspect.getsource(st)
        self.assertNotIn("load_closes", runner_src)  # closes are injected, never loaded here
        census_src = inspect.getsource(__import__(
            "options_researcher.h9_census", fromlist=["x"]))
        self.assertIn("load_closes_adjusted", census_src)


class Item9RegistryExclusionTests(unittest.TestCase):
    def test_registry_window_reason_coded(self):
        # SMCI suspension window 2018-08-23..2020-05-04 (H7_AMENDMENT_V1_3):
        # an occurred event inside it must be excluded as registry_excluded,
        # not silently absent. The census applies data.audit_exceptions windows.
        from options_researcher import h9_census as cz
        e = ev.H9Event(symbol="SMCI", occurred_date=date(2019, 5, 2),
                       accepted_utc=datetime(2019, 5, 2, 20, 5, tzinfo=timezone.utc),
                       t_pre="2019-05-02", t_dec="2019-05-03", t_entry="2019-05-06")
        self.assertTrue(cz.in_registry_exclusion(e))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_h9_edge_matrix.py -q`
Expected: FAIL — `in_registry_exclusion` does not exist yet

- [ ] **Step 3: Add `in_registry_exclusion` to `h9_census.py`**

```python
# add to imports:
from data.audit_exceptions import exclusion_windows  # existing reviewed registry

# add function:
def in_registry_exclusion(event: H9Event) -> bool:
    """True when any of the event's sessions fall in a ratified registry window."""
    for symbol, start, end in exclusion_windows():
        if symbol != event.symbol:
            continue
        for iso in (event.t_pre, event.t_dec, event.t_entry):
            if iso and start <= iso <= end:
                return True
    return False
```

NOTE for implementer: check the actual export name in `data/audit_exceptions.py` first (`rg "def " data/audit_exceptions.py`). If the module exposes the registry as data rather than a function, adapt the import but keep `in_registry_exclusion`'s signature and add the registry check into `run_census` between the `window_edge` and closes checks, emitting reason `registry_excluded`.

- [ ] **Step 4: Wire the registry check into `run_census`** (insert immediately after the `window_edge` branch):

```python
        if in_registry_exclusion(e):
            reasons["registry_excluded"] += 1
            stats["excluded"] += 1
            continue
```

- [ ] **Step 5: Run the matrix + census tests**

Run: `uv run pytest tests/test_h9_edge_matrix.py tests/test_h9_census.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tests/test_h9_edge_matrix.py options_researcher/h9_census.py
git commit -m "test(h9): spec §8 adversarial matrix complete; registry exclusions reason-coded"
```

---

### Task 6: Gated CLI + receipt — `tools/h9_run_study.py`

**Files:**
- Create: `tools/h9_run_study.py`
- Test: `tests/test_h9_run_gate.py`

Pattern: `qm_prereg_gate` (refuse before data) + `h7_data_audit.write_receipt` (content-addressed binding). Two subcommands: `census` and `run`. BOTH refuse without the `H9_REGISTERED` fact. `run` additionally refuses if the census artifact is absent or `floor_met` is false, and refuses a second run if an `H9_RESULT` fact already exists (one-run contract).

- [ ] **Step 1: Write the failing tests**

```python
"""H9 CLI gate — refuses before touching any data."""
import tempfile
import unittest
from pathlib import Path

from tools import h9_run_study as cli


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        (self.base / "facts.log").write_text("")
        self.addCleanup(self.tmp.cleanup)

    def fact(self, text):
        with open(self.base / "facts.log", "a") as f:
            f.write(f"2026-07-16T00:00:00+00:00\t{text}\n")

    def test_refuses_without_registration_fact(self):
        msg = cli.h9_prereg_gate(base_dir=self.base)
        self.assertIsNotNone(msg)
        self.assertIn("H9_REGISTERED", msg)

    def test_clears_with_registration_fact(self):
        self.fact("H9_REGISTERED 2026-07-XX: spec sha256 abc at commit def")
        self.assertIsNone(cli.h9_prereg_gate(base_dir=self.base))

    def test_run_refuses_after_result_exists(self):
        self.fact("H9_REGISTERED 2026-07-XX: spec sha256 abc at commit def")
        self.fact("H9_RESULT 2026-07-XX: outcome REJECTED receipt xyz")
        msg = cli.h9_one_run_gate(base_dir=self.base)
        self.assertIsNotNone(msg)
        self.assertIn("one-run contract", msg)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_h9_run_gate.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `tools/h9_run_study.py`**

```python
"""H9 written-study CLI — census and the single gated run.

Refusal order (all BEFORE any market data is read):
  1. h9_prereg_gate: H9_REGISTERED fact must exist (owner external review
     precedes that fact per spec §8 order).
  2. h9_one_run_gate (run only): refuse when an H9_RESULT fact exists.
  3. run additionally requires the census artifact with floor_met=true.
This tool never touches the tombstoned H7 diagnostic path and never writes
the forward ledger.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import config
from research.facts import read_facts
from research.hashing import canonical_json, config_hash, cost_model_hash, sha256_file, sha256_hex

SPEC_PATH = Path("docs/superpowers/specs/2026-07-16-h9-post-earnings-historical-study-DRAFT.md")
CENSUS_ARTIFACT = Path("reports/h9/census.json")
RECEIPT_PATH = Path("reports/h9/receipt.json")


def h9_prereg_gate(base_dir="ledger") -> str | None:
    lines = read_facts(base_dir=base_dir)
    if not any(line.split("\t", 1)[-1].startswith("H9_REGISTERED") for line in lines):
        return ("H9 is not registered: no H9_REGISTERED fact in facts.log; "
                "the owner's external review and registration precede any data read. Refusing.")
    return None


def h9_one_run_gate(base_dir="ledger") -> str | None:
    lines = read_facts(base_dir=base_dir)
    if any(line.split("\t", 1)[-1].startswith("H9_RESULT") for line in lines):
        return "H9_RESULT already exists: the one-run contract is spent. Refusing."
    return None


def _code_sha() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()


def _census(chain_dir: Path) -> dict:
    # imports deferred so the gate refuses before any data module loads;
    # body supplied in step 4
    raise NotImplementedError("replaced in step 4")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("census", "run"))
    ap.add_argument("--chain-dir", default=".cache/chains")
    args = ap.parse_args(argv)
    refusal = h9_prereg_gate()
    if refusal:
        print(refusal)
        return 2
    if args.mode == "run":
        refusal = h9_one_run_gate()
        if refusal:
            print(refusal)
            return 2
        if not CENSUS_ARTIFACT.exists():
            print("no census artifact; run census first. Refusing.")
            return 2
        census = json.loads(CENSUS_ARTIFACT.read_text())
        if not census["floor_met"]:
            print("census floor unmet: outcome is INSUFFICIENT_SAMPLE without a run. Refusing.")
            return 2
    # ... census/run bodies in step 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Fill in the census and run bodies**

Replace the `_census` stub and complete `main`:

```python
def _events():
    from options_researcher.h7_earnings import load_raw_assertions
    from options_researcher.h9_events import derive_events
    return derive_events(load_raw_assertions(), symbols=config.H9_NAMES)


def _run_census(chain_dir: Path) -> dict:
    from options_researcher.h9_census import run_census
    res = run_census(_events(), chain_dir=chain_dir)
    payload = {
        "eligible_count": res.eligible_count,
        "per_symbol": res.per_symbol,
        "reasons": dict(res.reasons),
        "exit_window_gap_days": res.exit_window_gap_days,
        "floor": config.H9_MIN_ELIGIBLE_EVENTS,
        "floor_met": res.floor_met,
        "manifest_hash": sha256_hex(canonical_json(sorted(res.manifest))),
        "spec_sha256": sha256_file(SPEC_PATH),
        "code_sha": _code_sha(),
        "config_hash": config_hash(),
    }
    CENSUS_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    CENSUS_ARTIFACT.write_text(json.dumps(payload, indent=1, sort_keys=True))
    return payload


def _run_study(chain_dir: Path) -> dict:
    from data.thetadata_adapter import get_eod_chain
    from data.underlying_closes import load_closes_adjusted
    from options_researcher.h9_census import run_census
    from options_researcher.h9_events import H9Event
    from options_researcher.h9_study import adjudicate, simulate_trade, trigger

    events = _events()
    census = run_census(events, chain_dir=chain_dir)
    provider = lambda sym, iso: get_eod_chain(sym, iso, allow_oos=True)
    occurred_by_symbol: dict[str, list] = {}
    for e in events:
        occurred_by_symbol.setdefault(e.symbol, []).append(e.occurred_date.isoformat())
    trades, log = [], []
    for e in census.eligible_events:
        closes = load_closes_adjusted(e.symbol, e.t_pre, e.t_dec, allow_oos=True)
        sig = trigger(e, closes)
        if sig != "call":
            log.append({"event": f"{e.symbol}-{e.occurred_date}", "outcome": sig})
            continue
        nxt = sorted(d for d in occurred_by_symbol[e.symbol]
                     if d > e.occurred_date.isoformat())
        trade = simulate_trade(e, provider, next_report_iso=nxt[0] if nxt else None)
        if trade is None:
            log.append({"event": f"{e.symbol}-{e.occurred_date}", "outcome": "cancel"})
            continue
        trade["event"] = f"{e.symbol}-{e.occurred_date}"
        trades.append(trade)
    board = adjudicate(trades)
    secondary = adjudicate([t for t in trades if t["symbol"] in config.H9_SECONDARY_COHORT]) \
        if trades else {}
    receipt = {
        "study": "H9", "outcome": board["h9_outcome"], "board": board,
        "secondary_cohort_informational": secondary.get("h9_outcome"),
        "census": {k: v for k, v in json.loads(CENSUS_ARTIFACT.read_text()).items()},
        "n_trades": len(trades), "no_trade_log_count": len(log),
        "trade_log": log, "trades": trades,
        "spec_sha256": sha256_file(SPEC_PATH), "code_sha": _code_sha(),
        "config_hash": config_hash(), "cost_model_hash": cost_model_hash(),
    }
    bulk = {"trades", "trade_log", "board", "census"}
    receipt["receipt_hash"] = sha256_hex(canonical_json(
        {k: v for k, v in receipt.items() if k not in bulk}))
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=1, sort_keys=True, default=str))
    return receipt
```

Wire into `main`: `census` mode calls `_run_census(Path(args.chain_dir))` and prints the counts; `run` mode calls `_run_study(...)`, prints `receipt["outcome"]` and `receipt["receipt_hash"]`. Delete the `_census` stub and its broken import line.

- [ ] **Step 5: Run gate tests + full suite + linters**

Run: `uv run pytest tests/test_h9_run_gate.py -q && uv run pytest -q && uv run ruff check . && uv run pyright`
Expected: all green. The CLI without a registration fact exits 2 (verify manually: `uv run python -m tools.h9_run_study census` → refusal message, exit 2).

- [ ] **Step 6: Commit**

```bash
git add tools/h9_run_study.py tests/test_h9_run_gate.py
git commit -m "feat(h9): gated census/run CLI with content-addressed receipt; refuses before data"
```

---

### Task 7: Registration — **OWNER-GATED, orchestrator executes, not a subagent**

Preconditions (ALL must hold; verify in order):
1. Owner has confirmed in chat that the external review of the typed spec PASSED.
2. Working tree clean; Tasks 1–6 merged.

- [ ] **Step 1:** Rename spec: `git mv docs/superpowers/specs/2026-07-16-h9-post-earnings-historical-study-DRAFT.md docs/superpowers/specs/2026-07-16-h9-post-earnings-historical-study.md`, update the header DRAFT line to `Status: FROZEN <date>, external review PASS (owner, <date>)`, update `SPEC_PATH` in `tools/h9_run_study.py`, commit.
- [ ] **Step 2:** Compute `SPEC_SHA=$(uv run python -c "from research.hashing import sha256_file; print(sha256_file('docs/superpowers/specs/2026-07-16-h9-post-earnings-historical-study.md'))")` and `COMMIT=$(git rev-parse HEAD)`.
- [ ] **Step 3:** Append the trial-intent record (trial 11→12) via `research.ledger.append` with body `{"entry_type": "trial_intent", "hypothesis_id": "H9-post-earnings-call-historical-v1", "spec_sha256": SPEC_SHA, "code_sha": COMMIT, "notes": "registered written study; one-run contract; kill-not-bless"}`.
- [ ] **Step 4:** Append the fact: `H9_REGISTERED <date>: spec sha256 <SPEC_SHA> at commit <COMMIT>. Owner external review PASS (<date>, owner chat). Values owner-approved 2026-07-16 (entry mechanics disclosed in spec §5). One-run contract; outcomes REJECTED|INSUFFICIENT_SAMPLE|NOT_REJECTED_FOR_THIS_NARROW_HISTORICAL_TEST; never validates/rejects H7/H6/H8.`
- [ ] **Step 5:** Commit ledger files.

### Task 8: Census, then the ONE run — **OWNER-GATED, orchestrator executes**

- [ ] **Step 1:** `uv run python -m tools.h9_run_study census` — review counts with the owner. If `floor_met` false → append `H9_RESULT ...: outcome INSUFFICIENT_SAMPLE (census floor unmet, n=<x> < 60); no run executed` and STOP (that is the honest verdict).
- [ ] **Step 2:** `uv run python -m tools.h9_run_study run` — exactly once.
- [ ] **Step 3:** Append `H9_RESULT <date>: outcome <OUTCOME> receipt <receipt_hash> n_trades=<n> ...` fact; commit `reports/h9/` artifacts.
- [ ] **Step 4:** Report the outcome to the owner verbatim, including the secondary-cohort informational read. NO interpretation drift: INSUFFICIENT_SAMPLE and REJECTED are successful study outcomes.

---

## Self-review notes (against spec + interface map)

- Spec §2 timing (strict inequalities, boundary case, holiday) → Task 2 tests 1–4. ✓
- §3 trigger/selection/cap/exit-priority/T+1 fills/gap handling → Task 4. ✓
- §4 inheritance: H6 values imported, never re-typed → Tasks 1, 4. ✓
- §5 approved values → Task 1. ✓
- §6 census counts-only + structural no-P&L + floor short-circuit → Tasks 3, 6. ✓
- §7 vocabulary mapping (incl. PASS → NOT_REJECTED, kill-not-bless) → Task 4 AdjudicationTests. ✓
- §8 receipt binding + 11-item matrix + one-run contract + registration order → Tasks 5–8. ✓
- Known deferred check: `data/audit_exceptions.py` export name (Task 5 step 3 tells the implementer to verify with rg before wiring).
