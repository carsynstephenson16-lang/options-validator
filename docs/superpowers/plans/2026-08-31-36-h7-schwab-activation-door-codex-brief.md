# Brief 36 — H7 Schwab activation door, rebuilt on main

**Date:** 2026-08-31, rev 7 2026-09-02 (rev 1 FAILED review with blockers
B1–B5; rev 2 FAILED with N1–N6; rev 3 FAILED with P1–P6; rev 4 PASS WITH
FIXES; rev 5 applied the first bot wave C2–C10 after independent Opus
verification — 8 VALID, 1 PARTIALLY VALID, 0 INVALID; rev 6 applied the
second bot wave of 11 findings incl. the process catch that rev 5's final
text was never itself re-reviewed; rev 7 applied the final-text review's
R1–R11 + nits, delta re-read PASS, residuals D1–D3 folded in — all rounds
transcribed in `reports/2026-08-31-brief-36-adversarial-review-receipt.md`,
committed with this brief. The in-flight Codex implementation predates revs
5–7; its fix round must re-align to this text.)

**WP mapping for the owner's ruling text** (the 2026-08-31 rulings file cites
the PLAN's numeric WPs): plan WP-1→brief WP-A · WP-2→WP-B · WP-3→WP-C ·
WP-4→WP-D · WP-5→WP-E · WP-6→WP-H; brief WP-F/WP-G/WP-I/WP-J are
review-driven additions beyond the plan.
**Author:** Claude orchestrating session (PR #71 unfreeze arc; plan:
`docs/superpowers/plans/2026-08-30-pr71-unfreeze-pr115-closeout.md`)
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** READY FOR HAND-OFF — final-text review of rev 6 PASS WITH FIXES
(round 7, all R-fixes applied as rev 7) + delta re-read of rev 7 PASS with 3
cosmetic residuals D1–D3, applied in this revision; full trail in
`reports/2026-08-31-brief-36-adversarial-review-receipt.md`
**Provenance:** Repo-verified against `origin/main` @ `1d83453` unless labeled
otherwise.

## Why this exists (plain language)

PR #71 (`codex/h7-schwab-recovery`, closed 2026-08-31 per owner ruling 2) built
the owner-confirmed command that performs the real H7 Schwab window
registration, but it froze 2026-08-11 and main superseded its foundations. The
owner has given the final go on registering the bar-7 V0 forward window
(ruling 1, `reports/2026-08-31-owner-rulings-h7-unfreeze.md`), so the missing
piece is a trustworthy activation door built on TODAY's main. Findings this
brief closes:

