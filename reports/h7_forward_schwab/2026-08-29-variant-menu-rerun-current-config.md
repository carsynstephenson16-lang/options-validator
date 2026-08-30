# H7 variant menu — re-measured at current config

**Date:** 2026-08-29
**Owner directive:** in-session 2026-08-29 evening — *re-run the H7 entry-variant
menu at current config to produce the fresh feasibility receipt that packet row 5
requires*, resolving the config-drift question **by re-measurement rather than by
waiver**.
**Branch:** `claude/variant-menu-rerun-2026-08-29` (from `origin/main` @ `86e8ba6`)
**New receipts:** `reports/h7_forward_schwab/variant-receipts/rerun-2026-08-29-current-config/`
**Status:** measurement only. **Not a registration, not a backtest, no verdict, no
frozen number.** Nothing here is owner-typed.

---

## The short version

Every figure the bar-7 registration packet cites **re-measured identical** at the
current configuration. All 38 receipts were regenerated; comparing old against
new field by field produced **zero substantive differences**. The only things
that moved are the three provenance stamps that are *supposed* to move —
`code_sha`, `baseline_config_hash`, and the `receipt_hash` derived from them.

In plain terms: the configuration drift that made the old receipts fail their own
reproduction check did not touch any number in the packet. The measurement was
re-run, not waived.

*All figures below are **Tool-computed** (`tools/h7_entry_variant_menu.py`), not
owner-typed and not owner-ratified.*

---

## 1. Why this rerun exists

The packet's §0 row 5 ("fresh feasibility receipt at current config") read **NOT
MET** because every variant receipt it cites carries
`baseline_config_hash 031e711a…`, while `config_hash()` on `main` is now
`b86b3188…`. The receipts are immutable by content — `write_receipt` raises
`FileExistsError("immutable variant receipt conflict")` on any byte difference —
so re-running into the original paths refuses by design, and §8a's F8 note
concluded that reproduction was "pinned to each receipt's recorded `code_sha`,
not re-run it on main."

Row 5 left open whether the drift required a rerun or could be waived on the
strength of the review that verified no entry-stack constant had changed. The
owner chose the rerun. This document is that rerun.

---

## 2. What was measured, and how the fresh receipts were written

**Nineteen configurations**, matching the multiple-testing count the packet must
disclose:

- the full 18-variant menu (V0–V17) on both panels, and
- the cohort-9 follow-up combination `V9_LANE_A_OR_COHORT9`.

**The sanctioned fresh-output mechanism** is the menu tool's own `--outdir`
flag. Nothing was deleted, edited, moved, or overwritten; no immutability guard
was bypassed or relaxed; no strategy code and no tool code was modified. The
original receipts are untouched on disk, and the new set lives in a separate
dated sibling directory that names its own purpose.

`tools/h7_entry_variant_menu_v9_cohort9.py` has **no CLI and a hard-pinned
`OUTDIR`**, so it cannot write a fresh set as written (§6 records this as a
finding). Its variant was instead re-measured by importing its own unmodified
`build_combined_variant()` and running it through the parent tool's unmodified
`measure_variants` / `summarize_variant` / `write_receipt` pipeline — exactly
what that script does internally — with the output directory pointed at the new
dated folder. The harness is reproduced verbatim in §7.

### Window and universe — pinned, and verified unchanged

The tool pins the comparable panel to *the last 70 sessions that have a cached
chain for all 15 official-scope names*. That definition **can** slide forward if
the cache gains sessions, so it was checked rather than assumed:

| Check | Result |
|---|---|
| Panel bounds, old receipts | 2026-04-16 → 2026-07-27, 70 sessions, 1,050 name-days |
| Panel bounds, new receipts | 2026-04-16 → 2026-07-27, 70 sessions, 1,050 name-days |
| Latest cached chain session, every scope name | 2026-07-27 (unchanged) |
| Deep-census panel | 2018-01-02 → 2026-07-27, 2,152 sessions, 23,716 name-days — identical old and new |
| `sessions_per_symbol`, all 15 names | identical old and new |
| `data/earnings/gating_v3.csv` sha256 | `da2bf6ab…` — unchanged |
| `data/earnings/assertions_v2.csv` sha256 | `124f1fa2…` — unchanged |

