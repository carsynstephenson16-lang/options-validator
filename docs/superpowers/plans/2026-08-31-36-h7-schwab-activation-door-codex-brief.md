# Brief 36 — H7 Schwab activation door, rebuilt on main

**Date:** 2026-08-31 (rev 3 — rev 1 FAILED review with 5 blockers B1–B5, rev 2
FAILED with 3 new blockers N1–N3 + majors N4–N6; all findings applied below;
both rounds transcribed in
`reports/2026-08-31-brief-36-adversarial-review-receipt.md`, committed with
this brief)

**WP mapping for the owner's ruling text** (the 2026-08-31 rulings file cites
the PLAN's numeric WPs): plan WP-1→brief WP-A · WP-2→WP-B · WP-3→WP-C ·
WP-4→WP-D · WP-5→WP-E · WP-6→WP-H; brief WP-F/WP-G/WP-I are review-driven
additions beyond the plan.
**Author:** Claude orchestrating session (PR #71 unfreeze arc; plan:
`docs/superpowers/plans/2026-08-30-pr71-unfreeze-pr115-closeout.md`)
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** DRAFT — pending independent adversarial review before hand-off
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
- `tools/h7_schwab_feasibility.py` (WP-I extension)
- `options_researcher/h7_activation_guard.py` (scope-keyed owner-fields
  mapping ONLY, per WP-G)
- NEW `tools/h7_schwab_manual_activate.py` + NEW
  `tests/test_h7_schwab_manual_activate.py`
- NEW quote-age gate function/module per WP-E + `config.py` threshold constant
  with owner-typed provenance
- `options_researcher/schwab_chain_capture.py` (WP-E.4's visibility fix ONLY —
  bounded to the sidecar skip path at `:368-378`)
- `tests/test_h7_one_door.py` (must gain coverage of the new CLI — its
  `test_cli_never_appends_directly` hardcodes only `tools/h7_manual_activate.py`
  at `:266`/`:380` today, Repo-verified)
- `tests/test_h7_schwab_window_registration.py`,
  `tests/test_h7_schwab_data_gate.py` (constructs Schwab owner dicts — breaks
  under WP-F otherwise; rev-2 finding n2), and other existing test files the
  WPs name.

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
  scope-keyed mapping is the only sanctioned mechanism.
- NO modification of either module's `OWNER_FIELDS` tuple beyond what WP-F/WP-G
  specify; NO invented "OD-3 field" (see WP-C.3 — OD-3 is owner-typed prose
  inside the existing reason/pre-acceptance inputs, not a new schema field).
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
   registered scope.
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
  quoted number does not equal the receipt's computed `expected_entries`
  REFUSES with both numbers in the error (this is the WP that surfaces the
  §4-quotes-3 reconciliation to the owner rather than papering over it).

Acceptance tests: bar-met path; bar-failed + pre-acceptance quoting the
receipt's exact number; bar-failed + blank pre-acceptance refusal;
quoted-number-mismatch refusal showing both values.

### WP-F — Owner-typed loss bar reaches the event AND the scorer (closes rev-1 B3 + rev-2 N1)

Two halves, both required — the event alone is not enough because the scoring
engine reads config at scoring time:

1. **Event side.** The builder hardcodes
   `"min_losses_for_verdict": config.MIN_LOSSES_FOR_VERDICT` into the scorer
   block (`h7_schwab_window_registration.py:321-325`), which flows into
   `build_scoring_identity` (Repo-verified). Make it an owner-typed
   registration input for the Schwab door: required, refused when absent or
   non-integer, written into the scorer block and the scoring-identity hash.
   Field name: `SCHWAB_MIN_LOSSES_FOR_VERDICT` (SCREAMING_SNAKE, matching
   every existing entry in both `OWNER_FIELDS` tuples — rev-2 finding n3).
   This is the sanctioned `OWNER_FIELDS` change referenced in OUT.
2. **Scorer side (rev-2 N1).** The verdict gate actually applied is
   `if losses < config.MIN_LOSSES_FOR_VERDICT:` at
   `options_researcher/h7_forward_scoring.py:102`, with the config value
   re-stamped into scoring output at `h7_forward_scoring.py:451` and
   `h7_real_scoring.py:1809` (Repo-verified). Change these sites to read the
   bar from the REGISTERED EVENT's scorer block and REFUSE to score a window
   whose event lacks the field (no config fallback — a fallback silently
   reintroduces the contradiction). Backward compatibility: existing
   registered events already carry `min_losses_for_verdict` in their scorer
   blocks (stamped at build time), so read-from-event scores them under their
   own recorded rule; Codex must verify this on the actual seq-0 event and
   record the observed value in the implementation report.

Acceptance tests: red-green proving the built event carries the owner-typed
value (7 in the fixture) and NOT `config.MIN_LOSSES_FOR_VERDICT`; absence
refuses; non-integer refuses; red-green proving a 7-bar registered window is
VERDICTED at 7 by the scorer while config still says 10; scorer refuses an
event with no recorded bar.

### WP-G — Scope-keyed owner-fields in the activation guard (closes rev-1 B5)

