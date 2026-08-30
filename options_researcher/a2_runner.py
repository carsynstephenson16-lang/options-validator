"""One-shot, local-cache-only controller for the exploratory A2 battery.

The controller is deliberately a thin boundary around :mod:`a2_panel` and
:mod:`a2_battery`.  It validates the registration before touching a loader,
selects each week's ONLY candidate board from entry-time (pre-resolution)
availability on the current `config.ATTRACTIVENESS_UNIVERSE` board
(A2_AMENDMENT_V1_1, ledger seq 27; the 2026-08-15 breach/weekly-cohort
amendment), and writes one immutable report before an optional explicit
ledger publication.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import pandas as pd

import config
from options_researcher.a2_battery import (
    LANE_ARMS,
    A2Outcome,
    A2VariantSummary,
    non_overlapping_inference_rows,
    staggered_descriptive_rows,
    summarize_lane,
)
from options_researcher.a2_panel import (
    A2AuditResult,
    A2Diagnostics,
    audit_historical_inputs,
    build_historical_outcomes,
    select_income_contract,
)
from research.hashing import canonical_json, sha256_file, sha256_hex

REPORT_SCHEMA = "a2_outcome_battery_v1"
HYPOTHESIS_ID = "A2-v1"
REGISTRATION_SEQ = config.A2_REGISTRATION_SEQUENCE
REGISTRATION_RECORD_HASH = "684b59a2bf322a96ae375cd7b857706775eea2b971ffc456a4b09f40cb0383a2"
PIN_FACT_TOKEN = "RQ2_A2_PIN_ADDENDUM_V1"
ENTRY_CONVENTION_FACT_TOKEN = "A2_ENTRY_CONVENTION_ADDENDUM_V1"
ENTRY_CONVENTION_REPORT = "reports/2026-08-15-a2-entry-convention-validation.md"
ENTRY_CONVENTION_FACT_PAYLOAD = (
    "A2_ENTRY_CONVENTION_ADDENDUM_V1 owner-approved 2026-08-15 "
    "source=reports/2026-08-15-a2-entry-convention-validation.md "
    "status=historical-entry-convention-complete research-only=no-verdict"
)
# LLM-proposed governance strengthening, owner veto open (independent
# adversarial review 2026-08-30, governance Finding 7): the addendum fact
# above was agent-authored without owner evidence.  This second fact is
# ADDITIONALLY required -- it does not exist in ledger/facts.log yet and
# MUST NOT be written by any agent -- so the historical run stays fail-closed
# until an owner-authorized ratification fact is appended.  The addendum
# fact remains required too; its content is still referenced by the
# historical-entry-convention report.
ENTRY_CONVENTION_RATIFICATION_FACT_TOKEN = "A2_ENTRY_CONVENTION_RATIFIED_V1"
ENTRY_CONVENTION_RATIFICATION_FACT_PREFIX = (
    ENTRY_CONVENTION_RATIFICATION_FACT_TOKEN + " owner-approved"
)
UNSUPPORTED_FORWARD_FIELDS = (
    "forward_dates",
    "forward_adverse_gate_adjudication",
    "pmcc_synthetic_position_convention",
    "forward_verdict",
)
# F5 (independent adversarial review, 2026-08-30): ledger seq 27
# (A2_AMENDMENT_V1_1) mandates that "every historical output carries a
# permanent disclosure that the universe is the 2026-08 board applied
# retroactively and that name inclusion is outcome-informed (several names
# joined the board because of what they became -- the H10 precedent for
# permanent outcome-informed disclosures applies directly)."  Quoted
# verbatim below; required on every report and enforced by validate_report.
RETROACTIVE_UNIVERSE_DISCLOSURE = (
    "the universe is the 2026-08 board applied retroactively and name "
    "inclusion is outcome-informed (several names joined the board because "
    "of what they became -- the H10 precedent for permanent outcome-informed "
    "disclosures applies directly)"
)


class A2RunnerError(RuntimeError):
    """The A2 controller cannot produce a trustworthy artifact."""


class OneRunError(A2RunnerError):
    """The report is immutable or failed its retry-provenance checks."""


@dataclass(frozen=True, slots=True)
class CachePaths:
    chain: Path
    underlying: Path
    features: Path
    rates: Path
    earnings: Path
    positions: Path
    fomc: Path

    @classmethod
    def from_overrides(cls, **overrides: str | Path | None) -> "CachePaths":
        defaults = {
            "chain": Path(".cache/chains"),
            "underlying": Path(".cache/underlying"),
            "features": Path(".tmp/research/attractiveness"),
            "rates": Path("data/rates"),
            "earnings": Path("data/earnings/gating_v3.csv"),
            "positions": Path(".cache/positions"),
            "fomc": Path(".cache/fomc/fomc_pit.csv"),
        }
        for name, value in overrides.items():
            if value is not None and not Path(value).expanduser().is_absolute():
                raise ValueError(f"A2 {name} override must be an absolute path")
        paths = {
            name: Path(overrides.get(name) or default).expanduser().resolve()
            for name, default in defaults.items()
        }
        return cls(**paths)

    def as_tuple(self) -> tuple[Path, ...]:
        return (
            self.chain,
            self.underlying,
            self.features,
            self.rates,
            self.earnings,
            self.positions,
            self.fomc,
        )


@dataclass(slots=True)
class A2LocalInputs:
    signals: Mapping[str, Mapping[str, float]]
    chains: Mapping[str, Mapping[str, pd.DataFrame]]
    raw_closes: Mapping[str, Mapping[str, float]]
    adjusted_closes: Mapping[str, Mapping[str, float]]
    features: Mapping[str, pd.DataFrame] = field(default_factory=dict)
    rates: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    earnings_assertions: Mapping[str, Sequence[str]] = field(default_factory=dict)
    earnings_records: Mapping[str, Sequence[Mapping[str, object]]] = field(default_factory=dict)
    fomc_events: Sequence[object] | None = None
    feature_as_of: dict[str, str] = field(default_factory=dict)
    positions: Mapping[str, object] = field(default_factory=dict)
    outcomes: tuple[A2Outcome, ...] | None = None
    diagnostics: A2Diagnostics | None = None
    audit: A2AuditResult | None = None
    provenance: Mapping[str, object] = field(default_factory=dict)


def _json_safe(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if is_dataclass(value) and not isinstance(value, type):
        return _json_safe({item.name: getattr(value, item.name) for item in fields(value)})
    return value


def _report_digest(report: Mapping[str, object]) -> str:
    body = dict(report)
    body.pop("report_sha256", None)
    return sha256_hex(canonical_json(_json_safe(body)))


def _validate_audit(audit: A2AuditResult) -> None:
    if set(audit.checks) != set(range(1, 15)):
        raise A2RunnerError("A2 audit must contain exactly fourteen checks")


def _merge_audits(audits: Sequence[A2AuditResult]) -> A2AuditResult:
    """Combine symbol-scoped audits without discarding any numbered finding."""
    checks = {number: [] for number in range(1, 15)}
    warnings: list[str] = []
    verdicts: list[str] = []
    for audit in audits:
        _validate_audit(audit)
        verdicts.append(audit.verdict)
        warnings.extend(audit.warnings)
        for number, issues in audit.checks.items():
            checks[number].extend(issues)
    verdict = (
        "BLOCK"
        if "BLOCK" in verdicts
        else "PASS WITH WARNINGS"
        if warnings or "PASS WITH WARNINGS" in verdicts
        else "PASS"
    )
    return A2AuditResult(
        checks={number: tuple(issues) for number, issues in checks.items()},
        verdict=verdict,
        warnings=tuple(warnings),
    )


def _print_aggregate_audit(audit: A2AuditResult) -> None:
    for number in range(1, 15):
        print(f"A2 aggregate audit check {number}: {len(audit.checks[number])} issue(s)")
    print(f"A2 aggregate audit verdict: {audit.verdict}")


def _validate_realism(realism_grade: str | None, realism_receipt: Path | None) -> tuple[str, str]:
    if not isinstance(realism_grade, str) or not realism_grade.strip():
        raise A2RunnerError("reviewed realism grade is required")
    if not isinstance(realism_receipt, Path):
        raise A2RunnerError("reviewed realism receipt must be an absolute file path")
    receipt = realism_receipt.expanduser()
    if not receipt.is_absolute() or not receipt.is_file():
        raise A2RunnerError(f"reviewed realism receipt is unavailable: {receipt}")
    return realism_grade.strip(), sha256_file(receipt)


def validate_report(report: Mapping[str, object]) -> None:
    if not isinstance(report, Mapping):
        raise OneRunError("A2 report is not an object")
    if report.get("schema") != REPORT_SCHEMA or report.get("hypothesis_id") != HYPOTHESIS_ID:
        raise OneRunError("A2 report schema or hypothesis identity is invalid")
    if report.get("registration_seq") != REGISTRATION_SEQ:
        raise OneRunError("A2 report registration sequence is invalid")
    if report.get("status") != "RESEARCH-ONLY / NO VERDICT":
        raise OneRunError("A2 report status is not research-only")
    if report.get("retroactive_universe_disclosure") != RETROACTIVE_UNIVERSE_DISCLOSURE:
        raise OneRunError("A2 report is missing ledger seq 27's permanent retroactivity disclosure")

    def has_forbidden_key(value: object) -> bool:
        if isinstance(value, Mapping):
            return any(
                key == "forward_verdict" or has_forbidden_key(item) for key, item in value.items()
            )
        if isinstance(value, (list, tuple)):
            return any(has_forbidden_key(item) for item in value)
        return False

    if has_forbidden_key(report):
        raise OneRunError("A2 report exposes an unsupported forward verdict field")
    variants = report.get("variants")
    if not isinstance(variants, list) or len(variants) != sum(
        len(arms) for arms in LANE_ARMS.values()
    ):
        raise OneRunError("A2 report does not contain every registered lane/arm")
    weekly_keys = {
        "accepted_board_not_first_session_of_week",
        "weeks_without_complete_board",
        "weeks_skipped_by_spacing",
    }
    breach_variant: Mapping[str, object] | None = None
    for variant in variants:
        if not isinstance(variant, Mapping):
            raise OneRunError("A2 report variant is not an object")
        exclusions = variant.get("exclusions")
        if not isinstance(exclusions, Mapping) or not weekly_keys.issubset(exclusions):
            raise OneRunError("A2 report variant lacks weekly cohort diagnostics")
        if variant.get("lane") == "csp" and variant.get("arm") == "breach_hold_21_dte":
            breach_variant = variant
    if breach_variant is None or not isinstance(
        breach_variant.get("duplication_against_close_21_dte"), Mapping
    ):
        raise OneRunError("A2 report lacks breach-arm duplication diagnostics")
    if not isinstance(breach_variant.get("breach_path_skip_counts"), Mapping):
        raise OneRunError("A2 report lacks breach-path skip diagnostics")
    if not isinstance(report.get("lane_statuses"), Mapping):
        raise OneRunError("A2 report lane statuses are missing")
    provenance = report.get("provenance")
    if not isinstance(provenance, Mapping):
        raise OneRunError("A2 report provenance is missing")
    audit = report.get("audit")
    if not isinstance(audit, Mapping) or set(audit.get("checks", {})) != {
        str(i) for i in range(1, 15)
    }:
        raise OneRunError("A2 report audit checks are not exactly 1..14")
    if provenance.get("realism_grade") in (None, "UNASSESSED") or not provenance.get(
        "realism_receipt_sha256"
    ):
        raise OneRunError("A2 report lacks reviewed realism provenance")
    recorded = report.get("report_sha256")
    if not isinstance(recorded, str) or recorded != _report_digest(report):
        raise OneRunError("A2 report hash does not match its immutable content")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise A2RunnerError(f"cannot read governance ledger {path}") from exc


def validate_governance(
    governance_dir: Path = Path("ledger"),
    *,
    ledger_dir: Path | None = None,
    facts_path: Path | None = None,
) -> dict[str, object]:
    """Validate registration/addendum evidence before any cache loader call."""
    base = Path(ledger_dir or governance_dir)
    records = _read_jsonl(base / "experiments.jsonl")
    registration = next((row for row in records if row.get("seq") == REGISTRATION_SEQ), None)
    if (
        not isinstance(registration, Mapping)
        or registration.get("record_hash") != REGISTRATION_RECORD_HASH
    ):
        raise A2RunnerError("A2 registration seq 19 or its exact record hash is missing")
    facts = Path(facts_path) if facts_path is not None else base / "facts.log"
    try:
        lines = facts.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise A2RunnerError("A2 facts log is unavailable") from exc
    payloads = []
    for line in lines:
        timestamp, separator, payload = line.partition("\t")
        if not separator or not timestamp.strip() or not payload.strip():
            continue
        payloads.append(payload.rstrip("\n"))
    if not any(
        payload.startswith(PIN_FACT_TOKEN + " ")
        and "source=reports/2026-07-23-pin-addendum-validation.md" in payload
        for payload in payloads
    ):
        raise A2RunnerError(f"A2 prerequisite fact {PIN_FACT_TOKEN} is missing")
    if ENTRY_CONVENTION_FACT_PAYLOAD not in payloads:
        raise A2RunnerError("owner-approved A2 entry-convention fact is missing")
    if not any(
        payload.startswith(ENTRY_CONVENTION_RATIFICATION_FACT_PREFIX) for payload in payloads
    ):
        raise A2RunnerError(
            "owner-authorized A2_ENTRY_CONVENTION_RATIFIED_V1 ratification fact is missing "
            "(LLM-proposed governance strengthening, owner veto open)"
        )
    return {
        "registration_seq": REGISTRATION_SEQ,
        "registration_hash": REGISTRATION_RECORD_HASH,
        "pin_fact": PIN_FACT_TOKEN,
        "entry_convention_ratification_fact": ENTRY_CONVENTION_RATIFICATION_FACT_TOKEN,
        "entry_convention_fact": ENTRY_CONVENTION_FACT_TOKEN,
    }


def _atomic_create(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise OneRunError(f"A2 one-run report already exists: {path}") from exc
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _git_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise A2RunnerError("cannot identify source Git commit") from exc


def _variant_rows(
    outcomes: Sequence[A2Outcome],
    signals: Mapping[str, Mapping[str, float]],
    lane: str,
    arm: str,
) -> tuple[tuple[A2Outcome, ...], tuple[A2Outcome, ...], dict[str, object]]:
    """Weekly-cohort board construction (A2_AMENDMENT_V1_1, ledger seq 27; the
    2026-08-15 breach/weekly-cohort amendment Definition 2).

    The board is the current `config.ATTRACTIVENESS_UNIVERSE` (18 names), NOT
    the frozen 15-name `config.A2_UNIVERSE` (which stays defined only for
    registration provenance -- `A2_REGISTRATION_SEQUENCE`,
    `A2_CSP_FIXED_HORIZON_SESSIONS`, etc.).  Each cohort's expected board is
    the names scored in ``signals`` that day (a proxy for "cached chain data
    at that session's formation", since a score can only be computed from a
    chain that day) intersected with the current universe.  A partial board
    IS used for inference once resolved (skip-not-reject); candidate
    selection itself is delegated to
    :func:`non_overlapping_inference_rows`'s entry-time-only mode, which never
    inspects realized outcome rows to choose a week's candidate day.
    """
    rows = tuple(row for row in outcomes if row.lane == lane and row.arm == arm)
    universe = set(config.ATTRACTIVENESS_UNIVERSE)
    board_by_date: dict[str, tuple[str, ...]] = {
        decision: tuple(symbol for symbol in board if symbol in universe)
        for decision, board in signals.items()
    }
    grouped: dict[str, list[A2Outcome]] = {}
    for row in rows:
        grouped.setdefault(row.decision_date, []).append(row)
    incomplete = 0
    missing_by_date: dict[str, list[str]] = {}
    per_cohort_name_counts: dict[str, int] = {}
    split_entry_date_cohorts = 0
    for decision, cohort in sorted(grouped.items()):
        observed = {row.symbol for row in cohort}
        expected = set(board_by_date.get(decision, ()))
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        entries = {row.entry_date for row in cohort}
        scored = signals.get(decision, {})
        score_identity = all(
            symbol in scored
            and math.isclose(
                float(next(row.score for row in cohort if row.symbol == symbol)),
                float(scored[symbol]),
                abs_tol=1e-12,
                rel_tol=0.0,
            )
            for symbol in expected
            if symbol in observed
        )
        per_cohort_name_counts[decision] = len(cohort)
        if len(entries) > 1:
            split_entry_date_cohorts += 1
        if missing or extra or not score_identity:
            incomplete += 1
            if missing or extra:
                missing_by_date[decision] = missing + [f"extra:{symbol}" for symbol in extra]
    weekly_diagnostics: dict[str, int] = {}
    inference = non_overlapping_inference_rows(
        rows,
        lane=lane,
        arm=arm,
        board_symbols_by_date=board_by_date,
        decision_dates=tuple(signals),
        diagnostics=weekly_diagnostics,
    )
    for key in (
        "accepted_board_not_first_session_of_week",
        "weeks_without_complete_board",
        "weeks_skipped_by_spacing",
        "weeks_skipped_unresolvable_board",
        "weeks_skipped_split_entry_date",
    ):
        weekly_diagnostics.setdefault(key, 0)
    return (
        inference,
        rows,
        {
            "incomplete_cohorts": incomplete,
            "missing_names": missing_by_date,
            "original_bucket_identity_preserved": not incomplete and bool(grouped),
            "per_cohort_name_counts": per_cohort_name_counts,
            "split_entry_date_realized_cohorts": split_entry_date_cohorts,
            **weekly_diagnostics,
        },
    )


def _breach_duplication(
    rows: Sequence[A2Outcome], signals: Mapping[str, Mapping[str, float]]
) -> dict[str, int | float | None]:
    by_arm: dict[str, dict[tuple[str, str, str], A2Outcome]] = {
        "close_21_dte": {},
        "breach_hold_21_dte": {},
    }
    complete_decisions: dict[str, set[str]] = {
        "close_21_dte": set(),
        "breach_hold_21_dte": set(),
    }
    universe = set(config.ATTRACTIVENESS_UNIVERSE)
    for arm in by_arm:
        arm_rows = [row for row in rows if row.lane == "csp" and row.arm == arm]
        decisions = {row.decision_date for row in arm_rows}
        for decision in decisions:
            cohort = [row for row in arm_rows if row.decision_date == decision]
            expected = set(signals.get(decision, {})) & universe
            if (
                expected
                and len(cohort) == len(expected)
                and {row.symbol for row in cohort} == expected
            ):
                complete_decisions[arm].add(decision)
                by_arm[arm].update(
                    {(row.symbol, row.decision_date, row.entry_date): row for row in cohort}
                )
    comparable_keys = set(by_arm["close_21_dte"]) & set(by_arm["breach_hold_21_dte"])
    comparable_keys = {
        key
        for key in comparable_keys
        if key[1] in complete_decisions["close_21_dte"]
        and key[1] in complete_decisions["breach_hold_21_dte"]
    }
    identical = sum(
        by_arm["close_21_dte"][key].resolution_date
        == by_arm["breach_hold_21_dte"][key].resolution_date
        for key in comparable_keys
    )
    comparable = len(comparable_keys)
    return {
        "comparable_count": comparable,
        "identical_resolution_count": identical,
        "rate": identical / comparable if comparable else None,
    }


def _summary_dict(
    summary: object, *, exclusions: Mapping[str, object], descriptive_count: int
) -> dict[str, object]:
    if not is_dataclass(summary) or isinstance(summary, type):
        raise A2RunnerError("A2 summary is not a dataclass")
    raw = _json_safe({item.name: getattr(summary, item.name) for item in fields(summary)})
    assert isinstance(raw, dict)
    raw["descriptive_count"] = descriptive_count
    raw["exclusions"] = dict(exclusions)
    raw["views"] = {
        "inference": {"rows": int(raw.get("inference_count", 0))},
        "staggered": {"rows": descriptive_count, "used_for_inference": False},
    }
    raw["cost_stress"] = _json_safe(raw.get("cost_stress", {}))
    raw["bid_ask_stress"] = _json_safe(raw.get("bid_ask_stress", {}))
    return raw


def build_report(
    *,
    outcomes: Sequence[A2Outcome],
    signals: Mapping[str, Mapping[str, float]],
    audit: A2AuditResult,
    governance: Mapping[str, object],
    provenance: Mapping[str, object],
    diagnostics: A2Diagnostics | None = None,
    realism_grade: str | None = None,
    realism_receipt: Path | None = None,
) -> dict[str, object]:
    _validate_audit(audit)
    if audit.verdict == "BLOCK":
        raise A2RunnerError("A2 data audit BLOCK prevents report assembly")
    grade, receipt_hash = _validate_realism(realism_grade, realism_receipt)
    breach_duplication = _breach_duplication(outcomes, signals)
    breach_skips = diagnostics.skips if diagnostics is not None else {}
    breach_path_skip_counts = {
        "breached": sum(
            count
            for reason, count in breach_skips.items()
            if reason.startswith("breach_hold_21_dte_breached_")
        ),
        "unbreached": sum(
            count
            for reason, count in breach_skips.items()
            if reason.startswith("breach_hold_21_dte_unbreached_")
        ),
    }
    variants: list[dict[str, object]] = []
    lane_statuses: dict[str, object] = {}
    for lane, arms in LANE_ARMS.items():
        lane_variants: list[dict[str, object]] = []
        first_pass: dict[
            str,
            tuple[
                tuple[A2Outcome, ...], tuple[A2Outcome, ...], dict[str, object], A2VariantSummary
            ],
        ] = {}
        for arm in arms:
            inference, descriptive, exclusions = _variant_rows(outcomes, signals, lane, arm)
            summary = summarize_lane(inference, lane=lane, arm=arm)
            first_pass[arm] = (inference, descriptive, exclusions, summary)
        family = {
            arm: item[3].raw_p_value
            for arm, item in first_pass.items()
            if item[3].raw_p_value is not None
        }
        for arm in arms:
            inference, descriptive, exclusions, _summary = first_pass[arm]
            summary = summarize_lane(
                inference,
                lane=lane,
                arm=arm,
                family_raw_p_values=family,
            )
            row = _summary_dict(summary, exclusions=exclusions, descriptive_count=len(descriptive))
            row["lane"], row["arm"] = lane, arm
            row["status"] = summary.status
            if lane == "csp" and arm == "breach_hold_21_dte":
                row["duplication_against_close_21_dte"] = breach_duplication
                row["breach_path_skip_counts"] = breach_path_skip_counts
                row["data_gap_propagation"] = (
                    "one CSP arm data gap removes all five CSP arms and can make "
                    "the weekly board incomplete"
                )
            row["staggered_count"] = (
                len(staggered_descriptive_rows(descriptive, lane=lane, arm=arm))
                if descriptive
                else 0
            )
            variants.append(row)
            lane_variants.append(row)
        lane_statuses[lane] = {
            "status": "ok" if any(item["status"] == "ok" for item in lane_variants) else "no data",
            "variants": [{"arm": item["arm"], "status": item["status"]} for item in lane_variants],
        }
    audit_payload = {
        "verdict": audit.verdict,
        "checks": {str(number): list(values) for number, values in audit.checks.items()},
        "warnings": list(audit.warnings),
        "check_count": 14,
    }
    provenance_payload = {
        "source_commit": _git_head(),
        "runner_sha256": sha256_file(Path(__file__)),
        "registration_seq": REGISTRATION_SEQ,
        "registration_hash": REGISTRATION_RECORD_HASH,
        "max_as_of": _json_safe(dict(provenance)),
        "realism_grade": grade,
        "realism_receipt_sha256": receipt_hash,
    }
    if diagnostics is not None:
        provenance_payload["exclusion_counts"] = dict(diagnostics.skips)
        provenance_payload["pmcc_status"] = diagnostics.pmcc_status
        # F4 (independent adversarial review, 2026-08-30): breach-on-expiry is
        # a successful terminal-exception settlement (Definition 1.2), not a
        # skip; it gets its own report-level counter.
        provenance_payload["breach_on_expiry_settlements"] = diagnostics.breach_on_expiry_settlements
    report: dict[str, object] = {
        "schema": REPORT_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "registration_seq": REGISTRATION_SEQ,
        "registration_hash": REGISTRATION_RECORD_HASH,
        "status": "RESEARCH-ONLY / NO VERDICT",
        "claim_authority": "NO VERDICT",
        "lane_statuses": lane_statuses,
        "variants": variants,
        "audit": audit_payload,
        "provenance": provenance_payload,
        "governance": dict(governance),
        "unsupported_forward_fields": list(UNSUPPORTED_FORWARD_FIELDS),
        "retroactive_universe_disclosure": RETROACTIVE_UNIVERSE_DISCLOSURE,
        "results": {"lane_statuses": lane_statuses, "variants": variants},
    }
    report["report_sha256"] = _report_digest(report)
    validate_report(report)
    return report


def _append_ledger_result(
    report: Mapping[str, object], report_path: Path, *, ledger_dir: Path = Path("ledger")
) -> str:
    from datetime import datetime, timezone

    from research import ledger

    if any(
        record.get("entry_type") == "retrospective_result"
        and record.get("hypothesis_id") == HYPOTHESIS_ID
        for record in ledger.read_all(str(ledger_dir))
    ):
        raise OneRunError("A2 already has a retrospective result in the ledger")
    results = report.get("results", {})
    if not isinstance(results, Mapping):
        raise OneRunError("A2 report results are not an object")
    body = {
        "entry_type": "retrospective_result",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subject": "A2-v1 frozen GREEN-fraction outcome battery",
        "hypothesis_id": HYPOTHESIS_ID,
        "report_sha256": sha256_file(report_path),
        "context_sha256": sha256_file(Path(ENTRY_CONVENTION_REPORT)),
        "prereg_ref_sha256": REGISTRATION_RECORD_HASH,
        "source_commit": _git_head(),
        "labels": [
            "outcome-selected",
            "self-deceiving",
            "descriptive-only",
            "no-verdict",
            "cannot-promote",
        ],
        "result": dict(results),
    }
    return ledger.append(body, base_dir=str(ledger_dir))


def run_once(
    *,
    load_inputs: Callable[[CachePaths], A2LocalInputs] | None = None,
    report_path: Path = Path("reports/a2/a2-v1.json"),
    append_result: bool = False,
    governance_dir: Path = Path("ledger"),
    paths: CachePaths | None = None,
    realism_grade: str | None = None,
    realism_receipt: Path | None = None,
) -> dict[str, object]:
    """Execute the one-run shell, or retry a verified report publication."""
    report_path = Path(report_path)
    if report_path.exists():
        if not append_result:
            raise OneRunError(f"A2 one-run report already exists: {report_path}")
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            validate_report(report)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, OneRunError) as exc:
            raise OneRunError(
                f"existing A2 report failed immutable validation: {report_path}"
            ) from exc
        validate_governance(governance_dir)
        _append_ledger_result(report, report_path, ledger_dir=governance_dir)
        return report
    governance = validate_governance(governance_dir)
    cache_paths = paths or CachePaths.from_overrides()
    loader = load_inputs or _load_local_inputs
    inputs = loader(cache_paths)
    if inputs.audit is not None and inputs.audit.verdict == "BLOCK":
        raise A2RunnerError("A2 data audit BLOCK prevents historical execution")
    diagnostics = inputs.diagnostics or A2Diagnostics()
    outcomes = inputs.outcomes
    signals = (
        inputs.signals if outcomes is not None else (inputs.signals or _reconstruct_signals(inputs))
    )
    if outcomes is None:
        outcomes = build_historical_outcomes(
            signals=signals,
            chains=inputs.chains,
            raw_closes=inputs.raw_closes,
            adjusted_closes=inputs.adjusted_closes,
            features=_panel_feature_values(inputs.features),
            rates=inputs.rates,
            earnings_assertions=inputs.earnings_assertions,
            positions=inputs.positions,
            diagnostics=diagnostics,
        )
    audit = inputs.audit or audit_historical_inputs(
        chains=inputs.chains,
        raw_closes=inputs.raw_closes,
        selected_contracts=diagnostics.selected_contracts,
        eligible_universe=set(config.ATTRACTIVENESS_UNIVERSE),
    )
    if audit.verdict == "BLOCK":
        raise A2RunnerError("A2 data audit BLOCK prevents report writing")
    report = build_report(
        outcomes=outcomes,
        signals=signals,
        audit=audit,
        governance=governance,
        provenance=inputs.provenance,
        diagnostics=diagnostics,
        realism_grade=realism_grade,
        realism_receipt=realism_receipt,
    )
    encoded = (canonical_json(_json_safe(report)) + "\n").encode("utf-8")
    _atomic_create(report_path, encoded)
    try:
        written = report_path.read_bytes()
        if written != encoded:
            raise OneRunError("A2 report bytes changed after exclusive create")
        stored = json.loads(written)
        validate_report(stored)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, OneRunError) as exc:
        raise OneRunError("A2 report failed post-write verification") from exc
    if append_result:
        _append_ledger_result(report, report_path, ledger_dir=governance_dir)
    return report


def _files(path: Path, suffixes: tuple[str, ...] = (".parquet", ".csv")) -> list[Path]:
    if path.is_file():
        return [path]
    return (
        sorted(item for suffix in suffixes for item in path.rglob(f"*{suffix}"))
        if path.exists()
        else []
    )


def _frame(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)


def _hash_path(path: Path) -> str:
    """Hash one local input or a deterministic relative-path directory manifest."""
    if not path.exists():
        return sha256_hex(f"MISSING:{path}")
    if path.is_file():
        return sha256_file(path)
    entries: dict[str, str] = {}
    for item in sorted(item for item in path.rglob("*") if item.is_file()):
        entries[item.relative_to(path).as_posix()] = sha256_file(item)
    return sha256_hex(canonical_json(entries))


def _load_fomc(path: Path) -> list[dict[str, object]]:
    """Load only provenance-bearing FOMC events; legacy dates-only is refused."""
    if not path.exists():
        raise A2RunnerError(f"FOMC provenance-bearing input is unavailable: {path}")
    try:
        frame = pd.read_csv(path)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        raise A2RunnerError(f"FOMC input cannot be read: {path}") from exc
    required = {"date", "known_as_of_utc"}
    if not required.issubset(frame.columns) or not (
        {"source_id", "source", "source_url"} & set(frame.columns)
    ):
        raise A2RunnerError(
            "FOMC provenance is required (date, known_as_of_utc, and source identity)"
        )
    events: list[dict[str, object]] = []
    for row_number, (_, row) in enumerate(frame.iterrows(), start=2):
        try:
            event_date = date.fromisoformat(str(row["date"])[:10])
            known = datetime.fromisoformat(str(row["known_as_of_utc"]).replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise A2RunnerError(f"FOMC row {row_number} has malformed date provenance") from exc
        if known.tzinfo is None or known.utcoffset() is None:
            raise A2RunnerError(f"FOMC row {row_number} known_as_of_utc must be timezone-aware")
        source_key = next(
            key for key in ("source_id", "source", "source_url") if key in frame.columns
        )
        source = str(row[source_key]).strip()
        if not source or source.lower() == "nan":
            raise A2RunnerError(f"FOMC row {row_number} source identity is missing")
        events.append(
            {
                "date": event_date,
                "known_as_of_utc": known.astimezone(timezone.utc),
                source_key: source,
            }
        )
    return events


def _symbol_from_name(path: Path) -> str:
    match = re.match(r"^(.+?)_(?:\d{4}-\d{2}-\d{2}|features)$", path.stem)
    return (match.group(1) if match else path.stem).upper()


def _load_chain_bundle(
    path: Path,
    *,
    common_start: str | None = None,
    file_counts: dict[str, int] | None = None,
    symbols: Sequence[str] | None = None,
) -> dict[str, dict[str, pd.DataFrame]]:
    output: dict[str, dict[str, pd.DataFrame]] = {}
    counts = file_counts if file_counts is not None else {}
    requested = frozenset(symbols or config.ATTRACTIVENESS_UNIVERSE)
    for symbol in requested:
        counts.setdefault(symbol, 0)
    for item in _files(path, (".parquet",)):
        match = re.match(r"^(.+?)_(\d{4}-\d{2}-\d{2})$", item.stem)
        if match is None:
            continue
        symbol, day = match.group(1).upper(), match.group(2)
        if symbol not in requested:
            continue
        if day > config.BACKTEST_END or (common_start is not None and day < common_start):
            continue
        counts[symbol] += 1
        output.setdefault(symbol, {})[day] = _frame(item)
    return output


def _load_close_bundle(
    path: Path,
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    from data.underlying_closes import adjusted_from_raw

    raw: dict[str, dict[str, float]] = {}
    adjusted: dict[str, dict[str, float]] = {}
    explicit_adjusted: set[str] = set()
    for item in _files(path):
        frame = _frame(item)
        symbol = _symbol_from_name(item)
        date_col = "date" if "date" in frame else str(frame.columns[0])
        close_col = "close" if "close" in frame else str(frame.columns[-1])
        adjusted_col = "adjusted_close" if "adjusted_close" in frame else None
        if adjusted_col is not None:
            explicit_adjusted.add(symbol)
        for _, row in frame.iterrows():
            day = str(row[date_col])[:10]
            if day > config.BACKTEST_END:
                continue
            try:
                value = float(row[close_col])
                if not math.isfinite(value):
                    continue
            except (TypeError, ValueError):
                continue
            raw.setdefault(symbol, {})[day] = value
            adjusted_value = row[adjusted_col] if adjusted_col is not None else value
            try:
                adjusted_number = float(adjusted_value)
            except (TypeError, ValueError):
                adjusted_number = value
            adjusted.setdefault(symbol, {})[day] = (
                adjusted_number if math.isfinite(adjusted_number) else value
            )
    for symbol, values in raw.items():
        if symbol not in explicit_adjusted:
            series = pd.Series(values, dtype=float)
            adjusted[symbol] = {
                str(day): float(value) for day, value in adjusted_from_raw(series, symbol).items()
            }
    return raw, adjusted


def _load_feature_bundle(path: Path) -> dict[str, pd.DataFrame]:
    output: dict[str, pd.DataFrame] = {}
    for item in _files(path):
        frame = _frame(item).copy()
        if "date" in frame.columns:
            frame = frame.set_index("date")
        normalized: list[str] = []
        keep: list[int] = []
        for position, value in enumerate(frame.index):
            try:
                day = date.fromisoformat(str(value)[:10]).isoformat()
            except (TypeError, ValueError) as exc:
                raise A2RunnerError(f"feature index is malformed: {item}: {value!r}") from exc
            if day <= config.BACKTEST_END:
                keep.append(position)
                normalized.append(day)
        frame = frame.iloc[keep].copy()
        frame.index = normalized
        if len(set(normalized)) != len(normalized):
            raise A2RunnerError(f"feature index contains duplicate dates: {item}")
        output[_symbol_from_name(item)] = frame.sort_index()
    return output


def _common_feature_start(features: Mapping[str, pd.DataFrame]) -> str:
    starts: dict[str, str] = {}
    for symbol in config.ATTRACTIVENESS_UNIVERSE:
        frame = features.get(symbol)
        if frame is None or frame.empty:
            raise A2RunnerError(f"A2 feature coverage is missing for {symbol}")
        starts[symbol] = min(str(value)[:10] for value in frame.index)
    return max(starts.values())


def _panel_feature_values(
    features: Mapping[str, pd.DataFrame],
) -> dict[str, dict[str, dict[str, float]]]:
    """Adapt the indexed loader view to Task 2's exact-date feature API."""
    output: dict[str, dict[str, dict[str, float]]] = {}
    for symbol, frame in features.items():
        rows: dict[str, dict[str, float]] = {}
        for index, row in frame.iterrows():
            values: dict[str, float] = {}
            for name, value in row.items():
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(number):
                    values[str(name)] = number
            rows[str(index)[:10]] = values
        output[symbol] = rows
    return output


