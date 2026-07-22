# H7 Real-Exit + Scoring Build Plan

**Executor:** this plan is written for Codex, working task-by-task, agentically. Each
task is a self-contained red/green/refactor unit: write a failing test against the
*actual* interfaces named below, run it, implement the minimal change, run to green,
lint/type-check, commit. Do not skip ahead to a later task's implementation while a
prior task's tests are red.

> ## GATE
> **Build authorized.** Ledger fact `H7_C1_EXIT_AND_SCORING_SPEC_RATIFIED`
> (2026-07-22T15:59:44Z, spec sha256
> `ca639c1eae4f01610d474c599e9c9cfe079919cc36935d83ced097a93e2c0bac`) authorizes
> implementation of `docs/superpowers/specs/2026-07-22-h7-real-exit-scoring-SPEC.md`.
>
> **ACTIVATION PROHIBITED.** This plan builds code only. It does **not** wire
> anything into `tools/daily_ritual.sh` — SPEC §7's "proposed Step 2c" ritual
> ordering is explicitly deferred: *"This wiring remains fail-closed and is part
> of the future build/review, not this spec commit."* Do not touch
> `tools/daily_ritual.sh` while executing this plan.
>
> **REAL EXITS AND REAL-STORE SCORING REMAIN INACTIVE** even after every task
> below is green. SPEC §9 requires, before any of this code may run against the
> real `ledger/h7_forward` store: the complete offline test suite green, Ruff,
> Pyright, forward-ledger verification, immutable-artifact snapshots, a ritual
> syntax check, **a fresh-context independent adversarial review**, remediation
> of every blocker it raises, and **a separate owner-typed PASS**. Finishing this
> plan's tasks is necessary, not sufficient. No task in this plan may declare
> activation, run any CLI it builds against `ledger/h7_forward`, or assert the
> exit/scoring path is "ready" beyond "build complete, pending §9 review."

## Goal

Build the receipt-bound real-store exit and scoring machinery (SPEC §3–§8) as
narrow additive seams on top of the frozen synthetic lifecycle and scorer, so a
future, separately-gated review/activation step can turn on real exits and a
one-time real-window score without touching their frozen computation.

## Architecture

A new `RealExitSession` capability (mirroring the existing entry-only
`RealStoreSession`) re-earns authority every session from the data-gate/source-health
receipt chain and authorizes `h7_paper_lifecycle.observe_exit`/`process_exit_fill`
through a typed resolution seam, exactly as `RealStoreSession` already does for
entries. A new `h7_exit_session.py` module owns the exit-only evidence publisher,
receipt loader, and CLI; a new `h7_real_scoring.py` module wraps
`h7_forward_scoring.score_forward_window` through an injected-base seam and owns the
one-time durable `window_score` ledger event plus its immutable JSON artifact. Both
frozen modules (`h7_paper_lifecycle.py`'s exit functions get only additive seams;
`h7_forward_scoring.py` gets **zero** changes) keep their existing computation
byte-identical.

## Tech stack

Python 3.12, `uv` (uv.lock is source of truth), `unittest` (offline, no network),
`ruff check .`, `pyright` (pyrightconfig.json include paths only).

---

## Task 1 — SPEC §3: `RealExitSession` authority type

### Files

- **Modify** `options_researcher/h7_paper_lifecycle.py`:
  - add `RealExitSession` frozen dataclass near `RealStoreSession` (currently
    lines 45–64)
  - extend `_synthetic_base` (lines 89–103) to also refuse a bare `RealExitSession`
    (symmetric with its existing `RealStoreSession` refusal at lines 90–93)
  - add `_resolve_exit_base(base_dir)` next to `_resolve_base` (lines 106–110)
  - change `observe_exit`'s first line (currently `base = _synthetic_base(base_dir)`
    at line 1050) and `process_exit_fill`'s first line (currently
    `base = _synthetic_base(base_dir)` at line 1242) to call
    `_resolve_exit_base(base_dir)` instead
- **Create** `tests/test_h7_exit_session.py` (new; mirrors the tempdir/registration
  fixture style of `tests/test_h7_session_real_path.py:1-140`)

### Steps

- [ ] 1.1 Write a failing test in the new `tests/test_h7_exit_session.py`:
  ```python
  """C1 real-exit-session tests, synthetic/temporary registered stores only."""
  from __future__ import annotations

  import tempfile
  import unittest
  from pathlib import Path

  from options_researcher import h7_paper_lifecycle as lifecycle


  class RealExitSessionTypeTests(unittest.TestCase):
      def test_real_exit_session_is_a_frozen_dataclass_with_required_fields(self):
          session = lifecycle.RealExitSession(
              base_dir=Path("ledger/h7_forward"),
              activation_event_id="wr:2026-07-20:70",
              decision_session="2026-07-20",
              evaluation_session="2026-07-17",
              decision_window_start="2026-07-20",
              decision_window_end="2026-10-26",
              included_symbols=("AMD", "AMZN"),
              data_gate_receipt_path=Path("dg.json"),
              source_health_receipt_path=Path("sh.json"),
              data_gate_receipt_hash="deadbeef",
              source_health_receipt_hash="beadfeed",
              data_gate_config_hash="cfg",
              data_gate_source_hash="src",
              input_bindings={},
          )
          with self.assertRaises(Exception):
              session.decision_session = "2026-07-21"  # frozen -> FrozenInstanceError

      def test_bare_real_exit_session_refuses_via_synthetic_base(self):
          session = lifecycle.RealExitSession(
              base_dir=lifecycle.REAL_FORWARD_STORE,
              activation_event_id="wr:x", decision_session="2026-07-20",
              evaluation_session="2026-07-17", decision_window_start="2026-07-20",
              decision_window_end="2026-10-26", included_symbols=("AMD",),
              data_gate_receipt_path=Path("dg.json"),
              source_health_receipt_path=Path("sh.json"),
              data_gate_receipt_hash="x", source_health_receipt_hash="y",
              data_gate_config_hash="z", data_gate_source_hash="w",
              input_bindings={},
          )
          with self.assertRaises(lifecycle.ActivationBoundaryError):
              lifecycle._synthetic_base(session)

      def test_real_store_session_cannot_authorize_an_exit(self):
          # Cross-capability refusal (SPEC §3): RealStoreSession is entry-only.
          with tempfile.TemporaryDirectory() as tmp:
              base = Path(tmp) / "forward"
              real_store_session_stub = lifecycle.RealStoreSession(
                  base_dir=base, activation_event_id="wr:x",
                  decision_session="2026-07-20", evaluation_session="2026-07-17",
                  data_gate_receipt_path=Path("dg.json"),
                  source_health_receipt_path=Path("sh.json"),
                  data_gate_receipt_hash="x", source_health_receipt_hash="y",
                  data_gate_config_hash="z", data_gate_source_hash="w",
                  included_symbols=("AMD",),
              )
              with self.assertRaises(lifecycle.ActivationBoundaryError):
                  lifecycle._resolve_exit_base(real_store_session_stub)


  if __name__ == "__main__":
      unittest.main()
  ```
- [ ] 1.2 Run `uv run python -m unittest tests.test_h7_exit_session -v` — expect
  `AttributeError: module 'options_researcher.h7_paper_lifecycle' has no attribute
  'RealExitSession'` (FAIL).
- [ ] 1.3 Implement `RealExitSession` in `h7_paper_lifecycle.py`, immediately after
  `RealStoreSession` (line 64). Per SPEC §3's field list ("the verified real-store
  path and sequence-zero registration id; the operational decision session and
  completed source-evaluation session; the immutable included cohort; the
  data-gate and linked source-health receipt paths and hashes; config and
  source-hash identities; and the exact per-symbol chain and close bindings for
  the monitored session"):
  ```python
  @dataclass(frozen=True)
  class RealExitSession:
      """Validated authority for the real forward-store EXIT path.

      Production callers obtain this through
      ``h7_exit_session.open_real_exit_session``. Mechanical paper-book authority
      only: it cannot propose an entry, approve an entry, place an order, or
      score the window (SPEC §3).
      """

      base_dir: Path
      activation_event_id: str
      decision_session: str
      evaluation_session: str
      decision_window_start: str
      decision_window_end: str
      included_symbols: tuple[str, ...]
      data_gate_receipt_path: Path
      source_health_receipt_path: Path
      data_gate_receipt_hash: str
      source_health_receipt_hash: str
      data_gate_config_hash: str
      data_gate_source_hash: str
      # {symbol: {"chain": <input_file_record dict>, "close": <input_file_record dict>}}
      # -- the exact receipt-bound bindings from the data-gate receipt's
      # input_files (SPEC §4: "the exit path should reuse those bindings
      # directly"), never a second mutable cache manifest.
      input_bindings: dict[str, dict]
  ```
- [ ] 1.4 In `_synthetic_base` (lines 89–103), add the symmetric refusal
  immediately after the existing `RealStoreSession` check:
  ```python
  if isinstance(base_dir, RealExitSession):
      raise ActivationBoundaryError(
          "RealExitSession authorizes exit transitions only; call it through "
          "_resolve_exit_base, not _synthetic_base"
      )
  ```
- [ ] 1.5 Add `_resolve_exit_base`, mirroring `_resolve_base` (lines 106–110)
  exactly:
  ```python
  def _resolve_exit_base(base_dir) -> Path:
      """Permit only the explicit exit-session key to select a real exit store."""
      if isinstance(base_dir, RealExitSession):
          return Path(base_dir.base_dir)
      return _synthetic_base(base_dir)
  ```
- [ ] 1.6 Change `observe_exit`'s and `process_exit_fill`'s first statement from
  `base = _synthetic_base(base_dir)` to `base = _resolve_exit_base(base_dir)`
  (one-line change at each of the two call sites; do not touch anything else in
  either function yet — that is Tasks 2–5).
