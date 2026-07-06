# Attractiveness Scenario Tables Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a static, self-contained HTML view over the existing attractiveness candidates that shows, per candidate, a plain-language "if the stock is at price X, your gain or loss is Y" table computed at expiration (no options-pricing model).

**Architecture:** A new module `options_researcher/attractiveness_dashboard.py` mirroring `dashboard.py`'s `assemble()` / `render()` / `main()` split. A pure scenario-math layer computes a price ladder and per-structure payoff rows from candidate dicts produced (unmodified) by `attractiveness.py`'s card-builder functions. `render()` reuses `dashboard.py`'s dark CSS. `main()` writes `.tmp/dashboard/attractiveness.html`.

**Tech Stack:** Python 3.12, pandas, `unittest` (not pytest), `uv` runner. No new dependencies. No network, no pricing model.

**Reference spec:** `docs/superpowers/specs/2026-07-06-attractiveness-scenario-tables-design.md`

---

## File Structure

- Create: `options_researcher/attractiveness_dashboard.py` — the whole feature (scenario math, assemble, render, main). One file, matching `dashboard.py`'s single-file shape.
- Create: `tests/test_attractiveness_dashboard.py` — unit tests for every pure function.
- Modify: `README.md` and `CLAUDE.md` — add the new CLI command to the commands list.

`attractiveness.py` is **not modified** — its card-builder functions are imported and called as-is.

## Data shapes (types shared across tasks)

A **scenario row** (produced by Task 1):
```python
{"price": float,   # rounded to cents, > 0
 "tag": str,       # "" | "today" | "strike" | "breakeven"
 "pnl": float,     # dollar gain/loss at expiration (always a real number)
 "note": str}      # "" except PMCC credit-only rows
```

An **assembled card** (produced by Task 2, consumed by Task 3) is the dict from
`attractiveness.py` with these keys added:
```python
{... existing card keys ...,
 "headline": str,           # e.g. "Sell the MSFT $350 put — collect $250 now — result by 2026-07-17 (17 days out)"
 "scenarios": list[row],    # empty list for skipped cards
 "countdown": str}          # LEAPS only; "" otherwise
```
A **skipped card** keeps its `{"strike", "skipped"}` shape and gets `"scenarios": []`, `"headline": ""`, `"countdown": ""`.

---

### Task 1: Scenario math (pure functions)

**Files:**
- Create: `options_researcher/attractiveness_dashboard.py`
- Test: `tests/test_attractiveness_dashboard.py`

- [ ] **Step 1: Write the failing tests**

