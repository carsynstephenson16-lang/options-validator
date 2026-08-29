"""Receipt-bound measurement: V9_LANE_A_OR restricted to the 9-name registered
cohort, with the one-position-per-underlying occupancy constraint applied.

WHY THIS SCRIPT EXISTS
-----------------------
The 2026-08-14 variant menu (`reports/h7_forward_schwab/2026-08-14-entry-
redesign-variant-menu.md`) measured V9_LANE_A_OR only on the 15-name official
scope, and measured the registered 9-name cohort only under the frozen
(unchanged) entry rule (V14_REGISTERED_COHORT_9). It never measured the
COMBINATION -- V9's relaxed lane-a arming restricted to the 9-name cohort --
so that number in the report is an unmeasured, arithmetic-scaled estimate
("~7-8"), not a receipt.

This script produces the missing combination as an actual receipt. It adds
NO new strategy logic: `tools.h7_entry_variant_menu.Variant` is already a
declarative dataclass whose fields (``lane_a_mode`` and ``universe_label``)
are independently composable -- the menu's own V15/V16/V17 "combination"
variants do exactly this kind of field composition already. This script
constructs one more combination of two already-existing, already-tested
axes and runs it through the tool's own unmodified `measure_variants` /
`summarize_variant` / `write_receipt` pipeline, on the SAME comparable panel
convention (last 70 sessions with a cached chain for every one of the 15
official-scope names) as every other receipt in that report, so the numbers
are directly comparable.

For context the same run also re-measures V0_BASELINE, V9_LANE_A_OR and
V14_REGISTERED_COHORT_9 exactly as `tools/h7_entry_variant_menu.py --panel
comparable` does. Because receipt writing is immutable-by-content
(`write_receipt` raises on any byte difference against an existing file), a
clean re-run against the existing receipts in
`reports/h7_forward_schwab/variant-receipts/comparable_70_common/` is itself
an integrity check: if this script's numbers for those three variants don't
match the ones already on disk from the 2026-08-14 run, it will raise rather
than silently overwrite.

Same integrity rule as the parent tool: frequency ONLY. No P&L, win rate, or
any outcome statistic is computed, stored, or reported here.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from options_researcher.h7_earnings import load_assertions  # noqa: E402
from options_researcher.h7_scope import watch_universe  # noqa: E402
from research.hashing import config_hash  # noqa: E402
from tools.h7_entry_variant_menu import (  # noqa: E402
    DRIFT_HIGH,
    LANE_MODE_OR,
    PanelData,
    Variant,
    _code_sha,
    build_variants,
    common_sessions,
    input_file_hashes,
    measure_variants,
    summarize_variant,
    write_receipt,
)

OUTDIR = Path("reports/h7_forward_schwab/variant-receipts")
LOOKBACK_SESSIONS = 70
WINDOW_SESSIONS = 70


def build_combined_variant() -> Variant:
    """V9_LANE_A_OR's rule change, restricted to the registered 9-name cohort.

    Both ingredients already exist unmodified in the menu:
      * lane_a_mode=LANE_MODE_OR is exactly V9_LANE_A_OR's arming relaxation.
      * universe_label="registered_cohort_9" is exactly V14_REGISTERED_COHORT_9's
        universe restriction.
    No config override, no new lane logic, no board-policy change -- only the
    same two already-vetted axis fields V9 and V14 each use alone.
    """
    return Variant(
        variant_id="V9_LANE_A_OR_COHORT9",
        axis="trigger_logic_x_universe",
        rule_change=(
            "V9_LANE_A_OR's relaxation (lane a arms on a deep drawdown OR a "
            "20-day-high reclaim, instead of requiring both), restricted to "
            "the 9 names frozen into the registered cohort (V14's universe)."
        ),
        rationale_drift=DRIFT_HIGH,
        lane_a_mode=LANE_MODE_OR,
        universe_label="registered_cohort_9",
    )


def main() -> int:
    menu = {v.variant_id: v for v in build_variants()}
    variants = [
        menu["V0_BASELINE"],
        menu["V9_LANE_A_OR"],
        menu["V14_REGISTERED_COHORT_9"],
        build_combined_variant(),
    ]

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
    print(f"[{panel_id}] full stack; sessions={len(sessions)} "
          f"symbol_days={len(sessions) * len(scope)}")

    result = measure_variants(
        variants=variants, sessions_by_symbol=sessions_by_symbol, data=data,
        assertions=assertions)

    # Variants already receipted by the 2026-08-14 run keep their existing,
    # immutable receipt on disk (this run's code_sha has moved forward with
    # two doc-only commits since then, so a byte-identical re-write is not
    # possible and is not attempted -- write_receipt correctly refuses it).
    # Only the new V9 x cohort-9 combination, which has no prior receipt, is
    # written here. The other three are recomputed anyway, purely so their
    # entry counts can be printed as an in-run sanity check against the
    # numbers already on disk.
    already_receipted = {"V0_BASELINE", "V9_LANE_A_OR", "V14_REGISTERED_COHORT_9"}

    for variant in variants:
        receipt = summarize_variant(
            variant=variant, panel_id=panel_id, panel_sessions=sessions,
            sessions_by_symbol=sessions_by_symbol,
            entry_rows=result["entries"][variant.variant_id],
            error_rows=result["errors"][variant.variant_id],
            window_sessions=WINDOW_SESSIONS, code_sha=code_sha,
            baseline_config_hash=baseline_config_hash, input_files=inputs)
        if variant.variant_id not in already_receipted:
            write_receipt(receipt, OUTDIR / panel_id / f"{variant.variant_id}.json")
            written = "written"
        else:
            written = "recomputed only (existing receipt on disk is authoritative)"
        occ = receipt["occupancy_constrained_entries"]
        print(f"  {variant.variant_id:26s} "
              f"entries={receipt['entry_symbol_days']:4d}/"
              f"{receipt['symbol_days']:6d} "
              f"expected={receipt['expected_entries_per_window']:8.2f} "
              f"CI=[{receipt['expected_entries_ci95_exact']['low']:7.2f},"
              f"{receipt['expected_entries_ci95_exact']['high']:8.2f}] "
              f"clears={receipt['clears_bar_ci_lower_ge_bar']} "
              f"occupancy(42/21)={occ.get('42')}/{occ.get('21')} [{written}]")

    print("NO PASS/FAIL DECISION EMITTED; NO OUTCOME STATISTIC COMPUTED; OWNER DECIDES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
