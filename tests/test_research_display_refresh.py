"""Contract tests for the independent display-only research refresh wrapper."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from options_researcher.research_views_publication import load_current


@unittest.skipUnless(
    Path("/bin/zsh").is_file(),
    "requires /bin/zsh; research_display_refresh.sh is a macOS/zsh-only wrapper",
)
class ResearchDisplayRefreshTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.wrapper = self.repo_root / "tools" / "research_display_refresh.sh"
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.temp_root = Path(temporary.name)
        self.dashboard_dir = self.temp_root / "dashboard"
        self.call_log = self.temp_root / "fake-python.log"
        self.cwd_log = self.temp_root / "fake-python-cwd.log"
        self.fake_python = self.temp_root / "fake-python"
        self.fake_python.write_text(
            "#!/bin/zsh\n"
            'print -r -- "$@" >> "$FAKE_PYTHON_LOG"\n'
            'print -r -- "$PWD" >> "$FAKE_PYTHON_CWD_LOG"\n'
            'if [[ "$2" == "options_researcher.research_views_publication" ]]; then\n'
            '  exec "$REAL_PYTHON" "$@"\n'
            "fi\n"
            'module="$2"\n'
            "shift 2\n"
            'out=""\n'
            'json_out=""\n'
            "while [[ $# -gt 0 ]]; do\n"
            '  if [[ "$1" == "--out" ]]; then out="$2"; shift 2; continue; fi\n'
            '  if [[ "$1" == "--json-out" ]]; then json_out="$2"; shift 2; continue; fi\n'
            "  shift\n"
            "done\n"
            'mkdir -p "${out:h}"\n'
            'if [[ "$module" == "options_researcher.experiments_dashboard" ]]; then\n'
            '  print -r -- "experiments" > "$out"\n'
            "else\n"
            '  print -r -- "regime" > "$out"\n'
            '  print -r -- "{}" > "$json_out"\n'
            "fi\n"
            'if [[ "${FAKE_FAIL_MODULE:-}" == "$module" ]]; then exit 17; fi\n'
            "exit 0\n"
        )
        self.fake_python.chmod(0o755)

    def _run_wrapper(
        self, *, fail_module: str | None = None, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        env = {
            **os.environ,
            "RESEARCH_DISPLAY_PYTHON": str(self.fake_python),
            "RESEARCH_DISPLAY_DASHBOARD_DIR": str(self.dashboard_dir),
            "FAKE_PYTHON_LOG": str(self.call_log),
            "FAKE_PYTHON_CWD_LOG": str(self.cwd_log),
            "REAL_PYTHON": str(self.repo_root / ".venv" / "bin" / "python"),
        }
        if fail_module is not None:
            env["FAKE_FAIL_MODULE"] = fail_module
        return subprocess.run(
            ["/bin/zsh", str(self.wrapper)],
            cwd=self.repo_root if cwd is None else cwd,
            env=env,
            capture_output=True,
            text=True,
        )

    def _calls(self) -> list[str]:
        return self.call_log.read_text().splitlines()

    def test_success_publishes_one_immutable_generation_without_loose_aliases(self) -> None:
        result = self._run_wrapper()

        self.assertEqual(result.returncode, 0, result.stderr)
        loaded = load_current(self.dashboard_dir)
        self.assertEqual(loaded["state"], "published")
        self.assertEqual(
            set(path.name for path in loaded["generation_root"].iterdir()),
            {
                "experiments.html",
                "wasserstein-regime.txt",
                "wasserstein-regime.json",
                "research-views-status.txt",
                "research-views-manifest.json",
            },
        )
        for name in ("experiments.html", "wasserstein-regime.txt", "wasserstein-regime.json"):
            self.assertFalse((self.dashboard_dir / name).exists())
        self.assertFalse((self.dashboard_dir / "research-views-published.json").exists())

    def test_both_builders_receive_the_same_evaluation_date(self) -> None:
        result = self._run_wrapper()

        self.assertEqual(result.returncode, 0, result.stderr)
        builder_calls = [
            call for call in self._calls() if "_dashboard" in call or "regime_report" in call
        ]
        self.assertEqual(len(builder_calls), 2)
        dates = [call.split("--evaluation-date ", 1)[1].split()[0] for call in builder_calls]
        self.assertEqual(dates[0], dates[1])

    def test_builder_failure_runs_both_and_preserves_prior_current(self) -> None:
        self.assertEqual(self._run_wrapper().returncode, 0)
        pointer_before = (self.dashboard_dir / "research-views-current.json").read_bytes()
        generation_before = load_current(self.dashboard_dir)["generation_id"]
        self.call_log.write_text("")

        result = self._run_wrapper(fail_module="options_researcher.experiments_dashboard")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(
            (self.dashboard_dir / "research-views-current.json").read_bytes(), pointer_before
        )
        self.assertEqual(load_current(self.dashboard_dir)["generation_id"], generation_before)
        self.assertTrue(any("regime_report" in call for call in self._calls()))
        failure = json.loads((self.dashboard_dir / "research-views-last-failure.json").read_text())
        self.assertEqual((failure["experiments_exit"], failure["wasserstein_exit"]), (17, 0))
        self.assertEqual(
            list((self.dashboard_dir / "research-views-generations").glob(".staging-*")), []
        )

    def test_builders_run_from_repo_root_regardless_of_caller_cwd(self) -> None:
        result = self._run_wrapper(cwd=self.temp_root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(self.cwd_log.read_text().splitlines()), {str(self.repo_root)})


if __name__ == "__main__":
    unittest.main()
