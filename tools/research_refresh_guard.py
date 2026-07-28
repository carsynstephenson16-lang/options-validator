"""Durable schedule, repeated-failure, and monthly-budget guards for research refresh."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from data.atomic_io import atomic_text_write

SCHEMA_VERSION: Final = "research_refresh_guard/v1"
NEW_YORK: Final = ZoneInfo("America/New_York")
DEFAULT_MAX_FAILURES: Final = 2
DEFAULT_MONTHLY_BUDGET_USD: Final = Decimal("200.00")
DEFAULT_ATTEMPT_BUDGET_USD: Final = Decimal("8.00")
DEFAULT_STALE_MINUTES: Final = 120
FINAL_STATUSES: Final = frozenset({"SUCCEEDED", "FAILED", "STALE_FAILED"})
FAILURE_CLASSES: Final = frozenset(
    {
        "CLAUDE_EXIT",
        "BUNDLE_VERIFY",
        "DASHBOARD_BUILD",
        "FINAL_VERIFY",
        "SUCCESS_RECORD",
    }
)


class GuardError(ValueError):
    """Malformed state or invalid guard input."""


class ScheduleBlocked(GuardError):
    """The invocation is outside the weekday premarket window."""


class CircuitOpen(GuardError):
    """Too many consecutive paid-attempt failures occurred."""


class MonthlyBudgetExhausted(GuardError):
    """The next maximum-cost reservation would exceed the monthly ceiling."""


def _parse_now(value: str | None) -> datetime:
    if value is None:
        return datetime.now(NEW_YORK)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise GuardError("invalid --now timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise GuardError("--now must be timezone-aware")
    return parsed.astimezone(NEW_YORK)


def _decimal(value: str, *, where: str, allow_zero: bool = False) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise GuardError(f"{where}: invalid dollar amount") from error
    if not parsed.is_finite() or parsed < 0 or (parsed == 0 and not allow_zero):
        qualifier = "non-negative" if allow_zero else "positive"
        raise GuardError(f"{where}: dollar amount must be {qualifier}")
    return parsed.quantize(Decimal("0.01"))


def schedule_window_open(now_et: datetime, *, manual_override: bool = False) -> bool:
    """Allow only weekdays from 07:30 through 08:30 ET unless explicitly overridden."""
    if manual_override:
        return True
    localized = now_et.astimezone(NEW_YORK)
    minute = localized.hour * 60 + localized.minute
    return localized.isoweekday() <= 5 and 7 * 60 + 30 <= minute <= 8 * 60 + 30


def _empty_state() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at_utc": None,
        "consecutive_failures": 0,
        "attempts": [],
    }


def _load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return _empty_state()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GuardError("guard state is unreadable") from error
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise GuardError("guard state schema mismatch")
    attempts = value.get("attempts")
    if not isinstance(attempts, list):
        raise GuardError("guard state attempts are invalid")
    for index, attempt in enumerate(attempts):
        if not isinstance(attempt, dict):
            raise GuardError(f"guard state attempts[{index}] is invalid")
        required = ("attempt_id", "month", "reserved_usd", "reserved_at_utc", "status")
        if any(not isinstance(attempt.get(field), str) for field in required):
            raise GuardError(f"guard state attempts[{index}] is incomplete")
        _decimal(
            str(attempt["reserved_usd"]),
            where=f"attempts[{index}].reserved_usd",
            allow_zero=True,
        )
        reserved_at = _parse_timestamp(
            str(attempt["reserved_at_utc"]),
            where=f"attempts[{index}].reserved_at_utc",
        )
        if reserved_at.utcoffset() != timedelta(0):
            raise GuardError(f"attempts[{index}].reserved_at_utc is not UTC")
        if attempt["status"] not in {"RESERVED", *FINAL_STATUSES}:
            raise GuardError(f"attempts[{index}].status is invalid")
    return value


def _parse_timestamp(value: str, *, where: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise GuardError(f"{where}: invalid timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise GuardError(f"{where}: timestamp must be timezone-aware")
    return parsed


def _attempts(state: Mapping[str, object]) -> list[dict[str, object]]:
    value = state.get("attempts")
    if not isinstance(value, list):
        raise GuardError("guard state attempts are invalid")
    attempts: list[dict[str, object]] = []
    for attempt in value:
        if not isinstance(attempt, dict):
            raise GuardError("guard state attempt is invalid")
        attempts.append(attempt)
    return attempts


def _recompute_consecutive_failures(state: dict[str, object]) -> None:
    consecutive = 0
    ordered = sorted(
        _attempts(state),
        key=lambda attempt: str(attempt["reserved_at_utc"]),
    )
    for attempt in ordered:
        status = attempt.get("status")
        if status == "SUCCEEDED":
            consecutive = 0
        elif status in {"FAILED", "STALE_FAILED"}:
            consecutive += 1
    state["consecutive_failures"] = consecutive


def _reconcile_stale(
    state: dict[str, object],
    *,
    now_et: datetime,
    stale_minutes: int,
) -> None:
    if stale_minutes < 30:
        raise GuardError("stale_minutes must be at least 30")
    cutoff = now_et.astimezone(timezone.utc) - timedelta(minutes=stale_minutes)
    for attempt in _attempts(state):
        if attempt.get("status") != "RESERVED":
            continue
        reserved_at = _parse_timestamp(
            str(attempt["reserved_at_utc"]),
            where="attempt.reserved_at_utc",
        ).astimezone(timezone.utc)
        if reserved_at <= cutoff:
            attempt["status"] = "STALE_FAILED"
            attempt["failure_class"] = "STALE_RESERVATION"
            attempt["completed_at_utc"] = (
                now_et.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            )
    _recompute_consecutive_failures(state)


def _monthly_reserved(state: Mapping[str, object], month: str) -> Decimal:
    total = Decimal("0")
    for attempt in _attempts(state):
        if attempt.get("month") == month:
            total += _decimal(
                str(attempt["reserved_usd"]),
                where="attempt.reserved_usd",
                allow_zero=True,
            )
    return total.quantize(Decimal("0.01"))


def _utc_text(now_et: datetime) -> str:
    return now_et.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@contextmanager
def _locked_state(state_dir: Path) -> Iterator[tuple[dict[str, object], Path]]:
    state_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(state_dir, 0o700)
    lock_path = state_dir / "guard.lock"
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        state_path = state_dir / "guard_state.json"
        state = _load_state(state_path)
        yield state, state_path
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def _save_state(state: dict[str, object], path: Path, *, now_et: datetime) -> None:
    state["schema_version"] = SCHEMA_VERSION
    state["updated_at_utc"] = _utc_text(now_et)
    atomic_text_write(
        json.dumps(state, sort_keys=True, indent=2, allow_nan=False) + "\n",
        path,
    )
    os.chmod(path, 0o600)


def reserve_attempt(
    state_dir: Path,
    *,
    attempt_id: str,
    now_et: datetime,
    attempt_budget_usd: Decimal = DEFAULT_ATTEMPT_BUDGET_USD,
    monthly_budget_usd: Decimal = DEFAULT_MONTHLY_BUDGET_USD,
    max_failures: int = DEFAULT_MAX_FAILURES,
    stale_minutes: int = DEFAULT_STALE_MINUTES,
) -> str:
    """Atomically reserve worst-case spend before an LLM is invoked."""
    if not attempt_id or any(character.isspace() for character in attempt_id):
        raise GuardError("attempt_id must be non-empty and contain no whitespace")
    if max_failures < 1:
        raise GuardError("max_failures must be at least 1")
    attempt_budget_usd = attempt_budget_usd.quantize(Decimal("0.01"))
    monthly_budget_usd = monthly_budget_usd.quantize(Decimal("0.01"))
    if attempt_budget_usd <= 0 or monthly_budget_usd <= 0:
        raise GuardError("budget values must be positive")
    if attempt_budget_usd > monthly_budget_usd:
        raise GuardError("attempt budget exceeds monthly budget")

    with _locked_state(state_dir) as (state, state_path):
        state_before_reconcile = json.dumps(state, sort_keys=True)
        _reconcile_stale(state, now_et=now_et, stale_minutes=stale_minutes)
        if json.dumps(state, sort_keys=True) != state_before_reconcile:
            _save_state(state, state_path, now_et=now_et)
        attempts = _attempts(state)
        existing = next(
            (attempt for attempt in attempts if attempt.get("attempt_id") == attempt_id),
            None,
        )
        if existing is not None:
            return "ALREADY_RESERVED"
        consecutive = state.get("consecutive_failures")
        if not isinstance(consecutive, int) or isinstance(consecutive, bool):
            raise GuardError("guard state consecutive_failures is invalid")
        if consecutive >= max_failures:
            raise CircuitOpen(
                f"{consecutive} consecutive paid-attempt failures; manual reset required"
            )
        month = now_et.astimezone(NEW_YORK).strftime("%Y-%m")
        reserved = _monthly_reserved(state, month)
        if reserved + attempt_budget_usd > monthly_budget_usd:
            raise MonthlyBudgetExhausted(
                f"monthly reserved budget would exceed ${monthly_budget_usd:.2f}"
            )
        attempts.append(
            {
                "attempt_id": attempt_id,
                "month": month,
                "reserved_usd": f"{attempt_budget_usd:.2f}",
                "reserved_at_utc": _utc_text(now_et),
                "status": "RESERVED",
            }
        )
        state["attempts"] = attempts
        _save_state(state, state_path, now_et=now_et)
    return "RESERVED"


def record_outcome(
    state_dir: Path,
    *,
    attempt_id: str,
    succeeded: bool,
    now_et: datetime,
    failure_class: str | None = None,
) -> str:
    """Durably close one reservation without logging raw command output."""
    if not succeeded and failure_class not in FAILURE_CLASSES:
        raise GuardError("failure_class is not an approved non-secret classification")
    if succeeded and failure_class is not None:
        raise GuardError("successful outcome cannot carry failure_class")
    with _locked_state(state_dir) as (state, state_path):
        attempts = _attempts(state)
        matches = [attempt for attempt in attempts if attempt.get("attempt_id") == attempt_id]
        if len(matches) != 1:
            raise GuardError("attempt reservation not found or duplicated")
        attempt = matches[0]
        desired = "SUCCEEDED" if succeeded else "FAILED"
        current = attempt.get("status")
        if current == desired:
            return "ALREADY_RECORDED"
        if current != "RESERVED":
            raise GuardError(f"attempt is already finalized as {current}")
        attempt["status"] = desired
        attempt["completed_at_utc"] = _utc_text(now_et)
        if failure_class is not None:
            attempt["failure_class"] = failure_class
        _recompute_consecutive_failures(state)
        _save_state(state, state_path, now_et=now_et)
    return desired


def reset_failures(state_dir: Path, *, now_et: datetime) -> None:
    """Explicit operator recovery: preserve budget history and close the failure circuit."""
    with _locked_state(state_dir) as (state, state_path):
        attempts = _attempts(state)
        attempts.append(
            {
                "attempt_id": f"manual-reset-{_utc_text(now_et)}",
                "month": now_et.astimezone(NEW_YORK).strftime("%Y-%m"),
                "reserved_usd": "0.00",
                "reserved_at_utc": _utc_text(now_et),
                "completed_at_utc": _utc_text(now_et),
                "status": "SUCCEEDED",
                "operator_reset": True,
            }
        )
        state["attempts"] = attempts
        _recompute_consecutive_failures(state)
        _save_state(state, state_path, now_et=now_et)


def _state_dir(value: str | None) -> Path:
    configured = value or os.environ.get("RESEARCH_REFRESH_STATE_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return (
        Path.home() / "Library" / "Application Support" / "options-validator" / "research-refresh"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    window = commands.add_parser("window")
    window.add_argument("--now")
    window.add_argument("--manual-override", action="store_true")

    reserve = commands.add_parser("reserve")
    reserve.add_argument("--state-dir")
    reserve.add_argument("--attempt-id", required=True)
    reserve.add_argument("--now")
    reserve.add_argument("--attempt-budget-usd", default=str(DEFAULT_ATTEMPT_BUDGET_USD))
    reserve.add_argument("--monthly-budget-usd", default=str(DEFAULT_MONTHLY_BUDGET_USD))
    reserve.add_argument("--max-failures", type=int, default=DEFAULT_MAX_FAILURES)
    reserve.add_argument("--stale-minutes", type=int, default=DEFAULT_STALE_MINUTES)

    outcome = commands.add_parser("record")
    outcome.add_argument("--state-dir")
    outcome.add_argument("--attempt-id", required=True)
    outcome.add_argument("--now")
    result_group = outcome.add_mutually_exclusive_group(required=True)
    result_group.add_argument("--success", action="store_true")
    result_group.add_argument("--failure-class", choices=sorted(FAILURE_CLASSES))

    reset = commands.add_parser("reset-failures")
    reset.add_argument("--state-dir")
    reset.add_argument("--now")

    args = parser.parse_args(argv)
    try:
        now_et = _parse_now(args.now)
        if args.command == "window":
            if not schedule_window_open(now_et, manual_override=args.manual_override):
                raise ScheduleBlocked("outside weekday 07:30-08:30 America/New_York window")
            print("SCHEDULE_WINDOW_OK")
        elif args.command == "reserve":
            status = reserve_attempt(
                _state_dir(args.state_dir),
                attempt_id=args.attempt_id,
                now_et=now_et,
                attempt_budget_usd=_decimal(args.attempt_budget_usd, where="attempt_budget_usd"),
                monthly_budget_usd=_decimal(args.monthly_budget_usd, where="monthly_budget_usd"),
                max_failures=args.max_failures,
                stale_minutes=args.stale_minutes,
            )
            print(f"GUARD_{status}")
        elif args.command == "record":
            status = record_outcome(
                _state_dir(args.state_dir),
                attempt_id=args.attempt_id,
                succeeded=args.success,
                now_et=now_et,
                failure_class=args.failure_class,
            )
            print(f"GUARD_{status}")
        else:
            reset_failures(_state_dir(args.state_dir), now_et=now_et)
            print("GUARD_FAILURE_CIRCUIT_RESET")
    except ScheduleBlocked as error:
        print(f"SCHEDULE_BLOCKED: {error}")
        return 4
    except CircuitOpen as error:
        print(f"FAILURE_CIRCUIT_OPEN: {error}")
        return 5
    except MonthlyBudgetExhausted as error:
        print(f"MONTHLY_BUDGET_EXHAUSTED: {error}")
        return 6
    except GuardError as error:
        print(f"GUARD_STATE_REJECTED: {error}")
        return 7
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
