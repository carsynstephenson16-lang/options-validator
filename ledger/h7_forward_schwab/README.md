# H7 forward Schwab event ledger

This directory is the reserved, currently **VALID-EMPTY** store for namespace
`h7-forward-schwab-v1`. It is separate from the immutable old
`ledger/h7_forward/` chain.

Until the owner types the operative registration through the guarded API, this
directory must contain no `events.jsonl` and no `HEAD`. Once registered, those
files are append-only and may be written only by
`options_researcher.h7_event_ledger.append_event`; hand edits are blocked by
`.agents/hooks/block_ledger_edits.py`.

The event vocabulary and hash-chain format are exactly those implemented by
`options_researcher.h7_event_ledger`. Registration or existence of this store
does not authorize live trading and does not activate H7 authority switches.
