# Attractiveness Expiration Ladder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-expiration attractiveness scanner with a 5-bucket DTE ladder (14/30/60/90/120), each bucket showing one candidate, ranked by one transparent per-structure number.

**Architecture:** A new `chains.ladder_expirations` picks the nearest available expiration inside each bucket's window. The four short/mid card builders gain an optional `exp` param (defaulting to today's `nearest_monthly`, so existing callers/tests are unchanged) and each card now carries its ranking number. A thin orchestration layer loops the ladder, takes one card per bucket, and ranks them. CLI and dashboard render the ranked ladder with a ★ on the leader.

**Tech Stack:** Python 3.12, pandas, `unittest` (offline, local parquet). Verify with `uv run python -m unittest`, `uv run ruff check .`, `uv run pyright`.

Spec: `docs/superpowers/specs/2026-07-09-attractiveness-expiration-ladder-design.md`.

---

### Task 1: Ladder buckets in config + `chains.ladder_expirations`

**Files:**
- Modify: `config.py` (add `A_LADDER_BUCKETS` near `A_TARGET_DTE`, line ~113)
- Modify: `options_researcher/chains.py` (add `import logging`; add `ladder_expirations`)
- Test: `tests/test_chains_ladder.py` (create)

- [ ] **Step 1: Write the failing test**

```python
"""tests/test_chains_ladder.py"""
import unittest
from datetime import date

import pandas as pd

from options_researcher.chains import ladder_expirations


def _chain(exp_isos):
    # one throwaway put row per expiration date
    return pd.DataFrame([{"expiration": e, "strike": 100.0, "right": "P",
                          "bid": 1.0, "ask": 1.1, "open_interest": 500,
                          "iv": 0.5, "delta": -0.2} for e in exp_isos])


class LadderExpirationsTests(unittest.TestCase):
    today = date(2026, 7, 9)

    def test_picks_nearest_to_each_target_in_window(self):
        # DTE from 2026-07-09: 17, 32, 63, 95, 124
        chain = _chain(["2026-07-26", "2026-08-10", "2026-09-10",
                        "2026-10-12", "2026-11-10"])
        got = ladder_expirations(chain, self.today)
        self.assertEqual([t for t, _ in got], [14, 30, 60, 90, 120])
        self.assertEqual(got[0][1], date(2026, 7, 26))   # 17 DTE in [10,21]

    def test_skips_bucket_with_no_expiration_in_window(self):
        # only a 17 DTE expiration exists -> only the 14 bucket fills
        chain = _chain(["2026-07-26"])
        got = ladder_expirations(chain, self.today)
        self.assertEqual([t for t, _ in got], [14])

    def test_four_dte_option_excluded_from_two_week_bucket(self):
        # 2026-07-13 is 4 DTE -> below the 14-bucket floor of 10 -> no bucket
        chain = _chain(["2026-07-13"])
        got = ladder_expirations(chain, self.today)
        self.assertEqual(got, [])

    def test_nearest_wins_when_two_in_window(self):
        # 12 DTE and 20 DTE both in [10,21]; 12 is nearer target 14
        chain = _chain(["2026-07-21", "2026-07-29"])
        got = ladder_expirations(chain, self.today)
        self.assertEqual(got[0], (14, date(2026, 7, 21)))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_chains_ladder -v`
Expected: FAIL with `ImportError: cannot import name 'ladder_expirations'`

- [ ] **Step 3: Add config buckets**

In `config.py`, immediately after the `A_TARGET_DTE` line (~113):

```python
# Attractiveness expiration ladder: (target_dte, lo, hi) per bucket. Per-bucket
# accept windows (NOT a flat tolerance) so the 2-week bucket can't pull in a
# ~4 DTE option. Windows are disjoint; the upper tolerance widens with tenor
# because monthlies thin to ~30-day spacing far out. Owner-frozen 2026-07-09.
A_LADDER_BUCKETS     = ((14, 10, 21), (30, 24, 38), (60, 50, 75),
                        (90, 76, 105), (120, 106, 140))
```

- [ ] **Step 4: Implement `ladder_expirations`**

In `options_researcher/chains.py`, add `import logging` to the imports block, then add after `nearest_monthly`:

