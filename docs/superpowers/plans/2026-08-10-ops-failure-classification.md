# Ops Failure Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classify expired Schwab refresh tokens in both capture lanes and prove dashboard subprocess builds are fresh.

**Architecture:** A shared predicate identifies only the specified Authlib failure. Python CLI boundaries produce stable evidence lines; shell wrappers map those lines to actionable CRITICAL output while retaining generic fallbacks.

**Tech Stack:** Python 3.12, `unittest`, Authlib (already locked), zsh/bash wrapper snippets.

## Global Constraints

- Offline tests only; use mocks/fakes and never call Schwab.
- No new dependencies, retries, or changes to token storage/auth logic.
- Preserve fail-closed nonzero behavior.
- Do not touch `ledger/`, `~/options-validator-ops`, or `~/options-validator-research`.
- Record verbatim RED output in `reports/2026-08-10-ops-failure-classification-receipt.md`.

---

### Task 1: Intraday auth-expiry classification

**Files:**
- Create: `options_researcher/schwab_auth_failure.py`
- Modify: `options_researcher/intraday_capture.py`
- Modify: `tools/intraday_capture.sh`
- Test: `tests/test_intraday_capture.py`

- [ ] Add a CLI test using a real constructed `OAuthError` and a live shell-block test using fixture output.
- [ ] Run the focused tests and capture the expected failures.
- [ ] Add the narrow shared predicate, CLI catch, and evidence-based wrapper branch.
- [ ] Re-run the focused tests green.

### Task 2: Independent preclose auth-expiry classification

**Files:**
- Modify: `options_researcher/schwab_chain_capture.py`
- Modify: `tools/schwab_chain_capture.sh`
- Test: `tests/test_schwab_chain_capture.py`
- Test: `tests/test_schwab_chain_schedule.py`

- [ ] Add tests proving per-symbol auth expiry reaches the CLI boundary and the wrapper emits actionable CRITICAL output.
- [ ] Run the focused tests and capture the expected failures.
- [ ] Propagate only matching auth expiry, classify it in `main`, and add the wrapper evidence branch.
- [ ] Re-run the focused tests green.

### Task 3: Dashboard fresh-build assertion

**Files:**
- Modify: `tests/test_experiments_baseline.py`

- [ ] Assert `wrote ` in stdout after both subprocess invocations.
- [ ] Temporarily mutate the production print label and capture the focused test's failure.
- [ ] Restore production exactly and re-run the focused test green.

### Task 4: Receipt and verification

**Files:**
- Create: `reports/2026-08-10-ops-failure-classification-receipt.md`

- [ ] Record base, root-cause evidence, preclose finding, verbatim RED outputs, GREEN results, and scope guardrails.
- [ ] Run the full suite, Ruff, Ruff format check, Pyright, and `git diff --check`.
- [ ] Review the complete diff, commit, push the feature branch, create a `--no-ff` merge from `origin/main` without updating the ops/research checkouts, re-verify, and push main.
