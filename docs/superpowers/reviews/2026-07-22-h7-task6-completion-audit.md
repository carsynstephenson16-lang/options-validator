# H7 Task 6 (real exit + scoring) — completion audit

**Date:** 2026-07-22
**Branch:** `docs/replan-2026-07-22`
**Commits audited:** `39c7f6b`, `ab7cdb0`, `407a90a`, `ab883f4` (~4,100 lines)
**Auditor:** Claude orchestrator + three Sonnet subagents (exit-path SPEC
conformance, scoring-path SPEC conformance, safety/inactivity)
**Normative sources:** `docs/superpowers/specs/2026-07-22-h7-real-exit-scoring-SPEC.md`
(ratified `H7_C1_EXIT_AND_SCORING_SPEC_RATIFIED`, amended
`H7_EXIT_SCORING_SPEC_AMENDMENT_V1_1`), and
`docs/superpowers/specs/2026-07-22-project-replan-design.md` R1.

> **This is NOT the SPEC §9 review.** §9 requires a *fresh-context independent*
> adversarial review, remediation of every blocker, and a separate owner-typed
> PASS. This document is the completion/integrity audit that runs *before* that
> review, triggered because the Codex session ended mid-audit. The findings
> below are inputs to §9, not a substitute for it. **No PASS is claimed.**

**Post-audit status:** Codex remediated F1-F6 and F9 and answered F7/F10. The
fresh-context review and its one remaining owner-governance blocker are recorded
in [2026-07-22-h7-task6-independent-adversarial-review.md](2026-07-22-h7-task6-independent-adversarial-review.md).

## Verdict

The build is mechanically complete and the safety-critical invariants held.
**Task 6 is NOT signed off** — F1 below is a genuine spec violation, and F2–F4
are test-coverage gaps against the SPEC's own §9 minimum list.

## Verified green (measured, not asserted)