- **Codex-bot P1** (PR #71 review, 2026-08-24): `_validate_feasibility` never
  rehashes the measurement inputs — a stale qualifying receipt could register
  a window against data that no longer matches what produced it.
- **Codex-bot P2** (same review, misanchored at the CLI; actual defect
  Repo-verified in the BUILDERS on main):
  `bool(evidence["darwin_durability_verified"])` at
  `options_researcher/h7_schwab_window_registration.py:391` AND
  `options_researcher/h7_window_registration.py:243` records the string
  `"false"` as `true`. Live today; the second module built the existing seq-0
  registration (whose stored value is a genuine JSON `true` — Repo-verified —
  so the strict fix refuses no existing data).
- **Brief 32 round-3 finding F2** (quoted in packet row 7): a caller of
  `h7_schwab_data_gate.evaluate()` does NOT satisfy the quote-age obligation —
  a real blocking gate with the owner-typed threshold is required.
- **Rev-1 review B3**: the builder hardcodes
  `"min_losses_for_verdict": config.MIN_LOSSES_FOR_VERDICT` (=10) at
  `h7_schwab_window_registration.py:321-325` into the scorer and the
  scoring-identity hash — the owner-ruled bar for this window is 7, so an
  unmodified builder would register a window whose recorded verdict rule is
  wrong.
- **Rev-1 review B5**: `h7_activation_guard.py:16` imports the LEGACY
  ThetaData `OWNER_FIELDS` from `h7_window_registration` and checks them at
  `:197`. The Schwab door calls this guard, so the owner would be asked for
  ThetaData confirmations that cannot honestly exist (subscription ended
  ~2026-07-29) and every Schwab activation refuses forever.

## The ordering that makes this registrable (read first)

`config.py` is inside both `config_hash()` and the source hash
(`research/hashing.py:17-27`, `:71` — Repo-verified), so WP-E's new constant
invalidates EVERY existing receipt (feasibility, source-health, data-gate) the
moment it merges. The packet (§7 steps 3 and 7) anticipated exactly this.
Therefore the binding order is:

1. Land this brief's code (draft PR → adversarial review → owner merge).
2. Regenerate the qualifying receipts AT the new config: a fresh cohort-9
   feasibility receipt via `tools/h7_schwab_feasibility.py` AS EXTENDED BY
   WP-I (the tool on main today CANNOT produce it — it hardcodes the 15-name
   `watch_universe()` at `:234`, offers no cohort flag at `:226-232`, and its
   receipt `:67-95` carries no `input_files` hashes; rev-2 finding N2), plus
   fresh source-health and data-gate receipts in the operator flow.
3. Only then run the activation CLI.

The validator built here checks receipts against the config that exists WHEN
IT RUNS — it must NOT be weakened to accept the pre-merge receipts, and the
pre-merge receipts (e.g.
`reports/h7_forward_schwab/2026-08-11-feasibility-primary-earnings.json`,
15-name universe, old config hash) are historical evidence, NEVER the
qualifying receipt for this registration.

**The pinned quantity (rev-2 finding N3):** the number the owner's starvation
pre-acceptance priced is the **occupancy-constrained** expected-entries figure
(the packet §4 block quotes **3**, receipt-bound to
`V14_REGISTERED_COHORT_9.json`). The feasibility tool's current
`expected_entries = base_rate × window_sessions × len(symbols)`
(`tools/h7_schwab_feasibility.py:66`) is the UNCONSTRAINED figure — a
different quantity (4.0 on the 08-11 receipt). WP-I makes the receipt carry
both, explicitly labeled; WP-B's equality check runs against the
occupancy-constrained one ONLY. If the fresh occupancy-constrained number
differs from the 3 the owner's pre-acceptance quotes, the CLI STOPS and the
path forward is the owner retyping the pre-acceptance with the new number —
an owner decision by design, never a validator tolerance and never a silent
update of either side.

## Scope

**IN:**
- `options_researcher/h7_schwab_window_registration.py` (validator + builder)
- `options_researcher/h7_window_registration.py` (builder coercion fix only)
- `options_researcher/h7_forward_scoring.py` and
  `options_researcher/h7_real_scoring.py` (WP-F's read-bar-from-event change
  ONLY — see WP-F; rev-2 finding N1)
- `options_researcher/h7_scoring_identity.py` (WP-F.3 ONLY; rev-5 C5)
- NEW `docs/superpowers/specs/2026-09-02-h7-schwab-activation-spec.md`
  (WP-C's activation contract, ships UNSIGNED for owner review; rev-5 C10)
- `tools/h7_schwab_feasibility.py` (WP-I extension)
- `options_researcher/h7_activation_guard.py` (terminal-path-segment
  owner-fields classification ONLY, per WP-G)
- NEW `tools/h7_schwab_manual_activate.py` + NEW
  `tests/test_h7_schwab_manual_activate.py`
- NEW quote-age gate function/module per WP-E + `config.py` NON-BLOCKING
  display constant (WP-E.1) with owner-typed provenance
- `options_researcher/schwab_chain_capture.py` (WP-E.4's visibility fix ONLY —
  bounded to the sidecar skip path at `:368-378`)
- `options_researcher/schwab_quote_age_report.py` (final-review R10, WP-E.2
  ONLY: promote the private timestamp-coercion helper `_timestamps` (`:164`)
  to a public accessor — rename, behavior byte-identical; the module's own
  `:84-97` comment records exactly this accessor as a work package of the H7
  registration arc. No change to `sidecar_filename`, the report schema, or
  any emitted bytes; `tests/test_schwab_quote_age_report.py` stays
  untouched-green)
- `tests/test_ritual_switch_on_hash_containment.py` (final-review R11: its
  frozen snapshot of every uppercase `config.py` name gains exactly ONE
  entry — WP-E.1's sanctioned display constant — or the suite fails on any
  config addition by design)
- `tests/test_h7_one_door.py` (must gain coverage of the new CLI — its
  `test_cli_never_appends_directly` hardcodes only `tools/h7_manual_activate.py`
  at `:266`/`:380` today, Repo-verified)
- `tests/test_h7_schwab_window_registration.py`,
  `tests/test_h7_schwab_data_gate.py` (constructs Schwab owner dicts — breaks
  under WP-F otherwise; rev-2 finding n2),
  `tests/test_h7_forward_scoring.py` (bare-dict board cases at `:428-444`
  gain the bar parameter; round-3 P2/P6), `tests/test_h7_real_scoring.py`,
  `tests/test_h7_window_registration.py` (legacy WP-D half),
  `tests/test_h7_schwab_feasibility.py` (WP-I; round-4 Q2), and other
  existing test files the WPs name.

**OUT (executor over-reach stops here):**
- NO ledger writes and NO execution of any registration — including
  `ledger/h7_forward/*` AND `ledger/h7_forward_schwab/*` (the Schwab door's
  real store, `SCHWAB_FORWARD_STORE`, `h7_schwab_window_registration.py:35`).
  Tests use temporary stores only.
- NO authority flips, NO live-order paths, NO paper-mode changes.
- NO new numbers not already owner-typed. Single sources of truth: quote-age
  threshold = ruling 3 of `reports/2026-08-31-owner-rulings-h7-unfreeze.md`;
  loss bar 7 = owner ruling 2026-08-14
  (`reports/2026-08-14-owner-answers-decision-menu.md`) and enters the event
  ONLY as an owner-typed input per WP-F.
- NO caller-supplied owner-field lists anywhere (PR #71's `owner_fields`
  parameter was classified guardrail-loosening and stays dead). WP-G's frozen
  terminal-path-segment classification is the only sanctioned mechanism
  (final-review R6: no module-level mapping — see WP-G).
- NO modification of either module's `OWNER_FIELDS` tuple beyond what WP-F/WP-G
  specify; NO invented "OD-3 field" (see WP-C.3 — OD-3 is owner-typed prose
  inside WP-F's SCHWAB_STARVATION_RISK_PREACCEPTANCE field, not a schema
  field of its own).
- NO copying code from the deleted `codex/h7-schwab-recovery` branch; rebuild
  against main (the salvage map is in PR #71's close comment).
- The implementation PR starts and stays a GitHub draft; green checks are
  review evidence, not landing authority; merge requires a further independent
  adversarial review (see Acceptance).

## Work packages

WP-D lands as the FIRST commit (independently cherry-pickable); remaining WPs
in any coherent order.

### WP-D — Durability-evidence coercion fix ON MAIN (live defect; land first)

In BOTH builders — `options_researcher/h7_schwab_window_registration.py:391`
and `options_researcher/h7_window_registration.py:243` — replace
`bool(evidence["darwin_durability_verified"])` with a strict pass condition
`evidence["darwin_durability_verified"] is True`, plus a typed refusal check
placed BESIDE each module's own `_require` (each module has its own `_require`;
do not add typing inside the shared-shape `_require` itself — it validates
owner fields at four call sites and the blast radius is unreviewed). Use
`type(x) is bool` for the type refusal so `0`/`1` (ints) and `False` produce
distinct, accurate error messages (`0 == False` in Python — Repo-verified
language semantics).

Acceptance tests (both modules): `"false"` refuses, `"true"` refuses, `0`
refuses, `1` refuses, `None` refuses, `False` refuses with an
unverified-durability error, `True` passes. Refusal-only change: the existing
suite must pass untouched-green (the seq-0 event already carries JSON `true`;
rev-1 review verified no replay/recheck path rebuilds historical events
through the builders).

### WP-A — Validator input binding (closes Codex-bot P1)

`_validate_feasibility` (`options_researcher/h7_schwab_window_registration.py:111`)
currently validates the receipt's self-hash, kind, provenance, and arithmetic
only (Repo-verified). Extend it to:

1. Require per-input content hashes: the receipt's `input_files` mapping (NOT
   `canonical_data_paths`, which holds directories and machine-specific
   absolute paths — rev-1 finding m1) lists each input file with its sha256;
   at validation time recompute each file's sha256 and refuse with a distinct
   error on any mismatch or missing file. New receipts must record
   repo-relative paths; refuse absolute paths outside the repo root.
2. Require `error_count == 0` and the stack/tool identity labels to match the
   registered scope. **Code-surface binding (round-6 C8, mechanism per
   final-review R9):** input hashes and config_hash do not bind the
   COMPUTATION — the feasibility algorithm can change without either moving.
   Use `research.hashing.source_hash(paths=...)` (public, parameterized —
   `research/hashing.py:113`); do NOT use `diagnostic_source_hash()`, whose
   `options_researcher`+`tools` surface (`:132`) makes the receipt invalid
   after ANY unrelated edit — resurrecting the exact-HEAD defect the repo
   already removed (`h7_schwab_window_registration.py:245-253`). The path
   tuple (the extended feasibility tool module plus the modules it imports
   for the measurement) is recorded VERBATIM in the receipt so the surface is
   auditable rather than implicit; the validator recomputes over the recorded
   tuple with its own distinct refusal. `research/hashing.py` is not
   modified.
3. Require the receipt's universe to BE the registered cohort-9 universe
   (packet §2). The historical 15-name receipts fail this by design — the
   qualifying receipt is the fresh cohort-9 one from the ordering section.
4. Require the receipt's recorded `config_hash` to equal the config hash
   computed at validation time (fails for all pre-merge receipts by design —
   see ordering section; do NOT add a bypass).

Acceptance tests, one per refusal path: stale-input-hash, missing-input-file,
absolute-path, config-drift, nonzero-error-count, wrong-universe; happy path
uses a fixture receipt whose hashes are computed from fixture files at test
time.

### WP-B — Feasibility gate in its owner-ruled form

Enforce the 2026-07-24 registration feasibility gate exactly as `.cursorrules`
states it (Repo-verified): registration is valid only if the qualifying
receipt's **occupancy-constrained** expected-entries figure (the pinned
quantity — see the ordering section; carried by the WP-I receipt)
`>= 2 × (owner-typed loss bar from WP-F)` **OR** the registration carries a
present, non-empty, owner-typed starvation pre-acceptance that quotes that
same occupancy-constrained figure exactly. Constraints:

