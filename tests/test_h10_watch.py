import contextlib
import io
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from options_researcher import h10_watch, qm_signals
from options_researcher.h7_watch import evaluation_session
from tests.test_qm_signals import PARAMS, breakout_fixture, parabolic_fixture

AS_OF = "2026-07-14"
EVAL_ISO = evaluation_session(date.fromisoformat(AS_OF)).isoformat()
KNOWN_AS_OF = datetime.fromisoformat(f"{EVAL_ISO}T20:00:00+00:00")
EXPIRATION = "2026-08-21"
BOOK_HEADER = (
    "id,symbol,strike,expiration,contracts,entry_date,entry_cost,"
    "entry_receipt_hash,exit_date,exit_proceeds,exit_reason,exit_receipt_hash\n"
)


def _relabel(frame: pd.DataFrame, end_iso: str) -> pd.DataFrame:
    index = pd.bdate_range(end=end_iso, periods=len(frame))
    out = frame.copy()
    out.index = pd.Index([day.strftime("%Y-%m-%d") for day in index], name="date")
    return out


def _adjusted_quiet(_symbol: str, eval_iso: str) -> pd.DataFrame:
    closes = [100.0] * 80
    frame = pd.DataFrame(
        {
            "open": closes,
            "high": [value + 1.0 for value in closes],
            "low": [value - 1.0 for value in closes],
            "close": closes,
            "volume": [1_000_000.0] * len(closes),
        }
    )
    return _relabel(frame, eval_iso)


def _adjusted_breakout(_symbol: str, eval_iso: str) -> pd.DataFrame:
    return _relabel(breakout_fixture(), eval_iso)


def _adjusted_parabolic(_symbol: str, eval_iso: str) -> pd.DataFrame:
    frame = parabolic_fixture()
    first = next(
        position
        for position, stamp in enumerate(frame.index)
        if qm_signals.parabolic_qualifies(frame, stamp, PARAMS)
    )
    return _relabel(frame.iloc[: first + 1], eval_iso)


def _raw(_symbol: str, eval_iso: str) -> pd.DataFrame:
    closes = [100.0] * 5
    frame = pd.DataFrame(
        {
            "open": closes,
            "high": [101.0] * len(closes),
            "low": [99.0] * len(closes),
            "close": closes,
            "volume": [1_000_000.0] * len(closes),
        }
    )
    return _relabel(frame, eval_iso)


def _chain(_symbol: str, _eval_iso: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            (EXPIRATION, 92.0, "C", 0.60, 4.80, 5.00, 500),
            (EXPIRATION, 96.0, "C", 0.55, 4.80, 5.00, 500),
            (EXPIRATION, 100.0, "C", 0.50, 4.80, 5.00, 500),
            (EXPIRATION, 104.0, "C", 0.45, 4.80, 5.00, 500),
            (EXPIRATION, 108.0, "C", 0.40, 4.80, 5.00, 500),
            (EXPIRATION, 100.0, "P", -0.50, 4.80, 5.00, 500),
        ],
        columns=(
            "expiration",
            "strike",
            "right",
            "delta",
            "bid",
            "ask",
            "open_interest",
        ),
    )


def _assertion(report: str) -> dict:
    return {
        "record_id": "PLTR-2026Q3-confirmed",
        "symbol": "PLTR",
        "event_id": "PLTR-2026Q3",
        "fiscal_period": "2026Q3",
        "record_type": "assertion",
        "event_class": "actual_quarterly_earnings",
        "status": "confirmed",
        "expected_date": date.fromisoformat(report),
        "occurred_date": None,
        "session_timing": "amc",
        "source_type": "company_ir",
        "source_url": "https://example.test/pltr-ir",
        "known_as_of_utc": datetime.fromisoformat("2026-07-01T12:00:00+00:00"),
        "checked_at_utc": datetime.fromisoformat("2026-07-01T12:00:00+00:00"),
        "supersedes": "",
        "promoted_from": "raw-1",
        "notes": "",
    }


