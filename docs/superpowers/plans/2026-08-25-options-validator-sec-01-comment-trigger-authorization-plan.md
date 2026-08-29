# SEC-01 Comment-Trigger Authorization Implementation Plan

> **Execution:** Follow test-driven development and the subagent progress
> ledger. One Terra Medium writer owns the implementation; fresh Terra
> reviewers inspect the completed diff. No push, PR, merge, deployment,
> provider call, research run, cache mutation, ledger mutation, or order path.

**Goal:** Prevent untrusted PR commenters from invoking the optional
credentialed Claude review action while preserving automatic pull-request
review and trusted collaborator comment triggers.

**Root cause:** Both comment-event branches treat an `@claude` body mention as
authorization and do not inspect the comment author's association.

**Lane-A gate:** SEC-01 score 90; no protected-WIP overlap, dependency,
authority/data hard gate, or unsafe-action reject gate. See the audit's
`05-diminishing-returns-analysis.md` and final adversarial PASS in
`09-adversarial-verification.md`.

## Task 1: Write and prove the failing workflow contract

**File:** `tests/test_claude_review_workflow.py`

1. Add a stdlib-only `unittest` that reads
   `.github/workflows/claude-review.yml` without credentials or network.
2. Assert the `review` job condition retains automatic non-draft
   `pull_request` review.
3. Assert each of the `issue_comment` and
   `pull_request_review_comment` branches requires
   `github.event.comment.author_association`.
4. Assert the parsed allowlist is exactly `OWNER`, `MEMBER`, and
   `COLLABORATOR`; demonstrate `NONE` and an unlisted value are denied.
5. Run
   `UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run python -m unittest tests.test_claude_review_workflow -v`
   before changing the workflow and record the expected authorization-contract
   failure in the progress ledger.

## Task 2: Apply the smallest workflow repair

**File:** `.github/workflows/claude-review.yml`

1. Add the same comment-author association predicate to both comment branches.
2. Allow exactly `OWNER`, `MEMBER`, and `COLLABORATOR`; reject `NONE` and every
   unlisted association fail-closed.
3. Keep the automatic `pull_request` branch, permissions, auth-presence check,
   base-branch charter handling, pinned actions, and all other behavior intact.
4. Add no dependency and perform no unrelated cleanup.
5. Re-run the targeted command and require PASS.

## Task 3: Writer verification and handoff

1. Run targeted unittest, Ruff on the new Python file, Ruff format check on the
   new Python file, and `git diff --check`.
2. Inspect the final diff for exact scope and update the progress ledger with
   commands, results, changed files, and unresolved risks.
3. Stop for fresh spec-compliance and code-quality/security review. Do not
   commit; the parent creates the local-only candidate commit after reviews.

**Rollback:** Disable both comment event triggers and their job-condition
branches while retaining automatic non-draft `pull_request` review. Do not
restore public untrusted comment triggering. No state or data migration is
involved.
