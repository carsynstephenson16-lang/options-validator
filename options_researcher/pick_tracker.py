"""Dry-run-only shortlist recorder and conservative option outcome tracker.

This module has no trade, verdict, registration, or ledger authority.  Its
default CLI writes only below ``reports/pick_tracker/dryrun``; scored output
requires a separately validated owner-typed registration supplied by a future
authorized integration.
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import math
import os
import random
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

import config
from data.pandas_feed import adverse_buy, adverse_sell, quote_valid
from options_researcher import (
    exp_beta_qqq,
    exp_short_positioning,
    exp_spread_stability,
    exp_tail_shape,
    exp_tbill_carry,
)

REPORTS_ROOT = Path("reports/pick_tracker")
DRYRUN_ROOT = REPORTS_ROOT / "dryrun"
SNAPSHOT_PATH = Path(".tmp/dashboard/picks_snapshot.json")
HTML_PATH = Path(".tmp/dashboard/attractiveness.html")
_SCORED_ARMS = ("frozen_baseline", "context_lane")
_LANES = ("put", "cc", "pmcc", "leaps", "long_call")
_RECORDER_VERSION = "pick_tracker/v1"
_EXPERIMENT_MODULES = {
    "exp_beta_qqq": exp_beta_qqq,
    "exp_tail_shape": exp_tail_shape,
    "exp_spread_stability": exp_spread_stability,
    "exp_tbill_carry": exp_tbill_carry,
    "exp_short_positioning": exp_short_positioning,
}
_HEADER = (
    "DESCRIPTIVE ONLY — NOT A TRADE RANKING; no verdict authority; dry-run "
    "rows are permanently excluded from any registered window; A2-v1 "
    "(ledger seq 19/27) retains interpretive authority for board-level "
    "outcome questions; CONCENTRATION: picks are drawn from one 18-name "
    "AI-infrastructure board and are correlated — the effective sample is "
    "far smaller than the row count."
)


class TrackerError(RuntimeError):
    """An input cannot produce trustworthy tracker evidence."""


class TrackerConflict(TrackerError):
    """The append-only journal already binds the session to other bytes."""


class RegistrationRequired(TrackerError):
    """A write tried to leave the permanently excluded dry-run namespace."""


class PositionSchemaError(TrackerError):
    """The evaluated leg or its coverage/risk basis is incomplete."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def validate_snapshot(
    payload: Mapping[str, object],
    html_bytes: bytes,
    *,
    input_root: Path | None = None,
) -> dict[str, object]:
    if payload.get("schema") != "picks_snapshot/v1":
        raise TrackerError("snapshot schema is not picks_snapshot/v1")
    expected = payload.get("html_sha256")
    actual = _sha256_bytes(html_bytes)
    if expected != actual:
        raise TrackerError(f"SNAPSHOT_RENDER_MISMATCH: snapshot={expected!r} html={actual}")
    for arm in (*_SCORED_ARMS, "frozen_baseline_watch_inclusive"):
        value = payload.get(arm)
        if not isinstance(value, Mapping) or not isinstance(value.get("candidates"), list):
            raise TrackerError(f"snapshot arm {arm} is malformed")
    for field in (
        "evaluation_date",
        "data_as_of",
        "capture_receipt_path",
        "capture_receipt_sha256",
        "config_hash",
        "render_id",
    ):
        if not isinstance(payload.get(field), str) or not payload.get(field):
            raise TrackerError(f"snapshot provenance field {field} is absent")
    hashes = payload.get("source_row_hashes")
    if not isinstance(hashes, list) or not all(isinstance(value, str) for value in hashes):
        raise TrackerError("snapshot source_row_hashes are malformed")
    observed_hashes: set[str] = set()
    for arm in (*_SCORED_ARMS, "frozen_baseline_watch_inclusive"):
        arm_value = payload[arm]
        assert isinstance(arm_value, Mapping)
        candidates = arm_value["candidates"]
        assert isinstance(candidates, list)
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                raise TrackerError(f"snapshot arm {arm} candidate is malformed")
            raw_quote = candidate.get("raw_quote")
            source_hash = candidate.get("source_row_hash")
            if (
                not isinstance(raw_quote, Mapping)
                or not quote_valid(raw_quote.get("bid"), raw_quote.get("ask"))
                or not isinstance(source_hash, str)
                or not source_hash
            ):
                raise TrackerError(f"snapshot arm {arm} raw quote provenance is malformed")
            observed_hashes.add(source_hash)
    if observed_hashes != set(hashes):
        raise TrackerError("snapshot source_row_hashes do not match candidate rows")
    if input_root is not None:
        receipt_path = input_root / str(payload["capture_receipt_path"])
        try:
            receipt_hash = _sha256_bytes(receipt_path.read_bytes())
        except OSError as exc:
            raise TrackerError(f"CAPTURE_RECEIPT_UNREADABLE: {receipt_path}") from exc
        if receipt_hash != payload["capture_receipt_sha256"]:
            raise TrackerError(
                "CAPTURE_RECEIPT_MISMATCH: "
                f"snapshot={payload['capture_receipt_sha256']!r} actual={receipt_hash}"
            )
    return copy.deepcopy(dict(payload))


