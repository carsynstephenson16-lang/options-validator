# A2-v1 entry-convention addendum

**Status (corrected 2026-08-31):** pending owner ratification via an
owner-typed `A2_ENTRY_CONVENTION_RATIFIED_V1` fact
(`source=reports/2026-08-31-a2-entry-convention-ratification-receipt.md`).
The previous status line here ("owner-approved … on 2026-08-15") repeated a
claim the ledger has voided: the `A2_ENTRY_CONVENTION_ADDENDUM_V1` fact of
2026-08-15 was agent-authored without an owner-approval receipt and is void
as an approval record per `A2_ENTRY_CONVENTION_CORRECTION_V1` (2026-08-30).
This addendum does not change the frozen GREEN-fraction ranking, exits,
costs, horizons, bucket split, inference, or claim authority in ledger
sequence 19 (as amended by seq 27 and seq 31).

*Correction provenance:* required changes 1–4 of the independent adversarial
audit of 2026-08-31 (Opus; receipt above), applied under the owner-delegated
standing 2026-07-25 with the owner's in-session O2 ruling ("approve · audit
the docs"); owner veto by further append-only amendment.

## Historical entry convention

Signals use the frozen pre-badge GREEN-fraction reconstruction. An eligible
signal on session `t` enters at the next available trading-session close
(`t+1`), and requires that exact session's chain — selection never slides
forward to a later session's chain. Contract ties are resolved
deterministically by expiration, strike, right, and contract symbol after
applying the selector's distance ordering.

**Liquidity-filtered selection disclosure (audit D1, 2026-08-31):** in every
lane the expiration/contract is chosen from the liquidity-FILTERED chain
(open interest ≥ `config.MIN_OPEN_INTEREST`, spread ≤ `config.MAX_SPREAD_PCT`
applied first), not the raw chain. Where a name's front monthly has no
passing contract, selection therefore takes the next monthly — so selected
tenor can drift longer for less-liquid names, and less-liquid names may
correlate with ranking position. This is a deliberate, realistic convention
(an untradeable contract is not an opportunity), but it means tenor is not
held constant across buckets; a per-bucket selected-DTE distribution in the
report is the recorded follow-up for making this visible.

- **CSP:** use the sell-put candidate nearest `config.H5_INCOME_DELTA`.
  Resolve the five registered exit arms separately: 50% credit capture,
  close at 21 DTE, fixed 10 trading sessions (expiration settlement first,
  per `RQ2_A2_PIN_ADDENDUM_V1` clause (i)), the breach-defensive arm, and
  assignment-accepting. **Breach-arm definition:** as amended by ledger
  seq 31 — `docs/superpowers/specs/2026-08-15-a2-breach-weekly-cohort-amendment.md`
  Definition 1 controls (first strictly-below-strike underlying close on
  `[entry, expiry]`; exit at `max(first session at-or-below 21 DTE,
  breach+1)`; breach on the expiration session settles that session as a
  separately counted terminal exception; the no-breach branch holds to
  expiration settlement). Any shorthand elsewhere in this document defers to
  that definition.
- **Covered call:** use the covered-call candidate nearest
  `config.H5_INCOME_DELTA` against a hypothetical 100-share lot acquired at
  the same `t+1` close. The stock-only result from that identical lot is the
  benchmark; the option, stock, combined, combined-minus-stock-only,
  assignment, and lost-upside fields remain separate. *Acknowledged
  (audit item 5):* the CC exit rule — hold to expiration settlement, single
  commission and entry-side half-spread only on the settled leg — exists in
  code (`options_researcher/a2_panel.py`) and is not pinned by any
  registration; this ratification records awareness, not a pin.
- **PMCC:** historical status is `no data`, unconditionally — the
  implementation never consults recorded positions and no synthetic long leg
  or reconstructed holdings are permitted (audit D5: the earlier "until a
  real recorded LEAPS position exists" conditional described intent, not the
  code; `no data` is permanent for the historical pass).
- **LEAPS:** use `a2_panel.select_leaps_contract` at
  `config.H4_THESIS_DELTA`. *Correction (audit D2):* this is a dedicated
  selector, not the `_leaps_candidate` helper the earlier text named. Two
  deviations from `_leaps_candidate`: (i) it adds the liquidity gate
  (stricter); (ii) it filters to in-band-delta liquid rows before choosing
  the expiry nearest 365 days, so it can select a further-from-365 expiry in
  cases where `_leaps_candidate` would return nothing.
- **Tactical call:** use the short-dated call candidate nearest
  `config.H4_TACTICAL_DELTA`. *Acknowledged (audit item 5):* the 15–60 DTE
  monthly-only tenor window matches the repo's `nearest_monthly` convention
  but is presently a code literal, not a config constant; recorded follow-up.

Every lane uses the registered adverse entry and exit quote conventions,
commission per contract/leg/side, liquidity checks at entry and resolution,
and explicit skip reasons for missing inputs. A roll is a close of trade 1
plus a separately costed opening of trade 2 (no lane in the current
implementation rolls; the clause is retained for completeness).

## Acknowledged agent-derived threshold (audit item 5)

`MIN_TERCILE_COHORT_SIZE = BUCKET_COUNT` (= 3) in
`options_researcher/a2_battery.py` — the minimum entry-time board size for a
week to be a candidate and the minimum resolved cohort — is a derived,
disclosed, agent-created floor (it makes an existing implicit drop explicit
and counted). No owner typed it. It is acknowledged here, not pinned;
promotion of any A2-derived capability would need it owner-ruled.

## Effect of ratification (audit item 6)

Ratifying this document changes nothing operationally. The historical pass
remains blocked on the IV unblock criterion, the un-appended Definition-2.4
feasibility projection, and the owner-typed ratification fact itself; the
pass is one-shot and untimed, and "never run — data blocked" remains a
legitimate terminal state. Ratification is a statement that these
conventions are the ones the owner stands behind — not an authorization to
run.

**Governance note (audit item 7):** `validate_governance` still checks for
the byte-exact `A2_ENTRY_CONVENTION_ADDENDUM_V1` payload of 2026-08-15.
That line is void as an APPROVAL record (per the correction fact) but is
retained by the gate deliberately as an exact-content pointer to the
convention text this document describes; approval authority lives solely in
the owner-typed `A2_ENTRY_CONVENTION_RATIFIED_V1` fact. This dependence is
recorded here intentionally rather than silently.

## Authority and unresolved forward fields

The historical pass is a one-run, Card-3-class exploratory diagnostic. It
cannot produce a PASS, promotion, production recommendation, ranking change,
paper-book mutation, or forward verdict.

A2-specific forward dates, the forward adverse-gate adjudication vocabulary,
and any future PMCC synthetic-position convention remain unpinned. Forward
capture and verdict code must refuse until those fields are owner-approved in
a later registration amendment.
