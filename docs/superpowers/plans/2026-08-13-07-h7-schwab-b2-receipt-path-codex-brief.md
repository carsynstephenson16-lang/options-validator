# Codex brief 07 — Close B2: give the Schwab data gate a real receipt path

**Date:** 2026-08-13
**Author:** Claude (orchestrating session, PM scope pass)
**Executor:** Codex (Sol, high reasoning)
**Status:** DRAFT — pending independent adversarial review before hand-off
**Provenance:** every constraint below is Repo-verified against origin/main
@7fbe013 and `reports/h7_forward_schwab/2026-08-12-adversarial-review-receipt.md`
unless labeled otherwise.

## Why this exists (plain language)

The H7 restart cannot register until blocker **B2** from the 2026-08-12
independent adversarial review is closed. Today, a verified Schwab pre-close
capture cannot become a durable data-gate receipt at all:

- `options_researcher/h7_data_gate.py` `build_receipt` (~line 589) raises
  unless `evidence_mode == "REAL-H7-FULL-AUDIT"` (the ThetaData mode).
- `_validate_result_scope_closure` (~line 554) hardcodes the ThetaData
  `validate_v2_audit_receipt` recompute.

So the Schwab lane can capture and verify chains, but the gate can never say
"GO" in a form the registration door accepts. That is B2.

A local branch `codex/h7-schwab-evidence-mode` (commit `609d43a`, currently
**unpushed** — push it first per the 2026-08-04 branch-hygiene rule) closed
only the registration-side half: the door now refuses evidence whose
`data_gate_evidence_mode` mismatches. It did NOT add a Schwab receipt path.
Incorporate that commit's tests; do not duplicate or silently rewrite them.

## Scope

IN: `options_researcher/h7_data_gate.py`, `options_researcher/h7_schwab_data_gate.py`,
`options_researcher/h7_schwab_window_registration.py`, matching tests, and the
four hardening items below. OUT: any ledger write, any registration, any
authority flip, any change to the ThetaData receipt path's behavior for
existing modes, anything touching `data/ritual_authority.py`.

## Work packages

### WP-A — Schwab evidence mode receipt path (B2 proper)

1. REUSE the existing constant `h7_schwab_data_gate.EVIDENCE_MODE`
   (`"REAL-H7-SCHWAB-PRECLOSE-AUDIT"`, already defined at
   `options_researcher/h7_schwab_data_gate.py:13`) — do NOT define a second
   constant in `h7_data_gate.py`; one source of truth for the string.
   It runs alongside — never replacing — `"REAL-H7-FULL-AUDIT"`.
2. `build_receipt` accepts it only when the evidence package is Schwab-shaped.
   Note the mode string is ALREADY inside the hashed receipt payload today
   (`h7_data_gate.py` ~:606) — that alone protects nothing. The actual B2
   requirements: (a) `_validate_result_scope_closure` must DISPATCH on
   evidence mode — the Schwab path re-derives scope closure from the Schwab
   chain manifest (`tools/schwab_chain_manifest.py` verify), never
   `validate_v2_audit_receipt`; (b) the receipt payload must ADDITIONALLY
   carry the Schwab manifest hash and the capture-receipt hash, binding the
   receipt to the specific verified package; (c) a ThetaData-shaped package
   must be UNABLE to produce a receipt bearing the Schwab mode, and vice
   versa — prove both directions with tests.
3. The registration door check from `609d43a`
   (`data_gate_evidence_mode == EVIDENCE_MODE`) must pass end-to-end with the
   new receipt, and must still refuse: (a) mislabeled mode, (b) receipt built
   from an unverified manifest, (c) receipt whose universe or `config_hash`
   differs from registration-time values (keep the B3 binding semantics).
4. Follow-up from runbook 08 finding 7 (same scope, small): add
   `git fetch -q origin main` before the HEAD-alignment comparison in
   `tools/schwab_chain_capture.sh`, so the wrapper compares against the
   CURRENT origin/main rather than the last-fetched ref. Keep the refusal
   semantics identical.

### WP-B — Review hardening items (required before the canary counts)

**Status update (2026-08-13):** commit 401f78b on
`codex/pre-canary-capture-hardening` (277 insertions, 11 files; full offline
suite exit 0 on that exact tree; pushed, merge owner-gated per runbook 08)
implements all four items below with matching tests — independently
verified during the 2026-08-13 adversarial review. Codex's job in WP-B:
after 401f78b lands on origin/main, verify each item against the review
wording AND review the full 11-file diff, not only the four named items —
the diff also adds `reports/schwab_chains` to the irreplaceable-data guard
and inventory, and adds the `SCHWAB_PACKAGE_INVALID` fail-closed NO_GO
packaging to the Schwab data gate. Close any gap found.

From the 2026-08-12 review, high severity:

- **H1:** `verify_session` must verify capture time against the receipt's
  recorded `captured_at_et` (and reject `force=True`), not trust the
  self-asserted label. *(Implemented in the pending diff — verify.)*
- **H2:** `_normalize` in the Schwab capture path must stop discarding
  `contract_symbol`, `multiplier`, `non_standard`, `mini`, `timestamp`.
  These are unrecoverable once real captures start; persist them.
  *(Implemented in the pending diff — verify.)*
- **H3:** anchor the capture manifest + receipt hash in `facts.log` at capture
  time via the typed facts API (`research.facts.append_fact`) — never a
  hand-written line. One fact per completed capture session, none on partial.
  *(Implemented in the pending diff — verify.)*
- **M-c:** add `ledger/h7_forward_schwab` and `reports/schwab_chains` to the
  `tools/daily_ritual.sh` evidence git-add allow-list.
  *(Implemented in the pending diff — verify.)*

### WP-C — Tests (red first, per repo TDD norm)

- Red: a Schwab evidence package today cannot produce a receipt (proves B2).
- Green: full path capture-manifest → verify → gate GO → receipt →
  registration-door acceptance, all offline on fixtures.
- Refusal matrix: mislabeled mode, tampered manifest, stale `captured_at_et`,
  `force`-flagged capture, universe mismatch, config-hash mismatch.
- All existing ThetaData-mode tests must pass unchanged (no behavior change
  for the old mode).

## Acceptance

- `uv run python -m unittest discover -s tests` exit 0, offline.
- `uv run ruff check .` and `uv run pyright` clean.
- No new frozen numbers invented: any constant needed is either already in
  `config.py` or gets an explicit LLM-proposed provenance label per the
  2026-08-04 composite-lane precedent.
- Independent adversarial review receipt (Fable) before merge — same bar as
  the 2026-08-12 review that produced B1–B4.

## Explicitly forbidden

Registering a window, flipping authority, writing to `ledger/h7_forward*`
outside typed APIs, network calls in tests, touching the paused
`h7-forward-15-v1` namespace, weakening any existing refusal.
