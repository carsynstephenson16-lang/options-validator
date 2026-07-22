"""Read-only daily proof that the H7 real-entry path is reachable.

The forward window is live, but the ledger still holds only the registration
event: the code path that appends a real decision event has never run against
real receipts. Waiting for the first trigger to find out whether it works is
the wrong order. This module runs the real ``open_real_session`` validation --
activation cohort, decision window, receipt chain, source health, per-symbol
entry bans -- every session, against the real store and the real receipts, and
reports what would happen if a name triggered today.

It NEVER writes: no ledger append, no receipt, no artifact. ``open_real_session``
is pure validation, and a test asserts the store is byte-identical afterwards.
A refusal here is not a failure of the preflight -- it is the preflight doing
its job a day (or a month) before it would have mattered.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE
from options_researcher.h7_session import SessionRefused, open_real_session

DEFAULT_RECEIPTS_DIR = Path("reports/h7_data_gate")


@dataclass(frozen=True)
class PreflightResult:
    """What the real entry path would do today, without doing it."""

    ok: bool
    decision_session: str
    evaluation_session: str | None
    refusal: str | None = None
    entry_ready: tuple[str, ...] = ()
    banned: dict[str, str] = field(default_factory=dict)


def preflight(
    *,
    decision_session: str,
    data_gate_receipt_path: Path,
    source_evaluation_session: str | None = None,
    base_dir: Path = REAL_FORWARD_STORE,
) -> PreflightResult:
    """Validate the real entry path for ``decision_session``; write nothing."""
    common = {
        "base_dir": base_dir,
        "decision_session": decision_session,
        "source_evaluation_session": source_evaluation_session,
        "data_gate_receipt_path": Path(data_gate_receipt_path),
    }
    try:
        board = open_real_session(**common)
    except SessionRefused as exc:
        return PreflightResult(ok=False, decision_session=decision_session,
                               evaluation_session=source_evaluation_session,
                               refusal=str(exc))

    ready: list[str] = []
    banned: dict[str, str] = {}
    for symbol in board.included_symbols:
        try:
            open_real_session(**common, symbol=symbol)
        except SessionRefused as exc:
            banned[symbol] = str(exc)
        else:
            ready.append(symbol)
    return PreflightResult(ok=True, decision_session=board.decision_session,
                           evaluation_session=board.evaluation_session,
                           entry_ready=tuple(ready), banned=banned)


def default_gate_receipt_path(evaluation_session: str, *,
                              receipts_dir: Path = DEFAULT_RECEIPTS_DIR) -> Path:
    """The data-gate receipt the daily ritual writes for that session."""
    from options_researcher.h7_scope import scope_identity

    scope_id = scope_identity()["scope_id"]
    return Path(receipts_dir) / scope_id / "receipts" / f"{evaluation_session}.json"


def main(argv: list[str] | None = None) -> int:
    import argparse
    from zoneinfo import ZoneInfo

    from options_researcher.h7_watch import evaluation_session

    parser = argparse.ArgumentParser(
        description="Read-only H7 real-entry preflight (exit 0 reachable, "
                    "1 would refuse, 2 invalid invocation). Writes nothing.")
    parser.add_argument("--decision-session",
                        help="operator decision date YYYY-MM-DD "
                             "(default today America/New_York)")
    parser.add_argument("--source-evaluation-session",
                        help="completed source-data session; defaults to the "
                             "watcher-compatible preceding session")
    parser.add_argument("--data-gate-receipt", default=None,
                        help="defaults to the ritual's receipt for the session")
    parser.add_argument("--receipts-dir", default=str(DEFAULT_RECEIPTS_DIR))
    parser.add_argument("--base-dir", default=str(REAL_FORWARD_STORE))
    args = parser.parse_args(argv)

    from datetime import datetime

    ny_today = datetime.now(ZoneInfo("America/New_York")).date()
    try:
        decision = (date.fromisoformat(args.decision_session)
                    if args.decision_session else ny_today)
    except ValueError:
        print(f"--decision-session {args.decision_session!r} is not YYYY-MM-DD; "
              "refusing.")
        return 2
    evaluation = (args.source_evaluation_session
                  or evaluation_session(decision).isoformat())
    gate_path = (Path(args.data_gate_receipt) if args.data_gate_receipt
                 else default_gate_receipt_path(
                     evaluation, receipts_dir=Path(args.receipts_dir)))

    result = preflight(decision_session=decision.isoformat(),
                       source_evaluation_session=evaluation,
                       data_gate_receipt_path=gate_path,
                       base_dir=Path(args.base_dir))
    print(f"H7 ENTRY PREFLIGHT decision={result.decision_session} "
          f"session={result.evaluation_session} (read-only; writes nothing)")
    print(f"  data-gate receipt: {gate_path}")
    if not result.ok:
        print(f"  REAL ENTRY PATH WOULD REFUSE: {result.refusal}")
        return 1
    print(f"  entry-ready ({len(result.entry_ready)}): "
          f"{', '.join(result.entry_ready) or 'none'}")
    for symbol, reason in sorted(result.banned.items()):
        print(f"  entry-banned {symbol}: {reason}")
    if not result.entry_ready:
        print("  REAL ENTRY PATH REACHABLE but NO symbol is entry-ready.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
