# Codex brief 35 — pick-tracker round-5 follow-ups (NEW-A, NEW-C, N3)

**Date:** 2026-08-28
**Author:** Claude orchestrating session (Fable), deferred-closeout session
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** DRAFT — pending independent adversarial review before hand-off
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
   exactly as the current assertion is scoped. Locate the test via the
   round-5 receipt's reference; do not touch `tools/daily_ritual.sh`.
2. **NEW-C (disclosure + dead code + one test; review line 30).** The
   tracker's machine-date binding means a live-coverage change cancels a
   pick ONE RITUAL RUN LATE — the causally honest cost of removing the
   look-ahead, but currently undisclosed. Three parts:
   (a) disclose the one-run cancellation lag as a stated boundary in the
   scoreboard/report header wording (plain language);
   (b) the now-unreachable
   `raise TrackerError("coverage observation was not available…")` is dead
   code — delete it (do NOT try to re-reach it; the reviewer offered both
   options and deletion is the smaller change);
   (c) add a production-timing cancellation test: coverage change observed
   on day D → the affected pick's cancellation lands in day D+1's run, and
   day D's output is byte-stable.
3. **N3 (one unit test; review line 20).** The
   `SUPERSEDE_ALREADY_RECORDED` refusal (second distinct supersede
   attempt) has no unit test — pre-existing gap the reviewer exercised
   manually. Pin it: a test that records one supersede, attempts a second
   distinct one, and asserts the named refusal with no state change.

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
