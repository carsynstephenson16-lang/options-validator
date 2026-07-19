"""Stage-8 activation guard — read-only precondition computation.

Appends nothing, ever. ``allow_real_readonly=True`` permits VERIFY-ONLY
reads of the real store for readiness snapshots; every mutating Stage-8
action lives elsewhere and stays owner-gated.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from options_researcher import h7_event_ledger as ledger
from options_researcher.h7_window_registration import OWNER_FIELDS


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    reason: str


@dataclass
class GuardReport:
    checks: list[Check] = field(default_factory=list)

    @property
    def by_name(self) -> dict[str, Check]:
        return {c.name: c for c in self.checks}

    @property
    def ready(self) -> bool:
        return all(c.ok for c in self.checks)


def _working_tree_clean() -> Check:
    out = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                         text=True, check=True).stdout.strip()
    return Check("working_tree_clean", out == "",
                 "clean" if out == "" else f"dirty: {out.splitlines()[:5]}")


def activation_preconditions(*, forward_base, source_health_by_symbol: dict,
                             universe: tuple, data_gate_result: dict,
                             owner_inputs: dict,
                             allow_real_readonly: bool = False) -> GuardReport:
    from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE, ActivationBoundaryError
    base = Path(forward_base).resolve()
    real = Path(REAL_FORWARD_STORE).resolve()
    if not allow_real_readonly and (base == real or real in base.parents):
        raise ActivationBoundaryError("guard fixtures must use synthetic stores")

    report = GuardReport()
    v = ledger.verify(base_dir=base)
    report.checks.append(Check(
        "ledger_valid_empty", v.valid and v.empty,
        "VALID EMPTY" if v.valid and v.empty
        else f"valid={v.valid} empty={v.empty} count={v.count}"))

    unhealthy = sorted(s for s in universe
                       if not source_health_by_symbol.get(s, False))
    missing = sorted(set(universe) - set(source_health_by_symbol))
    report.checks.append(Check(
        "source_health_whole_universe", not unhealthy and not missing,
        "all healthy" if not unhealthy and not missing
        else f"unhealthy={unhealthy} missing={missing}"))

    gate_ok = (data_gate_result.get("whole_universe_verdict") == "GO"
               and data_gate_result.get("go_count") == len(data_gate_result.get("universe", [])))
    report.checks.append(Check(
        "data_gate_go", gate_ok,
        "GO whole-universe" if gate_ok
        else f"verdict={data_gate_result.get('whole_universe_verdict')}"))

    blank = [f for f in OWNER_FIELDS if owner_inputs.get(f) in (None, "")]
    report.checks.append(Check(
        "owner_inputs_complete", not blank,
        "complete" if not blank else f"blank: {blank}"))

    report.checks.append(_working_tree_clean())
    return report