- `config.MIN_LOSSES_FOR_VERDICT` (`config.py:184`) and
  `H10_MIN_LOSSES_FOR_VERDICT` (`config.py:612`) must not appear in this gate.
- Blank/missing pre-acceptance + failing bar REFUSES. A pre-acceptance whose
  quoted number does not equal the receipt's occupancy-constrained figure
  (same quantity as the head of this WP — one name, one field; round-3 P4)
  REFUSES with both numbers in the error (this is the WP that surfaces the
  §4-quotes-3 reconciliation to the owner rather than papering over it).

Acceptance tests (final-review R8 — the bar-met branch is permanently dead
with any WP-I receipt, since WP-I(d) always labels the figure
`upper_bound: true`): the `>= 2 × bar` branch REFUSES when the figure is
`upper_bound: true` (the only state a WP-I receipt can carry); bar-failed +
pre-acceptance carrying the exact canonical token passes; bar-failed + blank
pre-acceptance refuses; quoted-number-mismatch refuses showing both values.

### WP-F — Owner-typed loss bar reaches the event AND the scorer (closes rev-1 B3 + rev-2 N1)

Two halves, both required — the event alone is not enough because the scoring
engine reads config at scoring time:

1. **Event side.** The builder hardcodes
   `"min_losses_for_verdict": config.MIN_LOSSES_FOR_VERDICT` into the scorer
   block (`h7_schwab_window_registration.py:321-325`), which flows into
   `build_scoring_identity` (Repo-verified). Make it an owner-typed
   registration input for the Schwab door: required, refused when absent,
   and validated strictly (round-6 C9, mechanism per final-review R5):
   `type(x) is int` (rejects `True`), `x > 0`, AND equal to the value of a
   canonical machine-readable token `schwab_min_losses_for_verdict=7` that
   the Schwab activation spec carries on its own line (same token discipline
   as the pre-acceptance field — never prose extraction from markdown).
   Provenance stated honestly: until the owner freezes the spec, that 7 is
   TRANSCRIBED from owner ruling 2026-08-14 and the owner confirms it at
   spec-freeze time; the equality check asserts consistency, it does not
   confer owner authority. A mistyped `0`/`1`/`70` refuses instead of
   freezing into both identity surfaces. Written into the scorer block and
   the scoring-identity hash.
   Field name: `SCHWAB_MIN_LOSSES_FOR_VERDICT` (SCREAMING_SNAKE, matching
   every existing entry in both `OWNER_FIELDS` tuples — rev-2 finding n3).
   **Second sanctioned field (C6, Repo-verified):** neither `OWNER_FIELDS`
   nor `EVIDENCE_FIELDS` (`h7_schwab_window_registration.py:44-73`) carries a
   reason or pre-acceptance entry, and the built payload (`:331-393`)
   persists none — a feasibility gate that checks an unpersisted CLI string
   is theater, because the ledger would record no trace of why the bar was
   waived. Therefore the sanctioned `OWNER_FIELDS` additions are exactly TWO:
   `SCHWAB_MIN_LOSSES_FOR_VERDICT` and
   `SCHWAB_STARVATION_RISK_PREACCEPTANCE` (free text, owner-typed at use
   time, refused blank, frozen verbatim into `owner_authorization`). WP-B's
   equality check reads the quoted number out of THAT persisted field, not a
   transient CLI argument — and NOT by fishing a bare number out of prose
   (round-6 C10: the real pre-acceptance text contains dates, window sizes,
   bars, and variant counts; prose extraction either rejects the real text or
   matches the wrong number). The field must contain, alongside the owner's
   prose, the canonical labeled token
   `occupancy_constrained_expected_entries=<value>`; the validator parses
   exactly that token (missing or duplicated token ⇒ refuse) and tests
   include the full realistic owner text plus ambiguous-number cases. The OD-3 namespace line and row-7 quote-age
   commitment remain prose inside this same field — they still add no schema
   of their own.
