# A2-v1 entry-convention ratification receipt — 2026-08-31

Owner rulings recorded this session (in chat, 2026-08-31 ~09:43 ET), on the
four decision items of `reports/2026-08-30-a2-battery-closeout.md`:
**O1** do nothing (seq-31 activation stands) · **O2** "approve · audit the
docs · come up with any other suggestions if needed" · **O3** do nothing
(data-blocked state persists) · **O4** "fresh pin fact then".

## Pre-ratification audit (O2 condition)

Independent adversarial audit, 2026-08-31 (Opus, fresh instance), of the
entry-convention addendum + validation report against the code on `main`
@6e08cf8 (re-verified byte-identical at audit time). Verdict: **NEEDS
CHANGES** on the document text; on substance, quote: no rigged,
favorable-side, or outcome-peeking convention found — fills adverse past the
touch both directions, liquidity re-checked at every resolution quote,
deterministic non-outcome tie-breaks, entry-time-only cohort candidacy. The
conventions survived the audit's look-ahead and adverse-fill checks (this is
not a claim any eventual result will be meaningful).

## Required changes — applied before ratification (this branch)

1. Addendum status line corrected: it had repeated the voided
   "owner-approved 2026-08-15" claim (`A2_ENTRY_CONVENTION_CORRECTION_V1`
   voided it); now states approval lives only in the owner-typed fact below.
   The `config.py` comment repeating the claim corrected likewise.
2. Breach-arm clause re-pointed at the active seq-31 Definition 1 (breach+1
   floor, expiry-session terminal exception, no-breach hold-to-settlement).
3. LEAPS clause corrected to `a2_panel.select_leaps_contract` with its two
   recorded deviations from `_leaps_candidate`.
4. Liquidity-filtered selection disclosure added (audit D1): expiries are
   chosen from the OI/spread-filtered chain, so selected tenor can drift
   longer for less-liquid names — the one convention the audit judged able
   to move the headline number for non-ranking reasons; per-bucket
   selected-DTE distribution recorded as follow-up.

## Acknowledgments recorded in the addendum (audit items 5–7)

- Three conventions exist only in code and are NOT pinned by this
  ratification: the covered-call hold-to-expiration exit; the tactical
  15–60 DTE monthly window (code literal, not config); and
  `MIN_TERCILE_COHORT_SIZE = 3` (the only agent-created frozen threshold in
  the stack).
- Ratification changes nothing operationally: the run stays blocked on the
  IV unblock criterion and the Definition-2.4 feasibility projection;
  "never run — data blocked" remains a legitimate terminal state.
- `validate_governance`'s check of the voided 2026-08-15 payload is retained
  deliberately as an exact-content pointer, never as approval authority.

## Non-blocking follow-ups (recorded, not implemented)

Per-bucket selected-DTE distribution in the report schema (audit R1); a
counter for capture-scan sessions with a missing chain (R4); move the
tactical 15/60 literals into `config.py`; retire or re-comment the stale
`A2_UNIVERSE` test pin (`tests/test_a2_panel.py`); footnote or drop the
inert roll clause. None gate ratification; all would gate any future
promotion of A2-derived capability.

## Resolved this session (O4)

Fresh `RQ2_A2_PIN_ADDENDUM_V1` fact appended 2026-08-31 (format-normalized
re-record carrying the `source=reports/2026-07-23-pin-addendum-validation.md`
token; no new value or authority; owner-directed in-session). The governance
gate now fails at the ratification fact — the intended lock.

## The ratification fact (owner-typed)

The owner appends exactly this payload via `research.facts.append_fact`
(the append is the owner's act; this receipt is its `source=` target):

```
A2_ENTRY_CONVENTION_RATIFIED_V1 owner-approved 2026-08-31 source=reports/2026-08-31-a2-entry-convention-ratification-receipt.md scope=historical-entry-conventions-as-corrected effect=none-operational run-remains-blocked=IV-unblock-criterion+feasibility-projection
```

Provenance labels: audit findings Repo-/Test-verified per its citations;
the fact-token format LLM-proposed (2026-08-30 governance re-key, owner veto
open); the ratification decision and keystroke owner-owned.
