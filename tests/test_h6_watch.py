import csv
import dataclasses
import math
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import pandas as pd

import config
from options_researcher.h6_watch import (
    BOOK_FIELDS,
    BookPosition,
    build_receipt,
    build_snapshot,
    choose_contract,
    evaluate_entry,
    evaluate_exit,
    load_book,
    score_book,
    timing_state,
    validate_book,
    verify_book_receipts,
    verify_receipt,
    write_receipt,
)

AS_OF = date(2026, 7, 13)
KNOWN = datetime.fromisoformat("2026-07-13T22:00:00+00:00")


def assertion(
    symbol: str,
    report: str,
    *,
    status: str = "confirmed",
    timing: str = "amc",
    event: str = "FY26Q2",
    known: str = "2026-07-01T12:00:00+00:00",
) -> dict:
    stamp = datetime.fromisoformat(known)
    occurred = date.fromisoformat(report) if status == "occurred" else None
    expected = None if occurred else date.fromisoformat(report)
    return {
        "record_id": f"{symbol}-{event}-{status}",
        "symbol": symbol,
        "event_id": f"{symbol}-{event}",
        "fiscal_period": event,
        "record_type": "assertion",
        "event_class": "actual_quarterly_earnings",
        "status": status,
        "expected_date": expected,
        "occurred_date": occurred,
        "session_timing": timing,
        "source_type": "company_pr",
        "source_url": "https://example.test/ir",
        "known_as_of_utc": stamp,
        "checked_at_utc": stamp,
        "supersedes": "",
        "promoted_from": "raw-1",
        "notes": "",
    }


def chain() -> pd.DataFrame:
    rows = [
        # Weekly is closer but H6 requires a standard monthly.
        ("2026-08-28", 100.0, "C", 0.49, 7.00, 7.20, 500),
        # Earliest standard monthly inside 45-90 DTE is 2026-09-18.
        ("2026-09-18", 100.0, "C", 0.40, 6.00, 6.10, 500),
        ("2026-09-18", 105.0, "C", 0.50, 9.80, 9.90, 500),
        ("2026-09-18", 110.0, "C", 0.51, 5.00, 5.10, 500),
        ("2026-09-18", 115.0, "C", 0.45, 10.00, 10.01, 500),
        ("2026-09-18", 120.0, "C", 0.48, 5.00, 5.50, 10),
        # Later monthly must not win even with a higher in-band delta.
        ("2026-10-16", 100.0, "C", 0.50, 8.00, 8.10, 500),
        ("2026-09-18", 100.0, "P", -0.50, 9.00, 9.10, 500),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "expiration",
            "strike",
            "right",
            "delta",
            "bid",
            "ask",
            "open_interest",
        ],
    )


def position(
    *,
    pid: str = "h6-1",
    symbol: str = "NVDA",
    entry_date: date = date(2026, 7, 1),
    entry_cost: float = 900.65,
    expiration: date = date(2026, 9, 18),
    entry_receipt_hash: str = "a" * 64,
    exit_date: date | None = None,
    exit_proceeds: float | None = None,
    exit_reason: str | None = None,
    exit_receipt_hash: str | None = None,
) -> BookPosition:
    if exit_date is not None and exit_receipt_hash is None:
        exit_receipt_hash = "b" * 64
    return BookPosition(
        id=pid,
        symbol=symbol,
        strike=105.0,
        expiration=expiration,
        contracts=1,
        entry_date=entry_date,
        entry_cost=entry_cost,
        entry_receipt_hash=entry_receipt_hash,
        exit_date=exit_date,
        exit_proceeds=exit_proceeds,
        exit_reason=exit_reason,
        exit_receipt_hash=exit_receipt_hash,
    )


class ContractSelectionTests(unittest.TestCase):
    def test_nearest_monthly_and_highest_eligible_delta(self):
        picked = choose_contract(chain(), AS_OF)
        self.assertIsNotNone(picked)
        self.assertEqual(picked.expiration, date(2026, 9, 18))
        self.assertEqual(picked.strike, 105.0)
        self.assertEqual(picked.delta, 0.50)
        # Canonical adverse buy: ceil(9.90 * 1.01) + one entry commission.
        self.assertEqual(picked.entry_cost, 1000.65)

    def test_raw_ask_and_liquidity_gates_are_hard(self):
        frame = chain()
        frame.loc[frame["strike"] == 105.0, "ask"] = 10.01
        picked = choose_contract(frame, AS_OF)
        self.assertEqual(picked.strike, 100.0)
        self.assertLessEqual(picked.raw_ask * 100.0, config.H6_MAX_ASK_DOLLARS)

    def test_malformed_chain_fails_loud(self):
        with self.assertRaises(ValueError):
            choose_contract(chain().drop(columns=["delta"]), AS_OF)


