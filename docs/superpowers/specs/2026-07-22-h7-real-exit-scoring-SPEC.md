# H7 real-store exit and scoring path — SPEC

**Status: SPEC CANDIDATE ONLY. NOT BUILD-AUTHORIZED. REAL EXITS AND REAL-STORE
SCORING REMAIN INACTIVE.** This document defines the next H7 implementation
arc required by `H7_C1_EXIT_AND_SCORING_DEADLINES`. It does not authorize an
exit, score the live window, change a frozen parameter, or create an order path.

## 1. Goal and deadline

Promote the already reviewed synthetic exit and scoring mechanics through
narrow, receipt-bound doors to the registered real **paper** ledger. The
implementation must preserve the existing frozen logic and add only the
authority, evidence, CLI, and durable-result surfaces missing from the real
path.

The exit door must be implemented, independently adversarially reviewed, and
owner-approved before the first real `entry_intent` can fire. An entry can fill
one session later and can require an exit observation on that same fill
session, so an entry without the exit door would create an unmanaged paper
position. If any daily watcher first reports `ENTRY-OK` for an included name,
this arc becomes the only permitted options-validator implementation work until
the exit door is reviewed or the entry door is explicitly held closed.

Real-store scoring must be reviewed before the registered final decision
session, 2026-10-26, and before results are visible. The window scores exactly
once, only after every included decision and opened position is resolved.

## 2. Existing machinery that must remain unchanged

- `options_researcher.h7_paper_lifecycle.observe_exit` and
  `process_exit_fill` own the frozen trigger order, T+1 fill behavior, adverse
  quote transforms, costs, liquidity refusals, retry rules, and paper-ledger
  event shapes.
- `options_researcher.h7_forward_scoring.score_forward_window` owns trade
  reconstruction, per-lane and overall dependence-aware CI90 scoring, and the
  frozen `SURVIVED` / `REJECTED` / `INCONCLUSIVE` mapping.
- Sequence-zero `window_registration` is the source of truth for the included
  cohort, window bounds, config/cost identities, and scorer identity:
  `options_researcher.h7_forward_scoring`, `min_losses_for_verdict=10`, and
  `bootstrap_samples=5000`.
- `RealStoreSession` stays entry-only. Its explicit refusal of exit calls is a
  safety boundary, not a temporary inconvenience to bypass.
- No dated receipt, existing H7 event, registration payload, frozen threshold,
  or historical artifact is rewritten.

## 3. Required delta 1 — a distinct real-exit authority type

Add a frozen `RealExitSession` capability, separate from `RealStoreSession`.
Only a reviewed `open_real_exit_session(...)` factory may create it. The type
must carry:

- the verified real-store path and sequence-zero registration id;
- the operational decision session and completed source-evaluation session;
- the immutable included cohort;
- the data-gate and linked source-health receipt paths and hashes;
- config and source-hash identities; and
- the exact per-symbol chain and close bindings for the monitored session.

`observe_exit` and `process_exit_fill` may accept this capability in addition
to their existing explicit synthetic path. Passing a plain path resolving to
`ledger/h7_forward`, a `RealStoreSession`, a forged dataclass, or any other
object must continue to fail closed. The implementation must not weaken
`_synthetic_base`; it must introduce a typed resolution path analogous to the
entry-only `_resolve_base` seam.

Exit authority is mechanical paper-book authority only. It cannot propose an
entry, approve an entry, place an order, or score the window.

## 4. Required delta 2 — re-verify receipts and cache bytes every session

`open_real_exit_session` must re-earn authority from the current session's
immutable evidence. It must mirror the protections in
`h7_session._watcher_receipt_for_session`, `_receipt_input`,
`_load_bound_chain`, and `_load_bound_close`, without depending on actionable
entry rows.

For every monitoring or fill session it must:

1. verify the forward hash chain and load the cohort/window from seq 0;
2. require the decision session to be inside the registered window or to be a
   valid later fill/retry session causally descended from an in-window entry;
3. load and integrity-check the full-official-scope data-gate receipt and its
   linked source-health receipt for the exact completed evaluation session;