`h7_activation_guard.py` checks the legacy ThetaData `OWNER_FIELDS` imported at
`:16` and used at `:197` (Repo-verified) — the Schwab flow can never satisfy
them. Implement a module-level FROZEN mapping keyed by scope id (legacy scope →
the existing ThetaData tuple, Schwab scope → the Schwab tuple including
WP-F's new field). The scope key comes from the guard's OWN internal
derivation — `scope_identity()` already computed at
`h7_activation_guard.py:130` and used at `:145`/`:187` (Repo-verified) —
NEVER from a caller argument and never a caller-supplied field list (rev-2
finding N4: a caller-named scope id reopens the narrowing hole one level up).
Unknown scope REFUSES; scope-vs-store mismatch REFUSES. The legacy scope's
behavior must be byte-for-byte unchanged.

Acceptance tests: red-green proving a caller cannot narrow the field set NOR
name a scope (no such parameters exist — attempts are TypeErrors); Schwab
store ⇒ Schwab fields checked; unknown-scope refusal; scope-vs-store mismatch
refusal; legacy tests untouched-green.

### WP-C — Owner-confirmed activation CLI (rebuild)

NEW `tools/h7_schwab_manual_activate.py`: operator CLI that assembles the
registration evidence and delegates to `register_window_real`
(`h7_schwab_window_registration.py:436`) — the sole real append door.

1. **Call the door as it actually is** (rev-1 M2; signature Repo-verified at
   `:436-450`): the CLI must construct and pass `guard_report` (from WP-G's
   Schwab scope), `spec_sha256` + `spec_path` (the activation spec file whose
   on-disk sha256 must match `evidence["activation_spec_sha256"]`, enforced at
   `:477-486`), `base_dir`, `code_state` (the door refuses a dirty working
   tree and a HEAD mismatch, `:469-475`), `recheck_gates`, and respect
   `max_report_age_s`. Do not wrap or monkeypatch the door's own refusals.
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
   requires. Refuse on either mismatch. It must NOT add fields to any schema
   for them.
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

### WP-E — Quote-age blocking gate (closes F2; post-registration arming lane)

The gate belongs to the ENTRY/ARMING lane, not the registration path.

1. Add the threshold constant to `config.py` with a provenance comment citing
   ruling 3 of `reports/2026-08-31-owner-rulings-h7-unfreeze.md` (owner-typed
   2026-08-31: quotes older than 1 hour block). Strategy logic reads the
   constant; the number appears nowhere else.
2. The gate consumes the worst selectable QUOTE age — the quote `timestamp`
   population, NOT `trade_timestamp` (Inference from the ruling evidence's
   magnitude, 0.61–10.38 min, vs. the multi-day worst trade ages the sidecar
   docstring records; Codex must verify the column against
   `options_researcher/schwab_quote_age_report.py`'s emitted schema and record
   which column in the implementation report) — from the sidecar report for
   the session being armed. Missing or unparseable sidecar ⇒ FAIL CLOSED for
   that session with a visible per-name/per-board verdict; silence is never a
   pass. Per amendment v1.4 precedent, an over-threshold name is entry-banned
   per-name.
3. Arming precondition, stated honestly: NO sidecar artifacts exist yet for
   any session (Repo-verified 2026-08-31 — zero `*.quote_age.json` under
   `reports/schwab_chains` in repo and ops; the producer landed 08-29 and ops
   reached `1d83453` only today). The gate therefore arms from the first
   session that has a sidecar; it must not retroactively demand sidecars for
   pre-gate sessions.
4. Producer visibility (bounded fix; rev-2 finding N5 constraints): the
   sidecar block at `schwab_chain_capture.py:368-378` is DELIBERATELY
   fail-soft — it runs after the manifest/receipt/verification/fact are
   durable and its own comment requires that its failure "must be incapable of
   changing the capture's exit code or any of those bytes." Preserve that:
   the visible failure marker write must sit inside its OWN nested
   `try/except` that can never raise; the marker's filename must NOT match
   the sidecar glob pattern (nothing of the form `*.quote_age*.json` — use a
   clearly distinct suffix such as `.quote_age_skip.txt`); and the pinned
   sidecar naming conventions (`schwab_chain_capture.py:122-135`, asserted by
   `tests/test_schwab_quote_age_report.py:366-367`) stay untouched.
   Acceptance includes a test proving capture still exits 0 when the marker
   write ITSELF fails.
5. A bare call to `h7_schwab_data_gate.evaluate()`
   (`options_researcher/h7_schwab_data_gate.py:134`) without the quote-age
   check does NOT satisfy this WP (finding F2, verbatim constraint).

Acceptance tests: over-threshold name banned; under-threshold passes; missing
sidecar fails closed visibly; skip-marker emitted on producer failure;
threshold read from config (test asserts single source).

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
   reusing the occupancy logic already reviewed and landed with the
   cohort-9 variant work (`tools/h7_entry_variant_menu_v9_cohort9.py`,
   Repo-verified present on main; Codex must reuse, not re-derive, and cite
   which function in the implementation report).
4. Keep the tool offline (cached inputs only; no network, no provider calls).

Acceptance tests: cohort argument respected and recorded; `input_files`
hashes verifiable by WP-A's validator against fixtures; both figures present
and labeled; a receipt produced by the extended tool passes WP-A's happy path
end-to-end.

### WP-H — Test alignment

Extend `tests/test_h7_schwab_window_registration.py` for WP-A/B/D/F; extend the
legacy module's tests for its WP-D half; scorer tests (WP-F.2) against
`h7_forward_scoring.py`; new `tests/test_h7_schwab_manual_activate.py` for
WP-C; guard tests for WP-G; gate + producer-marker tests for WP-E;
feasibility-tool tests for WP-I; update `tests/test_h7_schwab_data_gate.py`
fixtures for WP-F's new owner field. All tests offline (unittest, no network,
no provider calls).

## Acceptance / verification

Done is defined by exit codes at the implementation head:

```
uv run python -m unittest discover -s tests   # exit 0
uv run ruff check .                            # exit 0
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
