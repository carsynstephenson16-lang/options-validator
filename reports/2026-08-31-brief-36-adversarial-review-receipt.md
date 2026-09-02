# Brief 36 — independent adversarial review receipt

Committed evidence for the review rounds on
`docs/superpowers/plans/2026-08-31-36-h7-schwab-activation-door-codex-brief.md`
(rev-2 finding N6: a review that lives only in a session transcript is a
provenance gap — packet §7a precedent). Reviewer: independent Opus subagent,
adversarial framing ("show how this brief could be lying or dangerous"),
read-only, verifying every claim against `origin/main @ 1d83453`.

## Round 1 (2026-08-31, rev 1) — verdict FAIL

All file:line anchors verified clean; defects were semantic. Blockers:

- **B1** — WP-A's config-hash equality can never pass: the only receipt on
  file predates config changes, and WP-E's own new constant drifts the hash
  again (`research/hashing.py:71` hashes all uppercase config constants).
- **B2** — WP-A's universe check refuses the only receipt on file (15-name
  universe vs the registered cohort-9).
- **B3** — the owner-typed loss bar 7 never reaches the event: the builder
  hardcodes `config.MIN_LOSSES_FOR_VERDICT` (=10) into the scorer block and
  scoring-identity hash (`h7_schwab_window_registration.py:321-325`), and no
  owner field for the bar exists.
- **B4** — WP-C wired the quote-age gate into pre-registration checks,
  contradicting packet row 7 ("Not a gate on this registration"), and the
  gate fails closed on a sidecar artifact that exists for zero sessions.
- **B5** — the activation guard checks the legacy ThetaData `OWNER_FIELDS`
  (`h7_activation_guard.py:16`, `:197`); the Schwab flow can never satisfy
  them, and the brief forbade the fix without providing the sanctioned
  scope-keyed alternative.

Majors M1–M7 (pre-acceptance quotes 3, not 4.0; `register_window_real`'s real
signature unstated; OUT list named the wrong ledger path; Scope-IN vs one-door
test contradiction; no receipt-vs-now reconciliation; OD-3 field does not
exist; review-before-merge clause missing) and minors m1–m5 + NIT recorded in
the session transcript. Also verified sound: WP-D is safe for the existing
seq-0 event (its stored `darwin_durability_verified` is JSON `true`; no
replay path rebuilds historical events through the builders).

## Round 2 (2026-08-31, rev 2) — verdict FAIL

Rev 2 closed B4, M2, M3, M4, M6, M7, m1–m5, NIT properly. New blockers:

- **N1** — the bar was fixed in the event but not the scorer: the verdict
  gate applied at scoring time is `config.MIN_LOSSES_FOR_VERDICT` at
  `h7_forward_scoring.py:102` (re-stamped at `:451` and
  `h7_real_scoring.py:1809`), so a 7-bar registration would verdict at 10 —
  a recorded contradiction.
- **N2** — the ordering section's "fresh cohort-9 receipt" step had no
  producer: `tools/h7_schwab_feasibility.py` hardcodes the 15-name universe
  (`:234`), has no cohort flag (`:226-232`), and emits no `input_files`
  (`:67-95`); the tool named (variant menu) emits the wrong receipt kind.
- **N3** — WP-B's exact-equality compared different quantities: the tool's
  `expected_entries` (`:66`) is unconstrained (4.0); the owner's
  pre-acceptance quotes the occupancy-constrained 3 — a refusal loop by
  construction with the quantity never pinned.

Majors: **N4** (caller-named scope id reopens the narrowing hole; guard
already derives `scope_identity()` internally at `:130`), **N5** (producer
marker write could break the deliberately fail-soft capture path; marker name
could match the sidecar glob), **N6** (this receipt file was cited before it
existed). Minors n1–n4 (OD-3 phrase check rubber-stampable;
`test_h7_schwab_data_gate.py` missing from Scope-IN; owner-field naming
convention; plan-WP ↔ brief-letter mapping for the rulings text).

## Round 3 (2026-08-31, rev 3) — verdict FAIL (one blocker; nothing structural)

Rev 3 closed N3, N5, N6, n1–n4 cleanly; its factual anchors verified true,
including WP-F.2's backward-compatibility claim (seq-0 carries
`frozen.scorer.min_losses_for_verdict = 10`). Remaining findings, all
wrong-pointer / understated-scope:

- **P1 (blocker)** — keying WP-G off `scope_identity()` cannot work: it is a
  pure function of the symbol universe (`h7_scope.py:57-60`) with no
  namespace/store concept, so both lanes resolve to one key and B5 reopens.
  Correct key: `forward_base` (the store path, kwarg at
  `h7_activation_guard.py:69`).