2. **Scorer side (rev-2 N1; scope corrected per round-3 P2).** The verdict
   gate actually applied is `if losses < config.MIN_LOSSES_FOR_VERDICT:`
   inside `map_forward_verdict(board)` (`h7_forward_scoring.py:92`, gate at
   `:102`) — a function whose sole argument is a scoreboard and which never
   sees the registered event. The change is therefore: `map_forward_verdict`
   gains a REQUIRED bar parameter, threaded from the registered event's
   scorer block by BOTH production callers (`h7_forward_scoring.py:124` and
   `h7_real_scoring.py:1600` — Repo-verified), refusing to score when the
   event lacks the field (no config fallback — a fallback silently
   reintroduces the contradiction). Separately, the provenance STAMPS at
   `h7_forward_scoring.py:451` and `h7_real_scoring.py:1809` (output-payload
   records, not gates) must stamp the event's bar, not config's. The
   parameterized board cases at `tests/test_h7_forward_scoring.py:428-444`
   pass bare dicts and must be updated. Backward compatibility: the seq-0
   event carries `frozen.scorer.min_losses_for_verdict = 10`
   (reviewer-verified round 3), so read-from-event scores the legacy window
   under its own recorded rule; Codex re-verifies and records the observed
   value in the implementation report.

3. **Identity surfaces (C5, Repo-verified — without this the bar-7 event can
   neither build nor score):** `h7_scoring_identity.py` joins Scope-IN.
   `STAGE456_PARAMETER_NAMES` contains `MIN_LOSSES_FOR_VERDICT`
   (`h7_scoring_identity.py:58`), the builder fills stage values from config
   (`h7_schwab_window_registration.py:318`), and `build_scoring_identity`
   REFUSES a stage/scorer disagreement (`h7_scoring_identity.py:136-139`) —
   so the owner-typed bar must be written into BOTH blocks. Then
   `h7_real_scoring._registered_identity` (`:213-222`) compares the
   registered identity against `runtime_scoring_identity()` (pure config) —
   so `runtime_scoring_identity` gains a `min_losses_for_verdict` argument
   that is REQUIRED on any registered-window scoring path, sourced from the
   registered event, with NO config default on that path (a keyword
   defaulting to config is exactly the fallback WP-F.2 forbids; the in-flight
   implementation's silent config fallback was flagged by its own reviewer
   and must not survive the fix round).

Acceptance tests: red-green proving the built event carries the owner-typed
value (7 in the fixture) and NOT `config.MIN_LOSSES_FOR_VERDICT`; absence
refuses; non-integer refuses; red-green proving a 7-bar Schwab event BUILDS
(stage+scorer agree at 7) and is VERDICTED at 7 by the scorer while
`config.MIN_LOSSES_FOR_VERDICT == 10`; omitting the runtime-identity argument
on a registered-window scoring path raises rather than silently using 10;
scorer refuses an event with no recorded bar; the legacy seq-0 event (bar 10
recorded) still builds/scores identically.

### WP-G — Scope-keyed owner-fields in the activation guard (closes rev-1 B5)

