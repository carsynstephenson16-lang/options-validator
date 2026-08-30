"""Offline authorization contract for the optional Claude review workflow."""

import re
import unittest
from pathlib import Path

WORKFLOW_PATH = Path(__file__).parents[1] / ".github/workflows/claude-review.yml"
EXPECTED_REVIEW_CONDITION = (
    "(github.event_name == 'pull_request' && "
    "github.event.pull_request.draft == false) || "
    "(github.event_name == 'issue_comment' && "
    "github.event.issue.pull_request != null && "
    "contains(github.event.comment.body, '@claude') && "
    "(github.event.comment.author_association == 'OWNER' || "
    "github.event.comment.author_association == 'MEMBER' || "
    "github.event.comment.author_association == 'COLLABORATOR')) || "
    "(github.event_name == 'pull_request_review_comment' && "
    "contains(github.event.comment.body, '@claude') && "
    "(github.event.comment.author_association == 'OWNER' || "
    "github.event.comment.author_association == 'MEMBER' || "
    "github.event.comment.author_association == 'COLLABORATOR'))"
)
EXPECTED_TRIGGER_BLOCK = """on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]"""
EXPECTED_PERMISSIONS_BLOCK = """permissions:
  contents: read
  pull-requests: write
  issues: write
  id-token: write"""
AUTH_ENABLED_GUARD = "if: steps.auth.outputs.enabled == 'true'"


def _assert_exact_review_condition(condition: str) -> None:
    actual = " ".join(condition.split())
    if actual != EXPECTED_REVIEW_CONDITION:
        raise AssertionError(
            f"review condition must exactly match its authorization contract: {actual!r}"
        )