def _load_earnings(
    path: Path,
) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[Mapping[str, object], ...]]]:
    if not path.exists():
        return {}, {}
    records: list[dict[str, object]] = []
    from options_researcher.h7_earnings import load_assertions, report_date

    raw_path = path.parent / "assertions_v2.csv"
    try:
        records = [dict(row) for row in load_assertions(path=path, raw_path=raw_path)]
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise A2RunnerError(f"point-in-time earnings store failed validation: {path}") from exc
    for row in records:
        known = row.get("known_as_of_utc")
        if not isinstance(known, datetime) or known.tzinfo is None or known.utcoffset() is None:
            raise A2RunnerError("earnings known_as_of_utc must be timezone-aware")
        try:
            row["event_date"] = report_date(row).isoformat()
        except (AttributeError, TypeError, ValueError) as exc:
            raise A2RunnerError(f"earnings event date is malformed: {path}") from exc
    grouped: dict[str, list[str]] = {}
    record_grouped: dict[str, list[Mapping[str, object]]] = {}
    for row in records:
        symbol = str(row.get("symbol", "")).upper()
        event = str(row.get("event_date", ""))[:10]
        if symbol and len(event) == 10:
            grouped.setdefault(symbol, []).append(event)
            record_grouped.setdefault(symbol, []).append(row)
    return (
        {symbol: tuple(sorted(set(events))) for symbol, events in grouped.items()},
        {symbol: tuple(rows) for symbol, rows in record_grouped.items()},
    )


