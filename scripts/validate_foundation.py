#!/usr/bin/env python3
"""Validate the local researcher scaffold without network or paid APIs."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from options_researcher.foundation import (  # noqa: E402
    FORBIDDEN_CAPABILITIES,
    foundation_summary,
)


def main() -> int:
    summary = foundation_summary(ROOT)
    if summary["missing"]:
        print("foundation missing required path(s):", file=sys.stderr)
        for path in summary["missing"]:
            print(f"- {path}", file=sys.stderr)
        return 1

    print("foundation OK")
    print("guardrails:")
    for capability in FORBIDDEN_CAPABILITIES:
        print(f"- no {capability}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