- [ ] 1.7 Run `uv run python -m unittest tests.test_h7_exit_session -v` — expect
  PASS.
- [ ] 1.8 Run the full existing suite to prove nothing synthetic broke:
  `uv run python -m unittest discover -s tests` — expect all green (this is the
  §9 requirement "all current synthetic lifecycle/scoring tests remain green
  unchanged").
- [ ] 1.9 `uv run ruff check .` && `uv run pyright` — fix any findings.
- [ ] 1.10 Commit:
  ```
  feat(h7): add RealExitSession authority type per real-exit-scoring SPEC §3
  ```

---

## Task 2 — SPEC §4: per-session re-verification (`open_real_exit_session`)

### Files

- **Create** `options_researcher/h7_exit_session.py` (new module; mirrors
  `options_researcher/h7_session.py`'s structure — the exit-side twin, never
  importing anything that would let it reuse `h7_session.record_session_evidence`
  or bypass its refusals per SPEC §2/§5)
- **Modify** `tests/test_h7_exit_session.py` (add the factory tests)

### Steps

- [ ] 2.1 Write a failing test exercising the seven §4 sub-requirements against a
  synthetic-registered store, using the exact fixture pattern from
  `tests/test_h7_session_real_path.py:108-200` (`register_window`,
  `make_receipt("source_health", ...)`, `make_receipt("data_gate", ...)`, and
  patching `options_researcher.h7_watch.diagnostic_source_hash`):
  ```python
  class OpenRealExitSessionTests(RealSessionCaseForExits):  # reuse/adapt fixture
      def test_valid_receipt_chain_opens_a_session_with_window_bounds(self):
          from options_researcher import h7_exit_session as exit_session

          source_path, gate_path = self._write_receipts(EVALUATION)
          session = exit_session.open_real_exit_session(
              data_gate_receipt_path=gate_path,
              decision_session=DECISION,
              source_evaluation_session=EVALUATION,
              base_dir=self.base,
          )
          self.assertEqual(session.decision_session, DECISION)
          self.assertEqual(session.decision_window_start, DECISION)
          self.assertIn("AMD", session.included_symbols)

      def test_no_go_receipt_is_representable_and_still_opens(self):
          # SPEC §4: "The exit factory must be able to represent a valid NO_GO
          # data-gate receipt." NO_GO must not raise here.
          from options_researcher import h7_exit_session as exit_session

          source_path, gate_path = self._write_receipts(EVALUATION, verdict="NO_GO")
          session = exit_session.open_real_exit_session(
              data_gate_receipt_path=gate_path, decision_session=DECISION,
              source_evaluation_session=EVALUATION, base_dir=self.base,
          )
          self.assertEqual(session.data_gate_receipt_hash, load_receipt(
              gate_path, expected_type="data_gate")["receipt_hash"])

      def test_stale_cache_bytes_refuse(self):
          from options_researcher import h7_exit_session as exit_session

          source_path, gate_path = self._write_receipts(EVALUATION)
          session = exit_session.open_real_exit_session(
              data_gate_receipt_path=gate_path, decision_session=DECISION,
              source_evaluation_session=EVALUATION, base_dir=self.base,
          )
          # Mutate a bound chain file byte after receipt was validated.
          bound_path = Path(session.input_bindings["AMD"]["chain"]["path"])
          bound_path.write_bytes(bound_path.read_bytes() + b"\x00")
          with self.assertRaises(exit_session.ExitSessionRefused):
              exit_session.open_real_exit_session(
                  data_gate_receipt_path=gate_path, decision_session=DECISION,
                  source_evaluation_session=EVALUATION, base_dir=self.base,
              )

      def test_watcher_receipt_is_not_required(self):
          # SPEC §4: "it must not require an ENTRY-OK watcher row"
          import inspect
          from options_researcher import h7_exit_session as exit_session

          sig = inspect.signature(exit_session.open_real_exit_session)
          self.assertNotIn("watcher_receipt_path", sig.parameters)
  ```
- [ ] 2.2 Run `uv run python -m unittest tests.test_h7_exit_session -v` — expect
  `ImportError` / `AttributeError` (module doesn't exist yet) (FAIL).
- [ ] 2.3 Implement `options_researcher/h7_exit_session.py`. Mirror
  `h7_session.py`'s `open_real_session` (lines 77-162) closely, but per SPEC §4:
  - class `ExitSessionRefused(RuntimeError)` (the exit-side twin of
    `h7_session.SessionRefused`)
  - `open_real_exit_session(*, data_gate_receipt_path: Path, decision_session: str,
    source_evaluation_session: str | None = None, base_dir: Path =
    lifecycle.REAL_FORWARD_STORE) -> RealExitSession` that, in order (each item
    number below cites the exact SPEC §4 sub-requirement it implements):
    1. loads `cohort = h7_cohort.load_registered_cohort(base_dir=base)` (§4.1 —
       verify the forward hash chain and load the cohort/window from seq 0;
       `load_registered_cohort` already calls `ledger.verify` internally per
       `h7_cohort.py:48-58`)
    2. validates `decision_session` is either inside
       `[cohort.decision_window_start, cohort.decision_window_end]` **or** is a
       canonical XNYS session at all (session-level check only — the
       richer "OR any XNYS session at or after an in-window opening fill... at
       or before that position's expiration" authorization from §4 item 2 is
       necessarily **per-position**, since one `RealExitSession` monitors many
       positions; that per-position check is implemented in Task 5, inside
       `observe_exit`/`process_exit_fill` themselves, using the window bounds
       this factory stores on the returned `RealExitSession`.
       **This split is a design choice, not spelled out in the SPEC text — see
       Ambiguity A1.**)
    3. loads and integrity-checks the data-gate receipt via a NEW exit-scoped
       loader `validate_exit_data_gate_receipt` (built in Task 4, since it must
       accept NO_GO — stub it in this task as a thin call into
       `h7_watch.validate_data_gate_receipt`'s re-hash logic minus the
       `whole_universe_verdict == "GO"` requirement; Task 4 will replace the stub
       with the full exit-scoped loader and its own tests)
    4. requires receipt scope/session/link hashes/config hash/source hash/
       `source_hash_contract` to agree, "where 'agree' for the source hash means
       receipt-vs-LIVE-tree agreement... never receipt-vs-seq-0" (§4.4 — reuse
       `research.hashing.diagnostic_source_hash()` exactly as
       `h7_watch.validate_data_gate_receipt` does at line 116; do **not**
       compare against `cohort`/seq-0's `gates.source_hash`)
    5. re-hashes every named input via `research.receipts.input_file_record`
       (§4.5 — same pattern as `h7_watch.validate_data_gate_receipt` lines
       118-124)
    6. loads only the exact chain/close files named in the data-gate receipt's
       `input_files` (keys `chain:<symbol>` / `close:<symbol>`, built by
       `h7_data_gate.build_receipt` at lines 369-377) and re-hashes the binding
       again after load (§4.6) — build the `input_bindings` dict for
       `RealExitSession` from these, one dict per symbol with `"chain"` and
       `"close"` sub-keys, each an `input_file_record`-shaped dict
    7. refuses stale/missing/changed/future/fallback/cross-session data (§4.7 —
       falls out of steps 3-6 raising `ExitSessionRefused`)
  - Return the constructed `RealExitSession` with
    `activation_event_id=cohort.event_id`,
    `decision_window_start=cohort.decision_window_start`,
    `decision_window_end=cohort.decision_window_end`,
    `included_symbols=cohort.included`.
- [ ] 2.4 Run `uv run python -m unittest tests.test_h7_exit_session -v` — expect
  PASS.
- [ ] 2.5 Add a cross-capability refusal test: passing a `RealStoreSession`,
  a forged dataclass, or a plain path resolving to `ledger/h7_forward` into
  `open_real_exit_session`'s `base_dir` refuses without mutation (per SPEC §3's
  "Passing a plain path resolving to `ledger/h7_forward`, a `RealStoreSession`,
  a forged dataclass, or any other object must continue to fail closed"). Run,
  confirm it passes given the implementation above (it should, since `base_dir`
  is always resolved through `_synthetic_base`/`REAL_FORWARD_STORE` identity
  checks before any real content is touched); if it doesn't, that's this task's
  remaining red test to fix.
- [ ] 2.6 `uv run python -m unittest discover -s tests` — full suite green.
- [ ] 2.7 `uv run ruff check .` && `uv run pyright`.
- [ ] 2.8 Commit:
  ```
  feat(h7): open_real_exit_session per-session re-verification per real-exit-scoring SPEC §4
  ```

---

## Task 3 — SPEC §4a: pre-registered expiration settlement

> **This task's leg-encoding design is provisional — see Ambiguity A2 before
> implementing.** The settlement *rule* (intrinsic value against the
> receipt-bound close) is frozen and unambiguous; how a no-quote settlement leg
> satisfies the frozen scorer's quote-based reconstruction is not addressed by
> the SPEC and is a real open question, not a coding detail.

### Files

- **Modify** `options_researcher/h7_paper_lifecycle.py`:
  - `observe_exit`'s expiration guard (currently raises at lines 1073-1076 when
    `evaluation_session >= expiration`)
  - `process_exit_fill`'s expiration guard (currently raises at lines 1284-1286
    when `fill_session >= expiration`)
  - add a new function `settle_expiration_close(...)`
- **Modify** `tests/test_h7_paper_lifecycle.py` (add a `TestExpirationSettlement`
  class near `TestExitLifecycle`, currently starting at line 784)

### Steps

