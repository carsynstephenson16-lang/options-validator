# Agent guard hooks (tracked)

Canonical, tested guard scripts for Claude Code PreToolUse hooks. The logic
lives here (tracked, covered by `tests/`), while the *registration* lives in
the local, gitignored `.claude/settings.local.json` — per this repo's policy
that `.claude/` is never committed.

## block_ledger_edits.py

Blocks hand-edits (Edit/Write/NotebookEdit, and shell writes) to the
append-only ledger chain files:

- `ledger/experiments.jsonl`, `ledger/HEAD` — research chain (`research/ledger.py`)
- `ledger/facts.log` — facts stream (`research/facts.py`)
- `ledger/h7_forward/events.jsonl`, `ledger/h7_forward/HEAD` — H7 chain
  (`h7_event_ledger.append_event`; must not be created before Stage 8)

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