4. require receipt scope, session, link hashes, config hash, source hash, and
   declared source-hash contract to agree;
5. re-hash every named input before use;
6. load only the exact chain and adjusted close named by the receipt binding,
   then re-hash the binding again after load; and
7. refuse stale, missing, changed, future, fallback, or cross-session data.

The exit factory must be able to represent a valid `NO_GO` data-gate receipt.
`NO_GO` grants no permission to infer a price; it exists so the frozen
lifecycle can append an honest `data_gap` and retry on the first valid later
session. A market-wide data problem must not silently stop exit monitoring.

The data-gate receipt already binds per-symbol chain and close files. The exit
path should reuse those bindings directly or extract shared receipt helpers;
it must not require an `ENTRY-OK` watcher row and must not duplicate a second
mutable cache manifest.

## 5. Required delta 3 — monitoring-session evidence events

Every real exit observation and exit-fill attempt must publish the session's
verified `data_gate` evidence event before the lifecycle transition. The event
uses the existing deterministic id `h7:data_gate:<evaluation-session>` and is
idempotent only when its receipt identity is identical.

An exit whose frozen reason depends on earnings (`pre_earnings` or
`earnings_unknown`) must additionally publish and cite the per-symbol
`source_health` evidence event for that session. Its gate, health state,
receipt hash, receipt path, and symbol must agree with the values passed to
`observe_exit`. A non-earnings exit must not fabricate an unnecessary
source-health cause.

No monitoring session disappears:

- GO + priceable + no trigger returns no exit intent but leaves its verified
  data-gate evidence in the ledger.
- NO_GO or unpriceable inputs append the existing `data_gap` event.
- A fired trigger appends one deterministic `exit_intent` citing the opening
  fill, the session data gate, and source health when earnings-dependent.
- A fill attempt appends either the closing `paper_fill` or a visible
  `data_gap`; retries remain first-later-session only.

## 6. Required delta 4 — decision session versus evaluation session

Real exit calls must preserve both dates explicitly:

- `evaluation_session` is the completed source-data/receipt date and remains
  the stored event's `evaluation_session`.
- `decision_session` is the operational session governed by the registered
  window and is recorded in the exit-intent payload.
- `planned_fill_session` is derived from `decision_session`, never from wall
  clock and never silently from the source date.

For synthetic callers the two dates remain identical, preserving current
tests and public behavior. For a `RealExitSession`, lifecycle code must derive
the operational date through one typed mapping helper, as the entry path does.
It must reject an inconsistent receipt date, an exit before the opening fill,
a decision outside the allowed window/fill lineage, and any attempt to use
today's unfinished EOD as completed evidence.

Transition ordering must be test-pinned: after an opening fill is recorded,
that new position is included in the same session's exit observation pass.
This is what closes the earliest-exit gap identified in
`H7_C1_EXIT_AND_SCORING_DEADLINES`.

## 7. Required delta 5 — owner-visible exit and scoring CLIs

Add an exit CLI with explicit subcommands, no network calls, and no order
surface:

```text
python -m options_researcher.h7_exit_session status ...
python -m options_researcher.h7_exit_session monitor ...
python -m options_researcher.h7_exit_session fill ...
```

`status` validates authority and writes nothing. `monitor` scans every open
real-paper position, records the session evidence, and calls the frozen exit
observer. `fill` processes every due/retry exit intent for the supplied
session. Both mutation commands require explicit receipt paths and print each
event id plus whether it appended or replayed. Exit code 2 means authority or
evidence refusal; partial success must be reported per position and must never
look like a clean run.

Add a scoring CLI with a read-only preview and a separately gated finalizer:

```text
python -m options_researcher.h7_forward_scoring preview
python -m options_researcher.h7_forward_scoring finalize --owner carsyn
```

`preview` may read the verified real store but writes nothing and must still
say `NOT FINAL`. `finalize` is unavailable until the scoring output convention
and all §8 gates pass. Neither command accepts caller-supplied window bounds;
both derive the immutable bounds and scorer identity from seq 0.

