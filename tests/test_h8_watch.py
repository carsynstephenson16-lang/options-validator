import csv
import math
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import pandas as pd

import config
from options_researcher.h8_watch import (
    BOOK_FIELDS,
    BookPosition,
    choose_contract,
    entry_window_state,
    evaluate_entry,
    evaluate_exit,
    load_book,
    next_scheduled_report,
    validate_book,
    validate_cross_book,
)

# on=2026-07-13 sits inside the T-15..T-8 window of a report dated 2026-07-31
# (T-15=2026-07-10, T-8=2026-07-21, T-2=2026-07-29); see the design check in
# the build session. Every boundary below is derived from config, never a
# hardcoded literal.
AS_OF = date(2026, 7, 13)
CONFIRMED_REPORT = date(2026, 7, 31)
KNOWN = datetime.fromisoformat("2026-07-31T22:00:00+00:00")


def assertion(
    symbol: str,
    report: str,
    *,
    status: str = "confirmed",
    timing: str = "amc",
    event: str = "FY26Q3",
    known: str = "2026-06-01T12:00:00+00:00",
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
        # Weekly is closer but H8 requires a standard monthly.
        ("2026-08-28", 100.0, "C", 0.49, 7.00, 7.20, 500),
        # Earliest standard monthly inside 45-90 DTE is 2026-09-18.
        ("2026-09-18", 100.0, "C", 0.40, 6.00, 6.10, 500),
        ("2026-09-18", 105.0, "C", 0.50, 9.80, 9.90, 500),
        ("2026-09-18", 110.0, "C", 0.51, 5.00, 5.10, 500),
        ("2026-09-18", 115.0, "C", 0.45, 10.00, 10.01, 500),
        ("2026-09-18", 120.0, "C", 0.48, 5.00, 5.50, 10),
        # A later monthly must not win even with a higher in-band delta.
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


def exit_chain(bid: float, ask: float) -> pd.DataFrame:
    return pd.DataFrame(
        [("2026-09-18", 105.0, "C", 0.40, bid, ask, 500)],
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
    pid: str = "h8-1",
    symbol: str = "PLTR",
    entry_date: date = date(2026, 7, 6),
    entry_cost: float = 500.0,
    expiration: date = date(2026, 9, 18),
    contracts: int = 1,
    strike: float = 105.0,
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
        strike=strike,
        expiration=expiration,
        contracts=contracts,
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
        picked = choose_contract(chain(), AS_OF, symbol="PLTR")
        self.assertIsNotNone(picked)
        self.assertEqual(picked.expiration, date(2026, 9, 18))
        self.assertEqual(picked.strike, 105.0)
        self.assertEqual(picked.delta, 0.50)
        # Canonical adverse buy: ceil(9.90 * 1.01) + one entry commission.
        self.assertEqual(picked.entry_cost, 1000.65)

    def test_raw_ask_and_liquidity_gates_are_hard(self):
        frame = chain()
        # Push the delta-0.50 strike over the $1,000 raw-ask cap; the 0.51
        # strike is out of band, so the 0.40 strike must win.
        frame.loc[frame["strike"] == 105.0, "ask"] = 10.01
        picked = choose_contract(frame, AS_OF)
        self.assertEqual(picked.strike, 100.0)
        self.assertLessEqual(picked.raw_ask * 100.0, config.H8_MAX_ASK_DOLLARS)

    def test_low_open_interest_leg_is_skipped(self):
        # strike 120 has delta 0.48 but only 10 open interest -> illiquid.
        picked = choose_contract(chain(), AS_OF)
        self.assertNotEqual(picked.strike, 120.0)

    def test_malformed_chain_fails_loud(self):
        with self.assertRaises(ValueError):
            choose_contract(chain().drop(columns=["delta"]), AS_OF)


class EntryWindowTests(unittest.TestCase):
    def test_confirmed_window_edges_are_in_window(self):
        for on in (date(2026, 7, 10), AS_OF, date(2026, 7, 21)):
            state = entry_window_state(
                "PLTR", on, [assertion("PLTR", "2026-07-31")], known_as_of=KNOWN
            )
            self.assertEqual(state.state, "IN_WINDOW", on)
            self.assertEqual(state.report, CONFIRMED_REPORT)

    def test_before_and_after_window_are_out_of_window(self):
        rows = [assertion("PLTR", "2026-07-31")]
        early = entry_window_state("PLTR", date(2026, 7, 9), rows, known_as_of=KNOWN)
        self.assertEqual(early.state, "OUT_OF_WINDOW")
        late = entry_window_state("PLTR", date(2026, 7, 22), rows, known_as_of=KNOWN)
        self.assertEqual(late.state, "OUT_OF_WINDOW")

    def test_estimated_date_in_window_fails_closed(self):
        rows = [assertion("PLTR", "2026-07-31", status="estimated")]
        state = entry_window_state("PLTR", AS_OF, rows, known_as_of=KNOWN)
        self.assertEqual(state.state, "ESTIMATED_BLOCKED")

    def test_no_assertions_is_unknown(self):
        state = entry_window_state("PLTR", AS_OF, [], known_as_of=KNOWN)
        self.assertEqual(state.state, "UNKNOWN")

    def test_conflicting_schedule_is_unknown(self):
        # Two distinct event_ids for the SAME fiscal period disagree on the
        # date -> the view keeps both and the gate fails closed to UNKNOWN.
        first = assertion("PLTR", "2026-07-31", status="estimated")
        second = assertion(
            "PLTR", "2026-08-14", status="estimated",
            known="2026-06-02T12:00:00+00:00",
        )
        second["event_id"] = "PLTR-FY26Q3-alt"
        state = entry_window_state("PLTR", AS_OF, [first, second], known_as_of=KNOWN)
        self.assertEqual(state.state, "UNKNOWN")


class EntryDecisionTests(unittest.TestCase):
    def confirmed(self):
        return [assertion("PLTR", "2026-07-31")]

    def _entry(self, *, iv_rank, h8_book=None, h6_book=None, symbol="PLTR"):
        return evaluate_entry(
            symbol,
            AS_OF,
            chain(),
            iv_rank=iv_rank,
            assertions=self.confirmed(),
            known_as_of=KNOWN,
            h8_book=h8_book or [],
            h6_book=h6_book or [],
        )

    def test_ivr_gate_boundary_and_nan(self):
        good = self._entry(iv_rank=config.H8_IVR_MAX)
        self.assertEqual(good.status, "ENTRY-OK")
        self.assertIsNotNone(good.candidate)
        high = self._entry(iv_rank=config.H8_IVR_MAX + 0.0001)
        self.assertEqual(high.status, "BLOCKED")
        self.assertIn("iv-rank", " ".join(high.reasons).lower())
        missing = self._entry(iv_rank=math.nan)
        self.assertEqual(missing.status, "BLOCKED")
        self.assertIn("unknown", " ".join(missing.reasons).lower())

    def test_out_of_window_is_not_blocked(self):
        decision = evaluate_entry(
            "PLTR",
            date(2026, 7, 22),  # T-7, too close to the report
            chain(),
            iv_rank=0.2,
            assertions=self.confirmed(),
            known_as_of=KNOWN,
            h8_book=[],
            h6_book=[],
        )
        self.assertEqual(decision.status, "OUT_OF_WINDOW")
        self.assertEqual(decision.reasons, ())

    def test_estimated_report_blocks_entry(self):
        decision = evaluate_entry(
            "PLTR",
            AS_OF,
            chain(),
            iv_rank=0.2,
            assertions=[assertion("PLTR", "2026-07-31", status="estimated")],
            known_as_of=KNOWN,
            h8_book=[],
            h6_book=[],
        )
        self.assertEqual(decision.status, "BLOCKED")
        self.assertIn("estimated", " ".join(decision.reasons).lower())

    def test_shared_h6_h8_monthly_cap_consumed_by_h6(self):
        # An open H6 NVDA position entered this month eats the shared cap; the
        # candidate premium (~$1,000.65) then overflows the $2,000 ceiling.
        h6_book = [
            position(pid="h6", symbol="NVDA", entry_date=date(2026, 7, 6), entry_cost=1500.0)
        ]
        decision = self._entry(iv_rank=0.2, h6_book=h6_book)
        self.assertEqual(decision.status, "BLOCKED")
        self.assertIn("shared", " ".join(decision.reasons).lower())
        self.assertEqual(decision.monthly_risk_used, 1500.0)

    def test_same_underlying_open_in_h6_blocks(self):
        h6_book = [
            position(pid="h6", symbol="PLTR", entry_date=date(2026, 7, 6), entry_cost=500.0)
        ]
        decision = self._entry(iv_rank=0.2, h6_book=h6_book)
        self.assertEqual(decision.status, "BLOCKED")
        self.assertIn("h6", " ".join(decision.reasons).lower())

    def test_same_name_open_in_h8_blocks(self):
        h8_book = [
            position(pid="open", symbol="PLTR", entry_date=date(2026, 7, 6), entry_cost=500.0)
        ]
        decision = self._entry(iv_rank=0.2, h8_book=h8_book)
        self.assertEqual(decision.status, "BLOCKED")
        self.assertIn("already open in h8", " ".join(decision.reasons).lower())

    def test_two_concurrent_h8_reaches_cap(self):
        h8_book = [
            position(pid="p-PLTR", symbol="PLTR", entry_date=date(2026, 7, 6), entry_cost=400.0),
            position(pid="p-AMZN", symbol="AMZN", entry_date=date(2026, 7, 6), entry_cost=400.0),
        ]
        decision = self._entry(iv_rank=0.2, h8_book=h8_book)
        self.assertEqual(decision.status, "BLOCKED")
        self.assertIn("reaches cap", " ".join(decision.reasons).lower())

    def test_out_of_scope_symbol_raises(self):
        with self.assertRaises(ValueError):
            self._entry(iv_rank=0.2, symbol="NVDA")


class ExitAlertTests(unittest.TestCase):
    def test_take_profit_fires_at_or_above_75pct(self):
        # $1,000 premium -> +75% threshold is exactly $1,750.00. Conservative
        # proceeds = floor(17.69 * 99) - 0.65 = $1,750.35, clearing the line.
        pos = position(entry_cost=1000.0)
        decision = evaluate_exit(pos, AS_OF, exit_chain(17.69, 17.80), next_report=None)
        self.assertEqual(decision.action, "EXIT")
        self.assertEqual(decision.reason, "take_profit")
        self.assertEqual(decision.proceeds, 1750.35)

    def test_take_profit_holds_just_below_threshold(self):
        # Same $1,750.00 threshold; one cent less bid -> proceeds $1,749.35,
        # a hair short of +75%, so the position holds.
        pos = position(entry_cost=1000.0)
        decision = evaluate_exit(pos, AS_OF, exit_chain(17.68, 17.80), next_report=None)
        self.assertEqual(decision.action, "HOLD")
        self.assertEqual(decision.proceeds, 1749.35)

    def test_hard_exit_fires_at_t2(self):
        pos = position(entry_cost=900.0)
        # T-2 for a 2026-07-31 report is 2026-07-29.
        at_t2 = evaluate_exit(
            pos, date(2026, 7, 29), exit_chain(5.0, 5.1), next_report=CONFIRMED_REPORT
        )
        self.assertEqual(at_t2.action, "EXIT")
        self.assertEqual(at_t2.reason, "hard_exit_t2")
        before = evaluate_exit(
            pos, date(2026, 7, 28), exit_chain(5.0, 5.1), next_report=CONFIRMED_REPORT
        )
        self.assertEqual(before.action, "HOLD")

    def test_confirmed_date_moving_inside_t2_forces_exit(self):
        # The report was pulled forward to 2026-07-16; evaluating on 2026-07-15
        # (T-1) is already inside T-2 -> exit immediately.
        pos = position(entry_cost=900.0)
        decision = evaluate_exit(
            pos, date(2026, 7, 15), exit_chain(5.0, 5.1), next_report=date(2026, 7, 16)
        )
        self.assertEqual(decision.action, "EXIT")
        self.assertEqual(decision.reason, "hard_exit_t2")

    def test_missing_exit_quote_is_blocked_not_raised(self):
        pos = position(entry_cost=900.0, strike=999.0)
        decision = evaluate_exit(pos, AS_OF, exit_chain(5.0, 5.1), next_report=None)
        self.assertEqual(decision.action, "BLOCKED")

    def test_next_scheduled_report_picks_earliest_upcoming(self):
        rows = [
            assertion("PLTR", "2026-07-31"),
            assertion(
                "PLTR",
                "2026-10-30",
                event="FY26Q4",
                known="2026-06-05T12:00:00+00:00",
            ),
        ]
        self.assertEqual(
            next_scheduled_report("PLTR", AS_OF, rows, known_as_of=KNOWN),
            CONFIRMED_REPORT,
        )


class BookValidationTests(unittest.TestCase):
    def test_rejects_non_session_entry_date(self):
        with self.assertRaisesRegex(ValueError, "XNYS session"):
            validate_book([position(entry_date=date(2026, 7, 4))])

    def test_rejects_entry_tenor_outside_band(self):
        with self.assertRaisesRegex(ValueError, "entry DTE"):
            validate_book(
                [position(entry_date=AS_OF, expiration=date(2026, 8, 21))]
            )

    def test_rejects_wrong_contract_count(self):
        with self.assertRaisesRegex(ValueError, "contracts must equal"):
            validate_book([position(entry_date=AS_OF, contracts=2)])

    def test_rejects_out_of_scope_symbol(self):
        with self.assertRaisesRegex(ValueError, "outside H8"):
            validate_book([position(entry_date=AS_OF, symbol="NVDA")])

    def test_rejects_three_concurrent(self):
        rows = [
            position(
                pid=f"p{i}",
                symbol=symbol,
                entry_date=AS_OF,
                entry_cost=400.0,
            )
            for i, symbol in enumerate(("PLTR", "AMZN", "PLTR"))
        ]
        with self.assertRaisesRegex(ValueError, "concurrent H8 positions 3"):
            validate_book(rows)

    def test_rejects_same_name_overlap(self):
        rows = [
            position(pid="a", symbol="PLTR", entry_date=date(2026, 7, 6), entry_cost=400.0),
            position(pid="b", symbol="PLTR", entry_date=AS_OF, entry_cost=400.0),
        ]
        with self.assertRaisesRegex(ValueError, "overlapping H8 positions for PLTR"):
            validate_book(rows)

    def test_rejects_unearned_take_profit(self):
        # 500 premium needs proceeds >= 500 * 1.75 = 875 to book a take-profit;
        # 800 is short of that, so the close is not a real +75% exit.
        false_tp = position(
            entry_date=AS_OF,
            expiration=date(2026, 9, 18),
            exit_date=date(2026, 7, 20),
            exit_proceeds=800.0,
            exit_reason="take_profit",
        )
        with self.assertRaisesRegex(ValueError, "take_profit"):
            validate_book([false_tp])

    def test_rejects_unknown_exit_reason(self):
        bad = position(
            entry_date=AS_OF,
            expiration=date(2026, 9, 18),
            exit_date=date(2026, 7, 20),
            exit_proceeds=800.0,
            exit_reason="time_21_dte",  # an H6 reason, not valid for H8
        )
        with self.assertRaisesRegex(ValueError, "exit_reason"):
            validate_book([bad])

    def test_cross_book_rejects_same_name_concurrent_with_h6(self):
        h8_book = [position(pid="h8", symbol="PLTR", entry_date=date(2026, 7, 6))]
        h6_book = [position(pid="h6", symbol="PLTR", entry_date=date(2026, 7, 6))]
        with self.assertRaisesRegex(ValueError, "both open"):
            validate_cross_book(h8_book, h6_book)

    def test_cross_book_rejects_combined_monthly_overflow(self):
        h8_book = [position(pid="h8", symbol="PLTR", entry_date=AS_OF, entry_cost=1000.0)]
        h6_book = [position(pid="h6", symbol="NVDA", entry_date=AS_OF, entry_cost=1500.0)]
        with self.assertRaisesRegex(ValueError, "combined H6\\+H8"):
            validate_cross_book(h8_book, h6_book)


class BookLoaderTests(unittest.TestCase):
    def _write(self, rows: list[list[str]]) -> Path:
        tmp = Path(tempfile.mkdtemp()) / "h8.csv"
        with tmp.open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(list(BOOK_FIELDS))
            for row in rows:
                writer.writerow(row)
        return tmp

    def test_loads_valid_open_row(self):
        path = self._write(
            [
                [
                    "h8-1",
                    "PLTR",
                    "105",
                    "2026-09-18",
                    "1",
                    "2026-07-13",
                    "500.0",
                    "a" * 64,
                    "",
                    "",
                    "",
                    "",
                ]
            ]
        )
        book = load_book(path)
        self.assertEqual(len(book), 1)
        self.assertEqual(book[0].symbol, "PLTR")
        self.assertTrue(book[0].is_open)

    def test_empty_book_loads(self):
        path = self._write([])
        self.assertEqual(load_book(path), [])

    def test_rejects_partial_close(self):
        path = self._write(
            [
                [
                    "h8-1",
                    "PLTR",
                    "105",
                    "2026-09-18",
                    "1",
                    "2026-07-13",
                    "500.0",
                    "a" * 64,
                    "2026-07-20",
                    "",  # missing proceeds
                    "hard_exit_t2",
                    "b" * 64,
                ]
            ]
        )
        with self.assertRaises(ValueError):
            load_book(path)


if __name__ == "__main__":
    unittest.main()