def _write_book(path: Path, *, open_premium: float | None = None) -> None:
    text = BOOK_HEADER
    if open_premium is not None:
        text += (
            "h10-1,NVDA,100,2026-08-21,1,2026-07-01,"
            f"{open_premium:.2f},{'a' * 64},,,,\n"
        )
    path.write_text(text, encoding="utf-8")


def _run(
    root: Path,
    *,
    adjusted=_adjusted_quiet,
    chain_loader=_chain,
    assertions: list[dict] | None = None,
    universe: list[str] | None = None,
):
    book = root / "h10_positions.csv"
    if not book.exists():
        _write_book(book)
    receipts = root / "receipts"
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        rc = h10_watch.main(
            ["--as-of", AS_OF],
            universe=["PLTR"] if universe is None else universe,
            load_adjusted=adjusted,
            load_raw=_raw,
            load_chain=chain_loader,
            params=PARAMS,
            gate=lambda: None,
            load_assertions_fn=lambda: (
                [_assertion("2026-10-01")] if assertions is None else assertions
            ),
            book_path=book,
            receipt_dir=receipts,
            known_as_of=KNOWN_AS_OF,
        )
    receipt_path = receipts / f"h10_watch_{AS_OF}.json"
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
    return rc, stdout.getvalue(), receipt, receipt_path


class QuietTests(unittest.TestCase):
    def test_no_signal_is_explicitly_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, output, receipt, _ = _run(Path(tmp))

        self.assertEqual(rc, 0)
        self.assertIn("forward paper study H10a/H10b", output)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "NO_SIGNAL")
        self.assertEqual(row["signals"], {"H10a": False, "H10b": False})
        self.assertIsNone(row["candidate_contract"])
        self.assertFalse(row["book_action_required"])
        self.assertFalse(receipt["book_action_required"])


class FireTests(unittest.TestCase):
    def test_parabolic_continuation_fire_selects_a_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, output, receipt, _ = _run(
                Path(tmp), adjusted=_adjusted_parabolic
            )

        self.assertEqual(rc, 0)
        self.assertIn("never trades", output)
        self.assertIn("verdict gates on losses", output)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "FIRED")
        self.assertEqual(row["signals"], {"H10a": True, "H10b": False})
        self.assertEqual(row["admitted_contracts"], 5)
        self.assertTrue(row["book_action_required"])
        candidate = row["candidate_contract"]
        self.assertEqual(candidate["right"], "C")
        self.assertEqual(candidate["strike"], 92.0)
        self.assertEqual(candidate["delta"], 0.60)
        self.assertEqual(candidate["entry_price"], 5.05)
        self.assertEqual(candidate["exit_price"], 4.75)
        self.assertEqual(candidate["entry_cost"], 505.65)

    def test_breakout_continuation_fire_is_recorded_as_h10b(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(Path(tmp), adjusted=_adjusted_breakout)

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "FIRED")
        self.assertEqual(row["signals"], {"H10a": False, "H10b": True})
        self.assertTrue(receipt["book_action_required"])

    def test_failed_h7_admission_is_an_explicit_skip(self):
        def four_contracts(symbol: str, eval_iso: str) -> pd.DataFrame:
            return _chain(symbol, eval_iso).iloc[:4].copy()

        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(
                Path(tmp), adjusted=_adjusted_breakout, chain_loader=four_contracts
            )

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "SKIPPED")
        self.assertEqual(row["reason"], "ADMISSION")
        self.assertEqual(row["admitted_contracts"], 4)
        self.assertFalse(row["book_action_required"])

    def test_after_cost_premium_cap_is_a_hard_contract_gate(self):
        def expensive(symbol: str, eval_iso: str) -> pd.DataFrame:
            frame = _chain(symbol, eval_iso)
            frame.loc[frame["right"] == "C", ["bid", "ask"]] = [5.80, 6.00]
            return frame

        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(
                Path(tmp), adjusted=_adjusted_breakout, chain_loader=expensive
            )

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "SKIPPED")
        self.assertEqual(row["reason"], "NO_CONTRACT")
        self.assertIsNone(row["candidate_contract"])