- [ ] 3.1 Write a failing test proving the *current* frozen behavior (a position
  reaching expiration with an unresolved exit still fails loud) stays unchanged
  for the plain synthetic path — this pins §2's "unchanged" guarantee before
  adding the new settlement door:
  ```python
  class TestExpirationSettlementDoorIsAdditive(TestExitLifecycle):
      def test_plain_synthetic_process_exit_fill_still_fails_loud_at_expiration(self):
          # SPEC §2: existing frozen raise behavior must not change for callers
          # that never invoke the new settlement door.
          opened = self.open_position()
          expiration = opened.payload["action"]["expiration"]
          self.exit_gate(expiration, "dg:atexp")
          with self.assertRaises(life.LifecycleValidationError):
              life.observe_exit(
                  base_dir=self.base, position_id=opened.payload["position_id"],
                  evaluation_session=expiration, chain=chain(),
                  data_gate_id="dg:atexp", chain_identity="sha256:x",
                  closes_identity="sha256:y", underlying_close=100.0,
                  earnings_gate="CLEAR", next_report=None, source_health_id=None,
                  clock=clock("2026-09-01T01:00:00+00:00"),
              )
  ```
  Run it — it should already pass today (documents current behavior; if it
  fails, something upstream regressed — stop and investigate before continuing).
- [ ] 3.2 Write the failing test for the new settlement function (long call,
  in-the-money at expiration, no valid closing fill available):
  ```python
  class TestExpirationSettlement(TestExitLifecycle):
      def test_itm_long_call_settles_at_intrinsic_against_receipt_close(self):
          opened = self.open_position()  # long_call, strike from long_action()
          strike = opened.payload["action"]["strike"]
          expiration = opened.payload["action"]["expiration"]
          self.exit_gate(expiration, "dg:settle")
          underlying_close_at_expiration = strike + 12.0  # ITM by $12
          result = life.settle_expiration_close(
              base_dir=self.base,
              position_id=opened.payload["position_id"],
              expiration_session=expiration,
              data_gate_id="dg:settle",
              underlying_close=underlying_close_at_expiration,
              closes_identity="sha256:expiration-close",
              clock=clock("2026-09-01T01:00:00+00:00"),
          )
          self.assertEqual(result.event_type, "paper_fill")
          self.assertEqual(result.payload["transition"], "close")
          self.assertEqual(result.payload["settlement"], True)
          self.assertEqual(
              result.payload["settlement_reason"], "expiration_no_valid_close"
          )
          self.assertEqual(life.replay_positions(base_dir=self.base)[0].state,
                            "closed")

      def test_otm_beyond_doubt_with_no_underlying_close_settles_at_zero(self):
          # SPEC §4a: "If the receipt-bound underlying close for the expiration
          # session is itself unavailable... OTM beyond doubt at zero".
          opened = self.open_position()
          expiration = opened.payload["action"]["expiration"]
          self.exit_gate(expiration, "dg:settle2")
          result = life.settle_expiration_close(
              base_dir=self.base, position_id=opened.payload["position_id"],
              expiration_session=expiration, data_gate_id="dg:settle2",
              underlying_close=None, closes_identity=None,
              otm_beyond_doubt=True,
              clock=clock("2026-09-01T01:00:00+00:00"),
          )
          self.assertEqual(result.payload["settlement_reason"],
                            "no_close_otm_beyond_doubt_zero")

      def test_already_closed_position_refuses(self):
          # Idempotency/safety: cannot re-settle a resolved position.
          ...  # exercise via a fully closed position, assertRaises LifecycleValidationError
  ```
- [ ] 3.3 Run `uv run python -m unittest tests.test_h7_paper_lifecycle -v` —
  expect `AttributeError: ... no attribute 'settle_expiration_close'` (FAIL).