The reviewed exit monitor must be wired into the daily ritual before entry
authority is allowed to append an intent. The ritual order must ensure due
exit fills and same-session monitoring cannot be skipped in favor of a new
entry. This wiring remains fail-closed and is part of the future build/review,
not this spec commit.

## 8. Required delta 6 — one durable scoring result

Introduce one new forward-ledger event type, `window_score`, and one immutable
receipt artifact:

```text
reports/h7_forward_scoring/<scope-id>/<final-decision-session>.json
```

The artifact is built with the repository's content-addressed receipt
primitive and has receipt type `window_score`. It contains the complete
JSON-safe result returned by the frozen scorer plus:

- scope id/hash and registration event id/hash;
- window start/end derived from seq 0;
- `input_ledger_head` captured before scoring;
- scorer module, config hash, cost-model hash, minimum-loss gate, bootstrap
  sample count, and forward contract count, all checked against seq 0;
- included/excluded cohort identity;
- finalization time and explicit owner acknowledgement; and
- the frozen disclaimer that `SURVIVED` is not validation, profitability,
  live-trading approval, or permission to change strategy rules.

The deterministic event id is
`h7:window_score:<scope-id>:<final-decision-session>`. Its causes include the
window registration and every included opening/closing fill used by the
score. Its payload carries the artifact path/hash, `input_ledger_head`, trade
count, overall verdict, and per-lane verdicts.

Finalization order is artifact first, ledger event second. An artifact without
the deterministic event is an orphan and is not authoritative; a retry may
append the event only after proving the artifact bytes and input head still
match. An existing event requires the exact existing artifact and makes every
later finalization an idempotent no-op. A different score, head, artifact, or
owner acknowledgement under the same id is a conflict, never an overwrite.

Finalization must refuse until:

1. the registered final decision session has completed;
2. every intent decided inside the window is terminal;
3. every included opening fill has exactly one valid closing fill;
4. the ledger, registration identities, code/config/cost/scorer identities,
   and all reconstructed economics verify;
5. no prior `window_score` exists; and
6. a fresh independent adversarial review and owner PASS for this real-store
   arc are recorded.

The scoring capability is a distinct typed door (for example,
`RealScoringSession`) accepted by the scorer only after these checks. Passing
the real path directly remains prohibited.

## 9. Required tests and adversarial review

The build arc must begin with tests and include, at minimum:

- forged/plain real paths and cross-capability objects refused;
- corrupt ledger, absent registration, wrong cohort, wrong date, stale hash
  contract, unlinked receipts, changed cache bytes, and future EOD refused;
- GO, NO_GO, missing quote, earnings-unknown, pre-earnings, scheduled-DTE,
  stop, profit-target, and credit-stop exit paths on the real capability;
- same-session observation of a newly opened fill;
- decision/evaluation offset mapping and T+1 derivation pinned;
- every monitoring and fill attempt leaves the required evidence or gap;
- duplicate/retry/concurrent calls are idempotent or conflict safely;
- scoring before window completion, with unresolved intent/open position,
  wrong scorer identity, changed config/cost, duplicate close, or existing
  different result refused;
- orphan-score-artifact recovery and score-event idempotency proven;
- no CLI can place an order, fetch data, rewrite a receipt, or mutate any
  store outside the explicit real forward ledger and scoring artifact path;
  and
- all current synthetic lifecycle/scoring tests remain green unchanged.

Acceptance requires focused tests, the complete offline suite, Ruff, Pyright,
forward-ledger verification, immutable-artifact snapshots, ritual syntax
check, a fresh-context independent adversarial review, remediation of every
blocker, and an owner-typed PASS.

## 10. Non-goals and frozen boundary

This arc does not add broker connectivity, order routing, live trading,
automatic owner approval, new entry logic, new exit logic, a threshold change,
an extra look at results, an interim verdict, or a second score. It does not
migrate or rewrite old receipts. It does not convert a paper result into a
strategy claim.

Build authorization, implementation, review, owner PASS, and ritual activation
are separate future steps. Until all of them complete, real exits and
real-store scoring remain locked even though their synthetic mechanics exist.
