# Agent guard hooks (tracked)

Canonical, tested guard scripts for Claude Code PreToolUse hooks. The logic
lives here (tracked, covered by `tests/`), while the *registration* lives in
the local, gitignored `.claude/settings.local.json` — per this repo's policy
that `.claude/` is never committed.

## block_ledger_edits.py

Blocks writes to the append-only ledger chain files:

- `ledger/experiments.jsonl`, `ledger/HEAD` — research chain (`research/ledger.py`)
- `ledger/facts.log` — facts stream (`research/facts.py`)
- `ledger/h7_forward/events.jsonl`, `ledger/h7_forward/HEAD` — H7 chain
  (`h7_event_ledger.append_event`; must not be created before Stage 8)

**Coverage — read this before trusting it.** The guard is complete for the
agent's own file tools (Edit / Write / NotebookEdit, by `file_path` /
`notebook_path`). For **Bash it is a best-effort denylist**, not a sandbox: it
matches the common write forms only — `>`/`>>` redirects, `tee`, in-place
`sed -i`, `rm`/`mv`/`cp`/`touch`/`truncate`/`shred`/`unlink`/`ln`, and
`dd of=`. A write that goes through an unlisted interpreter or utility — e.g.
`python -c "open('ledger/facts.log','w')..."`, `perl`, `awk`, an editor — is
**not** caught and exits 0. The append-only guarantee that actually holds is
the hash chain plus `verify`; this hook is a fast tripwire against accidental
hand-edits, not a security boundary. Extend the Bash regex before relying on it
for anything stronger.

Reads and the typed-API CLIs stay allowed. Fail-closed on unparseable input.
Tests: `tests/test_block_ledger_edits.py`.

To register, add to `.claude/settings.local.json` under `hooks.PreToolUse`
(alongside the existing `block_live_trading.py` entry):

```json
{
  "matcher": "Bash|Write|Edit|NotebookEdit",
  "hooks": [
    {
      "type": "command",
      "command": "python3 \"$CLAUDE_PROJECT_DIR/.agents/hooks/block_ledger_edits.py\"",
      "timeout": 15,
      "statusMessage": "Checking for ledger hand-edits..."
    }
  ]
}
```

**Register only after the script is present on disk.** The hook fails closed:
if `settings.local.json` points at a `block_ledger_edits.py` that does not
exist, `python3` exits non-zero and the fail-closed contract blocks *every*
Bash/Write/Edit in every session on that checkout (this happened once, 2026-07-15;
recovery was restoring the script). Order of operations: land the script first,
add the registration entry last; when removing the hook, drop the registration
before deleting the script.
