"""Read-only authority policy for the stateful daily ritual."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from data.provider_policy import THETADATA_ACQUISITION_DISABLED


@dataclass(frozen=True)
class RitualAuthority:
    h7_active: bool
    exact_session_source_active: bool


CURRENT_AUTHORITY = RitualAuthority(
    h7_active=False,
    exact_session_source_active=False,
)


@dataclass(frozen=True)
class RitualReadiness:
    ready: bool
    blockers: tuple[str, ...]


def evaluate_full_ritual(
    authority: RitualAuthority = CURRENT_AUTHORITY,
) -> RitualReadiness:
    """Return the tracked full-ritual authority state without side effects."""
    blockers: list[str] = []
    if not authority.exact_session_source_active:
        blockers.append("No approved ongoing exact-session options source is active.")
        if THETADATA_ACQUISITION_DISABLED:
            blockers.append(
                "ThetaData acquisition is disabled and is not an available fallback."
            )
    if not authority.h7_active:
        blockers.append("H7 forward-paper authority is paused; no active namespace exists.")
    return RitualReadiness(ready=not blockers, blockers=tuple(blockers))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("status", "require-full"))
    args = parser.parse_args(argv)
    readiness = evaluate_full_ritual()
    print(json.dumps(asdict(readiness), sort_keys=True))
    return 0 if args.mode == "status" or readiness.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
