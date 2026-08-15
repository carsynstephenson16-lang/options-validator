# Mutation-test results — ritual switch-on (brief 11 §10)

**Date:** 2026-08-14
**Branch:** `claude/ritual-switch-on-rev21` (base `origin/main` = `bfa58d8`)
**Spec:** `docs/superpowers/plans/2026-08-14-11-ritual-switch-on-rev2-spec.md` §10
**Why this exists:** the EC-1 lesson — a green suite plus passing tests still
hid a real defect. Each mutation below was applied to the implemented tree, the
named test module was run and confirmed **RED**, the mutation was reverted with
`git checkout --`, and the module was re-run and confirmed **green**. Every run
was offline `unittest`; no network, no provider calls.

Procedure driver: `/tmp/mutate.py` (scratch, not checked in — each mutation is
a one-line source edit reproducible from the "Mutation applied" column).

## Results — 10/10 turned a test RED

| # | Mutation applied | Test module | Test(s) that went RED | Evidence line |
| --- | --- | --- | --- | --- |
| M1 | Moved the whole `require-data` gate block below `mkdir -p "$LOGDIR"` | `test_daily_ritual_provenance.py` | `test_require_data_precedes_every_mutation_surface` (P1); `test_every_script_surface_is_classified` | `AssertionError: 2879 not less than 2830` (verb=`mkdir -p "$LOGDIR"`) |
| M2 | Moved the `h7_source_health` invocation above the `require-full` gate | `test_daily_ritual_provenance.py` | `test_require_full_precedes_every_h7_surface` (P2); `test_authority_gate_replaces_provider_topup_dependency` | `AssertionError: 7708 not less than 7311` (module=`options_researcher.h7_source_health`) |
| M3 | Added `"$UV" run python -m options_researcher.h9_something` without registering it | `test_daily_ritual_provenance.py` | `test_every_script_surface_is_classified` (P4, registry 1) | `AssertionError: Items in the first set but not the second:` (`options_researcher.h9_something`) |
| M4 | Added `reports/h7_receipts` to the unconditional `DATA_TIER_PATHS` | `test_daily_ritual_provenance.py` | `test_durability_allow_list_is_tier_scoped` | `AssertionError: 1118 not greater than 1532` (path=`reports/h7_receipts`) |
| M5 | Dropped the `exact_session_source_active` requirement from `evaluate_full_ritual()` (full tier ready with `ritual_data_phase_active=True`, `h7_active=False`) | `test_ritual_authority.py` | `test_tier_matrix_over_all_flag_combinations`; `test_full_tier_blocker_wording_is_preserved` | `AssertionError: True != False` (data=True, source=False, h7=True) |
| M6 | Appended `MUTATION_TEST_CONSTANT = 1` to `config.py` | `test_ritual_switch_on_hash_containment.py` | `test_config_hash_surface_unchanged` | `Tuples differ: (... 'MUTATION_TEST_CONSTANT', ...) != (...)` |
| M7 | Removed `[ "$CRIT_COUNT" -eq 1 ]` from the `[DATA-STARVED]` title condition (equivalent to a second, unrelated `crit` no longer forcing `[BROKEN]`) | `test_daily_ritual_provenance.py` | `test_starved_title_flips_to_broken_on_a_second_critical`; `test_starved_label_requires_single_capture_critical` | `AssertionError: '[DATA-STARVED] options-validator daily ritual' != '[BROKEN] options-validator daily ritual'` (critical=1, count=2) |
| M8 | Moved the `qm_dashboard --refresh-ohlcv` block inside full-tier region B | `test_daily_ritual_provenance.py` | `test_data_tier_island_is_outside_the_full_fence`; `test_dash_c_sites_are_classified_and_data_tier_ones_are_unfenced`; `test_frozen_operator_order_is_preserved`; `test_every_script_surface_is_classified` | `AssertionError: True is not false` (token=`options_researcher.qm_dashboard --refresh-ohlcv --as-of "$AS_OF"`) |
| M9 | Broadened the P2 matcher from `python -m <module>` to a bare `h7_` substring search | `test_daily_ritual_provenance.py` | `test_require_full_precedes_every_h7_surface`; `test_require_data_precedes_every_mutation_surface`; `test_frozen_operator_order_is_preserved` | `AssertionError: 7613 not less than 215` (module=`options_researcher.h7_watch`) — byte 215 is the header comment, i.e. the broadened matcher fails on a CORRECT script |
| M10 | Added a fifth `mkdir -p reports/mutation` site without registering it | `test_daily_ritual_provenance.py` | `test_every_script_surface_is_classified` (P4, registry 3) | verb-line dict differs: `'git add': (476,)` vs registered `(475,)`, and the unregistered `mkdir` shifts every downstream site |

Every row was followed by `git checkout --` and a re-run that printed `OK`.

## Notes on two rows

* **M5** is stated in the spec as a behavior check ("full tier still refuses"),
  not as a mutation. It was implemented as the mutation that would break that
  behavior — removing a flag's contribution to `evaluate_full_ritual()` — so it
  has a test to turn RED. The direct behavior is separately asserted for all
  eight flag combinations in `test_tier_matrix_over_all_flag_combinations` and
  `test_full_tier_implies_data_tier`.
* **M9** is the one mutation that must fail on a *correct* script rather than
  on a broken one. It proves the P2 matcher is specified rather than
  accidental: `daily_ritual.sh:115` imports `options_researcher.h7_watch`
  inside a `python -c` value resolution that runs *before* the `require-full`
  gate, and it is deliberately classified `DATA_TIER_PERMITTED`. Any matcher
  that greps for the bare substring flags a correct script.

## Battery run alongside these mutations

* Full suite: `uv run python -m unittest discover -s tests` → **2909 tests, OK
  (skipped=5), exit code 0** (captured directly, not through a pipe).
* `uv run ruff check .` → `All checks passed!` (exit 0).
* `uv run pyright` → `0 errors, 0 warnings, 0 informations`.
* `zsh tools/daily_ritual.sh status` → exit 0, byte-preserving (the guarded log
  tree and `uv.lock` are hash-compared by
  `test_status_preserves_log_tree_and_lockfile_bytes`).
* `uv run python -m data.ritual_authority require-data` → exit 1 with
  `{"blockers": ["Ritual data phase is not authorized."], "ready": false}` —
  the un-flipped flag still fails closed, as required.
