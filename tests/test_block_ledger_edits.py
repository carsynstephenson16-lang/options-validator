"""Tests for the block_ledger_edits PreToolUse guard hook.

The hook (.agents/hooks/block_ledger_edits.py) protects the append-only
ledger files that must only be written through their typed Python APIs:

- ledger/experiments.jsonl + ledger/HEAD  (research chain, research/ledger.py)
- ledger/facts.log                        (facts stream, research/facts.py)
- ledger/h7_forward/events.jsonl + HEAD   (H7 chain, h7_event_ledger.append_event;
                                           must not even be CREATED before Stage 8)

Contract (mirrors block_live_trading.py): exit 2 + "BLOCKED" on stderr to
block; exit 0 to allow; fail-closed (exit 2) on unparseable input. Reads of
the protected files are allowed; only writes/renames/deletes are blocked.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / ".agents" / "hooks" / "block_ledger_edits.py"


def run_hook(payload) -> subprocess.CompletedProcess:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=raw,
        capture_output=True,
        text=True,
        timeout=15,
    )


def edit(file_path: str) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": file_path}}


def write(file_path: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": file_path}}


def bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


class TestHookExists(unittest.TestCase):
    def test_hook_script_exists(self):
        self.assertTrue(HOOK.exists(), f"guard hook missing at {HOOK}")


class TestFileToolsBlocked(unittest.TestCase):
    """Edit/Write/NotebookEdit must never touch protected ledger files."""

    def assert_blocked(self, payload):
        proc = run_hook(payload)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("BLOCKED", proc.stderr)

    def test_edit_research_head(self):
        self.assert_blocked(edit("ledger/HEAD"))

    def test_edit_experiments_jsonl_absolute_path(self):
        self.assert_blocked(edit(str(REPO_ROOT / "ledger" / "experiments.jsonl")))

    def test_write_facts_log(self):
        self.assert_blocked(write("ledger/facts.log"))

    def test_write_h7_forward_events(self):
        # Stage 3: this file must not be created by any means but append_event().
        self.assert_blocked(write("ledger/h7_forward/events.jsonl"))

    def test_edit_h7_forward_head(self):
        self.assert_blocked(edit("ledger/h7_forward/HEAD"))

    def test_edit_with_redundant_path_segments(self):
        self.assert_blocked(edit("ledger/./HEAD"))

    def test_notebook_edit_under_ledger(self):
        self.assert_blocked(
            {
                "tool_name": "NotebookEdit",
                "tool_input": {"notebook_path": "ledger/experiments.jsonl"},
            }
        )


class TestFileToolsAllowed(unittest.TestCase):
    def assert_allowed(self, payload):
        proc = run_hook(payload)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_edit_ordinary_source_file(self):
        self.assert_allowed(edit("options_researcher/h7_watch.py"))

    def test_edit_ledger_readme(self):
        # READMEs in ledger/ are documentation, not chain files.
        self.assert_allowed(edit("ledger/README.md"))
        self.assert_allowed(edit("ledger/h7_forward/README.md"))

    def test_edit_file_merely_named_like_head(self):
        self.assert_allowed(edit("docs/ledger/HEADERS.md"))


class TestBashBlocked(unittest.TestCase):
    """Shell writes targeting protected paths are hand-edits; block them."""

    def assert_blocked(self, command: str):
        proc = run_hook(bash(command))
        self.assertEqual(proc.returncode, 2, f"allowed: {command!r}\n{proc.stderr}")
        self.assertIn("BLOCKED", proc.stderr)

    def test_append_redirect_to_facts_log(self):
        self.assert_blocked("echo 'note' >> ledger/facts.log")

    def test_truncate_redirect_to_head(self):
        self.assert_blocked("echo deadbeef > ledger/HEAD")

    def test_sed_in_place_on_experiments(self):
        self.assert_blocked("sed -i '' 's/fail/pass/' ledger/experiments.jsonl")

    def test_tee_append_to_facts_log(self):
        self.assert_blocked("echo x | tee -a ledger/facts.log")

    def test_rm_h7_forward_head(self):
        self.assert_blocked("rm ledger/h7_forward/HEAD")

    def test_touch_creates_h7_forward_events(self):
        self.assert_blocked("touch ledger/h7_forward/events.jsonl")

    def test_mv_over_experiments(self):
        self.assert_blocked("mv /tmp/fake.jsonl ledger/experiments.jsonl")

    def test_cp_over_head(self):
        self.assert_blocked("cp backup ledger/HEAD")


class TestBashAllowed(unittest.TestCase):
    """Reads, git plumbing, and the typed-API entry points stay usable."""

    def assert_allowed(self, command: str):
        proc = run_hook(bash(command))
        self.assertEqual(proc.returncode, 0, f"blocked: {command!r}\n{proc.stderr}")

    def test_cat_facts_log(self):
        self.assert_allowed("cat ledger/facts.log")

    def test_git_diff_head(self):
        self.assert_allowed("git diff ledger/HEAD")

    def test_grep_experiments(self):
        self.assert_allowed("grep trial ledger/experiments.jsonl | head -5")

    def test_h7_ledger_verify_cli(self):
        self.assert_allowed("uv run python -m options_researcher.h7_event_ledger verify")

    def test_research_ledger_api_invocation(self):
        self.assert_allowed("uv run python -m research.cli verify --anchored")

    def test_earnings_refresher(self):
        self.assert_allowed("uv run python tools/h7_refresh_earnings.py --help")

    def test_recent_topup_refresh_closes(self):
        # Legit writer of OTHER ledger/ files; never names the chain files.
        self.assert_allowed("uv run python data/recent_topup.py --scope h7 --refresh-closes")

    def test_unittest_suite(self):
        self.assert_allowed("uv run python -m unittest discover -s tests")


class TestFailClosed(unittest.TestCase):
    def test_garbage_stdin_blocks(self):
        proc = run_hook("this is not json{{{")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("BLOCKED", proc.stderr)

    def test_empty_tool_input_allows(self):
        # Parseable but empty input is not an attack; do not wedge the session.
        proc = run_hook({"tool_name": "Bash", "tool_input": {}})
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