**There is no window difference to disclose.** The Schwab pre-close captures
that resumed in August write to `.cache/schwab_chains/`, a different store, so
they did not extend the ThetaData panel this tool reads.

### Data and network discipline

Cached data only: the parquet chain cache plus cached underlying closes. Both
runs were executed under a Python audit hook that raises on any outbound network
event (`socket.connect`, `socket.getaddrinfo`, `urllib.Request`, and related).
**No network event fired at any point** — including during import, which pulls in
LumiBot. `uv run python tools/irreplaceable_data_guard.py verify` reported
`irreplaceable data: OK` afterwards; the cache was not mutated.

---

## 3. The comparison — old vs new

### 3a. Full-stack panel (2026-04-16 → 2026-07-27, 1,050 name-days)

"Occ 42" and "Occ 21" are the occupancy-constrained counts under the registered
one-open-position-per-underlying rule, at the 42-session and 21-session holding
assumptions.

| Variant | Entries old → new | 95% CI old → new | Occ 42 old → new | Occ 21 old → new |
|---|---|---|---|---|
| **V0_BASELINE** | **4.00 → 4.00** | [1.09, 10.21] → [1.09, 10.21] | **3 → 3** | 4 → 4 |
| V1_DRAWDOWN_15 | 5.00 → 5.00 | [1.63, 11.63] → [1.63, 11.63] | 3 → 3 | 5 → 5 |
| V2_DRAWDOWN_10 | 5.00 → 5.00 | [1.63, 11.63] → [1.63, 11.63] | 3 → 3 | 5 → 5 |
| V3_RANGE_20 | 4.00 → 4.00 | [1.09, 10.21] → [1.09, 10.21] | 3 → 3 | 4 → 4 |
| V4_RVPCTILE_40 | 4.00 → 4.00 | [1.09, 10.21] → [1.09, 10.21] | 3 → 3 | 4 → 4 |
| V5_CLOSE_ROUTE_DEADZONE | 4.00 → 4.00 | [1.09, 10.21] → [1.09, 10.21] | 3 → 3 | 4 → 4 |
| V6_ADMIT_3 | 4.00 → 4.00 | [1.09, 10.21] → [1.09, 10.21] | 3 → 3 | 4 → 4 |
| V7_DELTA_TOL_10 | 4.00 → 4.00 | [1.09, 10.21] → [1.09, 10.21] | 3 → 3 | 4 → 4 |
| V8_RECLAIM_10 | 4.00 → 4.00 | [1.09, 10.21] → [1.09, 10.21] | 3 → 3 | 4 → 4 |
| **V9_LANE_A_OR** | **104.00 → 104.00** | [85.73, 124.67] → [85.73, 124.67] | **10 → 10** | **16 → 16** |
| V10_LANE_B_OR | 5.00 → 5.00 | [1.63, 11.63] → [1.63, 11.63] | 4 → 4 | 5 → 5 |
| V11_LANE_B_NO_EDGE | 4.00 → 4.00 | [1.09, 10.21] → [1.09, 10.21] | 3 → 3 | 4 → 4 |
| V12_MULTI_LANE | 4.00 → 4.00 | [1.09, 10.21] → [1.09, 10.21] | 3 → 3 | 4 → 4 |
| V13_H7C_CONCURRENT_2 | 4.00 → 4.00 | [1.09, 10.21] → [1.09, 10.21] | 3 → 3 | 4 → 4 |
| **V14_REGISTERED_COHORT_9** | **4.00 → 4.00** | **[1.09, 10.19] → [1.09, 10.19]** | **3 → 3** | 4 → 4 |
| V15_COMBO_MILD | 5.00 → 5.00 | [1.63, 11.63] → [1.63, 11.63] | 3 → 3 | 5 → 5 |
| V16_COMBO_MEDIUM | 6.00 → 6.00 | [2.20, 13.02] → [2.20, 13.02] | 4 → 4 | 6 → 6 |
| V17_COMBO_WIDE | 147.00 → 147.00 | [125.55, 170.60] → [125.55, 170.60] | 15 → 15 | 24 → 24 |
| **V9_LANE_A_OR_COHORT9** | **80.00 → 80.00** (of 630 name-days) | **[64.25, 97.99] → [64.25, 97.99]** | **7 → 7** | **11 → 11** |

