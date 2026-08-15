"""One-shot, local-cache-only controller for the exploratory A2 battery.

The controller is deliberately a thin boundary around :mod:`a2_panel` and
:mod:`a2_battery`.  It validates the registration before touching a loader,
keeps incomplete fifteen-name boards out of inference, and writes one
immutable report before an optional explicit ledger publication.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import pandas as pd

import config
from options_researcher.a2_battery import (
    LANE_ARMS,
    A2Outcome,
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
UNSUPPORTED_FORWARD_FIELDS = (
    "forward_dates",
    "forward_adverse_gate_adjudication",
    "pmcc_synthetic_position_convention",
    "forward_verdict",
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

    @classmethod
    def from_overrides(cls, **overrides: str | Path | None) -> "CachePaths":
        defaults = {
            "chain": Path(".cache/chains"),
            "underlying": Path(".cache/underlying"),
            "features": Path(".tmp/research/attractiveness"),
            "rates": Path("data/rates"),
            "earnings": Path("data/earnings/gating_v3.csv"),
            "positions": Path(".cache/positions"),
        }
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
        )


@dataclass(slots=True)
class A2LocalInputs:
    signals: Mapping[str, Mapping[str, float]]
    chains: Mapping[str, Mapping[str, pd.DataFrame]]
    raw_closes: Mapping[str, Mapping[str, float]]
    adjusted_closes: Mapping[str, Mapping[str, float]]
    features: Mapping[str, Any] = field(default_factory=dict)
    rates: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    earnings_assertions: Mapping[str, Sequence[str]] = field(default_factory=dict)
    earnings_records: Mapping[str, Sequence[Mapping[str, object]]] = field(default_factory=dict)
    fomc_events: Sequence[object] | None = None
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


def validate_report(report: Mapping[str, object]) -> None:
    if not isinstance(report, Mapping):
        raise OneRunError("A2 report is not an object")
    if report.get("schema") != REPORT_SCHEMA or report.get("hypothesis_id") != HYPOTHESIS_ID:
        raise OneRunError("A2 report schema or hypothesis identity is invalid")
    if report.get("registration_seq") != REGISTRATION_SEQ:
        raise OneRunError("A2 report registration sequence is invalid")
    if report.get("status") != "RESEARCH-ONLY / NO VERDICT":
        raise OneRunError("A2 report status is not research-only")

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
    if not isinstance(report.get("lane_statuses"), Mapping):
        raise OneRunError("A2 report lane statuses are missing")
    if not isinstance(report.get("provenance"), Mapping):
        raise OneRunError("A2 report provenance is missing")
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
    if not any(PIN_FACT_TOKEN in line for line in lines):
        raise A2RunnerError(f"A2 prerequisite fact {PIN_FACT_TOKEN} is missing")
    if not any(
        ENTRY_CONVENTION_FACT_TOKEN in line and ENTRY_CONVENTION_REPORT in line for line in lines
    ):
        raise A2RunnerError("owner-approved A2 entry-convention fact is missing")
    return {
        "registration_seq": REGISTRATION_SEQ,
        "registration_hash": REGISTRATION_RECORD_HASH,
        "pin_fact": PIN_FACT_TOKEN,
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
    rows = tuple(row for row in outcomes if row.lane == lane and row.arm == arm)
    grouped: dict[str, list[A2Outcome]] = {}
    for row in rows:
        grouped.setdefault(row.decision_date, []).append(row)
    complete: list[A2Outcome] = []
    incomplete = 0
    missing_by_date: dict[str, list[str]] = {}
    for decision, cohort in sorted(grouped.items()):
        observed = {row.symbol for row in cohort}
        expected = set(config.A2_UNIVERSE)
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
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
        if observed == expected and len(cohort) == len(expected) and score_identity:
            complete.extend(sorted(cohort, key=lambda row: row.symbol))
        else:
            incomplete += 1
            missing_by_date[decision] = missing + [f"extra:{symbol}" for symbol in extra]
    return (
        tuple(complete),
        rows,
        {
            "incomplete_cohorts": incomplete,
            "missing_names": missing_by_date,
            "original_bucket_identity_preserved": not incomplete and bool(grouped),
        },
    )


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
) -> dict[str, object]:
    if audit.verdict == "BLOCK":
        raise A2RunnerError("A2 data audit BLOCK prevents report assembly")
    variants: list[dict[str, object]] = []
    lane_statuses: dict[str, object] = {}
    for lane, arms in LANE_ARMS.items():
        lane_variants: list[dict[str, object]] = []
        for arm in arms:
            inference, descriptive, exclusions = _variant_rows(outcomes, signals, lane, arm)
            summary = summarize_lane(inference, lane=lane, arm=arm)
            row = _summary_dict(summary, exclusions=exclusions, descriptive_count=len(descriptive))
            row["lane"], row["arm"] = lane, arm
            row["status"] = summary.status
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
        "realism_grade": provenance.get("realism_grade", "UNASSESSED"),
    }
    if diagnostics is not None:
        provenance_payload["exclusion_counts"] = dict(diagnostics.skips)
        provenance_payload["pmcc_status"] = diagnostics.pmcc_status
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
    signals = inputs.signals or _reconstruct_signals(inputs)
    if outcomes is None:
        outcomes = build_historical_outcomes(
            signals=signals,
            chains=inputs.chains,
            raw_closes=inputs.raw_closes,
            adjusted_closes=inputs.adjusted_closes,
            features=inputs.features,
            rates=inputs.rates,
            earnings_assertions=inputs.earnings_assertions,
            positions=inputs.positions,
            diagnostics=diagnostics,
        )
    audit = inputs.audit or audit_historical_inputs(
        chains=inputs.chains,
        raw_closes=inputs.raw_closes,
        selected_contracts=diagnostics.selected_contracts,
        eligible_universe=set(config.A2_UNIVERSE),
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
    )
    encoded = (canonical_json(_json_safe(report)) + "\n").encode("utf-8")
    _atomic_create(report_path, encoded)
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


def _symbol_from_name(path: Path) -> str:
    match = re.match(r"^(.+?)_(?:\d{4}-\d{2}-\d{2}|features)$", path.stem)
    return (match.group(1) if match else path.stem).upper()


def _load_chain_bundle(path: Path) -> dict[str, dict[str, pd.DataFrame]]:
    output: dict[str, dict[str, pd.DataFrame]] = {}
    for item in _files(path, (".parquet",)):
        match = re.match(r"^(.+?)_(\d{4}-\d{2}-\d{2})$", item.stem)
        if match is None:
            continue
        if match.group(2) > config.BACKTEST_END:
            continue
        output.setdefault(match.group(1).upper(), {})[match.group(2)] = _frame(item)
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
    return {_symbol_from_name(item): _frame(item).sort_index() for item in _files(path)}


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
    for record in records:
        event = str(record.get("event_date", ""))[:10]
        known = record.get("known_as_of_utc")
        if known is None or str(known)[:10] <= day:
            if len(event) == 10:
                result.append(event)
    return tuple(sorted(set(result)))


def _reconstruct_signals(inputs: A2LocalInputs) -> dict[str, dict[str, float]]:
    """Copy RQ1's frozen card recipe across the registered fifteen names."""
    from options_researcher.attractiveness import (
        ladder_cards,
        leaps_card_rows,
        long_call_card_rows,
        put_card_rows,
    )
    from options_researcher.rq1_runner import _point_in_time_fomc, green_fraction

    if inputs.fomc_events is None:
        if inputs.diagnostics is not None:
            inputs.diagnostics.skip("missing_causal_fomc_provenance")
        return {}

    signals: dict[str, dict[str, float]] = {}
    for symbol in config.A2_UNIVERSE:
        features = inputs.features.get(symbol)
        for day, chain in sorted(inputs.chains.get(symbol, {}).items()):
            if day > config.BACKTEST_END or day not in inputs.raw_closes.get(symbol, {}):
                continue
            if not isinstance(features, pd.DataFrame):
                continue
            available = features.loc[features.index.astype(str) <= day]
            if available.empty:
                continue
            feature = available.iloc[-1]

            def feature_float(name: str, default: float = 0.0) -> float:
                value = feature.get(name, default)
                return default if value is None or pd.isna(value) else float(value)

            try:
                close = float(inputs.raw_closes[symbol][day])
                fomc_dates = _point_in_time_fomc(inputs.fomc_events, date.fromisoformat(day))
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
                scored = [
                    (green_fraction(card.get("grades", {})), card)
                    for card in cards
                    if "skipped" not in card
                ]
                scored = [(score, card) for score, card in scored if score is not None]
                if scored:
                    best = max(scored, key=lambda pair: (pair[0], str(pair[1].get("expiry", ""))))
                    signals.setdefault(day, {})[symbol] = float(best[0])
            except (KeyError, TypeError, ValueError, IndexError, OverflowError):
                continue
    return signals


