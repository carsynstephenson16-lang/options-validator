# SEC-01 Subagent Progress

## Status

- Plan: ready
- Lane-A score: 90
- Protected-WIP overlap: none
- Hard gate: none
- Writer: complete (uncommitted)
- Independent reviews: PASS (fresh Sol spec and security/code-quality reviews)
- Candidate commit: this implementation commit; SHA recorded in the final audit report

## TDD receipt

The writer must append the exact pre-change failing command and failure, then
the post-change passing commands. A test written only after the workflow edit
does not satisfy this plan.

## Scope

- `.github/workflows/claude-review.yml`
- `tests/test_claude_review_workflow.py`
- this progress ledger

No other source or test file is authorized.

## Original writer claim (2026-08-25)

The initial writer receipt reported a failing offline authorization contract
before the workflow edit and passing targeted/lint/diff checks after it. The
mtime chronology did not independently prove that ordering, so it is not used
as the authoritative TDD evidence.

## Post-review reconstructed RED/GREEN proof (2026-08-25)

For this reconstruction only, the workflow was restored with `apply_patch`
to its vulnerable pre-fix comment predicates, then returned with `apply_patch`
to the identical minimal guard. No test file was changed during the
reconstruction.

### RED

Timestamp: `2026-08-25T18:48:25Z` UTC

Command: `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run python -m unittest tests.test_claude_review_workflow -v`
Exit status: `1`

Relevant exact output:

```text
test_comment_triggers_require_trusted_author_association (tests.test_claude_review_workflow.ClaudeReviewWorkflowTests.test_comment_triggers_require_trusted_author_association)
Removing an association check would let untrusted commenters spend review quota. ... FAIL
AssertionError: 'github.event.comment.author_association' not found in " github.event.issue.pull_request != null &&\n       contains(github.event.comment.body, '@claude')"
Ran 1 test in 0.001s
FAILED (failures=1)
EXIT_STATUS=1
```

### GREEN

Timestamp: `2026-08-25T18:48:36Z` UTC

Command: `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run python -m unittest tests.test_claude_review_workflow -v`
Exit status: `0`

Relevant exact output:

```text
test_comment_triggers_require_trusted_author_association (tests.test_claude_review_workflow.ClaudeReviewWorkflowTests.test_comment_triggers_require_trusted_author_association)
Removing an association check would let untrusted commenters spend review quota. ... ok
Ran 1 test in 0.000s
OK
EXIT_STATUS=0
```

### Final checks

- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run ruff check tests/test_claude_review_workflow.py`: PASS, exit status `0`, output `All checks passed!`.
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run ruff format --check tests/test_claude_review_workflow.py`: PASS, exit status `0`, output `1 file already formatted`.
- `git diff --check`: PASS, exit status `0`, no output.

## Parser false-negative hardening (Sol takeover, 2026-08-25)

Scope for this pass was limited to
`tests/test_claude_review_workflow.py` and this progress ledger. The stable
workflow guard was inspected but not edited.

### Fixture-quality check

The first attempted full-condition fixture had only one event-group opening
parenthesis. It passed immediately because the old regex stopped before the
allowlist's closing parenthesis and the resulting truncated branch mismatched
for the wrong reason. The command wrapper also attempted to assign zsh's
read-only `status` parameter after the test, producing
`zsh:2: read-only variable: status`. This run is not accepted as RED evidence.
The fixture was corrected, before changing the extractor, to place the named
event predicate inside a complete outer event group containing the permissive
OR clause.

### Authoritative RED: permissive OR hidden inside the event group

Command:

```text
PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run python -m unittest tests.test_claude_review_workflow.ClaudeReviewWorkflowTests.test_complete_comment_branch_rejects_permissive_or_inside_event_group -v
```

Exit status: `1`.

Relevant exact output:

