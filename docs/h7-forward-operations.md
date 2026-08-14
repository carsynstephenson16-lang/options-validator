# H7 forward repair operations

The official scope is `h7-forward-15-v1`. Its names and hash are recorded in
every current H7 receipt. Reports from the former 12-name scope remain
historical and cannot satisfy the current watcher or activation checks.

The safe command order for one completed session is:

```text
source health -> data gate -> watcher
```

Source health writes a receipt. The data gate must be given that receipt and
writes its own receipt. The watcher must be given the successful data-gate
receipt; it rechecks every close and chain hash before it can show actionable
entries.

The refresh runner starts with four workers, retries only transport-shaped
failures, writes cache files atomically, and records a resumable task manifest.
Use `--manifest` to choose a run-specific manifest. No refresh command is
invoked by the data gate or watcher.

Backups use Restic. Set `RESTIC_REPOSITORY` and either
`RESTIC_PASSWORD_COMMAND` or `RESTIC_PASSWORD_FILE`; passwords are never
passed as command arguments. The backup allow-list includes H7 chains,
underlying closes, earnings stores, facts, manifests, receipts, and H7
reports. It excludes environment files, credentials, temporary files, and
unrelated caches.

The allow-list also includes the prepared Schwab restart paths:
`.cache/schwab_chains/`, `reports/schwab_chains/`,
`reports/h7_forward_schwab/`, and `ledger/h7_forward_schwab/`. A real restore
drill for that lane requires a verified live canary package; do not substitute
synthetic bytes for operational durability evidence.

```sh
uv run python tools/h7_forward_backup.py backup \
  --completed-session YYYY-MM-DD
uv run python tools/h7_forward_backup.py restore-check \
  --backup-receipt <path of the backup receipt written by the command above> \
  --completed-session YYYY-MM-DD
```

`restore-check` no longer accepts `--snapshot latest` (hardening, 2026-08-14).
`--backup-receipt` is REQUIRED: the tool reads that receipt, restores the exact
`snapshot_id` it names, and refuses unless the restored inventory equals the
receipt's `input_files` exactly. `--snapshot` is now optional and only asserts
that the caller's expected id matches the receipt's; a mismatch is refused.
"Latest" was never durability evidence — it can silently resolve to a different
snapshot than the one being attested.

Stage 8 remains closed. The only real-store writer is
`tools/h7_manual_activate.py`; it requires the literal confirmation token,
owner fields, independent review, a valid empty ledger, current 15-name
receipts, a fresh verified restore, and a clean source tree. Do not run it as
part of routine refresh or repair verification.

## Preclose Schwab chain capture (audit M7)

`tools/schwab_chain_capture.sh` runs `options_researcher.schwab_chain_capture`
once, intended for 15:45 ET on weekdays via its own (currently uninstalled,
`RunAtLoad=false`) LaunchAgent template. Read-only; never trades; independent
of the display-only intraday capture lane.

**Same-day-retry constraint.** Each run refetches the WHOLE watch universe
live in one pass -- there is no per-symbol resume. Both the per-symbol
parquet writes and the session-level receipt are immutable:
`_write_parquet_once` refuses to overwrite an existing file unless the new
bytes hash-match it exactly, and `_write_receipt` is first-write-wins for the
session (a second write for the same session must be byte-identical text or
it is refused). Live market data and the receipt's own wall-clock timestamp
fields (`captured_at_et` / `captured_at_utc`) differ between any two
invocations, so in practice a session's receipt can be durably completed in
only **one atomic run per day**:

- A first run that succeeds completely writes the session's receipt once;
  that receipt is now locked for the day.
- A first run that fails partially (some symbols captured, some not) still
  writes a `failed` receipt. A second run the same day does **not** pick up
  where the first left off and fill the gap -- it refetches everything live,
  which will very likely produce different bytes for the already-captured
  symbols (hash mismatch -> refused) and a different receipt text (refused ->
  `RECEIPT CONFLICT`, exit 2) rather than a completed session.
- Bottom line: treat a partial or failed preclose day as needing **explicit
  operator handling** (accept the gap for that session, or otherwise
  investigate before touching anything under `.cache/schwab_chains/` or
  `reports/schwab_chains/`) -- never as "just re-run the wrapper." A blind
  same-day re-run is the wrong reflex and will usually just add a
  `RECEIPT CONFLICT` on top of the original problem.

The wrapper's own failure-taxonomy mirrors the intraday lane: it classifies a
nonzero exit from evidence in the module's printed output (never the exit
code alone, since exit 2 is shared between a genuine receipt conflict and an
unrelated argparse usage error) into `SCHWAB REAUTH REQUIRED` (expired Schwab
refresh token), `SCHWAB CHAIN REFUSED` (outside the regular session or
preclose timing tolerance), `SCHWAB CHAIN RECEIPT CONFLICT`, a partial
per-symbol `SCHWAB CHAIN PARTIAL FAILURE`, or a generic unrecognized-failure
fallback -- and fires a single `osascript` desktop notification (a silent
no-op off macOS) summarizing the result either way.
