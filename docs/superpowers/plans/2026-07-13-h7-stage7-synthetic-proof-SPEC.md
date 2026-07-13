# H7 Stage 7 — full synthetic proof: SPEC

**Status: PRE-REGISTRATION CANDIDATE. BUILD-ONLY, SYNTHETIC-ONLY, INACTIVE.
This stage rehearses Stages 1–6 entirely inside disposable fixture directories.
It reads no production market store, writes no real forward event, performs no
network call, registers no forward window, and exposes no operational watcher.
Stage 8 remains the only activation gate.**

## 1. Proof boundary

The proof is one deterministic, test-callable fixture runner plus adversarial
tests. Every ledger and market-data path is created below a caller-supplied
temporary root. The runner rejects the real `ledger/h7_forward` path and any
path resolving inside it. Its fixed fixture dates are examples only: they are
not a start date, duration, decision procedure registration, or permission to
observe a real tick.

No new strategy parameter is proposed. The proof reuses the frozen Stage-1–6
configuration and public APIs. It must not mock away a stage whose behavior it
claims to prove.

## 2. Happy-path dress rehearsal

The runner must exercise, in dependency order:

1. Stage 1 source health over synthetic typed earnings assertions for the
   complete H7 watch universe, proving every symbol healthy at the decision
   session cutoff.
2. Stage 2 whole-universe gate over synthetic Parquet closes and chains for the
   exact evaluation session, proving 12/12 `GO` without a fetch path.
3. Stage 3 append/verify of the source-health, data-gate, board, entry/approval,
   fill, exit, and close events in a disposable hash-chained ledger.
4. Stage 4 owner-approved decision-T entry, exact T+1 fill from canonical
   adverse quotes, mechanical exit intent, and first valid later-session exit
   fill with exact-session underlying benchmarks.
5. Stage 5 board reservation and book replay, including a same-board candidate
   rejected by the frozen monthly sleeve and a closed position that still
   consumes its opening month risk.
6. Stage 6 pure scoring of the exact inclusive decision window, reconstructing
   one closed trade after all costs with per-lane/overall output and the frozen
   `INCONCLUSIVE` small-sample verdict.

The result is a canonical-JSON-safe proof receipt containing fixture identity,
stage results, event count/head, T/T+1 sessions, risk evidence, reconstructed
PnL/benchmark fields, verdicts, and the statement
`BUILD-ONLY; SYNTHETIC-ONLY; INACTIVE`.

## 3. Required refusal proofs

Independent fixture arcs must prove:

- Stage 1 becomes unhealthy when one watched symbol lacks live earnings
  provenance.
- Stage 2 becomes whole-universe `NO_GO` when one exact-session chain is
  absent, and no decision/lifecycle event is produced from that refusal arc.
- Stage 3 verification rejects a byte-mutated copied ledger.
- Stage 4 refuses a same-session entry fill and a successful fill without its
  exact-session adjusted close.
- Stage 5 rejects an over-sleeve candidate and does not lose consumed monthly
  risk after close.
- Stage 6 refuses an incomplete included decision and does not mutate its
  input ledger.
- The default real forward ledger remains `VALID EMPTY` before and after the
  complete proof.

## 4. Determinism and evidence

Two runs with equivalent fixture roots must return canonical-equal receipts
after excluding physical temporary paths. All clocks used for append metadata
are fixed UTC test clocks. The proof receipt is evidence, not a verdict-bearing
forward result; only the dated Stage-7 verification summary is appended to
`ledger/facts.log` after independent review and the complete verification
bundle passes.

Acceptance requires focused proof tests, the complete suite, Ruff, Pyright,
focused pre-commit hooks, independent review, and the real ledger verifier.

## 5. Stage boundary

Stage 7 does not register a window, choose a live start/duration, confirm paid
data availability, add an operational CLI, create a scheduler, append a real
event, or reinterpret `SURVIVED` as approval. Those remain Stage-8 decisions
requiring separate owner authorization and independent review.
