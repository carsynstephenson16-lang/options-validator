# Options Validator Repository Audit - Preflight and Protected WIP

**Captured:** 2026-08-25 14:03 America/New_York
**Canonical checkout:** `/Users/carsynstephenson/options-validator`
**Audit worktree:** `/Users/carsynstephenson/options-validator/.tmp/worktrees/2026-08-25-1403-options-validator-audit`
**Audit branch:** `codex/options-validator-audit-20260825-1403`
**Verified default branch:** `main`
**Starting SHA:** `c9e74ccd05e4ecdd0de8de6f35bef714bc6f1771`
**Protected-path count:** 136
**Canonical sorted-list SHA-256:** `7c679ddef884e9ec63794818dcba5586ef9d524bfeea9f2ccd86145c9efa937e`

## Rulings

- The prompt's sibling worktree path is a preference. The repository's newer owner-directed rule requires `.tmp/worktrees/<short-name>`, so the audit uses the repository-local ignored worktree path.
- The supplied vault name `options-validator` resolves through Obsidian's registry to `/Users/carsynstephenson/options-validator`, which is also the canonical Git root.
- The canonical checkout was clean, but its branch contains active work relative to `main`; those changed paths are protected.
- Files changed by any open pull request, active worktree branch, active SDD ledger, or dirty/untracked worktree state are protected. Findings overlapping these paths are plan-only.

## Git and environment evidence

- Canonical checkout branch/HEAD: `claude/codex-handoff-plan-2026-08-22` at `915e303cd8a694b8cea91525bb87d44fc325e747`.
- Canonical checkout status: clean.
- Git identity: configured (values intentionally omitted).
- Default branch resolution: GitHub, local `main`, `origin/main`, and `git ls-remote origin refs/heads/main` all identified `c9e74ccd05e4ecdd0de8de6f35bef714bc6f1771`.
- Runtime visible on the host: Python 3.14.4 and uv 0.11.29. Repository commands remain bound to the existing locked project environment and Python 3.12 policy.
- GitHub coverage: six open pull requests were visible at capture time: #77, #76, #75, #71, #70, and #61. Checks were green for #77, #76, #75, and #70; #71 and #61 had no current checks and reported dirty merge state.
- Obsidian registry: vault `options-validator` is registered and open at the canonical checkout.

## Dirty or untracked operational evidence

The canonical checkout was clean. The sanctioned ops worktree contained seven untracked operational receipts, all protected:

```text
reports/h7_data_gate/h7-forward-15-v1/2026-08-21.json
reports/h7_data_gate/h7-forward-15-v1/receipts/2026-08-21.json
reports/h7_receipts/h7-forward-15-v1/source_health/2026-08-21.json
reports/intraday_capture/2026-08-25/midday.json
reports/intraday_capture/2026-08-25/midmorning.json
reports/intraday_capture/2026-08-25/open.json
reports/intraday_capture/2026-08-25/open_auction.json
```

## Protected path inventory

The canonical sorted inventory used for the hash is grouped below. Every listed path is read-only for this audit.

### Active ledgers and governance

```text
.superpowers/sdd/2026-08-24-24-repo-reconcile-redeploy-codex-brief/progress.md
.superpowers/sdd/h7-schwab-recovery-plan/progress.md
.superpowers/sdd/h7-schwab-recovery-plan/task-2-report.md
.superpowers/sdd/pasted-text.txt/progress.md
CLAUDE.md
config.py
ledger/facts.log
pyrightconfig.json
```

### Data and provider work

```text
data/earnings/assertions_v2.csv
data/earnings/gating_v3.csv
data/events/fomc_pit.csv
data/events/fomc_pit.provenance.md
data/rates.py
docs/provider-transition.md
```

### Plans, specs, reviews, and reports

