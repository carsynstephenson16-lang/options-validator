"""Tests for the separately refreshable display-only experiments artifact."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from options_researcher import experiments_dashboard as dashboard


def _card(experiment_id: str, symbol: str = "MSFT") -> dict:
    card = {
        "symbol": symbol,
        "experiment_id": experiment_id,
        "state": "OK",
        "data_blocked": False,
        "reason": None,
        "max_asof": "2026-08-03",
        "caveat": "Descriptive history, not a forecast.",
    }
    if experiment_id == "EXP-BETA":
        card.update(beta=1.2, r_squared=0.64, beta_half_window=1.1, n_obs=252)
    elif experiment_id == "EXP-TAIL":
        card.update(jump_count=2, skew=-0.2, excess_kurtosis=1.3)
    elif experiment_id == "EXP-SPREAD":
        card.update(ratio=1.1, baseline_sessions_used=20)
    elif experiment_id == "EXP-TBILL":
        card.update(
            collateral=18_400.0,
            credit_annualized_yield=0.07,
            tbill_annualized_yield=0.049,
            carry_spread=0.021,
            rate_provenance="treasury.gov capture 2026-07-27",
        )
    return card


class ExperimentsDashboardTests(unittest.TestCase):
    def test_module_entry_builds_all_lanes_with_empty_cache(self):
        repo_root = Path(__file__).resolve().parents[1]
        # Every cache path in this repo (.cache/underlying, .cache/chains,
        # .tmp/dashboard) is cwd-relative, so an empty scratch cwd is the
        # empty-cache contract regardless of the checkout's own .cache state
        # (the ops deployment symlinks a fully populated cache into place).
        scratch_ctx = tempfile.TemporaryDirectory()
        scratch = Path(scratch_ctx.name)
        self.addCleanup(scratch_ctx.cleanup)
        python_path = os.pathsep.join(
            [str(repo_root)] + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else [])
        )
        env = {
            **os.environ,
            "PYTHONPATH": python_path,
            "OPTIONS_CACHE_DIR": str(scratch / ".cache" / "chains"),
            "ATTRACTIVENESS_INPUT_ROOT": str(scratch),
        }
        result = subprocess.run(
            [sys.executable, "-m", "options_researcher.experiments_dashboard"],
            cwd=scratch,
            env=env,
            capture_output=True,
            text=True,
        )
        output = scratch / ".tmp" / "dashboard" / "experiments.html"

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("wrote ", result.stdout)
        html = output.read_text()
        for experiment_id in ("EXP-BETA", "EXP-TAIL", "EXP-SPREAD", "EXP-TBILL"):
            self.assertIn(experiment_id, html)
        self.assertGreaterEqual(html.count("max as-of"), 4)
        self.assertIn("DATA BLOCKED", html)
        self.assertIn(
            "display-only research experiments — not part of Top-5 ranking, no verdict authority",
            html,
        )

    def test_one_broken_lane_is_visible_without_blocking_other_lanes(self):
        with (
            mock.patch.object(
                dashboard,
                "build_exp_beta_board",
                side_effect=RuntimeError("synthetic beta failure <unsafe>"),
            ),
            mock.patch.object(
                dashboard,
                "build_exp_tail_board",
                return_value=[_card("EXP-TAIL")],
            ),
            mock.patch.object(
                dashboard,
                "build_exp_spread_board",
                return_value=[_card("EXP-SPREAD")],
            ),
            mock.patch.object(
                dashboard,
                "build_exp_tbill_board",
                return_value=[_card("EXP-TBILL")],
            ),
        ):
            data = dashboard.build_experiment_lanes(["MSFT"], asof="2026-08-10")

        html = dashboard.render(data, build_asof="2026-08-10")
        self.assertIn("ERROR", html)
        self.assertIn("RuntimeError", html)
        self.assertIn("synthetic beta failure &lt;unsafe&gt;", html)
        for experiment_id in ("EXP-TAIL", "EXP-SPREAD", "EXP-TBILL"):
            self.assertIn(experiment_id, html)

    def test_artifact_contains_status_css_without_production_stylesheet(self):
        data = {"exp_beta": [_card("EXP-BETA")]}
        html = dashboard.render(data, build_asof="2026-08-10")

        self.assertIn(".status-badge", html)
        self.assertIn('class="status-badge good"', html)
        self.assertNotIn("attractiveness.html", html)
        self.assertNotIn("<link", html.lower())

    def test_renderer_keeps_health_and_refusal_copy(self):
        blocked = {
            **_card("EXP-TBILL"),
            "state": "DATA_BLOCKED",
            "data_blocked": True,
            "reason": "no Treasury curve known by valuation close",
            "assignment": {
                "state": "DATA_BLOCKED",
                "reason": "EX_DIV_DATE_UNAVAILABLE",
            },
        }
        health = dashboard._experiment_health_html({"exp_tbill": [blocked]})
        line = dashboard._experiment_card_line(blocked)

        self.assertIn("0 / 1 names rendered", health)
        self.assertIn("no Treasury curve known by valuation close", health)
        self.assertIn("DATA BLOCKED as of 2026-08-03", line)
        self.assertIn("no ex-dividend-date data on disk yet", line)

    def test_main_accepts_explicit_staging_output_and_evaluation_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "generation" / "experiments.html"
            with mock.patch.object(
                dashboard,
                "build_experiment_lanes",
                return_value={"exp_beta": [_card("EXP-BETA")]},
            ) as build:
                exit_code = dashboard.main(
                    ["--out", str(output), "--evaluation-date", "2026-08-10"]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output.is_file())
            build.assert_called_once_with(
                list(dashboard.config.ATTRACTIVENESS_UNIVERSE), asof="2026-08-10"
            )


if __name__ == "__main__":
    unittest.main()