class EarningsTimingTests(unittest.TestCase):
    def test_unknown_schedule_fails_closed(self):
        state = timing_state("NVDA", AS_OF, [], known_as_of=KNOWN)
        self.assertEqual(state.state, "UNKNOWN")

    def test_pre_report_window_is_banned(self):
        rows = [assertion("NVDA", "2026-07-17")]
        state = timing_state("NVDA", AS_OF, rows, known_as_of=KNOWN)
        self.assertEqual(state.state, "PRE_REPORT_BANNED")

    def test_bmo_report_day_is_first_post_report_session(self):
        rows = [assertion("NVDA", "2026-07-13", status="occurred", timing="bmo")]
        state = timing_state("NVDA", AS_OF, rows, known_as_of=KNOWN)
        self.assertEqual(state.state, "POST_REPORT")

    def test_amc_report_day_starts_post_window_next_session(self):
        rows = [assertion("NVDA", "2026-07-10", status="occurred", timing="amc")]
        state = timing_state("NVDA", AS_OF, rows, known_as_of=KNOWN)
        self.assertEqual(state.state, "POST_REPORT")
        self.assertEqual(state.post_sessions[0], date(2026, 7, 13))


class EntryDecisionTests(unittest.TestCase):
    def future(self):
        return [assertion("NVDA", "2026-08-26", status="estimated")]

    def test_outside_post_window_requires_finite_low_ivr(self):
        # Boundary tracks config.H6_IVR_MAX (0.70 since H6_TRIAL7_AMENDMENT_1,
        # 2026-07-14; was 0.50) instead of a hardcoded literal.
        good = evaluate_entry(
            "NVDA",
            AS_OF,
            chain(),
            iv_rank=config.H6_IVR_MAX,
            assertions=self.future(),
            known_as_of=KNOWN,
            book=[],
        )
        self.assertEqual(good.status, "ELIGIBLE")
        high = evaluate_entry(
            "NVDA",
            AS_OF,
            chain(),
            iv_rank=config.H6_IVR_MAX + 0.0001,
            assertions=self.future(),
            known_as_of=KNOWN,
            book=[],
        )
        self.assertEqual(high.status, "BLOCKED")
        missing = evaluate_entry(
            "NVDA",
            AS_OF,
            chain(),
            iv_rank=math.nan,
            assertions=self.future(),
            known_as_of=KNOWN,
            book=[],
        )
        self.assertEqual(missing.status, "BLOCKED")

    def test_post_report_window_bypasses_only_ivr_gate(self):
        occurred = [
            assertion("NVDA", "2026-07-10", status="occurred", timing="amc")
        ]
        decision = evaluate_entry(
            "NVDA",
            AS_OF,
            chain(),
            iv_rank=math.nan,
            assertions=occurred,
            known_as_of=KNOWN,
            book=[],
        )
        self.assertEqual(decision.status, "ELIGIBLE")

    def test_monthly_gross_risk_and_open_book_caps(self):
        existing = [position(entry_cost=1000.0, symbol="PLTR")]
        risk = evaluate_entry(
            "NVDA",
            AS_OF,
            chain(),
            iv_rank=0.2,
            assertions=self.future(),
            known_as_of=KNOWN,
            book=existing,
        )
        self.assertEqual(risk.status, "BLOCKED")
        self.assertIn("monthly", " ".join(risk.reasons).lower())

        duplicate = evaluate_entry(
            "NVDA",
            AS_OF,
            chain(),
            iv_rank=0.2,
            assertions=self.future(),
            known_as_of=KNOWN,
            book=[position(symbol="NVDA")],
        )
        self.assertEqual(duplicate.status, "BLOCKED")
        self.assertIn("already open", " ".join(duplicate.reasons).lower())

    def test_same_session_close_does_not_free_capacity_or_name(self):
        same_day_close = position(
            symbol="PLTR",
            entry_date=date(2026, 5, 1),
            entry_cost=500.0,
            expiration=date(2026, 7, 17),
            exit_date=AS_OF,
            exit_proceeds=500.0,
            exit_reason="time_21_dte",
        )
        other_open = [
            position(
                pid=f"open-{symbol}",
                symbol=symbol,
                entry_date=date(2026, 6, 2),
                entry_cost=500.0,
                expiration=date(2026, 8, 21),
            )
            for symbol in ("NVDA", "AMZN")
        ]
        decision = evaluate_entry(
            "PLTR",
            AS_OF,
            chain(),
            iv_rank=0.2,
            assertions=[assertion("PLTR", "2026-08-26", status="estimated")],
            known_as_of=KNOWN,
            book=[same_day_close, *other_open],
        )
        reasons = " ".join(decision.reasons).lower()
        self.assertEqual(decision.status, "BLOCKED")
        self.assertIn("already open", reasons)
        self.assertIn("reaches cap", reasons)


