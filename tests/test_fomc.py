"""tests/test_fomc.py"""
import tempfile
import unittest
from datetime import date
from unittest import mock

from options_researcher import fomc


class LoadFomcTests(unittest.TestCase):
    def test_real_file_loads_and_is_strictly_increasing(self):
        dates = fomc.load_fomc()
        self.assertGreaterEqual(len(dates), 8)
        self.assertTrue(all(isinstance(d, date) for d in dates))
        self.assertTrue(all(a < b for a, b in zip(dates, dates[1:])))
        self.assertTrue(all(d.weekday() < 5 for d in dates))

    def test_malformed_header_refused(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv",
                                         delete=False) as f:
            f.write("day,url\n2026-01-28,https://x\n")
        with mock.patch.object(fomc, "FOMC_PATH", f.name):
            with self.assertRaises(ValueError):
                fomc.load_fomc()

    def test_empty_source_url_refused(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv",
                                         delete=False) as f:
            f.write("date,source_url\n2026-01-28,\n")
        with mock.patch.object(fomc, "FOMC_PATH", f.name):
            with self.assertRaises(ValueError):
                fomc.load_fomc()

    def test_non_increasing_refused(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv",
                                         delete=False) as f:
            f.write("date,source_url\n2026-03-18,https://x\n"
                    "2026-01-28,https://x\n")
        with mock.patch.object(fomc, "FOMC_PATH", f.name):
            with self.assertRaises(ValueError):
                fomc.load_fomc()


if __name__ == "__main__":
    unittest.main()