def _is_below(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _registration_valid(registration: Mapping[str, object] | None) -> bool:
    return bool(
        isinstance(registration, Mapping)
        and registration.get("schema") == "pick_tracker_registration/v1"
        and isinstance(registration.get("owner_typed_at"), str)
        and isinstance(registration.get("ledger_seq"), int)
    )


def _enforce_write_path(
    journal_path: Path,
    *,
    reports_root: Path | None,
    registration: Mapping[str, object] | None,
    registration_validator: Callable[[Mapping[str, object]], bool] | None,
) -> None:
    if reports_root is None:
        if "dryrun" in journal_path.resolve().parent.parts:
            return
    elif _is_below(journal_path, reports_root / "dryrun"):
        return
    registration_confirmed = bool(
        _registration_valid(registration)
        and registration_validator is not None
        and registration_validator(registration)
    )
    if not registration_confirmed:
        raise RegistrationRequired(
            "owner-typed registration is absent; writes must remain under dryrun/"
        )


def _read_journal(handle) -> list[dict[str, object]]:
    handle.seek(0)
    out: list[dict[str, object]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(handle, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TrackerError(f"journal line {line_number} is malformed") from exc
        if not isinstance(value, dict) or value.get("schema") != "pick_tracker_session/v1":
            raise TrackerError(f"journal line {line_number} has an unexpected schema")
        as_of = value.get("as_of")
        if not isinstance(as_of, str) or as_of in seen:
            raise TrackerError(f"journal line {line_number} has duplicate/invalid as_of")
        seen.add(as_of)
        out.append(value)
    return out


def _candidate_slot(value: Mapping[str, object]) -> str:
    symbol, lane = value.get("symbol"), value.get("lane")
    if not isinstance(symbol, str) or not symbol or not isinstance(lane, str) or not lane:
        raise TrackerError("candidate slot identity is invalid")
    return f"{symbol}:{lane}"


def _descriptive_nominations() -> dict[str, dict[str, object]]:
    """Declare imported experiment lanes that expose no natural selector."""
    return {
        name: {
            "state": "NOT_A_SELECTOR",
            "descriptive_only": True,
            "module": module.__name__,
        }
        for name, module in _EXPERIMENT_MODULES.items()
    }


def _arm_record(
    arm: str,
    candidates: Sequence[Mapping[str, object]],
    previous_slots: Mapping[str, object],
) -> dict[str, object]:
    current: dict[str, dict[str, object]] = {}
    for candidate in candidates:
        slot = _candidate_slot(candidate)
        if slot in current:
            raise TrackerError(f"arm {arm} repeats shortlist slot {slot}")
        candidate_id = candidate.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise TrackerError(f"arm {arm} candidate {slot} has no candidate_id")
        current[slot] = copy.deepcopy(dict(candidate))
    entries, restrikes, exits = [], [], []
    for slot, candidate in current.items():
        prior = previous_slots.get(slot)
        if not isinstance(prior, Mapping):
            entries.append({"slot": slot, "candidate": candidate})
        elif prior.get("candidate_id") != candidate["candidate_id"]:
            restrikes.append(
                {
                    "slot": slot,
                    "from_candidate_id": prior.get("candidate_id"),
                    "to_candidate_id": candidate["candidate_id"],
                }
            )
    for slot, prior in previous_slots.items():
        if slot not in current and isinstance(prior, Mapping):
            exits.append({"slot": slot, "candidate_id": prior.get("candidate_id")})
    return {
        "entries": entries,
        "restrikes": restrikes,
        "exits": exits,
        "current_slots": current,
    }


def append_membership(
    snapshot: Mapping[str, object],
    *,
    journal_path: Path,
    verified_sessions: Iterable[str],
    reports_root: Path | None = None,
    registration: Mapping[str, object] | None = None,
    registration_validator: Callable[[Mapping[str, object]], bool] | None = None,
) -> dict[str, object]:
    """Append one verified session, keyed by arm/symbol/lane shortlist slots."""
    as_of = snapshot.get("evaluation_date")
    if not isinstance(as_of, str) or as_of not in set(verified_sessions):
        raise TrackerError(f"SESSION_UNVERIFIED: {as_of!r}")
    nominations = snapshot.get("experiment_nominations")
    if nominations is None:
        nominations = _descriptive_nominations()
    elif not isinstance(nominations, Mapping) or not set(_EXPERIMENT_MODULES).issubset(nominations):
        raise TrackerError("descriptive experiment nomination columns are incomplete")
    _enforce_write_path(
        Path(journal_path),
        reports_root=reports_root,
        registration=registration,
        registration_validator=registration_validator,
    )
    registration_confirmed = bool(
        _registration_valid(registration)
        and registration_validator is not None
        and registration_validator(registration)
    )
    snapshot_hash = _sha256_bytes(_canonical_bytes(snapshot))
    journal_path = Path(journal_path)
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with journal_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        records = _read_journal(handle)
        for existing in records:
            if existing["as_of"] != as_of:
                continue
            if existing.get("snapshot_sha256") == snapshot_hash:
                return existing
            raise TrackerConflict(f"session {as_of} already recorded with different content")
        prior_arms = records[-1].get("arms") if records else {}
        prior_arms = prior_arms if isinstance(prior_arms, Mapping) else {}
        arms: dict[str, object] = {}
        for arm in _SCORED_ARMS:
            arm_value = snapshot.get(arm)
            if not isinstance(arm_value, Mapping):
                raise TrackerError(f"snapshot arm {arm} is absent")
            candidates = arm_value.get("candidates")
            if not isinstance(candidates, list):
                raise TrackerError(f"snapshot arm {arm} candidates are malformed")
            prior_arm = prior_arms.get(arm)
            prior_arm = prior_arm if isinstance(prior_arm, Mapping) else {}
            previous_slots = prior_arm.get("current_slots")
            previous_slots = previous_slots if isinstance(previous_slots, Mapping) else {}
            arm_record = _arm_record(arm, candidates, previous_slots)
            arm_record["state"] = str(arm_value.get("state") or "FAILED")
            arm_record["error"] = arm_value.get("error")
            arms[arm] = arm_record
        record = {
            "schema": "pick_tracker_session/v1",
            "as_of": as_of,
            "snapshot_sha256": snapshot_hash,
            "render_id": snapshot.get("render_id"),
            "capture_receipt_path": snapshot.get("capture_receipt_path"),
            "capture_receipt_sha256": snapshot.get("capture_receipt_sha256"),
            "artifact_schema": snapshot.get("schema"),
            "recorder_version": _RECORDER_VERSION,
            "config_hash": snapshot.get("config_hash"),
            "authority": (
                "NONE — descriptive tracking, scored registration-bound"
                if registration_confirmed
                else "NONE — descriptive tracking, dry-run"
            ),
            "arms": arms,
            "experiment_nominations": copy.deepcopy(nominations),
        }
        handle.seek(0, os.SEEK_END)
        handle.write(_canonical_bytes(record).decode() + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        return record


def _finite_positive(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PositionSchemaError(f"{label} must be a finite positive number")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise PositionSchemaError(f"{label} must be a finite positive number")
    return number


def validate_position(candidate: Mapping[str, object]) -> dict[str, object]:
    lane = candidate.get("lane")
    position = candidate.get("pick_position")
    if not isinstance(position, Mapping) or position.get("schema") != "pick_position/v1":
        raise PositionSchemaError("pick_position/v1 is required")
    if position.get("pnl_scope") != "INCREMENTAL_OPTION_LEG_ONLY":
        raise PositionSchemaError("incremental option leg P&L scope is required")
    leg = position.get("evaluated_leg")
    if not isinstance(leg, Mapping):
        raise PositionSchemaError("evaluated leg is required")
    symbol = candidate.get("symbol")
    lane = candidate.get("lane")
    if not isinstance(symbol, str) or not symbol or leg.get("symbol") != symbol:
        raise PositionSchemaError("evaluated leg symbol must match the candidate")
    strike = _finite_positive(leg.get("strike"), "evaluated strike")
    candidate_strike = _finite_positive(candidate.get("strike"), "candidate strike")
    if not math.isclose(strike, candidate_strike):
        raise PositionSchemaError("evaluated strike must match the candidate")
    if leg.get("contracts") != 1 or leg.get("side") not in {"buy", "sell"}:
        raise PositionSchemaError("evaluated leg must contain one contract and a valid side")
    expiry = leg.get("expiry")
    if not isinstance(expiry, str) or expiry != candidate.get("expiry"):
        raise PositionSchemaError("evaluated leg right/expiry is invalid")
    try:
        date.fromisoformat(expiry)
    except ValueError as exc:
        raise PositionSchemaError("evaluated leg expiry is not ISO formatted") from exc
    lane_contract = {
        "long_call": ("C", "buy"),
        "leaps": ("C", "buy"),
        "put": ("P", "sell"),
        "cc": ("C", "sell"),
        "pmcc": ("C", "sell"),
    }
    if lane not in lane_contract or (leg.get("right"), leg.get("side")) != lane_contract[lane]:
        raise PositionSchemaError("evaluated leg lane/right/side combination is invalid")
    basis = position.get("risk_basis")
    if not isinstance(basis, Mapping):
        raise PositionSchemaError("risk basis is required")
    basis_out = copy.deepcopy(dict(basis))
    if lane in {"long_call", "leaps"}:
        if basis.get("kind") != "ENTRY_DEBIT_AT_FILL":
            raise PositionSchemaError("long option risk basis must be entry debit")
        if basis.get("value") is not None:
            basis_out["value"] = _finite_positive(basis.get("value"), "risk basis")
    elif lane == "put":
        if basis.get("kind") != "ASSIGNMENT_CAPITAL":
            raise PositionSchemaError("put risk basis kind is invalid")
        value = _finite_positive(basis.get("value"), "risk basis")
        if basis.get("derivation") != "EVALUATED_STRIKE_X_100" or not math.isclose(
            value, strike * 100.0
        ):
            raise PositionSchemaError("put assignment capital must equal strike x 100")
        basis_out["value"] = value
    elif lane == "cc":
        if basis.get("kind") != "FROZEN_100_SHARE_COST_BASIS":
            raise PositionSchemaError("covered-call risk basis kind is invalid")
        basis_value = _finite_positive(basis.get("value"), "risk basis")
        coverage = position.get("coverage_context")
        if not isinstance(coverage, Mapping):
            raise PositionSchemaError("covered-call coverage is required")
        if (
            coverage.get("symbol") != symbol
            or coverage.get("shares") != 100
            or not isinstance(coverage.get("declared_shares"), int)
            or int(coverage["declared_shares"]) < 100
            or not isinstance(coverage.get("source_row_hash"), str)
            or not coverage.get("source_row_hash")
            or not isinstance(coverage.get("acquired"), str)
        ):
            raise PositionSchemaError("covered-call coverage must bind 100 shares and source hash")
        try:
            date.fromisoformat(str(coverage["acquired"]))
        except ValueError as exc:
            raise PositionSchemaError("covered-call acquired date is invalid") from exc
        cost_basis = _finite_positive(coverage.get("cost_basis"), "coverage cost basis")
        if not math.isclose(basis_value, cost_basis * 100.0):
            raise PositionSchemaError("covered-call basis must equal coverage cost basis x 100")
        basis_out["value"] = basis_value
    elif lane == "pmcc":
        if basis.get("kind") != "FROZEN_COVERING_LEAPS_ENTRY_DEBIT":
            raise PositionSchemaError("PMCC risk basis kind is invalid")
        basis_value = _finite_positive(basis.get("value"), "risk basis")
        coverage = position.get("coverage_context")
        required = {
            "id",
            "symbol",
            "right",
            "strike",
            "expiration",
            "contracts",
            "entry_price",
            "source_row_hash",
        }
        if (
            not isinstance(coverage, Mapping)
            or not required.issubset(coverage)
            or coverage.get("symbol") != symbol
            or coverage.get("right") != "C"
            or not isinstance(coverage.get("id"), str)
            or not coverage.get("id")
            or not isinstance(coverage.get("source_row_hash"), str)
            or not coverage.get("source_row_hash")
            or not isinstance(coverage.get("contracts"), int)
            or int(coverage["contracts"]) <= 0
        ):
            raise PositionSchemaError("PMCC coverage must preserve full held-LEAPS identity")
        _finite_positive(coverage.get("strike"), "PMCC covering strike")
        entry_price = _finite_positive(coverage.get("entry_price"), "PMCC covering entry price")
        try:
            date.fromisoformat(str(coverage["expiration"]))
        except ValueError as exc:
            raise PositionSchemaError("PMCC covering expiration is invalid") from exc
        if not math.isclose(basis_value, entry_price * 100.0):
            raise PositionSchemaError("PMCC basis must equal covering LEAPS entry debit")
        basis_out["value"] = basis_value
    else:
        raise PositionSchemaError(f"unsupported lane {lane!r}")
    out = copy.deepcopy(dict(position))
    out["risk_basis"] = basis_out
    return out


def _identity_hash(value: Mapping[str, object]) -> str:
    return _sha256_bytes(_canonical_bytes(value))


def coverage_identity_matches(
    position: Mapping[str, object],
    *,
    holdings: pd.DataFrame,
    positions: pd.DataFrame,
) -> bool:
    """Compare frozen coverage to the currently declared source-row identity."""
    coverage = position.get("coverage_context")
    leg = position.get("evaluated_leg")
    if not isinstance(coverage, Mapping) or not isinstance(leg, Mapping):
        return False
    symbol = str(leg.get("symbol") or "")
    kind = position.get("risk_basis")
    kind = kind.get("kind") if isinstance(kind, Mapping) else None
    if kind == "FROZEN_100_SHARE_COST_BASIS":
        rows = holdings.loc[holdings["symbol"].astype(str) == symbol]
        if len(rows) != 1:
            return False
        row = rows.iloc[0]
        identity = {
            "symbol": symbol,
            "shares": 100,
            "declared_shares": int(row["shares"]),
            "cost_basis": float(row["cost_basis"]),
            "acquired": str(row["acquired"]),
        }
    elif kind == "FROZEN_COVERING_LEAPS_ENTRY_DEBIT":
        rows = positions.loc[
            (positions["id"].astype(str) == str(coverage.get("id")))
            & (positions["structure"].astype(str) == "leaps_call")
        ]
        if len(rows) != 1:
            return False
        row = rows.iloc[0]
        identity = {
            "id": str(row["id"]),
            "symbol": str(row["symbol"]),
            "right": str(row["right"]),
            "strike": float(row["strike"]),
            "expiration": str(row["expiration"]),
            "contracts": int(row["contracts"]),
            "entry_price": float(row["entry_price"]),
        }
    else:
        return True
    identity["source_row_hash"] = _identity_hash(identity)
    return _canonical_bytes(identity) == _canonical_bytes(coverage)


def _current_coverage_validator(position: Mapping[str, object], _session: str) -> bool:
    from options_researcher.portfolio import load_holdings, load_positions

    try:
        return coverage_identity_matches(
            position,
            holdings=load_holdings(),
            positions=load_positions(),
        )
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError):
        return False


def _candidate_sessions(
    decision_session: str,
    trading_days_fn: Callable[[str, str], list[str]],
) -> list[str]:
    end = (date.fromisoformat(decision_session) + timedelta(days=14)).isoformat()
    sessions = [day for day in trading_days_fn(decision_session, end) if day > decision_session]
    if len(sessions) < 2:
        raise TrackerError("XNYS calendar did not return two sessions after decision")
    return sessions[:2]


def _exact_row(
    frame: pd.DataFrame, leg: Mapping[str, object]
) -> tuple[pd.Series | None, str | None]:
    required = {"expiration", "strike", "right", "bid", "ask"}
    if not required.issubset(frame.columns):
        return None, "CANCELLED_FILL_SCHEMA_INVALID"
    try:
        selected = frame.loc[
            (frame["expiration"].astype(str) == str(leg["expiry"]))
            & (frame["strike"].astype(float) == float(leg["strike"]))
            & (frame["right"].astype(str).str.upper() == str(leg["right"]).upper())
        ]
    except (KeyError, TypeError, ValueError):
        return None, "CANCELLED_FILL_SCHEMA_INVALID"
    if selected.empty:
        return None, "CANCELLED_CONTRACT_ABSENT"
    if len(selected) != 1:
        return None, "CANCELLED_FILL_SCHEMA_INVALID"
    row = selected.iloc[0]
    if not quote_valid(row["bid"], row["ask"]):
        return None, "CANCELLED_FILL_SCHEMA_INVALID"
    return row, None


def resolve_fill(
    decision: Mapping[str, object],
    *,
    decision_session: str,
    verified_sessions: Iterable[str],
    chain_loader: Callable[[str, str], pd.DataFrame],
    trading_days_fn: Callable[[str, str], list[str]],
    coverage_validator: Callable[[Mapping[str, object], str], bool] | None = None,
    current_session: str | None = None,
) -> dict[str, object]:
    """Resolve only the first verified D+1/D+2 capture; never use D."""
    try:
        position = validate_position(decision)
    except PositionSchemaError as exc:
        return {
            "status": "CANCELLED_POSITION_SCHEMA_INVALID",
            "decision_session": decision_session,
            "candidate_id": decision.get("candidate_id"),
            "reason": str(exc),
        }
    candidates = _candidate_sessions(decision_session, trading_days_fn)
    verified = set(verified_sessions)
    fill_session = next((session for session in candidates if session in verified), None)
    if fill_session is None:
        return {
            "status": (
                "PENDING_FILL_DATA"
                if current_session is not None and current_session < candidates[-1]
                else "CANCELLED_NO_FILL_DATA"
            ),
            "decision_session": decision_session,
            "candidate_id": decision.get("candidate_id"),
        }
    needs_coverage_check = decision.get("lane") in {"cc", "pmcc"}
    coverage_changed = coverage_validator is not None and not coverage_validator(
        position, fill_session
    )
    if needs_coverage_check and (coverage_validator is None or coverage_changed):
        return {
            "status": "CANCELLED_COVERAGE_CHANGED",
            "decision_session": decision_session,
            "fill_session": fill_session,
            "candidate_id": decision.get("candidate_id"),
        }
    leg = position["evaluated_leg"]
    assert isinstance(leg, Mapping)
    frame = chain_loader(str(leg["symbol"]), fill_session)
    row, cancellation = _exact_row(frame, leg)
    if cancellation is not None:
        return {
            "status": cancellation,
            "decision_session": decision_session,
            "fill_session": fill_session,
            "candidate_id": decision.get("candidate_id"),
        }
    assert row is not None
    side = str(leg["side"])
    fill_price = adverse_buy(row["ask"]) if side == "buy" else adverse_sell(row["bid"])
    commission = float(config.COMMISSION_PER_CONTRACT)
    entry_net_cash = (
        -(fill_price * 100.0 + commission) if side == "buy" else fill_price * 100.0 - commission
    )
    risk_basis = position["risk_basis"]
    assert isinstance(risk_basis, dict)
    if risk_basis.get("kind") == "ENTRY_DEBIT_AT_FILL":
        risk_basis["value"] = -entry_net_cash
    frozen_basis = _finite_positive(risk_basis.get("value"), "risk basis")
    return {
        "status": "OPEN",
        "candidate_id": decision.get("candidate_id"),
        "lane": decision.get("lane"),
        "decision_session": decision_session,
        "fill_session": fill_session,
        "pick_position": position,
        "raw_bid": float(row["bid"]),
        "raw_ask": float(row["ask"]),
        "fill_price": fill_price,
        "entry_commission": commission,
        "entry_net_cash": entry_net_cash,
        "frozen_risk_basis": frozen_basis,
        "pnl_scope": "INCREMENTAL_OPTION_LEG_ONLY",
    }


def mark_position(
    filled: Mapping[str, object],
    *,
    chain_frame: pd.DataFrame,
    mark_session: str,
) -> dict[str, object]:
    position = filled.get("pick_position")
    if not isinstance(position, Mapping):
        raise PositionSchemaError("filled position is absent")
    leg = position.get("evaluated_leg")
    if not isinstance(leg, Mapping):
        raise PositionSchemaError("filled evaluated leg is absent")
    row, cancellation = _exact_row(chain_frame, leg)
    if row is None:
        return {
            "status": "MARK_GAP",
            "mark_session": mark_session,
            "reason": cancellation,
        }
    side = str(leg["side"])
    commission = float(config.COMMISSION_PER_CONTRACT)
    if side == "buy":
        close_price = adverse_sell(row["bid"])
        close_net_cash = close_price * 100.0 - commission
    else:
        close_price = adverse_buy(row["ask"])
        close_net_cash = -(close_price * 100.0 + commission)
    pnl = float(filled["entry_net_cash"]) + close_net_cash
    basis = _finite_positive(filled.get("frozen_risk_basis"), "risk basis")
    return {
        "status": "MARKED",
        "mark_session": mark_session,
        "close_price": close_price,
        "evaluated_leg_pnl": pnl,
        "return_on_risk_basis": pnl / basis,
        "pnl_scope": "INCREMENTAL_OPTION_LEG_ONLY",
    }


def mark_at_expiry(
    filled: Mapping[str, object],
    *,
    underlying_close: float,
    expiry_session: str,
) -> dict[str, object]:
    """Settle the exact evaluated leg at intrinsic value on contract expiry."""
    position = filled.get("pick_position")
    if not isinstance(position, Mapping):
        raise PositionSchemaError("filled position is absent")
    leg = position.get("evaluated_leg")
    if not isinstance(leg, Mapping):
        raise PositionSchemaError("filled evaluated leg is absent")
    spot = _finite_positive(underlying_close, "underlying close")
    strike = _finite_positive(leg.get("strike"), "evaluated strike")
    intrinsic = max(spot - strike, 0.0) if leg.get("right") == "C" else max(strike - spot, 0.0)
    commission = float(config.COMMISSION_PER_CONTRACT)
    close_net_cash = (
        intrinsic * 100.0 - commission
        if leg.get("side") == "buy"
        else -(intrinsic * 100.0 + commission)
    )
    pnl = float(filled["entry_net_cash"]) + close_net_cash
    basis = _finite_positive(filled.get("frozen_risk_basis"), "risk basis")
    return {
        "status": "SETTLED",
        "mark_session": expiry_session,
        "termination": "expiry_intrinsic",
        "intrinsic_value": intrinsic,
        "evaluated_leg_pnl": pnl,
        "return_on_risk_basis": pnl / basis,
        "pnl_scope": "INCREMENTAL_OPTION_LEG_ONLY",
    }


def max_drawdown(normalized_marks: Sequence[float]) -> float | None:
    """Return the worst peak-to-trough change on the normalized mark series."""
    if not normalized_marks:
        return None
    peak = float(normalized_marks[0])
    worst = 0.0
    for value in normalized_marks:
        current = float(value)
        peak = max(peak, current)
        worst = min(worst, current - peak)
    return worst


def mark_schedule(lane: str, *, dte_at_fill: int) -> tuple[int, ...]:
    if lane == "leaps":
        return (21, 63, 126)
    if lane == "long_call":
        return (5, 10, 20)
    if lane in {"put", "cc", "pmcc"}:
        return (5, 10, 21) if dte_at_fill > 30 else (5, 10)
    raise TrackerError(f"unknown mark schedule lane {lane!r}")


def _scheduled_sessions(
    fill_session: str,
    offsets: Sequence[int],
    *,
    trading_days_fn: Callable[[str, str], list[str]],
) -> list[tuple[int, str]]:
    furthest = max(offsets, default=0)
    end = date.fromisoformat(fill_session) + timedelta(days=furthest * 2 + 30)
    sessions = [
        value for value in trading_days_fn(fill_session, end.isoformat()) if value > fill_session
    ]
    if len(sessions) < furthest:
        raise TrackerError("XNYS calendar did not cover the registered mark schedule")
    return [(offset, sessions[offset - 1]) for offset in offsets]


def evaluate_records(
    records: Sequence[Mapping[str, object]],
    *,
    as_of: str,
    verified_sessions: Iterable[str],
    chain_loader: Callable[[str, str], pd.DataFrame],
    trading_days_fn: Callable[[str, str], list[str]],
    close_loader: Callable[[str, str], float],
    coverage_validator: Callable[[Mapping[str, object], str], bool] | None = None,
) -> list[dict[str, object]]:
    """Rebuild the dry-run outcome book deterministically from opening events."""
    verified = set(verified_sessions)
    outcomes: list[dict[str, object]] = []
    for record in records:
        decision_session = record.get("as_of")
        arms = record.get("arms")
        if not isinstance(decision_session, str) or not isinstance(arms, Mapping):
            raise TrackerError("membership record is malformed")
        for arm in _SCORED_ARMS:
            arm_record = arms.get(arm)
            if not isinstance(arm_record, Mapping):
                raise TrackerError(f"membership record arm {arm} is malformed")
            arm_state = str(arm_record.get("state") or "READY")
            if arm_state != "READY":
                outcomes.append(
                    {
                        "arm": arm,
                        "lane": None,
                        "decision_session": decision_session,
                        "status": ("LANE_DISABLED" if arm_state == "DISABLED" else "LANE_FAILED"),
                        "reason": arm_record.get("error"),
                    }
                )
                continue
            entries = arm_record.get("entries")
            if not isinstance(entries, list):
                raise TrackerError(f"membership record arm {arm} entries are malformed")
            for entry in entries:
                candidate_value = entry.get("candidate") if isinstance(entry, Mapping) else None
                if not isinstance(candidate_value, Mapping):
                    raise TrackerError("membership entry candidate is malformed")
                candidate = copy.deepcopy(dict(candidate_value))
                result = resolve_fill(
                    candidate,
                    decision_session=decision_session,
                    verified_sessions=verified,
                    chain_loader=chain_loader,
                    trading_days_fn=trading_days_fn,
                    coverage_validator=coverage_validator,
                    current_session=as_of,
                )
                result.update(
                    {
                        "arm": arm,
                        "lane": candidate.get("lane"),
                        "decision_session": decision_session,
                    }
                )
                if result.get("status") != "OPEN":
                    outcomes.append(result)
                    continue
                position = result.get("pick_position")
                assert isinstance(position, Mapping)
                leg = position.get("evaluated_leg")
                assert isinstance(leg, Mapping)
                fill_session = str(result["fill_session"])
                expiry = str(leg["expiry"])
                dte_at_fill = (date.fromisoformat(expiry) - date.fromisoformat(fill_session)).days
                offsets = mark_schedule(str(candidate["lane"]), dte_at_fill=dte_at_fill)
                scheduled = _scheduled_sessions(
                    fill_session,
                    offsets,
                    trading_days_fn=trading_days_fn,
                )
                marks: list[dict[str, object]] = []
                unreachable = 0
                coverage_changed = False
                for offset, mark_session in scheduled:
                    if mark_session >= expiry:
                        if mark_session > expiry:
                            marks.append(
                                {
                                    "status": "MARK_AFTER_EXPIRY",
                                    "elapsed_sessions": offset,
                                    "mark_session": mark_session,
                                }
                            )
                            unreachable += 1
                    elif mark_session <= as_of:
                        if candidate.get("lane") in {"cc", "pmcc"} and (
                            coverage_validator is None
                            or not coverage_validator(position, mark_session)
                        ):
                            coverage_changed = True
                            result["status"] = "CANCELLED_COVERAGE_CHANGED"
                            marks.append(
                                {
                                    "status": "CANCELLED_COVERAGE_CHANGED",
                                    "mark_session": mark_session,
                                }
                            )
                            break
                        if mark_session not in verified:
                            marks.append(
                                {
                                    "status": "MARK_GAP",
                                    "elapsed_sessions": offset,
                                    "mark_session": mark_session,
                                    "reason": "SESSION_UNVERIFIED",
                                }
                            )
                        else:
                            try:
                                frame = chain_loader(str(leg["symbol"]), mark_session)
                            except (OSError, ValueError) as exc:
                                marks.append(
                                    {
                                        "status": "MARK_GAP",
                                        "elapsed_sessions": offset,
                                        "mark_session": mark_session,
                                        "reason": type(exc).__name__,
                                    }
                                )
                            else:
                                mark = mark_position(
                                    result,
                                    chain_frame=frame,
                                    mark_session=mark_session,
                                )
                                mark["elapsed_sessions"] = offset
                                marks.append(mark)
                if (
                    not coverage_changed
                    and expiry <= as_of
                    and candidate.get("lane") in {"cc", "pmcc"}
                    and (coverage_validator is None or not coverage_validator(position, expiry))
                ):
                    coverage_changed = True
                    result["status"] = "CANCELLED_COVERAGE_CHANGED"
                    marks.append(
                        {
                            "status": "CANCELLED_COVERAGE_CHANGED",
                            "mark_session": expiry,
                        }
                    )
                if not coverage_changed and expiry <= as_of:
                    try:
                        underlying_close = close_loader(str(leg["symbol"]), expiry)
                    except (OSError, KeyError, ValueError) as exc:
                        marks.append(
                            {
                                "status": "SETTLED",
                                "mark_session": expiry,
                                "termination": "terminal_conservative_mark",
                                "reason": type(exc).__name__,
                            }
                        )
                    else:
                        marks.append(
                            mark_at_expiry(
                                result,
                                underlying_close=underlying_close,
                                expiry_session=expiry,
                            )
                        )
                    result["status"] = "SETTLED"
                elif not coverage_changed and scheduled and scheduled[-1][1] <= as_of:
                    result["status"] = "SETTLED"
                    if marks:
                        marks[-1]["termination"] = "longest_applicable_mark"
                valid_marks = [
                    mark
                    for mark in marks
                    if isinstance(mark.get("return_on_risk_basis"), (int, float))
                ]
                if valid_marks:
                    latest = valid_marks[-1]
                    result["pnl"] = latest["evaluated_leg_pnl"]
                    result["return"] = latest["return_on_risk_basis"]
                    result["max_drawdown"] = max_drawdown(
                        [float(mark["return_on_risk_basis"]) for mark in valid_marks]
                    )
                    result["outcome_word"] = (
                        "gained after costs" if float(result["pnl"]) >= 0 else "lost after costs"
                    )
                result["marks"] = marks
                result["unreachable_marks"] = unreachable
                result["coverage_context_status"] = (
                    ("CHANGED" if coverage_changed else "VALIDATED_UNCHANGED")
                    if candidate.get("lane") in {"cc", "pmcc"}
                    else "NOT_APPLICABLE"
                )
                outcomes.append(result)
    return outcomes


def moving_block_samples(
    values: tuple[Any, ...],
    *,
    draws: int,
    seed: int,
) -> list[tuple[Any, ...]]:
    if len(values) < 2:
        raise ValueError("at least two chronological cohorts are required")
    rng = random.Random(seed)
    samples: list[tuple[Any, ...]] = []
    pairs = (len(values) + 1) // 2
    for _ in range(draws):
        sample: list[Any] = []
        for _pair in range(pairs):
            start = rng.randrange(len(values))
            sample.extend((values[start], values[(start + 1) % len(values)]))
        samples.append(tuple(sample[: len(values)]))
    return samples


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return float(ordered[index])


def weekly_paired_cohorts(
    outcomes: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Build non-overlapping calendar-week, equal-lane paired contrasts."""
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in outcomes:
        arm, lane, session = (
            row.get("arm"),
            row.get("lane"),
            row.get("decision_session"),
        )
        value = row.get("return")
        if (
            arm not in _SCORED_ARMS
            or not isinstance(lane, str)
            or not isinstance(session, str)
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
        ):
            continue
        decision = date.fromisoformat(session)
        week = (decision - timedelta(days=decision.weekday())).isoformat()
        grouped[(week, str(arm), lane)].append(float(value))
    weeks = sorted({key[0] for key in grouped})
    cohorts: list[dict[str, object]] = []
    for week in weeks:
        baseline_lanes = {
            lane
            for (row_week, arm, lane) in grouped
            if row_week == week and arm == "frozen_baseline"
        }
        context_lanes = {
            lane for (row_week, arm, lane) in grouped if row_week == week and arm == "context_lane"
        }
        paired = sorted(baseline_lanes & context_lanes)
        lane_contrasts = []
        for lane in paired:
            baseline = grouped[(week, "frozen_baseline", lane)]
            context = grouped[(week, "context_lane", lane)]
            lane_contrasts.append(sum(context) / len(context) - sum(baseline) / len(baseline))
        cohorts.append(
            {
                "week": week,
                "contrast": (sum(lane_contrasts) / len(lane_contrasts) if lane_contrasts else None),
                "paired_lanes": paired,
                "unmatched_lanes": sorted(baseline_lanes ^ context_lanes),
                "frozen_baseline_only": sorted(baseline_lanes - context_lanes),
                "context_lane_only": sorted(context_lanes - baseline_lanes),
            }
        )
    return cohorts


def build_scoreboard(
    outcomes: Sequence[Mapping[str, object]],
    *,
    weekly_cohorts: Sequence[Mapping[str, object]] | None = None,
) -> dict[str, object]:
    derived_weekly = weekly_cohorts is None
    if derived_weekly:
        weekly_cohorts = weekly_paired_cohorts(outcomes)
    arm_states = {arm: "READY" for arm in _SCORED_ARMS}
    lanes: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    represented: dict[str, set[str]] = {arm: set() for arm in _SCORED_ARMS}
    grouped: dict[tuple[str, str], list[Mapping[str, object]]] = defaultdict(list)
    for outcome in outcomes:
        arm, lane = outcome.get("arm"), outcome.get("lane")
        status = outcome.get("status")
        if arm in _SCORED_ARMS and status in {"LANE_DISABLED", "LANE_FAILED"}:
            arm_states[str(arm)] = str(status)
        if arm not in _SCORED_ARMS or not isinstance(lane, str):
            continue
        grouped[(str(arm), lane)].append(outcome)
        represented[str(arm)].add(lane)
    for (arm, lane), rows in grouped.items():
        cancellations: dict[str, int] = defaultdict(int)
        for row in rows:
            status = row.get("status")
            if isinstance(status, str) and status.startswith("CANCELLED_"):
                cancellations[status] += 1
        pnl_values = [float(row["pnl"]) for row in rows if isinstance(row.get("pnl"), (int, float))]
        return_values = [
            float(row["return"]) for row in rows if isinstance(row.get("return"), (int, float))
        ]
        lanes[arm][lane] = {
            "state": "DESCRIPTIVE",
            "entries": len(rows),
            "cancellations": dict(sorted(cancellations.items())),
            "open": sum(row.get("status") == "OPEN" for row in rows),
            "settled": sum(row.get("status") == "SETTLED" for row in rows),
            "raw_pnl": sum(pnl_values),
            "mean_return_on_risk_basis": (
                sum(return_values) / len(return_values) if return_values else None
            ),
            "unreachable_marks": sum(
                int(row.get("unreachable_marks", 0))
                for row in rows
                if isinstance(row.get("unreachable_marks", 0), int)
            ),
        }
    for arm in _SCORED_ARMS:
        for lane in _LANES:
            lanes[arm].setdefault(
                lane,
                {
                    "state": "NO_DATA",
                    "entries": 0,
                    "cancellations": {},
                    "open": 0,
                    "settled": 0,
                    "raw_pnl": None,
                    "mean_return_on_risk_basis": None,
                    "unreachable_marks": 0,
                },
            )
    if derived_weekly:
        baseline_only_count = sum(
            len(row.get("frozen_baseline_only", [])) for row in weekly_cohorts
        )
        context_only_count = sum(len(row.get("context_lane_only", [])) for row in weekly_cohorts)
    else:
        baseline_only_count = len(represented["frozen_baseline"] - represented["context_lane"])
        context_only_count = len(represented["context_lane"] - represented["frozen_baseline"])
    contrasts = [
        float(row["contrast"])
        for row in weekly_cohorts
        if isinstance(row.get("contrast"), (int, float))
    ]
    primary: dict[str, object] = {
        "point_estimate": sum(contrasts) / len(contrasts) if contrasts else None,
        "cohorts": len(contrasts),
        "ci_state": "INSUFFICIENT_COHORTS",
        "ci": None,
    }
    if len(contrasts) >= 8:
        samples = moving_block_samples(tuple(contrasts), draws=2_000, seed=27)
        means = [sum(sample) / len(sample) for sample in samples]
        primary.update(
            {
                "ci_state": "EXPLORATORY",
                "ci": [_percentile(means, 0.025), _percentile(means, 0.975)],
                "block_length_weeks": 2,
            }
        )
    if any(state != "READY" for state in arm_states.values()):
        primary = {
            "point_estimate": None,
            "cohorts": 0,
            "ci_state": "ARM_UNAVAILABLE",
            "ci": None,
        }
    return {
        "schema": "pick_tracker_scoreboard/v1",
        "header": _HEADER,
        "arm_states": arm_states,
        "lanes": {arm: dict(sorted(value.items())) for arm, value in lanes.items()},
        "unmatched_lane_counts": {
            "frozen_baseline_only": baseline_only_count,
            "context_lane_only": context_only_count,
        },
        "primary_contrast": primary,
        "weekly_cohorts": [copy.deepcopy(dict(row)) for row in weekly_cohorts],
    }


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _scoreboard_markdown(board: Mapping[str, object]) -> str:
    lines = [
        "# Pick tracker scoreboard",
        "",
        str(board["header"]),
        "",
        "This dry-run scoreboard contains no registered evidence and no verdict.",
        "",
        "| Arm | Lane | State | Entries | Open | Settled | Raw leg P&L | Mean return | Unreachable marks |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lanes = board.get("lanes")
    if isinstance(lanes, Mapping):
        for arm in _SCORED_ARMS:
            arm_lanes = lanes.get(arm)
            if not isinstance(arm_lanes, Mapping):
                continue
            for lane in _LANES:
                row = arm_lanes.get(lane)
                if not isinstance(row, Mapping):
                    continue
                lines.append(
                    "| "
                    + " | ".join(
                        str(value)
                        for value in (
                            arm,
                            lane,
                            row.get("state"),
                            row.get("entries"),
                            row.get("open"),
                            row.get("settled"),
                            row.get("raw_pnl"),
                            row.get("mean_return_on_risk_basis"),
                            row.get("unreachable_marks"),
                        )
                    )
                    + " |"
                )
    primary = board.get("primary_contrast")
    lines.extend(["", "## Primary paired-lane contrast", "", f"`{primary}`", ""])
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise TrackerError(f"{path} is unreadable: {type(exc).__name__}: {exc}") from exc
    if not isinstance(value, dict):
        raise TrackerError(f"{path} must contain a JSON object")
    return value


def record_cli(as_of: str) -> None:
    from options_researcher.schwab_chain_view import verified_sessions

    sessions, _failures = verified_sessions()
    if as_of not in set(sessions):
        raise TrackerError(f"SESSION_UNVERIFIED: {as_of!r}")
    payload = validate_snapshot(
        _load_json(SNAPSHOT_PATH), HTML_PATH.read_bytes(), input_root=Path(".")
    )
    if payload.get("evaluation_date") != as_of:
        raise TrackerError("snapshot evaluation_date does not match --as-of")
    append_membership(
        payload,
        journal_path=DRYRUN_ROOT / "events.jsonl",
        verified_sessions=sessions,
        reports_root=REPORTS_ROOT,
    )


def _load_journal_path(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
        return _read_journal(handle)


def evaluate_cli(as_of: str) -> None:
    from data.cache_runner import trading_days
    from data.underlying_closes import load_closes
    from options_researcher.schwab_chain_view import load_chain, verified_sessions

    sessions, _failures = verified_sessions()

    def close_loader(symbol: str, session: str) -> float:
        closes = load_closes(symbol, session, session, allow_oos=True)
        if closes.empty:
            raise ValueError(f"underlying close absent for {symbol} {session}")
        return float(closes.iloc[-1])

    records = _load_journal_path(DRYRUN_ROOT / "events.jsonl")
    outcomes = evaluate_records(
        records,
        as_of=as_of,
        verified_sessions=sessions,
        chain_loader=load_chain,
        trading_days_fn=trading_days,
        close_loader=close_loader,
        coverage_validator=_current_coverage_validator,
    )
    board = build_scoreboard(outcomes)
    board["as_of"] = as_of
    board["authority"] = "NONE — descriptive tracking, dry-run"
    destination = DRYRUN_ROOT / as_of
    _atomic_write(
        destination / "scoreboard.json",
        _canonical_bytes(board) + b"\n",
    )
    _atomic_write(
        destination / "scoreboard.md",
        _scoreboard_markdown(board).encode(),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("record", "evaluate"):
        child = subparsers.add_parser(command)
        child.add_argument("--as-of", required=True)
    args = parser.parse_args(argv)
    if args.command == "record":
        record_cli(args.as_of)
    else:
        evaluate_cli(args.as_of)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
