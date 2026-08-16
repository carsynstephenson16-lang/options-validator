"""Program-level isolation tests for display-only experiment wiring."""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

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


def _experiment_boundary_violations(source: str) -> list[str]:
    """Return prohibited experiment imports or resolved calls in Python source."""
    tree = ast.parse(source)
    aliases: dict[str, str] = {}
    violations: list[str] = []

    def prohibited(path: str) -> bool:
        return (
            path.startswith("options_researcher.exp_")
            or path == "options_researcher.experiments_dashboard"
            or path.startswith("options_researcher.experiments_dashboard.")
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for imported in node.names:
                local = imported.asname or imported.name.split(".")[0]
                aliases[local] = imported.name
                if prohibited(imported.name):
                    violations.append(f"import {imported.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if prohibited(module):
                violations.append(f"from {module}")
            for imported in node.names:
                target = f"{module}.{imported.name}" if module else imported.name
                aliases[imported.asname or imported.name] = target
                if prohibited(target):
                    violations.append(f"from {target}")

    def resolved_name(node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            parent = resolved_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        return ""

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            called = resolved_name(node.func)
            if prohibited(called):
                violations.append(f"call {called}")
    return violations


class ExperimentBaselineTests(unittest.TestCase):
    def test_production_dashboard_has_no_experiment_imports(self):
        self.assertFalse(_experiment_boundary_violations(Path(dashboard.__file__).read_text()))

    def test_boundary_rejects_direct_from_and_aliased_experiment_forms(self):
        fixtures = (
            "import options_researcher.exp_tbill_carry",
            "from options_researcher import exp_tbill_carry\nexp_tbill_carry.main()",
            "from options_researcher.exp_tbill_carry import main as build\nbuild()",
            "import options_researcher.experiments_dashboard as desk\ndesk.main()",
            "import options_researcher as research\nresearch.exp_beta_qqq.build()",
        )
        for source in fixtures:
            with self.subTest(source=source):
                self.assertTrue(_experiment_boundary_violations(source))

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
        self.assertIn("EXPERIMENTS SHELF", baseline_html)

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
            if name.startswith("EXP_")
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

if __name__ == "__main__":
    unittest.main()
