# B2 (Schwab durable receipt path) — adversarial review receipt

**Provenance: RECONSTRUCTED 2026-08-14** from the orchestrating session's
records and memory of the 2026-08-13 late session, because the review
happened in-session and its receipt was never filed as a dated artifact
(gap found by the 2026-08-14 H7 decision dossier audit). Commit history
corroborates every SHA cited. Wording below is a faithful summary, not a
verbatim transcript.

**Target:** Codex's `927dddd` implementing brief 07
(`docs/superpowers/plans/2026-08-13-07-h7-schwab-b2-receipt-path-codex-brief.md`).
**Reviewer:** independent Opus subagent, adversarial charter, 2026-08-13
late session (Fable orchestrating).

## Verdict on the branch as submitted: FAIL

- The B2 proof test had NEVER executed: a `tests.`-prefixed import made the
  test module unloadable under the discovery pattern; the branch suite
  exited 1 despite a "done" claim delivered with an empty commit body.

## Fixes applied in-session (landed via PR #35: `ab7611d`, `4c759ff`)

- Import fixed; the proof test executes and passes.
- Input-path binding red-proven with a forged receipt (test fails against
  the unbound version).
- Wrapper `origin/main` refresh made bounded and prompt-free
  (`GIT_TERMINAL_PROMPT=0`, low-speed limits) — brief 07 WP-A item 4.
- Strict fact dedupe on the capture's ledger append.
- The Codex bot's 5 inline PR #35 findings fixed red-first, including a
  real revision-lookahead causality bug in the FINRA lane; all threads
  replied and resolved.

## Final state (verified on the merge train before PR #35 merged)

ruff clean; pyright 0 errors; suite 2,878 OK with honest exit-code capture;
all PR CI checks green. B2 is CLOSED on `origin/main` as of 58b1fd9.

## Named follow-ups (pre-registration, still open as of 2026-08-14)

- `h7_watch` operating-door mode dispatch (Schwab window cannot open a
  session on its own evidence).
- `causal_cutoff_utc` payload asymmetry between the two data gates.
- Shared-fixture extraction for the Schwab gate tests.
