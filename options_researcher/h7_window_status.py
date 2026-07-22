"""Read-only status of the live H7 forward paper window.

This module renders nothing and writes nothing. It summarizes the verified
append-only real store and the receipt chain expected for today's completed
evaluation session. It carries no entry, exit, or scoring authority.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from options_researcher import h7_event_ledger
from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE
from options_researcher.h7_scope import scope_identity
from options_researcher.h7_watch import evaluation_session

_REPO_ROOT = REAL_FORWARD_STORE.parents[1]


def window_status(
    base_dir: Path = REAL_FORWARD_STORE,
    today: date | None = None,
) -> dict:
    """Return a fail-visible summary of the live forward window."""
    today = today or date.today()
    base = Path(base_dir)
    if not (base / "events.jsonl").exists():
        return {"ok": False, "detail": f"no forward store at {base}"}

    try:
        events = h7_event_ledger.read_events(base)
        if not events or events[0].event_type != "window_registration":
            return {
                "ok": False,
                "detail": "store has no window_registration preamble",
            }

        registration = events[0].payload
        window = registration["window"]
        universe = registration["universe"]
        start = window["start_decision_session"]
        end = window["final_decision_session"]
        total = window["decision_session_count"]
        included = list(universe["included"])
        excluded = [item["symbol"] for item in universe["excluded"]]

        eval_iso = evaluation_session(today).isoformat()
        elapsed_end = min(eval_iso, end)
        if elapsed_end < start:
            elapsed = 0
        else:
            from data.cache_runner import trading_days

            elapsed = len(trading_days(start, elapsed_end))
    except (
        h7_event_ledger.LedgerError,
        IndexError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        return {
            "ok": False,
            "detail": f"forward store failed verification: {exc}",
        }

    counts: dict[str, int] = {}
    for event in events:
        counts[event.event_type] = counts.get(event.event_type, 0) + 1

    scope_id = scope_identity()["scope_id"]
    source_path = (
        _REPO_ROOT
        / "reports"
        / "h7_receipts"
        / scope_id
        / "source_health"
        / f"{eval_iso}.json"
    )
    gate_path = (
        _REPO_ROOT
        / "reports"
        / "h7_data_gate"
        / scope_id
        / "receipts"
        / f"{eval_iso}.json"
    )
    receipts = {
        "evaluation_session": eval_iso,
        "source_health_present": source_path.is_file(),
        "data_gate_present": gate_path.is_file(),
        "data_gate_verdict": None,
    }
    if gate_path.is_file():
        try:
            from research.receipts import load_receipt

            gate = load_receipt(gate_path, expected_type="data_gate")
            receipts["data_gate_verdict"] = gate["whole_universe_verdict"]
        except (KeyError, OSError, TypeError, ValueError) as exc:
            receipts["data_gate_verdict"] = f"UNREADABLE: {exc}"

    return {
        "ok": True,
        "start": start,
        "end": end,
        "total_sessions": total,
        "sessions_elapsed": elapsed,
        "sessions_remaining": max(total - elapsed, 0),
        "included": included,
        "excluded": excluded,
        "event_counts": counts,
        "entries_taken": counts.get("entry_intent", 0),
        "receipts": receipts,
    }


def main() -> int:
    status = window_status()
    for key, value in status.items():
        print(f"{key}: {value}")
    return 0 if status["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
