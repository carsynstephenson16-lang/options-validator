# RQ1 runner adversarial review — 2026-07-23

**Scope:** `options_researcher/rq1_runner.py` and
`tests/test_rq1_runner.py`, before the single registered RQ1 run.

## Result: PASS for one descriptive run

The runner stays inside the queue contract:

- It reconstructs the pre-badge card surface from the existing card builders.
  New badges, rates, dividends, triggers, and ranking weights are not imported.
- Each board row uses the feature row at or before its board date. A future
  feature row, synthetic row, or explicitly lookahead-contaminated row is
  excluded and counted rather than converted to a score.
- The per-name rank is a deterministic **best available pre-badge card
  GREEN-fraction** score. Each card keeps UNKNOWN grades in its denominator;
  this is fail-closed and has no tunable threshold.
- Forward realized volatility is computed from adjusted closes over returns
  t+1 through t+21, so the signal-day return cannot leak into its outcome.
  Forward IV change is measured from the same 21-session feature horizon.
- Pooled Spearman values and cross-sectional day summaries are descriptive;
  `|rho| >= 0.30` is only the registered notable-effect flag. The report emits
  no verdict, promotion, trade, trigger, or probability.
- The report is created with an exclusive write. A second run refuses before
  calling its data loader. Ledger publication uses the typed
  `retrospective_result` API only when `--execute` is supplied.
- The default path is cache-only and has no order or network surface.

## Tests and review probes

- Pure metric tests pin rank-based correlation and the t+1..t+21 outcome
  window.
- Causality tests pin future-row and synthetic-row exclusion.
- One-run tests pin refusal before data loading and deterministic summary
  output.
- Ruff passes on the runner and focused changes.

## Limitations carried into the report

This is an historical, outcome-selected scanner description. It is not a
holdout, does not establish edge, and cannot promote a badge. The report will
also disclose usable-row counts and gaps; names or dates without a complete
causal board/outcome pair are absent, not filled with zero.

**Run authorization:** this review authorizes exactly one RQ1 descriptive run
against the frozen pre-badge recipe. It does not authorize any later rerun,
ranking change, trigger, or live/paper order.
