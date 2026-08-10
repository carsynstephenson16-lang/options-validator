"""Program-level isolation tests for display-only experiment wiring."""

from __future__ import annotations

import ast
import importlib.util
import json
import os
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
    def _run_mocked_main(self, output: Path) -> None:
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

    def test_default_path_never_invokes_experiment_builders(self):
        fail = AssertionError("experiment builder invoked on default path")
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "attractiveness.html"
            with (
                mock.patch(
                    "options_researcher.exp_beta_qqq.build_exp_beta_board",
                    side_effect=fail,
                ),
                mock.patch(
                    "options_researcher.exp_tail_shape.build_exp_tail_board",
                    side_effect=fail,
                ),
                mock.patch(
                    "options_researcher.exp_spread_stability.build_exp_spread_board",
                    side_effect=fail,
                ),
                mock.patch(
                    "options_researcher.exp_tbill_carry.build_exp_tbill_board",
                    side_effect=fail,
                ),
            ):
                self._run_mocked_main(output)

            self.assertTrue(output.is_file())

    def test_default_path_html_has_zero_experiment_markers(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "attractiveness.html"
            self._run_mocked_main(output)

            html = output.read_text()
            self.assertEqual(html.lower().count("experiment"), 0)
            self.assertNotIn("Experiments — display-only", html)

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
            self._run_mocked_main(output)

            self.assertNotIn("Experiments — display-only", output.read_text())

    def test_module_entry_no_args_matches_production_command(self):
        repo_root = Path(__file__).resolve().parents[1]
        output = repo_root / ".tmp" / "dashboard" / "attractiveness.html"
        original = output.read_bytes() if output.exists() else None

        def restore_output() -> None:
            if original is None:
                output.unlink(missing_ok=True)
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(original)

        self.addCleanup(restore_output)
        env = {**os.environ, "ATTRACTIVENESS_INPUT_ROOT": str(repo_root)}

        without_experiments = subprocess.run(
            [sys.executable, "-m", "options_researcher.attractiveness_dashboard"],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            without_experiments.returncode,
            0,
            without_experiments.stdout + without_experiments.stderr,
        )
        self.assertIn("wrote ", without_experiments.stdout)
        baseline_html = output.read_text()
        self.assertEqual(baseline_html.lower().count("experiment"), 0)

        with_experiments = subprocess.run(
            [
                sys.executable,
                "-m",
                "options_researcher.attractiveness_dashboard",
                "--experiments",
            ],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            with_experiments.returncode,
            0,
            with_experiments.stdout + with_experiments.stderr,
        )
        self.assertIn("wrote ", with_experiments.stdout)
        self.assertIn("Experiments — display-only", output.read_text())

    def test_config_matches_every_module_frozen_default(self):
        source_names_by_module = {}
        for module_name in _EXPERIMENT_DEFAULTS:
            spec = importlib.util.find_spec(module_name)
            self.assertIsNotNone(spec)
            self.assertIsNotNone(spec.origin)
            tree = ast.parse(Path(spec.origin).read_text())
            names = {
                node.args[1].value
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "getattr"
                and len(node.args) >= 3
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "config"
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
                and node.args[1].value.startswith("EXP_")
            }
            source_names_by_module[module_name] = names

        config_names = {
            name
            for name in dir(config)
            if name.startswith("EXP_") and name != "EXPERIMENT_LANES_ENABLED"
        }
        source_names = set().union(*source_names_by_module.values())
        self.assertEqual(source_names, config_names)

        expected_json = {
            module: {
                name: list(value) if isinstance(value, tuple) else value
                for name, value in values.items()
            }
            for module, values in _EXPERIMENT_DEFAULTS.items()
        }
        names_json = {
            module: sorted(names) for module, names in source_names_by_module.items()
        }
        script = f"""
import importlib
import json
import config

names_by_module = {names_json!r}
for names in names_by_module.values():
    for name in names:
        if hasattr(config, name):
            delattr(config, name)

observed = {{}}
for module_name, names in names_by_module.items():
    module = importlib.import_module(module_name)
    observed[module_name] = {{
        name: list(getattr(module, name)) if isinstance(getattr(module, name), tuple)
        else getattr(module, name)
        for name in names
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
        for module_name, values in module_defaults.items():
            for name, expected in values.items():
                actual = getattr(config, name)
                self.assertEqual(list(actual) if isinstance(actual, tuple) else actual, expected)


class ExperimentDashboardTests(unittest.TestCase):
    def test_experiment_badge_classes_reflect_state(self):
        cards = [
            {
                "symbol": "MSFT",
                "state": "OK",
                "data_blocked": False,
                "max_asof": "2026-08-03",
            },
            {
                "symbol": "CEG",
                "state": "DATA_BLOCKED",
                "data_blocked": True,
                "reason": "missing cached data",
                "max_asof": "2026-08-03",
            },
            {
                "symbol": "VST",
                "state": "UNSTABLE",
                "data_blocked": False,
                "max_asof": "2026-08-03",
            },
        ]

        lane_html = dashboard._experiment_lane_html(cards, "EXP-BETA")
        healthy_html = dashboard._experiment_health_html({"exp_beta": [cards[0]]})
        blocked_html = dashboard._experiment_health_html({"exp_beta": [cards[1]]})

        self.assertIn('class="status-badge good">OK</span>', lane_html)
        self.assertIn('class="status-badge bad">DATA_BLOCKED</span>', lane_html)
        self.assertIn('class="status-badge unknown">UNSTABLE</span>', lane_html)
        self.assertIn('class="status-badge good">ENABLED FOR THIS RENDER</span>', healthy_html)
        self.assertIn('class="status-badge bad">ENABLED FOR THIS RENDER</span>', blocked_html)

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

    def test_tbill_line_exposes_unknown_assignment_reason(self):
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
                "reason": "SOME_FUTURE_REASON",
            },
            "caveat": "Display-only comparison.",
        }

        line = dashboard._experiment_card_line(card)

        self.assertIn("Early-assignment risk caveat: SOME_FUTURE_REASON.", line)


if __name__ == "__main__":
    unittest.main()
