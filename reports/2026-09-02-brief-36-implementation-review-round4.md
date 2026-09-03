# Brief 36 implementation — round-4 independent adversarial review receipt (2026-09-02, ~21:20 ET)

**Head reviewed:** `8fa4085` on `codex/brief-36-h7-activation-door` (fix range `1156325..8fa4085`: B2 revert `1a68de1`,
B1 closure `8fa4085`; exactly 3 files, all in scope). **Fixes from this round applied at `fee356f`** (see bottom).
**Reviewer:** independent Opus adversarial subagent, read-only, dispatched by the orchestrating Claude session.
Owner-directed context: "fix brief 36 blockers now" (2026-09-02 20:39 ET) — the orchestrating session implemented
the blocker fixes directly instead of a Codex round.

## Verdict: PASS WITH FIXES (three LOW, non-blocking) — all three applied at `fee356f`.

## Per-item
**B2 (undeclared `format="mixed"`) — CONFIRMED FIXED.** `git diff --stat origin/main -- options_researcher/schwab_quote_age_report.py`
= 12 insertions, 0 deletions; the only addition is `selectable_timestamp_population` (`:164-174`); `_timestamps` (`:176`)
byte-identical to origin/main.

**B1 (source surface not a closure; tautological test) — CONFIRMED FIXED.** Independent ast walk (not the module's
function) rooted at `tools/h7_schwab_feasibility.py` over {config,data,options_researcher,research,strategies,tools},
excluding config.py → 49 paths, exactly equal to `FEASIBILITY_SOURCE_PATHS` (`h7_schwab_window_registration.py:125-175`).
`from pkg import submodule`, `from pkg.mod import name`, `import pkg.mod` all handled (`:79-97`). Zero relative imports in
the closure (grep `^\s*from\s+\.`). No first-party dynamic imports (6 `importlib.metadata` version lookups only, stdlib).
Function-level imports are walked (`data/recent_topup.py:72` → `h7_scope.py` present). The synthetic walker test
(`tests/test_h7_schwab_window_registration.py:541-566`) traps both resolution paths.

**Receipt side — CONFIRMED consistent.** `tools/h7_schwab_feasibility.py:137-138` records `source_paths` and
`source_hash` over the constant; `tests/test_h7_schwab_feasibility.py:105` pins equality;
`test_feasibility_refuses_when_bound_signal_source_changes` still mutates `h7_signals.py`, which is inside the surface.

**Tests at head:** 35/35, 9/9, 8/8 on the three affected modules; ruff clean; pyright 0.

## Fixes (LOW) → applied at `fee356f`
- **N1** — parent-package `__init__.py` files executed on import were outside the surface (`options_researcher/studies/__init__.py`,
  0 bytes). Fix: `_ancestor_packages()` binds every ancestor `__init__.py`; constant now 50 paths; synthetic test covers a nested package.
- **N2** — only the hash-mismatch refusal had a test. Fix: `test_feasibility_refuses_a_receipt_listing_a_different_source_surface`
  and `test_feasibility_refuses_when_a_bound_source_file_is_missing` (receipt re-sealed so the tamper check cannot mask the refusal under test).
- **N3** — synthetic walker test never exercised dotted `import a.b`. Fix: `import data.e` added.

## F6, quantified (OWNER DECISION — the brief does not forbid the closure)
Brief W3 freezes "the extended feasibility tool module plus the modules it imports for the measurement" and forbids only
`diagnostic_source_hash` (whole-package surface). The transitive closure is the literal reading of W3. Breadth: 49 of 163
`.py` files (30%) across the five packages, including `intraday_capture.py`, `live_quotes.py`, `schwab_adapter.py`,
`h7_data_gate.py`, `features.py`, `h7_watch.py`, and the validator itself. Over the last 60 days those files were touched by
141 commits on 38 distinct days — roughly two of every three working days would invalidate a qualifying receipt and force
re-measurement. The constant's comment discloses the trade but not the number; the owner should rule with this number in hand
(keep the honest upper bound, or amend the brief to a narrower reviewed surface).

## Round-3 non-blockers re-checked
F3 (no recompute-vs-sidecar numeric disagreement signal, `h7_schwab_quote_age_gate.py:96-98`) — still open.
F5 (no end-to-end test feeding `summarize_counts` output through `_validate_feasibility`) — still open. No regression.

## Not checked
Full suite by the reviewer (orchestrating session ran it: 3683 OK at `8fa4085`; rerun at `fee356f` recorded in the PR
thread). F4, F7–F10. Runtime behaviour of the measurement. Minimality of the surface (static reachability is an upper bound).

## Disposition
PR #147 may leave DRAFT for owner review once the `fee356f` suite run is green. Owner items before merge: rule on F6's
breadth; decide whether F3/F5 are pre-merge or follow-up. After merge: regenerate cohort-9 feasibility + source-health +
data-gate receipts at the post-merge config; owner runs the activation CLI (bar 7, OD-3 line, pre-acceptance).