```python
"""tests/test_attractiveness_dashboard.py"""
import math
import unittest

from options_researcher import attractiveness_dashboard as ad


class PriceLadderTests(unittest.TestCase):
    def test_ladder_uses_moves_strike_breakeven_and_tags(self):
        rows = ad._price_ladder(close=100.0, rv21=math.sqrt(12) * 0.10,
                                strike=95.0, breakeven=97.0)
        # monthly_move = 0.10 -> points at 80,90,100,110,120 plus 95,97
        prices = [r["price"] for r in rows]
        self.assertEqual(prices, sorted(prices))          # ascending
        self.assertEqual(len(prices), len(set(prices)))   # deduped
        self.assertTrue(all(p > 0 for p in prices))
        tag_by_price = {r["price"]: r["tag"] for r in rows}
        self.assertEqual(tag_by_price[100.0], "today")
        self.assertEqual(tag_by_price[95.0], "strike")
        self.assertEqual(tag_by_price[97.0], "breakeven")

    def test_invalid_vol_falls_back_to_close_strike_breakeven(self):
        rows = ad._price_ladder(close=100.0, rv21=float("nan"),
                                strike=95.0, breakeven=97.0)
        self.assertEqual([r["price"] for r in rows], [95.0, 97.0, 100.0])

    def test_nonpositive_prices_dropped(self):
        # huge vol would push the -2 sigma point below zero
        rows = ad._price_ladder(close=10.0, rv21=math.sqrt(12) * 0.60,
                                strike=10.0, breakeven=None)
        self.assertTrue(all(r["price"] > 0 for r in rows))


class PayoffTests(unittest.TestCase):
    def test_put_pnl(self):
        self.assertAlmostEqual(ad._put_pnl(145.0, 145.0, 212.20), 212.20, 2)
        self.assertAlmostEqual(ad._put_pnl(130.0, 145.0, 212.20), -1287.80, 2)

    def test_cc_pnl_vs_today(self):
        # called away at strike above today: credit + 100*(strike-close)
        self.assertAlmostEqual(ad._cc_pnl(180.0, 175.0, 150.0, 160.0),
                               150.0 + 1500.0, 2)
        # below strike: marked at scenario price
        self.assertAlmostEqual(ad._cc_pnl(150.0, 175.0, 150.0, 160.0),
                               150.0 - 1000.0, 2)

    def test_pmcc_split(self):
        above = ad._pmcc_pnl(430.0, 420.0, 340.0, 7954.0, 100.0)
        self.assertAlmostEqual(above[0], (420.0 - 340.0) * 100 - 7954.0 + 100.0, 2)
        self.assertEqual(above[1], "")
        below = ad._pmcc_pnl(400.0, 420.0, 340.0, 7954.0, 100.0)
        self.assertAlmostEqual(below[0], 100.0, 2)
        self.assertIn("LEAPS value not counted", below[1])

    def test_leaps_pnl(self):
        self.assertAlmostEqual(ad._leaps_pnl(457.32, 340.0, 7954.0),
                               (457.32 - 340.0) * 100 - 7954.0, 2)
        self.assertAlmostEqual(ad._leaps_pnl(300.0, 340.0, 7954.0), -7954.0, 2)


class ScenarioRowsTests(unittest.TestCase):
    def test_put_scenarios_carry_pnl_and_tags(self):
        card = {"strike": 145.0, "credit": 212.20}
        rows = ad.scenario_rows(card, "put", close=160.0,
                                rv21=math.sqrt(12) * 0.10)
        self.assertTrue(rows)
        self.assertTrue(any(r["tag"] == "strike" for r in rows))
        strike_row = next(r for r in rows if r["tag"] == "strike")
        self.assertAlmostEqual(strike_row["pnl"], 212.20, 2)

    def test_pmcc_scenarios_note_below_strike(self):
        card = {"strike": 420.0, "credit": 100.0,
                "leaps_strike": 340.0, "leaps_cost": 7954.0}
        rows = ad.scenario_rows(card, "pmcc", close=373.02,
                                rv21=math.sqrt(12) * 0.11)
        below = [r for r in rows if r["price"] < 420.0]
        self.assertTrue(below and all(r["note"] for r in below))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest tests.test_attractiveness_dashboard -v`
Expected: FAIL with `AttributeError: module ... has no attribute '_price_ladder'`

- [ ] **Step 3: Write the module skeleton + scenario math**

