"""Program-level isolation tests for display-only experiment wiring."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import config
from options_researcher import attractiveness_dashboard as dashboard

_EXPERIMENT_DEFAULTS = {
    "options_researcher.exp_beta_qqq": {
        "EXP_BETA_WINDOW": 252,
        "EXP_BETA_HALF_WINDOW": 126,
        "EXP_BETA_MIN_OBS": 126,
        "EXP_BETA_UNSTABLE_DELTA": 0.5,
    },
    "options_researcher.exp_tail_shape": {
        "EXP_TAIL_WINDOW": 252,
        "EXP_TAIL_MIN_OBS": 250,
        "EXP_TAIL_JUMP_SIGMA": 3.0,
        "EXP_TAIL_ALT_WINDOWS": (189, 378),
    },
    "options_researcher.exp_spread_stability": {
        "EXP_SPREAD_BASELINE": 20,
        "EXP_SPREAD_MIN_BASELINE_OBS": 10,
        "EXP_SPREAD_LOOKBACK_SESSIONS": 25,
        "EXP_SPREAD_ELEVATED": 2.0,
        "EXP_SPREAD_TENOR_DTE": (15, 60),
        "EXP_SPREAD_TARGET_DELTA": 0.5,
    },
    "options_researcher.exp_tbill_carry": {
        "EXP_TBILL_TENOR_DTE": (15, 60),
        "EXP_TBILL_TARGET_DELTA": 0.5,
    },
}


def _section() -> dict:
    return {
        "symbol": "MSFT",
        "as_of": "2026-07-24",
        "close": 373.02,
        "iv_rank": 0.88,
        "groups": [
            {
                "kind": "put",
                "title": "SELL A PUT?",
                "cards": [],
                "empty": "none this cycle",
            }
        ],
    }


class ExperimentBaselineTests(unittest.TestCase):
    def test_all_lanes_off_is_byte_identical_to_omitting_experiment_keywords(self):
        baseline = dashboard.render(
            dashboard.assemble(
                symbol_sections=[_section()],
                rv21_by_symbol={"MSFT": 1.1},
                composite_signals=[],
            )
        )
        explicitly_off = dashboard.render(
            dashboard.assemble(
                symbol_sections=[_section()],
                rv21_by_symbol={"MSFT": 1.1},
                composite_signals=[],
                exp_beta=None,
                exp_tail=None,
                exp_spread=None,
                exp_tbill=None,
            )
        )
        self.assertEqual(explicitly_off.encode(), baseline.encode())

    def test_experiment_lane_flags_default_false(self):
        self.assertEqual(
            config.EXPERIMENT_LANES_ENABLED,
            {
                "EXP-BETA": False,
                "EXP-TAIL": False,
                "EXP-SPREAD": False,
                "EXP-TBILL": False,
            },
        )

    def test_main_no_args_keeps_experiments_out_of_production_entry_point(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "attractiveness.html"
            with (
                mock.patch.object(dashboard, "_gather_all", return_value=([_section()], {}, [])),
                mock.patch.object(dashboard, "OUTPUT_PATH", str(output)),
                mock.patch.object(dashboard, "load_context", return_value=(None, None)),
                mock.patch(
                    "options_researcher.hypothesis_evidence.gather_hypothesis_evidence",
                    return_value={},
                ),
                mock.patch(
                    "options_researcher.composite_signals.build_board",
                    return_value=[],
                ),
                mock.patch(
                    "options_researcher.qm_dashboard.load_qm_context",
                    return_value={},
                ),
            ):
                dashboard.main()

            self.assertNotIn("Experiments — display-only", output.read_text())

    def test_config_matches_every_module_frozen_default(self):
        expected_json = {
            module: {
                name: list(value) if isinstance(value, tuple) else value
                for name, value in values.items()
            }
            for module, values in _EXPERIMENT_DEFAULTS.items()
        }
        script = f"""
import importlib
import json
import config

expected = {expected_json!r}
for values in expected.values():
    for name in values:
        if hasattr(config, name):
            delattr(config, name)

observed = {{}}
for module_name, values in expected.items():
    module = importlib.import_module(module_name)
    observed[module_name] = {{
        name: list(getattr(module, name)) if isinstance(getattr(module, name), tuple)
        else getattr(module, name)
        for name in values
    }}
