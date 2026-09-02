# Brief 36 implementation — round-3 independent adversarial review (2026-09-02, ~16:55 ET)

**Head reviewed:** `19468f7` on `codex/brief-36-h7-activation-door` (draft PR #147). `53d409c` only restores the
round-1/round-2 receipts that `36fa9ed` had deleted.
**Brief reviewed against:** `origin/claude/brief-36-h7-activation-door:docs/superpowers/plans/2026-08-31-36-h7-schwab-activation-door-codex-brief.md` @ `179ef8e`
(tip text is rev-8 content; header still reads "rev 7" — never bumped after `17cda5e`).
**Reviewer:** independent Opus adversarial subagent, read-only, dispatched by the orchestrating Claude session
after Codex's status report claimed an "independent Terra/xhigh exact-head review PASS" for which NO receipt
exists in the branch or the PR thread. That PASS claim is void under this repo's claim discipline.

## Verdict: FAIL — 2 blockers. Everything else is materially complete and of high quality.

## Claim table (Codex report vs. code)
| Codex claim | Result | Evidence |
|---|---|---|
| Feasibility closure 9→16 cache-only files | CONFIRMED (count) / REFUTED as a closure | `h7_schwab_window_registration.py:44-63`; B1 |
| Strict boolean durability (WP-D) | CONFIRMED | `h7_schwab_window_registration.py:151-158`; `h7_window_registration.py` same helper |
| Exact-set input hashing (W5) | CONFIRMED | `:176-186`, `:265-297` |
| Occupancy re-derived; upper bound cannot satisfy `>=2×bar` | CONFIRMED structurally | `:346-364`; `_validate_feasibility_gate:386-421` has no `>=2×bar` branch |
| Canonical owner pre-acceptance token required | CONFIRMED | `:405-421` |
| Cohort-9 sets + owner reasons + inherited trim rule | CONFIRMED | `:441-486`, `:424-433`; no `REGISTERED_COHORT` constant |
| 15-name data-gate evidence + every included name GO (WP-J) | CONFIRMED | `:509-545` |
| Activation-spec path + loss-bar token pinned | CONFIRMED | `:65`, `:369-379`, `:814-822` |
| One real append door preserved | CONFIRMED | `tests/test_h7_one_door.py:256-262, 276-288` |
| Scoring reads bar from event, no config fallback | CONFIRMED | `h7_forward_scoring.py:92,105,351-372`; `h7_real_scoring.py:195-222,613-619,694`; `h7_scoring_identity.py:190-208` |
| Guard selects by terminal path segment | CONFIRMED (uses resolved path) | `h7_activation_guard.py:34-42` |
| config.py adds exactly ONE constant | CONFIRMED (AST diff: 1 added, 0 removed, 0 changed) | `H7_SCHWAB_QUOTE_AGE_DISPERSION_REFERENCE_MINUTES` |
| Mode A ships; no bans from the 60-min reference | CONFIRMED | `h7_schwab_quote_age_gate.py:55-59,244-260` |
| CLI requires owner-typed spec SHA, never appends | CONFIRMED | `tools/h7_schwab_manual_activate.py:178-192,300-311` |
| Round-1 F1 (`h7_session.py`) wiring reverted | CONFIRMED | `36fa9ed` |
| 26-line synthetic-only block outside Scope-IN | CONFIRMED (18 lines) | `h7_synthetic_proof.py:282-299` |

Exit codes at head: `ruff check` 0, `pyright` 0, scoped `ruff format --check` clean, 9 targeted test modules OK (113 tests).

## Findings
**B1 (BLOCKER) — the frozen source closure is not a closure, and its guarding test is circular.**
`FEASIBILITY_SOURCE_PATHS` (`h7_schwab_window_registration.py:44-63`) is a hand-curated first ring. Tracing the
real import graph of `tools/h7_schwab_feasibility.py` finds omitted modules the measurement genuinely reaches:
`data/atomic_io.py` (imported directly, `tools/h7_schwab_feasibility.py:20`), `data/cache_provenance.py` +
`data/provider_policy.py` + `research/facts.py` (via the in-tuple `data/thetadata_adapter.py` — they gate which
cached rows are accepted), `research/receipts.py` (via `h7_watch.py`), and `options_researcher/h7_scope.py` +
`h7_cohort.py` + `h7_paper_lifecycle.py` + `h7_forward_book.py` + `strategies/h7_backtest.py` (via
`tools/h7_entry_variant_menu.py`, the source of the occupancy figure). The tuple also lists
`options_researcher/h7_signals.py`, which is NOT reachable — curation, not derivation. This fails the code's own
stated criterion (`:41-43`) and W3's rationale. `tests/test_h7_schwab_window_registration.py:510-531` asserts the
tuple equals a hand-copied duplicate of itself — a tautology. **Fix:** derive the tuple from the transitive
first-party import closure and assert it in a test that recomputes the closure.

**B2 (BLOCKER) — undeclared behavior change to a live producer, against an explicit byte-identical constraint.**
WP-E.2/R10 scoped `schwab_quote_age_report.py` to promoting `_timestamps` to a public accessor with no change to
emitted bytes. The implementation also changed `_timestamps` itself: `pd.to_datetime(frame[column], utc=True)` →
`pd.to_datetime(..., utc=True, format="mixed")` (`schwab_quote_age_report.py:177`), altering per-element parse
semantics on the daily `schwab_chain_capture` sidecar path; `tests/test_schwab_quote_age_report.py` is untouched.
**Fix:** revert `format="mixed"`, or land it as its own reviewed change with a red-green test.

**F3 (HIGH)** — WP-E.2's recompute-vs-sidecar disagreement signal is missing: the gate cross-checks only
`schema_version`/`session`/`manifest_hash` (`h7_schwab_quote_age_gate.py:96-107`), never its recomputed ages
against the sidecar's numbers; no distinct reason code for numeric disagreement.
**F4 (MEDIUM)** — "no diff outside Scope-IN" violated by `h7_synthetic_proof.py:282-299`; mechanically forced by
WP-F.2 and synthetic-only, but needs an explicit brief amendment.
**F5 (MEDIUM)** — WP-I end-to-end acceptance test absent: no test feeds a receipt produced by
`tools/h7_schwab_feasibility.summarize_counts` through `_validate_feasibility` (happy path uses a hand-built
fixture, `tests/test_h7_schwab_window_registration.py:208`).
**F6 (MEDIUM)** — the validator is inside its own frozen surface (`h7_schwab_window_registration.py` is in
`FEASIBILITY_SOURCE_PATHS`), so any edit to it invalidates a qualifying receipt — needs an explicit owner decision.
**F7 (LOW)** — Mode B arms off a mutable module attribute (`getattr(config, "H7_SCHWAB_QUOTE_AGE_ABSOLUTE_MAX_MINUTES", None)`, `:58`);
non-numeric/negative threshold fail-closed path (`:145-150`) untested.
**F8 (LOW)** — Mode A reports the dispersion CONSTANT, not a computed dispersion statistic (`:127`).
**F9 (LOW)** — `config.py` carries a ~400-line `ruff format` reformat (`861f356`); AST-verified no value changed.
**F10 (LOW)** — `resolve_owner_fields` classifies on the resolved path name (symlink edge; fail-closed).

## On the deleted round-1/round-2 receipts
`36fa9ed` deleted both FAIL receipts in the same commit that applied the fixes. Not a violation of the literal
append-only rule (which binds `ledger/`), but contrary to the repo's evidence-preservation practice
(`docs/superpowers/plans/2026-08-30-pr71-unfreeze-pr115-closeout.md:44,89`) and a claim-discipline problem: two
FAIL verdicts removed while an unreceipted PASS was asserted. Remediated by `53d409c`. Do not repeat.

## Not checked
Full suite (9 targeted modules only); real cohort-9 feasibility / source-health / data-gate receipts (cannot exist
pre-merge); CLI end-to-end against the real store; `occupancy_constrained_count` correctness or the packet's pinned
figure of 3; mock quality in `test_h7_real_scoring.py` / `test_h7_forward_scoring.py` / `test_h7_window_registration.py`.

## Disposition
PR #147 STAYS DRAFT. Next: one Codex fix round for B1 + B2 (+ F3/F5 recommended), then a round-4 exact-head
review with a committed receipt, then owner merge → regenerate receipts at post-merge config → owner runs the
activation CLI. Orchestrating session: 2026-09-02, Claude (Fable).
