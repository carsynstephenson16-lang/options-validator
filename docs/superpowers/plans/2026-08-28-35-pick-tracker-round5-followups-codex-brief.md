# Codex brief 35 — pick-tracker round-5 follow-ups (NEW-A, NEW-C, N3)

**Date:** 2026-08-28
**Author:** Claude orchestrating session (Fable), deferred-closeout session
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** HANDED OFF TO CODEX (rev 2) — round-1 independent adversarial
review (Opus, 2026-08-28) verdict PASS WITH FIXES (3 blocking + 4
advisory); all applied in this rev; Fable sign-off recorded. Owner
directive to proceed: 2026-08-28 in-session.
**Landing order (binding):** this brief lands BEFORE brief 33 (both touch
`tests/test_daily_ritual_provenance.py`; review finding C3).
**Provenance:** Repo-verified against origin/main @`704a138`. Finding
source: the round-5 independent review that closed PR #93
(`reports/2026-08-27-pr93-round5-independent-review-PASS.md:16,20,30-31`) —
these are its explicitly recorded residual boundaries, none blocking.
**Owner directive:** Carsyn in-session 2026-08-28 — "finish everything
that's deferred".

## The three items (small, self-contained)

1. **NEW-A (one-line test fix).** The ritual structural guard test asserts
   `assertNotIn("exit ", …)` — a bare `exit` (no trailing space) evades it
   (review line 31; verified 41/41 stayed green under that mutation).
   Fix: word-boundary regex (`assertNotRegex` with `r"\bexit\b"`) scoped
   exactly as the current assertion is scoped. Exact location:
   `tests/test_daily_ritual_provenance.py:258` (review-verified: the
   guarded region currently matches `\bexit\b` zero times — `exit_code`
   and `PICK_TRACKER_EVAL_LOG` do not match — so the change is RED only
   under mutation, GREEN on current bytes). Do not touch
   `tools/daily_ritual.sh`.
2. **NEW-C (disclosure + dead code + one test; review line 30).** The
   tracker's machine-date binding means a live-coverage change cancels a
   pick ONE RITUAL RUN LATE — the causally honest cost of removing the
   look-ahead, but currently undisclosed. Three parts:
   (a) disclose the one-run cancellation lag as a stated boundary in the
   scoreboard/report header wording (plain language);
   (b) the now-unreachable raise at
   `options_researcher/pick_tracker.py:741` is dead code (`:710` already
   raises on `session > self.as_of`, making `:739`'s condition
   unconditionally true) — replace `:739-741` with `return True` (NOT a
   bare delete: the function is annotated `-> bool` and a bare delete
   leaves an implicit-None path; review fix 3);
   (c) add a production-timing cancellation test: coverage change observed
   on day D → the affected pick's cancellation lands in day D+1's run, and
   day D's output is byte-stable.
   **Immutable-history decision (review fix 2, decided in this rev):** the
   header wording lives inside already-committed immutable dryrun
   artifacts (`reports/pick_tracker/dryrun/2026-08-27/scoreboard.*`,
   committed by `704a138`; re-runs at the same `as_of` raise
   `IMMUTABLE_HISTORY_CONFLICT`, `pick_tracker.py:1651-1660`). ACCEPT THE
   SPLIT: the new disclosure applies from the next `as_of` forward;
   2026-08-27's artifacts keep the old header permanently (append-only is
   the point). Do NOT supersede 08-27 and do NOT pass `--supersede-reason`
   through the ritual (its absence is asserted at
   `tests/test_daily_ritual_provenance.py:260`). Also update the verbatim
   header quote in
   `docs/superpowers/plans/2026-08-25-pick-tracker-registration-packet-DRAFT.md:132`
   so the draft packet doesn't go stale.
3. **N3 (unit tests; review line 20 + review fix 1).** The
   `SUPERSEDE_ALREADY_RECORDED` refusal (second distinct supersede
   attempt) has no unit test. IMPORTANT correction to rev 1: "no state
   change" is FALSE — `pick_tracker.py:1691-1692` writes the replacement
   artifacts via `_immutable_write` BEFORE the `:1707` raise, so a second
   distinct supersede leaves a written `supersedes/<as_of>-<new_id>/`
   directory. The test must assert: the named refusal is raised AND no
   supersede receipt is recorded, while explicitly acknowledging (in a
   comment) the partial artifact write as current pinned behavior. Do NOT
   reorder the check to make "no state change" true — behavior pinning
   only. Also add two sibling refusal tests while there (review A3, same
   surface): `SUPERSEDE_NOT_REQUIRED` (`:1655`) and
   `SUPERSEDE_REASON_REQUIRED` (`:1663`). Caution: the module you will
   edit contains a `create=True` mock at `tests/test_pick_tracker.py:613`
   (review NEW-E) — do not disturb it.

## Deliberate no-ops (review A1 — recorded so the coverage claim is honest)

Of the round-5 review's four carry-forward boundaries (its line 42): NEW-A
and NEW-C are handled here; the governed-path file was already closed by
`a35035a`; **NEW-B (midnight-straddle run fails closed, losing that day's
scoreboard; review line 32) is a DELIBERATE NO-OP** — not practically
reachable at the scheduled cadence and fail-closed in the right direction.

## Scope

**IN:** exactly the three items.
**OUT (hard stops):** no behavior change beyond NEW-C's dead-raise
deletion and header disclosure wording; the tracker stays descriptive,
non-verdict-bearing, zero-authority; no ledger writes; no ritual shell
edits; no changes to registered mark schedules, lanes, or the dry-run
gate; no test deletions or weakenings anywhere.

## Acceptance

```
uv run python -m unittest discover -s tests
uv run ruff check . && uv run pyright
```
RED/GREEN for 1 (mutation: bare `exit` in the guarded region → test RED),
2(c), and 3. Born-draft PR; owner un-drafts.
