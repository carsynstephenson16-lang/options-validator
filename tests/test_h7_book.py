"""H7 paper-book accounting. NO-GO remediation: book errors fail CLOSED
(H7BookError, no entries) and the monthly sleeve is DURABLE -- a position
opened and closed in the same month still consumed its at-risk."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from options_researcher.h7_watch import H7BookError, open_h7_book

HEADER = "symbol,lane,opened,at_risk,closed\n"


def _book(tmp, text):
    p = Path(tmp) / "h7_positions.csv"
    p.write_text(text)
    return p


class TestOpenH7Book(unittest.TestCase):
    def test_empty_book(self):
        with tempfile.TemporaryDirectory() as tmp:
            syms, open_c, spent = open_h7_book(date(2026, 7, 10),
                                               path=_book(tmp, HEADER))
        self.assertEqual(syms, ())
        self.assertEqual(open_c, 0)
        self.assertEqual(spent, 0.0)

    def test_open_rows_count_everywhere(self):
        text = HEADER + "NVDA,a,2026-07-02,900,\nCRWV,c,2026-07-06,450,\n"
        with tempfile.TemporaryDirectory() as tmp:
            syms, open_c, spent = open_h7_book(date(2026, 7, 10),
                                               path=_book(tmp, text))
        self.assertEqual(sorted(syms), ["CRWV", "NVDA"])
        self.assertEqual(open_c, 1)          # one lane-c row open
        self.assertAlmostEqual(spent, 1350.0)

    def test_closed_same_month_still_consumes_the_sleeve(self):
        text = HEADER + "NVDA,a,2026-07-02,900,2026-07-08\n"
        with tempfile.TemporaryDirectory() as tmp:
            syms, open_c, spent = open_h7_book(date(2026, 7, 10),
                                               path=_book(tmp, text))
        self.assertEqual(syms, ())           # not open: no one-per-underlying block
        self.assertEqual(open_c, 0)
        self.assertAlmostEqual(spent, 900.0)  # DURABLE: budget does not resurrect

    def test_prior_month_rows_do_not_count_against_this_month(self):
        text = HEADER + "PLTR,b,2026-06-15,800,2026-06-30\n"
        with tempfile.TemporaryDirectory() as tmp:
            _, _, spent = open_h7_book(date(2026, 7, 10), path=_book(tmp, text))
        self.assertAlmostEqual(spent, 0.0)

    def test_missing_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(H7BookError):
                open_h7_book(date(2026, 7, 10),
                             path=Path(tmp) / "nope.csv")

    def test_malformed_at_risk_fails_closed(self):
        text = HEADER + "NVDA,a,2026-07-02,not-a-number,\n"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(H7BookError):
                open_h7_book(date(2026, 7, 10), path=_book(tmp, text))

    def test_wrong_header_fails_closed(self):
        text = "symbol,lane,opened,at_risk\nNVDA,a,2026-07-02,900\n"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(H7BookError):
                open_h7_book(date(2026, 7, 10), path=_book(tmp, text))
