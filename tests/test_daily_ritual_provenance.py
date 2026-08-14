"""Offline contract tests for the ritual's cache/provenance dependency gate."""

import hashlib
import shutil
import subprocess
import unittest
from pathlib import Path

RITUAL = Path(__file__).resolve().parents[1] / "tools" / "daily_ritual.sh"


class DailyRitualProvenanceTests(unittest.TestCase):
    @staticmethod
    def _tree_identity(path: Path) -> tuple:
        if not path.exists():
            return ("missing",)
        if path.is_file():
            return ("file", hashlib.sha256(path.read_bytes()).hexdigest())
        return (
            "directory",
            tuple(
                (str(item.relative_to(path)), hashlib.sha256(item.read_bytes()).hexdigest())
                for item in sorted(path.rglob("*"))
                if item.is_file()
            ),
        )

    def test_authority_preflight_precedes_every_mutation_surface(self):
        source = RITUAL.read_text()
        marker = '"$PYTHON" -m data.ritual_authority require-full'
        self.assertIn(marker, source)
        preflight = source.index(marker)
        for token in (
            'mkdir -p "$LOGDIR"',
            "--status RUNNING",
            "options_researcher.h7_exit_session fill",
            "options_researcher.h10_observe",
            "git add --",
            "restic backup",
        ):
            with self.subTest(token=token):
                self.assertLess(preflight, source.index(token))

    def test_ritual_contains_no_provider_acquisition_or_key_preflight(self):
        source = RITUAL.read_text()
        self.assertNotIn("_resolve_api_key", source)
        self.assertNotIn("data/recent_topup.py", source)

    def test_status_mode_is_read_only_and_bypasses_full_authority_requirement(self):
        source = RITUAL.read_text()
        status = source.index('if [ "$RITUAL_MODE" = "status" ]; then')
        require_full = source.index("data.ritual_authority require-full")
        self.assertLess(status, require_full)
        self.assertIn("data.ritual_authority status", source)

    def test_authority_commands_use_installed_python_without_uv_sync(self):
        source = RITUAL.read_text()
        status = source.index("data.ritual_authority status")
        require_full = source.index("data.ritual_authority require-full")
        self.assertIn('PYTHON="$REPO/.venv/bin/python"', source)
        self.assertIn('PYTHONDONTWRITEBYTECODE=1 "$PYTHON"', source)
        self.assertNotIn('$UV" run python -m data.ritual_authority', source)
        self.assertLess(status, require_full)

    def test_status_preserves_log_tree_and_lockfile_bytes(self):
        zsh = shutil.which("zsh")
        if zsh is None:
            self.skipTest("zsh is required")
        repo = RITUAL.parents[1]
        guarded = (repo / ".tmp" / "daily_ritual", repo / "uv.lock")
        before = tuple(self._tree_identity(path) for path in guarded)
        result = subprocess.run(
            [zsh, str(RITUAL), "status"],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        after = tuple(self._tree_identity(path) for path in guarded)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"ready": false', result.stdout)
        self.assertEqual(after, before)

    def test_ops_publisher_requires_current_main(self):
        source = RITUAL.read_text()
        branch_guard = source.index('if [ "$RITUAL_BRANCH" != "main" ]')
        current_main_guard = source.index("rev-parse origin/main 2>/dev/null")
        publisher_role = source.index("export OPTIONS_VALIDATOR_CACHE_ROLE=publisher")
        source_health = source.index("options_researcher.h7_source_health")
        self.assertLess(branch_guard, current_main_guard)
        self.assertLess(current_main_guard, publisher_role)
        self.assertLess(publisher_role, source_health)

    def test_authority_gate_replaces_provider_topup_dependency(self):
        source = RITUAL.read_text()
        authority = source.index("data.ritual_authority require-full")
        source_health = source.index("options_researcher.h7_source_health")
        data_gate = source.index("options_researcher.h7_data_gate")
        self.assertLess(authority, source_health)
        self.assertLess(source_health, data_gate)
        self.assertNotIn("H7_DATA_READY", source)

    def test_h6_and_h8_nonzero_results_are_critical(self):
        source = RITUAL.read_text()
        self.assertIn('crit "h6_features: NONZERO EXIT"', source)
        self.assertIn('crit "h6_watch: NONZERO EXIT"', source)
        self.assertIn('crit "h8_watch: NONZERO EXIT"', source)

    def test_h5_rerun_failure_is_critical_before_terminal_publish(self):
        source = RITUAL.read_text()
        failure = 'crit "h5 entry watch: NONZERO EXIT"'
        terminal = source.index('if [ "$CRITICAL" -eq 1 ]; then')
        self.assertIn(failure, source)
        self.assertLess(source.index(failure), terminal)
        self.assertNotIn('note "WARNING: h5 entry watch failed to run"', source)

    def test_h10_rerun_failures_are_critical_before_terminal_publish(self):
        source = RITUAL.read_text()
        terminal = source.index('if [ "$CRITICAL" -eq 1 ]; then')
        failures = (
            'crit "h10_watch: NONZERO EXIT"',
            'crit "h10_observe: NONZERO EXIT"',
            'crit "h10_watch: module unavailable"',
        )
        for failure in failures:
            with self.subTest(failure=failure):
                self.assertIn(failure, source)
                self.assertLess(source.index(failure), terminal)
        self.assertNotIn('note "h10_watch: NONZERO EXIT"', source)
        self.assertNotIn('note "h10_observe: NONZERO EXIT"', source)

    def test_ritual_terminal_status_is_separate_from_capture_receipt(self):
        source = RITUAL.read_text()
        running = source.index("--status RUNNING")
        capture = source.index('"$UV" run python -m options_researcher.ritual_receipt')
        terminal = source.index('--status "$RITUAL_TERMINAL_STATUS"')
        durability = source.index("# Step 8 — DURABILITY")
        self.assertLess(running, capture)
        self.assertLess(capture, terminal)
        self.assertLess(terminal, durability)
        self.assertIn('RITUAL_TERMINAL_STATUS="BROKEN"', source)
        self.assertIn('RITUAL_TERMINAL_STATUS="OK"', source)

    def test_durability_allow_list_includes_schwab_ledger_and_reports(self):
        source = RITUAL.read_text()
        git_add = source.index("git add --")
        allow_list_end = source.index("2>/dev/null", git_add)
        allow_list = source[git_add:allow_list_end]

        self.assertIn("ledger/h7_forward_schwab", allow_list)
        self.assertIn("reports/schwab_chains", allow_list)


if __name__ == "__main__":
    unittest.main()
