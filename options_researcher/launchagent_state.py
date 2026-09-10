"""Observe installed versus loaded LaunchAgents without changing launchd state."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import subprocess
from collections.abc import Collection, Mapping
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol
from xml.parsers.expat import ExpatError

from data.atomic_io import atomic_text_write

# LLM-proposed literal matching the tracked options-validator plist labels.
OWN_PREFIX = "com.carsyn.options-validator."


class State(StrEnum):
    INSTALLED_NOT_LOADED = "INSTALLED_NOT_LOADED"
    DISABLED = "DISABLED"
    LOADED_NOT_INSTALLED = "LOADED_NOT_INSTALLED"
    UNTRACKED = "UNTRACKED"
    NOT_INSTALLED = "NOT_INSTALLED"
    LOADED = "LOADED"


@dataclass(frozen=True)
class LabelState:
    label: str
    tracked_path: str | None
    installed: bool
    loaded: bool
    disabled: bool
    state: State


@dataclass(frozen=True)
class Observation:
    states: tuple[LabelState, ...]
    unavailable_reason: str | None
    unavailable_inputs: tuple[str, ...]


def classify(*, tracked: bool, installed: bool, loaded: bool, disabled: bool) -> State:
    """Classify one membership tuple; reject labels absent from all inputs."""
    if tracked and installed and not disabled and not loaded:
        return State.INSTALLED_NOT_LOADED
    elif tracked and installed and disabled:
        return State.DISABLED
    elif tracked and loaded and not installed:
        return State.LOADED_NOT_INSTALLED
    elif not tracked and (installed or loaded):
        return State.UNTRACKED
    elif tracked and not installed:
        return State.NOT_INSTALLED
    elif tracked and installed and loaded:
        return State.LOADED
    raise ValueError("label must be tracked, installed, or loaded")


def compare(
    *,
    tracked: Mapping[str, str],
    installed: Collection[str],
    loaded: Collection[str],
    disabled: Collection[str],
    prefix: str = OWN_PREFIX,
) -> tuple[LabelState, ...]:
    universe = (
        set(tracked)
        | {x for x in installed if x.startswith(prefix)}
        | {x for x in loaded if x.startswith(prefix)}
    )
    states = (
        LabelState(
            label,
            tracked.get(label),
            label in installed,
            label in loaded,
            label in disabled,
            classify(
                tracked=label in tracked,
                installed=label in installed,
                loaded=label in loaded,
                disabled=label in disabled,
            ),
        )
        for label in universe
    )
    order = {state: i for i, state in enumerate(State)}
    return tuple(sorted(states, key=lambda item: (order[item.state], item.label)))


def tracked_labels(root: Path) -> dict[str, str]:
    labels: dict[str, str] = {}
    for directory in (
        "tools/launchagents",
        "tools/launchd",
        "tools/repo_rag/launchd",
        "tools/anti-stranding",
    ):
        for path in sorted((root / directory).rglob("*.plist")):
            try:
                with path.open("rb") as stream:
                    payload = plistlib.load(stream)
            except (ExpatError, plistlib.InvalidFileException):
                matches = set(
                    re.findall(
                        r"<key>Label</key>\s*<string>([^<]+)</string>",
                        path.read_text(encoding="utf-8"),
                    )
                )
                if len(matches) != 1:
                    raise ValueError(f"{path}: Label match count {len(matches)}") from None
                label = matches.pop()
            else:
                label = payload.get("Label") if isinstance(payload, Mapping) else None
                if not isinstance(label, str) or not label:
                    raise ValueError(f"{path}: Label match count 0")
            if label in labels:
                raise ValueError(f"{path}: duplicate Label {label!r} (also {labels[label]})")
            labels[label] = path.relative_to(root).as_posix()
    return labels


def installed_labels(agents_dir: Path = Path.home() / "Library" / "LaunchAgents") -> frozenset[str]:
    return frozenset(path.stem for path in agents_dir.glob("*.plist") if path.is_file())


class RunResult(Protocol):
    @property
    def returncode(self) -> int: ...
    @property
    def stdout(self) -> str: ...


class Runner(Protocol):
    def __call__(
        self,
        argv: list[str],
        /,
        *,
        capture_output: Literal[True],
        text: Literal[True],
        check: Literal[False],
    ) -> RunResult: ...


def listed_labels(*, run: Runner = subprocess.run) -> frozenset[str] | None:
    result = run(["/bin/launchctl", "list"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    return frozenset(
        parts[2]
        for line in result.stdout.splitlines()
        if line != "PID\tStatus\tLabel" and len(parts := line.split("\t", 2)) == 3
    )


def print_loaded(label: str, *, uid: int, run: Runner = subprocess.run) -> bool:
    result = run(
        ["/bin/launchctl", "print", f"gui/{uid}/{label}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def disabled_labels(*, uid: int, run: Runner = subprocess.run) -> frozenset[str] | None:
    result = run(
        ["/bin/launchctl", "print-disabled", f"gui/{uid}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return frozenset(
        match.group(1)
        for line in result.stdout.splitlines()
        if (match := re.fullmatch(r'\s*"([^"]+)"\s*=>\s*disabled\s*', line))
    )


def observe(
    *,
    root: Path,
    agents_dir: Path,
    uid: int,
    run: Runner = subprocess.run,
    prefix: str = OWN_PREFIX,
) -> Observation:
    tracked = tracked_labels(root)
    installed = installed_labels(agents_dir)
    try:
        listed = listed_labels(run=run)
        untracked_seen = {x for x in (listed or ()) if x.startswith(prefix)} - set(tracked)
        loaded = {x for x in tracked if print_loaded(x, uid=uid, run=run)} | untracked_seen
        disabled = disabled_labels(uid=uid, run=run)
    except FileNotFoundError as exc:
        return Observation((), f"/bin/launchctl absent: {exc}", ("list", "print", "print-disabled"))
    unavailable = tuple(
        name for name, value in (("list", listed), ("print-disabled", disabled)) if value is None
    )
    return Observation(
        compare(
            tracked=tracked,
            installed=installed,
            loaded=loaded,
            disabled=disabled or frozenset(),
            prefix=prefix,
        ),
        None,
        unavailable,
    )


def build_receipt(
    *, as_of: str | None, run_date: str | None, run_at_utc: str, observation: Observation
) -> dict:
    return {
        "schema_version": "daily_ritual/launchagent_state/v1",
        "as_of": as_of or None,
        "run_date": run_date,
        "run_at_utc": run_at_utc,
        "states": [asdict(item) for item in observation.states],
        "summary": {
            **{
                state.value.lower(): sum(item.state == state for item in observation.states)
                for state in State
            },
            "unavailable_reason": observation.unavailable_reason,
            "unavailable_inputs": list(observation.unavailable_inputs),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--as-of")
    parser.add_argument("--run-date")
    parser.add_argument("--agents-dir", type=Path, default=Path.home() / "Library" / "LaunchAgents")
    parser.add_argument("--no-receipt", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code:
            print("launchagents: invalid arguments; no observation or receipt produced")
        return 0
    try:
        if not args.no_receipt and not args.run_date:
            raise ValueError("--run-date is required unless --no-receipt")
        for value in (args.as_of, args.run_date):
            if value and date.fromisoformat(value).isoformat() != value:
                raise ValueError("dates must use YYYY-MM-DD")
        if not args.as_of:
            print(
                "launchagents: as_of unresolved (ritual crit at daily_ritual.sh:123); "
                "receipt keyed by run_date only"
            )
        observation = observe(root=args.root, agents_dir=args.agents_dir, uid=os.getuid())
        payload = build_receipt(
            as_of=args.as_of,
            run_date=args.run_date,
            run_at_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            observation=observation,
        )
        receipt = "none (--no-receipt)"
        if not args.no_receipt:
            path = args.root / "reports/ritual" / f"launchagent_state_{args.run_date}.json"
            try:
                atomic_text_write(json.dumps(payload, sort_keys=True, indent=2) + "\n", path)
            except OSError as exc:
                # Persistence failure must not hide incidents on the live ritual surface.
                print(f"launchagents: receipt write error: {exc}")
                receipt = f"unavailable ({path})"
            else:
                receipt = str(path)
        for item in observation.states:
            if item.state == State.INSTALLED_NOT_LOADED:
                print(
                    f"launchagents: {item.state} {item.label} ({item.tracked_path}) — run: "
                    f"launchctl bootstrap gui/$UID ~/Library/LaunchAgents/{item.label}.plist"
                )
            elif item.state == State.DISABLED:
                print(
                    f"launchagents: {item.state} {item.label} ({item.tracked_path}) — run: "
                    f"launchctl enable gui/$UID/{item.label} first; then launchctl bootstrap "
                    f"gui/$UID ~/Library/LaunchAgents/{item.label}.plist"
                )
            elif item.state in (State.UNTRACKED, State.LOADED_NOT_INSTALLED):
                print(f"launchagents: {item.state} {item.label}")
        if observation.unavailable_reason is not None:
            print(f"launchagents: UNAVAILABLE — {observation.unavailable_reason}")
        if observation.unavailable_inputs:
            print(f"launchagents: unavailable_inputs={','.join(observation.unavailable_inputs)}")
        summary = payload["summary"]
        tracked_count = sum(item.tracked_path is not None for item in observation.states)
        print(
            f"launchagents: {tracked_count} tracked, {summary['loaded']} loaded, "
            f"{summary['installed_not_loaded']} installed-not-loaded, {summary['disabled']} disabled, "
            f"{summary['not_installed']} not-installed (owner-gated), receipt={receipt}"
        )
    except (OSError, ValueError) as exc:
        print(f"launchagents: observation/receipt error: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