```python
"""options_researcher/attractiveness_dashboard.py -- interactive scenario
view over attractiveness candidates.

assemble() gathers the SAME candidates attractiveness.py prints (via its
card-builder functions, unmodified) and attaches an at-expiration payoff
table per candidate. render() turns that into one self-contained HTML
string (reusing dashboard.py's dark CSS; no network, no JS framework, no
options-pricing model). main() writes .tmp/dashboard/attractiveness.html.

Every payoff number is computed AT EXPIRATION from intrinsic value only --
there is deliberately no Black-Scholes / time-value model anywhere here.
"""
from __future__ import annotations

import html as _html
import math
import os

OUTPUT_PATH = os.path.join(".tmp", "dashboard", "attractiveness.html")

_PMCC_NOTE = "just the premium; LEAPS value not counted"


def _round_cents(x: float) -> float:
    return round(float(x), 2)


def _price_ladder(*, close: float, rv21: float, strike: float,
                  breakeven: float | None) -> list[dict]:
    """Ascending, deduped, positive-only price rows with anchor tags.

    Uses +/-1 and +/-2 monthly moves around close when rv21 gives a finite
    positive monthly move; otherwise falls back to close/strike/breakeven
    only (never invents points from a bad vol number)."""
    monthly = rv21 / math.sqrt(12.0) if rv21 and rv21 > 0 else float("nan")
    tagged: dict[float, str] = {}

    def put(price: float, tag: str) -> None:
        p = _round_cents(price)
        if p <= 0:
            return
        # anchor tags (today/strike/breakeven) win over untagged move points
        if tag or p not in tagged:
            tagged[p] = tag if tag else tagged.get(p, "")

    if monthly == monthly and monthly > 0:  # finite, positive
        for k in (-2, -1, 1, 2):
            put(close * (1 + k * monthly), "")
    put(close, "today")
    put(strike, "strike")
    if breakeven is not None:
        put(breakeven, "breakeven")
    return [{"price": p, "tag": tagged[p]} for p in sorted(tagged)]


def _put_pnl(price: float, strike: float, credit: float) -> float:
    return credit - max(0.0, strike - price) * 100.0


def _cc_pnl(price: float, strike: float, credit: float, close: float) -> float:
    return credit + 100.0 * (min(price, strike) - close)


def _pmcc_pnl(price: float, short_strike: float, leaps_strike: float,
              leaps_cost: float, credit: float) -> tuple[float, str]:
    if price >= short_strike:
        return ((short_strike - leaps_strike) * 100.0 - leaps_cost + credit, "")
    return (credit, _PMCC_NOTE)


def _leaps_pnl(price: float, strike: float, cost: float) -> float:
    return max(0.0, price - strike) * 100.0 - cost


def scenario_rows(card: dict, structure: str, *, close: float,
                  rv21: float) -> list[dict]:
    """At-expiration payoff rows for one candidate. `structure` is one of
    'put', 'cc', 'pmcc', 'leaps'."""
    strike = float(card["strike"])
    if structure == "put":
        credit = float(card["credit"])
        breakeven = strike - credit / 100.0
        ladder = _price_ladder(close=close, rv21=rv21, strike=strike,
                               breakeven=breakeven)
        return [{**row, "pnl": _round_cents(_put_pnl(row["price"], strike,
                                                     credit)), "note": ""}
                for row in ladder]
    if structure == "cc":
        credit = float(card["credit"])
        ladder = _price_ladder(close=close, rv21=rv21, strike=strike,
                               breakeven=None)
        return [{**row, "pnl": _round_cents(_cc_pnl(row["price"], strike,
                                                    credit, close)), "note": ""}
                for row in ladder]
    if structure == "pmcc":
        credit = float(card["credit"])
        lk, lc = float(card["leaps_strike"]), float(card["leaps_cost"])
        ladder = _price_ladder(close=close, rv21=rv21, strike=strike,
                               breakeven=None)
        out = []
        for row in ladder:
            pnl, note = _pmcc_pnl(row["price"], strike, lk, lc, credit)
            out.append({**row, "pnl": _round_cents(pnl), "note": note})
        return out
    if structure == "leaps":
        cost = float(card["cost"])
        breakeven = float(card["breakeven"])
        ladder = _price_ladder(close=close, rv21=rv21, strike=strike,
                               breakeven=breakeven)
        return [{**row, "pnl": _round_cents(_leaps_pnl(row["price"], strike,
                                                      cost)), "note": ""}
                for row in ladder]
    raise ValueError(f"unknown structure {structure!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_attractiveness_dashboard -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add options_researcher/attractiveness_dashboard.py tests/test_attractiveness_dashboard.py
git commit -m "feat(attractiveness): scenario math for at-expiration payoff tables"
```

---

### Task 2: assemble() — gather candidates, enrich PMCC, attach scenarios

**Files:**
- Modify: `options_researcher/attractiveness_dashboard.py`
- Test: `tests/test_attractiveness_dashboard.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_attractiveness_dashboard.py`:

