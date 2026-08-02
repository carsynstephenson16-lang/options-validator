# H7 real-exit/scoring SPEC — append-only amendment v1.3

**Amendment tag:** `H7_EXIT_SCORING_SPEC_AMENDMENT_V1_3`
**Date:** 2026-07-25
**Status:** BUILD PREPARED; FABLE IMPLEMENTATION SIGN-OFF AND APPEND-ONLY
GOVERNANCE FACT PENDING. REAL EXITS AND REAL-STORE SCORING REMAIN INACTIVE.
**Base SPEC:** `docs/superpowers/specs/2026-07-22-h7-real-exit-scoring-SPEC.md`
**Base SPEC SHA-256:** `c66d0e395ecc3ae77d5c554bd978e87fa305080cb61423015da513dd29065a75`

This is an append-only correction to the base SPEC's scoring-identity gate.
It does not rewrite the base SPEC, sequence-zero window registration, any H7
event, receipt, threshold, cohort, window, fill rule, result, or hypothesis.
When recorded in `ledger/facts.log` after Fable implementation sign-off, it
supersedes only the base SPEC's
requirement that the current global `config_hash()` equal sequence zero.
Every other base-SPEC requirement remains in force.

No fact is authorized by this document alone. The amendment fact may be
appended by Codex only after Fable's implementation sign-off, with provenance
labeled exactly `owner-delegated standing 2026-07-25`. This amendment is not
itself an owner act. Build authorization is not activation, and final scoring
still requires the base SPEC's separate fresh review-bound owner PASS.

The governance fact must carry the complete active chain:

```text
H7_EXIT_SCORING_SPEC_AMENDMENT_V1_3
contract=h7_scoring_identity/v1
base_spec_sha256=<actual on-disk base SPEC SHA-256>
amendment_spec_sha256=<actual on-disk amendment SHA-256>
provenance=owner-delegated standing 2026-07-25
```

Finalization fails closed unless that exact tag, contract, both hashes, and
provenance occur together in the latest matching fact. The independent-review
and owner-PASS facts must also bind both actual spec hashes and retain the
established `spec_sha256=<amendment SHA-256>` token.

## 1. Defect and result-blind correction

`research.hashing.config_hash()` is a provenance hash of every uppercase
constant in `config.py`. Presentation and plumbing additions therefore change
it even when H7 scoring computation is byte-identical. The current global hash
no longer equals sequence zero, while the complete sequence-zero Stage 4/5/6
parameters, scorer fields, and cost-model hash still match.

The corrected authority gate is `h7_scoring_identity/v1`. It binds the frozen
scoring computation explicitly and treats registered/current global config
hashes as receipt provenance only. Neither global config hash grants or refuses
scoring authority.

This correction is result-blind. The registered final session has not occurred,
preview withholds all interim results, and real scoring remains locked behind
the independent-review and owner-PASS facts.

## 2. `h7_scoring_identity/v1`

The canonical surface is:

```json
{
  "contract": "h7_scoring_identity/v1",
  "stage456_parameters": {
    "...": "all exact fields listed below"
  },
  "scorer": {
    "module": "options_researcher.h7_forward_scoring",
    "min_losses_for_verdict": 10,
    "bootstrap_samples": 5000
  },
  "cost_model_hash": "<sequence-zero frozen SHA-256>"
}
```

The Stage 4/5/6 block is complete and exact:

```text
H7_FORWARD_CONTRACTS
COMMISSION_PER_CONTRACT
SLIPPAGE_HAIRCUT
H7_LANE_PRIORITY
H7_LONG_DELTA_BAND
H7_LONG_DTE_BAND
H7_SPREAD_LONG_DELTA
H7_SPREAD_SHORT_DELTA
H7_LONG_TP_PCT
H7_SPREAD_TP_FRAC_MAX
H7_CLOSE_AT_DTE
H7_DELTA_TOLERANCE
H7C_SHORT_DELTA_MAX
H7C_DTE_BAND
H7C_CREDIT_FLOOR_FRAC
H7C_WIDTH_FRAC_OF_SPOT
H7C_TP_FRAC
H7C_STOP_CREDIT_MULT
H7C_MAX_CONCURRENT
H7C_CLOSE_AT_DTE
H7C_CLOSE_BEFORE_EARNINGS
H7C_TIEBREAK
H7_MONTHLY_AT_RISK
H7_MAX_OPEN_PER_UNDERLYING
H7_ADMIT_MIN_CONTRACTS
H7_ADMIT_MAX_SPREAD_PCT
H7_EARNINGS_BAN_SESSIONS
H7_EARNINGS_POST_REPORT_GRACE_D
H7_MAX_HOLD_BUFFER_D
MIN_LOSSES_FOR_VERDICT
BOOTSTRAP_SAMPLES
```

