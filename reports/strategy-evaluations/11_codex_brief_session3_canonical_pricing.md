# 11 — Codex brief: Session 3, one canonical adverse-rounded pricing path

**Status: READY TO IMPLEMENT. No owner decision pending.**
**Blocked on: D1 (target branch) only — see [`10_fix_arc_owner_decisions.md`](10_fix_arc_owner_decisions.md).**

Defect: C2, confirmed in [`08_repo_verification.md`](08_repo_verification.md).
Every number in this brief was re-derived against the working tree with the
repo's own functions before being written down.

---

## 1. What is wrong

Three layers price the same spread three different ways:

| Layer | Location | Rounding today |
|---|---|---|
| Selection / credit | `strategies/base.py:49-84` (`entry_credit_conservative`), formula at `:82-84` | **none** |
| Sizing | `strategies/base.py:33-46` (`size_defined_risk`) | inherits the unrounded credit |
| Engine fill | `data/pandas_feed.py:53-64` (`adverse_buy`/`adverse_sell`), applied at `:183-184` | **adverse, ceil/floor to the cent** |
| Exit mark / trigger | `strategies/put_credit_spread.py:344-363` (`_spread_mark`), formula at `:362-363` | **none** |

So sizing gates the $600 `MAX_LOSS_PER_TRADE` cap on a credit the engine will
never actually fill at, and the engine then fills a cent worse — putting real
exposure over the cap. `_finalize_trade` (`strategies/put_credit_spread.py:390-408`)
records `capital_at_risk` and `economic_max_loss` from the **engine** fills
(`:333-334`), so the cap-breaching number is the one that reaches the
scoreboard.

`data/pandas_feed.py:56-58` already declares `adverse_buy`/`adverse_sell` to be
THE canonical path: *"Decide layer, T+1 revalidation, exit marks and P&L must
all price buys through here."* Every later module obeys it —
`h6_watch.py:29`, `h8_watch.py:32`, `h9_study.py:31`, `h10_watch.py:24`,
`card3_study.py:56`, `qm_watch.py:34`, `h7_forward_scoring.py:16`,
`h7_paper_lifecycle.py:25`, `strategies/h7_lanes.py:29,68,73`.
**H1/H2 is the one path never migrated.**

This is not new design. It is finishing the migration recorded as "7b-2R
finding 5" in `docs/superpowers/plans/2026-07-11-h7-7b2r-correction.md:67-70`,
whose reference implementation is `strategies/h7_lanes.py:63-73`.

---

## 2. Measured magnitude (re-derived, not asserted)

Worst-case cap breach across the registered width sweep
(`config.A_SPREAD_WIDTH_SWEEP = [1, 2, 5]`), realistic quotes, $0.05 leg
spreads, credit 15–40% of width:

| Width | short bid/ask | long bid/ask | model total | engine total | breach | % of cap |
|---:|---|---|---:|---:|---:|---:|
| **$1** | 2.33 / 2.38 | 1.96 / 2.01 | $599.52 | **$612.80** | **$12.80** | 2.13% |
| **$2** (production) | 7.01 / 7.06 | 6.30 / 6.35 | $599.84 | **$606.40** | **$6.40** | 1.07% |
| $5 | — | — | — | — | none found | — |

Unconstrained, the mechanism is bounded only by the round-trip commission
floor: as the long leg approaches worthless the sizing denominator collapses,
permitting **228 contracts and a $448.80 breach (74.8% over cap)**. Not a
realistic 30-delta quote — included because it shows nothing structural
protects the cap.

---

## 3. The change

### 3.1 `strategies/base.py` — `entry_credit_conservative`

Add the import and route both legs through the canonical transform:

```python
from data.pandas_feed import adverse_buy, adverse_sell
...
short_fill = adverse_sell(short_base, haircut)   # was: short_base * (1 - haircut)
long_fill  = adverse_buy(long_base, haircut)     # was: long_base * (1 + haircut)
```

Signatures already match — `adverse_buy(ask, haircut=config.SLIPPAGE_HAIRCUT)`
and `adverse_sell(bid, haircut=config.SLIPPAGE_HAIRCUT)` take exactly the shape
this function already uses. Leave the quote-validation block (`:59-77`)
untouched.

### 3.2 `strategies/put_credit_spread.py` — `_spread_mark`

The file already does `from data import pandas_feed` at `:20`, so no new
import:

```python
return (pandas_feed.adverse_buy(float(srow.ask), self.haircut)
        - pandas_feed.adverse_sell(float(lrow.bid), self.haircut))
```

### 3.3 Do NOT touch

`size_defined_risk`, `capital_at_risk_per_spread`, and
`economic_max_loss_per_spread` (`strategies/base.py:23-46`) are pure arithmetic
on whatever credit they are handed. Fixing the input fixes the output. Changing
them too would double-apply the correction.

### 3.4 Import direction — the one that works, and the one that would cycle

- **Works:** `strategies/base.py` → `data.pandas_feed`. Verified: `data/`
  imports nothing from `strategies/`, and the sibling module
  `strategies/put_credit_spread.py` already imports `data.pandas_feed`. No new
  cycle.
- **Do not do this:** moving `adverse_buy`/`adverse_sell` out of
  `data/pandas_feed.py` into `strategies/base.py` and importing them back. That
  inverts the layering the docstring at `data/pandas_feed.py:56-58` declares
  canonical, and forces nine already-correct modules to change imports for no
  functional reason.

---

## 4. Tests — read this section before writing code

### 4.1 You are expected to break a currently-green test. This is the fix working.

`tests/test_core.py:28-34` asserts `entry_credit_conservative(1.00, 1.20, 0.30, 0.40)`
equals the **raw** formula `1.00*(1-h) - 0.40*(1+h)` = `0.586`. After the fix it
returns `adverse_sell(1.00) - adverse_buy(0.40)` = `0.99 - 0.41` = **`0.58`**.

