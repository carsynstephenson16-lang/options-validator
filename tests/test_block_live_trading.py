"""Tests for the block_live_trading PreToolUse guard hook.

The hook (.agents/hooks/block_live_trading.py) is the validator's first line:
any tool call whose command or written content looks like live order
placement, a live broker endpoint, or a paper-mode flip is blocked.

Contract (mirrors block_ledger_edits.py): exit 2 + "BLOCKED" on stderr to
block; exit 0 to allow; fail-closed (exit 2) on unparseable input. Specified
by docs/superpowers/plans/2026-07-23-integrity-hardening-batch-v1-codex-brief.md
and the 2026-08-11 core-plugin design; the hook body was laptop-only until
2026-09-15, so these tests land with its first tracked copy.

The trigger strings are assembled at runtime (`_s`) so that this file's own
text never contains them: the hook guards Write/Edit of this very file, and a
literal fixture would be blocked by the thing it tests.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / ".agents" / "hooks" / "block_live_trading.py"


def _s(*parts: str) -> str:
    """Join fragments at runtime so the trigger never appears in source."""
    return "".join(parts)


def run_hook(payload) -> subprocess.CompletedProcess:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=raw,
        capture_output=True,
        text=True,
        timeout=15,
    )


def bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def write(file_path: str, content: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": file_path, "content": content}}


def edit(file_path: str, new_string: str) -> dict:
    return {
        "tool_name": "Edit",
        "tool_input": {"file_path": file_path, "old_string": "x", "new_string": new_string},
    }


class TestHookExists(unittest.TestCase):
    def test_hook_script_exists(self):
        self.assertTrue(HOOK.exists(), f"guard hook missing at {HOOK}")


class TestBlocked(unittest.TestCase):
    def assert_blocked(self, payload):
        proc = run_hook(payload)
        self.assertEqual(proc.returncode, 2, f"allowed: {payload!r}\n{proc.stderr}")
        self.assertIn("BLOCKED", proc.stderr)

    def test_order_placement_call_in_command(self):
        self.assert_blocked(bash(_s("uv run python -c 'client.place", "_order(o)'")))

    def test_order_submission_in_written_content(self):
        self.assert_blocked(
            write("strategies/x.py", _s("def go():\n    broker.submit", "_order(o)\n"))
        )

    def test_broker_buy_in_edit(self):
        self.assert_blocked(edit("strategies/x.py", _s("broker.", "buy('VST', 1)")))

    def test_paper_mode_flip_any_case(self):
        self.assert_blocked(write("config.py", _s("paper_mode", " = False\n")))
        self.assert_blocked(write("config.py", _s("PAPER", " = false\n")))

    def test_live_flag_true(self):
        self.assert_blocked(bash(_s("python run.py --set live", "=true")))

    def test_broker_library_names(self):
        self.assert_blocked(write("x.py", _s("import ib_", "insync\n")))
        self.assert_blocked(bash(_s("python -c 'import trade", "api'")))
        self.assert_blocked(write("x.py", _s("schwab_client.send_", "trade(o)\n")))


class TestAllowed(unittest.TestCase):
    def assert_allowed(self, payload):
        proc = run_hook(payload)
        self.assertEqual(proc.returncode, 0, f"blocked: {payload!r}\n{proc.stderr}")

    def test_unittest_suite(self):
        self.assert_allowed(bash("uv run python -m unittest discover -s tests"))

    def test_ordinary_edit(self):
        self.assert_allowed(edit("options_researcher/h7_watch.py", "return evaluation_session(on)"))

    def test_words_that_merely_resemble_order_code(self):
        self.assert_allowed(write("docs/x.md", "the placeholder ordering of the table\n"))

    def test_read_only_git(self):
        self.assert_allowed(bash("git -C ~/options-validator-ops rev-parse origin/main"))


class TestFailClosed(unittest.TestCase):
    def test_garbage_stdin_blocks(self):
        proc = run_hook("this is not json{{{")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("BLOCKED", proc.stderr)

    def test_empty_tool_input_allows(self):
        proc = run_hook({"tool_name": "Bash", "tool_input": {}})
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
