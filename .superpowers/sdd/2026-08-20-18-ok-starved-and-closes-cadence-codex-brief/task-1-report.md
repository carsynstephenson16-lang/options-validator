# Task 1 report — Codex brief 18

## Verdict

DONE_WITH_CONCERNS: WP-A through WP-D are implemented and the full acceptance
commands completed successfully. The only concern is an existing out-of-scope
`OK_STARVED` occurrence in `reports/2026-08-20-chain-source-owner-decision-packet.md`
(the owner decision packet); it was not modified.

## Implementation summary

- Added the three-way ritual terminal assignment: `OK`, `OK_STARVED` only for
  the single starved capture critical predicate, otherwise `BROKEN`.
- Accepted `OK_STARVED` in both ritual-status validation sites and in the
  attractiveness preflight. On `OK_STARVED`, only H6/H7/H8 are excused; H5 and
  H10 remain required. Added the explicit subset/complement contract test.
- Added the guarded, glob-driven underlying-closes refresh before the feature
  rebuild. It pre-reads, fetches, post-reads, detects retroactive changes at
  `1e-4` relative tolerance, restores changed histories, continues per-symbol
  failures, and appends exactly one `DATA_PULL` fact per invocation.
- Added `ledger/facts.log` to data-tier durability and updated the three named
  downstream vocabulary documents.

## Files changed

`.agents/skills/independent-research-critic/SKILL.md`,
`.claude/skills/research-refresh/SKILL.md`, `data/recent_topup.py`,
`docs/research-context-refresh-runbook.md`,
`options_researcher/attractiveness_research_v2.py`,
`options_researcher/ritual_status.py`, `tests/test_daily_ritual_provenance.py`,
`tests/test_recent_topup.py`, `tests/test_research_context_assemble.py`,
`tests/test_ritual_status.py`, and `tools/daily_ritual.sh`.

No changes were made to `ritual_receipt.py`, `config.py`, `ledger/**`,
`research/facts.py`, `research/ledger.py`, plist files, final ritual exit
printing, or `SUCCESSFUL_RITUAL_STATUSES` contents.

## TDD evidence

Tests were written before production changes and observed RED:

```text
uv run python -m unittest discover -s tests -p 'test_ritual_status.py'
Ran 5 tests ... FAILED (errors=1)
ValueError: status must be RUNNING, OK, or BROKEN

uv run python -m unittest discover -s tests -p 'test_research_context_assemble.py'
Ran 45 tests ... FAILED (failures=2, errors=3)
OK_STARVED was rejected as not OK; H5/H10 lane assertions therefore failed.

uv run python -m unittest discover -s tests -p 'test_recent_topup.py'
Ran 26 tests ... FAILED (errors=4)
AttributeError: module 'data.recent_topup' has no attribute 'refresh_closes_guarded'

uv run python -m unittest discover -s tests -p 'test_daily_ritual_provenance.py'
Ran 27 tests ... FAILED (failures=3)
The new terminal and guarded-step assertions failed against the pre-change shell.
```

Focused GREEN after implementation:

```text
uv run python -m unittest discover -s tests -p 'test_ritual_status.py'
Ran 5 tests ... OK
uv run python -m unittest discover -s tests -p 'test_research_context_assemble.py'
Ran 46 tests ... OK
uv run python -m unittest discover -s tests -p 'test_recent_topup.py'
Ran 26 tests ... OK
uv run python -m unittest discover -s tests -p 'test_daily_ritual_provenance.py'
Ran 27 tests ... OK
```

## Full acceptance

```text
uv run python -m unittest discover -s tests
exit 0 (3,097 discovered tests; 5 skipped; expected fixture warnings/logs only)

uv run ruff check .
All checks passed!

uv run pyright
0 errors, 0 warnings, 0 informations
```

Additional final checks:

```text
zsh -n tools/daily_ritual.sh       exit 0
git diff --check                   exit 0
```

## `OK_STARVED` scope proof

Scoped command:

```text
git grep -n 'OK_STARVED' -- \
  .agents/skills/independent-research-critic/SKILL.md \
  .claude/skills/research-refresh/SKILL.md \
  docs/research-context-refresh-runbook.md \
  options_researcher/attractiveness_research_v2.py \
  options_researcher/ritual_status.py tests tools/daily_ritual.sh \
  docs/superpowers/plans/2026-08-20-18-ok-starved-and-closes-cadence-codex-brief.md
```

Output paths were limited to the three named documents, the two downstream
Python modules, `tests/**`, `tools/daily_ritual.sh`, and the brief itself.
An unscoped `git grep -n 'OK_STARVED'` also reports the pre-existing owner
decision packet under `reports/`; that file is outside Scope IN and remains
untouched.

## Self-review and concerns

- Reviewed the final diff for forbidden files, hidden scope expansion, shell
  ordering, status-schema changes, receipt-vocabulary changes, and accidental
  live-order/provider behavior. None were found.
- `SUCCESSFUL_RITUAL_STATUSES` remains exactly `{"CAPTURED", "NO_SIGNAL"}`;
  the run-status schema remains `daily_ritual/run_status/v1`.
- The guarded path resolves `underlying_closes.CACHE_DIR` at call time and
  never uses `today` for row filtering. Tests inject fetchers and never call
  Yahoo/network code.
- The scope-proof concern above is pre-existing repository state, not caused
  by this task; deleting or rewriting that report would violate the brief.
