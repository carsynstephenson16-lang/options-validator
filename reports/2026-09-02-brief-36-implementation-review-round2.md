# Brief 36 implementation — round-2 independent adversarial review receipt (2026-09-02)

**Reviewer:** fresh Opus instance, read-only, in-worktree test execution only.
**Object:** `codex/brief-36-h7-activation-door` @ e3bf887 (Codex implementation 8 commits + round-1 fix round 12 commits), PR #147.
**Brief text reviewed against:** `claude/brief-36-h7-activation-door` **rev 7** (the branch moved from rev 3 → rev 8 between 01:29 and 02:08 ET on 2026-09-02, in a concurrent session applying the PR #142 review-bot waves; round 1 and the fix round were executed against rev 3).
**Verdict:** **FAIL** — 4 blockers, 6 majors. Gates green (Test-verified: 3680 OK / skipped 5 / exit 0; ruff 0; pyright 0; `ledger/` diff 0 lines). The failures are brief-conformance against rev 7, not test-conformance.

## Blockers (verbatim from the reviewer)

**B1 — WP-E is built in exactly the form rev 7 forbids.** Rev 7 WP-E.1: the 60 lands as a NON-BLOCKING display constant (`H7_SCHWAB_QUOTE_AGE_DISPERSION_REFERENCE_MINUTES`) that "may not gate anything"; the blocking constant `H7_SCHWAB_QUOTE_AGE_ABSOLUTE_MAX_MINUTES` does not exist until the owner re-rules and types it. Implementation: `config.py:693-697` `H7_SCHWAB_MAX_SELECTABLE_QUOTE_AGE_MINUTES = 60` used as the blocking threshold by `h7_schwab_quote_age_gate.py:76-84`; no `AWAITING_OWNER_THRESHOLD` verdict exists (Mode A absent). WP-E.2 requires the decision statistic be recomputed from manifest-bound chain bytes with the sidecar display-only; the implementation's decision input IS the sidecar's dispersion metric (`gate:187-190`). `schwab_quote_age_report.py` untouched. Missing sidecar fails the whole board closed where rev 7 Mode A says it is reported, not blocking.

**B2 — WP-I(a): the banned occupancy arithmetic survived and was promoted.** Rev 7: the CLI must REFUSE `--lookback-sessions != --window-sessions`; the `count × window / len(sessions)` scaling "must not survive the fix round." `tools/h7_schwab_feasibility.py:102` still computes it; argparse `:291-300` has no equality refusal; the F6 fix hardened the formula into the validator at `h7_schwab_window_registration.py:245-252`.

**B3 — The activation spec does not exist and the CLI does not pin it.** Rev 7 Scope-IN / WP-C.1 require `docs/superpowers/specs/2026-09-02-h7-schwab-activation-spec.md` and a module-constant pin refusing any other `--activation-spec` (incl. the 2026-07-19 legacy spec, by explicit test). `tools/h7_schwab_manual_activate.py:334` passes `args.activation_spec` freely; only the owner-typed hash is compared (`:230-232`). WP-F.1's `schwab_min_losses_for_verdict=7` spec-token check therefore also unimplemented.

**B4 — WP-A closures W5 and C8/R9 absent.** `_validate_feasibility:167-208` hashes only what the receipt lists (the circularity W5 closed); no `research.hashing.source_hash(paths=...)` code-surface binding and no frozen canonical-surface tuple.

## Majors
- **M1** WP-J R7 not implemented: `_validate_data_gate_receipt:336-357` demands whole-universe GO (15/15, no NO_GO); rev 7 requires per-included-name GO so a NO_GO on an EXCLUDED name still registers.
- **M2** WP-G mechanism substituted: `resolve_owner_fields` keys on `data_gate_result["evidence_mode"]`, not `Path(forward_base).name`. Patch sites are zero and both real stores refuse the other lane's evidence (Repo-verified), but on a non-real store a caller still selects the field set by choosing evidence.
- **M3** Cohort is a `config.py` constant (`H7_SCHWAB_REGISTERED_COHORT`, `..._EXCLUSION_REASONS`); rev 7 WP-C.1 requires owner-typed at use time with the W2 seq-0 ledger SET pin. Values are correct (seq-0 `universe.included` = AMD AMZN CEG ET MSFT NOW PLTR TEM VST; six excluded `EARNINGS-UNKNOWN`; packet lines 94/264 agree).
- **M4** CLI forwards `max_report_age_s` (rev 7 C11 forbids exposing it) and calls `register_window_real` without an explicit `universe_manifest` (C8 requires it).
- **M5** WP-B upper-bound branch live: `_validate_feasibility_gate:262-263` passes on `expected >= 2*bar`, which WP-I(d)/WP-B require unreachable with any WP-I receipt.
- **M6** Diff outside Scope-IN: `options_researcher/h7_session.py` (+57), `options_researcher/h7_synthetic_proof.py` (+26).

## Minor
OD-3 / row-7 prose matched inside `H7_STAGE8_EXPLICIT_AUTHORIZATION` not `SCHWAB_STARVATION_RISK_PREACCEPTANCE`; `runtime_scoring_identity` passes `allow_zero=True`; `_schwab_quote_age_board` returns `None` silently on evidence-mode mismatch (omission invisible; forgery impossible via hash-sealed receipt); scoped `ruff format --check` newly dirties `h7_synthetic_proof.py` and `schwab_chain_capture.py`.

## Genuinely closed (re-derived by the reviewer)
F2 (patch sites zero), F3 (bar keyword-only, no default; `None` → `ScoringIdentityError`), F4 (registration selected by `event_type`, refuses ≠1), F5, F6-lockout (bound by test to `OCCUPANCY_LOCKOUT_SESSIONS[0]`), F7 (single identity definition, end-to-end tool-receipt test), F8 (real `score_forward_window` asserts 7 while config ≠ 7), F10 values, ledger untouched, config-name guard honest. No validator weakened to accept pre-merge receipts.

## Reviewer's "how this could be lying"
`open_real_session` defaults to the LEGACY store `ledger/h7_forward`; the Schwab window lives in `ledger/h7_forward_schwab`, which no session consumer reads, and the guard refuses Schwab evidence against the legacy store — so the round-1 F1 wiring fires only for a combination the rest of the PR declares illegitimate. Rev 7 itself says WP-E ships "with no production caller … wiring it into the Schwab arming path is a named successor work package." Round-1 F1 was therefore a mis-finding against the rev-7 text (it was raised against rev 3), and its fix cost an out-of-scope edit to `h7_session.py`.

## Disposition (orchestrating session, 2026-09-02 ~02:15 ET)
PR #147 stays **DRAFT**. No third round tonight: the brief moved four revisions during this session and is owned by a concurrent session; a fix round against a moving target would repeat this round's failure mode. Next: whoever owns the Brief 36 lane runs ONE fix round against the **final** brief revision (rev 8 @ d4fc1c4 or later), explicitly reverting the round-1 F1 wiring (`h7_session.py`), replacing the blocking 60 with Mode A, adding the activation spec + CLI pin, the lookback==window refusal, W5/C8 bindings, WP-J per-included-name GO, and moving the cohort to owner-typed-at-use; then a fresh round-3 review.
