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
