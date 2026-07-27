"""Receipt-backed intraday preview for the localhost dashboard.

The official H5 lane remains completed-session and close-based.  This module
only adapts immutable ``intraday_capture/v1`` receipts into descriptive
dashboard rows when the direct live-quote adapter is unavailable.
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

import config
from research.hashing import config_hash

NY = ZoneInfo("America/New_York")
_ALLOWED_STATUSES = {"ok", "unavailable"}
_FUTURE_TOLERANCE = timedelta(minutes=2)


def _short_note(value: object, limit: int = 240) -> str:
    text = str(value or "capture row unavailable").replace("\n", " ").strip()
    return text if len(text) <= limit else f"{text[:limit - 1]}…"


def _scheduled_at(on: date, tag: str) -> datetime:
    hour, minute = (
        int(part) for part in config.INTRADAY_CAPTURE_TIMES[tag].split(":", 1)
    )
    return datetime.combine(on, time(hour, minute), tzinfo=NY)


def _required_tag(now_ny: datetime) -> str | None:
    """Newest capture slot whose grace window has elapsed."""
    cutoff = now_ny - timedelta(
        minutes=config.INTRADAY_CAPTURE_TOLERANCE_MINUTES
    )
    due = [
        tag
        for tag in config.INTRADAY_CAPTURE_TIMES
        if _scheduled_at(now_ny.date(), tag) <= cutoff
    ]
    if not due:
        return None
    return max(due, key=lambda tag: _scheduled_at(now_ny.date(), tag))


def _parse_aware(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def _validate_receipt(
    receipt: object, path: Path, now_ny: datetime
) -> tuple[dict, datetime]:
    if not isinstance(receipt, dict):
        raise ValueError("receipt root must be an object")
    if receipt.get("receipt_kind") != "intraday_capture/v1":
        raise ValueError("unsupported receipt_kind")
    if receipt.get("force") is not False:
        raise ValueError("forced receipts are not eligible for automatic display")

    tag = receipt.get("session_tag")
    if tag not in config.INTRADAY_CAPTURE_TIMES:
        raise ValueError("unknown session_tag")
    if path.stem != tag:
        raise ValueError("filename and session_tag do not match")
    if receipt.get("scheduled_et") != config.INTRADAY_CAPTURE_TIMES[tag]:
        raise ValueError("scheduled_et does not match configuration")
    if receipt.get("config_hash") != config_hash():
        raise ValueError("receipt config identity is stale")

    captured_et = _parse_aware(receipt.get("captured_at_et"), "captured_at_et")
    captured_utc = _parse_aware(
        receipt.get("captured_at_utc"), "captured_at_utc"
    )
    captured_ny = captured_et.astimezone(NY)
    expected_day = now_ny.date().isoformat()
    if path.parent.name != expected_day:
        raise ValueError("receipt path is not for the current NY date")
    if captured_ny.date() != now_ny.date():
        raise ValueError("captured_at_et is not for the current NY date")
    if abs(
        (
            captured_et.astimezone(timezone.utc)
            - captured_utc.astimezone(timezone.utc)
        ).total_seconds()
    ) > 1:
        raise ValueError("ET and UTC capture timestamps disagree")
    if captured_utc > now_ny.astimezone(timezone.utc) + _FUTURE_TOLERANCE:
        raise ValueError("capture timestamp is in the future")

    universe = receipt.get("universe")
    expected_universe = list(config.ATTRACTIVENESS_UNIVERSE)
    if universe != expected_universe:
        raise ValueError("receipt universe does not match display universe")
    names = receipt.get("names")
    if not isinstance(names, dict) or set(names) != set(expected_universe):
        raise ValueError("receipt names do not exactly cover display universe")
    for symbol, row in names.items():
        if not isinstance(row, dict) or row.get("symbol") != symbol:
            raise ValueError(f"{symbol} row identity mismatch")
        if row.get("status") not in _ALLOWED_STATUSES:
            raise ValueError(f"{symbol} has an invalid status")
        if row.get("status") == "ok":
            spot = row.get("spot_mid")
            if (
                not isinstance(spot, (int, float))
                or not math.isfinite(float(spot))
                or float(spot) <= 0
            ):
                raise ValueError(f"{symbol} ok row has no finite positive spot")
            if not isinstance(row.get("spot_source"), str):
                raise ValueError(f"{symbol} ok row has no spot source")
    return receipt, captured_utc.astimezone(timezone.utc)


def load_current_receipt(
    *,
    now_ny: datetime | None = None,
    receipt_dir: Path | str | None = None,
) -> tuple[dict | None, Path | None, str]:
    """Return the newest valid current-day receipt or an explicit reason."""
    now_ny = (now_ny or datetime.now(NY)).astimezone(NY)
    root = Path(receipt_dir or config.INTRADAY_RECEIPT_DIR)
    day_dir = root / now_ny.date().isoformat()
    valid: list[tuple[datetime, Path, dict]] = []
    errors: list[str] = []
    for tag in config.INTRADAY_CAPTURE_TIMES:
        path = day_dir / f"{tag}.json"
        if not path.exists():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            receipt, captured = _validate_receipt(raw, path, now_ny)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        valid.append((captured, path, receipt))

    if not valid:
        detail = errors[0] if errors else "no current-day capture receipt"
        return None, None, detail

    _captured, path, receipt = max(valid, key=lambda item: item[0])
    required = _required_tag(now_ny)
    if required is not None:
        actual = str(receipt["session_tag"])
        if _scheduled_at(now_ny.date(), actual) < _scheduled_at(
            now_ny.date(), required
        ):
            return (
                None,
                None,
                f"latest required slot {required} is missing after its grace window",
            )
    return receipt, path, "ok"


def _spot_source_label(raw: object) -> str:
    labels = {
        "parity": "option-parity estimate",
        "parity_fallback": "option-parity estimate",
        "stock_snapshot_quote": "stock snapshot quote",
    }
    value = str(raw or "unknown")
    return labels.get(value, value.replace("_", " "))


def receipt_to_live_payload(
    receipt: dict,
    path: Path,
    *,
    now_ny: datetime,
    fallback_reason: str,
) -> dict:
    """Adapt a validated receipt without producing any decision fields."""
    captured_utc = _parse_aware(
        receipt["captured_at_utc"], "captured_at_utc"
    ).astimezone(timezone.utc)
    symbols: dict[str, dict] = {}
    for symbol, source in receipt["names"].items():
        if source.get("status") != "ok":
            symbols[symbol] = {
                "status": "unavailable",
                "note": _short_note(source.get("note")),
            }
            continue
        source_label = _spot_source_label(source.get("spot_source"))
        note_parts = [
            f"{receipt['session_tag']} capture",
            "descriptive only",
        ]
        if source.get("iv_label"):
            note_parts.append(str(source["iv_label"]))
        symbols[symbol] = {
            "status": "ok",
            "lane": "INTRADAY_CAPTURE_PREVIEW",
            "as_of_utc": captured_utc.isoformat(),
            "spot": float(source["spot_mid"]),
            "spot_source": source_label,
            "spot_ts": captured_utc.isoformat(),
            "atm_iv": source.get("atm_iv"),
            "iv_rank_preview": source.get("iv_rank_preview"),
            "note": "; ".join(note_parts),
        }

    from options_researcher.live_quotes import in_regular_session

    return {
        "generated_at_utc": captured_utc.isoformat(),
        "session_state": "open" if in_regular_session(now_ny) else "closed",
        "probe": {"ok": False, "reason": fallback_reason},
        "symbols": symbols,
        "freshness": {
            "status": "CURRENT",
            "source": "intraday_capture/v1",
            "descriptive_only": True,
            "captured_at_et": receipt["captured_at_et"],
            "captured_at_utc": receipt["captured_at_utc"],
            "session_tag": receipt["session_tag"],
            "receipt_path": str(path),
        },
    }


def refresh_with_receipt_fallback(
    *,
    live_refresh: Callable[[], dict] | None = None,
    now_ny: datetime | None = None,
    receipt_dir: Path | str | None = None,
) -> dict:
    """Use the direct live adapter when healthy, else current capture evidence."""
    now_ny = (now_ny or datetime.now(NY)).astimezone(NY)
    if live_refresh is None:
        from options_researcher.live_quotes import refresh

        live_refresh = refresh

    try:
        primary = live_refresh()
    except Exception as exc:
        primary = {
            "generated_at_utc": now_ny.astimezone(timezone.utc).isoformat(),
            "session_state": "open",
            "probe": {"ok": False, "reason": f"{type(exc).__name__}: {exc}"},
            "symbols": {},
            "refresh_error": f"{type(exc).__name__}: {exc}",
        }

    any_live = any(
        row.get("status") == "ok"
        for row in (primary.get("symbols") or {}).values()
        if isinstance(row, dict)
    )
    if any_live:
        primary.setdefault(
            "freshness",
            {
                "status": "CURRENT",
                "source": "direct_live_adapter",
                "descriptive_only": True,
                "captured_at_utc": primary.get("generated_at_utc"),
            },
        )
        return primary

    receipt, path, reason = load_current_receipt(
        now_ny=now_ny, receipt_dir=receipt_dir
    )
    fallback_reason = str(
        (primary.get("probe") or {}).get("reason")
        or primary.get("refresh_error")
        or "direct live adapter returned no usable rows"
    )
    if receipt is not None and path is not None:
        return receipt_to_live_payload(
            receipt,
            path,
            now_ny=now_ny,
            fallback_reason=fallback_reason,
        )

    primary["receipt_fallback"] = {
        "status": "UNAVAILABLE",
        "reason": reason,
    }
    primary.setdefault(
        "freshness",
        {
            "status": "UNAVAILABLE",
            "source": "none",
            "descriptive_only": True,
            "reason": reason,
        },
    )
    return primary