Every one of the specific figures row 5 was raised against re-measured
identical: V0 and V14 at **4.00** unconstrained and **3** occupancy-constrained;
V9 at **104** with **10** (42-session lockout) and **16** (21-session); the
cohort-9 combination at **80** unconstrained with **7** and **11**.

### 3b. Per-symbol contribution

| Variant | Old | New |
|---|---|---|
| V0_BASELINE | NOW 2, MSFT 1, PLTR 1 | NOW 2, MSFT 1, PLTR 1 |
| V9_LANE_A_OR | PLTR 37, NOW 28, CRWV 12, MSFT 12, SMCI 12, VST 2, AVGO 1 | PLTR 37, NOW 28, CRWV 12, MSFT 12, SMCI 12, VST 2, AVGO 1 |
| V14_REGISTERED_COHORT_9 | NOW 2, MSFT 1, PLTR 1 | NOW 2, MSFT 1, PLTR 1 |
| V9_LANE_A_OR_COHORT9 | PLTR 38, NOW 28, MSFT 12, VST 2 | PLTR 38, NOW 28, MSFT 12, VST 2 |

The packet's §3b per-symbol note (PLTR **38** on the strict 9-name subset against
**37** on the 15-name panel) reproduces exactly. So does the individual
`entry_symbol_day_rows` list for all four — the same symbol-days, in the same
order, not merely the same totals.

### 3c. Blocking-condition waterfall

| First blocker | Old lane-days | New lane-days |
|---|---|---|
| Earnings gate | 1,098 | 1,098 |
| Liquidity admission | 957 | 957 |
| Arming rule | 806 | 806 |
| Lane excluded by design | 280 | 280 |
| Pricing route | 5 | 5 |
| Reached ENTRY-OK | 4 | 4 |

The waterfall receipt records no `code_sha` or config hash, so even its
`receipt_hash` is unchanged: `2a9ea136…` → `2a9ea136…`.

### 3d. Deep arming census (2018-01-02 → 2026-07-27, 23,716 name-days)

All 18 variants matched on armed name-days, rate, per-70-session projection, and
the rolling-window min/median/max dispersion. Representative rows:

| Variant | Armed old → new | Per 70 sessions | Rolling min/med/max old → new |
|---|---|---|---|
| V0_BASELINE | 1,395 → 1,395 | 61.76 | 0/43/143 → 0/43/143 |
| V9_LANE_A_OR | 8,084 → 8,084 | 357.91 | 43/212/656 → 43/212/656 |
| V14_REGISTERED_COHORT_9 | 1,148 / 15,803 → 1,148 / 15,803 | 45.77 | 0/30/140 → 0/30/140 |
| V17_COMBO_WIDE | 20,654 → 20,654 | 914.43 | 285/665/1,044 → 285/665/1,044 |

### 3e. Machine diff across all 38 receipts

Old and new were compared recursively over every field of every receipt, with
only `code_sha`, `baseline_config_hash` and `receipt_hash` excluded:

```
files compared: 38   substantive field differences: 0
```

A second, independent cross-check: the cohort-9 harness re-derived V0, V9 and
V14 in its own separate measurement pass and wrote them to the same fresh paths
the menu run had already written. `write_receipt` compares bytes and raises on
any difference — it accepted them silently, so the two independent runs agree
**byte for byte**, not merely numerically.

### 3f. What did change — the provenance stamps

| Receipt | `code_sha` | `baseline_config_hash` | `receipt_hash` | `variant_identity_hash` |
|---|---|---|---|---|
| V0_BASELINE | `5a00a50` → `86e8ba6` | `031e711a…` → `b86b3188…` | `e405f805…` → `22886106…` | `591585d5…` (unchanged) |
| V14_REGISTERED_COHORT_9 | `5a00a50` → `86e8ba6` | `031e711a…` → `b86b3188…` | `d7193de8…` → `ddfbf04e…` | `13f9d4b7…` (unchanged) |
| V9_LANE_A_OR | `5a00a50` → `86e8ba6` | `031e711a…` → `b86b3188…` | `8396304d…` → `f9258fa0…` | `9e523154…` (unchanged) |
| V9_LANE_A_OR_COHORT9 | `ccd161f` → `86e8ba6` | `031e711a…` → `b86b3188…` | `5b0fb191…` → `07747c86…` | `6e47a2cb…` (unchanged) |