| Check | Result |
|---|---|
| Full offline suite | **1,694 tests, OK, exit 0** (matches Codex's claim exactly) |
| `ruff check .` | All checks passed |
| `pyright` | 0 errors, 0 warnings |
| Worktree | Clean; all work committed |
| Live forward ledger | **Untouched** — 1 event, seq-0 `window_registration`, `event_id wr:2026-07-20:70` |
| `h7_event_ledger verify` | `VALID records=1 head=a1ea228c2abb`, exit 0 |
| `tools/daily_ritual.sh` | **Unchanged** — no Task 7 leakage |
| `ledger/` files | Unchanged; no new facts appended (owner-typed only) |
| `h7_forward_scoring.py` | **Byte-identical** — `git diff` empty; amendment v1.1's central requirement holds |

Safety audit returned SAFE on all six checks. Strongest structural guarantees:
the new modules **do not exist in the ops worktree** (`/Users/carsynstephenson/options-validator-ops`,
on `main` @ `3e79059`) that runs the unattended LaunchAgent; the real ledger has
zero open positions, so the exit CLI is a no-op even if run directly; `finalize`
requires two PASS-tagged facts that are **not present** in `ledger/facts.log`;
and no network, broker, or order surface exists in any new module.

## Findings

### F1 — `preview` discloses an interim verdict (MATERIAL — research integrity)

`options_researcher/h7_real_scoring.py:1023-1026` prints:

```python
print(
    f"H7 SCORE NOT FINAL -- trades={result['n_trades']} "
    f"verdict={result['overall']['verdict']}"
)
```

`preview_real_score` (`:775-790`) does **not** call `_require_review_passes`
(only `finalize` does, `:889`). So once the window's final decision session has
passed, `preview` computes the full result and prints the actual verdict
(`SURVIVED`/`REJECTED`/`INCONCLUSIVE`) before the independent review and owner
PASS gates.

Both normative documents forbid this — this is **not** a document conflict:

- SPEC §10 (frozen boundary): "This arc does not add ... an extra look at
  results, **an interim verdict**, or a second score."
- Replan R1 acceptance: "**no interim-verdict output anywhere**."

SPEC §7 authorizes a `preview` subcommand and requires it to "still say
`NOT FINAL`" — but authorizing the command is not authorizing disclosure of the
verdict value. §10 resolves the question against the current implementation.

No test guards this. `tests/test_h7_real_scoring.py:336`
(`test_preview_is_read_only_and_explicitly_not_final`) runs `main(["preview"])`
with `_utc_now` patched past the window end — exercising exactly the
verdict-printing path — but asserts only that `"NOT FINAL"` appears and the
filesystem is unchanged. It never asserts the verdict is withheld.

**Mitigation (why this is not urgent):** the registered
`final_decision_session` is **2026-10-26**. `preview_real_score` raises
`RealScoringIncomplete` before that (`:781-784`), and the CLI prints the
refusal with no verdict. The violation is **latent, not live** — it cannot
disclose anything for ~3 months.

**Proposed remedy (for Codex, after owner direction):** `preview` reports
readiness only — completeness/gate status, and at most trade count — with no
`verdict`, expectancy, or CI. Add a test asserting the verdict string is
absent from preview output. Owner should confirm whether trade count itself
is acceptable to disclose pre-PASS.

### F2 — Exit-path refusal chain largely untested (MATERIAL — test coverage)

The exit path implements ~21 distinct refusal branches, all typed
(`ExitSessionRefused` / `ActivationBoundaryError`). Roughly **5 of 21** have a
dedicated negative test. SPEC §9's own minimum list names: "corrupt ledger,
absent registration, wrong cohort, wrong date, stale hash contract, unlinked
receipts, changed cache bytes, and future EOD refused."

- Tested: unlinked receipts, changed cache bytes, unfinished EOD, forged token,
  partial-batch exit code 2.
- **Untested (present in code, no failing test):** corrupt ledger
  (`h7_exit_session.py:329-334`), absent registration (`:335-336`), wrong cohort
  /stale scope (`:346-353`), wrong date — evaluation > decision (`:322-323`),
  stale hash contract (`:235-240`, `:255-260`), gate shape checks (`:202-234`),
  changed source-health inputs (`:261-265`), post-window with zero authorized
  positions (`:302-305`).

The mechanisms are correctly built; the gap is proof they fire.

### F3 — Cross-capability guard has zero test evidence in one direction (MATERIAL)

SPEC §3 explicitly requires that passing a `RealStoreSession` (entry authority)
into an exit path fail closed. The guard exists
(`h7_paper_lifecycle.py:147-150`, raising "authorizes entry transitions only"),
but a repo-wide grep for that message returns **only the raise statement
itself** — no test anywhere calls `observe_exit`/`process_exit_fill` with a
`RealStoreSession`. The reverse direction (exit session into
`record_entry_intent`) *is* tested (`tests/test_h7_exit_session.py:768-794`).
`_assert_capability` (`h7_exit_session.py:393-400`) is likewise never hit by a
test.

### F4 — `_revalidate` never proven to catch a change (MATERIAL)

`_revalidate` (`h7_exit_session.py:403-426`) re-earns authority on every
mutating call and is the mechanism embodying SPEC §4's per-session
re-verification. Every existing test's second call sees an unchanged world, so
only the trivial "nothing changed" branch (`:419-425`) is exercised. No test
mutates a receipt hash, re-registers a different scope, or appends a conflicting
event between `open()` and a subsequent call.

### F5 — Settlement tested for one structure only (MODERATE)

`_expiration_settlement` handles `long_call`, `call_debit_spread`, and
`bull_put_spread`, including a width-based charge on the short leg for
`bull_put_spread`. Tests exercise **only `long_call`** for both the intrinsic
path and the conservative fallback. The credit-spread width-charge logic is
completely unexercised. The intrinsic math itself matches §4a verbatim, uses the
OCC $0.01 exercise-by-exception threshold, and fabricates no quotes (settled
legs carry `intrinsic_per_share`/`settlement_cash_per_share`, never bid/ask).

### F6 — Idempotent replay untested through exit call sites (MODERATE)

SPEC §9 requires "duplicate/retry/concurrent calls are idempotent or conflict
safely." Ledger-level idempotency is tested generically in
`tests/test_h7_event_ledger.py`, but no test calls `record_exit_evidence`,
`observe_exit`, or `process_exit_fill` twice with identical inputs.

### F7 — Commit `ab883f4`'s message overstates its effect (MINOR — accuracy)

The commit titled "fix(h7): preserve one-door invariant in scoring seam" changes
exactly one line (`h7_real_scoring.py:418`): `Path(raw) / "ledger"` →
`f"{raw}/ledger"`, inside a `tempfile.TemporaryDirectory()` block. Verified: the
guard `_synthetic_base` (`h7_forward_scoring.py:44-54`) calls `Path(base_dir)`
on whatever it receives, and a repo-wide search finds **no `isinstance`/`type`
dispatch on `Path`** anywhere. The two forms are functionally identical, and
`base` is always derived from a fresh OS tempdir — never from caller input.

No hole was found open before or after. This reads as precautionary hardening,
not a fix for a demonstrated defect. In a repo where ledger facts cite commit
SHAs, a commit message claiming to "preserve an invariant" without a
demonstrable behavioral change is drift worth correcting. **§9 reviewer should
ask what the pre-fix failure mode actually was.**

### F8 — Three hand-written copies of the real-store guard (MINOR — maintainability)

`_synthetic_base`-style guard logic is independently reimplemented at
`h7_paper_lifecycle.py:146`, `h7_forward_scoring.py:44`, and
`h7_forward_book.py:108`. No single source of truth; a future edit to one copy
can drift from the others silently.

### F9 — `write_immutable_receipt` check-then-replace race (MINOR — latent, pre-existing)

`research/receipts.py:100-103,121` checks `path.exists()` then later
`os.replace(tmp, path)` with no lock held across the interval;
`h7_real_scoring.py:947` calls it without a surrounding lock (the ledger's
`fcntl` lock wraps only the later `append_event`). Two concurrent finalizes from
different ledger heads could theoretically both pass the check and clobber.
Pre-existing shared primitive, not introduced by this build; practical exposure
low (manual, single owner-run CLI).

### F10 — Two seams flagged for §9 reviewer attention (not defects)

1. `_frozen_market_result` (`h7_real_scoring.py:439-446`) injects an overridden
   `planned_fill_session` into a **copy** of the exit-intent event before the
   frozen scorer sees it, reconciling the real path's two-date model with the
   frozen scorer's single-date calendar. Reasoned benign (P&L comes from
   `evaluation_session` directly; timing independently re-verified by
   `_validate_market_lineage`), but a reviewer should re-derive that this cannot
   affect trade inclusion or P&L.