class CapTests(unittest.TestCase):
    def test_cap_exceeded_is_skipped_with_cap_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_book(root / "h10_positions.csv", open_premium=1_500.00)
            rc, _, receipt, _ = _run(root, adjusted=_adjusted_breakout)

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "SKIPPED")
        self.assertEqual(row["reason"], "CAP")
        self.assertIsNotNone(row["candidate_contract"])
        self.assertFalse(row["book_action_required"])

    def test_header_only_book_allows_an_eligible_fire(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(Path(tmp), adjusted=_adjusted_breakout)

        self.assertEqual(rc, 0)
        self.assertEqual(receipt["evaluations"][0]["status"], "FIRED")


class EarningsSkipTests(unittest.TestCase):
    def test_known_report_inside_option_life_skips_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(
                Path(tmp),
                adjusted=_adjusted_breakout,
                assertions=[_assertion("2026-08-10")],
            )

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "SKIPPED")
        self.assertEqual(row["reason"], "EARNINGS")
        self.assertFalse(row["book_action_required"])

    def test_unhealthy_source_is_a_per_name_entry_ban(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(
                Path(tmp), adjusted=_adjusted_breakout, assertions=[]
            )

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "SKIPPED")
        self.assertEqual(row["reason"], "SOURCE_HEALTH")


class ReceiptTests(unittest.TestCase):
    def test_receipt_schema_keys_are_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, receipt, _ = _run(Path(tmp), adjusted=_adjusted_breakout)

        self.assertEqual(
            set(receipt),
            {"as_of", "evaluation_session", "evaluations", "book_action_required"},
        )
        row = receipt["evaluations"][0]
        self.assertEqual(
            set(row),
            {
                "symbol",
                "signals",
                "status",
                "reason",
                "admitted_contracts",
                "candidate_contract",
                "book_action_required",
            },
        )
        self.assertEqual(set(row["signals"]), {"H10a", "H10b"})
        self.assertEqual(
            set(row["candidate_contract"]),
            {
                "symbol",
                "right",
                "strike",
                "expiration",
                "dte",
                "delta",
                "bid",
                "ask",
                "open_interest",
                "spot",
                "entry_price",
                "exit_price",
                "entry_cost",
            },
        )

    def test_same_as_of_is_idempotent_and_only_receipt_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book = root / "h10_positions.csv"
            _write_book(book)
            before_book = book.read_bytes()
            first_rc, _, _, path = _run(root, adjusted=_adjusted_breakout)
            first_bytes = path.read_bytes()
            second_rc, _, _, second_path = _run(root, adjusted=_adjusted_breakout)
            second_bytes = second_path.read_bytes()
            after_book = book.read_bytes()
            files = sorted(
                item.relative_to(root).as_posix()
                for item in root.rglob("*")
                if item.is_file()
            )

        self.assertEqual((first_rc, second_rc), (0, 0))
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(before_book, after_book)
        self.assertEqual(
            files,
            ["h10_positions.csv", f"receipts/h10_watch_{AS_OF}.json"],
        )


class FutureAsOfTests(unittest.TestCase):
    def test_future_as_of_refuses_before_loaders_or_receipt(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        calls: list[str] = []

        def spy(symbol: str, _eval_iso: str):
            calls.append(symbol)
            raise AssertionError("future refusal must precede data loading")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_book(root / "h10_positions.csv")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                rc = h10_watch.main(
                    ["--as-of", future],
                    universe=["PLTR"],
                    load_adjusted=spy,
                    load_raw=spy,
                    load_chain=spy,
                    params=PARAMS,
                    gate=lambda: None,
                    load_assertions_fn=lambda: [],
                    book_path=root / "h10_positions.csv",
                    receipt_dir=root / "receipts",
                    known_as_of=KNOWN_AS_OF,
                )

        self.assertEqual(rc, 2)
        self.assertEqual(calls, [])
        self.assertIn("future", stdout.getvalue().lower())
        self.assertFalse((root / "receipts").exists())


if __name__ == "__main__":
    unittest.main()
