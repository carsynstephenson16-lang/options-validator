Independent adversarial review, round 1, 2026-09-02, fresh Opus instance, branch codex/brief-36-h7-activation-door @ 8107273. Verdict FAIL (2 blockers). Suite 3658 OK / ruff 0 / pyright 0 at review time.

# Brief 36 implementation — round-1 adversarial review receipt

Brief under review:
`docs/superpowers/plans/2026-08-31-36-h7-schwab-activation-door-codex-brief.md`
(on `claude/brief-36-h7-activation-door`), with its own pre-hand-off review
receipt at `reports/2026-08-31-brief-36-adversarial-review-receipt.md`.

All anchors below are Repo-verified at `8107273` unless labeled otherwise.

## Findings (verbatim)

F1 — BLOCKER (WP-E). The "blocking gate" has zero production callers. `evaluate_schwab_quote_age` in `options_researcher/h7_schwab_quote_age_gate.py:76` is referenced only by itself and `tests/test_h7_schwab_quote_age_gate.py:70`. `options_researcher/entry_watch.py`, `h7_watch.py`, and `h7_entry_preflight.py` contain no `quote_age` reference. A function nobody calls cannot ban a name from arming. WP-E is a library, not a gate.

F2 — BLOCKER (WP-G). The guard now refuses every store not in the frozen map, and five test files monkeypatch that map to work around it. `h7_activation_guard.py:114-117` raises `unrecognized forward store` for any base absent from `OWNER_FIELDS_BY_STORE`. Synthetic/temp stores are absent, so `tests/test_h7_activation_guard.py:23-26`, `test_h7_trim_at_append.py:80, 342`, `test_h7_stage8_synthetic.py:57`, `test_h7_one_door.py:422`, `test_h7_schwab_manual_activate.py:132` all `patch.object(ag, "OWNER_FIELDS_BY_STORE", mapping)`. (a) The brief's "legacy store's behavior must be byte-for-byte unchanged" is violated — synthetic-store guard runs that worked on main now raise; (b) the sole owner-field gate is a module attribute any in-process code replaces wholesale — functionally the rejected `owner_fields` parameter relocated to a patch point. Also `:118` narrowed the real-store test from `base == real or real in base.parents` to exact membership; a subpath now falls to the unrecognized branch (fail-closed, but the containment check is gone).

F3 — MAJOR (WP-F). `h7_scoring_identity.py:201-217` `runtime_scoring_identity(*, min_losses_for_verdict: int | None = None)` falls back to `config.MIN_LOSSES_FOR_VERDICT` when omitted. Brief: "refusing to score when the event lacks the field (no config fallback)". `tests/test_h7_real_scoring.py:1190` and `test_h7_scoring_identity.py:51, 80` exercise the fallback.

F4 — MAJOR (WP-F). `h7_real_scoring.py:1185-1190` `_frozen_market_result` appends `_copy_event(events[0], [])` into a temp ledger assuming `events[0]` is the `window_registration` without checking. If ordering changes it raises or scores under the wrong bar.

F5 — MODERATE (WP-B). `h7_schwab_window_registration.py:230-234` raises with only the receipt's number; the brief requires both numbers (receipt figure AND the owner's quoted pre-acceptance value) in the error.

F6 — MODERATE (WP-I/WP-A). `tools/h7_schwab_feasibility.py:95` `occupancy_expected = occupancy_count * window_sessions / len(sessions)` is new LLM-authored arithmetic and the ONE receipt number `_validate_feasibility` does not re-derive (`h7_schwab_window_registration.py:203-211` only checks `0 <= occupancy <= expected`); `base_rate` and `expected_entries` ARE re-derived. Also `OCCUPANCY_LOCKOUT_SESSIONS[0]` is a bare index and the validator never checks recorded `occupancy_lockout_sessions` against the registered value.

F7 — MODERATE (WP-I). No test proves a tool-produced receipt passes `_validate_feasibility` end-to-end. `stack_version`/`tool_label` are duplicated literals in `tools/h7_schwab_feasibility.py:34, 102` vs `h7_schwab_window_registration.py:42-43` with no binding test.

F8 — MINOR (WP-F). No test asserts `score_forward_window(...)["frozen"]["min_losses_for_verdict"] == 7` while `config.MIN_LOSSES_FOR_VERDICT == 10`, nor the equivalent on the real-scoring receipt.

F9 — MINOR (scope creep). `_validate_data_gate_receipt` `:281-302` changed from cohort-9 to full-official-scope comparison; `score_forward_window` `:400-406` gained a refusal when requested window != registered window. Defensible tightenings, but undocumented — document them in the receipt/commit, don't revert.

