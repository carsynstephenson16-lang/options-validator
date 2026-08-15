"""Contract tests for the independent display-only research refresh wrapper."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class ResearchDisplayRefreshTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.wrapper = self.repo_root / "tools" / "research_display_refresh.sh"
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.temp_root = Path(temp_dir.name)
        self.dashboard_dir = self.temp_root / "dashboard"
        self.call_log = self.temp_root / "fake-python.log"
        self.fake_python = self.temp_root / "fake-python"
        self.fake_python.write_text(
            "#!/bin/zsh\n"
            'print -r -- "$@" >> "$FAKE_PYTHON_LOG"\n'
            'if [[ "${FAKE_FAIL_MODULE:-}" == "$2" ]]; then\n'
            "  exit 17\n"
            "fi\n"
        )
        self.fake_python.chmod(0o755)

    def _run_wrapper(self, *, fail_module: str | None = None) -> subprocess.CompletedProcess[str]:
        env = {
            **os.environ,
            "RESEARCH_DISPLAY_PYTHON": str(self.fake_python),
            "RESEARCH_DISPLAY_DASHBOARD_DIR": str(self.dashboard_dir),
            "FAKE_PYTHON_LOG": str(self.call_log),
        }
        if fail_module is not None:
            env["FAKE_FAIL_MODULE"] = fail_module
        return subprocess.run(
            ["/bin/zsh", str(self.wrapper)],
            cwd=self.repo_root,
            env=env,
            capture_output=True,
            text=True,
        )

    def _calls(self) -> list[str]:
        return self.call_log.read_text().splitlines()

    def _status(self) -> str:
        return (self.dashboard_dir / "research-views-status.txt").read_text()

    def test_runs_both_builders_in_order_with_regime_dashboard_output(self) -> None:
        result = self._run_wrapper()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self._calls(),
            [
                "-m options_researcher.experiments_dashboard",
                "-m options_researcher.regime_report "
                f"--out {self.dashboard_dir}/wasserstein-regime.txt",
            ],
        )

    def test_records_experiments_failure_after_running_wasserstein_without_overwriting_outputs(
        self,
    ) -> None:
        self.dashboard_dir.mkdir(parents=True)
        experiments = self.dashboard_dir / "experiments.html"
        wasserstein = self.dashboard_dir / "wasserstein-regime.txt"
        experiments.write_text("experiments sentinel")
        wasserstein.write_text("wasserstein sentinel")

        result = self._run_wrapper(fail_module="options_researcher.experiments_dashboard")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(self._calls()), 2)
        self.assertIn("-m options_researcher.regime_report", self._calls()[1])
        self.assertIn("experiments: FAILED exit=17", self._status())
        self.assertIn("wasserstein: OK exit=0", self._status())
        self.assertEqual(experiments.read_text(), "experiments sentinel")
        self.assertEqual(wasserstein.read_text(), "wasserstein sentinel")

    def test_records_wasserstein_failure_after_running_experiments(self) -> None:
        result = self._run_wrapper(fail_module="options_researcher.regime_report")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(self._calls()), 2)
        self.assertIn("-m options_researcher.experiments_dashboard", self._calls()[0])
        self.assertIn("experiments: OK exit=0", self._status())
        self.assertIn("wasserstein: FAILED exit=17", self._status())

    def test_records_successes_atomically_without_leaving_a_temp_status_file(self) -> None:
        result = self._run_wrapper()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("research views refresh: ", self._status())
        self.assertIn("experiments: OK exit=0", self._status())
        self.assertIn("wasserstein: OK exit=0", self._status())
        self.assertEqual(
            list(self.dashboard_dir.glob("research-views-status.txt.*.tmp")),
            [],
        )


if __name__ == "__main__":
    unittest.main()
