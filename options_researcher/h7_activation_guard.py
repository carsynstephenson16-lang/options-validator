"""Stage-8 activation guard — read-only precondition computation.

Appends nothing, ever. ``allow_real_readonly=True`` permits VERIFY-ONLY
reads of the real store for readiness snapshots; every mutating Stage-8
action lives elsewhere and stays owner-gated.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from options_researcher import h7_event_ledger as ledger
from options_researcher.h7_scope import scope_identity
from options_researcher.h7_window_registration import OWNER_FIELDS
from research.hashing import config_hash, diagnostic_source_hash
from research.receipts import verify_receipt


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    reason: str


@dataclass
class GuardReport:
    checks: list[Check] = field(default_factory=list)
    # Binding + freshness provenance. These do not gate ``ready`` (which is the
    # AND of every check); they let a downstream real-store append prove the
    # report it was handed was computed against THIS forward store and THIS
    # code identity, in the same session -- so a stale or store-mismatched PASS
    # can never authorize a write. Empty strings on a freshly-built report only
    # when git is unavailable; the real-append path treats those as non-fresh.
    forward_base: str = ""
    code_commit: str = ""
    built_at_utc: str = ""

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


def _git_head() -> str:
    """Current committed code identity (``git rev-parse HEAD``). Empty string
    if git cannot answer -- the real-append path treats an empty commit as
    non-fresh and refuses, so this never silently degrades safety."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return ""
    return out