```python
class AssembleTests(unittest.TestCase):
    def _fake_symbol(self):
        # One symbol section shaped exactly like _gather_symbol() returns:
        # raw card dicts from attractiveness.py plus context scalars.
        return {
            "symbol": "MSFT", "as_of": "2026-06-30", "close": 373.02,
            "iv_rank": 0.88,
            "groups": [
                {"kind": "put", "title": "SELL A PUT?",
                 "cards": [{"strike": 350.0, "expiry": "2026-07-17",
                            "dte": 17, "credit": 250.0, "yield_mo": 0.0071,
                            "grades": {"yield": "AMBER"},
                            "verdict": "you'd be promising..."}],
                 "empty": None},
                {"kind": "pmcc", "title": "SELL A CALL AGAINST YOUR LEAPS?",
                 "leaps_strike": 340.0, "leaps_premium": 79.54,
                 "cards": [{"strike": 420.0, "expiry": "2026-07-17",
                            "dte": 17, "credit": 100.0, "yield_mo": 0.0126,
                            "grades": {"safety": "GREEN"},
                            "verdict": "sells a $420 call..."}],
                 "empty": None},
            ],
        }

    def test_assemble_attaches_scenarios_and_enriches_pmcc(self):
        d = ad.assemble(symbol_sections=[self._fake_symbol()],
                        rv21_by_symbol={"MSFT": math.sqrt(12) * 0.11})
        put_card = d["symbols"][0]["groups"][0]["cards"][0]
        self.assertTrue(put_card["scenarios"])
        self.assertIn("Sell", put_card["headline"])
        pmcc_card = d["symbols"][0]["groups"][1]["cards"][0]
        # enrichment: leaps context copied onto the card for the math layer
        self.assertEqual(pmcc_card["leaps_strike"], 340.0)
        self.assertAlmostEqual(pmcc_card["leaps_cost"], 7954.0, 2)
        self.assertTrue(any(r["note"] for r in pmcc_card["scenarios"]))

    def test_skipped_card_gets_no_scenarios(self):
        section = {"symbol": "VST", "as_of": "2026-06-30", "close": 112.0,
                   "iv_rank": 0.3,
                   "groups": [{"kind": "cc", "title": "SELL A COVERED CALL?",
                               "cards": [{"strike": 110.0,
                                          "skipped": "strike below cost basis"}],
                               "empty": None}]}
        d = ad.assemble(symbol_sections=[section],
                        rv21_by_symbol={"VST": 0.5})
        card = d["symbols"][0]["groups"][0]["cards"][0]
        self.assertEqual(card["scenarios"], [])
        self.assertEqual(card["headline"], "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_attractiveness_dashboard.AssembleTests -v`
Expected: FAIL with `AttributeError: ... has no attribute 'assemble'`

- [ ] **Step 3: Implement assemble() + the default real-data gatherer**

Add to `options_researcher/attractiveness_dashboard.py`:

