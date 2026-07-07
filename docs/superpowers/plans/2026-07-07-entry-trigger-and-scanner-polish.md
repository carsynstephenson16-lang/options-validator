# Entry Trigger + ThetaData Exit + Scanner Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the owner's LEAPS entry triggers (VST ≤ $140, AMZN ≤ $220, IV-rank ≤ 0.5) as pre-registered config + a WAIT/FIRE watch CLI, add an FOMC-in-cycle descriptive flag, add vega/IV prose to buy-side cards, and document the ThetaData cancel-day checklist.

**Architecture:** Everything follows existing repo patterns: frozen constants in `config.py`, pure card/status functions with injected frames for offline tests, strict CSV loaders modeled on `options_researcher/earnings.py`, ledger pre-registration before any result exists. All new output is descriptive — nothing trades, writes positions, or re-ranks the frozen H5 rubric.

**Tech Stack:** Python 3.12 / uv / unittest (offline, no network) / pandas / ruff.

**Spec:** `docs/superpowers/specs/2026-07-07-entry-trigger-and-exit-plan-design.md`

**Commit policy:** every task ends in a commit once its tests are green ("done and green = commit").

---

### Task 1: Frozen entry-trigger constants + ledger pre-registration

**Files:**
- Modify: `config.py` (H5 block, after `H5_INCOME_DELTA` ~line 194)
- Modify: `ledger/facts.log` (append only — NEVER edit existing lines)

- [ ] **Step 1: Add constants to config.py**

```python
# H5 LEAPS entry trigger (owner-frozen 2026-07-07; ledger
# H5_ENTRY_TRIGGER_PREREG). ALL conditions must hold before the owner even
# evaluates an entry: close <= level AND iv_rank <= H5_ENTRY_IVR_MAX AND the
# 0.70-delta LEAPS candidate passes the liquidity gates. IVR_MAX is 0.5 (not
# the GREEN 0.3) because a pullback that hits the price level typically
# RAISES IV-rank; demanding bottom-tercile IV simultaneously risks a trigger
# that can never fire.
H5_ENTRY_TRIGGERS = {"VST": 140.0, "AMZN": 220.0}
H5_ENTRY_IVR_MAX = 0.5
```

- [ ] **Step 2: Append the pre-registration to the ledger**

Append one line to `ledger/facts.log` (timestamp = now, ISO-8601 UTC, tab-separated like every other line):

```
<ISO-TIMESTAMP>	H5_ENTRY_TRIGGER_PREREG 2026-07-07: owner-frozen LEAPS entry trigger, registered BEFORE any entry exists. Evaluate (never auto-enter) a 0.70-delta LEAPS per H5 CORE rules on a name when ALL of: (a) underlying close <= H5_ENTRY_TRIGGERS level (VST 140.00, AMZN 220.00), (b) iv_rank <= H5_ENTRY_IVR_MAX=0.5, (c) the candidate LEAPS passes frozen liquidity gates (MIN_OPEN_INTEREST, MAX_SPREAD_PCT). At most one LEAPS entered first; owner records any entry manually in data/positions/positions.csv. Rationale: pullbacks raise IV, so a price-only trigger can deliver a cheap stock with an expensive option; IVR_MAX=0.5 (not GREEN 0.3) so the trigger can actually fire. Tool = options_researcher/entry_watch.py (Task 2/3), alert-only.
```

- [ ] **Step 3: Run suite to confirm nothing broke**

Run: `uv run python -m unittest discover -s tests`
Expected: `OK` (370 tests)

- [ ] **Step 4: Commit**

```bash
git add config.py ledger/facts.log
git commit -m "feat(config): pre-registered H5 LEAPS entry triggers (VST 140 / AMZN 220, IVR<=0.5)"
```

---

### Task 2: entry_watch pure status logic (TDD)

**Files:**
- Create: `options_researcher/entry_watch.py`
- Create: `tests/test_entry_watch.py`

- [ ] **Step 1: Write the failing tests**

