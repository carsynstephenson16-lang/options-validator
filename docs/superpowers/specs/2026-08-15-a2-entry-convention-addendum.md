# A2-v1 entry-convention addendum

**Status:** owner-approved pre-result completion of the A2-v1 historical
entry convention on 2026-08-15. This addendum does not change the frozen
GREEN-fraction ranking, exits, costs, horizons, bucket split, inference, or
claim authority in ledger sequence 19.

## Historical entry convention

Signals use the frozen pre-badge GREEN-fraction reconstruction. An eligible
signal on session `t` enters at the next available trading-session close
(`t+1`). Contract ties are resolved deterministically by expiration, strike,
right, and contract symbol after applying the existing selector's distance
ordering.

- **CSP:** use the existing sell-put candidate nearest
  `config.H5_INCOME_DELTA`. Resolve the five registered exit arms separately:
  50% credit capture, close at 21 DTE, fixed 10 trading sessions (expiration
  settlement first), breach then hold to 21 DTE and close, and
  assignment-accepting.
- **Covered call:** use the existing covered-call candidate nearest
  `config.H5_INCOME_DELTA` against a hypothetical 100-share lot acquired at
  the same `t+1` close. The stock-only result from that identical lot is the
  benchmark; the option, stock, combined, combined-minus-stock-only,
  assignment, and lost-upside fields remain separate.
- **PMCC:** historical status is `no data` until a real recorded LEAPS
  position exists. No synthetic long leg or reconstructed holdings are
  permitted.
- **LEAPS:** use the existing `_leaps_candidate` selector at
  `config.H4_THESIS_DELTA`.
- **Tactical call:** use the existing short-dated call candidate nearest
  `config.H4_TACTICAL_DELTA`.

Every lane uses the registered adverse entry and exit quote conventions,
commission per contract/leg/side, liquidity checks at entry and resolution,
and explicit skip reasons for missing inputs. A roll is a close of trade 1
plus a separately costed opening of trade 2.

## Authority and unresolved forward fields

The historical pass is a one-run, Card-3-class exploratory diagnostic. It
cannot produce a PASS, promotion, production recommendation, ranking change,
paper-book mutation, or forward verdict.

A2-specific forward dates, the forward adverse-gate adjudication vocabulary,
and any future PMCC synthetic-position convention remain unpinned. Forward
capture and verdict code must refuse until those fields are owner-approved in
a later registration amendment.