```python
def _headline(symbol: str, kind: str, card: dict) -> str:
    verbs = {"put": "Sell the {sym} ${k:.0f} put",
             "cc": "Sell the {sym} ${k:.0f} covered call",
             "pmcc": "Sell the {sym} ${k:.0f} call vs your LEAPS",
             "leaps": "Buy the {sym} ${k:.0f} LEAPS"}
    k = float(card["strike"])
    lead = verbs[kind].format(sym=symbol, k=k)
    if kind == "leaps":
        money = f"costs ${float(card['cost']):,.0f}"
    else:
        money = f"collect ${float(card['credit']):,.0f} now"
    return (f"{lead} — {money} — result by {card['expiry']} "
            f"({card['dte']} days out)")


def _countdown(card: dict) -> str:
    import config
    dte = int(card["dte"])
    roll = config.H4_THESIS_ROLL_DTE
    return (f"{dte} days until expiration · roll reminder kicks in with "
            f"{roll} days left")


def assemble(*, symbol_sections: list[dict] | None = None,
             rv21_by_symbol: dict[str, float] | None = None) -> dict:
    """Attach scenario tables + headlines to gathered candidate sections.

    Both arguments default to the real project state (see _gather_all);
    inject them to unit-test without touching disk or the network."""
    if symbol_sections is None:
        symbol_sections, rv21_by_symbol = _gather_all()
    rv21_by_symbol = rv21_by_symbol or {}

    out_symbols = []
    for sec in symbol_sections:
        sym = sec["symbol"]
        rv21 = float(rv21_by_symbol.get(sym, float("nan")))
        out_groups = []
        for grp in sec["groups"]:
            kind = grp["kind"]
            cards = []
            for card in grp["cards"]:
                if "skipped" in card:
                    cards.append({**card, "scenarios": [], "headline": "",
                                  "countdown": ""})
                    continue
                enriched = dict(card)
                if kind == "pmcc":
                    enriched["leaps_strike"] = float(grp["leaps_strike"])
                    enriched["leaps_cost"] = float(grp["leaps_premium"]) * 100.0
                enriched["scenarios"] = scenario_rows(
                    enriched, kind, close=float(sec["close"]), rv21=rv21)
                enriched["headline"] = _headline(sym, kind, enriched)
                enriched["countdown"] = (_countdown(enriched)
                                         if kind == "leaps" else "")
                cards.append(enriched)
            out_groups.append({"kind": kind, "title": grp["title"],
                               "cards": cards, "empty": grp.get("empty")})
        out_symbols.append({"symbol": sym, "close": float(sec["close"]),
                            "iv_rank": float(sec["iv_rank"]),
                            "as_of": sec["as_of"], "groups": out_groups})
    return {"symbols": out_symbols}
```

- [ ] **Step 4: Implement `_gather_all()` (the real loader)**

This reuses the exact loading `attractiveness.main()` already does, but returns
structured section dicts instead of printing. Add to the module:

```python
def _gather_all() -> tuple[list[dict], dict[str, float]]:
    """Load real per-symbol candidate sections + rv21, mirroring
    attractiveness.main()'s data gathering (no printing)."""
    import glob
    from datetime import date

    import pandas as pd

    import config
    from data.underlying_closes import load_closes
    from options_researcher.attractiveness import (cc_card_rows,
                                                    leaps_card_rows,
                                                    pmcc_card_rows,
                                                    put_card_rows)
    from options_researcher.chains import nearest_monthly
    from options_researcher.earnings import load_earnings
    from options_researcher.features import load_features
    from options_researcher.portfolio import (HOLDINGS_PATH, load_holdings,
                                               load_positions)

    holdings = (load_holdings() if os.path.exists(HOLDINGS_PATH)
                else pd.DataFrame(columns=["symbol", "shares", "cost_basis"]))
    positions = load_positions()
    thesis_used = 0.0
    held_leaps: dict[str, tuple[float, float]] = {}
    if not positions.empty:
        t = positions[positions["bucket"] == "thesis"]
        thesis_used = float((t["entry_price"] * 100 * t["contracts"]).sum())
        for _, lp in positions[positions["structure"] == "leaps_call"].iterrows():
            held_leaps.setdefault(lp["symbol"],
                                  (float(lp["strike"]), float(lp["entry_price"])))
    bucket_room = config.H4_THESIS_MAX_PREMIUM_TOTAL - thesis_used

    sections, rv21_by_symbol = [], {}
    for symbol in config.UNIVERSE:
        files = sorted(glob.glob(os.path.join(".cache", "chains",
                                              f"{symbol}_*.parquet")))
        if not files:
            continue
        day = os.path.basename(files[-1]).split("_")[1].replace(".parquet", "")
        chain = pd.read_parquet(files[-1])
        row = load_features(symbol).iloc[-1]
        close = float(load_closes(symbol, "2018-01-01", day,
                                  allow_oos=True).iloc[-1])
        rv21 = float(row["rv21"])
        rv21_by_symbol[symbol] = rv21
        iv_rank = float(row["iv_rank"]) if pd.notna(row["iv_rank"]) else 0.0
        exp = nearest_monthly(chain, date.fromisoformat(day))
        earn_in_cycle = bool(exp is not None and any(
            date.fromisoformat(day) < e <= exp for e in load_earnings(symbol)))

        groups = [{"kind": "put", "title": "SELL A PUT? (promise to buy lower)",
                   "cards": put_card_rows(symbol, chain, day, close=close,
                                          rv21=rv21, iv_rank=iv_rank,
                                          earnings_in_cycle=earn_in_cycle),
                   "empty": "no candidates near the target delta this cycle"
                   if not put_card_rows(symbol, chain, day, close=close,
                                        rv21=rv21, iv_rank=iv_rank,
                                        earnings_in_cycle=earn_in_cycle)
                   else None}]

        lot = holdings[holdings["symbol"] == symbol] if len(holdings) else []
        if len(lot) and int(lot.iloc[0]["shares"]) >= 100:
            groups.append({"kind": "cc",
                           "title": "SELL A COVERED CALL? (rent out your shares)",
                           "cards": cc_card_rows(
                               symbol, chain, day, close=close,
                               cost_basis=float(lot.iloc[0]["cost_basis"]),
                               iv_rank=iv_rank,
                               earnings_in_cycle=earn_in_cycle),
                           "empty": None})
        if symbol in held_leaps:
            lk, lp = held_leaps[symbol]
            groups.append({"kind": "pmcc",
                           "title": "SELL A CALL AGAINST YOUR LEAPS? (PMCC)",
                           "leaps_strike": lk, "leaps_premium": lp,
                           "cards": pmcc_card_rows(
                               symbol, chain, day, leaps_strike=lk,
                               leaps_premium=lp, close=close, iv_rank=iv_rank,
                               earnings_in_cycle=earn_in_cycle),
                           "empty": None})
        if symbol in config.H4_THESIS_NAMES:
            groups.append({"kind": "leaps",
                           "title": f"BUY A LEAPS? (bucket room ${bucket_room:,.0f})",
                           "cards": leaps_card_rows(symbol, chain, day,
                                                    close=close, iv_rank=iv_rank,
                                                    bucket_room=bucket_room),
                           "empty": None})

        sections.append({"symbol": symbol, "as_of": day, "close": close,
                         "iv_rank": iv_rank, "groups": groups})
    return sections, rv21_by_symbol
```