Identical `variant_identity_hash` values confirm the *rules measured* are the
same rules, not merely rules producing the same counts.

---

## 4. What the config drift actually was — re-verified independently

Measured directly between the receipts' own recorded code SHA and current main
(`git diff 5a00a50 86e8ba6 -- config.py`; `config.py` is byte-identical at
`5a00a50` and `ccd161f`, which is why both receipt sets recorded the same
`031e711a…`):

| Constant | Change |
|---|---|
| `H10B_RESUME_FLOOR_SESSION` | added, `"2026-08-19"` |
| `H5_RESUME_FLOOR_SESSION` | added, `"2026-08-19"` |
| `PICK_TOP_N` | added, `5` (display shortlist width) |
| `CONSISTENCY_DELTA_JUMP_ABS` | added, `0.30` |
| `CONSISTENCY_UNDERLYING_SMALL_MOVE` | added, `0.01` |
| `CONSISTENCY_SPREAD_BLOWOUT_MIN_RATIO` | added, `2.0` |
| `CONSISTENCY_MAX_EXAMPLES` | added, `20` |
| `CONTEXT_LANE_ENABLED` | added, `True` |
| `SHORT_CONTEXT_ENABLED` | `False` → `True` |

**Finding (minor, does not change any conclusion).** That is **nine** constants
inside `config_hash()`'s scope — the function hashes *every* uppercase name in
`config.py` — not the **five** recorded in the packet's §8a F8 note and §0 row 5.
The extra four (`CONTEXT_LANE_ENABLED`, `PICK_TOP_N`, and the two resume-floor
sessions) are display-lane and lane-resume constants. The earlier count appears
to have been taken against a different baseline. Every one of the nine is a
display-layer, chain-consistency-shadow, or lane-resume constant: **none is an H7
entry-stack, arming, routing, liquidity, fill-realism, earnings-gate, or
risk-sizing constant.** Re-verified: `h7_signals`, `h7_watch`, `h7_board`,
`h7_lanes`, `h7_cohort`, `h7_scope`, `h7_earnings`, `chains`, `underlying_closes`,
`cache_runner`, `research/hashing.py` and `tools/h7_entry_variant_menu.py` are all
**byte-identical** between `5a00a50` and `86e8ba6`. The rerun is the empirical
confirmation of what that inspection predicted.

---

## 5. Conclusion, in honest vocabulary

**Re-measured identical.** Running the H7 entry-variant menu at the current
configuration reproduces every packet-cited figure exactly, on the same declared
window and universe, from unchanged cached inputs. The configuration drift is
now shown to be inert with respect to this measurement, by measurement rather
than by inference or waiver.

What this does **not** say:

- It says nothing about whether any variant has an edge. **No outcome statistic
  of any kind was computed** — no P&L, no win rate, no premium capture. The
  tool's guards refuse to produce one.
- It does not change the feasibility conclusion. Against the packet's 14-entry
  bar (2 × the owner-typed loss bar of 7), the occupancy-constrained figures
  remain **3** (V0 / V14), **7** (V9 × cohort-9, 42-session), **10** (V9 on 15
  names) and **11** (V9 × cohort-9, 21-session). All still short of 14. The
  rerun confirms the shortfall; it does not narrow it.
- It is not a registration and emits no verdict. Nineteen configurations have now
  been measured, and any registration selecting one must disclose that count.
- The receipts' own `clears_bar_ci_lower_ge_bar` fields are computed against the
  tool's coded 20-entry bar and the **unconstrained** counts. They are not
  statements about the 14-entry bar and not statements about the
  occupancy-constrained figures.

---

## 6. Findings for the record