def _load_rates(
    path: Path,
    chains: Mapping[str, Mapping[str, pd.DataFrame]],
) -> tuple[dict[str, dict[str, float]], dict[str, str]]:
    from data.rates import risk_free_rate

    candidate = path / "treasury_cmt.csv" if path.is_dir() else path
    if not candidate.exists():
        return {}, {}
    rates: dict[str, dict[str, float]] = {}
    source_dates: dict[str, str] = {}
    for symbol, sessions in chains.items():
        for entry_day, chain in sessions.items():
            selected = select_income_contract(chain, entry_day, right="P")
            if selected is None:
                continue
            expiry = str(selected.get("expiration", ""))[:10]
            try:
                result = risk_free_rate(
                    date.fromisoformat(entry_day), date.fromisoformat(expiry), path=candidate
                )
            except (OSError, TypeError, ValueError):
                continue
            rates.setdefault(symbol, {})[entry_day] = float(result.rate)
            source_dates[f"{symbol}:{entry_day}"] = result.provenance.source_date.isoformat()
    return rates, source_dates


def _load_positions(path: Path) -> tuple[dict[str, object], str]:
    if not path.exists():
        return {}, "no data (positions input absent)"
    files = _files(path)
    if not files:
        return {}, "no data (positions input empty)"
    # The registered Task 2 contract intentionally does not synthesize a PMCC
    # holding from a generic position file.  Reading its header proves the
    # path is local and present while preserving PMCC's no-data status.
    frame = _frame(files[0])
    return {}, f"no data (generic positions header loaded: {len(frame.columns)} columns)"