2. The same function calls `ledger.append_event` **directly**, outside the
   one-door session boundary. Safe today because `base` is a fresh tempdir, but
   it sets an architectural precedent worth an explicit ruling.

## Conformance summary

| SPEC area | Verdict |
|---|---|
| §3 distinct RealExitSession authority | CONFORMS (untested in one direction — F3) |
| §4 per-session receipt/hash re-verification | CONFORMS on mechanism (F4 on proof) |
| §4 item 4 live-tree vs seq-0 hash rule | CONFORMS — correctly checks live tree, never seq-0 |
| §4a / §4a.1 settlement | CONFORMS (F5 on coverage); no fabricated quotes |
| §5 exit-evidence publisher | CONFORMS — NO_GO faithfully recorded and tested |
| §6 decision-vs-evaluation split | CONFORMS |
| §7 CLIs | CONFORMS — `status`/`monitor`/`fill`; `status` writes nothing (byte-snapshot test) |
| §8 scores exactly once | CONFORMS — three independent enforcement layers |
| §8 finalize gates | CONFORMS (gate 6 correctly `finalize`-only) |
| Amendment v1.1 identical statistics | CONFORMS — loss gate, bootstrap, CI all route through the same shared functions; nothing re-declared locally |
| Amendment v1.1 three disclosures | CONFORMS |
| Amendment v1.1 frozen scorer byte-identical | CONFORMS — verified empty diff |
| Vocabulary discipline | CONFORMS — no banned results words |
| R1 "no interim-verdict output anywhere" | **DIVERGES — F1** |

## Required before any §9 PASS

1. Owner ruling on F1, then Codex remediation + a test asserting the verdict is
   withheld from `preview`.
2. Negative tests closing F2, F3, F4 (SPEC §9's own minimum list).
3. F5/F6 coverage, or an explicit reviewer waiver recorded with reasoning.
4. Codex answer on F7 (what failure mode did `ab883f4` fix?).
5. Fresh-context independent adversarial review per §9, then owner-typed PASS.

Until all of that lands, real exits and real-store scoring remain **INACTIVE**,
Task 7 (ritual wiring) stays closed, and this branch must not be merged to the
ops worktree's lineage.