- [ ] 3.4 Implement `settle_expiration_close` in `h7_paper_lifecycle.py`, placed
  after `process_exit_fill` (after line 1369). Signature:
  ```python
  def settle_expiration_close(
      *, base_dir, position_id: str, expiration_session: str, data_gate_id: str,
      closes_identity: str | None, underlying_close: float | None = None,
      otm_beyond_doubt: bool = False, clock=None,
  ) -> TransitionResult:
      """SPEC §4a: a pre-registered, zero-discretion terminal accounting rule —
      not a new exit trigger. Only reachable when the position has no valid
      closing fill AND evaluation_session has reached contract expiration.
      """
  ```
  Behavior, per SPEC §4a verbatim:
  - resolve `base = _resolve_exit_base(base_dir)` (real or synthetic, same
    boundary as `observe_exit`/`process_exit_fill`)
  - load the position via `_position(base, position_id)`; refuse if already
    `"closed"` (idempotency/safety)
  - require `expiration_session == position.entry_payload["action"]["expiration"]`
    (this function settles exactly the expiration session, never earlier)
  - require a `data_gate` event exists for `expiration_session` (reuse
    `_require_event`)
  - **valuation branch** (long legs pay `max(0, S-K)` for calls / `max(0, K-S)`
    for puts; short legs charged symmetrically; §4a):
    - if `underlying_close is not None`: compute per-leg intrinsic value from
      `position.entry_payload["legs"]` (the frozen action/legs — same source
      `_close_prices` reads) against `underlying_close`
    - if `underlying_close is None` and `otm_beyond_doubt`: value the position at
      zero (§4a: "OTM beyond doubt... at zero")
    - if `underlying_close is None` and not `otm_beyond_doubt`: value at
      full-width loss for the defined-risk structure (§4a: "ITM or
      undeterminable defined-risk structures at full-width loss")
  - **PROVISIONAL — resolve Ambiguity A2 before finishing this step**: encode
    the settled legs so `h7_forward_scoring._fill_price`
    (`h7_forward_scoring.py:142-169`) can reconstruct them unmodified. That
    function recomputes `expected = adverse_buy(ask)` or `adverse_sell(bid)` and
    requires `passes_liquidity(open_interest, bid, ask)` and `quote_valid(bid,
    ask)` to hold. A settlement leg has no real quote or open interest. Do not
    silently invent a "fake quote" without the resolution below being ratified;
    write the failing test in 3.5 pinned to whichever resolution is chosen.
  - emit `payload["settlement"] = True` and
    `payload["settlement_reason"]` ∈
    `{"expiration_no_valid_close", "no_close_otm_beyond_doubt_zero",
    "no_close_full_width_loss"}`
  - emit the event as `event_type="paper_fill"`, `payload["transition"] =
    "close"` (so `h7_forward_book.derive_book` and
    `h7_forward_scoring.score_forward_window` both treat it as an ordinary
    close with **zero changes to either module** — this is what makes §4a's
    "scoring becomes reachable" claim true)
  - event id: reuse `_exit_fill_id(exit_intent_id, expiration_session)` if an
    `exit_intent` already exists for the position at/before expiration, else a
    new deterministic id `f"s4.settlement:{expiration_session}:{position.position_id}"`
    — **flag which id scheme is correct as part of Ambiguity A2's resolution**;
    either must be stable/idempotent and must not collide with a real
    `process_exit_fill` close for the same position.
  - add the assignment/pin-risk disclosure only at the scoring-artifact layer
    (§8, Task 7), not on every settlement event — settlement events themselves
    just need to be truthfully labeled `settlement: true`.
- [ ] 3.5 Run `uv run python -m unittest tests.test_h7_paper_lifecycle -v` until
  green, iterating on the leg-encoding resolution from 3.4.
- [ ] 3.6 Add a round-trip test: build a synthetic ledger with one settled
  position (via `settle_expiration_close`) plus one ordinary closed position,
  call `h7_forward_scoring.score_forward_window` **unmodified** over both, and
  assert it returns a trade for the settled position with no
  `ScoringValidationError`. This is the direct proof that §4a's "scoring becomes
  reachable" claim holds against the *actual*, unmodified scorer — write it in
  `tests/test_h7_forward_scoring.py` as a new test class, not by editing that
  module's frozen logic.
- [ ] 3.7 `uv run python -m unittest discover -s tests` — full suite green.
- [ ] 3.8 `uv run ruff check .` && `uv run pyright`.
- [ ] 3.9 Commit:
  ```
  feat(h7): expiration settlement close per real-exit-scoring SPEC §4a
  ```

---

## Task 4 — SPEC §5: exit evidence publisher

### Files

- **Modify** `options_researcher/h7_exit_session.py` (add the publisher/loader;
  replace Task 2's stub loader with the real one)
- **Modify** `tests/test_h7_exit_session.py`

### Steps

- [ ] 4.1 Write failing tests for the exit-scoped receipt loader accepting
  NO_GO, per SPEC §5:
  ```python
  class ValidateExitDataGateReceiptTests(RealSessionCaseForExits):
      def test_no_go_receipt_is_accepted_and_verdict_counts_recorded(self):
          from options_researcher import h7_exit_session as exit_session

          source_path, gate_path = self._write_receipts(EVALUATION, verdict="NO_GO")
          receipt = exit_session.validate_exit_data_gate_receipt(
              gate_path, evaluation_session=EVALUATION,
              names=list(self.scope["symbols"]),
          )
          self.assertEqual(receipt["whole_universe_verdict"], "NO_GO")

      def test_stale_config_hash_refuses(self):
          from options_researcher import h7_exit_session as exit_session
          ...  # write a gate receipt with config_hash="stale", assertRaises

      def test_unlinked_source_health_refuses(self):
          ...
  ```
- [ ] 4.2 Write failing tests for `record_exit_evidence`:
  ```python
  class RecordExitEvidenceTests(RealSessionCaseForExits):
      def test_go_evidence_matches_receipt_verdict_and_counts(self):
          from options_researcher import h7_exit_session as exit_session

          source_path, gate_path = self._write_receipts(EVALUATION)
          session = exit_session.open_real_exit_session(
              data_gate_receipt_path=gate_path, decision_session=DECISION,
              source_evaluation_session=EVALUATION, base_dir=self.base,
          )
          evidence = exit_session.record_exit_evidence(
              session, symbol="AMD", earnings_dependent=False,
          )
          self.assertEqual(evidence.data_gate.event_type, "data_gate")
          self.assertIsNone(evidence.source_health)

      def test_earnings_dependent_exit_publishes_unhealthy_source_health(self):
          # SPEC §5: "The frozen earnings_unknown exit requires a source-health
          # evidence event carrying healthy: false -- which the entry publisher
          # can never emit."
          from options_researcher import h7_exit_session as exit_session

          source_path, gate_path = self._write_receipts(
              EVALUATION, unhealthy=("AMD",)
          )
          session = exit_session.open_real_exit_session(
              data_gate_receipt_path=gate_path, decision_session=DECISION,
              source_evaluation_session=EVALUATION, base_dir=self.base,
          )
          evidence = exit_session.record_exit_evidence(
              session, symbol="AMD", earnings_dependent=True,
          )
          self.assertIsNotNone(evidence.source_health)
          self.assertEqual(evidence.source_health.payload["healthy"], False)

      def test_non_earnings_exit_never_fabricates_source_health(self):
          # SPEC §5: "A non-earnings exit must not fabricate an unnecessary
          # source-health cause."
          ...  # earnings_dependent=False -> evidence.source_health is None

      def test_go_data_gate_event_id_matches_entry_publisher_scheme(self):
          # Same deterministic id as h7_session.record_session_evidence's
          # gate_id = f"h7:data_gate:{session}" -- idempotent across the two
          # publishers on a GO day (SPEC §5).
          ...
  ```
- [ ] 4.3 Run `uv run python -m unittest tests.test_h7_exit_session -v` — expect
  FAIL (functions don't exist).
- [ ] 4.4 Implement `validate_exit_data_gate_receipt` in
  `h7_exit_session.py`, mirroring `h7_watch.validate_data_gate_receipt`
  (`h7_watch.py:66-125`) line-for-line **except**: drop the
  `receipt.get("whole_universe_verdict") != "GO"` refusal (line 89) and the
  `go_count` check (lines 90-91) entirely — accept whatever verdict/counts the
  receipt states; keep every other check (scope, session, source-health link
  hash/session/scope, `changed_input_files`, `config_hash`, `diagnostic_source_hash`,
  per-file re-hash) byte-for-byte identical to `h7_watch.py`'s version, per SPEC
  §5's requirement to "still checking scope, session, config hash, live source
  hash, source-hash contract, linked source-health hash, and re-hashing every
  named input."
- [ ] 4.5 Implement a typed result and `record_exit_evidence`:
  ```python
  @dataclass(frozen=True)
  class ExitSessionEvidence:
      data_gate: lifecycle.TransitionResult
      source_health: lifecycle.TransitionResult | None


  def record_exit_evidence(
      session: RealExitSession, *, symbol: str, earnings_dependent: bool
  ) -> ExitSessionEvidence:
      """Publish the session's verified data_gate evidence (any verdict), and
      the per-symbol source_health event ONLY when earnings_dependent (SPEC §5).
      """
  ```
  Body:
  - re-load and re-validate the receipt chain (mirroring
    `h7_session.record_session_evidence`'s re-validation-before-publication
    pattern at `h7_session.py:184-207`, but via
    `validate_exit_data_gate_receipt`)
  - publish `data_gate` at id `f"h7:data_gate:{session.evaluation_session}"`
    with `payload["whole_universe_verdict"]` = the receipt's actual verdict and
    `go_count`/`no_go_count` copied from the receipt (not hardcoded `"GO"` —
    this is the literal difference from `h7_session.record_session_evidence`
    lines 231-254 that SPEC §5 requires)
  - when `earnings_dependent`: load the linked source-health receipt, publish
    `source_health` at id `f"h7:source_health:{session.evaluation_session}:{symbol}"`
    with `payload["healthy"]` / `payload["gate"]` copied from the receipt's
    per-symbol entry (which may be `False`/`"UNKNOWN"` — unlike
    `h7_session.record_session_evidence`'s hardcoded `True`/`"CLEAR"` at lines
    268-270); when not `earnings_dependent`, `source_health` stays `None` and no
    event is appended
- [ ] 4.6 Wire `open_real_exit_session` (Task 2) to call
  `validate_exit_data_gate_receipt` instead of its Task-2 stub.
- [ ] 4.7 Run `uv run python -m unittest tests.test_h7_exit_session -v` — green.
- [ ] 4.8 `uv run python -m unittest discover -s tests` — full suite green.
- [ ] 4.9 `uv run ruff check .` && `uv run pyright`.
- [ ] 4.10 Commit:
  ```
  feat(h7): exit-evidence publisher and receipt loader per real-exit-scoring SPEC §5
  ```

---

## Task 5 — SPEC §6: decision session vs. evaluation session

### Files

- **Modify** `options_researcher/h7_paper_lifecycle.py`:
  - add `_operational_exit_decision_session(base_dir, source_session)` next to
    `_operational_decision_session` (lines 113-121)
  - add `_require_exit_window_authority(base_dir, position, operational_decision)`
    (new private helper implementing SPEC §4 item 2's post-window authorization,
    deferred here because it needs the decision/evaluation mapping from this
    task to know the operational date)
  - modify `observe_exit` (from line 1029): compute
    `operational_decision = _operational_exit_decision_session(base_dir,
    evaluation_session)`; change `planned_fill = _next_session(evaluation_session)`
    (line 1069) to `planned_fill = _next_session(operational_decision)`; add
    `"decision_session": operational_decision` to the `exit_intent` payload dict
    (currently built at lines 1199-1212, which has no `decision_session` key
    today); call `_require_exit_window_authority(...)` before emitting the
    intent
  - modify `process_exit_fill` similarly where it needs the mapped date (its
    retry-session arithmetic at lines 1257-1271 is keyed off the **stored**
    `intent.payload["planned_fill_session"]`, which already carries the mapped
    value once `observe_exit` is fixed above — `process_exit_fill` itself needs
    no `_next_session` change, only the `_require_exit_window_authority` call
    for defense-in-depth on the fill path too)
- **Modify** `tests/test_h7_paper_lifecycle.py`

### Steps

- [ ] 5.1 Write the failing "same-session observation" acceptance test verbatim
  from SPEC §6: *"a real opening fill recorded on source session E must be
  observed by an exit pass parameterized with source session E in the same
  run, and a triggered intent's planned fill must equal the next XNYS session
  after the mapped operational decision date."*
  ```python
  class TestDecisionEvaluationMapping(RealSessionCaseForExits):
      def test_same_session_observation_of_a_newly_opened_fill(self):
          # Build a RealStoreSession-backed entry that fills on source
          # session E, then a RealExitSession for the SAME E observes it in
          # the same run.
          ...
          opening = session_module.fill_entry(...)  # fills on source session E
          exit_evidence = exit_session.record_exit_evidence(
              exit_session_obj, symbol="AMD", earnings_dependent=False,
          )
          result = life.observe_exit(
              base_dir=exit_session_obj,
              position_id=opening.payload["position_id"],
              evaluation_session=E,  # SAME session as the opening fill
              chain=..., data_gate_id=exit_evidence.data_gate.event_id,
              chain_identity=..., closes_identity=..., underlying_close=...,
              earnings_gate="CLEAR", next_report=None, source_health_id=None,
          )
          # planned fill = next XNYS session after the MAPPED operational date,
          # not after the raw source session E.
          expected_planned = ...  # compute via the mapped decision_session
          self.assertEqual(result.payload["planned_fill_session"], expected_planned)
          self.assertEqual(result.payload["decision_session"], mapped_decision)
          self.assertEqual(result.payload["evaluation_session"], E)  # unchanged: source date

      def test_synthetic_caller_keeps_decision_equal_to_evaluation(self):
          # SPEC §6: "For synthetic callers the two dates remain identical,
          # preserving current tests and public behavior."
          opened = self.open_position()
          self.exit_gate("2026-07-14", "dg:exit")
          result = life.observe_exit(
              base_dir=self.base, position_id=opened.payload["position_id"],
              evaluation_session="2026-07-14", chain=chain(bid=10.30, ask=10.40),
              data_gate_id="dg:exit", chain_identity="sha256:x",
              closes_identity="sha256:y", underlying_close=90.0,
              earnings_gate="CLEAR", next_report=None, source_health_id=None,
              clock=clock("2026-07-15T01:00:00+00:00"),
          )
          self.assertEqual(result.payload["decision_session"], "2026-07-14")

      def test_inconsistent_receipt_date_refuses(self):
          # SPEC §6: "It must reject an inconsistent receipt date, an exit
          # before the opening fill, a decision outside the allowed
          # window/fill lineage, and any attempt to use today's unfinished
          # EOD as completed evidence."
          ...

      def test_post_window_monitoring_of_in_window_position_is_authorized(self):
          # SPEC §4 item 2 / §9: post-window authority.
          ...  # position opened inside window, decision_session AFTER window_end -> allowed

      def test_new_entry_intent_still_bounded_by_window_end(self):
          # Negative control: post-window authority never extends to NEW entries.
          ...  # entry-side open_real_session already enforces this; assert it
               # is UNCHANGED by this task (regression guard, not new behavior)
  ```
- [ ] 5.2 Run `uv run python -m unittest tests.test_h7_paper_lifecycle -v` and
  `tests.test_h7_exit_session` — expect FAIL (`decision_session` missing from
  payload; `planned_fill_session` computed from the wrong date).
- [ ] 5.3 Implement `_operational_exit_decision_session`, mirroring
  `_operational_decision_session` (lines 113-121) exactly:
  ```python
  def _operational_exit_decision_session(base_dir, source_session: str) -> str:
      """Map a real exit session's source-data date to its registered decision
      date (SPEC §6). Identity for every synthetic caller."""
      if not isinstance(base_dir, RealExitSession):
          return source_session
      if base_dir.evaluation_session != source_session:
          raise LifecycleValidationError(
              "RealExitSession evaluation_session does not match exit source data"
          )
      return base_dir.decision_session
  ```
- [ ] 5.4 Implement `_require_exit_window_authority`:
  ```python
  def _require_exit_window_authority(
      base_dir, position: PaperPosition, operational_decision: str
  ) -> None:
      """SPEC §4 item 2: authorize in-window monitoring/fills normally, and
      post-window monitoring/fill/retry/settlement sessions ONLY for positions
      causally descended from an in-window opening fill. Never authorizes a
      new entry intent (entries are gated entirely separately, in
      h7_session.open_real_session)."""
      if not isinstance(base_dir, RealExitSession):
          return
      start, end = base_dir.decision_window_start, base_dir.decision_window_end
      if start <= operational_decision <= end:
          return
      opened_decision = position.entry_payload.get("decision_session")
      if not (isinstance(opened_decision, str) and start <= opened_decision <= end):
          raise LifecycleValidationError(
              f"exit decision session {operational_decision} is outside the "
              f"registered window [{start}, {end}] and position "
              f"{position.position_id!r} was not opened in-window"
          )
  ```
  Call this from `observe_exit` right after computing `operational_decision`
  and loading `position`, and from `process_exit_fill` right after loading
  `position` (via `intent.payload["position_id"]`) — before either function does
  anything else with `base_dir` as a `RealExitSession`.
- [ ] 5.5 In `observe_exit`: replace `planned_fill = _next_session(evaluation_session)`
  with `operational_decision = _operational_exit_decision_session(base_dir,
  evaluation_session)` followed by `planned_fill = _next_session(operational_decision)`;
  add `"decision_session": operational_decision` to the payload dict (SPEC §6:
  *"`decision_session` is the operational session governed by the registered
  window and is recorded in the exit-intent payload"*); keep
  `"trigger_session": evaluation_session` unchanged (SPEC §6: *"the stored
  event's `evaluation_session` remains the source date"* — `evaluation_session`
  the ledger field, not to be confused with `trigger_session` the payload key,
  both already equal `evaluation_session` today).
- [ ] 5.6 Run tests, iterate to green.
- [ ] 5.7 `uv run python -m unittest discover -s tests` — full suite green
  (confirms synthetic exit tests in `TestExitLifecycle` at
  `tests/test_h7_paper_lifecycle.py:784` are unaffected, since
  `_operational_exit_decision_session` is identity for non-`RealExitSession`
  callers).
- [ ] 5.8 `uv run ruff check .` && `uv run pyright`.
- [ ] 5.9 Commit:
  ```
  feat(h7): decision/evaluation session mapping for exits per real-exit-scoring SPEC §6
  ```

---

## Task 6 — SPEC §7: owner-visible exit and scoring CLIs (not ritual-wired)

### Files

- **Modify** `options_researcher/h7_exit_session.py` (add `main()`)
- **Create** `options_researcher/h7_real_scoring.py` (new module; `main()` only
  — `preview` in this task, `finalize` stubbed to "unavailable" until Task 7)
- **Create** `tests/test_h7_real_scoring.py`
- **Modify** `tests/test_h7_exit_session.py` (CLI tests)

### Steps

- [ ] 6.1 Write failing CLI tests for `h7_exit_session`:
  ```python
  class ExitSessionCLITests(RealSessionCaseForExits):
      def test_status_validates_and_writes_nothing(self):
          from options_researcher import h7_exit_session as exit_session

          source_path, gate_path = self._write_receipts(EVALUATION)
          before = _snapshot(self.base)
          rc = exit_session.main([
              "status", "--data-gate-receipt", str(gate_path),
              "--decision-session", DECISION,
              "--source-evaluation-session", EVALUATION,
              "--base-dir", str(self.base),
          ])
          self.assertEqual(rc, 0)
          self.assertEqual(_snapshot(self.base), before)

      def test_monitor_requires_explicit_receipt_path(self):
          from options_researcher import h7_exit_session as exit_session
          import argparse

          with self.assertRaises(SystemExit):
              exit_session.main(["monitor", "--decision-session", DECISION])

      def test_authority_refusal_exits_2(self):
          from options_researcher import h7_exit_session as exit_session

          rc = exit_session.main([
              "status", "--data-gate-receipt", "/no/such/receipt.json",
              "--decision-session", DECISION, "--base-dir", str(self.base),
          ])
          self.assertEqual(rc, 2)

      def test_fill_reports_appended_or_replayed_per_event(self):
          ...  # capture stdout, assert each event id + appended=True/False printed
  ```
- [ ] 6.2 Write failing CLI tests for `h7_real_scoring preview`:
  ```python
  class RealScoringPreviewTests(unittest.TestCase):
      def test_preview_says_not_final(self):
          from options_researcher import h7_real_scoring as real_scoring
          buf = io.StringIO()
          with redirect_stdout(buf):
              rc = real_scoring.main(["preview"])
          self.assertIn("NOT FINAL", buf.getvalue())

      def test_preview_accepts_no_window_bounds_flags(self):
          # SPEC §7: "Neither command accepts caller-supplied window bounds;
          # both derive the immutable bounds and scorer identity from seq 0."
          import argparse
          from options_researcher import h7_real_scoring as real_scoring
          with self.assertRaises(SystemExit):
              real_scoring.main(["preview", "--window-start", "2026-01-01"])

      def test_finalize_is_unavailable_before_task_7(self):
          from options_researcher import h7_real_scoring as real_scoring
          rc = real_scoring.main(["finalize", "--owner", "carsyn"])
          self.assertEqual(rc, 2)
  ```
- [ ] 6.3 Run both new test files — expect FAIL (modules/CLIs don't exist).
- [ ] 6.4 Implement `h7_exit_session.main()`, mirroring `h7_session.py`'s CLI
  structure (`_add_session_arguments` at lines 480-493, `main` at 496-592), with
  the three subcommands SPEC §7 names literally:
  ```
  python -m options_researcher.h7_exit_session status ...
  python -m options_researcher.h7_exit_session monitor ...
  python -m options_researcher.h7_exit_session fill ...
  ```
  - `status`: calls `open_real_exit_session(...)`, prints readiness, **writes
    nothing** (per SPEC §7: *"`status` validates authority and writes
    nothing."*)
  - `monitor`: for every open real-paper position (read via
    `lifecycle.replay_positions(base_dir=session)` — note: `replay_positions`
    currently calls `_synthetic_base` at line 1428; it must be reachable for a
    `RealExitSession` too — extend `replay_positions`'s resolution the same way
    as Task 1 did for `observe_exit`/`process_exit_fill`, i.e. add this call
    site to use `_resolve_exit_base` as well, with its own dedicated test), call
    `record_exit_evidence` then `lifecycle.observe_exit(...)`. Print each event
    id and `appended=True/False`; refuse (exit 2) on any authority/evidence
    error without silently continuing to the next position — "partial success
    must be reported per position and must never look like a clean run" (SPEC
    §7): accumulate per-position outcomes and print a summary line, but the
    process exit code must be 2 if **any** position refused.
  - `fill`: for every due/retry exit intent in the supplied session, call
    `lifecycle.process_exit_fill(...)`. Same per-position reporting/exit-code
    discipline as `monitor`.
  - No network calls, no order-placement surface anywhere in this file (grep
    check in 6.7 below).
- [ ] 6.5 Implement `h7_real_scoring.py`'s `main()` with the two subcommands:
  ```
  python -m options_researcher.h7_real_scoring preview
  python -m options_researcher.h7_real_scoring finalize --owner carsyn
  ```
  - `preview`: reads the verified real store (via the copy-and-call seam
    described in Task 7 — for this task, a minimal version is acceptable that
    calls `h7_forward_scoring.score_forward_window` over a **byte-identical
    temporary copy** of `ledger/h7_forward` and always prints `NOT FINAL`
    prominently; **writes nothing**
  - `finalize`: in this task, print `"finalize is not available until the SPEC
    §8 gates are implemented (Task 7)"` and return `2` unconditionally — Task 7
    replaces this stub with the real refusal chain and gates
  - argparse must not expose any window-bounds flag (SPEC §7: *"Neither
    command accepts caller-supplied window bounds"*)
- [ ] 6.6 Run both test files to green.
- [ ] 6.7 Add one grep-based safety test (or a `unittest` test using
  `ast`/plain substring search) asserting neither new module imports any
  order-placement or broker module and neither calls `requests`/`httpx`/network
  primitives — cheap insurance for the §9 requirement *"no CLI can place an
  order, fetch data, rewrite a receipt, or mutate any store outside the
  explicit real forward ledger and scoring artifact path."*
- [ ] 6.8 `uv run python -m unittest discover -s tests` — full suite green.
- [ ] 6.9 `uv run ruff check .` && `uv run pyright`.
- [ ] 6.10 Commit:
  ```
  feat(h7): exit and real-scoring CLIs per real-exit-scoring SPEC §7
  ```

---

## Task 7 — SPEC §8: one durable `window_score` result

### Files

- **Modify** `options_researcher/h7_event_ledger.py`: add `"window_score"` to
  `EVENT_TYPES` (currently lines 52-57)
- **Modify** `options_researcher/h7_real_scoring.py`: implement `finalize` for
  real, add `RealScoringSession`, the artifact builder, and the copy-and-call
  seam into `score_forward_window`
- **Modify** `tests/test_h7_real_scoring.py`

### Steps

- [ ] 7.1 Write a failing test that `"window_score"` is a legal event type:
  ```python
  def test_window_score_is_a_known_event_type(self):
      from options_researcher import h7_event_ledger as ledger
      self.assertIn("window_score", ledger.EVENT_TYPES)
  ```
  Run, expect FAIL. Add `"window_score",` to the `EVENT_TYPES` tuple in
  `h7_event_ledger.py:52-57` (one-line change; this is the only edit this whole
  plan makes to that module, and it is explicitly required by SPEC §8: *"one
  new forward-ledger event type, `window_score`"*). Run
  `uv run python -m unittest tests.test_h7_event_ledger -v` to confirm nothing
  else in that frozen suite broke. Commit this one-line change together with
  the rest of this task (do not split it into its own commit).
- [ ] 7.2 Write the failing test for the copy-and-call seam (the mechanism that
  lets the wrapper call `score_forward_window` over real events without adding
  any seam to `h7_forward_scoring.py` itself — **see Ambiguity A3**; this is
  the interpretation this plan adopts for *"a narrow injected-base seam"*,
  confirm it during the SPEC §9 adversarial review before relying on it):
  ```python
  class MaterializeRealSnapshotTests(unittest.TestCase):
      def test_snapshot_is_byte_identical_copy_verified_independently(self):
          from options_researcher import h7_real_scoring as real_scoring
          from options_researcher import h7_event_ledger as ledger

          # Build a small synthetic ledger standing in for "the real store"
          # (never touch lifecycle.REAL_FORWARD_STORE from a test).
          with tempfile.TemporaryDirectory() as tmp:
              fake_real = Path(tmp) / "forward"
              ledger.append_event(_ev(), base_dir=fake_real, clock=_clock())
              with real_scoring._materialize_snapshot(fake_real) as copy_dir:
                  self.assertNotEqual(Path(copy_dir).resolve(), fake_real.resolve())
                  copy_verify = ledger.verify(copy_dir)
                  real_verify = ledger.verify(fake_real)
                  self.assertEqual(copy_verify.head, real_verify.head)
                  self.assertEqual(copy_verify.count, real_verify.count)
  ```
- [ ] 7.3 Run — expect FAIL (`_materialize_snapshot` doesn't exist).
- [ ] 7.4 Implement `_materialize_snapshot` as a context manager in
  `h7_real_scoring.py`:
  ```python
  @contextlib.contextmanager
  def _materialize_snapshot(source_base: Path):
      """Copy events.jsonl + HEAD byte-for-byte into a fresh TemporaryDirectory
      and verify the copy reproduces the source's exact head/count before
      yielding it. h7_forward_scoring.py never sees the real path -- it only
      ever receives this synthetic-shaped temp directory, so its frozen
      _synthetic_base check passes unmodified and its computation runs
      completely unchanged (SPEC §2/§7)."""
      source = Path(source_base)
      source_verify = ledger.verify(source)
      with tempfile.TemporaryDirectory() as tmp:
          copy_dir = Path(tmp) / "forward-snapshot"
          copy_dir.mkdir()
          if source_verify.count:
              shutil.copy2(source / "events.jsonl", copy_dir / "events.jsonl")
              shutil.copy2(source / "HEAD", copy_dir / "HEAD")
          copy_verify = ledger.verify(copy_dir)
          if (copy_verify.head, copy_verify.count) != (
              source_verify.head, source_verify.count
          ):
              raise ScoringSnapshotError(
                  "materialized snapshot does not reproduce the source ledger"
              )
          yield copy_dir
  ```
- [ ] 7.5 Write the failing test for `RealScoringSession` and the finalize
  refusal chain (mirror `register_window_real`'s numbered-refusal style,
  `h7_window_registration.py:303-441`), covering each SPEC §8 finalize
  precondition:
  ```python
  class FinalizeRefusalChainTests(unittest.TestCase):
      def test_refuses_before_final_decision_session_completes(self): ...
      def test_refuses_with_unresolved_intent_inside_window(self): ...
      def test_refuses_with_unclosed_included_opening_fill(self): ...
      def test_settlement_close_counts_as_the_closing_fill(self): ...
      def test_refuses_on_scorer_identity_mismatch(self): ...  # module name,
          # min_losses_for_verdict, bootstrap_samples vs seq-0's frozen values
      def test_refuses_on_config_or_cost_model_hash_mismatch(self): ...
      def test_does_not_check_code_source_hash_against_seq_0(self):
          # SPEC §8 item 4: "Code/source identity is intentionally NOT checked
          # against seq 0 ... Receipts are validated against the live source
          # hash only".
          ...
      def test_refuses_if_a_window_score_already_exists(self): ...
      def test_refuses_without_a_fresh_adversarial_review_and_owner_pass(self):
          # PROVISIONAL input shape -- see Ambiguity A4.
          ...
      def test_second_finalize_call_is_an_idempotent_no_op(self): ...
      def test_conflicting_finalize_under_same_id_refuses_never_overwrites(self): ...
      def test_orphan_artifact_without_event_recovers_on_retry(self):
          # SPEC §8: "An artifact without the deterministic event is an
          # orphan and is not authoritative; a retry may append the event
          # only after proving the artifact bytes and input head still
          # match."
          ...
  ```
- [ ] 7.6 Run — expect FAIL.
- [ ] 7.7 Implement `RealScoringSession` (frozen dataclass, lives in
  `h7_real_scoring.py` per this plan's reading of SPEC §8 — see Ambiguity A3
  for why it is *not* added to `h7_forward_scoring.py`) and `finalize(...)`,
  following the numbered order in SPEC §8 exactly:
  ```python
  @dataclass(frozen=True)
  class RealScoringSession:
      base_dir: Path
      scope_id: str
      final_decision_session: str
      window_start: str
      window_end: str


  class ScoringActivationRefused(RuntimeError):
      """Mirrors h7_window_registration.ActivationRefused's style: every
      refusal names the failed precondition; nothing was written."""


  def finalize(
      *, base_dir, owner: str, review_evidence_path: Path, now=None, clock=None,
  ) -> ledger.AppendResult:
      """Refuses until (SPEC §8, numbered 1-6):
      1. the registered final decision session has completed;
      2. every intent decided inside the window is terminal;
      3. every included opening fill has exactly one valid closing fill (a
         §4a settlement close counts as the closing fill);
      4. ledger/registration identities, config_hash, cost_model_hash, and
         scorer identity (module name, MIN_LOSSES_FOR_VERDICT, BOOTSTRAP_SAMPLES
         -- each recomputed and equal to seq 0's frozen values) verify;
         code/source identity is NOT checked against seq 0 (receipts validate
         against the live source hash only, as the entry path does);
      5. no prior window_score exists; and
      6. a fresh independent adversarial review and owner PASS are recorded.
      """
  ```
  Build the artifact via `research.receipts.make_receipt("window_score", ...)`
  / `write_immutable_receipt` at
  `reports/h7_forward_scoring/<scope-id>/<final-decision-session>.json`, with
  every field SPEC §8 lists verbatim (scope id/hash, registration event id/hash,
  window start/end from seq 0, `input_ledger_head` captured before scoring,
  scorer module/config hash/cost-model hash/min-loss gate/bootstrap count/
  forward contract count checked against seq 0, included/excluded cohort
  identity, finalization time, explicit owner acknowledgement, the frozen
  `SURVIVED`-is-not-approval disclaimer, the assignment/pin-risk disclosure,
  and the small-sample bootstrap under-coverage disclosure — copy the exact
  wording SPEC §8 gives for these three disclosures, do not paraphrase). Note
  the SPEC's explicit correction: *"The scorer's returned `frozen` block does
  not include the cost-model hash; the artifact builder computes
  `cost_model_hash()` directly"* — call `research.hashing.cost_model_hash()`
  yourself; do not expect it inside `score_forward_window`'s return value.
  Finalization order is **artifact first, ledger event second** (SPEC §8);
  implement it in that order, and make a retry re-derive and byte-compare the
  existing artifact before appending the event (recovering an orphan) rather
  than re-scoring.
- [ ] 7.8 Wire `h7_real_scoring.main()`'s `finalize` subcommand (stubbed in
  Task 6) to call this real `finalize(...)`, requiring `--owner` and a
  `--review-evidence` path argument.
- [ ] 7.9 Run all new tests to green.
- [ ] 7.10 `uv run python -m unittest discover -s tests` — full suite green.
- [ ] 7.11 `uv run ruff check .` && `uv run pyright`.
- [ ] 7.12 Commit:
  ```
  feat(h7): durable window_score event and artifact per real-exit-scoring SPEC §8
  ```

---

## Task 8 — SPEC §9: test-suite completion checklist

Tasks 1–7 each already write focused failing-tests-first for their own delta.
This task is the closing sweep: confirm every SPEC §9 bullet has a
corresponding green test **somewhere** in the suite, and fill any gap with a
new test in the most appropriate existing file from Tasks 1–7 (do not create a
new module for this task unless a gap doesn't fit any existing file).

### Files

- **Modify** whichever of `tests/test_h7_exit_session.py`,
  `tests/test_h7_paper_lifecycle.py`, `tests/test_h7_forward_scoring.py`,
  `tests/test_h7_real_scoring.py` is the natural home for each gap found below

### Steps

- [ ] 8.1 Walk SPEC §9's bullet list one by one and mark which task/test
  covers it; write the missing ones as new failing tests, then implement only
  if a genuine behavior gap (not just a missing test) is found:
  - [ ] forged/plain real paths and cross-capability objects refused — Task 1
  - [ ] corrupt ledger, absent registration, wrong cohort, wrong date, stale
    hash contract, unlinked receipts, changed cache bytes, future EOD refused
    — Task 2
  - [ ] GO, NO_GO, missing quote, earnings-unknown, pre-earnings,
    scheduled-DTE, stop, profit-target, and credit-stop exit paths on the
    real capability — Tasks 4-5 (extend `TestExitLifecycle`-style fixtures with
    a `RealExitSession` variant of each existing synthetic exit-reason test)
  - [ ] expiration settlement (§4a): both branches + scoring reachable — Task 3
  - [ ] post-window authority: monitoring/fill/retry/settlement accepted for
    in-window positions, refused for new entries — Task 5 (add the negative
    "new entry intent" control explicitly if 5.1's test list didn't already
    cover it)
  - [ ] NO_GO evidence + earnings_unknown source-health `healthy: false` +
    unhealthy/banned name still exit-manageable — Task 4
  - [ ] same-session observation of a newly opened fill — Task 5
  - [ ] decision/evaluation offset mapping and T+1 derivation pinned — Task 5
  - [ ] every monitoring/fill attempt leaves required evidence or gap — Task 6
    (`monitor`/`fill` CLI per-position reporting tests)
  - [ ] duplicate/retry/concurrent calls idempotent or conflict-safe — Tasks
    2, 4, 7 (append_event's existing idempotency contract already covers the
    ledger layer; add one test per new publisher confirming it, e.g.
    `record_exit_evidence` called twice with identical receipts is a no-op)
  - [ ] scoring refusals (before completion, unresolved intent/open position,
    wrong scorer identity, changed config/cost, duplicate close, existing
    different result) — Task 7
  - [ ] orphan-score-artifact recovery and score-event idempotency — Task 7
  - [ ] no CLI can place an order/fetch data/rewrite a receipt/mutate any
    store outside the forward ledger and scoring artifact path — Task 6.7
  - [ ] all current synthetic lifecycle/scoring tests remain green unchanged —
    re-run full suite after every task (already a checklist item in each task)
- [ ] 8.2 Run `uv run python -m unittest discover -s tests` — full suite
  green, including every gap-fill test added in 8.1.
- [ ] 8.3 Run `uv run python -m options_researcher.h7_event_ledger verify` over
  a scratch copy (never the real store) to sanity-check nothing in this plan
  touched forward-ledger verification semantics.
- [ ] 8.4 Take immutable-artifact snapshots: run `h7_real_scoring.py preview`
  and `finalize` (against a synthetic fixture store, never
  `ledger/h7_forward`) and diff their output against a checked-in golden file
  if the project's convention favors one (check `tests/` for an existing
  golden-file pattern before inventing one).
  - [ ] 8.4a Check `git diff --stat -- tools/daily_ritual.sh` is empty — this
    plan must not have touched ritual wiring (GATE banner requirement).
  - [ ] 8.4b Run `bash -n tools/daily_ritual.sh` anyway (a ritual syntax check
    is one of SPEC §9's acceptance items even though this plan changes
    nothing in that file — confirming it is still syntactically valid untouched
    is the cheap proof of "not modified").
- [ ] 8.5 `uv run ruff check .` && `uv run pyright` one final time across the
  whole tree.
- [ ] 8.6 Commit:
  ```
  test(h7): complete real-exit/scoring adversarial test suite per real-exit-scoring SPEC §9
  ```
- [ ] 8.7 **Stop here.** Do not run any of these CLIs against the real
  `ledger/h7_forward` store. Do not wire anything into
  `tools/daily_ritual.sh`. Report task completion and hand off for the SPEC §9
  fresh-context independent adversarial review — that review, its remediation,
  and a separate owner-typed PASS are the only things standing between this
  build and activation, and none of them are part of this plan.

---

## Rules (apply to every task above)

- **Never hand-edit `ledger/h7_forward/events.jsonl` or `HEAD`**, in tests or
  otherwise. Every write goes through `h7_event_ledger.append_event` (typed
  API only). A hand edit breaks the hash chain and `verify` refuses.
- **New `EVENT_TYPES` entries exactly as the SPEC names them.** The only new
  entry this plan introduces is `"window_score"` (Task 7, SPEC §8). Do not add
  any other event type; do not rename an existing one.
- **The entry evidence publisher must never be reused for exits** (SPEC §2/§5):
  `h7_session.record_session_evidence` and `h7_watch.validate_data_gate_receipt`
  are never called directly from `h7_exit_session.py`'s evidence-publishing
  path (only their *pattern* is mirrored, with the GO-only/healthy-only
  hardcoding removed). If a future edit makes `h7_exit_session.py` import and
  call `h7_session.record_session_evidence` for anything other than reading
  its helper constants, stop — that is exactly the reuse SPEC §5 prohibits.
- **`h7_forward_scoring.py` gets zero behavioral changes.** No CLI, no
  real-store branch, no resolution seam, no new parameter. Task 7's wrapper
  only ever hands it a materialized temporary copy that looks exactly like an
  ordinary synthetic store to its existing `_synthetic_base` check.
- **No network in tests.** Every fixture uses `tempfile.TemporaryDirectory()`
  and synthetic/patched receipts, exactly like
  `tests/test_h7_event_ledger.py`'s `LedgerBase` and
  `tests/test_h7_session_real_path.py`'s `RealSessionCase`. Never call
  `data.thetadata_adapter`, `data.recent_topup`, or anything that reaches the
  network from a test.
- **Full offline suite green before every commit** in every task
  (`uv run python -m unittest discover -s tests`), not just the task's own new
  test file.
- **No task in this plan wires anything into `tools/daily_ritual.sh`** or runs
  a built CLI against the real `ledger/h7_forward` store. If a test needs to
  prove a refusal against "the real store," it does so via
  `lifecycle.REAL_FORWARD_STORE`'s existing boundary checks (as
  `tests/test_h7_paper_lifecycle.py:189-204`'s `TestStoreGuard` already does),
  never by writing to it.

---

## Ambiguities requiring Claude/owner resolution

**A1 — Where does §4 item 2's post-window per-position authorization live?**
SPEC §4 describes the window/lineage check as something `open_real_exit_session`
must enforce ("For every monitoring or fill session it must... require the
operational decision session to be inside the registered window, OR...").
But one `RealExitSession` is naturally opened once per calendar session and
then used across *many* open positions (the `monitor` CLI command "scans every
open real-paper position"), and whether a given session is authorized for
*this specific* position depends on that position's own entry date and retry
history — information the factory doesn't have until `observe_exit`/
`process_exit_fill` load the position. This plan splits the check: the factory
(Task 2) validates the session-level receipt chain and stores the window
bounds; the per-position lineage/window test (Task 5's
`_require_exit_window_authority`) runs inside `observe_exit`/
`process_exit_fill` themselves. The SPEC does not say this split is correct —
an alternative reading is that `open_real_exit_session` should take an
optional `position_id`/`symbol` parameter (mirroring entry's optional
`symbol=` narrowing in `open_real_session`) and refuse eagerly at open time for
a *specific* position, with the `monitor` CLI opening one narrowed session per
position instead of one per calendar session. **Confirm which shape is
intended before Task 2/Task 5 land**, since it affects both modules'
signatures and the CLI's per-position vs. per-session error-reporting
granularity (SPEC §7: "partial success must be reported per position").

**A2 — How do §4a settlement legs satisfy the frozen scorer's quote-based
reconstruction?** Confirmed by reading `h7_forward_scoring.py:142-169` directly:
`_fill_price` recomputes `expected = adverse_buy(ask)` (`ceil(ask*(1+haircut)*100)/100`,
`data/pandas_feed.py:53-59`) or `adverse_sell(bid)` (`floor(bid*(1-haircut)*100)/100`,
`data/pandas_feed.py:62-64`) from the stored leg's `raw_bid`/`raw_ask`, and
additionally requires `quote_valid(bid, ask)` and
`passes_liquidity(open_interest, bid, ask)` (`data/thetadata_adapter.py:456-464`,
which demands `open_interest >= MIN_OPEN_INTEREST` = 100) to hold. SPEC §4a's
intrinsic-settlement legs have **no real quote or open interest** — that is the
entire premise of needing a settlement rule. SPEC §2 requires
`h7_forward_scoring.py` stay byte-identical and §7 explicitly forbids adding any
seam to it, yet §4a requires settled positions to become scoreable by that same
unmodified scorer. Two ways to reconcile, neither endorsed by the SPEC text:
  - **(a)** Reverse-solve a synthetic `raw_bid`/`raw_ask`/`open_interest` per
    settled leg that round-trips through `adverse_buy`/`adverse_sell` to the
    intended intrinsic value and passes `passes_liquidity`. Mechanically clean,
    requires no changes to the frozen module, but embeds a fabricated "quote"
    in the ledger event that isn't labeled as such to `h7_forward_scoring.py`
    (only to a human reading `payload["settlement"]`) — in tension with this
    repo's "never fabricate data" guardrail, even though the *value* it encodes
    is the honestly pre-registered intrinsic settlement.
  - **(b)** Add a narrow, explicitly-flagged exception inside
    `h7_forward_scoring.py`'s leg reconstruction for `settlement: true` legs
    (skip the quote re-derivation, trust the recorded value directly) — this is
    a literal, if small and well-motivated, change to a module both §2 and §7
    declare frozen and explicitly closed to new seams.
  Task 3 as written proceeds provisionally under (a) (it is the only option
  that requires zero changes outside the new settlement function), but flags
  every place this choice touches the payload shape and event-id scheme as
  provisional. **This must be explicitly re-examined during the SPEC §9
  fresh-context adversarial review before it is trusted**, and ideally settled
  with the owner before Task 3 is implemented rather than after.

**A3 — What does "accepted by the scorer" mean for `RealScoringSession` (§8),
given §7's explicit prohibition on modifying `h7_forward_scoring.py`?** SPEC §8
says: *"The scoring capability is a distinct typed door (for example,
`RealScoringSession`) accepted by the scorer only after these checks."* Read
literally, "the scorer" is `h7_forward_scoring.score_forward_window`, which
would mean that function should accept and type-check a `RealScoringSession`
argument — directly contradicting §7's *"Do not add a CLI, a real-store
branch, or a resolution seam to `h7_forward_scoring.py` itself."* This plan
resolves the tension by reading "the scorer" loosely as "the real-scoring
finalize path" and placing `RealScoringSession` inside the new
`h7_real_scoring.py` wrapper module instead, which never modifies
`h7_forward_scoring.py` and instead hands it a materialized temporary ledger
copy (Task 7's `_materialize_snapshot`) that is indistinguishable, to that
module, from an ordinary synthetic fixture. **Confirm this reading is what was
intended** — if the SPEC's authors meant literal support inside
`h7_forward_scoring.py`, §7's prohibition needs to be reconciled or amended
before Task 7 is built, not silently overridden by this plan's interpretation.

**A4 — What is the exact artifact/format for "a fresh independent adversarial
review and owner PASS" as a *finalize precondition* (§8 item 6)?** The SPEC
requires `finalize` to refuse without this evidence but does not specify what
file, schema, or flag records it — unlike `register_window_real`
(`h7_window_registration.py:303-441`), which has a fully specified evidence
dict (`owner`/`evidence` dicts with named required fields) to check against.
Task 7 proposes `finalize(..., review_evidence_path: Path)` loading a small
JSON receipt the reviewer/owner produces out-of-band, but the exact schema
(reviewer identity, reviewed-artifact hash, verdict string, owner
acknowledgement field name) is invented for this plan, not specified by the
SPEC. **The owner should confirm or specify this schema before Task 7's
`finalize` is implemented for real**, since it is the literal gate between
"code built" and "code the SPEC would call reviewed."

**A5 — Exact file/module home for `RealExitSession` and its factory.** The
SPEC states the type and factory must exist ("Add a frozen `RealExitSession`
capability... Only a reviewed `open_real_exit_session(...)` factory may create
it") but does not name a module. This plan places `RealExitSession` in
`h7_paper_lifecycle.py` (co-located with `RealStoreSession`, since
`observe_exit`/`process_exit_fill` must `isinstance`-check it) and
`open_real_exit_session` in a new `h7_exit_session.py` (mirroring
`h7_session.py`'s split of type-in-lifecycle-module,
factory-in-session-module). This is a reasonable, symmetric choice but is this
plan's judgment call, not a SPEC requirement — flag it if a fresh-context
reviewer would expect a different layout (e.g. everything exit-related in one
new module, including the dataclass).

**A6 — Does `settle_expiration_close` need its own CLI subcommand, or is it
only ever invoked implicitly by `h7_exit_session fill`/`monitor` when they
detect an exhausted retry runway at expiration?** SPEC §7 lists exactly three
`h7_exit_session` subcommands (`status`, `monitor`, `fill`) and does not
mention settlement explicitly. This plan (Task 3) builds
`settle_expiration_close` as a library function only, tested directly, and
does **not** wire it into the Task-6 CLI's `fill`/`monitor` command bodies
(that wiring — detecting "no valid closing fill and now at/after expiration"
and routing to settlement instead of an ordinary `process_exit_fill` call — is
left undone by this plan). **Confirm whether CLI wiring for §4a settlement is
in scope for this plan or a follow-on task**; as written, a fresh-context
reviewer will find `settle_expiration_close` reachable only via direct Python
call, not via any CLI, which may itself be a gap worth flagging in §9 review.

---

## Completion checklist — SPEC §3–§9 requirement → implementing task

| SPEC requirement | Task |
|---|---|
| §3: `RealExitSession` frozen type, all named fields | Task 1 |
| §3: only `open_real_exit_session` factory constructs it | Task 2 |
| §3: `observe_exit`/`process_exit_fill` accept it via typed seam | Task 1 |
| §3: forged/plain-path/`RealStoreSession` cross-capability refusal | Task 1, 2 |
| §3: exit authority cannot propose/approve entry, place order, score | Task 6 (CLI has no such surface), Task 7 (scoring is a separate door) |
| §4 item 1: verify hash chain, load cohort/window from seq 0 | Task 2 |
| §4 item 2: in-window OR post-window-causally-descended authorization | Task 2 (session-level) + Task 5 (per-position) — see Ambiguity A1 |
| §4 item 3: load/integrity-check full-scope data-gate + linked source-health receipts | Task 2, Task 4 |
| §4 item 4: receipt-vs-LIVE-tree source-hash agreement (never vs seq-0) | Task 2 |
| §4 item 5: re-hash every named input | Task 2 |
| §4 item 6: load only receipt-bound chain/close, re-hash after load | Task 2 |
| §4 item 7: refuse stale/missing/changed/future/fallback/cross-session data | Task 2 |
| §4: exit factory can represent a valid NO_GO receipt | Task 2, Task 4 |
| §4: no `ENTRY-OK` watcher row required; no second mutable cache manifest | Task 2 |
| §4a: intrinsic settlement at expiration (calls/puts, long/short) | Task 3 |
| §4a: no-close fallback (OTM-beyond-doubt zero / full-width loss) | Task 3 |
| §4a: settlement makes scoring reachable via the unmodified scorer | Task 3 (+ Ambiguity A2) |
| §4a: assignment/pin-risk disclosure carried on settled positions | Task 7 (artifact-level disclosure) |
| §5: exit publishes verified `data_gate` evidence before every transition | Task 4 |
| §5: earnings-dependent exits publish `source_health` with actual gate/healthy | Task 4 |
| §5: non-earnings exits never fabricate source-health cause | Task 4 |
| §5: GO/priceable/no-trigger leaves evidence with no intent | Task 4 (existing `observe_exit` behavior + evidence call) |
| §5: NO_GO/unpriceable appends `data_gap`; fired trigger appends `exit_intent`; fill appends `paper_fill`/`data_gap` | already frozen in `h7_paper_lifecycle.py` — Task 4 only adds evidence publication around unchanged transitions |
| §5: distinct exit-evidence publisher/loader; entry publisher never reused | Task 4 |
| §6: `evaluation_session`/`decision_session`/`planned_fill_session` semantics | Task 5 |
| §6: synthetic callers keep both dates identical | Task 5 |
| §6: reject inconsistent receipt date, exit-before-entry, out-of-lineage decision, unfinished EOD | Task 5 |
| §6: same-session observation of a newly opened fill (acceptance test) | Task 5 |
| §7: `h7_exit_session status/monitor/fill` CLI, no network, no order surface | Task 6 |
| §7: `status` writes nothing; `monitor`/`fill` require explicit receipts, report per-position appended/replayed, exit 2 on refusal | Task 6 |
| §7: `h7_real_scoring preview/finalize` in a separate wrapper module | Task 6 (preview + finalize stub), Task 7 (finalize for real) |
| §7: no seam/CLI/real-store branch added to `h7_forward_scoring.py` | Task 7 (`_materialize_snapshot`) — see Ambiguity A3 |
| §7: neither scoring command accepts caller-supplied window bounds | Task 6 |
| §7: ritual wiring (Step 2c ordering) | **out of scope for this plan** — GATE banner |
| §8: `window_score` event type + immutable artifact at the receipt path | Task 7 |
| §8: artifact fields (scope/registration ids, window bounds, `input_ledger_head`, scorer/config/cost identities, cohort, finalization time/owner ack, disclaimers) | Task 7 |
| §8: `cost_model_hash()` computed directly by the artifact builder | Task 7 |
| §8: deterministic event id, causes include registration + every included fill | Task 7 |
| §8: artifact-first-then-event finalization order; orphan recovery; conflict-never-overwrite | Task 7 |
| §8 items 1-6 finalize refusal chain | Task 7 |
| §8: `RealScoringSession` typed door | Task 7 — see Ambiguity A3 |
| §9: full test list (forged paths, corrupt state, all exit reasons, settlement, post-window authority, NO_GO evidence, same-session observation, mapping, evidence-or-gap, idempotency, scoring refusals, orphan recovery, no-order/no-network CLI, unchanged synthetic suite) | Task 8 (sweep + gap-fill; individual items also covered incrementally in Tasks 1-7) |
| §9: fresh-context independent adversarial review + owner PASS | **explicitly not part of this plan** — GATE banner |

---

## Orchestrator review + rulings (Claude, 2026-07-22)

Plan reviewed against the ratified SPEC (sha256 ca639c1e…) and the live
scorer code. Rulings on the drafter's ambiguities:

- **A1 (authorization placement): RULED.** Post-window per-position
  authorization is checked at session open in the `open_real_exit_session`
  factory, mirroring `open_real_session`; mechanical calls require a valid
  session object. Flagged for the §9 reviewer to challenge.
- **A2 (settlement vs frozen scorer): CONFIRMED REAL SPEC DEFECT — BLOCKER
  for Task 7.** Verified directly: `h7_forward_scoring._fill_price`
  (`:142-169`) requires every closing leg to carry raw quotes passing
  `quote_valid` + `passes_liquidity` and a canonical adverse fill price; a
  §4a settlement close has no market quote by definition. Resolution
  requires an owner-ratified SPEC amendment (v1.1) — drafted and presented
  to the owner 2026-07-22; NOT yet ratified. **Tasks 1–6 may proceed now;
  Tasks 7–8 are HELD until the amendment is ratified and folded into the
  SPEC.**
- **A3 ("accepted by the scorer"): RULED.** Means accepted by the new
  `h7_real_scoring` wrapper module; the §7 ban on touching
  `h7_forward_scoring.py` stands absolutely. Final mechanics contingent on
  the A2 amendment.
- **A4 (finalize precondition schema): RULED (provisional).** `finalize`
  refuses unless `ledger/facts.log` contains an independent-review PASS
  fact and a separate owner PASS fact, each citing the exact commit SHA
  that HEAD resolves to at finalize time; mismatch or absence → typed
  refusal. The §9 reviewer may tighten this.
- **A5 (module home): APPROVED** as proposed (symmetric split with the
  entry-side layout).
- **A6 (settlement CLI): RULED.** `settle_expiration_close` is
  library-only this arc; §7 defines exactly two CLIs and this plan adds no
  third.

Execution status: recorder-brief Task 2 (h10_watch) is in flight with Codex
and unaffected. This plan's Tasks 1–6 are cleared for Codex now; 7–8 held
per A2.