def _causal_earnings(inputs: A2LocalInputs, symbol: str, day: str) -> tuple[str, ...]:
    records = inputs.earnings_records.get(symbol, ())
    if not records:
        return tuple(inputs.earnings_assertions.get(symbol, ()))
    result: list[str] = []
    cutoff = datetime.combine(date.fromisoformat(day), datetime.max.time(), tzinfo=timezone.utc)
    for record in records:
        event = str(record.get("event_date", ""))[:10]
        known = record.get("known_as_of_utc")
        if not isinstance(known, datetime) or known.tzinfo is None or known.utcoffset() is None:
            raise A2RunnerError("earnings known_as_of_utc must be timezone-aware")
        if known <= cutoff and len(event) == 10:
            result.append(event)
    return tuple(sorted(set(result)))


def _green_fraction(grades: Mapping[str, object]) -> float | None:
    """Frozen RQ1 card score: GREEN count divided by all grade fields."""
    if not grades:
        return None
    return sum(value == "GREEN" for value in grades.values()) / len(grades)


def _rank_cards(cards: Sequence[Mapping[str, object]]) -> list[Mapping[str, object]]:
    """Deterministic RQ1 card ordering kept local to avoid runner imports."""
    scored = []
    for card in cards:
        if "skipped" in card:
            continue
        grades = card.get("grades", {})
        score = _green_fraction(grades if isinstance(grades, Mapping) else {})
        if score is not None:
            scored.append((score, card))
    return [
        card
        for _score, card in sorted(
            scored,
            key=lambda pair: (pair[0], str(pair[1].get("expiry", ""))),
            reverse=True,
        )
    ]


