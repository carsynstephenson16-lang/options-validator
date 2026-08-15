# A2 runner adversarial review — 2026-08-15

**Scope:** `options_researcher/a2_runner.py`, `options_researcher/a2_panel.py`,
`options_researcher/a2_battery.py`, their A2 tests, and the frozen A2 plan and
entry-convention addendum. This is a pre-run code review, not a historical
execution review.

## Result: APPROVED FOR GOVERNED HISTORICAL INVOCATION ONLY; NO-GO NOW

The reviewed implementation is approved as the code path for one governed,
research-only historical invocation after its external prerequisites are
satisfied. It is **not approved to run now**. No A2 historical command, report
write, facts append, or ledger append occurred as part of this review.

## Review findings resolved in the implementation

- The CLI requires explicit `--historical`, absolute paths for every local
  input, a reviewed realism grade, and an existing realism receipt. Its loader
  boundary has no network, broker, dashboard, paper-book, or scanner-ranking
  import.
- Registration/fact checks precede loading. The runner pins A2-v1 sequence 19,
  its record hash, the RQ2 pin fact, and the owner-approved entry-convention
  fact before it constructs local inputs.
- The ranking reconstruction uses the pre-badge card builders and
  `green_fraction`; it does not consume the spent four-name RQ1 report.
  Feature, earnings, and FOMC rows must be known at the decision-date close.
- A signal enters only at its exact next raw-close session and requires that
  session's chain. Missing entry/resolution inputs are excluded and counted;
  they are not forward-filled.
- Inference is restricted to complete 15-name boards with their original
  five/top, five/middle, five/bottom identities. Staggered rows are emitted
  separately and cannot supply inference p-values or Holm adjustment.
- The report uses exclusive creation and verifies its hash before an explicit
  retrospective-result append. A verified existing report may be used only to
  retry the requested missing append.
- The data audit is required before publication and a selected-contract audit
  failure blocks the report. PMCC remains the explicit `no data` lane when
  there is no real recorded LEAPS position.
- Report authority is constrained to `RESEARCH-ONLY / NO VERDICT`; unsupported
  forward fields are serialized rather than inferred.

## Preconditions still blocking the one historical invocation

1. Add the owner-approved entry-convention fact with
   `research.facts.append_fact`; do not hand-edit facts.
2. Supply a provenance-bearing point-in-time FOMC file. A legacy dates-only
   calendar is refused. This is a data/provenance execution blocker, not a
   simulation-quality judgment.
3. Run the programmatic A2 options-data audit on the actual selected
   contracts. Any `BLOCK` is a no-go.
4. Use the accompanying realism receipt and its reviewed grade. The receipt
   identifies remaining modeling limits; it does not authorize execution.
5. Obtain the required statistical red-team receipt after the report/result
   workflow, before discussing any apparent ranking outcome.

## Approval boundary

This review authorizes no run, rerun, report overwrite, facts change, ledger
change, promotion, ranking change, order, paper-book mutation, or forward
claim. Once every prerequisite above is satisfied, it authorizes at most the
registered one-shot A2 historical command under the frozen inputs and the
separate controller gate.
