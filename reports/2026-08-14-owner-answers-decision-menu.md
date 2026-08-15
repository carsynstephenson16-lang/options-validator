# Owner decisions — six-item menu answers (2026-08-14, ~23:00 ET)

**Owner wording (in-session, verbatim):** "1.b 2.c lets use 7 as well but i
want to watch it fire i want all these different pathways to be running while
i monitor. 3. 3. i want it to be automatic then do whatevers most optimal at
the most otpimal times . whther that be it pulling when i ask it to pull up
dashboard or distinctly pulling at 3 different times per day. 4. a 5. i want
it displayed explain why that wouldve killed the live panel. 6. cap it at
16k. these are my answers to your questions if you disagree explain why then
implement and lets commit and push"

Menu presented in the same session (drill disposition / H7 design / source-bar
sub-fork / alignment check / short-interest display / $16k ruling).

## Rulings recorded

1. **Drill disposition = B** ("record the invalidation, then accept recorded
   invalidations", per
   `reports/h7_forward_schwab/2026-08-14-backup-drill-failure-receipt.md`).
   Requires its own spec + independent adversarial review (receipt's own
   terms); owner sign-off is THIS record. Landing B through review unblocks
   H7 registration.
2. **H7 design = (c) lower the loss bar; MIN loss bar = 7 (owner-typed
   in-session).** Feasibility gate math changes to 2×7 = 14 expected
   entries; the registration packet must quote the computed expectation for
   the registered cohort and, if it falls short of 14, carry the explicit
   pre-accept disclosure (gate's OR-branch, H10 precedent). Owner intent
   noted verbatim: wants to WATCH the lanes fire and monitor all pathways.
   Honest sequencing acknowledged in-session: displays now; fire-capable
   watch lanes only after (i) disposition B lands, (ii) S1's three clean
   sessions (earliest ≈ 2026-08-19), (iii) registration lands.
3. **Source-bar sub-fork = 3a (automatic provenance).** The capture receipt
   gains an `invocation_source` field ("launchd" / "manual") set from a
   plist-set environment marker — a hashed `options_researcher/` change,
   batched into the current §11 regime-1 landing window. Capture cadence:
   owner delegates timing optimization; standing cadence retained (5 intraday
   quote snapshots + 15:45 pre-close full chain — already at the "3 different
   times per day or better" ask); dashboards rebuild on demand from the
   newest verified capture (no ad-hoc provider pulls outside the scheduled
   sessions — the deferred 10:00-capture spec owns any cadence change).
4. **D-6 = (a): scheduled pre-15:45 alignment check.** New plist + check
   script. `launchctl bootstrap` is an OWNER step (classifier denies agents);
   the exact command ships with the implementation.
5. **Short-interest display = ON** (`SHORT_CONTEXT_ENABLED=True`).
   Owner accepts the explained cost: the config-fingerprint change makes
   existing capture receipts mismatch, so the live panel's intraday section
   refuses until Monday 09:31's first new receipt. Weekend-degraded,
   self-healing. The "disabled by default" clause of the 2026-08-09
   experiment authorization is superseded for this flag by this owner
   directive; any test asserting the default-off artifact is amended with
   this provenance.
6. **$16k ruling = INTENTIONAL (cap stays 16,000).** Owner wording "cap it
   at 16k" interpreted as: the existing
   `H4_THESIS_MAX_PREMIUM_TOTAL = 16_000` stands, structurally exceeding
   `RISK_SLEEVE = 14_000`, accepted. Interpretation flagged to the owner
   in-session (if "cap to sleeve" was meant, a follow-up ruling corrects
   this). Dormant in practice (no LEAPS open). Formal chained-ledger
   recording follows the amendment path; this record is the decision
   provenance.

## Sequencing consequences

- Brief 12 (display freshness) proceeds under its amended spec (implementer
  blockers + independent audit findings folded in first).
- Disposition-B spec + implementation + review: tonight's second work order.
- Registration packet (loss bar 7): drafted after B is in flight; the
  registration EVENT stays blocked until B lands and remains subject to the
  feasibility-gate disclosure above.
- Items 3a, 4, 5 land tonight; 3a batched with the hashed landing window.
