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


def _assert_exact_review_condition(condition: str) -> None:
    actual = " ".join(condition.split())
    if actual != EXPECTED_REVIEW_CONDITION:
        raise AssertionError(
            f"review condition must exactly match its authorization contract: {actual!r}"
        )


class ClaudeReviewWorkflowTests(unittest.TestCase):
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
