from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .config import load_policy
from .status import build_status


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only repository RAG")
    subparsers = parser.add_subparsers(dest="command", required=True)
    status = subparsers.add_parser("status", help="show machine-readable application status")
    status.add_argument("--policy", type=Path, default=_project_root() / "policy.json")
    status.add_argument("--repo-root", type=Path, default=_repository_root())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "status":
        policy = load_policy(args.policy)
        report = build_status(args.repo_root, policy)
        print(json.dumps(report.to_mapping(), indent=2, sort_keys=True))
        return 0 if report.status == "READY_OFFLINE" else 2
    raise AssertionError(f"unhandled command: {args.command}")