```text
test_complete_comment_branch_rejects_permissive_or_inside_event_group (tests.test_claude_review_workflow.ClaudeReviewWorkflowTests.test_complete_comment_branch_rejects_permissive_or_inside_event_group)
The parser cannot hide a permissive clause after the trusted allowlist. ... FAIL
AssertionError: AssertionError not raised
Ran 1 test in 0.000s
FAILED (failures=1)
EXIT_STATUS=1
```

This proves the old lazy regex returned only the trusted inner predicate and
hid the appended
`|| github.event.comment.author_association == 'CONTRIBUTOR'` clause from the
exact comparison.

### Authoritative RED: quoted parenthesis text

Command:

```text
PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run python -m unittest tests.test_claude_review_workflow.ClaudeReviewWorkflowTests.test_comment_branch_parser_ignores_parentheses_inside_quoted_strings -v
```

Exit status: `1`. The old regex returned only
`"contains(github.event.comment.body, '"` instead of the complete branch;
the literal `') || still quoted'` incorrectly terminated its match.

### GREEN implementation and evidence

`_comment_branch` now uses a stdlib-only balanced-parenthesis scan. It includes
immediately enclosing event-group parentheses, counts nested groups, and
ignores parentheses inside single- or double-quoted strings, including
backslash-escaped and doubled quote characters. The exact branch comparison
remains unchanged.

Commands and results:

- Direct regression pair: PASS, exit status `0`, 2 tests.
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run python -m unittest tests.test_claude_review_workflow -v`: PASS, exit status `0`, 4 tests. This accepts the current workflow while rejecting the complete permissive-OR fixture.
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run python -m unittest discover -s tests -p 'test_claude_review_workflow.py' -v`: PASS, exit status `0`, 4 tests.
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run ruff check tests/test_claude_review_workflow.py`: PASS, exit status `0`, output `All checks passed!`.
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run ruff format --check tests/test_claude_review_workflow.py`: PASS, exit status `0`, output `1 file already formatted`.
- `git diff --check`: PASS, exit status `0`, no output.

Changed in this hardening pass:

- `tests/test_claude_review_workflow.py`
- `.superpowers/sdd/2026-08-25-options-validator-sec-01-comment-trigger-authorization-plan/progress.md`

Remaining risk: this remains a source-level, offline workflow contract rather
than an evaluator for GitHub Actions expression semantics. It deliberately
fails closed on source-shape changes and cannot independently validate live
GitHub event payload behavior. No unsupported production-behavior assumption
was introduced, and no workflow, audit report, credential, provider, research,
cache, ledger, or order path was changed in this pass.

Changed files:

- `.github/workflows/claude-review.yml`
- `tests/test_claude_review_workflow.py`
- `.superpowers/sdd/2026-08-25-options-validator-sec-01-comment-trigger-authorization-plan/progress.md`

Unresolved risks: the offline contract validates the job predicate shape and
fail-closed allowlist only; GitHub Actions event-payload behavior remains for
fresh review.

## Quality-review P2 resolution (2026-08-25)

Reviewer feedback: collecting only association equality literals allowed a
future permissive OR clause to coexist with the three trusted values and pass
the test.

Resolution: the stdlib-only workflow contract now normalizes each extracted
comment branch and compares it with the complete intended predicate. The
issue-comment branch must include the PR-comment check, `@claude` check, and
the exact three-value association group; the review-comment branch must
include the `@claude` check and that same exact group. A negative fixture
with an appended `CONTRIBUTOR` OR clause is rejected.

Test-first evidence: before adding the exact-branch comparator, the new
negative test failed with `NameError: name '_assert_exact_comment_branch' is
not defined`. The comparator was then added without changing the workflow.

Final commands and results:

- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run python -m unittest tests.test_claude_review_workflow -v`: PASS, exit status `0`, 2 tests.
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run python -m unittest discover -s tests -p 'test_claude_review_workflow.py' -v`: PASS, exit status `0`, 2 tests.
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run ruff check tests/test_claude_review_workflow.py`: PASS, exit status `0`, output `All checks passed!`.
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run ruff format --check tests/test_claude_review_workflow.py`: PASS, exit status `0`, output `1 file already formatted`.
- `git diff --check`: PASS, exit status `0`, no output.

