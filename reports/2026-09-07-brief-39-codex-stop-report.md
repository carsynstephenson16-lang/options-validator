# Brief 39 — Codex stop-and-report (2026-09-07 15:06 ET), recorded verbatim in substance

**Executor:** Codex, dispatched by the owner ~15:00 ET against brief 39 rev 6 (`346ba6a`),
worktree `.tmp/worktrees/brief39`, branch `codex/brief39-board-redesign` based on `f83428d`.
**Outcome:** stopped before Task 1 under the brief's stop-and-report rule; no repository
files changed; no commits; no snapshot; no PR. Worktree parked (`git status --porcelain` empty).
**Owner's text (pasted 2026-09-07 15:06 ET) — Codex's report:**

> Stopped before Task 1 because rev 6's supplied code contradicts its cited spec. The spec's
> fail-visible rule (line 200) requires: "Every column carries its as-of; a lane whose as-of
> differs from the board's chain session is marked in the header." But Task 3's supplied
> builder passes `board_as_of` to every lane adapter. The adapters discard the supplied lane
> dates, and Task 5's header renderer prints that substituted date without a mismatch indicator.
> I executed the verbatim Task 3 module in memory with synthetic dated inputs and only its three
> required configuration constants supplied. No cache or provider access was involved:
>
> | Lane | Input evidence date | Board session | Returned column date | Returned state |
> |---|---|---|---|---|
> | Context | 2026-09-03 | 2026-09-04 | 2026-09-04 | READY |
> | Composite | 2026-09-03 | 2026-09-04 | 2026-09-04 | READY |
> | T-bill carry | 2026-09-03 | 2026-09-04 | 2026-09-04 | READY |
>
> No date-mismatch notice appeared in the column notes or board notes. This demonstrates a
> contract failure on injected inputs; it is not a claim about Friday's actual data. …
> Not ready to proceed under "exactly as written." The brief needs a bounded correction
> specifying how each lane derives its displayed evidence date — including mixed-date inputs —
> and how a mismatch is marked, with test-first coverage. I have not substituted my own rule.

**Orchestrator's assessment:** correct, and missed by the author and five adversarial review
rounds (rounds 3–4 built the page but never fed lane inputs dated off the board session).
The defect is real on injected inputs and would have been real on any day the composite /
context / experiment evidence lagged the chain session — which is the common case (closes-based
lanes lag the 15:45 chain capture).

**Correction (brief 39 rev 7):** each adapter derives its own date (baseline = board session
by construction; context = latest `context_max_asof`; composite and experiments = latest
`max_asof` else `asof`, the repo's own convention at `experiments_dashboard.py:74`; QM = the
movement context's session via a new `_qm_as_of` reader); mixed dates within a lane show the
latest and say "mixed as-of (earliest X)"; `build_lane_board` stamps `as_of_mismatch` on any
READY lane whose date is unknown or ≠ the board session and adds a board note; the header prints
`as of X ≠ board` with `class="asof-mismatch"`. Three new module tests + one render assertion
pin it. Bounded round-6 verification before re-dispatch.
