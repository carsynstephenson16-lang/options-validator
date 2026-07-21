"""C1 entry-only real-session tests, using temporary registered stores only."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import pandas as pd

from options_researcher import h7_event_ledger as ledger
from options_researcher import h7_forward_book as book
from options_researcher import h7_paper_lifecycle as lifecycle
from options_researcher import h7_window_registration as registration
from options_researcher.h7_scope import scope_identity
from options_researcher.h7_session import (
    SessionRefused,
    open_real_session,
    record_session_evidence,
)
from research.hashing import config_hash, diagnostic_source_hash
from research.receipts import make_receipt

DECISION = "2026-07-20"  # operator decision date, inside the window
EVALUATION = "2026-07-17"  # prior completed source-data session
FILL = "2026-07-21"  # T+1 recorded quote session
INCLUDED = ("AMD", "AMZN", "CEG", "ET", "MSFT", "NOW", "PLTR", "TEM", "VST")


def _clock(iso: str):
    stamp = datetime.fromisoformat(iso)
    assert stamp.tzinfo is not None
    return lambda: stamp


def _owner_inputs() -> dict:
    return {
        "H7_STAGE8_EXPLICIT_AUTHORIZATION": "synthetic C1 fixture",
        "WINDOW_START_DECISION_SESSION": DECISION,
        "WINDOW_DECISION_SESSION_COUNT": 70,
        "WINDOW_END_RULE_ACKNOWLEDGED": "70 XNYS sessions from start",
        "WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED": "yes",
        "THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH": "2026-12-31",
        "THETADATA_CONFIRMATION_EVIDENCE": "synthetic fixture",
    }


def _evidence() -> dict:
    return {
        "review_evidence": "synthetic fixture",
        "activation_spec_sha256": "a" * 64,
        "code_commit": "b" * 40,
        "source_health_evidence_id": "sh:fixture",
        "data_gate_evidence_id": "dg:fixture",
        "darwin_durability_verified": True,
        "pre_append_state": "VALID EMPTY",
    }


def _long_action() -> dict:
    return {
        "lane": "a",
        "kind": "long_call",
        "expiration": "2026-10-16",
        "strike": 100.0,
        "delta": 0.60,
        # Ask 5.10 with the frozen 1% adverse-fill haircut is 5.16; the
        # one-leg round trip adds $1.30 in commission.
        "cost": 517.3,
        "max_loss": 517.3,
        "dte_band": [30, 90],
        "stop_ref": 80.0,
    }


def _chain() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "expiration": "2026-10-16",
                "strike": 100.0,
                "right": "C",
                "bid": 5.00,
                "ask": 5.10,
                "open_interest": 500,
                "delta": 0.60,
            }
        ]
    )


def _snapshot(base: Path) -> tuple[tuple[str, bytes], ...]:
    if not base.exists():
        return ()
    return tuple(
        sorted(
            (path.relative_to(base).as_posix(), path.read_bytes())
            for path in base.rglob("*")
            if path.is_file()
        )
    )


class RealSessionCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = self.root / "forward"
        self.scope = scope_identity()
        excluded = [symbol for symbol in self.scope["symbols"] if symbol not in INCLUDED]
        registration.register_window(
            owner=_owner_inputs(),
            evidence=_evidence(),
            base_dir=self.base,
            universe_manifest={
                "scope_id": self.scope["scope_id"],
                "scope_hash": self.scope["scope_hash"],
                "included": list(INCLUDED),
                "excluded": [
                    {"symbol": symbol, "reason": "EARNINGS-UNKNOWN"} for symbol in excluded
                ],
                "trim_rule": "source_health_ready_at_pinned_session",
            },
        )
        self._write_receipts(EVALUATION)
        self.real_before = _snapshot(lifecycle.REAL_FORWARD_STORE)
        self.addCleanup(self._assert_real_store_untouched)

    def _assert_real_store_untouched(self):
        self.assertEqual(_snapshot(lifecycle.REAL_FORWARD_STORE), self.real_before)

    def _paths(self, evaluation: str) -> tuple[Path, Path]:
        return (
            self.root / f"source-{evaluation}.json",
            self.root / f"gate-{evaluation}.json",
        )

    def _write_receipts(
        self, evaluation: str, *, verdict: str = "GO", amd_gate: str = "CLEAR", linked: bool = True
    ) -> Path:
        source_path, gate_path = self._paths(evaluation)
        symbol_map = {
            symbol: {
                "symbol": symbol,
                "healthy": True,
                "gate": amd_gate if symbol == "AMD" else "CLEAR",
                "flags": [],
            }
            for symbol in self.scope["symbols"]
        }
        source = make_receipt(
            "source_health",
            {
                "evaluation_session": evaluation,
                "requested_run_date": DECISION,
                "known_as_of_utc": f"{evaluation}T20:00:00+00:00",
                "scope": self.scope,
                "healthy_count": len(symbol_map),
                "unhealthy_count": 0,
                "unhealthy_symbols": [],
                "activation_ready": True,
                "symbols": symbol_map,
                "input_files": {},
                "config_hash": config_hash(),
                "source_hash": diagnostic_source_hash(),
            },
        )
        source_path.write_text(json.dumps(source))
        gate = make_receipt(
            "data_gate",
            {
                "evaluation_session": evaluation,
                "requested_run_date": DECISION,
                "scope": self.scope,
                "whole_universe_verdict": verdict,
                "go_count": len(symbol_map) if verdict == "GO" else 0,
                "no_go_count": 0 if verdict == "GO" else len(symbol_map),
                "symbols": {
                    symbol: {"symbol": symbol, "verdict": verdict}
                    for symbol in self.scope["symbols"]
                },
                "input_files": {},
                "source_health_receipt_hash": (
                    source["receipt_hash"] if linked else "not-the-source-hash"
                ),
                "source_health_receipt_path": str(source_path),
                "config_hash": config_hash(),
                "source_hash": diagnostic_source_hash(),
            },
        )
        gate_path.write_text(json.dumps(gate))
        return gate_path

    def open(self, **over):
        kwargs = {
            "base_dir": self.base,
            "decision_session": DECISION,
            "source_evaluation_session": EVALUATION,
            "data_gate_receipt_path": self._paths(EVALUATION)[1],
        }
        kwargs.update(over)
        return open_real_session(**kwargs)


class TestSessionRefusals(RealSessionCase):
    def test_refuses_missing_activation_or_receipt_linkage(self):
        with self.assertRaises(SessionRefused):
            self.open(base_dir=self.root / "empty")
        with self.assertRaises(SessionRefused):
            self.open(data_gate_receipt_path=self.root / "missing.json")

        self._write_receipts(EVALUATION, linked=False)
        with self.assertRaises(SessionRefused):
            self.open()

    def test_refuses_no_go_non_cohort_and_entry_ban(self):
        self._write_receipts(EVALUATION, verdict="NO_GO")
        with self.assertRaises(SessionRefused):
            self.open()

        self._write_receipts(EVALUATION)
        with self.assertRaises(SessionRefused):
            self.open(symbol="USAR")

        self._write_receipts(EVALUATION, amd_gate="BANNED")
        with self.assertRaises(SessionRefused):
            self.open(symbol="AMD")

    def test_refuses_before_registered_decision_window_not_prior_data_session(self):
        with self.assertRaises(SessionRefused):
            self.open(decision_session="2026-07-19")

        session = self.open(symbol="AMD")
        self.assertEqual(session.decision_session, DECISION)
        self.assertEqual(session.evaluation_session, EVALUATION)


class TestEntryOnlyRealPath(RealSessionCase):
    def test_publish_board_intent_approval_fill_and_keep_exits_refused(self):
        decision = self.open(symbol="AMD")
        decision_evidence = record_session_evidence(decision, symbol="AMD")
        self.assertTrue(decision_evidence.source_health.appended)
        self.assertTrue(decision_evidence.data_gate.appended)

        board_result = book.record_board_resolution(
            base_dir=decision,
            evaluation_session=EVALUATION,
            candidates=[
                {
                    "symbol": "AMD",
                    "lane": "a",
                    "session": EVALUATION,
                    "action": _long_action(),
                }
            ],
            source_health_id=decision_evidence.source_health.event_id,
            data_gate_id=decision_evidence.data_gate.event_id,
            clock=_clock("2026-07-21T01:00:00+00:00"),
        )
        intent = lifecycle.record_entry_intent(
            base_dir=decision,
            symbol="AMD",
            action=_long_action(),
            decision_chain=_chain(),
            decision_session=EVALUATION,
            source_health_id=decision_evidence.source_health.event_id,
            data_gate_id=decision_evidence.data_gate.event_id,
            board_resolution_id=board_result.event_id,
            chain_identity="sha256:decision-chain",
            closes_identity="sha256:decision-closes",
            clock=_clock("2026-07-21T01:00:00+00:00"),
        )
        stored_intent = next(
            event for event in ledger.read_events(self.base) if event.event_id == intent.event_id
        )
        self.assertEqual(stored_intent.evaluation_session, EVALUATION)
        self.assertEqual(stored_intent.payload["decision_session"], DECISION)
        self.assertEqual(stored_intent.payload["planned_fill_session"], FILL)

        approval = lifecycle.record_owner_approval(
            base_dir=decision,
            entry_intent_id=intent.event_id,
            clock=_clock("2026-07-21T18:00:00+00:00"),
        )
        self.assertEqual(approval.event_type, "owner_approval")

        fill_gate = self._write_receipts(FILL)
        fill = self.open(
            data_gate_receipt_path=fill_gate,
            source_evaluation_session=FILL,
            symbol="AMD",
        )
        fill_evidence = record_session_evidence(fill, symbol="AMD")
        opened = lifecycle.process_entry_fill(
            base_dir=fill,
            entry_intent_id=intent.event_id,
            fill_session=FILL,
            chain=_chain(),
            source_health_id=fill_evidence.symbol_source_health.event_id,
            data_gate_id=fill_evidence.data_gate.event_id,
            chain_identity="sha256:fill-chain",
            closes_identity="sha256:fill-closes",
            underlying_close=100.0,
            clock=_clock("2026-07-22T01:00:00+00:00"),
        )
        self.assertEqual(opened.event_type, "paper_fill", opened.payload)
        self.assertTrue(ledger.verify(self.base).valid)
        snapshot = book.derive_book(base_dir=fill, evaluation_session=FILL)
        self.assertEqual(snapshot.open_symbols, ("AMD",))

        with self.assertRaises(lifecycle.ActivationBoundaryError):
            lifecycle.process_exit_fill(
                base_dir=fill,
                exit_intent_id="no-exit-path",
                fill_session=FILL,
                chain=_chain(),
                data_gate_id=fill_evidence.data_gate.event_id,
                chain_identity="sha256:exit-chain",
                closes_identity="sha256:exit-closes",
            )


if __name__ == "__main__":
    unittest.main()