```python
def ladder_expirations(chain: pd.DataFrame, today: date,
                       buckets=None) -> list[tuple[int, date]]:
    """For each (target, lo, hi) in config.A_LADDER_BUCKETS, the available
    expiration whose DTE is nearest `target` inside [lo, hi] (weekly OR
    monthly). Buckets with no in-window expiration are omitted and logged.
    Disjoint windows mean each expiration maps to at most one bucket, so no
    dedup is needed."""
    import config
    if buckets is None:
        buckets = config.A_LADDER_BUCKETS
    exp_dates = sorted({d for d in pd.to_datetime(chain["expiration"]).dt.date})
    out: list[tuple[int, date]] = []
    for target, lo, hi in buckets:
        in_win = [e for e in exp_dates if lo <= (e - today).days <= hi]
        if not in_win:
            logging.getLogger(__name__).info(
                "ladder: no expiration in [%d,%d] DTE (target %d) as of %s",
                lo, hi, target, today)
            continue
        out.append((target, min(in_win,
                                key=lambda e: abs((e - today).days - target))))
    return out
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run python -m unittest tests.test_chains_ladder -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add config.py options_researcher/chains.py tests/test_chains_ladder.py
git commit -m "feat(chains): ladder_expirations + A_LADDER_BUCKETS (5 DTE buckets)"
```

---

### Task 2: `_expiry_rows` + `exp` param + ranking numbers on cards

Makes each builder able to target an explicit expiration and carry its rank metric. Backward-compatible: with `exp=None` the builders behave exactly as today (existing tests stay green), plus new numeric keys.

**Files:**
- Modify: `options_researcher/attractiveness.py:35-45` (`_monthly_rows` → `_expiry_rows`) and the four builders' signatures + `_monthly_rows` call sites + emitted dicts
- Test: `tests/test_attractiveness.py` (add a class)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_attractiveness.py` (extend the imports line to include `long_card` helpers as needed):

```python
class LadderMetricTests(unittest.TestCase):
    def test_put_card_has_annualized_yield(self):
        from options_researcher.attractiveness import put_card_rows
        chain = chain_rows([("P", 145.0, -0.20, 2.15)])  # exp 2026-07-17
        rows = put_card_rows("VST", chain, "2026-06-30", close=160.0,
                             rv21=0.50, iv_rank=0.62, iv_minus_rv=0.04,
                             earnings_in_cycle=False, fomc_in_cycle=False)
        r = rows[0]
        expected = r["yield_mo"] * 365.0 / r["dte"]
        self.assertAlmostEqual(r["annualized_yield"], expected, places=6)

    def test_long_call_has_breakeven_move_and_cost_per_delta(self):
        from options_researcher.attractiveness import long_call_card_rows
        chain = chain_rows([("C", 165.0, 0.40, 4.00)])  # exp 2026-07-17
        rows = long_call_card_rows("VST", chain, "2026-06-30",
                                   close=160.0, iv_rank=0.30)
        r = rows[0]
        self.assertAlmostEqual(r["breakeven_move"],
                               r["breakeven"] / 160.0 - 1.0, places=6)
        self.assertAlmostEqual(r["cost_per_delta"],
                               r["cost"] / (100.0 * 0.40), places=6)

    def test_exp_param_targets_a_specific_expiration(self):
        from datetime import date
        from options_researcher.attractiveness import put_card_rows
        chain = pd.concat([
            chain_rows([("P", 145.0, -0.20, 2.15)], exp="2026-07-17"),
            chain_rows([("P", 140.0, -0.20, 3.00)], exp="2026-09-18"),
        ], ignore_index=True)
        rows = put_card_rows("VST", chain, "2026-06-30", close=160.0,
                             rv21=0.50, iv_rank=0.62, iv_minus_rv=0.04,
                             earnings_in_cycle=False, fomc_in_cycle=False,
                             exp=date(2026, 9, 18))
        self.assertEqual(rows[0]["expiry"], "2026-09-18")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_attractiveness.LadderMetricTests -v`
Expected: FAIL (`KeyError: 'annualized_yield'` / unexpected `exp` kwarg)

- [ ] **Step 3: Replace `_monthly_rows` with `_expiry_rows`**

In `options_researcher/attractiveness.py`, replace lines 35-45:

```python
def _expiry_rows(chain: pd.DataFrame, day: str, right: str,
                 exp: date | None = None) -> pd.DataFrame:
    today = date.fromisoformat(day)
    if exp is None:
        exp = nearest_monthly(chain, today)
    if exp is None:
        return pd.DataFrame()
    exp_dates = pd.to_datetime(chain["expiration"]).dt.date
    rows = chain[(chain["right"] == right) & (exp_dates == exp)
                 & (chain["bid"] > 0) & (chain["ask"] >= chain["bid"])].copy()
    rows["exp_date"] = exp
    rows["dte"] = (exp - today).days
    return rows
