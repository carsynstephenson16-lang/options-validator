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
  --completed-session YYYY-MM-DD
```

Stage 8 remains closed. The only real-store writer is
`tools/h7_manual_activate.py`; it requires the literal confirmation token,
owner fields, independent review, a valid empty ledger, current 15-name
receipts, a fresh verified restore, and a clean source tree. Do not run it as
part of routine refresh or repair verification.