def activation_preconditions(*, forward_base, source_health_by_symbol: dict,
                             universe: tuple, data_gate_result: dict,
                             owner_inputs: dict,
                             allow_real_readonly: bool = False,
                             strict: bool = False,
                             source_health_receipt: dict | None = None,
                             data_gate_receipt: dict | None = None,
                             backup_restore_receipt: dict | None = None,
                             completed_session: str | None = None,
                             included: tuple | None = None) -> GuardReport:
    """When ``included`` is None (default) the guard checks the whole
    ``universe`` -- today's all-or-nothing 15-name activation, unchanged.

    When ``included`` is a subset (Option C trim-at-append), the source-health
    and data-gate checks operate on the INCLUDED names ONLY: every included name
    must be healthy, and every included name must be per-symbol GO in the
    data-gate receipt. Excluded names are recorded in the payload elsewhere and
    are NOT health-checked here. The receipt-binding strict checks
    (``scope_identity``, ``receipt_chain``, ``source_config_identity``,
    ``fresh_backup_restore``) still verify the receipts cover the FULL official
    scope -- that is the anti-cherry-pick guarantee: trimming only SELECTS from
    pre-computed full-scope evidence, it never narrows the evidence itself."""
    from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE, ActivationBoundaryError
    base = Path(forward_base).resolve()
    real = Path(REAL_FORWARD_STORE).resolve()
    if not allow_real_readonly and (base == real or real in base.parents):
        raise ActivationBoundaryError("guard fixtures must use synthetic stores")

    report = GuardReport(forward_base=str(base), code_commit=_git_head(),
                         built_at_utc=datetime.now(timezone.utc).isoformat())
    v = ledger.verify(base_dir=base)
    report.checks.append(Check(
        "ledger_valid_empty", v.valid and v.empty,
        "VALID EMPTY" if v.valid and v.empty
        else f"valid={v.valid} empty={v.empty} count={v.count}"))

    checked_names = tuple(universe if included is None else included)
    unhealthy = sorted(s for s in checked_names
                       if not source_health_by_symbol.get(s, False))
    missing = sorted(set(checked_names) - set(source_health_by_symbol))
    report.checks.append(Check(
        "source_health_whole_universe", not unhealthy and not missing,
        "all healthy" if not unhealthy and not missing
        else f"unhealthy={unhealthy} missing={missing}"))

    if included is None:
        gate_ok = (data_gate_result.get("whole_universe_verdict") == "GO"
                   and data_gate_result.get("go_count") ==
                   len(data_gate_result.get("universe", [])))
        gate_reason = ("GO whole-universe" if gate_ok
                       else f"verdict={data_gate_result.get('whole_universe_verdict')}")
    else:
        per_symbol = data_gate_result.get("symbols", {})
        not_go = sorted(s for s in checked_names
                        if per_symbol.get(s, {}).get("verdict") != "GO")
        gate_ok = bool(checked_names) and not not_go
        gate_reason = ("GO for all included" if gate_ok
                       else f"included not GO: {not_go}")
    report.checks.append(Check("data_gate_go", gate_ok, gate_reason))

    if strict:
        current_scope = scope_identity()
        scope_ok = (data_gate_result.get("scope") == current_scope
                    and tuple(data_gate_result.get("universe", ())) ==
                    tuple(current_scope["symbols"]))
        report.checks.append(Check(
            "scope_identity", scope_ok,
            "official current scope" if scope_ok else "missing/stale scope identity"))
        receipts_ok = (source_health_receipt is not None
                       and data_gate_receipt is not None
                       and not verify_receipt(source_health_receipt)
                       and not verify_receipt(data_gate_receipt)
                       and data_gate_receipt.get("receipt_hash") ==
                       data_gate_result.get("receipt_hash")
                       and source_health_receipt.get("receipt_hash") ==
                       data_gate_receipt.get("source_health_receipt_hash")
                       and data_gate_receipt.get("scope") == current_scope)
        report.checks.append(Check(
            "receipt_chain", receipts_ok,
            "source-health -> data-gate receipts linked" if receipts_ok
            else "receipt chain missing, tampered, or mismatched"))
        if included is None:
            source_ok = (source_health_receipt is not None
                         and source_health_receipt.get("activation_ready") is True
                         and source_health_receipt.get("healthy_count") == len(universe)
                         and not source_health_receipt.get("unhealthy_symbols"))
            source_reason = ("all current names healthy" if source_ok
                             else "source health is partial or stale")
        else:
            # Trim mode: the FULL-scope receipt need not be all-healthy, but
            # every INCLUDED name must be healthy in its per-symbol map and none
            # may appear in the receipt's unhealthy list.
            incl = set(checked_names)
            receipt_syms = (source_health_receipt.get("symbols", {})
                            if source_health_receipt else {})
            source_ok = (source_health_receipt is not None
                         and bool(incl)
                         and incl.isdisjoint(set(
                             source_health_receipt.get("unhealthy_symbols") or []))
                         and all(receipt_syms.get(s, {}).get("healthy") is True
                                 for s in incl))
            source_reason = ("all included names healthy" if source_ok
                             else "an included name is unhealthy/stale in the receipt")
        report.checks.append(Check(
            "source_health_all_names", source_ok, source_reason))
        identity_ok = (data_gate_receipt is not None
                       and data_gate_receipt.get("config_hash") == config_hash()
                       and data_gate_receipt.get("source_hash") ==
                       diagnostic_source_hash())
        report.checks.append(Check(
            "source_config_identity", identity_ok,
            "code/config identity matches receipts" if identity_ok
            else "code/config identity changed since gate"))
        backup_ok = False
        if backup_restore_receipt is not None:
            backup_ok = (
                not verify_receipt(backup_restore_receipt)
                and backup_restore_receipt.get("receipt_type") == "backup_restore"
                and backup_restore_receipt.get("scope") == current_scope
                and backup_restore_receipt.get("verification", {}).get("ok") is True
                and (completed_session is None or
                     backup_restore_receipt.get("completed_session") ==
                     completed_session))
        report.checks.append(Check(
            "fresh_backup_restore", backup_ok,
            "fresh verified restore evidence" if backup_ok
            else "missing/stale/unverified backup restore evidence"))

    blank = [f for f in OWNER_FIELDS if owner_inputs.get(f) in (None, "")]
    report.checks.append(Check(
        "owner_inputs_complete", not blank,
        "complete" if not blank else f"blank: {blank}"))

    report.checks.append(_working_tree_clean())
    return report