```

- [ ] **Step 4: Thread `exp` through the four builders and add the metric keys**

For `put_card_rows`, `cc_card_rows`, `pmcc_card_rows`, `long_call_card_rows`:
add `exp: date | None = None` as the last keyword arg, and change each
`_monthly_rows(chain, day, "P"|"C")` call to `_expiry_rows(chain, day, "P"|"C", exp)`.

Then in the emitted dicts:

`put_card_rows` (dict at ~line 111) — add key:
```python
                    "annualized_yield": yield_mo * 365.0 / max(int(r["dte"]), 1),
```
`cc_card_rows` (dict at ~line 162) — add the same key.
`pmcc_card_rows` (dict at ~line 215) — add the same key (its `yield_mo` base is `leaps_cost`; annualization is identical).

`long_call_card_rows` (dict at ~line 294) — add:
```python
                    "breakeven_move": breakeven / close - 1.0,
                    "cost_per_delta": cost / (100.0 * abs(float(r["delta"]))),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_attractiveness -v`
Expected: PASS — the new `LadderMetricTests` and all existing card tests (the extra dict keys don't disturb prior assertions).

- [ ] **Step 6: Commit**

```bash
git add options_researcher/attractiveness.py tests/test_attractiveness.py
git commit -m "refactor(attractiveness): _expiry_rows + exp param + per-card rank numbers"
```

---

### Task 3: `rank_cards` + `ladder_cards` orchestration

**Files:**
- Modify: `options_researcher/attractiveness.py` (add two module-level helpers after `_expiry_rows`)
- Test: `tests/test_attractiveness.py` (add a class)

- [ ] **Step 1: Write the failing test**

```python
class RankLadderTests(unittest.TestCase):
    def test_rank_cards_marks_single_leader_higher_better(self):
        from options_researcher.attractiveness import rank_cards
        cards = [{"annualized_yield": 0.10}, {"annualized_yield": 0.25},
                 {"annualized_yield": 0.18}]
        ranked = rank_cards(cards, "annualized_yield", higher_is_better=True)
        self.assertEqual([c["annualized_yield"] for c in ranked],
                         [0.25, 0.18, 0.10])
        self.assertEqual([c["rank_leader"] for c in ranked],
                         [True, False, False])

    def test_rank_cards_nan_sorts_last_never_leads(self):
        from options_researcher.attractiveness import rank_cards
        cards = [{"breakeven_move": float("nan")}, {"breakeven_move": 0.05}]
        ranked = rank_cards(cards, "breakeven_move", higher_is_better=False)
        self.assertEqual(ranked[0]["breakeven_move"], 0.05)
        self.assertTrue(ranked[0]["rank_leader"])
        self.assertFalse(ranked[1]["rank_leader"])

    def test_ladder_cards_one_per_bucket_ranked(self):
        from options_researcher.attractiveness import ladder_cards, put_card_rows
        # two expirations -> two buckets (17 DTE and ~80 DTE from 2026-06-30)
        chain = pd.concat([
            chain_rows([("P", 150.0, -0.20, 2.00)], exp="2026-07-17"),
            chain_rows([("P", 150.0, -0.20, 5.00)], exp="2026-09-18"),
        ], ignore_index=True)
        rows = ladder_cards(put_card_rows, "VST", chain, "2026-06-30",
                            rank_key="annualized_yield", higher_is_better=True,
                            close=160.0, rv21=0.50, iv_rank=0.62,
                            iv_minus_rv=0.04, earnings_in_cycle=False,
                            fomc_in_cycle=False)
        self.assertEqual(len(rows), 2)              # one per filled bucket
        self.assertTrue(rows[0]["rank_leader"])     # best annualized yield first
        self.assertGreaterEqual(rows[0]["annualized_yield"],
                                rows[1]["annualized_yield"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_attractiveness.RankLadderTests -v`
Expected: FAIL (`cannot import name 'rank_cards'`)

- [ ] **Step 3: Implement the helpers**

Add to `options_researcher/attractiveness.py` after `_expiry_rows`:

```python
def rank_cards(cards: list[dict], key: str, *,
               higher_is_better: bool) -> list[dict]:
    """Sort cards by ONE transparent numeric field and flag the leader.
    Cards missing the key or holding NaN sort last and never lead. Mutates
    each card's `rank_leader` and returns the sorted list."""
    def finite(c):
        v = c.get(key)
        return isinstance(v, (int, float)) and v == v
    good = sorted((c for c in cards if finite(c)),
                  key=lambda c: float(c[key]), reverse=higher_is_better)
    bad = [c for c in cards if not finite(c)]
    ranked = good + bad
    for i, c in enumerate(ranked):
        c["rank_leader"] = bool(good) and i == 0
    return ranked


def ladder_cards(builder, symbol: str, chain: pd.DataFrame, day: str, *,
                 rank_key: str, higher_is_better: bool, **kwargs) -> list[dict]:
    """Run `builder` once per ladder expiration, keep the delta-target card
    (the first, since builders sort by delta distance) from each filled
    bucket, then rank the buckets by `rank_key`."""
    from options_researcher.chains import ladder_expirations
    picked: list[dict] = []
    for _target, exp in ladder_expirations(chain, date.fromisoformat(day)):
        cards = builder(symbol, chain, day, exp=exp, **kwargs)
        cards = [c for c in cards if "skipped" not in c]
        if cards:
            picked.append(cards[0])
    return rank_cards(picked, rank_key, higher_is_better=higher_is_better)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_attractiveness.RankLadderTests -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add options_researcher/attractiveness.py tests/test_attractiveness.py
git commit -m "feat(attractiveness): rank_cards + ladder_cards orchestration"
```

---

### Task 4: Wire the ladder into the CLI printout

**Files:**
- Modify: `options_researcher/attractiveness.py` `main()` — the put / covered-call / pmcc / long-call print blocks (~lines 345-405)
- Test: none new (CLI is disk-driven; covered by dashboard test in Task 5 and manual run)

- [ ] **Step 1: Replace the put block to use the ladder**

In `main()`, replace the `put_card_rows(...)` call and its loop with:

```python
        print("-- SELL A PUT? (ladder; ranked by annualized income on capital)")
        rows = ladder_cards(put_card_rows, symbol, chain, day,
                            rank_key="annualized_yield", higher_is_better=True,
                            close=close, rv21=rv21, iv_rank=iv_rank,
                            iv_minus_rv=iv_minus_rv,
                            earnings_in_cycle=earn_in_cycle,
                            fomc_in_cycle=fomc_in_cycle)
        for c in rows or []:
            star = "★ " if c.get("rank_leader") else "  "
            badges = " ".join(f"{k}:{v}" for k, v in c["grades"].items())
            print(f"{star}${c['strike']:.0f} {c['expiry']} "
                  f"({c['dte']}d, {100 * c['annualized_yield']:.0f}%/yr): "
                  f"{c['verdict']}")
            print(f"    [{badges}]")
            if c["grades"]["iv_for_seller"] == "GREEN":
                print(STUDY_A_LINE)
        if not rows:
            print("  no candidates near the target delta this cycle")
```

- [ ] **Step 2: Replace the covered-call loop**

Swap the `cc_card_rows(...)` iteration for:

```python
            rows = ladder_cards(cc_card_rows, symbol, chain, day,
                               rank_key="annualized_yield",
                               higher_is_better=True, close=close,
                               cost_basis=float(lot.iloc[0]["cost_basis"]),
                               iv_rank=iv_rank, iv_minus_rv=iv_minus_rv,
                               earnings_in_cycle=earn_in_cycle,
                               fomc_in_cycle=fomc_in_cycle)
            for c in rows:
                star = "★ " if c.get("rank_leader") else "  "
                badges = " ".join(f"{k}:{v}" for k, v in c["grades"].items())
                print(f"{star}${c['strike']:.0f} {c['expiry']} "
                      f"({c['dte']}d, {100 * c['annualized_yield']:.0f}%/yr): "
                      f"{c['verdict']}")
                print(f"    [{badges}]")
```

(`ladder_cards` already drops the `skipped` cost-basis rows, so the old
`if "skipped" in c` branch is removed here.)

- [ ] **Step 3: Replace the pmcc loop**

```python
            pmcc = ladder_cards(pmcc_card_rows, symbol, chain, day,
                               rank_key="annualized_yield",
                               higher_is_better=True, leaps_strike=k_leaps,
                               leaps_premium=prem_leaps, close=close,
                               iv_rank=iv_rank, iv_minus_rv=iv_minus_rv,
                               earnings_in_cycle=earn_in_cycle,
                               fomc_in_cycle=fomc_in_cycle)
            for c in pmcc:
                star = "★ " if c.get("rank_leader") else "  "
                badges = " ".join(f"{k}:{v}" for k, v in c["grades"].items())
                print(f"{star}${c['strike']:.0f} {c['expiry']}: {c['verdict']}")
                print(f"    [{badges}]")
```

- [ ] **Step 4: Add a tactical long-call ladder block after the LEAPS block**

Directly after the `leaps_card_rows` loop, add:

```python
        print("-- BUY A CALL? (tactical ladder; ranked by smallest move needed)")
        lc = ladder_cards(long_call_card_rows, symbol, chain, day,
                         rank_key="breakeven_move", higher_is_better=False,
                         close=close, iv_rank=iv_rank)
        for c in lc:
            star = "★ " if c.get("rank_leader") else "  "
            badges = " ".join(f"{k}:{v}" for k, v in c["grades"].items())
            print(f"{star}${c['strike']:.0f} {c['expiry']} "
                  f"({c['dte']}d, move {100 * c['breakeven_move']:+.1f}%, "
                  f"${c['cost_per_delta']:,.0f}/delta): {c['verdict']}")
            print(f"    [{badges}]")
        if not lc:
            print("  no tactical long call near the target delta this cycle")
```

- [ ] **Step 5: Smoke-run the CLI against the local cache**

Run: `uv run python -m options_researcher.attractiveness`
Expected: each name prints a SELL A PUT ladder with a `★` leader and `%/yr`
figures for several expirations; a BUY A CALL ladder appears. No traceback.

- [ ] **Step 6: Commit**

```bash
git add options_researcher/attractiveness.py
git commit -m "feat(attractiveness): CLI renders ranked expiration ladders"
```

---

### Task 5: Wire the ladder into the dashboard

**Files:**
- Modify: `options_researcher/attractiveness_dashboard.py` — the `_gather_all` builder calls (~lines 240-300) to use `ladder_cards`; `_headline` (~line 133) to add the ★
- Test: `tests/test_attractiveness_dashboard.py` (add a case using injected `symbol_sections`)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_attractiveness_dashboard.py` (reuse its existing `assemble` injection pattern; mirror the fixture already used there):

```python
    def test_headline_marks_ladder_leader(self):
        from options_researcher.attractiveness_dashboard import _headline
        leader = {"strike": 145.0, "expiry": "2026-08-15", "dte": 60,
                  "credit": 210.0, "rank_leader": True}
        s = _headline("VST", "put", leader)
        self.assertIn("★", s)
        self.assertIn("60 days out", s)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_attractiveness_dashboard -v`
Expected: FAIL (`★` not in headline)

- [ ] **Step 3: Add the ★ to `_headline`**

In `_headline` (~line 133), change the return to prefix a star for the leader:

```python
    star = "★ " if card.get("rank_leader") else ""
    return (f"{star}{lead} — {money} — result by {card['expiry']} "
            f"({card['dte']} days out)")
```

- [ ] **Step 4: Switch `_gather_all` builder calls to `ladder_cards`**

In `_gather_all` (the block starting ~line 240), import `ladder_cards`
alongside the card builders, and replace each direct builder call used for a
group's `cards` with the ladder equivalent, matching Task 4:

- put group: `ladder_cards(put_card_rows, symbol, chain, day, rank_key="annualized_yield", higher_is_better=True, close=close, rv21=rv21, iv_rank=iv_rank, iv_minus_rv=iv_minus_rv, earnings_in_cycle=earn_in_cycle, fomc_in_cycle=fomc_in_cycle)`
- covered-call group: `ladder_cards(cc_card_rows, symbol, chain, day, rank_key="annualized_yield", higher_is_better=True, close=close, cost_basis=float(lot.iloc[0]["cost_basis"]), iv_rank=iv_rank, iv_minus_rv=iv_minus_rv, earnings_in_cycle=earn_in_cycle, fomc_in_cycle=fomc_in_cycle)`
- pmcc group: `ladder_cards(pmcc_card_rows, symbol, chain, day, rank_key="annualized_yield", higher_is_better=True, leaps_strike=k_leaps, leaps_premium=prem_leaps, close=close, iv_rank=iv_rank, iv_minus_rv=iv_minus_rv, earnings_in_cycle=earn_in_cycle, fomc_in_cycle=fomc_in_cycle)`
- long-call group: `ladder_cards(long_call_card_rows, symbol, chain, day, rank_key="breakeven_move", higher_is_better=False, close=close, iv_rank=iv_rank)`

Leave the LEAPS group calling `leaps_card_rows` unchanged.

- [ ] **Step 5: Run tests + regenerate the dashboard**

Run: `uv run python -m unittest tests.test_attractiveness_dashboard -v`
Expected: PASS (new case + existing).
Run: `uv run python -m options_researcher.attractiveness_dashboard`
Expected: writes `.tmp/dashboard/attractiveness.html`; each name shows multiple
expirations per structure with one ★ leader. No traceback.

- [ ] **Step 6: Commit**

```bash
git add options_researcher/attractiveness_dashboard.py tests/test_attractiveness_dashboard.py
git commit -m "feat(dashboard): ranked expiration ladder + leader star"
```

---

### Task 6: Ledger note + full verification

**Files:**
- Modify: `ledger/facts.log` (append one line)

- [ ] **Step 1: Append the facts.log note**

Append a single line (match the file's existing timestamped-line style; read the last line first to copy the format):

```
2026-07-09  ATTRACTIVENESS_LADDER: scanner now shows a 5-bucket DTE ladder (14/30/60/90/120, per-bucket accept windows in config.A_LADDER_BUCKETS) and ranks each structure by one transparent number — annualized yield on capital (credit lanes), required breakeven move (long call, cost-per-delta secondary). Tooling only; no hypothesis, cost, gate, or H5/H6 threshold changed.
```

- [ ] **Step 2: Run the full suite + lint + types**

Run: `uv run python -m unittest discover -s tests`
Expected: OK (exit code 0) — this is the verdict, not a grep of output.
Run: `uv run ruff check .`
Expected: `All checks passed!`
Run: `uv run pyright`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add ledger/facts.log
git commit -m "ledger: note attractiveness expiration ladder (tooling, no hypothesis change)"
```

- [ ] **Step 4: Finish the branch**

Use the `superpowers:finishing-a-development-branch` skill to decide merge/PR
with owner sign-off (merges are owner-gated per repo policy).

---

## Self-Review

**Spec coverage:**
- Ladder buckets + windows → Task 1 ✓
- Weekly eligibility + skip-and-log → Task 1 (`ladder_expirations`) ✓
- Nearest-to-target, disjoint, no-dedup → Task 1 tests ✓
- Annualized-yield ranking (credit) → Tasks 2/3/4/5 ✓
- Breakeven-move primary + cost-per-delta secondary (long call) → Tasks 2/4/5 ✓
- One candidate per bucket, ranked, ★ leader → Task 3 `ladder_cards`, Tasks 4/5 render ✓
- LEAPS excluded from ladder → Tasks 4/5 leave `leaps_card_rows` as-is ✓
- Reuse frozen costs/liquidity, drop thin weeklies → inherited (builders unchanged internally) ✓
- facts.log note, no ledger trial → Task 6 ✓

**Placeholder scan:** none — every code step shows complete code.

**Type consistency:** `ladder_expirations` → `list[tuple[int, date]]` consumed by `ladder_cards`; `rank_cards`/`ladder_cards` signatures identical across Tasks 3/4/5; new card keys `annualized_yield`, `breakeven_move`, `cost_per_delta`, `rank_leader` defined in Task 2/3 and read in Tasks 4/5. Consistent.