F10 — MINOR. `REGISTERED_COHORT` (9 names) and blanket `"EARNINGS-UNKNOWN"` exclusion reason hardcoded at `h7_schwab_window_registration.py:40-42, 245-247`.

## Fix round 1 (2026-09-02)

Implemented in this worktree on `codex/brief-36-h7-activation-door`, one
commit per finding, each test-first (failing test recorded before the fix).
Gates at the end of the round: `uv run python -m unittest discover -s tests`
**exit 0** (3680 tests, 5 skipped), `uv run ruff check .` **exit 0**,
`uv run pyright` **0 errors**.

| Finding | Commit | Files | Tests | What changed |
| --- | --- | --- | --- | --- |
| F1 (BLOCKER) | `9429b49` | `options_researcher/h7_session.py`, `tests/test_h7_session_real_path.py` | `TestSchwabQuoteAgeArmingGate.test_fresh_quotes_arm_and_stale_name_is_entry_banned`, `…test_missing_sidecar_refuses_the_whole_schwab_board`, `…test_unreadable_sidecar_refuses_the_whole_schwab_board`, `…test_legacy_thetadata_lane_never_consults_the_quote_age_gate` | `evaluate_schwab_quote_age` is now called by `open_real_session` — the one arming door the entry preflight and every real session go through — for Schwab-evidence data-gate receipts only: board-level fail-closed on missing/unreadable/mismatched sidecar, per-name entry ban over threshold (v1.4 precedent), legacy ThetaData lane untouched. |
| F2 (BLOCKER) | `96b2bd6` | `options_researcher/h7_activation_guard.py`, `tests/test_h7_activation_guard.py`, `tests/test_h7_trim_at_append.py`, `tests/test_h7_stage8_synthetic.py`, `tests/test_h7_one_door.py`, `tests/test_h7_schwab_manual_activate.py` | `GuardTests.test_synthetic_store_resolves_legacy_fields_without_any_patching`, `…test_synthetic_store_with_schwab_evidence_resolves_schwab_fields`, `…test_owner_field_set_cannot_be_supplied_or_named_by_a_caller`, `…test_schwab_evidence_cannot_activate_the_legacy_real_store`, `…test_legacy_evidence_cannot_activate_the_schwab_real_store`, `…test_a_subpath_of_either_real_store_is_still_boundary_guarded` | `OWNER_FIELDS_BY_STORE` deleted; `resolve_owner_fields(base, data_gate_result)` is a pure function of store path + data-gate `evidence_mode`. Legacy/absent evidence ⇒ legacy tuple (main's behavior for every synthetic and legacy store); Schwab evidence ⇒ Schwab tuple with no patching; each real store refuses the other lane's evidence; pre-branch `base == real or real in base.parents` containment restored and now applied to BOTH real stores. All five `patch.object(ag, "OWNER_FIELDS_BY_STORE", …)` sites removed. |
| F3 (MAJOR) | `acebc3a` | `options_researcher/h7_scoring_identity.py`, `tests/test_h7_scoring_identity.py`, `tests/test_h7_real_scoring.py` | `test_runtime_identity_refuses_a_missing_registered_loss_bar` | `runtime_scoring_identity(min_losses_for_verdict=…)` is required (omission = `TypeError`, `None` = named `ScoringIdentityError`); the `config.MIN_LOSSES_FOR_VERDICT` fallback is gone and the two tests that relied on it now pass the bar explicitly. |
| F4 (MAJOR) | `4fb069d` | `options_researcher/h7_real_scoring.py`, `tests/test_h7_real_scoring.py` | `TestRealScoringAuthority.test_frozen_market_scoring_selects_the_registration_explicitly` | `_frozen_market_result` selects the event with `event_type == "window_registration"` and refuses (named error) unless there is exactly one, instead of assuming `events[0]`. |
| F5 (MODERATE) | `6d3e89a` | `options_researcher/h7_schwab_window_registration.py`, `tests/test_h7_schwab_window_registration.py` | `BuilderTests.test_preacceptance_mismatch_names_both_numbers` | The pre-acceptance refusal prints the receipt's occupancy-constrained figure AND the number(s) the owner's text quotes (`no number` when it quotes none). |
| F6 (MODERATE) | `1c4885e`, `410cfe8` | `config.py`, `tools/h7_schwab_feasibility.py`, `options_researcher/h7_schwab_window_registration.py`, `tests/test_h7_schwab_feasibility.py`, `tests/test_h7_schwab_window_registration.py`, `tests/test_ritual_switch_on_hash_containment.py` | `test_occupancy_inputs_are_recorded_for_independent_rederivation`, `test_registered_lockout_constant_matches_the_menu_derivation`, `test_validator_refuses_a_forged_occupancy_projection`, `test_validator_refuses_an_unregistered_lockout` | Receipt records `occupancy_constrained_count` beside `lookback_sessions`; `_validate_feasibility` re-derives `count × window_sessions ÷ lookback_sessions` and refuses on mismatch; the bare `OCCUPANCY_LOCKOUT_SESSIONS[0]` index is replaced by `config.H7_SCHWAB_REGISTERED_OCCUPANCY_LOCKOUT_SESSIONS` (schedule-derived, NOT owner-typed; a test binds it to the menu's own derivation) and the validator refuses a receipt recording any other lockout. |
| F7 (MODERATE) | `b3cd546` | `options_researcher/h7_schwab_window_registration.py`, `tools/h7_schwab_feasibility.py`, `tests/test_h7_schwab_feasibility.py` | `test_stack_and_tool_identity_have_one_definition`, `ToolReceiptPassesTheRegistrationValidatorTests.test_tool_receipt_validates` | `FEASIBILITY_RECEIPT_KIND` / `_STACK_VERSION` / `_TOOL_LABEL` are defined once in the validator module and imported by the tool (`assertIs` on all three); a new end-to-end test builds a receipt through `summarize_counts` and feeds it to `_validate_feasibility`. |
| F8 (MINOR) | `ff0c86a` | `tests/test_h7_forward_scoring.py`, `tests/test_h7_real_scoring.py` | `test_frozen_bar_is_the_registered_one_not_config`, `test_receipt_publishes_the_registered_bar_not_the_runtime_config` | Pins WP-F's headline claim in both scorers: the published frozen bar is the registered 7 while `config.MIN_LOSSES_FOR_VERDICT` is not 7; both tests were confirmed red against the pre-fix `config.MIN_LOSSES_FOR_VERDICT` publication sites. |
| F9 (MINOR, document-only) | this receipt | — | — | **Not reverted; recorded as deliberate tightenings.** (a) `_validate_data_gate_receipt` now compares the Schwab data-gate receipt against the FULL official scope (`universe`, `go_count`, verified symbols) rather than the 9-name cohort: the registration cohort SELECTS from whole-scope evidence and never narrows the evidence itself, which is the same anti-cherry-pick rule the trim-at-append guard states. (b) `score_forward_window` refuses when the requested window differs from the registered window's `start_decision_session` / `final_decision_session`, so a scoring run cannot quietly re-cut the registered window. Both are refusal-only: they can reject inputs the previous code accepted, never accept inputs it rejected. |
| F10 (MINOR) | `0031564`, `410cfe8` | `config.py`, `options_researcher/h7_schwab_window_registration.py`, `tests/test_h7_schwab_window_registration.py`, `tests/test_h7_schwab_feasibility.py`, `tests/test_ritual_switch_on_hash_containment.py` | `test_cohort_and_exclusion_reasons_come_from_config`, `test_an_unrecorded_exclusion_reason_refuses` | Cohort moved to `config.H7_SCHWAB_REGISTERED_COHORT` with provenance (legacy `ledger/h7_forward/events.jsonl` seq 0 `payload.universe.included`, quoted "Inherited-registered" in the 2026-08-15 bar-7 packet); exclusion reasons are now a per-name map transcribed from that same seq-0 event's `universe.excluded` (all six read `EARNINGS-UNKNOWN` there, so the honest per-name transcription is uniform today), and the manifest builder REFUSES to exclude a name with no recorded reason. |

### Consequences the owner must know

- **Three new `config.py` names** (`H7_SCHWAB_REGISTERED_OCCUPANCY_LOCKOUT_SESSIONS`,
  `H7_SCHWAB_REGISTERED_COHORT`, `H7_SCHWAB_REGISTERED_COHORT_EXCLUSION_REASONS`)
  change `config_hash()` and the diagnostic source hash on top of WP-E's
  threshold constant. This is the invalidation the brief's ordering section
  already requires: regenerate the qualifying feasibility, source-health and
  data-gate receipts AT the merged config before running the activation CLI.
  No validator was weakened to accept pre-merge receipts.
- **The feasibility receipt shape changed** (`occupancy_constrained_count` is
  now required and validated). The historical 2026-08-11 receipt cannot
  satisfy the validator — by design, per the same ordering section.
- Nothing in this round appends to any ledger, adds FIRE capability, touches a
  live-order path, or introduces a number outside `config.py`.