- **P2 (major)** — `map_forward_verdict(board)` (`h7_forward_scoring.py:92`)
  never sees the event; the bar must arrive as a required parameter threaded
  by both production callers (`:124`, `h7_real_scoring.py:1600`); `:451` and
  `:1809` are provenance stamps, not gates; `tests/test_h7_forward_scoring.py:428-444`
  affected.
- **P3 (major)** — the reusable occupancy function is
  `occupancy_constrained_count` at `tools/h7_entry_variant_menu.py:354`
  (invoked `:727-728`); the v9 file only reads a precomputed value.
- **P4/P5/P6 (minor)** — quantity-name consistency in WP-B; sidecar naming
  conventions live in `schwab_quote_age_report.py:122-135`; scoring/legacy
  test files named by path in Scope-IN.

Reviewer's closing assessment: a rev 4 applying P1–P6 is expected to pass on
a targeted spot-check of those six points rather than a full fourth round;
WP-D independently landable.

## Round 4 (2026-08-31, rev 4) — targeted spot-check of P1–P6

Rev 4 applies all six: WP-G keyed off `forward_base` with
unrecognized-store refusal; WP-F.2 rewritten as the required-parameter
threading with stamps handled separately and the test file in scope; WP-I.3
cites `tools/h7_entry_variant_menu.py:354`; WP-B uses the
occupancy-constrained name in both places; WP-E.4 cites
`schwab_quote_age_report.py:122-135`; Scope-IN names the three test files by
path. Spot-check verdict recorded below.

- Spot-check verdict: **PASS WITH FIXES.** All six P-fixes independently
  re-verified at exact anchors; no new defects; receipt transcription of all
  three prior rounds confirmed faithful ("no round's verdict is softened, and
  no finding is recorded as closed that I did not close"). Remaining items
  Q1 (WP-G acceptance vocabulary: unrecognized-STORE refusal;
  scope-vs-store mismatch defined as the receipt's `scope_identity()`
  disagreeing with the store being activated), Q2
  (`tests/test_h7_schwab_feasibility.py` added to Scope-IN by path), Q3
  (this line) — all applied in the same commit as this entry; reviewer:
  "neither can produce a defective implementation … neither warrants a fifth
  review round." Standing conditions restated: WP-D independently landable;
  the implementation PR requires its own independent adversarial review
  before the owner considers merging; this brief authorizes no registration —
  owner fields, receipt regeneration, and merge remain with the owner.

## Round 5 (2026-09-02, rev 5) — PR #142 Codex-bot findings, Opus-verified

After PR #142 was readied, the chatgpt-codex-connector bot posted 9 inline
findings (C2–C10). Per claim discipline, each was independently verified by
an Opus adversarial pass against `origin/main @ 1d83453` before any brief
change: **8 VALID, 1 PARTIALLY VALID (C9 — the sidecar IS manifest-hash-bound;
the real gap was that the gate never checked the binding), 0 INVALID.** Six
findings were independently corroborated by the in-flight Codex
implementation (branch `codex/brief-36-h7-activation-door`), which had to
edit files outside Scope-IN (`h7_scoring_identity.py`, a
`_validate_data_gate_receipt` rewrite), add an unsanctioned `OWNER_FIELDS`
entry, monkeypatch a "frozen" mapping in five test files, and invent
normalization arithmetic — its own round-1 review FAILED with blockers
matching C3/C4.

Applied in rev 5: C2 (absolute-age metric; gate reports both numbers and
blocks on neither until the OWNER re-confirms the 60-min threshold against
absolute ages — ruling 3's 0-of-7 evidence was measured on the dispersion
metric); C3 (WP-G reclassified by terminal path segment, no
unrecognized-store refusal, no patchable mapping); C4 (WP-E honestly labeled
consumer-less; wiring is a named successor); C5 (WP-F.3:
`h7_scoring_identity.py` in scope, required runtime-identity argument, no
config fallback); C6 (second sanctioned owner field
`SCHWAB_STARVATION_RISK_PREACCEPTANCE`, persisted verbatim); C7 (WP-I refuses
lookback≠window, records `occupancy_lockout_sessions`=42, WP-A re-derives);
C8 (WP-C.1 requires explicit cohort-9 `universe_manifest`; new WP-J
reconciles the all-15 data-gate scope closure with a 9-name registration via
the Option-C full-scope-evidence precedent, `h7_data_gate.py` untouched);
C9 (gate verifies session + `manifest_hash` binding, fail-closed); C10 (new
Schwab activation spec doc in scope, ships UNSIGNED for owner review; CLI
refuses specs outside `docs/superpowers/specs/`).

Owner items created by this round: (1) re-confirm or retype the quote-age
threshold against the ABSOLUTE age metric before the gate may block; (2)
review and freeze the new Schwab activation spec before any real run.