## Whole-condition contract supersedes balanced parser (Sol, 2026-08-25)

The balanced-parenthesis extractor was superseded because its contract ended
at the named event group's close. A new top-level permissive OR appended after
that close was therefore outside the extracted substring and invisible to the
branch comparison. The roughly 40-line quote-aware parser was also unnecessary
for this static source-shape contract.

The replacement extracts the existing `review` job `if: >` block,
whitespace-normalizes the complete condition, and compares it exactly with one
`EXPECTED_REVIEW_CONDITION`. That literal contains only the approved automatic
non-draft pull-request branch and the two approved comment branches with the
exact `OWNER`, `MEMBER`, and `COLLABORATOR` allowlist. Any inner or outer added
clause, removed guard, unlisted association, branch reorder, or other condition
mutation now changes the complete normalized string and fails closed.

### TDD receipt

The first test run errored with
`NameError: name '_assert_exact_review_condition' is not defined`; this was not
accepted as the behavioral RED. A temporary no-op validator was added, then the
focused top-level bypass test was rerun before the real comparator existed.

Authoritative RED command:

```text
PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run python -m unittest tests.test_claude_review_workflow.ClaudeReviewWorkflowTests.test_review_condition_rejects_top_level_permissive_or -v
```

Exit status: `1`.

Relevant exact output:

```text
test_review_condition_rejects_top_level_permissive_or (tests.test_claude_review_workflow.ClaudeReviewWorkflowTests.test_review_condition_rejects_top_level_permissive_or)
No permissive clause can be appended after the approved branches. ... FAIL
AssertionError: AssertionError not raised
Ran 1 test in 0.000s
FAILED (failures=1)
EXIT_STATUS=1
```

After that RED, the branch expected map, balanced parser, branch comparator,
and three parser-specific tests were removed. The no-op was replaced with the
complete normalized condition comparator. No workflow line changed.

### GREEN and verification

- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run python -m unittest tests.test_claude_review_workflow -v`: PASS, exit status `0`, 2 tests. The current workflow is accepted and the top-level permissive-OR fixture is rejected.
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run python -m unittest discover -s tests -p 'test_claude_review_workflow.py' -v`: PASS, exit status `0`, 2 tests.
- One-off mutation check: PASS, exit status `0`; printed `REJECTED: inner permissive OR` and `REJECTED: unlisted association`.
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run ruff check tests/test_claude_review_workflow.py`: PASS, exit status `0`, output `All checks passed!`.
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/Users/carsynstephenson/options-validator/.venv UV_OFFLINE=1 uv run ruff format --check tests/test_claude_review_workflow.py`: PASS, exit status `0`, output `1 file already formatted`.
- `git diff --check`: PASS, exit status `0`, no output.

Changed in this pass only:

- `tests/test_claude_review_workflow.py`
- `.superpowers/sdd/2026-08-25-options-validator-sec-01-comment-trigger-authorization-plan/progress.md`

Remaining risk: this is intentionally an exact source-level contract, not a
GitHub Actions expression evaluator. Semantically equivalent condition
refactors require an explicit expected-literal update and review. Live GitHub
event-payload behavior remains outside this offline test's evidence.

## Final Sol review receipt

- Spec compliance: PASS; no findings.
- Security/code quality: PASS; SEC-01 fixed in the candidate checkout with no
  high- or medium-severity residual finding.
- Low-severity rollback correction: accepted. The plan and audit artifacts now
  require disabling both comment triggers while retaining automatic PR review;
  they no longer suggest restoring the vulnerable public-comment condition.
- Residual proof gap: no live GitHub-hosted event was dispatched and an
  Actions-aware validator was unavailable. Static source review, YAML parsing,
  exact mutation probes, and the offline contract support a high-confidence
  candidate-checkout result.
