# H5 Sector Income Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved H5 design: frozen evaluator thresholds in config, real-share holdings + covered-call/PMCC coverage enforcement in the portfolio tracker, and the beginner-readable attractiveness evaluator.

**Architecture:** Thresholds live in a config `H5_*` block (owner-amendable only). `portfolio.py` gains a fail-loud holdings loader, two short-call structures, and coverage hard-checks (short calls must be backed by declared shares or a safety-gated LEAPS; naked calls impossible). `attractiveness.py` is pure scoring functions (golden-tested) + a prose-first card renderer reading latest chains/features/earnings, read-only.

**Tech Stack:** Python 3.12/uv, pandas, unittest (`discover -p` form; dotted form doesn't work here). `LUMIBOT_LOG_LEVEL=WARNING` for clean runs.

---

### Task 1: Config H5 thresholds

**Files:** Modify `config.py` (append); Test: append to `tests/test_h3r_config.py`? NO — create `tests/test_h5_config.py`.

- [ ] Step 1 failing test (`tests/test_h5_config.py`):

```python
import unittest

import config


class H5ConfigTests(unittest.TestCase):
    def test_thresholds_frozen(self):
        self.assertEqual(config.H5_PUT_YIELD_GREEN, 0.010)
        self.assertEqual(config.H5_PUT_YIELD_AMBER, 0.006)
        self.assertEqual(config.H5_CUSHION_GREEN, 0.8)
        self.assertEqual(config.H5_CUSHION_AMBER, 0.5)
        self.assertEqual(config.H5_CC_YIELD_GREEN, 0.008)
        self.assertEqual(config.H5_CC_YIELD_AMBER, 0.004)
        self.assertEqual(config.H5_CC_UPSIDE_GREEN, 0.03)
        self.assertEqual(config.H5_IVR_SELL_GREEN, 0.5)
        self.assertEqual(config.H5_IVR_BUY_GREEN, 0.3)
        self.assertEqual(config.H5_IVR_BUY_RED, 0.7)
        self.assertEqual(config.H5_INCOME_DELTA, 0.20)


if __name__ == "__main__":
    unittest.main()
```

- [ ] Step 2 run → AttributeError. Step 3 append to `config.py`:

```python
# ---------------------------------------------------------------------------
# H5 ATTRACTIVENESS THRESHOLDS (frozen; owner-amendment only). Anchors:
# put-yield GREEN 1.0%/mo = Study E measured VST 0.20d average; CC-yield
# GREEN 0.8%/mo = Study C AMZN 0.20d collected while beating buy-and-hold;
# cushion = %OTM / (rv21/sqrt(12)); IV-rank grades flip sign buyer vs seller
# (Study A: high rank = paid more AND real risk higher -- never "free").
# ---------------------------------------------------------------------------
H5_PUT_YIELD_GREEN = 0.010
H5_PUT_YIELD_AMBER = 0.006
H5_CUSHION_GREEN   = 0.8
H5_CUSHION_AMBER   = 0.5
H5_CC_YIELD_GREEN  = 0.008
H5_CC_YIELD_AMBER  = 0.004
H5_CC_UPSIDE_GREEN = 0.03
H5_IVR_SELL_GREEN  = 0.5
H5_IVR_BUY_GREEN   = 0.3
H5_IVR_BUY_RED     = 0.7
H5_INCOME_DELTA    = 0.20     # CSP + CC short-leg target delta (band +/-0.15)
```

- [ ] Step 4 suite green. Step 5 commit `feat(config): H5 frozen attractiveness thresholds`.

### Task 2: Holdings + coverage in portfolio.py

**Files:** Modify `options_researcher/portfolio.py`; Test: append `tests/test_portfolio.py`; Create `data/positions/holdings.csv` (header only: `symbol,shares,cost_basis,acquired`).

- [ ] Step 1 failing tests (append to `tests/test_portfolio.py`):

```python
from options_researcher.portfolio import check_coverage, load_holdings


class HoldingsTests(unittest.TestCase):
    def write(self, body):
        import tempfile
        t = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False)
        t.write("symbol,shares,cost_basis,acquired\n" + body)
        t.close()
        self.addCleanup(os.unlink, t.name)
        return t.name

    def test_loads_and_validates(self):
        h = load_holdings(self.write("VST,200,118.50,2025-11-03\n"))
        self.assertEqual(int(h.iloc[0]["shares"]), 200)

    def test_negative_shares_rejected(self):
        with self.assertRaises(ValueError):
            load_holdings(self.write("VST,-100,118.50,2025-11-03\n"))


class CoverageTests(unittest.TestCase):
    def positions(self, rows):
        return pd.DataFrame(rows, columns=["id", "structure", "symbol",
                                           "right", "strike", "expiration",
                                           "contracts", "entry_date",
                                           "entry_price", "bucket"])

    def holdings(self, rows):
        return pd.DataFrame(rows, columns=["symbol", "shares", "cost_basis",
                                           "acquired"])

    def test_covered_call_needs_100_shares_per_contract(self):
        pos = self.positions([["c1", "covered_call", "VST", "C", 180,
                               "2026-08-21", 2, "2026-07-04", 1.5, "income"]])
        issues = check_coverage(pos, self.holdings([["VST", 100, 118.5,
                                                     "2025-11-03"]]))
        self.assertTrue(any("uncovered" in i for i in issues))
        self.assertEqual(check_coverage(
            pos, self.holdings([["VST", 200, 118.5, "2025-11-03"]])), [])

    def test_pmcc_requires_safety_gated_leaps(self):
        pos = self.positions([
            ["l1", "leaps_call", "MSFT", "C", 340, "2027-06-17", 1,
             "2026-07-04", 79.54, "thesis"],
            ["p1", "pmcc_call", "MSFT", "C", 400, "2026-08-21", 1,
             "2026-07-04", 2.0, "income"],
        ])
        issues = check_coverage(pos, self.holdings([]))
        self.assertTrue(any("safety" in i for i in issues))   # 400 < 340+79.54
        pos.loc[1, "strike"] = 420.0
        self.assertEqual(check_coverage(pos, self.holdings([])), [])

    def test_cc_below_cost_basis_flagged(self):
        pos = self.positions([["c1", "covered_call", "VST", "C", 110,
                               "2026-08-21", 1, "2026-07-04", 1.5, "income"]])
        issues = check_coverage(pos, self.holdings([["VST", 100, 118.5,
                                                     "2025-11-03"]]))
        self.assertTrue(any("below cost basis" in i for i in issues))
```

- [ ] Step 2 run → ImportError. Step 3 implement in `portfolio.py`: extend
`_STRUCTURES` with `"covered_call": ("C", "income", "short")` and
`"pmcc_call": ("C", "income", "short")`; add `HOLDINGS_PATH`,
`load_holdings(path)` (schema/positivity validation mirroring
`load_positions`), and:

```python
def check_coverage(frame: pd.DataFrame, holdings: pd.DataFrame) -> list[str]:
    """Short calls must be backed: covered_call by declared shares (100 per
    contract, strike >= that symbol's cost basis), pmcc_call by a live
    leaps_call on the same symbol with K_short >= K_leaps + entry_price
    (assignment then cannot lock a loss). A naked short call is impossible
    by construction -- anything unbacked is an issue."""
    issues = []
    held = {r["symbol"]: r for _, r in holdings.iterrows()}
    for _, p in frame[frame["structure"] == "covered_call"].iterrows():
        lot = held.get(p["symbol"])
        need = 100 * int(p["contracts"])
        if lot is None or int(lot["shares"]) < need:
            issues.append(f"covered_call {p['id']} uncovered: need {need} "
                          f"shares of {p['symbol']} in holdings.csv")
        elif float(p["strike"]) < float(lot["cost_basis"]):
            issues.append(f"covered_call {p['id']} strike {p['strike']} "
                          f"below cost basis {lot['cost_basis']} -- H5 bans "
                          "locking in a sale at a loss")
    leaps = frame[frame["structure"] == "leaps_call"]
    for _, p in frame[frame["structure"] == "pmcc_call"].iterrows():
        ok = False
        for _, lp in leaps[leaps["symbol"] == p["symbol"]].iterrows():
            if float(p["strike"]) >= float(lp["strike"]) + float(lp["entry_price"]):
                ok = True
        if not ok:
            issues.append(f"pmcc_call {p['id']} fails the safety gate: "
                          "short strike must be >= LEAPS strike + premium "
                          "paid (else assignment can lock a loss)")
    return issues
```

Wire into `analyze()`: load holdings (empty frame if file has only header),
run `check_coverage`, print issues alongside bucket issues; RAISE
RuntimeError if any short call is uncovered (fail-loud per spec). Also in
`analyze()`: for csp rows with `dte <= 0`, print the assignment instruction
("EXPIRED: if close < strike, add 100 sh @ strike to holdings.csv and
remove this row; else just remove"). Create `data/positions/holdings.csv`
with header only.
- [ ] Step 4 suite green. Step 5 commit `feat(portfolio): holdings + short-call coverage (naked calls impossible)`.

### Task 3: Attractiveness evaluator

**Files:** Create `options_researcher/attractiveness.py`; Test `tests/test_attractiveness.py`.

- [ ] Step 1 failing tests:

```python
import unittest

import pandas as pd

import config
from options_researcher.attractiveness import grade, put_card_rows


def put_chain(strike, delta, bid, exp="2026-07-17"):
    return pd.DataFrame([{"expiration": exp, "strike": strike, "right": "P",
                          "bid": bid, "ask": bid + 0.10,
                          "open_interest": 500, "iv": 0.5, "delta": delta,
                          "gamma": 0.0, "theta": 0.0, "vega": 0.0}])


class GradeTests(unittest.TestCase):
    def test_grade_directions(self):
        self.assertEqual(grade(0.012, 0.010, 0.006), "GREEN")
        self.assertEqual(grade(0.007, 0.010, 0.006), "AMBER")
        self.assertEqual(grade(0.005, 0.010, 0.006), "RED")
        self.assertEqual(grade(0.2, 0.3, 0.7, higher_is_better=False), "GREEN")
        self.assertEqual(grade(0.8, 0.3, 0.7, higher_is_better=False), "RED")


class PutCardTests(unittest.TestCase):
    def test_golden_numbers(self):
        rows = put_card_rows("VST", put_chain(145.0, -0.20, 2.15),
                             "2026-06-30", close=160.0, rv21=0.50,
                             iv_rank=0.62, earnings_in_cycle=False)
        r = rows[0]
        h = config.SLIPPAGE_HAIRCUT
        credit = 2.15 * (1 - h) * 100 - config.COMMISSION_PER_CONTRACT
        self.assertAlmostEqual(r["credit"], credit, places=2)
        self.assertAlmostEqual(r["yield_mo"], credit / 14500.0, places=6)
        # cushion: 9.375% OTM / (50%/sqrt12 = 14.43%) = 0.6496 -> AMBER
        self.assertAlmostEqual(r["cushion"], 0.6496, places=3)
        self.assertEqual(r["grades"]["cushion"], "AMBER")
        self.assertEqual(r["grades"]["yield"], "GREEN")
        self.assertEqual(r["grades"]["iv_for_seller"], "GREEN")
        self.assertIn("promise", r["verdict"].lower())


if __name__ == "__main__":
    unittest.main()
```

- [ ] Step 2 run → ModuleNotFoundError. Step 3 implement
`attractiveness.py`: `grade(value, green, amber, higher_is_better=True)`;
`put_card_rows(symbol, chain, day, *, close, rv21, iv_rank,
earnings_in_cycle)` selecting up to 3 puts nearest `config.H5_INCOME_DELTA`
on the nearest monthly via `chains.nearest_monthly`/window filtering,
computing credit (bid×(1−haircut)×100 − commission), yield_mo =
credit/(100×strike), cushion = ((close−K)/close) / (rv21/√12), grades dict
(yield vs H5_PUT_YIELD_*, cushion vs H5_CUSHION_*, iv_for_seller GREEN iff
iv_rank ≥ H5_IVR_SELL_GREEN else AMBER, liquidity via
`passes_liquidity`, earnings AMBER flag), and a one-sentence beginner
`verdict` string that always names the promise ("you'd be promising to buy
100 sh at $K = $X; pays $C now = Y%/mo") plus the Study-A honesty line when
iv_for_seller is GREEN. Analogous `cc_card_rows(symbol, chain, day, *,
close, holdings_row, ...)` (yield vs H5_CC_YIELD_*, upside room vs
H5_CC_UPSIDE_GREEN, hard skip with message when 0.20Δ strike < cost_basis)
and `leaps_card_rows(symbol, chain, day, *, close, iv_rank, bucket_room)`
(cost vs room, breakeven = K + ask×(1+h), % move needed, theta/day =
extrinsic/DTE, iv_for_buyer graded INVERTED via H5_IVR_BUY_*). `main()`
iterates config.UNIVERSE, loads latest chain/features/earnings/holdings,
prints cards prose-first; pure read-only.
- [ ] Step 4 tests + suite green. Step 5 commit `feat(researcher): attractiveness evaluator (frozen thresholds, beginner prose)`.

### Task 4: Register H5 + first live run

- [ ] `uv run python -m research.cli trial-log --reason "H5 registered: Sector Income Core ... (doc: specs/2026-07-04-h5-sector-income-core-design.md); H4 SUPERSEDED-AT-ZERO-CYCLES, book carries over, forward-window clock restarts"`; `append_fact` H5_REGISTERED line; README status row + evaluator quickstart line; run `uv run python -m options_researcher.attractiveness` and eyeball cards; full suite; commit `feat(h5): registered -- evaluator live, window clock restarted`.

## Self-review notes

Spec §2 engines → Tasks 2/4; §3 evaluator → Task 3 (all three card types,
frozen thresholds Task 1); §4 tracker additions → Task 2 (coverage,
holdings, expired-CSP instruction); §5 registration → Task 4; §6 testing →
golden fixtures in every task; naked-call ban = structural (no naked
structure exists + coverage check). Type consistency: `check_coverage(
positions_frame, holdings_frame) -> list[str]` used identically in tests
and analyze(); card row dicts carry `grades: dict[str,str]` + `verdict: str`.
