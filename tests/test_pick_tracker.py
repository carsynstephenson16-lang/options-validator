"""Contract tests for Brief 27's descriptive, registration-gated tracker."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from contextlib import chdir
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
    raw_quote = {
        "symbol": symbol,
        "right": right,
        "strike": strike,
        "expiry": expiry,
        "bid": 1.0,
        "ask": 1.2,
        "open_interest": 500,
    }
    source_row_hash = hashlib.sha256(
        json.dumps(raw_quote, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "candidate_id": candidate_id,
        "symbol": symbol,
        "lane": lane,
        "strike": strike,
        "expiry": expiry,
        "dte": 24,
        "raw_quote": raw_quote,
        "source_row_hash": source_row_hash,
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
    all_items = [*items, *(context_items if context_items is not None else items)]
    payload = {
        "schema": "picks_snapshot/v1",
        "evaluation_date": as_of,
        "data_as_of": as_of,
        "html_sha256": "b" * 64,
        "capture_receipt_path": f"reports/schwab_chains/{as_of}/preclose.json",
        "capture_receipt_sha256": "d" * 64,
        "config_hash": "e" * 64,
        "source_row_hashes": sorted({item["source_row_hash"] for item in all_items}),
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
    payload["source_rows_sha256"] = source_rows_digest(payload)
    bind_render_id(payload)
    return payload


def source_rows_digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            sorted(payload["source_row_hashes"]),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def bind_html(payload: dict, body: bytes = b"bound html") -> bytes:
    digest = source_rows_digest(payload)
    payload["source_rows_sha256"] = digest
    html = body + f"\n<!-- pick-tracker-source-rows-sha256:{digest} -->\n".encode()
    payload["html_sha256"] = hashlib.sha256(html).hexdigest()
    bind_render_id(payload)
    return html


def bind_render_id(payload: dict) -> None:
    snapshot_payload = json.loads(json.dumps(payload))
    snapshot_payload.pop("render_id", None)
    payload["render_id"] = hashlib.sha256(
        json.dumps(
            {"html_sha256": payload["html_sha256"], "snapshot": snapshot_payload},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


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

    def test_snapshot_source_row_mutation_fails_closed(self):
        payload = snapshot("2026-08-25", [candidate("VST:long_call:one")])
        html = bind_html(payload)
        payload["frozen_baseline"]["candidates"][0]["raw_quote"]["bid"] = 1.1
        changed_quote = payload["frozen_baseline"]["candidates"][0]["raw_quote"]
        changed_hash = hashlib.sha256(
            json.dumps(changed_quote, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        payload["frozen_baseline"]["candidates"][0]["source_row_hash"] = changed_hash
        payload["source_row_hashes"] = [changed_hash]

        with self.assertRaisesRegex(tracker.TrackerError, "SNAPSHOT_HTML_SOURCE_MISMATCH"):
            tracker.validate_snapshot(payload, html)

    def test_snapshot_rejects_self_consistent_rows_that_diverge_from_html(self):
        """Probe A: all snapshot hashes are rebuilt but rendered values stay stale."""
        payload = snapshot("2026-08-25", [candidate("VST:long_call:one")])
        html = bind_html(payload)
        payload["frozen_baseline"]["candidates"][0]["raw_quote"]["bid"] = 1.1
        changed_quote = payload["frozen_baseline"]["candidates"][0]["raw_quote"]
        changed_hash = hashlib.sha256(
            json.dumps(changed_quote, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        payload["frozen_baseline"]["candidates"][0]["source_row_hash"] = changed_hash
        payload["source_row_hashes"] = [changed_hash]
        payload["source_rows_sha256"] = source_rows_digest(payload)
        bind_render_id(payload)

        with self.assertRaisesRegex(tracker.TrackerError, "SNAPSHOT_HTML_SOURCE_MISMATCH"):
            tracker.validate_snapshot(payload, html)

    def test_snapshot_rejects_raw_row_that_does_not_match_its_recorded_hash(self):
        """R1: deleting the per-row hash guard must make this test fail."""
        payload = snapshot("2026-08-25", [candidate("VST:long_call:one")])
        html = bind_html(payload)
        payload["frozen_baseline"]["candidates"][0]["raw_quote"]["bid"] = 1.1
        bind_render_id(payload)

        with self.assertRaisesRegex(tracker.TrackerError, "SNAPSHOT_SOURCE_ROW_MISMATCH"):
            tracker.validate_snapshot(payload, html)

    def test_snapshot_render_id_mismatch_fails_closed_independently(self):
        """R2: source rows and HTML remain valid while only render_id drifts."""
        payload = snapshot("2026-08-25", [candidate("VST:long_call:one")])
        html = bind_html(payload)
        payload["render_id"] = "f" * 64

        with self.assertRaisesRegex(tracker.TrackerError, "SNAPSHOT_RENDER_ID_MISMATCH"):
            tracker.validate_snapshot(payload, html)

    def test_snapshot_capture_receipt_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = root / "reports/schwab_chains/2026-08-25/preclose.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_bytes(b"verified receipt")
            payload = snapshot("2026-08-25", [candidate("VST:long_call:one")])
            html = bind_html(payload)
            payload["capture_receipt_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
            bind_render_id(payload)
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
                    reports_root=journal.parent.parent,
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
                reports_root=journal.parent.parent,
                verified_sessions=sessions,
            )
            second = tracker.append_membership(
                snapshot(sessions[1], [candidate("VST:long_call:two")]),
                journal_path=journal,
                reports_root=journal.parent.parent,
                verified_sessions=sessions,
            )
            exited = tracker.append_membership(
                snapshot(sessions[2], []),
                journal_path=journal,
                reports_root=journal.parent.parent,
                verified_sessions=sessions,
            )
            reentered = tracker.append_membership(
                snapshot(sessions[3], [candidate("VST:long_call:three")]),
                journal_path=journal,
                reports_root=journal.parent.parent,
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
                    reports_root=journal.parent.parent,
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
                reports_root=journal.parent.parent,
                verified_sessions=["2026-08-25"],
            )
            second = tracker.append_membership(
                payload,
                journal_path=journal,
                reports_root=journal.parent.parent,
                verified_sessions=["2026-08-25"],
            )
            self.assertEqual(second, first)
            self.assertEqual(len(journal.read_text().splitlines()), 1)
            changed = snapshot("2026-08-25", [candidate("MSFT:long_call:one", symbol="MSFT")])
            with self.assertRaisesRegex(tracker.TrackerConflict, "different content"):
                tracker.append_membership(
                    changed,
                    journal_path=journal,
                    reports_root=journal.parent.parent,
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
                    journal_path=Path(tmp) / "dryrun/scored/events.jsonl",
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

    def test_record_cli_uses_data_session_not_wall_clock_evaluation_date(self):
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = root / "reports/schwab_chains/2026-08-25/preclose.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_bytes(b"verified receipt")
            payload = snapshot("2026-08-25", [candidate("VST:long_call:one")])
            payload["evaluation_date"] = "2026-08-26"
            html = bind_html(payload)
            payload["capture_receipt_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
            bind_render_id(payload)
            snapshot_path = root / tracker.SNAPSHOT_PATH
            snapshot_path.parent.mkdir(parents=True)
            snapshot_path.write_text(json.dumps(payload))
            html_path = root / tracker.HTML_PATH
            html_path.write_bytes(html)

            with (
                chdir(root),
                mock.patch(
                    "options_researcher.schwab_chain_view.verified_sessions",
                    return_value=(["2026-08-25"], []),
                ),
            ):
                tracker.record_cli("2026-08-25")

            journal = root / "reports/pick_tracker/dryrun/events.jsonl"
            records = [json.loads(line) for line in journal.read_text().splitlines()]
            self.assertEqual([record["as_of"] for record in records], ["2026-08-25"])

    def test_unavailable_arms_never_synthesize_exits_or_reentries(self):
        for unavailable_state in ("FAILED", "DISABLED"):
            with self.subTest(state=unavailable_state), tempfile.TemporaryDirectory() as tmp:
                journal = Path(tmp) / "reports/pick_tracker/dryrun/events.jsonl"
                reports_root = journal.parent.parent
                opening = candidate("VST:long_call:one")
                first = tracker.append_membership(
                    snapshot("2026-08-25", [opening]),
                    journal_path=journal,
                    reports_root=reports_root,
                    verified_sessions=["2026-08-25"],
                )
                unavailable = snapshot("2026-08-26", [opening], context_items=[])
                unavailable["context_lane"]["state"] = unavailable_state
                middle = tracker.append_membership(
                    unavailable,
                    journal_path=journal,
                    reports_root=reports_root,
                    verified_sessions=["2026-08-26"],
                )
                resumed = tracker.append_membership(
                    snapshot("2026-08-27", [opening]),
                    journal_path=journal,
                    reports_root=reports_root,
                    verified_sessions=["2026-08-27"],
                )

                prior_slots = first["arms"]["context_lane"]["current_slots"]
                self.assertEqual(middle["arms"]["context_lane"]["current_slots"], prior_slots)
                self.assertEqual(middle["arms"]["context_lane"]["exits"], [])
                self.assertEqual(resumed["arms"]["context_lane"]["entries"], [])

    def test_any_non_ready_arm_state_preserves_slots_without_transitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / "reports/pick_tracker/dryrun/events.jsonl"
            reports_root = journal.parent.parent
            opening = candidate("VST:long_call:one")
            first = tracker.append_membership(
                snapshot("2026-08-25", [opening]),
                journal_path=journal,
                reports_root=reports_root,
                verified_sessions=["2026-08-25"],
            )
            paused = snapshot("2026-08-26", [], context_items=[])
            paused["context_lane"]["state"] = "PAUSED"
            middle = tracker.append_membership(
                paused,
                journal_path=journal,
                reports_root=reports_root,
                verified_sessions=["2026-08-26"],
            )

            self.assertEqual(
                middle["arms"]["context_lane"]["current_slots"],
                first["arms"]["context_lane"]["current_slots"],
            )
            self.assertEqual(middle["arms"]["context_lane"]["entries"], [])
            self.assertEqual(middle["arms"]["context_lane"]["restrikes"], [])
            self.assertEqual(middle["arms"]["context_lane"]["exits"], [])

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
                reports_root=Path(tmp),
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

    @staticmethod
    def _calendar(start: str, end: str) -> list[str]:
        cursor, stop, days = date.fromisoformat(start), date.fromisoformat(end), []
        while cursor <= stop:
            if cursor.weekday() < 5:
                days.append(cursor.isoformat())
            cursor += timedelta(days=1)
        return days

    @staticmethod
    def _record(opening: dict, *, slot: str) -> dict:
        return {
            "schema": "pick_tracker_session/v1",
            "as_of": "2026-08-25",
            "arms": {
                arm: {
                    "state": "READY",
                    "entries": [{"slot": slot, "candidate": opening}],
                    "restrikes": [],
                    "exits": [],
                    "current_slots": {slot: opening},
                }
                for arm in ("frozen_baseline", "context_lane")
            },
        }

    @staticmethod
    def _coverage_inputs() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
        identity = {
            "symbol": "VST",
            "shares": 100,
            "declared_shares": 100,
            "cost_basis": 100.0,
            "acquired": "2025-01-02",
        }
        identity["source_row_hash"] = tracker._identity_hash(identity)
        holdings = pd.DataFrame(
            [{"symbol": "VST", "shares": 100, "cost_basis": 100.0, "acquired": "2025-01-02"}]
        )
        positions = pd.DataFrame(
            columns=(
                "id",
                "structure",
                "symbol",
                "right",
                "strike",
                "expiration",
                "contracts",
                "entry_price",
            )
        )
        return identity, holdings, positions

    def _run_evaluate_cli(
        self,
        *,
        root: Path,
        as_of: str,
        record: dict,
        holdings: pd.DataFrame,
        positions: pd.DataFrame,
        current_new_york_session: str,
    ) -> None:
        from unittest import mock

        journal = root / "reports/pick_tracker/dryrun/events.jsonl"
        journal.parent.mkdir(parents=True, exist_ok=True)
        journal.write_bytes(tracker._canonical_bytes(record) + b"\n")
        sessions = self._calendar("2026-08-25", "2026-08-27")
        with (
            chdir(root),
            mock.patch(
                "options_researcher.schwab_chain_view.verified_sessions",
                return_value=(sessions, []),
            ),
            mock.patch("options_researcher.schwab_chain_view.load_chain", return_value=chain()),
            mock.patch("data.cache_runner.trading_days", side_effect=self._calendar),
            mock.patch("options_researcher.portfolio.load_holdings", return_value=holdings),
            mock.patch("options_researcher.portfolio.load_positions", return_value=positions),
            mock.patch.object(
                tracker,
                "_current_new_york_session",
                return_value=current_new_york_session,
                create=True,
            ),
        ):
            tracker.evaluate_cli(as_of)

    def test_evaluate_cli_noncovered_lane_does_not_invoke_real_coverage_validator(self):
        opening = candidate("VST:long_call:cli")
        record = self._record(opening, slot="VST:long_call")
        _identity, holdings, positions = self._coverage_inputs()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._run_evaluate_cli(
                root=root,
                as_of="2026-08-27",
                record=record,
                holdings=holdings,
                positions=positions,
                current_new_york_session="2026-08-27",
            )
            outcomes = json.loads(
                (root / "reports/pick_tracker/dryrun/2026-08-27/outcomes.json").read_text()
            )["outcomes"]
            self.assertEqual({row["status"] for row in outcomes}, {"OPEN"})

    def test_backdated_fresh_tracker_observation_uses_machine_session(self):
        identity, holdings, positions = self._coverage_inputs()
        opening = candidate(
            "VST:cc:fresh",
            lane="cc",
            side="sell",
            risk_kind="FROZEN_100_SHARE_COST_BASIS",
            risk_value=10_000.0,
            coverage=identity,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._run_evaluate_cli(
                root=root,
                as_of="2026-08-26",
                record=self._record(opening, slot="VST:cc"),
                holdings=holdings,
                positions=positions,
                current_new_york_session="2026-08-28",
            )
            observations = json.loads(
                (
                    root / "reports/pick_tracker/dryrun/2026-08-26/coverage_observations.json"
                ).read_text()
            )["observations"]
            self.assertEqual({row["observed_session"] for row in observations}, {"2026-08-28"})
            self.assertNotIn("2026-08-26", {row["observed_session"] for row in observations})

    def test_backdated_gap_observation_uses_machine_session(self):
        identity, holdings, positions = self._coverage_inputs()
        opening = candidate(
            "VST:cc:gap",
            lane="cc",
            side="sell",
            risk_kind="FROZEN_100_SHARE_COST_BASIS",
            risk_value=10_000.0,
            coverage=identity,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            newest = root / "reports/pick_tracker/dryrun/2026-08-25/scoreboard.json"
            newest.parent.mkdir(parents=True)
            newest.write_text('{"schema":"pick_tracker_scoreboard/v1"}\n')
            self._run_evaluate_cli(
                root=root,
                as_of="2026-08-26",
                record=self._record(opening, slot="VST:cc"),
                holdings=holdings,
                positions=positions,
                current_new_york_session="2026-08-28",
            )
            self.assertEqual(newest.read_text(), '{"schema":"pick_tracker_scoreboard/v1"}\n')
            observations = json.loads(
                (
                    root / "reports/pick_tracker/dryrun/2026-08-26/coverage_observations.json"
                ).read_text()
            )["observations"]
            self.assertEqual({row["observed_session"] for row in observations}, {"2026-08-28"})

    def test_scheduled_prior_completed_session_publishes_machine_dated_observation(self):
        identity, holdings, positions = self._coverage_inputs()
        opening = candidate(
            "VST:cc:today",
            lane="cc",
            side="sell",
            risk_kind="FROZEN_100_SHARE_COST_BASIS",
            risk_value=10_000.0,
            coverage=identity,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._run_evaluate_cli(
                root=root,
                as_of="2026-08-26",
                record=self._record(opening, slot="VST:cc"),
                holdings=holdings,
                positions=positions,
                current_new_york_session="2026-08-27",
            )
            outcomes = json.loads(
                (root / "reports/pick_tracker/dryrun/2026-08-26/outcomes.json").read_text()
            )["outcomes"]
            self.assertEqual({row["status"] for row in outcomes}, {"OPEN"})
            observations = json.loads(
                (
                    root / "reports/pick_tracker/dryrun/2026-08-26/coverage_observations.json"
                ).read_text()
            )["observations"]
            self.assertEqual(len(observations), 1)
            self.assertEqual(observations[0]["observed_session"], "2026-08-27")
            self.assertTrue(observations[0]["matches"])

    def test_writer_refuses_non_machine_coverage_observation_date(self):
        from unittest import mock

        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(tracker, "_current_new_york_session", return_value="2026-08-27"),
        ):
            destination = Path(tmp) / "reports/pick_tracker/dryrun/2026-08-26"
            with self.assertRaisesRegex(
                tracker.TrackerError,
                "LIVE_HOLDINGS_OBSERVATION_SESSION_MISMATCH",
            ):
                tracker._write_evaluation_reports(
                    destination,
                    as_of="2026-08-26",
                    outcomes=[],
                    board=tracker.build_scoreboard([]),
                    coverage_observations=[
                        {
                            "coverage_key": "a" * 64,
                            "observed_session": "2026-08-26",
                            "matches": True,
                        }
                    ],
                    reports_root=Path(tmp) / "reports/pick_tracker",
                )
            self.assertFalse(destination.exists())

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

    def test_missing_symbol_file_cancels_contract_absent(self):
        calls: list[tuple[str, str]] = []

        def missing(symbol: str, session: str) -> pd.DataFrame:
            calls.append((symbol, session))
            raise FileNotFoundError(f"no captured chain for {symbol} {session}")

        result = tracker.resolve_fill(
            candidate("VST:long_call:one"),
            decision_session="2026-08-25",
            verified_sessions=["2026-08-26", "2026-08-27"],
            chain_loader=missing,
            trading_days_fn=self.sessions,
        )

        self.assertEqual(result["status"], "CANCELLED_CONTRACT_ABSENT")
        self.assertEqual(result["fill_session"], "2026-08-26")
        self.assertEqual(calls, [("VST", "2026-08-26")])

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

    def test_recorded_cc_history_is_byte_stable_after_portfolio_mutation(self):
        identity = {
            "symbol": "VST",
            "shares": 100,
            "declared_shares": 100,
            "cost_basis": 100.0,
            "acquired": "2025-01-02",
        }
        identity["source_row_hash"] = tracker._identity_hash(identity)
        opening = candidate(
            "VST:cc:immutable",
            lane="cc",
            side="sell",
            risk_kind="FROZEN_100_SHARE_COST_BASIS",
            risk_value=10_000.0,
            coverage=identity,
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
        holdings = pd.DataFrame(
            [{"symbol": "VST", "shares": 100, "cost_basis": 100.0, "acquired": "2025-01-02"}]
        )
        positions = pd.DataFrame(
            columns=(
                "id",
                "structure",
                "symbol",
                "right",
                "strike",
                "expiration",
                "contracts",
                "entry_price",
            )
        )

        def calendar(start: str, end: str) -> list[str]:
            cursor, stop, days = date.fromisoformat(start), date.fromisoformat(end), []
            while cursor <= stop:
                if cursor.weekday() < 5:
                    days.append(cursor.isoformat())
                cursor += timedelta(days=1)
            return days

        def evaluate() -> list[dict[str, object]]:
            return tracker.evaluate_records(
                [record],
                as_of="2026-08-27",
                verified_sessions=calendar("2026-08-25", "2026-08-27"),
                chain_loader=lambda _symbol, _session: chain(),
                trading_days_fn=calendar,
                close_loader=lambda _symbol, _session: 100.0,
                coverage_validator=lambda position, _session: tracker.coverage_identity_matches(
                    position, holdings=holdings, positions=positions
                ),
            )

        with tempfile.TemporaryDirectory() as tmp:
            reports_root = Path(tmp) / "reports/pick_tracker"
            destination = reports_root / "dryrun/2026-08-27"
            first_outcomes = evaluate()
            tracker._write_evaluation_reports(
                destination,
                as_of="2026-08-27",
                outcomes=first_outcomes,
                board=tracker.build_scoreboard(first_outcomes),
                reports_root=reports_root,
            )
            before = {path.name: path.read_bytes() for path in destination.iterdir()}

            holdings.loc[0, "shares"] = 0
            changed_outcomes = evaluate()
            with self.assertRaisesRegex(tracker.TrackerConflict, "IMMUTABLE_HISTORY_CONFLICT"):
                tracker._write_evaluation_reports(
                    destination,
                    as_of="2026-08-27",
                    outcomes=changed_outcomes,
                    board=tracker.build_scoreboard(changed_outcomes),
                    reports_root=reports_root,
                )

            after = {path.name: path.read_bytes() for path in destination.iterdir()}
            self.assertEqual(after, before)

    def test_explicit_supersede_preserves_canonical_artifacts_and_records_reason(self):
        first_outcomes = [
            {
                "arm": "frozen_baseline",
                "lane": "cc",
                "decision_session": "2026-08-25",
                "status": "OPEN",
            }
        ]
        replacement_outcomes = [
            {
                "arm": "frozen_baseline",
                "lane": "cc",
                "decision_session": "2026-08-25",
                "status": "SETTLED",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "reports/pick_tracker"
            destination = root / "dryrun/2026-08-27"
            tracker._write_evaluation_reports(
                destination,
                as_of="2026-08-27",
                outcomes=first_outcomes,
                board=tracker.build_scoreboard(first_outcomes),
                reports_root=root,
            )
            canonical_before = {
                path.name: path.read_bytes() for path in destination.iterdir() if path.is_file()
            }
            with self.assertRaisesRegex(tracker.TrackerConflict, "IMMUTABLE_HISTORY_CONFLICT"):
                tracker._write_evaluation_reports(
                    destination,
                    as_of="2026-08-27",
                    outcomes=replacement_outcomes,
                    board=tracker.build_scoreboard(replacement_outcomes),
                    reports_root=root,
                )

            receipt_path = tracker._write_evaluation_reports(
                destination,
                as_of="2026-08-27",
                outcomes=replacement_outcomes,
                board=tracker.build_scoreboard(replacement_outcomes),
                reports_root=root,
                supersede_reason="late verified close became available",
            )

            canonical_after = {
                path.name: path.read_bytes() for path in destination.iterdir() if path.is_file()
            }
            self.assertEqual(canonical_after, canonical_before)
            self.assertIsInstance(receipt_path, Path)
            receipt = json.loads(receipt_path.read_text())
            self.assertEqual(receipt["schema"], "pick_tracker_supersede/v1")
            self.assertEqual(receipt["as_of"], "2026-08-27")
            self.assertEqual(receipt["reason"], "late verified close became available")
            replacement = destination / receipt["replacement_path"] / "outcomes.json"
            self.assertEqual(
                tracker._active_evaluation_artifact(destination, "outcomes.json"),
                replacement,
            )
            self.assertEqual(json.loads(replacement.read_text())["outcomes"], replacement_outcomes)
            self.assertEqual(
                receipt["superseded_sha256"]["outcomes.json"],
                hashlib.sha256(canonical_before["outcomes.json"]).hexdigest(),
            )

    def test_immutable_write_wraps_stale_temp_file_as_tracker_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "artifact.json"
            stale = path.with_name(f".{path.name}.{os.getpid()}.tmp")
            stale.write_bytes(b"stale")
            with self.assertRaisesRegex(tracker.TrackerConflict, "TRACKER_TEMP_CONFLICT"):
                tracker._immutable_write(path, b"new")

    def test_evaluation_reports_enforce_dryrun_write_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "reports/pick_tracker"
            with self.assertRaisesRegex(tracker.RegistrationRequired, "dryrun"):
                tracker._write_evaluation_reports(
                    root / "outside/2026-08-27",
                    as_of="2026-08-27",
                    outcomes=[],
                    board=tracker.build_scoreboard([]),
                    reports_root=root,
                )

    def test_later_coverage_change_is_observed_prospectively_without_rewriting_history(self):
        """Probe B: current holdings must not be back-applied to prior sessions."""
        from unittest import mock

        identity = {
            "symbol": "VST",
            "shares": 100,
            "declared_shares": 100,
            "cost_basis": 100.0,
            "acquired": "2025-01-02",
        }
        identity["source_row_hash"] = tracker._identity_hash(identity)
        opening = candidate(
            "VST:cc:causal",
            lane="cc",
            side="sell",
            risk_kind="FROZEN_100_SHARE_COST_BASIS",
            risk_value=10_000.0,
            coverage=identity,
        )
        record = {
            "schema": "pick_tracker_session/v1",
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
        holdings = pd.DataFrame(
            [{"symbol": "VST", "shares": 100, "cost_basis": 100.0, "acquired": "2025-01-02"}]
        )
        positions = pd.DataFrame(
            columns=(
                "id",
                "structure",
                "symbol",
                "right",
                "strike",
                "expiration",
                "contracts",
                "entry_price",
            )
        )

        def calendar(start: str, end: str) -> list[str]:
            cursor, stop, days = date.fromisoformat(start), date.fromisoformat(end), []
            while cursor <= stop:
                if cursor.weekday() < 5:
                    days.append(cursor.isoformat())
                cursor += timedelta(days=1)
            return days

        with tempfile.TemporaryDirectory() as tmp, chdir(tmp):
            journal = Path("reports/pick_tracker/dryrun/events.jsonl")
            journal.parent.mkdir(parents=True)
            journal.write_bytes(tracker._canonical_bytes(record) + b"\n")
            sessions = calendar("2026-08-25", "2026-08-27")
            with (
                mock.patch(
                    "options_researcher.schwab_chain_view.verified_sessions",
                    return_value=(sessions, []),
                ),
                mock.patch("options_researcher.schwab_chain_view.load_chain", return_value=chain()),
                mock.patch("data.cache_runner.trading_days", side_effect=calendar),
                mock.patch(
                    "options_researcher.portfolio.load_holdings",
                    side_effect=lambda: holdings.copy(),
                ),
                mock.patch("options_researcher.portfolio.load_positions", return_value=positions),
                mock.patch.object(
                    tracker,
                    "_current_new_york_session",
                    side_effect=(
                        "2026-08-26",
                        "2026-08-26",
                        "2026-08-27",
                        "2026-08-27",
                    ),
                ),
            ):
                tracker.evaluate_cli("2026-08-26")
                day1_path = Path("reports/pick_tracker/dryrun/2026-08-26/outcomes.json")
                day1_bytes = day1_path.read_bytes()
                day1 = json.loads(day1_bytes)["outcomes"][0]
                self.assertEqual(day1["status"], "OPEN")

                holdings.loc[0, "shares"] = 0
                tracker.evaluate_cli("2026-08-27")

            day2 = json.loads(
                Path("reports/pick_tracker/dryrun/2026-08-27/outcomes.json").read_text()
            )["outcomes"][0]
            self.assertEqual(day1_path.read_bytes(), day1_bytes)
            self.assertEqual(day2["status"], "CANCELLED_COVERAGE_CHANGED")
            self.assertIn("daily_marks", day2)
            self.assertEqual(day2["daily_marks"][0], day1["daily_marks"][0])
            self.assertEqual(
                day2["status_events"],
                [
                    {"session": "2026-08-26", "status": "OPEN"},
                    {"session": "2026-08-27", "status": "CANCELLED_COVERAGE_CHANGED"},
                ],
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

    def test_evaluator_marks_daily_and_drawdown_starts_at_zero_return_entry(self):
        opening = candidate("VST:long_call:daily")
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
        sessions = ["2026-08-25", "2026-08-26", "2026-08-27"]

        def calendar(start: str, end: str) -> list[str]:
            cursor, stop, days = date.fromisoformat(start), date.fromisoformat(end), []
            while cursor <= stop:
                if cursor.weekday() < 5:
                    days.append(cursor.isoformat())
                cursor += timedelta(days=1)
            return days

        outcomes = tracker.evaluate_records(
            [record],
            as_of="2026-08-27",
            verified_sessions=sessions,
            chain_loader=lambda _symbol, session: (
                chain(bid=2.0, ask=2.2) if session == "2026-08-26" else chain(bid=1.0, ask=1.2)
            ),
            trading_days_fn=calendar,
            close_loader=lambda _symbol, _session: 100.0,
        )

        first = outcomes[0]
        self.assertEqual(
            [(mark["mark_session"], mark["status"]) for mark in first["daily_marks"]],
            [("2026-08-26", "ENTRY"), ("2026-08-27", "MARKED")],
        )
        self.assertEqual(first["daily_marks"][0]["return_on_risk_basis"], 0.0)
        self.assertLess(first["max_drawdown"], 0.0)

    def test_daily_marks_stop_at_the_recorded_settlement_checkpoint(self):
        opening = candidate("VST:long_call:horizon", expiry="2026-10-30")
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
            as_of="2026-10-01",
            verified_sessions=calendar("2026-08-25", "2026-10-01"),
            chain_loader=lambda _symbol, _session: chain(expiry="2026-10-30"),
            trading_days_fn=calendar,
            close_loader=lambda _symbol, _session: 100.0,
        )

        first = outcomes[0]
        self.assertEqual(first["status"], "SETTLED")
        self.assertEqual(first["marks"][-1]["termination"], "longest_applicable_mark")
        self.assertEqual(
            first["daily_marks"][-1]["mark_session"],
            first["marks"][-1]["mark_session"],
        )

    def test_evaluator_loads_each_symbol_session_chain_at_most_once(self):
        """N2 scale probe: duplicate arms must share the per-run chain cache."""
        opening = candidate(
            "VST:leaps:scale",
            lane="leaps",
            expiry="2027-12-17",
        )
        record = {
            "as_of": "2026-08-25",
            "arms": {
                arm: {
                    "state": "READY",
                    "entries": [{"slot": "VST:leaps", "candidate": opening}],
                    "restrikes": [],
                    "exits": [],
                    "current_slots": {"VST:leaps": opening},
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

        calls: list[tuple[str, str]] = []

        def load(symbol: str, session: str) -> pd.DataFrame:
            calls.append((symbol, session))
            return chain(expiry="2027-12-17")

        sessions = calendar("2026-08-25", "2027-03-31")
        tracker.evaluate_records(
            [record],
            as_of="2027-03-31",
            verified_sessions=sessions,
            chain_loader=load,
            trading_days_fn=calendar,
            close_loader=lambda _symbol, _session: 100.0,
        )

        self.assertEqual(len(calls), len(set(calls)), calls[:3])

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
        self.assertEqual(outcomes[0]["unreachable_marks"], 1)


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

    def test_seven_cohorts_are_insufficient_and_eight_enable_non_circular_blocks(self):
        seven = [{"week": i, "contrast": i / 100.0} for i in range(7)]
        self.assertEqual(
            tracker.build_scoreboard([], weekly_cohorts=seven)["primary_contrast"]["ci_state"],
            "INSUFFICIENT_COHORTS",
        )
        eight = [{"week": i, "contrast": i / 100.0} for i in range(8)]
        board = tracker.build_scoreboard([], weekly_cohorts=eight)
        self.assertEqual(board["primary_contrast"]["ci_state"], "EXPLORATORY")
        for sample in tracker.moving_block_samples(tuple(range(8)), draws=1, seed=9):
            for left, right in zip(sample[::2], sample[1::2]):
                self.assertEqual(right, left + 1)

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

    def test_markdown_carries_wp_d_cancellations_cohorts_and_scoreboard_context(self):
        outcomes = [
            {
                "arm": "frozen_baseline",
                "lane": "put",
                "decision_session": "2026-08-03",
                "status": "CANCELLED_NO_FILL_DATA",
            }
        ]
        cohorts = [
            {
                "week": "2026-08-03",
                "contrast": 0.05,
                "paired_lanes": ["long_call"],
                "unmatched_lanes": ["put"],
                "frozen_baseline_only": ["put"],
                "context_lane_only": [],
            }
        ]
        markdown = tracker._scoreboard_markdown(
            tracker.build_scoreboard(outcomes, weekly_cohorts=cohorts)
        )

        self.assertIn("Cancellations by kind", markdown)
        self.assertIn("CANCELLED_NO_FILL_DATA: 1", markdown)
        self.assertIn("## Arm availability", markdown)
        self.assertIn("## Unmatched-lane counts", markdown)
        self.assertIn("## Weekly non-overlapping cohorts", markdown)
        self.assertIn("2026-08-03", markdown)
        self.assertIn("long_call", markdown)
        self.assertIn("frozen_baseline_only=put", markdown)


if __name__ == "__main__":
    unittest.main()
