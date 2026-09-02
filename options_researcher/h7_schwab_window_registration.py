"""Registration builder for the read-only Schwab H7 restart namespace.

BUILD-ONLY; SYNTHETIC-ONLY through :func:`register_window`; INACTIVE. This
module does not expose a CLI and does not activate either authority switch.
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime, timezone
from pathlib import Path

import config
from data.cache_runner import session_close_utc, trading_days
from options_researcher import h7_data_gate, h7_schwab_data_gate
from options_researcher import h7_event_ledger as ledger
from options_researcher import h7_window_registration as old_registration
from options_researcher.h7_paper_lifecycle import ActivationBoundaryError
from options_researcher.h7_scope import scope_identity
from options_researcher.h7_scoring_identity import (
    REGISTRATION_CONTRACT_FIELD,
    REGISTRATION_HASH_FIELD,
    STAGE456_PARAMETER_NAMES,
    build_scoring_identity,
)
from research.hashing import (
    canonical_json,
    config_hash,
    cost_model_hash,
    sha256_file,
    sha256_hex,
    source_hash,
)

NAMESPACE = "h7-forward-schwab-v1"
SCHWAB_FORWARD_STORE = Path("ledger/h7_forward_schwab")
CACHE_NAMESPACE = ".cache/schwab_chains/"
SESSION_CHAIN_CONVENTION = "preclose_snapshot_v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
FEASIBILITY_DATA_ROOT = REPO_ROOT
FEASIBILITY_SOURCE_PATHS = (
    "tools/h7_schwab_feasibility.py",
    "tools/h7_entry_variant_menu.py",
    "options_researcher/h7_schwab_window_registration.py",
    "options_researcher/h7_watch.py",
    "options_researcher/h7_board.py",
    "options_researcher/h7_earnings.py",
    "options_researcher/chains.py",
    "data/cache_runner.py",
    "data/underlying_closes.py",
)
INHERITED_TRIM_RULE = "inherited_seq0_cohort_2026-07-20"
SCHWAB_ACTIVATION_SPEC_PATH = (
    REPO_ROOT / "docs/superpowers/specs/2026-09-02-h7-schwab-activation-spec.md"
)
# Single source of truth for the feasibility receipt's identity labels. The
# measurement tool (tools/h7_schwab_feasibility.py) imports these rather than
# repeating the literals, so the producer and this validator cannot drift
# apart unnoticed (round-1 finding F7); a test asserts both sides bind to the
# same objects.
FEASIBILITY_RECEIPT_KIND = "h7_schwab_feasibility/v1"
FEASIBILITY_STACK_VERSION = "h7-frozen-entry-stack-plus-board/v1"
FEASIBILITY_TOOL_LABEL = "cached-only read-only measurement; no verdict"
STARVATION_PREACCEPTANCE_FIELD = "SCHWAB_STARVATION_RISK_PREACCEPTANCE"

RegistrationInputError = old_registration.RegistrationInputError
WindowRuleError = old_registration.WindowRuleError
ActivationRefused = old_registration.ActivationRefused
GUARD_REPORT_MAX_AGE_S = old_registration.GUARD_REPORT_MAX_AGE_S

OWNER_FIELDS = (
    "H7_STAGE8_EXPLICIT_AUTHORIZATION",
    "WINDOW_START_DECISION_SESSION",
    "WINDOW_DECISION_SESSION_COUNT",
    "WINDOW_END_RULE_ACKNOWLEDGED",
    "WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED",
    "SCHWAB_CAPTURE_LANE_VERIFIED_THROUGH",
    "SCHWAB_CAPTURE_COMMITMENT_THROUGH",
    "SCHWAB_CONFIRMATION_EVIDENCE",
    "SESSION_CHAIN_CONVENTION",
    "SCHWAB_MIN_LOSSES_FOR_VERDICT",
    "SCHWAB_STARVATION_RISK_PREACCEPTANCE",
)
EVIDENCE_FIELDS = (
    "review_evidence",
    "activation_spec_sha256",
    "code_commit",
    "source_health_evidence_id",
    "data_gate_evidence_id",
    "data_gate_evidence_mode",
    "source_health_receipt_hash",
    "data_gate_receipt",
    "data_gate_receipt_hash",
    "last_historical_session",
    "last_historical_manifest_receipt_hash",
    "provider_identity",
    "cache_namespace",
    "feasibility_receipt",
    "feasibility_receipt_hash",
    "darwin_durability_verified",
    "pre_append_state",
)
FEASIBILITY_FIELDS = (
    "receipt_kind",
    "provenance",
    "lookback_start",
    "lookback_end",
    "stack_version",
    "tool_label",
    "code_sha",
    "config_hash",
    "universe",
    "universe_size",
    "window_sessions",
    "symbol_days",
    "full_stack_passes",
    "passing_symbol_days",
    "lookback_sessions",
    "sessions",
    "base_rate",
    "expected_entries",
    "occupancy_constrained_expected_entries",
    "occupancy_constrained_count",
    "occupancy_input_rows",
    "occupancy_lockout_sessions",
    "occupancy_upper_bound",
    "input_files",
    "source_paths",
    "source_hash",
    "errors",
    "error_count",
    "receipt_hash",
)


def _require(mapping: dict, fields: tuple[str, ...], label: str) -> None:
    for field in fields:
        if mapping.get(field) in (None, ""):
            raise RegistrationInputError(
                f"{label} input {field!r} is missing/None/empty; no default may be inferred"
            )


def _validate_durability_evidence(evidence: dict) -> None:
    value = evidence["darwin_durability_verified"]
    if type(value) is not bool:
        raise RegistrationInputError(
            "evidence input 'darwin_durability_verified' must be a JSON boolean"
        )
    if value is not True:
        raise RegistrationInputError("Darwin durability evidence is not verified")


def _canonical_date(value: object, label: str) -> str:
    try:
        parsed = date.fromisoformat(str(value))
    except ValueError as exc:
        raise RegistrationInputError(f"{label} must be YYYY-MM-DD") from exc
    if parsed.isoformat() != str(value):
        raise RegistrationInputError(f"{label} must be canonical YYYY-MM-DD")
    return parsed.isoformat()


def _expected_feasibility_input_paths(universe: list[str], sessions: list[str]) -> dict[str, str]:
    expected = {
        "gating_assertions": "data/earnings/gating_v3.csv",
        "raw_assertions": "data/earnings/assertions_v2.csv",
    }
    for symbol in universe:
        expected[f"underlying:{symbol}"] = f".cache/underlying/{symbol}.parquet"
        for session in sessions:
            expected[f"chain:{symbol}:{session}"] = f".cache/chains/{symbol}_{session}.parquet"
    return expected


def _validate_feasibility(receipt: dict, claimed_hash: str) -> float:
    if not isinstance(receipt, dict):
        raise RegistrationInputError("feasibility_receipt must be an object")
    _require(receipt, FEASIBILITY_FIELDS, "feasibility receipt")
    embedded_hash = receipt["receipt_hash"]
    unhashed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    computed = sha256_hex(canonical_json(unhashed))
    if embedded_hash != computed or claimed_hash != computed:
        raise RegistrationInputError(
            "feasibility receipt hash mismatch; payload may have been tampered"
        )
    if receipt["receipt_kind"] != FEASIBILITY_RECEIPT_KIND:
        raise RegistrationInputError("unexpected feasibility receipt kind")
    if receipt["provenance"] != "LLM/tool-computed":
        raise RegistrationInputError("feasibility provenance must be LLM/tool-computed")
    if receipt["stack_version"] != FEASIBILITY_STACK_VERSION:
        raise RegistrationInputError("feasibility stack identity is not registered")
    if receipt["tool_label"] != FEASIBILITY_TOOL_LABEL:
        raise RegistrationInputError("feasibility tool identity is not registered")
    if receipt["config_hash"] != config_hash():
        raise RegistrationInputError(
            "feasibility receipt config_hash disagrees with registration-time config"
        )

    recorded_paths = receipt["source_paths"]
    if recorded_paths != list(FEASIBILITY_SOURCE_PATHS):
        raise RegistrationInputError(
            "feasibility source_paths disagrees with the frozen computation surface"
        )
    missing_source = [path for path in FEASIBILITY_SOURCE_PATHS if not (REPO_ROOT / path).is_file()]
    if missing_source:
        raise RegistrationInputError(
            f"feasibility computation source path is missing: {missing_source}"
        )
    if receipt["source_hash"] != source_hash(paths=FEASIBILITY_SOURCE_PATHS, root=REPO_ROOT):
        raise RegistrationInputError("feasibility computation source hash mismatch")

    errors = receipt["errors"]
    error_count = receipt["error_count"]
    if (
        not isinstance(errors, list)
        or type(error_count) is not int
        or error_count != len(errors)
        or error_count != 0
    ):
        raise RegistrationInputError("feasibility receipt contains measurement errors")

    universe = receipt["universe"]
    sessions = receipt["sessions"]
    if (
        not isinstance(universe, list)
        or not universe
        or any(not isinstance(symbol, str) or symbol != symbol.upper() for symbol in universe)
        or len(set(universe)) != len(universe)
        or not isinstance(sessions, list)
        or not sessions
        or len(set(sessions)) != len(sessions)
    ):
        raise RegistrationInputError("feasibility universe or sessions are malformed")
    try:
        canonical_sessions = [date.fromisoformat(session).isoformat() for session in sessions]
    except (TypeError, ValueError) as exc:
        raise RegistrationInputError("feasibility sessions must be canonical dates") from exc
    if canonical_sessions != sessions:
        raise RegistrationInputError("feasibility sessions must be canonical dates")
    lookback = receipt["lookback_sessions"]
    window_sessions = receipt["window_sessions"]
    if (
        type(lookback) is not int
        or type(window_sessions) is not int
        or lookback != len(sessions)
        or window_sessions != lookback
        or receipt["lookback_start"] != sessions[0]
        or receipt["lookback_end"] != sessions[-1]
    ):
        raise RegistrationInputError(
            "feasibility lookback panel must exactly equal the registration window"
        )

    expected_paths = _expected_feasibility_input_paths(universe, sessions)
    input_files = receipt["input_files"]
    if not isinstance(input_files, dict) or set(input_files) != set(expected_paths):
        raise RegistrationInputError(
            "feasibility input_files does not equal the derived complete input set"
        )
    for label, expected_path in expected_paths.items():
        item = input_files.get(label)
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise RegistrationInputError("feasibility input_files is malformed")
        raw_path = item["path"]
        claimed_input_hash = item["sha256"]
        if raw_path != expected_path:
            raise RegistrationInputError(
                f"feasibility input path mismatch for {label}: {raw_path!r}"
            )
        relative = Path(raw_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise RegistrationInputError("feasibility input path must be repo-relative")
        path = (FEASIBILITY_DATA_ROOT / relative).resolve()
        try:
            path.relative_to(FEASIBILITY_DATA_ROOT.resolve())
        except ValueError as exc:
            raise RegistrationInputError("feasibility input path escapes the repository") from exc
        if not path.is_file():
            raise RegistrationInputError(f"feasibility input file is missing: {raw_path}")
        if not isinstance(claimed_input_hash, str) or sha256_file(path) != claimed_input_hash:
            raise RegistrationInputError(f"feasibility input hash mismatch: {raw_path}")

    universe_size = receipt["universe_size"]
    symbol_days = receipt["symbol_days"]
    passing_rows = receipt["passing_symbol_days"]
    if (
        type(universe_size) is not int
        or universe_size != len(universe)
        or type(symbol_days) is not int
        or symbol_days != len(sessions) * len(universe)
        or not isinstance(passing_rows, list)
    ):
        raise RegistrationInputError("invalid feasibility census")
    try:
        passing_pairs = {
            (row["session"], row["symbol"])
            for row in passing_rows
            if set(row) == {"session", "symbol"}
        }
    except (KeyError, TypeError) as exc:
        raise RegistrationInputError("passing_symbol_days is malformed") from exc
    if len(passing_pairs) != len(passing_rows) or any(
        session not in sessions or symbol not in universe for session, symbol in passing_pairs
    ):
        raise RegistrationInputError("passing_symbol_days is outside the census")
    passes = receipt["full_stack_passes"]
    if type(passes) is not int or passes != len(passing_pairs):
        raise RegistrationInputError("invalid feasibility pass count")
    base_rate = passes / symbol_days
    expected = base_rate * window_sessions * universe_size
    if not math.isclose(float(receipt["base_rate"]), base_rate, rel_tol=1e-12):
        raise RegistrationInputError("feasibility base_rate arithmetic mismatch")
    if not math.isclose(float(receipt["expected_entries"]), expected, rel_tol=1e-12):
        raise RegistrationInputError("feasibility expected_entries arithmetic mismatch")

    from tools.h7_entry_variant_menu import (
        OCCUPANCY_LOCKOUT_SESSIONS,
        occupancy_constrained_count,
    )

    lockout = receipt["occupancy_lockout_sessions"]
    registered_lockout = OCCUPANCY_LOCKOUT_SESSIONS[0]
    if type(lockout) is not int or lockout != registered_lockout:
        raise RegistrationInputError(
            "feasibility receipt occupancy lockout is not the registered value "
            f"({registered_lockout})"
        )
    occupancy_rows = receipt["occupancy_input_rows"]
    if not isinstance(occupancy_rows, list) or any(
        not isinstance(row, dict)
        or set(row) != {"session", "symbol", "lane"}
        or row["session"] not in sessions
        or row["symbol"] not in universe
        or not isinstance(row["lane"], str)
        for row in occupancy_rows
    ):
        raise RegistrationInputError("occupancy input rows are malformed")
    if {(row["session"], row["symbol"]) for row in occupancy_rows} != passing_pairs or len(
        occupancy_rows
    ) != len(passing_pairs):
        raise RegistrationInputError("occupancy input rows disagree with passing_symbol_days")
    occupancy_count = occupancy_constrained_count(occupancy_rows, sessions, registered_lockout)
    if receipt["occupancy_constrained_count"] != occupancy_count:
        raise RegistrationInputError("occupancy-constrained count mismatch")
    occupancy = receipt["occupancy_constrained_expected_entries"]
    if (
        isinstance(occupancy, bool)
        or not isinstance(occupancy, (int, float))
        or not math.isfinite(float(occupancy))
        or not math.isclose(float(occupancy), float(occupancy_count), rel_tol=1e-12)
    ):
        raise RegistrationInputError("occupancy-constrained expected entries arithmetic mismatch")
    if receipt["occupancy_upper_bound"] is not True:
        raise RegistrationInputError(
            "occupancy-constrained figure must be labeled upper_bound: true"
        )
    return float(occupancy)


def _activation_spec_loss_bar() -> int:
    try:
        text = SCHWAB_ACTIVATION_SPEC_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise RegistrationInputError("Schwab activation spec is missing") from exc
    matches = re.findall(r"(?m)^schwab_min_losses_for_verdict=([0-9]+)$", text)
    if len(matches) != 1:
        raise RegistrationInputError(
            "Schwab activation spec must contain exactly one canonical loss-bar token"
        )
    return int(matches[0])


def _validate_feasibility_gate(receipt: dict, owner: dict) -> str:
    bar = owner["SCHWAB_MIN_LOSSES_FOR_VERDICT"]
    if type(bar) is not int or bar <= 0:
        raise RegistrationInputError(
            "SCHWAB_MIN_LOSSES_FOR_VERDICT must be a positive owner-typed integer"
        )
    spec_bar = _activation_spec_loss_bar()
    if bar != spec_bar:
        raise RegistrationInputError(
            "SCHWAB_MIN_LOSSES_FOR_VERDICT disagrees with activation-spec token "
            f"schwab_min_losses_for_verdict={spec_bar}"
        )
    expected = float(receipt["occupancy_constrained_expected_entries"])
    if receipt.get("occupancy_upper_bound") is not True:
        raise RegistrationInputError(
            "feasibility figure is not the required upper_bound measurement"
        )
    text = owner.get(STARVATION_PREACCEPTANCE_FIELD)
    if not isinstance(text, str) or not text.strip():
        raise RegistrationInputError(
            "upper-bound feasibility figure requires owner-typed starvation pre-acceptance"
        )
    matches = re.findall(
        r"(?<![A-Za-z0-9_])occupancy_constrained_expected_entries="
        r"([0-9]+(?:\.[0-9]+)?)(?![0-9.])",
        text,
    )
    number = format(expected, ".15g")
    quoted = matches[0] if len(matches) == 1 else "missing-or-duplicated-token"
    matches_expected = len(matches) == 1 and matches[0] == number
    if not matches_expected:
        raise RegistrationInputError(
            "starvation pre-acceptance token must quote the occupancy-constrained "
            f"expected entries exactly: receipt figure {number}, "
            f"pre-acceptance token {quoted}"
        )
    return text


def _legacy_registered_universe() -> dict:
    events = ledger.read_events(REPO_ROOT / "ledger/h7_forward")
    registrations = [event for event in events if event.event_type == "window_registration"]
    if len(registrations) != 1 or registrations[0].seq != 0:
        raise RegistrationInputError("legacy seq-0 window registration is missing or ambiguous")
    manifest = registrations[0].payload.get("universe")
    if not isinstance(manifest, dict):
        raise RegistrationInputError("legacy seq-0 universe manifest is missing")
    return manifest


def _validate_schwab_universe_manifest(manifest: dict) -> None:
    if not isinstance(manifest, dict):
        raise RegistrationInputError("universe_manifest must be owner-typed at use time")
    old_registration._validate_universe_manifest(manifest)
    scope = scope_identity()
    if (
        manifest.get("scope_id") != scope["scope_id"]
        or manifest.get("scope_hash") != scope["scope_hash"]
    ):
        raise RegistrationInputError("universe manifest is not bound to H7 scope")
    included = manifest.get("included")
    excluded = manifest.get("excluded")
    if (
        not isinstance(included, list)
        or len(included) != len(set(included))
        or any(not isinstance(symbol, str) or not symbol for symbol in included)
        or not isinstance(excluded, list)
        or any(
            not isinstance(row, dict)
            or set(row) != {"symbol", "reason"}
            or not isinstance(row["symbol"], str)
            or not row["symbol"]
            or not isinstance(row["reason"], str)
            or not row["reason"].strip()
            for row in excluded
        )
    ):
        raise RegistrationInputError(
            "owner-typed cohort manifest is malformed or has a blank exclusion reason"
        )
    excluded_symbols = [row["symbol"] for row in excluded]
    if len(excluded_symbols) != len(set(excluded_symbols)):
        raise RegistrationInputError("owner-typed cohort has duplicate excluded names")
    if set(included) & set(excluded_symbols) or set(included) | set(excluded_symbols) != set(
        scope["symbols"]
    ):
        raise RegistrationInputError(
            "included and excluded names must exactly partition the official H7 scope"
        )
    inherited = _legacy_registered_universe()
    inherited_included = set(inherited.get("included") or [])
    inherited_excluded = {
        row.get("symbol") for row in inherited.get("excluded") or [] if isinstance(row, dict)
    }
    if set(included) != inherited_included or set(excluded_symbols) != inherited_excluded:
        raise RegistrationInputError(
            "owner-typed cohort must equal the inherited legacy seq-0 symbol sets"
        )
    if manifest.get("trim_rule") != INHERITED_TRIM_RULE:
        raise RegistrationInputError(f"trim_rule must equal {INHERITED_TRIM_RULE!r}")


def _validate_data_gate_receipt(
    receipt: dict,
    claimed_hash: str,
    claimed_source_health_hash: str,
    universe_manifest: dict,
    historical_session: str,
) -> None:
    if not isinstance(receipt, dict):
        raise RegistrationInputError("data-gate receipt must be an object")
    try:
        verified_symbols = h7_data_gate.validate_durable_receipt(receipt)
    except (OSError, ValueError) as exc:
        raise RegistrationInputError(
            f"data-gate receipt failed durable verification: {exc}"
        ) from exc
    if receipt.get("receipt_hash") != claimed_hash:
        raise RegistrationInputError("data-gate receipt hash mismatch")
    if receipt.get("source_health_receipt_hash") != claimed_source_health_hash:
        raise RegistrationInputError(
            "data-gate receipt source-health hash disagrees with registration evidence"
        )
    if receipt.get("evidence_mode") != h7_schwab_data_gate.EVIDENCE_MODE:
        raise RegistrationInputError("data-gate receipt is not Schwab evidence")
    if receipt.get("evaluation_session") != historical_session:
        raise RegistrationInputError("data-gate receipt session disagrees with registered history")
    official_scope = scope_identity()
    official_symbols = official_scope["symbols"]
    if receipt.get("config_hash") != config_hash():
        raise RegistrationInputError(
            "data-gate receipt config_hash disagrees with registration-time config"
        )
    if receipt.get("universe") != official_symbols:
        raise RegistrationInputError("data-gate receipt does not cover the full official scope")
    if verified_symbols != official_symbols:
        raise RegistrationInputError(
            "verified data-gate symbols disagree with the full official scope"
        )
    scope = receipt.get("scope")
    if not isinstance(scope, dict) or (
        scope.get("scope_id") != universe_manifest["scope_id"]
        or scope.get("scope_hash") != universe_manifest["scope_hash"]
    ):
        raise RegistrationInputError("data-gate receipt scope disagrees with registration cohort")
    if universe_manifest.get("excluded"):
        per_symbol = receipt.get("symbols")
        not_go = [
            symbol
            for symbol in universe_manifest["included"]
            if not isinstance(per_symbol, dict) or per_symbol.get(symbol, {}).get("verdict") != "GO"
        ]
        if not_go:
            raise RegistrationInputError(
                f"included Schwab cohort names are not data-gate GO: {not_go}"
            )
    elif (
        receipt.get("whole_universe_verdict") != "GO"
        or receipt.get("go_count") != len(official_symbols)
        or receipt.get("no_go_count") != 0
    ):
        raise RegistrationInputError("untrimmed data-gate receipt is not a whole-universe GO")
    for field in ("schwab_manifest_hash", "schwab_capture_receipt_hash"):
        value = receipt.get(field)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)
        ):
            raise RegistrationInputError(f"data-gate receipt lacks a valid {field} binding")


def build_window_registration_event(
    *,
    owner: dict,
    evidence: dict,
    universe_manifest: dict,
) -> dict:
    """Build, but never append, the Schwab namespace registration event."""
    _require(owner, OWNER_FIELDS, "owner")
    _require(evidence, EVIDENCE_FIELDS, "evidence")
    _validate_durability_evidence(evidence)
    if evidence["data_gate_evidence_mode"] != h7_schwab_data_gate.EVIDENCE_MODE:
        raise RegistrationInputError(
            f"data_gate_evidence_mode must equal {h7_schwab_data_gate.EVIDENCE_MODE!r}"
        )
    if owner["SESSION_CHAIN_CONVENTION"] != SESSION_CHAIN_CONVENTION:
        raise RegistrationInputError(
            f"SESSION_CHAIN_CONVENTION must equal {SESSION_CHAIN_CONVENTION!r}"
        )
    if evidence["cache_namespace"] != CACHE_NAMESPACE:
        raise RegistrationInputError(f"cache_namespace must equal {CACHE_NAMESPACE!r}")

    start = _canonical_date(owner["WINDOW_START_DECISION_SESSION"], "window start")
    count = int(owner["WINDOW_DECISION_SESSION_COUNT"])
    end = old_registration.derive_window_end(start, count)
    commitment = _canonical_date(
        owner["SCHWAB_CAPTURE_COMMITMENT_THROUGH"],
        "Schwab capture commitment",
    )
    if commitment < end:
        raise WindowRuleError(
            f"Schwab capture commitment only through {commitment}, short of window end {end}"
        )
    verified_through = _canonical_date(
        owner["SCHWAB_CAPTURE_LANE_VERIFIED_THROUGH"],
        "Schwab capture lane verified through",
    )
    historical_session = _canonical_date(
        evidence["last_historical_session"], "last historical session"
    )
    if verified_through != historical_session:
        raise RegistrationInputError(
            "SCHWAB_CAPTURE_LANE_VERIFIED_THROUGH must equal the bound last historical session"
        )
    if start <= historical_session:
        raise RegistrationInputError(
            "window start must be strictly later than the last historical session"
        )
    if trading_days(start, start) != [start]:
        raise RegistrationInputError("window start must be an XNYS trading session")

    _validate_schwab_universe_manifest(universe_manifest)
    manifest = universe_manifest
    scope = scope_identity()
    feasibility = evidence["feasibility_receipt"]
    _validate_feasibility(feasibility, evidence["feasibility_receipt_hash"])
    starvation_preacceptance = _validate_feasibility_gate(feasibility, owner)
    if feasibility["config_hash"] != config_hash():
        raise RegistrationInputError(
            "feasibility receipt config_hash disagrees with the registering "
            "commit's config_hash(); the base rate must be re-measured"
        )
    if int(feasibility["window_sessions"]) != count:
        raise RegistrationInputError(
            "feasibility window_sessions disagrees with registration window"
        )
    if feasibility.get("universe") != manifest["included"]:
        raise RegistrationInputError(
            "feasibility universe disagrees with registration cohort "
            "(name-list mismatch, not just count)"
        )
    if int(feasibility["universe_size"]) != len(manifest["included"]):
        raise RegistrationInputError("feasibility universe_size disagrees with registration cohort")

    data_gate_receipt = evidence["data_gate_receipt"]
    _validate_data_gate_receipt(
        data_gate_receipt,
        evidence["data_gate_receipt_hash"],
        evidence["source_health_receipt_hash"],
        manifest,
        historical_session,
    )
    if (
        evidence["last_historical_manifest_receipt_hash"]
        != data_gate_receipt["schwab_manifest_hash"]
    ):
        raise RegistrationInputError(
            "last historical manifest hash disagrees with the verified data-gate package"
        )
    if evidence["data_gate_evidence_id"] != evidence["data_gate_receipt_hash"]:
        raise RegistrationInputError("data_gate_evidence_id must equal the durable receipt hash")
    if evidence["source_health_evidence_id"] != evidence["source_health_receipt_hash"]:
        raise RegistrationInputError(
            "source_health_evidence_id must equal the durable receipt hash"
        )

    registered_cost_hash = cost_model_hash()
    stage456_parameters = {name: getattr(config, name) for name in STAGE456_PARAMETER_NAMES}
    loss_bar = owner["SCHWAB_MIN_LOSSES_FOR_VERDICT"]
    stage456_parameters["MIN_LOSSES_FOR_VERDICT"] = loss_bar
    scorer = {
        "module": "options_researcher.h7_forward_scoring",
        "bootstrap_samples": config.BOOTSTRAP_SAMPLES,
        "min_losses_for_verdict": loss_bar,
    }
    scoring_identity = build_scoring_identity(
        stage456_parameters=stage456_parameters,
        scorer=scorer,
        cost_model_hash_value=registered_cost_hash,
    )
    payload = {
        "namespace": NAMESPACE,
        "owner_authorization": {field: owner[field] for field in OWNER_FIELDS},
        "review_evidence": evidence["review_evidence"],
        "activation_spec_sha256": evidence["activation_spec_sha256"],
        "code_commit": evidence["code_commit"],
        "provider": {
            "identity": evidence["provider_identity"],
            "access": "read_only",
            "cache_namespace": CACHE_NAMESPACE,
            "session_chain_convention": SESSION_CHAIN_CONVENTION,
            "confirmation_evidence": owner["SCHWAB_CONFIRMATION_EVIDENCE"],
            "capture_commitment_through": commitment,
        },
        "history": {
            "last_session": historical_session,
            "manifest_receipt_hash": evidence["last_historical_manifest_receipt_hash"],
        },
        "window": {
            "start_decision_session": start,
            "decision_session_count": count,
            "final_decision_session": end,
            "end_rule": "inclusive count of XNYS decision sessions from start",
            "three_month_proof": (f"{end} >= three-calendar-month anniversary of {start}"),
        },
        "cohort_rule": "decision_session in registered window (immutable key)",
        "frozen": {
            "config_hash": config_hash(),
            "cost_model_hash": registered_cost_hash,
            "stage456_parameters": stage456_parameters,
            "scorer": scorer,
            REGISTRATION_CONTRACT_FIELD: scoring_identity.contract,
            REGISTRATION_HASH_FIELD: scoring_identity.identity_hash,
            "verdict_mapping": {
                "SURVIVED": "ci_above_zero",
                "REJECTED": "ci_below_zero",
                "INCONCLUSIVE": "insufficient_or_no_edge",
            },
            "survived_disclaimer": (
                "SURVIVED is not live-trading approval, not a profitability "
                "claim, and not validation"
            ),
        },
        "gates": {
            "source_health_evidence_id": evidence["source_health_evidence_id"],
            "data_gate_evidence_id": evidence["data_gate_evidence_id"],
            "source_health_receipt_hash": evidence["source_health_receipt_hash"],
            "data_gate_receipt_hash": evidence["data_gate_receipt_hash"],
            "scope_id": scope["scope_id"],
            "scope_hash": scope["scope_hash"],
        },
        "feasibility": {
            "receipt_hash": evidence["feasibility_receipt_hash"],
            "receipt": feasibility,
            "occupancy_constrained_expected_entries": feasibility[
                "occupancy_constrained_expected_entries"
            ],
            "loss_bar": loss_bar,
            "starvation_preacceptance": starvation_preacceptance,
        },
        "universe": manifest,
        "darwin_durability_verified": evidence["darwin_durability_verified"],
        "pre_append_state": evidence["pre_append_state"],
    }
    return {
        "schema_version": ledger.SCHEMA_VERSION,
        "event_id": f"wr:{NAMESPACE}:{start}:{count}",
        "event_type": "window_registration",
        "occurred_at_utc": session_close_utc(start).isoformat(),
        "evaluation_session": start,
        "symbol": None,
        "lane": None,
        "causes": [],
        "payload": payload,
    }


def _synthetic_base(base_dir: object) -> Path:
    if base_dir is None:
        raise ActivationBoundaryError("an explicit synthetic base_dir is required")
    base = Path(base_dir)
    resolved = base.resolve(strict=False)
    real = SCHWAB_FORWARD_STORE.resolve()
    if resolved == real or real in resolved.parents:
        raise ActivationBoundaryError(
            "the real Schwab H7 store is prohibited until owner registration"
        )
    return base


def register_window(
    *,
    owner: dict,
    evidence: dict,
    base_dir: object,
    universe_manifest: dict,
    clock=None,
) -> ledger.AppendResult:
    """Append only to an explicit synthetic VALID-EMPTY store."""
    base = _synthetic_base(base_dir)
    event = build_window_registration_event(
        owner=owner, evidence=evidence, universe_manifest=universe_manifest
    )
    return ledger.append_event(event, base_dir=base, clock=clock, expected_head=None)


def register_window_real(
    *,
    owner: dict,
    evidence: dict,
    guard_report,
    spec_sha256: str,
    spec_path: object,
    base_dir: object,
    code_state,
    recheck_gates,
    universe_manifest: dict,
    clock=None,
    now=None,
    max_report_age_s: int = GUARD_REPORT_MAX_AGE_S,
) -> ledger.AppendResult:
    """Owner-gated door for the first event; callers must earn every check."""
    _require(owner, OWNER_FIELDS, "owner")
    _require(evidence, EVIDENCE_FIELDS, "evidence")

    if not guard_report.ready:
        failed = [check.name for check in guard_report.checks if not check.ok]
        raise ActivationRefused(
            f"guard report is not a full PASS (failed: {failed or 'no checks'})"
        )
    base = Path(base_dir)
    bound = str(base.resolve(strict=False))
    if guard_report.forward_base != bound:
        raise ActivationRefused("guard report is bound to a different target store")
    if not guard_report.code_commit or not guard_report.built_at_utc:
        raise ActivationRefused("guard report carries no fresh code/build identity")

    head_now, tree_clean = code_state()
    if not tree_clean:
        raise ActivationRefused("working tree is dirty at append time")
    if head_now != guard_report.code_commit:
        raise ActivationRefused("HEAD moved since the guard report")
    if evidence["code_commit"] != head_now:
        raise ActivationRefused("evidence code_commit disagrees with HEAD")

    sha = str(spec_sha256)
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        raise ActivationRefused("activation spec sha must be 64 lowercase hex")
    if evidence["activation_spec_sha256"] != sha:
        raise ActivationRefused("activation spec hash disagrees with evidence")
    spec_file = Path(spec_path)
    if spec_file.resolve(strict=False) != SCHWAB_ACTIVATION_SPEC_PATH.resolve(strict=False):
        raise ActivationRefused("activation spec path is not the pinned Schwab spec")
    if not spec_file.is_file():
        raise ActivationRefused("activation spec file does not exist")
    if sha256_file(spec_file) != sha:
        raise ActivationRefused("activation spec file drifted after review")

    if now is None:
        now = datetime.now(timezone.utc)
    try:
        built = datetime.fromisoformat(guard_report.built_at_utc)
    except ValueError as exc:
        raise ActivationRefused("guard report timestamp is malformed") from exc
    age = (now - built).total_seconds()
    if age < 0 or age > max_report_age_s:
        raise ActivationRefused("guard report is stale or from the future")

    gates = recheck_gates()
    if gates.get("source_health_all_healthy") is not True:
        raise ActivationRefused("source-health recheck is not all-healthy")
    if gates.get("data_gate_go") is not True:
        raise ActivationRefused("data-gate recheck is not GO")
    for key in ("source_health_evidence_id", "data_gate_evidence_id"):
        if gates.get(key) != evidence[key]:
            raise ActivationRefused(f"append-time {key} disagrees with evidence")

    verified = ledger.verify(base_dir=base)
    if not (verified.valid and verified.empty):
        raise ActivationRefused("target Schwab forward store is not VALID EMPTY at append time")
    event = build_window_registration_event(
        owner=owner, evidence=evidence, universe_manifest=universe_manifest
    )
    return ledger.append_event(event, base_dir=base, clock=clock, expected_head=None)