**F-R1 — `tools/h7_entry_variant_menu_v9_cohort9.py` cannot write a fresh
receipt set as written.** It has no argument parser and pins
`OUTDIR = Path("reports/h7_forward_schwab/variant-receipts")` as a module
constant. Run unchanged today it re-measures V0/V9/V14 correctly, then raises
`FileExistsError` when it reaches the only receipt it writes. The parent tool
solved this with `--outdir`; the follow-up script did not inherit it. Adding the
same flag would make future config-drift reruns a one-line command instead of a
harness. **Not done here** — this session was directed to run the measurement,
not to modify tooling, and the parent tool's `--outdir` was sufficient for 18 of
the 19 configurations.

**F-R2 — the "five constants" count in the packet's F8 note is an undercount**
(nine; §4 above). No conclusion moves: none of the nine is an entry-stack or
fill-realism constant, and the rerun shows the drift changed nothing measurable.

---

## 7. Reproducing this

Run from the main checkout, or from a worktree whose `.cache` is symlinked to the
main checkout's (a worktree has no `.cache` of its own). Remove that symlink
before running the full test suite: two unrelated tests require an empty cache.

**The 18-variant menu, both panels:**

```bash
uv run python -m tools.h7_entry_variant_menu --panel both \
  --outdir reports/h7_forward_schwab/variant-receipts/rerun-2026-08-29-current-config
```

**The cohort-9 combination** (the script's `OUTDIR` is hard-pinned, so its own
unmodified variant definition is driven through the parent tool's unmodified
pipeline — no strategy code, tool code, or variant definition is altered):

```python
import sys
from pathlib import Path
sys.path.insert(0, ".")

from options_researcher.h7_earnings import load_assertions
from options_researcher.h7_scope import watch_universe
from research.hashing import config_hash
from tools.h7_entry_variant_menu import (
    PanelData, _code_sha, build_variants, common_sessions, input_file_hashes,
    measure_variants, summarize_variant, write_receipt,
)
from tools.h7_entry_variant_menu_v9_cohort9 import (
    LOOKBACK_SESSIONS, WINDOW_SESSIONS, build_combined_variant,
)

OUTDIR = Path("reports/h7_forward_schwab/variant-receipts/"
              "rerun-2026-08-29-current-config")

menu = {v.variant_id: v for v in build_variants()}
variants = [menu["V0_BASELINE"], menu["V9_LANE_A_OR"],
            menu["V14_REGISTERED_COHORT_9"], build_combined_variant()]

data = PanelData()
assertions = load_assertions()
code_sha = _code_sha()
baseline_config_hash = config_hash()
inputs = input_file_hashes({
    "gating_assertions": Path("data/earnings/gating_v3.csv"),
    "raw_assertions": Path("data/earnings/assertions_v2.csv"),
})
scope = sorted(watch_universe())
sessions = common_sessions(scope, data, limit=LOOKBACK_SESSIONS)
if len(sessions) < LOOKBACK_SESSIONS:
    raise RuntimeError(f"only {len(sessions)} common cached sessions")
sessions_by_symbol = {s: list(sessions) for s in scope}
panel_id = "comparable_70_common"

result = measure_variants(variants=variants, sessions_by_symbol=sessions_by_symbol,
                          data=data, assertions=assertions)
for variant in variants:
    receipt = summarize_variant(
        variant=variant, panel_id=panel_id, panel_sessions=sessions,
        sessions_by_symbol=sessions_by_symbol,
        entry_rows=result["entries"][variant.variant_id],
        error_rows=result["errors"][variant.variant_id],
        window_sessions=WINDOW_SESSIONS, code_sha=code_sha,
        baseline_config_hash=baseline_config_hash, input_files=inputs)
    # V0/V9/V14 already exist in OUTDIR from the menu run; write_receipt is
    # byte-comparison immutable, so a silent no-op proves the two independent
    # runs agree byte-for-byte, and any difference raises FileExistsError.
    write_receipt(receipt, OUTDIR / panel_id / f"{variant.variant_id}.json")
```

**Checks run alongside:** an audit-hook network guard over both runs (no event
fired); `uv run python tools/irreplaceable_data_guard.py verify` →
`irreplaceable data: OK`; `uv run python -m unittest discover -s tests
-p 'test_h7_entry_variant_menu.py'` → **54 tests, OK**.
