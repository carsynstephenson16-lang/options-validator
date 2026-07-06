"""tests/test_earnings_loader.py"""
import os
import tempfile
import unittest
from datetime import date
from unittest import mock

from options_researcher import earnings

GOOD = "date,when,source_url\n2024-02-01,amc,https://example.com/a\n2024-04-30,amc,https://example.com/b\n"


class EarningsLoaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.object(earnings, "EARNINGS_DIR", self.tmp.name)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, symbol, text):
        with open(os.path.join(self.tmp.name, f"{symbol}.csv"), "w") as f:
            f.write(text)

    def test_loads_sorted_dates(self):
        self.write("AMZN", GOOD)
        self.assertEqual(earnings.load_earnings("AMZN"),
                         [date(2024, 2, 1), date(2024, 4, 30)])

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            earnings.load_earnings("MSFT")

    def test_bad_header_raises(self):
        self.write("VST", "day,when,url\n2024-02-01,amc,https://x\n")
        with self.assertRaises(ValueError):
            earnings.load_earnings("VST")

    def test_unsorted_or_duplicate_dates_raise(self):
        self.write("CEG", "date,when,source_url\n2024-05-01,bmo,https://x\n2024-02-01,bmo,https://y\n")
        with self.assertRaises(ValueError):
            earnings.load_earnings("CEG")

    def test_missing_source_url_raises(self):
        self.write("VST", "date,when,source_url\n2024-02-01,amc,\n")
        with self.assertRaises(ValueError):
            earnings.load_earnings("VST")


if __name__ == "__main__":
    unittest.main()
