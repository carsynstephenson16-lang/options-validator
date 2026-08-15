# Owner directive record — Schwab freshness + gate unfreeze (2026-08-14, late)

**Owner wording (in-session, 2026-08-14 ~22:15 ET):** "scope and implement
the charles schwab implementation path as well as fix the dashboard for the
newest data localhost:8766/attractiveness.html and unfreeze all gates that
can be unfrozen for example the qm and other ideas. i dont care abt et and
usar just all the other tickers i cached for"

Recorded by the orchestrating session. Interpretation presented back to the
owner in the same session; scope spec to follow as a dated plan doc.

## Scope adopted

1. **Display-layer Schwab freshness (implements tonight):** the
   attractiveness scanner, QM context, and dashboards gain a read path to
   the NEWEST verified Schwab capture session, so their staleness gates
   unfreeze by *seeing fresh data* — no gate is deleted or loosened.
   Honest timing semantics: every consumer of the new path labels data as
   "15:45 pre-close (Schwab)" — never as an end-of-day close.
2. **Name scope (owner-directed):** the capture cohort MINUS ET and USAR —
   i.e. AMD, AMZN, AVGO, CEG, CRWV, IREN, MSFT, NOW, NVDA, PLTR, SMCI,
   TEM, VST. This exclusion applies to the NEW display path only; it does
   not and cannot remove ET from the registered H7 9-name cohort (that
   would be a registration amendment, not directed here).
3. **"Unfreeze all gates that can be unfrozen":** read as data-gates whose
   blocking condition is staleness that fresh captures genuinely cure
   (scanner staleness banner, card DATA_BLOCKED, QM quote/context gates).

## Explicitly NOT unfrozen tonight, and why (each has a named key)

- `exact_session_source_active` — the S1 bar the owner ratified earlier
  tonight requires THREE consecutive verifying scheduled sessions; only
  one exists (2026-08-14). Earliest honest flip ≈ 2026-08-19 after the
  Mon/Tue/Wed captures. Flipping tonight would violate a bar ratified two
  hours ago.
- `h7_active` — registration day only; Group-2 items (variant pick, frozen
  numbers, feasibility receipt) remain owner-open.
- Closes store `.cache/underlying` — its refresh is the subject of the
  2026-08-14 drill-RED receipt; unfreezing awaits the owner's disposition
  (A/B). Fresh-capture display does not touch it.
- H5/H6/H8/H10 registered inputs — feeding capture data to the hypothesis
  WATCHERS is a per-hypothesis registered-input amendment (spec §4 Option A
  reasons 2-3), draftable under the 2026-07-25 delegation with adversarial
  review, but it is a separate later phase, not tonight's display work.
  D-1=F1 (recorded earlier tonight) keeps those lanes off in the ritual.

## Constraints inherited (unchanged)

No look-ahead; conservative quotes (mid or worse framing in any derived
number); no network at render time (captures are upstream; consumers read
local parquet); OD-2/OD-4 stand (`.cache/chains` is never refilled); no
verdict authority, FIRE authority, or registered-signal status for anything
this arc emits without its own future registration.
