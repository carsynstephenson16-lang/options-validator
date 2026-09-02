# Task 6 independent stop-gate re-review

## Verdict

**PASS — no blocking findings remain in candidate `06ecf75321b397d7e359a5bf72d681e4f4422456`.**

The corrective commit closes both prior exploits. The v1 registration builder
now binds a feasibility receipt to the exact 2026-04-16 through 2026-07-27,
70-session, canonical ordered 15-name, 1,050-symbol-day study; the frozen v1
stack/tool identity; current configuration hash; and a zero-error result before
it evaluates the 20-entry threshold or owner line. Both synthetic and guarded
real registration paths share that builder.

## Blocking findings

None.

## Prior findings resolved

### Denominator shrink

The exact prior exploit retained four passes, changed `symbol_days` from 1,050
to 210, recomputed a hash-correct `expected_entries=20.0`, and supplied the
exact namespace/hash owner line. It now refuses through both
`build_window_registration_event(...)` and `register_window_real(...)`; the
temporary guarded store remains VALID EMPTY.

The builder requires `lookback_sessions == window_sessions == 70`, canonical
lookback dates, canonical universe size, and `symbol_days == 70 * 15 == 1,050`.

### Partial/substituted universe and changed stack

A hash-correct receipt with `universe=["FAKE1", "FAKE2"]` now refuses. The
receipt universe must equal the exact ordered symbols from `scope_identity()`,
and the registration manifest's `included` list must equal that receipt
universe. A reordered manifest also refuses.

The stack is bound to the feasibility tool's
`h7-frozen-entry-stack-plus-board/v1` constant. Alternate stack and tool labels
refuse, so changed v2 entry logic cannot qualify under the v1 namespace.

## Requested adversarial checks

- The actual immutable receipt
  `d0ffe1f900b8ffc132f757f9783d4581464aaf8b3538271fe2ae337ba1702d0c`
  remains 4/1,050 and is refused by both the builder and guarded real door; the
  temporary guarded ledger remains VALID EMPTY.
- A canonical hash-correct 20/1,050 receipt is accepted at the exact lower
  boundary by both the builder and guarded real door.
- Hash-correct alternate stack, tool label, forward-window count,
  lookback-session count, lookback start/end dates, and config hash all refuse.
- `error_count=1` refuses. A nonempty `errors` list with `error_count=0` also
  refuses.
- Missing, stale-hash, and wrong-namespace owner decision lines refuse. The
  accepted exact line binds both `h7-forward-schwab-v1` and the validated
  feasibility receipt hash and is frozen into `owner_authorization`.
- The exact canonical feasibility universe must also equal the registration
  manifest's `included` list.
- No other v1 registration caller or direct CLI append path was introduced;
  the one-door structural suite passes.

## Documentation and immutable-state review

The owner packet and provider-transition table truthfully state
`STOPPED_FEASIBILITY / NOT REGISTERED / NOT ACTIVATED`, cite 4.0 < 20, keep OD-3
untyped/inoperative, forbid the prepared v1 authority patch, and describe the
canary/restore as evidence-only. The earlier contradiction was removed: the
packet now says this current v1 candidate is stopped from this evidence, while
the exact owner-line template is explicitly hypothetical had the repaired
receipt qualified. The v2 report remains design-only and requires separate
versioning and preregistration.

Base-to-candidate Git object comparison confirms no changes to either H7
ledger, `data/ritual_authority.py`, or `tools/daily_ritual.sh`. The old ledger
verifies VALID with its existing record; `ledger/h7_forward_schwab` verifies
VALID EMPTY. Authority remains `h7_active=False` and
`exact_session_source_active=False`. No registration or ritual was executed.

## Validation

- Schwab window registration: 16/16 passed.
- Schwab manual activation composition: 5/5 passed.
- H7 one-door: 8/8 passed.
- Independent adversarial harness: all prior exploits and requested identity
  substitutions refused; canonical exact-20 control accepted.
- Ruff: passed.
- Ruff formatting: passed.
- Pyright: 0 errors, 0 warnings, 0 informations.
- `git diff --check e61709c..06ecf75`: passed.
- Production worktree remained clean; this review file is ignored.

Commands included:

```text
uv run python -m unittest discover -s tests -p 'test_h7_schwab_window_registration.py'
uv run python -m unittest discover -s tests -p 'test_h7_schwab_manual_activate.py'
uv run python -m unittest discover -s tests -p 'test_h7_one_door.py'
uv run ruff check options_researcher/h7_schwab_window_registration.py tests/test_h7_schwab_window_registration.py tests/test_h7_schwab_manual_activate.py
uv run ruff format --check options_researcher/h7_schwab_window_registration.py tests/test_h7_schwab_window_registration.py tests/test_h7_schwab_manual_activate.py
uv run pyright options_researcher/h7_schwab_window_registration.py tools/h7_schwab_manual_activate.py
uv run python -m options_researcher.h7_event_ledger verify --base-dir ledger/h7_forward
uv run python -m options_researcher.h7_event_ledger verify --base-dir ledger/h7_forward_schwab
git diff --exit-code e61709c..06ecf75 -- data/ritual_authority.py ledger/h7_forward ledger/h7_forward_schwab tools/daily_ritual.sh
```
