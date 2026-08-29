# H7 entry-rule redesign — V9_LANE_A_OR × registered cohort-9 × occupancy (measured)

**Date:** 2026-08-15
**Follow-up to:** `reports/h7_forward_schwab/2026-08-14-entry-redesign-variant-menu.md`
**Branch / code:** `wt/brief09-variant-menu-0814`
**Tool:** `tools/h7_entry_variant_menu.py` (unmodified) via a small composition
runner, `tools/h7_entry_variant_menu_v9_cohort9.py`
**Receipt:** `reports/h7_forward_schwab/variant-receipts/comparable_70_common/V9_LANE_A_OR_COHORT9.json`
**Status:** measurement only. No registration, no frozen numbers, no verdict.
Frequency only — no P&L, win rate, or any outcome statistic.

---

## What was missing

The 2026-08-14 menu measured V9_LANE_A_OR (lane-a arms on a deep drawdown *or*
a 20-day-high reclaim, instead of requiring both) only on the 15-name official
scope, and measured the registered 9-name cohort only under the *unchanged*
entry rule (V14_REGISTERED_COHORT_9). It never measured the **combination** —
V9's relaxed arming restricted to the 9-name registered cohort — with the
one-open-position-per-underlying occupancy constraint applied. The report's
own text only offered an arithmetic-scaled *estimate* for that combination
(~7-8 expected entries), not a receipt.

## What this run measured

`tools/h7_entry_variant_menu.py`'s `Variant` is a declarative dataclass; V9's
`lane_a_mode="or"` and V14's `universe_label="registered_cohort_9"` are two
already-existing, already-vetted fields (the menu's own V15–V17 "combination"
variants already compose fields this way). No strategy logic, config
override, or board policy was added or changed — the new variant
(`V9_LANE_A_OR_COHORT9`) is exactly V9's arming rule applied to V14's
universe, run through the tool's own unmodified `measure_variants` /
`summarize_variant` / `write_receipt` pipeline on the same "comparable"
70-session panel convention as every other receipt in the 2026-08-14 report
(2026-04-16 → 2026-07-27, sessions with a cached chain for all 15 official-
scope names).

As an integrity check, the same run also recomputed V0_BASELINE, V9_LANE_A_OR,
and V14_REGISTERED_COHORT_9. All three matched their existing 2026-08-14
receipts exactly on entries, symbol-days, and occupancy counts (the only
difference is `code_sha`, which legitimately advanced by two doc-only commits
since 2026-08-14 — see "Reproduction notes" below). Their receipts were **not**
rewritten; the existing files remain authoritative.

## Result

| Metric | Value |
|---|---|
| Universe | 9 names (registered cohort): AMD, AMZN, CEG, ET, MSFT, NOW, PLTR, TEM, VST |
| Panel | 70 sessions, 2026-04-16 → 2026-07-27; 630 symbol-days |
| Entries (unconstrained, flat-book assumption) | **80** / 630 symbol-days |
| Expected entries per 70-session window (unconstrained) | 80.00, 95% CI [64.25, 97.99] |
| **Occupancy-constrained (42-session lockout — primary schedule assumption)** | **7** |
| Occupancy-constrained (21-session lockout — generous alternate) | 11 |
| Top-symbol concentration | PLTR 38/80 = 47.5% |
| Names contributing | 4 of 9 (MSFT 12, NOW 28, PLTR 38, VST 2; AMD/AMZN/CEG/ET/TEM = 0) |

**The measured, receipt-bound number is 7 expected entries** per 70-session
window (42-session occupancy lockout, the schedule's primary assumption), or
**11** under the more generous 21-session alternate. Both are upper bounds —
neither nets the monthly risk sleeve across the lockout, and both assume the
book starts flat every session, which no live window can reproduce.

This lands almost exactly on the prior estimate (~7-8): the arithmetic scaling
in the 2026-08-14 report was a reasonable approximation for this axis, but it
was still an estimate, not a receipt, until now.

## Does it clear a feasibility bar?

- Against the tool's own coded bar (20 entries = 2× the *currently registered*
  10-loss requirement): **no**, whether judged on the unconstrained count
  interpreted honestly (the receipt's `clears_bar_ci_lower_ge_bar: true` field
  is computed against the unconstrained 80-entry count only, exactly as the
  existing V9_LANE_A_OR receipt already does — the report's own "asterisk"
  caveat about that field applies here too) or on either occupancy-constrained
  figure (7 or 11).
- Against a hypothetical 14-entry bar (2× a lower, *not-yet-registered* 7-loss
  requirement under separate owner discussion): **no** — 7 < 14 under the
  primary occupancy assumption, and 11 < 14 even under the generous alternate.

No verdict is implied by either comparison; the tool computes frequency only,
and the owner picks the bar and the loss requirement at registration.

## Reproduction notes

- Run from this worktree with `.cache` symlinked (read-only) to the main
  checkout's `.cache`, following the 2026-08-14 report's documented
  convention — the worktree carries no chain/underlying cache of its own.
  The symlink was removed again after the run and before the test suite ran
  (two suite tests require an empty `.cache`).
- `tools/irreplaceable_data_guard.py verify` (run from the main checkout, both
  before and after) reported the cache unchanged — read-only access only.
- `data/earnings/gating_v3.csv`, `data/earnings/assertions_v2.csv`, and the
  frozen `config_hash()` all matched the 2026-08-14 receipts byte-for-byte;
  only `code_sha` moved (two doc-only commits landed on this branch since
  2026-08-14: `aeb6653`, `ccd161f`), which is why the three re-measured
  variants were not rewritten over their existing, still-valid receipts.

```bash
uv run python -m tools.h7_entry_variant_menu_v9_cohort9
```
