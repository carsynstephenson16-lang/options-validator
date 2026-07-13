import csv
import math
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import pandas as pd

import config
from options_researcher.h6_watch import (
    BookPosition,
    choose_contract,
    evaluate_entry,
    evaluate_exit,
    load_book,
    score_book,
    timing_state,
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
    exit_date: date | None = None,
    exit_proceeds: float | None = None,
    exit_reason: str | None = None,
) -> BookPosition:
    return BookPosition(
        id=pid,
        symbol=symbol,
        strike=105.0,
        expiration=expiration,
        contracts=1,
        entry_date=entry_date,
        entry_cost=entry_cost,
        exit_date=exit_date,
        exit_proceeds=exit_proceeds,
        exit_reason=exit_reason,
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
        good = evaluate_entry(
            "NVDA",
            AS_OF,
            chain(),
            iv_rank=0.50,
            assertions=self.future(),
            known_as_of=KNOWN,
            book=[],
        )
        self.assertEqual(good.status, "ELIGIBLE")
        high = evaluate_entry(
            "NVDA",
            AS_OF,
            chain(),
            iv_rank=0.5001,
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
            "exit_date",
            "exit_proceeds",
            "exit_reason",
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
                        "2026-07-20",
                        "",
                        "take_profit",
                    ]
                )
            with self.assertRaises(ValueError):
                load_book(path)


class ScoreTests(unittest.TestCase):
    def closed(self, index: int, pnl: float) -> BookPosition:
        entry = date(2026, 1, 2) + pd.offsets.BDay(index * 5)
        entry_date = entry.date() if hasattr(entry, "date") else entry
        return position(
            pid=f"h6-{index}",
            symbol=config.H6_NAMES[index % len(config.H6_NAMES)],
            entry_date=entry_date,
            entry_cost=500.0,
            exit_date=entry_date + pd.Timedelta(days=30),
            exit_proceeds=500.0 + pnl,
            exit_reason="take_profit",
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
        for month in (1, 2, 3):
            for slot in (0, 1):
                rows.append(
                    position(
                        pid=f"loss-{month}-{slot}",
                        symbol=config.H6_NAMES[slot],
                        entry_date=date(2026, month, 2 + slot),
                        entry_cost=1000.0,
                        exit_date=date(2026, month, 20 + slot),
                        exit_proceeds=0.0,
                        exit_reason="time_21_dte",
                    )
                )
        score = score_book(rows)
        self.assertEqual(score.verdict, "REJECT")
        self.assertTrue(score.hard_kill)


if __name__ == "__main__":
    unittest.main()