```python
"""tests/test_entry_watch.py"""
import unittest

import pandas as pd

import config
from options_researcher import entry_watch as ew


def _leaps_row(oi=500, bid=40.0, ask=41.0):
    return pd.Series({"open_interest": oi, "bid": bid, "ask": ask,
                      "strike": 140.0, "delta": 0.70})


class TriggerStatusTests(unittest.TestCase):
    def test_all_conditions_met_fires(self):
        s = ew.trigger_status("VST", close=139.50, iv_rank=0.40,
                              leaps_row=_leaps_row())
        self.assertEqual(s["verdict"], "FIRE")
        self.assertEqual(s["unmet"], [])

    def test_price_above_trigger_waits(self):
        s = ew.trigger_status("VST", close=158.63, iv_rank=0.40,
                              leaps_row=_leaps_row())
        self.assertEqual(s["verdict"], "WAIT")
        self.assertTrue(any("trigger" in u for u in s["unmet"]))

    def test_rich_iv_waits_even_below_price(self):
        s = ew.trigger_status("VST", close=139.00, iv_rank=0.80,
                              leaps_row=_leaps_row())
        self.assertEqual(s["verdict"], "WAIT")
        self.assertTrue(any("IV-rank" in u for u in s["unmet"]))

    def test_illiquid_leaps_waits(self):
        s = ew.trigger_status("VST", close=139.00, iv_rank=0.40,
                              leaps_row=_leaps_row(oi=10))
        self.assertEqual(s["verdict"], "WAIT")

    def test_missing_leaps_candidate_waits(self):
        s = ew.trigger_status("VST", close=139.00, iv_rank=0.40,
                              leaps_row=None)
        self.assertEqual(s["verdict"], "WAIT")
        self.assertTrue(any("no LEAPS candidate" in u for u in s["unmet"]))

    def test_nan_iv_rank_waits(self):
        s = ew.trigger_status("VST", close=139.00, iv_rank=float("nan"),
                              leaps_row=_leaps_row())
        self.assertEqual(s["verdict"], "WAIT")

    def test_uses_config_constants(self):
        self.assertEqual(ew.trigger_status("AMZN", close=219.0, iv_rank=0.1,
                                           leaps_row=_leaps_row())["trigger"],
                         config.H5_ENTRY_TRIGGERS["AMZN"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest discover -s tests -k entry_watch -v`
Expected: FAIL / ERROR with `ModuleNotFoundError: No module named 'options_researcher.entry_watch'`

- [ ] **Step 3: Write the implementation**

