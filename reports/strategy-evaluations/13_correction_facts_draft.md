# 13 — Correction fact for three permanent records: APPROVED, APPENDED ONCE

**Updated:** 2026-07-31
**Owner direction:** append only after the owner reads and approves the exact
text.
**Status:** owner approved the exact payload on 2026-07-31. It was appended
exactly once through `research.facts.append_fact` at
`2026-08-01T00:20:49.515344+00:00` with payload SHA-256
`c489eb179e230aa9554408066957feb17112fad47b151448f28d50a431bd10e8`.

The permanent correction must be append-only and must use
`research.facts.append_fact`. It changes descriptive metrics only; it does not
amend a registered parameter, threshold, window, outcome, spent state, or
reveal state.

## Independently verified corrections

- H1 seq 0: `capital_efficiency` −4510.21% → −19.96% and
  `return_on_economic_max_loss` −4442.93% → −19.66%.
- H2 seq 3: `capital_efficiency` −1835.34% → −9.36% and
  `return_on_economic_max_loss` −1823.97% → −9.31%.
- H9: `capital_efficiency` +1387.30% → +86.71%; its
  `return_on_economic_max_loss` remains NaN because its trades do not carry
  `economic_max_loss`.
- Commit `5626c3f` fixed the numeric economic-max-loss ratio to sum-over-sum
  and defined closed-trade drawdown as zero-anchored with stable
  `entry_date` ordering. The historical H9 receipt order produced $361.30;
  replay under the implemented definition produces $718.50. Exit-session
  aggregation produces $572.20, so it is not interchangeable with the
  implemented closed-trade measure.
- The stored H1/H2 in-sample scoreboard strings remain FAIL, but both OOS
  holdouts remain unrevealed. H9 remains `INSUFFICIENT_SAMPLE` (4 losses vs
  10 required), and its unresolved-gap gate did not trip (0 gaps).
- H1/H2 drawdowns cannot be recomputed because their per-trade lists are not
  present in the canonical repository. Their aggregate records do not prove
  whether anchoring or ordering affected their stored values.

## Exact reviewed correction text — owner approval required

```text
METRIC_CORRECTION 2026-07-31 (H1 seq 0, H2 seq 3, H9). CORRECTION: the legacy scoreboard divided total P&L by mean per-trade capital, and by mean economic max loss where that field was populated, instead of the corresponding sums. Each numeric affected ratio therefore had an absolute magnitude exactly n times the sum-denominator value. The capital calculation was replaced by trade_weighted_return_on_risk in commit 88ffbb6; the numeric return_on_economic_max_loss calculation and closed-trade drawdown ordering were corrected in commit 5626c3f. Algebraic corrections from the stored aggregates, exact under the historical formulas as recorded/n: H1 seq 0 (n=226) capital_efficiency -4510.21% -> -19.96% and return_on_economic_max_loss -4442.93% -> -19.66%; H2 seq 3 (n=196) capital_efficiency -1835.34% -> -9.36% and return_on_economic_max_loss -1823.97% -> -9.31%; H9 reports/h9/receipt.json (n=16) capital_efficiency +1387.30% -> +86.71%; H9 return_on_economic_max_loss remains NaN because its trades do not record economic_max_loss. OUTCOMES UNAFFECTED: the stored H1 and H2 in-sample scoreboard verdict strings remain FAIL; their OOS holdouts remain unrevealed, so this correction asserts no final OOS verdict. H9 remains INSUFFICIENT_SAMPLE because it recorded 4 losses versus the required 10 and its unresolved-gap gate did not trip; neither corrected ratio nor drawdown feeds those gates. H9 DRAWDOWN CORRECTION: the receipt trade array is ordered by symbol then event date, not by entry date, and the historical unanchored calculation over that receipt order produced $361.30. Commit 5626c3f defines closed_trade_pnl_drawdown as zero-anchored and stably ordered by entry_date; replaying H9's 16 stored trades under that implemented definition yields $718.50. Aggregating realized P&L by exit_fill_session yields $572.20, so $718.50 is specifically the implemented entry-date-ordered closed-trade value, not a daily-NAV or generic chronological drawdown. The wrong $361.30 value is also quoted in ledger/facts.log H9_RESULT at line 17892. H1 and H2 drawdowns are not corrected because no per-trade lists are present in the canonical repository; their aggregate records cannot determine whether zero anchoring or ordering affected those values. No registered parameter, threshold, window, outcome, spent state, or reveal state is changed by this descriptive fact. Provenance: agent-drafted under owner direction 2026-07-30; independently adversarially reviewed 2026-07-31; append remains owner-gated and must use research.facts.append_fact.
```

## Append gate

- [x] Numeric and semantic claims independently adversarially reviewed.
- [x] Draft updated to cite the fixing commit `5626c3f`.
- [x] Typed API accepts the `METRIC_CORRECTION` payload in an isolated
      temporary ledger; the hook blocks direct ledger writes, not this prefix.
- [x] Fresh Fable sign-off on this exact revision (`SIGN-OFF: PASS`, explicit
      `--model fable`, read-only, 2026-07-31). Fable independently reproduced
      every ratio, the $361.30/$718.50/$572.20 drawdowns, outcome gates, and
      OOS-state claims; it required no replacement payload.
- [x] Owner read and approved this exact one-line payload.
- [x] Appended once through `research.facts.append_fact`; duplicate count is one.
