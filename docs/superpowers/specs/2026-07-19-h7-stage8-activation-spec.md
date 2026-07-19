# H7 Stage 8 — activation spec (the ONE real window_registration append)

**Status: BUILD-authorized draft (owner directive "switch it on, pursue now",
2026-07-18). This document authorizes BUILDING the guarded append path and
defines the exact contract under which the single real append may later run.
It does NOT itself open Stage 8: the real append additionally requires the
owner's typed `H7_STAGE8_EXPLICIT_AUTHORIZATION` string, every §2 field, an
independent review PASS recorded on THIS document, and every §3 precondition
green at the pinned session.**

Plain-English frame: "activation" means writing one immutable first record
(a `window_registration` event) into the real forward ledger
`ledger/h7_forward/`. That record locks the paper window's start date, its
length, and every frozen rule *before* the first decision. Everything after
it is Stage 3's hash-chained event stream; nothing before it exists at all
(the store must be VALID EMPTY — a verified, still-empty chain).

## 1. Hash-binding convention (decided; flagged for review)

The H9 precedent is used, not a self-referencing hash: this file's sha256 is
computed over the exact committed bytes and carried OUTSIDE the file — in
`evidence.activation_spec_sha256`, in the append call's `spec_sha256`
argument, and in the `H7_STAGE8_REGISTERED` ledger fact. The append path
refuses unless all three agree (64 lowercase hex). Any later edit to this
file changes the hash and is activation-voiding drift. *(Plain English: the
document gets fingerprinted; the machine refuses to register a window unless
the fingerprint it is handed, the fingerprint the reviewer approved, and the
document on disk all match.)*

## 2. Owner pre-commitments (the seven typed fields)

Exactly `OWNER_FIELDS` in `h7_window_registration.py`; none may be blank,
none may be defaulted, all are frozen into the event payload verbatim:
explicit authorization string; window start session; decision-session count;
end-rule acknowledgment (end is DERIVED = start + count inclusive XNYS
sessions, never hand-picked); three-calendar-months-per-lane acknowledgment;
ThetaData coverage-confirmed-through date; and the coverage evidence
pointer. The builder re-derives the end from the count and refuses if the
window spans less than three calendar months or coverage ends before the
window does. *(Plain English: you can't register a window your data
subscription can't see to the end of.)*

## 3. Preconditions the guard must report green (all-or-nothing)

`activation_preconditions()` — every check, at the same pinned session:
1. **ledger_valid_empty** — real store verifies VALID EMPTY.
2. **source_health_whole_universe** — every name in the derived 15-name
   universe has trustworthy (company-confirmed) earnings provenance; one
   unhealthy name blocks the board.
3. **data_gate_go** — whole-universe exact-session closes + chains GO.
4. **owner_inputs_complete** — all seven §2 fields present.
5. **working_tree_clean** — `git status --porcelain` empty; the registered
   `code_commit` is the identity actually running.
Plus runtime evidence produced inside the activation arc, not typed by the
owner: independent review PASS (`review_evidence`), this spec's sha256, the
code commit, source-health and data-gate evidence ids, a fresh Darwin
durability verification (fsync/F_FULLFSYNC success AND failure paths), and
`pre_append_state`.

**Procedural precondition (NOT code-enforced).** A FRESH data-audit receipt
covering the pinned session is required before activation, but no guard check
reads it — the pre-versioned `receipt_v4` is stale and must not be blessed.
This is an OWNER/ORCHESTRATOR-VERIFIED step of the activation sitting: the
orchestrator confirms by hand, in the same session as the append, that a fresh
data-audit receipt exists for the pinned session, and records that receipt's
hash verbatim in the activation fact. The `activation_preconditions()` guard
does not, and is not being changed to, enforce this; treat a missing or stale
data-audit receipt as a manual VOID of the sitting, not a code failure.

## 4. The append procedure (exactly once)

`register_window_real(...)` is the only code allowed to touch the real
store. Its refusal chain, in order (review conditions C1/C2 folded in,
2026-07-19): every owner/evidence field present; guard report is a full
PASS; report is bound to THIS store path; report carries a code identity;
that commit is still HEAD with a clean tree at append time; the evidence
commit equals that HEAD; the spec sha handed in is 64 lowercase hex, equals
the evidence sha, AND equals the sha256 of the on-disk spec file computed at
append time (the reviewed document, the recorded fingerprint, and the file
must be one and the same); the guard report is younger than
`GUARD_REPORT_MAX_AGE_S` (3600 s — HEAD/clean-tree cannot see untracked
cache files the gates read, so age itself refuses); the injected
`recheck_gates()` is EXECUTED at append time and must report source health
all-healthy and data gate GO carrying the same evidence ids the evidence
claims — gate PASSes are re-earned, never inherited; and the store
re-verifies VALID EMPTY at this instant. Only then is the event built
(re-deriving all window arithmetic) and appended with `expected_head=None`,
so even a racing concurrent write loses. One event, seq 0,
`window_registration`. *(Plain English: ten locks on one door, checked again
in the doorway, and the door only opens once.)*

Known residual limit (disclosed, per review): these checks defeat stale,
drifted, or mis-bound activations — they cannot defeat an operator who
deliberately fabricates every input at once. The owner-typed authorization
string plus the independent-review PASS are the human locks for that.

## 5. Void conditions

If ANY precondition changes between the guard check and the append — code
moves, tree dirties, a name goes unhealthy, the store gains an event, the
spec is edited — the append refuses and Stage 8 stays inactive. A refused or
crashed attempt appends nothing and is recorded honestly in `facts.log`;
there is no partial activation state. After a successful append: decisions
begin only on the registered start session; no backfill, no substituted
earlier opportunity, no end-date movement after outcomes are visible; the
window scores exactly once, after the last opened fill closes.

## 6. Boundary (registered invariant)

A `SURVIVED` outcome is **not** live-trading approval, not a profitability
claim, and not validation — it means the forward window's result was not
rejected under the frozen loss-gated scorer (`MIN_LOSSES_FOR_VERDICT=10`,
`BOOTSTRAP_SAMPLES=5000`). This repo remains a validator: no order placement,
ever, regardless of outcome.