def _load_local_inputs(paths: CachePaths) -> A2LocalInputs:
    chains = _load_chain_bundle(paths.chain)
    raw, adjusted = _load_close_bundle(paths.underlying)
    features = _load_feature_bundle(paths.features)
    earnings, earnings_records = _load_earnings(paths.earnings)
    rates, rate_source_dates = _load_rates(paths.rates, chains)
    positions, positions_status = _load_positions(paths.positions)
    try:
        from options_researcher.fomc import load_fomc

        fomc_events = load_fomc()
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise A2RunnerError("causal FOMC calendar is unavailable") from exc
    if any(not isinstance(event, Mapping) for event in fomc_events):
        raise A2RunnerError("causal FOMC calendar lacks provenance-bearing rows")
    seed = A2LocalInputs(
        signals={},
        chains=chains,
        raw_closes=raw,
        adjusted_closes=adjusted,
        features=features,
        earnings_assertions=earnings,
        earnings_records=earnings_records,
        fomc_events=fomc_events,
    )
    signals = _reconstruct_signals(seed)
    provenance = {
        "chain_path": str(paths.chain),
        "underlying_path": str(paths.underlying),
        "features_path": str(paths.features),
        "rates_path": str(paths.rates),
        "earnings_path": str(paths.earnings),
        "positions_path": str(paths.positions),
        "chain_max_as_of": max((day for days in chains.values() for day in days), default=None),
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
    }
    return A2LocalInputs(
        signals=signals,
        chains=chains,
        raw_closes=raw,
        adjusted_closes=adjusted,
        features=features,
        rates=rates,
        earnings_assertions=earnings,
        earnings_records=earnings_records,
        fomc_events=fomc_events,
        positions=positions,
        provenance=provenance,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical", action="store_true")
    parser.add_argument("--append-result", action="store_true")
    parser.add_argument("--report", type=Path, default=Path("reports/a2/a2-v1.json"))
    for name in ("chain", "underlying", "features", "rates", "earnings", "positions"):
        parser.add_argument(f"--{name}-path", type=Path)
    args = parser.parse_args(argv)
    if not args.historical:
        parser.error("A2 runner requires explicit --historical")
    paths = CachePaths.from_overrides(
        **{
            name: getattr(args, f"{name}_path")
            for name in ("chain", "underlying", "features", "rates", "earnings", "positions")
        }
    )
    report = run_once(report_path=args.report, append_result=args.append_result, paths=paths)
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
    "OneRunError",
    "build_report",
    "main",
    "run_once",
    "validate_governance",
    "validate_report",
]
