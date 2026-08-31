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

## Round 3 (2026-08-31, rev 3) — verdict recorded below after the round

Rev 3 applies N1–N6 and n1–n4: WP-F gains the scorer half
(read-bar-from-registered-event, no config fallback) with
`h7_forward_scoring.py`/`h7_real_scoring.py` in scope; new WP-I extends
`tools/h7_schwab_feasibility.py` (cohort argument, `input_files` hashes, both
expected-entries figures labeled); the ordering section pins the
occupancy-constrained quantity and names the mismatch-⇒-owner-retypes path;
WP-G keys off the guard's internal `scope_identity()`; WP-E.4 constrains the
marker write (nested try/except, non-glob-matching name, capture-still-exits-0
test); this receipt exists and is committed with the brief.
