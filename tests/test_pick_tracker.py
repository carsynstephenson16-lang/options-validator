"""Contract tests for Brief 27's descriptive, registration-gated tracker."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from options_researcher import pick_tracker as tracker


def candidate(
    candidate_id: str,
    *,
    symbol: str = "VST",
    lane: str = "long_call",
    side: str = "buy",
    right: str = "C",
    strike: float = 100.0,
    expiry: str = "2026-09-18",
    risk_kind: str = "ENTRY_DEBIT_AT_FILL",
    risk_value: float | None = None,
    coverage: dict | None = None,
) -> dict:
    return {
        "candidate_id": candidate_id,
        "symbol": symbol,
        "lane": lane,
        "strike": strike,
        "expiry": expiry,
        "dte": 24,
        "raw_quote": {"bid": 1.0, "ask": 1.2},
        "source_row_hash": "a" * 64,
        "pick_position": {
            "schema": "pick_position/v1",
            "evaluated_leg": {
                "symbol": symbol,
                "right": right,
                "strike": strike,
                "expiry": expiry,
                "side": side,
                "contracts": 1,
            },
            "coverage_context": coverage,
            "risk_basis": {
                "kind": risk_kind,
                "value": risk_value,
                **({"derivation": "EVALUATED_STRIKE_X_100"} if lane == "put" else {}),
            },
            "pnl_scope": "INCREMENTAL_OPTION_LEG_ONLY",
        },
    }


def snapshot(as_of: str, items: list[dict], *, context_items: list[dict] | None = None) -> dict:
    return {
        "schema": "picks_snapshot/v1",
        "evaluation_date": as_of,
        "data_as_of": as_of,
        "html_sha256": "b" * 64,
        "render_id": "c" * 64,
        "capture_receipt_path": f"reports/schwab_chains/{as_of}/preclose.json",
        "capture_receipt_sha256": "d" * 64,
        "config_hash": "e" * 64,
        "source_row_hashes": ["a" * 64],
        "frozen_baseline": {
            "state": "READY",
            "watch_included": False,
            "candidates": items,
        },
        "frozen_baseline_watch_inclusive": {
            "state": "READY",
            "watch_included": True,
            "candidates": items,
        },
        "context_lane": {
            "state": "READY",
            "error": None,
            "candidates": context_items if context_items is not None else items,
        },
        "experiment_nominations": {
            name: {"state": "NOT_A_SELECTOR", "descriptive_only": True}
            for name in (
                "exp_beta_qqq",
                "exp_tail_shape",
                "exp_spread_stability",
                "exp_tbill_carry",
                "exp_short_positioning",
            )
        },
    }


def chain(
    *,
    bid: float = 2.0,
    ask: float = 2.2,
    include: bool = True,
    expiry: str = "2026-09-18",
) -> pd.DataFrame:
    rows = []
    if include:
        rows.append(
            {
                "expiration": expiry,
                "strike": 100.0,
                "right": "C",
                "bid": bid,
                "ask": ask,
                "open_interest": 500,
            }
        )
    return pd.DataFrame(
        rows,
        columns=("expiration", "strike", "right", "bid", "ask", "open_interest"),
    )


class SnapshotAndMembershipTests(unittest.TestCase):
    def test_snapshot_html_hash_mismatch_fails_closed(self):
        payload = snapshot("2026-08-25", [candidate("VST:long_call:one")])
        with self.assertRaisesRegex(tracker.TrackerError, "SNAPSHOT_RENDER_MISMATCH"):
            tracker.validate_snapshot(payload, b"different html")

    def test_snapshot_capture_receipt_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = root / "reports/schwab_chains/2026-08-25/preclose.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_bytes(b"verified receipt")
            html = b"bound html"
            payload = snapshot("2026-08-25", [candidate("VST:long_call:one")])
            payload["html_sha256"] = hashlib.sha256(html).hexdigest()
            payload["capture_receipt_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
            tracker.validate_snapshot(payload, html, input_root=root)
            receipt.write_bytes(b"tampered")
            with self.assertRaisesRegex(tracker.TrackerError, "CAPTURE_RECEIPT_MISMATCH"):
                tracker.validate_snapshot(payload, html, input_root=root)

    def test_unverified_session_refuses_without_creating_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / "reports/pick_tracker/dryrun/events.jsonl"
            with self.assertRaisesRegex(tracker.TrackerError, "SESSION_UNVERIFIED"):
                tracker.append_membership(
                    snapshot("2026-08-25", [candidate("VST:long_call:one")]),
                    journal_path=journal,
                    verified_sessions=["2026-08-22"],
                )
            self.assertFalse(journal.exists())

    def test_slot_stays_open_across_restrikes_then_reopens_after_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / "reports/pick_tracker/dryrun/events.jsonl"
            sessions = [
                "2026-08-25",
                "2026-08-26",
                "2026-08-27",
                "2026-08-28",
            ]
            first = tracker.append_membership(
                snapshot(sessions[0], [candidate("VST:long_call:one")]),
                journal_path=journal,
                verified_sessions=sessions,
            )
            second = tracker.append_membership(
                snapshot(sessions[1], [candidate("VST:long_call:two")]),
                journal_path=journal,
                verified_sessions=sessions,
            )
            exited = tracker.append_membership(
                snapshot(sessions[2], []),
                journal_path=journal,
                verified_sessions=sessions,
            )
            reentered = tracker.append_membership(
                snapshot(sessions[3], [candidate("VST:long_call:three")]),
                journal_path=journal,
                verified_sessions=sessions,
            )

            self.assertEqual(len(first["arms"]["frozen_baseline"]["entries"]), 1)
            self.assertEqual(second["arms"]["frozen_baseline"]["entries"], [])
            self.assertEqual(
                second["arms"]["frozen_baseline"]["restrikes"][0]["to_candidate_id"],
                "VST:long_call:two",
            )
            self.assertEqual(len(exited["arms"]["frozen_baseline"]["exits"]), 1)
            self.assertEqual(len(reentered["arms"]["frozen_baseline"]["entries"]), 1)

    def test_ten_continuous_sessions_open_once_and_only_annotate_restrikes(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / "reports/pick_tracker/dryrun/events.jsonl"
            sessions = [f"2026-08-{day:02d}" for day in range(1, 11)]
            records = [
                tracker.append_membership(
                    snapshot(
                        session,
                        [candidate(f"VST:long_call:restrike-{index}")],
                    ),
                    journal_path=journal,
                    verified_sessions=sessions,
                )
                for index, session in enumerate(sessions)
            ]
            arm_records = [record["arms"]["frozen_baseline"] for record in records]
            self.assertEqual(sum(len(record["entries"]) for record in arm_records), 1)
            self.assertEqual(sum(len(record["restrikes"]) for record in arm_records), 9)

    def test_idempotent_reappend_is_noop_and_different_hash_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / "reports/pick_tracker/dryrun/events.jsonl"
            payload = snapshot("2026-08-25", [candidate("VST:long_call:one")])
            first = tracker.append_membership(
                payload,
                journal_path=journal,
                verified_sessions=["2026-08-25"],
            )
            second = tracker.append_membership(
                payload,
                journal_path=journal,
                verified_sessions=["2026-08-25"],
            )
            self.assertEqual(second, first)
            self.assertEqual(len(journal.read_text().splitlines()), 1)
            changed = snapshot("2026-08-25", [candidate("MSFT:long_call:one", symbol="MSFT")])
            with self.assertRaisesRegex(tracker.TrackerConflict, "different content"):
                tracker.append_membership(
                    changed,
                    journal_path=journal,
                    verified_sessions=["2026-08-25"],
                )

    def test_unregistered_scored_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "reports/pick_tracker"
            with self.assertRaisesRegex(tracker.RegistrationRequired, "dryrun"):
                tracker.append_membership(
                    snapshot("2026-08-25", []),
                    journal_path=root / "scored/events.jsonl",
                    verified_sessions=["2026-08-25"],
                    reports_root=root,
                )
            fabricated = {
                "schema": "pick_tracker_registration/v1",
                "owner_typed_at": "2026-08-26T12:00:00-04:00",
                "ledger_seq": 31,
            }
            with self.assertRaisesRegex(tracker.RegistrationRequired, "dryrun"):
                tracker.append_membership(
                    snapshot("2026-08-25", []),
                    journal_path=root / "scored/events.jsonl",
                    verified_sessions=["2026-08-25"],
                    reports_root=root,
                    registration=fabricated,
                )

            with self.assertRaisesRegex(tracker.RegistrationRequired, "dryrun"):
                tracker.append_membership(
                    snapshot("2026-08-25", []),
                    journal_path=root / "scored/bypass.jsonl",
                    verified_sessions=["2026-08-25"],
                )
            with self.assertRaisesRegex(tracker.RegistrationRequired, "dryrun"):
                tracker.append_membership(
                    snapshot("2026-08-25", []),
                    journal_path=Path(tmp) / "scored/events.jsonl",
                    verified_sessions=["2026-08-25"],
                )

    def test_record_cli_checks_session_before_reading_snapshot(self):
        from unittest import mock

        with (
            mock.patch(
                "options_researcher.schwab_chain_view.verified_sessions",
                return_value=([], []),
            ),
            mock.patch.object(tracker, "SNAPSHOT_PATH", Path("/definitely/missing/snapshot.json")),
            self.assertRaisesRegex(tracker.TrackerError, "SESSION_UNVERIFIED"),
        ):
            tracker.record_cli("2026-08-25")

    def test_disabled_context_arm_is_loud_and_refuses_primary_contrast(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = snapshot("2026-08-25", [candidate("VST:long_call:one")])
            payload["context_lane"] = {
                "state": "DISABLED",
                "error": None,
                "candidates": [],
            }
            record = tracker.append_membership(
                payload,
                journal_path=Path(tmp) / "dryrun/events.jsonl",
                verified_sessions=["2026-08-25"],
            )
            self.assertEqual(record["arms"]["context_lane"]["state"], "DISABLED")
            outcomes = tracker.evaluate_records(
                [record],
                as_of="2026-08-25",
                verified_sessions=["2026-08-25"],
                chain_loader=lambda _symbol, _session: self.fail("no fill yet"),
                trading_days_fn=lambda _start, _end: [
                    "2026-08-25",
                    "2026-08-26",
                    "2026-08-27",
                ],
                close_loader=lambda _symbol, _session: self.fail("no expiry"),
            )
            board = tracker.build_scoreboard(outcomes)
            self.assertEqual(board["arm_states"]["context_lane"], "LANE_DISABLED")
            self.assertEqual(board["primary_contrast"]["ci_state"], "ARM_UNAVAILABLE")


class FillAndPositionTests(unittest.TestCase):
    @staticmethod
    def sessions(_start: str, _end: str) -> list[str]:
        return ["2026-08-25", "2026-08-26", "2026-08-27", "2026-08-28"]

    def test_decision_quote_is_never_used_and_d_plus_one_worse_side_fills(self):
        decision = candidate("VST:long_call:one")
        calls: list[str] = []

        def load(_symbol: str, session: str) -> pd.DataFrame:
            calls.append(session)
            return chain(bid=5.0, ask=5.5) if session == "2026-08-25" else chain(bid=2.0, ask=2.2)

        result = tracker.resolve_fill(
            decision,
            decision_session="2026-08-25",
            verified_sessions=["2026-08-25", "2026-08-26"],
            chain_loader=load,
            trading_days_fn=self.sessions,
        )
        self.assertEqual(calls, ["2026-08-26"])
        self.assertEqual(result["fill_session"], "2026-08-26")
        self.assertGreater(result["fill_price"], 2.2)

    def test_missing_d_plus_one_uses_verified_d_plus_two(self):
        result = tracker.resolve_fill(
            candidate("VST:long_call:one"),
            decision_session="2026-08-25",
            verified_sessions=["2026-08-25", "2026-08-27"],
            chain_loader=lambda _symbol, _session: chain(),
            trading_days_fn=self.sessions,
        )
        self.assertEqual(result["fill_session"], "2026-08-27")

    def test_no_verified_candidate_cancels_and_rerun_on_decision_cannot_fill(self):
        result = tracker.resolve_fill(
            candidate("VST:long_call:one"),
            decision_session="2026-08-25",
            verified_sessions=["2026-08-25"],
            chain_loader=lambda _symbol, _session: self.fail("loader must not run"),
            trading_days_fn=self.sessions,
        )
        self.assertEqual(result["status"], "CANCELLED_NO_FILL_DATA")

        pending = tracker.resolve_fill(
            candidate("VST:long_call:one"),
            decision_session="2026-08-25",
            current_session="2026-08-26",
            verified_sessions=["2026-08-25"],
            chain_loader=lambda _symbol, _session: self.fail("loader must not run"),
            trading_days_fn=self.sessions,
        )
        self.assertEqual(pending["status"], "PENDING_FILL_DATA")

    def test_first_verified_candidate_absent_or_invalid_never_hunts_later(self):
        calls: list[str] = []

        def absent(_symbol: str, session: str) -> pd.DataFrame:
            calls.append(session)
            return chain(include=False) if session == "2026-08-26" else chain()

        result = tracker.resolve_fill(
            candidate("VST:long_call:one"),
            decision_session="2026-08-25",
            verified_sessions=["2026-08-26", "2026-08-27"],
            chain_loader=absent,
            trading_days_fn=self.sessions,
        )
        self.assertEqual(result["status"], "CANCELLED_CONTRACT_ABSENT")
        self.assertEqual(calls, ["2026-08-26"])

        invalid = tracker.resolve_fill(
            candidate("VST:long_call:one"),
            decision_session="2026-08-25",
            verified_sessions=["2026-08-26", "2026-08-27"],
            chain_loader=lambda _symbol, _session: chain(bid=3.0, ask=2.0),
            trading_days_fn=self.sessions,
        )
        self.assertEqual(invalid["status"], "CANCELLED_FILL_SCHEMA_INVALID")

    def test_lane_position_schema_and_basis_fail_closed(self):
        put = candidate(
            "VST:put:one",
            lane="put",
            side="sell",
            right="P",
            risk_kind="ASSIGNMENT_CAPITAL",
            risk_value=10_000.0,
        )
        self.assertEqual(tracker.validate_position(put)["risk_basis"]["value"], 10_000.0)
        put["pick_position"]["risk_basis"]["value"] = 9_999.0
        with self.assertRaisesRegex(tracker.PositionSchemaError, "strike x 100"):
            tracker.validate_position(put)

        cc = candidate(
            "VST:cc:one",
            lane="cc",
            side="sell",
            risk_kind="FROZEN_100_SHARE_COST_BASIS",
            risk_value=None,
            coverage={"shares": 100, "cost_basis": None, "source_row_hash": "a" * 64},
        )
        with self.assertRaisesRegex(tracker.PositionSchemaError, "risk basis"):
            tracker.validate_position(cc)

        pmcc = candidate(
            "VST:pmcc:one",
            lane="pmcc",
            side="sell",
            risk_kind="FROZEN_COVERING_LEAPS_ENTRY_DEBIT",
            risk_value=1_000.0,
            coverage={"id": "p1", "symbol": "VST", "strike": 80.0, "entry_price": 10.0},
        )
        with self.assertRaisesRegex(tracker.PositionSchemaError, "PMCC coverage"):
            tracker.validate_position(pmcc)

        cancelled = tracker.resolve_fill(
            pmcc,
            decision_session="2026-08-25",
            verified_sessions=["2026-08-26"],
            chain_loader=lambda _symbol, _session: chain(),
            trading_days_fn=self.sessions,
        )
        self.assertEqual(cancelled["status"], "CANCELLED_POSITION_SCHEMA_INVALID")

    def test_position_schema_rejects_identity_side_and_basis_mismatches(self):
        wrong_symbol = candidate("VST:long_call:one")
        wrong_symbol["pick_position"]["evaluated_leg"]["symbol"] = "MSFT"
        with self.assertRaisesRegex(tracker.PositionSchemaError, "symbol"):
            tracker.validate_position(wrong_symbol)

        wrong_side = candidate(
            "VST:put:one",
            lane="put",
            side="buy",
            right="P",
            risk_kind="ASSIGNMENT_CAPITAL",
            risk_value=10_000.0,
        )
        with self.assertRaisesRegex(tracker.PositionSchemaError, "lane/right/side"):
            tracker.validate_position(wrong_side)

        cc = candidate(
            "VST:cc:one",
            lane="cc",
            side="sell",
            risk_kind="FROZEN_100_SHARE_COST_BASIS",
            risk_value=9_999.0,
            coverage={
                "symbol": "VST",
                "shares": 100,
                "declared_shares": 100,
                "cost_basis": 100.0,
                "acquired": "2025-01-02",
                "source_row_hash": "a" * 64,
            },
        )
        with self.assertRaisesRegex(tracker.PositionSchemaError, "coverage cost basis"):
            tracker.validate_position(cc)

    def test_coverage_change_cancels_before_chain_lookup(self):
        decision = candidate(
            "VST:cc:one",
            lane="cc",
            side="sell",
            risk_kind="FROZEN_100_SHARE_COST_BASIS",
            risk_value=10_000.0,
            coverage={
                "symbol": "VST",
                "shares": 100,
                "declared_shares": 100,
                "cost_basis": 100.0,
                "acquired": "2025-01-02",
                "source_row_hash": "a" * 64,
            },
        )
        result = tracker.resolve_fill(
            decision,
            decision_session="2026-08-25",
            verified_sessions=["2026-08-26"],
            chain_loader=lambda _symbol, _session: self.fail("chain must not load"),
            trading_days_fn=self.sessions,
            coverage_validator=lambda _position, _session: False,
        )
        self.assertEqual(result["status"], "CANCELLED_COVERAGE_CHANGED")

    def test_current_coverage_identity_accepts_exact_cc_source_row(self):
        identity = {
            "symbol": "VST",
            "shares": 100,
            "declared_shares": 100,
            "cost_basis": 100.0,
            "acquired": "2025-01-02",
        }
        identity["source_row_hash"] = tracker._identity_hash(identity)
        decision = candidate(
            "VST:cc:one",
            lane="cc",
            side="sell",
            risk_kind="FROZEN_100_SHARE_COST_BASIS",
            risk_value=10_000.0,
            coverage=identity,
        )
        position = tracker.validate_position(decision)
        holdings = pd.DataFrame(
            [{"symbol": "VST", "shares": 100, "cost_basis": 100.0, "acquired": "2025-01-02"}]
        )
        positions = pd.DataFrame(
            columns=[
                "id",
                "structure",
                "symbol",
                "right",
                "strike",
                "expiration",
                "contracts",
                "entry_date",
                "entry_price",
                "bucket",
            ]
        )
        self.assertTrue(
            tracker.coverage_identity_matches(position, holdings=holdings, positions=positions)
        )

    def test_mark_gap_and_coverage_pnl_exclusion(self):
        filled = tracker.resolve_fill(
            candidate("VST:long_call:one"),
            decision_session="2026-08-25",
            verified_sessions=["2026-08-26"],
            chain_loader=lambda _symbol, _session: chain(),
            trading_days_fn=self.sessions,
        )
        gap = tracker.mark_position(
            filled, chain_frame=chain(include=False), mark_session="2026-08-27"
        )
        self.assertEqual(gap["status"], "MARK_GAP")
        marked = tracker.mark_position(
            filled, chain_frame=chain(bid=3.0, ask=3.2), mark_session="2026-08-27"
        )
        self.assertEqual(marked["pnl_scope"], "INCREMENTAL_OPTION_LEG_ONLY")
        self.assertNotIn("coverage_pnl", marked)

    def test_per_lane_mark_schedules(self):
        self.assertEqual(tracker.mark_schedule("leaps", dte_at_fill=200), (21, 63, 126))
        self.assertEqual(tracker.mark_schedule("long_call", dte_at_fill=20), (5, 10, 20))
        self.assertEqual(tracker.mark_schedule("put", dte_at_fill=31), (5, 10, 21))
        self.assertEqual(tracker.mark_schedule("put", dte_at_fill=30), (5, 10))

    def test_expiry_intrinsic_and_normalized_drawdown(self):
        filled = tracker.resolve_fill(
            candidate("VST:long_call:one"),
            decision_session="2026-08-25",
            verified_sessions=["2026-08-26"],
            chain_loader=lambda _symbol, _session: chain(),
            trading_days_fn=self.sessions,
        )
        terminal = tracker.mark_at_expiry(
            filled,
            underlying_close=103.0,
            expiry_session="2026-09-18",
        )
        self.assertEqual(terminal["status"], "SETTLED")
        self.assertEqual(terminal["termination"], "expiry_intrinsic")
        self.assertAlmostEqual(
            tracker.max_drawdown([0.10, -0.05, 0.20, 0.15]),
            -0.15,
        )

    def test_evaluator_applies_marks_then_expiry_and_omits_post_expiry_marks(self):
        opening = candidate(
            "VST:long_call:short",
            expiry="2026-09-04",
        )
        record = {
            "as_of": "2026-08-25",
            "arms": {
                arm: {
                    "entries": [{"slot": "VST:long_call", "candidate": opening}],
                    "restrikes": [],
                    "exits": [],
                    "current_slots": {"VST:long_call": opening},
                }
                for arm in ("frozen_baseline", "context_lane")
            },
        }

        def calendar(start: str, end: str) -> list[str]:
            cursor = date.fromisoformat(start)
            stop = date.fromisoformat(end)
            days = []
            while cursor <= stop:
                if cursor.weekday() < 5:
                    days.append(cursor.isoformat())
                cursor += timedelta(days=1)
            return days

        outcomes = tracker.evaluate_records(
            [record],
            as_of="2026-09-25",
            verified_sessions=calendar("2026-08-25", "2026-09-25"),
            chain_loader=lambda _symbol, _session: chain(expiry="2026-09-04"),
            trading_days_fn=calendar,
            close_loader=lambda _symbol, _session: 103.0,
        )
        self.assertEqual(len(outcomes), 2)
        first = outcomes[0]
        self.assertEqual(first["status"], "SETTLED")
        self.assertEqual(first["unreachable_marks"], 2)
        self.assertEqual(
            [mark["status"] for mark in first["marks"]],
            ["MARKED", "MARK_AFTER_EXPIRY", "MARK_AFTER_EXPIRY", "SETTLED"],
        )
        self.assertEqual(first["coverage_context_status"], "NOT_APPLICABLE")
        self.assertIn(first["outcome_word"], {"gained after costs", "lost after costs"})

    def test_expiry_aligned_schedule_has_one_intrinsic_mark(self):
        opening = candidate("VST:long_call:expiry", expiry="2026-09-02")
        record = {
            "as_of": "2026-08-25",
            "arms": {
                arm: {
                    "state": "READY",
                    "entries": [{"slot": "VST:long_call", "candidate": opening}],
                    "restrikes": [],
                    "exits": [],
                    "current_slots": {"VST:long_call": opening},
                }
                for arm in ("frozen_baseline", "context_lane")
            },
        }

        def calendar(start: str, end: str) -> list[str]:
            cursor, stop, days = date.fromisoformat(start), date.fromisoformat(end), []
            while cursor <= stop:
                if cursor.weekday() < 5:
                    days.append(cursor.isoformat())
                cursor += timedelta(days=1)
            return days

        outcomes = tracker.evaluate_records(
            [record],
            as_of="2026-09-03",
            verified_sessions=calendar("2026-08-25", "2026-09-03"),
            chain_loader=lambda _symbol, _session: chain(expiry="2026-09-02"),
            trading_days_fn=calendar,
            close_loader=lambda _symbol, _session: 103.0,
        )
        expiry_marks = [
            mark for mark in outcomes[0]["marks"] if mark.get("mark_session") == "2026-09-02"
        ]
        self.assertEqual(len(expiry_marks), 1)
        self.assertEqual(expiry_marks[0]["termination"], "expiry_intrinsic")

    def test_coverage_is_revalidated_before_marks(self):
        opening = candidate(
            "VST:cc:coverage",
            lane="cc",
            side="sell",
            risk_kind="FROZEN_100_SHARE_COST_BASIS",
            risk_value=10_000.0,
            coverage={
                "symbol": "VST",
                "shares": 100,
                "declared_shares": 100,
                "cost_basis": 100.0,
                "acquired": "2025-01-02",
                "source_row_hash": "a" * 64,
            },
        )
        record = {
            "as_of": "2026-08-25",
            "arms": {
                arm: {
                    "state": "READY",
                    "entries": [{"slot": "VST:cc", "candidate": opening}],
                    "restrikes": [],
                    "exits": [],
                    "current_slots": {"VST:cc": opening},
                }
                for arm in ("frozen_baseline", "context_lane")
            },
        }
        calls = 0

        def coverage(_position, _session):
            nonlocal calls
            calls += 1
            return calls == 1

        outcomes = tracker.evaluate_records(
            [record],
            as_of="2026-09-03",
            verified_sessions=self.sessions("", ""),
            chain_loader=lambda _symbol, _session: chain(),
            trading_days_fn=lambda _start, _end: [
                "2026-08-25",
                "2026-08-26",
                "2026-08-27",
                "2026-08-28",
                "2026-08-31",
                "2026-09-01",
                "2026-09-02",
                "2026-09-03",
                "2026-09-04",
                "2026-09-08",
                "2026-09-09",
                "2026-09-10",
                "2026-09-11",
                "2026-09-14",
                "2026-09-15",
                "2026-09-16",
                "2026-09-17",
                "2026-09-18",
                "2026-09-21",
                "2026-09-22",
                "2026-09-23",
                "2026-09-24",
                "2026-09-25",
            ],
            close_loader=lambda _symbol, _session: 100.0,
            coverage_validator=coverage,
        )
        self.assertEqual(outcomes[0]["status"], "CANCELLED_COVERAGE_CHANGED")
        self.assertGreaterEqual(calls, 2)


class ScoreboardTests(unittest.TestCase):
    def test_raw_dollars_never_pool_and_contrast_pairs_lanes(self):
        outcomes = [
            {"arm": "frozen_baseline", "lane": "long_call", "pnl": 100.0, "return": 0.10},
            {"arm": "context_lane", "lane": "long_call", "pnl": 80.0, "return": 0.20},
            {"arm": "frozen_baseline", "lane": "put", "pnl": 1_000.0, "return": 0.01},
        ]
        board = tracker.build_scoreboard(outcomes, weekly_cohorts=[])
        self.assertNotIn("raw_pnl_total", board)
        self.assertEqual(board["lanes"]["frozen_baseline"]["put"]["raw_pnl"], 1_000.0)
        self.assertEqual(board["unmatched_lane_counts"]["frozen_baseline_only"], 1)

    def test_seven_cohorts_are_insufficient_and_eight_enable_adjacent_blocks(self):
        seven = [{"week": i, "contrast": i / 100.0} for i in range(7)]
        self.assertEqual(
            tracker.build_scoreboard([], weekly_cohorts=seven)["primary_contrast"]["ci_state"],
            "INSUFFICIENT_COHORTS",
        )
        eight = [{"week": i, "contrast": i / 100.0} for i in range(8)]
        board = tracker.build_scoreboard([], weekly_cohorts=eight)
        self.assertEqual(board["primary_contrast"]["ci_state"], "EXPLORATORY")
        for sample in tracker.moving_block_samples(tuple(range(8)), draws=20, seed=7):
            for left, right in zip(sample[::2], sample[1::2]):
                self.assertEqual(right, (left + 1) % 8)

    def test_weekly_contrast_pairs_only_common_lanes_and_equal_weights_them(self):
        outcomes = [
            {
                "arm": "frozen_baseline",
                "lane": "long_call",
                "decision_session": "2026-08-03",
                "return": 0.10,
            },
            {
                "arm": "context_lane",
                "lane": "long_call",
                "decision_session": "2026-08-04",
                "return": 0.30,
            },
            {
                "arm": "frozen_baseline",
                "lane": "put",
                "decision_session": "2026-08-05",
                "return": 0.90,
            },
            {
                "arm": "frozen_baseline",
                "lane": "cc",
                "decision_session": "2026-08-06",
                "return": 0.10,
            },
            {"arm": "context_lane", "lane": "cc", "decision_session": "2026-08-06", "return": 0.20},
        ]
        cohorts = tracker.weekly_paired_cohorts(outcomes)
        self.assertEqual(len(cohorts), 1)
        self.assertAlmostEqual(cohorts[0]["contrast"], 0.15)
        self.assertEqual(cohorts[0]["paired_lanes"], ["cc", "long_call"])
        self.assertEqual(cohorts[0]["unmatched_lanes"], ["put"])

    def test_unmatched_lane_occurrences_are_disclosed_per_week(self):
        outcomes = [
            {
                "arm": "frozen_baseline",
                "lane": "put",
                "decision_session": "2026-08-03",
                "return": 0.10,
            },
            {
                "arm": "frozen_baseline",
                "lane": "put",
                "decision_session": "2026-08-10",
                "return": 0.20,
            },
            {
                "arm": "context_lane",
                "lane": "put",
                "decision_session": "2026-08-10",
                "return": 0.25,
            },
        ]
        board = tracker.build_scoreboard(outcomes)
        self.assertEqual(len(board["weekly_cohorts"]), 2)
        self.assertIsNone(board["weekly_cohorts"][0]["contrast"])
        self.assertEqual(board["unmatched_lane_counts"]["frozen_baseline_only"], 1)

    def test_header_contains_concentration_and_a2_authority(self):
        board = tracker.build_scoreboard([], weekly_cohorts=[])
        self.assertIn("A2-v1 (ledger seq 19/27) retains interpretive authority", board["header"])
        self.assertIn("effective sample is far smaller than the row count", board["header"])


if __name__ == "__main__":
    unittest.main()
