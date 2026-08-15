"""Read-only authority policy for the stateful daily ritual.

Three flags, each naming one authorization the owner actually holds (brief 11
§5, `docs/superpowers/plans/2026-08-14-11-ritual-switch-on-rev2-spec.md`):

``ritual_data_phase_active``
    "The owner authorizes the daily non-verdict-bearing data/display phase to
    run from cached data." Asserts NOTHING about a live source and NOTHING
    about H7.
``exact_session_source_active``
    "An approved ONGOING exact-session options source is active." Its flip bar
    is spec §7 (bar S1).
``h7_active``
    Registration day only.

The tiers are deliberately MONOTONE: the full ritual requires all three, so
``ritual_data_phase_active`` is a master switch rather than a data-only switch.
Post-registration that makes flipping it back off an incident-response-grade
action, not a one-line convenience (spec §11 rollback).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from data.provider_policy import THETADATA_ACQUISITION_DISABLED


@dataclass(frozen=True)
class RitualAuthority:
    h7_active: bool
    exact_session_source_active: bool
    ritual_data_phase_active: bool


CURRENT_AUTHORITY = RitualAuthority(
    h7_active=False,
    exact_session_source_active=False,
    ritual_data_phase_active=False,
)


@dataclass(frozen=True)
class RitualReadiness:
    ready: bool
    blockers: tuple[str, ...]


def evaluate_data_phase(
    authority: RitualAuthority = CURRENT_AUTHORITY,
) -> RitualReadiness:
    """Return the tracked data-phase authority state without side effects."""
    blockers: list[str] = []
    if not authority.ritual_data_phase_active:
        blockers.append("Ritual data phase is not authorized.")
    return RitualReadiness(ready=not blockers, blockers=tuple(blockers))


def evaluate_full_ritual(
    authority: RitualAuthority = CURRENT_AUTHORITY,
) -> RitualReadiness:
    """Return the tracked full-ritual authority state without side effects.

    Monotone: the full tier requires all three flags, so it can never be ready
    while the data tier is blocked.
    """
    blockers: list[str] = list(evaluate_data_phase(authority).blockers)
    if not authority.exact_session_source_active:
        blockers.append("No approved ongoing exact-session options source is active.")
        if THETADATA_ACQUISITION_DISABLED:
            blockers.append("ThetaData acquisition is disabled and is not an available fallback.")
    if not authority.h7_active:
        blockers.append("H7 forward-paper authority is paused; no active namespace exists.")
    return RitualReadiness(ready=not blockers, blockers=tuple(blockers))


def main(
    argv: list[str] | None = None,
    *,
    authority: RitualAuthority = CURRENT_AUTHORITY,
) -> int:
    """Read-only CLI. Every mode is side-effect free.

    The ``authority`` seam exists so tests assert behavior at explicitly named
    flag combinations rather than at whatever ``CURRENT_AUTHORITY`` currently
    holds; the default keeps the shell call sites byte-identical.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("status", "require-data", "require-full"))
    args = parser.parse_args(argv)
    data_phase = evaluate_data_phase(authority)
    full_ritual = evaluate_full_ritual(authority)
    if args.mode == "status":
        print(
            json.dumps(
                {
                    "data_phase": asdict(data_phase),
                    "flags": asdict(authority),
                    "full_ritual": asdict(full_ritual),
                },
                sort_keys=True,
            )
        )
        return 0
    readiness = data_phase if args.mode == "require-data" else full_ritual
    print(json.dumps(asdict(readiness), sort_keys=True))
    return 0 if readiness.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