The sequence-zero `cost_model_hash` remains an atomic gate. It transitively
binds fill/liquidity and dependence-aware metric constants that sequence zero
did not persist as independent Stage 4/5/6 fields. No post-hoc component value
may be invented from that opaque hash.

Before hashing or comparison, the complete surface is round-tripped through
the repository's canonical JSON serializer. This recursively normalizes
runtime tuples to JSON lists, including `H7_LANE_PRIORITY`, without relaxing
value or ordering equality. Missing fields, extra Stage 4/5/6 fields,
noncanonical values, stage/scorer disagreement, malformed hashes, or any
surface mismatch fail closed.

The `scorer` mapping has exactly three keys:
`module`, `bootstrap_samples`, and `min_losses_for_verdict`. Missing or extra
keys are malformed. In particular, no code/source hash is added to v1. The
base SPEC's source-provenance-only rule remains unchanged.

## 3. Legacy and future registrations

The immutable real sequence-zero registration predates this contract and must
not be edited. Its identity is derived from its existing
`frozen.stage456_parameters`, `frozen.scorer`, and
`frozen.cost_model_hash`.

Future registrations persist these additive fields inside `frozen`:

```text
scoring_identity_contract = "h7_scoring_identity/v1"
scoring_identity_hash = sha256(canonical identity surface)
```

The persisted contract/hash must exactly rederive from the accompanying frozen
fields. A partial pair, unsupported version, or stale hash is malformed and
fails closed. Adding or removing a frozen scoring field requires a new
versioned identity contract; v1 never grows silently.

## 4. Real-scoring authority and receipt

`RealScoringSession` stores the contract, canonical surface, identity hash,
actual base-SPEC hash, and actual amendment hash. Every preview/finalization
re-verifies both on-disk spec hashes and the ledger, rederives both registered
and runtime identities, and compares them with the capability's stored
identity.

The implementation also pins the base hash to
`c66d0e395ecc3ae77d5c554bd978e87fa305080cb61423015da513dd29065a75`;
hashing a simultaneously edited base and amendment cannot create a new trusted
chain. Base-hash drift refuses before a scoring capability opens.

The immutable `window_score` receipt records:

- scorer module;
- scoring-identity contract and hash;
- cost-model hash, minimum-loss gate, bootstrap count, and forward contracts.
- `spec_sha256` as a compatibility alias for the amendment SHA-256, plus an
  explicit `spec_chain` containing both base and amendment hashes.

It also carries an explicit, separate provenance object:

```json
{
  "config_provenance": {
    "authority": false,
    "registered_config_hash": "<sequence-zero provenance>",
    "runtime_config_hash": "<finalization-time provenance>"
  }
}
```

Both hashes must be canonical lowercase SHA-256 values. The two global config
hashes are never part of the authority comparison.
Unrelated presentation/plumbing changes may alter runtime provenance without
changing or reopening frozen H7 scoring computation.

On idempotent replay, the original immutable receipt's runtime config hash is
the finalization-time provenance and must be reused rather than recomputed.
The original provenance object must have exactly the declared keys, carry
`authority: false`, retain the registered hash, and contain canonical hashes;
otherwise replay fails closed. This lets unrelated later config drift coexist
with byte-identical artifact replay without rewriting history.

The source-identity rule remains as stated in the base SPEC: the broad live
source hash is provenance, not a sequence-zero runtime gate. The frozen scorer
module remains byte-identical; this amendment adds no scoring, settlement,
entry, exit, or verdict math.

## 5. Governance and acceptance

This is not a new H7 hypothesis version because it changes no frozen parameter,
ticker, cohort, date, rule, metric, threshold, or result. If implementation
requires any such change, stop and register a new hypothesis version instead.

Acceptance requires:

1. focused identity, registration, and real-scoring tests;
2. unrelated uppercase config drift allowed;
3. every frozen Stage 4/5/6, scorer, and cost drift refused;
4. list/tuple canonicalization and malformed persisted identity tested;
5. legacy real sequence zero opens read-only without changing its bytes;
6. receipt provenance and identity fields tested;
7. replay after unrelated global config drift is idempotent and preserves the
   original runtime provenance;
8. exact scorer-map shape and both spec hashes are fail-closed;
9. Ruff and Pyright clean on the touched Python surface;
10. Fable implementation review; and
11. a Codex-appended amendment fact labeled
   `owner-delegated standing 2026-07-25`, followed by the base SPEC's separate
   fresh review and review-bound owner-PASS gates before real scoring can
   activate.

No test, review, or owner fact authorizes live trading. This repository remains
paper research only and has no order path.
