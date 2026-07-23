"""Owner-facing CLI for doctor, run/resume, status, and report generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from options_researcher.robustness.registry import ExperimentRegistry
from options_researcher.robustness.reporting import write_reports
from options_researcher.robustness.runner import (
    doctor,
    load_panels,
    load_spec,
    run_experiment,
)
from research import ledger

REPO_ROOT = Path(__file__).resolve().parents[2]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m options_researcher.robustness",
        description="Research-only options validation robustness experiments.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    def execution(name: str, help_text: str) -> None:
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--spec", required=True, help="immutable experiment JSON")
        command.add_argument("--panels", required=True, help="precomputed panel CSV")
        command.add_argument(
            "--registry",
            default=".tmp/robustness/experiments.sqlite3",
            help="SQLite experiment registry",
        )
        command.add_argument(
            "--artifacts",
            default="reports/robustness",
            help="JSON/CSV/Markdown report directory",
        )
        command.add_argument("--workers", type=int, default=1, choices=range(1, 9))

    doctor_parser = commands.add_parser(
        "doctor", help="validate preregistration, data identity, and run prerequisites"
    )
    doctor_parser.add_argument("--spec", required=True)
    doctor_parser.add_argument("--panels", required=True)
    doctor_parser.add_argument("--ledger-dir", default="ledger")
    execution("run", "run one registered robustness experiment")
    execution("resume", "resume a deterministic interrupted experiment")

    report = commands.add_parser("report", help="regenerate reports from stored results")
    report.add_argument("--run-id", required=True)
    report.add_argument("--registry", default=".tmp/robustness/experiments.sqlite3")
    report.add_argument("--artifacts", default="reports/robustness")

    status = commands.add_parser("list", help="list experiment status")
    status.add_argument("--registry", default=".tmp/robustness/experiments.sqlite3")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "doctor":
        spec = load_spec(args.spec)
        ledger.verify(args.ledger_dir)
        result = doctor(
            spec,
            args.panels,
            ledger.read_all(args.ledger_dir),
            repo_root=REPO_ROOT,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.command in {"run", "resume"}:
        spec = load_spec(args.spec)
        panels = load_panels(args.panels)
        ledger.verify("ledger")
        records = ledger.read_all("ledger")
        doctor(spec, args.panels, records, repo_root=REPO_ROOT)
        with ExperimentRegistry(args.registry) as registry:
            paths = run_experiment(
                spec,
                panels,
                records,
                registry,
                output_directory=args.artifacts,
                workers=args.workers,
            )
        print(json.dumps({"run_id": spec.run_id, "artifacts": [str(p) for p in paths]}))
        return 0
    if args.command == "report":
        with ExperimentRegistry(args.registry) as registry:
            paths = write_reports(registry, args.run_id, args.artifacts)
        print(json.dumps({"run_id": args.run_id, "artifacts": [str(p) for p in paths]}))
        return 0
    if args.command == "list":
        with ExperimentRegistry(args.registry) as registry:
            print(json.dumps(registry.list_runs(), sort_keys=True, indent=2))
        return 0
    raise AssertionError(f"unhandled command {args.command!r}")