class ExitAndBookTests(unittest.TestCase):
    def test_take_profit_and_time_exit_use_conservative_proceeds(self):
        frame = pd.DataFrame(
            [("2026-09-18", 105.0, "C", 0.4, 20.00, 20.10, 500)],
            columns=[
                "expiration",
                "strike",
                "right",
                "delta",
                "bid",
                "ask",
                "open_interest",
            ],
        )
        tp = evaluate_exit(position(entry_cost=900.0), AS_OF, frame)
        self.assertEqual(tp.action, "CLOSE")
        self.assertEqual(tp.reason, "take_profit")
        self.assertEqual(tp.proceeds, 1979.35)

        timed = evaluate_exit(
            position(expiration=date(2026, 8, 3)), AS_OF, frame.assign(
                expiration="2026-08-03", bid=5.0, ask=5.1
            )
        )
        self.assertEqual(timed.action, "CLOSE")
        self.assertEqual(timed.reason, "time_21_dte")

    def test_book_loader_rejects_partial_closes(self):
        header = [
            "id",
            "symbol",
            "strike",
            "expiration",
            "contracts",
            "entry_date",
            "entry_cost",
            "entry_receipt_hash",
            "exit_date",
            "exit_proceeds",
            "exit_reason",
            "exit_receipt_hash",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "book.csv"
            with path.open("w", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(header)
                writer.writerow(
                    [
                        "h6-1",
                        "NVDA",
                        "105",
                        "2026-09-18",
                        "1",
                        "2026-07-13",
                        "900.65",
                        "a" * 64,
                        "2026-07-20",
                        "",
                        "take_profit",
                        "b" * 64,
                    ]
                )
            with self.assertRaises(ValueError):
                load_book(path)

    def test_book_rejects_non_session_and_wrong_entry_tenor(self):
        with self.assertRaisesRegex(ValueError, "XNYS session"):
            validate_book([position(entry_date=date(2026, 7, 4))])
        with self.assertRaisesRegex(ValueError, "entry DTE"):
            validate_book(
                [
                    position(
                        entry_date=date(2026, 7, 13),
                        expiration=date(2026, 8, 21),
                    )
                ]
            )

    def test_book_rejects_historical_same_name_overlap(self):
        first = position(
            pid="first",
            entry_date=date(2026, 7, 13),
            expiration=date(2026, 9, 18),
            exit_date=date(2026, 8, 28),
            exit_proceeds=500.0,
            exit_reason="time_21_dte",
        )
        second = position(
            pid="second",
            entry_date=date(2026, 7, 20),
            expiration=date(2026, 9, 18),
        )
        with self.assertRaisesRegex(ValueError, "overlapping.*NVDA"):
            validate_book([first, second])

    def test_book_rejects_historical_four_position_overlap(self):
        rows = [
            position(
                pid=f"p{i}",
                symbol=symbol,
                entry_date=date(2026, 7, 13),
                entry_cost=400.0,
                expiration=date(2026, 9, 18),
            )
            for i, symbol in enumerate(("NVDA", "PLTR", "AMZN", "NVDA"))
        ]
        with self.assertRaisesRegex(ValueError, "concurrent H6 positions 4"):
            validate_book(rows)

    def test_book_rejects_unearned_take_profit_and_early_time_exit(self):
        false_tp = position(
            entry_date=date(2026, 7, 13),
            expiration=date(2026, 9, 18),
            exit_date=date(2026, 7, 20),
            exit_proceeds=1000.0,
            exit_reason="take_profit",
        )
        with self.assertRaisesRegex(ValueError, "take_profit"):
            validate_book([false_tp])
        early_time = position(
            entry_date=date(2026, 7, 13),
            expiration=date(2026, 9, 18),
            exit_date=date(2026, 7, 20),
            exit_proceeds=500.0,
            exit_reason="time_21_dte",
        )
        with self.assertRaisesRegex(ValueError, "time_21_dte"):
            validate_book([early_time])


class ScoreTests(unittest.TestCase):
    def closed(self, index: int, pnl: float) -> BookPosition:
        expirations = [
            date(2026, 2, 20),
            date(2026, 3, 20),
            date(2026, 4, 17),
            date(2026, 5, 15),
            date(2026, 6, 19),
            date(2026, 7, 17),
            date(2026, 8, 21),
            date(2026, 9, 18),
        ]
        expiration = expirations[index]
        entry_date = date.fromisoformat(
            pd.bdate_range(end=expiration - pd.Timedelta(days=45), periods=1)[0]
            .date()
            .isoformat()
        )
        exit_date = date.fromisoformat(
            pd.bdate_range(end=expiration - pd.Timedelta(days=21), periods=1)[0]
            .date()
            .isoformat()
        )
        return position(
            pid=f"h6-{index}",
            symbol=config.H6_NAMES[index % len(config.H6_NAMES)],
            entry_date=entry_date,
            entry_cost=500.0,
            expiration=expiration,
            exit_date=exit_date,
            exit_proceeds=500.0 + pnl,
            exit_reason="time_21_dte",
        )

    def test_registered_ci_bounds_classify_after_eight(self):
        book = [self.closed(i, 100.0) for i in range(8)]
        with mock.patch(
            "options_researcher.h6_watch.metrics.dependence_aware_expectancy_ci",
            return_value=(-5.0, -1.0),
        ):
            self.assertEqual(score_book(book).verdict, "REJECT")
        with mock.patch(
            "options_researcher.h6_watch.metrics.dependence_aware_expectancy_ci",
            return_value=(1.0, 5.0),
        ):
            self.assertEqual(score_book(book).verdict, "EXTEND")
        with mock.patch(
            "options_researcher.h6_watch.metrics.dependence_aware_expectancy_ci",
            return_value=(-1.0, 5.0),
        ):
            self.assertEqual(score_book(book).verdict, "CONTINUE")

    def test_three_consecutive_full_cap_loss_months_hard_kill(self):
        rows = []
        cycles = (
            (date(2026, 1, 2), date(2026, 1, 30), date(2026, 2, 20)),
            (date(2026, 2, 2), date(2026, 2, 27), date(2026, 3, 20)),
            (date(2026, 3, 2), date(2026, 3, 27), date(2026, 4, 17)),
        )
        for month, (entry_date, exit_date, expiration) in enumerate(cycles, start=1):
            for slot in (0, 1):
                rows.append(
                    position(
                        pid=f"loss-{month}-{slot}",
                        symbol=config.H6_NAMES[slot],
                        entry_date=entry_date,
                        entry_cost=1000.0,
                        expiration=expiration,
                        exit_date=exit_date,
                        exit_proceeds=0.0,
                        exit_reason="time_21_dte",
                    )
                )
        score = score_book(rows)
        self.assertEqual(score.verdict, "REJECT")
        self.assertTrue(score.hard_kill)

    def test_hard_kill_uses_registered_configured_month_count(self):
        rows = []
        cycles = (
            (date(2026, 1, 2), date(2026, 1, 30), date(2026, 2, 20)),
            (date(2026, 2, 2), date(2026, 2, 27), date(2026, 3, 20)),
        )
        for month, (entry_date, exit_date, expiration) in enumerate(cycles, start=1):
            for slot in (0, 1):
                rows.append(
                    position(
                        pid=f"configured-loss-{month}-{slot}",
                        symbol=config.H6_NAMES[slot],
                        entry_date=entry_date,
                        entry_cost=1000.0,
                        expiration=expiration,
                        exit_date=exit_date,
                        exit_proceeds=0.0,
                        exit_reason="time_21_dte",
                    )
                )
        with mock.patch.object(config, "H6_HARD_KILL_FULL_LOSS_MONTHS", 2):
            self.assertTrue(score_book(rows).hard_kill)


class ReceiptTests(unittest.TestCase):
    def test_beyond_edge_does_not_substitute_prior_or_future_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chain_dir = root / "chains"
            chain_dir.mkdir()
            chain().to_parquet(chain_dir / "NVDA_2026-07-10.parquet")
            chain().to_parquet(chain_dir / "NVDA_2026-07-14.parquet")
            with (
                mock.patch.object(config, "H6_NAMES", ("NVDA",)),
                mock.patch(
                    "options_researcher.h6_watch.load_book", return_value=[]
                ),
                mock.patch(
                    "options_researcher.h6_watch.load_assertions", return_value=[]
                ),
            ):
                snapshot, _ = build_snapshot(
                    AS_OF,
                    book_path=root / "book.csv",
                    chain_dir=chain_dir,
                    feature_dir=root / "features",
                    assertions_path=root / "gating.csv",
                    raw_assertions_path=root / "raw.csv",
                )

        self.assertEqual(snapshot["entries"], [])
        self.assertEqual(len(snapshot["errors"]), 1)
        self.assertIn("exact chain missing", snapshot["errors"][0])
        self.assertIn("NVDA_2026-07-13.parquet", snapshot["errors"][0])

    def _seed_snapshot_inputs(self, root: Path) -> tuple[dict, dict[str, Path]]:
        book_path = root / "h6_positions.csv"
        with book_path.open("w", newline="") as fh:
            csv.writer(fh).writerow(
                [
                    "id",
                    "symbol",
                    "strike",
                    "expiration",
                    "contracts",
                    "entry_date",
                    "entry_cost",
                    "entry_receipt_hash",
                    "exit_date",
                    "exit_proceeds",
                    "exit_reason",
                    "exit_receipt_hash",
                ]
            )
        chain_dir = root / "chains"
        feature_dir = root / "features"
        chain_dir.mkdir()
        feature_dir.mkdir()
        for symbol in config.H6_NAMES:
            chain().to_parquet(chain_dir / f"{symbol}_{AS_OF.isoformat()}.parquet")
            pd.DataFrame(
                {"iv_rank": [0.2]}, index=pd.Index([AS_OF.isoformat()])
            ).to_parquet(feature_dir / f"{symbol}_features.parquet")
            (feature_dir / f"{symbol}_features.manifest.json").write_text(
                "synthetic manifest fixture\n"
            )
        gating_path = root / "gating.csv"
        raw_path = root / "raw.csv"
        gating_path.write_text("synthetic gating fixture\n")
        raw_path.write_text("synthetic raw fixture\n")
        assertions = [
            assertion(symbol, "2026-08-26", status="estimated")
            for symbol in config.H6_NAMES
        ]
        with (
            mock.patch(
                "options_researcher.h6_watch.load_assertions",
                return_value=assertions,
            ),
            mock.patch(
                "options_researcher.h6_watch.verify_feature_manifest"
            ) as verify_manifest,
        ):
            result = build_snapshot(
                AS_OF,
                book_path=book_path,
                chain_dir=chain_dir,
                feature_dir=feature_dir,
                assertions_path=gating_path,
                raw_assertions_path=raw_path,
            )
        self.assertEqual(verify_manifest.call_count, len(config.H6_NAMES))
        return result

    def test_snapshot_and_receipt_bind_all_exact_session_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot, inputs = self._seed_snapshot_inputs(root)
            self.assertEqual(snapshot["errors"], [])
            self.assertEqual(len(snapshot["entries"]), len(config.H6_NAMES))
            receipt = build_receipt(snapshot, inputs)
            self.assertEqual(receipt["hypothesis_id"], "H6")
            self.assertEqual(set(receipt["input_files"]), set(inputs))
            self.assertEqual(
                len(
                    [
                        label
                        for label in inputs
                        if label.startswith("feature_manifest:")
                    ]
                ),
                len(config.H6_NAMES),
            )
            self.assertEqual(verify_receipt(receipt, receipt), [])

            changed = next(path for label, path in inputs.items() if label.startswith("chain:"))
            changed.write_bytes(changed.read_bytes() + b"mutation")
            recomputed = build_receipt(snapshot, inputs)
            self.assertIn("input_files", verify_receipt(receipt, recomputed))

    def test_receipt_write_is_idempotent_but_refuses_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot, inputs = self._seed_snapshot_inputs(root)
            receipt = build_receipt(snapshot, inputs)
            path = root / "receipts" / "2026-07-13.json"
            first_hash = write_receipt(receipt, path)
            self.assertEqual(write_receipt(receipt, path), first_hash)

            changed_snapshot = dict(snapshot, evaluation_session="2026-07-14")
            changed_receipt = build_receipt(changed_snapshot, inputs)
            with self.assertRaisesRegex(FileExistsError, "non-identical"):
                write_receipt(changed_receipt, path)

    def test_receipt_self_hash_detects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, inputs = self._seed_snapshot_inputs(Path(tmp))
            receipt = build_receipt(snapshot, inputs)
            tampered = dict(receipt)
            tampered["trial_intent_record_hash"] = "0" * 64
            self.assertIn("receipt_hash", verify_receipt(tampered, receipt))

    def test_book_entry_must_match_one_eligible_receipt_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot, inputs = self._seed_snapshot_inputs(root)
            receipt = build_receipt(snapshot, inputs)
            receipt_dir = root / "receipts"
            write_receipt(receipt, receipt_dir / "decision-01.json")
            candidate = next(
                row["candidate"]
                for row in snapshot["entries"]
                if row["symbol"] == "NVDA"
            )
            recorded = position(
                entry_date=AS_OF,
                expiration=date.fromisoformat(candidate["expiration"]),
                entry_cost=float(candidate["entry_cost"]),
                entry_receipt_hash=receipt["receipt_hash"],
            )
            verify_book_receipts([recorded], receipt_dir=receipt_dir)
            with inputs["book"].open("a", newline="") as fh:
                csv.DictWriter(fh, fieldnames=BOOK_FIELDS).writerow(
                    {
                        "id": recorded.id,
                        "symbol": recorded.symbol,
                        "strike": recorded.strike,
                        "expiration": recorded.expiration.isoformat(),
                        "contracts": recorded.contracts,
                        "entry_date": recorded.entry_date.isoformat(),
                        "entry_cost": recorded.entry_cost,
                        "entry_receipt_hash": recorded.entry_receipt_hash,
                        "exit_date": "",
                        "exit_proceeds": "",
                        "exit_reason": "",
                        "exit_receipt_hash": "",
                    }
                )
            self.assertEqual(
                load_book(inputs["book"], receipt_dir=receipt_dir), [recorded]
            )

            altered = position(
                entry_date=AS_OF,
                expiration=date.fromisoformat(candidate["expiration"]),
                entry_cost=float(candidate["entry_cost"]) + 0.01,
                entry_receipt_hash=receipt["receipt_hash"],
            )
            with self.assertRaisesRegex(ValueError, "differs from receipt"):
                verify_book_receipts([altered], receipt_dir=receipt_dir)

    def test_one_receipt_cannot_authorize_multiple_book_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot, inputs = self._seed_snapshot_inputs(root)
            receipt = build_receipt(snapshot, inputs)
            receipt_dir = root / "receipts"
            write_receipt(receipt, receipt_dir / "decision-01.json")
            rows = [
                position(
                    pid=f"reuse-{symbol}",
                    symbol=symbol,
                    entry_date=AS_OF,
                    entry_receipt_hash=receipt["receipt_hash"],
                )
                for symbol in ("NVDA", "PLTR")
            ]
            with self.assertRaisesRegex(ValueError, "receipt reused"):
                verify_book_receipts(rows, receipt_dir=receipt_dir)

    def test_book_exit_must_match_close_decision_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot, inputs = self._seed_snapshot_inputs(root)
            entry_receipt = build_receipt(snapshot, inputs)
            candidate = next(
                row["candidate"]
                for row in snapshot["entries"]
                if row["symbol"] == "NVDA"
            )
            exit_snapshot = dict(
                snapshot,
                evaluation_session="2026-08-28",
                exits=[
                    {
                        "position_id": "h6-1",
                        "evaluation_session": "2026-08-28",
                        "action": "CLOSE",
                        "reason": "time_21_dte",
                        "dte": 21,
                        "proceeds": 500.0,
                        "pnl": 500.0 - float(candidate["entry_cost"]),
                    }
                ],
            )
            exit_receipt = build_receipt(exit_snapshot, inputs)
            receipt_dir = root / "receipts"
            write_receipt(entry_receipt, receipt_dir / "entry.json")
            write_receipt(exit_receipt, receipt_dir / "exit.json")
            recorded = position(
                entry_date=AS_OF,
                expiration=date.fromisoformat(candidate["expiration"]),
                entry_cost=float(candidate["entry_cost"]),
                entry_receipt_hash=entry_receipt["receipt_hash"],
                exit_date=date(2026, 8, 28),
                exit_proceeds=500.0,
                exit_reason="time_21_dte",
                exit_receipt_hash=exit_receipt["receipt_hash"],
            )
            verify_book_receipts([recorded], receipt_dir=receipt_dir)

            altered = dataclasses.replace(recorded, exit_proceeds=499.99)
            with self.assertRaisesRegex(ValueError, "exit differs from receipt"):
                verify_book_receipts([altered], receipt_dir=receipt_dir)


if __name__ == "__main__":
    unittest.main()