def _causal_fomc(events: Sequence[object], day: date) -> list[date]:
    cutoff = datetime.combine(day, datetime.max.time(), tzinfo=timezone.utc)
    output: list[date] = []
    for event in events:
        if not isinstance(event, Mapping):
            raise A2RunnerError("FOMC event lacks point-in-time provenance")
        event_date = event.get("date")
        known = event.get("known_as_of_utc")
        if not isinstance(event_date, date) or not isinstance(known, datetime):
            raise A2RunnerError("FOMC event provenance is malformed")
        if known.tzinfo is None or known.utcoffset() is None:
            raise A2RunnerError("FOMC event known_as_of_utc must be timezone-aware")
        if known <= cutoff and event_date >= day:
            output.append(event_date)
    return sorted(output)


def _reconstruct_signals(inputs: A2LocalInputs) -> dict[str, dict[str, float]]:
    """Copy RQ1's frozen card recipe across the registered fifteen names."""
    from options_researcher.attractiveness import (
        ladder_cards,
        leaps_card_rows,
        long_call_card_rows,
        put_card_rows,
    )

    if inputs.fomc_events is None:
        if inputs.diagnostics is not None:
            inputs.diagnostics.skip("missing_causal_fomc_provenance")
        return {}

    signals: dict[str, dict[str, float]] = {}
    for symbol in config.ATTRACTIVENESS_UNIVERSE:
        features = inputs.features.get(symbol)
        for day, chain in sorted(inputs.chains.get(symbol, {}).items()):
            if day > config.BACKTEST_END or day not in inputs.raw_closes.get(symbol, {}):
                continue
            if features is None:
                continue
            available = features.loc[features.index.astype(str) <= day]
            if available.empty:
                continue
            feature = available.iloc[-1]
            inputs.feature_as_of[f"{symbol}:{day}"] = str(available.index[-1])[:10]

            def feature_float(name: str, default: float = 0.0) -> float:
                value = feature.get(name, default)
                return default if value is None or pd.isna(value) else float(value)

            try:
                close = float(inputs.raw_closes[symbol][day])
                fomc_dates = _causal_fomc(inputs.fomc_events, date.fromisoformat(day))
                cards: list[dict[str, Any]] = []
                cards.extend(
                    ladder_cards(
                        put_card_rows,
                        symbol,
                        chain,
                        day,
                        rank_key="annualized_yield",
                        higher_is_better=True,
                        close=close,
                        rv21=feature_float("rv21"),
                        iv_rank=feature_float("iv_rank"),
                        iv_minus_rv=feature_float("iv_minus_rv"),
                        earnings_dates=_causal_earnings(inputs, symbol, day),
                        fomc_dates=fomc_dates,
                    )
                )
                cards.extend(
                    ladder_cards(
                        long_call_card_rows,
                        symbol,
                        chain,
                        day,
                        rank_key="breakeven_move",
                        higher_is_better=False,
                        close=close,
                        iv_rank=feature_float("iv_rank"),
                    )
                )
                if symbol in config.H4_THESIS_NAMES:
                    cards.extend(
                        leaps_card_rows(
                            symbol,
                            chain,
                            day,
                            close=close,
                            iv_rank=feature_float("iv_rank"),
                            bucket_room=config.H4_THESIS_MAX_PREMIUM_TOTAL,
                        )
                    )
                ordered = _rank_cards(cards)
                if ordered:
                    grades = ordered[0].get("grades", {})
                    score = _green_fraction(grades if isinstance(grades, Mapping) else {})
                    if score is not None:
                        signals.setdefault(day, {})[symbol] = float(score)
            except (KeyError, TypeError, ValueError, IndexError, OverflowError):
                continue
    return signals


