---
paths:
  - "ledger/**"
  - "reports/h9/**"
  - "research/ledger.py"
  - "research/facts.py"
  - "options_researcher/h7_event_ledger.py"
---

# Ledger and permanent records

- `ledger/experiments.jsonl`, `ledger/HEAD`, and `ledger/h7_forward/{events.jsonl,HEAD}`
  are append-only hash chains. Write them ONLY through their typed APIs
  (`research/ledger.py`, `options_researcher/h7_event_ledger.py`). A hand edit
  breaks the chain and `verify` refuses. The `block_ledger_edits` hook enforces
  this; treat a hook block as correct.
- `ledger/facts.log` is append-only but NOT hash-chained (see `ledger/README.md`).
  It is advisory context, never verdict-feeding. Frozen numbers belong in the
  chained ledger.
- Wrong entries are never edited or deleted. The only repair is a new appended
  correction fact, and a correction fact requires: independent adversarial
  review of the exact text, then owner approval, then append. Draft pending
  review: `reports/strategy-evaluations/13_correction_facts_draft.md`.
- Known-wrong descriptive numbers (do not quote without the correction caveat):
  H1 seq 0 and H2 seq 3 `capital_efficiency` and `return_on_economic_max_loss`
  are inflated by exactly the trade count; H9 `max_drawdown` $361.30 was
  computed over an alphabetically sorted trade list (chronological value:
  $718.50). Verdicts (FAIL, FAIL, INSUFFICIENT_SAMPLE) are unaffected — the
  verdict function reads neither ratio.
- One-run experiments stay spent. H9's single allowed run is used; no refetch,
  rebuild, or v2 backfill authorizes another H9 result.
- The H7 forward window (registered 2026-07-20, sole event in
  `ledger/h7_forward/events.jsonl`) must not be retrofitted with new entry
  conventions; a different entry timing is a NEW hypothesis registration.