Note: the `put_card_rows` double-call above is wasteful; replace with a local
variable in the actual code:

```python
        put_cards = put_card_rows(symbol, chain, day, close=close, rv21=rv21,
                                  iv_rank=iv_rank, earnings_in_cycle=earn_in_cycle)
        groups = [{"kind": "put", "title": "SELL A PUT? (promise to buy lower)",
                   "cards": put_cards,
                   "empty": None if put_cards
                   else "no candidates near the target delta this cycle"}]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_attractiveness_dashboard.AssembleTests -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add options_researcher/attractiveness_dashboard.py tests/test_attractiveness_dashboard.py
git commit -m "feat(attractiveness): assemble candidates with scenarios + PMCC enrichment"
```

---

### Task 3: render() — self-contained HTML

**Files:**
- Modify: `options_researcher/attractiveness_dashboard.py`
- Test: `tests/test_attractiveness_dashboard.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_attractiveness_dashboard.py`:

```python
class RenderTests(unittest.TestCase):
    def _assembled(self):
        return ad.assemble(
            symbol_sections=[{
                "symbol": "MSFT", "as_of": "2026-06-30", "close": 373.02,
                "iv_rank": 0.88,
                "groups": [
                    {"kind": "put", "title": "SELL A PUT?",
                     "cards": [{"strike": 350.0, "expiry": "2026-07-17",
                                "dte": 17, "credit": 250.0,
                                "grades": {"yield": "AMBER"},
                                "verdict": "promise to buy lower"}],
                     "empty": None},
                    {"kind": "cc", "title": "SELL A COVERED CALL?",
                     "cards": [], "empty": "no candidates this cycle"},
                ]}],
            rv21_by_symbol={"MSFT": 1.1})

    def test_render_has_label_and_no_external_assets(self):
        html = ad.render(self._assembled())
        self.assertIn("Your gain or loss", html)
        self.assertNotIn("You end up with", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://cdn", html)
        self.assertIn("<style>", html)

    def test_render_shows_empty_state_line(self):
        html = ad.render(self._assembled())
        self.assertIn("no candidates this cycle", html)

    def test_render_escapes_dynamic_text(self):
        assembled = self._assembled()
        assembled["symbols"][0]["groups"][0]["cards"][0]["verdict"] = "<x>&"
        html = ad.render(assembled)
        self.assertNotIn("<x>&", html)
        self.assertIn("&lt;x&gt;&amp;", html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_attractiveness_dashboard.RenderTests -v`
