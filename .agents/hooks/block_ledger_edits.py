#!/usr/bin/env python3
"""PreToolUse hook: blocks hand-edits to the append-only ledger chain files.

Protected files may ONLY be written through their typed Python APIs
(research/ledger.py, research/facts.py, options_researcher/h7_event_ledger.py).
A hand edit breaks the hash chain and `verify` refuses; the H7 forward files
must not even be created before Stage 8 activation.

Exit 2 = block the tool call; stderr is fed back to the agent as the reason.
FAIL-CLOSED: if input can't be parsed, block rather than guess.
Reads (cat/grep/git diff) and the typed-API CLI invocations are allowed.
"""
import json
import posixpath
import re
import sys

try:
    d = json.load(sys.stdin)
    ti = d.get("tool_input", {}) or {}
except Exception as e:  # noqa: BLE001 - safety hook fails closed on anything
    print(
        f"BLOCKED by block_ledger_edits hook: could not parse tool input ({e}). "
        f"Failing closed: the ledger is append-only via typed APIs.",
        file=sys.stderr,
    )
    sys.exit(2)

PROTECTED = (
    r"ledger/(?:HEAD\b|facts\.log|experiments\.jsonl"
    r"|h7_forward/(?:events\.jsonl|HEAD\b))"
)
PROTECTED_RE = re.compile(PROTECTED)

REASON = (
    "This file is part of the append-only ledger and may only be written "
    "through its typed Python API (research/ledger.py, research/facts.py, or "
    "options_researcher/h7_event_ledger.append_event). A hand edit breaks the "
    "hash chain and `verify` will refuse. ledger/h7_forward/{events.jsonl,HEAD} "
    "must not be created at all before Stage 8 activation."
)

# --- File tools: any direct Edit/Write/NotebookEdit on a protected path ---
for key in ("file_path", "notebook_path"):
    path = str(ti.get(key, ""))
    if path and PROTECTED_RE.search(posixpath.normpath(path.replace("\\", "/"))):
        print(
            f"BLOCKED by block_ledger_edits hook ({key}='{path}'). {REASON}",
            file=sys.stderr,
        )
        sys.exit(2)

# --- Bash: block write operations that name a protected path; allow reads ---
# A segment boundary [^|;&]* keeps the write verb and the target in the same
# pipeline segment, so `cat ledger/facts.log | grep x` stays allowed.
BASH_WRITE_RE = re.compile(
    r"(?:>>?\s*\S*" + PROTECTED + r")"  # > or >> redirect into the file
    r"|(?:\btee\b[^|;&]*" + PROTECTED + r")"  # tee / tee -a
    r"|(?:\bsed\b[^|;&]*\s-i[^|;&]*" + PROTECTED + r")"  # in-place sed
    r"|(?:\b(?:rm|mv|cp|touch|truncate|shred|unlink|ln)\b[^|;&]*" + PROTECTED + r")"
    r"|(?:\bdd\b[^|;&]*\bof=\S*" + PROTECTED + r")"
)

command = str(ti.get("command", ""))
if command:
    m = BASH_WRITE_RE.search(command)
    if m:
        print(
            f"BLOCKED by block_ledger_edits hook (matched: '{m.group(0)}'). {REASON}",
            file=sys.stderr,
        )
        sys.exit(2)

sys.exit(0)
