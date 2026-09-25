#!/usr/bin/env python3
"""PreToolUse hook: blocks tool calls that touch live order placement.

Exit 2 = block the tool call; stderr is fed back to the agent as the reason.
FAIL-CLOSED: if input can't be parsed, block rather than guess.
"""
import json
import re
import sys

try:
    d = json.load(sys.stdin)
    ti = d.get("tool_input", {}) or {}
    haystack = "\n".join(
        str(ti.get(k, ""))
        for k in ("command", "content", "file_text", "new_str", "new_string")
    )
except Exception as e:  # noqa: BLE001 - safety hook fails closed on anything
    print(
        f"BLOCKED by block_live_trading hook: could not parse tool input ({e}). "
        f"Failing closed: this project is validator-only.",
        file=sys.stderr,
    )
    sys.exit(2)

PATTERNS = re.compile(
    r"place_order|submit_order|live_order|create_order"
    r"|broker\.(buy|sell)"
    r"|alpaca\S*\.(submit|order)|tradeapi"
    r"|schwab\S*(order|trade)|robinhood\S*(order|trade)"
    r"|tastytrade\S*(order|trade)|ibkr\S*(order|placeorder)|ib_insync"
    r"|paper_mode\s*=\s*false|live\s*=\s*true|paper\s*=\s*false",
    re.IGNORECASE,
)

m = PATTERNS.search(haystack)
if m:
    print(
        f"BLOCKED by block_live_trading hook (matched: '{m.group(0)}'). "
        f"This project is validator-only: no order placement, no live broker "
        f"endpoints, no disabling paper mode. If this is a false positive in a "
        f"comment or test fixture, rename the string so it does not look like "
        f"order code.",
        file=sys.stderr,
    )
    sys.exit(2)

sys.exit(0)
