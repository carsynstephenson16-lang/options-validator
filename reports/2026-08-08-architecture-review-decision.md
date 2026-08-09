# 2026-08-08 architecture review decision — modular-monolith proposal

**Status:** advisory decision record. No guardrail, policy, scope, or
registration text changes. Nothing here is verdict-bearing.
**Provenance:** Claude Fable 5 audit session 2026-08-08/09 (six independent
evidence tracks + fresh adversarial verifier), recorded on owner direction
2026-08-09 ("save commit and push everything above").
**Baseline reviewed:** `c875839c982ca95d5f5873c327e5ea8229b50b77`
(= `origin/main` throughout the audit; no drift).

## What was reviewed

An external proposal recommended evolving the repo into a "policy-first
modular monolith": canonical capability ports for providers, a universal
`EvaluationContext` / authority-as-data object threaded through every use
case, an artifact-envelope contract over all derived stores, a typed Python
workflow runner replacing `tools/daily_ritual.sh`, a split of `config.py`
by authority, and a `domain/application/ports/adapters` package layout —
delivered via a phased migration with compatibility adapters.

## Verdict

**Path A selected: preserve the present architecture.** One small
boundary fix adopted; everything larger is deferred behind exact triggers
or rejected with evidence. Key audit findings (full detail in the audit
report / session transcript):

- The activation boundary is enforced *structurally* (no order methods
  exist on the Schwab facade — `tests/test_schwab_adapter.py`; the
  live-preview renderer cannot contain the literal `FIRE` —
  `tests/test_live_dashboard.py`; PreToolUse hooks fail closed). A
  data-flag authority model would weaken, not strengthen, this.
- The proposal's "vocabulary leak" (live lane importing private helpers
  from `thetadata_adapter`) was real as an import but wrong as a
  diagnosis: the helpers are provider-agnostic. The fix is relocation,
  not a port layer.
- Safety-critical transforms (`passes_liquidity`, `quote_valid`, mid
  pricing, DTE bands) were already centralized or intentionally
  per-hypothesis; no accidental duplication of policy was found.
- Provenance density already tracks authority: every verdict-bearing
  artifact carries rigorous provenance; the zero-provenance stores
  (attractiveness features, composite scratch, CSV mirrors) are
  disposable or subordinate by design.
- `daily_ritual.sh` concentrates eight effect types and has real fix
  history (~10 of 29 commits), but each defect class received a
  structural in-place fix, and the ritual is currently
  authority-blocked — a shadow runner built now would shadow a dormant
  lane.
- At the pinned commit: 2,535 tests / 0 assertion failures, ruff clean,
  pyright clean (narrow include list — noted as a known coverage gap).

## Adopted (shipped with this record)

- **`data/chain_policy.py` extraction:** `mid_price`, `passes_liquidity`,
  `_pick_col`, `_normalize_contract_keys` moved verbatim out of the
  retired ThetaData adapter; `thetadata_adapter` re-imports them under
  the same names (all ~44 importers resolve identical objects, pinned by
  `tests/test_chain_policy.py`); `live_quotes` imports from the neutral
  module. Behavior-preserving: full suite 2,536 green, ruff/pyright
  clean. Rationale: the conservative fill/liquidity policy bound by
  `.cursorrules` should not live in an exiting provider's module.

## Deferred with exact triggers

- **Shadow Python workflow runner** — trigger: ≥2 new `fix(ritual)`-class
  defects after `c875839`, OR owner directs a new hypothesis lane/step in
  the ritual. Shape when triggered: shadow-only, zero mutation authority,
  shell stays authoritative until owner-approved cutover.
- **Typed Card/Badge/status objects in the attractiveness/QM display
  layer** — trigger: next material feature change to
  `attractiveness_dashboard.py` or first defect traced to a card/badge
  dict shape. Template: `quote_integrity.Tier`/`Verdict`.
- **Promote `_leaps_candidate` to a public name** (3-consumer de facto
  contract) — trigger: next functional change to
  `studies/long_call_carry.py` or its importers' use of it.
- **Per-file inline `(bid+ask)/2` migration to `chain_policy.mid_price`**
  — trigger: next functional edit to a file containing an inline mid;
  never wholesale, never frozen-study files.
- **Typed capability-absence error on the live-provider surface** —
  trigger: a second live provider or new live-lane capability.

## Deferred for evidence

- **`config.py` split by authority** — missing evidence: a defect traced
  to the shared namespace. (`config.py` is a zero-import leaf; runs
  already freeze `config_hash`.)
- **Artifact-envelope contract** — missing evidence: a provenance gap on
  a *verdict-bearing* artifact.
- **Central status-string constants/enum** — missing evidence: one real
  status-string mismatch defect.
- **Artifact-path ownership test extension** — missing evidence: a third
  writer of `{symbol}_features.parquet` or any manifest-bound artifact
  (existing `tests/test_features.py` pairwise pinning already covers the
  2026-07-16 clobber class).

## Rejected (with reasons)

- **Capability-port layer** — guarantees already structural and tested;
  one polymorphic consumer; concepts without a verified problem.
- **Universal `EvaluationContext` / authority-as-data threading** — would
  trade absence-based structural enforcement for settable flags; fails
  the "never weaken a fail-closed boundary" gate as a direction.
- **`domain/application/ports/adapters` reorganization** — no
  import-graph pain at that scale; churn across ~180 importer edges for
  no measurable result.
- **New shared analytical kernel layer** — already solved where it
  matters; remaining differences are deliberate policy.
- Concurring with the proposal's own no-gos (already codified in
  `docs/evidence-upgrade/final-architecture.md`): no rewrite, no
  microservices/Airflow/always-on platform, no database, no ledger
  consolidation, no authority inheritance by scanners or live quotes, no
  policy changes inside refactors.

## Re-litigation guard

Before reopening any rejected or deferred item, check its trigger above.
A new proposal that does not present the named missing evidence adds
nothing to this record.
