"""Skip-and-log must stay narrow: unreadable cache files are skipped with a
warning, but unexpected error types must propagate instead of being
swallowed (a profiler that 'succeeds' on a broken run lies)."""
import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

from options_researcher import profile_monthlies, profile_tradability


def _touch_garbage(cache_dir, name):
    path = os.path.join(cache_dir, name)
    with open(path, "wb") as fh:
        fh.write(b"this is not a parquet file")
    return path


class TradabilityProfilerTests(unittest.TestCase):
    def test_corrupt_parquet_is_skipped_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            _touch_garbage(tmp, "VST_2024-01-02.parquet")
            err, out = io.StringIO(), io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                profile_tradability.profile_symbol("VST", tmp)
            self.assertIn("WARN unreadable cache file skipped", err.getvalue())

    def test_unexpected_error_type_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            _touch_garbage(tmp, "VST_2024-01-02.parquet")
            with mock.patch.object(profile_tradability.pd, "read_parquet",
                                   side_effect=TypeError("boom")):
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(TypeError):
                        profile_tradability.profile_symbol("VST", tmp)


class MonthliesProfilerTests(unittest.TestCase):
    def test_corrupt_parquet_is_skipped_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            _touch_garbage(tmp, "VST_2024-01-02.parquet")
            err, out = io.StringIO(), io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                with mock.patch.object(profile_monthlies, "CACHE_DIR", tmp):
                    profile_monthlies.profile_symbol("VST")
            self.assertIn("WARN unreadable cache file skipped", err.getvalue())

    def test_unexpected_error_type_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            _touch_garbage(tmp, "VST_2024-01-02.parquet")
            with mock.patch.object(profile_monthlies, "CACHE_DIR", tmp), \
                    mock.patch.object(profile_monthlies.pd, "read_parquet",
                                      side_effect=TypeError("boom")):
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(TypeError):
                        profile_monthlies.profile_symbol("VST")


if __name__ == "__main__":
    unittest.main()