```text
docs/plans/2026-08-24-options-validator-research-integration-plan.md
docs/plans/2026-08-25-research-integration-plan-verification-addendum.md
docs/superpowers/2026-07-17-qm-dashboard-remediation-addendum.md
docs/superpowers/plans/2026-08-11-vst-post-earnings-analyst-review.md
docs/superpowers/plans/2026-08-15-a2-outcome-battery.md
docs/superpowers/plans/2026-08-24-22-chain-consistency-flags-codex-brief.md
docs/superpowers/plans/2026-08-24-23-slippage-haircut-calibration-codex-brief.md
docs/superpowers/plans/2026-08-24-24-repo-reconcile-redeploy-codex-brief.md
docs/superpowers/plans/2026-08-25-25-market-context-signal-lane-codex-brief.md
docs/superpowers/plans/2026-08-25-26-board-declutter-top5-codex-brief.md
docs/superpowers/plans/2026-08-25-27-pick-tracker-scoreboard-codex-brief.md
docs/superpowers/reviews/2026-08-15-a2-final-branch-review.md
docs/superpowers/reviews/2026-08-15-a2-runner-adversarial-review.md
docs/superpowers/specs/2026-08-10-vst-post-earnings-analyst-review-design.md
docs/superpowers/specs/2026-08-11-options-validator-core-plugin-design.md
docs/superpowers/specs/2026-08-11-options-validator-plugin-program-design.md
docs/superpowers/specs/2026-08-11-options-validator-sentry-plugin-design.md
docs/superpowers/specs/2026-08-11-options-validator-zotero-plugin-design.md
docs/superpowers/specs/2026-08-15-a2-breach-weekly-cohort-amendment.md
docs/superpowers/specs/2026-08-15-a2-entry-convention-addendum.md
reports/2026-08-15-a2-entry-convention-validation.md
reports/2026-08-15-a2-options-data-audit.md
reports/2026-08-15-a2-realism-audit.md
reports/2026-08-15-branch-cleanup-batch.md
reports/2026-08-15-evidence-receipt-durability-proposal.md
reports/2026-08-25-briefs-25-27-adversarial-review-receipt.md
reports/fill_calibration/2026-08-24-fill-adversity-context-4614cb4238d5.json
reports/fill_calibration/2026-08-24-fill-adversity-context-5c52893cae57.json
reports/fill_calibration/2026-08-24-fill-adversity-context-b6191b02abee.json
reports/fill_calibration/2026-08-24-fill-adversity-context.md
reports/h7_data_gate/h7-forward-15-v1/2026-08-21.json
reports/h7_data_gate/h7-forward-15-v1/receipts/2026-08-21.json
reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md
reports/h7_forward_schwab/2026-08-11-feasibility-primary-earnings.json
reports/h7_forward_schwab/2026-08-11-primary-earnings-evidence.md
reports/h7_forward_schwab/2026-08-11-v2-arming-bottleneck-design.md
reports/h7_forward_schwab/2026-08-14-entry-redesign-variant-menu.md
reports/h7_forward_schwab/2026-08-15-registration-packet-bar7-draft.md
reports/h7_forward_schwab/2026-08-15-v9-cohort9-occupancy-followup.md
reports/h7_receipts/h7-forward-15-v1/source_health/2026-08-21.json
reports/intraday_capture/2026-08-25/midday.json
reports/intraday_capture/2026-08-25/midmorning.json
reports/intraday_capture/2026-08-25/open.json
reports/intraday_capture/2026-08-25/open_auction.json
reports/qm_context/2026-07-14.json
```

All files below `reports/h7_forward_schwab/variant-receipts/comparable_70_common/` and `reports/h7_forward_schwab/variant-receipts/deep_arming_census/` are protected. This covers the named V0-V17 JSON variants, the comparable `V9_LANE_A_OR_COHORT9.json`, and `_baseline_waterfall.json`.

### Source and tests

```text
options_researcher/__init__.py
options_researcher/a2_battery.py
options_researcher/a2_panel.py
options_researcher/a2_runner.py
options_researcher/attractiveness_dashboard.py
options_researcher/h7_activation_guard.py
options_researcher/h7_schwab_window_registration.py
options_researcher/hypothesis_evidence.py
options_researcher/qm_dashboard.py
options_researcher/schwab_chain_capture.py
tests/fixtures/top3_fixed_baseline_d5c241a.json
tests/test_a2_battery.py
tests/test_a2_panel.py
tests/test_a2_runner.py
tests/test_attractiveness_dashboard.py
tests/test_attractiveness_v3.py
tests/test_composite_signals.py
tests/test_daily_ritual_provenance.py
tests/test_experiments_baseline.py
tests/test_fill_haircut_calibration.py
tests/test_h7_backup.py
tests/test_h7_entry_variant_menu.py
tests/test_h7_one_door.py
tests/test_h7_schwab_manual_activate.py
tests/test_h7_schwab_window_registration.py
tests/test_hypothesis_evidence.py
tests/test_qm_dashboard.py
tests/test_rates.py
tests/test_ritual_switch_on_hash_containment.py
tests/test_schwab_chain_capture.py
tools/anti-stranding/repo-reconcile
tools/daily_ritual.sh
tools/fill_haircut_calibration.py
tools/h7_entry_variant_menu.py
tools/h7_entry_variant_menu_v9_cohort9.py
tools/h7_forward_backup.py
tools/h7_schwab_manual_activate.py
tools/launchagents/README.md
tools/launchagents/com.carsyn.options-validator.schwab-chain-preclose.plist
```

## Coverage limits

- GitHub state is a point-in-time snapshot from 2026-08-25; later PR changes are unexpected state for this run.
- Branch-relative file inventories use each active worktree's merge base with local `main`; they identify overlap, not ownership or merge readiness.
- Ignored cache contents were not enumerated into the protected-path hash because all cache and raw-evidence namespaces are globally non-mutable by the audit authorization.
