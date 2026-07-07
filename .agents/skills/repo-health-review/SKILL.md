---
name: repo-health-review
description: On-demand, read-only review of the repo's code health that PROPOSES improvements but changes nothing. Use only when Carsyn explicitly asks for a repo review, health check, or "what should I improve." Never run automatically. Never edit files as part of this skill.
---

# Repo Health Review

This skill exists as the safe replacement for "an agent that improves the project automatically." Automatic improvement in a research-integrity repo is a contradiction: unsupervised changes to validation code silently change what results mean, and unlogged changes break the ledger's guarantee. So this skill is read-only and proposal-only, run only when asked.

## Review checklist

1. **Test coverage of the guardrails themselves:** does a test prove the pre-registration gate actually blocks an unregistered run? Does a test prove the ledger rejects edits to past entries? Untested guardrails are decoration.
2. **Drift between docs and code:** does CLAUDE.md/README describe rules the code no longer enforces, or vice versa?
3. **Dead code and abandoned experiments:** files no test imports and no entry references.
4. **Hardcoded values that should be config:** dates, tickers, account size scattered in code.
5. **Silent failure paths:** bare excepts, default values on missing data, anything that lets a run "succeed" on bad input.
6. **Dependency pinning:** unpinned versions mean today's PASS may not reproduce next month.
7. **One-command reproducibility:** can a fresh clone re-run the last logged experiment and get the same hash? If not, that's the top priority.

## Output

**Health summary:** 3 sentences max.
**Findings:** each with file path, why it matters, and a proposed fix — as a proposal, not an edit.
**Priority order:** what to fix first and the reason.
**Explicitly out of scope:** this review never proposes strategy or parameter changes. Strategy changes go through ledger-discipline as new hypothesis versions, or they don't happen.

After the review, stop. Implementing any fix is a separate, explicit request from Carsyn.
