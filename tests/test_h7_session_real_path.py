"""C1 entry-only real-session tests, using temporary registered stores only."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd

from options_researcher import h7_event_ledger as ledger
from options_researcher import h7_forward_book as book
from options_researcher import h7_paper_lifecycle as lifecycle
from options_researcher import h7_session as session_module
from options_researcher import h7_window_registration as registration
from options_researcher.h7_scope import scope_identity
from options_researcher.h7_session import (
    SessionRefused,
    open_real_session,
)
from options_researcher.h7_source_health import evaluate_health
from research.hashing import config_hash
from research.receipts import input_files, load_receipt, make_receipt

DECISION = "2026-07-20"  # operator decision date, inside the window
EVALUATION = "2026-07-17"  # prior completed source-data session
FILL = "2026-07-21"  # T+1 recorded quote session
FILL_REQUESTED = "2026-07-22"  # first run date after the T+1 close
INCLUDED = ("AMD", "AMZN", "CEG", "ET", "MSFT", "NOW", "PLTR", "TEM", "VST")
SOURCE_HASH = "c" * 64


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
        self.source_hash = patch(
            "options_researcher.h7_watch.diagnostic_source_hash", return_value=SOURCE_HASH
        )
        self.source_hash.start()
        self.addCleanup(self.source_hash.stop)
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
        self,
        evaluation: str,
        *,
        verdict: str = "GO",
        amd_gate: str = "CLEAR",
        linked: bool = True,
        unhealthy: tuple[str, ...] = (),
        source_names: tuple[str, ...] | None = None,
        symbols_override: dict | None = None,
        source_requested_run_date: str | None = None,
        gate_requested_run_date: str | None = None,
    ) -> Path:
        source_path, gate_path = self._paths(evaluation)
        default_requested = DECISION if evaluation == EVALUATION else FILL_REQUESTED
        source_requested = source_requested_run_date or default_requested
        gate_requested = gate_requested_run_date or default_requested
        unhealthy_set = set(unhealthy)
        source_names = source_names or tuple(self.scope["symbols"])
        source_symbol_map = symbols_override or {
            symbol: {
                "symbol": symbol,
                "healthy": symbol not in unhealthy_set,
                "gate": (
                    amd_gate
                    if symbol == "AMD"
                    else ("UNKNOWN" if symbol in unhealthy_set else "CLEAR")
                ),
                "flags": ["MISSING"] if symbol in unhealthy_set else [],
            }
            for symbol in source_names
        }
        # Derive counts from the map actually used (real evaluate_health()
        # output when symbols_override is given) rather than the synthetic
        # unhealthy_set, so both code paths stay internally consistent.
        source_unhealthy = sorted(
            symbol for symbol, row in source_symbol_map.items()
            if row.get("healthy") is not True
        )
        source = make_receipt(
            "source_health",
            {
                "evaluation_session": evaluation,
                "requested_run_date": source_requested,
                "known_as_of_utc": f"{evaluation}T20:00:00+00:00",
                "scope": self.scope,
                "healthy_count": len(source_symbol_map) - len(source_unhealthy),
                "unhealthy_count": len(source_unhealthy),
                "unhealthy_symbols": source_unhealthy,
                "activation_ready": not source_unhealthy,
                "symbols": source_symbol_map,
                "input_files": {},
                "config_hash": config_hash(),
                "source_hash": SOURCE_HASH,
            },
        )
        source_path.write_text(json.dumps(source))
        gate = make_receipt(
            "data_gate",
            {
                "evaluation_session": evaluation,
                "requested_run_date": gate_requested,
                "scope": self.scope,
                "whole_universe_verdict": verdict,
                "go_count": len(self.scope["symbols"]) if verdict == "GO" else 0,
                "no_go_count": 0 if verdict == "GO" else len(self.scope["symbols"]),
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
                "source_hash": SOURCE_HASH,
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

    def _write_watcher_receipt(
        self,
        evaluation: str,
        gate_path: Path,
        *,
        actionable: bool,
        requested_run_date: str | None = None,
    ) -> Path:
        bindings: dict[str, Path] = {}
        for symbol in self.scope["symbols"]:
            close = self.root / f"close-{evaluation}-{symbol}.cache"
            chain = self.root / f"chain-{evaluation}-{symbol}.cache"
            close.write_text(f"close {evaluation} {symbol}")
            chain.write_text(f"chain {evaluation} {symbol}")
            bindings[f"close:{symbol}"] = close
            bindings[f"chain:{symbol}"] = chain
        gate = load_receipt(gate_path, expected_type="data_gate")
        rows = (
            [
                {
                    "symbol": "AMD",
                    "lane": "lane_a",
                    "state": "ENTRY-OK",
                    "actionable": True,
                    "action": json.dumps(_long_action(), sort_keys=True),
                }
            ]
            if actionable
            else []
        )
        watcher = make_receipt(
            "watcher_decision",
            {
                "evaluation_session": evaluation,
                "requested_run_date": (
                    requested_run_date or (DECISION if evaluation == EVALUATION else FILL_REQUESTED)
                ),
                "scope": self.scope,
                "data_gate_receipt_hash": gate["receipt_hash"],
                "source_health_receipt_hash": gate["source_health_receipt_hash"],
                "input_files": input_files(bindings),
                "rows": rows,
                "errors": [],
                "actionable_count": len(rows),
                "config_hash": gate["config_hash"],
                "source_hash": gate["source_hash"],
            },
        )
        path = self.root / f"watcher-{evaluation}.json"
        path.write_text(json.dumps(watcher))
        return path


class TestSessionRefusals(RealSessionCase):
    def _forged_session(self) -> lifecycle.RealStoreSession:
        genuine = self.open()
        return lifecycle.RealStoreSession(
            base_dir=genuine.base_dir,
            activation_event_id=genuine.activation_event_id,
            decision_session=genuine.decision_session,
            evaluation_session=genuine.evaluation_session,
            data_gate_receipt_path=genuine.data_gate_receipt_path,
            source_health_receipt_path=genuine.source_health_receipt_path,
            data_gate_receipt_hash=genuine.data_gate_receipt_hash,
            source_health_receipt_hash=genuine.source_health_receipt_hash,
            data_gate_config_hash=genuine.data_gate_config_hash,
            data_gate_source_hash=genuine.data_gate_source_hash,
            included_symbols=genuine.included_symbols,
        )

    def test_forged_session_cannot_publish_receipt_evidence(self):
        with self.assertRaises(lifecycle.ActivationBoundaryError):
            session_module.record_session_evidence(
                self._forged_session(),
                symbol="AMD",
            )

    def test_forged_session_cannot_reach_entry_lifecycle(self):
        with self.assertRaises(lifecycle.ActivationBoundaryError):
            lifecycle.record_owner_approval(
                base_dir=self._forged_session(),
                entry_intent_id="s4.entry_intent:forged",
            )

    def test_forged_session_cannot_reach_forward_book(self):
        with self.assertRaises(lifecycle.ActivationBoundaryError):
            book.derive_book(
                base_dir=self._forged_session(),
                evaluation_session=EVALUATION,
            )

    def test_copied_factory_session_loses_authority(self):
        copied = replace(self.open(), decision_session="2026-07-21")

        with self.assertRaises(lifecycle.ActivationBoundaryError):
            lifecycle.record_owner_approval(
                base_dir=copied,
                entry_intent_id="s4.entry_intent:forged",
            )

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

    def test_uses_registered_cohort_for_health_veto(self):
        excluded = tuple(sorted(set(self.scope["symbols"]) - set(INCLUDED)))
        self._write_receipts(EVALUATION, unhealthy=excluded)

        session = self.open()
        self.assertEqual(session.included_symbols, INCLUDED)
        evidence = session_module.record_session_evidence(session, symbol="AMD")
        self.assertEqual(evidence.source_health.payload["healthy_symbols"], sorted(INCLUDED))

    def test_refuses_receipt_not_covering_full_official_scope(self):
        self._write_receipts(EVALUATION, source_names=INCLUDED)

        with self.assertRaises(SessionRefused) as ctx:
            self.open()
        self.assertIn(
            "does not cover the full official scope",
            str(ctx.exception),
        )

    def test_refuses_before_registered_decision_window_not_prior_data_session(self):
        with self.assertRaises(SessionRefused):
            self.open(decision_session="2026-07-19")

        session = self.open(symbol="AMD")
        self.assertEqual(session.decision_session, DECISION)
        self.assertEqual(session.evaluation_session, EVALUATION)

    def test_refuses_source_session_not_bound_to_decision_operation(self):
        stale_evaluation = "2026-07-16"
        stale_gate = self._write_receipts(
            stale_evaluation,
            source_requested_run_date=DECISION,
            gate_requested_run_date=DECISION,
        )

        with self.assertRaisesRegex(SessionRefused, "decision operation requires"):
            self.open(
                data_gate_receipt_path=stale_gate,
                source_evaluation_session=stale_evaluation,
            )

    def test_refuses_gate_requested_for_another_run_date(self):
        self._write_receipts(
            EVALUATION,
            gate_requested_run_date="2026-07-21",
        )

        with self.assertRaisesRegex(SessionRefused, "requested run date"):
            self.open()

    def test_refuses_source_health_requested_for_another_run_date(self):
        self._write_receipts(
            EVALUATION,
            source_requested_run_date="2026-07-21",
        )

        with self.assertRaisesRegex(SessionRefused, "requested run date"):
            self.open()

    def test_refuses_watcher_requested_for_another_run_date(self):
        opened = self.open(symbol="AMD")
        watcher = self._write_watcher_receipt(
            EVALUATION,
            self._paths(EVALUATION)[1],
            actionable=True,
            requested_run_date="2026-07-21",
        )

        with self.assertRaisesRegex(SessionRefused, "requested run date"):
            session_module._watcher_receipt_for_session(
                path=watcher,
                session=opened,
            )

    def _grace_shaped_assertions(self, evaluation: str) -> list[dict]:
        """Real v3-gating-store-shaped fixtures: NOW reported 7 days before
        `evaluation` with only a CONFIRMED (never occurred) record -- the
        exact 2026-07-24 owner-amendment shape. The rest of the registered
        cohort carries an ordinary far-future confirmed schedule."""
        known = datetime.fromisoformat("2026-07-01T12:00:00+00:00")
        on = date.fromisoformat(evaluation)

        def row(symbol: str, expected: date, *, event: str) -> dict:
            return {
                "record_id": f"{symbol}-{event}", "symbol": symbol,
                "event_id": f"{symbol}-{event}", "fiscal_period": "FY26Q2",
                "record_type": "assertion",
                "event_class": "actual_quarterly_earnings", "status": "confirmed",
                "expected_date": expected, "occurred_date": None,
                "session_timing": "amc", "source_type": "company_pr",
                "source_url": "https://example.test/ir",
                "known_as_of_utc": known, "checked_at_utc": known,
                "supersedes": "", "promoted_from": "", "notes": "",
            }

        rows = [row("NOW", on - timedelta(days=7), event="past")]
        for symbol in INCLUDED:
            if symbol != "NOW":
                rows.append(row(symbol, date(2026, 9, 1), event="future"))
        return rows

    def test_grace_name_in_cohort_no_longer_refuses_the_door(self):
        # 2026-07-24 owner amendment: the door refused the WHOLE registered
        # cohort the moment NOW went UNHEALTHY [MISSING] on nothing more
        # than having reported. Prove the fix at the layer h7_session.py
        # actually consumes: run the REAL evaluate_health() over a
        # NOW-shaped fixture (not a hand-set healthy flag) and confirm the
        # resulting receipt lets the door open.
        result = evaluate_health(
            requested_on=date.fromisoformat(EVALUATION),
            on=date.fromisoformat(EVALUATION),
            known_as_of=datetime.fromisoformat(f"{EVALUATION}T20:00:00+00:00"),
            assertions=self._grace_shaped_assertions(EVALUATION),
            names=self.scope["symbols"],
        )
        self.assertTrue(result["symbols"]["NOW"]["healthy"])
        self.assertEqual(result["symbols"]["NOW"]["coverage"], "post_report_grace")
        self.assertEqual(result["symbols"]["NOW"]["gate"], "CLEAR")

        self._write_receipts(EVALUATION, symbols_override=result["symbols"])

        session = self.open()   # must NOT raise SessionRefused
        self.assertIn("NOW", session.included_symbols)
        evidence = session_module.record_session_evidence(session, symbol="NOW")
        self.assertIn("NOW", evidence.source_health.payload["healthy_symbols"])


class TestEntryOnlyRealPath(RealSessionCase):
    def test_fill_handoff_opens_then_monitors_a_fresh_exit_session(self):
        fill_session = self.open(symbol="AMD")
        entry_result = lifecycle.TransitionResult(
            event_id="s4.paper_fill.open:fixture",
            event_type="paper_fill",
            payload={},
            appended=True,
        )
        exit_authority = object()
        exit_report = Mock(failed=False)
        calls: list[str] = []

        with (
            patch.object(
                session_module,
                "fill_entry",
                side_effect=lambda **_kwargs: calls.append("entry_fill") or entry_result,
            ) as fill_entry,
            patch(
                "options_researcher.h7_exit_session.open_real_exit_session",
                side_effect=lambda **_kwargs: calls.append("exit_open") or exit_authority,
            ) as open_exit,
            patch(
                "options_researcher.h7_exit_session.monitor_real_exits",
                side_effect=lambda _authority: calls.append("exit_monitor") or exit_report,
            ) as monitor,
        ):
            entry, report = session_module.fill_entry_and_observe_exit(
                session=fill_session,
                entry_intent_id="s4.entry_intent:fixture",
                symbol="AMD",
                watcher_receipt_path=self.root / "watcher.json",
            )

        self.assertIs(entry, entry_result)
        self.assertIs(report, exit_report)
        self.assertEqual(calls, ["entry_fill", "exit_open", "exit_monitor"])
        fill_entry.assert_called_once()
        open_exit.assert_called_once_with(
            data_gate_receipt_path=fill_session.data_gate_receipt_path,
            decision_session=fill_session.decision_session,
            source_evaluation_session=fill_session.evaluation_session,
            base_dir=fill_session.base_dir,
        )
        monitor.assert_called_once_with(exit_authority)

    def test_publish_board_intent_approval_fill_and_keep_exits_refused(self):
        decision = self.open(symbol="AMD")
        decision_watcher = self._write_watcher_receipt(
            EVALUATION, self._paths(EVALUATION)[1], actionable=True
        )
        with patch.object(session_module, "load_range", return_value={EVALUATION: _chain()}):
            with patch.object(
                lifecycle,
                "_clock_utc",
                return_value=datetime(2026, 7, 21, 1, tzinfo=timezone.utc),
            ):
                intent = session_module.propose_entry(
                    session=decision,
                    symbol="AMD",
                    lane="a",
                    watcher_receipt_path=decision_watcher,
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
            operation="fill",
        )
        fill_watcher = self._write_watcher_receipt(FILL, fill_gate, actionable=False)
        with patch.object(session_module, "load_range", return_value={FILL: _chain()}):
            with patch.object(
                session_module,
                "load_closes_adjusted",
                return_value=pd.Series([100.0], index=[FILL]),
            ):
                with patch.object(
                    lifecycle,
                    "_clock_utc",
                    return_value=datetime(2026, 7, 22, 1, tzinfo=timezone.utc),
                ):
                    opened = session_module.fill_entry(
                        session=fill,
                        entry_intent_id=intent.event_id,
                        symbol="AMD",
                        watcher_receipt_path=fill_watcher,
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
                data_gate_id=f"h7:data_gate:{FILL}",
                chain_identity="sha256:exit-chain",
                closes_identity="sha256:exit-closes",
            )


if __name__ == "__main__":
    unittest.main()
