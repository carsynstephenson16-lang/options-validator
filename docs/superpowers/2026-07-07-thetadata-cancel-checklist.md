# ThetaData cancellation checklist (target: on/before 2026-07-25)

Plan pre-declared 2026-07-07 (ledger THETADATA_EXIT_PLAN). History is
complete and cached locally; nothing needs bulk-pulling. Each cached day
holds the FULL chain (every strike, every expiration), so the parked
enrichment ideas' raw material (IV term structure, event windows) is
derivable offline from the existing cache. The only ongoing need was daily
forward-window top-ups, which end at cancellation.

## On cancel day (run locally, in order)

1. `uv run python data/recent_topup.py` — one run catches ALL missing days
   since the last top-up (it blind-caches by explicit date; holidays and
   unfinalized days become logged CACHE_GAPs, never substituted data).
2. Confirm the tool prints `audit overall: PASS` or `PASS WITH WARNINGS`
   (the known-benign warning is deep-ITM |delta|=1 rows with IV<=0 — see
   ledger DATA_AUDIT 2026-07-06). Any other verdict: STOP, investigate
   before canceling.
3. Append a `THETADATA_CANCEL` line to `ledger/facts.log` recording the
   final cached day per symbol (MSFT/AMZN/VST/CEG).
4. Cancel the subscription in the ThetaData account portal.

## After cancellation

- Trigger watching needs NO chain data: `uv run python -m
  options_researcher.entry_watch` runs on free underlying closes
  (AlphaVantage) + the frozen cache. The chain-staleness note in its output
  is expected and honest.
- The scanner CLIs keep working against the frozen cache (as-of dates shown
  on every card).
- When a trigger FIREs: re-subscribe for ONE month, run the top-up +
  data-audit, evaluate the entry with fresh audited chains, then decide
  whether ongoing chain data is worth paying for during the holding period
  (actual short-call cadence is monthly; broker quotes are free at
  execution time).