def _load_local_inputs(paths: CachePaths) -> A2LocalInputs:
    features = _load_feature_bundle(paths.features)
    common_start = _common_feature_start(features)
    chain_file_counts: dict[str, int] = {}
    raw, adjusted = _load_close_bundle(paths.underlying)
    earnings, earnings_records = _load_earnings(paths.earnings)
    positions, positions_status = _load_positions(paths.positions)
    fomc_events = _load_fomc(paths.fomc)
    signals: dict[str, dict[str, float]] = {}
    outcomes: list[A2Outcome] = []
    audits: list[A2AuditResult] = []
    diagnostics = A2Diagnostics()
    rate_source_dates: dict[str, str] = {}
    chain_max_as_of: str | None = None
    feature_as_of: dict[str, str] = {}

    for symbol in config.ATTRACTIVENESS_UNIVERSE:
        symbol_chains = _load_chain_bundle(
            paths.chain,
            common_start=common_start,
            file_counts=chain_file_counts,
            symbols=(symbol,),
        )
        symbol_raw = {symbol: raw.get(symbol, {})}
        symbol_adjusted = {symbol: adjusted.get(symbol, {})}
        symbol_diagnostics = A2Diagnostics()
        symbol_inputs = A2LocalInputs(
            signals={},
            chains=symbol_chains,
            raw_closes=symbol_raw,
            adjusted_closes=symbol_adjusted,
            features={symbol: features[symbol]},
            earnings_assertions=earnings,
            earnings_records=earnings_records,
            fomc_events=fomc_events,
            diagnostics=symbol_diagnostics,
        )
        symbol_signals = _reconstruct_signals(symbol_inputs)
        for decision, board in symbol_signals.items():
            signals.setdefault(decision, {}).update(board)
        symbol_rates, source_dates = _load_rates(paths.rates, symbol_chains)
        rate_source_dates.update(source_dates)
        outcomes.extend(
            build_historical_outcomes(
                signals=symbol_signals,
                chains=symbol_chains,
                raw_closes=symbol_raw,
                adjusted_closes=symbol_adjusted,
                features=_panel_feature_values(symbol_inputs.features),
                rates=symbol_rates,
                earnings_assertions=earnings,
                positions=positions,
                diagnostics=symbol_diagnostics,
            )
        )
        audits.append(
            audit_historical_inputs(
                chains=symbol_chains,
                raw_closes=symbol_raw,
                selected_contracts=symbol_diagnostics.selected_contracts,
                audit_start=common_start,
                audit_end=config.BACKTEST_END,
                eligible_universe={symbol},
            )
        )
        diagnostics.skips.update(symbol_diagnostics.skips)
        diagnostics.selected_contracts.update(symbol_diagnostics.selected_contracts)
        diagnostics.max_as_of = max(
            (value for value in (diagnostics.max_as_of, symbol_diagnostics.max_as_of) if value),
            default=None,
        )
        feature_as_of.update(symbol_inputs.feature_as_of)
        chain_max_as_of = max(
            (
                value
                for value in (chain_max_as_of, max(symbol_chains.get(symbol, {}), default=None))
                if value
            ),
            default=None,
        )
        del symbol_chains

    audit = _merge_audits(audits)
    _print_aggregate_audit(audit)
    provenance = {
        "chain_path": str(paths.chain),
        "underlying_path": str(paths.underlying),
        "features_path": str(paths.features),
        "rates_path": str(paths.rates),
        "earnings_path": str(paths.earnings),
        "positions_path": str(paths.positions),
        "common_start": common_start,
        "chain_file_counts": chain_file_counts,
        "chain_max_as_of": chain_max_as_of,
        "close_max_as_of": max((day for days in raw.values() for day in days), default=None),
        "earnings_max_as_of": max(
            (
                str(record.get("known_as_of_utc", ""))[:10]
                for rows in earnings_records.values()
                for record in rows
            ),
            default=None,
        ),
        "rate_source_dates": rate_source_dates,
        "positions_status": positions_status,
        "input_hashes": {
            "chains": _hash_path(paths.chain),
            "underlying_closes": _hash_path(paths.underlying),
            "features": _hash_path(paths.features),
            "rates": _hash_path(paths.rates),
            "earnings": _hash_path(paths.earnings),
            "earnings_raw_lineage": _hash_path(paths.earnings.parent / "assertions_v2.csv"),
            "positions": _hash_path(paths.positions),
            "fomc": _hash_path(paths.fomc),
        },
        "feature_as_of": feature_as_of,
        "fomc_hash": _hash_path(paths.fomc),
    }
    return A2LocalInputs(
        signals=signals,
        chains={},
        raw_closes=raw,
        adjusted_closes=adjusted,
        features=features,
        rates={},
        earnings_assertions=earnings,
        earnings_records=earnings_records,
        fomc_events=fomc_events,
        positions=positions,
        feature_as_of=feature_as_of,
        outcomes=tuple(outcomes),
        diagnostics=diagnostics,
        audit=audit,
        provenance=provenance,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical", action="store_true")
    parser.add_argument("--append-result", action="store_true")
    parser.add_argument("--report", type=Path, default=Path("reports/a2/a2-v1.json"))
    parser.add_argument("--realism-grade", required=True)
    parser.add_argument("--realism-receipt", type=Path, required=True)
    for name in ("chain", "underlying", "features", "rates", "earnings", "positions", "fomc"):
        parser.add_argument(f"--{name}-path", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.historical:
        parser.error("A2 runner requires explicit --historical")
    paths = CachePaths.from_overrides(
        **{
            name: getattr(args, f"{name}_path")
            for name in (
                "chain",
                "underlying",
                "features",
                "rates",
                "earnings",
                "positions",
                "fomc",
            )
        }
    )
    report = run_once(
        report_path=args.report,
        append_result=args.append_result,
        paths=paths,
        realism_grade=args.realism_grade,
        realism_receipt=args.realism_receipt,
    )
    print(
        json.dumps(
            {"schema": report["schema"], "report": str(args.report), "status": report["status"]},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "A2LocalInputs",
    "A2RunnerError",
    "CachePaths",
    "ENTRY_CONVENTION_FACT_TOKEN",
    "ENTRY_CONVENTION_RATIFICATION_FACT_TOKEN",
    "OneRunError",
    "RETROACTIVE_UNIVERSE_DISCLOSURE",
    "build_report",
    "main",
    "run_once",
    "validate_governance",
    "validate_report",
]