**That test will go red. Update its assertion to the canonical composition —
do not revert the fix, and do not paper over it by editing the input quotes.**
Write the new assertion against `adverse_sell(...)`/`adverse_buy(...)` composed
the way the fixed function composes them, mirroring the pattern in
`tests/test_h7_fill_model.py:48-56`. Do not hand-roll a duplicate rounding
formula in the test — that would let the test and the code drift apart.

### 4.2 The hand-math comment block

`tests/test_pcs_adapters.py:139-146` currently documents the two-regime split
explicitly: "model credit" `0.5416` (used for sizing) vs "engine credit" `0.53`
(used for P&L). **After the fix these must be the same number.** Rewrite the
comment, not just the digits — the comment is what tells the next reader the
split was intentional, and it will no longer be true.

### 4.3 New test — the rounded-sizing boundary proof

File: `tests/test_core.py`, new class `RoundedSizingBoundaryTests`.
Add `from data.pandas_feed import adverse_buy, adverse_sell`.

```python
def test_sized_position_never_exceeds_cap_at_true_engine_fill_prices(self):
    width, short_bid, short_ask, long_bid, long_ask = 1.0, 2.33, 2.38, 1.96, 2.01

    credit = entry_credit_conservative(short_bid, short_ask, long_bid, long_ask)
    contracts, _ = size_defined_risk(width, credit)
    self.assertEqual(contracts, 8)   # the trade sizing accepts here

    engine_credit = adverse_sell(short_bid) - adverse_buy(long_ask)
    true_max_loss = economic_max_loss_per_spread(width, engine_credit) * contracts

    self.assertLessEqual(true_max_loss, config.MAX_LOSS_PER_TRADE)
```

**Pre-fix:** `true_max_loss` = `$612.80` > `$600.00` → the final assertion
fails. **Post-fix:** selection and engine compute the same credit by
construction, so the cap cannot be crossed by rounding. Keep the
`contracts == 8` line — it documents that today's *acceptance decision itself*
is wrong, not merely a downstream metric.

Add the width-$2 case (`7.01/7.06`, `6.30/6.35`, 4 contracts, `$606.40`) as a
second method so the production width is covered directly.

### 4.4 Fixtures

Keep raw human-readable quotes as **inputs** — the fix lives inside the
function, not in the fixtures. Only **assertions** written against the raw
formula need rewriting.

Out of scope, do not touch: `tests/test_study_short_put.py` and
`options_researcher/studies/*.py` assert the raw formula but are self-consistent
descriptive studies with no engine counterpart to diverge from. They will change
value after this fix; that is expected and is not part of C2.

---

## 5. Guardrails

- **No config change.** `MAX_LOSS_PER_TRADE`, `SLIPPAGE_HAIRCUT`,
  `A_SPREAD_WIDTH`, `A_SPREAD_WIDTH_SWEEP`, `COMMISSION_PER_CONTRACT` all stay
  exactly as registered. If you find yourself wanting to change one, stop and
  report — this fix is logic consistency, not calibration.
- **No ledger writes.** Append nothing.
- **No network, no ThetaData, no paid call.** The suite runs offline.
- **Do not build a shared "pricing service" abstraction.** Two call sites route
  to two existing functions. `.cursorrules`: "Keep it minimal."
- If the `block_live_trading` hook fires, treat it as correct and report it.

---

## 6. Acceptance criteria

1. `entry_credit_conservative` and `_spread_mark` both route through
   `adverse_sell`/`adverse_buy`. No other pricing site changed.
2. `tests/test_core.py:28-34` updated to the canonical composition, with the
   old raw-formula assertion gone.
3. `RoundedSizingBoundaryTests` added, covering width $1 and width $2, and
   **demonstrated red before the fix and green after** — state both results
   explicitly in the report. A test that was only ever run post-fix does not
   satisfy this.
4. `tests/test_pcs_adapters.py:139-146` comment block rewritten to reflect one
   credit, not two.
5. Full suite green: `uv run python -m unittest discover -s tests` — report the
   **exit code and the `Ran N tests` line**, not a grep.
6. `uv run ruff check .` and `uv run pyright` both clean.
7. Report every file touched.

## 7. Known consequence — expected, do not "fix"

The change is one-directional: adverse rounding only moves the credit down,
which only moves required capital up, which can only reduce the contract count.
**Trades accepted today may become rejections** (`risk_budget_too_small` at
`strategies/put_credit_spread.py:195-200`, or in rare cases
`non_positive_credit` at `:193-194`). It can never create a trade.

If any test's expected trade count drops, that is the fix working. Report the
change; do not loosen a threshold to restore the old count.

**Not measured, and worth reporting if cheap:** how many historical cached
selections flip from accepted to rejected. That requires running
`select_put_credit_spread_candidate` over the cached in-sample chains twice and
diffing. Do **not** read past `config.IN_SAMPLE_END` and do **not** pass
`allow_oos=True`. If this path ever feeds a new loss-gated registration, that
count is an input to the registration feasibility gate
(`docs/superpowers/2026-07-24-registration-feasibility-gate.md`).

## 8. Relationship to Session 2 (causal clock)

**Logically independent.** C1 changes *which day's* quotes are read; C2 changes
*how a quote becomes a dollar price*. Neither reads state the other writes, and
the boundary tests above use synthetic quotes with no date coupling — valid
whichever lands first.

**One practical coupling:** both fixes touch
`strategies/put_credit_spread.py` and both must edit the same hand-math comment
at `tests/test_pcs_adapters.py:139-146`. Landing them in one changeset risks a
conflict there; landing them separately means that comment gets rewritten twice.
Either is fine — just know which you are doing.