Expected: FAIL with `AttributeError: ... has no attribute 'render'`

- [ ] **Step 3: Implement render() + helpers**

Add to `options_researcher/attractiveness_dashboard.py`. Reuse the CSS block
from `dashboard.py` (copy the `<style>...</style>` contents verbatim so the two
pages match; the panel/table classes are already defined there).

```python
def _esc(v) -> str:
    return _html.escape(str(v))


def _pnl_cell(row: dict) -> str:
    pnl = row["pnl"]
    color = "#2fd27d" if pnl >= 0 else "#ff5470"
    sign = "+" if pnl >= 0 else "-"
    body = f'<span style="color:{color}">{sign}${abs(pnl):,.0f}</span>'
    if row["note"]:
        body += f' <span class="label">({_esc(row["note"])})</span>'
    return body


def _scenario_table(rows: list[dict]) -> str:
    if not rows:
        return ""
    trs = []
    for r in rows:
        tag = _esc(r["tag"]) if r["tag"] else ""
        trs.append(f"<tr><td>${r['price']:,.2f}</td>"
                   f'<td class="label">{tag}</td>'
                   f"<td>{_pnl_cell(r)}</td></tr>")
    return ("<table><thead><tr><th>Price</th><th></th>"
            "<th>Your gain or loss</th></tr></thead><tbody>"
            + "".join(trs) + "</tbody></table>")


def _card_html(card: dict) -> str:
    if "skipped" in card:
        return f'<div class="panel"><div class="label">{_esc(card["skipped"])}</div></div>'
    parts = [f'<div class="panel">',
             f'<div class="party-name">{_esc(card["headline"])}</div>',
             _scenario_table(card["scenarios"]),
             f'<div class="header-sub">{_esc(card.get("verdict", ""))}</div>']
    if card.get("countdown"):
        parts.append(f'<div class="label">{_esc(card["countdown"])}</div>')
    parts.append("</div>")
    return "".join(parts)


def _group_html(grp: dict) -> str:
    head = f'<h3>{_esc(grp["title"])}</h3>'
    if not grp["cards"]:
        body = f'<div class="empty">{_esc(grp.get("empty") or "none this cycle")}</div>'
    else:
        body = "".join(_card_html(c) for c in grp["cards"])
    return head + body


def render(data: dict) -> str:
    _STYLE = "..."  # paste the exact <style> body from dashboard.py.render()
    symbols_html = ""
    for sec in data["symbols"]:
        groups = "".join(_group_html(g) for g in sec["groups"])
        symbols_html += (
            f'<div class="panel"><h2>{_esc(sec["symbol"])} '
            f'&mdash; close ${sec["close"]:,.2f} &mdash; '
            f'IV-rank {sec["iv_rank"]:.2f}</h2>{groups}</div>')
    return (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>WHICH OPTIONS LOOK ATTRACTIVE?</title><style>{_STYLE}</style>"
            f"</head><body><div class=\"panel\"><h1>WHICH OPTIONS LOOK "
            f"ATTRACTIVE TODAY?</h1><div class=\"header-sub\">at-expiration "
            f"payoff &mdash; not a prediction</div></div>{symbols_html}"
            f"</body></html>")
```

