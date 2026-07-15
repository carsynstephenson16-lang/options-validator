#!/usr/bin/env python3
"""PreToolUse guard: block hand-edits to append-only / hash-chained ledger files.

RECONSTRUCTED 2026-07-15 by Claude. The original was registered in
.claude/settings.local.json but the script file was missing, which made the
hook fail closed on every Bash/Write/Edit call (python3 exits 2 on a missing
file). Rules below are reconstructed from the repo's documented policy
(CLAUDE.md, ledger/README.md): owner should review and adjust.

Policy enforced:
  - Hash-chained files (ledger/experiments.jsonl, ledger/HEAD,
    ledger/h7_forward/events.jsonl, ledger/h7_forward/HEAD): NEVER hand-edit,
    never mutate via shell. Append only via the typed Python API
    (research/ledger.py / the h7_event_ledger API).
  - ledger/facts.log: append-only. Shell '>>' appends are allowed; overwrite,
    in-place edit, delete, or whole-file Write/Edit are blocked.

Conventions match .claude/hooks/block_live_trading.py: JSON on stdin,
exit 2 + stderr message to block, exit 0 to allow, FAIL-CLOSED on parse error.
"""
import json
import re
import sys

HOOK = "block_ledger_edits"

CHAINED = (
    "ledger/experiments.jsonl",
    "ledger/HEAD",
    "ledger/h7_forward/events.jsonl",
    "ledger/h7_forward/HEAD",
)
FACTS = "ledger/facts.log"


def block(msg: str) -> None:
    print(f"BLOCKED by {HOOK} hook: {msg}", file=sys.stderr)
    sys.exit(2)


try:
    d = json.load(sys.stdin)
except Exception:
    # FAIL-CLOSED: if input can't be parsed, block rather than guess.
    block("could not parse tool input JSON (fail-closed)")

tool = d.get("tool_name", "")
tool_input = d.get("tool_input", {}) or {}

if tool in ("Write", "Edit", "NotebookEdit"):
    path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
    for p in CHAINED:
        if p in path:
            block(
                f"direct {tool} of hash-chained ledger file '{p}'. "
                "Append only via the typed Python API; a hand edit breaks the "
                "hash chain and verify will refuse."
            )
    if FACTS in path:
        block(
            f"whole-file {tool} of append-only {FACTS}. "
            "Append new lines via shell '>>' or the facts API; never rewrite."
        )
elif tool == "Bash":
    cmd = str(tool_input.get("command") or "")
    chained_hits = [p for p in CHAINED if p in cmd]
    if chained_hits and re.search(
        r"(>>?|\bsed\s+-i|\btee\b|\brm\b|\bmv\b|\bcp\b|\btruncate\b|\bperl\s+-i)", cmd
    ):
        block(
            f"shell mutation touching hash-chained ledger file(s) {chained_hits}. "
            "Append only via the typed Python API. (Reads without redirects are allowed; "
            "if this is a false positive, read the file with the Read tool instead.)"
        )
    if FACTS in cmd and re.search(
        r"((?<!>)>\s*\S*ledger/facts\.log|\bsed\s+-i|\btruncate\b"
        r"|\brm\b[^|;&]*ledger/facts\.log|\bmv\b[^|;&]*ledger/facts\.log"
        r"|\bcp\b[^|;&]*\sledger/facts\.log)",
        cmd,
    ):
        block(
            f"overwrite/in-place-edit/delete of append-only {FACTS} "
            "('>>' append is allowed)."
        )

sys.exit(0)
