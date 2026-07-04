"""tests/test_refresh.py"""
import unittest

from options_researcher.refresh import run_refresh


class RefreshTests(unittest.TestCase):
    def test_runs_steps_in_order_and_reports(self):
        calls = []
        summary = run_refresh(steps=[
            ("chains", lambda: calls.append("chains") or {"fetched": 3}),
            ("closes", lambda: calls.append("closes") or {"rows_added": 5}),
            ("features", lambda: calls.append("features") or {"symbols": 4}),
        ])
        self.assertEqual(calls, ["chains", "closes", "features"])
        self.assertEqual(summary["chains"], {"fetched": 3})
        self.assertEqual(summary["closes"], {"rows_added": 5})

    def test_step_failure_stops_and_is_reported_loudly(self):
        def boom():
            raise RuntimeError("fetch died")
        with self.assertRaises(RuntimeError):
            run_refresh(steps=[("chains", boom),
                               ("closes", lambda: {"rows_added": 0})])