When implementing, replace `_STYLE = "..."` with the literal CSS string copied
from `dashboard.py`'s `render()` (everything between `<style>` and `</style>`).
Do not link an external stylesheet — the page must stay self-contained.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_attractiveness_dashboard.RenderTests -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add options_researcher/attractiveness_dashboard.py tests/test_attractiveness_dashboard.py
git commit -m "feat(attractiveness): render self-contained scenario-table HTML"
```

---

### Task 4: main() CLI

**Files:**
- Modify: `options_researcher/attractiveness_dashboard.py`
- Test: `tests/test_attractiveness_dashboard.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_attractiveness_dashboard.py`:

```python
class MainTests(unittest.TestCase):
    def test_main_writes_file_and_prints_path(self):
        import io
        import os
        import tempfile
        from contextlib import redirect_stdout
        from unittest import mock

        section = {"symbol": "MSFT", "as_of": "2026-06-30", "close": 373.02,
                   "iv_rank": 0.88,
                   "groups": [{"kind": "put", "title": "SELL A PUT?",
                               "cards": [], "empty": "none this cycle"}]}
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "dashboard", "attractiveness.html")
            with mock.patch.object(ad, "OUTPUT_PATH", out):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    path = ad.main(symbol_sections=[section],
                                   rv21_by_symbol={"MSFT": 1.1})
                self.assertTrue(os.path.exists(out))
                self.assertIn("attractiveness.html", buf.getvalue())
                self.assertEqual(path, os.path.abspath(out))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_attractiveness_dashboard.MainTests -v`
Expected: FAIL with `AttributeError: ... has no attribute 'main'`

- [ ] **Step 3: Implement main()**

Add to `options_researcher/attractiveness_dashboard.py`:

```python
def main(**assemble_kwargs) -> str:
    """Assemble real (or injected) candidates, render, write to OUTPUT_PATH.
    Read-only over project data; the only write is the HTML file."""
    data = assemble(**assemble_kwargs)
    out_html = render(data)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(out_html)
    abs_path = os.path.abspath(OUTPUT_PATH)
    print(f"wrote {abs_path}")
    print("open it in your browser to see the scenario tables")
    return abs_path


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_attractiveness_dashboard.MainTests -v`
Expected: PASS (1 test)

- [ ] **Step 5: Smoke-test against real cache and open it**

Run: `LUMIBOT_LOG_LEVEL=WARNING uv run python -m options_researcher.attractiveness_dashboard`
Expected: prints `wrote .../.tmp/dashboard/attractiveness.html`. Then
`open .tmp/dashboard/attractiveness.html` and confirm the cards render with
tables. (This step is manual verification, not a test.)

- [ ] **Step 6: Commit**

```bash
git add options_researcher/attractiveness_dashboard.py tests/test_attractiveness_dashboard.py
git commit -m "feat(attractiveness): main() CLI writes .tmp/dashboard/attractiveness.html"
```

---

### Task 5: Wire the command into docs; full green gate

**Files:**
- Modify: `README.md`, `CLAUDE.md`

- [ ] **Step 1: Add the command to `CLAUDE.md`**

In the "Commands (verified ...)" block, after the existing dashboard line, add:

```
uv run python -m options_researcher.attractiveness_dashboard  # writes .tmp/dashboard/attractiveness.html
```

- [ ] **Step 2: Add the command to `README.md`**

Find where `options_researcher.dashboard` is documented in `README.md` and add a
sibling bullet for `options_researcher.attractiveness_dashboard` describing it as
the interactive at-expiration scenario view over attractiveness candidates.

- [ ] **Step 3: Run the full gate**

Run: `uv run ruff check . && uv run python -m unittest discover -s tests`
Expected: ruff clean; full suite passes (previous count + the new tests).

Run: `uv run pyright`
Expected: no new errors in `options_researcher/attractiveness_dashboard.py`.

- [ ] **Step 4: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: document attractiveness_dashboard CLI command"
```

---

## Self-Review notes (for the implementer)

- The scenario math never imports a pricing model; if you find yourself
  reaching for Black-Scholes or `norm.cdf`, stop — that is explicitly out of
  scope (see spec Non-goals).
- `attractiveness.py` must remain byte-for-byte unchanged. If a test seems to
  need a change there, the change belongs in `attractiveness_dashboard.py`
  instead.
- Keep the CSS identical to `dashboard.py` so the two pages stay visually
  consistent; do not introduce a second theme.