def _normalize_yaml_block(block: str) -> str:
    semantic_lines = [
        f"{line[: len(line) - len(line.lstrip())]}{' '.join(line.split())}"
        for line in block.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return "\n".join(semantic_lines)


def _extract_anchored_block(workflow: str, start: str, end: str) -> str:
    start_anchors = re.findall(rf"^{re.escape(start)}[ \t]*:", workflow, re.MULTILINE)
    end_anchors = re.findall(rf"^{re.escape(end)}[ \t]*:", workflow, re.MULTILINE)
    if len(start_anchors) != 1 or len(end_anchors) != 1:
        raise AssertionError(f"{start} contract anchors must appear exactly once")
    match = re.search(
        rf"^{re.escape(start)}[ \t]*:\n(?P<block>.*?)^{re.escape(end)}[ \t]*:",
        workflow,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"missing {start} block before {end}")
    return f"{start}:\n{match.group('block')}"


def _assert_exact_trigger_contract(workflow: str) -> None:
    actual = _normalize_yaml_block(_extract_anchored_block(workflow, "on", "permissions"))
    if actual != EXPECTED_TRIGGER_BLOCK:
        raise AssertionError(f"trigger contract must exactly match: {actual!r}")


def _assert_exact_permissions_contract(workflow: str) -> None:
    actual = _normalize_yaml_block(_extract_anchored_block(workflow, "permissions", "concurrency"))
    if actual != EXPECTED_PERMISSIONS_BLOCK:
        raise AssertionError(f"permissions contract must exactly match: {actual!r}")


def _workflow_steps(workflow: str) -> list[tuple[str, str]]:
    return re.findall(
        r"^      -(?P<header>.*?)(?:\n|$)(?P<body>.*?)(?=^      -(?:\s|$)|\Z)",
        workflow,
        re.MULTILINE | re.DOTALL,
    )


def _assert_auth_gate_wiring(workflow: str) -> None:
    steps = _workflow_steps(workflow)
    auth_steps = [body for header, body in steps if header == " name: Check Claude authentication"]
    charter_steps = [
        body
        for header, body in steps
        if header == " name: Load review charter from the base branch"
    ]
    if len(auth_steps) != 1 or not re.search(r"^        id: auth$", auth_steps[0], re.MULTILINE):
        raise AssertionError("auth-gate wiring must retain the Check Claude authentication step")

    action_steps = [
        (header, body)
        for header, body in steps
        if re.search(r"^ uses:[ \t]*anthropics/claude-code-action@", header)
        or re.search(
            r"^[ \t]+uses:[ \t]*anthropics/claude-code-action@",
            body,
            re.MULTILINE,
        )
    ]
    guarded_steps = [*charter_steps, *(body for _, body in action_steps)]
    if (
        len(charter_steps) != 1
        or len(action_steps) != 1
        or action_steps[0][0] != " name: Claude review"
        or any(
            step is None
            or not re.search(rf"^        {re.escape(AUTH_ENABLED_GUARD)}$", step, re.MULTILINE)
            for step in guarded_steps
        )
    ):
        raise AssertionError("auth-gate wiring must guard the charter and Claude action steps")


class ClaudeReviewWorkflowTests(unittest.TestCase):
    def test_trigger_contract_rejects_dedented_trigger_child(self):
        """A trigger cannot become a second top-level workflow key."""
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        mutated = workflow.replace("  pull_request:\n", "pull_request:\n", 1)

        with self.assertRaisesRegex(AssertionError, "trigger contract"):
            _assert_exact_trigger_contract(mutated)

    def test_permissions_contract_rejects_dedented_permission_child(self):
        """A permission cannot become a second top-level workflow key."""
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        mutated = workflow.replace("  contents: read\n", "contents: read\n", 1)

        with self.assertRaisesRegex(AssertionError, "permissions contract"):
            _assert_exact_permissions_contract(mutated)

    def test_trigger_contract_rejects_a_second_top_level_on_anchor(self):
        """A later trigger contract cannot evade the anchored-block assertion."""
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        mutated = workflow + "\non:\n  workflow_run:\n"

        with self.assertRaisesRegex(AssertionError, "contract anchors"):
            _assert_exact_trigger_contract(mutated)

    def test_permissions_contract_rejects_a_whitespace_variant_duplicate_anchor(self):
        """A duplicate top-level permission key cannot hide before its colon."""
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        mutated = workflow + "\npermissions :\n  contents: write\n"

        with self.assertRaisesRegex(AssertionError, "contract anchors"):
            _assert_exact_permissions_contract(mutated)

    def test_trigger_contract_rejects_an_added_pull_request_target_trigger(self):
        """Adding a privileged PR trigger changes the workflow contract."""
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        mutated = workflow.replace(
            "  issue_comment:\n",
            "  pull_request_target:\n    types: [opened]\n  issue_comment:\n",
            1,
        )

        with self.assertRaisesRegex(AssertionError, "trigger contract"):
            _assert_exact_trigger_contract(mutated)

    def test_trigger_contract_matches_current_trigger_to_type_mapping(self):
        """Only the approved review triggers and activity types are enabled."""
        _assert_exact_trigger_contract(WORKFLOW_PATH.read_text(encoding="utf-8"))

    def test_permissions_contract_rejects_a_widened_contents_permission(self):
        """A write-capable contents token is not part of this review workflow."""
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        mutated = workflow.replace("  contents: read\n", "  contents: write\n", 1)

        with self.assertRaisesRegex(AssertionError, "permissions contract"):
            _assert_exact_permissions_contract(mutated)

    def test_permissions_contract_matches_current_permission_mapping(self):
        """The workflow retains its least-privilege permission mapping."""
        _assert_exact_permissions_contract(WORKFLOW_PATH.read_text(encoding="utf-8"))

    def test_auth_gate_wiring_rejects_a_removed_charter_step_guard(self):
        """The base-branch charter read cannot run without Claude authentication."""
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        mutated = workflow.replace(AUTH_ENABLED_GUARD + "\n        shell: bash", "shell: bash", 1)

        with self.assertRaisesRegex(AssertionError, "auth-gate wiring"):
            _assert_auth_gate_wiring(mutated)

    def test_auth_gate_wiring_rejects_an_unnamed_unguarded_claude_action_step(self):
        """An unnamed sequence item cannot inherit the charter step's guard."""
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        mutated = workflow.replace(
            "      - name: Claude review\n"
            "        if: steps.auth.outputs.enabled == 'true'\n"
            "        uses: anthropics/claude-code-action@",
            "      -\n        uses: anthropics/claude-code-action@",
            1,
        )

        with self.assertRaisesRegex(AssertionError, "auth-gate wiring"):
            _assert_auth_gate_wiring(mutated)

    def test_auth_gate_wiring_rejects_an_inline_unguarded_claude_action_step(self):
        """An inline action mapping cannot evade the Claude-action count."""
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        mutated = workflow + "\n      - uses: anthropics/claude-code-action@deadbeef\n"

        with self.assertRaisesRegex(AssertionError, "auth-gate wiring"):
            _assert_auth_gate_wiring(mutated)

    def test_auth_gate_wiring_matches_the_named_steps_and_guards(self):
        """Only the two Claude-dependent steps are required to carry the auth guard."""
        _assert_auth_gate_wiring(WORKFLOW_PATH.read_text(encoding="utf-8"))

    def test_comment_only_edits_do_not_change_the_pinned_workflow_contracts(self):
        """Comments inside target blocks are documentation, not contract content."""
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        commented = workflow.replace(
            "on:\n", "on:\n  # comment-only trigger documentation\n", 1
        ).replace("permissions:\n", "permissions:\n  # comment-only permission documentation\n", 1)

        _assert_exact_trigger_contract(commented)
        _assert_exact_permissions_contract(commented)
        _assert_auth_gate_wiring(commented)

    def test_review_condition_rejects_top_level_permissive_or(self):
        """No permissive clause can be appended after the approved branches."""
        condition = """
          (github.event_name == 'pull_request' &&
           github.event.pull_request.draft == false) ||
          (github.event_name == 'issue_comment' &&
           github.event.issue.pull_request != null &&
           contains(github.event.comment.body, '@claude') &&
           (github.event.comment.author_association == 'OWNER' ||
            github.event.comment.author_association == 'MEMBER' ||
            github.event.comment.author_association == 'COLLABORATOR')) ||
          (github.event_name == 'pull_request_review_comment' &&
           contains(github.event.comment.body, '@claude') &&
           (github.event.comment.author_association == 'OWNER' ||
            github.event.comment.author_association == 'MEMBER' ||
            github.event.comment.author_association == 'COLLABORATOR')) ||
          github.event.comment.author_association == 'CONTRIBUTOR'
        """

        with self.assertRaisesRegex(AssertionError, "must exactly match"):
            _assert_exact_review_condition(condition)

    def test_review_condition_matches_exact_authorization_contract(self):
        """The workflow retains only the approved automatic and comment branches."""
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        condition_match = re.search(
            r"^    if: >\n(?P<condition>.*?)^    runs-on:",
            workflow,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(condition_match)
        assert condition_match is not None
        condition = condition_match.group("condition")

        _assert_exact_review_condition(condition)


if __name__ == "__main__":
    unittest.main()