print("EXPERIMENT_DEFAULTS=" + json.dumps(observed, sort_keys=True))
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            check=True,
            capture_output=True,
            text=True,
        )
        defaults_line = next(
            line for line in result.stdout.splitlines() if line.startswith("EXPERIMENT_DEFAULTS=")
        )
        module_defaults = json.loads(defaults_line.removeprefix("EXPERIMENT_DEFAULTS="))
        self.assertEqual(module_defaults, expected_json)
        for values in _EXPERIMENT_DEFAULTS.values():
            for name, expected in values.items():
                self.assertEqual(getattr(config, name), expected)


class ExperimentDashboardTests(unittest.TestCase):
    def test_renderer_includes_health_strip_honest_lines_and_limitations(self):
        data = dashboard.assemble(
            symbol_sections=[_section()],
            rv21_by_symbol={"MSFT": 1.1},
            composite_signals=[],
            exp_beta=[
                {
                    "symbol": "MSFT",
                    "experiment_id": "EXP-BETA",
                    "state": "OK",
                    "data_blocked": False,
                    "reason": None,
                    "max_asof": "2026-08-03",
                    "beta": 1.2,
                    "r_squared": 0.64,
                    "beta_half_window": 1.1,
                    "n_obs": 252,
                    "caveat": "Descriptive history, not a forecast.",
                }
            ],
            exp_tbill=[
                {
                    "symbol": "MSFT",
                    "experiment_id": "EXP-TBILL",
                    "state": "DATA_BLOCKED",
                    "data_blocked": True,
                    "reason": "no Treasury curve known by valuation close",
                    "max_asof": "2026-07-27",
                    "assignment": {
                        "state": "DATA_BLOCKED",
                        "reason": "EX_DIV_DATE_UNAVAILABLE",
                    },
                    "caveat": "Display-only comparison.",
                }
            ],
        )

        html = dashboard.render(data)

        self.assertIn("Experiments — display-only (not part of Top-3 ranking)", html)
        self.assertIn("1 / 1 names rendered", html)
        self.assertIn("0 / 1 names rendered", html)
        self.assertIn("beta 1.20", html)
        self.assertIn("no Treasury curve known by valuation close", html)
        self.assertIn("no ex-dividend-date data on disk yet", html)
        self.assertIn("constants are LLM-proposed and not owner-ratified", html)

    def test_cli_builds_only_enabled_lanes_unless_force_all(self):
        builders = {
            "beta": mock.Mock(return_value=[{"experiment_id": "EXP-BETA"}]),
            "tail": mock.Mock(return_value=[{"experiment_id": "EXP-TAIL"}]),
            "spread": mock.Mock(return_value=[{"experiment_id": "EXP-SPREAD"}]),
            "tbill": mock.Mock(return_value=[{"experiment_id": "EXP-TBILL"}]),
        }
        enabled = {
            "EXP-BETA": True,
            "EXP-TAIL": False,
            "EXP-SPREAD": False,
            "EXP-TBILL": False,
        }
        with (
            mock.patch.object(config, "EXPERIMENT_LANES_ENABLED", enabled),
            mock.patch("options_researcher.exp_beta_qqq.build_exp_beta_board", builders["beta"]),
            mock.patch("options_researcher.exp_tail_shape.build_exp_tail_board", builders["tail"]),
            mock.patch(
                "options_researcher.exp_spread_stability.build_exp_spread_board",
                builders["spread"],
            ),
            mock.patch(
                "options_researcher.exp_tbill_carry.build_exp_tbill_board", builders["tbill"]
            ),
        ):
            selected = dashboard._cli_experiment_payloads(force_all=False, asof="2026-08-04")
            all_lanes = dashboard._cli_experiment_payloads(force_all=True, asof="2026-08-04")

        self.assertEqual(set(selected), {"exp_beta"})
        self.assertEqual(set(all_lanes), {"exp_beta", "exp_tail", "exp_spread", "exp_tbill"})

    def test_tbill_line_exposes_rate_provenance_and_fill_caveat(self):
        card = {
            "symbol": "MSFT",
            "experiment_id": "EXP-TBILL",
            "state": "ABOVE_TBILL",
            "data_blocked": False,
            "reason": None,
            "max_asof": "2026-07-27",
            "collateral": 18_400.0,
            "credit_annualized_yield": 0.07,
            "tbill_annualized_yield": 0.049,
            "carry_spread": 0.021,
            "rate_provenance": "treasury.gov capture 2026-07-27",
            "assignment": {
                "state": "DATA_BLOCKED",
                "reason": "EX_DIV_DATE_UNAVAILABLE",
            },
            "caveat": "Display-only comparison.",
        }

        line = dashboard._experiment_card_line(card)

        self.assertIn("treasury.gov capture 2026-07-27", line)
        self.assertIn("real fills are mid or worse", line)


if __name__ == "__main__":
    unittest.main()