```python
"""options_researcher/entry_watch.py -- pre-registered LEAPS entry-trigger watch.

Prints one WAIT/FIRE line per name in config.H5_ENTRY_TRIGGERS. FIRE means
"evaluate a 0.70-delta LEAPS per H5 CORE rules now" -- never "buy". The rule
is pre-registered in ledger/facts.log (H5_ENTRY_TRIGGER_PREREG 2026-07-07).
Read-only: never writes positions, never trades. NaN IV-rank counts as
UNMET (unknown never passes a gate).
"""
from __future__ import annotations

import glob
import os
from datetime import date

import pandas as pd

import config
from data.thetadata_adapter import passes_liquidity


def trigger_status(symbol: str, *, close: float, iv_rank: float,
                   leaps_row) -> dict:
    """Grade one name against the frozen entry trigger. `leaps_row` is the
    0.70-delta LEAPS candidate row from the latest cached chain, or None
    when no candidate exists in the DTE band."""
    level = config.H5_ENTRY_TRIGGERS[symbol]
    price_ok = close <= level
    iv_ok = iv_rank <= config.H5_ENTRY_IVR_MAX  # NaN compares False
    liq_ok = bool(leaps_row is not None and passes_liquidity(
        leaps_row["open_interest"], leaps_row["bid"], leaps_row["ask"]))
    unmet = []
    if not price_ok:
        unmet.append(f"close ${close:,.2f} > trigger ${level:,.2f}")
    if not iv_ok:
        unmet.append(f"IV-rank {iv_rank:.2f} > {config.H5_ENTRY_IVR_MAX}")
    if not liq_ok:
        unmet.append("LEAPS fails liquidity gates" if leaps_row is not None
                     else "no LEAPS candidate in DTE band")
    return {"symbol": symbol, "close": close, "trigger": level,
            "iv_rank": iv_rank, "price_ok": price_ok, "iv_ok": iv_ok,
            "liq_ok": liq_ok, "unmet": unmet,
            "verdict": "WAIT" if unmet else "FIRE"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest discover -s tests -k entry_watch -v`
Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add options_researcher/entry_watch.py tests/test_entry_watch.py
git commit -m "feat(entry-watch): WAIT/FIRE status logic for pre-registered entry triggers"
```

---

### Task 3: entry_watch gather + CLI main

**Files:**
- Modify: `options_researcher/entry_watch.py`
- Modify: `tests/test_entry_watch.py`

- [ ] **Step 1: Write the failing tests (append to tests/test_entry_watch.py)**

```python
class MainTests(unittest.TestCase):
    def _rows(self):
        return [{"symbol": "VST", "close": 158.63, "trigger": 140.0,
                 "iv_rank": 0.47, "price_ok": False, "iv_ok": True,
                 "liq_ok": True, "unmet": ["close $158.63 > trigger $140.00"],
                 "verdict": "WAIT", "close_asof": "2026-07-06",
                 "chain_asof": "2026-07-06"},
                {"symbol": "AMZN", "close": 219.00, "trigger": 220.0,
                 "iv_rank": 0.30, "price_ok": True, "iv_ok": True,
                 "liq_ok": True, "unmet": [], "verdict": "FIRE",
                 "close_asof": "2026-07-06", "chain_asof": "2026-07-02"}]

    def test_main_prints_verdicts_and_staleness(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ew.main(rows=self._rows())
        out = buf.getvalue()
        self.assertIn("VST", out)
        self.assertIn("WAIT", out)
        self.assertIn("FIRE", out)
        self.assertIn("evaluate", out.lower())      # FIRE explains itself
        self.assertIn("stale", out.lower())         # AMZN chain older than close
        self.assertIn("never auto-enters", out)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run python -m unittest discover -s tests -k entry_watch -v`
Expected: `test_main_prints_verdicts_and_staleness` ERRORs (`ew.main` missing); the 7 Task-2 tests still PASS

- [ ] **Step 3: Implement _gather + main (append to entry_watch.py)**

```python
def _gather() -> list[dict]:
    """Real project state: free underlying closes, cached features, latest
    cached chain per name. Read-only; no network beyond the closes cache."""
    from data.underlying_closes import load_closes
    from options_researcher.features import load_features
    from options_researcher.studies.long_call_carry import _leaps_candidate

    out = []
    today = date.today().isoformat()
    for symbol in config.H5_ENTRY_TRIGGERS:
        closes = load_closes(symbol, "2018-01-01", today, allow_oos=True)
        close = float(closes.iloc[-1])
        close_asof = str(closes.index[-1])[:10]
        ivr = load_features(symbol)["iv_rank"].iloc[-1]
        iv_rank = float(ivr) if pd.notna(ivr) else float("nan")
        files = sorted(glob.glob(os.path.join(".cache", "chains",
                                              f"{symbol}_*.parquet")))
        leaps_row, chain_asof = None, None
        if files:
            chain_asof = (os.path.basename(files[-1]).split("_")[1]
                          .replace(".parquet", ""))
            chain = pd.read_parquet(files[-1])
            leaps_row = _leaps_candidate(chain, date.fromisoformat(chain_asof),
                                         config.H4_THESIS_DELTA)
        row = trigger_status(symbol, close=close, iv_rank=iv_rank,
                             leaps_row=leaps_row)
        row["close_asof"] = close_asof
        row["chain_asof"] = chain_asof
        out.append(row)
    return out


def main(rows: list[dict] | None = None) -> None:
    if rows is None:
        rows = _gather()
    print("H5 LEAPS ENTRY TRIGGER WATCH (pre-registered "
          "H5_ENTRY_TRIGGER_PREREG; this tool alerts, it never auto-enters)")
    for r in rows:
        line = (f"{r['symbol']}: {r['verdict']}  close ${r['close']:,.2f} "
                f"(as of {r['close_asof']}) vs trigger ${r['trigger']:,.2f}; "
                f"IV-rank {r['iv_rank']:.2f} (max "
                f"{config.H5_ENTRY_IVR_MAX})")
        if r["unmet"]:
            line += " -- waiting on: " + "; ".join(r["unmet"])
        else:
            line += (" -- ALL conditions met: evaluate the 0.70-delta LEAPS "
                     "per H5 CORE rules with FRESH data before any entry "
                     "(re-subscribe/audit first if the chain cache is old)")
        print(line)
        if r["chain_asof"] and r["chain_asof"] < r["close_asof"]:
            print(f"  note: chain cache is stale ({r['chain_asof']} < close "
                  f"{r['close_asof']}) -- liquidity check may be outdated")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests + the real CLI**

Run: `uv run python -m unittest discover -s tests -k entry_watch -v`
Expected: 8 tests PASS

Run: `uv run python -m options_researcher.entry_watch`
Expected: two lines, both WAIT today (VST close ~$158 > $140; AMZN close ~$238 > $220), no traceback

- [ ] **Step 5: Commit**

```bash
git add options_researcher/entry_watch.py tests/test_entry_watch.py
git commit -m "feat(entry-watch): gather real state + WAIT/FIRE CLI with staleness note"
```

---

### Task 4: Dashboard trigger pills

**Files:**
- Modify: `options_researcher/dashboard.py` (`assemble` ~line 119, `_party_card` ~line 244, plus `_party_card`'s call site in `render`)
- Modify: `tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test (append to tests/test_dashboard.py, matching its existing fixture style — read the file's existing `assemble`/`render` tests first and reuse their fixture kwargs)**

```python
class TriggerPillTests(unittest.TestCase):
    def test_render_shows_trigger_pills(self):
        from options_researcher import dashboard as d
        data = d.assemble(book={"marks": []}, facts=[], reports=[],
                          closes={}, triggers={"VST": "WAIT", "AMZN": "FIRE"})
        html = d.render(data)
        self.assertIn("TRIGGER: WAIT", html)
        self.assertIn("TRIGGER: FIRE", html)

    def test_assemble_default_triggers_never_raises(self):
        from options_researcher import dashboard as d
        data = d.assemble(book={"marks": []}, facts=[], reports=[], closes={})
        self.assertIsInstance(data["triggers"], dict)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run python -m unittest discover -s tests -k dashboard -v`
Expected: the two new tests fail (`assemble() got an unexpected keyword argument 'triggers'`); existing tests still pass

- [ ] **Step 3: Implement**

In `assemble`, add a `triggers` kwarg mirroring the other defaults:

```python
def assemble(*, book: dict | None = None, facts: list[str] | None = None,
            reports: list[str] | None = None,
            closes: dict[str, list[float]] | None = None,
            triggers: dict[str, str] | None = None) -> dict:
```

with the default loader (tolerant — the dashboard must render even if the
trigger gather hits missing caches):

```python
    if triggers is None:
        try:
            from options_researcher.entry_watch import _gather
            triggers = {r["symbol"]: r["verdict"] for r in _gather()}
        except Exception:
            triggers = {}
```

and add `"triggers": dict(triggers),` to the returned dict.

In `_party_card`, add a `trigger: str | None = None` parameter and a pill next to the role line:

```python
def _party_card(symbol: str, color: str, role: str, sparklines: dict,
                marks: list[dict], trigger: str | None = None) -> str:
```

```python
    trigger_html = ""
    if trigger:
        t_color = "#ff5470" if trigger == "FIRE" else "#caa53d"
        trigger_html = (f'<div class="party-trigger" style="color:{t_color}">'
                        f'TRIGGER: {_esc(trigger)}</div>')
```

and place `{trigger_html}` in the card template right after the
`party-role` div. At `_party_card`'s call site inside `render`, pass
`trigger=data.get("triggers", {}).get(symbol)`.

- [ ] **Step 4: Run tests + build the real dashboard**

Run: `uv run python -m unittest discover -s tests -k dashboard -v`
Expected: all PASS

Run: `uv run python -m options_researcher.dashboard`
Expected: writes `.tmp/dashboard/index.html`; VST and AMZN cards show `TRIGGER: WAIT`

- [ ] **Step 5: Commit**

```bash
git add options_researcher/dashboard.py tests/test_dashboard.py
git commit -m "feat(dashboard): entry-trigger WAIT/FIRE pills on VST/AMZN watch cards"
```

---

### Task 5: FOMC dates — official calendar → CSV + strict loader (TDD)

**Files:**
- Create: `data/events/fomc_dates.csv`
- Create: `options_researcher/fomc.py`
- Create: `tests/test_fomc.py`

- [ ] **Step 1: Fetch the official calendar (implementation-time action, NOT from memory)**

Fetch `https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm` (WebFetch or firecrawl). Extract every 2026 and 2027 FOMC meeting; record the **decision date** (the meeting's final day, when the statement is released). Validation before writing the CSV: exactly 8 scheduled meetings per year, all weekdays, strictly increasing. Cross-check the 2026 set against this remembered list — Jan 27–28, Mar 17–18, Apr 28–29, Jun 16–17, Jul 28–29, Sep 15–16, Oct 27–28, Dec 8–9 — **the fetched page wins any discrepancy**. If the fetch fails entirely, STOP this task and report; do not write dates from memory (claim discipline: Official-source required).

- [ ] **Step 2: Write the CSV**

`data/events/fomc_dates.csv`, one row per decision date, 2026 + 2027:

```csv
date,source_url
2026-01-28,https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
...(every decision date from the fetched page, strictly increasing)...
```

- [ ] **Step 3: Write the failing tests**

```python
"""tests/test_fomc.py"""
import tempfile
import unittest
from datetime import date
from unittest import mock

from options_researcher import fomc


class LoadFomcTests(unittest.TestCase):
    def test_real_file_loads_and_is_strictly_increasing(self):
        dates = fomc.load_fomc()
        self.assertGreaterEqual(len(dates), 8)   # at least the 2026 meetings
        self.assertTrue(all(isinstance(d, date) for d in dates))
        self.assertTrue(all(a < b for a, b in zip(dates, dates[1:])))
        self.assertTrue(all(d.weekday() < 5 for d in dates))

    def test_malformed_header_refused(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv",
                                         delete=False) as f:
            f.write("day,url\n2026-01-28,https://x\n")
        with mock.patch.object(fomc, "FOMC_PATH", f.name):
            with self.assertRaises(ValueError):
                fomc.load_fomc()

    def test_empty_source_url_refused(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv",
                                         delete=False) as f:
            f.write("date,source_url\n2026-01-28,\n")
        with mock.patch.object(fomc, "FOMC_PATH", f.name):
            with self.assertRaises(ValueError):
                fomc.load_fomc()

    def test_non_increasing_refused(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv",
                                         delete=False) as f:
            f.write("date,source_url\n2026-03-18,https://x\n"
                    "2026-01-28,https://x\n")
        with mock.patch.object(fomc, "FOMC_PATH", f.name):
            with self.assertRaises(ValueError):
                fomc.load_fomc()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run to verify failure**

Run: `uv run python -m unittest discover -s tests -k fomc -v`
Expected: ERROR — `No module named 'options_researcher.fomc'`

- [ ] **Step 5: Implement the loader (mirrors earnings.py strictness)**

```python
"""options_researcher/fomc.py -- FOMC decision-date loader.

data/events/fomc_dates.csv holds the DECISION date (final day) of each
scheduled FOMC meeting, taken from the Federal Reserve's published calendar
(source_url on every row; Official-source). Like earnings.py, this loader
REFUSES malformed files instead of silently coping. Descriptive use only:
the scanner flags "FOMC inside this option's cycle" AMBER; the flag never
gates, scores, or ranks a candidate.
"""
from __future__ import annotations

import csv
import os
from datetime import date

FOMC_PATH = os.path.join("data", "events", "fomc_dates.csv")
_REQUIRED = ["date", "source_url"]


def load_fomc() -> list[date]:
    """Strictly-increasing FOMC decision dates. Raises FileNotFoundError
    (no file) or ValueError (malformed content)."""
    if not os.path.exists(FOMC_PATH):
        raise FileNotFoundError(
            f"{FOMC_PATH} missing -- compile it from the Fed's published "
            "calendar (with source URLs) first")
    with open(FOMC_PATH, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != _REQUIRED:
            raise ValueError(
                f"{FOMC_PATH}: header must be {_REQUIRED}, "
                f"got {reader.fieldnames}")
        out: list[date] = []
        for i, row in enumerate(reader, start=2):
            if not row["source_url"].strip():
                raise ValueError(f"{FOMC_PATH}:{i}: empty source_url")
            d = date.fromisoformat(row["date"])
            if out and d <= out[-1]:
                raise ValueError(
                    f"{FOMC_PATH}:{i}: dates not strictly increasing")
            out.append(d)
    return out
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run python -m unittest discover -s tests -k fomc -v`
Expected: 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add data/events/fomc_dates.csv options_researcher/fomc.py tests/test_fomc.py
git commit -m "feat(events): FOMC decision-date CSV (official calendar) + strict loader"
```

---

### Task 6: FOMC AMBER flag on seller cards

**Files:**
- Modify: `options_researcher/attractiveness.py` (`put_card_rows` ~line 61, `cc_card_rows` ~line 105, `pmcc_card_rows` ~line 154, `main()` cycle-flag block ~line 322)
- Modify: `options_researcher/attractiveness_dashboard.py` (`_gather_all`, same cycle-flag pattern)
- Modify: `tests/test_attractiveness.py`, `tests/test_attractiveness_dashboard.py` (update every card-builder call to pass the new kwarg)

- [ ] **Step 1: Write a failing test (add to tests/test_attractiveness.py, reusing its existing chain fixture — read the file's put-card test first and copy its fixture call)**

```python
    def test_fomc_flag_amber_when_meeting_in_cycle(self):
        # reuse the exact chain fixture + kwargs of the existing
        # put_card_rows test in this file, adding fomc_in_cycle=True
        rows = put_card_rows(..., earnings_in_cycle=False,
                             fomc_in_cycle=True)
        self.assertEqual(rows[0]["grades"]["fomc"], "AMBER")

    def test_fomc_flag_green_when_no_meeting(self):
        rows = put_card_rows(..., earnings_in_cycle=False,
                             fomc_in_cycle=False)
        self.assertEqual(rows[0]["grades"]["fomc"], "GREEN")
```

(The `...` above means: copy the positional/keyword arguments verbatim from
the existing passing put-card test in the same file — do not invent a new
fixture.)

- [ ] **Step 2: Run to verify failure**

Run: `uv run python -m unittest discover -s tests -k attractiveness -v`
Expected: the new tests ERROR with `unexpected keyword argument 'fomc_in_cycle'`

- [ ] **Step 3: Implement**

In each of `put_card_rows`, `cc_card_rows`, `pmcc_card_rows`: add the
required keyword parameter `fomc_in_cycle: bool` (right after
`earnings_in_cycle: bool`) and, in the grades dict directly under the
`"earnings"` entry, add:

```python
            "fomc": "AMBER" if fomc_in_cycle else "GREEN",
```

In `attractiveness.main()` (~line 322) extend the cycle-flag block:

```python
        from options_researcher.fomc import load_fomc
        earn_in_cycle = False
        fomc_in_cycle = False
        if exp is not None:
            earn_in_cycle = any(date.fromisoformat(day) < e <= exp
                                for e in load_earnings(symbol))
            fomc_in_cycle = any(date.fromisoformat(day) < m <= exp
                                for m in load_fomc())
```

and pass `fomc_in_cycle=fomc_in_cycle` at every seller-card call site
(lines ~331/347/366). Apply the identical change in
`attractiveness_dashboard._gather_all()` (it mirrors main()'s gathering; find
its `earn_in_cycle` computation and card-builder calls and extend the same
way). Update every existing test call of the three card builders to pass
`fomc_in_cycle=False`.

- [ ] **Step 4: Run the whole suite + both CLIs**

Run: `uv run python -m unittest discover -s tests`
Expected: `OK`

Run: `uv run python -m options_researcher.attractiveness | head -20`
Expected: seller badges now include `fomc:GREEN` or `fomc:AMBER` (July 28–29 FOMC falls inside the Aug-21 monthly cycle, so expect AMBER today)

Run: `uv run python -m options_researcher.attractiveness_dashboard`
Expected: writes the HTML, no traceback, fomc badge visible on seller cards

- [ ] **Step 5: Commit**

```bash
git add options_researcher/attractiveness.py options_researcher/attractiveness_dashboard.py tests/test_attractiveness.py tests/test_attractiveness_dashboard.py
git commit -m "feat(attractiveness): descriptive FOMC-in-cycle AMBER flag on seller cards"
```

---

### Task 7: Vega/IV prose on LEAPS + tactical-call cards (TDD)

**Files:**
- Modify: `options_researcher/attractiveness.py` (`leaps_card_rows` ~line 202, `long_call_card_rows` ~line 237)
- Modify: `tests/test_attractiveness.py` (LEAPS/long-call fixtures need `vega` and `iv` columns if they lack them)

**Vega scale (empirically verified 2026-07-07 against the real cache):** the
cached `vega` column is per-share per 1.00 change in IV — e.g. MSFT
2027-06-17 350C: price ~$80/share, vega 129.24, so a 1-vol-point (0.01) IV
move ≈ 129.24 × 0.01 × 100 shares = **the raw vega number in dollars per
contract per vol point**. Use it directly; do not rescale.

- [ ] **Step 1: Write failing tests (extend the existing LEAPS-card test in tests/test_attractiveness.py; its fixture must include `vega` and `iv` columns — add them if missing, e.g. `vega=129.24, iv=0.378`)**

```python
    def test_leaps_card_speaks_vega_and_iv(self):
        rows = leaps_card_rows(...)  # existing fixture + kwargs
        self.assertIn("implied vol drops 1 point", rows[0]["verdict"])
        self.assertIn("vega", rows[0])
        self.assertIn("iv", rows[0])

    def test_long_call_card_speaks_vega_and_iv(self):
        rows = long_call_card_rows(...)  # existing fixture + kwargs
        self.assertIn("implied vol drops 1 point", rows[0]["verdict"])
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run python -m unittest discover -s tests -k attractiveness -v`
Expected: new tests FAIL (missing prose/keys)

- [ ] **Step 3: Implement**

Add a shared helper (both card builders call it) and guard **before** any
`float()` — never extract then validate:

```python
def _vol_prose(r) -> tuple[float | None, float | None, str]:
    if not (pd.notna(r.get("vega")) and pd.notna(r.get("iv"))):
        return None, None, ""
    vega = float(r["vega"])
    contract_iv = float(r["iv"])
    sentence = (
        f"this contract's own implied vol is {contract_iv:.0%}; if "
        f"implied vol drops 1 point the option loses ~${vega:,.0f} "
        f"(vega), on top of time decay; "
    )
    return vega, contract_iv, sentence
```

In `leaps_card_rows` and `long_call_card_rows`, after the `extrinsic` line:

```python
    vega, contract_iv, vol_sentence = _vol_prose(r)
```

Insert `{vol_sentence}` in the verdict before "max loss", and add
`"vega": vega, "iv": contract_iv` to the returned dict. When `vega` or `iv`
is missing/NaN, the helper returns `(None, None, "")` — omit the sentence and
never print a number that isn't there (skip-and-log ethos).

- [ ] **Step 4: Run suite + CLI**

Run: `uv run python -m unittest discover -s tests`
Expected: `OK`

Run: `uv run python -m options_researcher.attractiveness | grep -A2 "BUY A LEAPS"`
Expected: LEAPS lines now include "implied vol ... vega" prose with plausible magnitudes (MSFT LEAPS ≈ $130/vol-point)

- [ ] **Step 5: Commit**

```bash
git add options_researcher/attractiveness.py tests/test_attractiveness.py
git commit -m "feat(attractiveness): plain-English vega/IV lines on LEAPS + tactical cards"
```

---

### Task 8: ThetaData cancel-day checklist + ledger pre-declaration

**Files:**
- Create: `docs/superpowers/2026-07-07-thetadata-cancel-checklist.md`
- Modify: `ledger/facts.log` (append only)

- [ ] **Step 1: Write the checklist doc**

```markdown
# ThetaData cancellation checklist (target: on/before 2026-07-25)

Plan pre-declared 2026-07-07 (ledger THETADATA_EXIT_PLAN). History is
complete and cached locally; nothing needs bulk-pulling. The only ongoing
need was daily forward-window top-ups, which end at cancellation.

## On cancel day (run locally, in order)

1. `uv run python data/recent_topup.py` — one run catches ALL missing days
   since the last top-up (it blind-caches by explicit date; holidays and
   unfinalized days become logged CACHE_GAPs, never substituted data).
2. Confirm the tool prints `audit overall: PASS` or `PASS WITH WARNINGS`
   (the known-benign warning is deep-ITM |delta|=1 rows with IV<=0 — see
   ledger DATA_AUDIT 2026-07-06). Any other verdict: STOP, investigate
   before canceling.
3. Append a `THETADATA_CANCEL` line to `ledger/facts.log` recording the
   final cached day per symbol (MSFT/AMZN/VST/CEG).
4. Cancel the subscription in the ThetaData account portal.

## After cancellation

- Trigger watching needs NO chain data: `uv run python -m
  options_researcher.entry_watch` runs on free underlying closes
  (AlphaVantage) + the frozen cache. The chain-staleness note in its output
  is expected and honest.
- The scanner CLIs keep working against the frozen cache (as-of dates shown
  on every card).
- When a trigger FIREs: re-subscribe for ONE month, run the top-up +
  data-audit, evaluate the entry with fresh audited chains, then decide
  whether ongoing chain data is worth paying for during the holding period
  (actual short-call cadence is monthly; broker quotes are free at
  execution time).
```

- [ ] **Step 2: Append the ledger pre-declaration**

```
<ISO-TIMESTAMP>	THETADATA_EXIT_PLAN 2026-07-07: subscription cancels on/before 2026-07-25. Pre-declared: NO bulk history pull needed (full-chain daily EODs already cached for all 4 names; parked enrichment ideas' raw data -- IV tenors, event windows -- is derivable offline from the existing cache). Cancel-day checklist = docs/superpowers/2026-07-07-thetadata-cancel-checklist.md (final top-up run + audit PASS required before cancel). Post-cancel: entry_watch runs on free closes; scanner runs on frozen cache with as-of labels; re-subscribe ONE month when a trigger fires to price entry with fresh audited data. This preserves the original spend-once intent; the forward-window daily feed was the only ongoing need and it pauses until an entry actually exists.
```

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/2026-07-07-thetadata-cancel-checklist.md ledger/facts.log
git commit -m "docs(data): ThetaData cancel-day checklist + ledger exit-plan pre-declaration"
```

---

### Task 9: README + final verification + merge

**Files:**
- Modify: `README.md` (Quickstart block + Scope status)
- Modify: `CLAUDE.md` (Commands block)

- [ ] **Step 1: Document the new command in both files' command lists**

Add to README Quickstart and CLAUDE.md Commands:

```bash
uv run python -m options_researcher.entry_watch              # WAIT/FIRE vs frozen entry triggers
```

Add one sentence to README "Scope status": entry triggers are pre-registered
(VST ≤ $140, AMZN ≤ $220, IV-rank ≤ 0.5, liquidity-gated; ledger
H5_ENTRY_TRIGGER_PREREG); ThetaData cancels ~07-25 per the checklist doc.

- [ ] **Step 2: Full verification**

Run: `uv run python -m unittest discover -s tests` → `OK`
Run: `uv run ruff check .` → `All checks passed!`
Run: `uv run pyright` → 0 errors
Run each CLI once (`attractiveness`, `attractiveness_dashboard`, `dashboard`, `entry_watch`) → no tracebacks

- [ ] **Step 3: Commit, push, merge when CI is green**

```bash
git add README.md CLAUDE.md
git commit -m "docs: entry-watch command + trigger/exit-plan scope status"
git push origin <branch>
gh pr checks   # wait for green, then merge per the repo's merge-judgment gates
```