`h7_activation_guard.py` checks the legacy ThetaData `OWNER_FIELDS` imported at
`:16` and used at `:197` (Repo-verified) — the Schwab flow can never satisfy
them. Classify by the store's TERMINAL PATH SEGMENT (`Path(forward_base).name`,
where `forward_base` is already a keyword argument to
`activation_preconditions` at `h7_activation_guard.py:69` — Repo-verified):
segment `h7_forward_schwab` ⇒ the Schwab tuple (including WP-F's new fields);
EVERY other segment ⇒ the legacy ThetaData tuple, i.e. today's exact
behavior. Corrections baked in from review:

- **No unrecognized-store refusal** (C3, Repo-verified): the required
  temp-store tests are impossible under refuse-on-unrecognized — existing
  legacy tests pass synthetic stores (`tests/test_h7_activation_guard.py:17`
  `synthetic-forward`, `test_h7_stage8_synthetic.py:56`,
  `test_h7_trim_at_append.py:224/:353`) whose segments match no real store.
  Segment classification lets Schwab tests classify by constructing temp
  stores named `.../h7_forward_schwab`
  (`tests/test_h7_schwab_window_registration.py:472` already does) while
  every legacy synthetic store keeps legacy behavior byte-for-byte.
- **No monkeypatchable module-level mapping**: tests must achieve Schwab
  fields ONLY by store naming, never by patching/substituting the classifier
  or a mapping constant — a red-green test proves patching is not the
  mechanism. (The in-flight implementation's `patch.object(...,
  OWNER_FIELDS_BY_STORE, ...)` in five test files is the rejected
  `owner_fields` parameter relocated; do not reproduce it. No
  `allow_real_readonly` real-store escape hatch in unit tests either.)
- Do NOT key off `scope_identity()` — it is a pure function of the symbol
  universe (`h7_scope.py:57-60`) with no namespace/provider/store concept
  (round-3 P1); it keeps its existing role in the scope checks unchanged.
  Never a caller-supplied field list, never a caller-named scope id (rev-2
  N4).

Acceptance tests: red-green proving a caller cannot narrow the field set NOR
name a scope (no such parameters exist — attempts are TypeErrors); temp store
named `h7_forward_schwab` ⇒ Schwab fields checked without any patching;
scope-vs-store mismatch refusal (the receipt's `scope_identity()` disagreeing
with the store being activated); legacy tests untouched-green.

### WP-C — Owner-confirmed activation CLI (rebuild)

NEW `tools/h7_schwab_manual_activate.py`: operator CLI that assembles the
registration evidence and delegates to `register_window_real`
(`h7_schwab_window_registration.py:436`) — the sole real append door.

1. **Call the door as it actually is** (rev-1 M2; signature Repo-verified at
   `:436-450`): the CLI must construct and pass `guard_report` (from WP-G's
   Schwab classification), `spec_sha256` + `spec_path`, `base_dir`,
   `code_state` (the door refuses a dirty working tree and a HEAD mismatch,
   `:469-475`), `recheck_gates` — but NOT `max_report_age_s` (round-6 C11:
   the CLI must not expose or pass it; the door's own guardrail default
   applies, and a test proves no CLI path can widen the report-age window) —
   **and
   `universe_manifest` (C8): the CLI MUST pass the registered cohort-9
   manifest explicitly — the door's `None` default resolves to the all-15
   `default_universe_manifest()` (`h7_schwab_window_registration.py:274-278`
   → `h7_window_registration.py:121-132`, Repo-verified) and would silently
   register the wrong universe. The cohort's 9 names and each excluded name's
   reason code are owner-typed at use time, never a hardcoded module constant
   (the in-flight implementation's invented `REGISTERED_COHORT` tuple must
   not survive the fix round). **Typo guard (round-6 C3): owner-typed does
   not mean unverified — the builder must additionally require (a) the typed
   included set to EQUAL the qualifying feasibility receipt's universe (the
   receipt WP-A already hash-validates, so the cohort is receipt-bound, not
   free text; note this equality is ALREADY enforced on main at
   `h7_schwab_window_registration.py:172-181` — verify, do not duplicate),
   (b) included + excluded to partition `scope_identity()["symbols"]`
   exactly (9 + 6 = 15, no overlap, no gaps), and (c) every exclusion reason
   non-empty. A typo'd or substituted nine-name set then fails (a) or (b)
   instead of registering.** Do not wrap or monkeypatch the door's own
   refusals.
   **Activation spec (C10, Repo-verified):** `register_window_real:477-486`
   constrains only the HASH, never which file — and the only activation spec
   on main, `docs/superpowers/specs/2026-07-19-h7-stage8-activation-spec.md`,
   pins the LEGACY ThetaData `OWNER_FIELDS` and the all-15 default manifest
   (its §2), so it cannot honestly serve as this door's contract. A NEW
   `docs/superpowers/specs/2026-09-02-h7-schwab-activation-spec.md` joins
   Scope-IN: it states the Schwab `OWNER_FIELDS` (including WP-F's two
   additions), the cohort-9 manifest rule, the owner-typed loss bar, the
   quote-age arming obligation, and the ordering constraint. It ships
   UNSIGNED — the OWNER reviews and freezes it before any real run. **Pinning
   (round-6 C4): a directory check is insufficient — the legacy ThetaData
   spec lives in the same directory and would still hash cleanly. The CLI
   pins the EXACT path `docs/superpowers/specs/2026-09-02-h7-schwab-activation-spec.md`
   as a module constant and REFUSES any other `--activation-spec` value
   (including the 2026-07-19 legacy spec, by an explicit test); tests pin the
   real file, not a temp fixture.**
2. **Owner types everything at use time**: the confirmation string, every
   Schwab owner field (incl. WP-F's loss bar), and the reason /
   pre-acceptance text. The CLI defaults NONE of them and refuses blanks.
3. **OD-3 and the row-7 commitment are prose, not schema** (rev-1 M6): the
   OD-3 namespace line (owner-typed, recorded in `PROJECT_STATE.md:452-461`
   and the 08-09 gate packet) and the packet-row-7 quote-age commitment must
   appear inside the owner-typed reason text. Not a rubber-stampable
   non-empty check (rev-2 finding n1): the CLI matches the CONTENT — the exact
   namespace string as recorded in the OD-3 prose (Codex reads
   `PROJECT_STATE.md:452-461` and pins the literal string in a test), and for
   row 7 both the commitment wording and the evidence citation the packet
   requires. Refuse on either mismatch. These two phrases add no schema of
   their own — they live inside WP-F's persisted
   `SCHWAB_STARVATION_RISK_PREACCEPTANCE` field (C6).
4. **Pre-delegation revalidation**: source-health, data-gate, backup + restore
   receipts, WP-A, WP-B, WP-D. The quote-age gate (WP-E) is deliberately NOT
   in this list — packet row 7 verbatim: "Not a gate on this registration"; it
   is a post-registration arming obligation (rev-1 B4).
5. No direct append: `tests/test_h7_one_door.py` must cover the new CLI.
   Hazard (rev-1 m5): the AST scan `_real_store_constructor_functions` walks
   `tools/` (`_SCAN_ROOTS`, `test_h7_one_door.py:68-69`) and the test asserts
   exact equality of the offender map — construct store paths only through the
   sanctioned door arguments, never a bare `Path(args.store)`.
6. Tests run only against temporary stores; the CLI hard-refuses the real
   store without the owner confirmation string.

### WP-E — Quote-age blocking gate (provides the blocking gate F2 requires; WIRING IS A NAMED SUCCESSOR; post-registration arming lane)

The gate belongs to the ENTRY/ARMING lane, not the registration path.
Honesty note (C4, Repo-verified @1d83453): there is NO Schwab arming consumer
on main — `h7_session.py:137` and `h7_entry_preflight.py:46` open
`REAL_FORWARD_STORE` (legacy) only, and `SCHWAB_FORWARD_STORE` has no consumer
outside its own registration module. WP-E therefore ships a callable,
fully-tested gate with no production caller, and this brief does not claim
otherwise; wiring it into the Schwab arming path is a named successor work
package that lands WITH that path, and until then no name is actually
entry-banned by this gate. Codex records this explicitly in the implementation
report.

1. Land the dispersion-era 60-minute value as an explicitly NON-BLOCKING
   display constant — name it so, e.g.
   `H7_SCHWAB_QUOTE_AGE_DISPERSION_REFERENCE_MINUTES` — with a provenance
   comment citing ruling 3 of `reports/2026-08-31-owner-rulings-h7-unfreeze.md`
   (owner-typed 2026-08-31) AND recording that ruling 3's evidence was
   measured on the dispersion metric, so this constant may not gate anything
   (final-review R2). The BLOCKING constant is the separate absolute-metric
   constant of WP-E.2, which this PR does NOT create. The number appears
   nowhere else.
2. **Metric correction (C2, Repo-verified):** the sidecar's `age_minutes` is
   measured against the per-symbol MAXIMUM timestamp
   (`schwab_quote_age_report.py:221-231`) — it is a WITHIN-PACKAGE DISPERSION
   statistic, and the module's own docstring (`:24-30`) warns that a package
   whose quotes are ALL late reads as fresh. A 60-minute bar on that number
   passes a uniformly-2-hour-old package. The gate must therefore compute an
   ABSOLUTE age — evaluation reference (session close UTC) minus the sidecar's
   `columns.timestamp.selectable.min_utc` (`:201`; no sidecar schema change
   needed) — using the quote `timestamp` population, NOT `trade_timestamp`.
   **Owner gate on arming, explicit mechanism (C2 + round-6 C5):** ruling 3's
   "0 of 7 blocked" evidence was measured on the DISPERSION metric, so the
   60-minute constant is not yet confirmed against absolute ages. The
   distinguishing state is the EXISTENCE of a dedicated config constant for
   the ABSOLUTE metric (e.g. `H7_SCHWAB_QUOTE_AGE_ABSOLUTE_MAX_MINUTES`),
   which DOES NOT EXIST until the owner re-rules and types it — no code
   default, no reuse of the dispersion-era constant for blocking. Behavior is
   two-mode and test-split accordingly: constant ABSENT ⇒ the gate computes
   and visibly reports both numbers with an explicit
   `AWAITING_OWNER_THRESHOLD` verdict and blocks nothing (acceptance tests:
   report-only content, verdict label, nothing banned); constant PRESENT
   (test fixture config) ⇒ over-threshold name entry-banned per-name,
   under-threshold passes, fail-closed paths active (the banning acceptance
   tests apply ONLY to this mode). An implementation is never asked to
   satisfy both modes in one state.
   **Decision statistic comes from the chain bytes, not the sidecar (C9 +
   round-6 C6):** the manifest hash authenticates the parquet package, never
   the sidecar's numbers — an edited sidecar keeps a correct
   session/manifest_hash while lying about ages. Therefore the gate
   RECOMPUTES its decision statistic (worst absolute selectable quote age)
   directly from the manifest-bound chain files of the session being armed,
   reusing `schwab_quote_age_report`'s selectable-population logic (reuse,
   not re-derive). The sidecar is display/diagnostic only and NEVER an input
   to the block/pass decision; the gate still cross-checks
   `sidecar["schema_version"]`/`["session"]`/`["manifest_hash"]` when a
   sidecar is present and reports (not blocks on) a recompute-vs-sidecar
   disagreement with a distinct reason code — that disagreement signal is
   what catches the stale-sidecar path (`write_quote_age_report:363-373`
   refuses a differing rewrite while `schwab_chain_capture.py:376-377`
   swallows the failure, leaving an OLD sidecar beside NEW bytes). Missing
   chain data for the session ⇒ FAIL CLOSED in BOTH modes (Mode A: a visible
   EVIDENCE_INVALID verdict with nothing banned; Mode B: additionally banned);
   silence is never a pass. Per amendment v1.4
   precedent, an over-threshold name is entry-banned per-name (once wired —
   see the honesty note above; and only in blocking mode — see the owner-gate
   mechanism).
3. Arming precondition, stated honestly: NO sidecar artifacts exist yet for
   any session (Repo-verified 2026-08-31 — zero `*.quote_age.json` under
   `reports/schwab_chains` in repo and ops; the producer landed 08-29 and ops
   reached `1d83453` only today). The gate therefore arms from the first
   session that has manifest-bound chain data; sidecar presence is neither
   required nor sufficient (final-review R4 — the decision statistic comes
   from the chain bytes per WP-E.2), and it must not retroactively demand
   sidecars for pre-gate sessions.
4. Producer visibility (bounded fix; rev-2 finding N5 constraints): the
   sidecar block at `schwab_chain_capture.py:368-378` is DELIBERATELY
   fail-soft — it runs after the manifest/receipt/verification/fact are
   durable and its own comment requires that its failure "must be incapable of
   changing the capture's exit code or any of those bytes." Preserve that:
   the visible failure marker write must sit inside its OWN nested
   `try/except` that can never raise; the marker's filename must NOT match
   the sidecar glob pattern (nothing of the form `*.quote_age*.json` — use a
   clearly distinct suffix such as `.quote_age_skip.txt`); and the pinned
   sidecar naming conventions (`sidecar_filename` at
   `schwab_quote_age_report.py:122-135` — file corrected per round-3 P5 —
   asserted by `tests/test_schwab_quote_age_report.py:366-367`) stay
   untouched.
   Acceptance includes a test proving capture still exits 0 when the marker
   write ITSELF fails.
5. A bare call to `h7_schwab_data_gate.evaluate()`
   (`options_researcher/h7_schwab_data_gate.py:134`) without the quote-age
   check does NOT satisfy this WP (finding F2, verbatim constraint).

Acceptance tests, split by mode (final-review R3):
- **Mode A (absolute constant absent — the state this PR ships):** both
  numbers computed and visibly reported; `AWAITING_OWNER_THRESHOLD` verdict;
  nothing banned; missing/mismatched sidecar REPORTED, not blocking; missing
  chain data still fails closed and visibly.
- **Mode B (fixture config supplies the absolute constant):** over-threshold
  name banned per-name; under-threshold passes; missing chain data fails
  closed; threshold read from the single config constant (test asserts single
  source).
- **Both modes:** skip-marker emitted on producer failure; capture still
  exits 0 when the marker write itself fails.

### WP-I — Feasibility tool produces the receipt the validator demands (closes rev-2 N2)

`tools/h7_schwab_feasibility.py` at `1d83453` cannot produce a qualifying
receipt for this registration (Repo-verified): `symbols = sorted(watch_universe())`
at `:234` hardcodes the 15-name universe; argparse (`:226-232`) offers only
`--lookback-sessions`/`--window-sessions`/`--output`; the receipt shape
(`:67-95`) has no `input_files` and only the unconstrained
`expected_entries = base_rate × window_sessions × len(symbols)` (`:66`).
Extend it to:

1. Accept an explicit cohort/universe argument (the registered cohort-9 set,
   packet §2) and record the universe in the receipt.
2. Record `input_files`: every input file consumed, with repo-relative path
   and sha256 (the shape WP-A validates; the preserved
   `2026-08-11-feasibility-primary-earnings.json` shows the field layout —
   Repo-verified on main via PR #137).
3. Compute and record BOTH figures, explicitly labeled: the existing
   unconstrained `expected_entries` AND the occupancy-constrained figure —
   reusing `occupancy_constrained_count(...)` at
   `tools/h7_entry_variant_menu.py:354` (invoked at `:727-728`;
   Repo-verified round 3 — note `tools/h7_entry_variant_menu_v9_cohort9.py`
   only READS a precomputed value at `:147` and contains no reusable logic).
   Codex must reuse, not re-derive. **Window commensurability (C7,
   Repo-verified):** the function returns a RAW surviving-entry count over
   the supplied panel — no normalization to `window_sessions` — and the
   packet's pinned 3 is the 42-session-lockout entry of
   `occupancy_constrained_entries` on `V14_REGISTERED_COHORT_9.json`, where
   panel == window == 70. Therefore: (a) the extended CLI REFUSES
   `--lookback-sessions != --window-sessions` rather than normalizing (no
   LLM-authored conversion arithmetic — the pinned 3 is commensurate only
   under equality; the in-flight implementation's invented
   `count × window / len(sessions)` scaling must not survive the fix round);
   (b) the receipt records `occupancy_lockout_sessions` = 42 with its
   `OCCUPANCY_LOCKOUT_SESSIONS` provenance, plus the panel length; (c) WP-A
   re-derives the occupancy figure from the receipt's own inputs exactly as
   it re-derives `base_rate`/`expected_entries`, refusing if the recorded
   lockout or panel length disagrees with the registration window; and (d)
   **upper-bound honesty (round-6 C12):** the helper's own docstring says it
   enforces only the per-underlying lockout and does NOT net the monthly
   sleeve across overlapping positions, so its output OVERSTATES what the
   registered capital cap would allow. The receipt records the figure with an
   explicit `upper_bound: true` label, and WP-B's `>= 2 × bar` branch may NOT
   be satisfied by an upper-bound figure — with this receipt only the
   starvation pre-acceptance branch can authorize registration (the operative
   branch anyway: 3 < 14). Do NOT author portfolio-netting arithmetic to
   tighten the bound — that is unreviewed modeling; a tight figure, if ever
   needed, is its own reviewed work package.
4. Keep the tool offline (cached inputs only; no network, no provider calls).

Acceptance tests: cohort argument respected and recorded; `input_files`
hashes verifiable by WP-A's validator against fixtures; both figures present
and labeled; a receipt produced by the extended tool passes WP-A's happy path
end-to-end.

### WP-J — Cohort-9 / data-gate scope reconciliation (closes C8's structural half)

Repo-verified structural conflict at `1d83453`: `h7_data_gate.
_validate_result_scope_closure` (`:518-541`, called by `validate_durable_receipt:687`)
forces every durable data-gate receipt to cover ALL 15 official names
(`result["universe"] == list(scope_identity()["symbols"])`), while the Schwab
door requires the receipt universe to EQUAL `manifest["included"]`
(`h7_schwab_window_registration.py:179`, with `:170` and `:183` matching GO
count and verified symbols to the same list). A 9-name registration is
therefore impossible on main today. Reconciliation follows the legacy
Option-C precedent documented at `h7_activation_guard.py:79-90` — FULL-SCOPE
evidence, trim only SELECTS from it: change the three Schwab-side checks to
compare the receipt against `scope_identity()["symbols"]` (all 15) and add a
separate check that every name in `manifest["included"]` is among the
receipt's per-symbol GO names. `options_researcher/h7_data_gate.py` stays
UNCHANGED and out of scope (the in-flight implementation's rewrite of
`_validate_data_gate_receipt` without this WP was flagged as scope creep;
this WP is now its sanction and its exact boundary).

**Whole-universe-GO handling (final-review R7):** the untouched check at
`h7_schwab_window_registration.py:168-174` requires whole-universe GO and
`no_go_count == 0` — if retained, all 15 names must be GO and the cohort-9
trim buys nothing. Mirror the guard's Option-C branch
(`h7_activation_guard.py:120-127`): with a TRIMMED manifest, the
whole-universe-GO requirement is replaced by per-included-name GO over an
all-15 receipt. This is a deliberate, precedent-bound relaxation of
`:168-174` for the trimmed path ONLY; the untrimmed path keeps whole-universe
GO.

Acceptance tests: red-green proving a cohort-9 manifest registers against an
all-15 receipt where every INCLUDED name is GO; an all-15 receipt with a
NO_GO on an EXCLUDED name still registers; the same NO_GO on an INCLUDED name
refuses; a receipt covering fewer than 15 names refuses.

### WP-H — Test alignment

Extend `tests/test_h7_schwab_window_registration.py` for WP-A/B/D/F; extend the
legacy module's tests for its WP-D half; scorer tests (WP-F.2) against
`h7_forward_scoring.py`; identity tests (`tests/test_h7_scoring_identity.py`)
for WP-F.3; new `tests/test_h7_schwab_manual_activate.py` for WP-C; guard
tests for WP-G; gate + producer-marker tests for WP-E (mode-split per WP-E's
acceptance); feasibility-tool tests for WP-I; update
`tests/test_h7_schwab_data_gate.py` fixtures for WP-F's new owner fields; the
one-line snapshot update in `tests/test_ritual_switch_on_hash_containment.py`
(R11). Validation-layer ownership (final-review nit): the BUILDER owns the
canonical-token parses (loss-bar token from the spec, pre-acceptance token
from the owner field) — one refusal, one layer; the CLI owns the OD-3 /
row-7 prose-presence checks and surfaces the builder's refusals verbatim, so
the two layers cannot drift or double-refuse. All tests offline (unittest,
no network, no provider calls).

## Acceptance / verification

Done is defined by exit codes at the implementation head:

```
uv run python -m unittest discover -s tests   # exit 0
uv run ruff check .                            # exit 0
uv run ruff format --check <Scope-IN files>    # Python files only - exit 0 (round-6 C7, SCOPED per final-review R1: the repo at 1d83453 is not format-clean — 276 files would reformat — so a repo-wide gate would force an out-of-scope reformat)
uv run pyright                                 # exit 0
```

plus: every refusal path named above has a red-green test (red evidence
recorded in the PR description); `tests/test_h7_one_door.py` passes and covers
the new CLI; no diff outside the Scope-IN file list; WP-D is the first commit.
The implementation PR is a GitHub draft and **must pass an independent
adversarial review before the owner considers merging** (rev-1 M7; this is the
sole caller of the real append door). Hand-off ends at the reviewed draft —
merge timing, receipt regeneration, registration execution, and every owner
field remain with the owner. Owner-ruling provenance labels in this brief
(loss bar 7, 60-minute threshold) cite the rulings files directly; they are a
distinct provenance class from `.cursorrules`' Official-source (rev-1 NIT).
