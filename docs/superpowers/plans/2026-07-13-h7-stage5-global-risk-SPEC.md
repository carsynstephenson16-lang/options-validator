# H7 Stage 5 — global paper-book risk accounting: SPEC

**Status: PRE-REGISTRATION CANDIDATE. BUILD-ONLY, SYNTHETIC-ONLY, INACTIVE.
This stage may operate only on an explicit synthetic Stage-3 ledger directory.
It must not create `ledger/h7_forward/events.jsonl` or `HEAD`, modify the
owner-edited position mirror, activate the watcher, or create a real forward
event. Stage 8 remains the only activation gate.**

Ratified roadmap contract:

> Cross-symbol enforcement of the monthly sleeve (`H7_MONTHLY_AT_RISK`),
> `H7C_MAX_CONCURRENT`, and one-open-per-underlying at the BOOK level (the
> live analogue of the board resolver), reconciled daily against
> `data/positions/h7_positions.csv` with `open_h7_book` semantics.

## 1. Authority and state

The verified Stage-3 ledger is the sole source of truth. Stage 5 derives book
state by replaying lifecycle events; it never trusts mutable process memory or
the CSV mirror to authorize an entry. The existing CSV remains an
owner-maintained reconciliation target and is read-only to Stage 5.

All Stage-5 public operations require an explicit synthetic ledger directory
and inherit Stage 4's structural rejection of the real ledger, descendants,
and symlink aliases. A malformed or unverifiable ledger or mirror fails
closed.

## 2. Frozen capacity rules

Stage 5 introduces no parameter. It enforces the existing frozen values:

- `H7_MONTHLY_AT_RISK=6000`: sum actual `at_risk` for every entry paper fill
  whose fill session falls in the calendar month. A same-month close never
  restores capacity.
- `H7C_MAX_CONCURRENT=1`: open lane-c fills plus unresolved lane-c entry
  reservations may not exceed the basket-wide cap.
- `H7_MAX_OPEN_PER_UNDERLYING=1`: an open fill or unresolved entry reservation
  blocks every other lane for that underlying.

An unresolved `entry_intent` reserves its `decision_at_risk` in the calendar
month of `planned_fill_session`, its underlying, and (for lane c) one basket
seat. A matching entry `paper_fill` or terminal entry `skip` releases that
reservation; an opening fill replaces it with actual at-risk and open-book
occupancy. Reservations prevent separate sessions from oversubscribing
capacity while earlier T+1 intents are pending.

## 3. Board resolution

For each decision session, Stage 5:

1. replays the verified ledger through that session;
2. derives open symbols, open lane-c count, monthly actual risk, and earlier
   unresolved reservations;
3. invokes the existing deterministic `resolve_board` with remaining
   capacity; and
4. records one `board_resolution` caused by that session's `source_health`
   and `data_gate`, plus one `lane_displaced` per rejected candidate.

The board payload commits to the accepted/rejected candidates, actual and
reserved usage, remaining capacity, frozen limits, and a canonical hash of
the derived book snapshot. Candidate ordering and rejection vocabulary remain
owned by `h7_board`; Stage 5 does not create a second ordering algorithm.
Reruns are byte-identical idempotent appends; changed content under a stable
event identity is a conflict.

## 4. Fill-time enforcement

Stage 4 re-prices an accepted intent at T+1. Immediately before an opening
fill append, Stage 5 atomically rechecks the verified ledger after excluding
that intent's own reservation and substituting the actual fill at-risk.

If the actual fill would breach the monthly sleeve, one-open-per-underlying,
or lane-c cap, the entry records a terminal `skip` with reason
`book_capacity_at_fill`; it never scales, substitutes, delays, or chases.
The skip payload records the failed constraint and the complete capacity
snapshot. Exits are never blocked by an entry-risk cap.

The read/check/append boundary must be concurrency-safe. An optimistic
verified-head precondition (or an equivalent single lock-held transaction)
must make a changed ledger head fail and force recomputation; a stale capacity
snapshot may never append a fill.

## 5. Daily CSV reconciliation

Given an evaluation session and an explicit mirror path, Stage 5 compares the
mirror with ledger-derived rows using the existing columns:

`symbol,lane,opened,at_risk,closed`

`opened` is the entry fill session, `at_risk` is the actual opening-fill
charge, and `closed` is empty or the exit fill session. The reconciliation
also compares aggregate open symbols, open lane-c count, and calendar-month
risk under `open_h7_book` semantics. It returns a deterministic structured
report with `MATCH` or `MISMATCH` and explicit differences; it never edits the
CSV. Duplicate, future-dated, non-finite, non-positive, invalid-lane, or
otherwise malformed mirror rows fail closed.

Pending entry reservations are reported separately because the legacy CSV
cannot represent them; they do not create a false row mismatch.

## 6. Acceptance tests

The implementation is complete only when tests prove:

- empty, open, pending-exit, closed-same-month, prior-month, and month-boundary
  replay semantics;
- unresolved reservations block same-underlying, lane-c, and sleeve capacity,
  while a skip releases them and a fill replaces decision risk with actual;
- board results are deterministic, causally bound, fully auditable, and
  idempotent;
- fill-time adverse movement that breaches capacity produces a terminal skip;
- stale-head/concurrent contenders cannot both consume the same capacity;
- exact CSV match, every mismatch class, strict malformed-row refusal, and no
  mirror writes;
- the default real forward ledger remains absent and verifies `VALID EMPTY`;
  and
- the focused suite, complete suite, Ruff, Pyright, and pre-commit pass.

## 7. Stage boundary

Stage 5 does not calculate expectancy, confidence intervals, loss-count
gates, lane verdicts, or benchmarks (Stage 6); run an end-to-end dress
rehearsal (Stage 7); or authorize a real forward window (Stage 8).

